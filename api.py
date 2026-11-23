"""Small local HTTP service for the saved Banking77 intent model."""
import argparse
import json
import logging
import sqlite3
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import joblib

from config import ROOT
from preprocessing import clean_text
from ticket_store import (
    add_agent_note,
    assign_agent,
    department_summary,
    create_ticket,
    decide_ticket,
    feedback_summary,
    get_intents,
    get_ticket,
    init_store,
    list_review_queue,
    list_tickets,
    mark_review_started,
    review_summary,
    resolve_ticket,
    start_ticket,
)
from ticket_routing import DEMO_AGENTS, get_departments

MODEL_PATH = ROOT / "models" / "banking77_intent_model.joblib"
UI_PATH = ROOT / "web" / "index.html"
PROJECT_PATH = ROOT / "web" / "project_journey.html"
ADMIN_PATH = ROOT / "web" / "admin_review.html"
ADMIN_JS_PATH = ROOT / "web" / "admin_review.js"
MAX_TEXT_CHARACTERS = 4000
MAX_BODY_BYTES = 20000
logging.basicConfig(level=logging.INFO, format="%(message)s")


class ServiceState:
    """Shared model and privacy-safe counters for this running process."""

    def __init__(self):
        self.started_at = time.time()
        self.model = None
        self.load_error = None
        self.lock = threading.Lock()
        self.requests = 0
        self.predictions = 0
        self.client_errors = 0
        self.server_errors = 0
        self.total_latency_ms = 0.0
        self.prediction_counts = {}

    def load_model(self):
        try:
            model = joblib.load(MODEL_PATH)
            model_labels = {str(label) for label in model.classes_}
            dataset_labels = set(get_intents())
            if model_labels != dataset_labels:
                raise ValueError("model_labels_do_not_match_dataset_categories")
            self.model = model
            self.load_error = None
        except Exception as error:
            self.model = None
            self.load_error = type(error).__name__
            logging.error(json.dumps({"event": "model_load_failed", "error_type": self.load_error}))

    def record(self, status, elapsed_ms, label=None):
        with self.lock:
            self.requests += 1
            self.total_latency_ms += elapsed_ms
            if status == 200:
                self.predictions += 1
                self.prediction_counts[label] = self.prediction_counts.get(label, 0) + 1
            elif status < 500:
                self.client_errors += 1
            else:
                self.server_errors += 1

    def metrics(self):
        with self.lock:
            count = self.requests
            return {
                "uptime_seconds": round(time.time() - self.started_at, 2),
                "model_ready": self.model is not None,
                "prediction_requests": count,
                "successful_predictions": self.predictions,
                "client_errors": self.client_errors,
                "server_errors": self.server_errors,
                "average_latency_ms": round(self.total_latency_ms / count, 2) if count else 0,
                "predictions_by_intent": dict(sorted(self.prediction_counts.items())),
                "note": "Counters are in memory and reset when this prototype restarts.",
            }


STATE = ServiceState()


class ApiHandler(BaseHTTPRequestHandler):
    """Handle health, metrics, and one-message prediction requests."""

    server_version = "TicketIntentPrototype/1.0"

    def log_message(self, format_string, *args):
        # The standard handler logs request paths. Keep prototype logs structured and minimal.
        return

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        request_path = self.path.partition("?")[0]
        if request_path in ("/", "/index.html", "/project_journey.html", "/admin/review"):
            try:
                if request_path == "/project_journey.html":
                    page_path = PROJECT_PATH
                elif request_path == "/admin/review":
                    page_path = ADMIN_PATH
                else:
                    page_path = UI_PATH
                body = page_path.read_bytes()
            except OSError:
                self.send_json(404, {"error": "ui_not_found"})
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        elif request_path == "/admin_review.js":
            try:
                body = ADMIN_JS_PATH.read_bytes()
            except OSError:
                self.send_json(404, {"error": "ui_not_found"})
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        elif request_path == "/tickets/review-queue":
            self.send_json(200, {"tickets": list_review_queue(), "summary": review_summary()})
        elif request_path == "/tickets/summary":
            self.send_json(200, review_summary())
        elif request_path == "/tickets/feedback":
            self.send_json(200, feedback_summary())
        elif request_path == "/tickets/operations":
            self.send_json(200, {
                "summary": review_summary(),
                "departments": department_summary(),
            })
        elif request_path == "/departments":
            self.send_json(200, {"departments": get_departments()})
        elif request_path == "/agents":
            self.send_json(200, {"demo": True, "agents_by_department": DEMO_AGENTS})
        elif request_path == "/tickets/labels":
            labels = get_intents()
            self.send_json(200, {"labels": labels, "count": len(labels)})
        elif request_path == "/tickets":
            self.send_json(200, {"tickets": list_tickets()})
        elif request_path.startswith("/tickets/"):
            ticket_id = request_path.removeprefix("/tickets/")
            ticket = get_ticket(ticket_id)
            self.send_json(200, ticket) if ticket else self.send_json(404, {"error": "ticket_not_found"})
        elif request_path == "/model-info":
            classifier = (type(STATE.model.named_steps["classifier"]).__name__
                          if STATE.model is not None else None)
            self.send_json(200, {
                "model_ready": STATE.model is not None,
                "classifier": classifier,
                "display_name": f"TF-IDF + {classifier}" if classifier else None,
                "intent_categories": len(STATE.model.classes_) if STATE.model is not None else None,
                "confidence_available": False,
            })
        elif request_path == "/health":
            self.send_json(200, {"status": "alive", "ready": STATE.model is not None})
        elif self.path == "/ready":
            if STATE.model is None:
                self.send_json(503, {"status": "not_ready", "reason": "model_unavailable"})
            else:
                self.send_json(200, {"status": "ready"})
        elif self.path == "/metrics":
            self.send_json(200, STATE.metrics())
        else:
            self.send_json(404, {"error": "not_found"})

    def do_POST(self):
        request_path = self.path.partition("?")[0]
        if request_path.startswith("/tickets/"):
            self.handle_ticket_action(request_path)
            return
        if request_path != "/predict":
            self.send_json(404, {"error": "not_found"})
            return

        started = time.perf_counter()
        request_id = uuid.uuid4().hex[:12]
        status = 500
        label = None
        try:
            if STATE.model is None:
                status = 503
                payload = {"error": "model_unavailable", "request_id": request_id}
            elif not self.headers.get("Content-Type", "").lower().startswith("application/json"):
                status = 415
                payload = {"error": "content_type_must_be_application_json", "request_id": request_id}
            else:
                raw_length = self.headers.get("Content-Length")
                if raw_length is None:
                    status = 411
                    payload = {"error": "content_length_required", "request_id": request_id}
                elif not raw_length.isdigit():
                    status = 400
                    payload = {"error": "invalid_content_length", "request_id": request_id}
                elif int(raw_length) > MAX_BODY_BYTES:
                    status = 413
                    payload = {"error": "request_too_large", "max_bytes": MAX_BODY_BYTES,
                               "request_id": request_id}
                else:
                    try:
                        request = json.loads(self.rfile.read(int(raw_length)))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        request = None
                    if not isinstance(request, dict):
                        status = 400
                        payload = {"error": "body_must_be_a_json_object", "request_id": request_id}
                    elif not isinstance(request.get("text"), str) or not request["text"].strip():
                        status = 400
                        payload = {"error": "text_must_be_a_non_empty_string", "request_id": request_id}
                    elif len(request["text"]) > MAX_TEXT_CHARACTERS:
                        status = 413
                        payload = {"error": "text_too_long", "max_characters": MAX_TEXT_CHARACTERS,
                                   "request_id": request_id}
                    else:
                        cleaned = clean_text(request["text"])
                        if not cleaned:
                            status = 400
                            payload = {"error": "text_has_no_usable_words", "request_id": request_id}
                        else:
                            scores = STATE.model.decision_function([cleaned])[0]
                            top_indices = scores.argsort()[::-1][:3]
                            labels = [str(STATE.model.classes_[index]) for index in top_indices]
                            label = labels[0]
                            status = 200
                            payload = {
                                "suggestion": label,
                                "alternatives": labels[1:],
                                "request_id": request_id,
                                "review_required": True,
                            }
                            try:
                                payload["ticket_id"] = create_ticket(
                                    request_id, request["text"], labels[0], labels[1:]
                                )
                            except Exception as error:
                                status = 500
                                payload = {"error": "ticket_persistence_failed", "request_id": request_id}
                                logging.error(json.dumps({
                                    "event": "ticket_persistence_failed",
                                    "request_id": request_id,
                                    "error_type": type(error).__name__,
                                }))
        except Exception as error:
            # Do not include submitted text or exception details in the response/log.
            status = 500
            payload = {"error": "prediction_failed", "request_id": request_id}
            logging.error(json.dumps({"event": "prediction_failed", "request_id": request_id,
                                      "error_type": type(error).__name__}))

        elapsed_ms = (time.perf_counter() - started) * 1000
        STATE.record(status, elapsed_ms, label)
        logging.info(json.dumps({"event": "prediction_request", "request_id": request_id,
                                 "status": status, "latency_ms": round(elapsed_ms, 2)}))
        self.send_json(status, payload)

    def handle_ticket_action(self, request_path):
        parts = request_path.strip("/").split("/")
        if len(parts) != 3 or parts[0] != "tickets":
            self.send_json(404, {"error": "not_found"})
            return
        ticket_id, action = parts[1], parts[2]
        if action == "start-review":
            try:
                ticket = mark_review_started(ticket_id)
            except sqlite3.Error:
                self.send_json(500, {"error": "review_queue_unavailable"})
                return
            self.send_json(200, ticket) if ticket else self.send_json(404, {"error": "ticket_not_found"})
            return
        if action not in ("approve", "correct", "assign", "start", "notes", "resolve"):
            self.send_json(404, {"error": "not_found"})
            return
        try:
            raw_length = self.headers.get("Content-Length", "0")
            if not raw_length.isdigit() or int(raw_length) > MAX_BODY_BYTES:
                self.send_json(413, {"error": "request_too_large"})
                return
            body = self.rfile.read(int(raw_length)) if int(raw_length) else b"{}"
            request = json.loads(body)
            if not isinstance(request, dict):
                self.send_json(400, {"error": "body_must_be_a_json_object"})
                return
            if action in ("approve", "correct"):
                ticket = decide_ticket(
                    ticket_id,
                    action,
                    final_intent=request.get("intent"),
                    reason=request.get("reason", "") if isinstance(request.get("reason", ""), str) else "",
                )
            elif action == "assign":
                ticket = assign_agent(ticket_id, request.get("agent"))
            elif action == "start":
                ticket = start_ticket(ticket_id)
            elif action == "notes":
                ticket = add_agent_note(ticket_id, request.get("note", "") if isinstance(request.get("note", ""), str) else "")
            else:
                ticket = resolve_ticket(ticket_id, request.get("summary", "") if isinstance(request.get("summary", ""), str) else "")
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(400, {"error": "invalid_json"})
            return
        except ValueError as error:
            self.send_json(400, {"error": str(error)})
            return
        except RuntimeError as error:
            self.send_json(409, {"error": str(error)})
            return
        except sqlite3.Error:
            self.send_json(500, {"error": "ticket_update_failed"})
            return
        self.send_json(200, ticket) if ticket else self.send_json(404, {"error": "ticket_not_found"})


def main():
    parser = argparse.ArgumentParser(description="Run the local Banking77 intent API.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default is local only).")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    init_store()
    STATE.load_model()
    server = ThreadingHTTPServer((args.host, args.port), ApiHandler)
    logging.info(json.dumps({"event": "service_started", "host": args.host, "port": args.port,
                             "model_ready": STATE.model is not None}))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info(json.dumps({"event": "service_stopping"}))
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

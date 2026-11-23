"""Small local HTTP service for the saved Banking77 intent model."""
import argparse
import json
import logging
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import joblib

from config import ROOT
from preprocessing import clean_text

MODEL_PATH = ROOT / "models" / "banking77_intent_model.joblib"
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
            self.model = joblib.load(MODEL_PATH)
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
        if self.path == "/health":
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
        if self.path != "/predict":
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


def main():
    parser = argparse.ArgumentParser(description="Run the local Banking77 intent API.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default is local only).")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

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

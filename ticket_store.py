"""Small SQLite store for reviewable predictions and human decision audit events."""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from config import RAW, ROOT
from ticket_routing import department_for_intent, get_departments

DB_PATH = ROOT / "data" / "tickets.sqlite3"


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def get_intents():
    return json.loads((RAW / "categories.json").read_text(encoding="utf-8"))


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def database():
    connection = connect()
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def init_store():
    """Create the local ticket and audit tables if they do not exist yet."""
    with database() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL UNIQUE,
                message TEXT NOT NULL,
                ai_intent TEXT NOT NULL,
                alternatives_json TEXT NOT NULL,
                review_required INTEGER NOT NULL,
                priority TEXT,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                review_outcome TEXT,
                decision TEXT,
                final_intent TEXT,
                reviewed_by TEXT,
                reviewed_at TEXT,
                correction_reason TEXT,
                assigned_queue TEXT,
                routed_at TEXT,
                assigned_agent TEXT,
                assigned_at TEXT,
                started_at TEXT,
                resolved_at TEXT,
                resolution_summary TEXT
            );
            CREATE TABLE IF NOT EXISTS ticket_audit (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT NOT NULL REFERENCES tickets(ticket_id),
                event_type TEXT NOT NULL,
                event_at TEXT NOT NULL,
                actor TEXT NOT NULL,
                details_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ticket_notes (
                note_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT NOT NULL REFERENCES tickets(ticket_id),
                body TEXT NOT NULL,
                author TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tickets_status_created
                ON tickets(status, created_at);
            CREATE INDEX IF NOT EXISTS idx_tickets_reviewed_at
                ON tickets(reviewed_at);
            CREATE INDEX IF NOT EXISTS idx_audit_ticket_time
                ON ticket_audit(ticket_id, event_at, event_id);
            """
        )
        columns = {row["name"] for row in db.execute("PRAGMA table_info(tickets)")}
        for name, definition in (
            ("assigned_agent", "TEXT"), ("assigned_at", "TEXT"),
            ("started_at", "TEXT"), ("resolved_at", "TEXT"),
            ("resolution_summary", "TEXT"),
        ):
            if name not in columns:
                db.execute(f"ALTER TABLE tickets ADD COLUMN {name} {definition}")


def add_audit(db, ticket_id, event_type, event_at, details=None, actor="System"):
    db.execute(
        """INSERT INTO ticket_audit
           (ticket_id, event_type, event_at, actor, details_json)
           VALUES (?, ?, ?, ?, ?)""",
        (ticket_id, event_type, event_at, actor, json.dumps(details or {})),
    )


def create_ticket(request_id, message, suggestion, alternatives):
    """Persist one successful API prediction as a real review-queue ticket."""
    ticket_id = "TK-" + uuid.uuid4().hex[:8].upper()
    created_at = now_utc()
    with database() as db:
        db.execute(
            """INSERT INTO tickets
               (ticket_id, request_id, message, ai_intent, alternatives_json,
                review_required, created_at, status)
               VALUES (?, ?, ?, ?, ?, 1, ?, 'AWAITING_REVIEW')""",
            (ticket_id, request_id, message, suggestion,
             json.dumps(alternatives), created_at),
        )
        add_audit(db, ticket_id, "TICKET_CREATED", created_at)
        add_audit(db, ticket_id, "AI_CLASSIFIED", created_at, {
            "intent": suggestion,
            "alternatives": alternatives,
        })
    return ticket_id


def serialize_ticket(row):
    if row is None:
        return None
    item = dict(row)
    item["alternatives"] = json.loads(item.pop("alternatives_json"))
    item["review_required"] = bool(item["review_required"])
    item["assigned_department"] = item.get("assigned_queue")
    return item


def list_review_queue():
    with database() as db:
        rows = db.execute(
            """SELECT * FROM tickets
               WHERE status = 'AWAITING_REVIEW'
               ORDER BY created_at ASC"""
        ).fetchall()
    return [serialize_ticket(row) for row in rows]


def list_tickets():
    with database() as db:
        rows = db.execute(
            "SELECT * FROM tickets ORDER BY created_at DESC"
        ).fetchall()
    return [serialize_ticket(row) for row in rows]


def get_ticket(ticket_id):
    with database() as db:
        row = db.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        if row is None:
            return None
        ticket = serialize_ticket(row)
        audit_rows = db.execute(
            """SELECT event_type, event_at, actor, details_json
               FROM ticket_audit WHERE ticket_id = ?
               ORDER BY event_at, event_id""",
            (ticket_id,),
        ).fetchall()
        note_rows = db.execute(
            "SELECT body, author, created_at FROM ticket_notes WHERE ticket_id = ? ORDER BY note_id",
            (ticket_id,),
        ).fetchall()
    ticket["audit"] = [
        {
            "event_type": row["event_type"],
            "event_at": row["event_at"],
            "actor": row["actor"],
            "details": json.loads(row["details_json"]),
        }
        for row in audit_rows
    ]
    ticket["agent_notes"] = [dict(row) for row in note_rows]
    return ticket


def mark_review_started(ticket_id):
    """Record the first time an agent opens the review panel."""
    event_at = now_utc()
    with database() as db:
        row = db.execute(
            "SELECT status FROM tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        if row is None:
            return None
        if row["status"] == "AWAITING_REVIEW":
            exists = db.execute(
                """SELECT 1 FROM ticket_audit
                   WHERE ticket_id = ? AND event_type = 'ADMIN_REVIEW_STARTED'""",
                (ticket_id,),
            ).fetchone()
            if not exists:
                add_audit(
                    db, ticket_id, "ADMIN_REVIEW_STARTED", event_at,
                    actor="Admin (local prototype)",
                )
    return get_ticket(ticket_id)


def decide_ticket(ticket_id, action, final_intent=None, reason=""):
    """Approve or correct a pending ticket, then route it in one transaction."""
    if action not in {"approve", "correct"}:
        raise ValueError("unsupported_review_action")
    if action == "correct" and final_intent not in get_intents():
        raise ValueError("intent_not_in_categories")

    reviewed_at = now_utc()
    actor = "Admin (local prototype)"
    with database() as db:
        row = db.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        if row is None:
            return None
        if row["status"] != "AWAITING_REVIEW":
            raise RuntimeError("ticket_not_awaiting_review")

        ai_intent = row["ai_intent"]
        if action == "correct" and final_intent == ai_intent:
            raise ValueError("correction_must_differ_from_ai_prediction")
        decision = "APPROVED" if action == "approve" else "CORRECTED"
        review_outcome = "HUMAN_VERIFIED" if action == "approve" else "HUMAN_CORRECTED"
        chosen_intent = ai_intent if action == "approve" else final_intent
        queue = department_for_intent(chosen_intent)

        db.execute(
            """UPDATE tickets SET status = 'ROUTED', review_outcome = ?,
               decision = ?, final_intent = ?, reviewed_by = ?, reviewed_at = ?,
               correction_reason = ?, assigned_queue = ?, routed_at = ?
               WHERE ticket_id = ?""",
            (review_outcome, decision, chosen_intent, actor, reviewed_at,
             reason.strip() or None if action == "correct" else None,
             queue, reviewed_at, ticket_id),
        )
        if action == "approve":
            add_audit(db, ticket_id, "CLASSIFICATION_APPROVED", reviewed_at, {
                "ai_intent": ai_intent,
                "final_intent": chosen_intent,
            }, actor=actor)
        else:
            add_audit(db, ticket_id, "CLASSIFICATION_CORRECTED", reviewed_at, {
                "ai_intent": ai_intent,
                "final_intent": chosen_intent,
                "reason": reason.strip() or None,
            }, actor=actor)
        add_audit(db, ticket_id, "TICKET_ROUTED", reviewed_at, {
            "final_intent": chosen_intent,
            "assigned_queue": queue,
        }, actor="Routing rules")
    return get_ticket(ticket_id)


def assign_agent(ticket_id, agent):
    """Assign a configured demo agent to a routed ticket."""
    from ticket_routing import get_demo_agents

    at = now_utc()
    with database() as db:
        row = db.execute("SELECT status, assigned_queue FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
        if row is None:
            return None
        if row["status"] != "ROUTED":
            raise RuntimeError("ticket_must_be_routed_before_assignment")
        if agent not in get_demo_agents(row["assigned_queue"]):
            raise ValueError("agent_not_available_for_department")
        db.execute("UPDATE tickets SET assigned_agent = ?, assigned_at = ? WHERE ticket_id = ?", (agent, at, ticket_id))
        add_audit(db, ticket_id, "AGENT_ASSIGNED", at, {"agent": agent, "department": row["assigned_queue"]}, actor="Admin (local prototype)")
    return get_ticket(ticket_id)


def start_ticket(ticket_id):
    """Start work only after the ticket has an assigned agent."""
    at = now_utc()
    with database() as db:
        row = db.execute("SELECT status, assigned_agent FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
        if row is None:
            return None
        if row["status"] != "ROUTED":
            raise RuntimeError("ticket_must_be_routed_before_work")
        if not row["assigned_agent"]:
            raise RuntimeError("assign_an_agent_before_starting_work")
        db.execute("UPDATE tickets SET status = 'IN_PROGRESS', started_at = ? WHERE ticket_id = ?", (at, ticket_id))
        add_audit(db, ticket_id, "WORK_STARTED", at, {"agent": row["assigned_agent"]}, actor=row["assigned_agent"])
    return get_ticket(ticket_id)


def add_agent_note(ticket_id, note):
    """Store a human-entered internal note on an in-progress ticket."""
    note = note.strip()
    if not note:
        raise ValueError("note_must_not_be_empty")
    if len(note) > 4000:
        raise ValueError("note_too_long")
    at = now_utc()
    with database() as db:
        row = db.execute("SELECT status, assigned_agent FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
        if row is None:
            return None
        if row["status"] != "IN_PROGRESS":
            raise RuntimeError("ticket_must_be_in_progress_to_add_notes")
        author = row["assigned_agent"] or "Demo support agent"
        db.execute("INSERT INTO ticket_notes (ticket_id, body, author, created_at) VALUES (?, ?, ?, ?)", (ticket_id, note, author, at))
        add_audit(db, ticket_id, "AGENT_NOTE_ADDED", at, {"note": note}, actor=author)
    return get_ticket(ticket_id)


def resolve_ticket(ticket_id, summary):
    """Mark a ticket resolved only after an assigned agent supplies a summary."""
    summary = summary.strip()
    if not summary:
        raise ValueError("resolution_summary_required")
    if len(summary) > 4000:
        raise ValueError("resolution_summary_too_long")
    at = now_utc()
    with database() as db:
        row = db.execute("SELECT status, assigned_agent FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
        if row is None:
            return None
        if row["status"] != "IN_PROGRESS":
            raise RuntimeError("ticket_must_be_in_progress_before_resolution")
        if not row["assigned_agent"]:
            raise RuntimeError("assign_an_agent_before_resolution")
        db.execute("UPDATE tickets SET status = 'RESOLVED', resolved_at = ?, resolution_summary = ? WHERE ticket_id = ?", (at, summary, ticket_id))
        add_audit(db, ticket_id, "TICKET_RESOLVED", at, {"summary": summary}, actor=row["assigned_agent"])
    return get_ticket(ticket_id)


def review_summary():
    today = datetime.now(timezone.utc).date().isoformat()
    with database() as db:
        awaiting = db.execute(
            "SELECT COUNT(*) FROM tickets WHERE status = 'AWAITING_REVIEW'"
        ).fetchone()[0]
        approved = db.execute(
            """SELECT COUNT(*) FROM tickets
               WHERE decision = 'APPROVED' AND date(reviewed_at) = ?""",
            (today,),
        ).fetchone()[0]
        corrected = db.execute(
            """SELECT COUNT(*) FROM tickets
               WHERE decision = 'CORRECTED' AND date(reviewed_at) = ?""",
            (today,),
        ).fetchone()[0]
        avg_seconds = db.execute(
            """SELECT AVG((julianday(reviewed_at) - julianday(created_at)) * 86400)
               FROM tickets WHERE reviewed_at IS NOT NULL"""
        ).fetchone()[0]
    with database() as db:
        total = db.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        states = {row["status"]: row["count"] for row in db.execute("SELECT status, COUNT(*) AS count FROM tickets GROUP BY status")}
        verified = db.execute("SELECT COUNT(*) FROM tickets WHERE review_outcome = 'HUMAN_VERIFIED'").fetchone()[0]
        corrected_total = db.execute("SELECT COUNT(*) FROM tickets WHERE review_outcome = 'HUMAN_CORRECTED'").fetchone()[0]
    return {
        "awaiting_review": awaiting,
        "approved_today": approved,
        "corrected_today": corrected,
        "average_review_seconds": round(avg_seconds, 1) if avg_seconds is not None else None,
        "total_tickets": total,
        "human_verified": verified,
        "human_corrected": corrected_total,
        "routed": states.get("ROUTED", 0),
        "in_progress": states.get("IN_PROGRESS", 0),
        "resolved": states.get("RESOLVED", 0),
    }


def department_summary():
    with database() as db:
        rows = db.execute(
            "SELECT assigned_queue AS department, COUNT(*) AS count FROM tickets WHERE assigned_queue IS NOT NULL GROUP BY assigned_queue ORDER BY assigned_queue"
        ).fetchall()
    counts = {row["department"]: row["count"] for row in rows}
    return [{"department": item["name"], "count": counts.get(item["name"], 0)} for item in get_departments()]


def feedback_summary():
    with database() as db:
        rows = db.execute(
            """SELECT ai_intent, final_intent, decision, COUNT(*) AS count
               FROM tickets WHERE review_outcome IS NOT NULL
               GROUP BY ai_intent, final_intent, decision
               ORDER BY count DESC"""
        ).fetchall()
    total = sum(row["count"] for row in rows)
    agreement = sum(row["count"] for row in rows if row["ai_intent"] == row["final_intent"])
    corrected = sum(row["count"] for row in rows if row["decision"] == "CORRECTED")
    return {
        "reviewed_total": total,
        "approved_total": total - corrected,
        "corrected_total": corrected,
        "agreement_rate": round(agreement / total, 4) if total else None,
        "correction_rate": round(corrected / total, 4) if total else None,
        "intent_outcomes": [dict(row) for row in rows],
    }

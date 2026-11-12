"""Local SQLite persistence. All workflow writes use an immediate transaction."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from clinic_agent_lab.models import Case, Event, State

TRANSITIONS = {
    State.ACCEPTED: {State.GATHERING, State.FAILED, State.EXPIRED},
    State.GATHERING: {State.DRAFTED, State.FAILED, State.EXPIRED},
    State.DRAFTED: {State.AWAITING, State.FAILED, State.EXPIRED},
    State.AWAITING: {State.CONFIRMED, State.REJECTED, State.EXPIRED, State.FAILED},
    State.CONFIRMED: set(), State.REJECTED: set(), State.EXPIRED: set(), State.FAILED: set(),
}


class WorkflowError(Exception):
    def __init__(self, message: str, status_code: int = 409):
        super().__init__(message)
        self.status_code = status_code


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS cases (
                    id TEXT PRIMARY KEY, clientCaseId TEXT UNIQUE NOT NULL,
                    fixture_id TEXT NOT NULL, patient_id TEXT NOT NULL, status TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, expires_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT NOT NULL REFERENCES cases(id),
                    kind TEXT NOT NULL, payload TEXT NOT NULL, timestamp TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS drafts (
                    case_id TEXT PRIMARY KEY REFERENCES cases(id),
                    order_json TEXT NOT NULL, card_json TEXT NOT NULL
                );
            """)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def event(self, conn, case_id: str, kind: str, payload: dict, now: datetime):
        conn.execute(
            "INSERT INTO events(case_id,kind,payload,timestamp) VALUES(?,?,?,?)",
            (case_id, kind, json.dumps(payload, sort_keys=True), now.isoformat()),
        )

    def case(self, conn, case_id: str) -> Case:
        row = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        if row is None:
            raise WorkflowError("Case not found", 404)
        return Case.model_validate(dict(row))

    def create(self, conn, client_id: str, fixture_id: str, now: datetime, ttl: float):
        existing = conn.execute(
            "SELECT * FROM cases WHERE clientCaseId=?", (client_id,)
        ).fetchone()
        if existing:
            case = Case.model_validate(dict(existing))
            if case.fixture_id != fixture_id:
                raise WorkflowError("clientCaseId already belongs to another fixture")
            return case, False
        case = Case(
            id=str(uuid4()), clientCaseId=client_id, fixture_id=fixture_id, patient_id=fixture_id,
            status=State.ACCEPTED, created_at=now, updated_at=now,
            expires_at=now + timedelta(seconds=ttl),
        )
        conn.execute("INSERT INTO cases VALUES(?,?,?,?,?,?,?,?)", tuple(
            case.model_dump(mode="json").values()
        ))
        self.event(conn, case.id, "state", {"from": None, "to": State.ACCEPTED}, now)
        return case, True

    def transition(self, conn, case_id: str, target: State, now: datetime) -> Case:
        case = self.case(conn, case_id)
        if target not in TRANSITIONS[case.status]:
            raise WorkflowError(f"Illegal transition: {case.status} -> {target}")
        conn.execute("UPDATE cases SET status=?,updated_at=? WHERE id=?",
                     (target, now.isoformat(), case_id))
        self.event(conn, case_id, "state", {"from": case.status, "to": target}, now)
        return self.case(conn, case_id)

    def events(self, conn, case_id: str) -> list[Event]:
        return [Event(**{**dict(row), "payload": json.loads(row["payload"])}) for row in
                conn.execute("SELECT * FROM events WHERE case_id=? ORDER BY id", (case_id,))]

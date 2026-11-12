"""Synchronous, locally persisted deterministic agent loop."""

from collections.abc import Callable
from datetime import UTC, datetime

from clinic_agent_lab.data import get_fixture
from clinic_agent_lab.models import MedicationRequest, SafetyCard, State
from clinic_agent_lab.rules import evaluate_rules
from clinic_agent_lab.store import Store, WorkflowError
from clinic_agent_lab.tools import TOOL_ORDER, Tools


def utc_now() -> datetime:
    return datetime.now(UTC)


class AgentService:
    def __init__(self, store: Store, ttl_seconds: float = 300,
                 clock: Callable[[], datetime] = utc_now, tools: Tools | None = None):
        if ttl_seconds <= 0:
            raise ValueError("TTL must be positive")
        self.store, self.ttl_seconds, self.clock = store, ttl_seconds, clock
        self.tools = tools or Tools()

    def submit(self, client_id: str, fixture_id: str) -> dict:
        if not client_id.strip() or len(client_id) > 120:
            raise WorkflowError("clientCaseId must contain 1-120 characters", 422)
        try:
            fixture = get_fixture(fixture_id)
        except ValueError as exc:
            raise WorkflowError(str(exc), 422) from exc
        now = self.clock()
        with self.store.transaction() as conn:
            case, created = self.store.create(conn, client_id, fixture_id, now, self.ttl_seconds)
            if created:
                self.store.transition(conn, case.id, State.GATHERING, now)
                try:
                    outputs = {}
                    for name in TOOL_ORDER[:-1]:
                        outputs[name] = getattr(self.tools, name)(fixture)
                        self.store.event(conn, case.id, "tool", {
                            "name": name, "result": outputs[name],
                        }, self.clock())
                    # Revalidate gathered inputs; tools, not hidden model context, feed rules.
                    gathered = fixture.model_dump()
                    gathered.update(outputs["get_patient_summary"])
                    gathered.update(observations=outputs["get_labs"],
                                    allergies=outputs["get_allergies"],
                                    medications=outputs["get_medications"])
                    fixture = type(fixture).model_validate(gathered)
                    order = MedicationRequest.model_validate(self.tools.draft_order(fixture))
                    card = evaluate_rules(fixture, order)
                    conn.execute("INSERT INTO drafts VALUES(?,?,?)", (
                        case.id, order.model_dump_json(), card.model_dump_json(),
                    ))
                    self.store.event(conn, case.id, "tool", {
                        "name": "draft_order", "result": order.model_dump(),
                    }, self.clock())
                    self.store.transition(conn, case.id, State.DRAFTED, self.clock())
                    self.store.event(conn, case.id, "safety_card", card.model_dump(), self.clock())
                    self.store.transition(conn, case.id, State.AWAITING, self.clock())
                except Exception as exc:
                    self.store.event(conn, case.id, "failure", {
                        "error_type": type(exc).__name__, "message": "Demo tool loop failed",
                    }, self.clock())
                    self.store.transition(conn, case.id, State.FAILED, self.clock())
            return self._detail(conn, case.id)

    def _detail(self, conn, case_id: str) -> dict:
        case = self.store.case(conn, case_id)
        row = conn.execute("SELECT * FROM drafts WHERE case_id=?", (case_id,)).fetchone()
        return {
            "case": case.model_dump(mode="json"),
            "draft": MedicationRequest.model_validate_json(row["order_json"]).model_dump()
            if row else None,
            "safety_card": SafetyCard.model_validate_json(row["card_json"]).model_dump()
            if row else None,
            "events": [item.model_dump(mode="json")
                       for item in self.store.events(conn, case_id)],
            "draft_count": int(row is not None),
        }

    def get(self, case_id: str) -> dict:
        with self.store.transaction() as conn:
            return self._detail(conn, case_id)

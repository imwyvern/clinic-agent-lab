from datetime import UTC, datetime, timedelta

import pytest

from clinic_agent_lab.data import load_fixtures
from clinic_agent_lab.models import PhysicianDecision
from clinic_agent_lab.service import AgentService
from clinic_agent_lab.store import Store, WorkflowError


class Clock:
    def __init__(self):
        self.now = datetime(2026, 1, 1, tzinfo=UTC)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)


@pytest.fixture
def service(tmp_path):
    return AgentService(Store(tmp_path / "safety.db"), ttl_seconds=10, clock=Clock())


def physician(action="confirm", role="physician"):
    return PhysicianDecision(action=action, role=role, actor="demo-physician", reason="Demo review")


BLOCK_FIXTURES = [f.id for f in load_fixtures().values() if f.expected_level == "block"]
WARN_FIXTURES = [f.id for f in load_fixtures().values() if f.scenario.startswith("missing_labs")]


@pytest.mark.parametrize("fixture_id", BLOCK_FIXTURES)
def test_fixture_block_hits_and_confirmation_refusal(service, fixture_id):
    detail = service.submit(fixture_id, fixture_id)
    case_id = detail["case"]["id"]
    assert detail["safety_card"]["level"] == "block"
    with pytest.raises(WorkflowError, match="cannot be confirmed"):
        service.decide(case_id, physician())
    assert service.get(case_id) == detail
    assert service.decide(case_id, physician("reject"))["case"]["status"] == "rejected"


@pytest.mark.parametrize("fixture_id", WARN_FIXTURES)
@pytest.mark.parametrize("action,terminal", [("confirm", "confirmed"), ("reject", "rejected")])
def test_missing_lab_only_warn_allows_both_decisions(service, fixture_id, action, terminal):
    detail = service.submit(fixture_id, fixture_id)
    assert detail["safety_card"]["level"] == "warn"
    assert service.decide(detail["case"]["id"], physician(action))["case"]["status"] == terminal


@pytest.mark.parametrize("action", ["confirm", "reject"])
def test_observer_cannot_decide(service, action):
    detail = service.submit("observer", "syn-001")
    with pytest.raises(WorkflowError, match="physician role"):
        service.decide(detail["case"]["id"], physician(action, role="observer"))
    assert service.get(detail["case"]["id"]) == detail


@pytest.mark.parametrize("trigger", ["read", "list", "replay", "confirm"])
def test_timeout_is_lazy_persisted_and_late_confirm_denied(service, trigger):
    detail = service.submit("timeout", "syn-005")
    case_id = detail["case"]["id"]
    service.clock.advance(10)
    if trigger == "read":
        assert service.get(case_id)["case"]["status"] == "expired"
    elif trigger == "list":
        assert service.list_cases()[0]["status"] == "expired"
    elif trigger == "replay":
        assert service.submit("timeout", "syn-005")["case"]["status"] == "expired"
    with pytest.raises(WorkflowError, match="expired"):
        service.decide(case_id, physician())
    reopened = AgentService(Store(service.store.path), clock=service.clock)
    assert reopened.get(case_id)["case"]["status"] == "expired"
    assert sum(e["kind"] == "state" and e["payload"]["to"] == "expired"
               for e in reopened.get(case_id)["events"]) == 1


@pytest.mark.parametrize("fixture", list(load_fixtures().values()), ids=lambda f: f.id)
def test_entire_p0_never_activates_or_executes_order(service, fixture):
    before = service.submit(fixture.id, fixture.id)
    assert before["draft"]["status"] == "draft"
    assert before["case"]["status"] == "awaiting_physician"
    action = "reject" if fixture.expected_level == "block" else "confirm"
    after = service.decide(before["case"]["id"], physician(action))
    assert after["draft"] == before["draft"] == after["safety_card"]["draft"]
    assert after["draft"]["status"] == "draft"
    assert after["draft"]["intent"] == "proposal"
    assert service.submit(fixture.id, fixture.id) == after
    with pytest.raises(WorkflowError, match="decision refused"):
        service.decide(before["case"]["id"], physician())
    with service.store.transaction() as conn:
        assert conn.execute("SELECT COUNT(*) FROM drafts WHERE case_id=?",
                            (before["case"]["id"],)).fetchone()[0] == 1


@pytest.mark.parametrize("ttl", [0, -1, float("inf"), float("nan")])
def test_invalid_timeout_is_rejected(tmp_path, ttl):
    with pytest.raises(ValueError):
        AgentService(Store(tmp_path / "ttl.db"), ttl_seconds=ttl)

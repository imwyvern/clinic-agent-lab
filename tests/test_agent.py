from concurrent.futures import ThreadPoolExecutor

from clinic_agent_lab.service import AgentService
from clinic_agent_lab.store import Store
from clinic_agent_lab.tools import TOOL_ORDER, Tools


def test_loop_timeline_persists_and_replays(tmp_path):
    service = AgentService(Store(tmp_path / "agent.db"))
    detail = service.submit("normal", "syn-001")
    assert detail["case"]["status"] == "awaiting_physician"
    assert detail["safety_card"]["level"] == "clear"
    events = detail["events"]
    assert [e["payload"]["name"] for e in events if e["kind"] == "tool"] == list(TOOL_ORDER)
    assert [e["payload"]["to"] for e in events if e["kind"] == "state"] == [
        "accepted", "gathering", "drafted", "awaiting_physician",
    ]
    assert len([e for e in events if e["kind"] == "safety_card"]) == 1
    assert detail["draft_count"] == 1
    assert AgentService(Store(service.store.path)).get(detail["case"]["id"]) == detail
    assert service.submit("normal", "syn-001") == detail


def test_concurrent_replay_produces_one_draft(tmp_path):
    service = AgentService(Store(tmp_path / "agent.db"))
    with ThreadPoolExecutor(max_workers=4) as pool:
        details = list(pool.map(lambda _: service.submit("replay", "syn-006"), range(8)))
    assert all(detail == details[0] for detail in details)
    with service.store.transaction() as conn:
        assert conn.execute("SELECT COUNT(*) FROM drafts").fetchone()[0] == 1
    assert details[0]["draft"]["status"] == "draft"


def test_tool_failure_is_safe_and_persisted(tmp_path):
    class FailingTools(Tools):
        def get_labs(self, fixture):
            raise RuntimeError("synthetic failure")
    service = AgentService(Store(tmp_path / "agent.db"), tools=FailingTools())
    detail = service.submit("failure", "syn-001")
    assert detail["case"]["status"] == "failed"
    assert detail["draft"] is None and detail["safety_card"] is None
    assert any(e["kind"] == "failure" for e in detail["events"])
    assert service.submit("failure", "syn-001") == detail


def test_tools_supply_rule_context(tmp_path):
    class MissingLabs(Tools):
        def get_labs(self, fixture):
            return []
    service = AgentService(Store(tmp_path / "agent.db"), tools=MissingLabs())
    detail = service.submit("gathered", "syn-001")
    assert detail["safety_card"]["level"] == "warn"
    assert detail["safety_card"]["missing_data"] == ["creatinine"]

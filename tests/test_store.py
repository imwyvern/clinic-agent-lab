from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest

from clinic_agent_lab.models import State
from clinic_agent_lab.store import TRANSITIONS, Store, WorkflowError

NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "test.db")


def test_persisted_idempotency_and_payload_conflict(store):
    with store.transaction() as conn:
        case, created = store.create(conn, "business-1", "syn-001", NOW, 30)
        assert created
    reopened = Store(store.path)
    with reopened.transaction() as conn:
        replay, created = reopened.create(conn, "business-1", "syn-001", NOW, 30)
        assert not created and replay == case
        assert len(reopened.events(conn, case.id)) == 1
        with pytest.raises(WorkflowError, match="another fixture"):
            reopened.create(conn, "business-1", "syn-002", NOW, 30)


@pytest.mark.parametrize("source,target", [(s, t) for s, ts in TRANSITIONS.items() for t in ts])
def test_all_legal_transitions(store, source, target):
    with store.transaction() as conn:
        case, _ = store.create(conn, "legal", "syn-001", NOW, 30)
        # Arrange source state directly; transition behavior is under test.
        conn.execute("UPDATE cases SET status=? WHERE id=?", (source, case.id))
        assert store.transition(conn, case.id, target, NOW).status == target


@pytest.mark.parametrize("source,target", [
    (State.ACCEPTED, State.CONFIRMED), (State.GATHERING, State.AWAITING),
    (State.CONFIRMED, State.REJECTED), (State.EXPIRED, State.CONFIRMED),
    (State.REJECTED, State.AWAITING), (State.FAILED, State.GATHERING),
])
def test_illegal_transitions_are_rejected(store, source, target):
    with store.transaction() as conn:
        case, _ = store.create(conn, "illegal", "syn-001", NOW, 30)
        conn.execute("UPDATE cases SET status=? WHERE id=?", (source, case.id))
        with pytest.raises(WorkflowError, match="Illegal transition"):
            store.transition(conn, case.id, target, NOW)
        assert store.case(conn, case.id).status == source


def test_concurrent_unique_business_key(store):
    def create(_):
        with store.transaction() as conn:
            case, _created = store.create(conn, "same", "syn-001", NOW, 30)
            return case.id
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert len(set(pool.map(create, range(8)))) == 1
    with store.transaction() as conn:
        assert conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0] == 1


def test_transaction_rolls_back(store):
    with pytest.raises(RuntimeError), store.transaction() as conn:
        store.create(conn, "rollback", "syn-001", NOW, 30)
        raise RuntimeError("synthetic failure")
    with store.transaction() as conn:
        assert conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0] == 0

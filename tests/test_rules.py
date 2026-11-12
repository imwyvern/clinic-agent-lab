import copy

import pytest
from pydantic import ValidationError

from clinic_agent_lab.data import get_fixture, load_fixtures
from clinic_agent_lab.models import Fixture, Level, MedicationRequest
from clinic_agent_lab.rules import RULE_IDS, evaluate_rules

FIXTURES = list(load_fixtures().values())


def test_fixture_inventory():
    assert len(FIXTURES) == 10
    assert len(RULE_IDS) == 4
    assert len(set(RULE_IDS)) == 4
    assert all(f.synthetic is True and f.license == "Apache-2.0" for f in FIXTURES)
    assert {f.scenario for f in FIXTURES} >= {
        "normal", "allergy", "missing_labs", "duplicate", "expired",
        "idempotent_replay", "physician_reject", "blocked_confirm", "overdose",
    }


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda f: f.id)
def test_fixture_rule_hits_and_determinism(fixture):
    original = copy.deepcopy(fixture.model_dump())
    first, second = evaluate_rules(fixture), evaluate_rules(fixture)
    assert first == second
    assert fixture.model_dump() == original
    assert first.level == fixture.expected_level
    assert first.draft.status == "draft"
    assert "Demo Rule Pack" in first.disclaimer


@pytest.mark.parametrize("dose,expected", [(99, "block"), (100, "clear"),
                                             (500, "clear"), (501, "block")])
def test_demo_dose_boundaries(dose, expected):
    fixture = get_fixture("syn-001")
    order = fixture.proposed_order.model_copy(update={"dose_mg": dose})
    assert evaluate_rules(fixture, order).level == expected


def test_combined_rules_preserve_block_and_all_evidence():
    fixture = get_fixture("syn-002").model_copy(update={"observations": []})
    card = evaluate_rules(fixture)
    assert card.level == Level.BLOCK
    assert card.rule_ids == ["DEMO-ALLERGY-001", "DEMO-LAB-002"]
    assert card.missing_data == ["creatinine"]
    assert card.conflicts


@pytest.mark.parametrize("field,value", [("synthetic", False), ("license", "unknown")])
def test_reject_unmarked_or_unlicensed_fixture(field, value):
    data = get_fixture("syn-001").model_dump()
    data[field] = value
    with pytest.raises(ValidationError):
        Fixture.model_validate(data)


@pytest.mark.parametrize("status", ["active", "completed", "executed"])
def test_order_model_cannot_represent_execution(status):
    with pytest.raises(ValidationError):
        MedicationRequest(medication="amoxicillin", dose_mg=250, status=status)


def test_unknown_fixture_is_not_a_file_path():
    with pytest.raises(ValueError, match="Unknown synthetic"):
        get_fixture("../record.json")

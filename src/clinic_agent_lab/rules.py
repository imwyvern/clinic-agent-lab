"""Self-authored Demo Rule Pack. Arbitrary demo bounds, NOT clinical guidelines."""

from clinic_agent_lab.models import Fixture, Level, MedicationRequest, SafetyCard

RULE_IDS = ("DEMO-ALLERGY-001", "DEMO-LAB-002", "DEMO-DUPLICATE-003", "DEMO-DOSE-004")
# These numbers exist only to exercise branches. Do not use them for prescribing.
DEMO_FORMULARY = {"amoxicillin": (100, 500), "acetaminophen": (100, 500)}
REQUIRED_LAB = "creatinine"


def evaluate_rules(fixture: Fixture, draft: MedicationRequest | None = None) -> SafetyCard:
    """Pure and deterministic; never mutates input, reads a clock, or calls a model."""
    order = draft or fixture.proposed_order
    hits, missing, conflicts, explanations = [], [], [], []
    level = Level.CLEAR
    if order.medication == "amoxicillin" and any(
        item.substance.lower() in {"penicillin", "amoxicillin"} for item in fixture.allergies
    ):
        hits.append(RULE_IDS[0])
        conflicts.append("penicillin-class allergy / amoxicillin")
        explanations.append("Demo allergy rule blocks this penicillin-class proposal.")
        level = Level.BLOCK
    if not any(lab.code == REQUIRED_LAB for lab in fixture.observations):
        hits.append(RULE_IDS[1])
        missing.append(REQUIRED_LAB)
        explanations.append("Demo workflow requires a creatinine observation; it is missing.")
        if level != Level.BLOCK:
            level = Level.WARN
    if any(item.medication.lower() == order.medication for item in fixture.medications):
        hits.append(RULE_IDS[2])
        conflicts.append(f"duplicate medication: {order.medication}")
        explanations.append("Demo duplicate-medication rule requires physician review.")
        if level != Level.BLOCK:
            level = Level.WARN
    lower, upper = DEMO_FORMULARY[order.medication]
    if not lower <= order.dose_mg <= upper:
        hits.append(RULE_IDS[3])
        conflicts.append(f"dose {order.dose_mg:g} mg outside demo interval [{lower}, {upper}]")
        explanations.append("Dose is outside arbitrary demo bounds, not prescribing guidance.")
        level = Level.BLOCK
    if not hits:
        explanations.append("No Demo Rule Pack hits. This is not evidence of clinical safety.")
    return SafetyCard(
        level=level, rule_ids=hits, missing_data=missing, conflicts=conflicts,
        draft=order, explanations=explanations,
    )

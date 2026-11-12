"""Deterministic four-read/one-draft tools. No external model or order execution."""

from clinic_agent_lab.models import Fixture, MedicationRequest

TOOL_ORDER = (
    "get_patient_summary", "get_labs", "get_allergies", "get_medications", "draft_order",
)


class Tools:
    def get_patient_summary(self, fixture: Fixture) -> dict:
        return {"patient": fixture.patient.model_dump(),
                "encounter": fixture.encounter.model_dump()}

    def get_labs(self, fixture: Fixture) -> list[dict]:
        return [item.model_dump() for item in fixture.observations]

    def get_allergies(self, fixture: Fixture) -> list[dict]:
        return [item.model_dump() for item in fixture.allergies]

    def get_medications(self, fixture: Fixture) -> list[dict]:
        return [item.model_dump() for item in fixture.medications]

    def draft_order(self, fixture: Fixture) -> MedicationRequest:
        # A fixture-specified proposal, never an inferred diagnosis or treatment plan.
        return fixture.proposed_order.model_copy(deep=True)

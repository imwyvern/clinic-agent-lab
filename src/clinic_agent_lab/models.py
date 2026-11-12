"""Small FHIR-style demo objects, deliberately not a FHIR implementation."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Level(StrEnum):
    CLEAR = "clear"
    CAUTION = "caution"
    WARN = "warn"
    BLOCK = "block"


class Patient(Model):
    resourceType: Literal["Patient"] = "Patient"
    id: str
    name: str


class Encounter(Model):
    resourceType: Literal["Encounter"] = "Encounter"
    id: str
    subject: str
    workflow: Literal["outpatient-medication-demo"] = "outpatient-medication-demo"


class Observation(Model):
    resourceType: Literal["Observation"] = "Observation"
    code: str
    value: float
    unit: str


class AllergyIntolerance(Model):
    resourceType: Literal["AllergyIntolerance"] = "AllergyIntolerance"
    substance: str


class MedicationStatement(Model):
    resourceType: Literal["MedicationStatement"] = "MedicationStatement"
    medication: str


class MedicationRequest(Model):
    resourceType: Literal["MedicationRequest"] = "MedicationRequest"
    status: Literal["draft"] = "draft"
    intent: Literal["proposal"] = "proposal"
    medication: Literal["amoxicillin", "acetaminophen"]
    dose_mg: float = Field(gt=0, allow_inf_nan=False)


class Fixture(Model):
    id: str = Field(pattern=r"^syn-\d{3}$")
    synthetic: Literal[True]
    license: Literal["Apache-2.0"]
    note: Literal["SYNTHETIC. Fictional patient. Not derived from any real record."]
    scenario: str
    patient: Patient
    encounter: Encounter
    observations: list[Observation]
    allergies: list[AllergyIntolerance]
    medications: list[MedicationStatement]
    proposed_order: MedicationRequest
    expected_level: Level


class SafetyCard(Model):
    level: Level
    rule_ids: list[str]
    missing_data: list[str]
    conflicts: list[str]
    draft: MedicationRequest
    explanations: list[str]
    disclaimer: str = (
        "SYNTHETIC. Not a medical device. Demo Rule Pack only; not clinical guidance. "
        "No orders are executed."
    )


class State(StrEnum):
    ACCEPTED = "accepted"
    GATHERING = "gathering"
    DRAFTED = "drafted"
    AWAITING = "awaiting_physician"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    FAILED = "failed"


class Case(Model):
    id: str
    clientCaseId: str
    fixture_id: str
    patient_id: str
    status: State
    created_at: datetime
    updated_at: datetime
    expires_at: datetime


class Event(Model):
    id: int
    case_id: str
    kind: str
    payload: dict
    timestamp: datetime


class PhysicianDecision(Model):
    action: Literal["confirm", "reject"]
    role: Literal["physician", "observer"]
    actor: str = Field(min_length=1, max_length=80)
    reason: str | None = Field(default=None, max_length=500)

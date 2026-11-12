# Data and licensing

All **10** files in `fixtures/synthetic/` are self-authored **SYNTHETIC** fixtures, not
derived from any real record or external dataset. Each JSON explicitly declares
`synthetic: true`, `license: "Apache-2.0"`, and
`SYNTHETIC. Fictional patient. Not derived from any real record.`
Patients use obvious labels `Pat syn-001` through `Pat syn-010`; IDs are fictional.

| Fixture | Scenario | Independently authored expected level |
| --- | --- | --- |
| syn-001 | Normal confirm | clear |
| syn-002 | Penicillin-class allergy | block |
| syn-003 | Missing required lab | warn |
| syn-004 | Duplicate medication | warn |
| syn-005 | Expiration scenario | clear |
| syn-006 | Idempotent replay | clear |
| syn-007 | Physician rejection | clear |
| syn-008 | Blocked confirmation | block |
| syn-009 | Dose outside demo interval | block |
| syn-010 | Missing lab with rejection | warn |

Each contains minimal Patient, Encounter, Observation, AllergyIntolerance,
MedicationStatement and a draft MedicationRequest. These are FHIR-style names and
simplified JSON objects, not full FHIR resources, a certified implementation or a real EHR.
Scenario labels select demonstration behavior; an expiration fixture is not inherently
expired until its persisted deadline passes. Physician decisions are separate workflow events.

There are no real names, record numbers, hospital IDs, device brands or drug brands.
Only generic medication names are used. The API selects these bundled IDs and cannot
import patient records. Free-text demo actor/reason fields must stay fictional.

Code, documentation, fixtures and the four original Demo Rule Pack rules are licensed
under [Apache-2.0](../LICENSE); see [NOTICE](../NOTICE). No external dataset license or
data-use credential is needed. Third-party Python dependencies retain their own licenses.
Not a medical device; no clinical validity follows from these fixtures or their labels.

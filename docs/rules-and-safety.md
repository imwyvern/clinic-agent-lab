# Demo Rule Pack and safety cards

**Self-authored, demo-only, not clinical guidelines. Not a medical device.** The four
rules exist to exercise safety-gate branches on fictional fixtures. No society or medical
authority endorses them; the dose bounds are arbitrary and must never guide prescribing.

| Rule ID | Demonstration condition | Level | Card evidence |
| --- | --- | --- | --- |
| DEMO-ALLERGY-001 | amoxicillin proposal plus penicillin/amoxicillin allergy label | block | Allergy/drug conflict |
| DEMO-LAB-002 | creatinine observation absent | warn | Missing creatinine |
| DEMO-DUPLICATE-003 | Proposed generic drug also appears in MedicationStatement | warn | Duplicate drug conflict |
| DEMO-DOSE-004 | Dose outside inclusive demo interval 100–500 mg for either bundled generic drug | block | Dose and demo bounds |

These intervals describe a single numeric demo field, not a regimen, dosing frequency,
age/weight adjustment or clinically valid prescription. Lab values are not interpreted;
the rule only tests presence. Missing allergy/medication lists are not inferred as proof
of safety. Fixtures are deliberately small and controlled, with no real-care coverage claim.

`evaluate_rules` is a pure function: no clock, I/O, external model or mutation. Hits are
returned in the fixed table order. Evidence is additive: missing data and conflicts remain
visible even when a stronger rule blocks. `block` dominates `warn`; a hit-free card is `clear`.
`caution` is an available schema level reserved for future use; no P0 rule produces it.

Every draft has a persisted card with `level`, `rule_ids`, `missing_data`, `conflicts`,
`draft`, `explanations` and a disclaimer. Explanations come from local templates and never
quote or claim a clinical guideline. Card and proposal are immutable snapshots on replay.

`clear` is not evidence of clinical safety. Both `clear` and `warn` permit a demo physician
to confirm or reject the workflow decision. `block` cannot be confirmed by any role; the
case remains awaiting_physician, still rejectable or eligible for expiry. An `observer`
cannot confirm or reject any level. Roles are unauthenticated demo labels.

At all levels, before and after every decision, MedicationRequest remains `draft` with
intent `proposal`. Nothing sends or executes a medical order. Timeout ends the workflow
as expired, and a late confirm is refused. The UI repeats this boundary on every card.

# Evaluation method and actual results

Run timestamp: **2026-11-12T11:52:21.731152+08:00 (HKT, UTC+8)**. Version 0.1.0.
This run uses **10 SYNTHETIC fixtures** and **4
self-authored demo rules**. These are fixture-only rule hits and workflow checks, not
model accuracy, diagnostic performance, clinician agreement, or clinical validation.

Reproduce from the repository root after installing `.[dev]`:

```bash
ruff check .
pytest
python -m clinic_agent_lab.evaluate --output .demo/evaluation.json
python scripts/check_docs.py
```

To regenerate this table and the committed [raw report](evaluation-results.json) from
an actual run, use `python scripts/update_evaluation.py`. Timestamps will change; metric
counts should remain stable on the same fixtures. Do not type invented measurements.

| Check | Passed | Total | Meaning of denominator |
| --- | ---: | ---: | --- |
| deterministic_rules | 10 | 10 | Each fixture evaluated twice with exact card equality |
| idempotency | 10 | 10 | Each fixture replayed after a physician decision, one draft |
| draft_only | 10 | 10 | Each fixture before/after confirm or reject retains the same draft |
| fixture_block_hits | 3 | 3 | Independently labeled allergy/dose block fixtures |
| block_confirmation_refusal | 3 | 3 | Attempted confirm on each labeled block fixture |
| missing_lab_warn | 2 | 2 | Independently labeled missing-lab-only fixtures |
| warn_decisions | 4 | 4 | Confirm and reject on separate cases for each missing-lab fixture |
| expiry_refusal | 1 | 1 | Injected-clock deadline, late confirm refused and expired persisted |

Fixture expectations are authored in JSON independently of the rule function. Block
fixtures are syn-002, syn-008 and syn-009; missing-lab-only fixtures are syn-003 and syn-010.
The duplicate-medication fixture is checked by pytest as a warning. A hit-free result means
only that these four demo rules did not match; it is not proof of clinical safety.

The evaluation harness creates a fresh temporary SQLite store inside `.demo/` and uses an
injected UTC clock for exact-deadline expiration. It never needs keys, real records or an
external model. It independently constructs warning decision cases so terminal decisions
are not overwritten. Safety cards, proposed orders and replayed detail snapshots are compared.

`pytest` additionally locks legal and illegal state transitions, concurrent business-key
replays, persistence on reopening, observer rejection, tool failures and malformed model
instances, dose boundaries, HTTP/forms and escaping, real-HTTP demo, and the documentation
gate. Run pytest twice to check the same fixture outcomes; no stochastic inference exists.
The six READMEs are checked against runtime fixture/rule/version counts, state names,
commands, safety boundaries, planned scope and local links. Evaluation results are also
checked against a fresh run with timestamps excluded.

Limits: the small self-authored fixtures are intentionally narrow; expectations are not
clinical ground truth. No real-data generalization, trained model, doctor comparison,
production throughput or measured latency is claimed. This is not a medical device.

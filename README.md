# clinic-agent-lab

Version **0.1.0** · Apache-2.0 · [GitHub: imwyvern](https://github.com/imwyvern)

> **Honest boundary:** SYNTHETIC data only; **not a medical device**. No diagnosis,
> no clinical model training, no auto-executed orders, and not a production system.
> Never enter real patient data. Every proposal remains a MedicationRequest `draft`,
> even after a demo physician confirms the workflow decision.

[简体中文](docs/i18n/README.zh-CN.md) · [繁體中文](docs/i18n/README.zh-TW.md) ·
[日本語](docs/i18n/README.ja.md) · [한국어](docs/i18n/README.ko.md) ·
[Español](docs/i18n/README.es.md)

## What it does

A small Python workflow laboratory: a deterministic agent gathers a fictional patient's
summary, labs, allergies and medications, drafts the fixture's proposal, and produces a
safety card. An unauthenticated **demo physician role** can confirm or reject a decision.
This demonstrates engineering methods for tool orchestration, persistence, idempotency,
safety gates and reproducible evaluation. It does not choose a diagnosis or treatment.

P0 ships **10 synthetic fixtures** and **4 self-authored rules** in a **Demo Rule Pack**.
The short rules and arbitrary dose bounds are demonstration logic, not clinical guidelines.
Resources are simplified FHIR-style JSON, not full FHIR or an interoperable EHR.

## Quick start

Python **3.11+**; run commands from this checkout. No keys, external models or paid services.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m clinic_agent_lab.demo --serve
```

Open <http://127.0.0.1:8000>. The demo performs the script below and leaves its local
server running. Ctrl-C after the success summary stops it with exit code 0. The default
database is `.demo/demo.db`; reruns use unique fictional business keys and preserve history.
If port 8000 is occupied, use `--port 8001` or `--port 0` and read the printed address.

For an unattended demo that checks the management pages over real HTTP and then exits:

```bash
python -m clinic_agent_lab.demo
```

It prints the management address and a command to reopen the saved cases; its server stops
after the checks. A standalone empty local API/management server can also be started with:

```bash
python -m uvicorn clinic_agent_lab.api:app --host 127.0.0.1 --port 8000
```

That server uses `.demo/clinic.db`. To reopen the demo history, set
`CLINIC_DB_PATH=.demo/demo.db` before the same server command. `.env.example` lists
configuration examples; the app reads environment variables and does not auto-load `.env`.
Default `CLINIC_CASE_TTL_SECONDS=300`; expiry is checked on access, without a background worker.

## Demo steps and API

1. Normal proposal enters `awaiting_physician`; demo physician confirms; timeline ends `confirmed`.
2. Penicillin-class allergy produces `block`; confirmation returns HTTP 409; rejection remains possible.
3. Missing required lab produces `warn`; demonstrate both confirmation and rejection.
4. Replay one `clientCaseId`; the original case and one draft are returned.
5. A short-TTL case becomes `expired`; a late confirmation returns HTTP 409.
6. Inspect list/detail pages, safety cards and persisted tool/state/decision event timelines.

With the standalone server running, the minimal [API example](examples/api_demo.py) matches:

```bash
python examples/api_demo.py
```

API: `GET /api/fixtures`, `POST /api/cases`, `GET /api/cases`,
`GET /api/cases/{id}`, `POST /api/cases/{id}/decision`.
Create accepts only `clientCaseId` and a bundled `fixture_id`, never patient-record uploads.
Decisions accept `action` (`confirm`/`reject`), `role`, `actor`, optional `reason` (fictional only).
Role `physician` is required for both actions; `observer` is refused with HTTP 403.
There is **no authentication** or verified medical identity. Bind to loopback only.

## State machine and safety semantics

```text
accepted → gathering → drafted → awaiting_physician → confirmed | rejected | expired | failed
```

Any nonterminal state can become `expired` or `failed`. Terminal states cannot be reopened.
The fixed tools are `get_patient_summary`, `get_labs`, `get_allergies`, `get_medications`,
`draft_order`. State transitions and tool outputs are persisted in SQLite (`cases`, `events`,
`drafts`). The business key `clientCaseId` is unique; reuse with another fixture returns 409.

Card levels: `clear`, `caution`, `warn`, `block`; `block` takes precedence over `warn`.
`caution` is reserved; no P0 rule emits it. A clear card means no demo-rule hits, not evidence
of clinical safety. Each card contains rule IDs, missing data, conflicts, explanation and draft.
Block confirmation is refused without changing `awaiting_physician`; it can still be rejected
or expire. Other levels permit a demo physician decision. **No level executes an order.**

## Evaluation

```bash
ruff check .
pytest
python -m clinic_agent_lab.evaluate --output .demo/evaluation.json
python scripts/check_docs.py
```

Tests lock the labeled allergy/dose block fixtures, blocked-confirm refusal, warning-only
behavior and both decisions, idempotency under replay/concurrency, expiry, non-execution,
determinism and documentation consistency. Evaluation reports only actual fixture-level rule
hits and workflow checks. It makes no diagnostic accuracy, clinician-agreement, or latency
claims. See the actual HKT-dated [results and method](docs/evaluation.md).

## Local container

```bash
docker build -t clinic-agent-lab:local .
docker run --rm -p 127.0.0.1:8000:8000 clinic-agent-lab:local
```

This runs the local API/pages, not the scripted demo. Container data is ephemeral unless
you mount a local directory at `/app/data`. This is a convenience image, not production deployment.

## Shipped

P0: Python/FastAPI/Pydantic v2, SQLite state machine, deterministic tools, 10 synthetic
fixtures, 4 demo rules, safety cards, physician gates, HTML management, real-HTTP demo,
fixture evaluation, tests, lint, CI workflow file, local Dockerfile and six-language docs.
This implementation was validated locally; a CI workflow file alone does not establish
hosted CI status or a published release.

## Planned

P1/T8 is outside this release: optional LLM wording-only rewriting (cannot change rule
decisions), licensed Synthea import, and a tiny synthetic-feature classifier baseline.
None is implemented. There is no clinical model training, hospital integration or execution adapter.

## Experience boundary and disclaimer

The author primarily uses TypeScript/Node for backend work. Python experience includes Django,
FastAPI, py-agents and personal projects; Python is not the author's daily primary stack.
The author has no clinical-data training experience, hospital-system integration experience,
licensed medical background, or experience co-developing clinical systems with physicians.
This laboratory demonstrates workflow agents, safety gates and reproducible evaluation;
it does not establish clinical expertise or readiness for clinical use.

Use only the bundled fictional fixtures. Do not use outputs for real care, prescribing,
diagnosis or operational decisions. Confirmation records a local demo decision only.

## Documentation, contribution and license

[Architecture](docs/architecture.md) · [Rules and cards](docs/rules-and-safety.md) ·
[Data and license](docs/data-and-license.md) · [Security](SECURITY.md) ·
[Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

Code, original fixtures and documentation: [Apache-2.0](LICENSE), with [NOTICE](NOTICE).
Contact: wpkreg@gmail.com · GitHub: [imwyvern](https://github.com/imwyvern).

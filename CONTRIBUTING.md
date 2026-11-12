# Contributing

Use Python 3.11+, a local virtual environment, and `python -m pip install -e '.[dev]'`.
Run `ruff check .`, `pytest`, `python -m clinic_agent_lab.demo`,
`python -m clinic_agent_lab.evaluate --output .demo/evaluation.json`, and
`python scripts/check_docs.py` before proposing a change. Tests keep temporary artifacts
inside `.pytest_tmp/`; local services and evaluation use `.demo/`. Do not commit either.

Fixtures belong in `fixtures/synthetic/`, one `syn-NNN.json` per fictional patient.
Each must explicitly contain boolean `synthetic: true`, `license: "Apache-2.0"`, and the
standard SYNTHETIC fictional-record note. Use obvious labels such as `Pat syn-011`.
No real data, institution names, internal IDs, drug brands or external datasets. Give
each fixture an independently chosen scenario and `expected_level`, with tests that check
both its rule evidence and workflow behavior. Never derive expected labels from the rules.

New demo rules need stable rule IDs, pure deterministic implementation, tests for hits,
non-hits and boundaries, and an update to `docs/rules-and-safety.md`. Mark invented bounds
as demo-only; do not imply a medical society or guideline source. Preserve block precedence,
physician-role checks and non-execution. No new order status may become active/executed.

Synchronize counts, states, commands, version, license and disclaimers across the English
README and all five translations. Run `python scripts/update_evaluation.py` to refresh
the actual HKT-dated report after behavior changes; do not type invented result numbers.
Keep planned work separate from shipped functionality. Do not add secrets or contact details
other than wpkreg@gmail.com and GitHub imwyvern. Contributions use Apache-2.0.

# 0.1.0 local validation record

Validation date: 2026-11-12 HKT. This records local work, not a hosted release.

- [x] T0–T7 implemented and accepted in order; task evidence is in the parent PROGRESS.md.
- [x] 10 synthetic fixtures, four self-authored rules and all §6 workflow/safety gates tested.
- [x] Six READMEs, quality files, example, local container and CI workflow file present.
- [x] Documentation checker verifies state machine, exact counts/commands, license and boundaries.
- [x] Actual HKT-dated evaluation JSON/table agree with a fresh automated run.
- [x] Python 3.14.6 suite: 90 passed; Python 3.11.15 built-wheel suite: 90 passed.
- [x] Wheel installed and demo/evaluation ran outside the source checkout, exit 0.
- [x] One-command real-HTTP demo and minimal API example passed, with proposals still draft.
- [x] Docker image built locally; API/create/confirm/HTML/license smoke check passed.

The current dependency stack emits one upstream Starlette TestClient deprecation warning
about httpx during tests; it does not fail checks. It has not been hidden or presented as
a project result. The CUA browser host was unavailable, so no visual browser QA is claimed;
HTML forms, escaping, cards and timelines are covered by automated and real-HTTP checks.

During final inspection, local git history/configuration showed an externally inserted
`e79e2d2` snapshot commit and an `origin` remote. The implementation tool run did not create
a remote or invoke push. External history/configuration was preserved; remote publication
and hosted CI status were not inspected or asserted. No package/registry publication or
third-party contact was performed by this implementation run.

Limitations remain those in README and SECURITY: synthetic-only, no diagnosis or clinical
model, no execution adapter, unauthenticated demo roles, lazy expiry and local SQLite.

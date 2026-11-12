"""Reproducible fixture-only checks. These are rule/workflow hits, not model metrics."""

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

from clinic_agent_lab import __version__
from clinic_agent_lab.data import load_fixtures
from clinic_agent_lab.models import PhysicianDecision
from clinic_agent_lab.rules import RULE_IDS, evaluate_rules
from clinic_agent_lab.service import AgentService
from clinic_agent_lab.store import Store, WorkflowError


def run_evaluation(work_dir: Path | None = None) -> dict:
    fixtures = load_fixtures()
    results = {}

    def record(name, success):
        metric = results.setdefault(name, {"passed": 0, "total": 0})
        metric["total"] += 1
        metric["passed"] += int(bool(success))

    def physician(action):
        return PhysicianDecision(action=action, role="physician", actor="evaluation-physician")

    work_dir = work_dir or Path(".demo")
    work_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="evaluation-", dir=work_dir) as directory:
        clock_value = datetime(2026, 1, 1, tzinfo=UTC)
        service = AgentService(Store(Path(directory) / "evaluation.db"),
                               ttl_seconds=10, clock=lambda: clock_value)
        for fixture in fixtures.values():
            card = evaluate_rules(fixture)
            record("deterministic_rules", card == evaluate_rules(fixture))
            detail = service.submit(f"eval-{fixture.id}", fixture.id)
            case_id = detail["case"]["id"]
            if fixture.expected_level == "block":
                record("fixture_block_hits", card.level == "block")
                try:
                    service.decide(case_id, physician("confirm"))
                except WorkflowError:
                    record("block_confirmation_refusal",
                           service.get(case_id)["case"]["status"] == "awaiting_physician")
                else:
                    record("block_confirmation_refusal", False)
            if fixture.scenario.startswith("missing_labs"):
                record("missing_lab_warn", card.level == "warn")
                for action, terminal in [("confirm", "confirmed"), ("reject", "rejected")]:
                    warning = service.submit(f"warn-{fixture.id}-{action}", fixture.id)
                    result = service.decide(warning["case"]["id"], physician(action))
                    record("warn_decisions", result["case"]["status"] == terminal)
            action = "reject" if fixture.expected_level == "block" else "confirm"
            final = service.decide(case_id, physician(action))
            replay = service.submit(f"eval-{fixture.id}", fixture.id)
            record("idempotency", replay == final and replay["draft_count"] == 1)
            record("draft_only", detail["draft"]["status"] == final["draft"]["status"] == "draft"
                   and detail["draft"] == final["draft"])
        expiring = service.submit("expiry-check", "syn-005")
        clock_value += timedelta(seconds=10)
        try:
            service.decide(expiring["case"]["id"], physician("confirm"))
        except WorkflowError:
            record("expiry_refusal", service.get(expiring["case"]["id"])["case"]["status"]
                   == "expired")
        else:
            record("expiry_refusal", False)
    return {
        "version": __version__, "fixture_count": len(fixtures), "rule_count": len(RULE_IDS),
        "generated_at_hkt": datetime.now(ZoneInfo("Asia/Hong_Kong")).isoformat(),
        "scope": "SYNTHETIC fixture rule hits and workflow checks only; not model accuracy.",
        "results": results,
        "all_passed": all(m["passed"] == m["total"] for m in results.values()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Also save the actual JSON report")
    args = parser.parse_args()
    report = run_evaluation()
    rendered = json.dumps(report, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

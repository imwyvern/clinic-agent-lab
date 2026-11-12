import json
from pathlib import Path

from clinic_agent_lab.doccheck import check_docs, check_readme
from clinic_agent_lab.evaluate import run_evaluation

ROOT = Path(__file__).resolve().parents[1]


def test_all_documentation_gates():
    assert check_docs(ROOT) == []
    required = [
        "LICENSE", "NOTICE", "SECURITY.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md",
        "CHANGELOG.md", "docs/architecture.md", "docs/rules-and-safety.md",
        "docs/data-and-license.md", "docs/evaluation.md", "examples/api_demo.py",
        ".github/workflows/ci.yml", "Dockerfile", ".env.example", "pyproject.toml",
    ]
    assert all((ROOT / path).is_file() for path in required)
    license_text = (ROOT / "LICENSE").read_text()
    assert len(license_text) > 10000
    assert "END OF TERMS AND CONDITIONS" in license_text
    assert "APPENDIX" in license_text
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    assert "ruff check ." in workflow and "pytest" in workflow


def test_checker_rejects_missing_boundary_state_count_or_command():
    text = (ROOT / "README.md").read_text()
    assert check_readme(text, "en", 10, 4) == []
    for token in ["not a medical device", "awaiting_physician", "ruff check ."]:
        assert check_readme(text.replace(token, "REMOVED"), "en", 10, 4)
    assert check_readme(text, "en", 999, 4)
    assert check_readme(text, "en", 10, 999)
    assert check_readme(text.replace("10 synthetic fixtures", "11 synthetic fixtures", 1),
                        "en", 10, 4)


def test_committed_evaluation_is_from_reproducible_actual_checks(tmp_path):
    recorded = json.loads((ROOT / "docs/evaluation-results.json").read_text())
    fresh = run_evaluation(tmp_path)
    assert recorded["results"] == fresh["results"]
    assert recorded["fixture_count"] == fresh["fixture_count"]
    assert recorded["rule_count"] == fresh["rule_count"]
    assert recorded["all_passed"] is True
    assert "+08:00" in recorded["generated_at_hkt"]
    report = (ROOT / "docs/evaluation.md").read_text()
    assert recorded["generated_at_hkt"] in report
    for name, metric in recorded["results"].items():
        assert f"| {name} | {metric['passed']} | {metric['total']} |" in report

from clinic_agent_lab.demo import run_demo
from clinic_agent_lab.evaluate import run_evaluation


def test_actual_fixture_evaluation_is_complete_and_repeatable(tmp_path):
    first, second = run_evaluation(tmp_path), run_evaluation(tmp_path)
    assert first["all_passed"] and second["all_passed"]
    assert first["results"] == second["results"]
    assert first["fixture_count"] == 10 and first["rule_count"] == 4
    assert set(first["results"]) == {
        "deterministic_rules", "fixture_block_hits", "block_confirmation_refusal",
        "missing_lab_warn", "warn_decisions", "idempotency", "draft_only", "expiry_refusal",
    }
    assert first["results"]["fixture_block_hits"] == {"passed": 3, "total": 3}


def test_demo_runs_real_http_script_and_stops_server(tmp_path, capsys):
    report = run_demo(tmp_path / "demo.db", port=0)
    assert report["all_passed"]
    output = capsys.readouterr().out
    assert "SYNTHETIC demo passed" in output
    assert "Management page: http://127.0.0.1:" in output
    assert "fixture_block_hits: 3/3" in output

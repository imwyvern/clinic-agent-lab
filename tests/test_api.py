from fastapi.testclient import TestClient

from clinic_agent_lab.api import create_app


def test_api_normal_idempotency_and_nonexecution(tmp_path):
    with TestClient(create_app(tmp_path / "api.db")) as client:
        payload = {"clientCaseId": "api-normal", "fixture_id": "syn-001"}
        response = client.post("/api/cases", json=payload)
        assert response.status_code == 201
        detail = response.json()
        case_id = detail["case"]["id"]
        assert client.post("/api/cases", json=payload).json() == detail
        assert client.get(f"/api/cases/{case_id}").json() == detail
        assert len(client.get("/api/cases").json()) == 1
        assert len(client.get("/api/fixtures").json()) == 10
        decision = {"action": "confirm", "role": "physician", "actor": "demo"}
        confirmed = client.post(f"/api/cases/{case_id}/decision", json=decision)
        assert confirmed.json()["case"]["status"] == "confirmed"
        assert confirmed.json()["draft"]["status"] == "draft"
        assert client.post(f"/api/cases/{case_id}/decision", json=decision).status_code == 409
        payload["fixture_id"] = "syn-002"
        assert client.post("/api/cases", json=payload).status_code == 409


def test_block_api_and_usable_html_forms(tmp_path):
    with TestClient(create_app(tmp_path / "api.db")) as client:
        result = client.post("/cases", data={"clientCaseId": "html-block", "fixture_id": "syn-008"})
        assert result.status_code == 200
        assert "Safety card: block" in result.text
        assert 'value="confirm" disabled' in result.text
        assert "Event timeline" in result.text and "get_patient_summary" in result.text
        case_id = client.get("/api/cases").json()[0]["id"]
        decision = {"action": "confirm", "role": "physician", "actor": "demo"}
        assert client.post(f"/api/cases/{case_id}/decision", json=decision).status_code == 409
        decision["action"] = "reject"
        decision["reason"] = "<script>synthetic</script>"
        rejected = client.post(f"/cases/{case_id}/decision", data=decision)
        assert rejected.status_code == 200 and "rejected" in rejected.text
        assert "<script>synthetic</script>" not in rejected.text
        assert "&lt;script&gt;synthetic&lt;/script&gt;" in rejected.text
        for response in [client.get("/"), result, rejected]:
            assert response.text.count("Not a medical device") >= 2
            assert "SYNTHETIC" in response.text and "No orders are executed" in response.text
            assert response.headers["content-security-policy"]


def test_api_rejects_unknown_fixture_upload_and_wrong_role(tmp_path):
    with TestClient(create_app(tmp_path / "api.db")) as client:
        payload = {"clientCaseId": "invalid", "fixture_id": "syn-999"}
        assert client.post("/api/cases", json=payload).status_code == 422
        payload.update(fixture_id="syn-001", record={"name": "unsupported input"})
        response = client.post("/api/cases", json=payload)
        assert response.status_code == 422
        assert "unsupported input" not in response.text
        assert client.get("/api/cases").json() == []
        assert client.get("/api/cases/unknown").status_code == 404
        del payload["record"]
        detail = client.post("/api/cases", json=payload).json()
        response = client.post(f'/api/cases/{detail["case"]["id"]}/decision', json={
            "action": "reject", "role": "observer", "actor": "observer",
        })
        assert response.status_code == 403


def test_html_normal_confirmation(tmp_path):
    with TestClient(create_app(tmp_path / "api.db")) as client:
        result = client.post("/cases", data={"clientCaseId": "html-clear", "fixture_id": "syn-001"})
        result = client.post(result.url.path + "/decision", data={
            "action": "confirm", "role": "physician", "actor": "demo", "reason": "Demo only",
        })
        assert result.status_code == 200 and "confirmed" in result.text
        assert "&quot;status&quot;: &quot;draft&quot;" in result.text

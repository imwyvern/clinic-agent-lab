"""Minimal standard-library API example. Start the local server first; fictional data only."""

import json
from urllib.request import Request, urlopen
from uuid import uuid4


def main():
    base = "http://127.0.0.1:8000"

    def post(path, payload):
        req = Request(base + path, data=json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=10) as response:
            return json.load(response)

    detail = post("/api/cases", {"clientCaseId": f"example-{uuid4().hex[:8]}",
                                 "fixture_id": "syn-001"})
    print("SYNTHETIC only. Not a medical device. No orders are executed.")
    print("Created:", detail["case"]["status"], detail["safety_card"]["level"])
    final = post(f'/api/cases/{detail["case"]["id"]}/decision', {
        "action": "confirm", "role": "physician", "actor": "example-physician",
        "reason": "Fictional example review",
    })
    if final["case"]["status"] != "confirmed" or final["draft"]["status"] != "draft":
        raise RuntimeError("Unexpected workflow or non-draft order")
    print("Decision:", final["case"]["status"], "MedicationRequest:", final["draft"]["status"])


if __name__ == "__main__":
    main()

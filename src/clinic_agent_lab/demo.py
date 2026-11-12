"""One-command synthetic HTTP demo; --serve keeps the management page available."""

import argparse
import json
import socket
import threading
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

import uvicorn

from clinic_agent_lab.api import create_app
from clinic_agent_lab.evaluate import run_evaluation
from clinic_agent_lab.service import AgentService
from clinic_agent_lab.store import Store


def require(condition, message):
    if not condition:
        raise RuntimeError(f"Demo check failed: {message}")


def run_demo(db_path: Path, port: int = 8000, keep_serving: bool = False) -> dict:
    store = Store(db_path)
    app = create_app(service=AgentService(store))
    sock = socket.socket()
    sock.bind(("127.0.0.1", port))
    port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    checks_complete = False

    def request(path, data=None):
        req = Request(base + path, data=json.dumps(data).encode() if data is not None else None,
                      headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=5) as response:
                raw = response.read().decode()
                return response.status, json.loads(raw) if path.startswith("/api/") else raw
        except HTTPError as exc:
            return exc.code, json.loads(exc.read())

    try:
        deadline = time.monotonic() + 10
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError("Local demo server did not start")
            time.sleep(0.01)
        prefix = "demo-" + uuid4().hex[:8]

        def create(label, fixture_id):
            status, detail = request("/api/cases", {"clientCaseId": f"{prefix}-{label}",
                                                    "fixture_id": fixture_id})
            require(status == 201, "create case")
            return detail

        def decide(detail, action):
            return request(f'/api/cases/{detail["case"]["id"]}/decision', {
                "action": action, "role": "physician", "actor": "demo-physician",
                "reason": "Synthetic demo review only",
            })

        normal = create("normal", "syn-001")
        require(normal["case"]["status"] == "awaiting_physician", "normal awaits review")
        status, final = decide(normal, "confirm")
        require(status == 200 and final["case"]["status"] == "confirmed", "normal confirmation")
        blocked = create("allergy", "syn-002")
        require(blocked["safety_card"]["level"] == "block", "allergy block")
        require(decide(blocked, "confirm")[0] == 409, "block confirmation refused")
        require(decide(blocked, "reject")[1]["case"]["status"] == "rejected", "block rejection")
        for action, fixture_id in [("confirm", "syn-003"), ("reject", "syn-010")]:
            warning = create(f"warn-{action}", fixture_id)
            require(warning["safety_card"]["level"] == "warn", "missing-lab warning")
            expected = "confirmed" if action == "confirm" else "rejected"
            require(decide(warning, action)[1]["case"]["status"] == expected, "warning decision")
        replay = create("replay", "syn-006")
        require(create("replay", "syn-006") == replay and replay["draft_count"] == 1,
                "idempotent single draft")
        # Same persisted store, very short TTL only for the expiration demonstration.
        expiring = AgentService(store, ttl_seconds=0.02).submit(f"{prefix}-expiry", "syn-005")
        time.sleep(0.03)
        require(decide(expiring, "confirm")[0] == 409, "late confirmation refused")
        require(request(f'/api/cases/{expiring["case"]["id"]}')[1]["case"]["status"] == "expired",
                "expiration persisted")
        for detail in [normal, blocked, replay, expiring]:
            status, html = request(f'/cases/{detail["case"]["id"]}')
            require(status == 200 and "Safety card" in html and "Event timeline" in html,
                    "management cards and timeline")
        require(request("/")[0] == 200, "management list")
        report = run_evaluation(db_path.parent)
        require(report["all_passed"], "fixture evaluation")
        checks_complete = True
        print("SYNTHETIC demo passed: normal, allergy block/refusal/reject, warn confirm/reject, "
              "idempotency, expiry, management pages.")
        print(f"Management page: {base}")
        print(f"Saved cases: {db_path}")
        for name, metric in report["results"].items():
            print(f"{name}: {metric['passed']}/{metric['total']} (fixture-only checks)")
        if keep_serving:
            print("Local management server running; Ctrl-C stops it with exit code 0.", flush=True)
            while thread.is_alive():
                time.sleep(0.2)
        else:
            print("Server stops after checks. To inspect saved cases:")
            print(f"CLINIC_DB_PATH={db_path} python -m uvicorn clinic_agent_lab.api:app "
                  f"--host 127.0.0.1 --port {port}")
        return report
    except KeyboardInterrupt:
        if not checks_complete:
            raise RuntimeError("Demo interrupted before checks completed") from None
        return report
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(".demo/demo.db"))
    parser.add_argument("--port", type=int, default=8000, help="Local port; 0 picks a free port")
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()
    try:
        run_demo(args.db, args.port, args.serve)
    except (OSError, RuntimeError, URLError) as exc:
        print(f"Demo failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

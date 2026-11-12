"""Local-only API and server-rendered management pages for SYNTHETIC fixtures."""

import json
import os
from contextlib import asynccontextmanager
from html import escape
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import Field, ValidationError

from clinic_agent_lab import __version__
from clinic_agent_lab.data import load_fixtures
from clinic_agent_lab.models import Model, PhysicianDecision
from clinic_agent_lab.service import AgentService
from clinic_agent_lab.store import Store, WorkflowError

BOUNDARY = (
    "SYNTHETIC data only. Not a medical device. No diagnosis or clinical model training. "
    "No orders are executed. Not a production system. Demo roles are not authenticated. "
    "Do not enter real patient data."
)


class CreateCase(Model):
    clientCaseId: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_-]+$")
    fixture_id: str = Field(pattern=r"^syn-\d{3}$")


def page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{escape(title)} · clinic-agent-lab</title>"
        "<style>body{font:16px system-ui;max-width:1000px;margin:2rem auto;padding:0 1rem;"
        "line-height:1.5;color:#16222a;background:#fafafa}a{color:#145b8b}"
        "table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:.6rem;"
        "border-bottom:1px solid #bbb}.boundary,.card{padding:1rem;border:2px solid #526775;"
        "margin:1rem 0;background:white}.block{border-color:#a02020}"
        "pre{white-space:pre-wrap;overflow-wrap:anywhere}input,select,button{font:inherit;"
        "padding:.4rem;margin:.3rem}label{display:block}button:disabled{opacity:.5}</style>"
        '<header><a href="/">clinic-agent-lab 0.1.0</a>'
        f'<p class="boundary">{escape(BOUNDARY)}</p></header><main>'
        f"<h1>{escape(title)}</h1>{body}</main><footer><p>{escape(BOUNDARY)}</p>"
        "<p>Demo Rule Pack: self-authored, not clinical guidelines. Apache-2.0.</p>"
        "</footer></html>"
    )


def render_detail(detail: dict) -> HTMLResponse:
    case, card = detail["case"], detail["safety_card"]
    body = f'<p>Business key: {escape(case["clientCaseId"])}</p>'
    body += f'<p>State: <strong>{escape(case["status"])}</strong></p>'
    body += f'<p>Fixture: {escape(case["fixture_id"])} · expires {escape(case["expires_at"])}</p>'
    if card:
        body += f'<section class="card {escape(card["level"])}"><h2>Safety card: '
        body += f'{escape(card["level"])}</h2><p>{escape(card["disclaimer"])}</p>'
        body += f'<pre>{escape(json.dumps(card, indent=2))}</pre></section>'
    if case["status"] == "awaiting_physician":
        disabled = " disabled" if card and card["level"] == "block" else ""
        body += (
            f'<form method="post" action="/cases/{case["id"]}/decision">'
            '<h2>Demo physician review</h2><label>Role <select name="role">'
            '<option>physician</option><option>observer</option></select></label>'
            '<label>Demo actor <input name="actor" value="demo-physician" '
            'maxlength="80" required></label><label>Reason (synthetic only) '
            '<input name="reason" maxlength="500"></label>'
            f'<button name="action" value="confirm"{disabled}>Confirm decision only</button>'
            '<button name="action" value="reject">Reject</button></form>'
        )
    body += '<h2>Event timeline</h2><ol>'
    for event in detail["events"]:
        body += f'<li><strong>{escape(event["kind"])}</strong> {escape(event["timestamp"])}'
        body += f'<pre>{escape(json.dumps(event["payload"], indent=2))}</pre></li>'
    return page("Case detail", body + "</ol>")


def create_app(db_path: str | Path | None = None, ttl_seconds: float | None = None,
               service: AgentService | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        app.state.service = service or AgentService(
            Store(db_path or os.getenv("CLINIC_DB_PATH", ".demo/clinic.db")),
            ttl_seconds=ttl_seconds if ttl_seconds is not None else
            float(os.getenv("CLINIC_CASE_TTL_SECONDS", "300")),
        )
        yield

    app = FastAPI(title="clinic-agent-lab (SYNTHETIC only)", version=__version__,
                  lifespan=lifespan)

    @app.middleware("http")
    async def headers(request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
            "frame-ancestors 'none'; base-uri 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(WorkflowError)
    async def workflow_error(request, exc):
        if request.url.path.startswith("/api/"):
            return JSONResponse({"detail": str(exc)}, status_code=exc.status_code)
        response = page("Request refused", f"<p>{escape(str(exc))}</p>")
        response.status_code = exc.status_code
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        # Do not echo submitted fields, which could accidentally contain real data.
        return JSONResponse({"detail": "Invalid synthetic-only request"}, status_code=422)

    @app.get("/api/fixtures")
    def fixtures():
        return [{"id": f.id, "scenario": f.scenario, "synthetic": True}
                for f in load_fixtures().values()]

    @app.post("/api/cases", status_code=201)
    def create_case(payload: CreateCase, request: Request):
        return request.app.state.service.submit(payload.clientCaseId, payload.fixture_id)

    @app.get("/api/cases")
    def list_cases(request: Request):
        return request.app.state.service.list_cases()

    @app.get("/api/cases/{case_id}")
    def get_case(case_id: str, request: Request):
        return request.app.state.service.get(case_id)

    @app.post("/api/cases/{case_id}/decision")
    def decide(case_id: str, payload: PhysicianDecision, request: Request):
        return request.app.state.service.decide(case_id, payload)

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        options = "".join(f'<option value="{f.id}">{f.id}: {escape(f.scenario)}</option>'
                          for f in load_fixtures().values())
        body = (
            '<form method="post" action="/cases"><label>Business key (fictional only) '
            '<input name="clientCaseId" pattern="[A-Za-z0-9_-]+" maxlength="120" required>'
            '</label><label>Synthetic fixture <select name="fixture_id">'
            f'{options}</select></label><button>Create or replay</button></form>'
            '<table><thead><tr><th>Business key</th><th>Fixture</th><th>State</th></tr></thead>'
            '<tbody>'
        )
        for case in request.app.state.service.list_cases():
            body += f'<tr><td><a href="/cases/{case["id"]}">{escape(case["clientCaseId"])}</a>'
            body += f'</td><td>{escape(case["fixture_id"])}</td>'
            body += f'<td>{escape(case["status"])}</td></tr>'
        return page("Synthetic case management", body + "</tbody></table>")

    async def form(request: Request) -> dict:
        if len(raw := await request.body()) > 4096:
            raise WorkflowError("Demo form too large", 413)
        try:
            values = parse_qs(raw.decode("utf-8"), keep_blank_values=True)
        except UnicodeDecodeError as exc:
            raise WorkflowError("Invalid demo form", 422) from exc
        if any(len(value) != 1 for value in values.values()):
            raise WorkflowError("Duplicate form fields", 422)
        return {key: value[0] for key, value in values.items()}

    @app.post("/cases")
    async def create_form(request: Request):
        try:
            payload = CreateCase.model_validate(await form(request))
        except ValidationError as exc:
            raise WorkflowError("Invalid synthetic-only form", 422) from exc
        detail = request.app.state.service.submit(payload.clientCaseId, payload.fixture_id)
        return RedirectResponse(f'/cases/{detail["case"]["id"]}', status_code=303)

    @app.get("/cases/{case_id}", response_class=HTMLResponse)
    def detail_page(case_id: str, request: Request):
        return render_detail(request.app.state.service.get(case_id))

    @app.post("/cases/{case_id}/decision")
    async def decision_form(case_id: str, request: Request):
        try:
            decision = PhysicianDecision.model_validate(await form(request))
        except ValidationError as exc:
            raise WorkflowError("Invalid synthetic-only form", 422) from exc
        request.app.state.service.decide(case_id, decision)
        return RedirectResponse(f"/cases/{case_id}", status_code=303)

    return app


app = create_app()

"""Check the six README fact sets against the installed code and source fixtures."""

import re
from pathlib import Path

from clinic_agent_lab import __version__
from clinic_agent_lab.data import load_fixtures
from clinic_agent_lab.models import State
from clinic_agent_lab.rules import RULE_IDS

LANGUAGES = ("zh-CN", "zh-TW", "ja", "ko", "es")
REQUIRED_COMMANDS = (
    "python3 -m venv .venv",
    "source .venv/bin/activate",
    "python -m pip install -e '.[dev]'",
    "python -m clinic_agent_lab.demo --serve",
    "python -m clinic_agent_lab.demo",
    "python -m uvicorn clinic_agent_lab.api:app --host 127.0.0.1 --port 8000",
    "python examples/api_demo.py",
    "ruff check .",
    "pytest",
    "python -m clinic_agent_lab.evaluate --output .demo/evaluation.json",
    "python scripts/check_docs.py",
    "docker build -t clinic-agent-lab:local .",
    "docker run --rm -p 127.0.0.1:8000:8000 clinic-agent-lab:local",
)
# Translations keep a canonical English boundary alongside local-language explanation.
BOUNDARIES = {
    "en": ("SYNTHETIC data only", "no clinical model training", "no auto-executed orders",
           "not a production system"),
    "zh-CN": ("合成", "训练", "生产"),
    "zh-TW": ("合成", "訓練", "正式"),
    "ja": ("合成", "学習", "本番"),
    "ko": ("합성", "학습", "운영 환경"),
    "es": ("sintéticos", "entrenamiento", "producción"),
}
COUNT_PATTERNS = {
    "en": (r"(\d+)\s+synthetic fixtures", r"(\d+)\s+(?:self-authored|demo) rules"),
    "zh-CN": (r"(\d+)\s*份合成夹具", r"(\d+)\s*条(?:自行编写的|演示)规则"),
    "zh-TW": (r"(\d+)\s*份合成測試資料", r"(\d+)\s*條(?:自行編寫的|示範)規則"),
    "ja": (r"(\d+)\s*件の合成フィクスチャ", r"(\d+)\s*件の(?:独自|デモ)ルール"),
    "ko": (r"합성 픽스처\s*(\d+)개", r"규칙\s*(\d+)개"),
    "es": (r"(\d+)\s+casos de prueba sintéticos", r"(\d+)\s+reglas"),
}


def check_readme(text: str, language: str, fixture_count: int, rule_count: int) -> list[str]:
    errors = []
    required = [
        "SYNTHETIC", "Apache-2.0", "not a medical device", __version__, "3.11+",
        "Demo Rule Pack", "MedicationRequest", "clientCaseId", "physician", "observer",
        "CLINIC_DB_PATH=.demo/demo.db", "CLINIC_CASE_TTL_SECONDS=300",
        "get_patient_summary", "get_labs", "get_allergies", "get_medications", "draft_order",
        "TypeScript/Node", "Django", "FastAPI", "py-agents", "wpkreg@gmail.com", "imwyvern",
        *[state.value for state in State], *REQUIRED_COMMANDS, *BOUNDARIES[language],
    ]
    compact = " ".join(text.split()).lower()
    for fact in required:
        if " ".join(fact.split()).lower() not in compact:
            errors.append(f"{language}: missing fact/command {fact!r}")
    prose = " ".join(re.sub(r"```.*?```|https?://\S+|\*", "", text, flags=re.S).split())
    for pattern, label, count in zip(COUNT_PATTERNS[language], ["fixture", "rule"],
                                     [fixture_count, rule_count], strict=True):
        counts = {int(value) for value in re.findall(pattern, prose)}
        if counts != {count}:
            errors.append(f"{language}: {label} counts {counts} differ from actual {count}")
    state_line = ("accepted → gathering → drafted → awaiting_physician → "
                  "confirmed | rejected | expired | failed")
    if state_line not in text:
        errors.append(f"{language}: state machine differs")
    if not re.search(r"^## .*Planned|^## Planned", text, re.M):
        errors.append(f"{language}: missing explicit Planned heading")
    # Optional functionality must never appear before the explicit Planned section.
    shipped_part = re.split(r"^## .*Planned|^## Planned", text, flags=re.M)[0]
    for planned in ["Synthea", "LLM", "P1/T8"]:
        if planned in shipped_part:
            errors.append(f"{language}: planned item appears in shipped content: {planned}")
    if len(text.splitlines()) < 100:
        errors.append(f"{language}: README is incomplete")
    return errors


def check_docs(root: Path) -> list[str]:
    errors = []
    fixtures = load_fixtures()
    paths = {"en": root / "README.md", **{
        lang: root / "docs" / "i18n" / f"README.{lang}.md" for lang in LANGUAGES
    }}
    for language, path in paths.items():
        if not path.is_file():
            errors.append(f"Missing {path.relative_to(root)}")
            continue
        text = path.read_text(encoding="utf-8")
        errors.extend(check_readme(text, language, len(fixtures), len(RULE_IDS)))
        for link in re.findall(r"\]\(([^)]+)\)", text):
            if ("://" not in link and not link.startswith("#")
                    and not (path.parent / link.split("#")[0]).is_file()):
                errors.append(f"{language}: broken local link {link}")
    return errors

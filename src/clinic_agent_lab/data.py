"""Read only the bundled, explicitly synthetic fixtures; there is no record upload."""

import json
from importlib.resources import files
from pathlib import Path

from clinic_agent_lab.models import Fixture


def fixture_directory():
    bundled = files("clinic_agent_lab").joinpath("fixtures/synthetic")
    if bundled.is_dir():
        return bundled
    return Path(__file__).resolve().parents[2] / "fixtures" / "synthetic"


def load_fixtures() -> dict[str, Fixture]:
    result = {}
    for path in sorted(fixture_directory().iterdir(), key=lambda path: path.name):
        if path.name.endswith(".json"):
            fixture = Fixture.model_validate(json.loads(path.read_text(encoding="utf-8")))
            if fixture.id in result or path.name != f"{fixture.id}.json":
                raise ValueError("Fixture IDs must be unique and match file names")
            result[fixture.id] = fixture
    if not result:
        raise ValueError("No synthetic fixtures found")
    return result


def get_fixture(fixture_id: str) -> Fixture:
    try:
        return load_fixtures()[fixture_id]
    except KeyError as exc:
        raise ValueError("Unknown synthetic fixture") from exc

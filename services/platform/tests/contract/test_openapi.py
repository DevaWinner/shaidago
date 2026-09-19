import json
from pathlib import Path

import pytest

from shaidago.api.openapi import build_openapi, main, render_openapi

COMMITTED = Path(__file__).parents[4] / "contracts" / "openapi.json"


def test_generation_is_deterministic_and_needs_no_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("DATABASE_URL", "REDIS_URL", "OPENAI_API_KEY", "APP_ENV"):
        monkeypatch.delenv(name, raising=False)
    assert render_openapi() == render_openapi()


def test_schema_describes_health_routes_and_no_secret_material() -> None:
    schema = build_openapi()
    assert {"/health/live", "/health/ready"} <= set(schema["paths"])
    rendered = render_openapi()
    for forbidden in ("change-me", "postgresql", "localhost", "credential"):
        assert forbidden not in rendered


def test_committed_contract_matches_the_application() -> None:
    assert COMMITTED.read_text(encoding="utf-8") == render_openapi()
    assert json.loads(COMMITTED.read_text(encoding="utf-8"))["info"]["title"]


def test_check_mode_fails_on_drift_and_write_mode_repairs_it(tmp_path: Path) -> None:
    target = tmp_path / "openapi.json"
    assert main(["--output", str(target), "--check"]) == 1  # missing file
    assert main(["--output", str(target)]) == 0
    assert main(["--output", str(target), "--check"]) == 0
    target.write_text("{}\n", encoding="utf-8")
    assert main(["--output", str(target), "--check"]) == 1

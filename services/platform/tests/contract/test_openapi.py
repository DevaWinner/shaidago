import json
import re
import runpy
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest
from fastapi.routing import APIRoute

from shaidago.api.openapi import build_contract_app, build_openapi, main, render_openapi

COMMITTED = Path(__file__).parents[4] / "contracts" / "openapi.json"
FRONTEND_FIXTURES = Path(__file__).parents[4] / "contracts" / "frontend-fixtures.json"
FRONTEND_RENDERER = Path(__file__).parents[4] / "scripts" / "render_frontend_contract.py"


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
    for forbidden in ("change-me", "postgresql", "localhost", "openapi-schema-only", "Y2hhbmdl"):
        assert forbidden not in rendered


def test_committed_contract_matches_the_application() -> None:
    assert COMMITTED.read_text(encoding="utf-8") == render_openapi()
    assert json.loads(COMMITTED.read_text(encoding="utf-8"))["info"]["title"]


def test_every_operation_id_is_explicit_stable_and_unique() -> None:
    routes = [route for route in build_contract_app().routes if isinstance(route, APIRoute)]
    operation_ids = [route.operation_id for route in routes]
    assert all(operation_id is not None for operation_id in operation_ids)
    explicit_ids = [operation_id for operation_id in operation_ids if operation_id is not None]
    assert len(explicit_ids) == len(set(explicit_ids))
    assert all(re.fullmatch(r"[a-z][a-z0-9_]*", operation_id) for operation_id in explicit_ids)


def test_frontend_fixture_manifest_covers_every_operation_and_documented_response() -> None:
    schema = build_openapi()
    fixtures = json.loads(FRONTEND_FIXTURES.read_text(encoding="utf-8"))
    expected: dict[str, set[int]] = {}
    for path_item in schema["paths"].values():
        for method in ("get", "post", "put", "patch", "delete"):
            operation = path_item.get(method)
            if operation is not None:
                expected[operation["operationId"]] = {
                    int(status) for status in operation["responses"] if status.isdigit()
                }
    assert set(fixtures["operations"]) == set(expected)
    for operation_id, statuses in expected.items():
        examples = fixtures["operations"][operation_id]["responses"]
        assert {example["status"] for example in examples} == statuses
        assert all(example["id"] == f"{operation_id}.{example['status']}" for example in examples)
    assert set(fixtures["scenarios"]) == {
        "success",
        "empty",
        "stale",
        "partial",
        "denied",
        "rate_limited",
        "dependency_down",
        "validation",
    }


def test_frontend_fixture_manifest_has_no_generator_drift() -> None:
    renderer = runpy.run_path(str(FRONTEND_RENDERER))
    render = cast("Callable[[], str]", renderer["render"])
    assert FRONTEND_FIXTURES.read_text(encoding="utf-8") == render()


def test_check_mode_fails_on_drift_and_write_mode_repairs_it(tmp_path: Path) -> None:
    target = tmp_path / "openapi.json"
    assert main(["--output", str(target), "--check"]) == 1  # missing file
    assert main(["--output", str(target)]) == 0
    assert main(["--output", str(target), "--check"]) == 0
    target.write_text("{}\n", encoding="utf-8")
    assert main(["--output", str(target), "--check"]) == 1

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
PUBLIC_READ_OPERATIONS = {
    "health_live",
    "health_ready",
    "projects_list_localities",
    "projects_list",
    "projects_get",
    "projects_get_source",
    "projects_ask_question",
    "discovery_start_public_run",
    "discovery_get_public_run",
}
PRIVATE_FIELD_NAMES = {
    "contact",
    "contact_value",
    "description",
    "tracking_code",
    "handle",
    "passphrase",
    "session_token",
    "csrf_token",
    "object_key",
    "report_id",
    "reviewer_id",
    "reviewer_identifier",
    "internal_reason",
    "query_text",
    "question",
    "evidence_id",
    "requested_by",
    "cancel_requested",
    "attached_source_id",
    "injection_flag",
    "disposition",
}


def object_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise AssertionError("expected an OpenAPI object")
    return cast("dict[str, object]", value)


def schema_property_names(
    schema: dict[str, object], document: dict[str, object], seen: frozenset[str] = frozenset()
) -> set[str]:
    ref = schema.get("$ref")
    if isinstance(ref, str):
        if ref in seen:
            return set()
        node: object = document
        for part in ref.removeprefix("#/").split("/"):
            node = object_mapping(node)[part]
        return schema_property_names(object_mapping(node), document, seen | {ref})
    properties = object_mapping(schema.get("properties", {}))
    names = set(properties)
    for child in properties.values():
        names |= schema_property_names(object_mapping(child), document, seen)
    items = schema.get("items")
    if items is not None:
        names |= schema_property_names(object_mapping(items), document, seen)
    for union in ("oneOf", "anyOf", "allOf"):
        children = schema.get(union, [])
        if isinstance(children, list):
            for child in cast("list[object]", children):
                names |= schema_property_names(object_mapping(child), document, seen)
    return names


def test_generation_is_deterministic_and_needs_no_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("DATABASE_URL", "REDIS_URL", "GROQ_API_KEY", "APP_ENV"):
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


def test_public_read_schemas_do_not_expose_private_field_names() -> None:
    schema = object_mapping(build_openapi())
    paths = object_mapping(schema["paths"])
    reviewed: set[str] = set()
    for path_item_value in paths.values():
        path_item = object_mapping(path_item_value)
        for method in ("get", "post", "put", "patch", "delete"):
            operation = path_item.get(method)
            if operation is None:
                continue
            operation_map = object_mapping(operation)
            operation_id = operation_map.get("operationId")
            if not isinstance(operation_id, str) or operation_id not in PUBLIC_READ_OPERATIONS:
                continue
            responses = object_mapping(operation_map["responses"])
            success = next(
                object_mapping(response)
                for status, response in responses.items()
                if status.startswith("2")
            )
            content = object_mapping(success.get("content", {}))
            media = content.get("application/json")
            if media is not None:
                response_schema = object_mapping(object_mapping(media).get("schema", {}))
                assert not PRIVATE_FIELD_NAMES & schema_property_names(response_schema, schema)
            reviewed.add(operation_id)
    assert reviewed == PUBLIC_READ_OPERATIONS


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

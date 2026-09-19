#!/usr/bin/env python3
"""Render deterministic, MSW-ready response examples from the committed OpenAPI contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OPENAPI = ROOT / "contracts" / "openapi.json"
OUTPUT = ROOT / "contracts" / "frontend-fixtures.json"
HTTP_METHODS = ("get", "post", "put", "patch", "delete")
SUCCESS_STATUSES = range(200, 300)
HTTP_CLIENT_ERROR = 400
VALIDATION_STATUS = 422
RATE_LIMIT_STATUS = 429
PROBLEM_CODES = {
    400: "bad_request",
    401: "unauthenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_failed",
    429: "rate_limited",
    500: "internal_error",
    503: "dependency_unavailable",
}
SYNTHETIC_UUID = "018f0000-0000-7000-8000-000000000001"
SYNTHETIC_TIME = "2026-09-19T09:00:00Z"
_MISSING = object()


def _resolve(schema: dict[str, Any], document: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    if not isinstance(ref, str):
        return schema
    node: Any = document
    for part in ref.removeprefix("#/").split("/"):
        node = node[part]
    return node


def _direct_example(schema: dict[str, Any]) -> Any:
    examples = schema.get("examples")
    if isinstance(examples, list) and examples:
        return examples[0]
    if "example" in schema:
        return schema["example"]
    if "const" in schema:
        return schema["const"]
    enum = schema.get("enum")
    if isinstance(enum, list) and enum:
        return enum[0]
    return _MISSING


def _composed_example(
    schema: dict[str, Any], document: dict[str, Any], seen: frozenset[str]
) -> Any:
    for union in ("oneOf", "anyOf"):
        choices = schema.get(union)
        if isinstance(choices, list):
            choice = next((item for item in choices if item.get("type") != "null"), choices[0])
            return _example(choice, document, seen)
    all_of = schema.get("allOf")
    if isinstance(all_of, list):
        merged: dict[str, Any] = {}
        for part in all_of:
            value = _example(part, document, seen)
            if isinstance(value, dict):
                merged.update(value)
        return merged
    return _MISSING


def _typed_example(schema: dict[str, Any], document: dict[str, Any], seen: frozenset[str]) -> Any:
    schema_type = schema.get("type")
    if schema_type == "object" or "properties" in schema:
        properties = schema.get("properties", {})
        required = schema.get("required", list(properties))
        value: Any = {
            name: _example(properties[name], document, seen)
            for name in required
            if name in properties
        }
    elif schema_type == "array":
        count = max(0, int(schema.get("minItems", 0)))
        value = [_example(schema.get("items", {}), document, seen) for _ in range(count)]
    elif schema_type == "boolean":
        value = bool(schema.get("default", False))
    elif schema_type == "integer":
        value = int(schema.get("minimum", 0))
    elif schema_type == "number":
        value = float(schema.get("minimum", 0))
    elif schema_type == "string":
        if "default" in schema:
            value = schema["default"]
        else:
            value = {
                "date": "2026-09-19",
                "date-time": SYNTHETIC_TIME,
                "uuid": SYNTHETIC_UUID,
                "uri": "https://synthetic.example/resource",
            }.get(schema.get("format"), "synthetic-example")
    else:
        value = None
    return value


def _example(
    schema: dict[str, Any], document: dict[str, Any], seen: frozenset[str] = frozenset()
) -> Any:
    ref = schema.get("$ref")
    if isinstance(ref, str):
        return None if ref in seen else _example(_resolve(schema, document), document, seen | {ref})
    direct = _direct_example(schema)
    if direct is not _MISSING:
        return direct
    composed = _composed_example(schema, document, seen)
    if composed is not _MISSING:
        return composed
    return _typed_example(schema, document, seen)


def _problem(status: int) -> dict[str, Any]:
    code = PROBLEM_CODES.get(status, "request_failed")
    body: dict[str, Any] = {
        "type": f"https://shaidago.example/problems/{code}",
        "title": code.replace("_", " ").title(),
        "status": status,
        "code": code,
        "detail": "A safe synthetic error example.",
        "request_id": SYNTHETIC_UUID,
        "errors": None,
    }
    if status == VALIDATION_STATUS:
        body["errors"] = [{"field": "body.example", "code": "invalid"}]
    return body


def _headers(response: dict[str, Any], status: int, problem: bool) -> dict[str, str]:
    headers: dict[str, str] = {}
    for name, specification in response.get("headers", {}).items():
        headers[name] = str(_example(specification.get("schema", {}), {"components": {}}))
    if status == RATE_LIMIT_STATUS:
        headers["Retry-After"] = "30"
    if problem:
        headers.update({"Content-Type": "application/problem+json", "Cache-Control": "no-store"})
    return headers


def _response_example(
    operation_id: str,
    status_text: str,
    response: dict[str, Any],
    document: dict[str, Any],
) -> dict[str, Any]:
    status = int(status_text)
    content = response.get("content", {})
    problem_media = content.get("application/problem+json")
    json_media = content.get("application/json")
    media = problem_media or json_media
    problem = problem_media is not None or status >= HTTP_CLIENT_ERROR
    fixture: dict[str, Any] = {
        "id": f"{operation_id}.{status}",
        "status": status,
        "kind": "success" if status in SUCCESS_STATUSES else "error",
        "headers": _headers(response, status, problem),
    }
    if status not in (204, 304):
        if problem:
            fixture["body"] = _problem(status)
        elif media is not None:
            fixture["body"] = _example(media.get("schema", {}), document)
        elif content:
            fixture["body_kind"] = "binary"
    return fixture


def _msw_path(path: str) -> str:
    return re.sub(r"\{([^}:]+)(?::[^}]+)?\}", r":\1", path)


def _operations(document: dict[str, Any]) -> dict[str, Any]:
    operations: dict[str, Any] = {}
    for path, path_item in document["paths"].items():
        for method in HTTP_METHODS:
            operation = path_item.get(method)
            if operation is None:
                continue
            operation_id = operation["operationId"]
            operations[operation_id] = {
                "method": method.upper(),
                "path": path,
                "msw_path": _msw_path(path),
                "responses": [
                    _response_example(operation_id, status, response, document)
                    for status, response in sorted(operation["responses"].items())
                    if status.isdigit()
                ],
            }
    return dict(sorted(operations.items()))


def _scenarios() -> dict[str, Any]:
    partial_receipt = {
        "tracking_code": "SG-R-7M4K-P2QW-9",
        "status": "received",
        "published": False,
        "contact_saved": False,
        "attachments": [
            {"position": 1, "kept": True, "reason": None},
            {"position": 2, "kept": False, "reason": "unsupported_type"},
        ],
        "next_steps": ["save_tracking_code", "check_status_later", "see_escalation_guidance"],
    }
    return {
        "success": {
            "operation_id": "health_live",
            "status": 200,
            "headers": {"Cache-Control": "no-store"},
            "body": {"status": "live"},
        },
        "empty": {
            "operation_id": "projects_list",
            "status": 200,
            "headers": {"Cache-Control": "public, max-age=60"},
            "body": {"items": [], "next_cursor": None},
        },
        "stale": {
            "operation_id": "reviewer_decisions_transition",
            "status": 409,
            "headers": {"Content-Type": "application/problem+json", "Cache-Control": "no-store"},
            "body": {**_problem(409), "code": "report_version_conflict"},
        },
        "partial": {
            "operation_id": "reports_submit",
            "status": 201,
            "headers": {"Cache-Control": "no-store"},
            "body": partial_receipt,
        },
        "denied": {
            "operation_id": "reviewer_reports_get",
            "status": 403,
            "headers": {"Content-Type": "application/problem+json", "Cache-Control": "no-store"},
            "body": _problem(403),
        },
        "rate_limited": {
            "operation_id": "projects_ask_question",
            "status": 429,
            "headers": {
                "Content-Type": "application/problem+json",
                "Cache-Control": "no-store",
                "Retry-After": "30",
            },
            "body": _problem(429),
        },
        "dependency_down": {
            "operation_id": "projects_ask_question",
            "status": 503,
            "headers": {"Content-Type": "application/problem+json", "Cache-Control": "no-store"},
            "body": _problem(503),
        },
        "validation": {
            "operation_id": "reports_submit",
            "status": 422,
            "headers": {"Content-Type": "application/problem+json", "Cache-Control": "no-store"},
            "body": _problem(422),
        },
    }


def render() -> str:
    document = json.loads(OPENAPI.read_text(encoding="utf-8"))
    payload = {
        "_generated": "Generated by scripts/render_frontend_contract.py; do not edit by hand.",
        "schema_version": 1,
        "openapi_version": document["info"]["version"],
        "operations": _operations(document),
        "scenarios": _scenarios(),
    }
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    rendered = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            sys.stderr.write("contracts/frontend-fixtures.json is out of date\n")
            return 1
        return 0
    OUTPUT.write_text(rendered, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

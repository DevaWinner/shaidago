#!/usr/bin/env python3
"""Validate FE-001 route and journey coverage against OpenAPI."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOCUMENT = ROOT / "docs" / "FRONTEND_ROUTE_MATRIX.md"
OPENAPI = ROOT / "contracts" / "openapi.json"


class RouteMatrixError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RouteMatrixError(message)


def operation_ids(openapi: dict[str, Any]) -> set[str]:
    return {
        operation["operationId"]
        for methods in openapi["paths"].values()
        for method, operation in methods.items()
        if method in {"get", "post", "put", "patch", "delete"}
    }


def validate(text: str, openapi: dict[str, Any]) -> None:
    require("- **Task:** FE-001" in text, "FE-001 marker is missing")
    route_ids = re.findall(r"^\| (FR-\d{2}) \|", text, re.MULTILINE)
    expected_ids = {f"FR-{number:02d}" for number in range(1, 13)}
    require(set(route_ids) == expected_ids and len(route_ids) == 12, "route matrix must contain FR-01 through FR-12 exactly once")

    required_routes = {
        "/{locale}",
        "/{locale}/projects",
        "/{locale}/projects/{slug}",
        "/{locale}/projects/{slug}/sources/{sourceId}",
        "/{locale}/report/{projectSlug}",
        "/{locale}/report/complete",
        "/{locale}/track",
        "/{locale}/handle",
        "/{locale}/trust",
        "/{locale}/reviewer/sign-in",
        "/{locale}/reviewer/reports",
        "/{locale}/reviewer/reports/{reportId}",
    }
    declared_routes = set(re.findall(r"^\| FR-\d{2} \| `([^`]+)` \|", text, re.MULTILINE))
    require(declared_routes == required_routes, f"route set differs: missing={sorted(required_routes - declared_routes)}")

    known_operations = operation_ids(openapi)
    referenced = set(re.findall(r"`([a-z][a-z0-9_]+)`", text)) & known_operations
    required_operations = known_operations - {"health_live", "health_ready"}
    require(referenced == required_operations, f"operation coverage differs: missing={sorted(required_operations - referenced)}")

    journey_rows = re.findall(r"^\| ([^|]+) \| FR-", text.split("## 3. User-journey route sequences", 1)[1].split("## 4.", 1)[0], re.MULTILINE)
    require(len(journey_rows) == 7, "journey sequence table must contain seven rows")

    require(text.count("- [x]") == 6 and "- [ ]" not in text, "FE-001 exit gate must contain six checked controls")
    require("TODO" not in text and "TBD" not in text, "route matrix contains TODO/TBD")
    require("/api/proxy" not in text, "route matrix introduces a generic proxy")


def negative_self_tests(text: str, openapi: dict[str, Any]) -> None:
    mutations = {
        "missing route": text.replace("| FR-12 |", "| REMOVED-12 |", 1),
        "secret route": text.replace("`/{locale}/track`", "`/{locale}/track/{trackingCode}`", 1),
        "missing operation": text.replace("`reports_submit`", "`removed_reports_submit`"),
    }
    for name, mutation in mutations.items():
        try:
            validate(mutation, openapi)
        except RouteMatrixError:
            continue
        raise RouteMatrixError(f"negative self-test did not reject {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_DOCUMENT)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        text = args.path.read_text(encoding="utf-8")
        openapi = json.loads(OPENAPI.read_text(encoding="utf-8"))
        validate(text, openapi)
        if args.self_test:
            negative_self_tests(text, openapi)
    except (OSError, json.JSONDecodeError, RouteMatrixError) as error:
        print(f"frontend route matrix: FAIL: {error}", file=sys.stderr)
        return 1
    suffix = " with negative self-tests" if args.self_test else ""
    print(f"frontend route matrix: OK{suffix} ({args.path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

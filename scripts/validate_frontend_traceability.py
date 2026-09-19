#!/usr/bin/env python3
"""Validate FE-000 coverage against frontend tasks and OpenAPI operations."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOCUMENT = ROOT / "docs" / "FRONTEND_REQUIREMENTS_TRACEABILITY.md"
FRONTEND_ORDER = ROOT / "docs" / "FRONTEND_BUILD_ORDER.md"
OPENAPI = ROOT / "contracts" / "openapi.json"


class TraceabilityError(ValueError):
    """Raised when the frontend traceability contract is incomplete."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TraceabilityError(message)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(data, dict), f"{path} must contain an object")
    return data


def operation_ids(openapi: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    paths = openapi.get("paths")
    require(isinstance(paths, dict), "OpenAPI paths must be an object")
    for methods in paths.values():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if method not in {"get", "post", "put", "patch", "delete"} or not isinstance(operation, dict):
                continue
            operation_id = operation.get("operationId")
            require(isinstance(operation_id, str) and operation_id, "every HTTP operation must have an operationId")
            result.add(operation_id)
    return result


def table_section(text: str, start: str, end: str) -> str:
    try:
        return text.split(start, 1)[1].split(end, 1)[0]
    except IndexError as error:
        raise TraceabilityError(f"missing section boundary {start!r} or {end!r}") from error


def validate(text: str, frontend_order: str, openapi: dict[str, Any]) -> None:
    require("- **Task:** FE-000" in text, "FE-000 task marker is missing")
    require("- **Baseline:** 20 September 2026" in text, "absolute baseline date is missing")

    known_tasks = set(re.findall(r"^### (FE-\d{3}) —", frontend_order, re.MULTILINE))
    referenced_tasks = set(re.findall(r"FE-\d{3}", text))
    require(referenced_tasks <= known_tasks, f"unknown frontend tasks: {sorted(referenced_tasks - known_tasks)}")
    require("FE-000" in referenced_tasks, "FE-000 is not referenced")

    journey_ids = set(re.findall(r"^\| (FJ-\d{2}) \|", text, re.MULTILINE))
    require(journey_ids == {f"FJ-{number:02d}" for number in range(1, 6)}, "journey map must contain FJ-01 through FJ-05")

    capability_ids = set(re.findall(r"^\| (FCAP-\d{2}) \|", text, re.MULTILINE))
    require(capability_ids == {f"FCAP-{number:02d}" for number in range(1, 17)}, "capability map must contain FCAP-01 through FCAP-16")

    expected_acceptance = {
        *(f"FAC-TRUST-{number:02d}" for number in range(1, 8)),
        *(f"FAC-SAFE-{number:02d}" for number in range(1, 10)),
        *(f"FAC-RES-{number:02d}" for number in range(1, 5)),
        *(f"FAC-A11Y-{number:02d}" for number in range(1, 5)),
        "FAC-LANG-01",
        *(f"FAC-DEMO-{number:02d}" for number in range(1, 5)),
    }
    acceptance_ids = set(re.findall(r"^\| (FAC-[A-Z0-9-]+) \|", text, re.MULTILINE))
    require(acceptance_ids == expected_acceptance, f"acceptance map differs: missing={sorted(expected_acceptance - acceptance_ids)}, extra={sorted(acceptance_ids - expected_acceptance)}")

    declared_operations = set(re.findall(r"`([a-z][a-z0-9_]+)`", text))
    documented_operations = {value for value in declared_operations if value in operation_ids(openapi)}
    required_operations = operation_ids(openapi) - {"health_live", "health_ready"}
    require(documented_operations == required_operations, f"operation coverage differs: missing={sorted(required_operations - documented_operations)}")

    for data_class in ("public", "public_after_review", "private", "one_time_secret", "operational_only"):
        require(f"`{data_class}`" in text, f"data classification {data_class!r} is missing")

    expected_non_goals = {f"FNG-{number:02d}" for number in range(1, 9)}
    non_goals = set(re.findall(r"^\| (FNG-\d{2}) \|", text, re.MULTILINE))
    require(non_goals == expected_non_goals, "non-goal map must contain FNG-01 through FNG-08")

    exit_gate = table_section(text, "## 10. FE-000 exit gate", "FE-000 reopens")
    require(exit_gate.count("- [x]") == 8, "FE-000 exit gate must contain eight checked controls")
    require("- [ ]" not in exit_gate, "FE-000 exit gate contains an unchecked control")
    require("TODO" not in text and "TBD" not in text, "traceability contains TODO/TBD")
    require("/api/proxy" not in text, "traceability must not introduce a generic BFF proxy")


def run_negative_self_tests(text: str, frontend_order: str, openapi: dict[str, Any]) -> None:
    mutations = {
        "missing capability": text.replace("| FCAP-16 |", "| REMOVED-16 |", 1),
        "unknown frontend task": text.replace("FE-164", "FE-999", 1),
        "missing operation": text.replace("`reports_submit`", "`removed_reports_submit`"),
    }
    for name, mutation in mutations.items():
        try:
            validate(mutation, frontend_order, openapi)
        except TraceabilityError:
            continue
        raise TraceabilityError(f"negative self-test did not reject {name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_DOCUMENT)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        text = args.path.read_text(encoding="utf-8")
        frontend_order = FRONTEND_ORDER.read_text(encoding="utf-8")
        openapi = load_json(OPENAPI)
        validate(text, frontend_order, openapi)
        if args.self_test:
            run_negative_self_tests(text, frontend_order, openapi)
    except (OSError, json.JSONDecodeError, TraceabilityError) as error:
        print(f"frontend traceability: FAIL: {error}", file=sys.stderr)
        return 1

    suffix = " with negative self-tests" if args.self_test else ""
    print(f"frontend traceability: OK{suffix} ({args.path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

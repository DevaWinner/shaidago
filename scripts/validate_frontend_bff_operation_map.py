#!/usr/bin/env python3
"""Validate FE-004 operation coverage and BFF-boundary prohibitions."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOCUMENT = ROOT / "docs" / "FRONTEND_BFF_OPERATION_MAP.md"
OPENAPI = ROOT / "contracts" / "openapi.json"


class BffOperationMapError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BffOperationMapError(message)


def operation_ids(openapi: dict[str, Any]) -> set[str]:
    return {
        operation["operationId"]
        for methods in openapi["paths"].values()
        for method, operation in methods.items()
        if method in {"get", "post", "put", "patch", "delete"}
    }


def validate(text: str, openapi: dict[str, Any]) -> None:
    require("- **Task:** FE-004" in text, "FE-004 marker is missing")
    ledger = text.split("## 3. Operation ledger", 1)[1].split("## 4.", 1)[0]
    listed = re.findall(r"^\| `([a-z][a-z0-9_]+)` \|", ledger, re.MULTILINE)
    expected = operation_ids(openapi) - {"health_live", "health_ready"}
    require(set(listed) == expected and len(listed) == len(expected), "operation ledger must cover every non-health operation exactly once")

    profiles = {
        "SR-PUBLIC", "SR-REVIEWER", "BFF-PUBLIC-JSON", "BFF-PUBLIC-GET",
        "BFF-PUBLIC-IDEMPOTENT", "BFF-PUBLIC-IDEMPOTENT-EMPTY", "BFF-REPORT-MULTIPART",
        "BFF-REVIEWER-JSON", "BFF-REVIEWER-EMPTY", "BFF-REVIEWER-GET",
        "BFF-EVIDENCE-STREAM", "BFF-AUTH",
    }
    for profile in profiles:
        require(f"`{profile}`" in text, f"missing transport profile {profile}")
    for operation in listed:
        row = next(line for line in ledger.splitlines() if line.startswith(f"| `{operation}` |"))
        require("route.ts" in row or "src/lib/api/server.ts" in row, f"{operation} has no exact transport owner")
        require(any(profile in row for profile in profiles), f"{operation} has no transport profile")

    for marker in (
        "Origin", "CSRF", "Idempotency-Key", "application/problem+json", "Cache-Control: no-store",
        "X-Shaidago-Locale", "X-Request-Id", "X-Shaidago-Client-Hmac", "X-Forwarded-*",
        "Content-Disposition", "never echo backend detail",
    ):
        require(marker.casefold() in text.casefold(), f"required boundary rule {marker!r} is missing")
    require("/api/proxy/[...path]" in text, "generic proxy prohibition is missing")
    require("server environment/config" in text and "private FastAPI hostname" in text, "client/server prohibition is incomplete")
    require(text.count("- [x]") == 5 and "- [ ]" not in text, "FE-004 checklist must have five checked controls")
    require("TODO" not in text and "TBD" not in text, "operation map contains TODO/TBD")


def negative_self_tests(text: str, openapi: dict[str, Any]) -> None:
    mutations = {
        "missing operation": text.replace("| `reports_submit` |", "| `removed_submit` |", 1),
        "missing profile": text.replace("`BFF-EVIDENCE-STREAM`", "`REMOVED-STREAM`"),
        "unchecked gate": text.replace("- [x] Every 35", "- [ ] Every 35", 1),
    }
    for name, mutation in mutations.items():
        try:
            validate(mutation, openapi)
        except BffOperationMapError:
            continue
        raise BffOperationMapError(f"negative self-test did not reject {name}")


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
    except (OSError, json.JSONDecodeError, BffOperationMapError) as error:
        print(f"frontend BFF operation map: FAIL: {error}", file=sys.stderr)
        return 1
    suffix = " with negative self-tests" if args.self_test else ""
    print(f"frontend BFF operation map: OK{suffix} ({args.path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

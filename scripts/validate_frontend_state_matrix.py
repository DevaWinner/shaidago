#!/usr/bin/env python3
"""Validate FE-002 state and stable UI-fixture coverage."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOCUMENT = ROOT / "docs" / "FRONTEND_STATE_MATRIX.md"
FIXTURE_PATTERN = re.compile(r"ui\.[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+")


class StateMatrixError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise StateMatrixError(message)


def fixture_names(text: str) -> list[str]:
    fixtures: list[str] = []
    for line in text.splitlines():
        full_names = FIXTURE_PATTERN.findall(line)
        if not full_names:
            continue
        fixtures.extend(full_names)
        surface = full_names[0].split(".")[1]
        fixtures.extend(
            f"ui.{surface}.{state}"
            for state in re.findall(r"`\.([a-z][a-z0-9_]*)`", line)
        )
    return fixtures


def validate(text: str) -> None:
    require("- **Task:** FE-002" in text, "FE-002 marker is missing")
    required_states = {
        "initial", "loading", "revalidating", "empty", "no_matches",
        "success_minimum", "success_typical", "success_maximum", "stale",
        "source_unavailable", "partial", "partial_translation",
        "machine_assisted_translation", "field_validation", "server_validation",
        "unauthenticated", "forbidden", "session_expired", "csrf_rejected",
        "origin_rejected", "rate_limited", "backend_unavailable",
        "provider_unavailable", "timeout", "cancelled", "dead_letter",
        "offline_public_cached", "offline_public_uncached",
        "offline_private_unavailable", "retry_success", "idempotency_replay",
        "idempotency_conflict", "conflict", "javascript_disabled",
    }
    catalog = text.split("## 2. Shared state vocabulary", 1)[1].split("## 3.", 1)[0]
    declared_states = set(re.findall(r"^\| `([a-z][a-z0-9_]*)` \|", catalog, re.MULTILINE))
    require(declared_states == required_states, f"state catalogue differs: missing={sorted(required_states - declared_states)}, extra={sorted(declared_states - required_states)}")

    fixtures = fixture_names(text)
    require(len(fixtures) >= 180, f"expected at least 180 explicit fixture references, found {len(fixtures)}")
    require(all(fixture == fixture.lower() for fixture in fixtures), "fixture names must be lowercase")

    required_surfaces = {
        "landing", "project_directory", "project_detail", "source_view", "project_qa",
        "report_context", "report_wizard", "report_evidence", "report_submission",
        "report_completion", "tracking", "tracking_follow_up", "handle_create",
        "handle_list", "handle_delete", "reviewer_sign_in", "reviewer_queue",
        "reviewer_report", "evidence_download", "reviewer_note", "report_transition",
        "public_update", "public_discovery", "discovery_plan", "reviewer_discovery",
        "discovery_analysis", "discovery_follow_up", "source_decision",
    }
    surfaces = {fixture.split(".")[1] for fixture in fixtures}
    require(required_surfaces <= surfaces, f"fixture surfaces missing: {sorted(required_surfaces - surfaces)}")

    required_transport = {"success", "empty", "stale", "partial", "denied", "rate_limited", "dependency_down", "validation"}
    for scenario in required_transport:
        require(f"`{scenario}`" in text, f"transport scenario {scenario!r} is missing")

    require(text.count("- [x]") == 7 and "- [ ]" not in text, "FE-002 exit gate must contain seven checked controls")
    require("TODO" not in text and "TBD" not in text, "state matrix contains TODO/TBD")


def negative_self_tests(text: str) -> None:
    mutations = {
        "missing shared state": text.replace("| `dead_letter` |", "| removed_dead_letter |", 1),
        "missing surface": text.replace("ui.source_decision.", "ui.removed_decision."),
        "unchecked exit": text.replace("- [x] Stable fixture naming", "- [ ] Stable fixture naming", 1),
    }
    for name, mutation in mutations.items():
        try:
            validate(mutation)
        except StateMatrixError:
            continue
        raise StateMatrixError(f"negative self-test did not reject {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_DOCUMENT)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        text = args.path.read_text(encoding="utf-8")
        validate(text)
        if args.self_test:
            negative_self_tests(text)
    except (OSError, StateMatrixError) as error:
        print(f"frontend state matrix: FAIL: {error}", file=sys.stderr)
        return 1
    suffix = " with negative self-tests" if args.self_test else ""
    print(f"frontend state matrix: OK{suffix} ({args.path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

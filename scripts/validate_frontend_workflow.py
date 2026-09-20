#!/usr/bin/env python3
"""Checks the security and execution invariants of the frontend GitHub workflow."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


WORKFLOW_PATH = Path(".github/workflows/frontend.yml")
PINNED_ACTION_PATTERN = re.compile(
    r"^\s*- uses: (?P<action>[^@\s]+)@(?P<sha>[0-9a-f]{40})\s+# v[^\s]+$",
    re.MULTILINE,
)


def validate(workflow: str) -> list[str]:
    errors: list[str] = []
    pinned_actions = PINNED_ACTION_PATTERN.findall(workflow)
    action_reference_lines = re.findall(r"^\s*- uses: .+$", workflow, re.MULTILINE)

    if len(pinned_actions) != 4:
        errors.append("workflow must use exactly four full-SHA action references")

    if len(action_reference_lines) != len(pinned_actions):
        errors.append("every action reference must be pinned to a full SHA with a version comment")

    if {action for action, _ in pinned_actions} != {"actions/checkout", "actions/setup-node"}:
        errors.append("workflow may use only pinned actions/checkout and actions/setup-node")

    required_fragments = (
        "permissions:\n  contents: read",
        "persist-credentials: false",
        "node-version-file: .nvmrc",
        "cache: pnpm",
        "pnpm install --frozen-lockfile",
        "make web-format-check",
        "make web-lint",
        "make web-typecheck",
        "make web-unit",
        "make web-component",
        "make web-contract",
        "make web-boundary",
        "make web-e2e",
        "make web-a11y",
        "frontend-required",
    )
    for fragment in required_fragments:
        if fragment not in workflow:
            errors.append(f"workflow is missing required fragment: {fragment}")

    forbidden_fragments = (
        "actions/upload-artifact",
        "actions/download-artifact",
        "secrets.",
        "pull_request_target",
    )
    for fragment in forbidden_fragments:
        if fragment in workflow:
            errors.append(f"workflow contains forbidden fragment: {fragment}")

    if re.search(r":\s*write\b", workflow):
        errors.append("workflow must not request write permissions")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    arguments = parser.parse_args()

    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    errors = validate(workflow)
    if errors:
        raise SystemExit("\n".join(errors))

    if arguments.self_test:
        negative_workflow = workflow.replace("make web-boundary", "# web-boundary", 1)
        if not validate(negative_workflow):
            raise SystemExit("self-test did not reject a missing boundary check")

        unpinned_workflow = workflow.replace(
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            "actions/checkout@v7",
            1,
        )
        if not validate(unpinned_workflow):
            raise SystemExit("self-test did not reject an unpinned action")

    print("frontend workflow validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

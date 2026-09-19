#!/usr/bin/env python3
"""Validate ShaidaGo's architecture decision records without dependencies."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIRECTORY = ROOT / "docs" / "decisions"
BUILD_ORDERS = (ROOT / "docs" / "BACKEND_BUILD_ORDER.md", ROOT / "docs" / "FRONTEND_BUILD_ORDER.md")
TASK_HEADING = re.compile(r"^### ((?:BE|FE)-\d{3}) —", re.MULTILINE)
TASK_REFERENCE = re.compile(r"\b(?:BE|FE)-\d{3}\b")
FILENAME = re.compile(r"^(\d{4})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
DATE = re.compile(r"^- \*\*Date:\*\* \d{4}-\d{2}-\d{2}$", re.MULTILINE)
STATUS = re.compile(r"^- \*\*Status:\*\* (proposed|accepted|deprecated|superseded by ADR-\d{4})$", re.MULTILINE)
REQUIRED_SECTIONS = (
    "## Context",
    "## Decision",
    "## Alternatives considered",
    "## Consequences",
    "## Migration impact",
    "## Enforcement",
)
# BE-004 names these decisions; each must be covered by an accepted record.
REQUIRED_TOPICS = {
    "modular monolith": "Modular monolith",
    "BFF authority and internal-service authentication": "internal-service authentication",
    "database roles and no-RETURNING submission": "no-`RETURNING` submission",
    "envelope encryption": "Envelope encryption",
    "tracking-code storage": "Tracking-code structure",
    "sanitation and scanner limitation": "scanner limitation",
    "generated OpenAPI contract": "OpenAPI contract",
    "provider isolation and live tests": "Provider isolation",
}


class DecisionError(ValueError):
    """Raised when a decision record or the index violates a structural rule."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DecisionError(message)


def load_task_ids() -> set[str]:
    return {task_id for path in BUILD_ORDERS for task_id in TASK_HEADING.findall(path.read_text(encoding="utf-8"))}


def validate_record(name: str, text: str, task_ids: set[str]) -> tuple[str, str]:
    match = FILENAME.match(name)
    require(match is not None, f"{name}: file name must be NNNN-kebab-title.md")
    assert match is not None
    number = match.group(1)

    title_line = text.splitlines()[0] if text else ""
    require(title_line.startswith(f"# ADR-{number}: "), f"{name}: first line must be '# ADR-{number}: <title>'")
    status = STATUS.search(text)
    require(status is not None, f"{name}: missing or invalid status line")
    assert status is not None
    require(DATE.search(text) is not None, f"{name}: missing absolute YYYY-MM-DD date")
    require("- **Task:** BE-" in text, f"{name}: missing owning task")

    positions = [text.find(heading + "\n") for heading in REQUIRED_SECTIONS]
    require(all(position >= 0 for position in positions), f"{name}: missing a required section")
    require(positions == sorted(positions), f"{name}: required sections are out of order")

    enforcement = text.split("## Enforcement\n", 1)[1]
    rows = [line for line in enforcement.splitlines() if line.startswith("| ") and not line.startswith("| Control") and not line.startswith("| ---")]
    require(rows, f"{name}: enforcement table has no controls")
    require(all(TASK_REFERENCE.search(row) for row in rows), f"{name}: every enforcement row must name an owning task")

    unknown_tasks = set(TASK_REFERENCE.findall(text)) - task_ids
    require(not unknown_tasks, f"{name}: cites tasks absent from the build orders: {sorted(unknown_tasks)}")
    require("TODO" not in text and "TBD" not in text, f"{name}: contains an unresolved TODO/TBD")
    return title_line.split(": ", 1)[1], status.group(1)


def validate(records: dict[str, str], index: str, task_ids: set[str]) -> None:
    require(records, "no decision records found")
    numbers = sorted(name[:4] for name in records)
    require(numbers == [f"{n:04d}" for n in range(1, len(numbers) + 1)], "decision numbers must be contiguous from 0001")

    titles: dict[str, tuple[str, str]] = {}
    for name, text in sorted(records.items()):
        titles[name] = validate_record(name, text, task_ids)
        title, status = titles[name]
        require(f"]({name}) | {title} | {status} |" in index, f"index row for {name} is missing or out of date")

    index_links = set(re.findall(r"\]\((\d{4}-[^)]+\.md)\)", index))
    require(index_links == set(records), f"index links do not match records: {sorted(index_links ^ set(records))}")

    accepted_titles = " ".join(title for title, status in titles.values() if status == "accepted")
    for topic, marker in REQUIRED_TOPICS.items():
        require(marker in accepted_titles, f"no accepted record covers {topic}")


def run_negative_self_tests(records: dict[str, str], index: str, task_ids: set[str]) -> None:
    first = sorted(records)[0]
    mutations = {
        "missing section": ({**records, first: records[first].replace("## Migration impact\n", "## Impact\n", 1)}, index),
        "missing date": ({**records, first: records[first].replace("- **Date:** 2026-09-19", "- **Date:** September", 1)}, index),
        "invalid status": ({**records, first: records[first].replace("- **Status:** accepted", "- **Status:** agreed", 1)}, index),
        "unknown task reference": ({**records, first: records[first].replace("BE-110", "BE-119", 1)}, index),
        "stale index row": (records, index.replace("| accepted |", "| proposed |", 1)),
        "numbering gap": ({(("0009" + name[4:]) if name == first else name): text for name, text in records.items()}, index),
    }
    for name, (mutated_records, mutated_index) in mutations.items():
        try:
            validate(mutated_records, mutated_index, task_ids)
        except DecisionError:
            continue
        raise DecisionError(f"negative self-test did not reject {name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path, default=DEFAULT_DIRECTORY)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        records = {
            path.name: path.read_text(encoding="utf-8")
            for path in sorted(args.directory.glob("*.md"))
            if path.name != "README.md"
        }
        index = (args.directory / "README.md").read_text(encoding="utf-8")
        task_ids = load_task_ids()
        validate(records, index, task_ids)
        if args.self_test:
            run_negative_self_tests(records, index, task_ids)
    except (OSError, DecisionError) as error:
        print(f"decision records: FAIL: {error}", file=sys.stderr)
        return 1

    suffix = " with negative self-tests" if args.self_test else ""
    print(f"decision records: OK{suffix} ({len(records)} records in {args.directory})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

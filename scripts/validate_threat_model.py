#!/usr/bin/env python3
"""Validate structural coverage of ShaidaGo's threat model."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOCUMENT = ROOT / "docs" / "THREAT_MODEL.md"
BUILD_ORDERS = (ROOT / "docs" / "BACKEND_BUILD_ORDER.md", ROOT / "docs" / "FRONTEND_BUILD_ORDER.md")
TASK_HEADING = re.compile(r"^### ((?:BE|FE)-\d{3}) —", re.MULTILINE)
TASK_REFERENCE = re.compile(r"\b(?:BE|FE)-\d{3}\b")
ASSET_ROW = re.compile(
    r"^\| (A-\d{2}) \| .*? \| `(public|public_after_review|private|secret|security_metadata)` \|",
    re.MULTILINE,
)
THREAT_ROW = re.compile(r"^\| (TM-([STRIDE])\d{2}) \| ([A-Za-z ]+) \|", re.MULTILINE)


class ThreatModelError(ValueError):
    """Raised when the threat model loses required coverage."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ThreatModelError(message)


def section(text: str, start: str, end: str) -> str:
    try:
        after_start = text.split(start, 1)[1]
        return after_start.split(end, 1)[0]
    except IndexError as error:
        raise ThreatModelError(f"missing section boundary: {start!r} or {end!r}") from error


def load_task_ids() -> set[str]:
    return {task_id for path in BUILD_ORDERS for task_id in TASK_HEADING.findall(path.read_text(encoding="utf-8"))}


def validate(text: str, task_ids: set[str]) -> None:
    require("- **Task:** BE-003" in text, "task marker BE-003 is missing")
    require("- **Reviewed baseline date:** 2026-09-19" in text, "absolute baseline date is missing")

    expected_sections = [
        "## 1. Scope and security objectives",
        "## 2. Data classification",
        "## 3. Asset register",
        "## 4. Actors and capabilities",
        "## 5. Trust zones",
        "## 6. Critical data flows",
        "## 7. Outbound destination allowlists",
        "## 8. Private-data lifecycle, retention ownership, and deletion",
        "## 9. STRIDE threats and mandatory verification",
        "## 10. Security-test catalogue required by repository policy",
        "## 11. Residual risks and release blockers",
        "## 12. Exit checklist and change control",
    ]
    positions = [text.find(heading) for heading in expected_sections]
    require(all(position >= 0 for position in positions), "one or more required sections are missing")
    require(positions == sorted(positions), "required sections are out of order")

    asset_rows = ASSET_ROW.findall(text)
    asset_ids = [asset_id for asset_id, _ in asset_rows]
    expected_assets = {f"A-{number:02d}" for number in range(1, 25)}
    require(set(asset_ids) == expected_assets, "asset register must contain exactly A-01 through A-24")
    require(len(asset_ids) == len(set(asset_ids)), "asset register contains duplicate IDs")

    classifications = {asset_id: classification for asset_id, classification in asset_rows}
    lifecycle = section(
        text,
        "## 8. Private-data lifecycle, retention ownership, and deletion",
        "## 9. STRIDE threats and mandatory verification",
    )
    lifecycle_assets = set(re.findall(r"A-\d{2}", lifecycle))
    sensitive_assets = {
        asset_id
        for asset_id, classification in classifications.items()
        if classification in {"private", "secret", "security_metadata"}
    }
    require(sensitive_assets <= lifecycle_assets, f"lifecycle table omits {sorted(sensitive_assets - lifecycle_assets)}")

    expected_zones = {f"Z-{number:02d}" for number in range(0, 100, 10)}
    zone_section = section(text, "## 5. Trust zones", "## 6. Critical data flows")
    declared_zones = set(re.findall(r"^\| (Z-\d{2}) \|", zone_section, re.MULTILINE))
    require(declared_zones == expected_zones, "trust-zone table must contain Z-00 through Z-90")

    expected_boundaries = {f"TB-{number:02d}" for number in range(1, 10)}
    declared_boundaries = set(re.findall(r"^\| (TB-\d{2}) \|", zone_section, re.MULTILINE))
    require(declared_boundaries == expected_boundaries, "boundary table must contain TB-01 through TB-09")

    expected_flows = {f"DF-{number:02d}" for number in range(1, 7)}
    flow_headings = re.findall(r"^### (DF-\d{2}) —", text, re.MULTILINE)
    require(set(flow_headings) == expected_flows, "critical flows must contain exactly DF-01 through DF-06")
    require(len(flow_headings) == len(set(flow_headings)), "critical flow heading is duplicated")
    for flow_id in expected_flows:
        require(f"{flow_id}.1" in text, f"{flow_id} has no enumerated boundary edge")

    outbound = section(
        text,
        "## 7. Outbound destination allowlists",
        "## 8. Private-data lifecycle, retention ownership, and deletion",
    )
    for destination in (
        "Public browser",
        "Scoped reporter browser",
        "Reviewer browser",
        "Redis",
        "Object storage",
        "Search provider",
        "AI provider",
        "Public publisher",
        "Logs/error tracking",
        "Metrics",
        "CI/test artifacts",
    ):
        require(f"| {destination} |" in outbound, f"outbound allowlist omits {destination}")

    threat_rows = THREAT_ROW.findall(text)
    threat_ids = [threat_id for threat_id, _, _ in threat_rows]
    require(len(threat_ids) >= 25, "STRIDE register must contain at least 25 concrete threats")
    require(len(threat_ids) == len(set(threat_ids)), "STRIDE register contains duplicate threat IDs")
    require({letter for _, letter, _ in threat_rows} == set("STRIDE"), "STRIDE register does not cover all six categories")
    require(all("BE-" in line for line in text.splitlines() if line.startswith("| TM-")), "every threat must name a verification task")
    unknown_tasks = set(TASK_REFERENCE.findall(text)) - task_ids
    require(not unknown_tasks, f"threat model cites tasks absent from the build orders: {sorted(unknown_tasks)}")

    exit_section = section(text, "## 12. Exit checklist and change control", "Re-run threat modelling")
    require("- [ ]" not in exit_section, "BE-003 exit checklist contains an unchecked item")
    require(exit_section.count("- [x]") == 7, "BE-003 exit checklist must contain seven checked controls")
    require("TODO" not in text and "TBD" not in text, "threat model contains an unresolved TODO/TBD")


def run_negative_self_tests(text: str, task_ids: set[str]) -> None:
    mutations = {
        "missing critical flow": text.replace("### DF-06 —", "### Removed flow —", 1),
        "missing private lifecycle": text.replace("| A-05 contacts |", "| contacts |", 1),
        "duplicate threat ID": text.replace("| TM-S02 |", "| TM-S01 |", 1),
        "unclassified asset": text.replace("| AI prompts and raw provider output | `private` |", "| AI prompts and raw provider output | Mixed |", 1),
        "unknown task reference": text.replace("BE-093:", "BE-099:", 1),
    }
    for name, mutation in mutations.items():
        try:
            validate(mutation, task_ids)
        except ThreatModelError:
            continue
        raise ThreatModelError(f"negative self-test did not reject {name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_DOCUMENT)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        text = args.path.read_text(encoding="utf-8")
        task_ids = load_task_ids()
        validate(text, task_ids)
        if args.self_test:
            run_negative_self_tests(text, task_ids)
    except (OSError, ThreatModelError) as error:
        print(f"threat model: FAIL: {error}", file=sys.stderr)
        return 1

    suffix = " with negative self-tests" if args.self_test else ""
    print(f"threat model: OK{suffix} ({args.path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

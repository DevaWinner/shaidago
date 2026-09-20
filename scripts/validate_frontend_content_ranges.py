#!/usr/bin/env python3
"""Validate FE-003 synthetic frontend content-range fixtures and their documentation."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOCUMENT = ROOT / "docs" / "FRONTEND_CONTENT_RANGE_INVENTORY.md"
DEFAULT_FIXTURES = ROOT / "data" / "frontend-content-range-fixtures.json"
SOURCE_REGISTER = ROOT / "data" / "source-register.json"
LABEL = "SYNTHETIC LAYOUT FIXTURE — NOT A PROJECT, SOURCE, REPORT, OR CREDENTIAL"
EXPECTED_IDS = {
    f"content.{surface}.{tier}"
    for surface in (
        "project",
        "locale",
        "source",
        "report",
        "tracking",
        "reviewer",
        "discovery",
    )
    for tier in ("minimum", "typical", "maximum")
}


class ContentRangeError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContentRangeError(message)


def fixture_by_id(fixtures: dict[str, Any], identifier: str) -> dict[str, Any]:
    for fixture in fixtures["fixtures"]:
        if fixture["id"] == identifier:
            return fixture
    raise ContentRangeError(f"missing fixture {identifier}")


def source_register_text(source_register: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    for source in source_register["sources"]:
        values.add(source["title"])
    for project in source_register["projects"]:
        values.add(project["title"])
        for fact in project["facts"]:
            values.add(fact["statement"])
            for citation in fact["sources"]:
                for passage in citation.get("passages", []):
                    values.add(passage["text"])
                claimed = citation.get("claimed_passage_not_verified")
                if claimed is not None:
                    values.add(claimed)
    return values


def validate(document: str, fixtures: dict[str, Any], source_register: dict[str, Any]) -> None:
    require("- **Task:** FE-003" in document, "FE-003 marker is missing")
    require("frontend-content-range-fixtures.json" in document, "fixture-source link is missing")
    normalised_document = re.sub(r"\s+", " ", document)
    require(LABEL in normalised_document, "synthetic fixture label is missing from documentation")
    require(fixtures.get("schema_version") == 1, "fixture schema version must be 1")
    require(fixtures.get("kind") == "synthetic_frontend_layout_fixtures", "fixture kind is invalid")
    require(fixtures.get("fixture_label") == LABEL, "fixture label is invalid")

    records = fixtures.get("fixtures")
    require(isinstance(records, list), "fixtures must be a list")
    identifiers = [record.get("id") for record in records]
    require(set(identifiers) == EXPECTED_IDS and len(identifiers) == len(EXPECTED_IDS), "fixture IDs must cover each surface/tier exactly once")
    require(set(re.findall(r"`(content\.[a-z]+\.(?:minimum|typical|maximum))`", document)) == EXPECTED_IDS, "documentation fixture registry differs from source")

    for fixture in records:
        require(fixture.get("tier") in {"minimum", "typical", "maximum"}, f"invalid tier in {fixture.get('id')}")
        require(isinstance(fixture.get("data"), dict), f"missing data object in {fixture.get('id')}")

    locale_maximum = fixture_by_id(fixtures, "content.locale.maximum")["data"]["labels"]
    locale_status = {entry["locale"]: entry["review_status"] for entry in locale_maximum}
    require(set(locale_status) == {"ha", "ig", "yo"}, "maximum locale fixture must cover ha, ig, and yo")
    require(all(status == "machine_assisted_unreviewed" for status in locale_status.values()), "non-English layout strings must remain unreviewed")

    report_maximum = fixture_by_id(fixtures, "content.report.maximum")["data"]
    require(report_maximum["description_recipe"]["target_characters"] == 8000, "report maximum must reach the 8000-character contract limit")
    attachments = report_maximum["attachments"]
    require(len(attachments) == 3 and all(item["size_bytes"] == 10 * 1024 * 1024 for item in attachments), "report maximum must contain three 10 MiB metadata-only attachments")
    categories = {
        value["value"]
        for value in json.loads((ROOT / "contracts" / "controlled-vocabulary.json").read_text(encoding="utf-8"))["vocabularies"]["report_concern_category"]["values"]
    }
    for tier in ("minimum", "typical", "maximum"):
        report = fixture_by_id(fixtures, f"content.report.{tier}")["data"]
        require(set(report["concern_categories"]) <= categories, f"report {tier} uses an unknown concern category")

    for tier in ("minimum", "typical", "maximum"):
        tracking = fixture_by_id(fixtures, f"content.tracking.{tier}")["data"]
        require(tracking["history"] == "not_exposed_by_current_tracking_contract", "tracking history must not be invented")
    for tier in ("minimum", "typical", "maximum"):
        currency = fixture_by_id(fixtures, f"content.project.{tier}")["data"]["currency"]
        require(currency["contract_status"] == "not_exposed_by_current_public_contract", "currency must not be presented as a public DTO field")

    discovery_maximum = fixture_by_id(fixtures, "content.discovery.maximum")["data"]
    require(discovery_maximum["result_cards"] == 10, "discovery maximum must contain ten result cards")
    require(discovery_maximum["follow_up_questions"] == 5, "discovery maximum must contain five follow-up questions")
    require(discovery_maximum["label"] == "discovered — not yet reviewed", "discovery label is missing")

    raw_fixture_text = json.dumps(fixtures, ensure_ascii=False).casefold()
    forbidden_keys = {"tracking_code", "passphrase", "contact_value", "session_token", "csrf_token", "signed_url"}
    require(not (forbidden_keys & set(re.findall(r'"([^"\\]+)"\s*:', raw_fixture_text))), "fixture source contains a secret/private value key")
    for protected_text in source_register_text(source_register):
        require(protected_text.casefold() not in raw_fixture_text, "fixture source leaks source-register content")

    require(document.count("- [x]") == 5 and "- [ ]" not in document, "FE-003 checklist must have five checked controls")
    require("TODO" not in document and "TBD" not in document, "content inventory contains TODO/TBD")


def negative_self_tests(document: str, fixtures: dict[str, Any], source_register: dict[str, Any]) -> None:
    missing_fixture = json.loads(json.dumps(fixtures))
    missing_fixture["fixtures"] = [item for item in missing_fixture["fixtures"] if item["id"] != "content.discovery.maximum"]
    leaked_private_key = json.loads(json.dumps(fixtures))
    leaked_private_key["fixtures"][0]["data"]["tracking_code"] = "not-a-real-secret"
    unchecked_document = document.replace("- [x] All requested", "- [ ] All requested", 1)
    for name, mutated_document, mutated_fixtures in (
        ("missing fixture", document, missing_fixture),
        ("private key", document, leaked_private_key),
        ("unchecked checklist", unchecked_document, fixtures),
    ):
        try:
            validate(mutated_document, mutated_fixtures, source_register)
        except ContentRangeError:
            continue
        raise ContentRangeError(f"negative self-test did not reject {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", nargs="?", type=Path, default=DEFAULT_DOCUMENT)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        document = args.document.read_text(encoding="utf-8")
        fixtures = json.loads(args.fixtures.read_text(encoding="utf-8"))
        source_register = json.loads(SOURCE_REGISTER.read_text(encoding="utf-8"))
        validate(document, fixtures, source_register)
        if args.self_test:
            negative_self_tests(document, fixtures, source_register)
    except (OSError, json.JSONDecodeError, ContentRangeError) as error:
        print(f"frontend content ranges: FAIL: {error}", file=sys.stderr)
        return 1
    suffix = " with negative self-tests" if args.self_test else ""
    print(f"frontend content ranges: OK{suffix} ({args.document})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

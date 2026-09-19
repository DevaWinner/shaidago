#!/usr/bin/env python3
"""Validate data/source-register.json (BE-001). Dependency-free.

    python3 scripts/validate_source_register.py [--self-test] [PATH]

Structure and honesty rules only; it does not touch the network. To re-verify a passage against a
live page, fetch the page and compare it by hand or with the method recorded in the register.
"""

import copy
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "source-register.json"
VOCABULARY = ROOT / "contracts" / "controlled-vocabulary.json"
LOCALES = ("en", "ha", "ig", "yo")
FICTIONAL_LABEL = "FICTIONAL REPORT FIXTURE"
EVIDENCE = {"exact_passage_verified", "not_verified"}
# Words that assert a judgement about people or organisations. They may appear inside a quoted
# passage, never in a statement, gap, note, or basis written by us.
FORBIDDEN = re.compile(
    r"\b(corrupt\w*|fraud\w*|guilty|stole\w*|steal\w*|embezzl\w*|scam\w*|abandon\w*|criminal\w*)\b",
    re.IGNORECASE,
)
SHA = re.compile(r"^[0-9a-f]{64}$")
CONTACT = re.compile(r"(\+?\d[\d\s()-]{7,}\d|@|https?://)")


def vocabulary(name: str) -> set[str]:
    document = json.loads(VOCABULARY.read_text(encoding="utf-8"))
    return {entry["value"] for entry in document["vocabularies"][name]["values"]}


def iso(value: object) -> date | None:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def check(register: dict) -> list[str]:  # noqa: C901, PLR0912, PLR0915 - one flat rule list reads best
    errors: list[str] = []
    availability = vocabulary("source_availability")
    verification = vocabulary("verification_state")
    categories = vocabulary("project_category")
    statuses = vocabulary("project_public_status")
    translation = vocabulary("translation_status")
    prepared = iso(register.get("prepared_on"))
    if prepared is None:
        errors.append("prepared_on must be an ISO date")
    if register.get("fictional_label") != FICTIONAL_LABEL:
        errors.append("fictional_label must be the fixed label")

    sources: dict[str, dict] = {}
    for source in register.get("sources", []):
        sid = source.get("id", "?")
        if sid in sources:
            errors.append(f"{sid}: duplicate source id")
        sources[sid] = source
        if not str(source.get("url", "")).startswith("https://"):
            errors.append(f"{sid}: url must be https")
        if not source.get("publisher"):
            errors.append(f"{sid}: publisher is required")
        if source.get("availability") not in availability:
            errors.append(f"{sid}: availability is not in the controlled vocabulary")
        if iso(source.get("retrieved_on")) is None:
            errors.append(f"{sid}: retrieved_on must be an ISO date")
        elif prepared and iso(source["retrieved_on"]) > prepared:
            errors.append(f"{sid}: retrieved_on is after prepared_on")
        if source.get("published_on") is not None and iso(source["published_on"]) is None:
            errors.append(f"{sid}: published_on must be an ISO date or null")
        if not source.get("reuse_constraints"):
            errors.append(f"{sid}: reuse_constraints is required")
        digest = source.get("raw_page_sha256")
        if source.get("availability") == "available":
            if not (isinstance(digest, str) and SHA.match(digest)):
                errors.append(f"{sid}: an available source needs raw_page_sha256")
        elif digest is not None:
            errors.append(f"{sid}: a source that was not retrieved must not carry a hash")

    projects = register.get("projects", [])
    if len(projects) != 6:  # noqa: PLR2004 - the pilot register holds exactly six projects
        errors.append("the register must hold exactly six projects")
    localities = [p.get("locality") for p in projects]
    if localities.count("AMAC") != 3 or localities.count("Bwari") != 3:  # noqa: PLR2004
        errors.append("three AMAC and three Bwari projects are required")
    covered = {p.get("category") for p in projects}
    for need in ("health", "education", "water_sanitation", "roads_public_works"):
        if need not in covered:
            errors.append(f"no project covers {need}")

    seen_ids: set[str] = set()
    for project in projects:
        pid = project.get("id", "?")
        if pid in seen_ids:
            errors.append(f"{pid}: duplicate project id")
        seen_ids.add(pid)
        if project.get("category") not in categories:
            errors.append(f"{pid}: category is not in the controlled vocabulary")
        if project.get("proposed_public_status") not in statuses:
            errors.append(f"{pid}: proposed_public_status is not in the controlled vocabulary")
        checked = iso(project.get("last_checked_on"))
        if checked is None:
            errors.append(f"{pid}: last_checked_on is required")
        elif prepared and checked > prepared:
            errors.append(f"{pid}: last_checked_on is in the future")
        for text_field in ("status_basis", *project.get("unresolved_gaps", [])):
            value = project.get(text_field, text_field) if text_field == "status_basis" else text_field
            if FORBIDDEN.search(str(value)):
                errors.append(f"{pid}: judgemental wording in a project note")
        if not project.get("unresolved_gaps"):
            errors.append(f"{pid}: at least one unresolved gap must be recorded")
        if not project.get("facts"):
            errors.append(f"{pid}: a project needs at least one fact candidate")
        for fact in project.get("facts", []):
            fid = fact.get("id", "?")
            if FORBIDDEN.search(fact.get("statement", "") + " " + fact.get("note", "")):
                errors.append(f"{fid}: judgemental wording in a statement or note")
            if fact.get("evidence_status") not in EVIDENCE:
                errors.append(f"{fid}: evidence_status must be one of {sorted(EVIDENCE)}")
            if fact.get("proposed_verification_state") not in verification:
                errors.append(f"{fid}: proposed_verification_state is not in the vocabulary")
            if not fact.get("sources"):
                errors.append(f"{fid}: a fact needs at least one source candidate")
            publishers: set[str] = set()
            for reference in fact.get("sources", []):
                source = sources.get(reference.get("source_id"))
                if source is None:
                    errors.append(f"{fid}: unknown source {reference.get('source_id')}")
                    continue
                passages = reference.get("passages", [])
                if fact.get("evidence_status") == "exact_passage_verified":
                    if not passages:
                        errors.append(f"{fid}: a verified fact needs an exact passage")
                    if source.get("availability") != "available":
                        errors.append(f"{fid}: a verified fact needs an available source")
                    if source.get("published_on") is None:
                        errors.append(f"{fid}: a verified fact needs a publication date")
                    publishers.add(source.get("publisher", ""))
                for passage in passages:
                    text = passage.get("text", "")
                    if not text or len(text) > 1000:  # noqa: PLR2004
                        errors.append(f"{fid}: a passage must be 1 to 1000 characters")
                    if passage.get("sha256") != hashlib.sha256(text.encode()).hexdigest():
                        errors.append(f"{fid}: passage hash does not match its text")
                if fact.get("evidence_status") == "not_verified" and passages:
                    errors.append(f"{fid}: an unverified fact must not present verified passages")
            if fact.get("evidence_status") == "not_verified":
                if fact.get("seed_eligibility") != "not_eligible":
                    errors.append(f"{fid}: an unverified fact is not eligible for seeding")
                if fact.get("proposed_verification_state") != "awaiting_verification":
                    errors.append(f"{fid}: an unverified fact stays awaiting_verification")
            elif fact.get("seed_eligibility") != "eligible_as_cited_draft":
                errors.append(f"{fid}: a verified fact should be eligible as a cited draft")
            state = fact.get("proposed_verification_state")
            if state == "corroborated" and len(publishers) < 2:  # noqa: PLR2004
                errors.append(f"{fid}: corroborated needs two verified publishers")
            if state == "verified_official" and not any(
                sources.get(r.get("source_id"), {}).get("information_class") == "official_source"
                for r in fact.get("sources", [])
            ):
                errors.append(f"{fid}: verified_official needs an official source")
        for report in project.get("fictional_reports", []):
            if report.get("label") != FICTIONAL_LABEL or report.get("demo_only") is not True:
                errors.append(f"{pid}: a fictional report must carry the label and demo_only")
        if not project.get("fictional_reports"):
            errors.append(f"{pid}: a fictional report fixture is required")

    for route in register.get("escalation_routes", []):
        name = route.get("organisation", "?")
        if route.get("status") == "verified":
            if route.get("source_id") not in sources or iso(route.get("verified_on")) is None:
                errors.append(f"{name}: a verified route needs a source and a verification date")
        elif route.get("status") != "unverified_no_source":
            errors.append(f"{name}: unknown route status")
        elif route.get("source_id") is not None or route.get("verified_on") is not None:
            errors.append(f"{name}: an unverified route must not cite a source or date")
        if CONTACT.search(json.dumps(route)):
            errors.append(f"{name}: a route must not record contact details here")

    project_ids = {p.get("id") for p in projects}
    by_project: dict[str, set[str]] = {}
    for entry in register.get("translations", []):
        by_project.setdefault(entry.get("project_id", "?"), set()).add(entry.get("locale", "?"))
        if entry.get("project_id") not in project_ids:
            errors.append(f"translation for unknown project {entry.get('project_id')}")
        if entry.get("locale") not in LOCALES:
            errors.append("translation has an unsupported locale")
        if entry.get("translation_status") not in translation:
            errors.append("translation_status is not in the controlled vocabulary")
        if entry.get("translation_status") == "reviewed" and not (
            entry.get("reviewed_by") and iso(entry.get("reviewed_on"))
        ):
            errors.append("a reviewed translation needs reviewed_by and reviewed_on")
        if FORBIDDEN.search(entry.get("text", "")):
            errors.append("judgemental wording in a translation")
    for pid, locales in by_project.items():
        if locales != set(LOCALES):
            errors.append(f"{pid}: translations must cover en, ha, ig, and yo")
    return errors


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def self_test(register: dict) -> None:
    assert check(register) == [], check(register)

    def broken(mutate) -> list[str]:  # noqa: ANN001
        clone = copy.deepcopy(register)
        mutate(clone)
        return check(clone)

    facts = lambda r: r["projects"][0]["facts"][0]  # noqa: E731
    negatives = {
        "fact without a source": lambda r: facts(r).update(sources=[]),
        "missing last-checked date": lambda r: r["projects"][0].pop("last_checked_on"),
        "future last-checked date": lambda r: r["projects"][0].update(last_checked_on="2999-01-01"),
        "unlabeled fictional report": lambda r: r["projects"][0]["fictional_reports"][0].update(label="demo"),
        "verified fact without a passage": lambda r: facts(r)["sources"][0].update(passages=[]),
        "tampered passage": lambda r: facts(r)["sources"][0]["passages"][0].update(text="edited"),
        "judgemental wording": lambda r: facts(r).update(statement="The road was abandoned."),
        "unknown availability": lambda r: r["sources"][0].update(availability="fine"),
        "hash on an unretrieved source": lambda r: r["sources"][3].update(raw_page_sha256="0" * 64),
        "unverified fact made eligible": lambda r: r["projects"][1]["facts"][0].update(seed_eligibility="eligible_as_cited_draft"),
        "corroborated by one publisher": lambda r: facts(r).update(proposed_verification_state="corroborated"),
        "unverified route with a source": lambda r: r["escalation_routes"][0].update(source_id="S-PUNCH-2025-06"),
        "contact detail in a route": lambda r: r["escalation_routes"][0].update(note="call +234 803 555 0142"),
        "reviewed translation without a reviewer": lambda r: r["translations"][0].update(translation_status="reviewed"),
        "missing locale": lambda r: r["translations"].pop(),
        "category not covered": lambda r: [p.update(category="other_public_service") for p in r["projects"] if p["category"] == "health"],
        "fewer than six projects": lambda r: r["projects"].pop(),
    }
    for name, mutate in negatives.items():
        assert broken(mutate), f"expected a failure for: {name}"


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = Path(args[0]) if args else REGISTER
    register = load(path)
    if "--self-test" in sys.argv:
        self_test(register)
    errors = check(register)
    if errors:
        sys.stderr.write("source register: FAILED\n" + "\n".join(f"  - {e}" for e in errors) + "\n")
        return 1
    suffix = " with negative self-tests" if "--self-test" in sys.argv else ""
    sys.stdout.write(f"source register: OK{suffix} ({path})\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

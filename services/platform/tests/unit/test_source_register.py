"""The committed source register must validate, render without drift, and keep its honesty rules."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[4]
REGISTER = json.loads((ROOT / "data" / "source-register.json").read_text(encoding="utf-8"))


def run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed repository scripts
        [sys.executable, str(ROOT / "scripts" / script), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_register_passes_its_validator_and_negative_self_tests() -> None:
    result = run("validate_source_register.py", "--self-test")
    assert result.returncode == 0, result.stderr


def test_the_rendered_document_matches_the_data() -> None:
    result = run("render_source_register.py", "--check")
    assert result.returncode == 0, result.stderr


def test_only_verified_facts_are_eligible_for_seeding() -> None:
    for project in REGISTER["projects"]:
        for fact in project["facts"]:
            verified = fact["evidence_status"] == "exact_passage_verified"
            assert (fact["seed_eligibility"] == "eligible_as_cited_draft") == verified
            assert verified or not any(ref["passages"] for ref in fact["sources"])


def test_unreachable_sources_carry_no_hash_and_are_marked_restricted() -> None:
    for source in REGISTER["sources"]:
        if source["availability"] != "available":
            assert source["raw_page_sha256"] is None
            assert source["availability"] == "access_restricted"


def test_no_translation_claims_human_review_without_a_reviewer() -> None:
    assert all(t["translation_status"] != "reviewed" for t in REGISTER["translations"])

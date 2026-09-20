"""The staging smoke fixture is fictional in every string and matches its recorded replay."""

import json
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

from shaidago.discovery.planner import PublicProjectTerms, plan_public_query
from shaidago.seed.apply import SeedRefusedError, assert_safe_target
from shaidago.seed.plan import SeedPlan
from shaidago.seed.staging_fixture import (
    CATEGORY,
    DOCUMENT,
    LOCALITY_NAME,
    PASSAGE,
    REPLAY_QUERY,
    SLUG,
    TITLE,
    build_fixture_plan,
)

FIXTURES = Path(__file__).resolve().parents[5] / "data" / "discovery-fixtures" / "scenarios.json"


def _strings(plan: SeedPlan) -> list[str]:
    values: list[str] = []
    for source in plan.sources:
        values += [source.title, source.publisher, source.url, source.approval_note or ""]
    for project in plan.projects:
        values += [t.summary for t in project.translations]
    values += [fact.statement for fact in plan.facts]
    return values


def test_every_human_readable_string_says_it_is_fictional() -> None:
    plan = build_fixture_plan()
    for value in (
        *(s.title for s in plan.sources),
        *(s.publisher for s in plan.sources),
        *(f.statement for f in plan.facts),
        *(t.summary for p in plan.projects for t in p.translations),
    ):
        assert "fictional" in value.lower(), value


def test_it_uses_only_the_reserved_example_domain_and_no_real_names() -> None:
    plan = build_fixture_plan()
    for source in plan.sources:
        assert source.url.startswith("https://synthetic.example/")
    joined = " ".join(_strings(plan)).lower()
    for real in ("abuja", "amac", "bwari", "wike", "tinubu", "fct"):
        assert real not in joined


def test_it_never_borrows_the_real_registers_approval_note() -> None:
    (source,) = build_fixture_plan().sources
    assert source.approval_note is not None
    assert "SOURCE_REGISTER" not in source.approval_note
    assert "not a real source" in source.approval_note


def test_the_passage_is_inside_the_document_so_a_citation_can_quote_it() -> None:
    assert PASSAGE in DOCUMENT
    (fact,) = build_fixture_plan().facts
    assert fact.citations[0].passage == PASSAGE


def test_it_matches_the_query_the_recorded_replay_is_keyed_to() -> None:
    scenarios = json.loads(FIXTURES.read_text(encoding="utf-8"))["scenarios"]
    (recorded,) = (s for s in scenarios if s["id"] == "success")
    assert recorded["title"] == TITLE
    assert recorded["query"] == REPLAY_QUERY
    planned = plan_public_query(
        PublicProjectTerms(title=TITLE, locality=LOCALITY_NAME, category=CATEGORY)
    )
    assert planned.query == recorded["query"], "the planner must build exactly the recorded query"


def test_the_slug_is_the_one_the_smoke_journey_defaults_to() -> None:
    assert SLUG == "fixture-scenario-success"
    smoke = Path(__file__).resolve().parents[5] / "scripts" / "staging_smoke.py"
    assert f'"{SLUG}"' in smoke.read_text(encoding="utf-8")


@pytest.mark.parametrize("environment", ["production", "prod", ""])
def test_it_is_refused_wherever_the_real_seed_is_refused(environment: str) -> None:
    with pytest.raises(SeedRefusedError):
        assert_safe_target(
            {"APP_ENV": environment, "SEED_ALLOW_DEPLOYED": "1"},
            make_url("postgresql+psycopg://u:p@db.internal/db"),
        )


def test_staging_still_needs_the_explicit_flag() -> None:
    with pytest.raises(SeedRefusedError, match="SEED_ALLOW_DEPLOYED=1"):
        assert_safe_target(
            {"APP_ENV": "staging"}, make_url("postgresql+psycopg://u:p@db.internal/db")
        )

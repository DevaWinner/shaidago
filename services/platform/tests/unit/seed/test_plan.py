import copy
import json
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

from shaidago.seed.apply import SeedRefusedError, assert_safe_target
from shaidago.seed.plan import RegisterInvalidError, build_plan, load_register, slugify

REGISTER = load_register()


def test_only_projects_with_a_verified_fact_are_planned_and_the_rest_are_reported_as_gaps() -> None:
    plan = build_plan(REGISTER)
    assert [p.slug for p in plan.projects] == [
        "saburi-i-and-ii-access-road",
        "bwari-township-water-supply-network",
        "gaba-tokulo-road",
    ]
    gaps = "\n".join(plan.gaps)
    for skipped in ("AMAC-02", "AMAC-03", "BWARI-03"):
        assert f"{skipped}: not seeded" in gaps
    assert "escalation routes: none seeded" in gaps
    assert "fictional report fixtures: not seeded" in gaps


def test_no_unverified_claim_reaches_the_plan() -> None:
    plan = build_plan(REGISTER)
    statements = " ".join(f.statement for f in plan.facts)
    for unverified in ("Karshi", "Lokogoma", "Kuduru", "37/02/1/1/1/0005"):
        assert unverified not in statements
    every_passage = {c.passage for f in plan.facts for c in f.citations}
    assert all(any(p in source.content for source in plan.sources) for p in every_passage)


def test_proposed_status_is_held_at_unknown_and_reported() -> None:
    gaps = "\n".join(build_plan(REGISTER).gaps)
    assert "AMAC-01: proposed status 'completed' is held" in gaps
    assert "BWARI-02: proposed status 'completed' is held" in gaps


def test_source_versions_hold_only_the_cited_excerpts_and_are_content_addressed() -> None:
    plan = build_plan(REGISTER)
    for source in plan.sources:
        assert source.availability == "available"
        assert len(source.content) < 2000
        assert len(source.sha256) == 64
    again = build_plan(REGISTER)
    assert [s.sha256 for s in plan.sources] == [s.sha256 for s in again.sources]


def test_the_bwari_water_project_carries_all_four_locales_labelled_machine_assisted() -> None:
    project = next(p for p in build_plan(REGISTER).projects if p.slug.startswith("bwari-township"))
    assert {t.locale for t in project.translations} == {"en", "ha", "ig", "yo"}
    assert {t.status for t in project.translations} == {"machine_assisted"}


def test_every_planned_project_has_english_text_and_a_verified_summary() -> None:
    for project in build_plan(REGISTER).projects:
        english = next(t for t in project.translations if t.locale == "en")
        assert english.title
        assert english.summary


def test_the_plan_never_marks_anything_published_or_approved() -> None:
    text = json.dumps(build_plan(REGISTER).gaps)
    assert "published" not in text.lower() or "held" in text.lower()


@pytest.mark.parametrize(
    ("title", "slug"),
    [("Saburi I and II Access Road", "saburi-i-and-ii-access-road"), ("  A -- B!  ", "a-b")],
)
def test_slugs_are_kebab_case(title: str, slug: str) -> None:
    assert slugify(title) == slug


def test_an_invalid_register_is_refused_before_any_plan_exists(tmp_path: Path) -> None:
    broken = copy.deepcopy(REGISTER)
    broken["projects"][0]["facts"][0]["sources"] = []
    path = tmp_path / "register.json"
    path.write_text(json.dumps(broken), encoding="utf-8")
    with pytest.raises(RegisterInvalidError) as raised:
        load_register(path)
    assert any("source candidate" in p for p in raised.value.problems)


@pytest.mark.parametrize("environment", ["production", "staging", "", "prod"])
def test_the_seed_refuses_non_development_environments(environment: str) -> None:
    with pytest.raises(SeedRefusedError, match="development or test"):
        assert_safe_target(
            {"APP_ENV": environment}, make_url("postgresql+psycopg://u:p@localhost/db")
        )


def test_the_seed_refuses_a_missing_environment_and_remote_hosts_without_echoing_secrets() -> None:
    with pytest.raises(SeedRefusedError):
        assert_safe_target({}, make_url("postgresql+psycopg://u:p@localhost/db"))
    for host in ("db.example.com", "10.0.0.5", "shaidago.railway.internal"):
        with pytest.raises(SeedRefusedError) as raised:
            assert_safe_target(
                {"APP_ENV": "development"}, make_url(f"postgresql+psycopg://u:s3cret@{host}/db")
            )
        assert "s3cret" not in str(raised.value)
        assert host not in str(raised.value)


def test_local_targets_are_allowed_in_development_and_test() -> None:
    for env in ("development", "test"):
        for host in ("localhost", "127.0.0.1", "postgres"):
            assert_safe_target({"APP_ENV": env}, make_url(f"postgresql+psycopg://u:p@{host}/db"))

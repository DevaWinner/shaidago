"""The seed against PostgreSQL: idempotent, additive, evidence-honest, and safe."""

import copy
import hashlib
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import URL

from shaidago.api.app import create_app
from shaidago.api.dependencies import Dependencies
from shaidago.seed.__main__ import run
from shaidago.seed.apply import SeedRefusedError, apply_plan
from shaidago.seed.plan import RegisterInvalidError, build_plan, load_register
from shaidago.shared.clock import ManualClock
from shaidago.shared.database import Database, build_engine
from shaidago.shared.ids import Uuid7Generator
from tests.factories import CREDENTIAL, build_settings

START = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
TABLES = (
    "localities",
    "projects",
    "project_translations",
    "sources",
    "source_versions",
    "project_facts",
    "fact_citations",
)


@pytest.fixture
async def owner(role_urls: dict[str, URL]) -> AsyncIterator[Database]:
    engine = build_engine(role_urls["owner"], application_name="seed", statement_timeout_ms=20000)
    yield Database(engine)
    await engine.dispose()


async def seed(owner: Database, register: dict[str, Any] | None = None, hour: int = 12) -> str:
    clock = ManualClock(START.replace(hour=hour))
    plan = build_plan(register or load_register())
    async with owner.unit_of_work() as session:
        return (await apply_plan(session, plan, clock=clock, ids=Uuid7Generator(clock))).render()


async def snapshot(owner: Database) -> dict[str, list[tuple[object, ...]]]:
    async with owner.unit_of_work() as session:
        return {
            table: [
                tuple(row)
                for row in await session.execute(text(f"SELECT * FROM app.{table} ORDER BY id"))
            ]
            for table in TABLES
        }


async def test_a_second_run_changes_nothing_and_reports_everything_unchanged(
    owner: Database,
) -> None:
    first = await seed(owner)
    after_first = await snapshot(owner)
    second = await seed(owner, hour=15)
    assert await snapshot(owner) == after_first, "identical database state after the second run"
    assert "added 0, updated 0" in second
    assert "added 0" not in first.splitlines()[0]
    for line in second.splitlines():
        if "unchanged" in line:
            assert "added 0, updated 0" in line


async def test_the_seed_adds_the_expected_rows_and_only_verified_evidence(owner: Database) -> None:
    await seed(owner)
    async with owner.unit_of_work() as session:
        projects = {
            r.slug: r
            for r in await session.execute(
                text("SELECT slug, public_status, visibility FROM app.projects")
            )
        }
        facts = (
            await session.execute(
                text("SELECT visibility, verification_state FROM app.project_facts")
            )
        ).all()
        versions = (
            await session.execute(text("SELECT review_state, media_type FROM app.source_versions"))
        ).all()
        sources = {
            r[0] for r in await session.execute(text("SELECT canonical_url FROM app.sources"))
        }
        routes = (
            await session.execute(text("SELECT count(*) FROM app.escalation_routes"))
        ).scalar_one()
    assert {
        "saburi-i-and-ii-access-road",
        "bwari-township-water-supply-network",
        "gaba-tokulo-road",
    } <= set(projects)
    assert all(
        p.public_status == "unknown" for p in projects.values() if p.slug in {"gaba-tokulo-road"}
    )
    assert {f.visibility for f in facts} == {"draft"}, "nothing is published by the seed"
    assert {f.verification_state for f in facts} == {"awaiting_verification"}
    assert {v.review_state for v in versions} == {"pending"}, "approval is a human act"
    assert not any("fctubeb" in s or "thehospitalbook" in s for s in sources)
    assert routes == 0, "no escalation route is seeded"


async def test_citations_quote_the_stored_excerpts_exactly(owner: Database) -> None:
    await seed(owner)
    async with owner.unit_of_work() as session:
        bad = (
            await session.execute(
                text(
                    "SELECT count(*) FROM app.fact_citations c JOIN app.source_versions v "
                    "ON v.id = c.source_version_id WHERE substr(v.content_text, c.passage_start + 1, "
                    "char_length(c.passage)) <> c.passage"
                )
            )
        ).scalar_one()
    assert bad == 0


async def test_reviewer_owned_fields_and_reviewed_text_survive_a_rerun(owner: Database) -> None:
    await seed(owner)
    async with owner.unit_of_work() as session:
        await session.execute(
            text(
                "UPDATE app.projects SET public_status = 'in_progress', visibility = 'hidden' WHERE slug = 'gaba-tokulo-road'"
            )
        )
        await session.execute(
            text(
                "UPDATE app.project_translations SET title = 'Reviewed title', translation_status = 'reviewed', "
                "reviewed_at = now() WHERE project_id = (SELECT id FROM app.projects WHERE slug = 'gaba-tokulo-road')"
            )
        )
    await seed(owner, hour=16)
    async with owner.unit_of_work() as session:
        row = (
            await session.execute(
                text(
                    "SELECT public_status, visibility FROM app.projects WHERE slug = 'gaba-tokulo-road'"
                )
            )
        ).one()
        title = (
            await session.execute(
                text(
                    "SELECT title FROM app.project_translations t JOIN app.projects p ON p.id = t.project_id WHERE p.slug = 'gaba-tokulo-road'"
                )
            )
        ).scalar_one()
    assert (row.public_status, row.visibility) == ("in_progress", "hidden")
    assert title == "Reviewed title"


async def test_changed_evidence_adds_a_version_and_never_rewrites_history(owner: Database) -> None:
    await seed(owner)
    before = await snapshot(owner)
    changed = copy.deepcopy(load_register())
    extra = "An additional verified sentence for this test only."
    fact = changed["projects"][4]["facts"][1]
    fact["sources"][0]["passages"].append(
        {"text": extra, "sha256": hashlib.sha256(extra.encode()).hexdigest()}
    )
    await seed(owner, changed, hour=17)
    after = await snapshot(owner)
    old_ids = {row[0] for row in before["source_versions"]}
    kept = [row for row in after["source_versions"] if row[0] in old_ids]
    assert sorted(kept) == sorted(before["source_versions"]), "old versions are untouched"
    assert len(after["source_versions"]) == len(before["source_versions"]) + 1
    assert len(after["sources"]) == len(before["sources"]), "no source is duplicated"


async def test_an_invalid_register_writes_nothing(
    owner: Database,
    role_urls: dict[str, URL],
    tmp_path: Path,
) -> None:
    before = await snapshot(owner)
    broken = copy.deepcopy(load_register())
    broken["projects"][0]["fictional_reports"][0]["label"] = "demo"
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(broken), encoding="utf-8")
    environ = {
        "APP_ENV": "development",
        "DATABASE_URL": role_urls["owner"].render_as_string(hide_password=False),
    }
    with pytest.raises(RegisterInvalidError):
        await run(environ, path)
    assert await snapshot(owner) == before


async def test_seed_command_uses_keyword_fallback_without_a_provider_key(
    role_urls: dict[str, URL],
) -> None:
    output = await run(
        {
            "APP_ENV": "development",
            "DATABASE_URL": role_urls["owner"].render_as_string(hide_password=False),
            "OPENAI_EMBEDDING_MODEL": "no-checked-in-fixture",
        }
    )

    assert "chunks: inserted" in output
    assert "keyword fallback enabled" in output


async def test_the_command_refuses_production_and_remote_targets_before_touching_anything(
    role_urls: dict[str, URL],
) -> None:
    url = role_urls["owner"].render_as_string(hide_password=False)
    for env in (
        {"APP_ENV": "production", "DATABASE_URL": url},
        {"DATABASE_URL": url},
        {
            "APP_ENV": "development",
            "DATABASE_URL": url.replace("127.0.0.1", "db.example.com").replace(
                "localhost", "db.example.com"
            ),
        },
    ):
        with pytest.raises(SeedRefusedError):
            await run(env)


async def test_seeded_projects_are_visible_publicly_without_any_fact_or_citation(
    owner: Database, role_urls: dict[str, URL]
) -> None:
    await seed(owner)
    engine = build_engine(
        role_urls["shaidago_public"], application_name="pub", statement_timeout_ms=8000
    )
    try:
        app = create_app(build_settings(), Dependencies(public_database=Database(engine)))
        with TestClient(app, headers={"Authorization": f"Bearer web.{CREDENTIAL}"}) as client:
            listing = client.get("/v1/projects", params={"limit": "50"}).json()["items"]
            slugs = {i["slug"] for i in listing}
            detail = client.get("/v1/projects/bwari-township-water-supply-network").json()
            hausa = client.get(
                "/v1/projects/bwari-township-water-supply-network",
                headers={"X-Shaidago-Locale": "ha"},
            ).json()
            yoruba_only = client.get(
                "/v1/projects/saburi-i-and-ii-access-road", headers={"X-Shaidago-Locale": "yo"}
            ).json()
    finally:
        await engine.dispose()
    assert "bwari-township-water-supply-network" in slugs, slugs
    assert detail["facts"] == [], "unapproved evidence is not shown"
    assert detail["text"]["translation_status"] == "machine_assisted"
    assert (hausa["text"]["served_locale"], hausa["text"]["is_fallback"]) == ("ha", False)
    assert yoruba_only["text"]["is_fallback"] is True, (
        "a missing translation is labelled as English fallback"
    )

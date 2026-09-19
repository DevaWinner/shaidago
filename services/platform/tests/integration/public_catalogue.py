"""The seeded synthetic public catalogue shared by the public API and contract tests."""

import asyncio
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import URL

from shaidago.api.app import create_app
from shaidago.api.dependencies import Dependencies
from shaidago.shared.clock import ManualClock
from shaidago.shared.database import Database, build_engine
from shaidago.sources.publication import PublicationService
from tests.factories import CREDENTIAL, build_settings
from tests.integration.support import (
    NOW,
    Plain,
    insert_citation,
    insert_claim,
    insert_project,
    insert_source,
    insert_version,
)

PUBLISH_AT = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)


class Seed:
    """Slugs and IDs of the synthetic catalogue built once per module."""

    slugs: dict[str, str]
    sources: dict[str, uuid.UUID]
    facts: dict[str, uuid.UUID]


@pytest.fixture(scope="module")
def seed(role_urls: dict[str, URL]) -> Seed:
    result = Seed()

    async def build() -> None:
        engine = build_engine(
            role_urls["owner"], application_name="seed", statement_timeout_ms=20000
        )
        owner = Plain(engine)
        try:
            async with owner.unit_of_work() as session:
                slugs: dict[str, str] = {}
                for name, slug in (
                    ("alpha", "synthetic-alpha-clinic"),
                    ("beta", "synthetic-beta-school"),
                    ("gamma", "synthetic-gamma-borehole"),
                    ("delta", "synthetic-delta-hidden"),
                    ("epsilon", "synthetic-epsilon-road"),
                ):
                    slugs[name] = slug
                    await insert_project(session, slug)
                await session.execute(
                    text(
                        "INSERT INTO app.localities VALUES (gen_random_uuid(), 'synthetic-other', "
                        "'Synthetic Other', 'area_council', NULL, ARRAY['en'], :now, :now)"
                    ),
                    {"now": NOW},
                )
                for slug, category, status, day in (
                    ("synthetic-alpha-clinic", "health", "planned", 5),
                    ("synthetic-beta-school", "education", "in_progress", 4),
                    ("synthetic-gamma-borehole", "water_sanitation", "completed", 3),
                    ("synthetic-delta-hidden", "health", "planned", 2),
                    ("synthetic-epsilon-road", "roads_public_works", "unknown", 3),
                ):
                    await session.execute(
                        text(
                            "UPDATE app.projects SET category = :c, public_status = :s, "
                            "updated_at = make_timestamptz(2026, 9, :d, 9, 0, 0, 'UTC') "
                            "WHERE slug = :slug"
                        ),
                        {"c": category, "s": status, "d": day, "slug": slug},
                    )
                await session.execute(
                    text("UPDATE app.projects SET visibility = 'hidden' WHERE slug = :s"),
                    {"s": "synthetic-delta-hidden"},
                )
                await session.execute(
                    text(
                        "UPDATE app.projects SET locality_id = (SELECT id FROM app.localities "
                        "WHERE slug = 'synthetic-other') WHERE slug = 'synthetic-gamma-borehole'"
                    )
                )
                await session.execute(
                    text(
                        "UPDATE app.project_translations SET title = 'Alpha clinic', "
                        "summary = 'Rehabilitation of a synthetic clinic' "
                        "WHERE locale = 'en' AND project_id = (SELECT id FROM app.projects "
                        "WHERE slug = 'synthetic-alpha-clinic')"
                    )
                )
                await session.execute(
                    text(
                        "UPDATE app.project_translations SET title = 'Beta school', "
                        "summary = 'A synthetic classroom block' WHERE locale = 'en' AND project_id = "
                        "(SELECT id FROM app.projects WHERE slug = 'synthetic-beta-school')"
                    )
                )
                await session.execute(
                    text(
                        "INSERT INTO app.project_translations VALUES (gen_random_uuid(), "
                        "(SELECT id FROM app.projects WHERE slug = 'synthetic-alpha-clinic'), 'ha', "
                        "'Asibitin Alpha', 'Taƙaitaccen bayani na roba', 'Abin da aka yi alkawari', "
                        "'machine_assisted', NULL, NULL, :now, :now)"
                    ),
                    {"now": NOW},
                )
                official = await insert_source(session, information_class="official_source")
                official_version = await insert_version(session, official)
                media = await insert_source(
                    session, information_class="independent_source", publisher="Synthetic Press"
                )
                media_version = await insert_version(session, media)
                unrelated = await insert_source(session)
                await insert_version(session, unrelated)
                project_ids = {
                    slug: (
                        await session.execute(
                            text("SELECT id FROM app.projects WHERE slug = :s"), {"s": slug}
                        )
                    ).scalar_one()
                    for slug in slugs.values()
                }
                alpha = project_ids["synthetic-alpha-clinic"]
                beta = project_ids["synthetic-beta-school"]
                alpha_fact = await insert_claim(session, "fact", alpha)
                alpha_draft = await insert_claim(session, "fact", alpha)
                alpha_update = await insert_claim(session, "update", alpha)
                beta_fact = await insert_claim(session, "fact", beta)
                await insert_citation(session, "fact", alpha_fact, official_version)
                await insert_citation(session, "fact", alpha_draft, official_version, label="p9")
                await insert_citation(session, "update", alpha_update, official_version, label="p2")
                await insert_citation(session, "fact", beta_fact, media_version)
                result.slugs = slugs
                result.sources = {"official": official, "media": media, "unrelated": unrelated}
                result.facts = {"alpha": alpha_fact, "draft": alpha_draft, "beta": beta_fact}
            async with owner.unit_of_work() as session:
                service = PublicationService(session, ManualClock(PUBLISH_AT))
                await service.publish("fact", alpha_fact, verification_state="verified_official")
                await service.publish(
                    "update", alpha_update, verification_state="verified_official"
                )
                await service.publish("fact", beta_fact, verification_state="disputed")
        finally:
            await engine.dispose()

    asyncio.run(build())
    return result


AUTH = {"Authorization": f"Bearer web.{CREDENTIAL}"}


@pytest.fixture
def client(role_urls: dict[str, URL], seed: Seed) -> Iterator[TestClient]:
    del seed  # ensures the catalogue exists
    engine = build_engine(
        role_urls["shaidago_public"], application_name="api", statement_timeout_ms=8000
    )
    app = create_app(
        build_settings(),
        Dependencies(public_database=Database(engine), clock=ManualClock(PUBLISH_AT)),
    )
    with TestClient(app, headers=AUTH) as test_client:
        yield test_client

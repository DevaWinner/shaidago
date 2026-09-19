"""Synthetic-data builders shared by integration tests. Nothing here describes a real project."""

import hashlib
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

NOW = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
LOCALITY = uuid.UUID("018f0000-0000-7000-8000-0000000000aa")
DOCUMENT = "Synthetic document. The synthetic clinic opened on 1 March. Section two follows."


class Plain:
    """One transaction per block on an engine, with no error translation."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._sessions = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def unit_of_work(self) -> AsyncGenerator[AsyncSession]:
        async with self._sessions() as session, session.begin():
            yield session


async def insert_project(session: AsyncSession, slug: str | None = None) -> uuid.UUID:
    """A public synthetic project with English text. Slugs are unique so tests never collide."""
    project_id = uuid.uuid4()
    slug = slug or f"synthetic-{project_id.hex[:12]}"
    await session.execute(
        text(
            "INSERT INTO app.localities VALUES (:l, 'synthetic-council', 'Synthetic Council', "
            "'area_council', NULL, ARRAY['en'], :now, :now) ON CONFLICT DO NOTHING"
        ),
        {"l": LOCALITY, "now": NOW},
    )
    await session.execute(
        text(
            "INSERT INTO app.projects VALUES (:id, :slug, :l, 'health', 'planned', 'public', "
            "NULL, :now, :now)"
        ),
        {"id": project_id, "slug": slug, "l": LOCALITY, "now": NOW},
    )
    await session.execute(
        text(
            "INSERT INTO app.project_translations VALUES (gen_random_uuid(), :id, 'en', "
            "'synthetic title', 'synthetic summary', 'synthetic deliverable', 'reviewed', :now, "
            "NULL, :now, :now)"
        ),
        {"id": project_id, "now": NOW},
    )
    return project_id


async def insert_source(
    session: AsyncSession,
    *,
    publisher: str = "Synthetic Publisher",
    information_class: str = "official_source",
    url: str | None = None,
) -> uuid.UUID:
    source_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO app.sources VALUES (:id, :url, 'Synthetic source', :publisher, "
            "'government_publication', :cls, 'available', :now, :now, :now)"
        ),
        {
            "id": source_id,
            "url": url or f"https://synthetic.example/{source_id}",
            "publisher": publisher,
            "cls": information_class,
            "now": NOW,
        },
    )
    return source_id


def sha256_hex(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


async def insert_version(
    session: AsyncSession,
    source_id: uuid.UUID,
    *,
    content: str = DOCUMENT,
    state: str = "approved",
) -> uuid.UUID:
    version_id = uuid.uuid4()
    decided = state not in ("pending", "in_review")
    await session.execute(
        text(
            "INSERT INTO app.source_versions VALUES (:id, :s, :sha, :content, 'text/plain', :now, "
            ":state, :reviewed, NULL, :now)"
        ),
        {
            "id": version_id,
            "s": source_id,
            "sha": sha256_hex(content),
            "content": content,
            "now": NOW,
            "state": state,
            "reviewed": NOW if decided else None,
        },
    )
    return version_id


async def insert_claim(
    session: AsyncSession,
    kind: str,
    project_id: uuid.UUID,
    **overrides: Any,
) -> uuid.UUID:
    fields: dict[str, Any] = {
        "visibility": "draft",
        "state": "awaiting_verification",
        "effective": "2026-03-01",
        "checked": None,
        "published": None,
    } | overrides
    claim_id = uuid.uuid4()
    if kind == "fact":
        statement = text(
            "INSERT INTO app.project_facts VALUES (:id, :p, 'opening', 'synthetic statement', "
            "CAST(:eff AS date), CAST(:chk AS date), :state, :vis, :pub, :now, :now)"
        )
    else:
        statement = text(
            "INSERT INTO app.project_updates VALUES (:id, :p, 'synthetic update', "
            "CAST(:eff AS date), CAST(:chk AS date), :state, :vis, :pub, :now, :now)"
        )
    await session.execute(
        statement,
        {
            "id": claim_id,
            "p": project_id,
            "eff": fields["effective"],
            "chk": fields["checked"],
            "state": fields["state"],
            "vis": fields["visibility"],
            "pub": fields["published"],
            "now": NOW,
        },
    )
    return claim_id


async def insert_citation(
    session: AsyncSession,
    kind: str,
    claim_id: uuid.UUID,
    version_id: uuid.UUID,
    **overrides: str,
) -> None:
    passage = overrides.get("passage", "The synthetic clinic opened on 1 March.")
    label = overrides.get("label", "section 1")
    start = DOCUMENT.index(passage) if passage in DOCUMENT else 0
    table, column = (
        ("fact_citations", "fact_id") if kind == "fact" else ("update_citations", "update_id")
    )
    await session.execute(
        text(
            f"INSERT INTO app.{table} (id, {column}, source_version_id, passage, location_label, "
            "passage_start, created_at) VALUES (gen_random_uuid(), :c, :v, :p, :l, :s, :now)"
        ),
        {"c": claim_id, "v": version_id, "p": passage, "l": label, "s": start, "now": NOW},
    )

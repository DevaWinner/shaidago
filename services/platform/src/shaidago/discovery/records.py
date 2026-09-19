"""Recording discovered sources: deduplicate within one scope and keep every sighting.

Deduplication never crosses scopes: a report-scoped run's findings are compared only with that
report's own, so a private discovery cannot be revealed (or merged) through a public run. A
duplicate is kept with a pointer to the source it repeats, and every run that finds a source
leaves a sighting.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.discovery.dedupe import NEAR_DUPLICATE_DISTANCE
from shaidago.discovery.extract import ExtractedPage
from shaidago.shared.ids import IdGenerator

Kind = Literal["new", "same_url", "same_content", "near_duplicate"]

_BY_URL = text(
    "SELECT id FROM app.discovered_sources WHERE COALESCE(report_id, project_id) = :scope_key "
    "AND scope = :scope AND canonical_url = :url"
)
_BY_HASH = text(
    "SELECT id FROM app.discovered_sources WHERE COALESCE(report_id, project_id) = :scope_key "
    "AND scope = :scope AND text_sha256 = :sha "
    "AND duplicate_of IS NULL ORDER BY first_discovered_at, id LIMIT 1"
)
_NEAR = text(
    "SELECT id FROM app.discovered_sources WHERE COALESCE(report_id, project_id) = :scope_key "
    "AND scope = :scope AND duplicate_of IS NULL "
    "AND bit_count(CAST(simhash # :hash AS bit(64))) <= :distance "
    "ORDER BY bit_count(CAST(simhash # :hash AS bit(64))), first_discovered_at, id LIMIT 1"
)
_INSERT = text(
    "INSERT INTO app.discovered_sources (id, scope, project_id, report_id, canonical_url, "
    "publisher_domain, title, preliminary_type, published_on, published_provenance, "
    "date_conflict, content_type, excerpt, text_sha256, simhash, extraction_version, "
    "injection_flag, duplicate_of, duplicate_kind, availability, first_discovered_at, "
    "last_retrieved_at, created_at, updated_at) VALUES (:id, :scope, :project, :report, :url, "
    ":domain, :title, :ptype, :published, :provenance, :conflict, :ctype, :excerpt, :sha, :hash, "
    ":version, :injection, :dup, :dup_kind, 'available', :now, :now, :now, :now)"
)
_REFRESH = text(
    "UPDATE app.discovered_sources SET last_retrieved_at = :now, availability = 'available', "
    "updated_at = :now WHERE id = :id"
)
_SIGHTING = text(
    "INSERT INTO app.discovered_source_sightings (id, discovered_source_id, run_id, "
    "discovered_at, retrieved_at) VALUES (:id, :source, :run, :now, :now) "
    "ON CONFLICT (discovered_source_id, run_id) DO NOTHING"
)


@dataclass(frozen=True)
class Scope:
    scope: Literal["public", "report"]
    project_id: UUID
    report_id: UUID | None = None

    @property
    def key(self) -> UUID:
        return self.report_id if self.report_id is not None else self.project_id


@dataclass(frozen=True)
class Recorded:
    source_id: UUID
    kind: Kind
    duplicate_of: UUID | None


class SourceRecorder:
    def __init__(self, session: AsyncSession, ids: IdGenerator) -> None:
        self._session = session
        self._ids = ids

    async def record(
        self, scope: Scope, run_id: UUID, page: ExtractedPage, now: datetime
    ) -> Recorded:
        """Store or refresh one discovered source and leave a sighting for this run."""
        where = {"scope_key": scope.key, "scope": scope.scope}
        found = (
            await self._session.execute(_BY_URL, where | {"url": page.canonical_url})
        ).one_or_none()
        if found is not None:
            await self._session.execute(_REFRESH, {"id": found.id, "now": now})
            await self._sight(found.id, run_id, now)
            return Recorded(found.id, "same_url", None)
        kind: Kind = "new"
        original: UUID | None = None
        same = (
            await self._session.execute(_BY_HASH, where | {"sha": page.text_sha256})
        ).one_or_none()
        if same is not None:
            kind, original = "same_content", same.id
        else:
            near = (
                await self._session.execute(
                    _NEAR, where | {"hash": page.simhash, "distance": NEAR_DUPLICATE_DISTANCE}
                )
            ).one_or_none()
            if near is not None:
                kind, original = "near_duplicate", near.id
        source_id = self._ids.new()
        await self._session.execute(
            _INSERT,
            where
            | {
                "id": source_id,
                "project": scope.project_id,
                "report": scope.report_id,
                "url": page.canonical_url,
                "domain": page.publisher_domain,
                "title": page.title,
                "ptype": page.preliminary_type,
                "published": page.published_on,
                "provenance": page.published_provenance,
                "conflict": page.date_conflict,
                "ctype": page.content_type,
                "excerpt": page.excerpt,
                "sha": page.text_sha256,
                "hash": page.simhash,
                "version": page.extraction_version,
                "injection": page.injection_flag,
                "dup": original,
                "dup_kind": None if original is None else kind,
                "now": now,
            },
        )
        await self._sight(source_id, run_id, now)
        return Recorded(source_id, kind, original)

    async def _sight(self, source_id: UUID, run_id: UUID, now: datetime) -> None:
        await self._session.execute(
            _SIGHTING, {"id": self._ids.new(), "source": source_id, "run": run_id, "now": now}
        )

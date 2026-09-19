"""Read-only public catalogue queries over the ``public_api`` views.

Every statement is a fixed string with bound parameters. Ordering is total: ``updated_at`` then
``id``, both descending, so cursors never skip or repeat a project.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Row, text
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.projects.models import SOURCE_LOCALE, Locale

MAX_QUERY_CHARS = 100

LIST_PROJECTS_SQL = text(
    """
    SELECT p.id, p.slug, p.locality_slug, p.category, p.public_status, p.last_checked_on,
           p.updated_at,
           COALESCE(tl.title, te.title) AS title,
           COALESCE(tl.summary, te.summary) AS summary,
           COALESCE(tl.locale, te.locale) AS served_locale,
           COALESCE(tl.translation_status, te.translation_status) AS translation_status
    FROM public_api.projects p
    JOIN public_api.project_translations te ON te.project_id = p.id AND te.locale = 'en'
    LEFT JOIN public_api.project_translations tl
           ON tl.project_id = p.id AND tl.locale = :locale AND :locale <> 'en'
    WHERE (CAST(:locality AS text) IS NULL OR p.locality_slug = :locality)
      AND (CAST(:category AS text) IS NULL OR p.category = :category)
      AND (CAST(:status AS text) IS NULL OR p.public_status = :status)
      AND (CAST(:verification AS text) IS NULL OR EXISTS (
            SELECT 1 FROM public_api.project_facts f
            WHERE f.project_slug = p.slug AND f.verification_state = :verification))
      AND (CAST(:q AS text) IS NULL OR EXISTS (
            SELECT 1 FROM public_api.project_translations st
            WHERE st.project_id = p.id AND st.locale IN (:locale, 'en')
              AND to_tsvector('simple', st.title || ' ' || st.summary)
                  @@ plainto_tsquery('simple', :q)))
      AND (CAST(:after_updated AS timestamptz) IS NULL
           OR (p.updated_at, p.id) < (CAST(:after_updated AS timestamptz), CAST(:after_id AS uuid)))
    ORDER BY p.updated_at DESC, p.id DESC
    LIMIT :limit
    """
)
_PROJECT = text(
    "SELECT id, slug, locality_slug, category, public_status, last_checked_on, updated_at "
    "FROM public_api.projects WHERE slug = :slug"
)
_TEXT = text(
    "SELECT locale, title, summary, promised_deliverable, translation_status, reviewed_at "
    "FROM public_api.project_translations WHERE project_id = :id AND locale = ANY(:locales)"
)
_FACTS = text(
    "SELECT id, kind, statement, effective_on, last_checked_on, verification_state "
    "FROM public_api.project_facts WHERE project_slug = :slug "
    "ORDER BY effective_on DESC NULLS LAST, id"
)
_UPDATES = text(
    "SELECT id, statement, effective_on, last_checked_on, verification_state "
    "FROM public_api.project_updates WHERE project_slug = :slug "
    "ORDER BY effective_on DESC NULLS LAST, id"
)
_FACT_CITATIONS = text(
    "SELECT c.fact_id AS item_id, c.source_version_id, c.source_id, c.source_title, c.publisher, "
    "c.canonical_url, "
    "c.source_type, c.information_class, c.retrieved_at, c.passage, c.location_label "
    "FROM public_api.fact_citations c JOIN public_api.project_facts f ON f.id = c.fact_id "
    "WHERE f.project_slug = :slug ORDER BY c.location_label, c.source_id"
)
_UPDATE_CITATIONS = text(
    "SELECT c.update_id AS item_id, c.source_version_id, c.source_id, c.source_title, c.publisher, "
    "c.canonical_url, "
    "c.source_type, c.information_class, c.retrieved_at, c.passage, c.location_label "
    "FROM public_api.update_citations c JOIN public_api.project_updates u ON u.id = c.update_id "
    "WHERE u.project_slug = :slug ORDER BY c.location_label, c.source_id"
)
_SOURCE = text(
    "SELECT id, canonical_url, title, publisher, source_type, information_class, availability, "
    "availability_checked_at FROM public_api.cited_sources WHERE id = :id"
)
_EXCERPTS = text(
    "SELECT 'fact' AS cited_by, c.fact_id AS item_id, c.passage, c.location_label "
    "FROM public_api.fact_citations c JOIN public_api.project_facts f ON f.id = c.fact_id "
    "WHERE f.project_slug = :slug AND c.source_id = :id "
    "UNION ALL "
    "SELECT 'update', c.update_id, c.passage, c.location_label "
    "FROM public_api.update_citations c JOIN public_api.project_updates u ON u.id = c.update_id "
    "WHERE u.project_slug = :slug AND c.source_id = :id "
    "ORDER BY 1, 4, 2"
)

_CLASS_STRENGTH = {"official_source": 0, "independent_source": 1, "community_evidence_reviewed": 2}


@dataclass(frozen=True)
class ListFilters:
    locality: str | None = None
    category: str | None = None
    status: str | None = None
    verification: str | None = None
    query: str | None = None


@dataclass(frozen=True)
class Cited:
    """A published fact or update with its citations, ready for the public DTO."""

    row: Row[Any]
    citations: list[Row[Any]]

    @property
    def information_class(self) -> str:
        """The strongest class among its citations (official, then independent, then reviewed)."""
        return min(
            (c.information_class for c in self.citations),
            key=lambda value: _CLASS_STRENGTH.get(value, len(_CLASS_STRENGTH)),
        )


@dataclass(frozen=True)
class ProjectDetail:
    project: Row[Any]
    text: Row[Any]
    requested_locale: Locale
    facts: list[Cited]
    updates: list[Cited]


@dataclass(frozen=True)
class SourceView:
    source: Row[Any]
    excerpts: list[Row[Any]]


class PublicCatalogue:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def localities(self) -> list[Row[Any]]:
        return list(
            (
                await self._session.execute(
                    text(
                        "SELECT slug, name, kind, parent_slug, enabled_locales "
                        "FROM public_api.localities ORDER BY name, slug"
                    )
                )
            ).all()
        )

    async def list_projects(
        self,
        filters: ListFilters,
        locale: Locale,
        limit: int,
        after: tuple[datetime, UUID] | None,
    ) -> list[Row[Any]]:
        """Up to ``limit`` rows in the total order; callers fetch ``limit + 1`` for paging."""
        return list(
            (
                await self._session.execute(
                    LIST_PROJECTS_SQL,
                    {
                        "locale": locale,
                        "locality": filters.locality,
                        "category": filters.category,
                        "status": filters.status,
                        "verification": filters.verification,
                        "q": filters.query,
                        "after_updated": after[0] if after else None,
                        "after_id": after[1] if after else None,
                        "limit": limit,
                    },
                )
            ).all()
        )

    async def project(self, slug: str, locale: Locale) -> ProjectDetail | None:
        project = (await self._session.execute(_PROJECT, {"slug": slug})).one_or_none()
        if project is None:
            return None
        texts = {
            row.locale: row
            for row in (
                await self._session.execute(
                    _TEXT, {"id": project.id, "locales": [locale, SOURCE_LOCALE]}
                )
            ).all()
        }
        served = texts.get(locale) or texts.get(SOURCE_LOCALE)
        if served is None:
            return None
        facts = await self._cited(slug, _FACTS, _FACT_CITATIONS)
        updates = await self._cited(slug, _UPDATES, _UPDATE_CITATIONS)
        return ProjectDetail(
            project=project, text=served, requested_locale=locale, facts=facts, updates=updates
        )

    async def _cited(self, slug: str, items_sql: Any, citations_sql: Any) -> list[Cited]:
        items = (await self._session.execute(items_sql, {"slug": slug})).all()
        by_item: dict[UUID, list[Row[Any]]] = {}
        for citation in (await self._session.execute(citations_sql, {"slug": slug})).all():
            by_item.setdefault(citation.item_id, []).append(citation)
        # An item without a visible citation cannot be shown, whatever the database says.
        return [Cited(row, by_item[row.id]) for row in items if by_item.get(row.id)]

    async def source(self, slug: str, source_id: UUID) -> SourceView | None:
        """Source metadata and only the passages this project cites from it."""
        excerpts = (await self._session.execute(_EXCERPTS, {"slug": slug, "id": source_id})).all()
        if not excerpts:
            return None
        source = (await self._session.execute(_SOURCE, {"id": source_id})).one_or_none()
        if source is None:
            return None
        return SourceView(source=source, excerpts=list(excerpts))


__all__ = [
    "MAX_QUERY_CHARS",
    "Cited",
    "ListFilters",
    "ProjectDetail",
    "PublicCatalogue",
    "SourceView",
]

"""Public reads of localities and projects, through the ``public_api`` views only."""

from typing import cast, get_args
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.projects.models import (
    SOURCE_LOCALE,
    Locale,
    LocalityKind,
    LocalitySummary,
    ProjectCategory,
    PublicProject,
    PublicStatus,
    ServedText,
    TranslationStatus,
)

_LOCALITIES = text(
    "SELECT slug, name, kind, parent_slug, enabled_locales FROM public_api.localities "
    "ORDER BY name, slug"
)
_PROJECT = text(
    "SELECT id, slug, locality_slug, category, public_status, last_checked_on, updated_at "
    "FROM public_api.projects WHERE slug = :slug"
)
_PROJECT_ID = text("SELECT id FROM public_api.projects WHERE slug = :slug")
_TEXT = text(
    "SELECT locale, title, summary, promised_deliverable, translation_status, reviewed_at "
    "FROM public_api.project_translations WHERE project_id = :project_id AND locale = ANY(:locales)"
)
_KNOWN_LOCALES = set(get_args(Locale))


class PublicProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_localities(self) -> list[LocalitySummary]:
        rows = (await self._session.execute(_LOCALITIES)).all()
        return [
            LocalitySummary(
                slug=row.slug,
                name=row.name,
                kind=cast("LocalityKind", row.kind),
                parent_slug=row.parent_slug,
                enabled_locales=tuple(
                    cast("Locale", code) for code in row.enabled_locales if code in _KNOWN_LOCALES
                ),
            )
            for row in rows
        ]

    async def resolve_project_id(self, slug: str) -> UUID | None:
        """The internal ID of a public project, for a private report to reference."""
        row = (await self._session.execute(_PROJECT_ID, {"slug": slug})).one_or_none()
        return None if row is None else UUID(str(row.id))

    async def get_project(self, slug: str, locale: Locale) -> PublicProject | None:
        """The public project in ``locale``; absent, hidden, or untranslatable gives ``None``."""
        project = (await self._session.execute(_PROJECT, {"slug": slug})).one_or_none()
        if project is None:
            return None
        texts = {
            row.locale: row
            for row in (
                await self._session.execute(
                    _TEXT, {"project_id": project.id, "locales": [locale, SOURCE_LOCALE]}
                )
            ).all()
        }
        served = texts.get(locale) or texts.get(SOURCE_LOCALE)
        if served is None:
            return None
        return PublicProject(
            slug=project.slug,
            locality_slug=project.locality_slug,
            category=cast("ProjectCategory", project.category),
            public_status=cast("PublicStatus", project.public_status),
            last_checked_on=project.last_checked_on,
            updated_at=project.updated_at,
            text=ServedText(
                requested_locale=locale,
                served_locale=cast("Locale", served.locale),
                title=served.title,
                summary=served.summary,
                promised_deliverable=served.promised_deliverable,
                translation_status=cast("TranslationStatus", served.translation_status),
                reviewed_at=served.reviewed_at,
            ),
        )

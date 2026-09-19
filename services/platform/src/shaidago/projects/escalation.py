"""Public escalation guidance: cited, dated, locale-honest, and never an invented contact."""

from dataclasses import dataclass
from datetime import date
from typing import Any, Literal, cast

from sqlalchemy import Row, text
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.projects.models import SOURCE_LOCALE, Locale

ConcernCategory = Literal[
    "no_visible_work",
    "incomplete_work",
    "unsafe_construction",
    "suspected_incorrect_status",
    "access_barrier",
    "other_concern",
]

_ROUTES = text(
    "SELECT concern_category, locale, organisation, instructions, disclaimer, verified_on, "
    "valid_from, valid_to, source_title, source_publisher, source_url "
    "FROM public_api.escalation_routes "
    "WHERE locality_slug = :locality AND locale = ANY(:locales) "
    "AND (concern_category IS NULL OR concern_category = :category) "
    "AND valid_from <= :today AND (valid_to IS NULL OR valid_to >= :today) "
    "ORDER BY (concern_category IS NULL), organisation"
)


@dataclass(frozen=True)
class EscalationRoute:
    organisation: str
    instructions: str
    disclaimer: str
    concern_category: ConcernCategory | None
    requested_locale: Locale
    served_locale: Locale
    verified_on: date
    valid_from: date
    valid_to: date | None
    source_title: str
    source_publisher: str
    source_url: str

    @property
    def is_fallback(self) -> bool:
        return self.requested_locale != self.served_locale


class EscalationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def routes_for(
        self, locality_slug: str, category: ConcernCategory, locale: Locale, *, today: date
    ) -> list[EscalationRoute]:
        """Routes valid on ``today``, most specific category first.

        For each organisation the requested locale wins; otherwise the English text is served
        and flagged as a fallback. An empty list means no verified route exists, and the caller
        must say so rather than supply a default contact.
        """
        rows = (
            await self._session.execute(
                _ROUTES,
                {
                    "locality": locality_slug,
                    "locales": [locale, SOURCE_LOCALE],
                    "category": category,
                    "today": today,
                },
            )
        ).all()
        chosen: dict[tuple[str | None, str], Row[Any]] = {}
        for row in rows:
            key = (row.concern_category, row.organisation)
            current = chosen.get(key)
            if current is None or (row.locale == locale and current.locale != locale):
                chosen[key] = row
        return [
            EscalationRoute(
                organisation=row.organisation,
                instructions=row.instructions,
                disclaimer=row.disclaimer,
                concern_category=cast("ConcernCategory | None", row.concern_category),
                requested_locale=locale,
                served_locale=cast("Locale", row.locale),
                verified_on=row.verified_on,
                valid_from=row.valid_from,
                valid_to=row.valid_to,
                source_title=row.source_title,
                source_publisher=row.source_publisher,
                source_url=row.source_url,
            )
            for row in chosen.values()
        ]

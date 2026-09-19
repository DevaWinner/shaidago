"""Public-safe projections of localities and projects.

These are frozen values returned by repositories instead of ORM rows. The Literal types mirror
``contracts/controlled-vocabulary.json``; ``tests/unit/projects/test_vocabulary_parity.py``
fails if they drift.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

Locale = Literal["en", "ha", "ig", "yo"]
LocalityKind = Literal["state", "area_council"]
ProjectCategory = Literal[
    "health", "education", "water_sanitation", "roads_public_works", "other_public_service"
]
PublicStatus = Literal[
    "unknown", "planned", "procurement", "in_progress", "on_hold", "completed", "cancelled"
]
TranslationStatus = Literal["reviewed", "machine_assisted", "unavailable"]

SOURCE_LOCALE: Locale = "en"
LOCALES: tuple[Locale, ...] = ("en", "ha", "ig", "yo")


@dataclass(frozen=True)
class LocalitySummary:
    slug: str
    name: str
    kind: LocalityKind
    parent_slug: str | None
    enabled_locales: tuple[Locale, ...]


@dataclass(frozen=True)
class ServedText:
    """Project text as served, with an honest account of which locale it really is."""

    requested_locale: Locale
    served_locale: Locale
    title: str
    summary: str
    promised_deliverable: str
    translation_status: TranslationStatus
    reviewed_at: datetime | None

    @property
    def is_fallback(self) -> bool:
        """True when the requested locale had no text and the source locale is shown instead."""
        return self.requested_locale != self.served_locale


@dataclass(frozen=True)
class PublicProject:
    slug: str
    locality_slug: str
    category: ProjectCategory
    public_status: PublicStatus
    last_checked_on: date | None
    updated_at: datetime
    text: ServedText

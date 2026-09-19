"""Public trust metadata: how each displayed item should be labelled.

The API returns these values so every client shows the same distinction between a supported
fact, a source's reported claim, an AI explanation, and an unknown. AI output is never an
independent source (AGENTS.md), so the AI label is a separate flag that no verification state
can clear.
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal

InformationClass = Literal[
    "official_source",
    "independent_source",
    "community_evidence_reviewed",
    "ai_generated_explanation",
]
PUBLIC_CLASSES: frozenset[str] = frozenset(
    {"official_source", "independent_source", "community_evidence_reviewed"}
)


@dataclass(frozen=True)
class TrustMetadata:
    information_class: InformationClass
    verification_state: str | None
    effective_on: date | None
    last_checked_on: date | None
    translation_status: str | None
    ai_generated: bool

    @property
    def has_visible_date(self) -> bool:
        return self.effective_on is not None or self.last_checked_on is not None


def for_cited_item(
    information_class: str,
    *,
    verification_state: str,
    effective_on: date | None,
    last_checked_on: date | None,
    translation_status: str | None = None,
) -> TrustMetadata:
    """Trust labels for a fact or update that passed publication (so it has citations)."""
    if information_class not in PUBLIC_CLASSES:
        raise ValueError("only public source classes may label a cited item")
    return TrustMetadata(
        information_class=information_class,  # type: ignore[arg-type]  # narrowed by the check above
        verification_state=verification_state,
        effective_on=effective_on,
        last_checked_on=last_checked_on,
        translation_status=translation_status,
        ai_generated=False,
    )


def for_ai_explanation(*, translation_status: str | None = None) -> TrustMetadata:
    """Labels for generated text: never verified, never independent, always flagged."""
    return TrustMetadata(
        information_class="ai_generated_explanation",
        verification_state=None,
        effective_on=None,
        last_checked_on=None,
        translation_status=translation_status,
        ai_generated=True,
    )

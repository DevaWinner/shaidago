"""Publishing a fact or update: every requirement is checked, then applied, in one transaction.

Publication is a separate human act (AGENTS.md): this service never runs from a status change,
a worker, or AI output. The database re-checks the same core rules at commit (revision 0004), so
this service adds the verification-state rules that need cross-row reasoning and reports gaps
as stable codes without leaking any content.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import TextClause, text
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.shared.clock import Clock
from shaidago.shared.problems import NOT_FOUND, PUBLICATION_INCOMPLETE, FieldError, ProblemError

ClaimKind = Literal["fact", "update"]
_CITABLE = frozenset({"approved", "superseded"})


@dataclass(frozen=True)
class _Statements:
    """Literal SQL for one kind of claim, so no statement is assembled from variables."""

    lock: TextClause
    citations: TextClause
    publish: TextClause


_STATEMENTS: dict[ClaimKind, _Statements] = {
    "fact": _Statements(
        lock=text(
            "SELECT effective_on, last_checked_on FROM app.project_facts WHERE id = :id FOR UPDATE"
        ),
        citations=text(
            "SELECT s.id AS source_id, s.publisher, s.information_class, v.review_state "
            "FROM app.fact_citations ci JOIN app.source_versions v ON v.id = ci.source_version_id "
            "JOIN app.sources s ON s.id = v.source_id WHERE ci.fact_id = :id"
        ),
        publish=text(
            "UPDATE app.project_facts SET visibility = 'public', published_at = :now, "
            "verification_state = :state, updated_at = :now WHERE id = :id"
        ),
    ),
    "update": _Statements(
        lock=text(
            "SELECT effective_on, last_checked_on FROM app.project_updates "
            "WHERE id = :id FOR UPDATE"
        ),
        citations=text(
            "SELECT s.id AS source_id, s.publisher, s.information_class, v.review_state "
            "FROM app.update_citations ci "
            "JOIN app.source_versions v ON v.id = ci.source_version_id "
            "JOIN app.sources s ON s.id = v.source_id WHERE ci.update_id = :id"
        ),
        publish=text(
            "UPDATE app.project_updates SET visibility = 'public', published_at = :now, "
            "verification_state = :state, updated_at = :now WHERE id = :id"
        ),
    ),
}


@dataclass(frozen=True)
class PublishedClaim:
    claim_id: UUID
    published_at: datetime


@dataclass(frozen=True)
class Citation:
    source_id: UUID
    publisher: str
    information_class: str
    review_state: str


def publication_gaps(
    *,
    verification_state: str,
    citations: Sequence[Citation],
    effective_on: date | None,
    last_checked_on: date | None,
) -> list[FieldError]:
    """Every unmet requirement as ``FieldError(field, stable_code)``; empty means publishable."""
    gaps: list[FieldError] = []
    eligible = [c for c in citations if c.review_state in _CITABLE]
    if not eligible:
        gaps.append(FieldError("citations", "approved_citation_required"))
    if effective_on is None and last_checked_on is None:
        gaps.append(FieldError("dates", "visible_date_required"))
    if verification_state == "awaiting_verification":
        gaps.append(FieldError("verification_state", "verification_required"))
    if verification_state == "verified_official" and not any(
        c.information_class == "official_source" for c in eligible
    ):
        gaps.append(FieldError("verification_state", "official_source_required"))
    if verification_state == "corroborated" and (
        len({c.source_id for c in eligible}) < 2 or len({c.publisher for c in eligible}) < 2  # noqa: PLR2004 - "at least two"
    ):
        gaps.append(FieldError("verification_state", "independent_sources_required"))
    if verification_state == "community_reviewed" and not any(
        c.information_class == "community_evidence_reviewed" for c in eligible
    ):
        gaps.append(FieldError("verification_state", "reviewed_community_evidence_required"))
    return gaps


class PublicationService:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    async def publish(
        self, kind: ClaimKind, claim_id: UUID, *, verification_state: str
    ) -> PublishedClaim:
        """Publish, or raise ``publication_incomplete`` naming each gap; nothing is half-applied."""
        statements = _STATEMENTS[kind]
        claim = (await self._session.execute(statements.lock, {"id": claim_id})).one_or_none()
        if claim is None:
            raise ProblemError(NOT_FOUND)
        rows = (await self._session.execute(statements.citations, {"id": claim_id})).all()
        citations = [
            Citation(r.source_id, r.publisher, r.information_class, r.review_state) for r in rows
        ]
        gaps = publication_gaps(
            verification_state=verification_state,
            citations=citations,
            effective_on=claim.effective_on,
            last_checked_on=claim.last_checked_on,
        )
        if gaps:
            raise ProblemError(PUBLICATION_INCOMPLETE, field_errors=gaps)
        now = self._clock.now()
        await self._session.execute(
            statements.publish, {"now": now, "state": verification_state, "id": claim_id}
        )
        return PublishedClaim(claim_id=claim_id, published_at=now)

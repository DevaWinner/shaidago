"""The reviewer queue: the fields needed to triage a report before opening it, and no more.

A row carries no report text, contact, handle, or evidence detail: only category, risk, status,
timing, the public project slug, and three counts or flags. It is one statement whatever the page
size, ordered oldest first by an immutable timestamp so a report never moves while being worked.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_QUEUE = text(
    "SELECT r.id, r.created_at, r.status, r.status_updated_at, r.concern_category, "
    "r.risk_level, r.version, p.slug AS project_slug, (NOT r.anonymous) AS has_contact, "
    "(SELECT count(*) FROM app.evidence_files e WHERE e.report_id = r.id) AS evidence_count, "
    "(SELECT count(*) FROM app.report_follow_up_questions q WHERE q.report_id = r.id "
    " AND q.withdrawn_at IS NULL AND NOT EXISTS ("
    "  SELECT 1 FROM app.report_follow_up_answers a WHERE a.question_id = q.id)) "
    "AS open_follow_ups "
    "FROM app.reports r JOIN app.projects p ON p.id = r.project_id "
    "WHERE (CAST(:no_status AS boolean) OR r.status = ANY(CAST(:statuses AS text[]))) "
    "AND (CAST(:risk AS text) IS NULL OR r.risk_level = :risk) "
    "AND (CAST(:category AS text) IS NULL OR r.concern_category = :category) "
    "AND (CAST(:project AS text) IS NULL OR p.slug = :project) "
    "AND (CAST(:after_at AS timestamptz) IS NULL "
    " OR (r.created_at, r.id) > (CAST(:after_at AS timestamptz), CAST(:after_id AS uuid))) "
    "ORDER BY r.created_at ASC, r.id ASC LIMIT :limit"
)


@dataclass(frozen=True)
class QueueFilters:
    statuses: tuple[str, ...] = ()
    risk_level: str | None = None
    concern_category: str | None = None
    project_slug: str | None = None


@dataclass(frozen=True)
class QueueRow:
    id: UUID
    created_at: datetime
    status: str
    status_updated_at: datetime
    concern_category: str
    risk_level: str
    version: int
    project_slug: str
    has_contact: bool
    evidence_count: int
    open_follow_ups: int


async def list_queue(
    session: AsyncSession,
    filters: QueueFilters,
    limit: int,
    after: tuple[datetime, UUID] | None,
) -> list[QueueRow]:
    rows = (
        await session.execute(
            _QUEUE,
            {
                "no_status": not filters.statuses,
                "statuses": list(filters.statuses),
                "risk": filters.risk_level,
                "category": filters.concern_category,
                "project": filters.project_slug,
                "after_at": after[0] if after else None,
                "after_id": after[1] if after else None,
                "limit": limit,
            },
        )
    ).all()
    return [
        QueueRow(
            id=r.id,
            created_at=r.created_at,
            status=r.status,
            status_updated_at=r.status_updated_at,
            concern_category=r.concern_category,
            risk_level=r.risk_level,
            version=r.version,
            project_slug=r.project_slug,
            has_contact=bool(r.has_contact),
            evidence_count=int(r.evidence_count),
            open_follow_ups=int(r.open_follow_ups),
        )
        for r in rows
    ]

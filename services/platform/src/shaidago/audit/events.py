"""Append-only audit events. Details are redacted before they are stored.

Events record who did what to which subject, with a request ID for correlation. They never carry
passwords, tokens, tracking codes, report text, or contacts: the writer runs every detail value
through the central redactor as a second line of defence, and callers pass identifiers only.
"""

import json
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.shared.clock import Clock
from shaidago.shared.ids import IdGenerator
from shaidago.shared.logging import redact

ActorType = Literal["system", "worker", "reviewer", "admin", "reporter"]
Outcome = Literal["success", "failure", "denied"]

_INSERT = text(
    "INSERT INTO app.audit_events (id, occurred_at, actor_type, actor_id, event, subject_type, "
    "subject_id, outcome, request_id, details) VALUES (:id, :at, :actor_type, :actor_id, :event, "
    ":subject_type, :subject_id, :outcome, :request_id, :details)"
).bindparams(bindparam("details", type_=JSONB))


class AuditWriter:
    def __init__(self, session: AsyncSession, clock: Clock, ids: IdGenerator) -> None:
        self._session = session
        self._clock = clock
        self._ids = ids

    async def record(  # noqa: PLR0913 - the audit vocabulary is inherently wide
        self,
        event: str,
        *,
        actor_type: ActorType,
        actor_id: UUID | None = None,
        subject_type: str | None = None,
        subject_id: UUID | None = None,
        outcome: Outcome = "success",
        request_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> UUID:
        event_id = self._ids.new()
        safe_details = json.loads(json.dumps(redact(details or {}), default=str))
        await self._session.execute(
            _INSERT,
            {
                "id": event_id,
                "at": self._clock.now(),
                "actor_type": actor_type,
                "actor_id": actor_id,
                "event": event,
                "subject_type": subject_type,
                "subject_id": subject_id,
                "outcome": outcome,
                "request_id": request_id,
                "details": safe_details,
            },
        )
        return event_id

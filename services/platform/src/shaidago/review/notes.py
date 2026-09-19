"""Encrypted, append-only reviewer notes.

A note is plain text (markup is refused, so it can never be rendered as HTML), encrypted under its
own data key before it reaches the database, and readable only through the reviewer routes. Audit
records the note's ID and author, never its content. A correction is a new note.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Final
from uuid import UUID

from sqlalchemy import LargeBinary, bindparam, text

from shaidago.audit.events import AuditWriter
from shaidago.review.context import ReviewContext
from shaidago.review.detail import Reviewer
from shaidago.shared.crypto import DataKey, DecryptionError, field_context
from shaidago.shared.problems import NOT_FOUND, VALIDATION_FAILED, FieldError, ProblemError

SCHEMA_VERSION: Final = 1
OWNER_TABLE: Final = "report_notes"
MAX_CHARS: Final = 4000
# A tag-like sequence: notes are text, not markup.
_MARKUP: Final = re.compile(r"<\s*[/!?a-zA-Z]")

_EXISTS = text("SELECT 1 FROM app.reports WHERE id = :id")
_INSERT = text(
    "INSERT INTO app.report_notes (id, report_id, author_id, body_ciphertext, data_key_id, "
    "schema_version, created_at) VALUES (:id, :report, :author, :body, :key, :version, :at)"
).bindparams(bindparam("body", type_=LargeBinary))
_PAGE = text(
    "SELECT n.id, n.created_at, n.body_ciphertext, n.data_key_id, n.schema_version, "
    "rv.identifier AS author "
    "FROM app.report_notes n LEFT JOIN app.reviewers rv ON rv.id = n.author_id "
    "WHERE n.report_id = :report "
    "AND (CAST(:after_at AS timestamptz) IS NULL "
    " OR (n.created_at, n.id) > (CAST(:after_at AS timestamptz), CAST(:after_id AS uuid))) "
    "ORDER BY n.created_at ASC, n.id ASC LIMIT :limit"
)


@dataclass(frozen=True)
class NoteView:
    id: UUID
    created_at: datetime
    author: str | None
    body: str | None

    def __repr__(self) -> str:
        return f"NoteView(id={self.id})"


def validated_body(body: str) -> str:
    cleaned = body.strip()
    problem = None
    if not cleaned or len(cleaned) > MAX_CHARS:
        problem = "length"
    elif any(c < " " and c not in "\n\t" for c in cleaned) or "\x7f" in cleaned:
        problem = "invalid_text"
    elif _MARKUP.search(cleaned):
        problem = "markup_not_allowed"
    if problem is not None:
        raise ProblemError(VALIDATION_FAILED, field_errors=[FieldError("body", problem)])
    return cleaned


async def add_note(
    ctx: ReviewContext, reviewer: Reviewer, report_id: UUID, body: str
) -> tuple[UUID, datetime]:
    cleaned = validated_body(body)
    if (await ctx.session.execute(_EXISTS, {"id": report_id})).one_or_none() is None:
        raise ProblemError(NOT_FOUND)
    note_id = ctx.ids.new()
    now = ctx.clock.now()
    key = await ctx.keys.create(OWNER_TABLE, note_id, "review_notes")
    await ctx.session.execute(
        _INSERT,
        {
            "id": note_id,
            "report": report_id,
            "author": reviewer.actor_id,
            "body": ctx.cipher.encrypt(
                key, cleaned.encode(), field_context(OWNER_TABLE, note_id, "body", SCHEMA_VERSION)
            ),
            "key": key.id,
            "version": SCHEMA_VERSION,
            "at": now,
        },
    )
    await AuditWriter(ctx.session, ctx.clock, ctx.ids).record(
        "report_note_added",
        actor_type=reviewer.actor_type,
        actor_id=reviewer.actor_id,
        subject_type="report",
        subject_id=report_id,
        request_id=reviewer.request_id,
        details={"note_id": str(note_id)},
    )
    return note_id, now


async def list_notes(
    ctx: ReviewContext,
    report_id: UUID,
    limit: int,
    after: tuple[datetime, UUID] | None,
) -> list[tuple[UUID, datetime, str | None, str | None]]:
    """Up to ``limit`` notes oldest first: (id, created_at, author identifier, plaintext)."""
    if (await ctx.session.execute(_EXISTS, {"id": report_id})).one_or_none() is None:
        raise ProblemError(NOT_FOUND)
    rows = (
        await ctx.session.execute(
            _PAGE,
            {
                "report": report_id,
                "after_at": after[0] if after else None,
                "after_id": after[1] if after else None,
                "limit": limit,
            },
        )
    ).all()
    keys = await ctx.keys.load_many([r.data_key_id for r in rows])
    return [
        (
            r.id,
            r.created_at,
            r.author,
            _decrypt(
                ctx, keys.get(r.data_key_id), bytes(r.body_ciphertext), r.id, r.schema_version
            ),
        )
        for r in rows
    ]


def _decrypt(
    ctx: ReviewContext, key: DataKey | None, ciphertext: bytes, note_id: UUID, version: int
) -> str | None:
    if key is None:
        return None
    try:
        return ctx.cipher.decrypt(
            key, ciphertext, field_context(OWNER_TABLE, note_id, "body", version)
        ).decode()
    except DecryptionError:
        return None

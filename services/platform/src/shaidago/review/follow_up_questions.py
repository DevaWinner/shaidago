"""Reviewer-authored follow-up questions (BE-067's reviewer half).

A question is plain text the reporter sees on tracking, so it must never repeat private report
content; the reviewer is responsible for that, and the length and character rules bound it. Asking
does not change the report's status: a reviewer moves it to ``needs_information`` with the
``request_information`` command. Questions are withdrawn, never deleted or edited.
"""

from typing import Final
from uuid import UUID

from sqlalchemy import text

from shaidago.audit.events import AuditWriter
from shaidago.review.context import ReviewContext
from shaidago.review.detail import Reviewer
from shaidago.shared.problems import (
    CONFLICT,
    NOT_FOUND,
    VALIDATION_FAILED,
    FieldError,
    ProblemError,
)

MIN_CHARS: Final = 5
MAX_CHARS: Final = 500
MAX_OPEN_QUESTIONS: Final = 10

_REPORT = text("SELECT status FROM app.reports WHERE id = :id FOR UPDATE OF reports")
_OPEN_COUNT = text(
    "SELECT count(*) FROM app.report_follow_up_questions "
    "WHERE report_id = :id AND withdrawn_at IS NULL"
)
_INSERT = text(
    "INSERT INTO app.report_follow_up_questions (id, report_id, question, asked_by, asked_at) "
    "VALUES (:id, :report, :question, :by, :at)"
)
_WITHDRAW = text(
    "UPDATE app.report_follow_up_questions SET withdrawn_at = :at "
    "WHERE id = :id AND report_id = :report AND withdrawn_at IS NULL"
)


def _valid(question: str) -> str:
    cleaned = question.strip()
    if not (MIN_CHARS <= len(cleaned) <= MAX_CHARS) or any(c < " " or c == "\x7f" for c in cleaned):
        raise ProblemError(VALIDATION_FAILED, field_errors=[FieldError("question", "invalid_text")])
    return cleaned


async def ask(ctx: ReviewContext, reviewer: Reviewer, report_id: UUID, question: str) -> UUID:
    cleaned = _valid(question)
    row = (await ctx.session.execute(_REPORT, {"id": report_id})).one_or_none()
    if row is None:
        raise ProblemError(NOT_FOUND)
    if row.status == "closed":
        raise ProblemError(CONFLICT)
    open_count = (await ctx.session.execute(_OPEN_COUNT, {"id": report_id})).scalar_one()
    if open_count >= MAX_OPEN_QUESTIONS:
        raise ProblemError(CONFLICT)
    question_id = ctx.ids.new()
    await ctx.session.execute(
        _INSERT,
        {
            "id": question_id,
            "report": report_id,
            "question": cleaned,
            "by": reviewer.actor_id,
            "at": ctx.clock.now(),
        },
    )
    await AuditWriter(ctx.session, ctx.clock, ctx.ids).record(
        "report_follow_up_question_added",
        actor_type=reviewer.actor_type,
        actor_id=reviewer.actor_id,
        subject_type="report",
        subject_id=report_id,
        request_id=reviewer.request_id,
        details={"question_id": str(question_id)},
    )
    return question_id


async def withdraw(
    ctx: ReviewContext, reviewer: Reviewer, report_id: UUID, question_id: UUID
) -> None:
    result = await ctx.session.execute(
        _WITHDRAW, {"id": question_id, "report": report_id, "at": ctx.clock.now()}
    )
    if not getattr(result, "rowcount", 0):
        raise ProblemError(NOT_FOUND)
    await AuditWriter(ctx.session, ctx.clock, ctx.ids).record(
        "report_follow_up_question_withdrawn",
        actor_type=reviewer.actor_type,
        actor_id=reviewer.actor_id,
        subject_type="report",
        subject_id=report_id,
        request_id=reviewer.request_id,
        details={"question_id": str(question_id)},
    )

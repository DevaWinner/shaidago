"""Discovery runs for the public and for reviewers: create or reuse, read, cancel, decide.

Public runs are shared and cost-bounded: one per project per 24 hours, a global daily budget,
serialised by an advisory lock so concurrent requests cannot overspend. A public caller can
start (or re-use) a run and read a scope-safe projection; it cannot cancel or steer a shared
run. Report-scoped runs exist only for reviewers, use a query the reviewer approved verbatim, and
are invisible to every public path. Nothing here attaches or publishes: a decision to attach
creates a *pending* source that still needs the ordinary source review.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import Any, Final
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.audit.events import AuditWriter
from shaidago.discovery.budget import BudgetDecision, PriorRun, decide_public_run
from shaidago.discovery.dispositions import DecisionNotAllowedError, find_decision
from shaidago.discovery.planner import (
    POLICY_VERSION,
    PublicProjectTerms,
    QueryPlan,
    plan_public_query,
)
from shaidago.review.context import ReviewContext
from shaidago.review.detail import Reviewer
from shaidago.shared.clock import Clock
from shaidago.shared.crypto import field_context
from shaidago.shared.ids import IdGenerator
from shaidago.shared.problems import (
    CONFLICT,
    NOT_FOUND,
    VALIDATION_FAILED,
    FieldError,
    Problem,
    ProblemError,
)
from shaidago.worker.machine import DiscoveryTransitionNotAllowedError, find_transition

LAGOS: Final = ZoneInfo("Africa/Lagos")
SCHEMA_VERSION: Final = 1
STALE_QUEUED_SECONDS: Final = 60
DISCOVERY_TRANSITION_NOT_ALLOWED: Final = Problem(
    409, "discovery_transition_not_allowed", "Change not allowed",
    "That change is not allowed from the run's current status.",
)  # fmt: skip
DECISION_NOT_ALLOWED: Final = Problem(
    409, "discovered_source_decision_not_allowed", "Decision not allowed",
    "That decision is not allowed from the source's current state.",
)  # fmt: skip
QUERY_CHANGED: Final = Problem(
    409, "query_changed", "Query changed",
    "The outbound query differs from the one that was approved. Review and approve it again.",
)  # fmt: skip

_PROJECT = text("SELECT slug FROM public_api.projects WHERE slug = :slug")
_LOCK = text("SELECT pg_advisory_xact_lock(hashtext('shaidago.discovery.public_budget'))")
_PUBLIC_RUNS = text(
    "SELECT id, status, created_at, finished_at, updated_at FROM public_api.discovery_runs "
    "WHERE project_slug = :slug ORDER BY created_at DESC, id DESC LIMIT 20"
)
_TODAY = text(
    "SELECT count(*) FROM public_api.discovery_runs "
    "WHERE created_at >= :start AND created_at < :end"
)
_CREATE_PUBLIC = text(
    "SELECT app.create_public_discovery_run(:id, :slug, :now, :mode, :demo, :query, :policy)"
)
_PUBLIC_RUN = text("SELECT * FROM public_api.discovery_runs WHERE id = :id")
_PUBLIC_SOURCES = text(
    "SELECT source_id, canonical_url, publisher_domain, title, preliminary_type, published_on, "
    "published_provenance, date_conflict, content_type, excerpt, availability, "
    "first_discovered_at, last_retrieved_at FROM public_api.discovery_run_sources "
    "WHERE run_id = :id ORDER BY first_discovered_at, source_id LIMIT 20"
)
_TERMS = text(
    "SELECT t.title, l.name AS locality, p.category FROM public_api.projects p "
    "JOIN public_api.project_translations t ON t.project_id = p.id AND t.locale = 'en' "
    "JOIN public_api.localities l ON l.slug = p.locality_slug WHERE p.slug = :slug"
)
_REPORT = text(
    "SELECT r.id, r.project_id, p.slug FROM app.reports r JOIN app.projects p "
    "ON p.id = r.project_id WHERE r.id = :id"
)
_INSERT_REPORT_RUN = text(
    "INSERT INTO app.discovery_runs (id, scope, project_id, report_id, requested_by, status, "
    "query_text, query_policy_version, query_approved_by, provider_mode, demo_replay, "
    "created_at, updated_at) VALUES (:id, 'report', :project, :report, :by, 'queued', :query, "
    ":policy, :by, :mode, :demo, :now, :now)"
)
_REVIEWER_RUN = text(
    "SELECT id, scope, project_id, report_id, status, cancel_requested, failure_code, "
    "query_text, query_policy_version, provider_mode, demo_replay, results_found, "
    "fetched_count, analysed_count, version, analysis, created_at, updated_at, finished_at "
    "FROM app.discovery_runs WHERE id = :id"
)
_REVIEWER_SOURCES = text(
    "SELECT d.id, d.canonical_url, d.publisher_domain, d.title, d.preliminary_type, "
    "d.published_on, d.published_provenance, d.date_conflict, d.excerpt, d.availability, "
    "d.injection_flag, d.duplicate_of, d.duplicate_kind, d.disposition, d.attached_source_id "
    "FROM app.discovered_source_sightings s JOIN app.discovered_sources d "
    "ON d.id = s.discovered_source_id WHERE s.run_id = :id "
    "ORDER BY d.first_discovered_at, d.id LIMIT 50"
)
_LOCK_RUN = text(
    "SELECT status, cancel_requested FROM app.discovery_runs WHERE id = :id FOR UPDATE"
)
_CANCEL_NOW = text(
    "UPDATE app.discovery_runs SET status = 'cancelled', finished_at = :now, updated_at = :now "
    "WHERE id = :id"
)
_CANCEL_FLAG = text(
    "UPDATE app.discovery_runs SET cancel_requested = true, updated_at = :now WHERE id = :id"
)
_REVIEW_APPROVE = text(
    "UPDATE app.discovery_runs SET status = 'complete', finished_at = :now, updated_at = :now "
    "WHERE id = :id"
)
_REVIEW_REJECT = text(
    "UPDATE app.discovery_runs SET status = 'failed', failure_code = 'reviewer_rejected', "
    "finished_at = :now, updated_at = :now WHERE id = :id"
)
_SOURCE = text(
    "SELECT id, disposition, canonical_url FROM app.discovered_sources WHERE id = :id FOR UPDATE"
)
_DECIDE = text(
    "UPDATE app.discovered_sources SET disposition = :new, decided_by = :by, decided_at = :now, "
    "decision_reason_ciphertext = :reason, decision_key_id = :key, updated_at = :now "
    "WHERE id = :id"
)
_ATTACH = text(
    "SELECT app.attach_discovered_source(:id, :by, :now, :source, :version, :reason, :key, "
    ":audit, :request)"
)
_ANSWER = text(
    "INSERT INTO app.discovery_follow_up_answers (id, run_id, question_index, kind, "
    "answer_ciphertext, data_key_id, schema_version, answered_by, created_at) VALUES "
    "(:id, :run, :index, :kind, :ciphertext, :key, :version, :by, :now) "
    "ON CONFLICT (run_id, question_index) DO NOTHING"
)


@dataclass(frozen=True)
class PublicRunRequest:
    run_id: UUID
    action: str
    created: bool
    enqueue: bool


def lagos_day_start(now: datetime) -> datetime:
    local = now.astimezone(LAGOS)
    return datetime.combine(local.date(), time.min, LAGOS).astimezone(UTC)


async def request_public_run(  # noqa: PLR0913 - the budget inputs are named, not bundled
    session: AsyncSession,
    clock: Clock,
    ids: IdGenerator,
    slug: str,
    *,
    daily_limit: int,
    provider_mode: str,
) -> PublicRunRequest | None:
    """Reuse, create, or fall back per the budget rule. None means an unknown project."""
    if (await session.execute(_PROJECT, {"slug": slug})).one_or_none() is None:
        return None
    await session.execute(_LOCK)
    now = clock.now()
    rows = (await session.execute(_PUBLIC_RUNS, {"slug": slug})).all()
    start = lagos_day_start(now)
    today = (
        await session.execute(_TODAY, {"start": start, "end": start + timedelta(days=1)})
    ).scalar_one()
    runs = [PriorRun(str(r.id), r.status, r.created_at, r.finished_at) for r in rows]
    decision: BudgetDecision = decide_public_run(
        now=now, runs=runs, fresh_runs_today=int(today), daily_limit=daily_limit
    )
    if decision.action == "create":
        terms = await project_terms(session, slug)
        plan = plan_public_query(terms) if terms is not None else None
        if plan is None or not plan.terms:
            return PublicRunRequest(UUID(int=0), "unavailable", created=False, enqueue=False)
        run_id = UUID(
            str(
                (
                    await session.execute(
                        _CREATE_PUBLIC,
                        {
                            "id": ids.new(),
                            "slug": slug,
                            "now": now,
                            "mode": provider_mode,
                            "demo": provider_mode == "replay",
                            "query": plan.query,
                            "policy": plan.policy_version,
                        },
                    )
                ).scalar_one()
            )
        )
        return PublicRunRequest(run_id, "create", created=True, enqueue=True)
    if decision.run_id is None:
        return PublicRunRequest(UUID(int=0), "unavailable", created=False, enqueue=False)
    chosen = next(r for r in rows if str(r.id) == decision.run_id)
    stale = (
        chosen.status == "queued"
        and (now - chosen.updated_at).total_seconds() > STALE_QUEUED_SECONDS
    )
    return PublicRunRequest(UUID(decision.run_id), decision.action, created=False, enqueue=stale)


async def public_run_view(session: AsyncSession, run_id: UUID) -> tuple[Any, list[Any]] | None:
    run = (await session.execute(_PUBLIC_RUN, {"id": run_id})).one_or_none()
    if run is None:
        return None
    sources = (await session.execute(_PUBLIC_SOURCES, {"id": run_id})).all()
    return run, list(sources)


async def project_terms(session: AsyncSession, slug: str) -> PublicProjectTerms | None:
    row = (await session.execute(_TERMS, {"slug": slug})).one_or_none()
    if row is None:
        return None
    return PublicProjectTerms(title=row.title, locality=row.locality, category=row.category)


async def report_project(session: AsyncSession, report_id: UUID) -> Any | None:
    return (await session.execute(_REPORT, {"id": report_id})).one_or_none()


async def create_report_run(
    ctx: ReviewContext,
    reviewer: Reviewer,
    report: Any,
    plan: QueryPlan,
    *,
    provider_mode: str,
) -> UUID:
    run_id = ctx.ids.new()
    await ctx.session.execute(
        _INSERT_REPORT_RUN,
        {
            "id": run_id, "project": report.project_id, "report": report.id,
            "by": reviewer.actor_id, "query": plan.query, "policy": POLICY_VERSION,
            "mode": provider_mode, "demo": provider_mode == "replay", "now": ctx.clock.now(),
        },
    )  # fmt: skip
    await AuditWriter(ctx.session, ctx.clock, ctx.ids).record(
        "discovery_run_created",
        actor_type=reviewer.actor_type,
        actor_id=reviewer.actor_id,
        subject_type="discovery_run",
        subject_id=run_id,
        request_id=reviewer.request_id,
        details={"scope": "report", "policy": POLICY_VERSION, "query_digest": plan.digest},
    )
    return run_id


async def reviewer_run_view(session: AsyncSession, run_id: UUID) -> tuple[Any, list[Any]] | None:
    run = (await session.execute(_REVIEWER_RUN, {"id": run_id})).one_or_none()
    if run is None:
        return None
    return run, list((await session.execute(_REVIEWER_SOURCES, {"id": run_id})).all())


async def cancel_run(ctx: ReviewContext, reviewer: Reviewer, run_id: UUID) -> str:
    """Cancel now if nothing has started, otherwise ask the worker to stop between stages."""
    row = (await ctx.session.execute(_LOCK_RUN, {"id": run_id})).one_or_none()
    if row is None:
        raise ProblemError(NOT_FOUND)
    try:
        find_transition(row.status, "cancel", reviewer.actor_type)
    except DiscoveryTransitionNotAllowedError:
        raise ProblemError(DISCOVERY_TRANSITION_NOT_ALLOWED) from None
    now = ctx.clock.now()
    immediate = row.status in {"queued", "needs_review"}
    await ctx.session.execute(
        _CANCEL_NOW if immediate else _CANCEL_FLAG, {"id": run_id, "now": now}
    )
    await _audit(
        ctx, reviewer, "discovery_cancelled" if immediate else "discovery_cancel_requested", run_id
    )
    return "cancelled" if immediate else "cancel_requested"


async def review_run(ctx: ReviewContext, reviewer: Reviewer, run_id: UUID, command: str) -> str:
    row = (await ctx.session.execute(_LOCK_RUN, {"id": run_id})).one_or_none()
    if row is None:
        raise ProblemError(NOT_FOUND)
    try:
        step = find_transition(row.status, command, reviewer.actor_type)
    except DiscoveryTransitionNotAllowedError:
        raise ProblemError(DISCOVERY_TRANSITION_NOT_ALLOWED) from None
    statement = _REVIEW_APPROVE if command == "approve_completion" else _REVIEW_REJECT
    await ctx.session.execute(statement, {"id": run_id, "now": ctx.clock.now()})
    await _audit(ctx, reviewer, step.audit_event, run_id)
    return step.to_status


async def _audit(ctx: ReviewContext, reviewer: Reviewer, event: str, subject: UUID) -> None:
    await AuditWriter(ctx.session, ctx.clock, ctx.ids).record(
        event,
        actor_type=reviewer.actor_type,
        actor_id=reviewer.actor_id,
        subject_type="discovery_run",
        subject_id=subject,
        request_id=reviewer.request_id,
    )


def _clean_reason(reason: str) -> str:
    cleaned = reason.strip()
    if not 5 <= len(cleaned) <= 300 or any(c < " " and c not in "\n\t" for c in cleaned):  # noqa: PLR2004
        raise ProblemError(VALIDATION_FAILED, field_errors=[FieldError("reason", "invalid_text")])
    return cleaned


async def decide_source(
    ctx: ReviewContext, reviewer: Reviewer, source_id: UUID, command: str, reason: str
) -> str:
    """Record a decision on a discovered source. Attaching yields a pending source only."""
    cleaned = _clean_reason(reason)
    row = (await ctx.session.execute(_SOURCE, {"id": source_id})).one_or_none()
    if row is None:
        raise ProblemError(NOT_FOUND)
    try:
        step = find_decision(row.disposition, command, reviewer.actor_type)
    except DecisionNotAllowedError:
        raise ProblemError(DECISION_NOT_ALLOWED) from None
    # A source can be decided several times, so each decision has its own key and owner ID; the
    # ciphertext is bound to that key's ID, which the row stores.
    key = await ctx.keys.create("discovered_source_decisions", ctx.ids.new(), "review_notes")
    ciphertext = ctx.cipher.encrypt(
        key,
        cleaned.encode(),
        field_context("discovered_source_decisions", key.id, "reason", SCHEMA_VERSION),
    )
    now = ctx.clock.now()
    if command == "attach":
        outcome = (
            await ctx.session.execute(
                _ATTACH,
                {
                    "id": source_id, "by": reviewer.actor_id, "now": now,
                    "source": ctx.ids.new(), "version": ctx.ids.new(), "reason": ciphertext,
                    "key": key.id, "audit": ctx.ids.new(), "request": reviewer.request_id,
                },
            )
        ).scalar_one()  # fmt: skip
        if outcome != "attached":
            raise ProblemError(DECISION_NOT_ALLOWED if outcome == "not_allowed" else NOT_FOUND)
        return step.to_state
    await ctx.session.execute(
        _DECIDE,
        {"id": source_id, "new": step.to_state, "by": reviewer.actor_id, "now": now,
         "reason": ciphertext, "key": key.id},
    )  # fmt: skip
    await AuditWriter(ctx.session, ctx.clock, ctx.ids).record(
        step.audit_event,
        actor_type=reviewer.actor_type,
        actor_id=reviewer.actor_id,
        subject_type="discovered_source",
        subject_id=source_id,
        request_id=reviewer.request_id,
        details={"from": row.disposition, "to": step.to_state},
    )
    return step.to_state


async def answer_follow_up(  # noqa: PLR0913, PLR0917 - one answer names its run, question, kind, and text
    ctx: ReviewContext,
    reviewer: Reviewer,
    run_id: UUID,
    index: int,
    kind: str,
    answer: str | None,
) -> None:
    run = (await ctx.session.execute(_REVIEWER_RUN, {"id": run_id})).one_or_none()
    if run is None:
        raise ProblemError(NOT_FOUND)
    stored: dict[str, Any] = run.analysis or {}
    analysis: dict[str, Any] = stored.get("analysis") or {}
    questions: list[Any] = analysis.get("follow_up_questions") or []
    if index >= len(questions):
        raise ProblemError(
            VALIDATION_FAILED, field_errors=[FieldError("question_index", "unknown")]
        )
    ciphertext: bytes | None = None
    key_id: UUID | None = None
    answer_id = ctx.ids.new()
    if kind == "answered":
        body = (answer or "").strip()
        if not body or len(body) > 2000:  # noqa: PLR2004
            raise ProblemError(VALIDATION_FAILED, field_errors=[FieldError("answer", "length")])
        key = await ctx.keys.create("discovery_follow_up_answers", answer_id, "follow_up_answers")
        key_id = key.id
        ciphertext = ctx.cipher.encrypt(
            key, body.encode(),
            field_context("discovery_follow_up_answers", answer_id, "answer", SCHEMA_VERSION),
        )  # fmt: skip
    result = await ctx.session.execute(
        _ANSWER,
        {"id": answer_id, "run": run_id, "index": index, "kind": kind, "ciphertext": ciphertext,
         "key": key_id, "version": SCHEMA_VERSION, "by": reviewer.actor_id, "now": ctx.clock.now()},
    )  # fmt: skip
    if not getattr(result, "rowcount", 0):
        raise ProblemError(CONFLICT)
    await _audit(ctx, reviewer, "discovery_follow_up_answered", run_id)

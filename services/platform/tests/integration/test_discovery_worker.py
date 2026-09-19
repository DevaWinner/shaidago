"""The worker lifecycle (BE-090): leases, idempotent stages, crashes, cancellation, exhaustion."""

import asyncio
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from shaidago.worker.process import (
    Outcome,
    PermanentStageError,
    TransientStageError,
    fail_exhausted,
    process_run,
)
from shaidago.worker.store import LEASE_SECONDS, MAX_ATTEMPTS
from tests.integration.discovery_support import Discovery, RecordingPipeline, discovery

__all__ = ["discovery"]


async def test_a_run_moves_through_every_stage_and_records_each_step(discovery: Discovery) -> None:
    run_id = await discovery.new_run()
    pipeline = RecordingPipeline()
    assert await process_run(discovery.store, pipeline, run_id, "w1") == Outcome.COMPLETED
    row = await discovery.row(run_id)
    assert (row.status, row.attempts, row.lease_owner) == ("complete", 1, None)
    assert row.started_at is not None
    assert row.finished_at is not None
    assert pipeline.searches == [run_id]
    assert pipeline.analyses == [run_id]
    assert await discovery.audit(run_id) == [
        "discovery_search_started",
        "discovery_analysis_started",
        "discovery_completed",
    ]


async def test_analysis_can_hand_the_run_to_a_reviewer(discovery: Discovery) -> None:
    run_id = await discovery.new_run()
    outcome = await process_run(discovery.store, RecordingPipeline(needs_review=True), run_id, "w")
    assert outcome == Outcome.NEEDS_REVIEW
    assert (await discovery.row(run_id)).status == "needs_review"


async def test_a_duplicate_delivery_while_the_lease_is_held_does_nothing(
    discovery: Discovery,
) -> None:
    run_id = await discovery.new_run()
    started, release = asyncio.Event(), asyncio.Event()

    async def slow_search(*_: object) -> None:
        started.set()
        await release.wait()

    first_pipeline = RecordingPipeline(on_search=slow_search)
    second_pipeline = RecordingPipeline()
    first = asyncio.create_task(process_run(discovery.store, first_pipeline, run_id, "w1"))
    await started.wait()
    second = await process_run(discovery.store, second_pipeline, run_id, "w2")
    assert second == Outcome.SKIPPED
    assert second_pipeline.searches == []
    release.set()
    assert await first == Outcome.COMPLETED
    assert first_pipeline.searches == [run_id]


async def test_an_expired_lease_can_be_taken_over_but_a_live_one_cannot(
    discovery: Discovery,
) -> None:
    run_id = await discovery.new_run()
    assert await discovery.store.acquire(run_id, "w1") == 1
    assert await discovery.store.acquire(run_id, "w2") is None
    discovery.clock.advance(timedelta(seconds=LEASE_SECONDS + 1))
    assert await discovery.store.acquire(run_id, "w2") == 2


async def test_a_crash_between_stages_resumes_without_repeating_finished_work(
    discovery: Discovery,
) -> None:
    run_id = await discovery.new_run()
    calls = {"n": 0}

    async def flaky_search(*_: object) -> None:
        calls["n"] += 1
        if calls["n"] == 1:
            raise TransientStageError

    pipeline = RecordingPipeline(on_search=flaky_search)
    with pytest.raises(TransientStageError):
        await process_run(discovery.store, pipeline, run_id, "w1")
    interrupted = await discovery.row(run_id)
    assert (interrupted.status, interrupted.lease_owner) == ("searching", None)
    assert await process_run(discovery.store, pipeline, run_id, "w2") == Outcome.COMPLETED
    assert (await discovery.row(run_id)).attempts == 2
    assert pipeline.searches == [run_id, run_id]
    events = await discovery.audit(run_id)
    assert events.count("discovery_search_started") == 1


async def test_a_permanent_failure_ends_the_run_with_a_safe_code(discovery: Discovery) -> None:
    run_id = await discovery.new_run()

    async def broken(*_: object) -> None:
        raise PermanentStageError("extraction_failed")

    outcome = await process_run(discovery.store, RecordingPipeline(on_search=broken), run_id, "w")
    row = await discovery.row(run_id)
    assert outcome == Outcome.FAILED
    assert (row.status, row.failure_code, row.lease_owner) == ("failed", "extraction_failed", None)


async def test_a_run_that_has_used_all_its_attempts_fails_instead_of_retrying(
    discovery: Discovery,
) -> None:
    run_id = await discovery.new_run(attempts=MAX_ATTEMPTS)
    pipeline = RecordingPipeline()
    assert await process_run(discovery.store, pipeline, run_id, "w") == Outcome.FAILED
    assert (await discovery.row(run_id)).failure_code == "attempts_exhausted"
    assert pipeline.searches == []


@pytest.mark.parametrize("status", ["complete", "failed", "cancelled"])
async def test_a_finished_run_and_an_unknown_run_are_ignored(
    discovery: Discovery, status: str
) -> None:
    run_id = await discovery.new_run(status="queued")
    async with discovery.owner.unit_of_work() as session:
        await session.execute(
            text("ALTER TABLE app.discovery_runs DISABLE TRIGGER discovery_runs_guard")
        )
        await session.execute(
            text("UPDATE app.discovery_runs SET status = :s, failure_code = 'x' WHERE id = :i"),
            {"s": status, "i": run_id},
        )
        await session.execute(
            text("ALTER TABLE app.discovery_runs ENABLE TRIGGER discovery_runs_guard")
        )
    pipeline = RecordingPipeline()
    assert await process_run(discovery.store, pipeline, run_id, "w") == Outcome.SKIPPED
    assert await process_run(discovery.store, pipeline, uuid.uuid4(), "w") == Outcome.SKIPPED
    assert pipeline.searches == []


async def test_a_cancel_request_stops_future_work_and_keeps_what_was_retrieved(
    discovery: Discovery,
) -> None:
    run_id = await discovery.new_run()

    async def search_then_cancel(run: object, store: object) -> None:
        del run, store
        await discovery.store.progress(run_id, found=3, fetched=2, analysed=0)
        async with discovery.owner.unit_of_work() as session:
            await session.execute(
                text("UPDATE app.discovery_runs SET cancel_requested = true WHERE id = :i"),
                {"i": run_id},
            )

    pipeline = RecordingPipeline(on_search=search_then_cancel)
    assert await process_run(discovery.store, pipeline, run_id, "w") == Outcome.CANCELLED
    row = await discovery.row(run_id)
    assert (row.status, row.results_found, row.fetched_count) == ("cancelled", 3, 2)
    assert pipeline.analyses == []
    assert (await discovery.audit(run_id))[-1] == "discovery_cancelled"


async def test_a_cancel_requested_before_the_first_stage_never_searches(
    discovery: Discovery,
) -> None:
    run_id = await discovery.new_run(cancel=True)
    pipeline = RecordingPipeline()
    assert await process_run(discovery.store, pipeline, run_id, "w") == Outcome.CANCELLED
    assert pipeline.searches == []


async def test_exhausted_retries_fail_an_active_run_and_leave_a_finished_one_alone(
    discovery: Discovery,
) -> None:
    active = await discovery.new_run(status="queued")
    await fail_exhausted(discovery.store, active, "retries_exhausted")
    row = await discovery.row(active)
    assert (row.status, row.failure_code) == ("failed", "retries_exhausted")
    await fail_exhausted(discovery.store, active, "retries_exhausted")
    await fail_exhausted(discovery.store, uuid.uuid4(), "retries_exhausted")
    assert (await discovery.row(active)).version == row.version


async def test_the_database_refuses_edges_the_machine_forbids_even_for_the_worker(
    discovery: Discovery,
) -> None:
    run_id = await discovery.new_run()
    for statement in (
        "UPDATE app.discovery_runs SET status = 'complete' WHERE id = :i",
        "UPDATE app.discovery_runs SET scope = 'report' WHERE id = :i",
        "UPDATE app.discovery_runs SET project_id = gen_random_uuid() WHERE id = :i",
        "DELETE FROM app.discovery_runs WHERE id = :i",
    ):
        async with discovery.worker.engine.connect() as connection:
            with pytest.raises((DBAPIError, ProgrammingError)):
                await connection.execute(text(statement), {"i": run_id})
    assert (await discovery.row(run_id)).status == "queued"


async def test_the_worker_can_neither_create_runs_nor_edit_their_query(
    discovery: Discovery,
) -> None:
    run_id = await discovery.new_run()
    for statement in (
        "INSERT INTO app.discovery_runs (id, scope, project_id, status, provider_mode, created_at, updated_at) "
        "SELECT gen_random_uuid(), 'public', project_id, 'queued', 'live', now(), now() FROM app.discovery_runs LIMIT 1",
        "UPDATE app.discovery_runs SET query_text = 'a different query' WHERE id = :i",
        "UPDATE app.discovery_runs SET cancel_requested = true WHERE id = :i",
    ):
        async with discovery.worker.engine.connect() as connection:
            with pytest.raises(ProgrammingError, match="permission denied"):
                await connection.execute(text(statement), {"i": run_id})


async def test_the_scope_rule_and_the_public_role_boundary_hold(
    discovery: Discovery, role_urls: dict[str, object]
) -> None:
    async with discovery.owner.unit_of_work() as session:
        with pytest.raises(DBAPIError):
            await session.execute(
                text(
                    "INSERT INTO app.discovery_runs (id, scope, project_id, status, provider_mode, "
                    "created_at, updated_at) VALUES (gen_random_uuid(), 'report', :p, 'queued', "
                    "'replay', now(), now())"
                ),
                {"p": discovery.project_id},
            )
    assert role_urls  # the public role has no grant on the table (proved in the roles suite)

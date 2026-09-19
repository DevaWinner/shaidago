"""Every checked-in replay scenario end to end, and proof the fixtures are current (BE-097)."""

import asyncio
import importlib.util
import json
import re
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from dramatiq import Worker
from dramatiq.brokers.stub import StubBroker
from sqlalchemy import text
from sqlalchemy.engine import URL

from shaidago.discovery.pages import FIXTURE_ROOT
from shaidago.discovery.pipeline import SourceScoutPipeline
from shaidago.discovery.providers import replay_providers
from shaidago.shared.database import Database, build_engine
from shaidago.shared.ids import Uuid7Generator
from shaidago.worker.broker import QUEUE_NAME, build_stub_broker, enqueue, register_actors
from shaidago.worker.envelope import CONFIG_VERSION, JobEnvelope
from shaidago.worker.process import (
    Outcome,
    TransientStageError,
    fail_exhausted,
    process_run,
)
from shaidago.worker.store import RunStore
from tests.integration.reviewer_support import ReviewWorld
from tests.integration.support import insert_project

MANIFEST = json.loads((FIXTURE_ROOT / "scenarios.json").read_text("utf-8"))["scenarios"]
IDS = [s["id"] for s in MANIFEST]
SCRIPT = Path(__file__).parents[2] / "scripts" / "build_discovery_fixtures.py"


def scenario(scenario_id: str) -> dict[str, Any]:
    return next(s for s in MANIFEST if s["id"] == scenario_id)


def test_the_fixture_files_are_exactly_what_the_builder_produces() -> None:
    spec = importlib.util.spec_from_file_location("build_discovery_fixtures", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name, document in module.build().items():
        assert (FIXTURE_ROOT / name).read_text("utf-8") == module.render(document), name


def test_the_fixtures_contain_only_synthetic_reserved_domains() -> None:
    for name in ("search.json", "pages.json"):
        content = (FIXTURE_ROOT / name).read_text("utf-8")
        for url in re.findall(r"https?://[^\"/]+", content):
            assert (
                url.split("://")[1]
                .split("@")[-1]
                .endswith((".test", "127.0.0.1", "169.254.169.254"))
            ), url


async def project_for(world: ReviewWorld, title: str) -> str:
    slug = f"fixture-{uuid.uuid4().hex[:10]}"
    async with world.owner.unit_of_work() as session:
        project_id = await insert_project(session, slug=slug)
        await session.execute(
            text(
                "UPDATE app.project_translations SET title = :t WHERE project_id = :p AND locale = 'en'"
            ),
            {"t": title, "p": project_id},
        )
    return slug


async def public_run(world: ReviewWorld, slug: str) -> uuid.UUID:
    async with world.client() as http:
        response = await http.post(f"/v1/projects/{slug}/discovery-runs")
    assert response.status_code == 200, response.text
    assert response.json()["demo_replay"] is True
    return uuid.UUID(response.json()["run_id"])


async def read_run(world: ReviewWorld, run_id: uuid.UUID) -> dict[str, Any]:
    async with world.client() as http:
        response = await http.get(f"/v1/discovery-runs/{run_id}")
    return response.json()  # type: ignore[no-any-return]


def worker_store(role_urls: dict[str, URL], world: ReviewWorld) -> tuple[RunStore, Database]:
    engine = build_engine(
        role_urls["shaidago_worker"], application_name="w", statement_timeout_ms=8000
    )
    database = Database(engine)
    return RunStore(database, world.clock, Uuid7Generator(world.clock)), database


@pytest.fixture(autouse=True)
def own_lagos_day(review_world: ReviewWorld) -> None:
    review_world.clock.advance(timedelta(days=100 + uuid.uuid4().int % 20000))


@pytest.mark.parametrize(
    "scenario_id",
    [
        i
        for i in IDS
        if not scenario(i)["expected"].get("transient")
        and not scenario(i)["expected"].get("dead_letter")
        and "cancel_after" not in scenario(i)["expected"]
    ],
)
async def test_each_scenario_ends_as_recorded_and_is_labelled_a_replay(
    review_world: ReviewWorld, role_urls: dict[str, URL], scenario_id: str
) -> None:
    spec = scenario(scenario_id)
    expected = spec["expected"]
    slug = await project_for(review_world, spec["title"])
    run_id = await public_run(review_world, slug)
    store, database = worker_store(role_urls, review_world)
    try:
        providers = replay_providers()
        pipeline = SourceScoutPipeline(providers.search, providers.fetcher, providers.analyser_for)
        outcome = await process_run(store, pipeline, run_id, "w")
    finally:
        await database.engine.dispose()
    [row] = await review_world.rows("SELECT * FROM app.discovery_runs WHERE id = :r", r=run_id)
    assert row.query_text == spec["query"]  # planned from public fields at creation
    assert row.status == expected["status"], (scenario_id, row.failure_code)
    assert (row.results_found, row.fetched_count) == (expected["found"], expected["fetched"])
    assert row.analysis["status"] == expected["analysis"]
    assert row.analysis["demo_replay"] is True
    assert row.analysis["label"] == "discovered — not yet reviewed"
    assert row.analysis.get("failure_code") == expected.get("failure_code")
    assert outcome in {Outcome.COMPLETED, Outcome.NEEDS_REVIEW}
    view = await read_run(review_world, run_id)
    assert len(view["sources"]) == expected["shown"]
    assert view["demo_replay"] is True
    assert all(card["label"] == "discovered — not yet reviewed" for card in view["sources"])
    assert (view["result"] is not None) == (expected["status"] == "complete")
    if expected["analysis"] == "needs_review":
        assert "guilty" not in json.dumps(row.analysis)


async def test_a_provider_outage_is_retried_and_leaves_the_run_in_progress(
    review_world: ReviewWorld, role_urls: dict[str, URL]
) -> None:
    spec = scenario("provider_outage")
    run_id = await public_run(review_world, await project_for(review_world, spec["title"]))
    store, database = worker_store(role_urls, review_world)
    try:
        providers = replay_providers()
        pipeline = SourceScoutPipeline(providers.search, providers.fetcher, providers.analyser_for)
        with pytest.raises(TransientStageError):
            await process_run(store, pipeline, run_id, "w")
    finally:
        await database.engine.dispose()
    [row] = await review_world.rows(
        "SELECT status, lease_owner FROM app.discovery_runs WHERE id = :r", r=run_id
    )
    assert (row.status, row.lease_owner) == ("searching", None)


async def test_a_cancel_request_stops_the_cancellation_scenario_after_two_pages(
    review_world: ReviewWorld, role_urls: dict[str, URL]
) -> None:
    spec = scenario("cancellation")
    run_id = await public_run(review_world, await project_for(review_world, spec["title"]))
    store, database = worker_store(role_urls, review_world)
    providers = replay_providers()
    fetched: list[str] = []

    class CancelAfter:
        async def fetch(self, url: str) -> Any:
            page = await providers.fetcher.fetch(url)
            fetched.append(url)
            if len(fetched) == spec["expected"]["cancel_after"]:
                async with review_world.owner.unit_of_work() as session:
                    await session.execute(
                        text("UPDATE app.discovery_runs SET cancel_requested = true WHERE id = :r"),
                        {"r": run_id},
                    )
            return page

    try:
        pipeline = SourceScoutPipeline(providers.search, CancelAfter(), providers.analyser_for)
        outcome = await process_run(store, pipeline, run_id, "w")
    finally:
        await database.engine.dispose()
    [row] = await review_world.rows(
        "SELECT status, results_found, fetched_count FROM app.discovery_runs WHERE id = :r",
        r=run_id,
    )
    assert outcome == Outcome.CANCELLED
    assert (row.status, row.results_found, row.fetched_count) == ("cancelled", 5, 2)
    assert len(fetched) == 2
    view = await read_run(review_world, run_id)
    assert (view["status"], len(view["sources"])) == ("cancelled", 2)  # what was retrieved is kept


async def test_a_job_that_always_fails_is_dead_lettered_and_its_run_is_marked_failed(
    review_world: ReviewWorld, role_urls: dict[str, URL]
) -> None:
    spec = scenario("dead_letter")
    run_id = await public_run(review_world, await project_for(review_world, spec["title"]))

    async def handle(job_run_id: uuid.UUID, owner: str) -> Outcome:
        store, database = worker_store(role_urls, review_world)
        try:
            providers = replay_providers()
            pipeline = SourceScoutPipeline(
                providers.search, providers.fetcher, providers.analyser_for
            )
            return await process_run(store, pipeline, job_run_id, owner)
        finally:
            await database.engine.dispose()

    async def give_up(job_run_id: uuid.UUID, code: str) -> None:
        store, database = worker_store(role_urls, review_world)
        try:
            await fail_exhausted(store, job_run_id, code)
        finally:
            await database.engine.dispose()

    broker: StubBroker = build_stub_broker()
    actors = register_actors(
        broker, handle, give_up, max_retries=2, min_backoff_ms=10, max_backoff_ms=20
    )
    worker = Worker(broker, worker_timeout=50, worker_threads=1)
    worker.start()
    try:
        enqueue(actors, JobEnvelope(run_id=run_id, config_version=CONFIG_VERSION))
        await asyncio.to_thread(broker.join, QUEUE_NAME, fail_fast=False)
        await asyncio.to_thread(worker.join)
    finally:
        worker.stop()
    assert len(broker.dead_letters) == 1
    [row] = await review_world.rows(
        "SELECT status, failure_code, attempts, lease_owner FROM app.discovery_runs WHERE id = :r",
        r=run_id,
    )
    assert (row.status, row.failure_code, row.lease_owner) == ("failed", "retries_exhausted", None)
    assert row.attempts == 3  # the first attempt and two retries, never more
    view = await read_run(review_world, run_id)
    assert (view["status"], view["failure_code"], view["result"]) == (
        "failed",
        "retries_exhausted",
        None,
    )

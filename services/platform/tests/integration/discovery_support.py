"""Shared harness for discovery tests: real worker/reviewer roles, a synthetic public project."""

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL

from shaidago.shared.clock import ManualClock
from shaidago.shared.database import Database, build_engine
from shaidago.shared.ids import Uuid7Generator
from shaidago.worker.process import AnalysisResult
from shaidago.worker.store import RunStore, RunView
from tests.integration.support import Plain, insert_project

START = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)


@dataclass
class Discovery:
    owner: Plain
    worker: Database
    clock: ManualClock
    store: RunStore
    project_id: uuid.UUID
    slug: str

    async def new_run(self, **overrides: Any) -> uuid.UUID:
        run_id = uuid.uuid4()
        fields: dict[str, Any] = {
            "scope": "public",
            "status": "queued",
            "attempts": 0,
            "cancel": False,
        } | overrides
        async with self.owner.unit_of_work() as session:
            await session.execute(
                text(
                    "INSERT INTO app.discovery_runs (id, scope, project_id, status, attempts, "
                    "cancel_requested, provider_mode, demo_replay, created_at, updated_at) VALUES "
                    "(:id, :scope, :project, :status, :attempts, :cancel, 'replay', true, :now, :now)"
                ),
                {
                    "id": run_id,
                    "scope": fields["scope"],
                    "project": self.project_id,
                    "status": fields["status"],
                    "attempts": fields["attempts"],
                    "cancel": fields["cancel"],
                    "now": self.clock.now(),
                },
            )
        return run_id

    async def row(self, run_id: uuid.UUID) -> Any:
        async with self.owner.unit_of_work() as session:
            return (
                await session.execute(
                    text("SELECT * FROM app.discovery_runs WHERE id = :i"), {"i": run_id}
                )
            ).one()

    async def audit(self, run_id: uuid.UUID) -> list[str]:
        async with self.owner.unit_of_work() as session:
            rows = await session.execute(
                text(
                    "SELECT event FROM app.audit_events WHERE subject_id = :i ORDER BY occurred_at, id"
                ),
                {"i": run_id},
            )
        return [r.event for r in rows]


@dataclass
class RecordingPipeline:
    """A test pipeline that records calls and can be told to misbehave once."""

    searches: list[uuid.UUID] = field(default_factory=list[uuid.UUID])
    analyses: list[uuid.UUID] = field(default_factory=list[uuid.UUID])
    on_search: Any = None
    on_analyse: Any = None
    needs_review: bool = False

    async def search(self, run: RunView, store: RunStore) -> None:
        self.searches.append(run.id)
        if self.on_search is not None:
            await self.on_search(run, store)

    async def analyse(self, run: RunView, store: RunStore) -> AnalysisResult:
        self.analyses.append(run.id)
        if self.on_analyse is not None:
            await self.on_analyse(run, store)
        return AnalysisResult(needs_review=self.needs_review)


@pytest.fixture
async def discovery(role_urls: dict[str, URL]) -> AsyncIterator[Discovery]:
    owner_engine = build_engine(role_urls["owner"], application_name="o", statement_timeout_ms=8000)
    worker_engine = build_engine(
        role_urls["shaidago_worker"], application_name="w", statement_timeout_ms=8000
    )
    clock = ManualClock(START)
    owner = Plain(owner_engine)
    async with owner.unit_of_work() as session:
        slug = f"synthetic-{uuid.uuid4().hex[:10]}"
        project_id = await insert_project(session, slug=slug)
    worker = Database(worker_engine)
    yield Discovery(
        owner, worker, clock, RunStore(worker, clock, Uuid7Generator(clock)), project_id, slug
    )
    await owner_engine.dispose()
    await worker_engine.dispose()

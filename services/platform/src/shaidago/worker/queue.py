"""Enqueueing discovery jobs from the API: identifiers only, through the same broker."""

import asyncio
from typing import Protocol
from uuid import UUID

from shaidago.worker.broker import DiscoveryActors, build_redis_broker, enqueue, register_actors
from shaidago.worker.envelope import CONFIG_VERSION, JobEnvelope
from shaidago.worker.process import Outcome


class JobQueue(Protocol):
    async def enqueue_discovery(self, run_id: UUID) -> None:
        """Send one job. Raises if the broker is unavailable; delivering twice is harmless."""
        ...


class DramatiqJobQueue:
    def __init__(self, actors: DiscoveryActors) -> None:
        self._actors = actors

    async def enqueue_discovery(self, run_id: UUID) -> None:
        envelope = JobEnvelope(run_id=run_id, config_version=CONFIG_VERSION)
        await asyncio.to_thread(enqueue, self._actors, envelope)


async def _never_run(*_: object) -> Outcome:  # pragma: no cover - the API never consumes jobs
    raise RuntimeError("the API process does not run jobs")


def build_producer_queue(redis_url: str) -> DramatiqJobQueue:
    broker = build_redis_broker(redis_url)
    return DramatiqJobQueue(register_actors(broker, _never_run, _never_run))

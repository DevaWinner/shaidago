"""Dramatiq broker and actor configuration: namespaces, limits, bounded retries, dead letters.

Retries use exponential backoff and stop at ``MAX_RETRIES``; a message that exhausts them moves
to the broker's dead-letter queue (kept for inspection) and its run is marked ``failed`` with the
safe code ``retries_exhausted`` by ``on_retries_exhausted``, so an exhausted job is visible in the
product and never retried forever. Messages carry a ``JobEnvelope`` and nothing else.
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final
from uuid import UUID, uuid4

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.brokers.stub import StubBroker

from shaidago.worker.envelope import (
    ACTOR_NAME,
    QUEUE_NAME,
    InvalidEnvelopeError,
    JobEnvelope,
    parse_envelope,
    to_message,
)
from shaidago.worker.process import EXHAUSTED, Outcome

NAMESPACE: Final = "shaidago"
MAX_RETRIES: Final = 4
MIN_BACKOFF_MS: Final = 2_000
MAX_BACKOFF_MS: Final = 120_000
TIME_LIMIT_MS: Final = 180_000
MAX_AGE_MS: Final = 3_600_000

RunHandler = Callable[[UUID, str], Any]
"""Async callable ``(run_id, owner) -> Outcome`` supplied by the worker runtime."""
ExhaustedHandler = Callable[[UUID, str], Any]
"""Async callable ``(run_id, failure_code)`` marking the run failed."""


def build_redis_broker(url: str) -> dramatiq.Broker:
    return RedisBroker(url=url, namespace=NAMESPACE)


def build_stub_broker() -> StubBroker:
    return StubBroker()


@dataclass(frozen=True)
class DiscoveryActors:
    run: Any
    exhausted: Any


EXHAUSTED_ACTOR: Final = "run_discovery_exhausted"


def register_actors(  # noqa: PLR0913 - retry limits are tunable for tests, not for callers
    broker: dramatiq.Broker,
    handle: RunHandler,
    exhausted: ExhaustedHandler,
    *,
    max_retries: int = MAX_RETRIES,
    min_backoff_ms: int = MIN_BACKOFF_MS,
    max_backoff_ms: int = MAX_BACKOFF_MS,
) -> DiscoveryActors:
    """Define the discovery actors on ``broker``. A message must be a valid envelope."""
    dramatiq.set_broker(broker)

    def run_discovery(payload: dict[str, object]) -> str:
        try:
            envelope = parse_envelope(payload)
        except InvalidEnvelopeError:
            return "invalid_envelope"  # never retried: the same bytes can never become valid
        outcome: Outcome = asyncio.run(handle(envelope.run_id, f"worker-{uuid4().hex[:12]}"))
        return outcome.value

    def run_discovery_exhausted(message_data: dict[str, Any], _exception: dict[str, Any]) -> None:
        kwargs: dict[str, Any] = message_data.get("kwargs") or {}
        try:
            envelope = parse_envelope(kwargs.get("payload"))
        except InvalidEnvelopeError:
            return
        asyncio.run(exhausted(envelope.run_id, EXHAUSTED))

    define: Any = dramatiq.actor  # its stubs do not describe the options we pass
    exhausted_actor = define(
        run_discovery_exhausted,
        broker=broker,
        actor_name=EXHAUSTED_ACTOR,
        queue_name=QUEUE_NAME,
        max_retries=max_retries,
        min_backoff=min_backoff_ms,
        max_backoff=max_backoff_ms,
    )
    run_actor = define(
        run_discovery,
        broker=broker,
        actor_name=ACTOR_NAME,
        queue_name=QUEUE_NAME,
        max_retries=max_retries,
        min_backoff=min_backoff_ms,
        max_backoff=max_backoff_ms,
        time_limit=TIME_LIMIT_MS,
        max_age=MAX_AGE_MS,
        on_retry_exhausted=EXHAUSTED_ACTOR,
    )
    return DiscoveryActors(run_actor, exhausted_actor)


def enqueue(actors: DiscoveryActors, envelope: JobEnvelope) -> None:
    actors.run.send(payload=to_message(envelope))

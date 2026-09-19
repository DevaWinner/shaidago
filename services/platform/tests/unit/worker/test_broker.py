"""Dramatiq wiring on the stub broker: delivery, invalid messages, bounded retries, dead letters."""

import threading
from uuid import UUID, uuid4, uuid7

import structlog
from dramatiq import Worker
from dramatiq.brokers.stub import StubBroker

from shaidago.worker.broker import (
    QUEUE_NAME,
    DiscoveryActors,
    build_stub_broker,
    enqueue,
    register_actors,
)
from shaidago.worker.envelope import JobEnvelope
from shaidago.worker.process import EXHAUSTED, Outcome, TransientStageError


class Recorder:
    def __init__(self, fail_times: int = 0) -> None:
        self.handled: list[UUID] = []
        self.exhausted: list[tuple[UUID, str]] = []
        self.fail_times = fail_times
        self.done = threading.Event()

    async def handle(self, run_id: UUID, owner: str) -> Outcome:
        del owner
        self.handled.append(run_id)
        if len(self.handled) <= self.fail_times:
            raise TransientStageError
        return Outcome.COMPLETED

    async def give_up(self, run_id: UUID, code: str) -> None:
        self.exhausted.append((run_id, code))


def run_worker(
    recorder: Recorder, envelopes: list[JobEnvelope], **limits: int
) -> tuple[StubBroker, DiscoveryActors]:
    broker = build_stub_broker()
    broker.emit_after("process_boot")
    actors = register_actors(
        broker, recorder.handle, recorder.give_up,
        min_backoff_ms=10, max_backoff_ms=20, **({"max_retries": 2} | limits),
    )  # fmt: skip
    worker = Worker(broker, worker_timeout=50, worker_threads=1)
    worker.start()
    try:
        for envelope in envelopes:
            enqueue(actors, envelope)
        broker.join(QUEUE_NAME, fail_fast=False)
        worker.join()
    finally:
        worker.stop()
    return broker, actors


def envelope() -> JobEnvelope:
    return JobEnvelope(run_id=uuid4(), config_version="discovery-v1")


def test_the_worker_binds_the_originating_request_id_for_its_logs() -> None:
    request_id = str(uuid7())
    recorder = Recorder()
    captured: list[object] = []

    class Capture(Recorder):
        async def handle(self, run_id: UUID, owner: str) -> Outcome:
            captured.append(structlog.contextvars.get_contextvars().get("request_id"))
            return await super().handle(run_id, owner)

    capture = Capture()
    run_worker(
        capture, [JobEnvelope(run_id=uuid4(), config_version="discovery-v1", request_id=request_id)]
    )
    assert captured == [request_id]
    # The binding does not leak into the next job or the process context.
    assert structlog.contextvars.get_contextvars().get("request_id") is None
    run_worker(recorder, [envelope()])
    assert recorder.handled


def test_a_valid_message_is_delivered_once_with_only_its_identifiers() -> None:
    recorder = Recorder()
    message = envelope()
    run_worker(recorder, [message])
    assert recorder.handled == [message.run_id]
    assert recorder.exhausted == []


def test_an_invalid_message_is_acknowledged_and_never_retried() -> None:
    recorder = Recorder()
    broker = build_stub_broker()
    actors = register_actors(
        broker, recorder.handle, recorder.give_up, min_backoff_ms=10, max_backoff_ms=20
    )
    worker = Worker(broker, worker_timeout=50, worker_threads=1)
    worker.start()
    try:
        actors.run.send(payload={"run_id": "nope", "report_text": "FICTIONAL private text"})
        broker.join(QUEUE_NAME, fail_fast=False)
        worker.join()
    finally:
        worker.stop()
    assert recorder.handled == []
    assert broker.dead_letters == []


def test_a_transient_failure_is_retried_and_then_succeeds() -> None:
    recorder = Recorder(fail_times=1)
    message = envelope()
    broker, _ = run_worker(recorder, [message])
    assert recorder.handled == [message.run_id, message.run_id]
    assert broker.dead_letters == []
    assert recorder.exhausted == []


def test_retries_are_bounded_then_dead_lettered_and_the_run_is_failed() -> None:
    recorder = Recorder(fail_times=100)
    message = envelope()
    broker, _ = run_worker(recorder, [message], max_retries=2)
    assert len(recorder.handled) == 3  # the first attempt and two retries, never more
    assert len(broker.dead_letters) == 1
    assert recorder.exhausted == [(message.run_id, EXHAUSTED)]

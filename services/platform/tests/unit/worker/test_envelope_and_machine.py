"""The job envelope carries identifiers only; the discovery machine matches the contract."""

import json
from itertools import product
from uuid import uuid4, uuid7

import pytest

from shaidago.shared.vocabulary import CONTRACT
from shaidago.worker.envelope import (
    ENVELOPE_VERSION,
    InvalidEnvelopeError,
    JobEnvelope,
    parse_envelope,
    to_message,
)
from shaidago.worker.machine import (
    TRANSITIONS,
    DiscoveryTransitionNotAllowedError,
    find_transition,
)

MACHINE = json.loads(CONTRACT.read_text("utf-8"))["state_machines"]["discovery_status"]
STATUSES = ("queued", "searching", "analysing", "needs_review", "complete", "failed", "cancelled")
COMMANDS = tuple(dict.fromkeys(t.command for t in TRANSITIONS))
ACTORS = ("worker", "reporter", "reviewer", "admin", "system")
ALLOWED = {
    (t["from"], t["command"], a): t["to"] for t in MACHINE["transitions"] for a in t["actors"]
}


def test_a_round_trip_keeps_only_identifiers_and_a_version() -> None:
    envelope = JobEnvelope(run_id=uuid4(), config_version="discovery-v1")
    message = to_message(envelope)
    assert set(message) == {"envelope_version", "run_id", "config_version"}
    assert parse_envelope(message) == envelope
    assert message["envelope_version"] == ENVELOPE_VERSION


def test_a_round_trip_carries_the_originating_request_id() -> None:
    request_id = str(uuid7())
    envelope = JobEnvelope(run_id=uuid4(), config_version="discovery-v1", request_id=request_id)
    message = to_message(envelope)
    assert message["request_id"] == request_id
    assert parse_envelope(message) == envelope


@pytest.mark.parametrize("value", ["not-a-uuid", "", "  ", "0" * 64, "'; DROP TABLE app.reports--"])
def test_a_malformed_request_id_is_refused(value: str) -> None:
    message = to_message(JobEnvelope(run_id=uuid4(), config_version="discovery-v1"))
    with pytest.raises(InvalidEnvelopeError):
        parse_envelope(message | {"request_id": value})


@pytest.mark.parametrize(
    "extra",
    [
        {"report_text": "FICTIONAL private text"},
        {"tracking_code": "SG-AAAAA-BBBBB-CCCCC-DDDDD-E"},
        {"query": "fictional query"},
        {"contact": "someone@example.test"},
        {"attachment": "bytes"},
    ],
)
def test_a_message_cannot_carry_private_fields(extra: dict[str, str]) -> None:
    message = to_message(JobEnvelope(run_id=uuid4(), config_version="discovery-v1")) | extra
    with pytest.raises(InvalidEnvelopeError):
        parse_envelope(message)


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "run",
        [],
        {},
        {"run_id": "not-a-uuid", "config_version": "v1", "envelope_version": 1},
        {"run_id": str(uuid4()), "config_version": "Bad Version!", "envelope_version": 1},
        {"run_id": str(uuid4()), "config_version": "v1", "envelope_version": 99},
        {"run_id": 5, "config_version": "v1", "envelope_version": 1},
    ],
)
def test_malformed_messages_are_refused_without_echoing_them(raw: object) -> None:
    with pytest.raises(InvalidEnvelopeError) as raised:
        parse_envelope(raw)
    assert "FICTIONAL" not in str(raised.value)


def test_the_table_is_a_literal_copy_of_the_contract() -> None:
    assert [
        (t.from_status, t.command, t.to_status, sorted(t.actors), t.audit_event)
        for t in TRANSITIONS
    ] == [
        (t["from"], t["command"], t["to"], sorted(t["actors"]), t["audit_event"])
        for t in MACHINE["transitions"]
    ]


@pytest.mark.parametrize(("status", "command", "actor"), list(product(STATUSES, COMMANDS, ACTORS)))
def test_every_status_command_and_actor_pair_matches_the_contract(
    status: str, command: str, actor: str
) -> None:
    expected = ALLOWED.get((status, command, actor))
    if expected is None:
        with pytest.raises(DiscoveryTransitionNotAllowedError):
            find_transition(status, command, actor)
    else:
        assert find_transition(status, command, actor).to_status == expected


def test_finished_runs_allow_nothing() -> None:
    for status, command, actor in product(("complete", "failed", "cancelled"), COMMANDS, ACTORS):
        with pytest.raises(DiscoveryTransitionNotAllowedError):
            find_transition(status, command, actor)

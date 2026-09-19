"""The report state machine: parity with the contract and an exhaustive state/command/actor matrix."""

import json
from itertools import product
from typing import get_args

import pytest

from shaidago.api.v1.reviewer_decisions import Command
from shaidago.review.state_machine import (
    ACTORS,
    COMMANDS,
    STATUSES,
    TRANSITIONS,
    TransitionNotAllowedError,
    find_transition,
)
from shaidago.shared.vocabulary import CONTRACT, values

CONTRACT_MACHINE = json.loads(CONTRACT.read_text("utf-8"))["state_machines"]["report_status"]
ALLOWED = {
    (t["from"], t["command"], actor): t["to"]
    for t in CONTRACT_MACHINE["transitions"]
    for actor in t["actors"]
}


def test_the_table_is_a_literal_copy_of_the_contract() -> None:
    assert [
        (t.from_status, t.command, t.to_status, sorted(t.actors), t.audit_event)
        for t in TRANSITIONS
    ] == [
        (t["from"], t["command"], t["to"], sorted(t["actors"]), t["audit_event"])
        for t in CONTRACT_MACHINE["transitions"]
    ]


def test_statuses_and_actors_match_the_contract() -> None:
    assert values("report_status") == STATUSES
    assert set(json.loads(CONTRACT.read_text("utf-8"))["actors"]) == set(ACTORS)


def test_the_api_command_type_lists_every_command() -> None:
    assert set(get_args(Command)) == set(COMMANDS)


@pytest.mark.parametrize(("status", "command", "actor"), list(product(STATUSES, COMMANDS, ACTORS)))
def test_every_state_command_and_actor_pair_is_allowed_only_if_the_contract_says_so(
    status: str, command: str, actor: str
) -> None:
    expected = ALLOWED.get((status, command, actor))
    if expected is None:
        with pytest.raises(TransitionNotAllowedError):
            find_transition(status, command, actor)
    else:
        assert find_transition(status, command, actor).to_status == expected


@pytest.mark.parametrize("status", ["", "published", "CLOSED", "unknown"])
def test_an_unknown_status_allows_nothing(status: str) -> None:
    for command, actor in product(COMMANDS, ACTORS):
        with pytest.raises(TransitionNotAllowedError):
            find_transition(status, command, actor)


def test_an_unknown_command_or_actor_is_refused() -> None:
    with pytest.raises(TransitionNotAllowedError):
        find_transition("received", "publish", "reviewer")
    with pytest.raises(TransitionNotAllowedError):
        find_transition("received", "start_review", "anonymous")


def test_no_transition_publishes_and_only_the_reporter_records_a_follow_up() -> None:
    assert "publish" not in " ".join(COMMANDS)
    assert {t.command: t.actors for t in TRANSITIONS if t.command == "record_follow_up"} == {
        "record_follow_up": frozenset({"reporter"})
    }
    assert all(t.to_status != "published" for t in TRANSITIONS)

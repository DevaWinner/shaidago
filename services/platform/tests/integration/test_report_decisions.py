"""Reviewer decisions (BE-071): state machine over HTTP, stale views, history, audit, privacy."""

import asyncio
import uuid
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from shaidago.review.state_machine import COMMANDS, STATUSES, TRANSITIONS
from tests.integration.report_support import CANARY
from tests.integration.reviewer_support import ReviewWorld

REASON = "FICTIONAL internal reason: the fictional photo matches the fictional register."
QUEUE = "/v1/reviewer/reports"


def transitions(report_id: uuid.UUID) -> str:
    return f"{QUEUE}/{report_id}/status-transitions"


async def state(world: ReviewWorld, report_id: uuid.UUID) -> tuple[str, int]:
    [row] = await world.rows("SELECT status, version FROM app.reports WHERE id = :r", r=report_id)
    return row.status, row.version


async def event_count(world: ReviewWorld, report_id: uuid.UUID) -> int:
    [row] = await world.rows(
        "SELECT count(*) AS n FROM app.report_status_events WHERE report_id = :r", r=report_id
    )
    return int(row.n)


PATHS = {
    "needs_information": ("needs_information",),
    "under_review": ("under_review",),
    "verified_for_public_update": ("under_review", "verified_for_public_update"),
    "referred": ("under_review", "referred"),
    "closed": ("closed",),
}


async def put_in_status(world: ReviewWorld, report_id: uuid.UUID, status: str) -> None:
    """Fictional setup along a legal path: each step is one event plus the matching projection."""
    for step in PATHS[status]:
        world.advance(1)
        async with world.owner.unit_of_work() as session:
            old = (
                await session.execute(
                    text("SELECT status FROM app.reports WHERE id = :r"), {"r": report_id}
                )
            ).scalar_one()
            await session.execute(
                text(
                    "INSERT INTO app.report_status_events (id, report_id, previous_status, "
                    "new_status, public_message, actor_type, occurred_at) VALUES "
                    "(gen_random_uuid(), :r, :old, :new, 'fictional setup', 'reviewer', :at)"
                ),
                {"r": report_id, "old": old, "new": step, "at": world.clock.now()},
            )
            await session.execute(
                text("UPDATE app.reports SET status = :new, status_updated_at = :at WHERE id = :r"),
                {"r": report_id, "new": step, "at": world.clock.now()},
            )


async def lookup(world: ReviewWorld, code: str) -> dict[str, object]:
    async with world.client() as client:
        response = await client.post("/v1/report-status:lookup", json={"code": code})
    assert response.status_code == 200, response.text
    return response.json()  # type: ignore[no-any-return]


def decision(command: str, status: str, version: int, **extra: str | None) -> dict[str, Any]:
    return {"command": command, "expected_status": status, "expected_version": version} | extra


async def test_a_decision_writes_one_event_moves_the_projection_and_publishes_nothing(
    review_world: ReviewWorld,
) -> None:
    code, report_id = await review_world.submit()
    actor = await review_world.signed_in()
    updates_before = await review_world.rows("SELECT count(*) AS n FROM app.project_updates")
    response = await review_world.call(
        actor, "POST", transitions(report_id), json=decision("start_review", "received", 1)
    )
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    result = response.json()
    assert (result["previous_status"], result["status"], result["version"]) == (
        "received",
        "under_review",
        2,
    )
    assert result["published"] is False
    assert await state(review_world, report_id) == ("under_review", 2)
    assert await event_count(review_world, report_id) == 2
    after = await review_world.rows("SELECT count(*) AS n FROM app.project_updates")
    assert after[0].n == updates_before[0].n
    assert (await lookup(review_world, code))["status"] == "under_review"
    [audit] = await review_world.rows(
        "SELECT actor_id, details FROM app.audit_events "
        "WHERE event = 'report_status_changed' AND subject_id = :r",
        r=report_id,
    )
    assert audit.actor_id == actor.record.id
    assert audit.details["command"] == "start_review"
    assert audit.details["new_version"] == 2


@pytest.mark.parametrize("role", ["reviewer", "admin"])
async def test_every_state_and_command_over_http_matches_the_transition_table(
    review_world: ReviewWorld, role: str
) -> None:
    actor = await review_world.signed_in(role)
    allowed = {(t.from_status, t.command): t.to_status for t in TRANSITIONS if role in t.actors}
    for status in STATUSES:
        for command in COMMANDS:
            _, report_id = await review_world.submit()
            if status != "received":
                await put_in_status(review_world, report_id, status)
            review_world.advance(1)
            _, version = await state(review_world, report_id)
            extra = {"internal_reason": REASON} if command == "reopen" else {}
            response = await review_world.call(
                actor,
                "POST",
                transitions(report_id),
                json=decision(command, status, version, **extra),
            )
            if (status, command) in allowed:
                assert response.status_code == 200, (status, command, response.text)
                assert response.json()["status"] == allowed[(status, command)]
            else:
                assert response.status_code == 409, (status, command)
                assert response.json()["code"] == "report_status_transition_not_allowed"
                assert await state(review_world, report_id) == (status, version)


async def test_a_refused_command_is_audited_and_changes_nothing(review_world: ReviewWorld) -> None:
    _, report_id = await review_world.submit()
    actor = await review_world.signed_in()
    response = await review_world.call(
        actor, "POST", transitions(report_id), json=decision("close", "under_review", 1)
    )
    assert response.status_code == 409
    assert response.json()["code"] == "report_version_conflict"
    response = await review_world.call(
        actor, "POST", transitions(report_id), json=decision("refer", "received", 1)
    )
    assert response.json()["code"] == "report_status_transition_not_allowed"
    [audit] = await review_world.rows(
        "SELECT outcome, details FROM app.audit_events "
        "WHERE event = 'report_status_change_denied' AND subject_id = :r",
        r=report_id,
    )
    assert audit.outcome == "denied"
    assert audit.details == {"command": "refer", "status": "received"}
    assert await event_count(review_world, report_id) == 1


async def test_the_reviewer_cannot_perform_the_reporters_transition(
    review_world: ReviewWorld,
) -> None:
    _, report_id = await review_world.submit()
    await put_in_status(review_world, report_id, "needs_information")
    actor = await review_world.signed_in("admin")
    _, version = await state(review_world, report_id)
    response = await review_world.call(
        actor,
        "POST",
        transitions(report_id),
        json=decision("record_follow_up", "needs_information", version),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "report_status_transition_not_allowed"


async def test_a_stale_view_is_refused_and_writes_nothing(review_world: ReviewWorld) -> None:
    _, report_id = await review_world.submit()
    first = await review_world.signed_in()
    second = await review_world.signed_in()
    ok = await review_world.call(
        first, "POST", transitions(report_id), json=decision("start_review", "received", 1)
    )
    assert ok.status_code == 200
    stale = await review_world.call(
        second, "POST", transitions(report_id), json=decision("close", "received", 1)
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "report_version_conflict"
    right_status_wrong_version = await review_world.call(
        second, "POST", transitions(report_id), json=decision("close", "under_review", 1)
    )
    assert right_status_wrong_version.json()["code"] == "report_version_conflict"
    assert await state(review_world, report_id) == ("under_review", 2)
    assert await event_count(review_world, report_id) == 2


async def test_two_concurrent_decisions_on_one_version_apply_exactly_once(
    review_world: ReviewWorld,
) -> None:
    _, report_id = await review_world.submit()
    actors = [await review_world.signed_in() for _ in range(4)]
    responses = await asyncio.gather(
        *(
            review_world.call(
                actor,
                "POST",
                transitions(report_id),
                json=decision(command, "received", 1),
            )
            for actor, command in zip(
                actors,
                ("start_review", "close", "request_information", "start_review"),
                strict=True,
            )
        )
    )
    assert sorted(r.status_code for r in responses) == [200, 409, 409, 409]
    assert {r.json()["code"] for r in responses if r.status_code == 409} == {
        "report_version_conflict"
    }
    assert await event_count(review_world, report_id) == 2
    assert (await state(review_world, report_id))[1] == 2


async def test_the_private_reason_is_encrypted_and_never_reaches_the_reporter(
    review_world: ReviewWorld,
) -> None:
    code, report_id = await review_world.submit()
    actor = await review_world.signed_in()
    response = await review_world.call(
        actor,
        "POST",
        transitions(report_id),
        json=decision("start_review", "received", 1, internal_reason=REASON),
    )
    assert response.status_code == 200
    assert REASON not in response.text
    [row] = await review_world.rows(
        "SELECT reason_ciphertext, public_message FROM app.report_status_events "
        "WHERE report_id = :r AND new_status = 'under_review'",
        r=report_id,
    )
    assert REASON.encode() not in bytes(row.reason_ciphertext)
    assert REASON not in row.public_message
    tracked = await lookup(review_world, code)
    assert REASON not in str(tracked)
    assert CANARY not in str(tracked)
    detail = (await review_world.call(actor, "GET", f"{QUEUE}/{report_id}")).json()
    assert [e["internal_reason"] for e in detail["events"]] == [None, REASON]
    [audit] = await review_world.rows(
        "SELECT details FROM app.audit_events WHERE event = 'report_status_changed' "
        "AND subject_id = :r",
        r=report_id,
    )
    assert REASON not in str(audit.details)
    assert audit.details["reason_recorded"] is True


async def test_the_reporter_message_is_separate_from_the_reason(review_world: ReviewWorld) -> None:
    code, report_id = await review_world.submit()
    actor = await review_world.signed_in()
    await review_world.call(
        actor,
        "POST",
        transitions(report_id),
        json=decision(
            "start_review",
            "received",
            1,
            reporter_message="A reviewer is looking at your report now.",
            internal_reason=REASON,
        ),
    )
    tracked = await lookup(review_world, code)
    assert tracked["message"] == "A reviewer is looking at your report now."


async def test_reopening_needs_a_private_reason_and_keeps_all_history(
    review_world: ReviewWorld,
) -> None:
    _, report_id = await review_world.submit()
    actor = await review_world.signed_in()
    await put_in_status(review_world, report_id, "closed")
    _, version = await state(review_world, report_id)
    missing = await review_world.call(
        actor, "POST", transitions(report_id), json=decision("reopen", "closed", version)
    )
    assert missing.status_code == 422
    assert missing.json()["errors"] == [{"field": "internal_reason", "code": "required"}]
    before = await event_count(review_world, report_id)
    reopened = await review_world.call(
        actor,
        "POST",
        transitions(report_id),
        json=decision("reopen", "closed", version, internal_reason=REASON),
    )
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "under_review"
    assert await event_count(review_world, report_id) == before + 1
    [audit] = await review_world.rows(
        "SELECT actor_id FROM app.audit_events WHERE event = 'report_status_reopened' "
        "AND subject_id = :r",
        r=report_id,
    )
    assert audit.actor_id == actor.record.id


async def test_bad_text_is_a_validation_failure_before_anything_is_written(
    review_world: ReviewWorld,
) -> None:
    _, report_id = await review_world.submit()
    actor = await review_world.signed_in()
    for extra in (
        {"reporter_message": "no"},
        {"reporter_message": "bell\x07 character in the message"},
        {"internal_reason": "x" * 1100},
    ):
        response = await review_world.call(
            actor,
            "POST",
            transitions(report_id),
            json=decision("start_review", "received", 1, **extra),
        )
        assert response.status_code == 422, extra
    for bad in (
        {"command": "publish", "expected_status": "received", "expected_version": 1},
        {"command": "close", "expected_status": "published", "expected_version": 1},
        {"command": "close", "expected_status": "received", "expected_version": 0},
        {"command": "close", "expected_status": "received", "expected_version": 1, "status": "x"},
    ):
        response = await review_world.call(actor, "POST", transitions(report_id), json=bad)
        assert response.status_code == 422, bad
    assert await state(review_world, report_id) == ("received", 1)
    assert await event_count(review_world, report_id) == 1


async def test_a_decision_needs_a_session_csrf_and_a_known_report(
    review_world: ReviewWorld,
) -> None:
    _, report_id = await review_world.submit()
    actor = await review_world.signed_in()
    payload = decision("start_review", "received", 1)
    anonymous = await review_world.call(None, "POST", transitions(report_id), json=payload)
    assert anonymous.status_code == 401
    no_csrf = await review_world.call(
        actor, "POST", transitions(report_id), json=payload, csrf=False
    )
    assert no_csrf.status_code == 403
    assert no_csrf.json()["code"] == "csrf_invalid"
    unknown = await review_world.call(actor, "POST", transitions(uuid.uuid4()), json=payload)
    assert unknown.status_code == 404
    assert await state(review_world, report_id) == ("received", 1)


async def test_status_history_cannot_be_edited_or_deleted_even_by_the_reviewer_role(
    review_world: ReviewWorld,
) -> None:
    _, report_id = await review_world.submit()
    engine = review_world.app.state.dependencies.reviewer_database.engine
    for statement in (
        "UPDATE app.report_status_events SET public_message = 'edited' WHERE report_id = :r",
        "DELETE FROM app.report_status_events WHERE report_id = :r",
    ):
        async with engine.connect() as connection:
            with pytest.raises(DBAPIError):
                await connection.execute(text(statement), {"r": report_id})
    assert await event_count(review_world, report_id) == 1


async def test_a_reporter_answer_that_resumes_review_also_raises_the_version(
    review_world: ReviewWorld,
) -> None:
    code, report_id = await review_world.submit()
    actor = await review_world.signed_in()
    asked = await review_world.call(
        actor,
        "POST",
        f"{QUEUE}/{report_id}/follow-up-questions",
        json={"question": "FICTIONAL question: which day was the site closed?"},
    )
    assert asked.status_code == 201
    question_id = asked.json()["question_id"]
    moved = await review_world.call(
        actor,
        "POST",
        transitions(report_id),
        json=decision("request_information", "received", 1),
    )
    assert moved.json()["version"] == 2
    tracked = await lookup(review_world, code)
    assert [q["state"] for q in tracked["follow_up_questions"]] == ["open"]  # type: ignore[index]
    review_world.advance(1)  # the reporter's event must be later than the reviewer's
    async with review_world.client() as client:
        answered = await client.post(
            "/v1/report-status:answer-follow-up",
            json={"question_id": question_id, "kind": "skipped", "code": code},
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )
    assert answered.status_code == 200
    assert await state(review_world, report_id) == ("under_review", 3)


async def test_questions_can_be_asked_withdrawn_and_are_bounded(review_world: ReviewWorld) -> None:
    code, report_id = await review_world.submit()
    actor = await review_world.signed_in()
    url = f"{QUEUE}/{report_id}/follow-up-questions"
    bad = await review_world.call(actor, "POST", url, json={"question": "no"})
    assert bad.status_code == 422
    first = await review_world.call(
        actor, "POST", url, json={"question": "FICTIONAL question: when did you see it?"}
    )
    question_id = first.json()["question_id"]
    assert [q["state"] for q in (await _tracked(review_world, code))["follow_up_questions"]] == [  # type: ignore[index]
        "open"
    ]
    gone = await review_world.call(actor, "POST", f"{url}/{question_id}:withdraw")
    assert gone.status_code == 204
    assert (await _tracked(review_world, code))["follow_up_questions"] == []
    again = await review_world.call(actor, "POST", f"{url}/{question_id}:withdraw")
    assert again.status_code == 404
    for n in range(10):
        made = await review_world.call(
            actor, "POST", url, json={"question": f"FICTIONAL question number {n}?"}
        )
        assert made.status_code == 201
    over = await review_world.call(
        actor, "POST", url, json={"question": "FICTIONAL question eleven?"}
    )
    assert over.status_code == 409
    events = await review_world.rows(
        "SELECT event FROM app.audit_events WHERE subject_id = :r AND event LIKE "
        "'report_follow_up_question_%'",
        r=report_id,
    )
    assert {e.event for e in events} == {
        "report_follow_up_question_added",
        "report_follow_up_question_withdrawn",
    }


async def test_no_question_can_be_added_to_a_closed_report(review_world: ReviewWorld) -> None:
    _, report_id = await review_world.submit()
    await put_in_status(review_world, report_id, "closed")
    actor = await review_world.signed_in()
    response = await review_world.call(
        actor,
        "POST",
        f"{QUEUE}/{report_id}/follow-up-questions",
        json={"question": "FICTIONAL question after closing?"},
    )
    assert response.status_code == 409


async def _tracked(world: ReviewWorld, code: str) -> dict[str, object]:
    return await lookup(world, code)

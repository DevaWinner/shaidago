"""Follow-up answers: ownership, encryption, one answer per question, and no answer on tracking."""

import asyncio
import base64
import io
import logging
import uuid
from collections.abc import Callable
from dataclasses import replace
from datetime import timedelta
from typing import Any

import httpx
import pytest
import structlog
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError

from shaidago.auth.passwords import PasswordPolicy, PasswordVerifier
from shaidago.reports.follow_ups import RECEIVED_MESSAGE, read_answer
from shaidago.shared.clock import ManualClock
from shaidago.shared.crypto import EnvironmentKekWrapper, FieldCipher
from shaidago.shared.data_keys import DataKeyDestroyedError, DataKeyService
from shaidago.shared.database import Database, build_engine
from shaidago.shared.ids import Uuid7Generator
from shaidago.shared.logging import configure_logging
from tests.factories import KEY_A
from tests.integration.report_support import (
    CANARY,
    Harness,
    ask,
    report_id_for,
    set_status,
)

ANSWER = "FICTIONAL answer canary: the fictional contractor visited on a Tuesday."
QUESTION = "Which day of the week did you see the work stopped?"
ENDPOINT = "/v1/report-status:answer-follow-up"
PRIVILEGE = "42501"
FAST = PasswordVerifier(PasswordPolicy(time_cost=1, memory_cost_kib=1024, parallelism=1))


def prepare(harness: Harness) -> ManualClock:
    harness.app.state.dependencies = replace(
        harness.app.state.dependencies, password_verifier=FAST, lookup_minimum_seconds=0.0
    )
    clock = harness.app.state.dependencies.clock
    assert isinstance(clock, ManualClock)
    return clock


async def new_report(harness: Harness, **extra: str) -> str:
    response = await harness.post(harness.fields(**extra))
    assert response.status_code == 201
    return str(response.json()["tracking_code"])


async def needing_information(harness: Harness, questions: int = 1) -> tuple[str, list[uuid.UUID]]:
    """A report whose reviewer asked ``questions`` questions and moved it to needs_information."""
    clock = harness.app.state.dependencies.clock
    code = await new_report(harness)
    start = clock.now()
    ids = [
        await ask(harness, code, f"{QUESTION} ({n})", start + timedelta(seconds=n))
        for n in range(questions)
    ]
    await set_status(
        harness, code, "needs_information", "We need one more detail.", start + timedelta(minutes=1)
    )
    clock.set(start + timedelta(hours=1))  # the reporter answers later than the reviewer asked
    return code, ids


async def answer(
    harness: Harness,
    body: dict[str, Any],
    key: str | None = "",
    client: str | None = None,
) -> httpx.Response:
    headers = {"X-Shaidago-Client-Hmac": client or uuid.uuid4().hex * 2}
    if key is not None:
        headers["Idempotency-Key"] = key or str(uuid.uuid4())
    async with harness.client() as http:
        return await http.post(ENDPOINT, json=body, headers=headers)


def by_code(
    code: str, question: uuid.UUID, kind: str = "answered", text_: str | None = ANSWER
) -> dict[str, Any]:
    body: dict[str, Any] = {"code": code, "question_id": str(question), "kind": kind}
    if text_ is not None and kind == "answered":
        body["answer"] = text_
    return body


async def count(harness: Harness, sql: str) -> int:
    return int((await harness.rows(sql))[0][0])


async def test_an_answer_is_encrypted_acknowledged_and_moves_the_report_on(
    harness: Harness,
) -> None:
    prepare(harness)
    code, (question,) = await needing_information(harness)
    response = await answer(harness, by_code(code, question))
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {"acknowledged": True, "question_state": "answered"}
    assert ANSWER not in response.text
    row = (
        await harness.rows(
            "SELECT kind, answer_ciphertext, data_key_id FROM app.report_follow_up_answers "
            f"WHERE question_id = '{question}'"
        )
    )[0]
    assert row.kind == "answered"
    assert ANSWER.encode() not in bytes(row.answer_ciphertext)
    purposes = await harness.rows(
        f"SELECT purpose, owner_table FROM app.data_keys WHERE id = '{row.data_key_id}'"
    )
    assert tuple(purposes[0]) == ("follow_up_answers", "report_follow_up_answers")
    status = (
        await harness.rows(
            f"SELECT status FROM app.reports WHERE id = '{await report_id_for(harness, code)}'"
        )
    )[0][0]
    assert status == "under_review"
    event = (
        await harness.rows(
            "SELECT previous_status, new_status, actor_type, public_message "
            f"FROM app.report_status_events WHERE report_id = '{await report_id_for(harness, code)}' "
            "ORDER BY occurred_at DESC, id DESC LIMIT 1"
        )
    )[0]
    assert tuple(event) == ("needs_information", "under_review", "reporter", RECEIVED_MESSAGE)
    audit = await harness.rows(
        "SELECT actor_type, actor_id, details::text FROM app.audit_events "
        f"WHERE event = 'report_follow_up_received' AND subject_id = '{await report_id_for(harness, code)}'"
    )
    assert len(audit) == 1
    assert (audit[0][0], audit[0][1]) == ("reporter", None)
    assert ANSWER not in audit[0][2]


async def test_a_reviewer_can_decrypt_the_answer_and_shredding_removes_it(
    harness: Harness, role_urls: dict[str, URL]
) -> None:
    prepare(harness)
    code, (question,) = await needing_information(harness)
    assert (await answer(harness, by_code(code, question))).status_code == 200
    engine = build_engine(
        role_urls["shaidago_reviewer"], application_name="r", statement_timeout_ms=8000
    )
    clock = ManualClock(harness.app.state.dependencies.clock.now())
    try:
        async with Database(engine).unit_of_work() as session:
            keys = DataKeyService(
                session,
                EnvironmentKekWrapper({"kek-1": base64.b64decode(KEY_A)}, "kek-1"),
                clock,
                Uuid7Generator(clock),
            )
            assert await read_answer(session, keys, FieldCipher(), question) == ANSWER
    finally:
        await engine.dispose()
    async with harness.owner.unit_of_work() as session:
        clock2 = ManualClock(clock.now())
        keys = DataKeyService(
            session,
            EnvironmentKekWrapper({"kek-1": base64.b64decode(KEY_A)}, "kek-1"),
            clock2,
            Uuid7Generator(clock2),
        )
        answer_id = (
            await session.execute(
                text(
                    f"SELECT id FROM app.report_follow_up_answers WHERE question_id = '{question}'"
                )
            )
        ).scalar_one()
        assert await keys.destroy("report_follow_up_answers", answer_id, "follow_up_answers")
    async with harness.owner.unit_of_work() as session:
        keys = DataKeyService(
            session,
            EnvironmentKekWrapper({"kek-1": base64.b64decode(KEY_A)}, "kek-1"),
            clock,
            Uuid7Generator(clock),
        )
        with pytest.raises(DataKeyDestroyedError):
            await read_answer(session, keys, FieldCipher(), question)
        assert (
            await count(
                harness,
                f"SELECT count(*) FROM app.reports WHERE id = '{await report_id_for(harness, code)}'",
            )
            == 1
        )


async def test_tracking_shows_the_question_and_an_acknowledgement_but_never_the_answer(
    harness: Harness,
) -> None:
    prepare(harness)
    code, (question,) = await needing_information(harness)

    async def track() -> dict[str, Any]:
        async with harness.client() as http:
            result = await http.post(
                "/v1/report-status:lookup",
                json={"code": code},
                headers={"X-Shaidago-Client-Hmac": uuid.uuid4().hex * 2},
            )
        assert ANSWER not in result.text
        return dict(result.json())

    before = await track()
    assert before["status"] == "needs_information"
    assert before["next_action"] == "answer_follow_up"
    assert before["follow_up_questions"] == [
        {"question_id": str(question), "text": f"{QUESTION} (0)", "state": "open"}
    ]
    assert (await answer(harness, by_code(code, question))).status_code == 200
    after = await track()
    assert after["follow_up_questions"][0]["state"] == "answered"
    assert after["status"] == "under_review"
    assert set(after["follow_up_questions"][0]) == {"question_id", "text", "state"}


async def test_the_report_resumes_only_when_the_last_open_question_is_answered(
    harness: Harness,
) -> None:
    prepare(harness)
    code, (first, second) = await needing_information(harness, questions=2)
    report_id = await report_id_for(harness, code)
    assert (await answer(harness, by_code(code, first))).status_code == 200
    assert (await harness.rows(f"SELECT status FROM app.reports WHERE id = '{report_id}'"))[0][
        0
    ] == "needs_information"
    assert (await answer(harness, by_code(code, second, "skipped"))).status_code == 200
    assert (await harness.rows(f"SELECT status FROM app.reports WHERE id = '{report_id}'"))[0][
        0
    ] == "under_review"


async def test_an_answer_outside_needs_information_changes_no_status(harness: Harness) -> None:
    clock = prepare(harness)
    code = await new_report(harness)
    question = await ask(harness, code, QUESTION, clock.now())
    clock.advance(timedelta(minutes=5))
    events_before = await count(
        harness,
        f"SELECT count(*) FROM app.report_status_events WHERE report_id = '{await report_id_for(harness, code)}'",
    )
    assert (await answer(harness, by_code(code, question))).status_code == 200
    events_after = await count(
        harness,
        f"SELECT count(*) FROM app.report_status_events WHERE report_id = '{await report_id_for(harness, code)}'",
    )
    assert events_after == events_before
    assert (
        await harness.rows(
            f"SELECT status FROM app.reports WHERE id = '{await report_id_for(harness, code)}'"
        )
    )[0][0] == "received"


@pytest.mark.parametrize("kind", ["skipped", "unsafe"])
async def test_skipping_or_flagging_a_question_stores_no_text_and_no_key(
    harness: Harness, kind: str
) -> None:
    prepare(harness)
    code, (question,) = await needing_information(harness)
    keys_before = await count(
        harness, "SELECT count(*) FROM app.data_keys WHERE purpose = 'follow_up_answers'"
    )
    response = await answer(harness, by_code(code, question, kind))
    assert response.json() == {"acknowledged": True, "question_state": kind}
    row = (
        await harness.rows(
            f"SELECT kind, answer_ciphertext, data_key_id FROM app.report_follow_up_answers WHERE question_id = '{question}'"
        )
    )[0]
    assert tuple(row) == (kind, None, None)
    assert (
        await count(
            harness, "SELECT count(*) FROM app.data_keys WHERE purpose = 'follow_up_answers'"
        )
        == keys_before
    )


Body = dict[str, Any]
MUTATIONS: list[Callable[[Body], Body]] = [
    lambda b: {**b, "kind": "skipped"},  # text with a skip
    lambda b: {k: v for k, v in b.items() if k != "answer"},  # answered without text
    lambda b: {**b, "answer": ""},
    lambda b: {**b, "answer": "x" * 2001},
    lambda b: {**b, "handle": "SG-H-AAAA-AAAA", "passphrase": "x"},  # two credential styles
    lambda b: {k: v for k, v in b.items() if k != "code"},  # no credential
    lambda b: {**b, "extra": "field"},
    lambda b: {**b, "question_id": "not-a-uuid"},
]


@pytest.mark.parametrize("mutate", MUTATIONS)
async def test_malformed_answers_are_rejected_before_anything_is_stored(
    harness: Harness, mutate: Callable[[Body], Body]
) -> None:
    prepare(harness)
    code, (question,) = await needing_information(harness)
    response = await answer(harness, mutate(by_code(code, question)))
    assert response.status_code == 422
    assert ANSWER not in response.text
    assert (
        await count(
            harness,
            f"SELECT count(*) FROM app.report_follow_up_answers WHERE question_id = '{question}'",
        )
        == 0
    )


async def test_every_ownership_failure_is_the_same_generic_answer(harness: Harness) -> None:
    prepare(harness)
    clock = harness.app.state.dependencies.clock
    mine, (mine_q,) = await needing_information(harness)
    _theirs, (theirs_q,) = await needing_information(harness)
    done, (done_q,) = await needing_information(harness)
    assert (await answer(harness, by_code(done, done_q))).status_code == 200
    withdrawn_q = await ask(harness, mine, "A withdrawn question?", clock.now())
    async with harness.owner.unit_of_work() as session:
        await session.execute(
            text(
                f"UPDATE app.report_follow_up_questions SET withdrawn_at = now() WHERE id = '{withdrawn_q}'"
            )
        )
    other_valid_code = await new_report(harness)
    attempts = {
        "someone else's question": by_code(mine, theirs_q),
        "unknown question": by_code(mine, uuid.uuid4()),
        "already answered": by_code(done, done_q),
        "withdrawn question": by_code(mine, withdrawn_q),
        "unknown code": by_code(other_valid_code, mine_q),
        "malformed code": by_code("not a code", mine_q),
        "empty code": by_code("", mine_q),
    }
    seen: dict[str, tuple[int, dict[str, Any]]] = {}
    for label, body in attempts.items():
        response = await answer(harness, body)
        payload = response.json()
        payload.pop("request_id", None)
        seen[label] = (response.status_code, payload)
        assert ANSWER not in response.text
    assert len({repr(v) for v in seen.values()}) == 1, seen
    assert next(iter(seen.values()))[0] == 404
    assert next(iter(seen.values()))[1]["code"] == "tracking_code_not_recognised"
    assert (
        await count(
            harness,
            f"SELECT count(*) FROM app.report_follow_up_answers WHERE question_id IN ('{mine_q}', '{theirs_q}', '{withdrawn_q}')",
        )
        == 0
    )
    assert await count(
        harness,
        "SELECT count(*) FROM app.data_keys WHERE purpose = 'follow_up_answers' AND owner_table = 'report_follow_up_answers'",
    ) == await count(
        harness, "SELECT count(*) FROM app.report_follow_up_answers WHERE kind = 'answered'"
    ), "a refused answer leaves no orphan key"


async def test_a_reporter_handle_can_answer_only_its_own_questions(harness: Harness) -> None:
    prepare(harness)
    async with harness.client() as http:
        made = [
            (
                await http.post(
                    "/v1/reporter-handles",
                    headers={
                        "Idempotency-Key": str(uuid.uuid4()),
                        "X-Shaidago-Client-Hmac": uuid.uuid4().hex * 2,
                    },
                )
            ).json()
            for _ in range(2)
        ]
    mine, other = made
    posted = await harness.post(
        harness.fields(reporter_handle=mine["handle"], reporter_passphrase=mine["passphrase"]),
        headers={"X-Shaidago-Client-Hmac": uuid.uuid4().hex * 2},
    )
    code = posted.json()["tracking_code"]
    clock = harness.app.state.dependencies.clock
    question = await ask(harness, code, QUESTION, clock.now())
    await set_status(
        harness, code, "needs_information", "One detail please.", clock.now() + timedelta(minutes=1)
    )
    clock.advance(timedelta(hours=1))

    def with_handle(who: dict[str, str], passphrase: str | None = None) -> dict[str, Any]:
        return {
            "question_id": str(question),
            "kind": "answered",
            "answer": ANSWER,
            "handle": who["handle"],
            "passphrase": passphrase or who["passphrase"],
        }

    failures = [
        await answer(harness, with_handle(other)),
        await answer(harness, with_handle(mine, "abacus abdomen abdominal abide abiding ability")),
        await answer(harness, {**with_handle(mine), "handle": "SG-H-AAAA-AAAA"}),
    ]
    assert {(f.status_code, f.json()["code"]) for f in failures} == {
        (403, "invalid_reporter_credentials")
    }
    assert (
        await count(
            harness,
            f"SELECT count(*) FROM app.report_follow_up_answers WHERE question_id = '{question}'",
        )
        == 0
    )
    ok = await answer(harness, with_handle(mine))
    assert ok.status_code == 200
    assert mine["passphrase"] not in ok.text


async def test_a_retry_replays_and_a_changed_retry_conflicts(harness: Harness) -> None:
    prepare(harness)
    code, (question,) = await needing_information(harness)
    key = str(uuid.uuid4())
    first = await answer(harness, by_code(code, question), key=key)
    second = await answer(harness, by_code(code, question), key=key)
    assert (first.status_code, second.status_code) == (200, 200)
    assert second.content == first.content
    assert second.headers["idempotency-replayed"] == "true"
    clash = await answer(harness, by_code(code, question, text_="a different answer"), key=key)
    assert clash.status_code == 409
    assert (
        await count(
            harness,
            f"SELECT count(*) FROM app.report_follow_up_answers WHERE question_id = '{question}'",
        )
        == 1
    )
    assert (await answer(harness, by_code(code, question), key=None)).status_code == 400
    again = await answer(harness, by_code(code, question))
    assert again.status_code == 404, "a new key cannot answer the same question twice"


async def test_concurrent_answers_to_one_question_store_exactly_one(harness: Harness) -> None:
    prepare(harness)
    code, (question,) = await needing_information(harness)
    results = await asyncio.gather(
        *(answer(harness, by_code(code, question, text_=f"{ANSWER} #{n}")) for n in range(4))
    )
    assert sorted(r.status_code for r in results) == [200, 404, 404, 404]
    assert (
        await count(
            harness,
            f"SELECT count(*) FROM app.report_follow_up_answers WHERE question_id = '{question}'",
        )
        == 1
    )
    assert await count(
        harness, "SELECT count(*) FROM app.data_keys WHERE purpose = 'follow_up_answers'"
    ) == await count(
        harness, "SELECT count(*) FROM app.report_follow_up_answers WHERE kind = 'answered'"
    )
    events = await count(
        harness,
        f"SELECT count(*) FROM app.report_status_events WHERE report_id = '{await report_id_for(harness, code)}' AND actor_type = 'reporter' AND new_status = 'under_review'",
    )
    assert events == 1


async def test_the_body_is_capped(harness: Harness) -> None:
    prepare(harness)
    async with harness.client() as http:
        response = await http.post(
            ENDPOINT,
            content=b'{"answer":"' + b"a" * 20000 + b'"}',
            headers={"content-type": "application/json", "Idempotency-Key": str(uuid.uuid4())},
        )
    assert response.status_code == 413


async def test_the_answer_and_credentials_never_reach_logs(harness: Harness) -> None:
    prepare(harness)
    code, (question,) = await needing_information(harness)
    buffer = io.StringIO()
    configure_logging(service="svc", environment="test", level="DEBUG", stream=buffer)
    try:
        await answer(harness, by_code(code, question))
        await answer(harness, by_code(code, question))
        output = buffer.getvalue()
    finally:
        structlog.reset_defaults()
        logging.getLogger().handlers.clear()
    assert ANSWER not in output
    assert code not in output
    assert CANARY not in output


async def test_the_public_role_touches_the_tables_only_through_the_functions(
    harness: Harness, role_urls: dict[str, URL]
) -> None:
    engine = build_engine(
        role_urls["shaidago_public"], application_name="p", statement_timeout_ms=8000
    )
    try:
        for sql in (
            "SELECT * FROM app.report_follow_up_questions",
            "SELECT * FROM app.report_follow_up_answers",
            "INSERT INTO app.report_follow_up_answers (id) VALUES (gen_random_uuid())",
            "UPDATE app.report_follow_up_questions SET withdrawn_at = now()",
        ):
            with pytest.raises(DBAPIError) as raised:
                async with Database(engine).unit_of_work() as session:
                    await session.execute(text(sql))
            assert getattr(raised.value.orig, "sqlstate", None) == PRIVILEGE, sql
    finally:
        await engine.dispose()
    for signature in (
        "follow_up_submit(uuid, bytea[], uuid, uuid, text, bytea, uuid, integer, timestamptz, uuid, uuid, text)",
        "tracking_follow_ups(bytea[])",
    ):
        grants = {
            role: (
                await harness.rows(
                    f"SELECT has_function_privilege('{role}', 'app.{signature}', 'EXECUTE')"
                )
            )[0][0]
            for role in ("shaidago_public", "shaidago_reviewer", "shaidago_worker", "public")
        }
        assert grants == {
            "shaidago_public": True,
            "shaidago_reviewer": False,
            "shaidago_worker": False,
            "public": False,
        }


async def test_reviewers_author_and_withdraw_questions_but_cannot_write_or_rewrite_answers(
    harness: Harness, role_urls: dict[str, URL]
) -> None:
    prepare(harness)
    code, (question,) = await needing_information(harness)
    report_id = await report_id_for(harness, code)
    engine = build_engine(
        role_urls["shaidago_reviewer"], application_name="r", statement_timeout_ms=8000
    )
    reviewer = Database(engine)
    try:
        async with reviewer.unit_of_work() as session:
            await session.execute(
                text(
                    "INSERT INTO app.report_follow_up_questions (id, report_id, question, asked_at) VALUES (gen_random_uuid(), :r, 'A reviewer question?', now())"
                ),
                {"r": report_id},
            )
            await session.execute(
                text(
                    f"UPDATE app.report_follow_up_questions SET withdrawn_at = now() WHERE id = '{question}'"
                )
            )
        for sql in (
            f"UPDATE app.report_follow_up_questions SET question = 'rewritten?' WHERE id = '{question}'",
            "INSERT INTO app.report_follow_up_answers (id) VALUES (gen_random_uuid())",
            "UPDATE app.report_follow_up_answers SET kind = 'skipped'",
            "DELETE FROM app.report_follow_up_answers",
            "DELETE FROM app.report_follow_up_questions",
        ):
            with pytest.raises(DBAPIError) as raised:
                async with reviewer.unit_of_work() as session:
                    await session.execute(text(sql))
            assert getattr(raised.value.orig, "sqlstate", None) == PRIVILEGE, sql
    finally:
        await engine.dispose()


async def test_a_withdrawn_question_disappears_from_tracking(harness: Harness) -> None:
    prepare(harness)
    code, (question,) = await needing_information(harness)
    async with harness.owner.unit_of_work() as session:
        await session.execute(
            text(
                f"UPDATE app.report_follow_up_questions SET withdrawn_at = now() WHERE id = '{question}'"
            )
        )
    async with harness.client() as http:
        tracked = await http.post(
            "/v1/report-status:lookup",
            json={"code": code},
            headers={"X-Shaidago-Client-Hmac": uuid.uuid4().hex * 2},
        )
    assert tracked.json()["follow_up_questions"] == []

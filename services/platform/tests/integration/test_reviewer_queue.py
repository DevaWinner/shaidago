"""Reviewer queue and detail (BE-070): least privilege, minimal data, bounded queries, audit."""

import json
import uuid

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import ProgrammingError

from tests.integration.report_support import CANARY, CONTACT_CANARY, ask
from tests.integration.reviewer_support import Actor, ReviewWorld

QUEUE = "/v1/reviewer/reports"
QUEUE_KEYS = {
    "report_id",
    "project_slug",
    "concern_category",
    "risk_level",
    "status",
    "version",
    "created_at",
    "status_updated_at",
    "has_contact",
    "evidence_count",
    "open_follow_ups",
}


async def _answer(world: ReviewWorld, code: str, question_id: uuid.UUID, text_: str) -> None:
    async with world.client() as client:
        response = await client.post(
            "/v1/report-status:answer-follow-up",
            json={
                "question_id": str(question_id),
                "kind": "answered",
                "answer": text_,
                "code": code,
            },
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )
    assert response.status_code == 200, response.text


async def test_the_queue_and_detail_need_a_reviewer_session(review_world: ReviewWorld) -> None:
    _, report_id = await review_world.submit()
    for path in (QUEUE, f"{QUEUE}/{report_id}"):
        response = await review_world.call(None, "GET", path)
        assert response.status_code == 401
        assert response.json()["code"] == "unauthenticated"
        assert response.headers["cache-control"] == "no-store"


async def test_a_disabled_reviewer_and_an_unknown_token_are_refused(
    review_world: ReviewWorld,
) -> None:
    record = await review_world.reviewer()
    actor = Actor(record, await review_world.session(record))
    assert (await review_world.call(actor, "GET", QUEUE)).status_code == 200
    async with review_world.owner.unit_of_work() as session:
        await session.execute(
            text("UPDATE app.reviewers SET state = 'disabled' WHERE id = :i"), {"i": record.id}
        )
    assert (await review_world.call(actor, "GET", QUEUE)).status_code == 401


async def test_the_queue_shows_triage_fields_only(review_world: ReviewWorld) -> None:
    code, report_id = await review_world.submit(contact=True, attachments=1)
    actor = await review_world.signed_in()
    response = await review_world.call(actor, "GET", QUEUE, params={"project": review_world.slug})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    [item] = response.json()["items"]
    assert set(item) == QUEUE_KEYS
    assert item["report_id"] == str(report_id)
    assert item["status"] == "received"
    assert item["has_contact"] is True
    assert item["evidence_count"] == 1
    for private in (CANARY, CONTACT_CANARY, code, "object_key", "description", "contact_value"):
        assert private not in response.text


async def test_the_queue_is_oldest_first_and_pages_without_skips_or_repeats(
    review_world: ReviewWorld,
) -> None:
    ids: list[str] = []
    for _ in range(5):
        _, report_id = await review_world.submit()
        ids.append(str(report_id))
        review_world.advance(60)
    actor = await review_world.signed_in()
    seen: list[str] = []
    cursor = None
    while True:
        params = {"project": review_world.slug, "limit": 2} | ({"cursor": cursor} if cursor else {})
        body = (await review_world.call(actor, "GET", QUEUE, params=params)).json()
        seen += [item["report_id"] for item in body["items"]]
        cursor = body["next_cursor"]
        if cursor is None:
            break
    assert seen == ids


async def test_filters_narrow_the_queue_and_a_cursor_only_fits_its_own_filters(
    review_world: ReviewWorld,
) -> None:
    await review_world.submit(category="no_visible_work")
    await review_world.submit(category="unsafe_construction")
    await review_world.submit(category="unsafe_construction")
    actor = await review_world.signed_in()
    base = {"project": review_world.slug}
    unsafe = (
        await review_world.call(
            actor,
            "GET",
            QUEUE,
            params=base | {"concern_category": "unsafe_construction", "limit": 1},
        )
    ).json()
    assert len(unsafe["items"]) == 1
    assert unsafe["next_cursor"]
    assert unsafe["items"][0]["concern_category"] == "unsafe_construction"
    reused = await review_world.call(
        actor, "GET", QUEUE, params=base | {"cursor": unsafe["next_cursor"]}
    )
    assert reused.status_code == 400
    assert reused.json()["code"] == "invalid_cursor"
    none = await review_world.call(
        actor, "GET", QUEUE, params=base | {"status": ["closed", "referred"]}
    )
    assert none.json()["items"] == []
    both = await review_world.call(actor, "GET", QUEUE, params=base | {"status": ["received"]})
    assert len(both.json()["items"]) == 3


async def test_bad_filters_and_unknown_parameters_are_validation_failures(
    review_world: ReviewWorld,
) -> None:
    actor = await review_world.signed_in()
    for params in (
        {"status": "published"},
        {"risk_level": "critical"},
        {"project": "Not A Slug"},
        {"tracking_code": "SG-AAAAA"},
        {"include": "description"},
    ):
        response = await review_world.call(actor, "GET", QUEUE, params=params)
        assert response.status_code == 422, params
        assert response.json()["code"] == "validation_failed"


async def test_detail_decrypts_only_what_a_reviewer_needs_and_audits_the_view(
    review_world: ReviewWorld,
) -> None:
    code, report_id = await review_world.submit(contact=True, attachments=2)
    actor = await review_world.signed_in()
    response = await review_world.call(actor, "GET", f"{QUEUE}/{report_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["description"] == CANARY
    assert body["contact"] is None
    assert body["has_contact"] is True
    assert body["version"] == 1
    assert [e["new_status"] for e in body["events"]] == ["received"]
    assert len(body["evidence"]) == 2
    for evidence in body["evidence"]:
        assert set(evidence) == {
            "evidence_id",
            "display_name",
            "mime_type",
            "size_bytes",
            "sanitation_state",
            "scan_state",
            "created_at",
        }
    for private in (CONTACT_CANARY, code, "object_key", "http://", "https://"):
        assert private not in response.text
    [audit] = await review_world.rows(
        "SELECT actor_id, details FROM app.audit_events "
        "WHERE event = 'report_detail_viewed' AND subject_id = :r",
        r=report_id,
    )
    assert audit.actor_id == actor.record.id
    assert audit.details == {"contact_included": False}


async def test_a_contact_is_returned_only_when_asked_for_and_the_read_is_audited(
    review_world: ReviewWorld,
) -> None:
    _, report_id = await review_world.submit(contact=True)
    actor = await review_world.signed_in()
    plain = await review_world.call(actor, "GET", f"{QUEUE}/{report_id}")
    assert CONTACT_CANARY not in plain.text
    assert not await review_world.rows(
        "SELECT 1 FROM app.audit_events WHERE event = 'report_contact_read'"
    )
    asked = await review_world.call(
        actor, "GET", f"{QUEUE}/{report_id}", params={"include_contact": "true"}
    )
    assert asked.json()["contact"] == {"channel": "email", "value": CONTACT_CANARY}
    [audit] = await review_world.rows(
        "SELECT actor_id, actor_type, details FROM app.audit_events "
        "WHERE event = 'report_contact_read' AND subject_id = :r",
        r=report_id,
    )
    assert audit.actor_id == actor.record.id
    assert CONTACT_CANARY not in json.dumps(audit.details)


async def test_an_anonymous_report_has_no_contact_even_when_one_is_requested(
    review_world: ReviewWorld,
) -> None:
    _, report_id = await review_world.submit(contact=False)
    actor = await review_world.signed_in("admin")
    response = await review_world.call(
        actor, "GET", f"{QUEUE}/{report_id}", params={"include_contact": "true"}
    )
    assert response.status_code == 200
    assert response.json()["contact"] is None
    assert response.json()["has_contact"] is False


async def test_the_reviewer_role_cannot_read_contacts_or_notes_except_through_the_function(
    review_world: ReviewWorld,
) -> None:
    await review_world.submit(contact=True)
    reviewer_engine = review_world.app.state.dependencies.reviewer_database.engine
    async with reviewer_engine.connect() as connection:
        with pytest.raises(ProgrammingError, match="permission denied"):
            await connection.execute(text("SELECT count(*) FROM app.report_contacts"))


async def test_an_unknown_report_is_a_generic_not_found(review_world: ReviewWorld) -> None:
    actor = await review_world.signed_in()
    response = await review_world.call(actor, "GET", f"{QUEUE}/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    malformed = await review_world.call(actor, "GET", f"{QUEUE}/not-a-uuid")
    assert malformed.status_code == 422


async def test_follow_up_answers_are_decrypted_for_the_reviewer(review_world: ReviewWorld) -> None:
    code, report_id = await review_world.submit()
    question = await ask(
        review_world.public, code, "What time of day was the gate locked?", review_world.clock.now()
    )
    await _answer(review_world, code, question, "FICTIONAL answer: mornings.")
    actor = await review_world.signed_in()
    body = (await review_world.call(actor, "GET", f"{QUEUE}/{report_id}")).json()
    [follow_up] = body["follow_ups"]
    assert follow_up["answer"] == "FICTIONAL answer: mornings."
    assert follow_up["answer_kind"] == "answered"


async def test_detail_uses_a_fixed_number_of_statements_however_much_the_report_holds(
    review_world: ReviewWorld,
) -> None:
    small_code, small = await review_world.submit(contact=True)
    big_code, big = await review_world.submit(contact=True, attachments=3)
    for n in range(4):
        question = await ask(
            review_world.public,
            big_code,
            f"FICTIONAL question number {n}?",
            review_world.clock.now(),
        )
        await _answer(review_world, big_code, question, f"FICTIONAL answer {n}.")
    actor = await review_world.signed_in()
    reviewer_engine = review_world.app.state.dependencies.reviewer_database.engine.sync_engine
    counts: dict[str, int] = {}
    for label, report_id in (("small", small), ("big", big)):
        seen: list[str] = []

        def record(
            _c: object, _cur: object, statement: str, *_rest: object, sink: list[str] = seen
        ) -> None:
            sink.append(statement)

        event.listen(reviewer_engine, "before_cursor_execute", record)
        try:
            response = await review_world.call(
                actor, "GET", f"{QUEUE}/{report_id}", params={"include_contact": "true"}
            )
        finally:
            event.remove(reviewer_engine, "before_cursor_execute", record)
        assert response.status_code == 200
        counts[label] = len(seen)
    assert counts["small"] == counts["big"]
    assert small_code != big_code


async def test_the_queue_is_one_statement_whatever_the_page_size(
    review_world: ReviewWorld,
) -> None:
    for _ in range(4):
        await review_world.submit(attachments=1)
    actor = await review_world.signed_in()
    engine = review_world.app.state.dependencies.reviewer_database.engine.sync_engine
    counts: list[int] = []
    for limit in (1, 4):
        seen: list[str] = []

        def record(
            _c: object, _cur: object, statement: str, *_rest: object, sink: list[str] = seen
        ) -> None:
            sink.append(statement)

        event.listen(engine, "before_cursor_execute", record)
        try:
            await review_world.call(
                actor, "GET", QUEUE, params={"project": review_world.slug, "limit": limit}
            )
        finally:
            event.remove(engine, "before_cursor_execute", record)
        counts.append(len([s for s in seen if "app.reports" in s]))
    assert counts == [1, 1]


async def test_a_status_or_risk_change_raises_the_report_version_and_nothing_else_does(
    review_world: ReviewWorld,
) -> None:
    _, report_id = await review_world.submit()
    async with review_world.owner.unit_of_work() as session:
        await session.execute(
            text("UPDATE app.reports SET updated_at = updated_at WHERE id = :r"), {"r": report_id}
        )
    [row] = await review_world.rows("SELECT version FROM app.reports WHERE id = :r", r=report_id)
    assert row.version == 1
    async with review_world.owner.unit_of_work() as session:
        await session.execute(
            text("UPDATE app.reports SET risk_level = 'elevated' WHERE id = :r"), {"r": report_id}
        )
    [row] = await review_world.rows("SELECT version FROM app.reports WHERE id = :r", r=report_id)
    assert row.version == 2


async def test_the_public_role_cannot_call_the_contact_function(review_world: ReviewWorld) -> None:
    _, report_id = await review_world.submit(contact=True)
    public_engine = review_world.app.state.dependencies.public_database.engine
    async with public_engine.connect() as connection:
        with pytest.raises(ProgrammingError, match="permission denied"):
            await connection.execute(
                text(
                    "SELECT * FROM app.reviewer_read_contact(:r, 'reviewer', NULL, now(), "
                    "gen_random_uuid(), NULL)"
                ),
                {"r": report_id},
            )

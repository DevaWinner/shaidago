"""Reviewer notes (BE-072): encrypted, append-only, private, audited without content."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from tests.integration.reviewer_support import ReviewWorld

NOTE = "FICTIONAL note canary: the fictional site manager confirmed nothing by phone."
QUEUE = "/v1/reviewer/reports"


def url(report_id: uuid.UUID) -> str:
    return f"{QUEUE}/{report_id}/notes"


async def test_a_note_is_encrypted_at_rest_and_readable_by_a_reviewer(
    review_world: ReviewWorld,
) -> None:
    _, report_id = await review_world.submit()
    actor = await review_world.signed_in()
    created = await review_world.call(actor, "POST", url(report_id), json={"body": NOTE})
    assert created.status_code == 201
    assert created.headers["cache-control"] == "no-store"
    assert set(created.json()) == {"note_id", "created_at"}
    [row] = await review_world.rows(
        "SELECT n.body_ciphertext, n.author_id, k.purpose, k.owner_table, k.owner_id "
        "FROM app.report_notes n JOIN app.data_keys k ON k.id = n.data_key_id WHERE n.report_id = :r",
        r=report_id,
    )
    assert NOTE.encode() not in bytes(row.body_ciphertext)
    assert row.author_id == actor.record.id
    assert (row.purpose, row.owner_table) == ("review_notes", "report_notes")
    assert str(row.owner_id) == created.json()["note_id"]
    listed = await review_world.call(actor, "GET", url(report_id))
    [item] = listed.json()["items"]
    assert item["body"] == NOTE
    assert item["author"] == actor.record.identifier
    assert listed.headers["cache-control"] == "no-store"


async def test_notes_keep_their_order_and_page_without_skips_or_repeats(
    review_world: ReviewWorld,
) -> None:
    _, report_id = await review_world.submit()
    actor = await review_world.signed_in()
    for n in range(5):
        review_world.advance(1)
        await review_world.call(actor, "POST", url(report_id), json={"body": f"FICTIONAL note {n}"})
    seen: list[str] = []
    cursor = None
    while True:
        params = {"limit": 2} | ({"cursor": cursor} if cursor else {})
        body = (await review_world.call(actor, "GET", url(report_id), params=params)).json()
        seen += [item["body"] for item in body["items"]]
        cursor = body["next_cursor"]
        if cursor is None:
            break
    assert seen == [f"FICTIONAL note {n}" for n in range(5)]


async def test_a_cursor_from_another_report_and_unknown_parameters_are_refused(
    review_world: ReviewWorld,
) -> None:
    _, first = await review_world.submit()
    _, second = await review_world.submit()
    actor = await review_world.signed_in()
    for n in range(3):
        await review_world.call(actor, "POST", url(first), json={"body": f"FICTIONAL note {n}"})
    cursor = (await review_world.call(actor, "GET", url(first), params={"limit": 1})).json()[
        "next_cursor"
    ]
    reused = await review_world.call(actor, "GET", url(second), params={"cursor": cursor})
    assert reused.status_code == 400
    assert reused.json()["code"] == "invalid_cursor"
    extra = await review_world.call(actor, "GET", url(first), params={"body": "x"})
    assert extra.status_code == 422


async def test_markup_control_characters_and_bad_sizes_are_refused_before_storage(
    review_world: ReviewWorld,
) -> None:
    _, report_id = await review_world.submit()
    actor = await review_world.signed_in()
    for body in ("", "   ", "x" * 4001, "<script>alert(1)</script>", "a <b>bold</b> claim",
                 "</div>", "<!-- hidden -->", "bell\x07 char"):  # fmt: skip
        response = await review_world.call(actor, "POST", url(report_id), json={"body": body})
        assert response.status_code == 422, body
        assert response.json()["errors"][0]["field"] == "body"
    extra = await review_world.call(
        actor, "POST", url(report_id), json={"body": "fine note", "author": "someone"}
    )
    assert extra.status_code == 422
    fine = await review_world.call(
        actor, "POST", url(report_id), json={"body": "Cost 5 < 10 and 10 > 5 is fine text."}
    )
    assert fine.status_code == 201
    assert (
        await review_world.rows(
            "SELECT count(*) AS n FROM app.report_notes WHERE report_id = :r", r=report_id
        )
    )[0].n == 1


async def test_notes_need_a_session_csrf_and_a_known_report(review_world: ReviewWorld) -> None:
    _, report_id = await review_world.submit()
    actor = await review_world.signed_in()
    assert (
        await review_world.call(None, "POST", url(report_id), json={"body": NOTE})
    ).status_code == 401
    assert (await review_world.call(None, "GET", url(report_id))).status_code == 401
    no_csrf = await review_world.call(
        actor, "POST", url(report_id), json={"body": NOTE}, csrf=False
    )
    assert no_csrf.status_code == 403
    assert (
        await review_world.call(actor, "POST", url(uuid.uuid4()), json={"body": NOTE})
    ).status_code == 404
    assert (await review_world.call(actor, "GET", url(uuid.uuid4()))).status_code == 404


async def test_creating_a_note_is_audited_without_its_content(review_world: ReviewWorld) -> None:
    _, report_id = await review_world.submit()
    actor = await review_world.signed_in()
    created = await review_world.call(actor, "POST", url(report_id), json={"body": NOTE})
    [audit] = await review_world.rows(
        "SELECT actor_id, details FROM app.audit_events "
        "WHERE event = 'report_note_added' AND subject_id = :r",
        r=report_id,
    )
    assert audit.actor_id == actor.record.id
    assert audit.details == {"note_id": created.json()["note_id"]}
    assert "FICTIONAL" not in str(audit.details)


async def test_note_text_never_reaches_tracking_the_public_api_the_detail_or_the_logs(
    review_world: ReviewWorld, capsys: pytest.CaptureFixture[str]
) -> None:
    code, report_id = await review_world.submit()
    actor = await review_world.signed_in()
    await review_world.call(actor, "POST", url(report_id), json={"body": NOTE})
    async with review_world.client() as client:
        tracked = await client.post("/v1/report-status:lookup", json={"code": code})
        catalogue = await client.get(f"/v1/projects/{review_world.slug}")
    detail = await review_world.call(actor, "GET", f"{QUEUE}/{report_id}")
    for response in (tracked, catalogue, detail):
        assert "FICTIONAL note canary" not in response.text
    output = capsys.readouterr()
    assert "FICTIONAL note canary" not in output.out + output.err


async def test_the_public_role_has_no_access_and_history_cannot_be_edited(
    review_world: ReviewWorld,
) -> None:
    _, report_id = await review_world.submit()
    actor = await review_world.signed_in()
    await review_world.call(actor, "POST", url(report_id), json={"body": NOTE})
    deps = review_world.app.state.dependencies
    async with deps.public_database.engine.connect() as connection:
        with pytest.raises(ProgrammingError, match="permission denied"):
            await connection.execute(text("SELECT count(*) FROM app.report_notes"))
    for engine in (deps.reviewer_database.engine, review_world.owner.engine):
        for statement in (
            "UPDATE app.report_notes SET schema_version = 2 WHERE report_id = :r",
            "DELETE FROM app.report_notes WHERE report_id = :r",
        ):
            async with engine.connect() as connection:
                with pytest.raises(DBAPIError):
                    await connection.execute(text(statement), {"r": report_id})
    async with deps.reviewer_database.engine.connect() as connection:
        with pytest.raises(ProgrammingError, match="permission denied"):
            await connection.execute(text("UPDATE app.report_notes SET created_at = now()"))


async def test_a_shredded_note_key_leaves_the_note_present_but_unreadable(
    review_world: ReviewWorld,
) -> None:
    _, report_id = await review_world.submit()
    actor = await review_world.signed_in()
    created = await review_world.call(actor, "POST", url(report_id), json={"body": NOTE})
    async with review_world.owner.unit_of_work() as session:
        await session.execute(
            text(
                "UPDATE app.data_keys SET wrapped_key = NULL, kek_version = NULL, "
                "destroyed_at = now() WHERE owner_table = 'report_notes' AND owner_id = :n"
            ),
            {"n": uuid.UUID(created.json()["note_id"])},
        )
    listed = await review_world.call(actor, "GET", url(report_id))
    [item] = listed.json()["items"]
    assert item["body"] is None
    assert item["note_id"] == created.json()["note_id"]

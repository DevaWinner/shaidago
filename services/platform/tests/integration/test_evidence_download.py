"""The evidence download broker (BE-073): authorised, audited, private, and never a storage URL."""

import io
import uuid
from datetime import timedelta

from PIL import Image
from sqlalchemy import text

from tests.integration.report_support import png, report_id_for
from tests.integration.reviewer_support import ReviewWorld

QUEUE = "/v1/reviewer/reports"


async def evidence_of(world: ReviewWorld, report_id: uuid.UUID) -> tuple[uuid.UUID, str]:
    [row] = await world.rows(
        "SELECT id, object_key FROM app.evidence_files WHERE report_id = :r ORDER BY created_at "
        "LIMIT 1",
        r=report_id,
    )
    return row.id, row.object_key


def content(report_id: uuid.UUID, evidence_id: uuid.UUID) -> str:
    return f"{QUEUE}/{report_id}/evidence/{evidence_id}/content"


async def test_an_authorised_reviewer_downloads_the_sanitised_file_as_an_attachment(
    review_world: ReviewWorld,
) -> None:
    _, report_id = await review_world.submit(attachments=1)
    evidence_id, key = await evidence_of(review_world, report_id)
    actor = await review_world.signed_in()
    response = await review_world.call(actor, "GET", content(report_id, evidence_id))
    assert response.status_code == 200
    assert response.content == review_world.store.objects[key][0]
    assert response.headers["content-type"] == "image/png"
    assert response.headers["content-disposition"].startswith('attachment; filename="')
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in response.headers["content-security-policy"]
    assert response.headers["x-evidence-scan-state"] in {"clean", "not_scanned_demo"}
    assert key not in str(dict(response.headers))
    Image.open(io.BytesIO(response.content)).verify()


async def test_the_hosted_demo_scan_state_is_visible_to_the_reviewer(
    review_world: ReviewWorld,
) -> None:
    _, report_id = await review_world.submit(attachments=1)
    evidence_id, _ = await evidence_of(review_world, report_id)
    async with review_world.owner.unit_of_work() as session:
        await session.execute(
            text("UPDATE app.evidence_files SET scan_state = 'not_scanned_demo' WHERE id = :e"),
            {"e": evidence_id},
        )
    actor = await review_world.signed_in()
    response = await review_world.call(actor, "GET", content(report_id, evidence_id))
    assert response.headers["x-evidence-scan-state"] == "not_scanned_demo"
    detail = (await review_world.call(actor, "GET", f"{QUEUE}/{report_id}")).json()
    assert [e["scan_state"] for e in detail["evidence"]] == ["not_scanned_demo"]


async def test_the_object_key_never_appears_in_any_reviewer_response(
    review_world: ReviewWorld,
) -> None:
    _, report_id = await review_world.submit(attachments=2)
    evidence_id, key = await evidence_of(review_world, report_id)
    actor = await review_world.signed_in()
    for path in (
        f"{QUEUE}/{report_id}",
        QUEUE,
        f"{QUEUE}/{report_id}/notes",
        content(report_id, evidence_id),
    ):
        response = await review_world.call(actor, "GET", path)
        if response.headers["content-type"].startswith("application/json"):
            assert key not in response.text
        assert key not in str(dict(response.headers))


async def test_a_file_under_the_wrong_report_or_an_unknown_id_is_one_generic_not_found(
    review_world: ReviewWorld,
) -> None:
    _, mine = await review_world.submit(attachments=1)
    _, other = await review_world.submit(attachments=1)
    mine_evidence, _ = await evidence_of(review_world, mine)
    actor = await review_world.signed_in()
    responses = [
        await review_world.call(actor, "GET", content(other, mine_evidence)),
        await review_world.call(actor, "GET", content(mine, uuid.uuid4())),
        await review_world.call(actor, "GET", content(uuid.uuid4(), mine_evidence)),
    ]
    assert {r.status_code for r in responses} == {404}
    bodies = {str({k: v for k, v in r.json().items() if k != "request_id"}) for r in responses}
    assert len(bodies) == 1
    events = await review_world.rows(
        "SELECT outcome, details FROM app.audit_events "
        "WHERE event = 'report_evidence_download_denied' AND actor_id = :a",
        a=actor.record.id,
    )
    assert len(events) == 3
    assert {e.outcome for e in events} == {"denied"}
    assert {e.details["reason"] for e in events} == {"not_found"}


async def test_download_needs_a_live_session_and_an_active_reviewer(
    review_world: ReviewWorld,
) -> None:
    _, report_id = await review_world.submit(attachments=1)
    evidence_id, _ = await evidence_of(review_world, report_id)
    anonymous = await review_world.call(None, "GET", content(report_id, evidence_id))
    assert anonymous.status_code == 401
    actor = await review_world.signed_in()
    assert (
        await review_world.call(actor, "GET", content(report_id, evidence_id))
    ).status_code == 200
    # Nothing outlives the session: there is no separate token to replay after it ends.
    review_world.clock.advance(timedelta(days=2))
    replay = await review_world.call(actor, "GET", content(report_id, evidence_id))
    assert replay.status_code == 401
    assert replay.json()["code"] == "unauthenticated"
    disabled = await review_world.signed_in()
    async with review_world.owner.unit_of_work() as session:
        await session.execute(
            text("UPDATE app.reviewers SET state = 'disabled' WHERE id = :i"),
            {"i": disabled.record.id},
        )
    assert (
        await review_world.call(disabled, "GET", content(report_id, evidence_id))
    ).status_code == 401


async def test_every_grant_is_audited_without_a_url_a_token_or_content(
    review_world: ReviewWorld,
) -> None:
    _, report_id = await review_world.submit(attachments=1)
    evidence_id, key = await evidence_of(review_world, report_id)
    actor = await review_world.signed_in()
    await review_world.call(actor, "GET", content(report_id, evidence_id))
    [audit] = await review_world.rows(
        "SELECT actor_id, outcome, details FROM app.audit_events "
        "WHERE event = 'report_evidence_download_granted' AND subject_id = :r",
        r=report_id,
    )
    assert audit.actor_id == actor.record.id
    assert audit.outcome == "success"
    assert audit.details == {"evidence_id": str(evidence_id)}
    assert key not in str(audit.details)


async def test_missing_or_tampered_bytes_are_never_served_and_the_decision_is_still_recorded(
    review_world: ReviewWorld,
) -> None:
    _, report_id = await review_world.submit(attachments=1)
    evidence_id, key = await evidence_of(review_world, report_id)
    actor = await review_world.signed_in()
    original = review_world.store.objects[key]
    review_world.store.objects[key] = (original[0] + b"tampered", original[1])
    tampered = await review_world.call(actor, "GET", content(report_id, evidence_id))
    assert tampered.status_code == 503
    assert tampered.json()["code"] == "dependency_unavailable"
    assert b"tampered" not in tampered.content
    del review_world.store.objects[key]
    missing = await review_world.call(actor, "GET", content(report_id, evidence_id))
    assert missing.status_code == 503
    granted = await review_world.rows(
        "SELECT 1 FROM app.audit_events WHERE event = 'report_evidence_download_granted' "
        "AND subject_id = :r",
        r=report_id,
    )
    assert len(granted) == 2


async def test_a_hostile_original_file_name_cannot_shape_the_download_headers(
    review_world: ReviewWorld,
) -> None:
    fields = review_world.public.fields()
    response = await review_world.public.post(
        fields, [('evil"\r\nSet-Cookie: x=1.png', png(), "image/png")]
    )
    assert response.status_code == 201
    code = response.json()["tracking_code"]
    report_id = await report_id_for(review_world.public, code)
    evidence_id, _ = await evidence_of(review_world, report_id)
    actor = await review_world.signed_in()
    download = await review_world.call(actor, "GET", content(report_id, evidence_id))
    disposition = download.headers["content-disposition"]
    assert "\r" not in disposition
    assert "\n" not in disposition
    assert "set-cookie" not in download.headers
    assert disposition.count('"') == 2

"""Retention and crypto-shredding (BE-106): what is deleted, what is kept, and that it is repeatable."""

import os
import uuid
from datetime import timedelta
from pathlib import Path

from sqlalchemy import text

from shaidago.retention.purge import (
    purge_expired,
    shred_closed_reports,
    shred_report,
    stale_reviewers,
    sweep_scratch,
)
from shaidago.shared.ids import Uuid7Generator
from tests.integration.report_support import CANARY, CONTACT_CANARY
from tests.integration.reviewer_support import ReviewWorld

QUEUE = "/v1/reviewer/reports"


async def test_expired_sessions_and_idempotency_records_are_deleted_and_live_ones_kept(
    review_world: ReviewWorld,
) -> None:
    old = await review_world.signed_in()
    await review_world.submit()  # a record that will have expired
    review_world.clock.advance(timedelta(days=40))
    live = await review_world.signed_in()
    await review_world.submit()  # a record that is still live
    expired = (
        await review_world.rows(
            "SELECT count(*) AS n FROM app.idempotency_records WHERE expires_at < :now",
            now=review_world.clock.now(),
        )
    )[0].n
    assert expired >= 1
    async with review_world.owner.unit_of_work() as session:
        counts = await purge_expired(session, review_world.clock)
    assert counts.sessions >= 1
    assert counts.idempotency_records == expired
    assert (await review_world.call(live, "GET", QUEUE)).status_code == 200
    assert (await review_world.call(old, "GET", QUEUE)).status_code == 401
    async with review_world.owner.unit_of_work() as session:
        again = await purge_expired(session, review_world.clock)
    assert (again.sessions, again.idempotency_records) == (0, 0)


def test_only_old_abandoned_upload_files_are_swept(tmp_path: Path) -> None:
    from datetime import UTC, datetime  # noqa: PLC0415

    now = datetime.now(UTC)
    stale = tmp_path / "sg-upload-old"
    fresh = tmp_path / "sg-upload-new"
    other = tmp_path / "unrelated-old"
    for path in (stale, fresh, other):
        path.write_bytes(b"x")
    long_ago = (now - timedelta(hours=5)).timestamp()
    for path in (stale, other):
        os.utime(path, (long_ago, long_ago))
    assert sweep_scratch(tmp_path, now) == 1
    assert (stale.exists(), fresh.exists(), other.exists()) == (False, True, True)
    assert sweep_scratch(tmp_path, now) == 0


async def test_shredding_makes_private_content_permanently_unreadable_and_keeps_history(
    review_world: ReviewWorld,
) -> None:
    code, report_id = await review_world.submit(contact=True, attachments=1)
    actor = await review_world.signed_in()
    base = f"{QUEUE}/{report_id}"
    await review_world.call(
        actor, "POST", f"{base}/notes", json={"body": "FICTIONAL note to be shredded"}
    )
    detail = (await review_world.call(actor, "GET", base)).json()
    await review_world.call(
        actor,
        "POST",
        f"{base}/status-transitions",
        json={
            "command": "start_review",
            "expected_status": "received",
            "expected_version": detail["version"],
            "internal_reason": "FICTIONAL reason to be shredded",
        },
    )
    assert CANARY in (await review_world.call(actor, "GET", base)).text
    [evidence] = await review_world.rows(
        "SELECT object_key FROM app.evidence_files WHERE report_id = :r", r=report_id
    )
    assert evidence.object_key in review_world.store.objects
    events_before = (
        await review_world.rows(
            "SELECT count(*) AS n FROM app.report_status_events WHERE report_id = :r", r=report_id
        )
    )[0].n
    async with review_world.owner.unit_of_work() as session:
        result = await shred_report(
            session,
            review_world.store,
            review_world.clock,
            Uuid7Generator(review_world.clock),
            report_id,
        )
    assert result is not None
    assert result.keys_destroyed >= 4  # description, contact, note, decision reason
    assert result.evidence_removed == 1
    after = (await review_world.call(actor, "GET", base, params={"include_contact": "true"})).json()
    assert after["description"] == ""
    assert after["contact"] is None
    assert [e["internal_reason"] for e in after["events"]] == [None, None]
    assert CANARY not in str(after)
    assert CONTACT_CANARY not in str(after)
    assert after["evidence"] == []
    notes = (await review_world.call(actor, "GET", f"{base}/notes")).json()["items"]
    assert [n["body"] for n in notes] == [None]  # the note still exists, unreadable
    assert evidence.object_key not in review_world.store.objects
    live = await review_world.rows(
        "SELECT count(*) AS n FROM app.data_keys k WHERE k.destroyed_at IS NULL AND k.id IN (SELECT description_key_id FROM app.reports WHERE id = :r)",
        r=report_id,
    )
    assert live[0].n == 0
    assert (
        await review_world.rows(
            "SELECT count(*) AS n FROM app.report_status_events WHERE report_id = :r", r=report_id
        )
    )[0].n == events_before
    assert await review_world.rows(
        "SELECT 1 FROM app.audit_events WHERE event = 'report_shredded' AND subject_id = :r",
        r=report_id,
    )
    async with review_world.client() as http:
        tracked = await http.post("/v1/report-status:lookup", json={"code": code})
    assert tracked.status_code == 200  # the reporter can still see the public-safe status
    async with review_world.owner.unit_of_work() as session:
        again = await shred_report(
            session,
            review_world.store,
            review_world.clock,
            Uuid7Generator(review_world.clock),
            report_id,
        )
        missing = await shred_report(
            session,
            review_world.store,
            review_world.clock,
            Uuid7Generator(review_world.clock),
            uuid.uuid4(),
        )
    assert again is not None
    assert (again.keys_destroyed, again.evidence_removed) == (0, 0)
    assert missing is None


async def test_only_closed_reports_past_the_age_are_shredded(review_world: ReviewWorld) -> None:
    _, closed_old = await review_world.submit()
    _, closed_new = await review_world.submit()
    _, open_report = await review_world.submit()
    async with review_world.owner.unit_of_work() as session:
        for report, age in ((closed_old, "400 days"), (closed_new, "1 day")):
            await session.execute(
                text(
                    "INSERT INTO app.report_status_events (id, report_id, previous_status, new_status, public_message, actor_type, occurred_at) VALUES (gen_random_uuid(), :r, 'received', 'closed', 'Closed.', 'reviewer', :at)"
                ),
                {"r": report, "at": review_world.clock.now() + timedelta(seconds=1)},
            )
            await session.execute(
                text(
                    "UPDATE app.reports SET status = 'closed', status_updated_at = :at - CAST(:age AS interval) WHERE id = :r"
                ),
                {"r": report, "at": review_world.clock.now() + timedelta(seconds=1), "age": age},
            )
    async with review_world.owner.unit_of_work() as session:
        shredded = await shred_closed_reports(
            session,
            review_world.store,
            review_world.clock,
            Uuid7Generator(review_world.clock),
            older_than=timedelta(days=365),
        )
    assert {r.report_id for r in shredded} == {closed_old}
    for report, expected in ((closed_old, 0), (closed_new, 1), (open_report, 1)):
        live = await review_world.rows(
            "SELECT count(*) AS n FROM app.data_keys k WHERE k.destroyed_at IS NULL AND k.id IN (SELECT description_key_id FROM app.reports WHERE id = :r)",
            r=report,
        )
        assert live[0].n == expected


async def test_reviewers_with_no_recent_sign_in_are_listed_for_an_access_review(
    review_world: ReviewWorld,
) -> None:
    stale = await review_world.reviewer()
    recent = await review_world.signed_in()
    async with review_world.owner.unit_of_work() as session:
        await session.execute(
            text(
                "UPDATE app.reviewers SET last_sign_in_at = now() - interval '200 days' WHERE id = :i"
            ),
            {"i": stale.id},
        )
        await session.execute(
            text("UPDATE app.reviewers SET last_sign_in_at = now() WHERE id = :i"),
            {"i": recent.record.id},
        )
    async with review_world.owner.unit_of_work() as session:
        listed = await stale_reviewers(session, review_world.clock, timedelta(days=90))
    assert stale.id in listed
    assert recent.record.id not in listed

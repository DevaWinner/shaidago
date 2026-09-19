"""Concurrency and failure injection across the composed backend (BE-103).

Each test states what must hold: an atomic outcome, safe retry, a visible status, no partial data,
and no unbounded work. Cases already proven elsewhere are listed in the build order note.
"""

import asyncio
import subprocess
import sys
import uuid
from typing import Any

import pytest
from sqlalchemy.engine import URL

from shaidago.files.storage import InMemoryObjectStore
from tests.factories import KEY_B, build_settings
from tests.integration.conftest import disposable_database
from tests.integration.report_support import png
from tests.integration.reviewer_support import SETTINGS, ReviewWorld


async def count(world: ReviewWorld, table: str) -> int:
    return int((await world.rows(f"SELECT count(*) AS n FROM app.{table}"))[0].n)


async def test_the_same_idempotency_key_arriving_concurrently_creates_one_report(
    review_world: ReviewWorld,
) -> None:
    before = await count(review_world, "reports")
    key = str(uuid.uuid4())
    responses = await asyncio.gather(*(review_world.public.post(key=key) for _ in range(6)))
    assert await count(review_world, "reports") == before + 1
    assert {r.status_code for r in responses} <= {201, 409}
    assert any(r.status_code == 201 for r in responses)
    codes = {r.json()["tracking_code"] for r in responses if r.status_code == 201}
    assert len(codes) == 1  # every success is the same receipt, not six reports
    assert await count(review_world, "report_tracking_keys") >= 1


async def test_signing_out_while_a_request_is_in_flight_leaves_a_consistent_outcome(
    review_world: ReviewWorld,
) -> None:
    _, report_id = await review_world.submit()
    actor = await review_world.signed_in()
    url = f"/v1/reviewer/reports/{report_id}/notes"
    notes = [
        review_world.call(actor, "POST", url, json={"body": f"FICTIONAL racing note {n}"})
        for n in range(5)
    ]
    sign_out = review_world.call(actor, "DELETE", "/v1/auth/sessions/current")
    results = await asyncio.gather(*notes, sign_out)
    assert all(r.status_code in {201, 401} for r in results[:5]), [r.status_code for r in results]
    assert results[5].status_code == 204
    stored = await review_world.rows(
        "SELECT count(*) AS n FROM app.report_notes WHERE report_id = :r", r=report_id
    )
    assert stored[0].n == sum(
        r.status_code == 201 for r in results[:5]
    )  # what was answered is what is stored
    assert (
        await review_world.call(actor, "GET", url)
    ).status_code == 401  # and nothing works afterwards


async def test_dropped_database_connections_are_recovered_without_a_crash(
    review_world: ReviewWorld,
) -> None:
    actor = await review_world.signed_in()
    assert (await review_world.call(actor, "GET", "/v1/reviewer/reports")).status_code == 200
    await review_world.rows(
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        "WHERE usename = 'shaidago_reviewer' AND pid <> pg_backend_pid()"
    )
    statuses = [
        (await review_world.call(actor, "GET", "/v1/reviewer/reports")).status_code
        for _ in range(3)
    ]
    assert 500 not in statuses
    assert statuses[-1] == 200  # the pool reconnected on its own


class FailingStore(InMemoryObjectStore):
    async def put(self, key: str, data: bytes, content_type: str) -> None:
        del key, data, content_type
        from shaidago.files.rules import UploadRejectedError  # noqa: PLC0415

        raise UploadRejectedError("storage_failed")


async def test_object_storage_failing_during_an_upload_keeps_the_report_and_no_orphans(
    review_world: ReviewWorld,
) -> None:
    pipeline = review_world.app.state.dependencies.evidence_pipeline
    pipeline._store = FailingStore()
    reports, evidence = (
        await count(review_world, "reports"),
        await count(review_world, "evidence_files"),
    )
    response = await review_world.public.post(
        review_world.public.fields(), [("a.png", png(), "image/png")]
    )
    assert response.status_code == 201, response.text
    [outcome] = response.json()["attachments"]
    assert (outcome["kept"], outcome["reason"]) == (False, "storage_failed")
    assert await count(review_world, "reports") == reports + 1
    assert (
        await count(review_world, "evidence_files") == evidence
    )  # no row points at a missing object


async def test_a_missing_key_version_is_a_retryable_503_and_nothing_partial_is_written(
    review_world: ReviewWorld,
) -> None:
    _, report_id = await review_world.submit(contact=True)
    actor = await review_world.signed_in()
    good = review_world.app.state.settings
    review_world.app.state.settings = build_settings(
        **(
            SETTINGS
            | {"ENCRYPTION_KEKS": f"kek-2={KEY_B}", "ENCRYPTION_ACTIVE_KEK_VERSION": "kek-2"}
        )
    )
    notes_before = await count(review_world, "report_notes")
    try:
        detail = await review_world.call(actor, "GET", f"/v1/reviewer/reports/{report_id}")
        write = await review_world.call(
            actor,
            "POST",
            f"/v1/reviewer/reports/{report_id}/notes",
            json={"body": "FICTIONAL note under a new key ring"},
        )
    finally:
        review_world.app.state.settings = good
    assert detail.status_code == 503
    assert detail.json()["code"] == "dependency_unavailable"
    assert write.status_code == 201  # new data uses the active key; old data needs the old one
    assert await count(review_world, "report_notes") == notes_before + 1
    recovered = await review_world.call(actor, "GET", f"/v1/reviewer/reports/{report_id}")
    assert recovered.status_code == 200


def test_migrations_started_together_wait_for_each_other_and_all_finish(
    admin_connection: Any,
) -> None:
    code = (
        "import sys; from alembic import command; from shaidago.db.revision import alembic_config; "
        "command.upgrade(alembic_config(sys.argv[1]), 'head')"
    )
    with disposable_database(admin_connection) as url:
        assert isinstance(url, URL)
        dsn = url.render_as_string(hide_password=False)
        procs = [
            subprocess.Popen(  # noqa: S603 - a fixed command with our own arguments
                [sys.executable, "-c", code, dsn], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            for _ in range(3)
        ]
        codes: list[int] = []
        for proc in procs:
            try:
                proc.communicate(timeout=90)
                codes.append(proc.returncode)
            except subprocess.TimeoutExpired:
                proc.kill()
                codes.append(-1)
    assert codes == [0, 0, 0]


@pytest.mark.parametrize("field", ["contact_value", "contact_channel"])
async def test_a_partial_contact_is_refused_before_anything_is_stored(
    review_world: ReviewWorld, field: str
) -> None:
    reports = await count(review_world, "reports")
    fields = review_world.public.fields(
        **{field: "email" if field == "contact_channel" else "x@example.test"}
    )
    response = await review_world.public.post(fields)
    assert response.status_code == 422
    assert await count(review_world, "reports") == reports

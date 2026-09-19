"""Optional reporter handles: no PII, generic failures, backoff, unlink-on-delete, and absence."""

import asyncio
import io
import logging
import re
import uuid
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
from shaidago.reports import handles
from shaidago.shared.clock import ManualClock
from shaidago.shared.database import Database, build_engine
from shaidago.shared.logging import configure_logging
from tests.integration.report_support import CANARY, CLIENT, Harness

FAST = PasswordVerifier(PasswordPolicy(time_cost=1, memory_cost_kib=1024, parallelism=1))
BASE = "/v1/reporter-handles"
GENERIC = "invalid_reporter_credentials"
PRIVILEGE = "42501"
UUID_SHAPE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def fast(harness: Harness) -> Harness:
    harness.app.state.dependencies = replace(
        harness.app.state.dependencies, password_verifier=FAST, lookup_minimum_seconds=0.0
    )
    return harness


def clock_of(harness: Harness) -> ManualClock:
    clock = harness.app.state.dependencies.clock
    assert isinstance(clock, ManualClock)
    return clock


async def call(
    harness: Harness, path: str, json: dict[str, Any], client: str | None = None
) -> httpx.Response:
    headers = {"X-Shaidago-Client-Hmac": client or uuid.uuid4().hex * 2}
    async with harness.client() as http:
        return await http.post(f"{BASE}{path}", json=json, headers=headers)


async def create(harness: Harness) -> dict[str, str]:
    async with harness.client() as http:
        response = await http.post(
            BASE,
            headers={
                "Idempotency-Key": str(uuid.uuid4()),
                "X-Shaidago-Client-Hmac": uuid.uuid4().hex * 2,
            },
        )
    assert response.status_code == 201
    return dict(response.json())


def creds(new: dict[str, str], **override: str) -> dict[str, str]:
    return {"handle": new["handle"], "passphrase": new["passphrase"], **override}


async def report_with(harness: Harness, new: dict[str, str], **extra: str) -> httpx.Response:
    fields = harness.fields(
        reporter_handle=new["handle"], reporter_passphrase=new["passphrase"], **extra
    )
    return await harness.post(fields, headers={"X-Shaidago-Client-Hmac": uuid.uuid4().hex * 2})


async def handle_state(harness: Harness, new: dict[str, str]) -> Any:
    rows = await harness.rows(
        "SELECT failure_count, backoff_until FROM app.reporter_handles "
        f"WHERE handle = '{new['handle']}'"
    )
    return rows[0]


async def test_creation_returns_the_credentials_once_and_stores_only_a_hash(
    harness: Harness,
) -> None:
    fast(harness)
    async with harness.client() as http:
        response = await http.post(BASE, headers={"Idempotency-Key": str(uuid.uuid4())})
    body = response.json()
    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    assert set(body) == {"handle", "passphrase", "recoverable"}
    assert body["recoverable"] is False
    assert handles.normalise_handle(body["handle"]) == body["handle"]
    assert set(body["passphrase"].split(" ")) <= set(handles.wordlist())
    assert len(body["passphrase"].split(" ")) == 6
    row = (
        await harness.rows(
            "SELECT handle, passphrase_hash FROM app.reporter_handles ORDER BY created_at DESC"
        )
    )[0]
    stored = "|".join(map(str, row))
    assert body["passphrase"] not in stored
    assert row.passphrase_hash.startswith("$argon2id$")


async def test_the_handle_table_holds_no_personal_or_recovery_data(harness: Harness) -> None:
    columns = {
        r[0]
        for r in await harness.rows(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'app' AND table_name = 'reporter_handles'"
        )
    }
    assert columns == {
        "id",
        "handle",
        "passphrase_hash",
        "created_at",
        "last_used_on",
        "failure_count",
        "last_failure_at",
        "backoff_until",
    }
    forbidden = ("email", "phone", "name", "ip", "device", "agent", "recover", "reset", "question")
    assert not [c for c in columns if any(word in c.split("_") for word in forbidden)]
    last_used = (
        await harness.rows(
            "SELECT data_type FROM information_schema.columns WHERE table_schema = 'app' "
            "AND table_name = 'reporter_handles' AND column_name = 'last_used_on'"
        )
    )[0][0]
    assert last_used == "date", "day granularity only"


async def test_a_retried_creation_replays_and_separate_ones_differ(harness: Harness) -> None:
    fast(harness)
    key = {"Idempotency-Key": str(uuid.uuid4())}
    async with harness.client() as http:
        first = await http.post(BASE, headers=key)
        second = await http.post(BASE, headers=key)
    assert second.content == first.content
    assert second.headers["idempotency-replayed"] == "true"
    other = await create(harness)
    assert other["handle"] != first.json()["handle"]
    assert other["passphrase"] != first.json()["passphrase"]
    async with harness.client() as http:
        assert (await http.post(BASE)).status_code == 400, "an Idempotency-Key is required"


async def test_a_report_can_carry_a_handle_and_the_handle_lists_only_safe_statuses(
    harness: Harness,
) -> None:
    fast(harness)
    new = await create(harness)
    receipts = [await report_with(harness, new) for _ in range(2)]
    assert [r.status_code for r in receipts] == [201, 201]
    for receipt in receipts:
        assert new["handle"] not in receipt.text
        assert new["passphrase"] not in receipt.text
    linked = await harness.rows(
        "SELECT anonymous, reporter_handle_id IS NOT NULL FROM app.reports "
        "WHERE reporter_handle_id IS NOT NULL"
    )
    assert [tuple(r) for r in linked].count((True, True)) >= 2
    listing = await call(harness, ":list-reports", creds(new))
    body = listing.json()
    assert listing.status_code == 200
    assert listing.headers["cache-control"] == "no-store"
    assert set(body) == {"reports"}
    assert len(body["reports"]) == 2
    assert all(
        set(item) == {"status", "status_updated_at", "message", "next_action"}
        for item in body["reports"]
    )
    assert all(item["status"] == "received" for item in body["reports"])
    for private in (CANARY, harness.slug, new["passphrase"], receipts[0].json()["tracking_code"]):
        assert private not in listing.text
    assert UUID_SHAPE.search(listing.text) is None
    # The tracking lookup for the report's code never mentions the handle.
    async with harness.client() as http:
        tracked = await http.post(
            "/v1/report-status:lookup",
            json={"code": receipts[0].json()["tracking_code"]},
            headers={"X-Shaidago-Client-Hmac": "ab" * 32},
        )
    assert new["handle"] not in tracked.text


async def test_wrong_unknown_malformed_and_deleted_handles_are_indistinguishable(
    harness: Harness,
) -> None:
    fast(harness)
    live = await create(harness)
    gone = await create(harness)
    assert (await call(harness, ":delete", creds(gone))).status_code == 204
    other = handles.generate()
    attempts = {
        "wrong passphrase": creds(
            live, passphrase="abacus abdomen abdominal abide abiding ability"
        ),
        "unknown handle": {"handle": other.handle, "passphrase": other.passphrase},
        "malformed handle": {"handle": "nonsense", "passphrase": live["passphrase"]},
        "empty": {"handle": "", "passphrase": ""},
        "deleted handle": creds(gone),
    }
    before = int((await harness.rows("SELECT count(*) FROM app.reports"))[0][0])
    seen: dict[str, tuple[int, dict[str, Any]]] = {}
    for label, credentials in attempts.items():
        for path in (":list-reports", ":delete"):
            response = await call(harness, path, credentials)
            body = response.json()
            body.pop("request_id", None)
            seen[f"{label}{path}"] = (response.status_code, body)
    assert {repr(v) for v in seen.values()} == {repr((403, seen["empty:delete"][1]))}
    assert seen["empty:delete"][1]["code"] == GENERIC
    # The same generic answer stops a submission, and nothing is stored.
    submit = await harness.post(
        harness.fields(reporter_handle=live["handle"], reporter_passphrase="wrong words here"),
        headers={"X-Shaidago-Client-Hmac": uuid.uuid4().hex * 2},
    )
    assert (submit.status_code, submit.json()["code"]) == (403, GENERIC)
    assert int((await harness.rows("SELECT count(*) FROM app.reports"))[0][0]) == before
    assert live["passphrase"] not in submit.text


async def test_a_handle_and_a_contact_are_exclusive_and_credentials_come_in_pairs(
    harness: Harness,
) -> None:
    fast(harness)
    new = await create(harness)
    both = await harness.post(
        harness.fields(
            reporter_handle=new["handle"],
            reporter_passphrase=new["passphrase"],
            contact_channel="email",
            contact_value="fictional@example.test",
        )
    )
    half = await harness.post(harness.fields(reporter_handle=new["handle"]))
    assert both.status_code == half.status_code == 422
    assert {e["code"] for e in both.json()["errors"]} == {"exclusive_with_contact"}
    assert {e["code"] for e in half.json()["errors"]} == {"required_together"}
    assert new["passphrase"] not in both.text + half.text


async def test_failures_back_off_exponentially_without_a_permanent_lockout(
    harness: Harness,
) -> None:
    fast(harness)
    clock = clock_of(harness)
    new = await create(harness)
    wrong = creds(new, passphrase="abacus abdomen abdominal abide abiding ability")
    for _ in range(3):
        assert (await call(harness, ":list-reports", wrong)).status_code == 403
    assert (await call(harness, ":list-reports", creds(new))).status_code == 200, "three free tries"
    for _ in range(4):
        await call(harness, ":list-reports", wrong)
    state = await handle_state(harness, new)
    assert state.failure_count == 4
    assert state.backoff_until is not None
    assert state.backoff_until - clock.now() == timedelta(seconds=5), "first step is 5 seconds"
    blocked = await call(harness, ":list-reports", creds(new))
    assert blocked.status_code == 403
    assert blocked.json()["code"] == GENERIC, "backoff looks like any other failure"
    assert (await handle_state(harness, new)).failure_count == 5, "a blocked try still counts"
    clock.advance(timedelta(seconds=11))
    assert (await call(harness, ":list-reports", creds(new))).status_code == 200
    reset = await handle_state(harness, new)
    assert (reset.failure_count, reset.backoff_until) == (0, None), "success clears the backoff"
    for _ in range(30):
        await call(harness, ":list-reports", wrong)
    capped = (await handle_state(harness, new)).backoff_until
    assert capped is not None
    assert capped - clock.now() <= timedelta(minutes=15), "the wait is capped, never permanent"
    clock.advance(timedelta(minutes=16))
    assert (await call(harness, ":list-reports", creds(new))).status_code == 200


async def test_one_client_is_rate_limited_per_handle_and_overall(harness: Harness) -> None:
    fast(harness)
    new = await create(harness)
    wrong = creds(new, passphrase="abacus abdomen abdominal abide abiding ability")
    codes = [
        (await call(harness, ":list-reports", wrong, client=CLIENT)).status_code for _ in range(12)
    ]
    assert codes[:10] == [403] * 10
    assert codes[10:] == [429, 429]
    other_client = await call(harness, ":list-reports", creds(new), client="ee" * 32)
    assert other_client.status_code in {200, 403}
    unknown = handles.generate()
    guesses = [
        (
            await call(
                harness,
                ":list-reports",
                {"handle": unknown.handle, "passphrase": "x"},
                client=CLIENT,
            )
        ).status_code
        for _ in range(2)
    ]
    assert guesses == [429, 429], "the per-client bucket covers unknown handles too"


async def test_deleting_a_handle_unlinks_every_report_and_removes_the_credential(
    harness: Harness,
) -> None:
    fast(harness)
    new = await create(harness)
    codes = [(await report_with(harness, new)).json()["tracking_code"] for _ in range(3)]
    before = int((await harness.rows("SELECT count(*) FROM app.reports"))[0][0])
    deleted = await call(harness, ":delete", creds(new))
    assert deleted.status_code == 204
    assert deleted.headers["cache-control"] == "no-store"
    assert deleted.content == b""
    assert int((await harness.rows("SELECT count(*) FROM app.reports"))[0][0]) == before
    handle_rows = await harness.rows(
        f"SELECT count(*) FROM app.reporter_handles WHERE handle = '{new['handle']}'"
    )
    assert handle_rows[0][0] == 0
    assert (
        await harness.rows(
            "SELECT count(*) FROM app.reports r WHERE r.anonymous AND r.reporter_handle_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM app.reporter_handles h WHERE h.id = r.reporter_handle_id)"
        )
    )[0][0] == 0
    async with harness.client() as http:
        for code in codes:
            tracked = await http.post(
                "/v1/report-status:lookup",
                json={"code": code},
                headers={"X-Shaidago-Client-Hmac": uuid.uuid4().hex * 2},
            )
            assert tracked.status_code == 200, "reports remain, tracked by their codes"
    for path in (":list-reports", ":delete"):
        assert (await call(harness, path, creds(new))).json()["code"] == GENERIC


async def test_concurrent_deletes_and_creates_stay_consistent(harness: Harness) -> None:
    fast(harness)
    new = await create(harness)
    await report_with(harness, new)
    first, second = await asyncio.gather(
        call(harness, ":delete", creds(new)), call(harness, ":delete", creds(new))
    )
    assert sorted([first.status_code, second.status_code]) in ([204, 204], [204, 403])
    created = await asyncio.gather(*(create(harness) for _ in range(5)))
    assert len({c["handle"] for c in created}) == 5


async def test_concurrent_identical_submissions_with_a_handle_make_one_report(
    harness: Harness,
) -> None:
    fast(harness)
    new = await create(harness)
    key = str(uuid.uuid4())
    fields = harness.fields(reporter_handle=new["handle"], reporter_passphrase=new["passphrase"])
    first, second = await asyncio.gather(
        harness.post(fields, key=key, headers={"X-Shaidago-Client-Hmac": "11" * 32}),
        harness.post(fields, key=key, headers={"X-Shaidago-Client-Hmac": "22" * 32}),
    )
    assert first.status_code == second.status_code == 201
    assert first.content == second.content
    linked = await harness.rows(
        f"SELECT count(*) FROM app.reports r JOIN app.reporter_handles h ON h.id = r.reporter_handle_id WHERE h.handle = '{new['handle']}'"
    )
    assert linked[0][0] == 1


async def test_credentials_never_reach_logs(harness: Harness) -> None:
    fast(harness)
    buffer = io.StringIO()
    configure_logging(service="svc", environment="test", level="DEBUG", stream=buffer)
    try:
        new = await create(harness)
        await report_with(harness, new)
        await call(harness, ":list-reports", creds(new))
        await call(harness, ":list-reports", creds(new, passphrase="a secret wrong guess"))
        await call(harness, ":delete", creds(new))
        output = buffer.getvalue()
    finally:
        structlog.reset_defaults()
        logging.getLogger().handlers.clear()
    for secret in (new["handle"], new["passphrase"], "a secret wrong guess"):
        assert secret not in output


async def test_reviewers_get_context_not_the_hash_and_a_shared_handle_counts_once(
    harness: Harness, role_urls: dict[str, URL]
) -> None:
    fast(harness)
    new = await create(harness)
    for _ in range(3):
        await report_with(harness, new)
    anonymous = await harness.post(harness.fields())
    assert anonymous.status_code == 201
    report_id = (
        await harness.rows(
            "SELECT r.id FROM app.reports r JOIN app.reporter_handles h "
            f"ON h.id = r.reporter_handle_id WHERE h.handle = '{new['handle']}' LIMIT 1"
        )
    )[0][0]
    engine = build_engine(
        role_urls["shaidago_reviewer"], application_name="r", statement_timeout_ms=8000
    )
    reviewer = Database(engine)
    try:
        async with reviewer.unit_of_work() as session:
            record = (
                await session.execute(
                    text("SELECT * FROM app.reporter_handle_track_record(:r)"), {"r": report_id}
                )
            ).all()
            unlinked = (
                await session.execute(
                    text(
                        "SELECT count(*) FROM app.reporter_handle_track_record("
                        "(SELECT id FROM app.reports WHERE reporter_handle_id IS NULL LIMIT 1))"
                    )
                )
            ).scalar_one()
        assert len(record) == 1, "reports sharing a handle are one row, never several people"
        assert record[0].handle.startswith("SG-H-")
        assert record[0].reports_total >= 3
        assert unlinked == 0
        for sql in (
            "SELECT passphrase_hash FROM app.reporter_handles",
            "SELECT * FROM app.reporter_handles",
        ):
            with pytest.raises(DBAPIError) as raised:
                async with reviewer.unit_of_work() as session:
                    await session.execute(text(sql))
            assert getattr(raised.value.orig, "sqlstate", None) == PRIVILEGE
    finally:
        await engine.dispose()


async def test_the_public_role_cannot_read_handles_and_only_public_may_call_the_functions(
    harness: Harness, role_urls: dict[str, URL]
) -> None:
    engine = build_engine(
        role_urls["shaidago_public"], application_name="p", statement_timeout_ms=8000
    )
    try:
        for sql in (
            "SELECT * FROM app.reporter_handles",
            "UPDATE app.reporter_handles SET failure_count = 0",
            "DELETE FROM app.reporter_handles",
        ):
            with pytest.raises(DBAPIError) as raised:
                async with Database(engine).unit_of_work() as session:
                    await session.execute(text(sql))
            assert getattr(raised.value.orig, "sqlstate", None) == PRIVILEGE
    finally:
        await engine.dispose()
    functions = (
        "reporter_handle_get(text)",
        "reporter_handle_record_failure(uuid, timestamptz)",
        "reporter_handle_record_success(uuid, date)",
        "reporter_handle_reports(uuid, integer)",
        "reporter_handle_delete(uuid)",
    )
    for signature in functions:
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
        }, signature


async def test_there_is_no_recovery_or_reset_endpoint(harness: Harness) -> None:
    paths = sorted(path for path in harness.app.openapi()["paths"] if "reporter-handles" in path)
    assert paths == [
        "/v1/reporter-handles",
        "/v1/reporter-handles:delete",
        "/v1/reporter-handles:list-reports",
    ]
    assert not any(word in path for path in paths for word in ("recover", "reset", "forgot"))

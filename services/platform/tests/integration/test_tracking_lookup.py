"""POST /v1/report-status:lookup: generic failures, minimal output, and bounded abuse."""

import base64
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy import LargeBinary, bindparam, text

from shaidago.api.app import create_app
from shaidago.reports.persistence import RECEIVED_MESSAGE
from shaidago.reports.status_lookup import NEXT_ACTIONS
from shaidago.reports.tracking import generate, lookup_key, normalise
from shaidago.shared import vocabulary
from tests.factories import KEY_B, build_settings
from tests.integration.report_support import CANARY, CLIENT, CONTACT_CANARY, Harness, png

LOOKUP = "/v1/report-status:lookup"
KEYS = {"status", "status_updated_at", "message", "next_action", "follow_up_questions"}
UUID_SHAPE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def instant(harness: Harness) -> Harness:
    """Skip the timing floor (tested separately) and keep the limits."""
    harness.app.state.dependencies = replace(
        harness.app.state.dependencies, lookup_minimum_seconds=0.0
    )
    return harness


async def submit(harness: Harness, **extra: str) -> str:
    fields = harness.fields(contact_channel="email", contact_value=CONTACT_CANARY, **extra)
    response = await harness.post(fields, files=[("evidence-name.png", png(), "image/png")])
    assert response.status_code == 201
    return str(response.json()["tracking_code"])


async def lookup(harness: Harness, code: str, client: str = CLIENT) -> httpx.Response:
    async with harness.client() as http:
        return await http.post(
            LOOKUP, json={"code": code}, headers={"X-Shaidago-Client-Hmac": client}
        )


async def change_status(harness: Harness, code: str, new: str, message: str, at: datetime) -> None:
    """What a reviewer's transition writes: one event and the matching projection."""
    async with harness.owner.unit_of_work() as session:
        row = (
            await session.execute(
                text(
                    "SELECT r.id, r.status FROM app.reports r "
                    "JOIN app.report_tracking_keys k ON k.report_id = r.id "
                    "WHERE k.lookup_hmac = :digest"
                ).bindparams(bindparam("digest", type_=LargeBinary)),
                {"digest": lookup_key(base64.b64decode(KEY_B), normalise(code))},
            )
        ).one()
        await session.execute(
            text(
                "INSERT INTO app.report_status_events (id, report_id, previous_status, new_status, "
                "public_message, actor_type, occurred_at) VALUES "
                "(gen_random_uuid(), :r, :old, :new, :m, 'reviewer', :at)"
            ),
            {"r": row.id, "old": row.status, "new": new, "m": message, "at": at},
        )
        await session.execute(
            text("UPDATE app.reports SET status = :new, status_updated_at = :at WHERE id = :r"),
            {"r": row.id, "new": new, "at": at},
        )


async def test_a_valid_code_returns_only_the_safe_status_view(harness: Harness) -> None:
    instant(harness)
    code = await submit(harness)
    response = await lookup(harness, code)
    body = response.json()
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert set(body) == KEYS
    assert (body["status"], body["message"]) == ("received", RECEIVED_MESSAGE)
    assert body["next_action"] == "wait_for_review"
    assert body["follow_up_questions"] == []
    for private in (CANARY, CONTACT_CANARY, harness.slug, "evidence-name", code, "reviewer"):
        assert private not in response.text
    assert UUID_SHAPE.search(response.text) is None, "no internal identifier is exposed"


VARIANTS: list[Callable[[str], str]] = [
    str.lower,
    lambda c: c.replace("-", " "),
    lambda c: c.replace("-", ""),
    lambda c: f"  {c}  ",
]


@pytest.mark.parametrize("variant", VARIANTS)
async def test_common_ways_of_typing_the_code_all_work(
    harness: Harness, variant: Callable[[str], str]
) -> None:
    instant(harness)
    code = await submit(harness)
    assert (await lookup(harness, variant(code))).status_code == 200


async def test_the_newest_reviewer_message_and_status_are_shown(harness: Harness) -> None:
    instant(harness)
    code = await submit(harness)
    later = datetime(2026, 9, 20, 9, 0, tzinfo=UTC)
    await change_status(harness, code, "under_review", "A reviewer is looking at this.", later)
    await change_status(
        harness, code, "referred", "Sent to the approved route.", later + timedelta(hours=1)
    )
    body = (await lookup(harness, code)).json()
    assert body["status"] == "referred"
    assert body["message"] == "Sent to the approved route."
    assert body["next_action"] == "see_escalation_guidance"
    assert body["status_updated_at"].startswith("2026-09-20T10:00:00")


def test_every_status_has_a_next_action() -> None:
    assert set(NEXT_ACTIONS) == set(vocabulary.values("report_status"))


async def test_every_failure_is_the_same_response(harness: Harness) -> None:
    instant(harness)
    real = await submit(harness)
    bad_checksum = real[:-1] + ("0" if real[-1] != "0" else "1")
    unknown = generate().formatted
    attempts = [bad_checksum, unknown, "", "SG-", "not a code", "x" * 256, real[:-3], "é" * 30]
    seen: list[tuple[int, dict[str, Any]]] = []
    for index, attempt in enumerate(attempts):
        response = await lookup(harness, attempt, client=f"{index:02x}" * 32)
        body = response.json()
        body.pop("request_id", None)
        assert response.headers["cache-control"] == "no-store"
        seen.append((response.status_code, body))
        for value in (attempt, real):
            assert not value or value not in response.text
    assert len({repr(item) for item in seen}) == 1
    assert seen[0][0] == 404
    assert seen[0][1]["code"] == "tracking_code_not_recognised"


async def test_shape_errors_do_not_reveal_anything_about_records(harness: Harness) -> None:
    instant(harness)
    async with harness.client() as http:
        wrong_field = await http.post(LOOKUP, json={"code": "x", "handle": "y"})
        missing = await http.post(LOOKUP, json={})
        oversized = await http.post(
            LOOKUP,
            content=b'{"code":"' + b"a" * 2000 + b'"}',
            headers={"content-type": "application/json"},
        )
        get = await http.get(LOOKUP)
        in_path = await http.get("/v1/report-status/SG-AAAAA-AAAAA-AAAAA-AAAAA-A")
    assert (wrong_field.status_code, missing.status_code) == (422, 422)
    assert oversized.status_code == 413
    assert get.status_code == 405
    assert in_path.status_code == 404


async def test_a_lookup_takes_at_least_the_configured_floor_either_way(harness: Harness) -> None:
    code = await submit(harness)
    harness.app.state.dependencies = replace(
        harness.app.state.dependencies, lookup_minimum_seconds=0.3
    )
    durations: list[float] = []
    for attempt in (code, generate().formatted, "garbage"):
        start = time.monotonic()
        await lookup(harness, attempt, client=uuid.uuid4().hex * 2)
        durations.append(time.monotonic() - start)
    assert min(durations) >= 0.3
    assert max(durations) - min(durations) < 0.25, "hit and miss are indistinguishable by time"


async def test_lookups_are_limited_per_client_and_per_code_prefix(harness: Harness) -> None:
    instant(harness)
    code = await submit(harness)
    statuses = [(await lookup(harness, code, client="dd" * 32)).status_code for _ in range(7)]
    assert statuses == [200] * 5 + [429] * 2, "five tries per client and code prefix"
    limited = await lookup(harness, code, client="dd" * 32)
    assert limited.headers["retry-after"].isdigit()
    assert code not in limited.text
    other = await lookup(harness, code, client="ee" * 32)
    assert other.status_code == 200, "another client is not locked out"
    per_client = [
        (await lookup(harness, generate().formatted, client="ff" * 32)).status_code
        for _ in range(25)
    ]
    assert per_client.count(429) >= 1, "guessing many codes from one client is stopped"


async def test_a_retired_pepper_still_finds_a_report_created_under_it(harness: Harness) -> None:
    instant(harness)
    code = await submit(harness)
    rotated = build_settings(
        TRACKING_PEPPERS=(f"pepper-1={KEY_B},pepper-2={base64.b64encode(b'c' * 32).decode()}"),
        TRACKING_ACTIVE_PEPPER_VERSION="pepper-2",
    )
    dependencies = harness.app.state.dependencies
    app = create_app(rotated, dependencies)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://api.test",
        headers=harness.client().headers,
    ) as http:
        found = await http.post(LOOKUP, json={"code": code})
    assert found.status_code == 200


async def test_only_the_public_role_may_call_the_lookup_and_it_still_cannot_read_reports(
    harness: Harness,
) -> None:
    async with harness.owner.unit_of_work() as session:
        grants = {
            role: (
                await session.execute(
                    text(
                        "SELECT has_function_privilege(:r, 'app.tracking_lookup(bytea[])', 'EXECUTE')"
                    ),
                    {"r": role},
                )
            ).scalar_one()
            for role in ("shaidago_public", "shaidago_reviewer", "shaidago_worker", "public")
        }
        oversized = (
            await session.execute(
                text("SELECT count(*) FROM app.tracking_lookup(:d)"),
                {"d": [bytes([i]) * 32 for i in range(9)]},
            )
        ).scalar_one()
    assert grants == {
        "shaidago_public": True,
        "shaidago_reviewer": False,
        "shaidago_worker": False,
        "public": False,
    }
    assert oversized == 0, "more digests than pepper versions can ever exist returns nothing"

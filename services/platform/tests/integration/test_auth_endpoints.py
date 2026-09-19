"""Sign-in and sign-out: generic failures, bounded abuse, audit, rehash, and no secrets in logs."""

import asyncio
import io
import json
import logging
import os
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import structlog
from fastapi.testclient import TestClient
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.engine import URL

from shaidago.api.app import create_app
from shaidago.api.dependencies import Dependencies
from shaidago.auth.passwords import PasswordPolicy, PasswordVerifier
from shaidago.auth.reviewers import ReviewerService, find_reviewer
from shaidago.shared.clock import ManualClock
from shaidago.shared.database import Database, build_engine
from shaidago.shared.ids import Uuid7Generator
from shaidago.shared.logging import configure_logging
from shaidago.shared.ratelimit import (
    InMemoryRateLimiter,
    RateLimitUnavailableError,
    RedisRateLimiter,
)
from tests.factories import CREDENTIAL, build_settings

START = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
FAST = PasswordVerifier(PasswordPolicy(time_cost=1, memory_cost_kib=1024, parallelism=1))
STRONGER = PasswordVerifier(PasswordPolicy(time_cost=2, memory_cost_kib=2048, parallelism=1))
PASSWORD = "a-long-enough-reviewer-password"
INTERNAL = {"Authorization": f"Bearer web.{CREDENTIAL}"}
CLIENT_A = "aa" * 32
CLIENT_B = "bb" * 32


class Harness:
    def __init__(self, owner: Database, client: TestClient, clock: ManualClock) -> None:
        self.owner, self.client, self.clock = owner, client, clock

    async def reviewer(self, *, role: str = "reviewer", verifier: PasswordVerifier = FAST) -> str:
        identifier = f"auth-{uuid.uuid4().hex[:10]}"
        async with self.owner.unit_of_work() as session:
            await ReviewerService(
                session,
                clock=self.clock,
                ids=Uuid7Generator(self.clock),
                passwords=verifier,
                deployed=False,
            ).create(identifier, PASSWORD, role)  # type: ignore[arg-type]
        return identifier

    def sign_in(
        self,
        identifier: str,
        password: str = PASSWORD,
        client: str = CLIENT_A,
        request_id: str | None = None,
    ) -> Any:
        headers = {"X-Shaidago-Client-Hmac": client}
        if request_id is not None:
            headers["X-Request-Id"] = request_id
        return self.client.post(
            "/v1/auth/sessions",
            json={"identifier": identifier, "password": password},
            headers=headers,
        )


@pytest.fixture
async def harness(role_urls: dict[str, URL]) -> AsyncIterator[Harness]:
    owner_engine = build_engine(role_urls["owner"], application_name="o", statement_timeout_ms=8000)
    reviewer_engine = build_engine(
        role_urls["shaidago_reviewer"], application_name="r", statement_timeout_ms=8000
    )
    clock = ManualClock(START)
    app = create_app(
        build_settings(),
        Dependencies(
            clock=clock,
            ids=Uuid7Generator(clock),
            reviewer_database=Database(reviewer_engine),
            password_verifier=STRONGER,
            rate_limiter=InMemoryRateLimiter(clock),
        ),
    )
    with TestClient(app, headers=INTERNAL) as client:
        yield Harness(Database(owner_engine), client, clock)
    await owner_engine.dispose()
    await reviewer_engine.dispose()


def normalised(response: Any) -> dict[str, object]:
    return {k: v for k, v in response.json().items() if k != "request_id"}


async def test_sign_in_returns_the_session_once_with_the_cookie_contract(harness: Harness) -> None:
    identifier = await harness.reviewer(role="admin", verifier=STRONGER)
    response = harness.sign_in(identifier.upper())
    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["reviewer"] == {"role": "admin"}
    assert body["cookie"] == {
        "name": "sg_session", "secure": False, "http_only": True, "same_site": "Lax",
        "path": "/", "max_age_seconds": 28800,
    }  # fmt: skip
    assert len(body["session_token"]) >= 43
    assert body["csrf_token"] != body["session_token"]
    assert body["idle_timeout_seconds"] == 1800
    assert datetime.fromisoformat(body["expires_at"]) == START + timedelta(hours=8)
    assert set(body) == {
        "session_token",
        "csrf_token",
        "expires_at",
        "idle_timeout_seconds",
        "cookie",
        "reviewer",
    }


async def test_every_failure_is_one_indistinguishable_response(harness: Harness) -> None:
    active = await harness.reviewer(verifier=STRONGER)
    disabled = await harness.reviewer(verifier=STRONGER)
    async with harness.owner.unit_of_work() as session:
        found = await find_reviewer(session, disabled)
        assert found is not None
        await session.execute(
            text("UPDATE app.reviewers SET state = 'disabled' WHERE id = :i"), {"i": found.id}
        )
    cases = [
        (active, "wrong-password-entirely"),
        (f"nobody-{uuid.uuid4().hex[:8]}", PASSWORD),
        (disabled, PASSWORD),
        ("x", PASSWORD),
        ("has space", PASSWORD),
        (active, PASSWORD + "é"),
    ]
    responses = [harness.sign_in(i, p, client=f"{n:02x}" * 32) for n, (i, p) in enumerate(cases)]
    assert {r.status_code for r in responses} == {401}
    assert {json.dumps(normalised(r), sort_keys=True) for r in responses} == {
        json.dumps(normalised(responses[0]), sort_keys=True)
    }
    assert responses[0].json()["code"] == "invalid_credentials"


async def test_failures_and_successes_are_audited_without_identifiers_or_passwords(
    harness: Harness,
) -> None:
    identifier = await harness.reviewer(verifier=STRONGER)
    failed_id, ok_id = str(uuid.uuid4()), str(uuid.uuid4())
    harness.sign_in(identifier, "nope-nope-nope-nope", request_id=failed_id)
    harness.sign_in(identifier, request_id=ok_id)
    async with harness.owner.unit_of_work() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT request_id, outcome, actor_id, details::text AS details "
                    "FROM app.audit_events WHERE event = 'reviewer_sign_in' "
                    "AND request_id IN (:a, :b)"
                ),
                {"a": failed_id, "b": ok_id},
            )
        ).all()
    by_request = {r.request_id: r for r in rows}
    assert by_request[failed_id].outcome == "failure"
    assert by_request[failed_id].actor_id is None
    assert by_request[ok_id].outcome == "success"
    assert by_request[ok_id].actor_id is not None
    dump = " ".join(r.details for r in rows)
    assert identifier not in dump
    assert "nope-nope" not in dump
    assert PASSWORD not in dump


async def test_last_sign_in_is_recorded_and_a_weaker_hash_is_upgraded_on_success_only(
    harness: Harness,
) -> None:
    identifier = await harness.reviewer(verifier=FAST)
    async with harness.owner.unit_of_work() as session:
        before = await find_reviewer(session, identifier)
    assert before is not None
    assert harness.sign_in(identifier, "wrong-password-value").status_code == 401
    async with harness.owner.unit_of_work() as session:
        unchanged = await find_reviewer(session, identifier)
    assert unchanged is not None
    assert unchanged.password_hash == before.password_hash, "no rehash without a successful sign-in"
    assert harness.sign_in(identifier).status_code == 201
    async with harness.owner.unit_of_work() as session:
        after = await find_reviewer(session, identifier)
        stamp = (
            await session.execute(
                text("SELECT last_sign_in_at FROM app.reviewers WHERE id = :i"), {"i": before.id}
            )
        ).scalar_one()
    assert after is not None
    assert after.password_hash != before.password_hash
    assert STRONGER.verify(after.password_hash, PASSWORD).matches
    assert STRONGER.verify(after.password_hash, PASSWORD).new_hash is None
    assert stamp == START


async def test_attempts_are_bounded_per_client_and_identifier_without_locking_the_account(
    harness: Harness,
) -> None:
    victim = await harness.reviewer(verifier=STRONGER)
    statuses = [
        harness.sign_in(victim, "guess-guess-guess-x", client=CLIENT_A).status_code
        for _ in range(7)
    ]
    assert statuses == [401] * 5 + [429] * 2
    limited = harness.sign_in(victim, PASSWORD, client=CLIENT_A)
    assert limited.status_code == 429
    assert limited.json()["code"] == "rate_limited"
    assert int(limited.headers["retry-after"]) > 0
    assert harness.sign_in(victim, PASSWORD, client=CLIENT_B).status_code == 201, (
        "an attacker at one address cannot lock the real reviewer out from another"
    )
    harness.clock.advance(timedelta(minutes=16))
    assert harness.sign_in(victim, PASSWORD, client=CLIENT_A).status_code == 201


async def test_a_client_is_limited_across_identifiers_too(harness: Harness) -> None:
    statuses = [
        harness.sign_in(
            f"nobody-{i}-{uuid.uuid4().hex[:6]}", "irrelevant-password", client=CLIENT_A
        ).status_code
        for i in range(12)
    ]
    assert statuses[:10] == [401] * 10
    assert statuses[10:] == [429, 429]


async def test_body_limits_and_shape_are_enforced(harness: Harness) -> None:
    client = harness.client
    oversized = client.post(
        "/v1/auth/sessions",
        content=json.dumps({"identifier": "a" * 3000, "password": "p"}),
        headers={"content-type": "application/json"},
    )
    assert oversized.status_code == 413
    assert oversized.json()["code"] == "payload_too_large"
    for payload in (
        {"identifier": "x" * 129, "password": "p"},
        {"identifier": "x", "password": "p" * 257},
        {"identifier": "", "password": "p"},
        {"identifier": "x"},
        {"identifier": "x", "password": "p", "extra": 1},
        {"identifier": 5, "password": "p"},
    ):
        response = client.post("/v1/auth/sessions", json=payload)
        assert response.status_code == 422
        assert "x" * 100 not in response.text


async def test_the_password_and_tokens_never_reach_logs(harness: Harness) -> None:
    identifier = await harness.reviewer(verifier=STRONGER)
    buffer = io.StringIO()
    configure_logging(service="svc", environment="test", level="DEBUG", stream=buffer)
    try:
        ok = harness.sign_in(identifier)
        harness.sign_in(identifier, "a-secret-wrong-guess-value")
        output = buffer.getvalue()
    finally:
        structlog.reset_defaults()
        logging.getLogger().handlers.clear()
    body = ok.json()
    for secret in (
        PASSWORD,
        "a-secret-wrong-guess-value",
        body["session_token"],
        body["csrf_token"],
    ):
        assert secret not in output
    assert identifier not in output


async def test_sign_out_revokes_the_session_and_replay_fails(harness: Harness) -> None:
    identifier = await harness.reviewer(verifier=STRONGER)
    body = harness.sign_in(identifier).json()
    headers = {"X-Shaidago-Session": body["session_token"], "X-Shaidago-Csrf": body["csrf_token"]}
    assert (
        harness.client.delete(
            "/v1/auth/sessions/current", headers={"X-Shaidago-Session": body["session_token"]}
        ).status_code
        == 403
    )
    out = harness.client.delete("/v1/auth/sessions/current", headers=headers)
    assert out.status_code == 204
    assert out.headers["cache-control"] == "no-store"
    assert out.content == b""
    assert harness.client.delete("/v1/auth/sessions/current", headers=headers).status_code == 401
    async with harness.owner.unit_of_work() as session:
        events = (
            await session.execute(
                text("SELECT count(*) FROM app.audit_events WHERE event = 'reviewer_sign_out'")
            )
        ).scalar_one()
    assert events >= 1


async def test_signing_in_again_issues_a_different_session_each_time(harness: Harness) -> None:
    identifier = await harness.reviewer(verifier=STRONGER)
    tokens = {
        harness.sign_in(identifier, client=f"{n:02x}" * 32).json()["session_token"]
        for n in range(3)
    }
    assert len(tokens) == 3


async def test_sign_in_needs_a_configured_limiter_and_fails_closed_without_one(
    role_urls: dict[str, URL],
) -> None:
    engine = build_engine(
        role_urls["shaidago_reviewer"], application_name="r", statement_timeout_ms=8000
    )
    try:
        app = create_app(build_settings(), Dependencies(reviewer_database=Database(engine)))
        with TestClient(app, headers=INTERNAL) as client:
            response = client.post(
                "/v1/auth/sessions", json={"identifier": "abc", "password": PASSWORD}
            )
        assert response.status_code == 503
    finally:
        await engine.dispose()


def redis_client(port: str | None = None) -> Redis:
    return Redis(
        host=os.environ.get("INFRA_DB_HOST", "127.0.0.1"),
        port=int(port or os.environ.get("INFRA_REDIS_PORT", "56379")),
        password=os.environ.get("REDIS_PASSWORD"),
        socket_connect_timeout=1,
        socket_timeout=1,
    )


async def test_the_redis_limiter_counts_per_window_and_expires_keys() -> None:
    client = redis_client()
    limiter = RedisRateLimiter(client)
    key = f"sg:test:{uuid.uuid4().hex}"
    try:
        decisions = [await limiter.hit(key, limit=2, window_seconds=2) for _ in range(4)]
        assert [d.allowed for d in decisions] == [True, True, False, False]
        assert 1 <= decisions[-1].retry_after_seconds <= 2
        await asyncio.sleep(2.2)
        assert (await limiter.hit(key, limit=2, window_seconds=2)).allowed
    finally:
        await client.delete(key)
        await limiter.close()


async def test_the_redis_limiter_fails_closed_when_redis_is_unreachable() -> None:
    limiter = RedisRateLimiter(redis_client("1"))
    try:
        with pytest.raises(RateLimitUnavailableError):
            await limiter.hit("sg:test:unreachable", limit=1, window_seconds=1)
    finally:
        await limiter.close()

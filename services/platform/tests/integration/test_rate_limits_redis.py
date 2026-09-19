"""The Redis sliding-window limiter against real Redis: atomic, shared, expiring, fail-closed."""

import asyncio
import os
import re
import time
import uuid
from pathlib import Path

import pytest
from redis.asyncio import Redis

from shaidago.api.rate_policy import POLICIES
from shaidago.shared.config import RateLimitSettings
from shaidago.shared.ratelimit import RateLimitUnavailableError, RedisRateLimiter


def redis_url() -> str:
    return os.environ.get("REDIS_URL", "redis://localhost:56379/0")


def client() -> Redis:
    return Redis.from_url(redis_url(), socket_connect_timeout=1, socket_timeout=2)  # pyright: ignore[reportUnknownMemberType]


def key(name: str = "t") -> str:
    return f"sg:rl:test:{name}:{uuid.uuid4().hex}"


async def test_concurrent_attempts_from_many_connections_admit_exactly_the_limit() -> None:
    clients = [client() for _ in range(4)]  # four API processes sharing one Redis
    limiters = [RedisRateLimiter(c) for c in clients]
    shared = key()
    try:
        decisions = await asyncio.gather(
            *(limiters[n % 4].hit(shared, limit=10, window_seconds=30) for n in range(80))
        )
        assert sum(d.allowed for d in decisions) == 10
        assert min(d.remaining for d in decisions) == 0
        assert all(1 <= d.retry_after_seconds <= 30 for d in decisions if not d.allowed)
    finally:
        for c in clients:
            await c.aclose()


async def test_the_window_slides_and_refused_attempts_do_not_extend_the_lockout() -> None:
    c = client()
    limiter = RedisRateLimiter(c)
    name = key()
    try:
        assert [(await limiter.hit(name, limit=2, window_seconds=2)).allowed for _ in range(2)] == [
            True,
            True,
        ]
        started = time.monotonic()
        for _ in range(20):  # hammering a closed door
            denied = await limiter.hit(name, limit=2, window_seconds=2)
            assert not denied.allowed
            assert denied.retry_after_seconds in {1, 2}
        await asyncio.sleep(max(0.0, 2.2 - (time.monotonic() - started)))
        assert (await limiter.hit(name, limit=2, window_seconds=2)).allowed
    finally:
        await c.aclose()


async def test_keys_are_independent_and_expire_on_their_own() -> None:
    c = client()
    limiter = RedisRateLimiter(c)
    first, second = key("a"), key("b")
    try:
        for _ in range(3):
            await limiter.hit(first, limit=1, window_seconds=1)
        assert (await limiter.hit(second, limit=1, window_seconds=1)).allowed
        assert await c.pttl(first) > 0
        await asyncio.sleep(1.3)
        assert await c.exists(first) == 0  # no leftover state once the window has passed
    finally:
        await c.aclose()


async def test_an_unreachable_redis_is_reported_so_callers_can_fail_closed() -> None:
    dead = Redis.from_url("redis://127.0.0.1:1/0", socket_connect_timeout=0.2, socket_timeout=0.2)  # pyright: ignore[reportUnknownMemberType]
    try:
        with pytest.raises(RateLimitUnavailableError):
            await RedisRateLimiter(dead).hit(key(), limit=1, window_seconds=1)
    finally:
        await dead.aclose()


def test_every_rate_limit_key_in_the_source_is_registered_in_the_policy_table() -> None:
    source = Path(__file__).parents[2] / "src" / "shaidago"
    found: set[str] = set()
    for path in source.rglob("*.py"):
        if path.name == "rate_policy.py":
            continue
        found |= set(re.findall(r'f?"(sg:rl:[a-z:_]+)', path.read_text("utf-8")))
    assert found
    registered = [p.prefix for p in POLICIES]
    for used in sorted(found):
        assert any(used.startswith(prefix) or prefix.startswith(used) for prefix in registered), (
            used
        )


def test_every_policy_names_a_real_setting_and_fails_closed() -> None:
    fields = set(RateLimitSettings.model_fields)
    for policy in POLICIES:
        assert policy.on_unavailable == "closed"
        assert policy.setting in fields or policy.setting.startswith("fixed "), policy.setting

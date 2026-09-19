"""Fixed-window rate limiting behind a small interface.

``RedisRateLimiter`` is the shared limiter for the running service; ``InMemoryRateLimiter`` is the
deterministic test adapter. If Redis cannot be reached the limiter raises
``RateLimitUnavailableError`` and callers fail closed: an abuse control that silently turns
off is worse than a brief outage.
"""

import math
from dataclasses import dataclass
from typing import Protocol

from redis.asyncio import Redis
from redis.exceptions import RedisError

from shaidago.shared.clock import Clock


class RateLimitUnavailableError(Exception):
    """The limiter's backing store failed; callers must not treat the request as allowed."""


@dataclass(frozen=True)
class RateDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int


class RateLimiter(Protocol):
    async def hit(self, key: str, *, limit: int, window_seconds: int) -> RateDecision:
        """Count one attempt against ``key`` and say whether it is within ``limit`` per window."""
        ...


class InMemoryRateLimiter:
    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._windows: dict[str, tuple[int, float]] = {}

    async def hit(self, key: str, *, limit: int, window_seconds: int) -> RateDecision:
        now = self._clock.now().timestamp()
        count, reset_at = self._windows.get(key, (0, now + window_seconds))
        if now >= reset_at:
            count, reset_at = 0, now + window_seconds
        count += 1
        self._windows[key] = (count, reset_at)
        return _decision(count, limit, math.ceil(reset_at - now))


class RedisRateLimiter:
    """Also a managed resource: ``open`` checks reachability lazily, ``close`` releases the pool."""

    def __init__(self, client: Redis) -> None:
        self._client = client

    async def hit(self, key: str, *, limit: int, window_seconds: int) -> RateDecision:
        try:
            pipeline = self._client.pipeline(transaction=True)
            pipeline.set(key, 0, ex=window_seconds, nx=True)
            pipeline.incr(key)
            pipeline.ttl(key)
            _, count, ttl = await pipeline.execute()
        except RedisError as error:
            raise RateLimitUnavailableError from error
        return _decision(int(count), limit, max(int(ttl), 1))

    async def open(self) -> None:
        return

    async def close(self) -> None:
        await self._client.aclose()


def _decision(count: int, limit: int, retry_after: int) -> RateDecision:
    return RateDecision(
        allowed=count <= limit, remaining=max(limit - count, 0), retry_after_seconds=retry_after
    )

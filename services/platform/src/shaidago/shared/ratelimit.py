"""Fixed-window rate limiting behind a small interface.

``RedisRateLimiter`` is the shared limiter for the running service; ``InMemoryRateLimiter`` is the
deterministic test adapter. If Redis cannot be reached the limiter raises
``RateLimitUnavailableError`` and callers fail closed: an abuse control that silently turns
off is worse than a brief outage.
"""

import math
import secrets
from collections.abc import Callable
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


# One atomic step: drop entries older than the window, count what is left, and record this
# attempt only if it is within the limit. Time comes from Redis, so every API process shares one
# clock. A refused attempt is not recorded, so hammering a limit never extends its own lockout.
_SLIDING_WINDOW = """
local now = redis.call('TIME')
local now_ms = now[1] * 1000 + math.floor(now[2] / 1000)
local window_ms = tonumber(ARGV[1]) * 1000
local limit = tonumber(ARGV[2])
redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, now_ms - window_ms)
local count = redis.call('ZCARD', KEYS[1])
if count < limit then
  redis.call('ZADD', KEYS[1], now_ms, ARGV[3])
  redis.call('PEXPIRE', KEYS[1], window_ms)
  return {1, limit - count - 1, 0}
end
local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
local retry_ms = tonumber(oldest[2]) + window_ms - now_ms
return {0, 0, math.ceil(retry_ms / 1000)}
"""


class RedisRateLimiter:
    """Sliding-window limiter shared by every API process. Also a managed resource: ``open``
    checks reachability lazily, ``close`` releases the pool."""

    def __init__(
        self, client: Redis, *, token: Callable[[], str] = lambda: secrets.token_hex(8)
    ) -> None:
        self._client = client
        self._token = token

    async def check(self) -> None:
        """Readiness: Redis answers PING. Raises when it does not."""
        await self._client.ping()  # pyright: ignore[reportUnknownMemberType, reportGeneralTypeIssues]

    async def hit(self, key: str, *, limit: int, window_seconds: int) -> RateDecision:
        try:
            raw = await self._client.eval(  # pyright: ignore[reportUnknownMemberType, reportGeneralTypeIssues]
                _SLIDING_WINDOW, 1, key, window_seconds, limit, self._token()
            )
            allowed, remaining, retry_after = (int(v) for v in raw)  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
        except (RedisError, ValueError, TypeError) as error:
            raise RateLimitUnavailableError from error
        return RateDecision(
            allowed=bool(allowed),
            remaining=max(remaining, 0),
            retry_after_seconds=max(retry_after, 1),
        )

    async def open(self) -> None:
        return

    async def close(self) -> None:
        await self._client.aclose()


def _decision(count: int, limit: int, retry_after: int) -> RateDecision:
    return RateDecision(
        allowed=count <= limit, remaining=max(limit - count, 0), retry_after_seconds=retry_after
    )

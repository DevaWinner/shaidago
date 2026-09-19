from datetime import UTC, datetime, timedelta

from shaidago.shared.clock import ManualClock
from shaidago.shared.ratelimit import InMemoryRateLimiter

START = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)


async def test_attempts_beyond_the_limit_are_refused_until_the_window_ends() -> None:
    clock = ManualClock(START)
    limiter = InMemoryRateLimiter(clock)
    decisions = [await limiter.hit("k", limit=3, window_seconds=60) for _ in range(5)]
    assert [d.allowed for d in decisions] == [True, True, True, False, False]
    assert [d.remaining for d in decisions] == [2, 1, 0, 0, 0]
    assert decisions[3].retry_after_seconds == 60
    clock.advance(timedelta(seconds=61))
    assert (await limiter.hit("k", limit=3, window_seconds=60)).allowed


async def test_keys_are_independent_and_retry_after_shrinks_within_the_window() -> None:
    clock = ManualClock(START)
    limiter = InMemoryRateLimiter(clock)
    for _ in range(3):
        await limiter.hit("a", limit=2, window_seconds=100)
    assert not (await limiter.hit("a", limit=2, window_seconds=100)).allowed
    assert (await limiter.hit("b", limit=2, window_seconds=100)).allowed
    clock.advance(timedelta(seconds=40))
    assert (await limiter.hit("a", limit=2, window_seconds=100)).retry_after_seconds == 60

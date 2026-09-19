"""One place that turns a rate-limiter decision into the API's problem responses."""

from shaidago.api.dependencies import Dependencies
from shaidago.shared.problems import DEPENDENCY_UNAVAILABLE, RATE_LIMITED, ProblemError
from shaidago.shared.ratelimit import RateLimitUnavailableError

HOUR_SECONDS = 3600


async def enforce_rate_limit(
    dependencies: Dependencies, key: str, *, limit: int, window_seconds: int = HOUR_SECONDS
) -> None:
    """Fail closed if the limiter is down, and say how long to wait if the limit is exceeded."""
    limiter = dependencies.rate_limiter
    if limiter is None:
        raise ProblemError(DEPENDENCY_UNAVAILABLE)
    try:
        decision = await limiter.hit(key, limit=limit, window_seconds=window_seconds)
    except RateLimitUnavailableError:
        raise ProblemError(DEPENDENCY_UNAVAILABLE) from None
    if not decision.allowed:
        raise ProblemError(RATE_LIMITED, headers={"Retry-After": str(decision.retry_after_seconds)})

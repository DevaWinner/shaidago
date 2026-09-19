"""Injectable UTC clock. Domain code takes a ``Clock``; it never calls ``datetime.now`` itself."""

from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """The current time as a timezone-aware UTC ``datetime``."""
        ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class ManualClock:
    """Deterministic clock for tests: it moves only when told to."""

    def __init__(self, start: datetime) -> None:
        self._now = _require_utc(start)

    def now(self) -> datetime:
        return self._now

    def set(self, moment: datetime) -> None:
        self._now = _require_utc(moment)

    def advance(self, delta: timedelta) -> None:
        self._now += delta


def _require_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None or moment.utcoffset() != timedelta(0):
        raise ValueError("clock values must be timezone-aware UTC datetimes")
    return moment.astimezone(UTC)

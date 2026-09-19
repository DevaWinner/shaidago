"""UUIDv7 identifiers (RFC 9562), monotonic within a process, with a deterministic test adapter.

Layout: 48-bit millisecond timestamp, version 7, a 12-bit counter, variant bits, and 62 random
bits. IDs from one generator strictly increase even when many are minted in one millisecond or
the clock steps backwards, so they sort by creation and make good keyset-pagination tie-breakers.
"""

import secrets
import threading
from collections.abc import Callable
from typing import Protocol
from uuid import UUID

from shaidago.shared.clock import Clock, SystemClock

_COUNTER_BITS = 12
_COUNTER_MAX = (1 << _COUNTER_BITS) - 1
_TIMESTAMP_MAX = (1 << 48) - 1


class IdGenerator(Protocol):
    def new(self) -> UUID: ...


class Uuid7Generator:
    def __init__(
        self,
        clock: Clock | None = None,
        random_bytes: Callable[[int], bytes] = secrets.token_bytes,
    ) -> None:
        self._clock = clock or SystemClock()
        self._random_bytes = random_bytes
        self._lock = threading.Lock()
        self._last_ms = -1
        self._counter = 0

    def new(self) -> UUID:
        with self._lock:
            millis = int(self._clock.now().timestamp() * 1000)
            if millis > self._last_ms:
                self._last_ms = millis
                # Start below the maximum so a burst in one millisecond has headroom.
                self._counter = int.from_bytes(self._random_bytes(2), "big") & (_COUNTER_MAX >> 1)
            else:
                # Same millisecond, or the clock stepped back: keep increasing.
                self._counter += 1
                if self._counter > _COUNTER_MAX:
                    self._last_ms += 1
                    self._counter = 0
            if not 0 <= self._last_ms <= _TIMESTAMP_MAX:
                raise OverflowError("timestamp outside the UUIDv7 range")
            tail = int.from_bytes(self._random_bytes(8), "big") & ((1 << 62) - 1)
            value = (
                (self._last_ms << 80) | (0x7 << 76) | (self._counter << 64) | (0b10 << 62) | tail
            )
        return UUID(int=value)


class SequentialIds:
    """Deterministic UUIDv7-shaped IDs for tests: 1, 2, 3, ... under a fixed timestamp."""

    def __init__(self, start: int = 1, timestamp_ms: int = 1_800_000_000_000) -> None:
        self._next = start
        self._timestamp_ms = timestamp_ms

    def new(self) -> UUID:
        counter, self._next = self._next, self._next + 1
        return UUID(
            int=(self._timestamp_ms << 80)
            | (0x7 << 76)
            | (0b10 << 62)
            | (counter & ((1 << 62) - 1))
        )


def uuid7_timestamp_ms(value: UUID) -> int:
    if value.version != 7:  # noqa: PLR2004 - the UUID version this module defines
        raise ValueError("not a UUIDv7")
    return value.int >> 80

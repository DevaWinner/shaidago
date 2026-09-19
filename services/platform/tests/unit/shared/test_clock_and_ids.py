from datetime import UTC, datetime, timedelta, timezone
from itertools import pairwise
from uuid import UUID

import pytest
from hypothesis import given
from hypothesis import strategies as st

from shaidago.shared.clock import ManualClock, SystemClock
from shaidago.shared.ids import SequentialIds, Uuid7Generator, uuid7_timestamp_ms

START = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)


def test_system_clock_is_timezone_aware_utc() -> None:
    assert SystemClock().now().utcoffset() == timedelta(0)


def test_manual_clock_moves_only_when_told_and_rejects_naive_or_offset_times() -> None:
    clock = ManualClock(START)
    assert clock.now() == clock.now() == START
    clock.advance(timedelta(minutes=15))
    assert clock.now() == START + timedelta(minutes=15)
    with pytest.raises(ValueError, match="UTC"):
        clock.set(datetime(2026, 1, 1))  # noqa: DTZ001 - the naive value is the test input
    with pytest.raises(ValueError, match="UTC"):
        ManualClock(datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=1))))


def test_uuid7_has_version_variant_and_timestamp_from_the_clock() -> None:
    generated = Uuid7Generator(ManualClock(START)).new()
    assert generated.version == 7
    assert generated.variant == "specified in RFC 4122"
    assert uuid7_timestamp_ms(generated) == int(START.timestamp() * 1000)


def test_uuid7_is_strictly_increasing_within_one_millisecond() -> None:
    generator = Uuid7Generator(ManualClock(START))
    values = [generator.new() for _ in range(10_000)]  # far more than one 12-bit counter
    assert values == sorted(values)
    assert len(set(values)) == len(values)


def test_uuid7_keeps_increasing_when_the_clock_steps_backwards() -> None:
    clock = ManualClock(START)
    generator = Uuid7Generator(clock)
    first = generator.new()
    clock.advance(timedelta(seconds=-30))
    assert generator.new() > first


def test_uuid7_generation_is_deterministic_with_injected_clock_and_randomness() -> None:
    def run() -> list[UUID]:
        generator = Uuid7Generator(ManualClock(START), random_bytes=lambda n: bytes(range(n)))
        return [generator.new() for _ in range(5)]

    assert run() == run()


@given(st.integers(min_value=1, max_value=5000))
def test_ids_are_unique_and_ordered_for_any_burst_size(count: int) -> None:
    generator = Uuid7Generator(ManualClock(START))
    values = [generator.new() for _ in range(count)]
    assert all(a < b for a, b in pairwise(values))


@given(
    st.datetimes(
        min_value=datetime(2000, 1, 1),  # noqa: DTZ001 - Hypothesis requires naive bounds
        max_value=datetime(2100, 1, 1),  # noqa: DTZ001
        timezones=st.just(UTC),
    )
)
def test_timestamp_round_trips_to_the_millisecond(moment: datetime) -> None:
    generated = Uuid7Generator(ManualClock(moment)).new()
    assert uuid7_timestamp_ms(generated) == int(moment.timestamp() * 1000)


def test_sequential_ids_are_deterministic_uuid7_shaped_and_ordered() -> None:
    ids = SequentialIds()
    first, second = ids.new(), ids.new()
    assert first < second
    assert first.version == 7
    assert SequentialIds().new() == first


def test_timestamp_helper_rejects_other_uuid_versions() -> None:
    with pytest.raises(ValueError, match="UUIDv7"):
        uuid7_timestamp_ms(UUID("7d444840-9dc0-11d1-b245-5ffdce74fad2"))

import uuid

import pytest
from hypothesis import given
from hypothesis import strategies as st

from shaidago.shared.idempotency import (
    SealError,
    fingerprint,
    key_hash,
    seal,
    unseal,
    validate_idempotency_key,
)
from shaidago.shared.problems import (
    IDEMPOTENCY_KEY_INVALID,
    IDEMPOTENCY_KEY_REQUIRED,
    ProblemError,
)

PEPPER = b"p" * 32
KEY = "3f2b8c1e-9d4a-4b6e-8a1c-2d5e7f9a0b3c"
OPERATION = "reports.submit"


def problem_of(raw: str | None) -> object:
    with pytest.raises(ProblemError) as raised:
        validate_idempotency_key(raw)
    return raised.value.problem


def test_a_random_uuid4_is_accepted() -> None:
    assert validate_idempotency_key(KEY) == KEY
    assert validate_idempotency_key(str(uuid.uuid4())) is not None


def test_missing_and_blank_keys_are_required() -> None:
    assert problem_of(None) is IDEMPOTENCY_KEY_REQUIRED
    assert problem_of("") is IDEMPOTENCY_KEY_REQUIRED


@pytest.mark.parametrize(
    "raw",
    [
        " " + KEY,
        KEY.upper(),
        KEY + "0",
        KEY.replace("-", ""),
        str(uuid.UUID(int=1, version=1)),
        "018f0000-0000-7000-8000-00000000abcd",  # a UUIDv7 is not a random client key
        "../etc/passwd",
        "a" * 500,
        "3f2b8c1e-9d4a-4b6e-8a1c-2d5e7f9a0b3c\n",
    ],
)
def test_other_shapes_are_invalid(raw: str) -> None:
    assert problem_of(raw) is IDEMPOTENCY_KEY_INVALID


def test_key_hash_is_keyed_stable_and_hides_the_key() -> None:
    digest = key_hash(PEPPER, KEY)
    assert digest == key_hash(PEPPER, KEY)
    assert digest != key_hash(b"q" * 32, KEY)
    assert digest != key_hash(PEPPER, KEY[:-1] + "d")
    assert KEY.encode() not in digest
    assert len(digest) == 32


def test_fingerprint_separates_parts_and_is_deterministic() -> None:
    assert fingerprint("ab", "c") != fingerprint("a", "bc")
    assert fingerprint("a", b"b") == fingerprint("a", "b")
    assert fingerprint("x") != fingerprint("x", "")


@given(st.lists(st.binary(max_size=30), max_size=5), st.lists(st.binary(max_size=30), max_size=5))
def test_different_part_lists_never_collide(a: list[bytes], b: list[bytes]) -> None:
    assert (fingerprint(*a) == fingerprint(*b)) == (a == b)


@given(st.binary(max_size=2000))
def test_seal_round_trips_and_is_randomised(payload: bytes) -> None:
    sealed = seal(KEY, payload, context=OPERATION)
    assert unseal(KEY, sealed, context=OPERATION) == payload
    assert sealed != seal(KEY, payload, context=OPERATION)


def test_seal_hides_the_payload_and_rejects_the_wrong_key_context_or_tampering() -> None:
    payload = b"SG-7GQ2K-9M4XV-C8HTB-3WNZD-R"
    sealed = seal(KEY, payload, context=OPERATION)
    assert payload not in sealed
    other_key = "3f2b8c1e-9d4a-4b6e-8a1c-2d5e7f9a0b3d"
    with pytest.raises(SealError):
        unseal(other_key, sealed, context=OPERATION)
    with pytest.raises(SealError):
        unseal(KEY, sealed, context="reports.other")
    for index in range(len(sealed)):
        flipped = sealed[:index] + bytes([sealed[index] ^ 1]) + sealed[index + 1 :]
        with pytest.raises(SealError):
            unseal(KEY, flipped, context=OPERATION)
    for bad in (b"", b"\x01", sealed[:20], b"\x02" + sealed[1:]):
        with pytest.raises(SealError):
            unseal(KEY, bad, context=OPERATION)

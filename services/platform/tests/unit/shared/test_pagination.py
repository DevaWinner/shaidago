import base64
import contextlib
import hashlib
import hmac
import json
from uuid import UUID, uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy import Column, Integer, MetaData, Table, Uuid
from sqlalchemy.dialects import postgresql

from shaidago.shared.pagination import (
    MAX_PAGE_SIZE,
    CursorPosition,
    build_page,
    clamp_page_size,
    decode_cursor,
    encode_cursor,
    keyset_after,
    scope_of,
)
from shaidago.shared.problems import INVALID_CURSOR, ProblemError

KEY = b"k" * 32
OTHER_KEY = b"o" * 32
SCOPE = scope_of("/v1/projects", locality="amac", category=None)
POSITION = CursorPosition("2026-09-19T12:00:00+00:00", UUID("018f0000-0000-7000-8000-00000000abcd"))


def rejected(token: str, *, key: bytes = KEY, scope: str = SCOPE) -> None:
    with pytest.raises(ProblemError) as raised:
        decode_cursor(key, scope, token)
    assert raised.value.problem is INVALID_CURSOR


def test_cursor_round_trips() -> None:
    assert decode_cursor(KEY, SCOPE, encode_cursor(KEY, SCOPE, POSITION)) == POSITION


@given(
    st.one_of(st.text(max_size=40), st.integers(min_value=-(2**53), max_value=2**53)),
    st.uuids(),
)
def test_any_position_round_trips(sort_value: str | int, row_id: UUID) -> None:
    position = CursorPosition(sort_value, row_id)
    assert decode_cursor(KEY, SCOPE, encode_cursor(KEY, SCOPE, position)) == position


def test_cursor_is_opaque_url_safe_text_that_hides_the_raw_id() -> None:
    token = encode_cursor(KEY, SCOPE, POSITION)
    assert token.isascii()
    assert all(c.isalnum() or c in "-_" for c in token)
    assert str(POSITION.row_id) not in token


def test_tampered_cursors_are_rejected() -> None:
    token = encode_cursor(KEY, SCOPE, POSITION)
    for index in range(0, len(token), 7):
        flipped = token[:index] + ("A" if token[index] != "A" else "B") + token[index + 1 :]
        rejected(flipped)
    rejected(token[:-4])
    rejected(token + "AAAA")


def test_cursor_signed_with_another_key_or_scope_is_rejected() -> None:
    rejected(encode_cursor(OTHER_KEY, SCOPE, POSITION))
    rejected(
        encode_cursor(KEY, scope_of("/v1/projects", locality="bwari", category=None), POSITION)
    )
    rejected(encode_cursor(KEY, SCOPE, POSITION), scope=scope_of("/v1/reports"))


@pytest.mark.parametrize(
    "token", ["", " ", "not base64!!", "a" * 600, "é", "AAAA", "e30", "bnVsbA", "W10"]
)
def test_malformed_cursors_are_rejected_with_one_generic_problem(token: str) -> None:
    rejected(token)


@given(st.text(max_size=200))
def test_arbitrary_text_never_crashes_decoding(token: str) -> None:
    with contextlib.suppress(ProblemError):  # rejection is the only acceptable failure mode
        decode_cursor(KEY, SCOPE, token)


def test_unknown_cursor_version_is_rejected() -> None:
    payload = json.dumps({"v": 2, "s": SCOPE, "k": 1, "i": str(uuid4())}).encode()
    signature = hmac.new(KEY, payload, hashlib.sha256).digest()
    rejected(base64.urlsafe_b64encode(payload + signature).rstrip(b"=").decode())


def test_scope_depends_on_endpoint_and_every_filter() -> None:
    assert scope_of("/a", x=1) == scope_of("/a", x=1)
    assert scope_of("/a", x=1) != scope_of("/a", x=2)
    assert scope_of("/a", x=1) != scope_of("/b", x=1)
    assert scope_of("/a", x=1, y=2) == scope_of("/a", y=2, x=1)


@given(st.one_of(st.none(), st.integers(min_value=-(10**6), max_value=10**6)))
def test_page_size_is_always_within_bounds(requested: int | None) -> None:
    assert 1 <= clamp_page_size(requested) <= MAX_PAGE_SIZE


def test_page_size_defaults_and_caps() -> None:
    assert clamp_page_size(None) == 20
    assert clamp_page_size(0) == 1
    assert clamp_page_size(10_000) == MAX_PAGE_SIZE


def test_build_page_uses_the_extra_row_only_as_a_more_pages_signal() -> None:
    rows = [(i, UUID(int=i)) for i in range(1, 6)]

    def position(row: tuple[int, UUID]) -> CursorPosition:
        return CursorPosition(row[0], row[1])

    page = build_page(rows, 4, position_of=position, key=KEY, scope=SCOPE)
    assert page.items == rows[:4]
    assert page.next_cursor is not None
    assert decode_cursor(KEY, SCOPE, page.next_cursor) == CursorPosition(4, UUID(int=4))
    last = build_page(rows[:4], 4, position_of=position, key=KEY, scope=SCOPE)
    assert last.next_cursor is None
    empty = build_page([], 4, position_of=position, key=KEY, scope=SCOPE)
    assert (empty.items, empty.next_cursor) == ([], None)


def test_keyset_clause_compares_the_sort_and_id_pair_in_the_stated_direction() -> None:
    sort_column: Column[int] = Column("n", Integer)
    id_column: Column[UUID] = Column("id", Uuid)
    Table("t", MetaData(), sort_column, id_column)
    row_id = UUID(int=9)
    ascending = keyset_after(sort_column, id_column, 5, row_id, descending=False)
    descending = keyset_after(sort_column, id_column, 5, row_id, descending=True)
    dialect = postgresql.dialect()
    assert "(t.n, t.id) > (%(param_1)s, %(param_2)s::UUID)" in str(
        ascending.compile(dialect=dialect)
    )
    assert "(t.n, t.id) < (" in str(descending.compile(dialect=dialect))

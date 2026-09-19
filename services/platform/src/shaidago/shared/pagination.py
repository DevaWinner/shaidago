"""Cursor pagination: bounded page sizes, stable keyset ordering, and signed opaque cursors.

A cursor carries the position of the last returned row (sort value plus ID tie-breaker), a format
version, and a *scope* that binds it to one endpoint and filter set. It is signed with HMAC-SHA-256,
so a tampered, truncated, replayed-across-filters, or foreign cursor is rejected with one generic
problem and never reaches a query.
"""

import base64
import binascii
import hashlib
import hmac
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Final
from uuid import UUID

from sqlalchemy import ColumnElement, literal, tuple_

from shaidago.shared.problems import INVALID_CURSOR, ProblemError

CURSOR_VERSION: Final = 1
DEFAULT_PAGE_SIZE: Final = 20
MAX_PAGE_SIZE: Final = 50
_SIGNATURE_BYTES: Final = 32
MAX_CURSOR_CHARS: Final = 512


@dataclass(frozen=True)
class CursorPosition:
    """The last row returned: its sort value (ISO text or integer) and its ID."""

    sort_value: str | int
    row_id: UUID


@dataclass(frozen=True)
class Page[T]:
    items: list[T]
    next_cursor: str | None


def clamp_page_size(
    requested: int | None, *, default: int = DEFAULT_PAGE_SIZE, maximum: int = MAX_PAGE_SIZE
) -> int:
    """Never below 1, never above ``maximum``; ``None`` means the default."""
    if requested is None:
        return min(default, maximum)
    return max(1, min(requested, maximum))


def scope_of(endpoint: str, **filters: str | int | None) -> str:
    """A stable digest of the endpoint and its filter values, for binding a cursor to them."""
    canonical = json.dumps([endpoint, sorted(filters.items())], separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:32]


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(key: bytes, body: bytes) -> bytes:
    return hmac.new(key, body, hashlib.sha256).digest()


def encode_cursor(key: bytes, scope: str, position: CursorPosition) -> str:
    payload = json.dumps(
        {"v": CURSOR_VERSION, "s": scope, "k": position.sort_value, "i": str(position.row_id)},
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return _b64(payload + _sign(key, payload))


def decode_cursor(key: bytes, scope: str, token: str) -> CursorPosition:
    """Return the position or raise ``ProblemError(INVALID_CURSOR)``; the cause is never exposed."""
    try:
        return _decode(key, scope, token)
    except ValueError, KeyError, TypeError, binascii.Error:
        raise ProblemError(INVALID_CURSOR) from None


def _decode(key: bytes, scope: str, token: str) -> CursorPosition:
    if not token or len(token) > MAX_CURSOR_CHARS or not token.isascii():
        raise ValueError("malformed")
    raw = _unb64(token)
    if len(raw) <= _SIGNATURE_BYTES:
        raise ValueError("malformed")
    payload, signature = raw[:-_SIGNATURE_BYTES], raw[-_SIGNATURE_BYTES:]
    if not hmac.compare_digest(signature, _sign(key, payload)):
        raise ValueError("bad signature")
    body: dict[str, Any] = json.loads(payload)
    if body["v"] != CURSOR_VERSION or not hmac.compare_digest(str(body["s"]), scope):
        raise ValueError("wrong version or scope")
    sort_value = body["k"]
    if isinstance(sort_value, bool) or not isinstance(sort_value, (str, int)):
        raise TypeError("bad sort value")
    return CursorPosition(sort_value=sort_value, row_id=UUID(str(body["i"])))


def keyset_after(
    sort_column: ColumnElement[Any],
    id_column: ColumnElement[Any],
    sort_value: Any,
    row_id: UUID,
    *,
    descending: bool,
) -> ColumnElement[bool]:
    """Rows strictly after ``(sort_value, row_id)`` in ``(sort_column, id_column)`` order.

    The ID tie-breaker makes the order total, so no row is skipped or repeated across pages.
    Callers convert ``CursorPosition.sort_value`` to the column's type (for example
    ``datetime.fromisoformat``) and must also ``ORDER BY`` the same two columns and direction.
    """
    pair = tuple_(sort_column, id_column)
    after = tuple_(
        literal(sort_value, type_=sort_column.type), literal(row_id, type_=id_column.type)
    )
    return pair < after if descending else pair > after


def build_page[T](
    rows: Sequence[T],
    limit: int,
    *,
    position_of: Callable[[T], CursorPosition],
    key: bytes,
    scope: str,
) -> Page[T]:
    """Turn ``limit + 1`` fetched rows into a page; the extra row only signals that more exist."""
    items = list(rows[:limit])
    has_more = len(rows) > limit
    next_cursor = encode_cursor(key, scope, position_of(items[-1])) if has_more and items else None
    return Page(items=items, next_cursor=next_cursor)

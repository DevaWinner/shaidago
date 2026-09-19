"""Opaque reviewer sessions.

* The token is 256 bits from ``secrets``, generated only here, so a client cannot fix one.
* The database stores ``HMAC-SHA-256(session_key, token)``; the raw token exists only in the
  one response that issues it and in the cookie the BFF sets.
* The CSRF token is ``HMAC-SHA-256(session_key, "csrf" + token)``: bound to this session, needs no
  storage, and changes whenever the session token does.
* A session is valid only while it is unrevoked, inside its idle and absolute limits, and the
  reviewer is active with the same credential version and role it was issued for. Every failure
  looks the same to the caller.
"""

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Final, Literal
from uuid import UUID

from sqlalchemy import LargeBinary, Row, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.auth.reviewers import ReviewerRecord, Role
from shaidago.shared.clock import Clock
from shaidago.shared.ids import IdGenerator

TOKEN_BYTES: Final = 32
TOUCH_INTERVAL: Final = timedelta(seconds=60)
MAX_TOKEN_CHARS: Final = 128
RevocationReason = Literal[
    "logout", "disabled", "credential_change", "role_change", "admin_revoked", "expired"
]


def token_hmac(key: bytes, token: str) -> bytes:
    return hmac.new(key, b"sg-session-v1:" + token.encode(), hashlib.sha256).digest()


def csrf_token_for(key: bytes, token: str) -> str:
    digest = hmac.new(key, b"sg-csrf-v1:" + token.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def csrf_matches(key: bytes, token: str, presented: str) -> bool:
    """Constant-time comparison on bytes, so hostile non-ASCII input is a mismatch, not an error."""
    expected = csrf_token_for(key, token).encode("ascii")
    return hmac.compare_digest(expected, presented.encode("utf-8", errors="replace"))


@dataclass(frozen=True)
class SessionLifetimes:
    idle: timedelta
    absolute: timedelta


@dataclass(frozen=True)
class IssuedSession:
    """Returned once to the trusted BFF; ``token`` is never stored or logged."""

    token: str
    csrf_token: str
    session_id: UUID
    absolute_expires_at: datetime
    idle_timeout: timedelta

    def __repr__(self) -> str:
        return f"IssuedSession(session_id={self.session_id})"


@dataclass(frozen=True)
class Principal:
    reviewer_id: UUID
    identifier: str
    role: Role
    session_id: UUID


_INSERT = text(
    "INSERT INTO app.reviewer_sessions (id, token_hmac, reviewer_id, role_snapshot, "
    "credential_version, created_at, last_used_at, absolute_expires_at) "
    "VALUES (:id, :hmac, :reviewer, :role, :version, :now, :now, :expires)"
).bindparams(bindparam("hmac", type_=LargeBinary))
_LOOKUP = text(
    "SELECT s.id, s.reviewer_id, s.role_snapshot, s.credential_version AS session_version, "
    "s.last_used_at, s.absolute_expires_at, s.revoked_at, r.identifier, r.role, r.state, "
    "r.credential_version AS reviewer_version "
    "FROM app.reviewer_sessions s JOIN app.reviewers r ON r.id = s.reviewer_id "
    "WHERE s.token_hmac = :hmac"
).bindparams(bindparam("hmac", type_=LargeBinary))
_TOUCH = text("UPDATE app.reviewer_sessions SET last_used_at = :now WHERE id = :id")
_REVOKE_ONE = text(
    "UPDATE app.reviewer_sessions SET revoked_at = :now, revocation_reason = :reason "
    "WHERE id = :id AND revoked_at IS NULL"
)
_REVOKE_TOKEN = text(
    "UPDATE app.reviewer_sessions SET revoked_at = :now, revocation_reason = :reason "
    "WHERE token_hmac = :hmac AND revoked_at IS NULL"
).bindparams(bindparam("hmac", type_=LargeBinary))
_REVOKE_ALL = text(
    "UPDATE app.reviewer_sessions SET revoked_at = :now, revocation_reason = :reason "
    "WHERE reviewer_id = :reviewer AND revoked_at IS NULL"
)


class SessionService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        key: bytes,
        clock: Clock,
        ids: IdGenerator,
        lifetimes: SessionLifetimes,
    ) -> None:
        self._session = session
        self._key = key
        self._clock = clock
        self._ids = ids
        self._idle = lifetimes.idle
        self._absolute = lifetimes.absolute

    async def issue(self, reviewer: ReviewerRecord) -> IssuedSession:
        token = secrets.token_urlsafe(TOKEN_BYTES)
        now = self._clock.now()
        expires = now + self._absolute
        session_id = self._ids.new()
        await self._session.execute(
            _INSERT,
            {
                "id": session_id,
                "hmac": token_hmac(self._key, token),
                "reviewer": reviewer.id,
                "role": reviewer.role,
                "version": reviewer.credential_version,
                "now": now,
                "expires": expires,
            },
        )
        return IssuedSession(
            token=token,
            csrf_token=csrf_token_for(self._key, token),
            session_id=session_id,
            absolute_expires_at=expires,
            idle_timeout=self._idle,
        )

    def _is_valid(self, row: Row[Any], now: datetime) -> bool:
        return (
            row.revoked_at is None
            and now < row.absolute_expires_at
            and now < row.last_used_at + self._idle
            and row.state == "active"
            and row.reviewer_version == row.session_version
            and row.role == row.role_snapshot  # a privilege change requires a fresh sign-in
        )

    async def resolve(self, token: str | None) -> Principal | None:
        """The reviewer for a valid session, else ``None`` (the reason is never revealed)."""
        if not token or len(token) > MAX_TOKEN_CHARS:
            return None
        row = (
            await self._session.execute(_LOOKUP, {"hmac": token_hmac(self._key, token)})
        ).one_or_none()
        now = self._clock.now()
        if row is None or not self._is_valid(row, now):
            return None
        if now - row.last_used_at >= TOUCH_INTERVAL:
            await self._session.execute(_TOUCH, {"now": now, "id": row.id})
        return Principal(row.reviewer_id, row.identifier, row.role, row.id)

    async def revoke_token(self, token: str, reason: RevocationReason = "logout") -> None:
        await self._session.execute(
            _REVOKE_TOKEN,
            {"now": self._clock.now(), "reason": reason, "hmac": token_hmac(self._key, token)},
        )

    async def revoke_all(self, reviewer_id: UUID, reason: RevocationReason) -> None:
        await self._session.execute(
            _REVOKE_ALL, {"now": self._clock.now(), "reason": reason, "reviewer": reviewer_id}
        )

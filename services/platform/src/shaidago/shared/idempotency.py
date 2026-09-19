"""Idempotency for retried create operations (ADR-0005).

* The client sends a random UUIDv4 ``Idempotency-Key``. It is validated here and never stored:
  the database keeps only ``HMAC-SHA-256(pepper, key)`` and a request fingerprint.
* The first result is sealed with AES-256-GCM under a key derived (HKDF-SHA-256) from the raw
  key, so a database leak reveals nothing in it, yet a retry by the key's holder gets the same
  result within the replay window. After the window the sealed bytes are scrubbed and a retry
  gets a generic "already received" problem.
* Claiming, completing, and lookup run through ``SECURITY DEFINER`` functions, so even the
  insert-only public role needs no privilege on the table. Concurrent duplicates serialise on
  the unique index: the second claim waits for the first transaction, then sees its result.
"""

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Final

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import LargeBinary, Uuid, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.shared.clock import Clock
from shaidago.shared.ids import IdGenerator
from shaidago.shared.problems import (
    ALREADY_RECEIVED,
    IDEMPOTENCY_CONFLICT,
    IDEMPOTENCY_KEY_INVALID,
    IDEMPOTENCY_KEY_REQUIRED,
    ProblemError,
)

SEALED_WINDOW: Final = timedelta(minutes=15)
RETENTION: Final = timedelta(hours=24)
_SEAL_FORMAT: Final = b"\x01"
_NONCE_BYTES: Final = 12
_KEY_PATTERN: Final = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class SealError(Exception):
    """A sealed value could not be opened (wrong key, wrong context, or tampering)."""


def validate_idempotency_key(raw: str | None) -> str:
    if raw is None or raw == "":
        raise ProblemError(IDEMPOTENCY_KEY_REQUIRED)
    if _KEY_PATTERN.fullmatch(raw) is None:
        raise ProblemError(IDEMPOTENCY_KEY_INVALID)
    return raw


def key_hash(pepper: bytes, key: str) -> bytes:
    return hmac.new(pepper, b"sg-idem-v1:" + key.encode(), hashlib.sha256).digest()


def fingerprint(*parts: str | bytes) -> bytes:
    """Digest of the request's identity. Parts are length-prefixed so ("ab", "c") != ("a", "bc")."""
    digest = hashlib.sha256()
    for part in parts:
        data = part.encode() if isinstance(part, str) else part
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.digest()


def _seal_key(key: str, context: str) -> bytes:
    return HKDF(
        algorithm=SHA256(), length=32, salt=None, info=b"sg-idem-seal-v1:" + context.encode()
    ).derive(key.encode())


def seal(key: str, payload: bytes, *, context: str) -> bytes:
    nonce = secrets.token_bytes(_NONCE_BYTES)
    ciphertext = AESGCM(_seal_key(key, context)).encrypt(nonce, payload, context.encode())
    return _SEAL_FORMAT + nonce + ciphertext


def unseal(key: str, sealed: bytes, *, context: str) -> bytes:
    if not sealed.startswith(_SEAL_FORMAT) or len(sealed) < 1 + _NONCE_BYTES + 16:
        raise SealError
    nonce = sealed[1 : 1 + _NONCE_BYTES]
    try:
        return AESGCM(_seal_key(key, context)).decrypt(
            nonce, sealed[1 + _NONCE_BYTES :], context.encode()
        )
    except InvalidTag:
        raise SealError from None


@dataclass(frozen=True)
class Claimed:
    """First time this key is seen: do the work, then call ``complete``."""


@dataclass(frozen=True)
class Replay:
    """A completed earlier result, opened with the caller's key."""

    status: int
    payload: bytes


_CLAIM = text(
    "SELECT outcome, response_status, sealed_response FROM app.idempotency_claim("
    ":operation, :key_hash, :fingerprint, :id, :now, :sealed_until, :expires_at)"
).bindparams(
    bindparam("key_hash", type_=LargeBinary),
    bindparam("fingerprint", type_=LargeBinary),
    bindparam("id", type_=Uuid),
)
_COMPLETE = text(
    "SELECT app.idempotency_complete(:operation, :key_hash, :status, :sealed)"
).bindparams(bindparam("key_hash", type_=LargeBinary), bindparam("sealed", type_=LargeBinary))
_PURGE = text("SELECT app.idempotency_purge(:now, :batch)")


class IdempotencyStore:
    """Use inside the same unit of work as the operation being made idempotent."""

    def __init__(
        self, session: AsyncSession, *, pepper: bytes, clock: Clock, ids: IdGenerator
    ) -> None:
        self._session = session
        self._pepper = pepper
        self._clock = clock
        self._ids = ids

    async def begin(self, operation: str, key: str, request_fingerprint: bytes) -> Claimed | Replay:
        """Claim the key, or return the earlier result, or raise the conflict problem."""
        now = self._clock.now()
        row = (
            await self._session.execute(
                _CLAIM,
                {
                    "operation": operation,
                    "key_hash": key_hash(self._pepper, key),
                    "fingerprint": request_fingerprint,
                    "id": self._ids.new(),
                    "now": now,
                    "sealed_until": now + SEALED_WINDOW,
                    "expires_at": now + RETENTION,
                },
            )
        ).one()
        outcome: str = row.outcome
        if outcome == "claimed":
            return Claimed()
        if outcome == "replay":
            try:
                payload = unseal(key, bytes(row.sealed_response), context=operation)
            except SealError:
                # Same hash but not our key: cannot happen for a real holder of the key.
                raise ProblemError(IDEMPOTENCY_CONFLICT) from None
            return Replay(status=int(row.response_status), payload=payload)
        if outcome == "already_received":
            raise ProblemError(ALREADY_RECEIVED)
        raise ProblemError(IDEMPOTENCY_CONFLICT)  # different request, or still in progress

    async def complete(self, operation: str, key: str, *, status: int, payload: bytes) -> None:
        await self._session.execute(
            _COMPLETE,
            {
                "operation": operation,
                "key_hash": key_hash(self._pepper, key),
                "status": status,
                "sealed": seal(key, payload, context=operation),
            },
        )


async def purge_expired(session: AsyncSession, clock: Clock, *, batch: int = 500) -> int:
    """Worker maintenance: scrub sealed results past the window and delete expired records."""
    return int((await session.execute(_PURGE, {"now": clock.now(), "batch": batch})).scalar_one())


__all__ = [
    "RETENTION",
    "SEALED_WINDOW",
    "Claimed",
    "IdempotencyStore",
    "Replay",
    "SealError",
    "fingerprint",
    "key_hash",
    "purge_expired",
    "seal",
    "unseal",
    "validate_idempotency_key",
]

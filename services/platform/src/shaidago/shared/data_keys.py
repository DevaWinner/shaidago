"""Creating, loading, destroying, and rewrapping data-encryption keys.

The insert path is written for the restricted public role: application-generated IDs and
timestamps and no ``RETURNING``, because that role may insert into ``app.data_keys`` but not read
it (ADR-0003). Loading needs a role that can read the table.
"""

import secrets
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import ARRAY, LargeBinary, Row, Uuid, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.audit.events import AuditWriter
from shaidago.shared.clock import Clock
from shaidago.shared.crypto import (
    KEY_BYTES,
    PURPOSES,
    DataKey,
    DecryptionError,
    KekWrapper,
    KeyUnavailableError,
)
from shaidago.shared.ids import IdGenerator

_logger = structlog.get_logger("shaidago.crypto")

_INSERT = text(
    "INSERT INTO app.data_keys (id, purpose, owner_table, owner_id, wrapped_key, kek_version, "
    "created_at) VALUES (:id, :purpose, :owner_table, :owner_id, :wrapped, :version, :now)"
).bindparams(bindparam("wrapped", type_=LargeBinary))
_LOAD = text(
    "SELECT id, purpose, owner_table, owner_id, wrapped_key, kek_version "
    "FROM app.data_keys WHERE id = :id"
)
_LOAD_MANY = text(
    "SELECT id, purpose, owner_table, owner_id, wrapped_key, kek_version "
    "FROM app.data_keys WHERE id = ANY(:ids)"
).bindparams(bindparam("ids", type_=ARRAY(Uuid())))
_BY_OWNER = text(
    "SELECT id FROM app.data_keys WHERE owner_table = :owner_table AND owner_id = :owner_id "
    "AND purpose = :purpose"
)
_DESTROY = text(
    "UPDATE app.data_keys SET wrapped_key = NULL, kek_version = NULL, destroyed_at = :now "
    "WHERE owner_table = :owner_table AND owner_id = :owner_id AND purpose = :purpose "
    "AND destroyed_at IS NULL"
)
_STALE = text(
    "SELECT id, purpose, owner_table, owner_id, wrapped_key, kek_version FROM app.data_keys "
    "WHERE destroyed_at IS NULL AND kek_version <> :active ORDER BY id LIMIT :limit "
    "FOR UPDATE SKIP LOCKED"
)
_REWRAP = text(
    "UPDATE app.data_keys SET wrapped_key = :wrapped, kek_version = :version WHERE id = :id"
).bindparams(bindparam("wrapped", type_=LargeBinary))
_REMAINING = text(
    "SELECT count(*) FROM app.data_keys WHERE destroyed_at IS NULL AND kek_version <> :active"
)


class DataKeyDestroyedError(Exception):
    """The key was crypto-shredded; its data is permanently unreadable."""


def dek_context(key_id: UUID, purpose: str, owner_table: str, owner_id: UUID) -> bytes:
    return f"dek:{key_id}:{purpose}:{owner_table}:{owner_id}".encode()


@dataclass(frozen=True)
class RotationResult:
    rewrapped: int
    unavailable: int
    remaining: int


class DataKeyService:
    def __init__(
        self, session: AsyncSession, wrapper: KekWrapper, clock: Clock, ids: IdGenerator
    ) -> None:
        self._session = session
        self._wrapper = wrapper
        self._clock = clock
        self._ids = ids

    async def create(self, owner_table: str, owner_id: UUID, purpose: str) -> DataKey:
        if purpose not in PURPOSES:
            raise ValueError("unknown key purpose")
        key_id = self._ids.new()
        dek = secrets.token_bytes(KEY_BYTES)
        version, wrapped = self._wrapper.wrap(
            dek, dek_context(key_id, purpose, owner_table, owner_id)
        )
        await self._session.execute(
            _INSERT,
            {
                "id": key_id,
                "purpose": purpose,
                "owner_table": owner_table,
                "owner_id": owner_id,
                "wrapped": wrapped,
                "version": version,
                "now": self._clock.now(),
            },
        )
        return DataKey(key_id, dek)

    async def load(self, key_id: UUID) -> DataKey:
        row = (await self._session.execute(_LOAD, {"id": key_id})).one_or_none()
        if row is None:
            raise DecryptionError
        if row.wrapped_key is None:
            raise DataKeyDestroyedError
        return self._unwrap(row)

    async def load_many(self, key_ids: Sequence[UUID]) -> dict[UUID, DataKey]:
        """Load several keys in one query. A missing or destroyed key is simply absent."""
        wanted = list(dict.fromkeys(key_ids))
        if not wanted:
            return {}
        rows = (await self._session.execute(_LOAD_MANY, {"ids": wanted})).all()
        return {row.id: self._unwrap(row) for row in rows if row.wrapped_key is not None}

    async def find(self, owner_table: str, owner_id: UUID, purpose: str) -> UUID | None:
        row = (
            await self._session.execute(
                _BY_OWNER, {"owner_table": owner_table, "owner_id": owner_id, "purpose": purpose}
            )
        ).one_or_none()
        return None if row is None else row.id

    async def destroy(self, owner_table: str, owner_id: UUID, purpose: str) -> bool:
        """Crypto-shred one class of one record. Returns whether a live key was destroyed."""
        result = await self._session.execute(
            _DESTROY,
            {
                "now": self._clock.now(),
                "owner_table": owner_table,
                "owner_id": owner_id,
                "purpose": purpose,
            },
        )
        return bool(getattr(result, "rowcount", 0))

    async def rotate(self, *, limit: int = 100) -> RotationResult:
        """Rewrap up to ``limit`` DEKs under the active KEK.

        Resumable and idempotent: it only touches keys still on an older version, so an
        interrupted run simply continues, and a finished run does nothing. Keys whose KEK
        version is no longer configured are counted, never guessed at. Field ciphertext is
        untouched, and no plaintext key is logged.
        """
        active = self._wrapper.active_version
        rows = (await self._session.execute(_STALE, {"active": active, "limit": limit})).all()
        rewrapped = unavailable = 0
        for row in rows:
            try:
                dek = self._wrapper.unwrap(
                    row.kek_version,
                    bytes(row.wrapped_key),
                    dek_context(row.id, row.purpose, row.owner_table, row.owner_id),
                )
            except KeyUnavailableError:
                unavailable += 1
                continue
            version, wrapped = self._wrapper.wrap(
                dek, dek_context(row.id, row.purpose, row.owner_table, row.owner_id)
            )
            await self._session.execute(
                _REWRAP, {"wrapped": wrapped, "version": version, "id": row.id}
            )
            rewrapped += 1
        remaining = (await self._session.execute(_REMAINING, {"active": active})).scalar_one()
        _logger.info(
            "kek rotation batch", rewrapped=rewrapped, unavailable=unavailable, remaining=remaining
        )
        return RotationResult(rewrapped, unavailable, int(remaining))

    async def rotate_and_audit(self, *, limit: int = 100) -> RotationResult:
        result = await self.rotate(limit=limit)
        await AuditWriter(self._session, self._clock, self._ids).record(
            "kek_rotation_batch",
            actor_type="system",
            details={
                "rewrapped": result.rewrapped,
                "unavailable": result.unavailable,
                "remaining": result.remaining,
                "active_version": self._wrapper.active_version,
            },
        )
        return result

    def _unwrap(self, row: Row[Any]) -> DataKey:
        dek = self._wrapper.unwrap(
            row.kek_version,
            bytes(row.wrapped_key),
            dek_context(row.id, row.purpose, row.owner_table, row.owner_id),
        )
        return DataKey(row.id, dek)

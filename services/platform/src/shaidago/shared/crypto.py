"""Envelope encryption for private fields (ADR-0004).

Two levels: a per-record, per-purpose random data-encryption key (DEK) encrypts fields with
AES-256-GCM; the DEK is wrapped by a versioned key-encryption key (KEK) supplied by the
environment. Every ciphertext is bound to ``table:row_id:field:schema_version``, so moving it to
another row, field, or table fails authentication. Decrypt failures raise ``DecryptionError``,
which carries no plaintext, key, or context, and are never distinguishable to a public caller.

Production key custody moves to a managed KMS by replacing ``EnvironmentKekWrapper`` with an
adapter that implements the same ``KekWrapper`` protocol; ciphertext and wrapped keys need no
rewrite because the wrap/unwrap boundary is the only thing that changes (ADR-0004, decision 8).
"""

import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Final, Protocol
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

FORMAT_VERSION: Final = b"\x01"
NONCE_BYTES: Final = 12
TAG_BYTES: Final = 16
KEY_BYTES: Final = 32
MIN_ENVELOPE_BYTES: Final = 1 + NONCE_BYTES + TAG_BYTES
PURPOSES: Final = ("report_content", "contact", "review_notes", "follow_up_answers")


class DecryptionError(Exception):
    """A value could not be decrypted. Deliberately carries no detail."""

    def __init__(self) -> None:
        super().__init__("decryption failed")


class KeyUnavailableError(Exception):
    """The KEK version that wrapped a key is not configured on this instance."""


@dataclass(frozen=True)
class DataKey:
    """A record's DEK. The key bytes never appear in ``repr``."""

    id: UUID
    key: bytes = field(repr=False)

    def __repr__(self) -> str:
        return f"DataKey(id={self.id})"


def field_context(table: str, row_id: UUID, field_name: str, schema_version: int) -> bytes:
    """The associated data binding a ciphertext to its exact place."""
    return f"{table}:{row_id}:{field_name}:{schema_version}".encode()


class FieldCipher:
    def __init__(self, random_bytes: Callable[[int], bytes] = secrets.token_bytes) -> None:
        self._random_bytes = random_bytes

    def encrypt(self, data_key: DataKey, plaintext: bytes, context: bytes) -> bytes:
        nonce = self._random_bytes(NONCE_BYTES)
        return FORMAT_VERSION + nonce + AESGCM(data_key.key).encrypt(nonce, plaintext, context)

    def decrypt(self, data_key: DataKey, envelope: bytes, context: bytes) -> bytes:
        if len(envelope) < MIN_ENVELOPE_BYTES or envelope[:1] != FORMAT_VERSION:
            raise DecryptionError
        nonce = envelope[1 : 1 + NONCE_BYTES]
        try:
            return AESGCM(data_key.key).decrypt(nonce, envelope[1 + NONCE_BYTES :], context)
        except InvalidTag:
            raise DecryptionError from None


class KekWrapper(Protocol):
    """Wraps and unwraps DEKs. A KMS adapter replaces the environment implementation."""

    @property
    def active_version(self) -> str: ...

    def wrap(self, dek: bytes, context: bytes) -> tuple[str, bytes]:
        """Returns ``(kek_version, wrapped_key)`` under the active KEK."""
        ...

    def unwrap(self, kek_version: str, wrapped: bytes, context: bytes) -> bytes: ...


class EnvironmentKekWrapper:
    def __init__(self, keys: Mapping[str, bytes], active_version: str) -> None:
        if active_version not in keys:
            raise ValueError("the active KEK version must be in the key ring")
        self._keys = dict(keys)
        self._active = active_version

    @property
    def active_version(self) -> str:
        return self._active

    def wrap(self, dek: bytes, context: bytes) -> tuple[str, bytes]:
        nonce = secrets.token_bytes(NONCE_BYTES)
        wrapped = (
            FORMAT_VERSION + nonce + AESGCM(self._keys[self._active]).encrypt(nonce, dek, context)
        )
        return self._active, wrapped

    def unwrap(self, kek_version: str, wrapped: bytes, context: bytes) -> bytes:
        key = self._keys.get(kek_version)
        if key is None:
            raise KeyUnavailableError
        if len(wrapped) < MIN_ENVELOPE_BYTES or wrapped[:1] != FORMAT_VERSION:
            raise DecryptionError
        try:
            return AESGCM(key).decrypt(
                wrapped[1 : 1 + NONCE_BYTES], wrapped[1 + NONCE_BYTES :], context
            )
        except InvalidTag:
            raise DecryptionError from None

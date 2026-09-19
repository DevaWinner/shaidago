"""Reviewer password hashing (Argon2id) with central parameters and rehash-on-success."""

from dataclasses import dataclass
from typing import Final

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

MIN_PASSWORD_CHARS: Final = 12
MAX_PASSWORD_CHARS: Final = 256
PLACEHOLDER_MARKERS: Final = ("change-me", "changeme", "password", "reviewer-demo", "letmein")


@dataclass(frozen=True)
class PasswordPolicy:
    """Argon2id parameters, defined once. Defaults follow the OWASP minimum (19 MiB, t=2, p=1)."""

    time_cost: int = 2
    memory_cost_kib: int = 19_456
    parallelism: int = 1

    def hasher(self) -> PasswordHasher:
        return PasswordHasher(
            time_cost=self.time_cost,
            memory_cost=self.memory_cost_kib,
            parallelism=self.parallelism,
        )


class WeakPasswordError(ValueError):
    """The password is refused; the message names the rule, never the password."""


def validate_new_password(password: str, *, deployed: bool) -> None:
    if not MIN_PASSWORD_CHARS <= len(password) <= MAX_PASSWORD_CHARS:
        raise WeakPasswordError(
            f"password must be {MIN_PASSWORD_CHARS} to {MAX_PASSWORD_CHARS} characters"
        )
    if deployed and any(marker in password.lower() for marker in PLACEHOLDER_MARKERS):
        raise WeakPasswordError("a placeholder or demo password is refused outside development")


@dataclass(frozen=True)
class Verification:
    matches: bool
    new_hash: str | None = None  # set only when the stored hash should be replaced


class PasswordVerifier:
    """Verifies passwords in constant-shape time, including for identifiers that do not exist."""

    def __init__(self, policy: PasswordPolicy | None = None) -> None:
        self.policy = policy or PasswordPolicy()
        self._hasher = self.policy.hasher()
        # A real hash of a random string, so an unknown identifier costs one verification too.
        self._decoy = self._hasher.hash("decoy-" + "x" * 32)

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, stored_hash: str | None, password: str) -> Verification:
        candidate = stored_hash if stored_hash is not None else self._decoy
        try:
            self._hasher.verify(candidate, password)
        except VerifyMismatchError, VerificationError, InvalidHashError:
            return Verification(matches=False)
        if stored_hash is None:
            return Verification(matches=False)
        needs_rehash = self._hasher.check_needs_rehash(stored_hash)
        return Verification(
            matches=True, new_hash=self._hasher.hash(password) if needs_rehash else None
        )

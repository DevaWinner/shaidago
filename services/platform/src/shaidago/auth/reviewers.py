"""Reviewer users: creation, identifier rules, password change, and disablement."""

import re
from dataclasses import dataclass
from typing import Final, Literal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.audit.events import AuditWriter
from shaidago.auth.passwords import PasswordVerifier, validate_new_password
from shaidago.shared.clock import Clock
from shaidago.shared.ids import IdGenerator

Role = Literal["reviewer", "admin"]
IDENTIFIER_PATTERN: Final = re.compile(r"^[a-z0-9][a-z0-9._@+-]{2,127}$")


class IdentifierError(ValueError):
    """The identifier is not acceptable; carries no submitted value."""


def normalise_identifier(raw: str) -> str:
    """Trim and lower-case, then require the stored format. Raises ``IdentifierError``."""
    candidate = raw.strip().lower()
    if IDENTIFIER_PATTERN.fullmatch(candidate) is None:
        raise IdentifierError("identifier must be 3-128 characters of a-z, 0-9, and . _ @ + -")
    return candidate


@dataclass(frozen=True)
class ReviewerRecord:
    id: UUID
    identifier: str
    password_hash: str
    role: Role
    state: Literal["active", "disabled"]
    credential_version: int


_BY_IDENTIFIER = text(
    "SELECT id, identifier, password_hash, role, state, credential_version "
    "FROM app.reviewers WHERE identifier = :identifier"
)


async def find_reviewer(session: AsyncSession, identifier: str) -> ReviewerRecord | None:
    """Lookup by normalised identifier; an invalid identifier simply finds nothing."""
    try:
        normalised = normalise_identifier(identifier)
    except IdentifierError:
        return None
    row = (await session.execute(_BY_IDENTIFIER, {"identifier": normalised})).one_or_none()
    if row is None:
        return None
    return ReviewerRecord(
        row.id, row.identifier, row.password_hash, row.role, row.state, row.credential_version
    )


class ReviewerService:
    """Creation and administration. Session revocation is added with the session store (BE-051)."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        clock: Clock,
        ids: IdGenerator,
        passwords: PasswordVerifier,
        deployed: bool,
    ) -> None:
        self._session = session
        self._clock = clock
        self._ids = ids
        self._passwords = passwords
        self._deployed = deployed
        self._audit = AuditWriter(session, clock, ids)

    async def create(
        self, identifier: str, password: str, role: Role, *, request_id: str | None = None
    ) -> UUID:
        """Create a reviewer. Raises on a weak password or a duplicate identifier."""
        normalised = normalise_identifier(identifier)
        validate_new_password(password, deployed=self._deployed)
        now = self._clock.now()
        reviewer_id = self._ids.new()
        await self._session.execute(
            text(
                "INSERT INTO app.reviewers (id, identifier, password_hash, role, state, "
                "credential_version, created_at, updated_at) VALUES "
                "(:id, :identifier, :hash, :role, 'active', 1, :now, :now)"
            ),
            {
                "id": reviewer_id,
                "identifier": normalised,
                "hash": self._passwords.hash(password),
                "role": role,
                "now": now,
            },
        )
        await self._audit.record(
            "reviewer_created",
            actor_type="system",
            subject_type="reviewer",
            subject_id=reviewer_id,
            request_id=request_id,
            details={"role": role},
        )
        return reviewer_id

"""The collaborators every reviewer operation shares, built once per request transaction."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.api.dependencies import Dependencies
from shaidago.shared.clock import Clock
from shaidago.shared.config import Settings
from shaidago.shared.crypto import EnvironmentKekWrapper, FieldCipher
from shaidago.shared.data_keys import DataKeyService
from shaidago.shared.ids import IdGenerator


@dataclass(frozen=True)
class ReviewContext:
    session: AsyncSession
    keys: DataKeyService
    cipher: FieldCipher
    clock: Clock
    ids: IdGenerator

    @classmethod
    def build(
        cls, session: AsyncSession, dependencies: Dependencies, settings: Settings
    ) -> ReviewContext:
        ring = settings.crypto
        wrapper = EnvironmentKekWrapper(ring.kek_keys().keys, ring.active_kek_version)
        return cls(
            session,
            DataKeyService(session, wrapper, dependencies.clock, dependencies.ids),
            FieldCipher(),
            dependencies.clock,
            dependencies.ids,
        )

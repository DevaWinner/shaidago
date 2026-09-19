"""Data keys in PostgreSQL: creation as the insert-only role, shredding, and KEK rotation."""

import io
import json
import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime

import pytest
import structlog
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.shared.clock import ManualClock
from shaidago.shared.crypto import (
    DecryptionError,
    EnvironmentKekWrapper,
    FieldCipher,
    KeyUnavailableError,
    field_context,
)
from shaidago.shared.data_keys import DataKeyDestroyedError, DataKeyService, dek_context
from shaidago.shared.database import Database, build_engine
from shaidago.shared.ids import Uuid7Generator
from shaidago.shared.logging import configure_logging
from tests.integration.support import Plain

START = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
KEK1, KEK2 = b"1" * 32, b"2" * 32
CANARY = b"private-canary: a description a reporter wrote"
PRIVILEGE = "42501"
CHECK = "23514"


def service(session: AsyncSession, wrapper: EnvironmentKekWrapper) -> DataKeyService:
    clock = ManualClock(START)
    return DataKeyService(session, wrapper, clock, Uuid7Generator(clock))


@pytest.fixture
async def dbs(role_urls: dict[str, URL]) -> AsyncIterator[dict[str, Database]]:
    built = {
        role: build_engine(role_urls[role], application_name=role, statement_timeout_ms=8000)
        for role in ("owner", "shaidago_public", "shaidago_reviewer")
    }
    yield {role: Database(engine) for role, engine in built.items()}
    for engine in built.values():
        await engine.dispose()


async def sqlstate_of(action: Callable[[], Awaitable[object]]) -> str | None:
    with pytest.raises(DBAPIError) as raised:
        await action()
    return getattr(raised.value.orig, "sqlstate", None)


async def test_the_insert_only_public_role_can_create_a_key_but_never_read_it(
    dbs: dict[str, Database],
) -> None:
    wrapper = EnvironmentKekWrapper({"kek-1": KEK1}, "kek-1")
    owner_id = uuid.uuid4()
    async with dbs["shaidago_public"].unit_of_work() as session:
        created = await service(session, wrapper).create(
            "private_reports", owner_id, "report_content"
        )

    async def read() -> None:
        async with dbs["shaidago_public"].unit_of_work() as session:
            await session.execute(text("SELECT * FROM app.data_keys"))

    assert await sqlstate_of(read) == PRIVILEGE
    async with dbs["shaidago_reviewer"].unit_of_work() as session:
        loaded = await service(session, wrapper).load(created.id)
    assert loaded.key == created.key


async def test_a_field_encrypted_with_a_stored_key_decrypts_only_in_its_own_context(
    dbs: dict[str, Database],
) -> None:
    wrapper = EnvironmentKekWrapper({"kek-1": KEK1}, "kek-1")
    row = uuid.uuid4()
    cipher = FieldCipher()
    async with dbs["owner"].unit_of_work() as session:
        key = await service(session, wrapper).create("private_reports", row, "report_content")
    context = field_context("private_reports", row, "description", 1)
    envelope = cipher.encrypt(key, CANARY, context)
    async with dbs["owner"].unit_of_work() as session:
        reloaded = await service(session, wrapper).load(key.id)
    assert cipher.decrypt(reloaded, envelope, context) == CANARY
    with pytest.raises(DecryptionError):
        cipher.decrypt(
            reloaded, envelope, field_context("private_reports", uuid.uuid4(), "description", 1)
        )


async def test_one_key_per_record_and_purpose_and_only_the_known_purposes(
    dbs: dict[str, Database],
) -> None:
    wrapper = EnvironmentKekWrapper({"kek-1": KEK1}, "kek-1")
    row = uuid.uuid4()
    async with dbs["owner"].unit_of_work() as session:
        svc = service(session, wrapper)
        keys = [
            await svc.create("private_reports", row, p)
            for p in ("report_content", "contact", "review_notes", "follow_up_answers")
        ]
    assert len({k.key for k in keys}) == 4, "each purpose has an independent key"
    with pytest.raises(ValueError, match="purpose"):
        async with dbs["owner"].unit_of_work() as session:
            await service(session, wrapper).create("private_reports", row, "everything")

    async def duplicate() -> None:
        async with Plain(dbs["owner"].engine).unit_of_work() as session:
            await service(session, wrapper).create("private_reports", row, "contact")

    assert await sqlstate_of(duplicate) == "23505"


async def test_the_database_holds_only_a_wrapped_key_never_the_key(
    dbs: dict[str, Database],
) -> None:
    wrapper = EnvironmentKekWrapper({"kek-1": KEK1}, "kek-1")
    row = uuid.uuid4()
    async with dbs["owner"].unit_of_work() as session:
        key = await service(session, wrapper).create("private_reports", row, "contact")
        stored = (
            await session.execute(
                text("SELECT wrapped_key, kek_version FROM app.data_keys WHERE id = :i"),
                {"i": key.id},
            )
        ).one()
    assert key.key not in bytes(stored.wrapped_key)
    assert stored.kek_version == "kek-1"
    assert (
        wrapper.unwrap(
            "kek-1",
            bytes(stored.wrapped_key),
            dek_context(key.id, "contact", "private_reports", row),
        )
        == key.key
    )


async def test_destroying_a_purpose_shreds_only_that_key(dbs: dict[str, Database]) -> None:
    wrapper = EnvironmentKekWrapper({"kek-1": KEK1}, "kek-1")
    row = uuid.uuid4()
    async with dbs["owner"].unit_of_work() as session:
        svc = service(session, wrapper)
        content = await svc.create("private_reports", row, "report_content")
        contact = await svc.create("private_reports", row, "contact")
    async with dbs["owner"].unit_of_work() as session:
        assert await service(session, wrapper).destroy("private_reports", row, "contact") is True
        assert await service(session, wrapper).destroy("private_reports", row, "contact") is False
    async with dbs["owner"].unit_of_work() as session:
        svc = service(session, wrapper)
        assert (await svc.load(content.id)).key == content.key
        with pytest.raises(DataKeyDestroyedError):
            await svc.load(contact.id)
        state = (
            await session.execute(
                text(
                    "SELECT wrapped_key, kek_version, destroyed_at FROM app.data_keys WHERE id = :i"
                ),
                {"i": contact.id},
            )
        ).one()
    assert (state.wrapped_key, state.kek_version) == (None, None)
    assert state.destroyed_at == START


async def test_the_database_refuses_a_half_destroyed_or_malformed_key_row(
    dbs: dict[str, Database],
) -> None:
    async def insert(sql: str) -> None:
        async with dbs["owner"].unit_of_work() as session:
            await session.execute(text(sql))

    base = "INSERT INTO app.data_keys VALUES (gen_random_uuid(), 'contact', 'private_reports', gen_random_uuid(), "
    assert await sqlstate_of(lambda: insert(base + "NULL, NULL, now(), NULL)")) == CHECK
    assert await sqlstate_of(lambda: insert(base + "'\\x00', 'kek-1', now(), NULL)")) == CHECK
    assert await sqlstate_of(lambda: insert(base + "'\\x00', 'kek-1', now(), now())")) == CHECK


async def test_unknown_or_missing_keys_fail_generically(dbs: dict[str, Database]) -> None:
    wrapper = EnvironmentKekWrapper({"kek-1": KEK1}, "kek-1")
    with pytest.raises(DecryptionError):
        async with dbs["owner"].unit_of_work() as session:
            await service(session, wrapper).load(uuid.uuid4())


async def test_rotation_rewraps_in_resumable_batches_and_leaves_ciphertext_untouched(
    dbs: dict[str, Database],
) -> None:
    old = EnvironmentKekWrapper({"kek-1": KEK1}, "kek-1")
    both = EnvironmentKekWrapper({"kek-1": KEK1, "kek-2": KEK2}, "kek-2")
    cipher = FieldCipher()
    sealed: list[tuple[uuid.UUID, uuid.UUID, bytes]] = []  # key id, row id, envelope
    async with dbs["owner"].unit_of_work() as session:
        svc = service(session, old)
        for _ in range(25):
            row = uuid.uuid4()
            key = await svc.create("rotation_probe", row, "report_content")
            sealed.append(
                (
                    key.id,
                    row,
                    cipher.encrypt(key, CANARY, field_context("rotation_probe", row, "body", 1)),
                )
            )
    async with dbs["owner"].unit_of_work() as session:
        before = await service(session, both).rotate(limit=0)
    assert before.remaining >= 25
    counts: list[int] = []
    for _ in range(10):  # other tests share this database, so run batches until none remain
        async with dbs["owner"].unit_of_work() as session:
            result = await service(session, both).rotate_and_audit(limit=10)
        counts.append(result.rewrapped)
        if result.rewrapped == 0:
            break
    assert counts[0] == 10, "batches are bounded"
    assert sum(counts) >= 25
    assert counts[-1] == 0, "a finished rotation does nothing when run again"
    async with dbs["owner"].unit_of_work() as session:
        versions = {
            r[0]
            for r in await session.execute(
                text(
                    "SELECT DISTINCT kek_version FROM app.data_keys WHERE owner_table = 'rotation_probe'"
                )
            )
        }
    assert versions == {"kek-2"}
    only_new = EnvironmentKekWrapper({"kek-2": KEK2}, "kek-2")  # the old KEK may now be retired
    async with dbs["owner"].unit_of_work() as session:
        for key_id, row, envelope in sealed:
            key = await service(session, only_new).load(key_id)
            assert (
                cipher.decrypt(key, envelope, field_context("rotation_probe", row, "body", 1))
                == CANARY
            )


async def test_an_interrupted_batch_rolls_back_and_a_rerun_completes_it(
    dbs: dict[str, Database],
) -> None:
    old = EnvironmentKekWrapper({"kek-1": KEK1}, "kek-1")
    both = EnvironmentKekWrapper({"kek-1": KEK1, "kek-2": KEK2}, "kek-2")
    async with dbs["owner"].unit_of_work() as session:
        svc = service(session, old)
        rows = [uuid.uuid4() for _ in range(5)]
        for row in rows:
            await svc.create("interrupt_probe", row, "contact")

    async def failing_rotation() -> None:
        async with dbs["owner"].unit_of_work() as session:
            await service(session, both).rotate(limit=1000)
            raise RuntimeError("crash before commit")

    with pytest.raises(RuntimeError):
        await failing_rotation()
    async with dbs["owner"].unit_of_work() as session:
        stale = (
            await session.execute(
                text(
                    "SELECT count(*) FROM app.data_keys WHERE owner_table = 'interrupt_probe' AND kek_version = 'kek-1'"
                )
            )
        ).scalar_one()
    assert stale == 5, "nothing half-rotated"
    async with dbs["owner"].unit_of_work() as session:
        await service(session, both).rotate(limit=1000)
        left = (
            await session.execute(
                text(
                    "SELECT count(*) FROM app.data_keys WHERE owner_table = 'interrupt_probe' AND kek_version = 'kek-1'"
                )
            )
        ).scalar_one()
    assert left == 0


async def test_keys_wrapped_under_a_removed_kek_are_reported_not_guessed(
    dbs: dict[str, Database],
) -> None:
    old = EnvironmentKekWrapper({"kek-0": b"0" * 32}, "kek-0")
    current = EnvironmentKekWrapper({"kek-2": KEK2}, "kek-2")
    row = uuid.uuid4()
    async with dbs["owner"].unit_of_work() as session:
        key = await service(session, old).create("orphan_probe", row, "contact")
    async with dbs["owner"].unit_of_work() as session:
        result = await service(session, current).rotate(limit=10_000)
    assert result.unavailable >= 1
    with pytest.raises(KeyUnavailableError):
        async with dbs["owner"].unit_of_work() as session:
            await service(session, current).load(key.id)


async def test_rotation_audits_counts_only_and_never_logs_key_material(
    dbs: dict[str, Database],
) -> None:
    old = EnvironmentKekWrapper({"kek-1": KEK1}, "kek-1")
    both = EnvironmentKekWrapper({"kek-1": KEK1, "kek-2": KEK2}, "kek-2")
    buffer = io.StringIO()
    configure_logging(service="svc", environment="test", level="DEBUG", stream=buffer)
    try:
        async with dbs["owner"].unit_of_work() as session:
            key = await service(session, old).create("audit_probe", uuid.uuid4(), "contact")
        async with dbs["owner"].unit_of_work() as session:
            await service(session, both).rotate_and_audit(limit=10_000)
        output = buffer.getvalue()
    finally:
        structlog.reset_defaults()
        logging.getLogger().handlers.clear()
    assert key.key.hex() not in output
    assert KEK1.hex() not in output
    assert "kek rotation batch" in output
    async with dbs["owner"].unit_of_work() as session:
        details = (
            await session.execute(
                text(
                    "SELECT details FROM app.audit_events WHERE event = 'kek_rotation_batch' ORDER BY occurred_at DESC, id DESC LIMIT 1"
                )
            )
        ).scalar_one()
    assert set(details) == {"rewrapped", "unavailable", "remaining", "active_version"}
    assert key.key.hex() not in json.dumps(details)

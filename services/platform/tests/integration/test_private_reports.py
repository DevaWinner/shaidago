"""Private report persistence: insert-only role, encryption, atomicity, and status history."""

import json
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.reports.persistence import (
    ContactInput,
    InvalidReportError,
    NewReport,
    ReportWriter,
    read_description,
)
from shaidago.reports.tracking import generate, normalise
from shaidago.shared.clock import ManualClock
from shaidago.shared.crypto import EnvironmentKekWrapper, FieldCipher
from shaidago.shared.data_keys import DataKeyDestroyedError, DataKeyService
from shaidago.shared.database import Database, build_engine
from shaidago.shared.ids import Uuid7Generator
from shaidago.shared.problems import CONFLICT, ProblemError
from shaidago.shared.vocabulary import values
from tests.integration.support import Plain, insert_project

START = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
WRAPPER = EnvironmentKekWrapper({"kek-1": b"1" * 32}, "kek-1")
PEPPER = b"p" * 32
CANARY = "FICTIONAL private description canary: the gate was locked."
CONTACT = ContactInput("email", "fictional.reporter.canary@example.test")
LATER = START + timedelta(minutes=5)
PRIVILEGE = "42501"
CHECK = "23514"
APPEND_ONLY = "55000"
PRIVATE_TABLES = (
    "reports",
    "report_contacts",
    "report_status_events",
    "report_tracking_keys",
    "evidence_files",
)


@pytest.fixture
async def dbs(role_urls: dict[str, URL]) -> AsyncIterator[dict[str, Database]]:
    engines = {
        role: build_engine(role_urls[role], application_name=role, statement_timeout_ms=8000)
        for role in ("owner", "shaidago_public", "shaidago_reviewer")
    }
    yield {role: Database(engine) for role, engine in engines.items()}
    for engine in engines.values():
        await engine.dispose()


async def sqlstate_of(action: Callable[[], Awaitable[object]]) -> str | None:
    with pytest.raises(DBAPIError) as raised:
        await action()
    return getattr(raised.value.orig, "sqlstate", None)


async def project(dbs: dict[str, Database]) -> uuid.UUID:
    async with Plain(dbs["owner"].engine).unit_of_work() as session:
        return await insert_project(session)


def writer(session: AsyncSession) -> ReportWriter:
    clock = ManualClock(START)
    ids = Uuid7Generator(clock)
    return ReportWriter(
        session,
        DataKeyService(session, WRAPPER, clock, ids),
        cipher=FieldCipher(),
        clock=clock,
        ids=ids,
    )


def new_report(project_id: uuid.UUID, contact: ContactInput | None = None) -> NewReport:
    return NewReport(project_id, "incomplete_work", CANARY, contact)


async def submit(
    dbs: dict[str, Database], project_id: uuid.UUID, contact: ContactInput | None = None
) -> tuple[uuid.UUID, str]:
    code = generate()
    async with dbs["shaidago_public"].unit_of_work() as session:
        report_id = await writer(session).insert(
            new_report(project_id, contact), code, pepper_version="p-1", pepper=PEPPER
        )
    return report_id, code.canonical


async def test_the_insert_only_role_stores_a_report_without_ever_reading_back(
    dbs: dict[str, Database],
) -> None:
    project_id = await project(dbs)
    statements: list[str] = []
    engine = dbs["shaidago_public"].engine.sync_engine

    @event.listens_for(engine, "before_cursor_execute")
    def capture(_c: object, _cur: object, statement: str, *_rest: object) -> None:
        statements.append(statement)

    report_id, _code = await submit(dbs, project_id, CONTACT)
    event.remove(engine, "before_cursor_execute", capture)
    assert any("INSERT INTO app.reports" in s for s in statements)
    assert not [s for s in statements if s.lstrip().upper().startswith("SELECT") and "app." in s]
    assert not [s for s in statements if "RETURNING" in s.upper()]
    async with dbs["owner"].unit_of_work() as session:
        counts = {
            table: (
                await session.execute(
                    text(
                        f"SELECT count(*) FROM app.{table} WHERE report_id = :i"
                        if table != "reports"
                        else "SELECT count(*) FROM app.reports WHERE id = :i"
                    ),
                    {"i": report_id},
                )
            ).scalar_one()
            for table in (
                "reports",
                "report_contacts",
                "report_status_events",
                "report_tracking_keys",
            )
        }
    assert counts == {
        "reports": 1,
        "report_contacts": 1,
        "report_status_events": 1,
        "report_tracking_keys": 1,
    }


@pytest.mark.parametrize("table", PRIVATE_TABLES)
async def test_the_public_role_can_never_read_change_or_delete_private_rows(
    dbs: dict[str, Database], table: str
) -> None:
    for sql in (
        f"SELECT * FROM app.{table}",
        f"UPDATE app.{table} SET id = id",
        f"DELETE FROM app.{table}",
    ):

        async def run(sql: str = sql) -> None:
            async with dbs["shaidago_public"].unit_of_work() as session:
                await session.execute(text(sql))

        assert await sqlstate_of(run) == PRIVILEGE, sql


async def test_nothing_readable_is_stored_and_the_description_decrypts_for_reviewers_only(
    dbs: dict[str, Database],
) -> None:
    report_id, code = await submit(dbs, await project(dbs), CONTACT)
    async with dbs["owner"].unit_of_work() as session:
        rows = (
            await session.execute(text("SELECT * FROM app.reports WHERE id = :i"), {"i": report_id})
        ).all()
        contact = (
            await session.execute(
                text("SELECT * FROM app.report_contacts WHERE report_id = :i"), {"i": report_id}
            )
        ).all()
        tracking = (
            await session.execute(
                text("SELECT * FROM app.report_tracking_keys WHERE report_id = :i"),
                {"i": report_id},
            )
        ).all()
    blob = repr([tuple(map(_bytes, r)) for r in (*rows, *contact, *tracking)]).encode()
    for secret in (CANARY, CONTACT.value, CONTACT.channel, code):
        assert secret.encode() not in blob
    clock = ManualClock(START)
    async with dbs["shaidago_reviewer"].unit_of_work() as session:
        keys = DataKeyService(session, WRAPPER, clock, Uuid7Generator(clock))
        assert await read_description(session, keys, FieldCipher(), report_id) == CANARY


def _bytes(value: object) -> object:
    return value.hex() if isinstance(value, bytes | memoryview) else value


async def test_reviewers_cannot_read_contacts_and_can_change_only_the_status_projection(
    dbs: dict[str, Database],
) -> None:
    report_id, _ = await submit(dbs, await project(dbs), CONTACT)

    async def read_contacts() -> None:
        async with dbs["shaidago_reviewer"].unit_of_work() as session:
            await session.execute(text("SELECT * FROM app.report_contacts"))

    assert await sqlstate_of(read_contacts) == PRIVILEGE
    for sql in (
        "UPDATE app.reports SET concern_category = 'other_concern' WHERE id = :i",
        "UPDATE app.reports SET description_ciphertext = '\\x00' WHERE id = :i",
        "UPDATE app.reports SET project_id = gen_random_uuid() WHERE id = :i",
        "DELETE FROM app.reports WHERE id = :i",
    ):

        async def run(sql: str = sql) -> None:
            async with dbs["shaidago_reviewer"].unit_of_work() as session:
                await session.execute(text(sql), {"i": report_id})

        assert await sqlstate_of(run) == PRIVILEGE, sql


async def test_a_failure_at_any_step_leaves_nothing_behind(dbs: dict[str, Database]) -> None:
    project_id = await project(dbs)
    first_id, code_text = await submit(dbs, project_id)
    duplicate = normalise(code_text)  # the same tracking key: the last insert fails
    async with dbs["owner"].unit_of_work() as session:
        before = (await session.execute(text("SELECT count(*) FROM app.reports"))).scalar_one()
        keys_before = (
            await session.execute(text("SELECT count(*) FROM app.data_keys"))
        ).scalar_one()
    with pytest.raises(ProblemError) as raised:
        async with dbs["shaidago_public"].unit_of_work() as session:
            await writer(session).insert(
                new_report(project_id, CONTACT), duplicate, pepper_version="p-1", pepper=PEPPER
            )
    assert raised.value.problem is CONFLICT
    async with dbs["owner"].unit_of_work() as session:
        after = (await session.execute(text("SELECT count(*) FROM app.reports"))).scalar_one()
        keys_after = (
            await session.execute(text("SELECT count(*) FROM app.data_keys"))
        ).scalar_one()
    assert (after, keys_after) == (before, keys_before), (
        "report, event, contact, and both keys rolled back"
    )
    assert first_id


@pytest.mark.parametrize(
    "bad",
    [
        NewReport(uuid.uuid4(), "incomplete_work", "   "),
        NewReport(uuid.uuid4(), "incomplete_work", "x" * 8001),
        NewReport(uuid.uuid4(), "incomplete_work", "ok", ContactInput("email", "")),
        NewReport(uuid.uuid4(), "incomplete_work", "ok", ContactInput("email", "v" * 201)),
    ],
)
async def test_unusable_content_is_refused_before_any_write_without_echoing_it(
    dbs: dict[str, Database], bad: NewReport
) -> None:
    with pytest.raises(InvalidReportError) as raised:
        async with dbs["shaidago_public"].unit_of_work() as session:
            await writer(session).insert(bad, generate(), pepper_version="p-1", pepper=PEPPER)
    assert "x" * 20 not in str(raised.value)


async def test_the_contact_can_be_destroyed_without_touching_the_report(
    dbs: dict[str, Database],
) -> None:
    report_id, _ = await submit(dbs, await project(dbs), CONTACT)
    clock = ManualClock(START)
    async with dbs["owner"].unit_of_work() as session:
        service = DataKeyService(session, WRAPPER, clock, Uuid7Generator(clock))
        assert await service.destroy("reports", report_id, "contact") is True
    async with dbs["owner"].unit_of_work() as session:
        service = DataKeyService(session, WRAPPER, clock, Uuid7Generator(clock))
        assert await read_description(session, service, FieldCipher(), report_id) == CANARY
        contact_key = await service.find("reports", report_id, "contact")
        assert contact_key is not None
        with pytest.raises(DataKeyDestroyedError):
            await service.load(contact_key)


async def test_anonymous_reports_carry_no_contact_and_the_flag_says_so(
    dbs: dict[str, Database],
) -> None:
    anonymous, _ = await submit(dbs, await project(dbs))
    named, _ = await submit(dbs, await project(dbs), CONTACT)
    async with dbs["owner"].unit_of_work() as session:
        flags = {
            r.id: r.anonymous
            for r in await session.execute(text("SELECT id, anonymous FROM app.reports"))
        }
        contacts = (
            await session.execute(
                text("SELECT count(*) FROM app.report_contacts WHERE report_id = :i"),
                {"i": anonymous},
            )
        ).scalar_one()
    assert flags[anonymous] is True
    assert flags[named] is False
    assert contacts == 0


async def add_event(
    dbs: dict[str, Database],
    report_id: uuid.UUID,
    previous: str,
    new: str,
    *,
    update_status: bool = True,
) -> None:
    async with dbs["shaidago_reviewer"].unit_of_work() as session:
        await session.execute(
            text(
                "INSERT INTO app.report_status_events VALUES "
                "(:id, :r, :p, :n, 'A safe message.', 'reviewer', NULL, :at)"
            ),
            {"id": uuid.uuid4(), "r": report_id, "p": previous, "n": new, "at": LATER},
        )
        if update_status:
            await session.execute(
                text(
                    "UPDATE app.reports SET status = :n, status_updated_at = :at, "
                    "updated_at = :at WHERE id = :r"
                ),
                {"n": new, "r": report_id, "at": LATER},
            )


async def test_status_history_is_append_only_and_the_projection_must_match_it(
    dbs: dict[str, Database],
) -> None:
    report_id, _ = await submit(dbs, await project(dbs))
    event_without_status = await sqlstate_of(
        lambda: add_event(dbs, report_id, "received", "under_review", update_status=False)
    )
    assert event_without_status == CHECK
    await add_event(dbs, report_id, "received", "under_review")

    async def raw_status_change() -> None:
        async with dbs["shaidago_reviewer"].unit_of_work() as session:
            await session.execute(
                text("UPDATE app.reports SET status = 'closed' WHERE id = :r"), {"r": report_id}
            )

    assert await sqlstate_of(raw_status_change) == CHECK, "a status change needs its event"
    for sql in (
        "UPDATE app.report_status_events SET public_message = 'x'",
        "DELETE FROM app.report_status_events",
    ):

        async def run(sql: str = sql) -> None:
            async with dbs["owner"].unit_of_work() as session:
                await session.execute(text(sql))

        assert await sqlstate_of(run) == APPEND_ONLY, sql


@pytest.mark.parametrize(
    ("previous", "new", "allowed"),
    [
        ("received", "verified_for_public_update", False),
        ("received", "referred", False),
        ("closed", "received", False),
        ("under_review", "received", False),
        ("closed", "under_review", True),
        ("received", "needs_information", True),
        ("under_review", "verified_for_public_update", True),
    ],
)
async def test_only_legal_transitions_can_be_recorded(
    dbs: dict[str, Database], previous: str, new: str, allowed: bool
) -> None:
    report_id, _ = await submit(dbs, await project(dbs))
    attempt = lambda: add_event(dbs, report_id, previous, new)  # noqa: E731
    if allowed:
        await attempt()
    else:
        assert await sqlstate_of(attempt) == CHECK


async def test_the_database_checks_match_the_controlled_vocabulary(
    dbs: dict[str, Database],
) -> None:
    async with dbs["owner"].unit_of_work() as session:
        definitions = {
            r.conname: r.definition
            for r in await session.execute(
                text(
                    "SELECT conname, pg_get_constraintdef(oid) AS definition FROM pg_constraint WHERE conname IN ('ck_reports_concern_category', 'ck_reports_status', 'ck_report_status_events_transition', 'ck_reports_risk_level')"
                )
            )
        }
    for value in values("report_concern_category"):
        assert f"'{value}'" in definitions["ck_reports_concern_category"]
    for value in values("report_status"):
        assert f"'{value}'" in definitions["ck_reports_status"]
    for value in values("report_risk_level"):
        assert f"'{value}'" in definitions["ck_reports_risk_level"]
    document = json.loads(
        (Path(__file__).parents[4] / "contracts" / "controlled-vocabulary.json").read_text()
    )
    pairs = {
        (t["from"], t["to"]) for t in document["state_machines"]["report_status"]["transitions"]
    }
    assert len(pairs) == 15
    definition = definitions["ck_report_status_events_transition"]
    for previous, new in pairs:
        assert (
            f"(previous_status = '{previous}'::text) AND (new_status = '{new}'::text)" in definition
        )
    assert definition.count("previous_status = '") == len(pairs)


async def test_the_reports_table_has_no_plaintext_or_identity_columns(
    dbs: dict[str, Database],
) -> None:
    async with dbs["owner"].unit_of_work() as session:
        columns = {
            r[0]
            for r in await session.execute(
                text(
                    "SELECT column_name FROM information_schema.columns WHERE table_schema = 'app' AND table_name IN ('reports', 'report_contacts', 'report_tracking_keys', 'evidence_files', 'report_status_events')"
                )
            )
        }
    for name in columns:
        assert name not in {
            "description",
            "contact",
            "email",
            "phone",
            "ip_address",
            "device",
            "handle",
            "code",
            "tracking_code",
        }
    assert {
        "description_ciphertext",
        "channel_ciphertext",
        "value_ciphertext",
        "lookup_hmac",
    } <= columns


@pytest.mark.parametrize(
    "fields",
    [
        {"object_key": "not-random"},
        {"object_key": "A" * 32},
        {"display_name": "a/b.png"},
        {"display_name": ""},
        {"sniffed_mime": "image/svg+xml"},
        {"sniffed_mime": "text/html"},
        {"size_bytes": 0},
        {"size_bytes": 10485761},
        {"sha256": "abc"},
        {"sanitation_state": "pending"},
        {"scan_state": "scan_failed"},
        {"scan_state": "malware_detected"},
    ],
)
async def test_evidence_rows_accept_only_sanitised_scanned_or_demo_files(
    dbs: dict[str, Database], fields: dict[str, Any]
) -> None:
    report_id, _ = await submit(dbs, await project(dbs))
    good = {
        "object_key": uuid.uuid4().hex,
        "display_name": "photo.png",
        "sniffed_mime": "image/png",
        "size_bytes": 1234,
        "sha256": "a" * 64,
        "sanitation_state": "sanitised",
        "scan_state": "clean",
    }

    async def insert(values_: dict[str, Any]) -> None:
        async with dbs["shaidago_public"].unit_of_work() as session:
            await session.execute(
                text(
                    "INSERT INTO app.evidence_files VALUES (:id, :r, :object_key, :display_name, :sniffed_mime, :size_bytes, :sha256, :sanitation_state, :scan_state, now())"
                ),
                {"id": uuid.uuid4(), "r": report_id, **values_},
            )

    await insert(good)
    await insert(good | {"object_key": uuid.uuid4().hex, "scan_state": "not_scanned_demo"})
    assert await sqlstate_of(lambda: insert(good | {"object_key": uuid.uuid4().hex} | fields)) in {
        CHECK,
        "23505",
    }

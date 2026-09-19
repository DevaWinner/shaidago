"""POST /v1/reports: privacy, idempotency, bounds, attachment handling, and rollback."""

import asyncio
import io
import json
import logging
import uuid
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from typing import Any

import pytest
import structlog
from PIL import Image
from sqlalchemy.engine import URL

from shaidago.api.dependencies import Dependencies
from shaidago.api.v1 import reports as reports_api
from shaidago.files.pipeline import EvidencePipeline, PipelineParts, StoredEvidence
from shaidago.files.rules import FileLimits
from shaidago.files.scanner import EICAR, EicarScanner
from shaidago.reports.tracking import generate, lookup_key, normalise
from shaidago.shared.database import Database, build_engine
from shaidago.shared.logging import configure_logging
from tests.integration.report_support import (
    CANARY,
    CLIENT,
    CODE_SHAPE,
    CONTACT_CANARY,
    RECEIPT_KEYS,
    Harness,
    build,
    png,
)
from tests.integration.support import Plain, insert_project


async def test_an_anonymous_report_is_stored_privately_and_returns_the_code_once(
    harness: Harness,
) -> None:
    before = await harness.count("reports")
    response = await harness.post()
    body = response.json()
    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    assert set(body) == RECEIPT_KEYS
    assert CODE_SHAPE.fullmatch(body["tracking_code"])
    assert (body["status"], body["published"], body["contact_saved"]) == ("received", False, False)
    assert body["attachments"] == []
    assert await harness.count("reports") == before + 1
    stored = await harness.rows(
        "SELECT r.anonymous, r.status, r.description_ciphertext, t.lookup_hmac, t.pepper_version "
        "FROM app.reports r JOIN app.report_tracking_keys t ON t.report_id = r.id "
        "ORDER BY r.created_at DESC LIMIT 1"
    )
    anonymous, status, ciphertext, digest, version = stored[0]
    assert (anonymous, status) == (True, "received")
    assert CANARY.encode() not in bytes(ciphertext)
    peppers = harness.settings.crypto.tracking_pepper_keys().keys
    assert bytes(digest) == lookup_key(peppers[version], normalise(body["tracking_code"]))
    assert await harness.count("report_contacts") == 0
    assert CANARY not in response.text
    assert harness.slug not in response.text


async def test_an_optional_contact_is_encrypted_separately(harness: Harness) -> None:
    response = await harness.post(
        harness.fields(contact_channel="email", contact_value=CONTACT_CANARY)
    )
    assert response.status_code == 201
    assert response.json()["contact_saved"] is True
    row = (
        await harness.rows("SELECT channel_ciphertext, value_ciphertext FROM app.report_contacts")
    )[-1]
    assert CONTACT_CANARY.encode() not in bytes(row[1])
    assert b"email" not in bytes(row[0])
    assert CONTACT_CANARY not in response.text


async def test_a_report_is_accepted_when_an_attachment_fails_and_says_which(
    harness: Harness,
) -> None:
    files = [
        ("site.png", png(), "image/png"),
        ("bad.svg", b"<svg><script>alert(1)</script></svg>", "image/svg+xml"),
        ("virus.png", png() + EICAR, "image/png"),
    ]
    response = await harness.post(files=files)
    assert response.status_code == 201
    outcomes = response.json()["attachments"]
    assert outcomes == [
        {"position": 1, "kept": True, "reason": None},
        {"position": 2, "kept": False, "reason": "unsupported_type"},
        {"position": 3, "kept": False, "reason": "malware_detected"},
    ]
    assert len(harness.store.objects) == 1
    assert await harness.count("evidence_files") == 1
    assert "site.png" not in response.text
    assert "bad.svg" not in response.text


async def test_a_retry_replays_the_exact_result_and_stores_one_report(harness: Harness) -> None:
    key = str(uuid.uuid4())
    before = await harness.count("reports")
    first = await harness.post(key=key, files=[("a.png", png(), "image/png")])
    second = await harness.post(key=key, files=[("a.png", png(), "image/png")])
    assert first.status_code == second.status_code == 201
    assert second.content == first.content
    assert second.headers["idempotency-replayed"] == "true"
    assert "idempotency-replayed" not in first.headers
    assert await harness.count("reports") == before + 1
    assert len(harness.store.objects) == 1, "a replay must not process or store the file again"


@pytest.mark.parametrize(
    "change",
    [
        {"description": CANARY + " Edited."},
        {"concern_category": "incomplete_work"},
        {"contact_channel": "phone", "contact_value": "+2348000000000"},
    ],
)
async def test_a_key_reused_for_a_different_request_is_rejected(
    harness: Harness, change: dict[str, str]
) -> None:
    key = str(uuid.uuid4())
    assert (await harness.post(key=key)).status_code == 201
    before = await harness.count("reports")
    clash = await harness.post(harness.fields(**change), key=key)
    assert clash.status_code == 409
    assert clash.json()["code"] == "idempotency_conflict"
    assert await harness.count("reports") == before


async def test_a_key_reused_with_a_different_file_is_rejected(harness: Harness) -> None:
    key = str(uuid.uuid4())
    assert (await harness.post(key=key, files=[("a.png", png(), "image/png")])).status_code == 201
    other = io.BytesIO()
    Image.new("RGB", (16, 16), "black").save(other, "PNG")
    clash = await harness.post(key=key, files=[("a.png", other.getvalue(), "image/png")])
    assert clash.status_code == 409


async def test_concurrent_duplicates_create_exactly_one_report(harness: Harness) -> None:
    key = str(uuid.uuid4())
    before = await harness.count("reports")
    first, second = await asyncio.gather(harness.post(key=key), harness.post(key=key))
    assert {first.status_code, second.status_code} == {201}
    assert first.content == second.content
    assert await harness.count("reports") == before + 1


@pytest.mark.parametrize(
    ("key", "code"),
    [(None, "idempotency_key_required"), ("not-a-uuid", "idempotency_key_invalid")],
)
async def test_the_idempotency_key_is_required_and_validated(
    harness: Harness, key: str | None, code: str
) -> None:
    response = await harness.post(key=key)
    assert response.status_code == 400
    assert response.json()["code"] == code


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"project_slug": "no-such-project"}, "project_slug"),
        ({"project_slug": "Not A Slug!"}, "project_slug"),
        ({"concern_category": "guilty"}, "concern_category"),
        ({"description": "too short"}, "description"),
        ({"description": "x" * 8001}, "description"),
        ({"contact_channel": "email"}, "contact_value"),
        ({"contact_value": "a@b.example"}, "contact_channel"),
        ({"contact_channel": "email", "contact_value": "not-an-email"}, "contact_value"),
        ({"contact_channel": "fax", "contact_value": "12345678"}, "contact_channel"),
        ({"contact_channel": "phone", "contact_value": "call me"}, "contact_value"),
    ],
)
async def test_invalid_fields_are_named_without_echoing_values(
    harness: Harness, overrides: dict[str, str], field: str
) -> None:
    before = await harness.count("reports")
    response = await harness.post(harness.fields(**overrides))
    body = response.json()
    assert response.status_code == 422
    assert field in {error["field"] for error in body["errors"]}
    for value in overrides.values():
        assert value not in response.text or len(value) < 6
    assert await harness.count("reports") == before


async def test_unexpected_fields_and_too_many_files_are_refused(harness: Harness) -> None:
    extra = await harness.post({**harness.fields(), "reporter_name": "Somebody"})
    assert extra.status_code == 422
    assert "Somebody" not in extra.text
    assert "reporter_name" not in extra.text
    many = await harness.post(files=[(f"{i}.png", png(), "image/png") for i in range(4)])
    assert many.status_code == 422
    assert len(harness.store.objects) == 0


async def test_only_multipart_is_accepted(harness: Harness) -> None:
    async with harness.client() as client:
        response = await client.post(
            "/v1/reports",
            json={"description": CANARY},
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )
    assert response.status_code == 415


async def test_oversized_bodies_are_refused_by_declared_and_by_actual_size(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(reports_api, "MAX_BODY_BYTES", 5000)
    declared = await harness.post(files=[("a.bin", b"0" * 9000, "image/png")])
    assert declared.status_code == 413

    async def endless() -> AsyncIterator[bytes]:
        yield b"--b\r\nContent-Disposition: form-data; name=description\r\n\r\n"
        for _ in range(100):
            yield b"x" * 1000

    async with harness.client() as client:  # chunked, so there is no Content-Length to trust
        streamed = await client.post(
            "/v1/reports",
            content=endless(),
            headers={
                "Content-Type": "multipart/form-data; boundary=b",
                "Idempotency-Key": str(uuid.uuid4()),
            },
        )
    assert streamed.status_code == 413
    assert streamed.json()["code"] == "payload_too_large"


async def test_submissions_are_rate_limited_per_client(role_urls: dict[str, URL]) -> None:
    engines: list[Any] = []
    owner = build_engine(role_urls["owner"], application_name="o", statement_timeout_ms=8000)
    engines.append(owner)
    app, (store, pool) = build(role_urls, engines, RATE_SUBMISSION_PER_HOUR="2")
    try:
        async with Plain(owner).unit_of_work() as session:
            await insert_project(session, slug="synthetic-rate-limit")
        limited = Harness(app, Database(owner), store, "synthetic-rate-limit")
        codes = [(await limited.post()).status_code for _ in range(3)]
        blocked = await limited.post()
        assert codes == [201, 201, 429]
        assert blocked.headers["retry-after"].isdigit()
        assert blocked.json()["code"] == "rate_limited"
    finally:
        pool.shutdown()
        for engine in engines:
            await engine.dispose()


async def test_an_unknown_project_leaves_no_trace_and_the_key_stays_usable(
    harness: Harness,
) -> None:
    key = str(uuid.uuid4())
    before = (await harness.count("reports"), await harness.count("idempotency_records"))
    bad = await harness.post(harness.fields(project_slug="no-such-project"), key=key)
    assert bad.status_code == 422
    assert (await harness.count("reports"), await harness.count("idempotency_records")) == before
    assert (await harness.post(key=key)).status_code == 201


class BrokenEvidence(EvidencePipeline):
    """Stores a real object, then reports a state the database refuses."""

    async def process(
        self, chunks: Any, *, filename: str, declared_mime: str | None = None
    ) -> StoredEvidence:
        real = await super().process(chunks, filename=filename, declared_mime=declared_mime)
        return replace(real, scan_state="pending")


async def test_a_failure_while_saving_evidence_rolls_everything_back_and_discards_the_file(
    harness: Harness,
) -> None:
    store, pool = harness.store, ThreadPoolExecutor(max_workers=1)
    broken = BrokenEvidence(
        PipelineParts(EicarScanner(), store, pool), limits=FileLimits(max_dimension=64)
    )
    dependencies: Dependencies = harness.app.state.dependencies
    harness.app.state.dependencies = replace(dependencies, evidence_pipeline=broken)
    before = {t: await harness.count(t) for t in ("reports", "report_tracking_keys", "data_keys")}
    try:
        response = await harness.post(files=[("a.png", png(), "image/png")])
    finally:
        pool.shutdown()
    assert response.status_code >= 400
    assert {t: await harness.count(t) for t in before} == before
    assert store.objects == {}, "the uploaded object is removed when the database refuses the row"
    assert CANARY not in response.text


async def test_a_duplicate_tracking_code_rolls_back_the_second_report(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixed = generate()
    monkeypatch.setattr(reports_api, "generate", lambda: fixed)
    assert (await harness.post()).status_code == 201
    before = {t: await harness.count(t) for t in ("reports", "report_status_events", "data_keys")}
    clash = await harness.post()
    assert clash.status_code == 409
    assert {t: await harness.count(t) for t in before} == before
    assert fixed.canonical not in clash.text
    assert fixed.formatted not in clash.text


async def test_the_receipt_and_stored_rows_carry_no_identity(harness: Harness) -> None:
    response = await harness.post(
        headers={"X-Forwarded-For": "203.0.113.9", "User-Agent": "canary-agent/1.0"}
    )
    assert response.status_code == 201
    dump = json.dumps(
        [
            [str(cell) for cell in row]
            for table in ("reports", "report_status_events", "report_tracking_keys", "data_keys")
            for row in await harness.rows(f"SELECT * FROM app.{table}")
        ]
    )
    assert "203.0.113.9" not in dump
    assert "canary-agent" not in dump
    assert CLIENT not in dump


async def test_report_content_contacts_codes_and_file_names_never_reach_logs(
    harness: Harness,
) -> None:
    buffer = io.StringIO()
    configure_logging(service="svc", environment="test", level="DEBUG", stream=buffer)
    try:
        response = await harness.post(
            harness.fields(contact_channel="email", contact_value=CONTACT_CANARY),
            files=[("secret-site-photo.png", png(), "image/png")],
        )
        bad = await harness.post(harness.fields(description="too short"))
        assert (response.status_code, bad.status_code) == (201, 422)
        output = buffer.getvalue()
    finally:
        structlog.reset_defaults()
        logging.getLogger().handlers.clear()
    code = response.json()["tracking_code"]
    for private in (CANARY, CONTACT_CANARY, code, code.replace("-", ""), "secret-site-photo"):
        assert private not in output

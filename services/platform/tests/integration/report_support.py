"""Shared harness for the private-report endpoints: real public role, in-memory evidence store."""

import base64
import io
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import FastAPI
from PIL import Image
from sqlalchemy import LargeBinary, bindparam, text
from sqlalchemy.engine import URL

from shaidago.api.app import create_app
from shaidago.api.dependencies import Dependencies
from shaidago.files.pipeline import EvidencePipeline, PipelineParts
from shaidago.files.rules import FileLimits
from shaidago.files.scanner import EicarScanner
from shaidago.files.storage import InMemoryObjectStore
from shaidago.reports.tracking import lookup_key, normalise
from shaidago.shared.clock import ManualClock
from shaidago.shared.database import Database, build_engine
from shaidago.shared.ids import Uuid7Generator
from shaidago.shared.ratelimit import InMemoryRateLimiter
from tests.factories import CREDENTIAL, KEY_B, build_settings
from tests.integration.support import Plain

START = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
CANARY = "FICTIONAL canary: the fictional gate was locked all week."
CONTACT_CANARY = "fictional.reporter.canary@example.test"
CLIENT = "cc" * 32
CODE_SHAPE = re.compile(r"SG-[0-9A-Z]{5}(-[0-9A-Z]{5}){3}-[0-9A-Z]")
RECEIPT_KEYS = {
    "tracking_code",
    "status",
    "published",
    "contact_saved",
    "attachments",
    "next_steps",
}


def png() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (32, 32), "white").save(out, "PNG")
    return out.getvalue()


class Harness:
    def __init__(
        self, app: FastAPI, owner: Database, store: InMemoryObjectStore, slug: str
    ) -> None:
        self.app, self.owner, self.store, self.slug = app, owner, store, slug
        self.settings = build_settings()

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url="http://api.test",
            headers={
                "Authorization": f"Bearer web.{CREDENTIAL}",
                "X-Shaidago-Client-Hmac": CLIENT,
            },
        )

    def fields(self, **overrides: str | None) -> dict[str, str]:
        base: dict[str, str | None] = {
            "project_slug": self.slug,
            "concern_category": "no_visible_work",
            "description": CANARY,
        }
        base.update(overrides)
        return {k: v for k, v in base.items() if v is not None}

    async def post(
        self,
        fields: dict[str, str] | None = None,
        files: list[tuple[str, bytes, str]] | None = None,
        key: str | None = "",
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        parts: list[tuple[str, Any]] = [
            (k, (None, v)) for k, v in (fields or self.fields()).items()
        ]
        parts += [("attachments", (name, data, ctype)) for name, data, ctype in files or []]
        request_headers = dict(headers or {})
        if key is not None:
            request_headers["Idempotency-Key"] = key or str(uuid.uuid4())
        async with self.client() as client:
            return await client.post("/v1/reports", files=parts, headers=request_headers)

    async def rows(self, sql: str) -> list[Any]:
        async with Plain(self.owner.engine).unit_of_work() as session:
            return list((await session.execute(text(sql))).all())

    async def count(self, table: str) -> int:
        return int((await self.rows(f"SELECT count(*) FROM app.{table}"))[0][0])


def build(role_urls: dict[str, URL], engines: list[Any], **environ: str) -> tuple[FastAPI, Any]:
    clock = ManualClock(START)
    public = build_engine(
        role_urls["shaidago_public"], application_name="p", statement_timeout_ms=8000
    )
    engines.append(public)
    store = InMemoryObjectStore()
    pool = ThreadPoolExecutor(max_workers=2)
    pipeline = EvidencePipeline(
        PipelineParts(EicarScanner(), store, pool), limits=FileLimits(max_dimension=64)
    )
    app = create_app(
        build_settings(**environ),
        Dependencies(
            clock=clock,
            ids=Uuid7Generator(clock),
            public_database=Database(public),
            rate_limiter=InMemoryRateLimiter(clock),
            evidence_pipeline=pipeline,
        ),
    )
    return app, (store, pool)


async def report_id_for(harness: Harness, code: str) -> uuid.UUID:
    """The internal ID behind a tracking code, found the way the database would."""
    async with harness.owner.unit_of_work() as session:
        return uuid.UUID(
            str(
                (
                    await session.execute(
                        text(
                            "SELECT report_id FROM app.report_tracking_keys "
                            "WHERE lookup_hmac = :digest"
                        ).bindparams(bindparam("digest", type_=LargeBinary)),
                        {"digest": lookup_key(base64.b64decode(KEY_B), normalise(code))},
                    )
                ).scalar_one()
            )
        )


async def set_status(harness: Harness, code: str, new: str, message: str, at: datetime) -> None:
    """What a reviewer's transition writes: one event and the matching projection."""
    report_id = await report_id_for(harness, code)
    async with harness.owner.unit_of_work() as session:
        old = (
            await session.execute(
                text("SELECT status FROM app.reports WHERE id = :r"), {"r": report_id}
            )
        ).scalar_one()
        await session.execute(
            text(
                "INSERT INTO app.report_status_events (id, report_id, previous_status, new_status, "
                "public_message, actor_type, occurred_at) VALUES "
                "(gen_random_uuid(), :r, :old, :new, :m, 'reviewer', :at)"
            ),
            {"r": report_id, "old": old, "new": new, "m": message, "at": at},
        )
        await session.execute(
            text("UPDATE app.reports SET status = :new, status_updated_at = :at WHERE id = :r"),
            {"r": report_id, "new": new, "at": at},
        )


async def ask(harness: Harness, code: str, question: str, at: datetime) -> uuid.UUID:
    """A reviewer's follow-up question about the report behind ``code``."""
    report_id = await report_id_for(harness, code)
    question_id = uuid.uuid4()
    async with harness.owner.unit_of_work() as session:
        await session.execute(
            text(
                "INSERT INTO app.report_follow_up_questions (id, report_id, question, asked_at) "
                "VALUES (:id, :r, :q, :at)"
            ),
            {"id": question_id, "r": report_id, "q": question, "at": at},
        )
    return question_id

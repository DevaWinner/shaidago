"""Shared harness for reviewer endpoints: real reviewer and public roles, fictional reports."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.engine import URL

from shaidago.api.app import create_app
from shaidago.api.dependencies import Dependencies
from shaidago.api.reviewer_auth import session_service
from shaidago.auth.passwords import PasswordPolicy, PasswordVerifier
from shaidago.auth.reviewers import ReviewerRecord, ReviewerService, find_reviewer
from shaidago.auth.sessions import IssuedSession
from shaidago.files.pipeline import EvidencePipeline, PipelineParts
from shaidago.files.rules import FileLimits
from shaidago.files.scanner import EicarScanner
from shaidago.files.storage import InMemoryObjectStore
from shaidago.shared.clock import ManualClock
from shaidago.shared.database import Database, build_engine
from shaidago.shared.ids import Uuid7Generator
from shaidago.shared.ratelimit import InMemoryRateLimiter
from tests.factories import CREDENTIAL, build_settings
from tests.integration.report_support import CLIENT, START, Harness, png, report_id_for

FAST = PasswordVerifier(PasswordPolicy(time_cost=1, memory_cost_kib=1024, parallelism=1))
PASSWORD = "a-long-enough-reviewer-password"
SETTINGS = {"RATE_SUBMISSION_PER_HOUR": "1000"}
INTERNAL = {"Authorization": f"Bearer web.{CREDENTIAL}", "X-Shaidago-Client-Hmac": CLIENT}


class ReviewWorld:
    """One app serving both the public submission path and the reviewer routes."""

    def __init__(
        self, app: Any, owner: Database, store: InMemoryObjectStore, clock: ManualClock, slug: str
    ) -> None:
        self.app, self.owner, self.store, self.clock, self.slug = app, owner, store, clock, slug
        self.settings = build_settings(**SETTINGS)
        self.public = Harness(app, owner, store, slug)

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url="http://api.test",
            headers=INTERNAL,
        )

    async def submit(
        self,
        *,
        contact: bool = False,
        attachments: int = 0,
        description: str | None = None,
        category: str = "no_visible_work",
    ) -> tuple[str, uuid.UUID]:
        """A fictional report through the real public endpoint: (tracking code, report ID)."""
        fields = self.public.fields(concern_category=category)
        if description is not None:
            fields["description"] = description
        if contact:
            fields |= {
                "contact_channel": "email",
                "contact_value": "fictional.reporter.canary@example.test",
            }
        files = [(f"photo-{n}.png", png(), "image/png") for n in range(attachments)]
        response = await self.public.post(fields, files)
        assert response.status_code == 201, response.text
        code = response.json()["tracking_code"]
        return code, await report_id_for(self.public, code)

    async def reviewer(self, role: str = "reviewer", state: str = "active") -> ReviewerRecord:
        identifier = f"rev-{uuid.uuid4().hex[:10]}"
        async with self.owner.unit_of_work() as session:
            await ReviewerService(
                session,
                clock=self.clock,
                ids=Uuid7Generator(self.clock),
                passwords=FAST,
                deployed=False,
            ).create(identifier, PASSWORD, role)  # type: ignore[arg-type]
        async with self.owner.unit_of_work() as session:
            found = await find_reviewer(session, identifier)
        assert found is not None
        if state != "active":
            async with self.owner.unit_of_work() as session:
                await session.execute(
                    text("UPDATE app.reviewers SET state = :s WHERE id = :i"),
                    {"s": state, "i": found.id},
                )
        return found

    async def session(self, reviewer: ReviewerRecord) -> IssuedSession:
        async with self.owner.unit_of_work() as session:
            return await session_service(
                session,
                Dependencies(clock=self.clock, ids=Uuid7Generator(self.clock)),
                self.settings,
            ).issue(reviewer)

    async def signed_in(self, role: str = "reviewer") -> Actor:
        record = await self.reviewer(role)
        return Actor(record, await self.session(record))

    async def call(  # noqa: PLR0913 - a request names its parts
        self,
        actor: Actor | None,
        method: str,
        path: str,
        *,
        json: Any = None,
        csrf: bool = True,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        headers: dict[str, str] = {}
        if actor is not None:
            headers["X-Shaidago-Session"] = actor.issued.token
            if csrf:
                headers["X-Shaidago-Csrf"] = actor.issued.csrf_token
        async with self.client() as client:
            return await client.request(method, path, json=json, headers=headers, params=params)

    async def rows(self, sql: str, **parameters: Any) -> list[Any]:
        async with self.owner.unit_of_work() as session:
            return list((await session.execute(text(sql), parameters)).all())

    def advance(self, seconds: int) -> None:
        self.clock.advance(timedelta(seconds=seconds))


class Actor:
    def __init__(self, record: ReviewerRecord, issued: IssuedSession) -> None:
        self.record, self.issued = record, issued


def build_world(
    urls: dict[str, URL], engines: list[Any], slug: str
) -> tuple[ReviewWorld, ThreadPoolExecutor]:
    clock = ManualClock(START)
    owner = build_engine(urls["owner"], application_name="o", statement_timeout_ms=8000)
    public = build_engine(urls["shaidago_public"], application_name="p", statement_timeout_ms=8000)
    reviewer = build_engine(
        urls["shaidago_reviewer"], application_name="r", statement_timeout_ms=8000
    )
    engines += [owner, public, reviewer]
    store = InMemoryObjectStore()
    pool = ThreadPoolExecutor(max_workers=2)
    pipeline = EvidencePipeline(
        PipelineParts(EicarScanner(), store, pool), limits=FileLimits(max_dimension=64)
    )
    app = create_app(
        build_settings(**SETTINGS),
        Dependencies(
            clock=clock,
            ids=Uuid7Generator(clock),
            public_database=Database(public),
            reviewer_database=Database(reviewer),
            rate_limiter=InMemoryRateLimiter(clock),
            evidence_pipeline=pipeline,
            evidence_store=store,
        ),
    )
    return ReviewWorld(app, Database(owner), store, clock, slug), pool

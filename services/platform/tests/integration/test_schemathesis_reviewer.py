# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUntypedFunctionDecorator=false, reportUnknownParameterType=false
"""Property-based conformance of the reviewer API to its contract, with a valid reviewer session.

Every generated request carries a real session and CSRF token, so the fuzzer reaches the handlers
(not just the 401): malformed and boundary bodies, Unicode, unknown fields, wrong content types,
and invalid state commands, all against a real database with the reviewer role. Anything other than
a documented status, or any 5xx, fails.
"""

import asyncio
import uuid
from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any

import pytest
import schemathesis
from hypothesis import HealthCheck, settings
from schemathesis import Case
from schemathesis.specs.openapi.checks import negative_data_rejection, positive_data_acceptance
from sqlalchemy.engine import URL
from starlette.types import ASGIApp, Receive, Scope, Send

from shaidago.api.app import create_app
from shaidago.api.dependencies import Dependencies
from shaidago.api.reviewer_auth import session_service
from shaidago.auth.reviewers import ReviewerService, find_reviewer
from shaidago.files.storage import InMemoryObjectStore
from shaidago.shared.clock import ManualClock
from shaidago.shared.database import Database, build_engine
from shaidago.shared.ids import Uuid7Generator
from shaidago.shared.ratelimit import InMemoryRateLimiter
from tests.factories import CREDENTIAL, build_settings
from tests.integration.reviewer_support import FAST, PASSWORD, RecordingQueue

START = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)


class WithSession:
    """Test-only ASGI wrapper: the internal credential plus one reviewer's session and CSRF."""

    def __init__(self, app: ASGIApp, token: str, csrf: str) -> None:
        self._app, self._token, self._csrf = app, token, csrf

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            drop = {b"authorization", b"x-shaidago-session", b"x-shaidago-csrf"}
            headers = [(k, v) for k, v in scope["headers"] if k not in drop]
            headers += [
                (b"authorization", f"Bearer web.{CREDENTIAL}".encode()),
                (b"x-shaidago-session", self._token.encode()),
                (b"x-shaidago-csrf", self._csrf.encode()),
            ]
            scope = {**scope, "headers": headers}
        await self._app(scope, receive, send)


async def issue_session(
    owner_url: URL, config: Any, clock: ManualClock, ids: Uuid7Generator
) -> Any:
    """Create one administrator and a live session for it, in a short-lived engine."""
    owner = build_engine(owner_url, application_name="fuzz-setup", statement_timeout_ms=8000)
    try:
        identifier = f"fuzz-{uuid.uuid4().hex[:8]}"
        async with Database(owner).unit_of_work() as session:
            await ReviewerService(
                session, clock=clock, ids=ids, passwords=FAST, deployed=False
            ).create(identifier, PASSWORD, "admin")
        async with Database(owner).unit_of_work() as session:
            record = await find_reviewer(session, identifier)
        assert record is not None
        async with Database(owner).unit_of_work() as session:
            return await session_service(session, Dependencies(clock=clock, ids=ids), config).issue(
                record
            )
    finally:
        await owner.dispose()


@pytest.fixture(scope="module")
def reviewer_schema(role_urls: dict[str, URL]) -> Any:
    clock = ManualClock(START)
    ids = Uuid7Generator(clock)
    config = build_settings(
        RATE_REVIEWER_READ_PER_MINUTE="1000000",
        RATE_REVIEWER_WRITE_PER_MINUTE="1000000",
        RATE_DISCOVERY_REVIEWER_PER_HOUR="1000000",
        DOCS_ENABLED="true",
    )
    issued = asyncio.run(issue_session(role_urls["owner"], config, clock, ids))
    public = build_engine(
        role_urls["shaidago_public"], application_name="p", statement_timeout_ms=8000
    )
    reviewer = build_engine(
        role_urls["shaidago_reviewer"], application_name="r", statement_timeout_ms=8000
    )
    app = create_app(
        config,
        Dependencies(
            public_database=Database(public),
            reviewer_database=Database(reviewer),
            clock=clock,
            ids=ids,
            rate_limiter=InMemoryRateLimiter(clock),
            job_queue=RecordingQueue(),
            evidence_store=InMemoryObjectStore(),
        ),
    )
    return schemathesis.openapi.from_asgi(
        "/openapi.json", WithSession(app, issued.token, issued.csrf_token)
    )


schema = schemathesis.pytest.from_fixture("reviewer_schema")


@schema.include(path_regex=r"^/v1/reviewer").parametrize()
@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.data_too_large,
        HealthCheck.filter_too_much,
    ],
)
def test_reviewer_api_conforms_to_its_contract(case: Case[Any]) -> None:
    response = case.call()
    excluded = [positive_data_acceptance]
    if response.status_code == HTTPStatus.CONTENT_TOO_LARGE:
        excluded.append(negative_data_rejection)
    case.validate_response(response, excluded_checks=excluded)  # pyright: ignore[reportArgumentType]

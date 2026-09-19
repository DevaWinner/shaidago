# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUntypedFunctionDecorator=false, reportUnknownParameterType=false
# Schemathesis ships loosely typed decorators and check helpers; the rest of this file is strict.
"""Property-based conformance of the public API to its own OpenAPI contract.

Schemathesis generates malformed cursors, unknown filters, oversized and Unicode values, and
checks status codes, content types, and response bodies against the schema. The API runs against
the seeded synthetic catalogue in a real database as the restricted public role.
"""

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
from shaidago.retrieval.language import QA_FIXTURES_ROOT, FixtureLanguageModel
from shaidago.shared.clock import ManualClock
from shaidago.shared.database import Database, build_engine
from shaidago.shared.ratelimit import InMemoryRateLimiter
from tests.factories import CREDENTIAL, build_settings
from tests.integration.public_catalogue import PUBLISH_AT, Seed
from tests.integration.reviewer_support import RecordingQueue


class WithCredential:
    """Test-only ASGI wrapper: every generated request carries the internal credential."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = [(k, v) for k, v in scope["headers"] if k != b"authorization"]
            headers.append((b"authorization", f"Bearer web.{CREDENTIAL}".encode()))
            scope = {**scope, "headers": headers}
        await self._app(scope, receive, send)


@pytest.fixture(scope="module")
def api_schema(role_urls: dict[str, URL], seed: Seed) -> Any:
    del seed
    public = build_engine(
        role_urls["shaidago_public"], application_name="fuzz", statement_timeout_ms=8000
    )
    reviewer = build_engine(
        role_urls["shaidago_reviewer"], application_name="fuzz-reviewer", statement_timeout_ms=8000
    )
    clock = ManualClock(PUBLISH_AT)
    app = create_app(
        build_settings(DOCS_ENABLED="true"),
        Dependencies(
            public_database=Database(public),
            reviewer_database=Database(reviewer),
            clock=clock,
            rate_limiter=InMemoryRateLimiter(clock),
            language_model=FixtureLanguageModel.from_path(QA_FIXTURES_ROOT / "grounded-qa-v1.json"),
            job_queue=RecordingQueue(),
        ),
    )
    return schemathesis.openapi.from_asgi("/openapi.json", WithCredential(app))


schema = schemathesis.pytest.from_fixture("api_schema")


@schema.parametrize()
@settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.data_too_large,
        HealthCheck.filter_too_much,
    ],
)
def test_public_api_conforms_to_its_contract(case: Case[Any]) -> None:
    # The cursor is an opaque signed token, so an arbitrary well-formed string is rightly rejected
    # with the documented 400; positive-data acceptance is covered by test_public_api.py instead.
    # A body over the size cap is deliberately answered 413, which the generic "invalid data must
    # be rejected" check does not list, so it is exempt from that one check only.
    response = case.call()
    excluded = [positive_data_acceptance]
    if response.status_code == HTTPStatus.CONTENT_TOO_LARGE:
        excluded.append(negative_data_rejection)
    case.validate_response(response, excluded_checks=excluded)  # pyright: ignore[reportArgumentType]

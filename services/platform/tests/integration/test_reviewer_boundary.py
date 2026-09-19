"""The reviewer boundary: internal credential is not reviewer authority; CSRF binds mutations."""

import io
import json
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import pytest
import structlog
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import URL

from shaidago.api.app import create_app
from shaidago.api.dependencies import Dependencies
from shaidago.api.reviewer_auth import (
    AuthenticatedReviewer,
    authenticated_reviewer,
    require,
    session_service,
)
from shaidago.auth.passwords import PasswordPolicy, PasswordVerifier
from shaidago.auth.policy import Capability, is_allowed
from shaidago.auth.reviewers import ReviewerRecord, ReviewerService, find_reviewer
from shaidago.auth.sessions import IssuedSession
from shaidago.shared.clock import ManualClock
from shaidago.shared.database import Database, build_engine
from shaidago.shared.ids import Uuid7Generator
from shaidago.shared.logging import configure_logging
from tests.factories import CREDENTIAL, build_settings

INTERNAL = {"Authorization": f"Bearer web.{CREDENTIAL}"}
START = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
FAST = PasswordVerifier(PasswordPolicy(time_cost=1, memory_cost_kib=1024, parallelism=1))
PASSWORD = "a-long-enough-reviewer-password"


class World:
    """One app, one clock, and helpers to create reviewers and sessions."""

    def __init__(
        self, owner: Database, app_db: Database, clock: ManualClock, client: TestClient
    ) -> None:
        self.owner, self.app_db, self.clock, self.client = owner, app_db, clock, client
        self.settings = build_settings()

    async def reviewer(self, role: str = "reviewer") -> ReviewerRecord:
        identifier = f"bnd-{uuid.uuid4().hex[:10]}"
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
        return found

    async def session(self, reviewer: ReviewerRecord) -> IssuedSession:
        async with self.owner.unit_of_work() as session:
            return await session_service(
                session,
                Dependencies(clock=self.clock, ids=Uuid7Generator(self.clock)),
                self.settings,
            ).issue(reviewer)


@pytest.fixture
async def world(role_urls: dict[str, URL]) -> AsyncIterator[World]:
    owner_engine = build_engine(role_urls["owner"], application_name="o", statement_timeout_ms=8000)
    reviewer_engine = build_engine(
        role_urls["shaidago_reviewer"], application_name="r", statement_timeout_ms=8000
    )
    clock = ManualClock(START)
    reviewer_db = Database(reviewer_engine)
    app = create_app(
        build_settings(),
        Dependencies(clock=clock, ids=Uuid7Generator(clock), reviewer_database=reviewer_db),
    )
    router = APIRouter()

    @router.get("/v1/probe/reviewer")
    def read(
        who: Annotated[AuthenticatedReviewer, Depends(authenticated_reviewer)],
    ) -> dict[str, str]:
        return {"role": who.principal.role}

    @router.post("/v1/probe/reviewer")
    def write(
        who: Annotated[AuthenticatedReviewer, Depends(authenticated_reviewer)],
    ) -> dict[str, str]:
        return {"role": who.principal.role}

    app.include_router(router)
    with TestClient(app, headers=INTERNAL) as client:
        yield World(Database(owner_engine), reviewer_db, clock, client)
    await owner_engine.dispose()
    await reviewer_engine.dispose()


def hdr(issued: IssuedSession, *, csrf: bool = True) -> dict[str, str]:
    headers = {"X-Shaidago-Session": issued.token}
    return headers | ({"X-Shaidago-Csrf": issued.csrf_token} if csrf else {})


def body_without_id(response_json: dict[str, object]) -> dict[str, object]:
    return {k: v for k, v in response_json.items() if k != "request_id"}


async def test_a_valid_session_reads_without_csrf_and_writes_with_it(world: World) -> None:
    issued = await world.session(await world.reviewer("admin"))
    assert world.client.get("/v1/probe/reviewer", headers=hdr(issued, csrf=False)).json() == {
        "role": "admin"
    }
    assert world.client.post("/v1/probe/reviewer", headers=hdr(issued)).status_code == 200


async def test_the_internal_credential_alone_is_never_reviewer_authority(world: World) -> None:
    for method in ("get", "post"):
        response = getattr(world.client, method)("/v1/probe/reviewer")
        assert response.status_code == 401
        assert response.json()["code"] == "unauthenticated"


async def test_a_session_without_the_internal_credential_never_reaches_the_route(
    world: World,
) -> None:
    issued = await world.session(await world.reviewer())
    response = world.client.get(
        "/v1/probe/reviewer", headers=hdr(issued, csrf=False) | {"Authorization": ""}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"
    assert response.headers["www-authenticate"] == "Bearer", "denied by the internal boundary"


async def test_every_way_of_lacking_a_valid_session_gets_one_generic_response(world: World) -> None:
    active = await world.reviewer()
    revoked = await world.session(await world.reviewer())
    async with world.owner.unit_of_work() as session:
        await session_service(
            session,
            Dependencies(clock=world.clock, ids=Uuid7Generator(world.clock)),
            world.settings,
        ).revoke_token(revoked.token)
    disabled_reviewer = await world.reviewer()
    disabled = await world.session(disabled_reviewer)
    async with world.owner.unit_of_work() as session:
        await ReviewerService(
            session,
            clock=world.clock,
            ids=Uuid7Generator(world.clock),
            passwords=FAST,
            deployed=False,
        ).disable(disabled_reviewer.id)
    expired = await world.session(active)
    unknown = {"X-Shaidago-Session": "u" * 43}
    world.clock.advance(timedelta(hours=9))
    cases: list[Any] = [
        {},
        {"X-Shaidago-Session": ""},
        unknown,
        hdr(revoked, csrf=False),
        hdr(disabled, csrf=False),
        hdr(expired, csrf=False),
        [(b"x-shaidago-session", ("é" * 5).encode())],  # raw non-ASCII header bytes
    ]
    responses = [world.client.get("/v1/probe/reviewer", headers=h) for h in cases]
    assert {r.status_code for r in responses} == {401}
    bodies = [body_without_id(r.json()) for r in responses]
    assert all(body == bodies[0] for body in bodies)


async def test_mutations_need_the_csrf_token_of_this_session(world: World) -> None:
    mine = await world.session(await world.reviewer())
    theirs = await world.session(await world.reviewer())
    cases: list[Any] = [
        hdr(mine, csrf=False),
        hdr(mine) | {"X-Shaidago-Csrf": ""},
        hdr(mine) | {"X-Shaidago-Csrf": theirs.csrf_token},
        hdr(mine) | {"X-Shaidago-Csrf": mine.csrf_token[:-1] + "_"},
        [(b"x-shaidago-session", mine.token.encode()), (b"x-shaidago-csrf", ("é" * 40).encode())],
        hdr(mine) | {"X-Shaidago-Csrf": mine.token},
    ]
    responses = [world.client.post("/v1/probe/reviewer", headers=h) for h in cases]
    assert {r.status_code for r in responses} == {403}
    assert {r.json()["code"] for r in responses} == {"csrf_invalid"}
    assert len({json.dumps(body_without_id(r.json()), sort_keys=True) for r in responses}) == 1
    assert world.client.post("/v1/probe/reviewer", headers=hdr(mine)).status_code == 200


async def test_csrf_is_checked_only_after_the_session_so_an_anonymous_caller_learns_nothing(
    world: World,
) -> None:
    response = world.client.post("/v1/probe/reviewer", headers={"X-Shaidago-Csrf": "anything"})
    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"


async def test_a_session_in_a_cookie_or_query_string_is_ignored(world: World) -> None:
    issued = await world.session(await world.reviewer())
    by_cookie = world.client.get(
        "/v1/probe/reviewer", headers={"Cookie": f"sg_session={issued.token}"}
    )
    by_query = world.client.get("/v1/probe/reviewer", params={"session": issued.token})
    assert by_cookie.status_code == by_query.status_code == 401


async def test_tokens_never_reach_logs_or_error_bodies(world: World) -> None:
    buffer = io.StringIO()
    configure_logging(service="svc", environment="test", level="DEBUG", stream=buffer)
    try:
        issued = await world.session(await world.reviewer())
        world.client.post("/v1/probe/reviewer", headers=hdr(issued, csrf=False))  # csrf failure
        world.client.get("/v1/probe/reviewer", headers={"X-Shaidago-Session": issued.token + "x"})
        world.client.get("/v1/probe/reviewer", headers=hdr(issued, csrf=False))
        output = buffer.getvalue()
    finally:
        structlog.reset_defaults()
        logging.getLogger().handlers.clear()
    assert issued.token not in output
    assert issued.csrf_token not in output
    assert "x-shaidago-session" not in output.lower()


async def test_reviewer_routes_report_unavailable_when_no_reviewer_database_is_configured() -> None:
    app = create_app(build_settings(), Dependencies())
    router = APIRouter()

    @router.get("/v1/probe/reviewer")
    def read(who: Annotated[AuthenticatedReviewer, Depends(authenticated_reviewer)]) -> str:
        return who.principal.role

    app.include_router(router)
    response = TestClient(app, headers=INTERNAL).get(
        "/v1/probe/reviewer", headers={"X-Shaidago-Session": "t"}
    )
    assert response.status_code == 503
    assert response.json()["code"] == "dependency_unavailable"


async def test_capabilities_are_enforced_per_role_through_the_api(world: World) -> None:
    router = APIRouter()
    for capability in Capability:

        def make(cap: Capability = capability) -> None:
            @router.post(f"/v1/probe/cap/{cap.value}")
            def route(_who: Annotated[AuthenticatedReviewer, Depends(require(cap))]) -> str:
                return cap.value

        make()
    world.client.app.include_router(router)  # type: ignore[attr-defined]
    admin = await world.session(await world.reviewer("admin"))
    reviewer = await world.session(await world.reviewer("reviewer"))
    for capability in Capability:
        path = f"/v1/probe/cap/{capability.value}"
        assert world.client.post(path, headers=hdr(admin)).status_code == 200
        expected = 200 if is_allowed("reviewer", capability) else 403
        assert world.client.post(path, headers=hdr(reviewer)).status_code == expected
    denied = [
        world.client.post(f"/v1/probe/cap/{c.value}", headers=hdr(reviewer))
        for c in Capability
        if not is_allowed("reviewer", c)
    ]
    assert len({json.dumps(body_without_id(r.json()), sort_keys=True) for r in denied}) == 1
    assert denied[0].json()["code"] == "forbidden"


async def test_unauthenticated_and_forbidden_are_distinct_but_both_generic(world: World) -> None:
    world.client.app.include_router(_one_admin_route())  # type: ignore[attr-defined]
    reviewer = await world.session(await world.reviewer("reviewer"))
    anonymous = world.client.post("/v1/probe/admin", headers={})
    forbidden = world.client.post("/v1/probe/admin", headers=hdr(reviewer))
    assert (anonymous.status_code, anonymous.json()["code"]) == (401, "unauthenticated")
    assert (forbidden.status_code, forbidden.json()["code"]) == (403, "forbidden")


async def test_a_downgraded_admin_loses_access_on_the_next_request(world: World) -> None:
    world.client.app.include_router(_one_admin_route())  # type: ignore[attr-defined]
    admin = await world.reviewer("admin")
    issued = await world.session(admin)
    assert world.client.post("/v1/probe/admin", headers=hdr(issued)).status_code == 200
    async with world.owner.unit_of_work() as session:
        await session.execute(
            text("UPDATE app.reviewers SET role = 'reviewer' WHERE id = :i"), {"i": admin.id}
        )
    downgraded = world.client.post("/v1/probe/admin", headers=hdr(issued))
    assert downgraded.status_code == 401, "a privilege change forces a fresh sign-in"


def _one_admin_route() -> APIRouter:
    router = APIRouter()

    @router.post("/v1/probe/admin")
    def admin_only(
        _who: Annotated[AuthenticatedReviewer, Depends(require(Capability.REVIEWER_ADMIN))],
    ) -> str:
        return "ok"

    return router

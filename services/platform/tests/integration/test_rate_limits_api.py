"""Rate limits over HTTP: reviewer budgets, the shared Q&A budget, and fail-closed behaviour."""

import uuid
from dataclasses import replace
from datetime import timedelta

from shaidago.shared.ratelimit import RateDecision, RateLimitUnavailableError
from tests.factories import build_settings
from tests.integration.reviewer_support import SETTINGS, ReviewWorld


class BrokenLimiter:
    async def hit(self, key: str, *, limit: int, window_seconds: int) -> RateDecision:
        del key, limit, window_seconds
        raise RateLimitUnavailableError


def tighten(world: ReviewWorld, **environ: str) -> None:
    world.app.state.settings = build_settings(**(SETTINGS | environ))


async def test_a_reviewer_has_separate_read_and_write_budgets_that_reset(
    review_world: ReviewWorld,
) -> None:
    tighten(review_world, RATE_REVIEWER_WRITE_PER_MINUTE="3", RATE_REVIEWER_READ_PER_MINUTE="5")
    _, report_id = await review_world.submit()
    actor = await review_world.signed_in()
    other = await review_world.signed_in()
    url = f"/v1/reviewer/reports/{report_id}/notes"
    writes = [
        (
            await review_world.call(actor, "POST", url, json={"body": f"FICTIONAL note {n}"})
        ).status_code
        for n in range(4)
    ]
    assert writes == [201, 201, 201, 429]
    blocked = await review_world.call(actor, "POST", url, json={"body": "FICTIONAL note again"})
    assert blocked.json()["code"] == "rate_limited"
    assert 1 <= int(blocked.headers["retry-after"]) <= 60
    assert (
        await review_world.call(other, "POST", url, json={"body": "FICTIONAL other reviewer"})
    ).status_code == 201
    reads = [(await review_world.call(actor, "GET", url)).status_code for _ in range(6)]
    assert reads == [200] * 5 + [429]
    review_world.clock.advance(timedelta(seconds=61))
    assert (
        await review_world.call(actor, "POST", url, json={"body": "FICTIONAL after reset"})
    ).status_code == 201


async def test_the_shared_qa_budget_bounds_the_total_however_many_clients_ask(
    review_world: ReviewWorld,
) -> None:
    tighten(review_world, RATE_QA_GLOBAL_PER_HOUR="2")
    statuses: list[int] = []
    for n in range(4):
        async with review_world.client() as http:
            response = await http.post(
                f"/v1/projects/{review_world.slug}/questions",
                json={"question": "When did the clinic open?"},
                headers={"X-Shaidago-Client-Hmac": f"{n:064x}"},
            )
        statuses.append(response.status_code)
    assert statuses[2:] == [429, 429]
    assert 429 not in statuses[:2]


async def test_when_redis_is_down_protected_routes_fail_closed_and_change_nothing(
    review_world: ReviewWorld,
) -> None:
    actor = await review_world.signed_in()
    _, report_id = await review_world.submit()
    reports_before = (await review_world.rows("SELECT count(*) AS n FROM app.reports"))[0].n
    runs_before = (await review_world.rows("SELECT count(*) AS n FROM app.discovery_runs"))[0].n
    working = review_world.app.state.dependencies
    review_world.app.state.dependencies = replace(working, rate_limiter=BrokenLimiter())
    try:
        fields = review_world.public.fields()
        submit = await review_world.public.post(fields)
        async with review_world.client() as http:
            tracking = await http.post(
                "/v1/report-status:lookup", json={"code": "SG-AAAAA-BBBBB-CCCCC-DDDDD-E"}
            )
            sign_in = await http.post(
                "/v1/auth/sessions",
                json={"identifier": "someone", "password": "not-a-real-password"},
            )
            discovery = await http.post(f"/v1/projects/{review_world.slug}/discovery-runs")
            question = await http.post(
                f"/v1/projects/{review_world.slug}/questions",
                json={"question": "When did it open?"},
            )
        queue = await review_world.call(actor, "GET", "/v1/reviewer/reports")
        note = await review_world.call(
            actor,
            "POST",
            f"/v1/reviewer/reports/{report_id}/notes",
            json={"body": "FICTIONAL note"},
        )
    finally:
        review_world.app.state.dependencies = working
    for response in (submit, tracking, sign_in, discovery, question, queue, note):
        assert response.status_code == 503, response.text
        assert response.json()["code"] == "dependency_unavailable"
        assert "no-store" in response.headers["cache-control"]
    assert (await review_world.rows("SELECT count(*) AS n FROM app.reports"))[0].n == reports_before
    assert (await review_world.rows("SELECT count(*) AS n FROM app.discovery_runs"))[
        0
    ].n == runs_before
    assert not await review_world.rows(
        "SELECT 1 FROM app.report_notes WHERE report_id = :r", r=report_id
    )
    recovered = await review_world.call(
        actor, "GET", "/v1/reviewer/reports"
    )  # reconnects on its own
    assert recovered.status_code == 200
    assert uuid.UUID(int=0) != report_id

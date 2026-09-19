"""Discovery run APIs (BE-096): shared public runs, exact reviewer approval, decisions, isolation."""

import uuid
from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from shaidago.discovery.dispositions import COMMANDS, DECISIONS
from shaidago.shared.database import Database
from tests.integration.reviewer_support import Actor, ReviewWorld
from tests.integration.support import insert_project

RUNS = "/v1/discovery-runs"


@pytest.fixture(autouse=True)
def own_lagos_day(review_world: ReviewWorld) -> None:
    """The daily budget is global, so each test gets a Lagos day nobody else has used."""
    review_world.clock.advance(timedelta(days=100 + uuid.uuid4().int % 20000))


STATES = ("not_reviewed", "attached", "rejected", "deferred")


async def start(world: ReviewWorld, slug: str | None = None, client: str | None = None) -> Any:
    headers = {"X-Shaidago-Client-Hmac": client} if client else {}
    async with world.client() as http:
        return await http.post(f"/v1/projects/{slug or world.slug}/discovery-runs", headers=headers)


async def get_public(world: ReviewWorld, run_id: Any, **params: Any) -> Any:
    async with world.client() as http:
        return await http.get(f"{RUNS}/{run_id}", params=params)


async def new_project(world: ReviewWorld) -> str:
    slug = f"synthetic-{uuid.uuid4().hex[:10]}"
    async with world.owner.unit_of_work() as session:
        await insert_project(session, slug=slug)
    return slug


async def set_run(world: ReviewWorld, run_id: Any, **columns: Any) -> None:
    """Fictional setup as the owner, with the transition guard off so any state can be staged."""
    assignments = ", ".join(f"{name} = :{name}" for name in columns)
    async with world.owner.unit_of_work() as session:
        await session.execute(
            text("ALTER TABLE app.discovery_runs DISABLE TRIGGER discovery_runs_guard")
        )
        await session.execute(
            text(f"UPDATE app.discovery_runs SET {assignments} WHERE id = :run"),
            {**columns, "run": run_id},
        )
        await session.execute(
            text("ALTER TABLE app.discovery_runs ENABLE TRIGGER discovery_runs_guard")
        )


async def add_source(
    world: ReviewWorld,
    run_id: Any,
    *,
    scope: str = "public",
    report_id: Any = None,
    url: str | None = None,
    **extra: Any,
) -> uuid.UUID:
    source_id = uuid.uuid4()
    [project] = await world.rows(
        "SELECT project_id FROM app.discovery_runs WHERE id = :r", r=run_id
    )
    url = url or f"https://works.example.gov.ng/{source_id}"
    async with world.owner.unit_of_work() as session:
        await session.execute(
            text(
                "INSERT INTO app.discovered_sources (id, scope, project_id, report_id, canonical_url, publisher_domain, "
                "title, preliminary_type, published_provenance, date_conflict, content_type, excerpt, text_sha256, "
                "simhash, extraction_version, injection_flag, availability, first_discovered_at, last_retrieved_at, "
                "created_at, updated_at) VALUES (:id, :scope, :p, :rep, :url, 'works.example.gov.ng', 'A page', "
                "'government_publication', 'none', false, 'text/html', 'The clinic opened.', :sha, :hash, 'extract-v1', "
                ":inj, 'available', now(), now(), now(), now())"
            ),
            {
                "id": source_id,
                "scope": scope,
                "p": project.project_id,
                "rep": report_id,
                "url": url,
                "sha": uuid.uuid4().hex * 2,
                "hash": source_id.int % 1000,
                "inj": extra.get("injection", False),
            },
        )
        await session.execute(
            text(
                "INSERT INTO app.discovered_source_sightings VALUES (gen_random_uuid(), :s, :r, now(), now())"
            ),
            {"s": source_id, "r": run_id},
        )
    return source_id


# ---- public runs ------------------------------------------------------------------------------


async def test_a_public_run_is_created_once_shared_and_queued_by_id_only(
    review_world: ReviewWorld,
) -> None:
    first = await start(review_world)
    assert first.status_code == 200, first.text
    body = first.json()
    assert (body["action"], body["status"], body["demo_replay"]) == ("create", "queued", True)
    assert body["label"] == "discovered — not yet reviewed"
    assert first.headers["cache-control"] == "no-store"
    again = await start(review_world, client="dd" * 32)
    assert again.json()["action"] == "reuse_fresh"
    assert again.json()["run_id"] == body["run_id"]
    assert review_world.queue.run_ids == [uuid.UUID(body["run_id"])]
    [row] = await review_world.rows(
        "SELECT scope, report_id, provider_mode, query_text FROM app.discovery_runs WHERE id = :r",
        r=uuid.UUID(body["run_id"]),
    )
    assert (row.scope, row.report_id) == ("public", None)
    assert row.query_text == "synthetic title Synthetic Council health"


async def test_an_unknown_project_and_a_bad_rate_are_refused(review_world: ReviewWorld) -> None:
    missing = await start(review_world, slug="no-such-project")
    assert (missing.status_code, missing.json()["code"]) == (404, "not_found")
    limited = None
    for _ in range(7):
        limited = await start(review_world, client="ee" * 32)
    assert limited is not None
    assert (limited.status_code, limited.json()["code"]) == (429, "rate_limited")
    assert "retry-after" in limited.headers


async def test_the_daily_budget_shows_the_latest_completed_run_or_says_unavailable(
    review_world: ReviewWorld,
) -> None:
    old = (await start(review_world)).json()["run_id"]
    await set_run(
        review_world, uuid.UUID(old), status="complete", finished_at=review_world.clock.now()
    )
    review_world.clock.advance(timedelta(hours=26))  # a new Lagos day: the earlier run is stale
    for _ in range(3):
        created = await start(review_world, slug=await new_project(review_world))
        assert created.json()["action"] == "create"
    exhausted = await start(review_world)
    assert (exhausted.json()["action"], exhausted.json()["run_id"]) == (
        "show_latest_completed",
        old,
    )
    nothing = await start(review_world, slug=await new_project(review_world))
    assert (nothing.json()["action"], nothing.json()["run_id"]) == ("unavailable", None)


async def test_a_queued_run_whose_job_was_lost_is_re_enqueued_by_the_next_request(
    review_world: ReviewWorld,
) -> None:
    run_id = uuid.UUID((await start(review_world)).json()["run_id"])
    assert (await start(review_world, client="ff" * 32)).json()["action"] == "reuse_fresh"
    assert review_world.queue.run_ids == [run_id]
    review_world.clock.advance(timedelta(minutes=5))
    await start(review_world, client="ab" * 32)
    assert review_world.queue.run_ids == [run_id, run_id]  # harmless: delivery is idempotent


async def test_polling_shows_progress_and_only_a_complete_run_shows_a_result(
    review_world: ReviewWorld,
) -> None:
    run_id = uuid.UUID((await start(review_world)).json()["run_id"])
    queued = (await get_public(review_world, run_id)).json()
    assert (queued["status"], queued["result"], queued["sources"]) == ("queued", None, [])
    assert set(queued["progress"]) == {"results_found", "fetched", "analysed"}
    await set_run(
        review_world, run_id, status="searching", results_found=3, fetched_count=1, version=2
    )
    await add_source(review_world, run_id)
    running = (await get_public(review_world, run_id)).json()
    assert (running["status"], running["progress"]["fetched"], len(running["sources"])) == (
        "searching",
        1,
        1,
    )
    assert running["sources"][0]["label"] == "discovered — not yet reviewed"
    assert running["result"] is None
    unchanged = await get_public(review_world, run_id, since_version=running["version"])
    assert (unchanged.status_code, unchanged.content) == (304, b"")
    assert (
        await get_public(review_world, run_id, since_version=running["version"] - 1)
    ).status_code == 200
    await set_run(
        review_world, run_id, status="complete", analysis='{"label": "x", "status": "complete"}'
    )
    done = (await get_public(review_world, run_id)).json()
    assert done["result"]["status"] == "complete"
    assert (await get_public(review_world, run_id, since_version="x")).status_code == 422
    assert (await get_public(review_world, run_id, other=1)).status_code == 422
    assert (await get_public(review_world, uuid.uuid4())).status_code == 404


async def test_public_reads_hide_flagged_duplicate_and_rejected_sources(
    review_world: ReviewWorld,
) -> None:
    run_id = uuid.UUID((await start(review_world)).json()["run_id"])
    visible = await add_source(review_world, run_id)
    await add_source(review_world, run_id, injection=True)
    rejected = await add_source(review_world, run_id)
    actor = await review_world.signed_in()
    assert (await decide(review_world, actor, rejected, "reject")).status_code == 200
    duplicate = await add_source(review_world, run_id)
    async with review_world.owner.unit_of_work() as session:
        await session.execute(
            text(
                "UPDATE app.discovered_sources SET duplicate_of = :o, duplicate_kind = 'same_content' WHERE id = :d"
            ),
            {"o": visible, "d": duplicate},
        )
    shown = (await get_public(review_world, run_id)).json()["sources"]
    assert [s["source_id"] for s in shown] == [str(visible)]
    assert "injection" not in str(shown)


# ---- reviewer runs and isolation --------------------------------------------------------------


async def reviewer_report(world: ReviewWorld) -> tuple[Actor, uuid.UUID]:
    _, report_id = await world.submit(
        contact=True,
        description="FICTIONAL private text: the fictional supervisor demanded a fictional payment.",
    )
    return await world.signed_in(), report_id


def plan_path(report_id: uuid.UUID) -> str:
    return f"/v1/reviewer/reports/{report_id}/discovery-runs"


async def test_the_reviewer_sees_the_exact_query_with_provenance_and_exclusions(
    review_world: ReviewWorld,
) -> None:
    actor, report_id = await reviewer_report(review_world)
    canaries = [
        "fictional.reporter.canary@example.test",
        "the fictional supervisor",
        "08012345678",
        "SG-ABCDE-FGHJK-MNPQR-STVWX-2",
        "Delayed construction",
        "unfinished",
    ]
    response = await review_world.call(
        actor, "POST", f"{plan_path(report_id)}:plan", json={"concepts": canaries}
    )
    assert response.status_code == 200, response.text
    plan = response.json()
    assert plan["query"].startswith("synthetic title")
    concepts = [t for t in plan["terms"] if t["source"] == "incident_concept"]
    assert [(t["text"], t["suggested_by"]) for t in concepts] == [
        ("delayed construction", "ai_suggestion"),
        ("unfinished", "ai_suggestion"),
    ]
    assert {r["reason"] for r in plan["rejected"]} >= {
        "email",
        "not_in_vocabulary",
        "phone_or_identifier",
    }
    everything = response.text
    for private in ("canary@example", "supervisor", "08012345678", "ABCDE", "FICTIONAL private"):
        assert private not in everything
    assert response.headers["cache-control"] == "no-store"


async def test_a_run_needs_the_exact_approved_query_and_is_queued_by_id_only(
    review_world: ReviewWorld,
) -> None:
    actor, report_id = await reviewer_report(review_world)
    plan = (
        await review_world.call(
            actor, "POST", f"{plan_path(report_id)}:plan", json={"concepts": ["delayed"]}
        )
    ).json()
    stale = await review_world.call(
        actor,
        "POST",
        plan_path(report_id),
        json={"concepts": ["delayed", "road"], "approved_digest": plan["plan_digest"]},
    )
    assert (stale.status_code, stale.json()["code"]) == (409, "query_changed")
    assert review_world.queue.run_ids == []
    created = await review_world.call(
        actor,
        "POST",
        plan_path(report_id),
        json={"concepts": ["delayed"], "approved_digest": plan["plan_digest"]},
    )
    assert created.status_code == 201, created.text
    run_id = uuid.UUID(created.json()["run_id"])
    assert review_world.queue.run_ids == [run_id]
    [row] = await review_world.rows(
        "SELECT scope, report_id, query_text, query_policy_version, query_approved_by, requested_by FROM app.discovery_runs WHERE id = :r",
        r=run_id,
    )
    assert (row.scope, row.report_id, row.query_text) == ("report", report_id, plan["query"])
    assert row.query_approved_by == row.requested_by == actor.record.id
    [audit] = await review_world.rows(
        "SELECT details FROM app.audit_events WHERE event = 'discovery_run_created' AND subject_id = :r",
        r=run_id,
    )
    assert plan["query"] not in str(audit.details)


async def test_reviewer_run_creation_is_rate_limited_and_needs_a_session_and_csrf(
    review_world: ReviewWorld,
) -> None:
    actor, report_id = await reviewer_report(review_world)
    plan = (
        await review_world.call(
            actor, "POST", f"{plan_path(report_id)}:plan", json={"concepts": []}
        )
    ).json()
    body: dict[str, Any] = {"concepts": [], "approved_digest": plan["plan_digest"]}
    assert (
        await review_world.call(None, "POST", plan_path(report_id), json=body)
    ).status_code == 401
    assert (
        await review_world.call(actor, "POST", plan_path(report_id), json=body, csrf=False)
    ).status_code == 403
    assert (
        await review_world.call(
            actor, "POST", f"{plan_path(uuid.uuid4())}:plan", json={"concepts": []}
        )
    ).status_code == 404
    codes = [
        (await review_world.call(actor, "POST", plan_path(report_id), json=body)).status_code
        for _ in range(4)
    ]
    assert codes == [201, 201, 201, 429]


async def test_a_report_run_is_invisible_to_every_public_path(review_world: ReviewWorld) -> None:
    actor, report_id = await reviewer_report(review_world)
    plan = (
        await review_world.call(
            actor, "POST", f"{plan_path(report_id)}:plan", json={"concepts": []}
        )
    ).json()
    run_id = uuid.UUID(
        (
            await review_world.call(
                actor,
                "POST",
                plan_path(report_id),
                json={"concepts": [], "approved_digest": plan["plan_digest"]},
            )
        ).json()["run_id"]
    )
    await add_source(review_world, run_id, scope="report", report_id=report_id)
    assert (await get_public(review_world, run_id)).status_code == 404
    public_rows = await review_world.rows(
        "SELECT count(*) AS n FROM public_api.discovery_run_sources WHERE run_id = :r", r=run_id
    )
    assert public_rows[0].n == 0
    reviewer_view = await review_world.call(actor, "GET", f"/v1/reviewer/discovery-runs/{run_id}")
    assert reviewer_view.status_code == 200
    body: dict[str, Any] = reviewer_view.json()
    assert (body["scope"], body["report_id"], body["query_text"]) == (
        "report",
        str(report_id),
        plan["query"],
    )
    assert len(body["sources"]) == 1
    public = review_world.app.state.dependencies.public_database.engine
    for table in ("discovery_runs", "discovered_sources", "discovered_source_sightings"):
        async with public.connect() as connection:
            with pytest.raises(ProgrammingError, match="permission denied"):
                await connection.execute(text(f"SELECT 1 FROM app.{table}"))


async def test_a_public_caller_cannot_cancel_answer_or_decide(review_world: ReviewWorld) -> None:
    run_id = uuid.UUID((await start(review_world)).json()["run_id"])
    source = await add_source(review_world, run_id)
    async with review_world.client() as http:
        for method, path in (
            ("post", f"{RUNS}/{run_id}:cancel"),
            ("post", f"{RUNS}/{run_id}/follow-up-answers"),
            ("post", f"/v1/reviewer/discovered-sources/{source}/decision"),
            ("post", f"/v1/reviewer/discovery-runs/{run_id}:cancel"),
            ("get", f"/v1/reviewer/discovery-runs/{run_id}"),
        ):
            response = await getattr(http, method)(path)
            assert response.status_code in {401, 404, 405}, path


# ---- cancel, review, answers ------------------------------------------------------------------


async def cancel(world: ReviewWorld, actor: Actor, run_id: Any) -> Any:
    return await world.call(actor, "POST", f"/v1/reviewer/discovery-runs/{run_id}:cancel")


async def test_cancelling_stops_a_queued_run_now_and_asks_a_running_one_to_stop(
    review_world: ReviewWorld,
) -> None:
    actor = await review_world.signed_in()
    queued = uuid.UUID(
        (await start(review_world, slug=await new_project(review_world))).json()["run_id"]
    )
    assert (await cancel(review_world, actor, queued)).json() == {"result": "cancelled"}
    assert (
        await review_world.rows("SELECT status FROM app.discovery_runs WHERE id = :r", r=queued)
    )[0].status == "cancelled"
    running = uuid.UUID(
        (await start(review_world, slug=await new_project(review_world))).json()["run_id"]
    )
    await set_run(review_world, running, status="searching")
    assert (await cancel(review_world, actor, running)).json() == {"result": "cancel_requested"}
    assert (
        await review_world.rows(
            "SELECT status, cancel_requested FROM app.discovery_runs WHERE id = :r", r=running
        )
    )[0].cancel_requested is True
    assert (await cancel(review_world, actor, queued)).status_code == 409
    assert (await cancel(review_world, actor, uuid.uuid4())).status_code == 404
    assert (
        await review_world.call(None, "POST", f"/v1/reviewer/discovery-runs/{running}:cancel")
    ).status_code == 401


async def test_a_run_that_needs_review_is_approved_or_rejected_by_a_reviewer(
    review_world: ReviewWorld,
) -> None:
    actor = await review_world.signed_in()
    for command, expected in (("approve_completion", "complete"), ("reject_run", "failed")):
        run_id = uuid.UUID(
            (await start(review_world, slug=await new_project(review_world))).json()["run_id"]
        )
        await set_run(review_world, run_id, status="needs_review")
        response = await review_world.call(
            actor, "POST", f"/v1/reviewer/discovery-runs/{run_id}:review", json={"command": command}
        )
        assert (response.status_code, response.json()["status"]) == (200, expected)
    queued = uuid.UUID(
        (await start(review_world, slug=await new_project(review_world))).json()["run_id"]
    )
    wrong = await review_world.call(
        actor,
        "POST",
        f"/v1/reviewer/discovery-runs/{queued}:review",
        json={"command": "approve_completion"},
    )
    assert (wrong.status_code, wrong.json()["code"]) == (409, "discovery_transition_not_allowed")
    assert (
        await review_world.call(
            actor,
            "POST",
            f"/v1/reviewer/discovery-runs/{queued}:review",
            json={"command": "publish"},
        )
    ).status_code == 422


async def test_follow_up_answers_are_encrypted_once_per_question_and_bounded(
    review_world: ReviewWorld,
) -> None:
    actor = await review_world.signed_in()
    run_id = uuid.UUID((await start(review_world)).json()["run_id"])
    await set_run(
        review_world,
        run_id,
        analysis='{"analysis": {"follow_up_questions": [{"question": "q1"}, {"question": "q2"}]}}',
    )
    url = f"/v1/reviewer/discovery-runs/{run_id}/follow-up-answers"
    secret = "FICTIONAL private answer text"
    ok = await review_world.call(
        actor, "POST", url, json={"question_index": 0, "kind": "answered", "answer": secret}
    )
    assert ok.status_code == 204
    [row] = await review_world.rows(
        "SELECT answer_ciphertext, data_key_id FROM app.discovery_follow_up_answers WHERE run_id = :r",
        r=run_id,
    )
    assert secret.encode() not in bytes(row.answer_ciphertext)
    assert (
        await review_world.call(actor, "POST", url, json={"question_index": 0, "kind": "skipped"})
    ).status_code == 409
    assert (
        await review_world.call(actor, "POST", url, json={"question_index": 1, "kind": "unsafe"})
    ).status_code == 204
    for bad in (
        {"question_index": 2, "kind": "skipped"},
        {"question_index": 1, "kind": "answered"},
        {"question_index": 1, "kind": "skipped", "answer": "x"},
        {"question_index": 9, "kind": "skipped"},
    ):
        assert (await review_world.call(actor, "POST", url, json=bad)).status_code == 422, bad


# ---- source decisions -------------------------------------------------------------------------


async def staged(world: ReviewWorld, actor: Actor, run_id: Any, state: str) -> uuid.UUID:
    """A source in ``state``, reached only through real decisions."""
    source = await add_source(world, run_id)
    for command in {
        "not_reviewed": [],
        "attached": ["attach"],
        "rejected": ["reject"],
        "deferred": ["defer"],
    }[state]:
        assert (await decide(world, actor, source, command)).status_code == 200
    return source


async def decide(
    world: ReviewWorld,
    actor: Actor,
    source_id: Any,
    command: str,
    reason: str = "Checked against the public register.",
) -> Any:
    return await world.call(
        actor,
        "POST",
        f"/v1/reviewer/discovered-sources/{source_id}/decision",
        json={"command": command, "reason": reason},
    )


async def test_every_decision_and_state_over_http_matches_the_contract(
    review_world: ReviewWorld,
) -> None:
    actor = await review_world.signed_in()
    run_id = uuid.UUID((await start(review_world)).json()["run_id"])
    allowed = {(d.from_state, d.command): d.to_state for d in DECISIONS}
    for state in STATES:
        for command in COMMANDS:
            source = await staged(review_world, actor, run_id, state)
            response = await decide(review_world, actor, source, command)
            if (state, command) in allowed:
                if command == "attach":
                    assert response.status_code == 200, (state, command, response.text)
                else:
                    assert response.status_code == 200, (state, command, response.text)
                assert response.json() == {
                    "disposition": allowed[(state, command)],
                    "published": False,
                }
            else:
                assert response.status_code == 409, (state, command)
                assert response.json()["code"] == "discovered_source_decision_not_allowed"


async def test_attaching_creates_a_pending_source_and_nothing_public(
    review_world: ReviewWorld,
) -> None:
    actor = await review_world.signed_in()
    run_id = uuid.UUID((await start(review_world)).json()["run_id"])
    source = await add_source(review_world, run_id)
    facts_before = (
        await review_world.rows(
            "SELECT (SELECT count(*) FROM app.project_facts) AS f, (SELECT count(*) FROM app.project_updates) AS u"
        )
    )[0]
    response = await decide(
        review_world, actor, source, "attach", "Official ministry page that matches the project."
    )
    assert response.json() == {"disposition": "attached", "published": False}
    [row] = await review_world.rows(
        "SELECT d.disposition, d.attached_source_id, d.decision_reason_ciphertext, d.decided_by, s.canonical_url, v.review_state FROM app.discovered_sources d JOIN app.sources s ON s.id = d.attached_source_id JOIN app.source_versions v ON v.source_id = s.id WHERE d.id = :i",
        i=source,
    )
    assert (row.disposition, row.review_state, row.decided_by) == (
        "attached",
        "pending",
        actor.record.id,
    )
    assert b"Official ministry" not in bytes(row.decision_reason_ciphertext)
    facts_after = (
        await review_world.rows(
            "SELECT (SELECT count(*) FROM app.project_facts) AS f, (SELECT count(*) FROM app.project_updates) AS u"
        )
    )[0]
    assert (facts_after.f, facts_after.u) == (facts_before.f, facts_before.u)
    async with review_world.client() as http:
        cited = await http.get(f"/v1/projects/{review_world.slug}/sources/{row.attached_source_id}")
    assert cited.status_code == 404  # a pending source is not a public source
    [audit] = await review_world.rows(
        "SELECT details FROM app.audit_events WHERE event = 'discovered_source_attached' AND subject_id = :i",
        i=source,
    )
    assert "Official ministry" not in str(audit.details)
    assert (await decide(review_world, actor, source, "attach")).status_code == 409


async def test_a_rejected_source_disappears_from_the_public_view_and_reasons_are_validated(
    review_world: ReviewWorld,
) -> None:
    actor = await review_world.signed_in()
    run_id = uuid.UUID((await start(review_world)).json()["run_id"])
    source = await add_source(review_world, run_id)
    assert len((await get_public(review_world, run_id)).json()["sources"]) == 1
    for bad in ("no", "x" * 500, "bell\x07 char here"):
        assert (await decide(review_world, actor, source, "reject", bad)).status_code == 422, bad
    assert (await decide(review_world, actor, source, "reject")).status_code == 200
    assert (await get_public(review_world, run_id)).json()["sources"] == []
    assert (await decide(review_world, actor, uuid.uuid4(), "reject")).status_code == 404
    assert (
        await review_world.call(
            None,
            "POST",
            f"/v1/reviewer/discovered-sources/{source}/decision",
            json={"command": "defer", "reason": "later, please"},
        )
    ).status_code == 401
    unknown = await review_world.call(
        actor,
        "POST",
        f"/v1/reviewer/discovered-sources/{source}/decision",
        json={"command": "approve", "reason": "later, please"},
    )
    assert unknown.status_code == 422


async def test_the_database_refuses_illegal_decisions_and_rewrites(
    review_world: ReviewWorld,
) -> None:
    run_id = uuid.UUID((await start(review_world)).json()["run_id"])
    source = await add_source(review_world, run_id)
    reviewer = review_world.app.state.dependencies.reviewer_database
    assert isinstance(reviewer, Database)
    for statement in (
        "UPDATE app.discovered_sources SET disposition = 'attached' WHERE id = :i",
        "UPDATE app.discovered_sources SET excerpt = 'rewritten' WHERE id = :i",
        "DELETE FROM app.discovered_sources WHERE id = :i",
    ):
        async with reviewer.engine.connect() as connection:
            with pytest.raises(Exception):  # noqa: B017, PT011 - any database refusal
                await connection.execute(text(statement), {"i": source})

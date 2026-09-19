"""Private canaries never surface in any public, tracking, or error response, or in logs (BE-102)."""

import uuid
from dataclasses import replace
from typing import Any

import pytest
from sqlalchemy import text

from shaidago.api.v1.discovery import RunOut, SourceCardOut
from shaidago.auth.passwords import PasswordPolicy, PasswordVerifier
from tests.integration.report_support import CONTACT_CANARY, png
from tests.integration.reviewer_support import ReviewWorld

FAST = PasswordVerifier(PasswordPolicy(time_cost=1, memory_cost_kib=1024, parallelism=1))
DESCRIPTION = (
    "CANARYDESCRIPTION the fictional supervisor demanded a fictional payment at the fictional gate."
)
QUESTION = "CANARYQUESTION which fictional day was the fictional site closed?"
ANSWER = "CANARYANSWER the fictional site was closed on fictional mornings."
NOTE = "CANARYNOTE the fictional reviewer doubts the fictional account."
REASON = "CANARYREASON the fictional evidence matches the fictional register."
EXCERPT = "CANARYDISCOVERY private discovery excerpt about the fictional supervisor and payment."
PRIVATE = [
    "CANARYDESCRIPTION", CONTACT_CANARY, "CANARYQUESTION", "CANARYANSWER", "CANARYNOTE",
    "CANARYREASON", "CANARYDISCOVERY", "fictional supervisor",
]  # fmt: skip


async def build_private_world(world: ReviewWorld) -> tuple[str, uuid.UUID, str]:
    """A report with every private ingredient. Returns (tracking code, report ID, handle)."""
    world.app.state.dependencies = replace(world.app.state.dependencies, password_verifier=FAST)
    async with world.client() as http:
        handle = (
            await http.post("/v1/reporter-handles", headers={"Idempotency-Key": str(uuid.uuid4())})
        ).json()
    fields = world.public.fields(
        description=DESCRIPTION,
        reporter_handle=handle["handle"],
        reporter_passphrase=handle["passphrase"],
    )
    response = await world.public.post(fields, [("site.png", png(), "image/png")])
    assert response.status_code == 201, response.text
    code = response.json()["tracking_code"]
    [report] = await world.rows(
        "SELECT report_id FROM app.report_tracking_keys ORDER BY created_at DESC LIMIT 1"
    )
    report_id: uuid.UUID = report.report_id
    actor = await world.signed_in()
    base = f"/v1/reviewer/reports/{report_id}"
    await world.call(actor, "POST", f"{base}/follow-up-questions", json={"question": QUESTION})
    await world.call(actor, "POST", f"{base}/notes", json={"body": NOTE})
    detail = (await world.call(actor, "GET", base)).json()
    moved = await world.call(
        actor,
        "POST",
        f"{base}/status-transitions",
        json={
            "command": "start_review",
            "expected_status": "received",
            "expected_version": detail["version"],
            "internal_reason": REASON,
        },
    )
    assert moved.status_code == 200
    world.advance(1)
    [question] = await world.rows(
        "SELECT id FROM app.report_follow_up_questions WHERE report_id = :r", r=report_id
    )
    async with world.client() as http:
        answered = await http.post(
            "/v1/report-status:answer-follow-up",
            json={
                "question_id": str(question.id),
                "kind": "answered",
                "answer": ANSWER,
                "code": code,
            },
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )
    assert answered.status_code == 200, answered.text
    plan = (
        await world.call(
            actor, "POST", f"{base}/discovery-runs:plan", json={"concepts": ["delayed"]}
        )
    ).json()
    created = await world.call(
        actor,
        "POST",
        f"{base}/discovery-runs",
        json={"concepts": ["delayed"], "approved_digest": plan["plan_digest"]},
    )
    run_id = uuid.UUID(created.json()["run_id"])
    source_id = uuid.uuid4()
    async with world.owner.unit_of_work() as session:
        await session.execute(
            text(
                "INSERT INTO app.discovered_sources (id, scope, project_id, report_id, canonical_url, publisher_domain, title, "
                "preliminary_type, published_provenance, date_conflict, content_type, excerpt, text_sha256, simhash, "
                "extraction_version, injection_flag, availability, first_discovered_at, last_retrieved_at, created_at, updated_at) "
                "SELECT :id, 'report', project_id, :r, 'https://private.example/x', 'private.example', 'Private', "
                "'other_public_source', 'none', false, 'text/html', :ex, :sha, 1, 'extract-v1', false, 'available', now(), now(), now(), now() "
                "FROM app.reports WHERE id = :r"
            ),
            {"id": source_id, "r": report_id, "ex": EXCERPT, "sha": "a" * 64},
        )
        await session.execute(
            text(
                "INSERT INTO app.discovered_source_sightings VALUES (gen_random_uuid(), :s, :run, now(), now())"
            ),
            {"s": source_id, "run": run_id},
        )
    return code, report_id, handle["handle"]


async def test_no_private_value_reaches_any_public_tracking_or_error_response_or_log(
    review_world: ReviewWorld, capsys: pytest.CaptureFixture[str]
) -> None:
    code, report_id, handle = await build_private_world(review_world)
    # A reviewer's question is meant for the reporter, so only their own tracking response shows it.
    forbidden = [
        *(p for p in PRIVATE if p != "CANARYQUESTION"),
        code,
        code.replace("-", ""),
        handle,
        str(report_id),
    ]
    bodies: list[tuple[str, str]] = []

    async def record(label: str, coroutine: Any) -> None:
        response = await coroutine
        bodies.append((label, response.text + str(dict(response.headers))))

    async with review_world.client() as http:
        slug = review_world.slug
        run = (await http.post(f"/v1/projects/{slug}/discovery-runs")).json()["run_id"]
        for label, request in (
            ("localities", http.get("/v1/localities")),
            ("projects", http.get("/v1/projects")),
            ("project", http.get(f"/v1/projects/{slug}")),
            ("run", http.get(f"/v1/discovery-runs/{run}")),
            ("tracking-ok", http.post("/v1/report-status:lookup", json={"code": code})),
            (
                "tracking-wrong",
                http.post(
                    "/v1/report-status:lookup", json={"code": "SG-AAAAA-BBBBB-CCCCC-DDDDD-E"}
                ),
            ),
            ("tracking-echo", http.post("/v1/report-status:lookup", json={"code": DESCRIPTION})),
            (
                "tracking-extra",
                http.post("/v1/report-status:lookup", json={"code": code, "note": CONTACT_CANARY}),
            ),
            (
                "qa-echo",
                http.post(
                    f"/v1/projects/{slug}/questions",
                    json={"question": f"{QUESTION} {CONTACT_CANARY}"},
                ),
            ),
            (
                "qa-bad",
                http.post(
                    f"/v1/projects/{slug}/questions", json={"question": 5, "extra": DESCRIPTION}
                ),
            ),
            (
                "handle-wrong",
                http.post(
                    "/v1/reporter-handles:list-reports",
                    json={"handle": handle, "passphrase": "wrong words go here now ok fine"},
                ),
            ),
            (
                "answer-echo",
                http.post(
                    "/v1/report-status:answer-follow-up",
                    json={
                        "question_id": str(uuid.uuid4()),
                        "kind": "answered",
                        "answer": ANSWER,
                        "code": code,
                    },
                    headers={"Idempotency-Key": str(uuid.uuid4())},
                ),
            ),
            ("private-run", http.get(f"/v1/discovery-runs/{uuid.uuid4()}")),
            ("reviewer-anon", http.get(f"/v1/reviewer/reports/{report_id}")),
            (
                "bad-json",
                http.post("/v1/report-status:lookup", content=b"{" + DESCRIPTION.encode()),
            ),
        ):
            await record(label, request)
        for path in (
            "/nope",
            f"/v1/projects/{slug}/sources/{uuid.uuid4()}",
            "/health/live",
            "/health/ready",
        ):
            await record(path, http.get(path))
    for label, body in bodies:
        for secret in forbidden:
            assert secret not in body, (label, secret)
    tracked = next(b for label, b in bodies if label == "tracking-ok")
    assert "under_review" in tracked
    assert (
        "CANARYQUESTION" in tracked or "which fictional day" in tracked
    )  # the reviewer's question is meant to show
    captured = capsys.readouterr()
    for secret in [*PRIVATE, code, handle]:
        assert secret not in captured.out + captured.err, secret


def test_the_public_discovery_and_catalogue_dtos_have_an_explicit_field_allowlist() -> None:
    assert set(RunOut.model_fields) == {
        "run_id",
        "project_slug",
        "status",
        "version",
        "progress",
        "demo_replay",
        "created_at",
        "finished_at",
        "failure_code",
        "label",
        "sources",
        "result",
    }
    assert set(SourceCardOut.model_fields) == {
        "source_id",
        "canonical_url",
        "publisher_domain",
        "title",
        "preliminary_type",
        "published_on",
        "published_provenance",
        "date_conflict",
        "excerpt",
        "availability",
        "first_discovered_at",
        "last_retrieved_at",
        "label",
    }
    private = {
        "report_id",
        "query_text",
        "requested_by",
        "injection_flag",
        "disposition",
        "duplicate_of",
        "attached_source_id",
        "cancel_requested",
    }
    assert not private & (set(RunOut.model_fields) | set(SourceCardOut.model_fields))

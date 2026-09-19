"""Publishing a reviewer-authored update (BE-074): distinct text, exact preview, explicit confirm."""

import asyncio
import uuid
from dataclasses import dataclass, replace
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from shaidago.auth.passwords import PasswordPolicy, PasswordVerifier
from tests.integration.report_support import CANARY, CONTACT_CANARY, report_id_for
from tests.integration.reviewer_support import Actor, ReviewWorld
from tests.integration.support import DOCUMENT, insert_source, insert_version

QUEUE = "/v1/reviewer/reports"
PASSAGE = "The synthetic clinic opened on 1 March."
STATEMENT = "The clinic's opening on 1 March is recorded in the cited source."
FAST = PasswordVerifier(PasswordPolicy(time_cost=1, memory_cost_kib=1024, parallelism=1))


def transitions(report_id: uuid.UUID) -> str:
    return f"{QUEUE}/{report_id}/status-transitions"


def updates(report_id: uuid.UUID) -> str:
    return f"{QUEUE}/{report_id}/public-updates"


async def approved_version(world: ReviewWorld, **source: str) -> uuid.UUID:
    async with world.owner.unit_of_work() as session:
        source_id = await insert_source(session, **source)
        return await insert_version(session, source_id)


async def set_version_state(world: ReviewWorld, version_id: uuid.UUID, state: str) -> None:
    async with world.owner.unit_of_work() as session:
        await session.execute(
            text(
                "UPDATE app.source_versions SET review_state = :s, reviewed_at = now() WHERE id = :v"
            ),
            {"s": state, "v": version_id},
        )


async def state_of(world: ReviewWorld, report_id: uuid.UUID) -> tuple[str, int]:
    [row] = await world.rows("SELECT status, version FROM app.reports WHERE id = :r", r=report_id)
    return row.status, row.version


async def verified(world: ReviewWorld, actor: Actor, **submit: Any) -> tuple[str, uuid.UUID]:
    """A fictional report taken to ``verified_for_public_update`` by two real decisions."""
    code, report_id = await world.submit(**submit)
    for command, expected in (
        ("start_review", "received"),
        ("verify_for_public_update", "under_review"),
    ):
        _, version = await state_of(world, report_id)
        response = await world.call(
            actor,
            "POST",
            transitions(report_id),
            json={"command": command, "expected_status": expected, "expected_version": version},
        )
        assert response.status_code == 200, response.text
    return code, report_id


def draft(version_id: uuid.UUID, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "statement": STATEMENT,
        "effective_on": "2026-03-01",
        "last_checked_on": "2026-09-19",
        "verification_state": "verified_official",
        "citations": [
            {
                "source_version_id": str(version_id),
                "passage": PASSAGE,
                "location_label": "section 1",
            }
        ],
    }
    return body | overrides


async def public_updates(world: ReviewWorld) -> list[dict[str, Any]]:
    async with world.client() as client:
        response = await client.get(f"/v1/projects/{world.slug}")
    assert response.status_code == 200
    return response.json()["updates"]  # type: ignore[no-any-return]


async def project_update_count(world: ReviewWorld) -> int:
    [row] = await world.rows("SELECT count(*) AS n FROM app.project_updates")
    return int(row.n)


async def test_a_report_decision_alone_never_publishes_anything(review_world: ReviewWorld) -> None:
    actor = await review_world.signed_in()
    before = await project_update_count(review_world)
    code, report_id = await verified(review_world, actor)
    assert (await state_of(review_world, report_id))[0] == "verified_for_public_update"
    assert await project_update_count(review_world) == before
    assert await public_updates(review_world) == []
    assert not await review_world.rows("SELECT 1 FROM app.public_updates")
    async with review_world.client() as client:
        tracked = await client.post("/v1/report-status:lookup", json={"code": code})
    assert tracked.status_code == 200
    assert tracked.json()["message"].endswith("Nothing has been published.")


async def test_the_full_path_publishes_exactly_the_previewed_text_with_its_citations(
    review_world: ReviewWorld,
) -> None:
    actor = await review_world.signed_in()
    version_id = await approved_version(review_world)
    _, report_id = await verified(review_world, actor, contact=True, attachments=1)
    created = await review_world.call(actor, "POST", updates(report_id), json=draft(version_id))
    assert created.status_code == 201, created.text
    preview = created.json()
    assert preview["issues"] == []
    assert preview["can_publish"] is True
    assert preview["state"] == "draft"
    assert await public_updates(review_world) == []
    fetched = (
        await review_world.call(actor, "GET", f"{updates(report_id)}/{preview['public_update_id']}")
    ).json()
    assert fetched == preview
    published = await review_world.call(
        actor,
        "POST",
        f"{updates(report_id)}/{preview['public_update_id']}:publish",
        json={"preview_digest": preview["preview_digest"]},
    )
    assert published.status_code == 200, published.text
    assert published.json()["public_update_id"] == preview["public_update_id"]
    [public] = await public_updates(review_world)
    assert public == preview["update"]
    assert public["citations"][0]["passage"] == PASSAGE
    assert public["ai_generated"] is False
    # Publication is a separate act: the report is still where the reviewer left it.
    assert (await state_of(review_world, report_id))[0] == "verified_for_public_update"
    [audit] = await review_world.rows(
        "SELECT actor_id FROM app.audit_events WHERE event = 'public_update_published' "
        "AND subject_id = :u",
        u=uuid.UUID(preview["public_update_id"]),
    )
    assert audit.actor_id == actor.record.id
    columns = {
        r.column_name
        for r in await review_world.rows(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'app' AND table_name IN ('project_updates', 'update_citations')"
        )
    }
    assert "report_id" not in columns
    body = str(public)
    for private in (CANARY, CONTACT_CANARY, str(report_id), actor.record.identifier):
        assert private not in body


async def test_a_draft_needs_a_report_that_is_currently_verified(review_world: ReviewWorld) -> None:
    actor = await review_world.signed_in()
    version_id = await approved_version(review_world)
    _, report_id = await review_world.submit()
    response = await review_world.call(actor, "POST", updates(report_id), json=draft(version_id))
    assert response.status_code == 409
    assert response.json()["code"] == "public_update_report_not_verified"
    assert not await review_world.rows(
        "SELECT 1 FROM app.public_updates WHERE report_id = :r", r=report_id
    )


@dataclass(frozen=True)
class Blocked:
    report_id: uuid.UUID
    version_id: uuid.UUID
    statement: str
    expected_code: str


async def _publish_blocked_by(world: ReviewWorld, actor: Actor, case: Blocked) -> None:
    report_id, statement, expected_code = case.report_id, case.statement, case.expected_code
    version_id = case.version_id
    created = await world.call(
        actor, "POST", updates(report_id), json=draft(version_id, statement=statement)
    )
    assert created.status_code == 201, created.text
    preview = created.json()
    assert expected_code in [i["code"] for i in preview["issues"]], preview["issues"]
    assert preview["can_publish"] is False
    before = await project_update_count(world)
    response = await world.call(
        actor,
        "POST",
        f"{updates(report_id)}/{preview['public_update_id']}:publish",
        json={"preview_digest": preview["preview_digest"]},
    )
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "publication_incomplete"
    assert {"field": "statement", "code": expected_code} in response.json()["errors"]
    assert await project_update_count(world) == before
    assert await public_updates(world) == []


async def test_private_material_in_the_public_text_blocks_publication(
    review_world: ReviewWorld,
) -> None:
    actor = await review_world.signed_in()
    version_id = await approved_version(review_world)
    review_world.app.state.dependencies = replace(
        review_world.app.state.dependencies, password_verifier=FAST
    )
    async with review_world.client() as client:
        handle = (
            await client.post(
                "/v1/reporter-handles",
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )
        ).json()
    code, report_id = await verified(
        review_world,
        actor,
        description="FICTIONAL private text: the fictional supervisor demanded a fictional payment.",
    )
    contact_code, contact_report = await verified(review_world, actor, contact=True)
    handle_report_fields = review_world.public.fields(
        reporter_handle=handle["handle"], reporter_passphrase=handle["passphrase"]
    )
    handle_response = await review_world.public.post(handle_report_fields)
    assert handle_response.status_code == 201, handle_response.text
    handle_report = await report_id_for(
        review_world.public, handle_response.json()["tracking_code"]
    )
    for command, expected in (
        ("start_review", "received"),
        ("verify_for_public_update", "under_review"),
    ):
        _, version = await state_of(review_world, handle_report)
        await review_world.call(
            actor,
            "POST",
            transitions(handle_report),
            json={"command": command, "expected_status": expected, "expected_version": version},
        )
    cases = [
        (report_id, f"Reported under {code} in the register.", "tracking_code"),
        (
            report_id,
            "The record states the fictional supervisor demanded a fictional payment.",
            "report_text",
        ),
        (contact_report, f"Contact {CONTACT_CANARY} for details.", "contact"),
        (handle_report, f"Filed by {handle['handle']} in September.", "reporter_handle"),
        (report_id, f"Verified by {actor.record.identifier} on 1 March.", "reviewer_name"),
    ]
    assert contact_code
    for target, statement, expected_code in cases:
        await _publish_blocked_by(
            review_world, actor, Blocked(target, version_id, statement, expected_code)
        )


async def test_guarded_wording_needs_a_passage_that_says_it(review_world: ReviewWorld) -> None:
    actor = await review_world.signed_in()
    version_id = await approved_version(review_world)
    _, report_id = await verified(review_world, actor)
    case = Blocked(
        report_id,
        version_id,
        "The record says the clinic project is corrupt.",
        "unsupported_term_corrupt",
    )
    await _publish_blocked_by(review_world, actor, case)


async def test_sources_must_be_approved_and_passages_exact(review_world: ReviewWorld) -> None:
    actor = await review_world.signed_in()
    _, report_id = await verified(review_world, actor)
    async with review_world.owner.unit_of_work() as session:
        source_id = await insert_source(session)
        pending = await insert_version(session, source_id, state="pending")
    good = await approved_version(review_world)
    unapproved = await review_world.call(actor, "POST", updates(report_id), json=draft(pending))
    assert unapproved.status_code == 422
    assert unapproved.json()["errors"] == [
        {"field": "citations.0.source_version_id", "code": "approved_source_required"}
    ]
    unknown = await review_world.call(actor, "POST", updates(report_id), json=draft(uuid.uuid4()))
    assert unknown.json()["errors"][0]["code"] == "approved_source_required"
    misquoted = draft(good)
    misquoted["citations"][0]["passage"] = "The synthetic clinic opened on 2 March."
    response = await review_world.call(actor, "POST", updates(report_id), json=misquoted)
    assert response.json()["errors"] == [
        {"field": "citations.0.passage", "code": "passage_not_found"}
    ]
    assert DOCUMENT.count(PASSAGE) == 1
    assert not await review_world.rows(
        "SELECT 1 FROM app.public_updates WHERE report_id = :r", r=report_id
    )


async def test_invalid_drafts_are_refused_before_storage(review_world: ReviewWorld) -> None:
    actor = await review_world.signed_in()
    version_id = await approved_version(review_world)
    _, report_id = await verified(review_world, actor)
    bad_bodies = [
        draft(version_id, citations=[]),
        draft(version_id, statement="short"),
        draft(version_id, statement="<b>markup</b> in a public statement"),
        draft(version_id, verification_state="awaiting_verification"),
        draft(version_id, last_checked_on="2026-09-20"),
        draft(version_id, effective_on=None),
        draft(version_id, unexpected="field"),
        draft(version_id, citations=draft(version_id)["citations"] * 2),
    ]
    for body in bad_bodies:
        response = await review_world.call(actor, "POST", updates(report_id), json=body)
        assert response.status_code == 422, body
    assert not await review_world.rows(
        "SELECT 1 FROM app.public_updates WHERE report_id = :r", r=report_id
    )


async def test_a_preview_that_no_longer_matches_is_never_published(
    review_world: ReviewWorld,
) -> None:
    actor = await review_world.signed_in()
    version_id = await approved_version(review_world)
    _, report_id = await verified(review_world, actor)
    preview = (
        await review_world.call(actor, "POST", updates(report_id), json=draft(version_id))
    ).json()
    path = f"{updates(report_id)}/{preview['public_update_id']}:publish"
    wrong = await review_world.call(actor, "POST", path, json={"preview_digest": "0" * 64})
    assert wrong.status_code == 409
    assert wrong.json()["code"] == "preview_stale"
    malformed = await review_world.call(actor, "POST", path, json={"preview_digest": "nope"})
    assert malformed.status_code == 422
    async with review_world.owner.unit_of_work() as session:
        await session.execute(
            text("UPDATE app.reports SET risk_level = 'elevated' WHERE id = :r"), {"r": report_id}
        )
    stale = await review_world.call(
        actor, "POST", path, json={"preview_digest": preview["preview_digest"]}
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "preview_stale"
    assert await public_updates(review_world) == []
    fresh = (
        await review_world.call(actor, "GET", f"{updates(report_id)}/{preview['public_update_id']}")
    ).json()
    assert fresh["report_version"] == preview["report_version"] + 1
    ok = await review_world.call(
        actor, "POST", path, json={"preview_digest": fresh["preview_digest"]}
    )
    assert ok.status_code == 200


async def test_a_source_rejected_after_the_preview_stops_the_publication(
    review_world: ReviewWorld,
) -> None:
    actor = await review_world.signed_in()
    version_id = await approved_version(review_world)
    _, report_id = await verified(review_world, actor)
    preview = (
        await review_world.call(actor, "POST", updates(report_id), json=draft(version_id))
    ).json()
    await set_version_state(review_world, version_id, "in_review")
    await set_version_state(review_world, version_id, "rejected")
    path = f"{updates(report_id)}/{preview['public_update_id']}"
    response = await review_world.call(
        actor, "POST", f"{path}:publish", json={"preview_digest": preview["preview_digest"]}
    )
    assert response.status_code == 409
    fresh = (await review_world.call(actor, "GET", path)).json()
    assert {"field": "citations", "code": "approved_citation_required"} in fresh["issues"]
    assert fresh["update"]["citations"] == []
    blocked = await review_world.call(
        actor, "POST", f"{path}:publish", json={"preview_digest": fresh["preview_digest"]}
    )
    assert blocked.status_code == 422
    assert await public_updates(review_world) == []


async def test_a_status_change_after_the_preview_stops_the_publication(
    review_world: ReviewWorld,
) -> None:
    actor = await review_world.signed_in()
    version_id = await approved_version(review_world)
    _, report_id = await verified(review_world, actor)
    preview = (
        await review_world.call(actor, "POST", updates(report_id), json=draft(version_id))
    ).json()
    _, version = await state_of(review_world, report_id)
    moved = await review_world.call(
        actor,
        "POST",
        transitions(report_id),
        json={
            "command": "resume_review",
            "expected_status": "verified_for_public_update",
            "expected_version": version,
        },
    )
    assert moved.status_code == 200
    response = await review_world.call(
        actor,
        "POST",
        f"{updates(report_id)}/{preview['public_update_id']}:publish",
        json={"preview_digest": preview["preview_digest"]},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "public_update_report_not_verified"
    assert await public_updates(review_world) == []


async def test_a_publication_racing_a_status_change_is_consistent(
    review_world: ReviewWorld,
) -> None:
    actor = await review_world.signed_in()
    other = await review_world.signed_in()
    version_id = await approved_version(review_world)
    _, report_id = await verified(review_world, actor)
    preview = (
        await review_world.call(actor, "POST", updates(report_id), json=draft(version_id))
    ).json()
    _, version = await state_of(review_world, report_id)
    publish, move = await asyncio.gather(
        review_world.call(
            actor,
            "POST",
            f"{updates(report_id)}/{preview['public_update_id']}:publish",
            json={"preview_digest": preview["preview_digest"]},
        ),
        review_world.call(
            other,
            "POST",
            transitions(report_id),
            json={
                "command": "resume_review",
                "expected_status": "verified_for_public_update",
                "expected_version": version,
            },
        ),
    )
    published = len(await public_updates(review_world))
    if publish.status_code == 200:
        assert published == 1
    else:
        assert publish.status_code == 409
        assert move.status_code == 200
        assert published == 0
    assert move.status_code in {200, 409}


async def test_a_draft_is_published_or_withdrawn_once(review_world: ReviewWorld) -> None:
    actor = await review_world.signed_in()
    version_id = await approved_version(review_world)
    _, report_id = await verified(review_world, actor)
    first = (
        await review_world.call(actor, "POST", updates(report_id), json=draft(version_id))
    ).json()
    second = (
        await review_world.call(actor, "POST", updates(report_id), json=draft(version_id))
    ).json()
    listed = (await review_world.call(actor, "GET", updates(report_id))).json()["items"]
    assert {i["public_update_id"] for i in listed} == {
        first["public_update_id"],
        second["public_update_id"],
    }
    path = f"{updates(report_id)}/{first['public_update_id']}"
    assert (
        await review_world.call(
            actor, "POST", f"{path}:publish", json={"preview_digest": first["preview_digest"]}
        )
    ).status_code == 200
    again = await review_world.call(
        actor, "POST", f"{path}:publish", json={"preview_digest": first["preview_digest"]}
    )
    assert again.status_code == 409
    assert again.json()["code"] == "public_update_not_draft"
    assert (await review_world.call(actor, "POST", f"{path}:withdraw")).status_code == 409
    other = f"{updates(report_id)}/{second['public_update_id']}"
    assert (await review_world.call(actor, "POST", f"{other}:withdraw")).status_code == 204
    gone = await review_world.call(
        actor, "POST", f"{other}:publish", json={"preview_digest": second["preview_digest"]}
    )
    assert gone.json()["code"] == "public_update_not_draft"
    assert len(await public_updates(review_world)) == 1
    assert {
        r.event
        for r in await review_world.rows(
            "SELECT event FROM app.audit_events WHERE event LIKE 'public_update_%' AND subject_id = ANY(:ids)",
            ids=[uuid.UUID(first["public_update_id"]), uuid.UUID(second["public_update_id"])],
        )
    } == {"public_update_drafted", "public_update_published", "public_update_withdrawn"}


async def test_access_needs_a_session_csrf_and_the_right_report(review_world: ReviewWorld) -> None:
    actor = await review_world.signed_in()
    version_id = await approved_version(review_world)
    _, report_id = await verified(review_world, actor)
    _, other_report = await verified(review_world, actor)
    assert (
        await review_world.call(None, "POST", updates(report_id), json=draft(version_id))
    ).status_code == 401
    assert (await review_world.call(None, "GET", updates(report_id))).status_code == 401
    no_csrf = await review_world.call(
        actor, "POST", updates(report_id), json=draft(version_id), csrf=False
    )
    assert no_csrf.status_code == 403
    preview = (
        await review_world.call(actor, "POST", updates(report_id), json=draft(version_id))
    ).json()
    wrong_report = await review_world.call(
        actor, "GET", f"{updates(other_report)}/{preview['public_update_id']}"
    )
    assert wrong_report.status_code == 404
    unknown = await review_world.call(actor, "GET", f"{updates(report_id)}/{uuid.uuid4()}")
    assert unknown.status_code == 404
    published = await review_world.call(
        actor,
        "POST",
        f"{updates(other_report)}/{preview['public_update_id']}:publish",
        json={"preview_digest": preview["preview_digest"]},
    )
    assert published.status_code == 404


async def test_the_database_itself_refuses_shortcuts_around_the_service(
    review_world: ReviewWorld,
) -> None:
    actor = await review_world.signed_in()
    version_id = await approved_version(review_world)
    _, report_id = await verified(review_world, actor)
    preview = (
        await review_world.call(actor, "POST", updates(report_id), json=draft(version_id))
    ).json()
    draft_id = uuid.UUID(preview["public_update_id"])
    deps = review_world.app.state.dependencies
    async with deps.public_database.engine.connect() as connection:
        with pytest.raises(ProgrammingError, match="permission denied"):
            await connection.execute(text("SELECT count(*) FROM app.public_updates"))
    reviewer = deps.reviewer_database.engine
    for statement in (
        "INSERT INTO app.project_updates (id, project_id, statement, verification_state, visibility, created_at, updated_at) "
        "SELECT gen_random_uuid(), project_id, 'sneaky', 'verified_official', 'draft', now(), now() FROM app.projects LIMIT 1",
        "UPDATE app.project_updates SET visibility = 'public'",
        "UPDATE app.public_updates SET statement = 'changed' WHERE id = :d",
        "UPDATE app.public_updates SET state = 'published', published_at = now() WHERE id = :d",
        "DELETE FROM app.public_updates WHERE id = :d",
    ):
        async with reviewer.connect() as connection:
            with pytest.raises((ProgrammingError, DBAPIError)):
                await connection.execute(text(statement), {"d": draft_id})
    async with review_world.owner.unit_of_work() as session:
        await session.execute(
            text("UPDATE app.reports SET risk_level = 'high' WHERE id = :r"), {"r": report_id}
        )
    async with reviewer.begin() as connection:
        outcome = (
            await connection.execute(
                text(
                    "SELECT app.publish_public_update(:d, 1, 'reviewer', NULL, now(), gen_random_uuid(), NULL)"
                ),
                {"d": draft_id},
            )
        ).scalar_one()
    assert outcome == "stale"
    async with review_world.owner.unit_of_work() as session:
        await session.execute(
            text("UPDATE app.reports SET status = 'closed' WHERE id = :r AND false"),
            {"r": report_id},
        )
    assert await public_updates(review_world) == []

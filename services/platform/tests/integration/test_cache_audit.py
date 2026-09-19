"""Every response has an explicit cache decision: public reads may be cached, all else may not."""

import re
import uuid
from pathlib import Path

from shaidago.api.cache_policy import may_be_publicly_cached
from tests.integration.reviewer_support import ReviewWorld

SOURCE = Path(__file__).parents[2] / "src" / "shaidago"


def test_no_route_module_outside_the_public_catalogue_declares_a_public_cache_header() -> None:
    offenders: list[str] = []
    for path in SOURCE.rglob("*.py"):
        if path.name in {"projects.py", "cache_policy.py"}:
            continue
        text = path.read_text("utf-8")
        if re.search(r"public,\s*max-age|cacheable\(|s-maxage|\"ETag\"", text):
            offenders.append(str(path.relative_to(SOURCE)))
    assert offenders == []


def filled(path: str, slug: str) -> str:
    return re.sub(r"\{(\w+)\}", lambda m: slug if m.group(1) == "slug" else str(uuid.uuid4()), path)


async def test_every_documented_route_answers_with_an_explicit_cache_policy(
    review_world: ReviewWorld,
) -> None:
    schema = review_world.app.openapi()
    checked = 0
    async with review_world.client() as http:
        for template, item in schema["paths"].items():
            for method in item:
                if method not in {"get", "post", "delete", "put", "patch"}:
                    continue
                response = await http.request(method.upper(), filled(template, review_world.slug))
                policy = response.headers.get("cache-control", "")
                cacheable = may_be_publicly_cached(
                    method.upper(), response.request.url.path, response.status_code
                )
                assert policy, (method, template)
                if not cacheable:
                    assert policy == "no-store", (method, template, response.status_code, policy)
                checked += 1
    documented = sum(
        1
        for item in schema["paths"].values()
        for m in item
        if m in {"get", "post", "delete", "put", "patch"}
    )
    assert checked == documented > 30


async def test_success_responses_that_carry_private_data_are_no_store(
    review_world: ReviewWorld,
) -> None:
    code, report_id = await review_world.submit(contact=True, attachments=1)
    actor = await review_world.signed_in()
    evidence = (
        await review_world.rows(
            "SELECT id FROM app.evidence_files WHERE report_id = :r", r=report_id
        )
    )[0].id
    async with review_world.client() as http:
        tracking = await http.post("/v1/report-status:lookup", json={"code": code})
        run = await http.post(f"/v1/projects/{review_world.slug}/discovery-runs")
        live = await http.get("/health/live")
    run_id = run.json()["run_id"]
    async with review_world.client() as http:
        public_run = await http.get(f"/v1/discovery-runs/{run_id}")
        public_project = await http.get(f"/v1/projects/{review_world.slug}")
        catalogue = await http.get("/v1/projects")
    base = f"/v1/reviewer/reports/{report_id}"
    reviewer = [
        await review_world.call(actor, "GET", "/v1/reviewer/reports"),
        await review_world.call(actor, "GET", base),
        await review_world.call(actor, "GET", base, params={"include_contact": "true"}),
        await review_world.call(actor, "POST", f"{base}/notes", json={"body": "FICTIONAL note"}),
        await review_world.call(actor, "GET", f"{base}/notes"),
        await review_world.call(actor, "GET", f"{base}/evidence/{evidence}/content"),
        await review_world.call(actor, "GET", f"{base}/public-updates"),
        await review_world.call(actor, "GET", f"/v1/reviewer/discovery-runs/{run_id}"),
    ]
    for response in [tracking, run, public_run, live, *reviewer]:
        assert response.status_code in {200, 201}, (response.request.url.path, response.text)
        assert response.headers["cache-control"] == "no-store", response.request.url.path
    assert public_project.headers["cache-control"].startswith("public")
    assert catalogue.headers["cache-control"].startswith("public")
    assert "vary" in public_project.headers

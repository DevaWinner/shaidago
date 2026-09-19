"""The public project API end to end: seeded synthetic data, real database, restricted role."""

import json
import uuid
from datetime import date, datetime
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from tests.factories import CREDENTIAL
from tests.integration.public_catalogue import Seed

AUTH = {"Authorization": f"Bearer web.{CREDENTIAL}"}
FORBIDDEN_KEYS = {
    "content_text",
    "content_sha256",
    "review_state",
    "reviewer_note",
    "reviewed_by",
    "visibility",
    "source_version_id",
    "locality_id",
    "project_id",
    "created_at",
    "active",
    "internal_note",
}


def keys_of(payload: object) -> set[str]:
    if isinstance(payload, dict):
        mapping = cast("dict[str, object]", payload)
        found = set(mapping)
        for value in mapping.values():
            found |= keys_of(value)
        return found
    if isinstance(payload, list):
        collected: set[str] = set()
        for item in cast("list[object]", payload):
            collected |= keys_of(item)
        return collected
    return set()


def assert_public_only(response_text: str) -> None:
    assert not keys_of(json.loads(response_text)) & FORBIDDEN_KEYS
    for marker in ("shaidago_", "postgresql", "app.", "public_api", "password"):
        assert marker not in response_text


def all_pages(client: TestClient, **params: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    cursor: str | None = None
    for _ in range(20):
        query = dict(params, limit="2") | ({"cursor": cursor} if cursor else {})
        response = client.get("/v1/projects", params=query)
        assert response.status_code == 200, response.text
        body = response.json()
        items += body["items"]
        cursor = body["next_cursor"]
        if cursor is None:
            return items
    raise AssertionError("pagination did not terminate")


def test_credentials_are_required(client: TestClient) -> None:
    for path in ("/v1/localities", "/v1/projects", "/v1/projects/synthetic-alpha-clinic"):
        assert client.get(path, headers={"Authorization": ""}).status_code == 401


def test_localities_list_with_parents_and_cache_headers(client: TestClient) -> None:
    response = client.get("/v1/localities")
    assert response.status_code == 200
    slugs = {item["slug"] for item in response.json()["items"]}
    assert {"synthetic-council", "synthetic-other"} <= slugs
    assert response.headers["cache-control"] == "public, max-age=60"
    assert response.headers["vary"] == "X-Shaidago-Locale"
    assert_public_only(response.text)


def test_projects_are_listed_newest_first_with_a_total_order_and_no_hidden_ones(
    client: TestClient, seed: Seed
) -> None:
    items = all_pages(client)
    slugs = [item["slug"] for item in items]
    assert seed.slugs["delta"] not in slugs
    assert slugs[:2] == ["synthetic-alpha-clinic", "synthetic-beta-school"]
    assert set(slugs) >= {seed.slugs[name] for name in ("alpha", "beta", "gamma", "epsilon")}
    assert len(slugs) == len(set(slugs)), "no project repeats across pages"
    stamps = [(item["updated_at"], item["slug"]) for item in items]
    assert [s[0] for s in stamps] == sorted((s[0] for s in stamps), reverse=True)


def test_pages_cover_the_whole_set_exactly_once_for_any_page_size(client: TestClient) -> None:
    everything = [
        i["slug"] for i in client.get("/v1/projects", params={"limit": "50"}).json()["items"]
    ]
    for size in (1, 2, 3):
        collected: list[str] = []
        cursor: str | None = None
        while True:
            params = {"limit": str(size)} | ({"cursor": cursor} if cursor else {})
            body = client.get("/v1/projects", params=params).json()
            collected += [i["slug"] for i in body["items"]]
            cursor = body["next_cursor"]
            if cursor is None:
                break
        assert collected == everything


FILTER_CASES: list[tuple[dict[str, str], set[str]]] = [
    ({"category": "health"}, {"synthetic-alpha-clinic"}),
    ({"status": "in_progress"}, {"synthetic-beta-school"}),
    ({"locality": "synthetic-other"}, {"synthetic-gamma-borehole"}),
    ({"verification": "verified_official"}, {"synthetic-alpha-clinic"}),
    ({"verification": "disputed"}, {"synthetic-beta-school"}),
    ({"q": "classroom"}, {"synthetic-beta-school"}),
    ({"q": "REHABILITATION clinic"}, {"synthetic-alpha-clinic"}),
    ({"category": "health", "status": "completed"}, set()),
    ({"q": "nothing matches this"}, set()),
]


@pytest.mark.parametrize(("params", "expected"), FILTER_CASES)
def test_filters_and_text_search_narrow_the_list(
    client: TestClient, params: dict[str, str], expected: set[str]
) -> None:
    slugs = {item["slug"] for item in all_pages(client, **params)}
    assert slugs == expected


def test_a_cursor_only_works_for_the_request_that_produced_it(client: TestClient) -> None:
    body = client.get("/v1/projects", params={"limit": "1"}).json()
    cursor = body["next_cursor"]
    assert cursor
    for params in (
        {"limit": "1", "cursor": cursor, "category": "health"},
        {"limit": "1", "cursor": cursor + "x"},
        {"limit": "1", "cursor": "garbage"},
    ):
        response = client.get("/v1/projects", params=params)
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_cursor"
    other_locale = client.get(
        "/v1/projects",
        params={"limit": "1", "cursor": cursor},
        headers={"X-Shaidago-Locale": "ha"},
    )
    assert other_locale.status_code == 400


@pytest.mark.parametrize(
    "params",
    [
        {"unknown": "1"},
        {"category": "roads"},
        {"status": "abandoned"},
        {"verification": "awaiting_verification"},
        {"q": "x" * 101},
        {"q": ""},
        {"q": "a\x00b"},
        {"q": "line\nbreak"},
        {"limit": "0"},
        {"limit": "abc"},
        {"locality": "Not A Slug"},
        {"locality": "x" * 81},
    ],
)
def test_unknown_and_invalid_parameters_are_rejected_not_ignored(
    client: TestClient, params: dict[str, str]
) -> None:
    response = client.get("/v1/projects", params=params)
    assert response.status_code == 422
    assert response.json()["code"] == "validation_failed"
    assert "x" * 50 not in response.text


def test_page_size_is_capped(client: TestClient) -> None:
    assert len(client.get("/v1/projects", params={"limit": "1000"}).json()["items"]) <= 50


def test_unicode_and_hostile_search_text_is_bound_not_executed(client: TestClient) -> None:
    for query in ("Taƙaitaccen", "'; DROP TABLE app.projects; --", "%_\\", chr(0x202E), "日本語"):
        assert client.get("/v1/projects", params={"q": query}).status_code == 200
    assert client.get("/v1/projects").json()["items"]


def test_project_detail_shows_cited_published_facts_and_updates_only(
    client: TestClient, seed: Seed
) -> None:
    response = client.get("/v1/projects/synthetic-alpha-clinic")
    assert response.status_code == 200
    body = response.json()
    assert_public_only(response.text)
    assert [f["id"] for f in body["facts"]] == [str(seed.facts["alpha"])]
    fact = body["facts"][0]
    assert fact["verification_state"] == "verified_official"
    assert fact["information_class"] == "official_source"
    assert fact["ai_generated"] is False
    assert fact["effective_on"] == "2026-03-01"
    assert fact["citations"][0]["passage"] == "The synthetic clinic opened on 1 March."
    assert fact["citations"][0]["source_id"] == str(seed.sources["official"])
    assert len(body["updates"]) == 1
    assert str(seed.facts["draft"]) not in response.text
    assert body["text"]["is_fallback"] is False
    assert body["text"]["translation_status"] == "reviewed"


def test_locale_is_served_when_translated_and_flagged_as_fallback_when_not(
    client: TestClient,
) -> None:
    hausa = client.get("/v1/projects/synthetic-alpha-clinic", headers={"X-Shaidago-Locale": "ha"})
    text_hausa = hausa.json()["text"]
    assert (text_hausa["served_locale"], text_hausa["is_fallback"]) == ("ha", False)
    assert text_hausa["translation_status"] == "machine_assisted"
    yoruba = client.get("/v1/projects/synthetic-alpha-clinic", headers={"X-Shaidago-Locale": "yo"})
    text_yoruba = yoruba.json()["text"]
    assert (text_yoruba["requested_locale"], text_yoruba["served_locale"]) == ("yo", "en")
    assert text_yoruba["is_fallback"] is True
    listing = client.get("/v1/projects", headers={"X-Shaidago-Locale": "ha"}).json()["items"]
    alpha = next(i for i in listing if i["slug"] == "synthetic-alpha-clinic")
    assert alpha["text"]["served_locale"] == "ha"
    beta = next(i for i in listing if i["slug"] == "synthetic-beta-school")
    assert beta["text"]["is_fallback"] is True


def test_hidden_and_missing_projects_have_the_same_response(client: TestClient) -> None:
    hidden = client.get("/v1/projects/synthetic-delta-hidden")
    missing = client.get("/v1/projects/synthetic-does-not-exist")
    assert hidden.status_code == missing.status_code == 404

    def normalise(body: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in body.items() if k != "request_id"}

    assert normalise(hidden.json()) == normalise(missing.json())
    for name in ("content-type", "cache-control"):
        assert hidden.headers[name] == missing.headers[name]


def test_etag_changes_only_when_the_projection_changes_and_supports_revalidation(
    client: TestClient,
) -> None:
    first = client.get("/v1/projects/synthetic-beta-school")
    etag = first.headers["etag"]
    assert etag.startswith('W/"')
    assert client.get("/v1/projects/synthetic-beta-school").headers["etag"] == etag
    assert client.get("/v1/projects/synthetic-alpha-clinic").headers["etag"] != etag
    revalidated = client.get("/v1/projects/synthetic-beta-school", headers={"If-None-Match": etag})
    assert revalidated.status_code == 304
    assert revalidated.content == b""
    assert revalidated.headers["etag"] == etag
    stale = client.get("/v1/projects/synthetic-beta-school", headers={"If-None-Match": 'W/"stale"'})
    assert stale.status_code == 200


def test_source_endpoint_returns_metadata_and_only_this_projects_excerpts(
    client: TestClient, seed: Seed
) -> None:
    official = seed.sources["official"]
    response = client.get(f"/v1/projects/synthetic-alpha-clinic/sources/{official}")
    assert response.status_code == 200
    body = response.json()
    assert_public_only(response.text)
    assert body["source"]["id"] == str(official)
    assert body["source"]["information_class"] == "official_source"
    assert {(e["cited_by"], e["location_label"]) for e in body["excerpts"]} == {
        ("fact", "section 1"),
        ("update", "p2"),
    }
    assert "content_text" not in response.text
    assert "Section two follows" not in response.text, "only cited passages are returned"


def test_source_endpoint_hides_uncited_wrong_project_and_unknown_sources_identically(
    client: TestClient, seed: Seed
) -> None:
    official = seed.sources["official"]
    responses = [
        client.get(f"/v1/projects/synthetic-beta-school/sources/{official}"),  # not cited here
        client.get(f"/v1/projects/synthetic-alpha-clinic/sources/{seed.sources['unrelated']}"),
        client.get(f"/v1/projects/synthetic-alpha-clinic/sources/{uuid.uuid4()}"),
        client.get(f"/v1/projects/synthetic-delta-hidden/sources/{official}"),
    ]
    assert {r.status_code for r in responses} == {404}
    bodies = [{k: v for k, v in r.json().items() if k != "request_id"} for r in responses]
    assert all(body == bodies[0] for body in bodies)
    assert client.get("/v1/projects/synthetic-alpha-clinic/sources/not-a-uuid").status_code == 422


def test_dates_serialise_as_iso_and_times_are_timezone_aware(client: TestClient) -> None:
    body = client.get("/v1/projects/synthetic-alpha-clinic").json()
    assert date.fromisoformat(body["facts"][0]["effective_on"])
    assert datetime.fromisoformat(body["updated_at"]).utcoffset() is not None

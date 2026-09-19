"""Response-shape snapshots: a new public field fails here until a reviewer accepts it.

The snapshot records field names and JSON types, never values. Regenerate deliberately with
`UPDATE_SNAPSHOTS=1 make backend-integration` and review the diff for private data.
"""

import json
import os
from pathlib import Path
from typing import cast

from fastapi.testclient import TestClient

SNAPSHOT = Path(__file__).parent / "snapshots" / "public_response_shapes.json"
ENDPOINTS = {
    "localities": "/v1/localities",
    "project_list": "/v1/projects",
    "project_detail": "/v1/projects/synthetic-alpha-clinic",
}


def shape(value: object) -> object:
    """Field names and JSON types only; list shapes merge every element so absent keys show up."""
    if isinstance(value, dict):
        mapping = cast("dict[str, object]", value)
        return {key: shape(item) for key, item in sorted(mapping.items())}
    if isinstance(value, list):
        merged: dict[str, object] = {}
        for item in cast("list[object]", value):
            element = shape(item)
            if not isinstance(element, dict):
                return [element]
            merged |= cast("dict[str, object]", element)
        return [merged] if merged else []
    return "null" if value is None else type(value).__name__


def test_public_response_shapes_match_the_reviewed_snapshot(client: TestClient) -> None:
    detail = client.get(ENDPOINTS["project_detail"]).json()
    source_id = detail["facts"][0]["citations"][0]["source_id"]
    shapes = {name: shape(client.get(path).json()) for name, path in ENDPOINTS.items()}
    shapes["project_source"] = shape(
        client.get(f"/v1/projects/synthetic-alpha-clinic/sources/{source_id}").json()
    )
    rendered = json.dumps(shapes, indent=2, sort_keys=True) + "\n"
    if os.environ.get("UPDATE_SNAPSHOTS") == "1":
        SNAPSHOT.write_text(rendered, encoding="utf-8")
    assert SNAPSHOT.exists(), "run once with UPDATE_SNAPSHOTS=1 and review the file"
    assert rendered == SNAPSHOT.read_text(encoding="utf-8")


def test_the_snapshot_itself_contains_no_private_field_names() -> None:
    names = set(SNAPSHOT.read_text(encoding="utf-8").replace('"', " ").replace(":", " ").split())
    forbidden = {"content_text", "content_sha256", "review_state", "reviewer_note", "visibility"}
    assert not names & forbidden

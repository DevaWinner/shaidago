"""The one ``application/problem+json`` shape (RFC 9457) every error response uses.

Titles and details here are fixed, safe strings. Callers must never pass exception text,
SQL, object keys, provider output, or anything that reveals whether a record exists.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from starlette.responses import JSONResponse

PROBLEM_MEDIA_TYPE = "application/problem+json"
_TYPE_PREFIX = "urn:shaidago:problem:"


@dataclass(frozen=True)
class Problem:
    """A stable, safe error: ``code`` is the machine contract, the rest is fixed display text."""

    status: int
    code: str
    title: str
    detail: str


def problem_response(
    problem: Problem, *, request_id: str | None = None, headers: Mapping[str, str] | None = None
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"{_TYPE_PREFIX}{problem.code}",
        "title": problem.title,
        "status": problem.status,
        "code": problem.code,
        "detail": problem.detail,
    }
    if request_id is not None:
        body["request_id"] = request_id
    return JSONResponse(
        body,
        status_code=problem.status,
        media_type=PROBLEM_MEDIA_TYPE,
        headers={"Cache-Control": "no-store", **(headers or {})},
    )

"""The one ``application/problem+json`` shape (RFC 9457) every error response uses.

Titles and details here are fixed, safe strings. Callers must never pass exception text,
SQL, object keys, provider output, or anything that reveals whether a record exists. The
stable ``code`` is the contract; the BFF localises display text from it.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Final

from pydantic import BaseModel
from starlette.responses import JSONResponse

PROBLEM_MEDIA_TYPE: Final = "application/problem+json"
_TYPE_PREFIX: Final = "urn:shaidago:problem:"


@dataclass(frozen=True)
class Problem:
    """A stable, safe error: ``code`` is the machine contract, the rest is fixed display text."""

    status: int
    code: str
    title: str
    detail: str


@dataclass(frozen=True)
class FieldError:
    """Names the failing field and a stable rule code. Never carries the submitted value."""

    field: str
    code: str


BAD_REQUEST: Final = Problem(
    400, "bad_request", "Bad request", "The request could not be understood."
)
INVALID_CURSOR: Final = Problem(
    400, "invalid_cursor", "Invalid cursor", "The pagination cursor is not valid for this request."
)
IDEMPOTENCY_KEY_REQUIRED: Final = Problem(
    400,
    "idempotency_key_required",
    "Idempotency-Key required",
    "This request must include an Idempotency-Key header.",
)
IDEMPOTENCY_KEY_INVALID: Final = Problem(
    400,
    "idempotency_key_invalid",
    "Idempotency-Key invalid",
    "The Idempotency-Key must be a random UUID (version 4).",
)
IDEMPOTENCY_CONFLICT: Final = Problem(
    409,
    "idempotency_conflict",
    "Idempotency-Key conflict",
    "This Idempotency-Key was already used for a different request.",
)
ALREADY_RECEIVED: Final = Problem(
    409,
    "already_received",
    "Already received",
    "This request was already received and its result is no longer available.",
)
PUBLICATION_INCOMPLETE: Final = Problem(
    422,
    "publication_incomplete",
    "Publication requirements not met",
    "The evidence required to publish this item is incomplete.",
)
INVALID_CREDENTIALS: Final = Problem(
    401,
    "invalid_credentials",
    "Sign-in failed",
    "The identifier or password is not correct.",
)
UNAUTHENTICATED: Final = Problem(
    401, "unauthenticated", "Authentication required", "The request could not be authenticated."
)
FORBIDDEN: Final = Problem(403, "forbidden", "Not permitted", "The request is not permitted.")
CSRF_INVALID: Final = Problem(
    403, "csrf_invalid", "Request not permitted", "The request could not be verified."
)
NOT_FOUND: Final = Problem(404, "not_found", "Not found", "The requested resource was not found.")
# One answer for a malformed, unknown, or unreachable tracking code, so lookups reveal nothing.
TRACKING_NOT_RECOGNISED: Final = Problem(
    404,
    "tracking_code_not_recognised",
    "Tracking code not recognised",
    "We could not find a report for that code. Check the code and try again.",
)
# One answer for a missing handle, a wrong passphrase, a deleted handle, or a handle in backoff.
INVALID_REPORTER_CREDENTIALS: Final = Problem(
    403,
    "invalid_reporter_credentials",
    "Reporter credentials not accepted",
    "The handle and passphrase were not accepted.",
)
METHOD_NOT_ALLOWED: Final = Problem(
    405, "method_not_allowed", "Method not allowed", "This method is not supported here."
)
CONFLICT: Final = Problem(
    409, "conflict", "Conflict", "The request conflicts with the current state."
)
PAYLOAD_TOO_LARGE: Final = Problem(
    413, "payload_too_large", "Payload too large", "The request is larger than allowed."
)
UNSUPPORTED_MEDIA_TYPE: Final = Problem(
    415, "unsupported_media_type", "Unsupported media type", "That content type is not accepted."
)
VALIDATION_FAILED: Final = Problem(
    422, "validation_failed", "Validation failed", "One or more fields are invalid."
)
RATE_LIMITED: Final = Problem(
    429, "rate_limited", "Too many requests", "Too many requests. Try again later."
)
INTERNAL_ERROR: Final = Problem(
    500, "internal_error", "Internal error", "Something went wrong. Try again later."
)
DEPENDENCY_UNAVAILABLE: Final = Problem(
    503,
    "dependency_unavailable",
    "Temporarily unavailable",
    "A required service is unavailable. Try again later.",
)

_BY_STATUS: Final[Mapping[int, Problem]] = {
    problem.status: problem
    for problem in (
        BAD_REQUEST,
        UNAUTHENTICATED,
        FORBIDDEN,
        NOT_FOUND,
        METHOD_NOT_ALLOWED,
        CONFLICT,
        PAYLOAD_TOO_LARGE,
        UNSUPPORTED_MEDIA_TYPE,
        VALIDATION_FAILED,
        RATE_LIMITED,
        INTERNAL_ERROR,
        DEPENDENCY_UNAVAILABLE,
    )
}


def problem_for_status(status: int) -> Problem:
    """Map a framework HTTP error to the catalogue (other 4xx: generic 400, 5xx: generic 500)."""
    known = _BY_STATUS.get(status)
    if known is not None:
        return known
    return INTERNAL_ERROR if status >= HTTPStatus.INTERNAL_SERVER_ERROR else BAD_REQUEST


class ProblemError(Exception):
    """Raised by domain code for an expected outcome; carries only safe, fixed content."""

    def __init__(
        self,
        problem: Problem,
        *,
        field_errors: Sequence[FieldError] = (),
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(problem.code)
        self.problem = problem
        self.field_errors = tuple(field_errors)
        self.headers = dict(headers or {})


class FieldErrorBody(BaseModel):
    field: str
    code: str


class ProblemDetails(BaseModel):
    """OpenAPI description of the error body (the wire shape is built by ``problem_response``)."""

    type: str
    title: str
    status: int
    code: str
    detail: str
    request_id: str | None = None
    errors: list[FieldErrorBody] | None = None


def problem_response(
    problem: Problem,
    *,
    request_id: str | None = None,
    field_errors: Sequence[FieldError] = (),
    headers: Mapping[str, str] | None = None,
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
    if field_errors:
        body["errors"] = [{"field": error.field, "code": error.code} for error in field_errors]
    return JSONResponse(
        body,
        status_code=problem.status,
        media_type=PROBLEM_MEDIA_TYPE,
        headers={"Cache-Control": "no-store", **(headers or {})},
    )


def declare_problem_media_type(schema: dict[str, Any]) -> dict[str, Any]:
    """Document every error response as ``application/problem+json``, as it is really sent.

    FastAPI documents a response model under ``application/json``; error bodies use the RFC 9457
    media type, so the generated contract is rewritten to match.
    """
    for operations in schema.get("paths", {}).values():
        for operation in operations.values():
            for status, response in operation.get("responses", {}).items():
                content = response.get("content", {})
                is_error = status.isdigit() and int(status) >= HTTPStatus.BAD_REQUEST
                if is_error and "application/json" in content:
                    content[PROBLEM_MEDIA_TYPE] = content.pop("application/json")
    return schema

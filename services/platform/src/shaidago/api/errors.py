"""The single boundary that turns every exception into a safe problem response."""

from typing import cast

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from shaidago.shared.context import REQUEST_ID_HEADER
from shaidago.shared.problems import (
    INTERNAL_ERROR,
    VALIDATION_FAILED,
    FieldError,
    Problem,
    ProblemError,
    problem_for_status,
    problem_response,
)

_logger = structlog.get_logger("shaidago.errors")


def _respond(
    request: Request,
    problem: Problem,
    *,
    field_errors: tuple[FieldError, ...] = (),
    headers: dict[str, str] | None = None,
) -> Response:
    request_id: str | None = getattr(request.state, "request_id", None)
    request.state.error_code = problem.code
    merged = dict(headers or {})
    if request_id is not None:
        merged[REQUEST_ID_HEADER] = request_id
    return problem_response(
        problem, request_id=request_id, field_errors=field_errors, headers=merged
    )


async def _handle_problem(request: Request, error: Exception) -> Response:
    problem_error = cast("ProblemError", error)  # registered for this exact type only
    return _respond(
        request,
        problem_error.problem,
        field_errors=problem_error.field_errors,
        headers=problem_error.headers,
    )


async def _handle_validation(request: Request, error: Exception) -> Response:
    validation_error = cast("RequestValidationError", error)  # registered for this type only
    # Pydantic messages and inputs can echo submitted values, so only the location and the
    # stable rule type are returned.
    field_errors = tuple(
        FieldError(field=".".join(str(part) for part in item["loc"]), code=str(item["type"]))
        for item in validation_error.errors()
    )
    return _respond(request, VALIDATION_FAILED, field_errors=field_errors)


async def _handle_http(request: Request, error: Exception) -> Response:
    http_error = cast("StarletteHTTPException", error)  # registered for this type only
    allow = (http_error.headers or {}).get("Allow")
    headers = {"Allow": allow} if allow else {}
    return _respond(request, problem_for_status(http_error.status_code), headers=headers)


async def _handle_unexpected(request: Request, error: Exception) -> Response:
    # The exception is chained into the redacted server log; the client learns nothing about it.
    _logger.error("unhandled exception", exc_info=error)
    return _respond(request, INTERNAL_ERROR)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ProblemError, _handle_problem)
    app.add_exception_handler(RequestValidationError, _handle_validation)
    app.add_exception_handler(StarletteHTTPException, _handle_http)
    app.add_exception_handler(Exception, _handle_unexpected)

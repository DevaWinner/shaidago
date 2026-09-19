"""Optional anonymous reporter handles: create, list reports, delete.

A handle carries no identity. Credentials travel only in POST bodies, are shown once at creation,
and are never echoed, stored in a cookie, or logged. Every credential failure is the same
``invalid_reporter_credentials`` problem, whether the handle is unknown, deleted, wrong, or in
backoff. Reviewers may see a handle as context; it is never proof.
"""

import hashlib
from datetime import datetime
from typing import Annotated, Any, Final, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from shaidago.api.dependencies import Dependencies, get_dependencies, get_settings
from shaidago.api.rate_limits import enforce_rate_limit
from shaidago.reports import handle_store, handles
from shaidago.reports.status_lookup import NEXT_ACTIONS
from shaidago.shared.config import Settings
from shaidago.shared.idempotency import (
    IdempotencyStore,
    Replay,
    fingerprint,
    validate_idempotency_key,
)
from shaidago.shared.problems import (
    CONFLICT,
    DEPENDENCY_UNAVAILABLE,
    INVALID_REPORTER_CREDENTIALS,
    PAYLOAD_TOO_LARGE,
    ProblemDetails,
    ProblemError,
)

router = APIRouter(prefix="/reporter-handles", tags=["reporter-handles"])

CREATE_OPERATION: Final = "reporter_handles.create"
MAX_BODY_BYTES: Final = 1024
CREATE_ATTEMPTS: Final = 3
PAIR_LIMIT: Final = 10
PROBLEMS: dict[int | str, dict[str, Any]] = {
    400: {"model": ProblemDetails, "description": "Malformed body or Idempotency-Key."},
    403: {"model": ProblemDetails, "description": "One answer for every credential failure."},
    413: {"model": ProblemDetails},
    422: {"model": ProblemDetails},
    429: {"model": ProblemDetails},
    503: {"model": ProblemDetails},
}


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")

    handle: Annotated[str, Field(max_length=64)]
    passphrase: Annotated[str, Field(max_length=handles.MAX_CREDENTIAL_CHARS)]


class HandleCreated(BaseModel):
    """Shown once and never recoverable: nobody, including the operators, can show it again."""

    model_config = ConfigDict(extra="forbid")

    handle: str
    passphrase: str
    recoverable: Literal[False]


class ReportStatusItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    status_updated_at: datetime
    message: str
    next_action: str


class HandleReports(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reports: list[ReportStatusItem]


def _refuse_large_body(request: Request) -> None:
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        raise ProblemError(PAYLOAD_TOO_LARGE)


def _client(request: Request) -> str:
    return str(getattr(request.state, "client_hmac", None) or "unknown")


def _pair_bucket(client: str, handle: str) -> str:
    """Per client and handle, hashed, so it holds no handle and covers unknown ones too."""
    normal = handles.normalise_handle(handle) or handle.strip().upper()[:64]
    return hashlib.sha256(f"{client}:{normal}".encode()).hexdigest()[:32]


async def verified_handle(
    credentials: Credentials,
    request: Request,
    dependencies: Dependencies,
    settings: Settings,
) -> UUID:
    """Rate limit, then verify. Returns the handle's internal ID or raises the generic problem."""
    client = _client(request)
    await enforce_rate_limit(
        dependencies,
        f"sg:rl:handle:{client}",
        limit=settings.rate_limits.handle_verify_per_hour,
    )
    await enforce_rate_limit(
        dependencies,
        f"sg:rl:handle-pair:{_pair_bucket(client, credentials.handle)}",
        limit=PAIR_LIMIT,
    )
    database = dependencies.public_database
    if database is None:
        raise ProblemError(DEPENDENCY_UNAVAILABLE)
    handle_id = await handle_store.authenticate(
        database,
        handle_store.HandleServices(
            dependencies.password_verifier, dependencies.clock, dependencies.ids
        ),
        handle=credentials.handle,
        passphrase=credentials.passphrase,
    )
    if handle_id is None:
        raise ProblemError(INVALID_REPORTER_CREDENTIALS)
    return handle_id


@router.post(
    "",
    response_model=HandleCreated,
    status_code=201,
    responses=PROBLEMS,
)
async def create_handle(
    request: Request,
    response: Response,
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    response.headers["Cache-Control"] = "no-store"
    key = validate_idempotency_key(request.headers.get("idempotency-key"))
    await enforce_rate_limit(
        dependencies,
        f"sg:rl:handle-create:{_client(request)}",
        limit=settings.rate_limits.submission_per_hour,
    )
    database = dependencies.public_database
    if database is None:
        raise ProblemError(DEPENDENCY_UNAVAILABLE)
    for _ in range(CREATE_ATTEMPTS):
        new = handles.generate()
        try:
            async with database.unit_of_work() as session:
                store = IdempotencyStore(
                    session,
                    pepper=settings.crypto.idempotency_key(),
                    clock=dependencies.clock,
                    ids=dependencies.ids,
                )
                claim = await store.begin(CREATE_OPERATION, key, fingerprint("create"))
                if isinstance(claim, Replay):
                    return _created(claim.payload, replayed=True)
                await handle_store.insert_handle(
                    session,
                    new,
                    verifier=dependencies.password_verifier,
                    clock=dependencies.clock,
                    ids=dependencies.ids,
                )
                payload = (
                    HandleCreated(handle=new.handle, passphrase=new.passphrase, recoverable=False)
                    .model_dump_json()
                    .encode()
                )
                await store.complete(CREATE_OPERATION, key, status=201, payload=payload)
        except ProblemError as error:
            if error.problem is not CONFLICT:
                raise
            continue  # the random handle collided with an existing one; draw another
        return _created(payload, replayed=False)
    raise ProblemError(CONFLICT)


def _created(payload: bytes, *, replayed: bool) -> Response:
    headers = {"Cache-Control": "no-store"}
    if replayed:
        headers["Idempotency-Replayed"] = "true"
    return Response(payload, status_code=201, media_type="application/json", headers=headers)


@router.post(
    ":list-reports",
    response_model=HandleReports,
    responses=PROBLEMS,
    dependencies=[Depends(_refuse_large_body)],
)
async def list_handle_reports(
    body: Credentials,
    request: Request,
    response: Response,
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> HandleReports:
    """Public-safe statuses only: no code, ID, category, text, or evidence."""
    response.headers["Cache-Control"] = "no-store"
    handle_id = await verified_handle(body, request, dependencies, settings)
    database = dependencies.public_database
    if database is None:
        raise ProblemError(DEPENDENCY_UNAVAILABLE)
    async with database.unit_of_work() as session:
        items = await handle_store.list_reports(session, handle_id)
    return HandleReports(
        reports=[
            ReportStatusItem(
                status=item.status,
                status_updated_at=item.status_updated_at,
                message=item.message,
                next_action=NEXT_ACTIONS.get(item.status, "none"),
            )
            for item in items
        ]
    )


@router.post(
    ":delete",
    status_code=204,
    responses=PROBLEMS,
    dependencies=[Depends(_refuse_large_body)],
)
async def delete_handle(
    body: Credentials,
    request: Request,
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    """Unlinks every report, then removes the credential. The reports stay, fully anonymous."""
    handle_id = await verified_handle(body, request, dependencies, settings)
    database = dependencies.public_database
    if database is None:
        raise ProblemError(DEPENDENCY_UNAVAILABLE)
    async with database.unit_of_work() as session:
        await handle_store.delete_handle(session, handle_id)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})

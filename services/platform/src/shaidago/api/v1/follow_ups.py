"""Reporter follow-up answers, authenticated by tracking code or by reporter handle.

Ownership is checked in the database against the caller's credential, so an answer can only go to
a question about the caller's own report. Every way of failing (bad credential, another report's
question, unknown, already answered, withdrawn) gives the same generic problem for its credential
type, and the answer text is encrypted before storage and never returned.
"""

from typing import Annotated, Any, Final, Literal, Self
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

from shaidago.api.dependencies import Dependencies, get_dependencies, get_settings
from shaidago.api.rate_limits import enforce_rate_limit
from shaidago.api.v1.report_status import PREFIX_LIMIT, code_bucket
from shaidago.api.v1.reporter_handles import Credentials, verified_handle
from shaidago.reports import follow_ups
from shaidago.reports.status_lookup import code_prefix
from shaidago.reports.tracking import InvalidTrackingCodeError, lookup_candidates, normalise
from shaidago.shared.config import Settings
from shaidago.shared.crypto import EnvironmentKekWrapper, FieldCipher
from shaidago.shared.data_keys import DataKeyService
from shaidago.shared.idempotency import (
    IdempotencyStore,
    Replay,
    fingerprint,
    validate_idempotency_key,
)
from shaidago.shared.problems import (
    DEPENDENCY_UNAVAILABLE,
    INVALID_REPORTER_CREDENTIALS,
    PAYLOAD_TOO_LARGE,
    TRACKING_NOT_RECOGNISED,
    VALIDATION_FAILED,
    FieldError,
    ProblemDetails,
    ProblemError,
)

router = APIRouter(tags=["reports"])

OPERATION: Final = "follow_ups.answer"
MAX_BODY_BYTES: Final = 8 * 1024
PROBLEMS: dict[int | str, dict[str, Any]] = {
    400: {"model": ProblemDetails, "description": "Malformed body or Idempotency-Key."},
    403: {"model": ProblemDetails, "description": "Generic handle failure."},
    404: {"model": ProblemDetails, "description": "Generic tracking-code failure."},
    409: {"model": ProblemDetails, "description": "Key reused with a different request."},
    413: {"model": ProblemDetails},
    422: {"model": ProblemDetails},
    429: {"model": ProblemDetails},
    503: {"model": ProblemDetails},
}


class AnswerRequest(BaseModel):
    """Exactly one credential (a tracking code, or a handle with its passphrase)."""

    model_config = ConfigDict(extra="forbid")

    question_id: UUID
    kind: Literal["answered", "skipped", "unsafe"]
    answer: Annotated[str, Field(max_length=follow_ups.MAX_ANSWER_CHARS + 500)] | None = None
    code: Annotated[str, Field(max_length=256)] | None = None
    handle: Annotated[str, Field(max_length=64)] | None = None
    passphrase: Annotated[str, Field(max_length=200)] | None = None

    @model_validator(mode="after")
    def _one_credential_and_matching_content(self) -> Self:
        by_code = self.code is not None
        by_handle = self.handle is not None or self.passphrase is not None
        if by_code == by_handle or (by_handle and (self.handle is None or self.passphrase is None)):
            raise ValueError("credential")
        if (self.kind == "answered") != (self.answer is not None):
            raise ValueError("content")
        return self


class AnswerAck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    acknowledged: Literal[True]
    question_state: Literal["answered", "skipped", "unsafe"]


def _refuse_large_body(request: Request) -> None:
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        raise ProblemError(PAYLOAD_TOO_LARGE)


async def _caller(
    body: AnswerRequest, request: Request, dependencies: Dependencies, settings: Settings
) -> tuple[follow_ups.Caller, bytes, ProblemError]:
    """Authenticate; return who is calling, a stable identity for the fingerprint, and the
    generic problem to raise if the question turns out not to be theirs."""
    client = str(getattr(request.state, "client_hmac", None) or "unknown")
    if body.code is None:
        handle_id = await verified_handle(
            Credentials(handle=body.handle or "", passphrase=body.passphrase or ""),
            request,
            dependencies,
            settings,
        )
        return (
            follow_ups.Caller(handle_id=handle_id),
            handle_id.bytes,
            ProblemError(INVALID_REPORTER_CREDENTIALS),
        )
    await enforce_rate_limit(
        dependencies,
        f"sg:rl:track:{client}",
        limit=settings.rate_limits.tracking_lookup_per_hour,
    )
    prefix = code_prefix(body.code)
    if prefix is not None:
        await enforce_rate_limit(
            dependencies, f"sg:rl:track:{code_bucket(client, prefix)}", limit=PREFIX_LIMIT
        )
    crypto = settings.crypto
    try:
        candidates = lookup_candidates(
            dict(crypto.tracking_pepper_keys().keys),
            crypto.active_tracking_pepper_version,
            normalise(body.code),
        )
    except InvalidTrackingCodeError:
        return follow_ups.Caller(), b"", ProblemError(TRACKING_NOT_RECOGNISED)
    digests = tuple(digest for _, digest in candidates)
    return follow_ups.Caller(digests=digests), digests[0], ProblemError(TRACKING_NOT_RECOGNISED)


@router.post(
    "/report-status:answer-follow-up",
    response_model=AnswerAck,
    responses=PROBLEMS,
    dependencies=[Depends(_refuse_large_body)],
)
async def answer_follow_up(
    body: AnswerRequest,
    request: Request,
    response: Response,
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    response.headers["Cache-Control"] = "no-store"
    key = validate_idempotency_key(request.headers.get("idempotency-key"))
    caller, identity, failure = await _caller(body, request, dependencies, settings)
    database = dependencies.public_database
    if database is None:
        raise ProblemError(DEPENDENCY_UNAVAILABLE)
    crypto = settings.crypto
    request_fingerprint = fingerprint(
        str(body.question_id), body.kind, (body.answer or "").strip(), identity
    )
    async with database.unit_of_work() as session:
        claim = await IdempotencyStore(
            session, pepper=crypto.idempotency_key(), clock=dependencies.clock, ids=dependencies.ids
        ).begin(OPERATION, key, request_fingerprint)
        if isinstance(claim, Replay):
            return _ack(claim.payload, replayed=True)
        submitter = follow_ups.FollowUpSubmitter(
            session,
            DataKeyService(
                session,
                EnvironmentKekWrapper(crypto.kek_keys().keys, crypto.active_kek_version),
                dependencies.clock,
                dependencies.ids,
            ),
            FieldCipher(),
            dependencies.clock,
            dependencies.ids,
        )
        try:
            recorded = await submitter.submit(caller, body.question_id, body.kind, body.answer)
        except follow_ups.InvalidAnswerError:
            raise ProblemError(
                VALIDATION_FAILED, field_errors=[FieldError("answer", "length")]
            ) from None
        if not recorded:
            raise failure  # rolls back the claim and any key created for the answer
        payload = AnswerAck(acknowledged=True, question_state=body.kind).model_dump_json().encode()
        await IdempotencyStore(
            session, pepper=crypto.idempotency_key(), clock=dependencies.clock, ids=dependencies.ids
        ).complete(OPERATION, key, status=200, payload=payload)
    return _ack(payload, replayed=False)


def _ack(payload: bytes, *, replayed: bool) -> Response:
    headers = {"Cache-Control": "no-store"}
    if replayed:
        headers["Idempotency-Replayed"] = "true"
    return Response(payload, status_code=200, media_type="application/json", headers=headers)

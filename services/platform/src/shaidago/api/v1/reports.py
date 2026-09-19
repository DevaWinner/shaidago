"""Private report submission.

The endpoint never publishes anything and never echoes what was submitted. The tracking code is
returned once, in this response (or its sealed idempotent replay), and is not stored in a
recoverable form. Attachment problems never lose the report: the response says which files were
not kept and why, using stable codes only.
"""

import hashlib
import re
import unicodedata
from collections.abc import AsyncIterator, Awaitable, Callable, MutableMapping
from dataclasses import dataclass
from typing import Annotated, Any, Final, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict
from starlette.datastructures import FormData, UploadFile
from starlette.requests import Request as StarletteRequest

from shaidago.api.dependencies import Dependencies, get_dependencies, get_settings
from shaidago.api.rate_limits import enforce_rate_limit
from shaidago.api.v1.reporter_handles import Credentials, verified_handle
from shaidago.files.pipeline import StoredEvidence
from shaidago.files.rules import MIME_EXTENSIONS, UploadRejectedError
from shaidago.projects.repository import PublicProjectRepository
from shaidago.reports.persistence import (
    MAX_CONTACT_CHARS,
    MAX_DESCRIPTION_CHARS,
    ContactInput,
    InvalidReportError,
    NewReport,
    ReportWriter,
)
from shaidago.reports.tracking import generate
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
    PAYLOAD_TOO_LARGE,
    UNSUPPORTED_MEDIA_TYPE,
    VALIDATION_FAILED,
    FieldError,
    ProblemDetails,
    ProblemError,
)
from shaidago.shared.vocabulary import values

router = APIRouter(prefix="/reports", tags=["reports"])

OPERATION: Final = "reports.create"
MAX_FILES: Final = 3
MAX_FILE_BYTES: Final = 10 * 1024 * 1024
MAX_FIELD_BYTES: Final = 64 * 1024
MAX_BODY_BYTES: Final = MAX_FILES * MAX_FILE_BYTES + MAX_FIELD_BYTES
MIN_DESCRIPTION_CHARS: Final = 10
MAX_SLUG_CHARS: Final = 120
MIN_HANDLE_CHARS: Final = 3
MAX_CREDENTIAL_FIELD: Final = 200
RATE_WINDOW_SECONDS: Final = 3600
CONTACT_CHANNELS: Final = ("email", "phone", "messaging_app")
_EMAIL: Final = re.compile(r"[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,63}")
_PHONE: Final = re.compile(r"\+?[0-9][0-9 ()-]{5,19}")
_TEXT_FIELDS: Final = (
    "project_slug",
    "concern_category",
    "description",
    "contact_channel",
    "contact_value",
    "reporter_handle",
    "reporter_passphrase",
)
_SLUG: Final = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
PROBLEMS: dict[int | str, dict[str, Any]] = {
    400: {"model": ProblemDetails, "description": "Missing or malformed Idempotency-Key."},
    403: {"model": ProblemDetails, "description": "Reporter handle credentials not accepted."},
    409: {"model": ProblemDetails, "description": "Key reused with a different request."},
    413: {"model": ProblemDetails},
    415: {"model": ProblemDetails},
    422: {"model": ProblemDetails},
    429: {"model": ProblemDetails},
    503: {"model": ProblemDetails},
}
AttachmentReason = Literal[
    "unsupported_type",
    "spoofed_type",
    "active_content",
    "encrypted_pdf",
    "too_large",
    "too_many_pixels",
    "too_many_pages",
    "malformed",
    "malware_detected",
    "scan_failed",
    "storage_failed",
    "timeout",
]


class AttachmentOutcome(BaseModel):
    """Position only: names and content are never echoed."""

    model_config = ConfigDict(extra="forbid")

    position: int
    kept: bool
    reason: AttachmentReason | None


class ReportReceipt(BaseModel):
    """Shown once. The client must display the code and never put it in a URL or storage."""

    model_config = ConfigDict(extra="forbid")

    tracking_code: str
    status: Literal["received"]
    published: Literal[False]
    contact_saved: bool
    attachments: list[AttachmentOutcome]
    next_steps: list[Literal["save_tracking_code", "check_status_later", "see_escalation_guidance"]]


@dataclass(frozen=True)
class Submission:
    project_slug: str
    category: str
    description: str
    contact: ContactInput | None
    files: tuple[UploadFile, ...]
    credentials: Credentials | None = None


def _too_large() -> ProblemError:
    return ProblemError(PAYLOAD_TOO_LARGE)


def limited_request(request: Request, limit: int) -> StarletteRequest:
    """A request whose body stream fails as soon as it exceeds ``limit`` bytes.

    Content-Length is only a hint, so the count is enforced on the bytes actually received,
    before multipart parsing spools them anywhere.
    """
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > limit:
        raise _too_large()
    received = 0
    original: Callable[[], Awaitable[MutableMapping[str, Any]]] = request.receive

    async def receive() -> MutableMapping[str, Any]:
        nonlocal received
        message = await original()
        if message["type"] == "http.request":
            received += len(message.get("body", b""))
            if received > limit:
                raise _too_large()
        return message

    return StarletteRequest(request.scope, receive)


def _text(form: FormData, name: str) -> str:
    raw = form.get(name)
    return unicodedata.normalize("NFC", raw).strip() if isinstance(raw, str) else ""


def parse_submission(form: FormData, known_categories: tuple[str, ...]) -> Submission:
    errors: list[FieldError] = []
    if any(name not in _TEXT_FIELDS and name != "attachments" for name in form):
        errors.append(FieldError("form", "unexpected_field"))  # never echo a submitted name
    slug, category = _text(form, "project_slug"), _text(form, "concern_category")
    description = _text(form, "description")
    if not _SLUG.fullmatch(slug) or len(slug) > MAX_SLUG_CHARS:
        errors.append(FieldError("project_slug", "invalid"))
    if category not in known_categories:
        errors.append(FieldError("concern_category", "invalid"))
    if not MIN_DESCRIPTION_CHARS <= len(description) <= MAX_DESCRIPTION_CHARS:
        errors.append(FieldError("description", "length"))
    if "\x00" in description:
        errors.append(FieldError("description", "invalid"))
    contact, contact_errors = _contact(form)
    errors.extend(contact_errors)
    credentials, credential_errors = _credentials(form, has_contact=contact is not None)
    errors.extend(credential_errors)
    attachments = form.getlist("attachments")
    files = tuple(f for f in attachments if isinstance(f, UploadFile) and f.filename)
    if len(files) > MAX_FILES:
        errors.append(FieldError("attachments", "too_many"))
    if any(isinstance(item, str) and item for item in attachments):
        errors.append(FieldError("attachments", "not_a_file"))
    if errors:
        raise ProblemError(VALIDATION_FAILED, field_errors=errors)
    return Submission(slug, category, description, contact, files, credentials)


def _credentials(
    form: FormData, *, has_contact: bool
) -> tuple[Credentials | None, list[FieldError]]:
    """A handle is one of three exclusive choices: anonymous, handle, or a contact channel."""
    handle, passphrase = _text(form, "reporter_handle"), _text(form, "reporter_passphrase")
    if not handle and not passphrase:
        return None, []
    errors: list[FieldError] = []
    if not handle or not passphrase:
        errors.append(FieldError("reporter_handle", "required_together"))
    if has_contact:
        errors.append(FieldError("reporter_handle", "exclusive_with_contact"))
    if len(handle) > MAX_CREDENTIAL_FIELD or len(passphrase) > MAX_CREDENTIAL_FIELD:
        errors.append(FieldError("reporter_handle", "length"))
    return (None, errors) if errors else (Credentials(handle=handle, passphrase=passphrase), [])


def _contact_value_error(channel: str, value: str) -> str | None:
    if not value or len(value) > MAX_CONTACT_CHARS:
        return "length"
    valid = {
        "email": bool(_EMAIL.fullmatch(value)),
        "phone": bool(_PHONE.fullmatch(value)),
        "messaging_app": len(value) >= MIN_HANDLE_CHARS and value.isprintable(),
    }
    return None if valid.get(channel, True) else "invalid"


def _contact(form: FormData) -> tuple[ContactInput | None, list[FieldError]]:
    """Contact is optional and used only to reach the reporter, never as an identity."""
    channel, value = _text(form, "contact_channel"), _text(form, "contact_value")
    if not channel and not value:
        return None, []
    errors: list[FieldError] = []
    if channel not in CONTACT_CHANNELS:
        errors.append(FieldError("contact_channel", "invalid"))
    if (problem := _contact_value_error(channel, value)) is not None:
        errors.append(FieldError("contact_value", problem))
    return (None, errors) if errors else (ContactInput(channel, value), [])


async def _digest(upload: UploadFile) -> str:
    digest = hashlib.sha256()
    await upload.seek(0)
    while chunk := await upload.read(64 * 1024):
        digest.update(chunk)
    await upload.seek(0)
    return digest.hexdigest()


async def _chunks(upload: UploadFile) -> AsyncIterator[bytes]:
    while chunk := await upload.read(64 * 1024):
        yield chunk


def _declared_type(upload: UploadFile) -> str | None:
    declared = (upload.content_type or "").split(";")[0].strip().lower()
    return declared if declared in MIME_EXTENSIONS else None


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.post(
    "",
    response_model=ReportReceipt,
    status_code=201,
    responses=PROBLEMS,
    operation_id="reports_submit",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["project_slug", "concern_category", "description"],
                        "additionalProperties": False,
                        "properties": {
                            "project_slug": {"type": "string", "maxLength": 120},
                            "concern_category": {
                                "type": "string",
                                "enum": list(values("report_concern_category")),
                            },
                            "description": {
                                "type": "string",
                                "minLength": MIN_DESCRIPTION_CHARS,
                                "maxLength": MAX_DESCRIPTION_CHARS,
                            },
                            "contact_channel": {"type": "string", "enum": list(CONTACT_CHANNELS)},
                            "contact_value": {"type": "string", "maxLength": MAX_CONTACT_CHARS},
                            "reporter_handle": {"type": "string", "maxLength": 200},
                            "reporter_passphrase": {"type": "string", "maxLength": 200},
                            "attachments": {
                                "type": "array",
                                "maxItems": MAX_FILES,
                                "items": {"type": "string", "format": "binary"},
                            },
                        },
                    }
                }
            },
        }
    },
)
async def submit_report(
    request: Request,
    response: Response,
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    _no_store(response)
    client = getattr(request.state, "client_hmac", None) or "unknown"
    await enforce_rate_limit(
        dependencies, f"sg:rl:submit:{client}", limit=settings.rate_limits.submission_per_hour
    )
    key = validate_idempotency_key(request.headers.get("idempotency-key"))
    if not request.headers.get("content-type", "").lower().startswith("multipart/form-data"):
        raise ProblemError(UNSUPPORTED_MEDIA_TYPE)
    bounded = limited_request(request, MAX_BODY_BYTES)
    async with bounded.form(
        max_files=MAX_FILES + 1, max_fields=len(_TEXT_FIELDS) + 4, max_part_size=MAX_FIELD_BYTES
    ) as form:
        submission = parse_submission(form, values("report_concern_category"))
        handle_id: UUID | None = None
        if submission.credentials is not None:
            # Wrong credentials leave the report unsubmitted, with the one generic answer.
            handle_id = await verified_handle(
                submission.credentials, request, dependencies, settings
            )
        return await _store(submission, key, dependencies, settings, handle_id)


async def _store(
    submission: Submission,
    key: str,
    dependencies: Dependencies,
    settings: Settings,
    handle_id: UUID | None,
) -> Response:
    database = dependencies.public_database
    if database is None:
        raise ProblemError(DEPENDENCY_UNAVAILABLE)
    digests = [await _digest(upload) for upload in submission.files]
    contact = submission.contact
    request_fingerprint = fingerprint(
        submission.project_slug,
        submission.category,
        submission.description,
        contact.channel if contact else "",
        contact.value if contact else "",
        str(handle_id) if handle_id else "",
        *digests,
    )
    crypto = settings.crypto
    peppers = crypto.tracking_pepper_keys().keys
    pepper_version = crypto.active_tracking_pepper_version
    kek = crypto.kek_keys().keys
    kept: list[StoredEvidence] = []
    try:
        async with database.unit_of_work() as session:
            claim = await IdempotencyStore(
                session,
                pepper=crypto.idempotency_key(),
                clock=dependencies.clock,
                ids=dependencies.ids,
            ).begin(OPERATION, key, request_fingerprint)
            if isinstance(claim, Replay):
                return _json(claim.status, claim.payload, replayed=True)
            project_id = await PublicProjectRepository(session).resolve_project_id(
                submission.project_slug
            )
            if project_id is None:
                raise ProblemError(
                    VALIDATION_FAILED, field_errors=[FieldError("project_slug", "unknown")]
                )
            outcomes = await _process_files(submission.files, dependencies, kept)
            writer = ReportWriter(
                session,
                DataKeyService(
                    session,
                    EnvironmentKekWrapper(kek, crypto.active_kek_version),
                    dependencies.clock,
                    dependencies.ids,
                ),
                cipher=FieldCipher(),
                clock=dependencies.clock,
                ids=dependencies.ids,
            )
            code = generate()
            try:
                report_id = await writer.insert(
                    NewReport(
                        project_id,
                        submission.category,
                        submission.description,
                        contact,
                        reporter_handle_id=handle_id,
                    ),
                    code,
                    pepper_version=pepper_version,
                    pepper=peppers[pepper_version],
                )
            except InvalidReportError:
                raise ProblemError(
                    VALIDATION_FAILED, field_errors=[FieldError("description", "invalid")]
                ) from None
            await _attach(writer, report_id, kept)
            receipt = ReportReceipt(
                tracking_code=code.formatted,
                status="received",
                published=False,
                contact_saved=contact is not None,
                attachments=outcomes,
                next_steps=["save_tracking_code", "check_status_later", "see_escalation_guidance"],
            )
            payload = receipt.model_dump_json().encode()
            await IdempotencyStore(
                session,
                pepper=crypto.idempotency_key(),
                clock=dependencies.clock,
                ids=dependencies.ids,
            ).complete(OPERATION, key, status=201, payload=payload)
    except BaseException:
        await _discard(kept, dependencies)
        raise
    return _json(201, payload, replayed=False)


async def _attach(writer: ReportWriter, report_id: UUID, kept: list[StoredEvidence]) -> None:
    for stored in kept:
        await writer.attach_evidence(report_id, stored)


async def _process_files(
    files: tuple[UploadFile, ...], dependencies: Dependencies, kept: list[StoredEvidence]
) -> list[AttachmentOutcome]:
    outcomes: list[AttachmentOutcome] = []
    pipeline = dependencies.evidence_pipeline
    for position, upload in enumerate(files, start=1):
        reason: str | None = None
        if pipeline is None:
            reason = "storage_failed"
        else:
            try:
                kept.append(
                    await pipeline.process(
                        _chunks(upload),
                        filename=upload.filename or "",
                        declared_mime=_declared_type(upload),
                    )
                )
            except UploadRejectedError as rejected:
                reason = rejected.reason
        outcomes.append(
            AttachmentOutcome(position=position, kept=reason is None, reason=reason)  # type: ignore[arg-type]  # reasons are the AttachmentReason codes
        )
    return outcomes


async def _discard(kept: list[StoredEvidence], dependencies: Dependencies) -> None:
    """Best effort: a failed submission must not leave stored files that nothing references."""
    pipeline = dependencies.evidence_pipeline
    if pipeline is None:
        return
    for stored in kept:
        try:
            await pipeline.discard(stored.object_key)
        except UploadRejectedError:
            continue  # the orphan is unreferenced and unguessable; retention sweeps remove it


def _json(status: int, payload: bytes, *, replayed: bool) -> Response:
    headers = {"Cache-Control": "no-store"}
    if replayed:
        headers["Idempotency-Replayed"] = "true"
    return Response(payload, status_code=status, media_type="application/json", headers=headers)


__all__ = ["router"]

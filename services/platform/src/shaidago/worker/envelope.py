"""The only thing a job message may carry: identifiers and a configuration version.

Nothing private can be put in a message because the schema has no place for it: no report text,
contact, tracking code, query, or attachment content. Everything else is read from PostgreSQL by
the worker under its own restricted role.
"""

from typing import Annotated, Final, cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from shaidago.shared.context import REQUEST_ID_PATTERN

ENVELOPE_VERSION: Final = 1
ACTOR_NAME: Final = "run_discovery"
QUEUE_NAME: Final = "discovery"
CONFIG_VERSION: Final = "discovery-v1"


class JobEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    envelope_version: Annotated[int, Field(ge=1, le=ENVELOPE_VERSION)] = ENVELOPE_VERSION
    run_id: UUID
    config_version: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,39}$")]
    # The originating request ID, so one ID spans BFF, API, worker, and audit rows. It is
    # operational metadata with bounded shape (A-20), never a credential or private value.
    request_id: Annotated[str, Field(pattern=REQUEST_ID_PATTERN)] | None = None


class InvalidEnvelopeError(ValueError):
    """The message is not a valid envelope. The message never repeats its content."""


def parse_envelope(raw: object) -> JobEnvelope:
    if not isinstance(raw, dict):
        raise InvalidEnvelopeError
    data: dict[str, object] = {str(k): v for k, v in cast("dict[object, object]", raw).items()}
    try:
        run_id = data.get("run_id")
        if isinstance(run_id, str):
            data["run_id"] = UUID(run_id)
        return JobEnvelope.model_validate(data)
    except ValidationError, ValueError:
        raise InvalidEnvelopeError from None


def to_message(envelope: JobEnvelope) -> dict[str, object]:
    message: dict[str, object] = {
        "envelope_version": envelope.envelope_version,
        "run_id": str(envelope.run_id),
        "config_version": envelope.config_version,
    }
    if envelope.request_id is not None:
        message["request_id"] = envelope.request_id
    return message

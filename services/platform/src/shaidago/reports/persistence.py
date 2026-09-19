"""Writing and reading private reports.

The write path is built for the insert-only public role (ADR-0003): identifiers and timestamps come
from the application, every statement is a plain ``INSERT`` with no ``RETURNING``, and nothing is
read back. One transaction holds the description key, the report, the ``received`` event, the
optional contact (with its own key), and the tracking key, so a failure at any step leaves nothing
behind. Text is encrypted before it reaches the database.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import LargeBinary, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.files.pipeline import StoredEvidence
from shaidago.reports.tracking import CHECKSUM_VERSION, TrackingCode, lookup_key
from shaidago.shared.clock import Clock
from shaidago.shared.crypto import FieldCipher, field_context
from shaidago.shared.data_keys import DataKeyService
from shaidago.shared.ids import IdGenerator

SCHEMA_VERSION = 1
MAX_DESCRIPTION_CHARS = 8000
MAX_CONTACT_CHARS = 200
RECEIVED_MESSAGE = "Your report was received. It is private and has not been published."


class InvalidReportError(ValueError):
    """The report content is unusable. The message never repeats it."""


@dataclass(frozen=True)
class ContactInput:
    channel: str
    value: str

    def __repr__(self) -> str:
        return "ContactInput(<redacted>)"


@dataclass(frozen=True)
class NewReport:
    project_id: UUID
    concern_category: str
    description: str
    contact: ContactInput | None = None
    risk_level: str = "standard"

    def __repr__(self) -> str:
        return f"NewReport(project_id={self.project_id}, category={self.concern_category})"


_REPORT = text(
    "INSERT INTO app.reports (id, project_id, concern_category, description_ciphertext, "
    "description_key_id, schema_version, risk_level, anonymous, status, status_updated_at, "
    "created_at, updated_at) VALUES (:id, :project, :category, :ciphertext, :key, :version, "
    ":risk, :anonymous, 'received', :now, :now, :now)"
).bindparams(bindparam("ciphertext", type_=LargeBinary))
_EVENT = text(
    "INSERT INTO app.report_status_events (id, report_id, previous_status, new_status, "
    "public_message, actor_type, actor_id, occurred_at) VALUES "
    "(:id, :report, NULL, 'received', :message, 'reporter', NULL, :now)"
)
_CONTACT = text(
    "INSERT INTO app.report_contacts (id, report_id, channel_ciphertext, value_ciphertext, "
    "data_key_id, schema_version, created_at) VALUES "
    "(:id, :report, :channel, :value, :key, :version, :now)"
).bindparams(bindparam("channel", type_=LargeBinary), bindparam("value", type_=LargeBinary))
_TRACKING = text(
    "INSERT INTO app.report_tracking_keys (id, report_id, lookup_hmac, pepper_version, "
    "checksum_version, created_at) VALUES (:id, :report, :hmac, :pepper, :checksum, :now)"
).bindparams(bindparam("hmac", type_=LargeBinary))
_DESCRIPTION = text(
    "SELECT description_ciphertext, description_key_id, schema_version FROM app.reports "
    "WHERE id = :id"
)


_EVIDENCE = text(
    "INSERT INTO app.evidence_files (id, report_id, object_key, display_name, sniffed_mime, "
    "size_bytes, sha256, sanitation_state, scan_state, created_at) VALUES (:id, :report, :key, "
    ":name, :mime, :size, :sha, :sanitation, :scan, :now)"
)


class ReportWriter:
    def __init__(
        self,
        session: AsyncSession,
        keys: DataKeyService,
        *,
        cipher: FieldCipher,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._session = session
        self._keys = keys
        self._cipher = cipher
        self._clock = clock
        self._ids = ids

    async def insert(
        self, report: NewReport, code: TrackingCode, *, pepper_version: str, pepper: bytes
    ) -> UUID:
        """Store a report atomically and return its internal ID. Nothing is read back."""
        description = report.description.strip()
        if not description or len(description) > MAX_DESCRIPTION_CHARS:
            raise InvalidReportError("description length is not acceptable")
        if report.contact is not None and not (
            0 < len(report.contact.channel) <= MAX_CONTACT_CHARS
            and 0 < len(report.contact.value) <= MAX_CONTACT_CHARS
        ):
            raise InvalidReportError("contact length is not acceptable")
        now = self._clock.now()
        report_id = self._ids.new()
        key = await self._keys.create("reports", report_id, "report_content")
        ciphertext = self._cipher.encrypt(
            key,
            description.encode(),
            field_context("reports", report_id, "description", SCHEMA_VERSION),
        )
        await self._session.execute(
            _REPORT,
            {
                "id": report_id,
                "project": report.project_id,
                "category": report.concern_category,
                "ciphertext": ciphertext,
                "key": key.id,
                "version": SCHEMA_VERSION,
                "risk": report.risk_level,
                "anonymous": report.contact is None,
                "now": now,
            },
        )
        await self._session.execute(
            _EVENT,
            {"id": self._ids.new(), "report": report_id, "message": RECEIVED_MESSAGE, "now": now},
        )
        if report.contact is not None:
            contact_id = self._ids.new()
            contact_key = await self._keys.create("reports", report_id, "contact")
            await self._session.execute(
                _CONTACT,
                {
                    "id": contact_id,
                    "report": report_id,
                    "channel": self._cipher.encrypt(
                        contact_key,
                        report.contact.channel.encode(),
                        field_context("report_contacts", contact_id, "channel", SCHEMA_VERSION),
                    ),
                    "value": self._cipher.encrypt(
                        contact_key,
                        report.contact.value.encode(),
                        field_context("report_contacts", contact_id, "value", SCHEMA_VERSION),
                    ),
                    "key": contact_key.id,
                    "version": SCHEMA_VERSION,
                    "now": now,
                },
            )
        await self._session.execute(
            _TRACKING,
            {
                "id": self._ids.new(),
                "report": report_id,
                "hmac": lookup_key(pepper, code),
                "pepper": pepper_version,
                "checksum": CHECKSUM_VERSION,
                "now": now,
            },
        )
        return report_id

    async def attach_evidence(self, report_id: UUID, stored: StoredEvidence) -> None:
        """Record a sanitised, stored file. The database refuses anything else."""
        await self._session.execute(
            _EVIDENCE,
            {
                "id": self._ids.new(),
                "report": report_id,
                "key": stored.object_key,
                "name": stored.display_name,
                "mime": stored.mime_type,
                "size": stored.size_bytes,
                "sha": stored.sha256,
                "sanitation": stored.sanitation_state,
                "scan": stored.scan_state,
                "now": self._clock.now(),
            },
        )


async def read_description(
    session: AsyncSession, keys: DataKeyService, cipher: FieldCipher, report_id: UUID
) -> str:
    """Decrypt a report's description. Needs a role that can read reports and data keys."""
    row = (await session.execute(_DESCRIPTION, {"id": report_id})).one()
    key = await keys.load(row.description_key_id)
    plaintext = cipher.decrypt(
        key,
        bytes(row.description_ciphertext),
        field_context("reports", report_id, "description", row.schema_version),
    )
    return plaintext.decode()

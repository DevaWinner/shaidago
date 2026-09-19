"""The evidence download broker's rules: who may fetch what, and how it is presented.

Bytes are streamed through an authorised endpoint instead of handing out a storage URL, so there
is no token to leak, replay, or outlive the reviewer's session, and the object key never leaves the
service. Access is decided here, recorded before any byte is read, and only sanitised evidence with
a known scan state is ever served.
"""

import re
from dataclasses import dataclass
from typing import Final
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.audit.events import AuditWriter
from shaidago.files.rules import MIME_EXTENSIONS
from shaidago.review.context import ReviewContext
from shaidago.review.detail import Reviewer

# The scan states a reviewer may be served, and whether the reviewer must be told it is unscanned.
SERVABLE_SCAN_STATES: Final = frozenset({"clean", "not_scanned_demo"})
_FILENAME_UNSAFE: Final = re.compile(r"[^A-Za-z0-9._ -]")

_EVIDENCE = text(
    "SELECT e.id, e.object_key, e.display_name, e.sniffed_mime, e.size_bytes, e.sha256, "
    "e.sanitation_state, e.scan_state FROM app.evidence_files e "
    "WHERE e.id = :evidence AND e.report_id = :report"
)


@dataclass(frozen=True)
class EvidenceRecord:
    id: UUID
    object_key: str
    display_name: str
    mime_type: str
    size_bytes: int
    sha256: str
    sanitation_state: str
    scan_state: str

    def __repr__(self) -> str:
        return f"EvidenceRecord(id={self.id})"


async def find_evidence(
    session: AsyncSession, report_id: UUID, evidence_id: UUID
) -> EvidenceRecord | None:
    """The record only when the evidence belongs to that report; otherwise indistinguishable."""
    row = (
        await session.execute(_EVIDENCE, {"evidence": evidence_id, "report": report_id})
    ).one_or_none()
    if row is None:
        return None
    return EvidenceRecord(
        row.id,
        row.object_key,
        row.display_name,
        row.sniffed_mime,
        row.size_bytes,
        row.sha256,
        row.sanitation_state,
        row.scan_state,
    )


def is_servable(record: EvidenceRecord) -> bool:
    """Only sanitised artifacts with a known scan state, of an allowed type, may be served."""
    return (
        record.sanitation_state == "sanitised"
        and record.scan_state in SERVABLE_SCAN_STATES
        and record.mime_type in MIME_EXTENSIONS
    )


def download_filename(record: EvidenceRecord) -> str:
    """A plain ASCII name whose extension matches the stored type; never a path or quote."""
    extension = MIME_EXTENSIONS[record.mime_type]
    stem = _FILENAME_UNSAFE.sub("", record.display_name.rsplit(".", 1)[0]).strip(" .-_")[:60]
    return f"{stem or 'evidence'}.{extension}"


def content_headers(record: EvidenceRecord) -> dict[str, str]:
    """Headers that make a browser save the bytes, never render, cache, or sniff them."""
    return {
        "Content-Type": record.mime_type,
        "Content-Disposition": f'attachment; filename="{download_filename(record)}"',
        "Cache-Control": "no-store",
        "Pragma": "no-cache",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; sandbox",
        "Cross-Origin-Resource-Policy": "same-origin",
        # The hosted demo has no scanner; the reviewer must be able to see that.
        "X-Evidence-Scan-State": record.scan_state,
    }


async def record_download_decision(
    ctx: ReviewContext,
    reviewer: Reviewer,
    report_id: UUID,
    evidence_id: UUID,
    denied_reason: str | None = None,
) -> None:
    """Audit the decision (never a URL or a token; none exists). No reason means granted."""
    granted = denied_reason is None
    await AuditWriter(ctx.session, ctx.clock, ctx.ids).record(
        "report_evidence_download_granted" if granted else "report_evidence_download_denied",
        actor_type=reviewer.actor_type,
        actor_id=reviewer.actor_id,
        subject_type="report",
        subject_id=report_id,
        outcome="success" if granted else "denied",
        request_id=reviewer.request_id,
        details={"evidence_id": str(evidence_id)}
        | ({} if denied_reason is None else {"reason": denied_reason}),
    )

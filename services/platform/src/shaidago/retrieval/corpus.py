"""Build the Q&A corpus from the database's approved-public-source projection only.

The worker never receives a report table or arbitrary text input. It reads the narrow
``app.approved_source_documents`` view, deterministically chunks each immutable version, and
deactivates rows that are no longer eligible. The public retrieval view repeats the live
eligibility checks, so an interrupted refresh still fails closed.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.retrieval.chunking import CHUNKER_VERSION, ChunkSpan, chunk_text
from shaidago.shared.clock import Clock
from shaidago.shared.ids import IdGenerator

_DOCUMENTS = text(
    "SELECT project_id, source_id, source_version_id, content_text, language "
    "FROM app.approved_source_documents ORDER BY project_id, source_version_id"
)
_DEACTIVATE_INELIGIBLE = text(
    "UPDATE app.source_chunks c SET active = false, updated_at = :now "
    "WHERE c.active AND NOT EXISTS ("
    "SELECT 1 FROM app.approved_source_documents d "
    "WHERE d.project_id = c.project_id AND d.source_id = c.source_id "
    "AND d.source_version_id = c.source_version_id AND d.language = c.language) "
    "RETURNING c.id"
)
_EXISTING = text(
    "SELECT id, chunk_index, passage_start, passage_end, content_text, text_sha256, token_count, "
    "section_label, chunker_version, active FROM app.source_chunks "
    "WHERE project_id = :project AND source_version_id = :version AND language = :language"
)
_INSERT = text(
    "INSERT INTO app.source_chunks "
    "(id, project_id, source_id, source_version_id, chunk_index, passage_start, passage_end, "
    "content_text, text_sha256, token_count, language, section_label, chunker_version, active, "
    "created_at, updated_at) VALUES "
    "(:id, :project, :source, :version, :index, :start, :end, :content, :sha, :tokens, "
    ":language, :section, :chunker, true, :now, :now)"
)
_UPDATE = text(
    "UPDATE app.source_chunks SET source_id = :source, passage_start = :start, "
    "passage_end = :end, content_text = :content, text_sha256 = :sha, token_count = :tokens, "
    "section_label = :section, chunker_version = :chunker, active = true, updated_at = :now "
    "WHERE id = :id"
)
_DEACTIVATE_SURPLUS = text(
    "UPDATE app.source_chunks SET active = false, updated_at = :now "
    "WHERE project_id = :project AND source_version_id = :version AND language = :language "
    "AND active AND chunk_index >= :count RETURNING id"
)


@dataclass(frozen=True)
class ApprovedDocument:
    project_id: UUID
    source_id: UUID
    source_version_id: UUID
    content_text: str
    language: str


@dataclass(frozen=True)
class CorpusRefresh:
    documents: int
    inserted: int
    reactivated_or_changed: int
    unchanged: int
    deactivated: int


@dataclass(frozen=True)
class ExistingChunk:
    id: UUID
    chunk_index: int
    passage_start: int
    passage_end: int
    content_text: str
    text_sha256: str
    token_count: int
    section_label: str | None
    chunker_version: str
    active: bool


def _same(row: ExistingChunk, chunk: ChunkSpan) -> bool:
    return (
        row.passage_start == chunk.start
        and row.passage_end == chunk.end
        and row.content_text == chunk.text
        and row.text_sha256 == chunk.text_sha256
        and row.token_count == chunk.token_count
        and row.section_label == chunk.section_label
        and row.chunker_version == CHUNKER_VERSION
        and row.active is True
    )


class CorpusBuilder:
    """One transactional refresh. Call it from the worker or an explicit maintenance command."""

    def __init__(self, session: AsyncSession, *, clock: Clock, ids: IdGenerator) -> None:
        self._session = session
        self._clock = clock
        self._ids = ids

    async def refresh(self) -> CorpusRefresh:
        now = self._clock.now()
        deactivated = len((await self._session.execute(_DEACTIVATE_INELIGIBLE, {"now": now})).all())
        documents = [
            ApprovedDocument(*row) for row in (await self._session.execute(_DOCUMENTS)).all()
        ]
        inserted = changed = unchanged = 0
        for document in documents:
            chunks = chunk_text(document.content_text)
            existing = {
                row.chunk_index: row
                for row in [
                    ExistingChunk(*values)
                    for values in (
                        await self._session.execute(
                            _EXISTING,
                            {
                                "project": document.project_id,
                                "version": document.source_version_id,
                                "language": document.language,
                            },
                        )
                    ).all()
                ]
            }
            for chunk in chunks:
                row = existing.get(chunk.index)
                if row is None:
                    await self._session.execute(
                        _INSERT,
                        self._values(document, chunk, now) | {"id": self._ids.new()},
                    )
                    inserted += 1
                elif _same(row, chunk):
                    unchanged += 1
                else:
                    await self._session.execute(
                        _UPDATE,
                        self._values(document, chunk, now) | {"id": row.id},
                    )
                    changed += 1
            surplus = (
                await self._session.execute(
                    _DEACTIVATE_SURPLUS,
                    {
                        "project": document.project_id,
                        "version": document.source_version_id,
                        "language": document.language,
                        "count": len(chunks),
                        "now": now,
                    },
                )
            ).all()
            deactivated += len(surplus)
        return CorpusRefresh(
            documents=len(documents),
            inserted=inserted,
            reactivated_or_changed=changed,
            unchanged=unchanged,
            deactivated=deactivated,
        )

    @staticmethod
    def _values(document: ApprovedDocument, chunk: ChunkSpan, now: datetime) -> dict[str, object]:
        return {
            "project": document.project_id,
            "source": document.source_id,
            "version": document.source_version_id,
            "index": chunk.index,
            "start": chunk.start,
            "end": chunk.end,
            "content": chunk.text,
            "sha": chunk.text_sha256,
            "tokens": chunk.token_count,
            "language": document.language,
            "section": chunk.section_label,
            "chunker": CHUNKER_VERSION,
            "now": now,
        }

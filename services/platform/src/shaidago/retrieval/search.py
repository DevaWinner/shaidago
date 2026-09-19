"""Project-isolated full-text and vector retrieval with reciprocal-rank fusion."""

import math
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import TextClause, text
from sqlalchemy.ext.asyncio import AsyncSession

EMBEDDING_DIMENSIONS = 1536
MAX_QUERY_CHARS = 300
MAX_RESULTS = 10
RRF_K = 60
EMBEDDING_MODEL_MAX_CHARS = 100
VECTOR_ABS_MAX = 100
MAX_KEYWORD_TERMS = 30

_QUERY_TERMS = re.compile(r"[^\W_]+", re.UNICODE)

RetrievalMode = Literal["keyword", "hybrid"]

_KEYWORD = text(
    "WITH eligible AS ("
    "SELECT * FROM public_api.source_chunks WHERE project_id = :project), "
    "query AS (SELECT websearch_to_tsquery('simple', :query) value), "
    "ranked AS (SELECT e.*, row_number() OVER (ORDER BY "
    "ts_rank_cd(e.search_vector, q.value) DESC, e.text_sha256, e.source_version_id, "
    "e.chunk_index) keyword_rank FROM eligible e CROSS JOIN query q "
    "WHERE e.search_vector @@ q.value) "
    "SELECT *, (1.0 / (:rrf_k + keyword_rank)) AS score, false AS semantic_used "
    "FROM ranked ORDER BY score DESC, keyword_rank, text_sha256, source_version_id, chunk_index "
    "LIMIT :limit"
)

_HYBRID = text(
    "WITH eligible AS ("
    "SELECT * FROM public_api.source_chunks WHERE project_id = :project), "
    "query AS (SELECT websearch_to_tsquery('simple', :query) value), "
    "keyword AS (SELECT e.id, row_number() OVER (ORDER BY "
    "ts_rank_cd(e.search_vector, q.value) DESC, e.text_sha256, e.source_version_id, "
    "e.chunk_index) keyword_rank FROM eligible e CROSS JOIN query q "
    "WHERE e.search_vector @@ q.value), "
    "semantic AS (SELECT e.id, row_number() OVER (ORDER BY "
    "e.embedding <=> CAST(:embedding AS vector), e.text_sha256, e.source_version_id, "
    "e.chunk_index) semantic_rank FROM eligible e "
    "WHERE e.embedding IS NOT NULL AND e.embedding_model = :model), "
    "combined AS (SELECT COALESCE(k.id, s.id) id, k.keyword_rank, s.semantic_rank "
    "FROM keyword k FULL OUTER JOIN semantic s ON s.id = k.id), "
    "ranked AS (SELECT e.*, c.keyword_rank, c.semantic_rank, "
    "COALESCE(1.0 / (:rrf_k + c.keyword_rank), 0.0) + "
    "COALESCE(1.0 / (:rrf_k + c.semantic_rank), 0.0) AS score, "
    "bool_or(c.semantic_rank IS NOT NULL) OVER () AS semantic_used "
    "FROM combined c JOIN eligible e ON e.id = c.id) "
    "SELECT * FROM ranked ORDER BY score DESC, keyword_rank NULLS LAST, "
    "semantic_rank NULLS LAST, text_sha256, source_version_id, chunk_index LIMIT :limit"
)


@dataclass(frozen=True)
class RetrievedChunk:
    id: UUID
    project_id: UUID
    source_id: UUID
    source_version_id: UUID
    text: str
    text_sha256: str
    token_count: int
    language: str
    section_label: str | None
    passage_start: int
    passage_end: int
    source_title: str
    publisher: str
    canonical_url: str
    retrieved_at: datetime
    score: float


@dataclass(frozen=True)
class RetrievalResult:
    mode: RetrievalMode
    query: str
    chunks: tuple[RetrievedChunk, ...]


def normalise_query(value: str) -> str:
    """Bound and normalise untrusted text before it reaches PostgreSQL or a provider."""
    normalised = unicodedata.normalize("NFKC", value).strip()
    if not normalised:
        raise ValueError("query must not be empty")
    if len(normalised) > MAX_QUERY_CHARS:
        raise ValueError("query is too long")
    if any(unicodedata.category(character).startswith("C") for character in normalised):
        raise ValueError("query contains unsupported control characters")
    return normalised


def keyword_expression(value: str) -> str:
    """Build a bounded web-search OR query so conversational filler cannot hide a useful hit."""
    normalised = normalise_query(value)
    terms = list(dict.fromkeys(_QUERY_TERMS.findall(normalised.casefold())))[:MAX_KEYWORD_TERMS]
    return " OR ".join(terms)


def vector_literal(values: Sequence[float]) -> str:
    if len(values) != EMBEDDING_DIMENSIONS:
        raise ValueError(f"embedding must have {EMBEDDING_DIMENSIONS} dimensions")
    if not all(
        math.isfinite(value) and -VECTOR_ABS_MAX <= value <= VECTOR_ABS_MAX for value in values
    ):
        raise ValueError("embedding contains an invalid value")
    return "[" + ",".join(format(value, ".9g") for value in values) + "]"


class Retriever:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(
        self,
        project_id: UUID,
        query: str,
        *,
        query_embedding: Sequence[float] | None = None,
        embedding_model: str | None = None,
        limit: int = 5,
    ) -> RetrievalResult:
        safe_query = normalise_query(query)
        if not 1 <= limit <= MAX_RESULTS:
            raise ValueError(f"limit must be between 1 and {MAX_RESULTS}")
        statement: TextClause = _KEYWORD
        parameters: dict[str, object] = {
            "project": project_id,
            "query": keyword_expression(safe_query),
            "rrf_k": RRF_K,
            "limit": limit,
        }
        if query_embedding is not None:
            if not embedding_model or len(embedding_model) > EMBEDDING_MODEL_MAX_CHARS:
                raise ValueError("embedding model is required")
            statement = _HYBRID
            parameters |= {
                "embedding": vector_literal(query_embedding),
                "model": embedding_model,
            }
        rows = (await self._session.execute(statement, parameters)).all()
        mode: RetrievalMode = "hybrid" if rows and bool(rows[0].semantic_used) else "keyword"
        chunks = tuple(
            RetrievedChunk(
                id=row.id,
                project_id=row.project_id,
                source_id=row.source_id,
                source_version_id=row.source_version_id,
                text=row.content_text,
                text_sha256=row.text_sha256,
                token_count=row.token_count,
                language=row.language,
                section_label=row.section_label,
                passage_start=row.passage_start,
                passage_end=row.passage_end,
                source_title=row.source_title,
                publisher=row.publisher,
                canonical_url=row.canonical_url,
                retrieved_at=row.retrieved_at,
                score=float(row.score),
            )
            for row in rows
        )
        return RetrievalResult(mode=mode, query=safe_query, chunks=chunks)

"""Chunk embeddings become 384-dimensional for multilingual-e5-small (BE-081, ADR-0010).

Revision ID: 0027_embedding_384
Revises: 0026_citation_version_id

`app.source_chunks.embedding` was `vector(1536)`, sized for a hosted provider model. Retrieval now
embeds locally with multilingual-e5-small, whose vectors have 384 dimensions, so the column type,
the HNSW index and the public view are rebuilt around the new width.

Vectors from one model cannot be compared with vectors from another, so every stored vector is
cleared rather than converted. That loses nothing that cannot be regenerated: an embedding is
derived data, keyed by the SHA-256 of an immutable chunk text, and `make embeddings` rebuilds it.
The chunks themselves, and keyword retrieval, are untouched throughout.

`public_api.source_chunks` selects the column, so it depends on its type and is dropped and rebuilt
around the change. The rebuilt view is identical to the one from migration 0019.
"""

from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0027_embedding_384"
down_revision = "0026_citation_version_id"
branch_labels = None
depends_on = None

PUBLIC_VIEW = """
CREATE VIEW public_api.source_chunks WITH (security_barrier = true) AS
SELECT c.id, c.project_id, p.slug AS project_slug, c.source_id, c.source_version_id,
       c.chunk_index, c.passage_start, c.passage_end, c.content_text, c.text_sha256,
       c.token_count, c.language, c.section_label, c.chunker_version,
       s.title AS source_title, s.publisher, s.canonical_url, s.source_type,
       s.information_class, s.availability_checked_at, v.retrieved_at,
       c.search_vector, c.embedding, c.embedding_model
FROM app.source_chunks c
JOIN app.projects p ON p.id = c.project_id AND p.visibility = 'public'
JOIN app.sources s ON s.id = c.source_id AND s.availability = 'available'
JOIN app.source_versions v ON v.id = c.source_version_id AND v.source_id = s.id
    AND v.review_state = 'approved' AND v.language = c.language
WHERE c.active AND EXISTS (
    SELECT 1 FROM app.approved_source_documents d
    WHERE d.project_id = c.project_id AND d.source_id = c.source_id
      AND d.source_version_id = c.source_version_id AND d.language = c.language
)
"""


def _retype(dimensions: int) -> None:
    use_owner_role()
    op.execute("DROP VIEW public_api.source_chunks")
    op.execute("DROP INDEX app.ix_source_chunks_embedding_cosine")
    # The three columns are all null or all set (ck_source_chunks_embedding_complete), so they are
    # cleared together, in one statement, to keep that constraint satisfied.
    op.execute(
        "UPDATE app.source_chunks SET embedding = NULL, embedding_model = NULL, "
        "embedded_at = NULL WHERE embedding IS NOT NULL"
    )
    op.execute(f"ALTER TABLE app.source_chunks ALTER COLUMN embedding TYPE vector({dimensions})")
    op.execute(
        "CREATE INDEX ix_source_chunks_embedding_cosine ON app.source_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(PUBLIC_VIEW)


def upgrade() -> None:
    _retype(384)


def downgrade() -> None:
    # Returns the width only. The vectors were cleared on the way up and stay cleared: they belong
    # to a model that the previous width no longer describes.
    _retype(1536)

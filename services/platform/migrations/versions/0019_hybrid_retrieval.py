"""Full-text and pgvector columns for project-scoped hybrid retrieval (BE-081).

Revision ID: 0019_hybrid_retrieval
Revises: 0018_approved_source_chunks

The text vector is generated from the already verified chunk text. Embeddings are nullable and
carry their model and generation time together, which makes keyword-only operation an explicit
first-class state rather than a startup failure.
"""

from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0019_hybrid_retrieval"
down_revision = "0018_approved_source_chunks"
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

OLD_PUBLIC_VIEW = """
CREATE VIEW public_api.source_chunks WITH (security_barrier = true) AS
SELECT c.id, c.project_id, p.slug AS project_slug, c.source_id, c.source_version_id,
       c.chunk_index, c.passage_start, c.passage_end, c.content_text, c.text_sha256,
       c.token_count, c.language, c.section_label, c.chunker_version,
       s.title AS source_title, s.publisher, s.canonical_url, s.source_type,
       s.information_class, s.availability_checked_at, v.retrieved_at
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


def upgrade() -> None:
    use_owner_role()
    op.execute("DROP VIEW public_api.source_chunks")
    op.execute(
        "ALTER TABLE app.source_chunks ADD COLUMN search_vector tsvector "
        "GENERATED ALWAYS AS (to_tsvector('simple', content_text)) STORED"
    )
    op.execute("ALTER TABLE app.source_chunks ADD COLUMN embedding vector(1536)")
    op.execute("ALTER TABLE app.source_chunks ADD COLUMN embedding_model text")
    op.execute("ALTER TABLE app.source_chunks ADD COLUMN embedded_at timestamptz")
    op.execute(
        "ALTER TABLE app.source_chunks ADD CONSTRAINT ck_source_chunks_embedding_complete "
        "CHECK ((embedding IS NULL AND embedding_model IS NULL AND embedded_at IS NULL) OR "
        "(embedding IS NOT NULL AND embedding_model IS NOT NULL AND embedded_at IS NOT NULL))"
    )
    op.execute(
        "ALTER TABLE app.source_chunks ADD CONSTRAINT ck_source_chunks_embedding_model "
        "CHECK (embedding_model IS NULL OR char_length(embedding_model) BETWEEN 1 AND 100)"
    )
    op.execute(
        "CREATE INDEX ix_source_chunks_search_vector ON app.source_chunks USING gin (search_vector)"
    )
    op.execute(
        "CREATE INDEX ix_source_chunks_embedding_cosine ON app.source_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "GRANT UPDATE (embedding, embedding_model, embedded_at, updated_at) "
        "ON app.source_chunks TO shaidago_worker"
    )
    op.execute(PUBLIC_VIEW)


def downgrade() -> None:
    use_owner_role()
    op.execute("DROP VIEW public_api.source_chunks")
    op.execute("DROP INDEX app.ix_source_chunks_embedding_cosine")
    op.execute("DROP INDEX app.ix_source_chunks_search_vector")
    op.execute("ALTER TABLE app.source_chunks DROP CONSTRAINT ck_source_chunks_embedding_model")
    op.execute("ALTER TABLE app.source_chunks DROP CONSTRAINT ck_source_chunks_embedding_complete")
    op.execute("ALTER TABLE app.source_chunks DROP COLUMN embedded_at")
    op.execute("ALTER TABLE app.source_chunks DROP COLUMN embedding_model")
    op.execute("ALTER TABLE app.source_chunks DROP COLUMN embedding")
    op.execute("ALTER TABLE app.source_chunks DROP COLUMN search_vector")
    op.execute(OLD_PUBLIC_VIEW)

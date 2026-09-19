"""Approved, project-scoped source chunks for grounded retrieval (BE-080).

Revision ID: 0018_approved_source_chunks
Revises: 0017_public_updates

Only a worker may populate the corpus, and the database checks every active row against the
immutable source text and the current public/approved/available eligibility boundary. The public
role reads a view that repeats those live checks, so a stale active flag cannot expose a source
after its approval or availability changes. Source versions remain immutable; corpus rows are
deactivated rather than deleting or rewriting the evidence they came from.
"""

from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0018_approved_source_chunks"
down_revision = "0017_public_updates"
branch_labels = None
depends_on = None

PROTECT_VERSIONS = """
CREATE OR REPLACE FUNCTION app.protect_source_versions() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, app AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'source versions are immutable evidence and cannot be deleted'
            USING ERRCODE = '55000';
    END IF;
    IF (NEW.id, NEW.source_id, NEW.content_sha256, NEW.content_text, NEW.media_type,
        NEW.retrieved_at, NEW.created_at, NEW.language)
       IS DISTINCT FROM
       (OLD.id, OLD.source_id, OLD.content_sha256, OLD.content_text, OLD.media_type,
        OLD.retrieved_at, OLD.created_at, OLD.language) THEN
        RAISE EXCEPTION 'source version content is immutable; add a new version'
            USING ERRCODE = '55000';
    END IF;
    IF NEW.review_state <> OLD.review_state AND NOT (
        (OLD.review_state = 'pending' AND NEW.review_state = 'in_review')
        OR (OLD.review_state = 'in_review' AND NEW.review_state IN ('approved', 'rejected'))
        OR (OLD.review_state = 'approved' AND NEW.review_state IN ('in_review', 'superseded'))
        OR (OLD.review_state IN ('rejected', 'superseded') AND NEW.review_state = 'in_review')
    ) THEN
        RAISE EXCEPTION 'illegal source review transition' USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END
$$
"""

RESTORE_PROTECT_VERSIONS = """
CREATE OR REPLACE FUNCTION app.protect_source_versions() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, app AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'source versions are immutable evidence and cannot be deleted'
            USING ERRCODE = '55000';
    END IF;
    IF (NEW.id, NEW.source_id, NEW.content_sha256, NEW.content_text, NEW.media_type,
        NEW.retrieved_at, NEW.created_at)
       IS DISTINCT FROM
       (OLD.id, OLD.source_id, OLD.content_sha256, OLD.content_text, OLD.media_type,
        OLD.retrieved_at, OLD.created_at) THEN
        RAISE EXCEPTION 'source version content is immutable; add a new version'
            USING ERRCODE = '55000';
    END IF;
    IF NEW.review_state <> OLD.review_state AND NOT (
        (OLD.review_state = 'pending' AND NEW.review_state = 'in_review')
        OR (OLD.review_state = 'in_review' AND NEW.review_state IN ('approved', 'rejected'))
        OR (OLD.review_state = 'approved' AND NEW.review_state IN ('in_review', 'superseded'))
        OR (OLD.review_state IN ('rejected', 'superseded') AND NEW.review_state = 'in_review')
    ) THEN
        RAISE EXCEPTION 'illegal source review transition' USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END
$$
"""

CHUNKS = """
CREATE TABLE app.source_chunks (
    id uuid NOT NULL,
    project_id uuid NOT NULL,
    source_id uuid NOT NULL,
    source_version_id uuid NOT NULL,
    chunk_index integer NOT NULL,
    passage_start integer NOT NULL,
    passage_end integer NOT NULL,
    content_text text NOT NULL,
    text_sha256 text NOT NULL,
    token_count integer NOT NULL,
    language text NOT NULL,
    section_label text,
    chunker_version text NOT NULL,
    active boolean NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT pk_source_chunks PRIMARY KEY (id),
    CONSTRAINT fk_source_chunks_project_id_projects
        FOREIGN KEY (project_id) REFERENCES app.projects (id) ON DELETE RESTRICT,
    CONSTRAINT fk_source_chunks_source_id_sources
        FOREIGN KEY (source_id) REFERENCES app.sources (id) ON DELETE RESTRICT,
    CONSTRAINT fk_source_chunks_source_version_id_source_versions
        FOREIGN KEY (source_version_id) REFERENCES app.source_versions (id) ON DELETE RESTRICT,
    CONSTRAINT uq_source_chunks_project_version_language_index
        UNIQUE (project_id, source_version_id, language, chunk_index),
    CONSTRAINT ck_source_chunks_index_nonnegative CHECK (chunk_index >= 0),
    CONSTRAINT ck_source_chunks_passage_span CHECK (
        passage_start >= 0 AND passage_end > passage_start),
    CONSTRAINT ck_source_chunks_content_bounded CHECK (
        char_length(content_text) BETWEEN 1 AND 900),
    CONSTRAINT ck_source_chunks_hash CHECK (text_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_source_chunks_token_count CHECK (token_count BETWEEN 1 AND 2000),
    CONSTRAINT ck_source_chunks_language CHECK (language IN ('en', 'ha', 'ig', 'yo')),
    CONSTRAINT ck_source_chunks_section_label CHECK (
        section_label IS NULL OR char_length(section_label) BETWEEN 1 AND 200),
    CONSTRAINT ck_source_chunks_chunker_version CHECK (
        chunker_version ~ '^[a-z0-9][a-z0-9-]*-v[0-9]+$')
)
"""

ELIGIBLE_DOCUMENTS = """
CREATE VIEW app.approved_source_documents WITH (security_barrier = true) AS
SELECT DISTINCT links.project_id, s.id AS source_id, v.id AS source_version_id,
       v.content_text, v.language
FROM (
    SELECT f.project_id, c.source_version_id
    FROM app.project_facts f
    JOIN app.fact_citations c ON c.fact_id = f.id
    WHERE f.visibility = 'public'
    UNION
    SELECT u.project_id, c.source_version_id
    FROM app.project_updates u
    JOIN app.update_citations c ON c.update_id = u.id
    WHERE u.visibility = 'public'
) links
JOIN app.projects p ON p.id = links.project_id AND p.visibility = 'public'
JOIN app.source_versions v ON v.id = links.source_version_id AND v.review_state = 'approved'
JOIN app.sources s ON s.id = v.source_id AND s.availability = 'available'
"""

VERIFY_CHUNK = """
CREATE FUNCTION app.verify_source_chunk() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, app AS $$
DECLARE
    version_text text;
    version_source uuid;
    version_language text;
BEGIN
    SELECT v.content_text, v.source_id, v.language
    INTO version_text, version_source, version_language
    FROM app.source_versions v WHERE v.id = NEW.source_version_id;
    IF version_source IS DISTINCT FROM NEW.source_id
       OR version_language IS DISTINCT FROM NEW.language
       OR substr(version_text, NEW.passage_start + 1,
                 NEW.passage_end - NEW.passage_start) IS DISTINCT FROM NEW.content_text
       OR char_length(NEW.content_text) IS DISTINCT FROM NEW.passage_end - NEW.passage_start
       OR encode(sha256(convert_to(NEW.content_text, 'UTF8')), 'hex') <> NEW.text_sha256 THEN
        RAISE EXCEPTION 'source chunk does not match its immutable source version'
            USING ERRCODE = '23514', CONSTRAINT = 'source_chunk_exact';
    END IF;
    IF NEW.active AND NOT EXISTS (
        SELECT 1 FROM app.approved_source_documents d
        WHERE d.project_id = NEW.project_id AND d.source_id = NEW.source_id
          AND d.source_version_id = NEW.source_version_id AND d.language = NEW.language
    ) THEN
        RAISE EXCEPTION 'active source chunk is outside the approved public corpus'
            USING ERRCODE = '23514', CONSTRAINT = 'source_chunk_eligible';
    END IF;
    RETURN NEW;
END
$$
"""

PUBLIC_VIEW = """
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
    op.execute("ALTER TABLE app.source_versions ADD COLUMN language text NOT NULL DEFAULT 'en'")
    op.execute(
        "ALTER TABLE app.source_versions ADD CONSTRAINT ck_source_versions_language "
        "CHECK (language IN ('en', 'ha', 'ig', 'yo'))"
    )
    op.execute(PROTECT_VERSIONS)
    op.execute(CHUNKS)
    op.execute(
        "CREATE INDEX ix_source_chunks_project_active ON app.source_chunks (project_id, active)"
    )
    op.execute("CREATE INDEX ix_source_chunks_version ON app.source_chunks (source_version_id)")
    op.execute(ELIGIBLE_DOCUMENTS)
    op.execute(VERIFY_CHUNK)
    op.execute(
        "CREATE TRIGGER source_chunks_verify BEFORE INSERT OR UPDATE ON app.source_chunks "
        "FOR EACH ROW EXECUTE FUNCTION app.verify_source_chunk()"
    )
    op.execute("ALTER TABLE app.source_chunks ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE app.source_chunks FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY source_chunks_owner_all ON app.source_chunks TO shaidago_owner "
        "USING (true) WITH CHECK (true)"
    )
    op.execute(
        "CREATE POLICY source_chunks_worker_all ON app.source_chunks TO shaidago_worker "
        "USING (true) WITH CHECK (true)"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON app.source_chunks TO shaidago_worker")
    op.execute("GRANT SELECT ON app.approved_source_documents TO shaidago_worker")
    op.execute(PUBLIC_VIEW)


def downgrade() -> None:
    use_owner_role()
    op.execute("DROP VIEW public_api.source_chunks")
    op.execute("DROP VIEW app.approved_source_documents")
    op.execute("DROP TABLE app.source_chunks")
    op.execute("DROP FUNCTION app.verify_source_chunk()")
    op.execute(RESTORE_PROTECT_VERSIONS)
    op.execute("ALTER TABLE app.source_versions DROP CONSTRAINT ck_source_versions_language")
    op.execute("ALTER TABLE app.source_versions DROP COLUMN language")

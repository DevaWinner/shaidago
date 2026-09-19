"""Sources, immutable source versions, facts, updates, and citations (BE-041).

Revision ID: 0004_sources_facts_citations
Revises: 0003_projects_translations

Rules enforced in the database, so no code path can bypass them:

* a source version is content-addressed (its hash must equal the SHA-256 of its text), is never
  deleted, and never has its content changed; only its review state moves, along the
  ``source_review_state`` machine;
* a citation carries an exact passage of bounded length plus its offset, and the passage must
  equal the text at that offset in the cited version;
* a public fact or update needs at least one citation to an approved or superseded version, a
  visible date, and (for facts) a verification state other than "awaiting verification"; this is
  checked at commit, so publication is all-or-nothing;
* a version cited by a public fact or update cannot leave the citable states while it is the only
  support.
"""

import sqlalchemy as sa  # noqa: F401 - kept for revision-template parity
from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0004_sources_facts_citations"
down_revision = "0003_projects_translations"
branch_labels = None
depends_on = None

SOURCE_TYPES = (
    "'government_publication', 'budget_document', 'procurement_record', "
    "'audit_oversight_report', 'independent_media', 'civic_research', 'community_evidence', "
    "'other_public_source'"
)
INFORMATION_CLASSES = "'official_source', 'independent_source', 'community_evidence_reviewed'"
AVAILABILITIES = (
    "'unchecked', 'available', 'temporarily_unavailable', 'access_restricted', "
    "'permanently_unavailable'"
)
REVIEW_STATES = "'pending', 'in_review', 'approved', 'rejected', 'superseded'"
VERIFICATION_STATES = (
    "'awaiting_verification', 'verified_official', 'corroborated', 'community_reviewed', "
    "'disputed', 'outdated'"
)

SOURCES_DDL = f"""
CREATE TABLE app.sources (
    id uuid NOT NULL,
    canonical_url text NOT NULL,
    title text NOT NULL,
    publisher text NOT NULL,
    source_type text NOT NULL,
    information_class text NOT NULL,
    availability text NOT NULL,
    availability_checked_at timestamptz,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT pk_sources PRIMARY KEY (id),
    CONSTRAINT uq_sources_canonical_url UNIQUE (canonical_url),
    CONSTRAINT ck_sources_url CHECK (
        canonical_url ~ '^https?://[^[:space:]]+$' AND char_length(canonical_url) <= 2048),
    CONSTRAINT ck_sources_text CHECK (title <> '' AND publisher <> ''),
    CONSTRAINT ck_sources_source_type CHECK (source_type IN ({SOURCE_TYPES})),
    CONSTRAINT ck_sources_information_class CHECK (information_class IN ({INFORMATION_CLASSES})),
    CONSTRAINT ck_sources_availability CHECK (availability IN ({AVAILABILITIES}))
)
"""

VERSIONS_DDL = f"""
CREATE TABLE app.source_versions (
    id uuid NOT NULL,
    source_id uuid NOT NULL,
    content_sha256 text NOT NULL,
    content_text text NOT NULL,
    media_type text NOT NULL,
    retrieved_at timestamptz NOT NULL,
    review_state text NOT NULL,
    reviewed_at timestamptz,
    reviewer_note text,
    created_at timestamptz NOT NULL,
    CONSTRAINT pk_source_versions PRIMARY KEY (id),
    CONSTRAINT uq_source_versions_source_id_content_sha256 UNIQUE (source_id, content_sha256),
    CONSTRAINT fk_source_versions_source_id_sources
        FOREIGN KEY (source_id) REFERENCES app.sources (id) ON DELETE RESTRICT,
    CONSTRAINT ck_source_versions_content_addressed CHECK (
        content_sha256 = encode(sha256(convert_to(content_text, 'UTF8')), 'hex')),
    CONSTRAINT ck_source_versions_content_bounded CHECK (
        char_length(content_text) BETWEEN 1 AND 500000),
    CONSTRAINT ck_source_versions_media_type CHECK (media_type ~ '^[a-z0-9.+-]+/[a-z0-9.+-]+$'),
    CONSTRAINT ck_source_versions_review_state CHECK (review_state IN ({REVIEW_STATES})),
    CONSTRAINT ck_source_versions_decision_dated CHECK (
        review_state IN ('pending', 'in_review') OR reviewed_at IS NOT NULL)
)
"""

PROTECT_VERSIONS = """
CREATE FUNCTION app.protect_source_versions() RETURNS trigger
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

VERIFY_PASSAGE = """
CREATE FUNCTION app.verify_citation_passage() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, app AS $$
DECLARE
    version_text text;
BEGIN
    SELECT v.content_text INTO version_text FROM app.source_versions v
    WHERE v.id = NEW.source_version_id;
    IF substr(version_text, NEW.passage_start + 1, char_length(NEW.passage)) IS DISTINCT FROM
       NEW.passage THEN
        RAISE EXCEPTION 'the passage does not match the cited source version at its offset'
            USING ERRCODE = '23514', CONSTRAINT = 'citation_passage_exact';
    END IF;
    RETURN NEW;
END
$$
"""


def claim_ddl(table: str, *, with_kind: bool) -> str:
    kind_column = "    kind text NOT NULL,\n" if with_kind else ""
    kind_check = (
        f"    CONSTRAINT ck_{table}_kind CHECK (kind ~ '^[a-z0-9]+(_[a-z0-9]+)*$'),\n"
        if with_kind
        else ""
    )
    effective_check = (
        ""
        if with_kind
        else f"    CONSTRAINT ck_{table}_effective_date CHECK "
        "(visibility = 'draft' OR effective_on IS NOT NULL),\n"
    )
    return f"""
CREATE TABLE app.{table} (
    id uuid NOT NULL,
    project_id uuid NOT NULL,
{kind_column}    statement text NOT NULL,
    effective_on date,
    last_checked_on date,
    verification_state text NOT NULL,
    visibility text NOT NULL,
    published_at timestamptz,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT pk_{table} PRIMARY KEY (id),
    CONSTRAINT fk_{table}_project_id_projects
        FOREIGN KEY (project_id) REFERENCES app.projects (id) ON DELETE RESTRICT,
{kind_check}    CONSTRAINT ck_{table}_statement CHECK (char_length(statement) BETWEEN 1 AND 2000),
    CONSTRAINT ck_{table}_verification_state CHECK (verification_state IN ({VERIFICATION_STATES})),
    CONSTRAINT ck_{table}_visibility CHECK (visibility IN ('draft', 'public')),
    CONSTRAINT ck_{table}_public_complete CHECK (
        visibility = 'draft' OR (
            published_at IS NOT NULL
            AND verification_state <> 'awaiting_verification'
            AND (effective_on IS NOT NULL OR last_checked_on IS NOT NULL))),
{effective_check}    CONSTRAINT ck_{table}_last_checked_not_future CHECK (
        last_checked_on IS NULL
        OR last_checked_on <= (updated_at AT TIME ZONE 'Africa/Lagos')::date)
)
"""


def citation_ddl(table: str, parent: str, parent_column: str) -> str:
    return f"""
CREATE TABLE app.{table} (
    id uuid NOT NULL,
    {parent_column} uuid NOT NULL,
    source_version_id uuid NOT NULL,
    passage text NOT NULL,
    location_label text NOT NULL,
    passage_start integer NOT NULL,
    created_at timestamptz NOT NULL,
    CONSTRAINT pk_{table} PRIMARY KEY (id),
    CONSTRAINT uq_{table}_{parent_column}_source_version_id_location_label
        UNIQUE ({parent_column}, source_version_id, location_label),
    CONSTRAINT fk_{table}_{parent_column}_{parent}
        FOREIGN KEY ({parent_column}) REFERENCES app.{parent} (id) ON DELETE CASCADE,
    CONSTRAINT fk_{table}_source_version_id_source_versions
        FOREIGN KEY (source_version_id) REFERENCES app.source_versions (id) ON DELETE RESTRICT,
    CONSTRAINT ck_{table}_passage CHECK (char_length(passage) BETWEEN 1 AND 1000),
    CONSTRAINT ck_{table}_location CHECK (
        location_label <> '' AND char_length(location_label) <= 200),
    CONSTRAINT ck_{table}_start CHECK (passage_start >= 0)
)
"""


def enforce_function(claim: str, cites: str, parent_column: str) -> str:
    return f"""
CREATE FUNCTION app.enforce_public_{claim}_citation() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, app AS $$
DECLARE
    subject uuid;
BEGIN
    IF TG_TABLE_NAME = 'project_{claim}s' THEN
        subject := NEW.id;
    ELSE
        subject := OLD.{parent_column};
    END IF;
    IF EXISTS (
            SELECT 1 FROM app.project_{claim}s c
            WHERE c.id = subject AND c.visibility = 'public')
       AND NOT EXISTS (
            SELECT 1 FROM app.{cites} ci
            JOIN app.source_versions v ON v.id = ci.source_version_id
            WHERE ci.{parent_column} = subject
              AND v.review_state IN ('approved', 'superseded')) THEN
        RAISE EXCEPTION 'a public {claim} needs a citation to an approved source version'
            USING ERRCODE = '23514', CONSTRAINT = 'public_{claim}_citation';
    END IF;
    RETURN NULL;
END
$$
"""


KEEP_CITABLE = """
CREATE FUNCTION app.enforce_cited_version_stays_citable() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, app AS $$
BEGIN
    IF NEW.review_state IN ('approved', 'superseded') THEN
        RETURN NULL;
    END IF;
    IF EXISTS (
        SELECT 1 FROM app.fact_citations ci JOIN app.project_facts f ON f.id = ci.fact_id
        WHERE ci.source_version_id = NEW.id AND f.visibility = 'public'
          AND NOT EXISTS (
            SELECT 1 FROM app.fact_citations other
            JOIN app.source_versions ov ON ov.id = other.source_version_id
            WHERE other.fact_id = f.id AND ov.review_state IN ('approved', 'superseded'))
    ) OR EXISTS (
        SELECT 1 FROM app.update_citations ci JOIN app.project_updates u ON u.id = ci.update_id
        WHERE ci.source_version_id = NEW.id AND u.visibility = 'public'
          AND NOT EXISTS (
            SELECT 1 FROM app.update_citations other
            JOIN app.source_versions ov ON ov.id = other.source_version_id
            WHERE other.update_id = u.id AND ov.review_state IN ('approved', 'superseded'))
    ) THEN
        RAISE EXCEPTION 'a public fact or update still depends on this source version'
            USING ERRCODE = '23514', CONSTRAINT = 'cited_version_stays_citable';
    END IF;
    RETURN NULL;
END
$$
"""

VIEWS = (
    """CREATE VIEW public_api.project_facts AS
    SELECT f.id, p.slug AS project_slug, f.kind, f.statement, f.effective_on, f.last_checked_on,
           f.verification_state, f.published_at
    FROM app.project_facts f JOIN app.projects p ON p.id = f.project_id
    WHERE f.visibility = 'public' AND p.visibility = 'public'""",
    """CREATE VIEW public_api.project_updates AS
    SELECT u.id, p.slug AS project_slug, u.statement, u.effective_on, u.last_checked_on,
           u.verification_state, u.published_at
    FROM app.project_updates u JOIN app.projects p ON p.id = u.project_id
    WHERE u.visibility = 'public' AND p.visibility = 'public'""",
    """CREATE VIEW public_api.fact_citations AS
    SELECT ci.fact_id, ci.passage, ci.location_label, s.id AS source_id, s.title AS source_title,
           s.publisher, s.canonical_url, s.source_type, s.information_class, v.retrieved_at
    FROM app.fact_citations ci
    JOIN app.project_facts f ON f.id = ci.fact_id AND f.visibility = 'public'
    JOIN app.source_versions v ON v.id = ci.source_version_id
        AND v.review_state IN ('approved', 'superseded')
    JOIN app.sources s ON s.id = v.source_id""",
    """CREATE VIEW public_api.update_citations AS
    SELECT ci.update_id, ci.passage, ci.location_label, s.id AS source_id,
           s.title AS source_title, s.publisher, s.canonical_url, s.source_type,
           s.information_class, v.retrieved_at
    FROM app.update_citations ci
    JOIN app.project_updates u ON u.id = ci.update_id AND u.visibility = 'public'
    JOIN app.source_versions v ON v.id = ci.source_version_id
        AND v.review_state IN ('approved', 'superseded')
    JOIN app.sources s ON s.id = v.source_id""",
    """CREATE VIEW public_api.cited_sources AS
    SELECT s.id, s.canonical_url, s.title, s.publisher, s.source_type, s.information_class,
           s.availability, s.availability_checked_at
    FROM app.sources s
    WHERE EXISTS (SELECT 1 FROM public_api.fact_citations c WHERE c.source_id = s.id)
       OR EXISTS (SELECT 1 FROM public_api.update_citations c WHERE c.source_id = s.id)""",
)
VIEW_NAMES = (
    "cited_sources",
    "update_citations",
    "fact_citations",
    "project_updates",
    "project_facts",
)


def upgrade() -> None:
    use_owner_role()
    for statement in (SOURCES_DDL, VERSIONS_DDL):
        op.execute(statement)
    op.execute("CREATE INDEX ix_source_versions_source_id ON app.source_versions (source_id)")
    op.execute(PROTECT_VERSIONS)
    op.execute(
        "CREATE TRIGGER source_versions_protect BEFORE UPDATE OR DELETE ON app.source_versions "
        "FOR EACH ROW EXECUTE FUNCTION app.protect_source_versions()"
    )
    op.execute(claim_ddl("project_facts", with_kind=True))
    op.execute(claim_ddl("project_updates", with_kind=False))
    op.execute("CREATE INDEX ix_project_facts_project_id ON app.project_facts (project_id)")
    op.execute("CREATE INDEX ix_project_updates_project_id ON app.project_updates (project_id)")
    op.execute(citation_ddl("fact_citations", "project_facts", "fact_id"))
    op.execute(citation_ddl("update_citations", "project_updates", "update_id"))
    for cites in ("fact_citations", "update_citations"):
        op.execute(f"CREATE INDEX ix_{cites}_source_version_id ON app.{cites} (source_version_id)")
    op.execute(VERIFY_PASSAGE)
    for cites in ("fact_citations", "update_citations"):
        op.execute(
            f"CREATE TRIGGER {cites}_passage BEFORE INSERT OR UPDATE ON app.{cites} "
            "FOR EACH ROW EXECUTE FUNCTION app.verify_citation_passage()"
        )
    for claim, cites, parent_column in (
        ("fact", "fact_citations", "fact_id"),
        ("update", "update_citations", "update_id"),
    ):
        op.execute(enforce_function(claim, cites, parent_column))
        op.execute(
            f"CREATE CONSTRAINT TRIGGER {claim}s_public_citation AFTER INSERT OR UPDATE "
            f"ON app.project_{claim}s DEFERRABLE INITIALLY DEFERRED FOR EACH ROW "
            f"EXECUTE FUNCTION app.enforce_public_{claim}_citation()"
        )
        op.execute(
            f"CREATE CONSTRAINT TRIGGER {cites}_public_citation AFTER UPDATE OR DELETE "
            f"ON app.{cites} DEFERRABLE INITIALLY DEFERRED FOR EACH ROW "
            f"EXECUTE FUNCTION app.enforce_public_{claim}_citation()"
        )
    op.execute(KEEP_CITABLE)
    op.execute(
        "CREATE CONSTRAINT TRIGGER source_versions_stay_citable AFTER UPDATE OF review_state "
        "ON app.source_versions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW "
        "EXECUTE FUNCTION app.enforce_cited_version_stays_citable()"
    )
    op.execute(
        "GRANT SELECT ON app.sources, app.source_versions, app.project_facts, "
        "app.project_updates, app.fact_citations, app.update_citations TO shaidago_reviewer"
    )
    for view in VIEWS:
        op.execute(view)


def downgrade() -> None:
    use_owner_role()
    for name in VIEW_NAMES:
        op.execute(f"DROP VIEW public_api.{name}")
    for table in (
        "update_citations",
        "fact_citations",
        "project_updates",
        "project_facts",
        "source_versions",
        "sources",
    ):
        op.execute(f"DROP TABLE app.{table}")
    for function in (
        "enforce_cited_version_stays_citable()",
        "enforce_public_update_citation()",
        "enforce_public_fact_citation()",
        "verify_citation_passage()",
        "protect_source_versions()",
    ):
        op.execute(f"DROP FUNCTION app.{function}")

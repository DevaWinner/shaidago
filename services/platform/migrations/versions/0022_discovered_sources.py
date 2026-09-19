"""Discovered sources and their sightings (BE-094, ADR-0003).

Revision ID: 0022_discovered_sources
Revises: 0021_discovery_runs

A discovered source is metadata and a short excerpt about a public page, labelled
``discovered - not yet reviewed`` until a reviewer decides. No full page is stored. Rows belong to
one scope (a project for public runs, a report for private runs) and are never compared across
scopes, so a private run's findings cannot surface through a public run. Every time a run finds a
source is recorded as a sighting; a duplicate keeps a pointer to the source it repeats instead of
being discarded. The worker inserts and refreshes rows; a reviewer's decision is added with the
decision APIs.
"""

from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0022_discovered_sources"
down_revision = "0021_discovery_runs"
branch_labels = None
depends_on = None

SOURCES = """
CREATE TABLE app.discovered_sources (
    id uuid NOT NULL,
    scope text NOT NULL,
    project_id uuid NOT NULL,
    report_id uuid,
    canonical_url text NOT NULL,
    publisher_domain text NOT NULL,
    title text,
    preliminary_type text NOT NULL,
    published_on date,
    published_provenance text NOT NULL,
    date_conflict boolean NOT NULL,
    content_type text NOT NULL,
    excerpt text NOT NULL,
    text_sha256 text NOT NULL,
    simhash bigint NOT NULL,
    extraction_version text NOT NULL,
    injection_flag boolean NOT NULL,
    duplicate_of uuid,
    duplicate_kind text,
    availability text NOT NULL,
    disposition text NOT NULL DEFAULT 'not_reviewed',
    first_discovered_at timestamptz NOT NULL,
    last_retrieved_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT pk_discovered_sources PRIMARY KEY (id),
    CONSTRAINT fk_discovered_sources_project_id_projects
        FOREIGN KEY (project_id) REFERENCES app.projects (id) ON DELETE RESTRICT,
    CONSTRAINT fk_discovered_sources_report_id_reports
        FOREIGN KEY (report_id) REFERENCES app.reports (id) ON DELETE CASCADE,
    CONSTRAINT fk_discovered_sources_duplicate_of_discovered_sources
        FOREIGN KEY (duplicate_of) REFERENCES app.discovered_sources (id) ON DELETE SET NULL,
    CONSTRAINT ck_discovered_sources_scope CHECK (
        (scope = 'public' AND report_id IS NULL) OR (scope = 'report' AND report_id IS NOT NULL)),
    CONSTRAINT ck_discovered_sources_url CHECK (
        canonical_url ~ '^https?://[^[:space:]]+$' AND char_length(canonical_url) <= 2048),
    CONSTRAINT ck_discovered_sources_excerpt CHECK (char_length(excerpt) BETWEEN 1 AND 1200),
    CONSTRAINT ck_discovered_sources_sha CHECK (text_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_discovered_sources_published_provenance CHECK (
        published_provenance IN ('none', 'meta_published', 'time_element', 'pdf_metadata')
        AND ((published_on IS NULL) = (published_provenance = 'none'))),
    CONSTRAINT ck_discovered_sources_availability CHECK (
        availability IN ('available', 'stale', 'unavailable')),
    CONSTRAINT ck_discovered_sources_disposition CHECK (
        disposition IN ('not_reviewed', 'attached', 'rejected', 'deferred')),
    CONSTRAINT ck_discovered_sources_duplicate CHECK (
        (duplicate_of IS NULL) = (duplicate_kind IS NULL)
        AND (duplicate_of IS NULL OR duplicate_of <> id)
        AND (duplicate_kind IS NULL OR duplicate_kind IN ('same_content', 'near_duplicate')))
)
"""
SIGHTINGS = """
CREATE TABLE app.discovered_source_sightings (
    id uuid NOT NULL,
    discovered_source_id uuid NOT NULL,
    run_id uuid NOT NULL,
    discovered_at timestamptz NOT NULL,
    retrieved_at timestamptz NOT NULL,
    CONSTRAINT pk_discovered_source_sightings PRIMARY KEY (id),
    CONSTRAINT fk_discovered_source_sightings_source
        FOREIGN KEY (discovered_source_id) REFERENCES app.discovered_sources (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_discovered_source_sightings_run_id_discovery_runs
        FOREIGN KEY (run_id) REFERENCES app.discovery_runs (id) ON DELETE CASCADE,
    CONSTRAINT uq_discovered_source_sightings_source_run UNIQUE (discovered_source_id, run_id)
)
"""


def _guard(table: str) -> None:
    target = f"app.{table}"
    op.execute(f"ALTER TABLE {target} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {target} FORCE ROW LEVEL SECURITY")
    for role in ("owner", "worker", "reviewer"):
        op.execute(
            f"CREATE POLICY {table}_{role}_all ON {target} TO shaidago_{role} "
            "USING (true) WITH CHECK (true)"
        )
    op.execute(f"GRANT SELECT, INSERT ON {target} TO shaidago_worker")
    op.execute(f"GRANT SELECT ON {target} TO shaidago_reviewer")


def upgrade() -> None:
    use_owner_role()
    op.execute(SOURCES)
    op.execute(SIGHTINGS)
    op.execute(
        "CREATE UNIQUE INDEX uq_discovered_sources_scope_url ON app.discovered_sources "
        "(scope, COALESCE(report_id, project_id), canonical_url)"
    )
    op.execute(
        "CREATE INDEX ix_discovered_sources_hash ON app.discovered_sources "
        "(scope, COALESCE(report_id, project_id), text_sha256)"
    )
    op.execute(
        "CREATE INDEX ix_discovered_source_sightings_run_id "
        "ON app.discovered_source_sightings (run_id)"
    )
    _guard("discovered_sources")
    _guard("discovered_source_sightings")
    op.execute(
        "GRANT UPDATE (last_retrieved_at, availability, updated_at) "
        "ON app.discovered_sources TO shaidago_worker"
    )


def downgrade() -> None:
    use_owner_role()
    op.execute("DROP TABLE app.discovered_source_sightings")
    op.execute("DROP TABLE app.discovered_sources")

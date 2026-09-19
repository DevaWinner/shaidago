"""Source Scout discovery runs and their worker lease (BE-090, ADR-0003).

Revision ID: 0021_discovery_runs
Revises: 0020_question_metrics

A run is one bounded discovery job for a project: ``public`` runs use only public project terms,
``report`` runs are private to the reviewer who approved their outbound query. The row holds the
stage, attempt, lease, progress counters, and a safe failure code, never report text. The
worker role may only move a run along the ``discovery_status`` machine (a trigger refuses every
other edge, whatever code tries it); reviewers may request cancellation. The public role has no
privilege here: public progress is served through a scope-safe projection added with the APIs.
"""

from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0021_discovery_runs"
down_revision = "0020_question_metrics"
branch_labels = None
depends_on = None

RUNS = """
CREATE TABLE app.discovery_runs (
    id uuid NOT NULL,
    scope text NOT NULL,
    project_id uuid NOT NULL,
    report_id uuid,
    requested_by uuid,
    status text NOT NULL,
    attempts integer NOT NULL DEFAULT 0,
    lease_owner text,
    lease_expires_at timestamptz,
    cancel_requested boolean NOT NULL DEFAULT false,
    failure_code text,
    query_text text,
    query_policy_version text,
    query_approved_by uuid,
    provider_mode text NOT NULL,
    demo_replay boolean NOT NULL DEFAULT false,
    model_id text,
    prompt_version text,
    results_found integer NOT NULL DEFAULT 0,
    fetched_count integer NOT NULL DEFAULT 0,
    analysed_count integer NOT NULL DEFAULT 0,
    version integer NOT NULL DEFAULT 1,
    analysis jsonb,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    started_at timestamptz,
    finished_at timestamptz,
    CONSTRAINT pk_discovery_runs PRIMARY KEY (id),
    CONSTRAINT fk_discovery_runs_project_id_projects
        FOREIGN KEY (project_id) REFERENCES app.projects (id) ON DELETE RESTRICT,
    CONSTRAINT fk_discovery_runs_report_id_reports
        FOREIGN KEY (report_id) REFERENCES app.reports (id) ON DELETE CASCADE,
    CONSTRAINT fk_discovery_runs_requested_by_reviewers
        FOREIGN KEY (requested_by) REFERENCES app.reviewers (id) ON DELETE SET NULL,
    CONSTRAINT fk_discovery_runs_query_approved_by_reviewers
        FOREIGN KEY (query_approved_by) REFERENCES app.reviewers (id) ON DELETE SET NULL,
    CONSTRAINT ck_discovery_runs_scope CHECK (
        (scope = 'public' AND report_id IS NULL)
        OR (scope = 'report' AND report_id IS NOT NULL AND requested_by IS NOT NULL)),
    CONSTRAINT ck_discovery_runs_status CHECK (
        status IN ('queued', 'searching', 'analysing', 'needs_review', 'complete', 'failed',
                   'cancelled')),
    CONSTRAINT ck_discovery_runs_provider_mode CHECK (provider_mode IN ('live', 'replay')),
    CONSTRAINT ck_discovery_runs_attempts CHECK (attempts >= 0),
    CONSTRAINT ck_discovery_runs_counters CHECK (
        results_found >= 0 AND fetched_count >= 0 AND analysed_count >= 0),
    CONSTRAINT ck_discovery_runs_failure_code CHECK (
        failure_code IS NULL OR failure_code ~ '^[a-z0-9]+(_[a-z0-9]+)*$'),
    CONSTRAINT ck_discovery_runs_failed_has_code CHECK (
        status <> 'failed' OR failure_code IS NOT NULL),
    CONSTRAINT ck_discovery_runs_query_bounded CHECK (
        query_text IS NULL OR char_length(query_text) BETWEEN 3 AND 300)
)
"""
GUARD = """
CREATE FUNCTION app.discovery_runs_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, app AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'discovery runs are never deleted directly' USING ERRCODE = '55000';
    END IF;
    IF NEW.status <> OLD.status AND NOT (
        (OLD.status = 'queued' AND NEW.status IN ('searching', 'cancelled', 'failed'))
        OR (OLD.status = 'searching' AND NEW.status IN ('analysing', 'cancelled', 'failed'))
        OR (OLD.status = 'analysing'
            AND NEW.status IN ('complete', 'needs_review', 'cancelled', 'failed'))
        OR (OLD.status = 'needs_review' AND NEW.status IN ('complete', 'failed', 'cancelled'))
    ) THEN
        RAISE EXCEPTION 'illegal discovery status transition' USING ERRCODE = '55000';
    END IF;
    IF (NEW.id, NEW.scope, NEW.project_id, NEW.report_id, NEW.created_at)
       IS DISTINCT FROM (OLD.id, OLD.scope, OLD.project_id, OLD.report_id, OLD.created_at) THEN
        RAISE EXCEPTION 'a run''s scope and subject are fixed' USING ERRCODE = '55000';
    END IF;
    IF OLD.status IN ('complete', 'failed', 'cancelled') THEN
        RAISE EXCEPTION 'a finished discovery run cannot change' USING ERRCODE = '55000';
    END IF;
    NEW.version := OLD.version + 1;
    RETURN NEW;
END
$$
"""


def upgrade() -> None:
    use_owner_role()
    op.execute(RUNS)
    op.execute(
        "CREATE INDEX ix_discovery_runs_project_id ON app.discovery_runs (project_id, created_at)"
    )
    op.execute(
        "CREATE INDEX ix_discovery_runs_report_id ON app.discovery_runs (report_id) "
        "WHERE report_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX ix_discovery_runs_active ON app.discovery_runs (status) "
        "WHERE status IN ('queued', 'searching', 'analysing')"
    )
    op.execute(GUARD)
    op.execute(
        "CREATE TRIGGER discovery_runs_guard BEFORE UPDATE OR DELETE ON app.discovery_runs "
        "FOR EACH ROW EXECUTE FUNCTION app.discovery_runs_guard()"
    )
    op.execute("ALTER TABLE app.discovery_runs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE app.discovery_runs FORCE ROW LEVEL SECURITY")
    for role in ("owner", "worker", "reviewer"):
        op.execute(
            f"CREATE POLICY discovery_runs_{role}_all ON app.discovery_runs TO shaidago_{role} "
            "USING (true) WITH CHECK (true)"
        )
    op.execute("GRANT SELECT ON app.discovery_runs TO shaidago_worker, shaidago_reviewer")
    op.execute("GRANT INSERT ON app.discovery_runs TO shaidago_reviewer")
    op.execute(
        "GRANT UPDATE (status, attempts, lease_owner, lease_expires_at, failure_code, "
        "results_found, fetched_count, analysed_count, analysis, model_id, prompt_version, "
        "started_at, finished_at, updated_at) ON app.discovery_runs TO shaidago_worker"
    )
    op.execute(
        "GRANT UPDATE (cancel_requested, status, finished_at, updated_at) "
        "ON app.discovery_runs TO shaidago_reviewer"
    )


def downgrade() -> None:
    use_owner_role()
    op.execute("DROP TABLE app.discovery_runs")
    op.execute("DROP FUNCTION app.discovery_runs_guard()")

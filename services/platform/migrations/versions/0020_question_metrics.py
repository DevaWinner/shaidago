"""Privacy-safe operational records for grounded project questions.

Revision ID: 0020_question_metrics
Revises: 0019_hybrid_retrieval

The table deliberately has no question, prompt, passage, citation URL, client pseudonym, or IP
column. The public API role may append bounded metrics but cannot read them; the read-only
operations role can inspect aggregates without gaining access to user-authored content.
"""

from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0020_question_metrics"
down_revision = "0019_hybrid_retrieval"
branch_labels = None
depends_on = None

TABLE = """
CREATE TABLE app.question_runs (
    id uuid NOT NULL,
    project_id uuid NOT NULL,
    request_id text NOT NULL,
    requested_locale text NOT NULL,
    served_locale text,
    retrieval_mode text NOT NULL,
    retrieved_chunks integer NOT NULL,
    cited_sources integer NOT NULL,
    outcome text NOT NULL,
    model_id text NOT NULL,
    prompt_version text NOT NULL,
    schema_version text NOT NULL,
    demo_replay boolean,
    failure_code text,
    validation_findings integer NOT NULL,
    duration_ms integer NOT NULL,
    started_at timestamptz NOT NULL,
    completed_at timestamptz NOT NULL,
    CONSTRAINT pk_question_runs PRIMARY KEY (id),
    CONSTRAINT fk_question_runs_project_id_projects
        FOREIGN KEY (project_id) REFERENCES app.projects (id) ON DELETE RESTRICT,
    CONSTRAINT ck_question_runs_request_id CHECK (char_length(request_id) BETWEEN 1 AND 64),
    CONSTRAINT ck_question_runs_requested_locale CHECK (
        requested_locale IN ('en', 'ha', 'ig', 'yo')),
    CONSTRAINT ck_question_runs_served_locale CHECK (
        served_locale IS NULL OR served_locale IN ('en', 'ha', 'ig', 'yo')),
    CONSTRAINT ck_question_runs_retrieval_mode CHECK (retrieval_mode IN ('keyword', 'hybrid')),
    CONSTRAINT ck_question_runs_retrieved_chunks CHECK (retrieved_chunks BETWEEN 0 AND 5),
    CONSTRAINT ck_question_runs_cited_sources CHECK (cited_sources BETWEEN 0 AND 5),
    CONSTRAINT ck_question_runs_outcome CHECK (
        outcome IN ('answered', 'fallback', 'provider_unavailable')),
    CONSTRAINT ck_question_runs_model_id CHECK (char_length(model_id) BETWEEN 1 AND 100),
    CONSTRAINT ck_question_runs_prompt_version CHECK (
        char_length(prompt_version) BETWEEN 1 AND 100),
    CONSTRAINT ck_question_runs_schema_version CHECK (
        char_length(schema_version) BETWEEN 1 AND 100),
    CONSTRAINT ck_question_runs_failure_code CHECK (
        failure_code IS NULL OR failure_code ~ '^[a-z][a-z0-9_]{0,99}$'),
    CONSTRAINT ck_question_runs_validation_findings CHECK (
        validation_findings BETWEEN 0 AND 100),
    CONSTRAINT ck_question_runs_duration_ms CHECK (duration_ms BETWEEN 0 AND 120000),
    CONSTRAINT ck_question_runs_timestamps CHECK (completed_at >= started_at)
)
"""


def upgrade() -> None:
    use_owner_role()
    op.execute(TABLE)
    op.execute(
        "CREATE INDEX ix_question_runs_project_started "
        "ON app.question_runs (project_id, started_at)"
    )
    op.execute(
        "CREATE INDEX ix_question_runs_outcome_started ON app.question_runs (outcome, started_at)"
    )
    op.execute("ALTER TABLE app.question_runs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE app.question_runs FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY question_runs_owner_all ON app.question_runs TO shaidago_owner "
        "USING (true) WITH CHECK (true)"
    )
    op.execute(
        "CREATE POLICY question_runs_public_insert ON app.question_runs TO shaidago_public "
        "WITH CHECK (true)"
    )
    op.execute(
        "CREATE POLICY question_runs_ops_select ON app.question_runs TO shaidago_readonly_ops "
        "USING (true)"
    )
    op.execute("GRANT INSERT ON app.question_runs TO shaidago_public")
    op.execute("GRANT SELECT ON app.question_runs TO shaidago_readonly_ops")


def downgrade() -> None:
    use_owner_role()
    op.execute("DROP TABLE app.question_runs")

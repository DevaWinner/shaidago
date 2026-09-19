"""Reviewer users and the append-only audit log (BE-050).

Revision ID: 0007_reviewers_audit
Revises: 0006_public_query_indexes

Reviewer identifiers are pseudonymous handles, not required to be email addresses, and only an
Argon2id hash of the password is stored. Audit rows can be inserted but never changed or
deleted, by trigger, so history is corrected by new events (AGENTS.md).
"""

from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0007_reviewers_audit"
down_revision = "0006_public_query_indexes"
branch_labels = None
depends_on = None

REVIEWERS = """
CREATE TABLE app.reviewers (
    id uuid NOT NULL,
    identifier text NOT NULL,
    password_hash text NOT NULL,
    role text NOT NULL,
    state text NOT NULL,
    credential_version integer NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    last_sign_in_at timestamptz,
    CONSTRAINT pk_reviewers PRIMARY KEY (id),
    CONSTRAINT uq_reviewers_identifier UNIQUE (identifier),
    CONSTRAINT ck_reviewers_identifier CHECK (identifier ~ '^[a-z0-9][a-z0-9._@+-]{2,127}$'),
    CONSTRAINT ck_reviewers_password_hash CHECK (password_hash LIKE '$argon2id$%'),
    CONSTRAINT ck_reviewers_role CHECK (role IN ('reviewer', 'admin')),
    CONSTRAINT ck_reviewers_state CHECK (state IN ('active', 'disabled')),
    CONSTRAINT ck_reviewers_credential_version CHECK (credential_version >= 1)
)
"""

AUDIT = """
CREATE TABLE app.audit_events (
    id uuid NOT NULL,
    occurred_at timestamptz NOT NULL,
    actor_type text NOT NULL,
    actor_id uuid,
    event text NOT NULL,
    subject_type text,
    subject_id uuid,
    outcome text NOT NULL,
    request_id text,
    details jsonb NOT NULL,
    CONSTRAINT pk_audit_events PRIMARY KEY (id),
    CONSTRAINT ck_audit_events_actor_type CHECK (
        actor_type IN ('system', 'worker', 'reviewer', 'admin', 'reporter')),
    CONSTRAINT ck_audit_events_outcome CHECK (outcome IN ('success', 'failure', 'denied')),
    CONSTRAINT ck_audit_events_event CHECK (event ~ '^[a-z0-9]+(_[a-z0-9]+)*$'),
    CONSTRAINT ck_audit_events_details CHECK (jsonb_typeof(details) = 'object')
)
"""

APPEND_ONLY = """
CREATE FUNCTION app.audit_events_append_only() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, app AS $$
BEGIN
    RAISE EXCEPTION 'audit events are append-only; record a correcting event instead'
        USING ERRCODE = '55000';
END
$$
"""


def upgrade() -> None:
    use_owner_role()
    op.execute(REVIEWERS)
    op.execute(AUDIT)
    op.execute("CREATE INDEX ix_audit_events_occurred_at ON app.audit_events (occurred_at)")
    op.execute(
        "CREATE INDEX ix_audit_events_subject ON app.audit_events (subject_type, subject_id)"
    )
    op.execute(APPEND_ONLY)
    op.execute(
        "CREATE TRIGGER audit_events_append_only BEFORE UPDATE OR DELETE ON app.audit_events "
        "FOR EACH ROW EXECUTE FUNCTION app.audit_events_append_only()"
    )
    op.execute(
        "CREATE TRIGGER audit_events_no_truncate BEFORE TRUNCATE ON app.audit_events "
        "FOR EACH STATEMENT EXECUTE FUNCTION app.audit_events_append_only()"
    )
    # Reviewer sign-in and administration run as the reviewer role; nothing else touches these.
    op.execute(
        "GRANT SELECT, UPDATE (password_hash, state, credential_version, updated_at, "
        "last_sign_in_at) ON app.reviewers TO shaidago_reviewer"
    )
    op.execute("GRANT INSERT ON app.audit_events TO shaidago_reviewer, shaidago_worker")


def downgrade() -> None:
    use_owner_role()
    op.execute("DROP TABLE app.audit_events")
    op.execute("DROP TABLE app.reviewers")
    op.execute("DROP FUNCTION app.audit_events_append_only()")

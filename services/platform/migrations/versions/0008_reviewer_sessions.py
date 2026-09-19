"""Reviewer sessions: opaque, hashed at rest, revocable (BE-051).

Revision ID: 0008_reviewer_sessions
Revises: 0007_reviewers_audit

Only ``HMAC-SHA-256(session_key, token)`` is stored, never the token. A session is bound to the
reviewer's credential version and role at issue; changing either, disabling the reviewer, or an
explicit logout revokes it.
"""

from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0008_reviewer_sessions"
down_revision = "0007_reviewers_audit"
branch_labels = None
depends_on = None

TABLE = """
CREATE TABLE app.reviewer_sessions (
    id uuid NOT NULL,
    token_hmac bytea NOT NULL,
    reviewer_id uuid NOT NULL,
    role_snapshot text NOT NULL,
    credential_version integer NOT NULL,
    created_at timestamptz NOT NULL,
    last_used_at timestamptz NOT NULL,
    absolute_expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    revocation_reason text,
    CONSTRAINT pk_reviewer_sessions PRIMARY KEY (id),
    CONSTRAINT uq_reviewer_sessions_token_hmac UNIQUE (token_hmac),
    CONSTRAINT fk_reviewer_sessions_reviewer_id_reviewers
        FOREIGN KEY (reviewer_id) REFERENCES app.reviewers (id) ON DELETE RESTRICT,
    CONSTRAINT ck_reviewer_sessions_token_hmac CHECK (octet_length(token_hmac) = 32),
    CONSTRAINT ck_reviewer_sessions_role CHECK (role_snapshot IN ('reviewer', 'admin')),
    CONSTRAINT ck_reviewer_sessions_expiry CHECK (absolute_expires_at > created_at),
    CONSTRAINT ck_reviewer_sessions_revocation CHECK (
        (revoked_at IS NULL AND revocation_reason IS NULL)
        OR (revoked_at IS NOT NULL AND revocation_reason IN (
            'logout', 'disabled', 'credential_change', 'role_change', 'admin_revoked', 'expired')))
)
"""


def upgrade() -> None:
    use_owner_role()
    op.execute(TABLE)
    op.execute(
        "CREATE INDEX ix_reviewer_sessions_reviewer_id ON app.reviewer_sessions (reviewer_id)"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE (last_used_at, revoked_at, revocation_reason) "
        "ON app.reviewer_sessions TO shaidago_reviewer"
    )


def downgrade() -> None:
    use_owner_role()
    op.execute("DROP TABLE app.reviewer_sessions")

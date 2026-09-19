"""Wrapped data-encryption keys for private fields (BE-060, ADR-0004).

Revision ID: 0009_data_keys
Revises: 0008_reviewer_sessions

A row holds a DEK wrapped by a versioned KEK, never the DEK itself. Destroying a class of data is
crypto-shredding: the wrapped key is nulled and the row is marked destroyed. The table is private:
the insert-only public role may add keys but never read them (ADR-0003); reviewers and the
migration owner may read and rewrap.
"""

from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0009_data_keys"
down_revision = "0008_reviewer_sessions"
branch_labels = None
depends_on = None

TABLE = """
CREATE TABLE app.data_keys (
    id uuid NOT NULL,
    purpose text NOT NULL,
    owner_table text NOT NULL,
    owner_id uuid NOT NULL,
    wrapped_key bytea,
    kek_version text,
    created_at timestamptz NOT NULL,
    destroyed_at timestamptz,
    CONSTRAINT pk_data_keys PRIMARY KEY (id),
    CONSTRAINT uq_data_keys_owner_table_owner_id_purpose UNIQUE (owner_table, owner_id, purpose),
    CONSTRAINT ck_data_keys_purpose CHECK (
        purpose IN ('report_content', 'contact', 'review_notes', 'follow_up_answers')),
    CONSTRAINT ck_data_keys_owner_table CHECK (owner_table ~ '^[a-z][a-z0-9_]{0,62}$'),
    CONSTRAINT ck_data_keys_state CHECK (
        (destroyed_at IS NULL AND wrapped_key IS NOT NULL AND kek_version IS NOT NULL
         AND octet_length(wrapped_key) >= 29)
        OR (destroyed_at IS NOT NULL AND wrapped_key IS NULL AND kek_version IS NULL))
)
"""


def upgrade() -> None:
    use_owner_role()
    op.execute(TABLE)
    op.execute("CREATE INDEX ix_data_keys_kek_version ON app.data_keys (kek_version)")
    op.execute("ALTER TABLE app.data_keys ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE app.data_keys FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY data_keys_owner_all ON app.data_keys TO shaidago_owner "
        "USING (true) WITH CHECK (true)"
    )
    op.execute(
        "CREATE POLICY data_keys_public_insert ON app.data_keys FOR INSERT "
        "TO shaidago_public WITH CHECK (true)"
    )
    op.execute(
        "CREATE POLICY data_keys_reviewer_all ON app.data_keys TO shaidago_reviewer "
        "USING (true) WITH CHECK (true)"
    )
    op.execute("GRANT INSERT ON app.data_keys TO shaidago_public")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE (wrapped_key, kek_version, destroyed_at) "
        "ON app.data_keys TO shaidago_reviewer"
    )


def downgrade() -> None:
    use_owner_role()
    op.execute("DROP TABLE app.data_keys")

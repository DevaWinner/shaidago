"""Baseline: pgvector, roles, schemas, and default privileges.

Revision ID: 0001_baseline
Revises:

Roles are cluster-wide, so the downgrade removes the schemas and the extension but keeps the
roles; dropping them could break other databases that use them.
"""

from alembic import op

from shaidago.db.migration_helpers import read_versioned_sql, run_sql_script

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

BASELINE_SQL = "0001_security_baseline.sql"
BASELINE_SHA256 = "6575fa77a8dc4194f13454420783ddc75e83a39cf6bba1dc443726cb38ed7320"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    run_sql_script(read_versioned_sql(BASELINE_SQL, BASELINE_SHA256))
    # Later revisions run as shaidago_owner (SET LOCAL ROLE), which must be able to update the
    # version table. Transfer it, giving the owner the schema privileges the transfer needs.
    op.execute("GRANT USAGE, CREATE ON SCHEMA public TO shaidago_owner")
    op.execute("ALTER TABLE public.alembic_version OWNER TO shaidago_owner")
    # Readiness reads the applied revision through whichever application role the API uses.
    op.execute(
        "GRANT SELECT ON TABLE public.alembic_version TO "
        "shaidago_public, shaidago_reviewer, shaidago_worker, shaidago_readonly_ops"
    )


def downgrade() -> None:
    op.execute(
        "REVOKE SELECT ON TABLE public.alembic_version FROM "
        "shaidago_public, shaidago_reviewer, shaidago_worker, shaidago_readonly_ops"
    )
    # Both are RESTRICT drops: they fail rather than delete data if a later revision left tables.
    op.execute("DROP SCHEMA IF EXISTS public_api")
    op.execute("DROP SCHEMA IF EXISTS app")
    op.execute("DROP EXTENSION IF EXISTS vector")

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
BASELINE_SHA256 = "de2596f8beebaba9744afdca9bdcf7dccd65276f49bd799fd7a921d7e5a91fbb"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    run_sql_script(read_versioned_sql(BASELINE_SQL, BASELINE_SHA256))
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

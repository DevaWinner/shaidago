"""Indexes for the public list query, each justified by measured plans (docs/evidence/BE-045).

Revision ID: 0006_public_query_indexes
Revises: 0005_escalation_routes
"""

from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0006_public_query_indexes"
down_revision = "0005_escalation_routes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    use_owner_role()
    op.execute(
        "CREATE INDEX ix_projects_public_recent ON app.projects (updated_at DESC, id DESC) "
        "WHERE visibility = 'public'"
    )
    op.execute(
        "CREATE INDEX ix_project_translations_search ON app.project_translations "
        "USING gin (to_tsvector('simple', title || ' ' || summary))"
    )


def downgrade() -> None:
    use_owner_role()
    op.execute("DROP INDEX app.ix_project_translations_search")
    op.execute("DROP INDEX app.ix_projects_public_recent")

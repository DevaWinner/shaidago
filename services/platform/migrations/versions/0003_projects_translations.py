"""Localities, projects, and project translations.

Revision ID: 0003_projects_translations
Revises: 0002_idempotency_records

Public-zone tables: the public role reads them only through views in ``public_api`` that expose
public columns of visible projects; the reviewer role may read the tables. Writes are made by
the migration owner (seed pipeline) until reviewer publication tasks add narrower grants.
"""

import sqlalchemy as sa
from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0003_projects_translations"
down_revision = "0002_idempotency_records"
branch_labels = None
depends_on = None

SLUG = "slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'"

ENFORCE_FUNCTION = """
CREATE FUNCTION app.enforce_public_project_source_text() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, app AS $$
DECLARE
    subject uuid;
BEGIN
    IF TG_TABLE_NAME = 'projects' THEN
        subject := NEW.id;
    ELSE
        subject := OLD.project_id;
    END IF;
    IF EXISTS (SELECT 1 FROM app.projects p WHERE p.id = subject AND p.visibility = 'public')
       AND NOT EXISTS (
            SELECT 1 FROM app.project_translations t
            WHERE t.project_id = subject AND t.locale = 'en'
              AND t.translation_status <> 'unavailable') THEN
        RAISE EXCEPTION 'a public project needs English source text'
            USING ERRCODE = '23514', CONSTRAINT = 'public_project_source_text';
    END IF;
    RETURN NULL;
END
$$
"""


def upgrade() -> None:
    use_owner_role()
    op.create_table(
        "localities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("enabled_locales", sa.ARRAY(sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_localities")),
        sa.UniqueConstraint("slug", name=op.f("uq_localities_slug")),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["app.localities.id"],
            name=op.f("fk_localities_parent_id_localities"),
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("kind IN ('state', 'area_council')", name=op.f("ck_localities_kind")),
        sa.CheckConstraint(
            "enabled_locales <@ ARRAY['en','ha','ig','yo']::text[]",
            name=op.f("ck_localities_locales"),
        ),
        sa.CheckConstraint(
            "'en' = ANY (enabled_locales)", name=op.f("ck_localities_source_locale")
        ),
        sa.CheckConstraint(SLUG, name=op.f("ck_localities_slug_format")),
        schema="app",
    )
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("locality_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("public_status", sa.Text(), nullable=False),
        sa.Column("visibility", sa.Text(), nullable=False),
        sa.Column("last_checked_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
        sa.UniqueConstraint("slug", name=op.f("uq_projects_slug")),
        sa.ForeignKeyConstraint(
            ["locality_id"],
            ["app.localities.id"],
            name=op.f("fk_projects_locality_id_localities"),
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "category IN ('health', 'education', 'water_sanitation', "
            "'roads_public_works', 'other_public_service')",
            name=op.f("ck_projects_category"),
        ),
        sa.CheckConstraint(
            "public_status IN ('unknown', 'planned', 'procurement', 'in_progress', "
            "'on_hold', 'completed', 'cancelled')",
            name=op.f("ck_projects_public_status"),
        ),
        sa.CheckConstraint(
            "visibility IN ('public', 'hidden')", name=op.f("ck_projects_visibility")
        ),
        sa.CheckConstraint(SLUG, name=op.f("ck_projects_slug_format")),
        sa.CheckConstraint(
            "last_checked_on IS NULL OR "
            "last_checked_on <= (updated_at AT TIME ZONE 'Africa/Lagos')::date",
            name=op.f("ck_projects_last_checked_not_future"),
        ),
        schema="app",
    )
    op.create_index("ix_projects_locality_id", "projects", ["locality_id"], schema="app")
    op.create_table(
        "project_translations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("locale", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("promised_deliverable", sa.Text(), nullable=False),
        sa.Column("translation_status", sa.Text(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project_translations")),
        sa.UniqueConstraint(
            "project_id", "locale", name=op.f("uq_project_translations_project_id_locale")
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["app.projects.id"],
            name=op.f("fk_project_translations_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "locale IN ('en', 'ha', 'ig', 'yo')", name=op.f("ck_project_translations_locale")
        ),
        sa.CheckConstraint(
            "translation_status IN ('reviewed', 'machine_assisted', 'unavailable')",
            name=op.f("ck_project_translations_status"),
        ),
        sa.CheckConstraint(
            "translation_status <> 'reviewed' OR reviewed_at IS NOT NULL",
            name=op.f("ck_project_translations_reviewed_has_date"),
        ),
        sa.CheckConstraint(
            "title <> '' AND summary <> ''", name=op.f("ck_project_translations_text_not_empty")
        ),
        schema="app",
    )
    op.execute(ENFORCE_FUNCTION)
    for table, events in (
        ("projects", "INSERT OR UPDATE"),
        ("project_translations", "UPDATE OR DELETE"),
    ):
        op.execute(
            f"CREATE CONSTRAINT TRIGGER {table}_public_source_text AFTER {events} ON app.{table} "
            "DEFERRABLE INITIALLY DEFERRED FOR EACH ROW "
            "EXECUTE FUNCTION app.enforce_public_project_source_text()"
        )
    # Reviewers read the tables; the public role reads only the views below.
    op.execute(
        "GRANT SELECT ON app.localities, app.projects, app.project_translations "
        "TO shaidago_reviewer"
    )
    op.execute(
        "CREATE VIEW public_api.localities AS "
        "SELECT l.id, l.slug, l.name, l.kind, parent.slug AS parent_slug, l.enabled_locales "
        "FROM app.localities l LEFT JOIN app.localities parent ON parent.id = l.parent_id"
    )
    op.execute(
        "CREATE VIEW public_api.projects AS "
        "SELECT p.id, p.slug, l.slug AS locality_slug, p.category, p.public_status, "
        "p.last_checked_on, p.updated_at "
        "FROM app.projects p JOIN app.localities l ON l.id = p.locality_id "
        "WHERE p.visibility = 'public'"
    )
    op.execute(
        "CREATE VIEW public_api.project_translations AS "
        "SELECT t.project_id, t.locale, t.title, t.summary, t.promised_deliverable, "
        "t.translation_status, t.reviewed_at "
        "FROM app.project_translations t JOIN app.projects p ON p.id = t.project_id "
        "WHERE p.visibility = 'public' AND t.translation_status <> 'unavailable'"
    )


def downgrade() -> None:
    use_owner_role()
    op.execute("DROP VIEW public_api.project_translations")
    op.execute("DROP VIEW public_api.projects")
    op.execute("DROP VIEW public_api.localities")
    op.execute("DROP TABLE app.project_translations")
    op.execute("DROP TABLE app.projects")
    op.execute("DROP TABLE app.localities")
    op.execute("DROP FUNCTION app.enforce_public_project_source_text()")

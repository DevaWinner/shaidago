"""Public discovery runs carry their planned query (BE-097).

Revision ID: 0024_public_run_query
Revises: 0023_discovery_review

A public run's outbound query is planned by the API from public project fields and stored on the
run at creation, so the worker sends exactly that query and nothing else. The creation function
gains the query and policy version; it still refuses a project that is not public.
"""

from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0024_public_run_query"
down_revision = "0023_discovery_review"
branch_labels = None
depends_on = None

OLD_SIGNATURE = "app.create_public_discovery_run(uuid, text, timestamptz, text, boolean)"
NEW_SIGNATURE = (
    "app.create_public_discovery_run(uuid, text, timestamptz, text, boolean, text, text)"
)
CREATE = """
CREATE FUNCTION app.create_public_discovery_run(
    p_run_id uuid, p_slug text, p_now timestamptz, p_provider_mode text, p_demo_replay boolean,
    p_query text, p_policy text)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, app AS $$
DECLARE
    target uuid;
BEGIN
    SELECT id INTO target FROM app.projects WHERE slug = p_slug AND visibility = 'public';
    IF target IS NULL THEN
        RETURN NULL;
    END IF;
    INSERT INTO app.discovery_runs
        (id, scope, project_id, status, query_text, query_policy_version, provider_mode,
         demo_replay, created_at, updated_at)
    VALUES (p_run_id, 'public', target, 'queued', p_query, p_policy, p_provider_mode,
            p_demo_replay, p_now, p_now);
    RETURN p_run_id;
END
$$
"""
RESTORE = """
CREATE FUNCTION app.create_public_discovery_run(
    p_run_id uuid, p_slug text, p_now timestamptz, p_provider_mode text, p_demo_replay boolean)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, app AS $$
DECLARE
    target uuid;
BEGIN
    SELECT id INTO target FROM app.projects WHERE slug = p_slug AND visibility = 'public';
    IF target IS NULL THEN
        RETURN NULL;
    END IF;
    INSERT INTO app.discovery_runs
        (id, scope, project_id, status, provider_mode, demo_replay, created_at, updated_at)
    VALUES (p_run_id, 'public', target, 'queued', p_provider_mode, p_demo_replay, p_now, p_now);
    RETURN p_run_id;
END
$$
"""


def upgrade() -> None:
    use_owner_role()
    op.execute(f"DROP FUNCTION {OLD_SIGNATURE}")
    op.execute(CREATE)
    op.execute(f"REVOKE EXECUTE ON FUNCTION {NEW_SIGNATURE} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {NEW_SIGNATURE} TO shaidago_public")


def downgrade() -> None:
    use_owner_role()
    op.execute(f"DROP FUNCTION {NEW_SIGNATURE}")
    op.execute(RESTORE)
    op.execute(f"REVOKE EXECUTE ON FUNCTION {OLD_SIGNATURE} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {OLD_SIGNATURE} TO shaidago_public")

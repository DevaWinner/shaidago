"""Reviewer queue support: report versions and audited contact reads (BE-070, ADR-0003).

Revision ID: 0014_reviewer_queue
Revises: 0013_follow_up_answers

``app.reports.version`` is the optimistic-concurrency token for reviewer commands (BE-071). A
trigger raises it whenever the status or risk level changes, so no code path (including the
reporter-caused resume in ``follow_up_submit``) can change either without invalidating a reviewer's
stale view. Contacts stay unreadable to the reviewer role: the only way to read one is
``app.reviewer_read_contact``, which writes the audit event in the same transaction before it
returns any ciphertext, so an unaudited contact read cannot happen.
"""

from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0014_reviewer_queue"
down_revision = "0013_follow_up_answers"
branch_labels = None
depends_on = None

BUMP = """
CREATE FUNCTION app.bump_report_version() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, app AS $$
BEGIN
    IF NEW.status IS DISTINCT FROM OLD.status OR NEW.risk_level IS DISTINCT FROM OLD.risk_level THEN
        NEW.version := OLD.version + 1;
    ELSE
        NEW.version := OLD.version;
    END IF;
    RETURN NEW;
END
$$
"""
READ_CONTACT = """
CREATE FUNCTION app.reviewer_read_contact(
    p_report_id uuid, p_actor_type text, p_actor_id uuid, p_now timestamptz,
    p_audit_id uuid, p_request_id text)
RETURNS TABLE (contact_id uuid, channel_ciphertext bytea, value_ciphertext bytea,
               data_key_id uuid, schema_version integer)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, app AS $$
BEGIN
    IF p_actor_type NOT IN ('reviewer', 'admin') THEN
        RAISE EXCEPTION 'only a reviewer may read a contact' USING ERRCODE = '42501';
    END IF;
    -- Audit first, in the same transaction: no ciphertext leaves without a record.
    INSERT INTO app.audit_events
        (id, occurred_at, actor_type, actor_id, event, subject_type, subject_id, outcome,
         request_id, details)
    VALUES (p_audit_id, p_now, p_actor_type, p_actor_id, 'report_contact_read', 'report',
            p_report_id, 'success', p_request_id, '{}'::jsonb);
    RETURN QUERY
    SELECT c.id, c.channel_ciphertext, c.value_ciphertext, c.data_key_id, c.schema_version
    FROM app.report_contacts c
    WHERE c.report_id = p_report_id AND c.destroyed_at IS NULL;
END
$$
"""
READ_CONTACT_SIGNATURE = "app.reviewer_read_contact(uuid, text, uuid, timestamptz, uuid, text)"


def upgrade() -> None:
    use_owner_role()
    op.execute("ALTER TABLE app.reports ADD COLUMN version integer NOT NULL DEFAULT 1")
    op.execute("ALTER TABLE app.reports ADD CONSTRAINT ck_reports_version CHECK (version >= 1)")
    op.execute(BUMP)
    op.execute(
        "CREATE TRIGGER reports_bump_version BEFORE UPDATE ON app.reports "
        "FOR EACH ROW EXECUTE FUNCTION app.bump_report_version()"
    )
    op.execute(READ_CONTACT)
    op.execute(f"REVOKE EXECUTE ON FUNCTION {READ_CONTACT_SIGNATURE} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {READ_CONTACT_SIGNATURE} TO shaidago_reviewer")


def downgrade() -> None:
    use_owner_role()
    op.execute(f"DROP FUNCTION {READ_CONTACT_SIGNATURE}")
    op.execute("DROP TRIGGER reports_bump_version ON app.reports")
    op.execute("DROP FUNCTION app.bump_report_version()")
    op.execute("ALTER TABLE app.reports DROP CONSTRAINT ck_reports_version")
    op.execute("ALTER TABLE app.reports DROP COLUMN version")

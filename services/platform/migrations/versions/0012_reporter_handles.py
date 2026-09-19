"""Optional anonymous reporter handles (BE-066, ADR-0003, ADR-0005).

Revision ID: 0012_reporter_handles
Revises: 0011_tracking_lookup

``reporter_handles`` holds a random handle and an Argon2id passphrase hash, plus the counters
needed for per-handle backoff. It has no email, phone, address, IP, device, recovery, or profile
column. The public role may insert but never read; lookup, verification bookkeeping, listing, and
deletion go through ``SECURITY DEFINER`` functions. Deleting a handle unlinks every report and
then removes the credential in one transaction, so the reports stay as fully anonymous ones.

Backoff: three free failures, then 5 seconds doubling to at most 15 minutes, reset after an hour
without failures or on success. A failure only delays further tries; nothing is ever locked
permanently, so an attacker cannot lock a real reporter out for good.
"""

from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0012_reporter_handles"
down_revision = "0011_tracking_lookup"
branch_labels = None
depends_on = None

HANDLES = """
CREATE TABLE app.reporter_handles (
    id uuid NOT NULL,
    handle text NOT NULL,
    passphrase_hash text NOT NULL,
    created_at timestamptz NOT NULL,
    last_used_on date,
    failure_count integer NOT NULL DEFAULT 0,
    last_failure_at timestamptz,
    backoff_until timestamptz,
    CONSTRAINT pk_reporter_handles PRIMARY KEY (id),
    CONSTRAINT uq_reporter_handles_handle UNIQUE (handle),
    CONSTRAINT ck_reporter_handles_handle CHECK (
        handle ~ '^SG-H-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$'),
    CONSTRAINT ck_reporter_handles_passphrase_hash CHECK (passphrase_hash LIKE '$argon2id$%'),
    CONSTRAINT ck_reporter_handles_failure_count CHECK (failure_count >= 0)
)
"""

FUNCTIONS = {
    "app.reporter_handle_get(text)": """
CREATE FUNCTION app.reporter_handle_get(p_handle text)
RETURNS TABLE (id uuid, passphrase_hash text, backoff_until timestamptz)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, app AS $$
    SELECT h.id, h.passphrase_hash, h.backoff_until FROM app.reporter_handles h
    WHERE h.handle = p_handle
$$
""",
    "app.reporter_handle_record_failure(uuid, timestamptz)": """
CREATE FUNCTION app.reporter_handle_record_failure(p_id uuid, p_now timestamptz)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, app AS $$
DECLARE
    attempts integer;
BEGIN
    UPDATE app.reporter_handles h
    SET failure_count = CASE
            WHEN h.last_failure_at IS NULL OR h.last_failure_at < p_now - interval '1 hour'
            THEN 1 ELSE h.failure_count + 1 END,
        last_failure_at = p_now
    WHERE h.id = p_id
    RETURNING h.failure_count INTO attempts;
    IF attempts > 3 THEN
        UPDATE app.reporter_handles h
        SET backoff_until = p_now + make_interval(
            secs => least(900, 5 * power(2, least(attempts - 4, 10))))
        WHERE h.id = p_id;
    END IF;
END
$$
""",
    "app.reporter_handle_record_success(uuid, date)": """
CREATE FUNCTION app.reporter_handle_record_success(p_id uuid, p_today date)
RETURNS void LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, app AS $$
    UPDATE app.reporter_handles
    SET failure_count = 0, last_failure_at = NULL, backoff_until = NULL, last_used_on = p_today
    WHERE id = p_id
$$
""",
    "app.reporter_handle_reports(uuid, integer)": """
CREATE FUNCTION app.reporter_handle_reports(p_id uuid, p_limit integer)
RETURNS TABLE (status text, status_updated_at timestamptz, public_message text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, app AS $$
    SELECT r.status, r.status_updated_at,
           (SELECT e.public_message FROM app.report_status_events e
            WHERE e.report_id = r.id ORDER BY e.occurred_at DESC, e.id DESC LIMIT 1)
    FROM app.reports r
    WHERE r.reporter_handle_id = p_id
    ORDER BY r.created_at DESC, r.id DESC
    LIMIT least(greatest(p_limit, 1), 50)
$$
""",
    "app.reporter_handle_delete(uuid)": """
CREATE FUNCTION app.reporter_handle_delete(p_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, app AS $$
BEGIN
    -- One transaction: the reports become fully anonymous before the credential disappears.
    UPDATE app.reports SET reporter_handle_id = NULL WHERE reporter_handle_id = p_id;
    DELETE FROM app.reporter_handles WHERE id = p_id;
END
$$
""",
}
REVIEWER_TRACK_RECORD = """
CREATE FUNCTION app.reporter_handle_track_record(p_report_id uuid)
RETURNS TABLE (handle text, reports_total integer, verified_for_public_update integer,
               closed integer)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, app AS $$
    SELECT h.handle,
           count(*)::integer,
           (count(*) FILTER (WHERE r2.status = 'verified_for_public_update'))::integer,
           (count(*) FILTER (WHERE r2.status = 'closed'))::integer
    FROM app.reports r
    JOIN app.reporter_handles h ON h.id = r.reporter_handle_id
    JOIN app.reports r2 ON r2.reporter_handle_id = h.id
    WHERE r.id = p_report_id
    GROUP BY h.handle
$$
"""
TRACK_RECORD_SIGNATURE = "app.reporter_handle_track_record(uuid)"


def upgrade() -> None:
    use_owner_role()
    op.execute(HANDLES)
    op.execute("ALTER TABLE app.reporter_handles ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE app.reporter_handles FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY reporter_handles_owner_all ON app.reporter_handles TO shaidago_owner "
        "USING (true) WITH CHECK (true)"
    )
    op.execute(
        "CREATE POLICY reporter_handles_public_insert ON app.reporter_handles FOR INSERT "
        "TO shaidago_public WITH CHECK (true)"
    )
    op.execute("GRANT INSERT ON app.reporter_handles TO shaidago_public")
    op.execute(
        "ALTER TABLE app.reports ADD COLUMN reporter_handle_id uuid, "
        "ADD CONSTRAINT fk_reports_reporter_handle_id_reporter_handles "
        "FOREIGN KEY (reporter_handle_id) REFERENCES app.reporter_handles (id) ON DELETE SET NULL"
    )
    op.execute(
        "CREATE INDEX ix_reports_reporter_handle_id ON app.reports (reporter_handle_id) "
        "WHERE reporter_handle_id IS NOT NULL"
    )
    for signature, ddl in FUNCTIONS.items():
        op.execute(ddl)
        op.execute(f"REVOKE EXECUTE ON FUNCTION {signature} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO shaidago_public")
    # Reviewers see a handle only through the contextual track record, never the passphrase hash.
    op.execute(REVIEWER_TRACK_RECORD)
    op.execute(f"REVOKE EXECUTE ON FUNCTION {TRACK_RECORD_SIGNATURE} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {TRACK_RECORD_SIGNATURE} TO shaidago_reviewer")


def downgrade() -> None:
    use_owner_role()
    op.execute(f"DROP FUNCTION {TRACK_RECORD_SIGNATURE}")
    for signature in FUNCTIONS:
        op.execute(f"DROP FUNCTION {signature}")
    op.execute("DROP INDEX app.ix_reports_reporter_handle_id")
    op.execute("ALTER TABLE app.reports DROP COLUMN reporter_handle_id")
    op.execute("DROP TABLE app.reporter_handles")

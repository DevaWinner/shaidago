"""Private report persistence (BE-061, ADR-0003, ADR-0004, ADR-0005).

Revision ID: 0010_private_reports
Revises: 0009_data_keys

Five private tables. The insert-only public role may add rows but never read, update, or delete
them, so anonymous submission cannot read back what it wrote. Every table has forced row security.
Report text and contact values are AES-GCM ciphertext under separate data keys; the contact lives
in its own table so it can be crypto-shredded without touching the report. Status history is
append-only, and the report's current status is a projection that must equal the newest event at
commit.
"""

from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0010_private_reports"
down_revision = "0009_data_keys"
branch_labels = None
depends_on = None

CONCERNS = (
    "'no_visible_work', 'incomplete_work', 'unsafe_construction', "
    "'suspected_incorrect_status', 'access_barrier', 'other_concern'"
)
STATUSES = (
    "'received', 'needs_information', 'under_review', 'verified_for_public_update', "
    "'referred', 'closed'"
)
# Every legal (previous, new) pair from the report_status state machine in the controlled
# vocabulary; tests compare this list with contracts/controlled-vocabulary.json.
TRANSITIONS = (
    "('closed', 'under_review'), ('needs_information', 'closed'), "
    "('needs_information', 'under_review'), ('received', 'closed'), "
    "('received', 'needs_information'), ('received', 'under_review'), ('referred', 'closed'), "
    "('referred', 'under_review'), ('under_review', 'closed'), "
    "('under_review', 'needs_information'), ('under_review', 'referred'), "
    "('under_review', 'verified_for_public_update'), ('verified_for_public_update', 'closed'), "
    "('verified_for_public_update', 'referred'), ('verified_for_public_update', 'under_review')"
)

REPORTS = f"""
CREATE TABLE app.reports (
    id uuid NOT NULL,
    project_id uuid NOT NULL,
    concern_category text NOT NULL,
    description_ciphertext bytea NOT NULL,
    description_key_id uuid NOT NULL,
    schema_version integer NOT NULL,
    risk_level text NOT NULL,
    anonymous boolean NOT NULL,
    status text NOT NULL,
    status_updated_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT pk_reports PRIMARY KEY (id),
    CONSTRAINT fk_reports_project_id_projects
        FOREIGN KEY (project_id) REFERENCES app.projects (id) ON DELETE RESTRICT,
    CONSTRAINT fk_reports_description_key_id_data_keys
        FOREIGN KEY (description_key_id) REFERENCES app.data_keys (id) ON DELETE RESTRICT,
    CONSTRAINT ck_reports_concern_category CHECK (concern_category IN ({CONCERNS})),
    CONSTRAINT ck_reports_risk_level CHECK (risk_level IN ('standard', 'elevated', 'high')),
    CONSTRAINT ck_reports_status CHECK (status IN ({STATUSES})),
    CONSTRAINT ck_reports_ciphertext CHECK (
        octet_length(description_ciphertext) BETWEEN 29 AND 65536),
    CONSTRAINT ck_reports_schema_version CHECK (schema_version >= 1)
)
"""

CONTACTS = """
CREATE TABLE app.report_contacts (
    id uuid NOT NULL,
    report_id uuid NOT NULL,
    channel_ciphertext bytea,
    value_ciphertext bytea,
    data_key_id uuid NOT NULL,
    schema_version integer NOT NULL,
    created_at timestamptz NOT NULL,
    destroyed_at timestamptz,
    CONSTRAINT pk_report_contacts PRIMARY KEY (id),
    CONSTRAINT uq_report_contacts_report_id UNIQUE (report_id),
    CONSTRAINT fk_report_contacts_report_id_reports
        FOREIGN KEY (report_id) REFERENCES app.reports (id) ON DELETE CASCADE,
    CONSTRAINT fk_report_contacts_data_key_id_data_keys
        FOREIGN KEY (data_key_id) REFERENCES app.data_keys (id) ON DELETE RESTRICT,
    CONSTRAINT ck_report_contacts_state CHECK (
        (destroyed_at IS NULL AND channel_ciphertext IS NOT NULL AND value_ciphertext IS NOT NULL
         AND octet_length(channel_ciphertext) BETWEEN 29 AND 1024
         AND octet_length(value_ciphertext) BETWEEN 29 AND 4096)
        OR (destroyed_at IS NOT NULL AND channel_ciphertext IS NULL AND value_ciphertext IS NULL))
)
"""

EVENTS = f"""
CREATE TABLE app.report_status_events (
    id uuid NOT NULL,
    report_id uuid NOT NULL,
    previous_status text,
    new_status text NOT NULL,
    public_message text NOT NULL,
    actor_type text NOT NULL,
    actor_id uuid,
    occurred_at timestamptz NOT NULL,
    CONSTRAINT pk_report_status_events PRIMARY KEY (id),
    CONSTRAINT fk_report_status_events_report_id_reports
        FOREIGN KEY (report_id) REFERENCES app.reports (id) ON DELETE CASCADE,
    CONSTRAINT ck_report_status_events_new_status CHECK (new_status IN ({STATUSES})),
    CONSTRAINT ck_report_status_events_message CHECK (char_length(public_message) <= 500),
    CONSTRAINT ck_report_status_events_actor_type CHECK (
        actor_type IN ('reporter', 'reviewer', 'admin', 'system')),
    CONSTRAINT ck_report_status_events_transition CHECK (
        (previous_status IS NULL AND new_status = 'received')
        OR (previous_status IS NOT NULL AND (previous_status, new_status) IN ({TRANSITIONS})))
)
"""

TRACKING = """
CREATE TABLE app.report_tracking_keys (
    id uuid NOT NULL,
    report_id uuid NOT NULL,
    lookup_hmac bytea NOT NULL,
    pepper_version text NOT NULL,
    checksum_version integer NOT NULL,
    created_at timestamptz NOT NULL,
    CONSTRAINT pk_report_tracking_keys PRIMARY KEY (id),
    CONSTRAINT uq_report_tracking_keys_lookup_hmac UNIQUE (lookup_hmac),
    CONSTRAINT uq_report_tracking_keys_report_id UNIQUE (report_id),
    CONSTRAINT fk_report_tracking_keys_report_id_reports
        FOREIGN KEY (report_id) REFERENCES app.reports (id) ON DELETE CASCADE,
    CONSTRAINT ck_report_tracking_keys_hmac CHECK (octet_length(lookup_hmac) = 32),
    CONSTRAINT ck_report_tracking_keys_versions CHECK (
        checksum_version >= 1 AND pepper_version ~ '^[a-z0-9][a-z0-9._-]{0,31}$')
)
"""

EVIDENCE = """
CREATE TABLE app.evidence_files (
    id uuid NOT NULL,
    report_id uuid NOT NULL,
    object_key text NOT NULL,
    display_name text NOT NULL,
    sniffed_mime text NOT NULL,
    size_bytes bigint NOT NULL,
    sha256 text NOT NULL,
    sanitation_state text NOT NULL,
    scan_state text NOT NULL,
    created_at timestamptz NOT NULL,
    CONSTRAINT pk_evidence_files PRIMARY KEY (id),
    CONSTRAINT uq_evidence_files_object_key UNIQUE (object_key),
    CONSTRAINT fk_evidence_files_report_id_reports
        FOREIGN KEY (report_id) REFERENCES app.reports (id) ON DELETE CASCADE,
    CONSTRAINT ck_evidence_files_object_key CHECK (object_key ~ '^[0-9a-f]{32}$'),
    CONSTRAINT ck_evidence_files_display_name CHECK (
        char_length(display_name) BETWEEN 1 AND 120 AND display_name !~ '[/\\\\]'),
    CONSTRAINT ck_evidence_files_mime CHECK (
        sniffed_mime IN ('image/jpeg', 'image/png', 'image/webp', 'application/pdf')),
    CONSTRAINT ck_evidence_files_size CHECK (size_bytes BETWEEN 1 AND 10485760),
    CONSTRAINT ck_evidence_files_sha256 CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_evidence_files_sanitation_state CHECK (sanitation_state = 'sanitised'),
    CONSTRAINT ck_evidence_files_scan_state CHECK (
        scan_state IN ('clean', 'not_scanned_demo'))
)
"""

PROJECTION = """
CREATE FUNCTION app.enforce_report_status_projection() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, app AS $$
DECLARE
    subject uuid;
    newest text;
    current_status text;
BEGIN
    IF TG_TABLE_NAME = 'reports' THEN
        subject := NEW.id;
    ELSE
        subject := NEW.report_id;
    END IF;
    SELECT status INTO current_status FROM app.reports WHERE id = subject;
    SELECT new_status INTO newest FROM app.report_status_events
    WHERE report_id = subject ORDER BY occurred_at DESC, id DESC LIMIT 1;
    IF newest IS DISTINCT FROM current_status THEN
        RAISE EXCEPTION 'a report status must equal its newest status event'
            USING ERRCODE = '23514', CONSTRAINT = 'report_status_projection';
    END IF;
    RETURN NULL;
END
$$
"""

APPEND_ONLY = """
CREATE FUNCTION app.report_status_events_append_only() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, app AS $$
BEGIN
    RAISE EXCEPTION 'status history is append-only; record a new event instead'
        USING ERRCODE = '55000';
END
$$
"""

TABLES = (
    "reports",
    "report_contacts",
    "report_status_events",
    "report_tracking_keys",
    "evidence_files",
)


def _guard(table: str) -> None:
    """Force row security and give the public role insert-only access."""
    target = f"app.{table}"
    op.execute(f"ALTER TABLE {target} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {target} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY {table}_owner_all ON {target} TO shaidago_owner "
        "USING (true) WITH CHECK (true)"
    )
    op.execute(
        f"CREATE POLICY {table}_public_insert ON {target} FOR INSERT "
        "TO shaidago_public WITH CHECK (true)"
    )
    op.execute(f"GRANT INSERT ON {target} TO shaidago_public")


def _reviewer_access(table: str) -> None:
    target = f"app.{table}"
    op.execute(
        f"CREATE POLICY {table}_reviewer_all ON {target} TO shaidago_reviewer "
        "USING (true) WITH CHECK (true)"
    )
    op.execute(f"GRANT SELECT ON {target} TO shaidago_reviewer")


def upgrade() -> None:
    use_owner_role()
    for ddl in (REPORTS, CONTACTS, EVENTS, TRACKING, EVIDENCE):
        op.execute(ddl)
    op.execute("CREATE INDEX ix_reports_project_id ON app.reports (project_id)")
    op.execute("CREATE INDEX ix_reports_status ON app.reports (status, created_at)")
    op.execute(
        "CREATE INDEX ix_report_status_events_report_id "
        "ON app.report_status_events (report_id, occurred_at)"
    )
    op.execute("CREATE INDEX ix_evidence_files_report_id ON app.evidence_files (report_id)")
    for table in TABLES:
        _guard(table)
    # Reviewers read reports, events, and evidence metadata, and may write events and the status
    # projection (through the state-machine service). They get no access to contacts here: contact
    # reads go through an audited function added with the reviewer queue (BE-070).
    for table in ("reports", "report_status_events", "evidence_files"):
        _reviewer_access(table)
    op.execute(
        "GRANT UPDATE (status, status_updated_at, risk_level, updated_at) "
        "ON app.reports TO shaidago_reviewer"
    )
    op.execute("GRANT INSERT ON app.report_status_events TO shaidago_reviewer")
    op.execute(APPEND_ONLY)
    op.execute(
        "CREATE TRIGGER report_status_events_append_only BEFORE UPDATE OR DELETE "
        "ON app.report_status_events FOR EACH ROW "
        "EXECUTE FUNCTION app.report_status_events_append_only()"
    )
    op.execute(PROJECTION)
    op.execute(
        "CREATE CONSTRAINT TRIGGER reports_status_projection AFTER INSERT OR UPDATE OF status "
        "ON app.reports DEFERRABLE INITIALLY DEFERRED FOR EACH ROW "
        "EXECUTE FUNCTION app.enforce_report_status_projection()"
    )
    op.execute(
        "CREATE CONSTRAINT TRIGGER report_status_events_projection AFTER INSERT "
        "ON app.report_status_events DEFERRABLE INITIALLY DEFERRED FOR EACH ROW "
        "EXECUTE FUNCTION app.enforce_report_status_projection()"
    )


def downgrade() -> None:
    use_owner_role()
    for table in (
        "evidence_files",
        "report_tracking_keys",
        "report_status_events",
        "report_contacts",
        "reports",
    ):
        op.execute(f"DROP TABLE app.{table}")
    op.execute("DROP FUNCTION app.enforce_report_status_projection()")
    op.execute("DROP FUNCTION app.report_status_events_append_only()")

"""Encrypted, append-only reviewer notes (BE-072, ADR-0003, ADR-0004).

Revision ID: 0016_report_notes
Revises: 0015_status_event_reason

A note is ciphertext under its own data key (so one note can be crypto-shredded alone), authored
by a reviewer, and never edited or deleted directly: a correction is a new note. Only the reviewer
and owner roles have any privilege on the table; the public role has none, and no tracking or
public view selects from it.
"""

from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0016_report_notes"
down_revision = "0015_status_event_reason"
branch_labels = None
depends_on = None

NOTES = """
CREATE TABLE app.report_notes (
    id uuid NOT NULL,
    report_id uuid NOT NULL,
    author_id uuid,
    body_ciphertext bytea NOT NULL,
    data_key_id uuid NOT NULL,
    schema_version integer NOT NULL,
    created_at timestamptz NOT NULL,
    CONSTRAINT pk_report_notes PRIMARY KEY (id),
    CONSTRAINT fk_report_notes_report_id_reports
        FOREIGN KEY (report_id) REFERENCES app.reports (id) ON DELETE CASCADE,
    CONSTRAINT fk_report_notes_author_id_reviewers
        FOREIGN KEY (author_id) REFERENCES app.reviewers (id) ON DELETE SET NULL,
    CONSTRAINT fk_report_notes_data_key_id_data_keys
        FOREIGN KEY (data_key_id) REFERENCES app.data_keys (id) ON DELETE RESTRICT,
    CONSTRAINT ck_report_notes_body CHECK (octet_length(body_ciphertext) BETWEEN 29 AND 32768),
    CONSTRAINT ck_report_notes_schema_version CHECK (schema_version >= 1)
)
"""
APPEND_ONLY = """
CREATE FUNCTION app.report_notes_append_only() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, app AS $$
BEGIN
    -- A foreign-key cascade from a deleted report runs one trigger level deeper; a direct
    -- DELETE or any UPDATE does not.
    IF TG_OP = 'DELETE' AND pg_trigger_depth() > 1 THEN
        RETURN OLD;
    END IF;
    RAISE EXCEPTION 'notes are append-only; add a correcting note instead' USING ERRCODE = '55000';
END
$$
"""


def upgrade() -> None:
    use_owner_role()
    op.execute(NOTES)
    op.execute("CREATE INDEX ix_report_notes_report_id ON app.report_notes (report_id, created_at)")
    op.execute("ALTER TABLE app.report_notes ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE app.report_notes FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY report_notes_owner_all ON app.report_notes TO shaidago_owner "
        "USING (true) WITH CHECK (true)"
    )
    op.execute(
        "CREATE POLICY report_notes_reviewer_all ON app.report_notes TO shaidago_reviewer "
        "USING (true) WITH CHECK (true)"
    )
    op.execute("GRANT SELECT, INSERT ON app.report_notes TO shaidago_reviewer")
    op.execute(APPEND_ONLY)
    op.execute(
        "CREATE TRIGGER report_notes_append_only BEFORE UPDATE OR DELETE ON app.report_notes "
        "FOR EACH ROW EXECUTE FUNCTION app.report_notes_append_only()"
    )


def downgrade() -> None:
    use_owner_role()
    op.execute("DROP TABLE app.report_notes")
    op.execute("DROP FUNCTION app.report_notes_append_only()")

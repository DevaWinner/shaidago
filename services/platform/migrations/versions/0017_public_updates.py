"""Reviewer-authored public updates, kept apart from the private report (BE-074, ADR-0003).

Revision ID: 0017_public_updates
Revises: 0016_report_notes

A draft holds neutral text a reviewer wrote for the public, its dated citations, and the private
link to the report it came from. That link lives only here, in a table no public role can read:
the published row in ``app.project_updates`` carries no report reference at all. Only
``app.publish_public_update`` may create a public update, and only for a draft whose report is
``verified_for_public_update`` at the version the reviewer previewed. The function re-checks that
state under row locks, writes the public update and its citations with the draft's own ID (so the
previewed ID is the published ID), and records the audit event, all in one transaction. A status
change never calls it.
"""

from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0017_public_updates"
down_revision = "0016_report_notes"
branch_labels = None
depends_on = None

VERIFICATION_STATES = (
    "'awaiting_verification', 'verified_official', 'corroborated', 'community_reviewed', "
    "'disputed', 'outdated'"
)
UPDATES = f"""
CREATE TABLE app.public_updates (
    id uuid NOT NULL,
    report_id uuid NOT NULL,
    project_id uuid NOT NULL,
    statement text NOT NULL,
    effective_on date NOT NULL,
    last_checked_on date,
    verification_state text NOT NULL,
    state text NOT NULL,
    authored_by uuid,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    published_by uuid,
    published_at timestamptz,
    CONSTRAINT pk_public_updates PRIMARY KEY (id),
    CONSTRAINT fk_public_updates_report_id_reports
        FOREIGN KEY (report_id) REFERENCES app.reports (id) ON DELETE RESTRICT,
    CONSTRAINT fk_public_updates_project_id_projects
        FOREIGN KEY (project_id) REFERENCES app.projects (id) ON DELETE RESTRICT,
    CONSTRAINT fk_public_updates_authored_by_reviewers
        FOREIGN KEY (authored_by) REFERENCES app.reviewers (id) ON DELETE SET NULL,
    CONSTRAINT fk_public_updates_published_by_reviewers
        FOREIGN KEY (published_by) REFERENCES app.reviewers (id) ON DELETE SET NULL,
    CONSTRAINT ck_public_updates_statement CHECK (char_length(statement) BETWEEN 10 AND 2000),
    CONSTRAINT ck_public_updates_verification_state CHECK (
        verification_state IN ({VERIFICATION_STATES})),
    CONSTRAINT ck_public_updates_state CHECK (state IN ('draft', 'published', 'withdrawn')),
    CONSTRAINT ck_public_updates_published CHECK (
        (state = 'published') = (published_at IS NOT NULL))
)
"""
CITATIONS = """
CREATE TABLE app.public_update_citations (
    id uuid NOT NULL,
    public_update_id uuid NOT NULL,
    source_version_id uuid NOT NULL,
    passage text NOT NULL,
    location_label text NOT NULL,
    passage_start integer NOT NULL,
    created_at timestamptz NOT NULL,
    CONSTRAINT pk_public_update_citations PRIMARY KEY (id),
    CONSTRAINT uq_public_update_citations_update_version_label
        UNIQUE (public_update_id, source_version_id, location_label),
    CONSTRAINT fk_public_update_citations_public_update_id_public_updates
        FOREIGN KEY (public_update_id) REFERENCES app.public_updates (id) ON DELETE CASCADE,
    CONSTRAINT fk_public_update_citations_source_version_id_source_versions
        FOREIGN KEY (source_version_id) REFERENCES app.source_versions (id) ON DELETE RESTRICT,
    CONSTRAINT ck_public_update_citations_passage CHECK (char_length(passage) BETWEEN 1 AND 1000),
    CONSTRAINT ck_public_update_citations_location CHECK (
        location_label <> '' AND char_length(location_label) <= 200),
    CONSTRAINT ck_public_update_citations_start CHECK (passage_start >= 0)
)
"""
PUBLISH = """
CREATE FUNCTION app.publish_public_update(
    p_draft_id uuid, p_expected_report_version integer, p_actor_type text, p_actor_id uuid,
    p_now timestamptz, p_audit_id uuid, p_request_id text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, app AS $$
DECLARE
    draft app.public_updates%ROWTYPE;
    report_status text;
    report_version integer;
    report_project uuid;
BEGIN
    IF p_actor_type NOT IN ('reviewer', 'admin') THEN
        RAISE EXCEPTION 'only a reviewer may publish' USING ERRCODE = '42501';
    END IF;
    SELECT * INTO draft FROM app.public_updates WHERE id = p_draft_id FOR UPDATE;
    IF NOT FOUND THEN
        RETURN 'not_found';
    END IF;
    SELECT r.status, r.version, r.project_id INTO report_status, report_version, report_project
    FROM app.reports r WHERE r.id = draft.report_id FOR UPDATE;
    IF draft.state <> 'draft' THEN
        RETURN 'not_draft';
    END IF;
    IF report_status <> 'verified_for_public_update' THEN
        RETURN 'report_state';
    END IF;
    IF report_version <> p_expected_report_version THEN
        RETURN 'stale';
    END IF;
    IF draft.project_id <> report_project THEN
        RETURN 'project_mismatch';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM app.public_update_citations c
        JOIN app.source_versions v ON v.id = c.source_version_id
        WHERE c.public_update_id = draft.id AND v.review_state IN ('approved', 'superseded')) THEN
        RETURN 'no_citation';
    END IF;
    -- The public row shares the draft's ID and carries no reference to the report.
    INSERT INTO app.project_updates
        (id, project_id, statement, effective_on, last_checked_on, verification_state,
         visibility, published_at, created_at, updated_at)
    VALUES (draft.id, draft.project_id, draft.statement, draft.effective_on,
            draft.last_checked_on, draft.verification_state, 'public', p_now, p_now, p_now);
    INSERT INTO app.update_citations
        (id, update_id, source_version_id, passage, location_label, passage_start, created_at)
    SELECT uuidv7(), draft.id, c.source_version_id, c.passage, c.location_label,
           c.passage_start, p_now
    FROM app.public_update_citations c
    JOIN app.source_versions v ON v.id = c.source_version_id
    WHERE c.public_update_id = draft.id AND v.review_state IN ('approved', 'superseded');
    UPDATE app.public_updates
    SET state = 'published', published_by = p_actor_id, published_at = p_now, updated_at = p_now
    WHERE id = draft.id;
    INSERT INTO app.audit_events
        (id, occurred_at, actor_type, actor_id, event, subject_type, subject_id, outcome,
         request_id, details)
    VALUES (p_audit_id, p_now, p_actor_type, p_actor_id, 'public_update_published',
            'public_update', draft.id, 'success', p_request_id,
            jsonb_build_object('project_update_id', draft.id, 'report_version', report_version));
    RETURN 'published';
END
$$
"""
GUARD = """
CREATE FUNCTION app.public_updates_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, app AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'public update drafts are never deleted; withdraw one instead'
            USING ERRCODE = '55000';
    END IF;
    -- Published and withdrawn are terminal; a draft's content never changes.
    IF OLD.state <> 'draft' OR NEW.state = 'draft' THEN
        RAISE EXCEPTION 'a public update draft can only be published or withdrawn, once'
            USING ERRCODE = '55000';
    END IF;
    IF (NEW.id, NEW.report_id, NEW.project_id, NEW.statement, NEW.effective_on,
        NEW.last_checked_on, NEW.verification_state, NEW.authored_by, NEW.created_at)
       IS DISTINCT FROM
       (OLD.id, OLD.report_id, OLD.project_id, OLD.statement, OLD.effective_on,
        OLD.last_checked_on, OLD.verification_state, OLD.authored_by, OLD.created_at) THEN
        RAISE EXCEPTION 'public update content is fixed once written' USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END
$$
"""
PUBLISH_SIGNATURE = "app.publish_public_update(uuid, integer, text, uuid, timestamptz, uuid, text)"


def _guard(table: str) -> None:
    target = f"app.{table}"
    op.execute(f"ALTER TABLE {target} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {target} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY {table}_owner_all ON {target} TO shaidago_owner "
        "USING (true) WITH CHECK (true)"
    )
    op.execute(
        f"CREATE POLICY {table}_reviewer_all ON {target} TO shaidago_reviewer "
        "USING (true) WITH CHECK (true)"
    )


def upgrade() -> None:
    use_owner_role()
    op.execute(UPDATES)
    op.execute(CITATIONS)
    op.execute("CREATE INDEX ix_public_updates_report_id ON app.public_updates (report_id)")
    op.execute(
        "CREATE INDEX ix_public_update_citations_source_version_id "
        "ON app.public_update_citations (source_version_id)"
    )
    op.execute(
        "CREATE TRIGGER public_update_citations_passage BEFORE INSERT OR UPDATE "
        "ON app.public_update_citations FOR EACH ROW EXECUTE FUNCTION app.verify_citation_passage()"
    )
    _guard("public_updates")
    _guard("public_update_citations")
    # A reviewer authors drafts and may withdraw one. Everything else on a draft is fixed, and
    # only the publish function can mark it published.
    op.execute("GRANT SELECT, INSERT ON app.public_updates TO shaidago_reviewer")
    op.execute("GRANT UPDATE (state, updated_at) ON app.public_updates TO shaidago_reviewer")
    op.execute("GRANT SELECT, INSERT ON app.public_update_citations TO shaidago_reviewer")
    op.execute(GUARD)
    op.execute(
        "CREATE TRIGGER public_updates_guard BEFORE UPDATE OR DELETE ON app.public_updates "
        "FOR EACH ROW EXECUTE FUNCTION app.public_updates_guard()"
    )
    op.execute(PUBLISH)
    op.execute(f"REVOKE EXECUTE ON FUNCTION {PUBLISH_SIGNATURE} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {PUBLISH_SIGNATURE} TO shaidago_reviewer")


def downgrade() -> None:
    use_owner_role()
    op.execute(f"DROP FUNCTION {PUBLISH_SIGNATURE}")
    op.execute("DROP TABLE app.public_update_citations")
    op.execute("DROP TABLE app.public_updates")
    op.execute("DROP FUNCTION app.public_updates_guard()")

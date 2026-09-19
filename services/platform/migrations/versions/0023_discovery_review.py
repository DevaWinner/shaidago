"""Discovery run APIs: public projections, reviewer decisions, attach, and follow-up answers
(BE-096, ADR-0003, ADR-0004).

Revision ID: 0023_discovery_review
Revises: 0022_discovered_sources

* The public role reads discovery only through ``public_api`` views over public-scope runs and
  their unflagged, non-duplicate, non-rejected sources; report-scoped runs have no path to it. It
  creates a run only through ``app.create_public_discovery_run``, which insists on a public project.
* A reviewer's decision on a discovered source follows the ``discovered_source_disposition``
  machine (enforced by a trigger) and carries an encrypted reason. Attaching is done by one
  function that creates a *pending* source and version (never an approved one, never a fact) and
  carries no report linkage.
* Answers to a run's follow-up questions are encrypted per answer.
"""

from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0023_discovery_review"
down_revision = "0022_discovered_sources"
branch_labels = None
depends_on = None

COLUMNS = """
ALTER TABLE app.discovered_sources
    ADD COLUMN attached_source_id uuid,
    ADD COLUMN decided_by uuid,
    ADD COLUMN decided_at timestamptz,
    ADD COLUMN decision_reason_ciphertext bytea,
    ADD COLUMN decision_key_id uuid,
    ADD CONSTRAINT fk_discovered_sources_attached_source_id_sources
        FOREIGN KEY (attached_source_id) REFERENCES app.sources (id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_discovered_sources_decided_by_reviewers
        FOREIGN KEY (decided_by) REFERENCES app.reviewers (id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_discovered_sources_decision_key_id_data_keys
        FOREIGN KEY (decision_key_id) REFERENCES app.data_keys (id) ON DELETE RESTRICT,
    ADD CONSTRAINT ck_discovered_sources_decision CHECK (
        (disposition = 'not_reviewed' AND decided_at IS NULL
            AND decision_reason_ciphertext IS NULL)
        OR (disposition <> 'not_reviewed' AND decided_at IS NOT NULL
            AND decision_reason_ciphertext IS NOT NULL AND decision_key_id IS NOT NULL)),
    ADD CONSTRAINT ck_discovered_sources_attached CHECK (
        disposition <> 'attached' OR attached_source_id IS NOT NULL)
"""
DISPOSITION_GUARD = """
CREATE FUNCTION app.discovered_sources_disposition_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, app AS $$
BEGIN
    IF NEW.disposition <> OLD.disposition AND NOT (
        (OLD.disposition = 'not_reviewed'
            AND NEW.disposition IN ('attached', 'rejected', 'deferred'))
        OR (OLD.disposition = 'deferred' AND NEW.disposition IN ('attached', 'rejected'))
        OR (OLD.disposition IN ('attached', 'rejected') AND NEW.disposition = 'deferred')
    ) THEN
        RAISE EXCEPTION 'illegal discovered source decision' USING ERRCODE = '55000';
    END IF;
    IF (NEW.id, NEW.scope, NEW.project_id, NEW.report_id, NEW.canonical_url, NEW.excerpt,
        NEW.text_sha256, NEW.first_discovered_at)
       IS DISTINCT FROM
       (OLD.id, OLD.scope, OLD.project_id, OLD.report_id, OLD.canonical_url, OLD.excerpt,
        OLD.text_sha256, OLD.first_discovered_at) THEN
        RAISE EXCEPTION 'discovered source evidence is fixed' USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END
$$
"""
ANSWERS = """
CREATE TABLE app.discovery_follow_up_answers (
    id uuid NOT NULL,
    run_id uuid NOT NULL,
    question_index integer NOT NULL,
    kind text NOT NULL,
    answer_ciphertext bytea,
    data_key_id uuid,
    schema_version integer NOT NULL,
    answered_by uuid,
    created_at timestamptz NOT NULL,
    CONSTRAINT pk_discovery_follow_up_answers PRIMARY KEY (id),
    CONSTRAINT uq_discovery_follow_up_answers_run_question UNIQUE (run_id, question_index),
    CONSTRAINT fk_discovery_follow_up_answers_run_id_discovery_runs
        FOREIGN KEY (run_id) REFERENCES app.discovery_runs (id) ON DELETE CASCADE,
    CONSTRAINT fk_discovery_follow_up_answers_data_key_id_data_keys
        FOREIGN KEY (data_key_id) REFERENCES app.data_keys (id) ON DELETE RESTRICT,
    CONSTRAINT fk_discovery_follow_up_answers_answered_by_reviewers
        FOREIGN KEY (answered_by) REFERENCES app.reviewers (id) ON DELETE SET NULL,
    CONSTRAINT ck_discovery_follow_up_answers_index CHECK (question_index BETWEEN 0 AND 4),
    CONSTRAINT ck_discovery_follow_up_answers_kind CHECK (
        kind IN ('answered', 'skipped', 'unsafe')),
    CONSTRAINT ck_discovery_follow_up_answers_content CHECK (
        (kind = 'answered' AND answer_ciphertext IS NOT NULL AND data_key_id IS NOT NULL)
        OR (kind <> 'answered' AND answer_ciphertext IS NULL AND data_key_id IS NULL))
)
"""
RUN_VIEW = """
CREATE VIEW public_api.discovery_runs AS
SELECT r.id, p.slug AS project_slug, r.status, r.results_found, r.fetched_count,
       r.analysed_count, r.demo_replay, r.version, r.created_at, r.updated_at, r.finished_at,
       r.failure_code, r.analysis
FROM app.discovery_runs r JOIN app.projects p ON p.id = r.project_id
WHERE r.scope = 'public' AND p.visibility = 'public'
"""
SOURCE_VIEW = """
CREATE VIEW public_api.discovery_run_sources AS
SELECT s.run_id, d.id AS source_id, d.canonical_url, d.publisher_domain, d.title,
       d.preliminary_type, d.published_on, d.published_provenance, d.date_conflict,
       d.content_type, d.excerpt, d.availability, d.first_discovered_at, d.last_retrieved_at
FROM app.discovered_source_sightings s
JOIN app.discovered_sources d ON d.id = s.discovered_source_id
JOIN app.discovery_runs r ON r.id = s.run_id
WHERE d.scope = 'public' AND r.scope = 'public' AND d.duplicate_of IS NULL
  AND NOT d.injection_flag AND d.disposition <> 'rejected'
"""
CREATE_PUBLIC_RUN = """
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
ATTACH = """
CREATE FUNCTION app.attach_discovered_source(
    p_id uuid, p_actor uuid, p_now timestamptz, p_source_id uuid, p_version_id uuid,
    p_reason bytea, p_key uuid, p_audit uuid, p_request text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, app AS $$
DECLARE
    d app.discovered_sources%ROWTYPE;
    source uuid;
    kind text;
BEGIN
    SELECT * INTO d FROM app.discovered_sources WHERE id = p_id FOR UPDATE;
    IF NOT FOUND THEN
        RETURN 'not_found';
    END IF;
    IF d.disposition NOT IN ('not_reviewed', 'deferred') THEN
        RETURN 'not_allowed';
    END IF;
    SELECT id INTO source FROM app.sources WHERE canonical_url = d.canonical_url;
    IF source IS NULL THEN
        kind := CASE WHEN d.preliminary_type IN ('government_publication', 'civic_research',
                                                 'other_public_source')
                     THEN d.preliminary_type ELSE 'other_public_source' END;
        INSERT INTO app.sources
            (id, canonical_url, title, publisher, source_type, information_class, availability,
             availability_checked_at, created_at, updated_at)
        VALUES (p_source_id, d.canonical_url, coalesce(d.title, d.publisher_domain),
                d.publisher_domain, kind,
                CASE WHEN kind = 'government_publication' THEN 'official_source'
                     ELSE 'independent_source' END,
                'available', p_now, p_now, p_now);
        source := p_source_id;
    END IF;
    INSERT INTO app.source_versions
        (id, source_id, content_sha256, content_text, media_type, retrieved_at, review_state,
         created_at)
    VALUES (p_version_id, source, encode(sha256(convert_to(d.excerpt, 'UTF8')), 'hex'),
            d.excerpt, 'text/plain', d.last_retrieved_at, 'pending', p_now)
    ON CONFLICT (source_id, content_sha256) DO NOTHING;
    UPDATE app.discovered_sources
    SET disposition = 'attached', attached_source_id = source, decided_by = p_actor,
        decided_at = p_now, decision_reason_ciphertext = p_reason, decision_key_id = p_key,
        updated_at = p_now
    WHERE id = p_id;
    INSERT INTO app.audit_events
        (id, occurred_at, actor_type, actor_id, event, subject_type, subject_id, outcome,
         request_id, details)
    VALUES (p_audit, p_now, 'reviewer', p_actor, 'discovered_source_attached',
            'discovered_source', p_id, 'success', p_request,
            jsonb_build_object('source_id', source, 'review_state', 'pending'));
    RETURN 'attached';
END
$$
"""
CREATE_SIGNATURE = "app.create_public_discovery_run(uuid, text, timestamptz, text, boolean)"
ATTACH_SIGNATURE = (
    "app.attach_discovered_source(uuid, uuid, timestamptz, uuid, uuid, bytea, uuid, uuid, text)"
)


def upgrade() -> None:
    use_owner_role()
    op.execute(COLUMNS)
    op.execute(DISPOSITION_GUARD)
    op.execute(
        "CREATE TRIGGER discovered_sources_disposition_guard BEFORE UPDATE "
        "ON app.discovered_sources FOR EACH ROW "
        "EXECUTE FUNCTION app.discovered_sources_disposition_guard()"
    )
    op.execute(
        "GRANT UPDATE (disposition, decided_by, decided_at, decision_reason_ciphertext, "
        "decision_key_id, updated_at) ON app.discovered_sources TO shaidago_reviewer"
    )
    # A reviewer may reject a run that needs review, which records a reviewer failure code.
    op.execute("GRANT UPDATE (failure_code) ON app.discovery_runs TO shaidago_reviewer")
    op.execute(ANSWERS)
    op.execute("ALTER TABLE app.discovery_follow_up_answers ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE app.discovery_follow_up_answers FORCE ROW LEVEL SECURITY")
    for role in ("owner", "reviewer"):
        op.execute(
            f"CREATE POLICY discovery_follow_up_answers_{role}_all "
            f"ON app.discovery_follow_up_answers TO shaidago_{role} USING (true) WITH CHECK (true)"
        )
    op.execute("GRANT SELECT, INSERT ON app.discovery_follow_up_answers TO shaidago_reviewer")
    op.execute(RUN_VIEW)
    op.execute(SOURCE_VIEW)
    for ddl, signature, role in (
        (CREATE_PUBLIC_RUN, CREATE_SIGNATURE, "shaidago_public"),
        (ATTACH, ATTACH_SIGNATURE, "shaidago_reviewer"),
    ):
        op.execute(ddl)
        op.execute(f"REVOKE EXECUTE ON FUNCTION {signature} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO {role}")


def downgrade() -> None:
    use_owner_role()
    op.execute(f"DROP FUNCTION {ATTACH_SIGNATURE}")
    op.execute(f"DROP FUNCTION {CREATE_SIGNATURE}")
    op.execute("DROP VIEW public_api.discovery_run_sources")
    op.execute("DROP VIEW public_api.discovery_runs")
    op.execute("DROP TABLE app.discovery_follow_up_answers")
    op.execute("DROP TRIGGER discovered_sources_disposition_guard ON app.discovered_sources")
    op.execute("DROP FUNCTION app.discovered_sources_disposition_guard()")
    op.execute(
        "ALTER TABLE app.discovered_sources "
        "DROP CONSTRAINT ck_discovered_sources_attached, "
        "DROP CONSTRAINT ck_discovered_sources_decision, "
        "DROP CONSTRAINT fk_discovered_sources_decision_key_id_data_keys, "
        "DROP CONSTRAINT fk_discovered_sources_decided_by_reviewers, "
        "DROP CONSTRAINT fk_discovered_sources_attached_source_id_sources, "
        "DROP COLUMN decision_key_id, DROP COLUMN decision_reason_ciphertext, "
        "DROP COLUMN decided_at, DROP COLUMN decided_by, DROP COLUMN attached_source_id"
    )

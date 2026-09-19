"""Escalation routes: locality, concern category, and locale guidance with a cited source.

Revision ID: 0005_escalation_routes
Revises: 0004_sources_facts_citations

No route is seeded. A route may be active only while it cites an approved (or superseded) source
version and carries a verification date, and it always carries its own non-emergency disclaimer.
There is deliberately no phone-number or address column: contact details appear only inside the
reviewed, cited instruction text.
"""

from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0005_escalation_routes"
down_revision = "0004_sources_facts_citations"
branch_labels = None
depends_on = None

TABLE = """
CREATE TABLE app.escalation_routes (
    id uuid NOT NULL,
    locality_id uuid NOT NULL,
    concern_category text,
    locale text NOT NULL,
    organisation text NOT NULL,
    instructions text NOT NULL,
    disclaimer text NOT NULL,
    source_version_id uuid NOT NULL,
    verified_on date NOT NULL,
    valid_from date NOT NULL,
    valid_to date,
    active boolean NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT pk_escalation_routes PRIMARY KEY (id),
    CONSTRAINT uq_escalation_routes_scope
        UNIQUE NULLS NOT DISTINCT (locality_id, concern_category, locale, organisation),
    CONSTRAINT fk_escalation_routes_locality_id_localities
        FOREIGN KEY (locality_id) REFERENCES app.localities (id) ON DELETE RESTRICT,
    CONSTRAINT fk_escalation_routes_source_version_id_source_versions
        FOREIGN KEY (source_version_id) REFERENCES app.source_versions (id) ON DELETE RESTRICT,
    CONSTRAINT ck_escalation_routes_concern_category CHECK (
        concern_category IS NULL OR concern_category IN (
            'no_visible_work', 'incomplete_work', 'unsafe_construction',
            'suspected_incorrect_status', 'access_barrier', 'other_concern')),
    CONSTRAINT ck_escalation_routes_locale CHECK (locale IN ('en', 'ha', 'ig', 'yo')),
    CONSTRAINT ck_escalation_routes_text CHECK (
        organisation <> '' AND instructions <> '' AND disclaimer <> ''
        AND char_length(instructions) <= 2000 AND char_length(disclaimer) <= 1000),
    CONSTRAINT ck_escalation_routes_validity CHECK (valid_to IS NULL OR valid_to >= valid_from),
    CONSTRAINT ck_escalation_routes_verified_not_future CHECK (
        verified_on <= (updated_at AT TIME ZONE 'Africa/Lagos')::date)
)
"""

ENFORCE = """
CREATE FUNCTION app.enforce_active_route_source() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, app AS $$
BEGIN
    IF NEW.active AND NOT EXISTS (
        SELECT 1 FROM app.source_versions v
        WHERE v.id = NEW.source_version_id AND v.review_state IN ('approved', 'superseded')) THEN
        RAISE EXCEPTION 'an active escalation route must cite an approved source version'
            USING ERRCODE = '23514', CONSTRAINT = 'active_route_source';
    END IF;
    RETURN NULL;
END
$$
"""

VIEW = """
CREATE VIEW public_api.escalation_routes AS
SELECT r.id, l.slug AS locality_slug, r.concern_category, r.locale, r.organisation,
       r.instructions, r.disclaimer, r.verified_on, r.valid_from, r.valid_to,
       s.title AS source_title, s.publisher AS source_publisher,
       s.canonical_url AS source_url
FROM app.escalation_routes r
JOIN app.localities l ON l.id = r.locality_id
JOIN app.source_versions v ON v.id = r.source_version_id
JOIN app.sources s ON s.id = v.source_id
WHERE r.active
"""


def upgrade() -> None:
    use_owner_role()
    op.execute(TABLE)
    op.execute(
        "CREATE INDEX ix_escalation_routes_locality_id ON app.escalation_routes (locality_id)"
    )
    op.execute(
        "CREATE INDEX ix_escalation_routes_source_version_id "
        "ON app.escalation_routes (source_version_id)"
    )
    op.execute(ENFORCE)
    op.execute(
        "CREATE CONSTRAINT TRIGGER escalation_routes_active_source AFTER INSERT OR UPDATE "
        "ON app.escalation_routes DEFERRABLE INITIALLY DEFERRED FOR EACH ROW "
        "EXECUTE FUNCTION app.enforce_active_route_source()"
    )
    op.execute("GRANT SELECT ON app.escalation_routes TO shaidago_reviewer")
    op.execute(VIEW)


def downgrade() -> None:
    use_owner_role()
    op.execute("DROP VIEW public_api.escalation_routes")
    op.execute("DROP TABLE app.escalation_routes")
    op.execute("DROP FUNCTION app.enforce_active_route_source()")

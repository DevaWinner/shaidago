"""Public citations expose the approved source version they cite (BE-041, FE-115).

Revision ID: 0026_citation_version_id
Revises: 0025_public_awaiting

A reviewer composing a public update must cite an approved source version by id, but no response
exposed one: the public citation views returned `source_id` only, and there is no endpoint that
lists versions. The publication flow was therefore unreachable through the API, and the frontend
composer had nothing to offer a reviewer.

The id of an approved public source version is not private: the same row already publishes the
source, its canonical URL, the quoted passage and the retrieval time. Both public citation views now
return it, appended as the last column so `CREATE OR REPLACE` keeps `public_api.cited_sources`,
which depends on them, intact.
"""

from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0026_citation_version_id"
down_revision = "0025_public_awaiting"
branch_labels = None
depends_on = None

FACT_CITATIONS = """
CREATE OR REPLACE VIEW public_api.fact_citations AS
SELECT ci.fact_id,
       ci.passage,
       ci.location_label,
       s.id AS source_id,
       s.title AS source_title,
       s.publisher,
       s.canonical_url,
       s.source_type,
       s.information_class,
       v.retrieved_at{version_column}
  FROM app.fact_citations ci
  JOIN app.project_facts f ON f.id = ci.fact_id AND f.visibility = 'public'
  JOIN app.source_versions v
    ON v.id = ci.source_version_id AND v.review_state IN ('approved', 'superseded')
  JOIN app.sources s ON s.id = v.source_id
"""

UPDATE_CITATIONS = """
CREATE OR REPLACE VIEW public_api.update_citations AS
SELECT ci.update_id,
       ci.passage,
       ci.location_label,
       s.id AS source_id,
       s.title AS source_title,
       s.publisher,
       s.canonical_url,
       s.source_type,
       s.information_class,
       v.retrieved_at{version_column}
  FROM app.update_citations ci
  JOIN app.project_updates u ON u.id = ci.update_id AND u.visibility = 'public'
  JOIN app.source_versions v
    ON v.id = ci.source_version_id AND v.review_state IN ('approved', 'superseded')
  JOIN app.sources s ON s.id = v.source_id
"""

WITH_VERSION = ",\n       v.id AS source_version_id"
GRANTS = (
    "GRANT SELECT ON public_api.fact_citations TO shaidago_public, shaidago_reviewer",
    "GRANT SELECT ON public_api.update_citations TO shaidago_public, shaidago_reviewer",
)


def _replace(version_column: str) -> None:
    use_owner_role()
    op.execute(FACT_CITATIONS.format(version_column=version_column))
    op.execute(UPDATE_CITATIONS.format(version_column=version_column))
    for grant in GRANTS:
        op.execute(grant)


CITED_SOURCES = """
CREATE VIEW public_api.cited_sources AS
SELECT id, canonical_url, title, publisher, source_type, information_class, availability,
       availability_checked_at
  FROM app.sources s
 WHERE EXISTS (SELECT 1 FROM public_api.fact_citations c WHERE c.source_id = s.id)
    OR EXISTS (SELECT 1 FROM public_api.update_citations c WHERE c.source_id = s.id)
"""
CITED_SOURCES_GRANT = (
    "GRANT SELECT ON public_api.cited_sources "
    "TO shaidago_public, shaidago_reviewer, shaidago_worker"
)


def upgrade() -> None:
    _replace(WITH_VERSION)


def downgrade() -> None:
    # `CREATE OR REPLACE VIEW` cannot remove a column, so going back needs a real drop, and
    # `cited_sources` depends on both views; it is rebuilt from its migration 0004 definition.
    use_owner_role()
    op.execute("DROP VIEW public_api.cited_sources")
    op.execute("DROP VIEW public_api.fact_citations")
    op.execute("DROP VIEW public_api.update_citations")
    _replace("")
    op.execute(CITED_SOURCES)
    op.execute(CITED_SOURCES_GRANT)

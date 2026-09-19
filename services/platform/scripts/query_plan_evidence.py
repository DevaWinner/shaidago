"""Capture EXPLAIN evidence for the public list query on a scaled synthetic dataset.

    uv run --env-file ../../.env python scripts/query_plan_evidence.py [--projects 20000]

Creates a throwaway database on the local Compose PostgreSQL, migrates to the revision before the
index migration, seeds synthetic rows, records plans, migrates to head, records plans again, and
drops the database. Everything is synthetic; nothing touches a real database.
"""

import argparse
import os
import sys
import uuid
from typing import Any

import psycopg
from alembic import command
from psycopg import sql

from shaidago.db.revision import alembic_config, expected_head
from shaidago.projects.catalogue import LIST_PROJECTS_SQL

BASELINE_REVISION = "0005_escalation_routes"
BASE_PARAMS: dict[str, object] = {
    "locale": "en",
    "locality": None,
    "category": None,
    "status": None,
    "verification": None,
    "q": None,
    "after_updated": None,
    "after_id": None,
    "limit": 21,
}
CASES: dict[str, dict[str, object]] = {
    "list, newest first": {},
    "list, category filter": {"category": "health"},
    "list, locality and status": {"locality": "synthetic-council-a", "status": "in_progress"},
    "list, text search": {"q": "rehabilitation"},
    "list, second page": {
        "after_updated": "2026-01-01T00:00:00+00:00",
        "after_id": "ffffffff-ffff-7fff-bfff-ffffffffffff",
    },
}

Connection = psycopg.Connection[tuple[Any, ...]]


def connect(dbname: str) -> Connection:
    return psycopg.connect(
        host=os.environ.get("INFRA_DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("INFRA_POSTGRES_PORT", "55432")),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=dbname,
        autocommit=True,
    )


def seed(connection: Connection, count: int) -> None:
    # One transaction: the deferred source-text rule is checked at commit.
    with connection.transaction():
        connection.execute(
            "INSERT INTO app.localities SELECT gen_random_uuid(), 'synthetic-council-' || s, "
            "'C' || s, 'area_council', NULL, ARRAY['en'], now(), now() "
            "FROM (VALUES ('a'), ('b')) AS t(s)"
        )
        connection.execute(
            "INSERT INTO app.projects SELECT gen_random_uuid(), 'synthetic-project-' || n, "
            "(SELECT id FROM app.localities WHERE slug = 'synthetic-council-' || "
            "CASE WHEN n %% 2 = 0 THEN 'a' ELSE 'b' END), "
            "(ARRAY['health','education','water_sanitation','roads_public_works',"
            "'other_public_service'])[1 + n %% 5], "
            "(ARRAY['unknown','planned','procurement','in_progress','on_hold','completed',"
            "'cancelled'])[1 + n %% 7], "
            "CASE WHEN n %% 20 = 0 THEN 'hidden' ELSE 'public' END, NULL, "
            "now() - (n || ' minutes')::interval, now() - (n || ' minutes')::interval "
            "FROM generate_series(1, %s) AS n",
            (count,),
        )
        connection.execute(
            "INSERT INTO app.project_translations SELECT gen_random_uuid(), p.id, 'en', "
            "'Synthetic project ' || p.slug, "
            "CASE WHEN random() < 0.3 THEN 'Rehabilitation of a synthetic facility' "
            "ELSE 'A synthetic works project' END, 'A synthetic deliverable', 'reviewed', now(), "
            "NULL, now(), now() FROM app.projects p"
        )
    connection.execute("ANALYZE")


def describe(document: dict[str, Any]) -> tuple[float, list[str]]:
    """Execution time in milliseconds and the plan's nodes, outermost first."""
    nodes: list[str] = []

    def walk(node: dict[str, Any]) -> None:
        label = str(node["Node Type"])
        if "Index Name" in node:
            label += f" ({node['Index Name']})"
        elif "Relation Name" in node:
            label += f" ({node['Relation Name']})"
        nodes.append(label)
        for child in node.get("Plans", []):
            walk(child)

    walk(document["Plan"])
    return float(document["Execution Time"]), nodes


def explain(connection: Connection, overrides: dict[str, object]) -> tuple[float, list[str]]:
    params = BASE_PARAMS | overrides
    query = "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + LIST_PROJECTS_SQL.text
    for key in params:  # convert :name binds to psycopg's %(name)s form
        query = query.replace(f":{key}", f"%({key})s")
    row = connection.execute(query, params).fetchone()
    if row is None:
        raise RuntimeError("no plan returned")
    return describe(row[0][0])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--projects", type=int, default=20000)
    parser.add_argument(
        "--drop-index", help="drop this app-schema index after migrating, to measure its worth"
    )
    args = parser.parse_args()
    name = f"shaidago_plans_{uuid.uuid4().hex[:8]}"
    admin = connect("postgres")
    admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        host = os.environ.get("INFRA_DB_HOST", "127.0.0.1")
        port = os.environ.get("INFRA_POSTGRES_PORT", "55432")
        credentials = f"{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        config = alembic_config(f"postgresql+psycopg://{credentials}@{host}:{port}/{name}")
        command.upgrade(config, BASELINE_REVISION)
        connection = connect(name)
        seed(connection, args.projects)
        before = {case: explain(connection, o) for case, o in CASES.items()}
        command.upgrade(config, expected_head())
        if args.drop_index:
            connection.execute(sql.SQL("DROP INDEX app.{}").format(sql.Identifier(args.drop_index)))
        connection.execute("ANALYZE")
        after = {case: explain(connection, o) for case, o in CASES.items()}
        rows = ["| Query | Before (ms) | After (ms) | Plan after (outermost first) |"]
        rows.append("| --- | ---: | ---: | --- |")
        rows.extend(
            f"| {case} | {before[case][0]:.2f} | {after[case][0]:.2f} | "
            f"{' > '.join(after[case][1][:5])} |"
            for case in CASES
        )
        sys.stdout.write(
            f"Dataset: {args.projects} synthetic projects.\n\n" + "\n".join(rows) + "\n"
        )
    finally:
        admin.execute(
            sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name))
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

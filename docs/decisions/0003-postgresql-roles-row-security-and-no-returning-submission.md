# ADR-0003: PostgreSQL roles, public views, row security, and the no-`RETURNING` submission path

- **Status:** accepted
- **Date:** 2026-09-19
- **Task:** BE-004
- **Supersedes:** none

## Context

Application authorisation in FastAPI is mandatory, but a single all-powerful database login means one missed check or one injected query can read every report and contact. The threat model (TM-I01, TM-E04) requires database-level least privilege as defence in depth.

Anonymous submission must insert a report without being able to read reports back. PostgreSQL requires `SELECT` privilege for the columns an `INSERT … RETURNING` returns, and under row-level security it also requires a `SELECT` policy. SQLAlchemy emits `RETURNING` by default to read back server-generated primary keys and defaults, so a naive mapping fails with a permission error at runtime.

## Decision

1. **Five database roles.** Login roles do not own objects and are not superusers.

   | Role | Purpose | Key grants |
   | --- | --- | --- |
   | `shaidago_owner` | Owns schemas and objects; used only by migrations | All DDL; no application login in running services |
   | `shaidago_public` | Public reads and anonymous submission | `SELECT` on `public_api` views only; `INSERT` (no `SELECT`) on report, contact, data-key, tracking-key, evidence, status-event, and reporter-handle tables; `EXECUTE` on the tracking, handle, and idempotency lookup functions |
   | `shaidago_reviewer` | Authenticated reviewer operations | `SELECT`/`INSERT`/`UPDATE` on private tables required by review; contacts only through a function that writes an audit event |
   | `shaidago_worker` | Background jobs | Discovery, sanitation-result, and chunk tables; no access to contacts or reviewer notes |
   | `shaidago_readonly_ops` | Operational diagnostics | Aggregate views only; no private columns |

2. **Two schemas.** `app` holds tables. `public_api` holds views that project only public columns and rows (approved, visible, cited). Public repositories query `public_api` only.
3. **Row-level security** is enabled and forced on every private table. Policies are written per role. The public role has an `INSERT` policy and no `SELECT` policy on private tables.
4. **Narrow lookups through functions.** Tracking-code lookup, handle verification, handle report listing, and submission idempotency replay (ADR-0005) are `SECURITY DEFINER` functions owned by `shaidago_owner` with a fixed `search_path`. They take a keyed hash or handle and return only the public-safe status projection.
5. **No read-back on private inserts.** Private-report mappers use application-generated UUIDv7 primary keys and application-supplied timestamps, set `implicit_returning=False` and `eager_defaults=False`, and declare no server defaults that the ORM would fetch. Submission code uses `session.add(...)` and `flush()` without refreshing.
6. Each process selects its role by connection string: the API uses `shaidago_public` for public routers and `shaidago_reviewer` for reviewer routers through two engines; the worker uses `shaidago_worker`.

## Alternatives considered

| Alternative | Reason rejected |
| --- | --- |
| One application role plus application checks only | One missed check or injection exposes all private data; no defence in depth. |
| Grant `SELECT` to the public role and rely on RLS filters | A policy mistake becomes a data leak; insert-only is simpler to prove. |
| Keep `RETURNING` and grant column-level `SELECT (id)` | Leaks row existence and IDs to the public role and invites broadening later. |
| Separate databases for public and private data | Breaks transactional publication and citation checks across the boundary. |

## Consequences

- An injection through a public route cannot read private tables, and the worker cannot read contacts.
- The API holds two connection pools. Routers must declare which engine they use; mixing them is a review-blocking error.
- ORM conveniences that refresh rows are unavailable on private-insert mappers; integration tests catch regressions.
- Railway's managed PostgreSQL allows creating roles, but role creation runs as deployment SQL under the owner role, not as an application-startup side effect.

## Migration impact

Roles, schemas, grants, and policies are created by Alembic migrations (BE-033) or versioned deployment SQL run by the migration job (BE-112). Every later table migration must add its grants and policies in the same revision.

## Enforcement

| Control | Owning task | Planned verification |
| --- | --- | --- |
| Allowed and denied operations per role | BE-032 | Integration tests connect as each role and assert `SELECT`/`INSERT`/`UPDATE` outcomes on every private table and view. |
| Insert without read-back | BE-032, BE-061 | Submission runs as `shaidago_public`; test captures emitted SQL and asserts no `RETURNING` or `SELECT` on private tables. |
| Public repositories read only views | BE-044, BE-045 | Repository test asserts the public engine cannot read `app` tables. |
| Lookup functions return only safe projections | BE-065, BE-066 | Function output schema test with private canary values. |
| Every new private table has RLS | BE-033 | Migration test fails if a table in `app` lacks forced row security. |

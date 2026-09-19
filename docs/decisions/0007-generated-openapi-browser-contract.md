# ADR-0007: Generated OpenAPI contract for the browser boundary

- **Status:** accepted
- **Date:** 2026-09-19
- **Task:** BE-004
- **Supersedes:** none

## Context

The web app and the API are separate stacks in separate languages. Hand-written TypeScript types for API responses drift silently: a renamed field or new status value breaks the UI only at runtime, and a widened response can leak a private field into a client type without anyone noticing. Machine values such as report statuses are already frozen in `contracts/controlled-vocabulary.json` (BE-002) and must flow unchanged into the database, the API, and the UI.

## Decision

1. **Source of truth.** FastAPI route signatures and Pydantic models define the HTTP contract. A deterministic command writes `contracts/openapi.json` with sorted keys, stable formatting, and no environment-specific servers or hostnames. It runs without databases, Redis, or providers.
2. **Stable operation IDs.** Every route declares an explicit `operation_id` of the form `<module>_<action>`, for example `reports_submit` or `report_status_lookup`. Generated IDs from function names are not allowed.
3. **Vocabulary flows from the contract.** Python `StrEnum` types for controlled vocabularies are generated from `contracts/controlled-vocabulary.json` with a drift check, so OpenAPI enum values, database `CHECK` constraints, and UI labels all derive from one file.
4. **Client generation.** `apps/web` generates types with `openapi-typescript` into `src/lib/api/generated/` and calls the API through `openapi-fetch`. Generated files carry a do-not-edit header.
5. **Drift is a CI failure.** CI regenerates `openapi.json` and the TypeScript types and fails on any uncommitted difference.
6. **Separate public and private schemas.** Public and reviewer responses use distinct Pydantic models, never one model with optional private fields. A contract test fails if a known private field name appears in any public operation schema.
7. **Errors.** Every operation documents its `application/problem+json` responses with stable machine codes.
8. **Breaking changes.** Removing or renaming a field, operation, or enum value requires a new ADR, a deprecation window where a deployed client depends on it, and a new machine value rather than a repurposed one.

## Alternatives considered

| Alternative | Reason rejected |
| --- | --- |
| Hand-written TypeScript types | Drift is invisible until runtime. |
| Contract-first YAML written by hand, then server stubs | Two sources of truth for one maintainer; FastAPI already produces an accurate schema from the models it enforces. |
| GraphQL | Second query language and resolver authority; rejected in the implementation plan. |
| tRPC or shared TypeScript types | Requires a TypeScript backend; the backend is Python. |

## Consequences

- A backend change that alters a response shows up as a reviewable diff in `contracts/openapi.json` and in generated types in the same pull request.
- Frontend code maps generated types into smaller view models; it never imports ORM or database shapes.
- Contract fuzzing (Schemathesis) runs against the same committed file.

## Migration impact

None at baseline. Versioned paths (`/v1`) allow a future `/v2` alongside `/v1` if a breaking change becomes unavoidable.

## Enforcement

| Control | Owning task | Planned verification |
| --- | --- | --- |
| Deterministic generation without providers | BE-011, BE-021 | `openapi-generate` twice produces byte-identical output with providers offline. |
| Committed contract matches code | BE-011, BE-120 | `openapi-check` fails on any diff. |
| Explicit operation IDs | BE-045 | Contract test rejects missing or duplicate operation IDs. |
| No private fields in public schemas | BE-045, BE-102 | Denylist test over every public operation schema. |
| Vocabulary enums derived from the contract | BE-040 | Drift check between generated enums and `contracts/controlled-vocabulary.json`. |

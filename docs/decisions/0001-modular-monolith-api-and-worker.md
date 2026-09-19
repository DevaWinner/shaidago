# ADR-0001: Modular monolith with API and worker entry points

- **Status:** accepted
- **Date:** 2026-09-19
- **Task:** BE-004
- **Supersedes:** none

## Context

The backend owns every domain rule: report privacy, review state, citations, publication, and Source Scout. Some of that work is slow and must not block a request: page fetches, search calls, model analysis, and embedding generation. The pilot has one maintainer, six to eight projects, and a hard deadline of 21 September 2026 at 23:59 UTC. Every extra deployable adds configuration, secrets, network policy, and failure modes that judges must be able to run from a clean checkout.

## Decision

1. `services/platform` is one Python package, `shaidago`, with two process entry points built from the same image:
   - `api`: the FastAPI application created by `create_app(settings, dependencies)`;
   - `worker`: the Dramatiq worker that runs discovery and other bounded background jobs.
2. Domain modules (`projects`, `sources`, `reports`, `review`, `discovery`, `retrieval`, `files`, `auth`, `audit`) call each other through typed service and repository interfaces in-process, never over HTTP.
3. The worker does not call the API. It reaches PostgreSQL with its own database role (ADR-0003) and object storage with its own scoped credential. If a future job needs an API call, it gets a distinct internal caller identity under ADR-0002.
4. Jobs carry identifiers and a schema version only. The worker reloads authorised state from PostgreSQL, so a queue message can never carry private report text, contacts, tracking codes, or attachment bytes.
5. Evidence sanitation runs in the API process (ADR-0006), not the worker. Raw uploads must never reach shared durable storage, and separate containers do not share a disk.
6. Module boundaries are enforced by import rules: a module imports another module's `service` or public `models`, never its `tables` or `repository`.

## Alternatives considered

| Alternative | Reason rejected |
| --- | --- |
| Microservices per domain | Multiplies deployables, secrets, and network authentication for one maintainer and six projects, with no isolation benefit that database roles do not already give. |
| Single process with in-request slow work | Discovery takes tens of seconds and depends on third-party latency; it would tie up request workers and make timeouts the normal path. |
| Background tasks inside FastAPI (`BackgroundTasks`) | Work is lost on restart and has no retry, dead-letter, or cancellation state. |
| Separate worker codebase | Duplicates domain models and policy, creating a second authority. |

## Consequences

- One image, one lockfile, and one test suite cover both processes. Domain policy has one implementation.
- The worker has the same code but narrower database grants, so a worker compromise cannot read contacts or reviewer notes.
- Splitting a module into its own service later requires only replacing an in-process interface with a client; import rules keep that possible.
- CPU-bound sanitation in the API process needs a bounded process pool and concurrency cap (ADR-0006) so uploads cannot starve request handling.

## Migration impact

None; this is the baseline. A later split creates a new ADR and keeps the existing `/v1` contract stable.

## Enforcement

| Control | Owning task | Planned verification |
| --- | --- | --- |
| Same image runs both commands | BE-110 | Container test starts `api` and `worker` from one image. |
| No import-time I/O; injectable dependencies | BE-021 | App-factory test constructs the app with fixture dependencies and no network. |
| Jobs carry IDs only | BE-090 | Job-envelope schema test rejects extra fields and private canaries. |
| Worker grants narrower than API | BE-032 | Role test: worker role denied on contacts and reviewer notes. |
| Module import boundaries | BE-012 | CI import-rule check fails on a cross-module `tables`/`repository` import. |

# AGENTS.md

## Scope and purpose

These instructions apply to the entire repository. A nested `AGENTS.md` may add stricter module-specific rules; it must not weaken the privacy, publication, evidence, or security requirements here.

ShaidaGo is a low-bandwidth civic accountability and safe-reporting platform for an Abuja pilot covering AMAC and Bwari Area Councils. The public product supports English (`en`), Hausa (`ha`), Igbo (`ig`), and Yoruba (`yo`). Treat the repository as a judgeable public artifact and the reporting domain as safety-sensitive.

The repository is currently at the architecture/foundation stage. Do not claim that an application, command, test, integration, deployment, dataset, or translation exists or works until the corresponding artifact is present and verified.

## Read before changing code

1. Inspect `git status`, recent changes, and the files in scope. Preserve unrelated and uncommitted work.
2. Read `PRODUCT.md`, `docs/PRODUCT_BRIEF.md`, `docs/IMPLEMENTATION_PLAN.md`, the relevant `docs/BACKEND_BUILD_ORDER.md` or `docs/FRONTEND_BUILD_ORDER.md`, and the nearest applicable `AGENTS.md`.
3. Identify the build gate and acceptance criterion that the change advances.
4. Trace the complete browser → BFF → API → database/worker boundary for affected flows before editing.
5. Prefer a small vertical change with tests and documentation over broad scaffolding that does not produce a working user outcome.

## Authority and conflict resolution

Use this order when repository sources conflict:

1. The current user request and explicitly accepted decisions.
2. `PRODUCT.md` for product scope, pilot, users, languages, and non-goals.
3. `docs/PRODUCT_BRIEF.md` for detailed user journeys, trust rules, requirements, and acceptance criteria.
4. `docs/IMPLEMENTATION_PLAN.md` for accepted architecture, stack, data model, security controls, tests, and build order.
5. `docs/BACKEND_BUILD_ORDER.md` and `docs/FRONTEND_BUILD_ORDER.md` for task-level execution. They operationalise, but never override, the implementation plan.
6. Generated `contracts/openapi.json` for implemented HTTP contracts.
7. Migrations and executable tests for implemented behaviour.

Do not silently work around a contradiction. Correct the authoritative document, add an architecture decision record when appropriate, and change code and tests in the same pull request.

## Non-negotiable product invariants

- Use only public, non-sensitive sources for project records and only fictional reports in the hackathon environment.
- Never describe a project, institution, contractor, or person as corrupt, fraudulent, guilty, abandoned, or complete without exact reliable evidence supporting that wording.
- Every public fact and timeline update must resolve to an approved citation and a visible last-checked or effective date.
- AI output is an explanation, not a source. It cannot verify an allegation, infer guilt, assign a truth score, change a public status, or publish content.
- New reports, attachments, contacts, follow-up answers, internal notes, and report-scoped discovery are private by default and never publish automatically.
- Anonymous reporting must work without an account, email address, or phone number. Optional reporter handles remain optional and contain no identity or recovery data.
- Human review is required before community evidence, a discovered source, or a public-safe report summary affects the public record.
- The prototype is not an emergency service. Show the approved local escalation guidance without promising protection or response capabilities the product does not provide.
- Do not send reporter identity, contact data, private text, attachment content, tracking codes, internal notes, or unnecessary precise locations to search or AI providers.

## Required architecture

Maintain separate, independently tooled stacks with a deliberate BFF boundary:

- `apps/web`: Next.js App Router, React, strict TypeScript, server-rendered public pages, and thin same-origin Route Handlers for browser mutations, uploads, polling, and reviewer actions.
- `services/platform`: one FastAPI modular monolith with `api` and Dramatiq `worker` entry points. It owns all domain policy, authorisation, visibility, state transitions, citations, audit events, and publication decisions.
- PostgreSQL is the authoritative datastore. Redis is for bounded jobs and shared rate limits, not durable domain truth. Private object storage contains only sanitised evidence artifacts.
- The browser calls only the Next.js origin. Do not expose the private API hostname or provider/storage credentials to client bundles.
- Server Components may call the private API directly. Browser-originated calls go through the BFF; do not make Server Components call the application's own Route Handlers.
- FastAPI generates `contracts/openapi.json`; the web client under `apps/web/src/lib/api/generated/` is generated from it and is never edited by hand.
- Keep the BFF thin. It owns cookies, CSRF/origin checks, locale propagation, request IDs, browser-safe errors, and response shaping. It must not duplicate domain or authorisation rules.
- Do not add a microservice, second datastore, browser database client, autonomous agent framework, or direct third-party browser integration without an accepted architecture decision.

## Repository and tooling conventions

- `pnpm` owns JavaScript dependencies and the committed `pnpm-lock.yaml`; do not use npm, Yarn, or Bun in this repository.
- `uv` owns Python dependencies and the committed `uv.lock`; do not maintain a parallel `requirements.txt` unless it is generated for a documented deployment need.
- The root `Makefile` exposes cross-stack judge workflows only. Package-specific scripts remain with their stack.
- Runtime majors are pinned in repository configuration and containers. All dependency changes include lockfile changes and a reason in the pull request.
- Generated files contain a warning header where the format allows it. Change the generator or source schema, not generated output.
- Use UTF-8, LF line endings, a final newline, and the formatting rules in `.editorconfig`.
- Keep modules cohesive. Prefer explicit domain names over generic `utils`, `helpers`, `manager`, or `service` dumping grounds.
- Comments explain safety constraints, invariants, or non-obvious tradeoffs; they do not narrate syntax.
- A TODO must include an owner or issue reference and must not defer a security or privacy requirement required by the current gate.

## General coding standards

- Make invalid states difficult to represent with types, schemas, database constraints, and explicit state machines.
- Validate untrusted input at the outer boundary and enforce domain invariants again in the backend authority.
- Return explicit, stable errors. Never swallow exceptions, return success after partial failure, or leak internals to a public response.
- Inject clocks, randomness, provider adapters, and external I/O in code that requires deterministic tests.
- Store timestamps as UTC-aware values and render public dates in `Africa/Lagos`. Format Nigerian currency as NGN without converting values implicitly.
- Prefer idempotent operations for seeds, jobs, migrations, and retried mutations. Every background job has a stable identity, bounded retries, and a visible exhausted state.
- Keep functions and components small enough to test by behaviour. Avoid clever abstractions before two concrete uses exist.
- Use structured configuration validated at startup. No secret, credential, real contact detail, or environment-specific hostname belongs in source control.
- Do not introduce telemetry, analytics, cookies, or external assets without documenting their data flow, retention, consent impact, and low-bandwidth cost.

## TypeScript, Next.js, and frontend standards

- Enable all practical strict TypeScript checks. Do not use `any`; use `unknown` and narrow it. Type assertions require a local proof or explanatory comment.
- Prefer Server Components. Add `"use client"` only at the smallest interaction boundary and do not pull server-only modules or secrets into client graphs.
- Treat URL search parameters as the source of truth for shareable filters and pagination. Use TanStack Query only for mutations, polling, uploads, and genuinely client-owned server state.
- Use React Hook Form with Zod for interactive form ergonomics. Zod does not replace FastAPI validation or domain enforcement.
- Do not mirror backend models manually. Import generated API types and map them into intentionally smaller view models.
- Every asynchronous surface includes accessible loading, empty, stale, partial, offline, forbidden, and retryable-error states appropriate to the flow.
- Never place tracking codes, reporter handles/passphrases, contacts, private report content, or signed evidence URLs in route paths, query strings, analytics, browser logs, or persistent browser storage.
- Save a private-report draft only after the shared-device warning. Exclude attachments and contact data, expire it after 24 hours, and provide an immediate delete action.
- Use semantic HTML and project-owned accessible primitives. Icon-only controls require an accessible name; forms require programmatic labels and error association.
- Status is expressed in text, not colour alone. Core flows work by keyboard, at 200% zoom, with reduced motion, and without animation.
- Keep public pages functional without client JavaScript where feasible. Respect the implementation plan's first-load JavaScript budget and low-data behaviour.
- Do not cache reviewer pages, report payloads, tracking responses, private discovery, contact data, or attachment URLs in Next.js, a service worker, or a CDN.

## Python, FastAPI, and worker standards

- Use Python 3.14 features supported by the pinned toolchain, complete annotations, Pyright strictness, Ruff formatting/linting, and Pydantic 2 strict models at API boundaries.
- Use package imports and domain modules. Avoid import-time I/O, mutable module globals, and framework objects inside domain logic.
- Use SQLAlchemy 2 async APIs in request paths. Do not perform blocking file, network, parsing, or model work on the event loop; place bounded slow work in the worker.
- Do not use bare `except`, blanket exception suppression, or generic exceptions for expected domain outcomes. Map internal exceptions to stable `application/problem+json` codes at one API boundary.
- Repository methods return domain objects or explicit projections, never unrestricted ORM entities across boundaries.
- Public API responses use allowlisted Pydantic models. Never serialise ORM objects, database rows, or exception dictionaries directly.
- Provider adapters define timeouts, result/byte limits, retry classes, and deterministic fixture implementations. Live provider tests remain explicit opt-in tests.
- Worker jobs carry identifiers rather than private report bodies. They are idempotent by job/run ID, use bounded exponential retry, and expose failed/dead-letter state for review.

## HTTP and contract standards

- Version domain endpoints under `/v1`. Use nouns and explicit commands only where a state transition does not fit ordinary resource semantics.
- Use `application/problem+json` with a stable machine code, safe title/detail, request ID, and field errors where appropriate.
- Cursor-paginate lists and cap page sizes. Never add an unbounded list or provider result.
- Create operations that may be retried accept and enforce `Idempotency-Key` with a bounded retention policy.
- Secrets such as tracking codes and reporter credentials go in POST bodies, never paths or query strings. Relevant responses set `Cache-Control: no-store`.
- Regenerate OpenAPI and the TypeScript client in the same change. CI must fail on an uncommitted contract diff.
- Breaking contract changes require a migration/deprecation plan and an explicit architecture decision; do not silently repurpose fields or status values.

## Database and migration standards

- Change schema only through reviewed Alembic migrations. Never edit an applied migration; add a new one.
- Migrations must work from an empty database and from the last committed schema. Make rollback safe where data preservation permits; document irreversible data transformations.
- Use UUIDv7 primary keys, UTC `timestamptz`, named constraints, explicit foreign-key actions, and indexes justified by real query paths.
- Prefer text plus named `CHECK` constraints over PostgreSQL enum types during the proof of concept.
- Use transactions for state transitions and publication. Lock or compare versions where concurrent decisions could violate an invariant.
- Preserve append-only status and audit histories. Corrections are new events; do not rewrite history.
- Keep contact values, report content, reviewer notes, and private follow-up answers encrypted independently from public records.
- Maintain separate database roles for migrations, public operations, reviewers, and workers. Test the restricted role, grants, views, and row-security behaviour in integration tests.
- Seed commands are additive/idempotent, clearly label fictional data, refuse unsafe production targets, and never reset a database merely to rerun fixtures.

## Security, privacy, and file handling

- Follow deny-by-default authorisation for every private operation. Authentication alone is not authorisation; test horizontal and vertical access separately.
- Reviewer sessions are opaque, rotated on sign-in/privilege change, revocable, and stored client-side only in the configured secure `HttpOnly` cookie. Persist only a keyed hash server-side.
- Check Origin and CSRF tokens for cookie-authenticated mutations. Apply rate limits to sign-in, submission, tracking, handle verification, Q&A, and discovery.
- Tracking and handle lookups use generic response shapes and timing as far as practical; never reveal whether a private record or credential exists.
- Stream uploads with total and per-file caps. Sniff actual type, decode with resource limits, sanitise names, remove metadata, reject active/unsupported formats, scan where configured, and persist only the sanitised artifact.
- Evidence storage is private. Access uses short-lived signed URLs, attachment disposition, and no-store responses. Object keys contain no person, project, or report names.
- The public fetcher allows only public HTTP/HTTPS destinations and approved ports. Validate DNS results and every redirect; block private, loopback, link-local, multicast, reserved, metadata-service, credentialed, and ambiguous IP forms.
- Treat fetched text as untrusted inert data. It cannot add instructions, invoke tools, select private context, or trigger publication.
- Use environment-backed keys and versioned encryption. Never invent a fallback production secret or log decrypted values.
- Structured logs use a central sensitive-field denylist. Do not log bodies, contacts, credentials, tracking codes, attachment data, signed URLs, raw provider prompts, or full IP addresses.
- Report suspected vulnerabilities privately according to `SECURITY.md`; never place exploit details in a public issue.

## AI and source-grounding standards

- Use the OpenAI Responses API through a provider interface with configured model IDs; do not hard-code a model throughout domain code.
- Send the minimum approved source passages, opaque citation IDs, and `store: false` where specified. Never send private reports into the public Q&A index.
- Require strict structured outputs. Deterministically reject unknown citations, cross-project citations, uncited factual statements, malformed output, and more than five follow-up questions.
- Fail closed to the approved insufficient-evidence response when retrieval coverage or output validation is inadequate.
- Preserve prompt/schema/model versions and evaluation metrics without retaining sensitive raw inputs.
- Discovered web material stays `discovered — not yet reviewed`; ranking, repetition, or model confidence is not evidence of truth.
- Maintain deterministic replay fixtures and a versioned evaluation corpus. Live tests supplement fixtures; they never replace reproducible judge tests.

## Localisation, accessibility, and content

- English is the source locale. Keep `en`, `ha`, `ig`, and `yo` message keys, ICU variables, routes, and critical states in parity; CI must reject missing or silently fallback keys.
- Translate navigation, forms, validation, status, privacy/safety, escalation, trust explanations, and reviewer workflows. Label machine-assisted content and record human review status.
- Do not alter names, dates, monetary amounts, institutions, or quoted claims during translation. Keep the original source visibly reachable.
- Meet WCAG 2.2 AA. Test keyboard order, focus visibility/restoration, accessible names/descriptions, errors, contrast, 200% zoom, screen-reader landmarks, reduced motion, and no-colour-only communication.
- Write calm, plain, neutral copy. Distinguish a supported fact, a source's reported claim, a contradiction, an inference, and an unknown.

## Testing and quality gates

- Every behaviour change includes tests at the lowest useful layer and at the trust boundary it could break. A regression fix begins with a failing test where practical.
- Test the public/private boundary with response snapshots or explicit denylist assertions. Test state machines, authorisation, rate limits, redaction, file sanitation, SSRF controls, citation validation, and generic lookup failures adversarially.
- Use deterministic clocks, IDs, randomness, providers, and fixtures. Tests must not depend on live internet access, execution order, a developer's machine, or a production credential.
- Required coverage is at least 80% for frontend and 85% for backend, with 100% branch coverage for tracking-code normalisation, public-response allowlists, the privacy-safe query builder, SSRF guard, citation validator, and report state machine.
- Do not weaken a test, threshold, linter, type check, security rule, or acceptance criterion to make a change pass. Fix the cause or document an explicitly approved exception.
- `make verify` becomes the canonical full gate once implemented. Before it exists, run and report every available relevant check; never claim the planned command ran.
- A passing targeted test does not make a failing full suite green. Report both results accurately.

## Observability and operations

- Propagate one safe request ID across web, BFF, API, worker, and audit events. Use structured JSON logs and bounded label cardinality.
- Emit operational metrics for latency, error class, job age/state, provider failure, rate-limit rejection, and sanitation outcome without report content or identity.
- Liveness proves the process is responsive. Readiness checks required dependencies and migrations. AI/search outages degrade only those features, not project browsing or reporting.
- Production and staging use separate data, buckets, keys, queues, reviewer credentials, and provider budgets. Production never auto-seeds.
- Schema migration is an explicit pre-deploy step. Deployments must be backward compatible across the rolling window or deliberately stop the old version first.

## Git, dependencies, and review

- Use focused branches and Conventional Commit messages (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `build:`, `ci:`).
- Keep commits small, coherent, and reviewable. Do not rewrite or discard another contributor's work, force-push shared branches, or mix unrelated formatting with behaviour changes.
- Do not commit secrets, `.env`, credentials, local databases, raw evidence, private exports, build output, caches, coverage artifacts, or editor state.
- Add production dependencies only when the standard library or existing dependencies cannot meet the need cleanly. Record purpose, maintenance health, licence compatibility, security posture, and bundle/runtime cost.
- Pin GitHub Actions by full commit SHA with a version comment. Use least-privilege workflow permissions and never expose secrets to pull requests from forks.
- Pull requests state the user outcome, security/privacy impact, contract/schema impact, verification commands and results, screenshots for UI changes, and rollback or migration notes.
- Keep `main` releasable. Do not merge with required checks failing or unresolved high/critical exploitable findings.

## Documentation and decision hygiene

- Update the README, relevant docs, `.env.example`, OpenAPI contract, and AI build log in the same change when behaviour or setup changes.
- Record durable architecture changes in `docs/decisions/NNNN-short-title.md` with context, decision, alternatives, consequences, and status.
- Add only verified commands and links. Use absolute dates for deadlines and source-check dates.
- Do not create empty policy documents for appearance. Add each planned document when the corresponding controls and evidence exist.
- Log material AI assistance in `docs/AI_BUILD_LOG.md`, including the suggestion used, human changes/rejections, verification, and commit or pull request. Never claim human review that has not happened.

## Definition of done

A change is complete only when:

- it advances an accepted user journey or engineering gate without expanding unapproved scope;
- relevant format, lint, type, unit, integration, contract, migration, security, accessibility, and build checks pass;
- privacy and public-response boundaries are explicitly tested where applicable;
- all four locales and low-bandwidth/offline behaviour are considered for user-facing changes;
- documentation, configuration examples, generated contracts, migrations, fixtures, and the AI build log are current;
- no secret, private data, unsupported factual claim, or fictional record presented as real is present; and
- the diff has been reviewed for accidental changes, generated-file edits, dead code, and misleading completion claims.

## Code review rules

Flag as blocking:

- any path that can expose private report/contact/evidence/reviewer data to a public response, cache, log, metric, prompt, search query, analytics event, or client bundle;
- domain, authorisation, verification, or publication logic implemented only in the BFF or browser;
- a public fact, update, or AI statement without an approved and deterministically validated citation;
- automatic publication or status changes initiated by AI, search ranking, a worker, or unreviewed community evidence;
- secret credentials in paths/query strings, sequential or reversibly stored tracking codes, or distinguishable private-record lookup errors;
- fetch logic that skips DNS/redirect revalidation, IP-range blocking, size/time limits, or prompt-injection isolation;
- hand-edited generated clients, unreviewed migrations, unrestricted ORM serialisation, or schema changes without contract/tests;
- missing Hausa, Igbo, or Yoruba critical copy, inaccessible interaction, colour-only state, private-data caching, or unjustified public-page bundle growth;
- tests disabled or weakened to accommodate a change, live-provider-only test coverage, or a completion claim unsupported by executed checks.

When raising a review finding, cite the concrete file and failure path, explain user or system impact, and identify the invariant or acceptance criterion at risk.

# AI build log

This log records material AI assistance used to build ShaidaGo. It is evidence of reviewed collaboration, not a claim that generated output was accepted without inspection.

For each entry, record the task, prompt summary, material suggestion, human review outcome, verification, and resulting commit or pull request. Do not include secrets, private report content, personal data, hidden chain-of-thought, or sensitive exploit detail.

## 2026-09-19 — Repository foundation

- **Task:** Orient the edited workspace, reconcile planning documents, establish repository standards, organise documentation, and prepare the project for GitHub.
- **Prompt summary:** Create an enterprise-grade `AGENTS.md`, arrange the documents cleanly, preserve existing edits, and make ShaidaGo a GitHub repository suitable for hackathon grading.
- **AI assistance used:** Proposed the documentation hierarchy, repository governance files, code-review invariants, and consistency corrections for pilot location, languages, and the accepted BFF architecture.
- **Human review:** Pending maintainer review. Update this field with accepted, changed, or rejected decisions before treating the entry as closed.
- **Verification:** Repository hygiene, links, secret patterns, Git state, and remote settings are checked during handoff; application tests are not applicable before scaffolding.
- **Result:** Repository foundation prepared; application implementation remains at Gate 0.

## 2026-09-19 — License selection

- **Task:** Select and add an appropriate open-source license for the public hackathon repository.
- **Prompt summary:** Add a license suitable for a hackathon project.
- **AI assistance used:** Selected the OSI-approved MIT License because its short, permissive terms allow use, modification, distribution, sublicensing, and sale while retaining the copyright, permission notice, and warranty disclaimer.
- **Human review:** The maintainer authorised selection of an appropriate license; the exact license addition remains reviewable in commit history.
- **Verification:** The license text was checked against the Open Source Initiative template, repository references were updated, and GitHub license detection was checked after publication.
- **Result:** ShaidaGo is licensed under MIT, copyright 2026 Aniekan Winner Anietie.

## 2026-09-19 — Detailed backend and frontend build orders

- **Task:** Convert the accepted architecture into implementation-grade backend and frontend sequences that lower-capability coding models can execute without inventing requirements or trust boundaries.
- **Prompt summary:** Create a no-stone-unturned backend build order, then a frontend build order, grouping each task into a closed circle that explains every aspect of completion.
- **AI assistance used:** Produced dependency maps, closed-circle execution rules, 72 backend task packets, 91 frontend task packets, entry/exit gates, adversarial cases, verification evidence, and handoff templates. The frontend order also includes a mandatory human-approved visual-world gate and bounded finish-review workflow.
- **Human review:** Pending maintainer review. The task IDs and ordering are proposals constrained by the accepted implementation plan; record changes or approval before treating the orders as frozen.
- **Verification:** Both documents passed unique task-heading checks, local Markdown-link resolution, and whitespace validation. Cross-links in the README, documentation index, and implementation plan were updated.
- **Result:** Backend and frontend work now have explicit, dependency-ordered execution specifications; implementation remains at Gate 0.

## 2026-09-19 — BE-000 backend scope reconciliation

- **Task:** Map every backend-owned or shared proof-of-concept requirement to an implementation task, evidence type, journey, and explicit non-goal control.
- **Prompt summary:** Implement the first backend circle task, log it, commit it, and only then move to the next task.
- **AI assistance used:** Created stable requirement IDs and traceability tables for the five journeys, 16 must-have capabilities, public records, reporting, tracking, reviewer publication, grounded AI, Source Scout, security, resilience, release, demo readiness, and non-goals.
- **Human review:** The maintainer authorised sequential Circle 0 implementation. Content review of the mapping remains available through this task's commit.
- **Verification:** All local Markdown links resolve; every referenced `BE-*` task is checked against `BACKEND_BUILD_ORDER.md`; all five journeys and all 16 must-have capabilities have backend owners and proof; no accepted capability is assigned to the BFF alone.
- **Result:** `docs/REQUIREMENTS_TRACEABILITY.md` is the active orphan-prevention and change-control register for backend implementation.

## 2026-09-19 — BE-001 execution deferral

- **Task:** Decide whether to build the verified six-project source register during Circle 0 or alongside the evidence-backed seed pipeline.
- **Prompt summary:** Skip BE-001 because the project records and their evidence will be seeded later, then continue the first-circle sequence.
- **AI assistance used:** Recorded a narrow sequencing change that moves BE-001 immediately before BE-043 without weakening its source-audit requirements or representing the task as complete.
- **Human review:** The maintainer explicitly directed the deferral on 2026-09-19.
- **Verification:** The build-order note preserves BE-001 as a prerequisite for BE-043 and states that the Circle 0 exit gate remains open until the source register and validator pass.
- **Result:** BE-001 is deferred, not completed or removed. No project fact, source claim, or report fixture was created by this decision.

## 2026-09-19 — BE-002 controlled vocabularies and state machines

- **Task:** Freeze the backend-owned machine vocabulary and every safety-relevant state transition before database or API implementation.
- **Prompt summary:** Continue the first backend circle after deferring the source register; break the task down, implement it completely, record the work, and commit it independently.
- **AI assistance used:** Defined 15 field-scoped vocabularies and 11 explicit state machines covering projects, sources, verification, report concerns and risk, report review, evidence sanitation, malware scanning, Source Scout, discovered-source decisions, and translation review. Added authorised actors, terminal/quiescent states, mandatory guards, audit events, visibility effects, correction and reopen paths, and stable failure codes.
- **Human review:** The maintainer directed progression to this task. The exact vocabulary remains reviewable in the task commit; no claim is made that Hausa, Igbo, or Yoruba display copy has received fluent human review.
- **Verification:** The dependency-free validator passes the canonical JSON contract and three negative self-tests for invalid casing, unknown transition targets, and transitions out of terminal states. The generated Markdown view passes its drift check; JSON parsing, local Markdown links, whitespace, and repository diff checks are also run before commit.
- **Result:** `contracts/controlled-vocabulary.json` is the canonical derivation source for future database checks, Pydantic/OpenAPI types, translation keys, and fixtures. `docs/CONTROLLED_VOCABULARY.md` supplies the complete human-review table. No application or database implementation is claimed yet.

## 2026-09-19 — BE-003 data classification and trust boundaries

- **Task:** Classify every backend asset, draw trust zones and boundaries, model the six critical data flows, and assign each STRIDE threat to the task that must prove its control.
- **Prompt summary:** Pick up the in-progress BE-003 work, follow the established Circle 0 conventions, then continue through the rest of the circle task by task.
- **AI assistance used:** Completed `docs/THREAT_MODEL.md` with 24 classified assets, 11 actors, 10 trust zones, 9 boundaries, six data-flow diagrams with edge-level allowlists, destination allowlists, a private-data lifecycle table, 29 STRIDE threats, residual risks, and change control. Review found and corrected an unclassified `Mixed` asset (A-24 is now `private`, with retained versions/metrics handled as A-20) and 17 verification owners that cited wrong or non-existent tasks (for example `BE-026`, and `BE-025` for audit). The validator now rejects any `BE-`/`FE-` reference absent from the build orders.
- **Human review:** The maintainer directed continuation of the circle. The threat model's content remains reviewable in this task's commit; no control is claimed as implemented.
- **Verification:** `python3 scripts/validate_threat_model.py --self-test` passes, including negative self-tests for a missing flow, a missing lifecycle row, a duplicate threat ID, an unclassified asset, and an unknown task reference. Local Markdown links and whitespace were checked before commit.
- **Result:** Every outbound flow has an allowlist and every private or secret class has storage, encryption, logging/cache, retention-owner, and deletion rules. TB-02's internal-service authentication mechanism is handed to BE-004.

## 2026-09-19 — BE-004 backend architecture decisions

- **Task:** Record the backend decisions that are difficult to reverse as accepted ADRs, closing the design work of Circle 0.
- **Prompt summary:** After BE-003, finish the rest of the circle task by task, following the established conventions.
- **AI assistance used:** Wrote ADR-0001 to ADR-0008 covering the modular monolith, BFF authority and internal-service authentication, database roles and the no-`RETURNING` submission path, envelope encryption, tracking-code and handle credential storage, the evidence sanitation pipeline and hosted scanner limitation, the generated OpenAPI contract, and provider isolation with replay fixtures. New choices made here: per-caller bearer credentials with two-key rotation for BFF-to-API calls; per-record, per-purpose data keys wrapped by versioned key-encryption keys; Luhn mod 32 as the tracking-code checksum; sanitation inside the API in a bounded process pool because containers share no disk; and sealed idempotency replay, which resolves a conflict between BE-063 (replay the exact result) and the rule that raw tracking codes are never stored. Added a decisions index and a dependency-free validator.
- **Human review:** The maintainer directed completion of the circle. The individual choices above are recorded as accepted so implementation can proceed, and remain open to maintainer review through this task's commit; a changed decision gets a superseding ADR.
- **Verification:** `python3 scripts/validate_decisions.py --self-test` passes with negative self-tests for a missing section, missing date, invalid status, unknown task reference, stale index row, and numbering gap. `validate_threat_model.py --self-test` and `validate_controlled_vocabulary.py --self-test` still pass after the TB-02 update. Local Markdown links and whitespace were checked before commit.
- **Result:** Every Circle 0 design deliverable exists. The Circle 0 exit gate stays open only for deferred BE-001, the source register.

## 2026-09-19 — BE-010 Python project scaffold

- **Task:** BE-010 — Scaffold the Python project.
- **Outcome delivered:** A reproducible `services/platform` Python 3.14 project: dependency groups, Ruff and Pyright-strict configuration, pytest configuration, test layer directories, service README, and committed `uv.lock`.
- **Files changed:** `services/platform/{pyproject.toml,.python-version,uv.lock,README.md}`, `services/platform/src/shaidago/{__init__.py,py.typed}`, `services/platform/tests/{conftest.py,unit/test_package.py}` and `.gitkeep` files for the other test layers; build order note, README and CLAUDE.md status lines.
- **Schema/contract changes:** None.
- **Security/privacy impact:** None at runtime; no code, secrets, tables, or provider calls. `pip-audit` reported no known vulnerabilities in the locked set.
- **Failure behaviour verified:** Not applicable beyond the build: an initial sync failed on a missing README and was fixed at the cause.
- **Commands run and results:** From `services/platform` after deleting `.venv`: `uv sync --all-groups --frozen` succeeded; `uv run ruff check .` passed; `uv run ruff format --check .` passed; `uv run pyright` 0 errors; `uv run pytest` 1 passed; `uv run pip-audit` no known vulnerabilities. No `make` targets exist yet, and the Circle 0 validators were run before commit.
- **Tests added or changed:** `tests/unit/test_package.py` (package import).
- **Generated artifacts checked:** `uv.lock` (`uv lock --check` passes).
- **Known limitations/open decisions:** Dependency versions are unconstrained in `pyproject.toml` and pinned by the lockfile. Licences: `psycopg` and `dramatiq` are LGPL-3.0 and `hypothesis` is MPL-2.0, all used unmodified. CI proof belongs to BE-012.
- **Commit/PR:** `build: scaffold the Python platform service`
- **Next task may rely on:** A frozen, working toolchain to wrap in canonical commands (BE-011).
- **AI assistance used:** Chose dependency purposes, tool configuration, and the smoke test; checked licences and vulnerabilities.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** None yet; unattended run, pending maintainer review.

## 2026-09-19 — BE-011 canonical backend commands

- **Task:** BE-011 — Establish canonical backend commands.
- **Outcome delivered:** A root `Makefile` with one implementation per backend command name, all running through `uv run --frozen` in `services/platform`.
- **Files changed:** `Makefile`, `services/platform/README.md`, `README.md`, `CLAUDE.md`, build order note.
- **Schema/contract changes:** None.
- **Security/privacy impact:** Adds Bandit and pip-audit as `backend-security`; no runtime change.
- **Failure behaviour verified:** A deliberately failing test made `make backend-unit` exit 2, and an unused import made `make backend-lint` exit 2; both temporary files were removed. Empty integration and contract layers are reported explicitly and pass only on pytest exit code 5.
- **Commands run and results:** `make backend-verify` passed (sync, format check, lint, Pyright 0 errors, Bandit, pip-audit no known vulnerabilities, pytest 1 passed). `make backend-integration backend-contract` printed "no tests collected yet". Circle 0 validators passed.
- **Tests added or changed:** None; negative checks were temporary.
- **Generated artifacts checked:** `uv.lock` unchanged.
- **Known limitations/open decisions:** `openapi-generate` and `openapi-check` are absent until Circle 2. The empty-layer allowance must be removed once each layer has tests. `pip-audit` needs network access to the vulnerability service, so it is not fully offline.
- **Commit/PR:** `build: add canonical backend make targets`
- **Next task may rely on:** `make backend-verify` as the single local gate for CI to call (BE-012).
- **AI assistance used:** Designed the Makefile targets and the empty-layer handling.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** None yet; unattended run, pending maintainer review.

## 2026-09-19 — BE-012 backend CI workflow (partial)

- **Task:** BE-012 — Add backend CI without false claims.
- **Outcome delivered:** A least-privilege backend workflow that runs the canonical `make backend-*` targets and reports one aggregate result. It has not run.
- **Files changed:** `.github/workflows/backend.yml`, build order notes (BE-012 and the Circle 1 gate), `CLAUDE.md`.
- **Schema/contract changes:** None.
- **Security/privacy impact:** Read-only token, no secrets, no fork exposure, `persist-credentials: false`, actions pinned by full SHA, cache limited to uv package artifacts. No artifacts uploaded.
- **Failure behaviour verified:** The aggregate job fails on any non-success result, including skipped or cancelled. This was reasoned from the script, not executed.
- **Commands run and results:** SHAs resolved with `gh api` (both tags point directly at commits). YAML parsed with PyYAML. `uv lock --check` clean. actionlint was not installed, so no workflow linting was done. Circle 0 validators passed.
- **Tests added or changed:** None.
- **Generated artifacts checked:** `uv.lock` unchanged.
- **Known limitations/open decisions:** CI green is pending a maintainer push. Path-filtered required checks need a maintainer decision. Integration jobs, coverage and log upload arrive with later tasks.
- **Commit/PR:** `ci: add backend workflow`
- **Next task may rely on:** A workflow to extend; the Circle 1 gate stays open until it is proven on the branch.
- **AI assistance used:** Wrote the workflow and resolved action SHAs.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** None yet; unattended run, pending maintainer review.

## 2026-09-19 — BE-020 Typed environment configuration

- **Task:** BE-020 — Typed environment configuration.
- **Outcome delivered:** `shaidago.shared.config.load_settings(environ)` validates nine sections (app, database, Redis, storage, crypto, authentication, providers, rate limits, observability) into frozen models and fails fast with a `ConfigurationError` that names variables and failure kinds but never values.
- **Files changed:** `services/platform/src/shaidago/shared/{__init__,config}.py`, `services/platform/tests/unit/shared/test_config.py`, `services/platform/pyproject.toml` (Ruff `runtime-evaluated-base-classes` for Pydantic), `.env.example`, build order note.
- **Schema/contract changes:** None. Establishes the environment variable names later tasks read.
- **Security/privacy impact:** Secrets are `SecretStr`; keys must decode to 32 bytes; staging and production refuse debug, docs, DEBUG logs, non-`__Host-` or insecure cookies, public buckets, and placeholder secrets; production also refuses `SCANNER_MODE=not_deployed` and `PROVIDER_MODE=replay`. `.env.example` holds placeholders that decode to `change-me` and are refused outside development and test.
- **Failure behaviour verified:** 51 unit tests (parametrised) cover each production invariant in both staging and production, malformed URLs and keys, missing variables, active-key-version mismatch, live mode without keys, `__Host-` without Secure, and canary secrets absent from error text, `repr`, and `model_dump` output. One test loads `.env.example` in development and asserts production refuses it.
- **Commands run and results:** From `services/platform`: `uv run ruff format`, `ruff check`, `pyright` (0 errors), `pytest` (51 passed). Circle 0 validators passed.
- **Tests added or changed:** `tests/unit/shared/test_config.py`.
- **Generated artifacts checked:** `uv.lock` unchanged.
- **Known limitations/open decisions:** Rate-limit numbers and session cookie defaults are reviewable defaults, not documented requirements. Database role URLs (BE-032), storage/scanner host settings, and session TTLs are added by their owning tasks. `.env` file loading is not implemented; pass variables through the process environment.
- **Commit/PR:** `feat: add typed environment configuration`
- **Next task may rely on:** `load_settings(os.environ)` and the `Settings` sections, with no import-time I/O.
- **AI assistance used:** Designed the sections, invariants, and tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** None yet; unattended run, pending maintainer review.

## 2026-09-19 — BE-021 Application factory and lifespan

- **Task:** BE-021 — Application factory and lifespan.
- **Outcome delivered:** `create_app(settings, dependencies)` builds the FastAPI app with no import-time I/O, a `/v1` router mount point, config-gated docs, and a lifespan that opens `ManagedResource`s in order and closes them in reverse; `create_configured_app` is the `uvicorn --factory` entry point.
- **Files changed:** `services/platform/src/shaidago/api/{__init__,app,dependencies,main}.py`, `api/v1/__init__.py`, `shared/lifecycle.py`; tests `tests/factories.py`, `tests/unit/api/test_app_factory.py`, `tests/unit/shared/test_lifecycle.py` (config test constants moved into `tests/factories.py`); `pyproject.toml` and `uv.lock` (dev dependency `httpx2`, Ruff `TCH` not selected).
- **Schema/contract changes:** None; the `/v1` router has no routes yet.
- **Security/privacy impact:** Docs and `/openapi.json` are unmounted unless `DOCS_ENABLED` (which staging and production refuse). `httpx2` (BSD-3-Clause, pydantic organisation, no known vulnerabilities in `pip-audit`) is a dev-only dependency required by Starlette's `TestClient`.
- **Failure behaviour verified:** Resources close in reverse order when the body fails or a later resource fails to open, and a resource that failed to open is not closed. The schema generates identically twice with docs disabled and without any running dependency.
- **Commands run and results:** From `services/platform`: `ruff format`, `ruff check`, `pyright` (0 errors), `pytest` (60 passed, one third-party deprecation warning from Starlette's test client). Circle 0 validators passed.
- **Tests added or changed:** Factory, docs gating, lifespan order, determinism, and entry-point tests; lifecycle unit tests.
- **Generated artifacts checked:** `uv.lock` regenerated for `httpx2`.
- **Known limitations/open decisions:** The spec asks for injectable clocks and randomness; those belong to BE-034 and will be added to `Dependencies`. No pools or provider clients exist yet (BE-031 onward), so the lifespan is proven with recording fakes. Docs are disabled rather than authenticated in staging and production. Ruff `TCH` is off because FastAPI and Pydantic need runtime annotations.
- **Commit/PR:** `feat: add application factory and lifespan`
- **Next task may rely on:** `create_app`, `Dependencies`, `build_test_app`, and `open_resources` as the registration points for middleware, routers, and resources.
- **AI assistance used:** Designed the factory, lifecycle helper, and tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** None yet; unattended run, pending maintainer review.

## 2026-09-19 — BE-022 Internal caller authentication

- **Task:** BE-022 — Internal caller authentication.
- **Outcome delivered:** A pure-ASGI middleware, installed outermost by `create_app`, requires `Authorization: Bearer <caller-id>.<secret>` on every HTTP request except `/health/live` and answers every failure with one generic 401 problem response. `web` is the only identity (ADR-0002); its current and previous secrets come from configuration.
- **Files changed:** `services/platform/src/shaidago/auth/{__init__,internal}.py`, `shared/problems.py` (the shared problem shape, extended by BE-024), `api/app.py`; tests `tests/unit/auth/test_internal_auth.py` and updated docs tests.
- **Schema/contract changes:** None.
- **Security/privacy impact:** Unknown, malformed, wrong-caller, and removed credentials never reach a router, including for unknown paths, so path existence is not disclosed. Comparison uses `hmac.compare_digest` for both the current and previous secret on every attempt, with a decoy for unknown callers. Logs record the event only, never the caller claim or secret. The middleware refuses WebSocket scopes.
- **Failure behaviour verified:** 13 parametrised bad-header cases return an identical body, `application/problem+json`, `WWW-Authenticate: Bearer`, and `Cache-Control: no-store`, and no route handler runs. The previous credential works only while configured. Only `/health/live` is exempt; `/health/ready`, `/openapi.json`, and unknown paths are denied.
- **Commands run and results:** From `services/platform`: `ruff format`, `ruff check`, `pyright` (0 errors), `pytest` (79 passed). Circle 0 validators passed.
- **Tests added or changed:** Auth tests as above; app-factory docs tests now send the credential.
- **Generated artifacts checked:** None.
- **Known limitations/open decisions:** ADR-0002 exempts only `/health/live`, so interactive docs in development need the bearer header. Forwarded-header handling after authentication is BE-023. The 401 carries no request ID until BE-023. There is no worker identity because the worker does not call the API (ADR-0001). Timing behaviour is asserted by construction (calls counted), not by measurement.
- **Commit/PR:** `feat: authenticate internal API callers`
- **Next task may rely on:** `request.state.caller_id` on authenticated requests, and `Problem`/`problem_response` for error bodies.
- **AI assistance used:** Designed the middleware, decoy comparison, and tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** None yet; unattended run, pending maintainer review.

## 2026-09-19 — BE-023 Request context and structured logging

- **Task:** BE-023 — Request context and structured logging.
- **Outcome delivered:** `RequestContextMiddleware` (inside authentication) validates or mints a UUID request ID, validates the forwarded locale (`en`/`ha`/`ig`/`yo`, default `en`) and client HMAC (64 lower-case hex characters), echoes `X-Request-Id`, and writes one access log line. `configure_logging` sends structlog, stdlib, and uvicorn records through a single recursive redactor and JSON renderer.
- **Files changed:** `services/platform/src/shaidago/shared/{context,logging}.py`, `auth/internal.py` (a denied caller gets a freshly minted request ID), `api/{app,dependencies,main}.py`; tests `tests/unit/shared/{test_logging,test_context}.py` and the updated auth test.
- **Schema/contract changes:** None. Introduces the `X-Request-Id` response header and the `request_id` problem field.
- **Security/privacy impact:** Redaction is by key (exact names and suffixes such as `_token`, `_secret`, `_hmac`) and by pattern (bearer tokens, session cookies, signed URLs, tracking codes, emails, phone numbers, valid IPv4/IPv6), and bytes are never logged. Exception text is redacted after formatting. The access line logs the route template (`unmatched` for unknown paths), never path values, query strings, bodies, or headers. Forwarded headers are honoured only after authentication; forged ones from a denied caller are ignored. Uvicorn's access logger, which records raw paths, is disabled.
- **Failure behaviour verified:** Canary tests prove pattern canaries never reach output under innocent keys, messages, nested values, stdlib `extra`, or exception tracebacks, and key canaries (password, report text, passphrase) never reach output under their keys. Invalid, oversized, upper-case, and path-like request IDs are replaced. Request ID does not leak between requests. Lookalikes (`tokens_used`, `cache_key`, version strings, non-IP dotted numbers, ISO timestamps) are preserved.
- **Commands run and results:** From `services/platform`: `ruff format`, `ruff check`, `pyright` (0 errors), `pytest` (99 passed). Circle 0 validators passed.
- **Tests added or changed:** 25 new tests in `test_logging.py` and `test_context.py`; the auth test now ignores the per-response request ID.
- **Generated artifacts checked:** None.
- **Known limitations/open decisions:** Free text under an innocent key cannot be recognised by pattern; it is protected only by the denylist, so domain code must not log report text at all. The client HMAC format (SHA-256, hex) is chosen here because ADR-0002 does not specify one; the BFF must match it. Propagation into database audit metadata and worker messages waits for the audit table (Circle 3 and 5 onward) and BE-090. Error codes appear in the access line once BE-024 sets `error_code` on the request state. The Circle 2 exit criteria on canary logs and responses are only partly proven until BE-024.
- **Commit/PR:** `feat: add request context and redacted structured logging`
- **Next task may rely on:** `request.state.request_id/locale/client_hmac`, `configure_logging`, `redact`, and `structlog` context binding.
- **AI assistance used:** Designed the redactor, middleware, and canary tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** None yet; unattended run, pending maintainer review.

## 2026-09-19 — BE-024 Problem details and exception boundary

- **Task:** BE-024 — Problem details and exception boundary.
- **Outcome delivered:** One RFC 9457-style `application/problem+json` shape (`type`, `title`, `status`, `code`, `detail`, `request_id`, optional `errors`) built by `problem_response`, a fixed catalogue (400, 401, 403, 404, 405, 409, 413, 415, 422, 429, 500, 503), a `ProblemError` for expected domain outcomes, and `register_exception_handlers` as the single exception boundary.
- **Files changed:** `services/platform/src/shaidago/shared/problems.py`, `api/errors.py`, `api/app.py`, `auth/internal.py`, `shared/context.py` (no duplicate `X-Request-Id`), `shared/logging.py` (credentialed-URL pattern), `pyproject.toml` (test-only Ruff `S105`/`S106` ignores for synthetic canaries); tests `tests/unit/api/test_errors.py` and a DSN canary in `test_logging.py`.
- **Schema/contract changes:** Defines the error contract and its stable codes (the BFF localises from `code`). No routes yet.
- **Security/privacy impact:** Validation errors return the field location and Pydantic rule type only, never the submitted value or message text. Unhandled exceptions return a generic 500; the exception is logged after redaction. Unknown routes and wrong methods share the same shape. Every error is `no-store` and carries the request ID. Writing the test found that a database URL with credentials in exception text was not redacted; a `user:password@` URL pattern now covers it.
- **Failure behaviour verified:** Canary values submitted in a malformed body, a type-mismatched field, and an exception message (containing a DSN password and SQL text) appear in neither the response nor the redacted log; the response has no stack trace, class name, or SQL. Domain problems carry their headers (`Retry-After`) and field errors. `Allow` is kept on 405. The error code reaches the access log.
- **Commands run and results:** From `services/platform`: `ruff format`, `ruff check`, `pyright` (0 errors), `pytest` (all passed). Circle 0 validators passed.
- **Tests added or changed:** `test_errors.py` (9 tests including parametrised fallbacks), DSN canary, and the auth/context tests for a single request-ID header.
- **Generated artifacts checked:** None; OpenAPI generation arrives at the Circle 2 gate.
- **Known limitations/open decisions:** No separate localisation field is emitted (the spec says "if used"); `code` is the handoff. FastAPI's automatic 422 documentation still describes its own schema, and `ProblemDetails` is defined but not yet attached to route `responses`; BE-045 owns contract polish. Free text under an innocent key remains unrecognisable to the redactor, as recorded for BE-023.
- **Commit/PR:** `feat: add problem details and exception boundary`
- **Next task may rely on:** `ProblemError` plus the problem catalogue for every domain error, and `request.state.error_code` in access logs.
- **AI assistance used:** Designed the catalogue, handlers, and tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** None yet; unattended run, pending maintainer review.

## 2026-09-19 — BE-025 Health and readiness

- **Task:** BE-025 — Health and readiness.
- **Outcome delivered:** `GET /health/live` (process only, no credential) and `GET /health/ready` (internal credential required) backed by a `HealthCheck` protocol registered through `Dependencies.health_checks`. Checks run concurrently under `READINESS_CHECK_TIMEOUT_SECONDS`; the verdict is `ready`, `degraded` (only optional checks failed, HTTP 200), or `unavailable` (a required check failed, HTTP 503).
- **Files changed:** `services/platform/src/shaidago/shared/health.py`, `api/health.py`, `api/app.py`, `api/dependencies.py`, `shared/config.py` (`READINESS_CHECK_TIMEOUT_SECONDS`), `.env.example`; tests `tests/unit/api/test_health.py`.
- **Schema/contract changes:** Adds the two unversioned health routes and their response models.
- **Security/privacy impact:** Responses list components as `ok` or `unavailable` only; exception text, DSNs, and hostnames appear in neither the response nor the redacted log (only the component name and exception class). Readiness stays behind ADR-0002 authentication.
- **Failure behaviour verified:** Healthy, degraded optional provider (two providers down), required failure (503), a hung dependency (timeout under 1.2 s while three 0.3 s checks run concurrently), no detail leakage with a canary DSN password, no checks registered, and liveness making zero dependency calls even with a failing check registered.
- **Commands run and results:** From `services/platform`: `ruff format`, `ruff check`, `pyright` (0 errors), `pytest` (117 passed). Circle 0 validators passed.
- **Tests added or changed:** 8 tests in `test_health.py`.
- **Generated artifacts checked:** None.
- **Known limitations/open decisions:** Only the semantics are implemented and proven, with fake probes. No real database, Redis, or object-storage check is registered yet, so the running API reports `ready` with no components; those probes, and the migration-revision check, belong to BE-031, BE-033, and the tasks that add Redis and storage clients, each of which must register its check. The timeout test asserts elapsed time under a bound and could be flaky on a heavily loaded machine.
- **Commit/PR:** `feat: add liveness and readiness endpoints`
- **Next task may rely on:** `Dependencies.health_checks` as the registration point for real probes.
- **AI assistance used:** Designed the readiness semantics and tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** None yet; unattended run, pending maintainer review.

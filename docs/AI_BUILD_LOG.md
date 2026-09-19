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
- **Correction (same day):** BE-024 was committed after Ruff, Pyright, and pytest but before `make backend-verify` was run. The full gate then failed in Bandit (B101) because the exception handlers used `assert` for type narrowing, which is stripped under `python -O`. Fixed in `fix: replace assert narrowing in exception handlers` by using `cast`; `make backend-verify` then passed (exit 0, 117 tests).

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

## 2026-09-19 — Circle 2 gate: deterministic OpenAPI contract

- **Task:** Close the Circle 2 exit criterion "deterministic `contracts/openapi.json` generation is available even with external providers offline", and add the `openapi-generate` and `openapi-check` targets that BE-011 deferred.
- **Outcome delivered:** `python -m shaidago.api.openapi` renders the schema from fixed synthetic settings (sorted keys, LF, final newline) and can check it against the committed file; `contracts/openapi.json` is committed; `make openapi-check` is part of `make backend-verify`. `docs/API.md` documents calling convention, the error catalogue, and health semantics.
- **Files changed:** `services/platform/src/shaidago/api/openapi.py`, `services/platform/tests/contract/test_openapi.py`, `Makefile`, `contracts/openapi.json` (generated), `docs/API.md`, `docs/README.md`, build order notes.
- **Schema/contract changes:** First committed OpenAPI contract: the two health routes and their models.
- **Security/privacy impact:** The generator reads no environment and contacts nothing; a test asserts the rendered schema contains no placeholder secret, DSN, or host. Bandit flagged a placeholder assignment; the placeholder is now a shared constant rather than a suppression.
- **Failure behaviour verified:** Check mode fails for a missing file and for drift and passes after regeneration; generation is identical with the relevant environment variables unset; the committed contract equals the application's output.
- **Commands run and results:** `make backend-verify` exit 0 (121 tests); `make openapi-check` exit 0. A real `uvicorn --factory` process was started with `.env.example` values and queried with `curl` for the gate. The Circle 0 validators passed.
- **Tests added or changed:** 4 contract tests.
- **Generated artifacts checked:** `contracts/openapi.json` regenerated and diffed by `make openapi-check`.
- **Known limitations/open decisions:** Uvicorn's own startup lines are not JSON (it installs its own logging configuration); the container command in BE-111 should pass a log configuration. The empty-integration-layer allowance in the Makefile remains until BE-030.
- **Commit/PR:** `build: generate the deterministic OpenAPI contract`
- **Next task may rely on:** A committed contract and a gate that fails on drift, ready for the TypeScript client generation the frontend adds.
- **AI assistance used:** Wrote the generator, tests, Makefile targets, and API document.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** None yet; unattended run, pending maintainer review.

## 2026-09-19 — BE-030 Compose development infrastructure

- **Task:** BE-030 — Compose development infrastructure.
- **Outcome delivered:** `infra/docker/compose.yml` (project `shaidago`) defining PostgreSQL 18 with pgvector 0.8.6, Redis 8 with append-only persistence and a required password, MinIO with a one-shot provisioner that creates the evidence bucket and sets anonymous access to none, and an optional ClamAV service under the `scanner` profile. Make targets `infra-up`, `infra-up-core`, `infra-down`, `infra-logs`, and `infra-clean`.
- **Files changed:** `infra/docker/compose.yml`, `Makefile`, `.env.example` (bootstrap credentials, ports, memory limit; local URLs now use the compose ports), `services/platform/tests/unit/infra/test_compose.py`, `pyproject.toml`/`uv.lock` (dev dependencies `pyyaml`, `types-pyyaml`), README and docs notes.
- **Schema/contract changes:** None.
- **Security/privacy impact:** All published ports bind to `127.0.0.1` by default on unusual host ports (55432, 56379, 59000, 59001, 53310). Every credential is a required variable with no default, so Compose refuses to start without an env file. Images are pinned by digest. `infra-clean` refuses without `CONFIRM_DESTROY_SHAIDAGO_DATA=yes` and every target uses the fixed project name, so it cannot act on other projects' containers or volumes. Dependency check: `pyyaml` (MIT, dev only). MinIO's community edition is source-only maintenance mode and is used for local development only.
- **Failure behaviour verified:** With a synthetic env file (from `.env.example`): postgres, redis, and minio became healthy; the bucket reported `private`; an anonymous request to the bucket returned 403; Redis rejected a wrong password; `CREATE EXTENSION vector` succeeded; `infra-up-core` was idempotent; `infra-down` kept the three volumes and a row written before it was still present after restart; `infra-clean` without confirmation exited 2 and deleted nothing; with confirmation it removed all ShaidaGo volumes while the other tenant's containers kept running; a missing env file fails fast. Missing credential variables make `docker compose config` fail.
- **Commands run and results:** `docker compose config` for the scanner profile; `make infra-up-core`, `infra-down`, `infra-clean` against a temporary env file outside the repository; `make backend-verify` exit 0 (129 tests); Circle 0 validators passed.
- **Tests added or changed:** 8 static Compose and Makefile guards (digest pins, loopback ports, no literal credentials, health checks, limits, private bucket, guarded clean); they run without Docker.
- **Generated artifacts checked:** `uv.lock` for the new dev dependencies.
- **Known limitations/open decisions:** **The ClamAV service was not started.** The machine's Docker VM had about 2.6 GB free and hosts unrelated containers, and clamd needs roughly 1.5-3 GB, so starting it risked destabilising them; its `clamdcheck.sh` readiness health check is therefore unproven here and `make infra-up` (which includes it) was not run end to end. The Alpine ClamAV image has no arm64 build, so the Debian image is pinned. `infra-up` runs the bucket provisioner after `--wait` because Compose treats an exited one-shot container as failure. The password in `.env.example` is a placeholder with a loopback-only bind; nothing enforces rotation locally.
- **Commit/PR:** `build: add compose development infrastructure`
- **Next task may rely on:** PostgreSQL 18 with pgvector on `localhost:55432`, Redis on `56379`, and MinIO on `59000` with a private bucket, all started by `make infra-up-core` with a copy of `.env.example` as `.env`.
- **AI assistance used:** Wrote the Compose definition, Make targets, and static guards; ran the lifecycle checks.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** None yet; unattended run, pending maintainer review.

## 2026-09-19 — BE-031 Async database kernel

- **Task:** BE-031 — Async database kernel.
- **Outcome delivered:** `shared/database.py` provides `build_engine`/`create_engine` (pooled, `pool_pre_ping`, UTC session, server-side statement timeout, connect timeout, application name) and a `Database` class with `unit_of_work()` (one session and one transaction per use case, commit on success, rollback on error), plus `open`/`close`/`check` so it is both a managed resource and a readiness probe. `create_configured_app` now registers the database for lifespan and readiness.
- **Files changed:** `services/platform/src/shaidago/shared/{database,config}.py`, `api/main.py`, `Makefile` (integration and full-test targets read the infrastructure env file), `.github/workflows/backend.yml` (integration job with a pinned pgvector service container, plus `openapi-check` in the static job), `.env.example` (`DATABASE_STATEMENT_TIMEOUT_MS`); tests `tests/integration/{conftest,test_database_kernel,test_configured_app}.py`, `tests/unit/shared/test_database_translation.py`.
- **Schema/contract changes:** None.
- **Security/privacy impact:** Unique, serialization, and deadlock errors (SQLSTATE 23505, 40001, 40P01) become the generic `conflict` problem with no SQL or driver text; every other database error, including other integrity violations, stays internal and returns the generic 500. Integration fixtures create and drop a disposable database per session.
- **Failure behaviour verified (against PostgreSQL 18 from `make infra-up-core`):** commit on success; rollback on error; session `timezone` UTC, `statement_timeout` 5s, and application name applied; a 3-second `pg_sleep` cancelled by the server at 200 ms (SQLSTATE 57014); a unique violation raised at flush and one deferred until commit are both translated to a conflict; a missing-table error is not translated; the pool recovers after `pg_terminate_backend` killed its connection; `check()` passes on a live server and fails on a dead port; `close()` leaves zero connections in `pg_stat_activity`; through HTTP, readiness reports `database: ok` with the server up and `unavailable` (503) with it down, while liveness stays 200 and the API still starts.
- **Commands run and results:** `make backend-verify` exit 0 (144 passed, including 12 integration tests) with the Compose database running; `make backend-integration` 12 passed. Circle 0 validators passed.
- **Tests added or changed:** 12 integration tests, 3 unit tests for SQLSTATE translation.
- **Generated artifacts checked:** OpenAPI unchanged (`make openapi-check` passes).
- **Known limitations/open decisions:** One engine only; ADR-0003's separate public and reviewer pools arrive with BE-032 once the roles exist. Pools connect lazily, so a database that is down at startup shows as unready rather than preventing boot; the integration test asserts this. `Database.check` proves connectivity only; the migration-revision check belongs to BE-033. The integration CI job is written but has never run (no push); it uses a throwaway CI-only password.
- **Commit/PR:** `feat: add async database kernel`
- **Next task may rely on:** `Database.unit_of_work()` for every repository, the disposable-database integration fixtures, and the registered database readiness check.
- **AI assistance used:** Designed the kernel, the translation policy, and the integration tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** None yet; unattended run, pending maintainer review.

## 2026-09-19 — BE-032 Roles, schemas, grants, and row security

- **Task:** BE-032 — Roles, schemas, grants, and row security.
- **Outcome delivered:** A versioned, idempotent security baseline (`shaidago/db/sql/0001_security_baseline.sql`) creating the five ADR-0003 roles (NOLOGIN, no superuser, no `BYPASSRLS`), the `app` and `public_api` schemas, revoked `PUBLIC` access, USAGE-only schema grants, and default privileges that leave new `app` tables ungranted; `shaidago.db.roles` applies it and enables role logins from deployment-supplied passwords; `shared/private_insert.py` holds the no-read-back mapping options.
- **Files changed:** `services/platform/src/shaidago/db/{__init__,roles}.py`, `db/sql/0001_security_baseline.sql`, `shared/private_insert.py`, `tests/integration/{conftest,test_database_roles}.py`, `pyproject.toml` (test-only `S608` ignore for fixed test SQL).
- **Schema/contract changes:** Roles and two schemas; no tables.
- **Security/privacy impact:** Proven by connecting as each role. `shaidago_public`: may `INSERT` into a private probe table but cannot `SELECT`, `UPDATE`, `DELETE`, or `INSERT ... RETURNING`; reads only the `public_api` view and only its projected columns (selecting the hidden column fails with undefined-column); cannot read `app` tables or `pg_authid`, create objects in `public`, `app`, or `public_api`, `SET ROLE` to the owner, or alter itself. `shaidago_reviewer`: select/insert/update but no delete, no contact table, no DDL. Worker and ops roles: no private table access; ops get no view by default. With `FORCE ROW LEVEL SECURITY`, a `SELECT` grant without a policy returns zero rows. An ORM mapping with `implicit_returning=False`, `eager_defaults=False`, and client-generated ID and timestamp inserts as the restricted role with no `RETURNING` in the emitted SQL; the default mapping fails with SQLSTATE 42501, which shows the options are necessary.
- **Failure behaviour verified:** The baseline runs twice without error; `enable_login` rejects unknown roles and passwords under 16 characters, and a password containing a quote and a percent sign works for a real login.
- **Commands run and results:** `make backend-verify` exit 0 (155 passed, 11 of them new role tests) against the Compose PostgreSQL 18. Circle 0 validators passed.
- **Tests added or changed:** 11 role and mapping integration tests.
- **Generated artifacts checked:** OpenAPI unchanged.
- **Known limitations/open decisions:** The grant model is proven on synthetic **probe tables**, not the real report, contact, or evidence tables, which do not exist yet; each later table migration must add its own grants, policies, and allow/deny test (ADR-0003). The `SECURITY DEFINER` lookup functions and the real `public_api` views come with BE-041, BE-044, BE-062, and BE-065. The baseline is not yet executed by a migration; BE-033 must run it from the baseline revision, and the SQL file becomes immutable once applied. Role login URLs are not in configuration yet; the public and reviewer engines are added with their first consumers (BE-044, BE-054). `shaidago_readonly_ops` has no views to test until aggregate views exist.
- **Commit/PR:** `feat: add database roles, schemas, and grant baseline`
- **Next task may rely on:** Roles and schemas from `apply_security_baseline`, `enable_login`, and `PRIVATE_TABLE_ARGS`/`PRIVATE_MAPPER_ARGS` for private-insert mappings.
- **AI assistance used:** Wrote the baseline SQL, helpers, and the allow/deny matrix; the tests found and fixed a `%` handling defect in script execution.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** None yet; unattended run, pending maintainer review.
- **Correction (same day):** the baseline SQL's schema-scoped default-privilege `REVOKE ... ON FUNCTIONS` was ineffective and let `PUBLIC` execute new functions; it is now global and the pinned SHA-256 changed. Found by the BE-034 idempotency tests; see that entry.

## 2026-09-19 — BE-033 Alembic discipline and baseline

- **Task:** BE-033 — Alembic discipline and baseline.
- **Outcome delivered:** Alembic under `services/platform/migrations` with one shared metadata registry (`shaidago/db/metadata.py`, a naming convention for every constraint and index), a sync `env.py` that never imports the FastAPI app and runs one transaction per revision, and revision `0001_baseline` that installs pgvector, applies the versioned security SQL (refusing it if its SHA-256 changed), and lets application roles read the applied revision. `use_owner_role()` is the helper every later revision starts with. `make migrate` and `make db-roles` (via `shaidago.db.provision`) are the local and deployment commands. `MigrationRevisionCheck` makes readiness depend on the database being exactly at the build's head.
- **Files changed:** `services/platform/{alembic.ini,migrations/*}`, `src/shaidago/db/{metadata,migration_helpers,revision,provision,roles}.py`, `db/sql/0001_security_baseline.sql` (added `USAGE` on `public` for application roles before it was ever applied), `api/main.py`, `Makefile`, `.env.example` (`DB_PASSWORD_*`), tests `tests/integration/{test_migrations,test_provision,test_configured_app}.py`.
- **Schema/contract changes:** Baseline revision only: `vector` extension, roles, `app` and `public_api` schemas, default privileges. The OpenAPI contract is unchanged.
- **Security/privacy impact:** Role passwords come from the environment and are refused as placeholders in staging and production; the provisioning CLI never echoes a password. The baseline SQL is pinned by hash so an applied migration cannot be edited silently. Roles are cluster-wide, so the baseline downgrade keeps them.
- **Failure behaviour verified:** Empty database to head; a second upgrade is a no-op; head to base and back up; model metadata drift check finds nothing; every object in `app` and `public_api` is owned by `shaidago_owner`; each application role can read `alembic_version`; the naming convention names primary, foreign, unique, and index objects; an edited SQL hash is refused. Readiness through HTTP is `ready` only when migrated, and `unavailable` (503) for an unmigrated or unreachable database. Provisioning enables logins, is repeatable and rotates passwords, and rejects missing, short, and deployed placeholder passwords. End to end through the make targets on a scratch database: `make migrate`, `make db-roles`, a repeat `make migrate`, then a real login as `shaidago_public` read the revision.
- **Commands run and results:** `make backend-verify` exit 0 (170 passed). Circle 0 validators passed.
- **Tests added or changed:** 8 migration, 6 provisioning, and 3 configured-app tests (the latter rewritten to include the revision probe).
- **Generated artifacts checked:** OpenAPI unchanged.
- **Known limitations/open decisions:** No model tables exist, so the drift check is vacuous until BE-040; the check and the ownership test are in place for when they appear. pgvector is installed in `public`; BE-080 may move it if retrieval permissions need that, through a new revision. The downgrade leaves roles behind by design. `expected_head()` reads the `migrations/` directory beside the source tree, so container images must copy it (BE-111). Offline SQL generation is refused because revisions run driver-level scripts.
- **Commit/PR:** `feat: add Alembic migrations and the baseline revision`
- **Next task may rely on:** `Base`/`metadata` for mappings, `use_owner_role()` for revisions, and `make migrate` then `make db-roles` for a ready local database.
- **AI assistance used:** Designed the migration environment, baseline revision, provisioning CLI, and tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** None yet; unattended run, pending maintainer review.
- **Correction (same day):** revision 0001 now transfers `alembic_version` to `shaidago_owner` and grants it `USAGE, CREATE` on `public`, because later revisions run as the owner. Found while adding revision 0002; see the BE-034 entry.

## 2026-09-19 — BE-034 Shared identifiers, clock, pagination, and idempotency primitives

- **Task:** BE-034 — Shared identifiers, clock, pagination, and idempotency primitives.
- **Outcome delivered:** `shared/clock.py` (`Clock`, `SystemClock`, `ManualClock`); `shared/ids.py` (monotonic UUIDv7 `Uuid7Generator` with injectable clock and randomness, `SequentialIds` test adapter); `shared/pagination.py` (page-size clamp, HMAC-signed versioned cursors bound to an endpoint-and-filter scope, `keyset_after` for `(sort, id)` ordering, `build_page`); `shared/idempotency.py` with revision `0002_idempotency_records` (key validation, keyed key hash, length-prefixed request fingerprint, HKDF-derived AES-GCM sealing, and a store that claims, replays, and completes through three `SECURITY DEFINER` functions, plus a worker purge).
- **Files changed:** `services/platform/src/shaidago/shared/{clock,ids,pagination,idempotency,problems,config}.py`, `db/{idempotency_table,registry}.py`, `migrations/versions/0002_idempotency_records.py`, `migrations/env.py`, `api/openapi.py`, `.env.example` (`CURSOR_HMAC_KEY`), tests `tests/unit/shared/{test_clock_and_ids,test_pagination,test_idempotency}.py`, `tests/integration/test_idempotency.py`, updated migration tests. Corrections to earlier tasks are listed below.
- **Schema/contract changes:** Table `app.idempotency_records` (named constraints, index, forced row security) and functions `app.idempotency_claim`, `app.idempotency_complete`, `app.idempotency_purge`. New stable problem codes `invalid_cursor`, `idempotency_key_required`, `idempotency_key_invalid`, `idempotency_conflict`, `already_received`. OpenAPI unchanged.
- **Security/privacy impact:** The database holds only `HMAC-SHA-256(pepper, key)`, the fingerprint, and a sealed result; a test reads every stored column as the owner and finds neither the key nor the plaintext code. The public role has no privilege on the table and can only execute claim and complete; it is denied `SELECT`, `INSERT`, `UPDATE`, `DELETE`, and the worker-only purge. Cursors are signed, versioned, and scoped, and every malformed, tampered, foreign-key, wrong-scope, or wrong-version cursor gets one generic problem.
- **Failure behaviour verified:** UUIDv7 stays strictly increasing across 10,000 IDs in one millisecond and when the clock steps back; cursors survive any Hypothesis-generated position and never crash on arbitrary text; sealing round-trips any payload and rejects a wrong key, context, or any single flipped byte; different fingerprint parts never collide. Against PostgreSQL: a first call claims and a retry replays the sealed result; a different request under the same key conflicts; the replay window (15 minutes) and retention (24 hours) end as specified; a failed use case leaves no claim; two concurrent duplicates serialise, the second waits for the first transaction and then replays its result; a purge by the worker role scrubs and deletes; completing an unclaimed key raises SQLSTATE P0002.
- **Corrections to earlier work found by these tests (unreleased, never applied outside local scratch databases):** (1) The BE-032 baseline used a schema-scoped `ALTER DEFAULT PRIVILEGES ... REVOKE EXECUTE ON FUNCTIONS`, which cannot remove the global default `EXECUTE` for `PUBLIC`, so the public role could call the worker-only purge function. The baseline SQL now revokes globally, its pinned SHA-256 was updated, and revision 0002 also revokes explicitly. (2) Revisions run `SET LOCAL ROLE shaidago_owner`, which lacked access to `alembic_version`; revision 0001 now transfers that table to the owner and grants it the needed schema privileges. Both edits changed the committed baseline before it was released.
- **Commands run and results:** `make backend-verify` exit 0 (227 passed, including the new property and integration tests); `make openapi-check` exit 0. Circle 0 validators passed.
- **Tests added or changed:** 39 unit and property tests, 8 idempotency integration tests, two new migration tests (step down one and back to base), and the drift check now compares a real table.
- **Generated artifacts checked:** `contracts/openapi.json` unchanged; `uv.lock` unchanged.
- **Known limitations/open decisions:** The store is proven with an in-test use case; BE-063 must wire the header, fingerprint (including how multipart bodies are hashed), and response into the submission endpoint. A claim committed without completion would be reported as a conflict until it expires; the store assumes claim and complete share a transaction, which the tests exercise. The retention (24 hours) and replay window (15 minutes) are constants taken from ADR-0005 and the plan and are not configurable. The purge is a function; scheduling it is BE-090's job. Cursor sort values are text or integers and callers convert them to column types.
- **Commit/PR:** `feat: add shared clock, id, pagination, and idempotency primitives`
- **Next task may rely on:** `Clock`, `Uuid7Generator`, signed cursors with `keyset_after`, and `IdempotencyStore` for every create and list endpoint, with no local alternatives.
- **AI assistance used:** Designed the primitives, the SQL functions, and the property and concurrency tests; the tests exposed the two corrections above.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** None yet; unattended run, pending maintainer review.

## 2026-09-19 — BE-040 Locality, project, and translation model

- **Task:** BE-040 — Locality, project, and translation model.
- **Outcome delivered:** Revision `0003_projects_translations` creating `app.localities`, `app.projects`, and `app.project_translations` with named constraints derived from the controlled vocabulary, a deferred constraint trigger enforcing that a public project has English source text, and `public_api` views (`localities`, `projects`, `project_translations`) that expose only public columns of visible, translated projects. `shaidago.projects` provides frozen projections (`LocalitySummary`, `PublicProject`, `ServedText`) and `PublicProjectRepository`; `shared/vocabulary.py` reads `contracts/controlled-vocabulary.json`.
- **Files changed:** `services/platform/migrations/versions/0003_projects_translations.py`, `src/shaidago/db/{project_tables,registry}.py`, `src/shaidago/projects/{models,repository}.py`, `src/shaidago/shared/vocabulary.py`, tests `tests/unit/projects/test_vocabulary_parity.py`, `tests/integration/{test_projects,conftest}.py`.
- **Schema/contract changes:** Three tables, one trigger function with two constraint triggers, three views, and `SELECT` on the tables for `shaidago_reviewer`. OpenAPI unchanged (no endpoints yet). No rows are inserted by the migration.
- **Security/privacy impact:** The public role has no privilege on the tables and reads only the views; a hidden project, an `unavailable` translation, and the visibility column are unreachable through them. An unknown and a hidden slug both return `None`, so the caller cannot tell them apart. No seed or factual data was added; every test row is labelled `synthetic-*`.
- **Failure behaviour verified (PostgreSQL 18, 19 new integration tests):** unique and kebab-case slugs; every vocabulary column rejects a value outside the contract and accepts every contract value; `last_checked_on` cannot post-date the row's own `updated_at` in Lagos time; locality locales must be supported and include `en`; translation uniqueness, locale, status, `reviewed` requires a date, and non-empty text; locality delete is restricted and project delete cascades; a public project without English text (none, Hausa only, or `en` unavailable) fails at commit, including on update to public and on deleting the English row, while a hidden project needs none; the repository serves the requested locale and reports a Yoruba request served from English with `is_fallback` true.
- **Commands run and results:** `make backend-verify` exit 0 (246 passed); `make openapi-check` exit 0. Circle 0 validators passed.
- **Tests added or changed:** 19 integration and 3 unit tests; the migration step-down test now derives the parent revision instead of assuming one.
- **Generated artifacts checked:** OpenAPI unchanged; `uv.lock` unchanged.
- **Known limitations/open decisions:** "Non-future last-checked date" is enforced against the row's own write time because a CHECK cannot use `now()` safely; the service layer must still pass the injected clock's time as `updated_at`, and there is no scheduled-data exception because none is needed yet. "No public project without an approved locale representation" is interpreted as an English (source locale) translation that is not `unavailable`; the maintainer may prefer a stricter definition. `promised_deliverable` is required text. Reviewer identity is not recorded on translations yet (no reviewers table until BE-050). Locality names are not translated. Writes are made by the migration owner (the seed path); narrower reviewer write grants come with the publication tasks. No locality or project rows exist, so BE-043 remains blocked on BE-001.
- **Commit/PR:** `feat: add locality, project, and translation model`
- **Next task may rely on:** Public projections through the `public_api` views and `PublicProjectRepository`, with `Locale`/`ProjectCategory`/`PublicStatus` Literals checked against the vocabulary.
- **AI assistance used:** Designed the schema, trigger, views, repository, and tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** None yet; unattended run, pending maintainer review.

## 2026-09-19 — BE-041 Sources, immutable versions, and citations

- **Task:** BE-041 — Sources, immutable versions, and citations.
- **Outcome delivered:** Revision `0004_sources_facts_citations` creating `sources`, `source_versions`, `project_facts`, `project_updates`, `fact_citations`, and `update_citations`, with database-enforced rules and public `public_api` views; and `shaidago.sources.publication.PublicationService`, which checks every publication requirement and names gaps by stable code.
- **Files changed:** `services/platform/migrations/versions/0004_sources_facts_citations.py`, `src/shaidago/db/{source_tables,registry}.py`, `src/shaidago/sources/publication.py`, `src/shaidago/shared/problems.py` (`publication_incomplete`, 422), tests `tests/integration/{test_sources,support}.py`, `tests/unit/sources/{test_vocabulary_parity,test_publication_rules}.py`, `pyproject.toml` (migration `S608` and test `E501` ignores).
- **Schema/contract changes:** Six tables, five trigger functions, and views `project_facts`, `project_updates`, `fact_citations`, `update_citations`, and `cited_sources`. `SELECT` on the tables for `shaidago_reviewer`. OpenAPI unchanged.
- **Security/privacy impact:** Source rows can only carry public information classes, so `community_report_unverified` and `ai_generated_explanation` cannot become sources. The public role has no privilege on any table and sees only published items, citations to approved or superseded versions, and metadata of cited sources; the views omit version text, review state, and internal IDs of versions. Nothing publishes automatically: publication is one explicit service call.
- **Failure behaviour verified (PostgreSQL 18, 45 new tests):** a version's hash must equal the SHA-256 of its text; identical content is one version and changed content is a new one; content edits and deletes raise `55000`; 13 review-state transitions (7 legal, 6 illegal) follow the controlled state machine; a citation must quote its version exactly at its stated offset and be 1-1000 characters with a location label; a raw `UPDATE ... visibility = 'public'` with no citation, or with only a pending or rejected version, fails at commit for both facts and updates; a public item's last approved citation cannot be deleted and its sole supporting version cannot be reopened (a second approved version or a superseded state frees this); a public item needs a visible date and a verification state other than "awaiting verification"; the service reports every gap at once (`approved_citation_required`, `visible_date_required`, `verification_required`, `official_source_required`, `independent_sources_required`, `reviewed_community_evidence_required`) and leaves the draft untouched; two sources from one publisher do not corroborate; a complete item publishes with the injected time; an unknown ID is the generic not-found.
- **Bug found by these tests and fixed before commit:** the claim trigger compared `TG_TABLE_NAME` with `facts`/`updates` instead of `project_facts`/`project_updates`, so citation deletes crashed and the rule never ran on the claim table; the revision (unreleased) was corrected.
- **Commands run and results:** `make backend-verify` exit 0 (284 passed); `make openapi-check` exit 0. Circle 0 validators passed.
- **Tests added or changed:** 31 integration tests (parametrised to 45 cases), 7 unit tests.
- **Generated artifacts checked:** OpenAPI unchanged.
- **Known limitations/open decisions:** The database checks that a hash matches a version's text using `convert_to`, which PostgreSQL marks stable rather than immutable (it is accepted in a `CHECK` and is deterministic for UTF-8 databases). Source versions store extracted text in the row (up to 500,000 characters); where the bytes of a retrieved file live is a BE-064/BE-080 decision. "Materially independent" is approximated as distinct sources with distinct publishers; a reviewer must still judge independence. Reviewer identity, audit events, and the reviewer-role write path (approve, reject, supersede) arrive with BE-050 to BE-074, so tests write as the migration owner and `PublicationService` currently runs as that role. The `source_review_state` machine's actors and audit events are not enforced yet, only its legal transitions. `updated_at` must be supplied by the injected clock for the "not future" check to mean anything. No data was seeded.
- **Commit/PR:** `feat: add sources, immutable versions, and citations`
- **Next task may rely on:** Citation-complete public views, `PublicationService.publish`, and database backstops that make an uncited or unapproved public item impossible to commit.
- **AI assistance used:** Designed the tables, triggers, views, service, and adversarial tests; the tests found the trigger name bug.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** None yet; unattended run, pending maintainer review.

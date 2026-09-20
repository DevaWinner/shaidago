# AI build log

This log records material AI assistance used to build ShaidaGo. It is evidence of reviewed collaboration, not a claim that generated output was accepted without inspection.

For each entry, record the task, prompt summary, material suggestion, human review outcome, verification, and resulting commit or pull request. Do not include secrets, private report content, personal data, hidden chain-of-thought, or sensitive exploit detail.

## 2026-09-19 — Repository foundation

- **Task:** Orient the edited workspace, reconcile planning documents, establish repository standards, organise documentation, and prepare the project for GitHub.
- **Prompt summary:** Create an enterprise-grade `AGENTS.md`, arrange the documents cleanly, preserve existing edits, and make ShaidaGo a GitHub repository suitable for hackathon grading.
- **AI assistance used:** Proposed the documentation hierarchy, repository governance files, code-review invariants, and consistency corrections for pilot location, languages, and the accepted BFF architecture.
- **Human review:** Reviewed and accepted by the maintainer (Aniekan Winner Anietie) on 2026-09-19.
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
- **Human review:** Reviewed and accepted by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the task IDs and ordering are approved.
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
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

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
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

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
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

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
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

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
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

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
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

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
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

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
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.
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
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

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
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

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
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

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
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

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
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.
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
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.
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
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

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
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

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
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-042 Escalation routes and trust vocabulary

- **Task:** BE-042 — Escalation routes and trust vocabulary.
- **Outcome delivered:** Revision `0005_escalation_routes` (table, deferred trigger, `public_api.escalation_routes` view), `EscalationRepository` (routes valid on a supplied date, most specific concern category first, requested locale preferred with an honestly flagged English fallback), and `shaidago.projects.trust` (`TrustMetadata` with information class, verification state, dates, translation status, and a separate AI flag).
- **Files changed:** `services/platform/migrations/versions/0005_escalation_routes.py`, `src/shaidago/db/{escalation_tables,registry}.py`, `src/shaidago/projects/{escalation,trust}.py`, tests `tests/integration/test_escalation.py`, `tests/unit/projects/test_trust.py`.
- **Schema/contract changes:** `app.escalation_routes` with a scope unique key (locality, category, locale, organisation; nulls not distinct), one trigger function, one view. `SELECT` for `shaidago_reviewer`. OpenAPI unchanged.
- **Security/privacy impact:** No route is seeded and there is no phone, address, or email column, so a contact detail can appear only inside reviewed, cited instruction text. An active route must cite an approved or superseded source version (checked at commit) and carry a verification date not later than its write time and its own non-emergency disclaimer. The public role reads only the view, which omits internal IDs, the active flag, and timestamps. A locality with no verified route yields an empty list, never a default.
- **Failure behaviour verified (PostgreSQL 18, 14 new tests):** active routes citing pending or rejected versions fail while approved and superseded pass and an inactive draft may cite a pending one; invalid category and locale, empty or over-long text, an inverted validity window, and a future verification date are rejected; uniqueness holds even with no category; lookups exclude expired, future, inactive, and other-category routes and order specific before general; Hausa is served where it exists and English is labelled as fallback where it does not; the trust helper refuses private or AI classes for a cited item and always flags AI text.
- **Commands run and results:** `make backend-verify` exit 0 (295 passed). The drift check found a constraint name that PostgreSQL truncates and the metadata did not; it was fixed with an explicit short name. Circle 0 validators passed.
- **Tests added or changed:** 11 integration and 3 unit tests.
- **Generated artifacts checked:** OpenAPI unchanged.
- **Known limitations/open decisions:** "Category" is read as the report concern category (`report_concern_category`), with an empty value meaning "any concern"; the maintainer may prefer project category. The non-emergency disclaimer is per-route reviewed text, so the platform ships no default wording and no translation of it. Exposing these values over HTTP is BE-044. Sources cited only by an escalation route are not in `cited_sources`, so BE-044 must decide how their metadata is served. No route data exists, and none may be seeded before the maintainer supplies verified guidance.
- **Commit/PR:** `feat: add escalation routes and trust metadata`
- **Next task may rely on:** `EscalationRepository.routes_for`, `TrustMetadata`, and the view for the public API.
- **AI assistance used:** Designed the table, trigger, repository, and tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-044 Public list and detail services

- **Task:** BE-044 — Public list and detail services.
- **Outcome delivered:** `GET /v1/localities`, `GET /v1/projects` (cursor pagination and allowlisted filters for locality, category, public status, verification state, and full-text `q`), `GET /v1/projects/{slug}`, and `GET /v1/projects/{slug}/sources/{source_id}`, backed by `PublicCatalogue` queries over the `public_api` views. The API now connects as `shaidago_public` (new `DATABASE_URL_PUBLIC`), never as the migration owner.
- **Files changed:** `services/platform/src/shaidago/api/v1/{__init__,projects}.py`, `src/shaidago/projects/catalogue.py`, `api/{dependencies,main,openapi}.py`, `shared/{config,database}.py`, `db/provision.py`, `.env.example`, `contracts/openapi.json` (regenerated), `docs/API.md`, tests `tests/integration/test_public_api.py` and updated config, factory, and configured-app tests.
- **Schema/contract changes:** OpenAPI adds four `GET` operations and their allowlisted response models (`ProjectPageOut`, `ProjectDetailOut`, `SourceExcerptsOut`, `LocalityListOut`, and their parts). No database change.
- **Security/privacy impact:** Every response model is an explicit allowlist; a denylist test scans every JSON response for internal keys (`content_text`, `content_sha256`, `review_state`, `visibility`, `source_version_id`, ids of localities and projects, timestamps of creation) and for role, schema, and driver names. Hidden, missing, unpublished, and wrongly attributed projects and sources return one identical `not_found`. A fact or update without a visible citation is dropped before serialisation. Cursors are bound to endpoint, filters, and locale. The query text is bound as a parameter and tested with SQL, Unicode, wildcard, and bidirectional-control input. Production and staging must give the public role a different login from the owner.
- **Failure behaviour verified (PostgreSQL 18 through `TestClient`, 33 tests):** credentials required; deterministic newest-first order across pages of size 1, 2, and 3 with no repeats or gaps and hidden projects absent; every filter and their combinations; tampered, foreign-filter, and foreign-locale cursors give `400 invalid_cursor`; ten invalid or unknown parameters give `422` without echoing input; page size capped at 50; detail shows only published, cited items and never a draft; Hausa served where it exists and Yoruba flagged as English fallback in both detail and list; `ETag` stable for equal bodies, different across projects, and a matching `If-None-Match` returns an empty `304`; source excerpts contain only this project's cited passages (not the rest of the document) and an uncited, foreign, unknown, or hidden-project source is indistinguishable from a missing one.
- **Commands run and results:** `make backend-verify` exit 0 (329 passed); `make openapi-generate` regenerated the contract and `make openapi-check` is part of the gate. Circle 0 validators passed.
- **Tests added or changed:** 33 endpoint tests; the config tests for the new setting and its deployed-only "different login" rule; the configured-app and provisioning tests adapted.
- **Generated artifacts checked:** `contracts/openapi.json` regenerated and committed in the same change.
- **Known limitations/open decisions:** Text search is PostgreSQL full-text with the `simple` configuration over title and summary; language-aware stemming for Hausa, Igbo, and Yoruba was not evaluated, and the index and query plans are BE-045. Escalation routes and trust metadata are not exposed over HTTP yet; the source endpoint does not serve sources cited only by an escalation route. The list is not tied to a project's facts beyond the verification filter. Serving `Cache-Control: public` assumes the BFF and any CDN respect `Vary`; no CDN exists yet. The API needs `make db-roles` to have run so the public login works.
- **Commit/PR:** `feat: add public project, locality, and source endpoints`
- **Next task may rely on:** A committed OpenAPI contract for the public read journey, allowlisted DTOs, and `PublicCatalogue` for query work.
- **AI assistance used:** Designed the queries, DTOs, caching, and end-to-end tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-045 Public contract and query quality

- **Task:** BE-045 — Public contract and query quality.
- **Outcome delivered:** Two measured indexes (revision `0006_public_query_indexes`), committed `EXPLAIN` evidence and its reproducible script, synthetic OpenAPI examples, an error contract that documents the media type actually sent, a Schemathesis property test of the public API against its own contract, and response-shape snapshots plus a denylist for every public payload.
- **Files changed:** `services/platform/migrations/versions/0006_public_query_indexes.py`, `scripts/query_plan_evidence.py`, `docs/evidence/BE-045-query-plans.md`, `src/shaidago/{api/app,api/v1/projects,projects/catalogue,shared/problems}.py`, `db/{metadata,project_tables}.py`, `migrations/env.py`, `contracts/openapi.json`, tests `tests/integration/{test_schemathesis,test_public_shapes,public_catalogue,conftest,test_migrations,test_public_api}.py` and `snapshots/public_response_shapes.json`.
- **Schema/contract changes:** Indexes `ix_projects_public_recent` (partial, `updated_at DESC, id DESC`) and `ix_project_translations_search` (GIN over `to_tsvector('simple', title || ' ' || summary)`). The full-text filter now matches the requested locale's text or English. The contract documents `400` and `401` on the public endpoints, declares every error response as `application/problem+json`, and carries synthetic examples for the page and detail models.
- **Security/privacy impact:** Snapshot and denylist tests fail if a new field or private key name appears in any public response; examples are marked synthetic and describe no real project.
- **Evidence (20,000 synthetic projects, PostgreSQL 18, local Compose):** newest-first list 10.5 ms to 0.07 ms, category and locality filters about 3-4 ms to 0.07 ms, keyset next page 0.8 ms to 0.02 ms, full-text search 70 ms to 3.6 ms; each index was also dropped in turn to show it earns its place (search alone 18 ms without the recent-order index; recent-order alone leaves search at 57 ms).
- **Failure behaviour verified:** Schemathesis (40 generated cases per operation across all six operations) found two real contract gaps, an undocumented `400` and a `application/problem+json` body documented as `application/json`, both fixed in the API and schema; it passes now with only positive-data acceptance excluded, because an opaque signed cursor rightly rejects arbitrary well-formed strings and that behaviour is asserted directly in `test_public_api.py`. Malformed cursors, unknown filters, oversized values, Unicode, and hostile search text were already covered by the endpoint tests.
- **Commands run and results:** `make backend-verify` exit 0 (333 passed); `make openapi-check` exit 0; the plan script run four ways (both indexes, without the search index, without the recent-order index, baseline). Circle 0 validators passed.
- **Tests added or changed:** 1 Schemathesis property test (6 operations), 2 shape tests, 1 index-definition test, moved shared catalogue fixtures.
- **Generated artifacts checked:** `contracts/openapi.json` regenerated (indexes do not change it; errors and examples do) and committed.
- **Known limitations/open decisions:** Alembic cannot compare partial or expression indexes, so autogenerate skips these two by name and a `pg_indexes` test checks their definitions instead. Timings come from a synthetic, warm-cache, single-connection run and are evidence of plan shape, not a load test; the pilot holds about six projects. The `simple` full-text configuration was not evaluated for Hausa, Igbo, or Yoruba. The verification filter and detail queries were not plan-measured. Excluding `positive_data_acceptance` is broad for the whole test, not only the cursor parameter.
- **Commit/PR:** `feat: add public query indexes, contract tests, and response snapshots`
- **Next task may rely on:** A contract-tested, indexed, snapshot-guarded public read API and a plan-evidence script to re-run when queries change.
- **AI assistance used:** Designed the indexes and measurement, wrote the contract, snapshot, and property tests, and fixed the gaps the property test found.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-043 Idempotent evidence-backed seed pipeline (blocked)

- **Task:** BE-043 — Idempotent evidence-backed seed pipeline.
- **Outcome delivered:** None. The task is blocked and no code was written for it.
- **Files changed:** Build order status note and this entry only.
- **Schema/contract changes:** None.
- **Security/privacy impact:** None. No project, source, citation, escalation route, translation, or fictional-report fixture was created outside the synthetic rows inside tests, and none of those is presented as real.
- **Failure behaviour verified:** Not applicable.
- **Commands run and results:** None for this task.
- **Tests added or changed:** None.
- **Generated artifacts checked:** None.
- **Known limitations/open decisions:** BE-043 depends on BE-001, the verified six-project source register, which the maintainer deferred to just before this task; the loop's instructions forbid researching or inventing projects. The tables it would seed now exist (BE-040 to BE-042) and their constraints refuse uncited or unapproved public records, so the pipeline's target is ready. A partial build (versioned JSON schemas, validate-before-transaction, natural-key upserts, production and non-local refusal, counts and evidence-gap reporting, and a run-twice idempotency proof) could be written and tested against synthetic fixtures, but it would exercise a data contract that the real register has not yet shaped, so it was not started.
- **Unblock:** The maintainer supplies the verified source register (BE-001) with real public sources and exact passages, confirms the reviewed fields for four locales or honest machine-assisted status, and confirms the escalation guidance. BE-043 then builds against that register, and the Circle 4 and Circle 0 gates can close.
- **Commit/PR:** `docs: record BE-043 as blocked on the source register`
- **Next task may rely on:** Nothing from this task. Circle 5 does not depend on it.
- **AI assistance used:** Assessed the dependency and recorded the blocker.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-050 Reviewer user and bootstrap path

- **Task:** BE-050 — Reviewer user and bootstrap path.
- **Outcome delivered:** Revision `0007_reviewers_audit` (reviewers and an append-only audit log), Argon2id hashing with central parameters and a rehash-on-success path, identifier normalisation, `ReviewerService.create`, an `AuditWriter`, and an idempotent bootstrap command (`make reviewer-bootstrap`).
- **Files changed:** `services/platform/migrations/versions/0007_reviewers_audit.py`, `src/shaidago/db/{reviewer_tables,registry}.py`, `src/shaidago/auth/{passwords,reviewers,bootstrap}.py`, `src/shaidago/audit/{__init__,events}.py`, `Makefile`, `.env.example`, tests `tests/unit/auth/test_passwords_and_identifiers.py`, `tests/integration/test_reviewers.py`.
- **Schema/contract changes:** `app.reviewers` (identifier unique and format-checked, role in reviewer/admin, state in active/disabled, hash must be `$argon2id$`, credential version) and `app.audit_events` (actor, event, subject, outcome, request ID, JSON details) with triggers that refuse UPDATE, DELETE, and TRUNCATE for everyone including the owner. Grants: the reviewer role may read reviewers and update only the credential, state, and sign-in columns; reviewer and worker roles may insert audit events. OpenAPI unchanged.
- **Security/privacy impact:** Only an Argon2id hash is stored (OWASP-minimum parameters: 19 MiB, t=2, p=1), never the password; an unknown identifier still costs one verification against a decoy hash. Deployed environments refuse placeholder or demo passwords; every environment refuses passwords under 12 or over 256 characters. Audit details pass through the central redactor before storage, and the creation event holds only the role. The bootstrap command reads credentials from the environment, never overwrites an existing user, and its error messages name variables, not values. Identifiers are pseudonymous handles, not required to be email addresses.
- **Failure behaviour verified (PostgreSQL 18, 58 new tests):** hashes are salted and free of the password; stale-parameter hashes are replaced only after a successful verification; weak, oversized, and deployed-placeholder passwords and malformed identifiers create nothing; duplicate identifiers conflict regardless of case; the database rejects bad roles, states, identifiers, and non-Argon2id hashes; the audit log refuses update, delete, and truncate even as owner and stores neither the password nor the identifier nor an IP-like value from a canary; the public, worker, and read-only roles are denied on reviewers, and the reviewer role cannot change a role, rename, delete, or insert; bootstrap creates once, leaves an existing password untouched, and refuses seven kinds of unusable input.
- **Commands run and results:** `make backend-verify` exit 0; Circle 0 validators passed.
- **Tests added or changed:** 12 unit and 21 integration cases (58 with parametrisation and properties).
- **Generated artifacts checked:** OpenAPI unchanged.
- **Known limitations/open decisions:** Step 5, "disablement revokes active sessions transactionally", waits for the session store and is delivered by BE-051. The state vocabulary is `active` and `disabled` (a disabled account is one an administrator has locked); no automatic lockout exists, so an attacker cannot lock a reviewer out. The Argon2 parameters are code constants, not settings. The rehash path is implemented and unit-tested but only exercised by sign-in in BE-054. No password-change or admin-reset endpoint exists yet.
- **Commit/PR:** `feat: add reviewer users, audit log, and bootstrap command`
- **Next task may rely on:** `PasswordVerifier`, `find_reviewer`, `ReviewerService`, `AuditWriter`, and the reviewer table with `credential_version` for session binding.
- **AI assistance used:** Designed the schema, hashing policy, bootstrap, and adversarial tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-051 Opaque sessions and cookie contract

- **Task:** BE-051 — Opaque sessions and cookie contract.
- **Outcome delivered:** Revision `0008_reviewer_sessions`; `SessionService` (issue, resolve, revoke one, revoke all) with a 256-bit server-generated token stored only as an HMAC, a session-bound CSRF token derived from it, idle and absolute expiry on the injected clock, and validity tied to the reviewer's state, credential version, and role; `CookiePolicy` with the production and development `Set-Cookie` contracts; and `ReviewerService.disable`, `change_password`, and `set_role`, which revoke sessions in the same transaction (this closes BE-050 step 5).
- **Files changed:** `services/platform/migrations/versions/0008_reviewer_sessions.py`, `src/shaidago/auth/{sessions,cookies,reviewers}.py`, `db/reviewer_tables.py`, `shared/config.py` (`SESSION_IDLE_MINUTES`, `SESSION_ABSOLUTE_HOURS`), `api/v1/projects.py` (query fix below), `.env.example`, `contracts/openapi.json`, tests `tests/unit/auth/test_cookies_and_tokens.py`, `tests/integration/test_sessions.py`, `test_public_api.py`.
- **Schema/contract changes:** `app.reviewer_sessions` (token HMAC unique and 32 bytes, role, credential version, three timestamps, revocation with a fixed reason set). The reviewer role may select and insert sessions and update only last use and revocation. The `q` filter now rejects control characters (contract diff).
- **Security/privacy impact:** The raw token exists only in the issue response object (its `repr` omits it) and the cookie the BFF sets; a test reads every stored column and every audit detail for 20 sessions and finds neither token nor CSRF value. Only the trusted BFF sets the cookie, from `CookiePolicy`: production and staging `__Host-sg_session=...; Path=/; Max-Age=...; Secure; HttpOnly; SameSite=Lax` with no Domain; development `sg_session` without Secure. A role change made without any revocation still invalidates the session on the next request, so a downgrade cannot linger.
- **Failure behaviour verified (PostgreSQL 18):** unknown, malformed, oversized, non-ASCII, and injection-shaped tokens resolve to nothing; idle expiry, sliding activity, and the eight-hour absolute limit despite steady activity; last-use writes at most once a minute; logout revokes only that session and replay fails; disabling a reviewer revokes all its sessions atomically and a rolled-back disable keeps them; a password change ends all sessions and bumps the credential version; the public and worker roles are denied on sessions and the reviewer role cannot rebind a session, extend its expiry, overwrite the hash, or delete it.
- **Bugs found by these tests and fixed before commit:** (1) `hmac.compare_digest` on strings raised `TypeError` for non-ASCII input, which would have been a 500 on a hostile CSRF header; found by a Hypothesis property test, now compared as bytes. (2) Schemathesis, on a later random seed, found that a `q` containing a NUL byte reached PostgreSQL and returned a 500; `q` now rejects control characters and both cases are regression-tested.
- **Commands run and results:** `make backend-verify` exit 0 (395 passed); `make openapi-check` exit 0; the Schemathesis test was run repeatedly after the fix. Circle 0 validators passed.
- **Tests added or changed:** 12 unit and 10 integration tests, plus two `q` regression cases.
- **Generated artifacts checked:** `contracts/openapi.json` regenerated (only the `q` pattern changed).
- **Known limitations/open decisions:** The HTTP surface (session issue and logout endpoints, the BFF header contract for the token and CSRF value) is BE-052 and BE-054, so the cookie contract is proven as a policy object, not yet through a running BFF; the BFF's final `Set-Cookie` behaviour test belongs to the frontend build order. The CSRF token has no separate rotation beyond session rotation. Role changes need the owner connection (the reviewer role cannot update roles), so they are an administrative command, not an API operation. Idle and absolute limits are settings with sensible defaults (30 minutes and 8 hours) that the maintainer may want to review. Schemathesis draws fresh random cases each run, so an occasional new finding is expected and intended.
- **Commit/PR:** `feat: add opaque reviewer sessions and the cookie contract`
- **Next task may rely on:** `SessionService.resolve` returning a `Principal` (reviewer, current role, session), `csrf_matches`, and `CookiePolicy`.
- **AI assistance used:** Designed the session model and its failure tests; the property and fuzz tests found the two bugs above.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-052 CSRF, origin, and internal boundary

- **Task:** BE-052 — CSRF, origin, and internal boundary.
- **Outcome delivered:** `authenticated_reviewer`, a FastAPI dependency that resolves the reviewer session from `X-Shaidago-Session` and requires the session-bound CSRF token in `X-Shaidago-Csrf` on every state-changing method; a `csrf_invalid` problem; a separate least-privilege `shaidago_reviewer` database engine (`DATABASE_URL_REVIEWER`); and injectable `reviewer_database` and `ids` dependencies.
- **Files changed:** `services/platform/src/shaidago/api/{reviewer_auth,dependencies,main,openapi}.py`, `shared/{config,problems}.py`, `.env.example`, tests `tests/integration/test_reviewer_boundary.py` and updated factories and configured-app tests.
- **Schema/contract changes:** None to the database. No route uses the dependency yet (BE-054 does); the contract is unchanged.
- **Security/privacy impact:** The API reads the session only from the BFF header, never from cookies or the query string. The internal service credential is not reviewer authority: a valid credential without a session is `401 unauthenticated`, and a valid session without the credential never reaches the route. The CSRF token is HMAC-derived from the session token, so it is bound to one session and cannot be replayed from another. Session is checked before CSRF, so an anonymous caller cannot learn whether a CSRF token was right. Deployed environments must give the reviewer role a login distinct from the owner and the public role.
- **Failure behaviour verified (9 integration tests, PostgreSQL 18):** reads succeed with a session and no CSRF and writes need it; a missing session, blank session, unknown token, revoked session, disabled reviewer, expired session, and non-ASCII header bytes all give the same 401 body; missing, blank, another session's, altered, non-ASCII, and session-token-as-CSRF values all give the same `403 csrf_invalid` body; a session in a cookie or query string is ignored; neither the session token nor the CSRF token appears in captured logs; a missing reviewer database is `503 dependency_unavailable`.
- **Commands run and results:** `make backend-verify` exit 0; `make openapi-check` exit 0. Circle 0 validators passed.
- **Tests added or changed:** 9 integration tests plus config test updates for the new setting.
- **Generated artifacts checked:** OpenAPI unchanged.
- **Known limitations/open decisions:** Browser `Origin` checks and the same-origin cookie itself belong to the Next.js BFF (frontend build order); the API receives no origin signal and does not pretend to. The CSRF header name and the session header name are chosen here and the BFF must match them. The reviewer engine is not part of readiness yet. The tests use probe routes; real reviewer routes arrive in Circle 7.
- **Commit/PR:** `feat: add reviewer session and CSRF boundary`
- **Next task may rely on:** `authenticated_reviewer` for every reviewer route, and `Principal.role` for policy checks.
- **AI assistance used:** Designed the dependency and its adversarial tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-053 Role policy and authorisation tests

- **Task:** BE-053 — Role policy and authorisation tests.
- **Outcome delivered:** `shaidago.auth.policy` with ten capabilities (queue read, report detail read, evidence download, note write, status transition, discovery run, discovered-source decision, public-update publication, reopening a superseded source, and reviewer administration), a deny-by-default `is_allowed`/`authorize` that depends on a role and a capability only, and a `require(capability)` FastAPI dependency.
- **Files changed:** `services/platform/src/shaidago/auth/policy.py`, `api/reviewer_auth.py`, tests `tests/unit/auth/test_policy.py` and additions to `tests/integration/test_reviewer_boundary.py`.
- **Schema/contract changes:** None.
- **Security/privacy impact:** Roles other than `reviewer` and `admin` (empty, `reporter`, `system`, `worker`, upper-case variants) hold no capability. Only administrators may reopen a superseded source (taken from the controlled vocabulary) or administer reviewers. A denial is the same `403 forbidden` body for every capability and names no record, because the policy is never given a record.
- **Failure behaviour verified (95 tests across policy and boundary):** an allow/deny case for every capability and role, including 70 unknown-role cases; a denial is one identical problem for every capability; through the API each capability is allowed for an admin and allowed or denied for a reviewer as the policy says, and all reviewer denials share one body; `401 unauthenticated` and `403 forbidden` stay distinct; an admin downgraded in the database loses admin routes on the very next request (the session is invalidated), so no stale privilege survives.
- **Commands run and results:** `make backend-verify` exit 0; Circle 0 validators passed.
- **Tests added or changed:** 12 unit test functions (parametrised to many cases) and 3 integration tests.
- **Generated artifacts checked:** OpenAPI unchanged.
- **Known limitations/open decisions:** The spec's "horizontal access to a report outside an assignment or tenant rule" is untestable because the pilot has no assignment or tenant model; authorisation is by role only, and the policy module records that any future scope must be an explicit argument with its own tests. Capability names for the report and evidence operations are defined before those endpoints exist (Circle 6 and 7), so their routes must adopt `require(...)` and add their own route-level tests. Session-fixation and replay-after-logout are covered by the session tests (server-only token generation and revocation).
- **Commit/PR:** `feat: add reviewer capability policy`
- **Next task may rely on:** `require(Capability.X)` on every reviewer route.
- **AI assistance used:** Designed the policy and its exhaustive matrix tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-054 Authentication endpoints and abuse controls

- **Task:** BE-054 — Authentication endpoints and abuse controls.
- **Outcome delivered:** `POST /v1/auth/sessions` and `DELETE /v1/auth/sessions/current`, a shared `RateLimiter` interface with a Redis fixed-window implementation (fail-closed) and a deterministic in-memory adapter, an `invalid_credentials` problem, and audit events for sign-in success, failure, denial, and sign-out.
- **Files changed:** `services/platform/src/shaidago/api/v1/{auth,__init__}.py`, `shared/{ratelimit,problems}.py`, `api/{dependencies,main}.py`, `docs/API.md`, `contracts/openapi.json`, tests `tests/unit/shared/test_ratelimit.py`, `tests/integration/{test_auth_endpoints,test_schemathesis}.py`.
- **Schema/contract changes:** Two new operations and their allowlisted models (`SignInRequest`, `SessionOut`, `CookieOut`, `ReviewerOut`) in the committed OpenAPI.
- **Security/privacy impact:** All credential failures share one 401 body and an unknown identifier still costs a password verification against a decoy hash. Attempts are limited per client (default 10 per 15 minutes, `RATE_SIGN_IN_PER_15M`) and per client-and-identifier (5 per 15 minutes), keyed by the BFF's pseudonymous client HMAC and a truncated SHA-256 of the identifier, so no account can be locked from another address and nothing raw is stored in Redis. The audit log records outcome and request ID only, never the attempted identifier or password. A weaker stored hash is upgraded only after a successful sign-in. The session and CSRF tokens appear once in a `no-store` response and never in logs, audit rows, or storage.
- **Failure behaviour verified:** Six kinds of failing credentials return the same status and body; the sixth attempt for one client and identifier is `429` with `Retry-After` while the same identifier from another client still signs in and the window reopens after 16 minutes; a client is limited across identifiers after ten attempts; oversized (413), over-length, empty, missing, extra-field, and mistyped bodies are refused without echoing input; the password, guessed password, both tokens, and the identifier are absent from captured logs; sign-out needs CSRF, revokes the session, and a replay is `401`; each sign-in issues a different session; a missing limiter is `503` (fail closed); the Redis limiter counts per window, expires keys, and raises when Redis is unreachable.
- **Commands run and results:** `make backend-verify` exit 0 (505 passed); `make openapi-check` exit 0; the Schemathesis test was repeated 15 times with zero failures after the fixes below. Circle 0 validators passed.
- **Tests added or changed:** 13 auth endpoint tests, 2 limiter unit tests, and the fuzz test now includes both new operations against a real reviewer database and limiter.
- **Found by the fuzz test and fixed:** the endpoints' `400` (unparseable body) and `413` responses were undocumented in the contract; both are now documented, and a 413 is exempted from the generic negative-data check for that reason only.
- **Known limitations/open decisions:** Limits count attempts, not only failures, so five legitimate sign-ins by one reviewer from one address in 15 minutes would also be limited; this favours simplicity and the reviewer can retry after the window. The limiter is fixed-window, so a client can burst up to twice the limit across a window boundary. If the BFF does not forward a client HMAC, all such requests share one "unknown" bucket, which is safe but coarse. The body-size cap uses `Content-Length`; the BFF must also cap streamed bodies. There is no password-reset or self-service password change. Audit failure events are not attributed to any reviewer (the identifier is deliberately not stored).
- **Commit/PR:** `feat: add reviewer sign-in, sign-out, and abuse controls`
- **Next task may rely on:** A working reviewer authentication flow the BFF can drive, the shared limiter for other abuse controls (BE-100), and `AuditWriter` events.
- **AI assistance used:** Designed the endpoints, limiter, and adversarial tests; the fuzz test found the two contract gaps.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-060 Versioned encryption envelope

- **Task:** BE-060 — Versioned encryption envelope.
- **Outcome delivered:** `shaidago/shared/crypto.py` (AES-256-GCM `FieldCipher` with a version byte, random 96-bit nonce, and authenticated `table:row_id:field:schema_version` context; `EnvironmentKekWrapper` behind a `KekWrapper` interface; typed `DecryptionError` and `KeyUnavailableError`), `shared/data_keys.py` (`DataKeyService`: create, load, crypto-shred, and resumable rotation with audit), revision `0009_data_keys`, the rotation command (`make kek-rotate`), and `docs/KEY_MANAGEMENT.md` with the KMS migration path.
- **Files changed:** `services/platform/src/shaidago/shared/{crypto,data_keys,rotate_keks}.py`, `db/{crypto_tables,registry}.py`, `migrations/versions/0009_data_keys.py`, `Makefile`, `docs/KEY_MANAGEMENT.md`, `docs/README.md`, tests `tests/unit/shared/test_crypto.py`, `tests/integration/test_data_keys.py`.
- **Schema/contract changes:** `app.data_keys` (unique per owner table, owner, and purpose; a row is either live with a wrapped key and KEK version, or destroyed with neither), forced row security, an insert-only policy and grant for the public role, and reviewer read and rewrap rights. OpenAPI unchanged.
- **Security/privacy impact:** The database stores only wrapped DEKs; a test proves the plaintext key is absent from the row. A ciphertext moved to another table, row, field, or schema version, or read with another key, fails authentication with an error that carries no detail. The four purposes have independent keys, so one class can be destroyed without touching another. Rotation audits counts only and logs no key material (canary check on the output and the audit row).
- **Failure behaviour verified (26 new tests):** the AES-256-GCM primitive matches the published McGrew-Viega known-answer vector; the envelope layout equals an independent computation with an injected nonce; 50 encryptions give 50 distinct nonces and ciphertexts; any plaintext round-trips (Hypothesis); five wrong contexts, a wrong key, flipping each of the envelope's bytes, five truncations, appended bytes, and an unknown version all raise the same `DecryptionError`; the wrapper reads retired KEKs, rejects wrong contexts, and refuses unknown versions; the insert-only role creates a key but is denied `SELECT`; a duplicate key for one owner and purpose, a half-destroyed row, and a malformed row are refused by the database; destroying one purpose leaves the others readable and repeats safely; rotation of 25 keys runs in batches of 10, is idempotent, keeps ciphertext byte-identical, and every field decrypts afterwards with only the new KEK configured; an aborted batch rolls back completely and a rerun finishes it; keys wrapped by a removed KEK are counted, not guessed.
- **Commands run and results:** `make backend-verify` exit 0 (531 passed); `make openapi-check` exit 0. Circle 0 validators passed.
- **Tests added or changed:** 14 unit and 12 integration test functions.
- **Generated artifacts checked:** OpenAPI unchanged.
- **Known limitations/open decisions:** Only the wrap/unwrap boundary is prepared for a KMS; no KMS adapter exists and production must stay closed to real data until one does (ADR-0004). The fields themselves (report description, contact, notes, answers) are encrypted by BE-061 onward, so nothing yet stores a private value; this task proves the mechanism. KEK generation and escrow are outside the repository. `make kek-rotate` runs as the migration owner and is not scheduled anywhere. The NIST-style vector proves the primitive, not this envelope's format, which is checked by an independent recomputation instead.
- **Commit/PR:** `feat: add versioned envelope encryption and data keys`
- **Next task may rely on:** `DataKeyService` and `FieldCipher` for every private column, with the context helper `field_context`.
- **AI assistance used:** Designed the envelope, key service, rotation, and adversarial tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-062 Tracking code design and lookup primitive (pure core)

- **Task:** BE-062 — Tracking code design and lookup primitive.
- **Outcome delivered:** `shaidago/reports/tracking.py`: generation of `SG-XXXXX-XXXXX-XXXXX-XXXXX-C` from 100 random bits of Crockford Base32 with a Luhn mod 32 check symbol; strict normalisation; bounded collision retry; the keyed lookup hash `HMAC-SHA-256(pepper, "sg-track-v1:" + code)`; and pepper-ordered lookup candidates for rotation. The database side is not built.
- **Files changed:** `services/platform/src/shaidago/reports/{__init__,tracking}.py`, `tests/unit/reports/test_tracking.py`.
- **Schema/contract changes:** None.
- **Security/privacy impact:** A `TrackingCode` renders as `TrackingCode(<redacted>)` in `repr`, `str`, and f-strings, so a code cannot leak through logging by accident; its formatted value is exposed only through an explicit property meant for the one-time create response. Normalisation accepts only case, spaces, hyphens, and the Crockford look-alikes (O to 0; I and L to 1) and rejects `U` and every other symbol, and its error never repeats the input. Validation (format and checksum) happens with no database access. The stored value is a keyed hash, not an unkeyed digest, with a domain-separation prefix and an explicit checksum version constant.
- **Failure behaviour verified (30 tests, deterministic and Hypothesis):** the alphabet has 32 symbols and no I, L, O, or U; the byte source is called exactly once for 13 bytes and only the top 100 bits matter; 200 formatted codes all match the documented shape; any 13 bytes round-trip through format and normalise; 5,000 random codes are distinct; case, space, hyphen, and padding variants normalise identically; the `SG` prefix is recognised by length only; look-alikes map and eight kinds of foreign symbol (including a non-Latin digit and NUL) are rejected; wrong lengths and empty input are rejected; **every single-symbol substitution in every position is detected** (exhaustive for one code and by property for arbitrary codes); adjacent transpositions are missed in under 5% of cases (measured, and the ADR's "most" claim is now a tested bound); arbitrary text is either a valid code or a generic rejection; collisions retry a bounded number of times then raise; lookup keys are keyed, deterministic, 32 bytes, and differ across peppers and codes; retired peppers are tried after the active one.
- **Commands run and results:** `make backend-verify` exit 0 (561 passed). Circle 0 validators passed.
- **Tests added or changed:** 30 unit and property tests.
- **Generated artifacts checked:** OpenAPI unchanged.
- **Known limitations/open decisions:** **Steps 4 and 5 are only half done.** The `app.report_tracking_keys` table and the indexed lookup function need the private report tables (BE-061), and the "raw code shown exactly once" response is BE-063; this task proves the code, the hash, and the pepper ordering, not their storage. BE-061 was not started, so the build order's sequence was not followed for this pure task (it has no dependency on the tables). Peppers are read from `TRACKING_PEPPERS` and `TRACKING_ACTIVE_PEPPER_VERSION` (BE-020). 100 random bits are not brute-forceable, but rate limits on lookups are BE-065 and BE-100.
- **Commit/PR:** `feat: add tracking code generation, validation, and lookup hashing`
- **Next task may rely on:** `generate`, `normalise`, `lookup_key`, and `lookup_candidates` for the report tables and endpoints.
- **AI assistance used:** Designed the code format handling and the exhaustive typo and normalisation tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-001 verified source register

- **Task:** BE-001 — Build the verified source register (the last open Circle 0 task).
- **Outcome delivered:** `data/source-register.json`, the generated `docs/SOURCE_REGISTER.md`, and `scripts/validate_source_register.py` with 17 negative self-tests, plus `scripts/render_source_register.py --check` and five unit tests in the platform suite.
- **Files changed:** `data/source-register.json`, `docs/SOURCE_REGISTER.md`, `scripts/{validate,render}_source_register.py`, `services/platform/tests/unit/test_source_register.py`, `docs/BACKEND_BUILD_ORDER.md` (BE-001 status and the Circle 0 gate), `docs/README.md`, `CLAUDE.md`.
- **Schema/contract changes:** None to the database or OpenAPI; the register is the input the seed pipeline (BE-043) will read.
- **Security/privacy impact:** No private data. Fictional report fixtures are labelled and flagged for a maintainer decision because they mention real places. Blocked sources were not bypassed.
- **Failure behaviour verified:** Each of the six sources was requested once on 2026-09-19. Punch, The Nation, and Abuja Times were read in full; their quoted passages were checked word for word against the visible page text, and the hash of the bytes received was recorded. FCT UBEB and The Hospital Book returned HTTP 403 firewall or challenge pages and were not bypassed; the FCT UBEB homepage was read once through a summarising fetch tool, which showed only a headline. The validator rejects a fact without a source, a missing or future last-checked date, an unlabeled fictional report, a tampered or missing passage, judgemental wording, an unknown availability value, a hash on an unretrieved source, an unverified fact made eligible, corroboration by one publisher, an unverified route that cites a source, contact details in a route, a reviewed translation with no reviewer, a missing locale, an uncovered category, and fewer than six projects.
- **Corrections to the submitted draft:** the placeholder hashes were removed (real hashes for three pages, none for three); the FCT UBEB quotation was truncated with an ellipsis and unseen, so it is recorded as claimed and not verified; the Lokogoma passage was not found on the homepage; the 7.2 km length is in the Punch article, not The Nation's; "contract cost" became the quoted cost to the government; "emergency satellite town interventions", "8-bed", and "to improve access to clean water" are not in any passage seen and were dropped; the English summary was relabelled `machine_assisted` because no reviewer is recorded; the four escalation organisations had no source, date, or instructions and are marked unverified; "[cite: n]" markers were removed.
- **Commands run and results:** `python3 scripts/validate_source_register.py --self-test` and `python3 scripts/render_source_register.py --check` pass; the platform unit tests pass; the other Circle 0 validators pass.
- **Tests added or changed:** 5 unit tests.
- **Generated artifacts checked:** `docs/SOURCE_REGISTER.md` matches the data.
- **Known limitations/open decisions:** Three of six projects have no verified fact. The maintainer can supply readable pages or accept the blocked ones. Newspaper facts are single-source unless two publishers report the same fact, so most are `awaiting_verification` and stay drafts until a reviewer decides. Whether Punch and The Nation are materially independent needs reviewer judgement. The raw page hashes change if a site changes its markup; the passage hashes are the stable evidence. Reuse terms were not checked. The three Hausa, Igbo, and Yoruba texts are the submitted text with one clause removed, not reviewed by a fluent speaker.
- **Commit/PR:** `docs: add the verified source register and its validator`
- **Next task may rely on:** A validated register whose only seed-eligible facts have exact passages.
- **AI assistance used:** Fetched and verified the sources, corrected the draft, and wrote the validator, renderer, and tests.
- **Prompt summary:** The maintainer supplied a draft register and asked for it to be improved without invention and used to close Circle 0.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-043 evidence-backed seed pipeline

- **Task:** BE-043 — Idempotent evidence-backed seed pipeline (unblocked by BE-001).
- **Outcome delivered:** `shaidago.seed` (`plan.py`, `apply.py`, `__main__.py`) and `make seed-demo`. It reads `data/source-register.json`, validates it with the register validator before any connection, builds a database-independent plan, and applies it in one transaction.
- **Files changed:** `services/platform/src/shaidago/seed/*`, `Makefile`, `README.md`, `CLAUDE.md`, build order notes, tests `tests/unit/seed/test_plan.py` and `tests/integration/test_seed.py`.
- **Schema/contract changes:** None.
- **Security/privacy impact:** Refuses staging, production, a missing `APP_ENV`, and any non-local host, without echoing credentials. Seeds no private data, no escalation route, and no fictional report. Source versions store only the cited excerpts, not full articles.
- **Failure behaviour verified:** An invalid register aborts before anything is written; production, staging, empty, and remote targets are refused; a second run through the real command reports every row unchanged and leaves a full-table snapshot identical; reviewer-owned status, visibility, and reviewed translation text survive a rerun; changed evidence adds one version and leaves the old one byte-identical without duplicating a source; every citation still quotes its stored excerpt exactly; through the public API the seeded projects are visible with no facts, a Hausa translation is served as such, and a Yoruba request is labelled as English fallback.
- **Commands run and results:** `make backend-verify` exit 0 (590 passed). `make seed-demo` was run twice on a scratch database (first run added 3 localities, 3 projects, 6 translations, 3 sources, 3 versions, 7 facts, 11 citations; second run changed nothing) and once with `APP_ENV=production` (refused). Circle 0 validators passed.
- **Tests added or changed:** 12 unit and 8 integration tests.
- **Generated artifacts checked:** OpenAPI unchanged.
- **Known limitations/open decisions:** Only 3 of 6 projects are seeded (the other three have no verified fact). Seeded facts are drafts and approved evidence needs a reviewer, so the public API shows no facts yet. Public status stays `unknown`; the register proposes `completed` for two projects pending review. For AMAC-01 and BWARI-02 the English summary is the first verified statement (`machine_assisted`, no reviewer) and `promised_deliverable` is empty because the register supplies none. Stale citations to an older pending version remain when evidence changes. Fictional report fixtures need the report tables (BE-061 onward).
- **Commit/PR:** `feat: add the evidence-backed demo seed pipeline`
- **Next task may rely on:** A loadable demo dataset and the register as the single source of seed facts.
- **AI assistance used:** Designed and wrote the pipeline and tests.
- **Prompt summary:** The maintainer asked to complete the pending circles using the register.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-061 Private report persistence

- **Task:** BE-061 — Private report persistence.
- **Outcome delivered:** Revision `0010_private_reports` with `reports`, `report_contacts`, `report_status_events`, `report_tracking_keys`, and `evidence_files`, and `shaidago/reports/persistence.py` (`ReportWriter`, `read_description`).
- **Files changed:** `services/platform/migrations/versions/0010_private_reports.py`, `src/shaidago/db/{report_tables,registry}.py`, `src/shaidago/reports/persistence.py`, `tests/integration/test_private_reports.py`.
- **Schema/contract changes:** Five private tables with forced row security; the public role has INSERT only; reviewers read reports, events, and evidence metadata and may update only the status projection columns and insert events; nobody but the owner can read contacts yet. OpenAPI unchanged.
- **Security/privacy impact:** The description and the contact channel and value are AES-GCM ciphertext under separate data keys, and the contact is a separate table that can be crypto-shredded without touching the report (proven). The writer issues only plain `INSERT`s with application IDs and times and never reads back. No column holds plaintext, an IP, a device, a handle, or a raw tracking code. Status history is append-only, only legal transitions from the controlled vocabulary can be recorded, and a report's status must equal its newest event at commit, so a status cannot change without a history entry.
- **Failure behaviour verified (PostgreSQL 18, 37 test cases):** the public role is denied `SELECT`, `UPDATE`, and `DELETE` on all five tables; the captured SQL has no `SELECT` and no `RETURNING`; report, event, contact, tracking key, and both data keys are stored together, and a duplicate tracking key rolls all of them back; canary description, contact, channel, and code strings appear in no stored value; the description decrypts for the reviewer role and after the contact key is destroyed; reviewers cannot read contacts, rename a category, replace the ciphertext, move a report, or delete it; an event without a status update, and a status update without an event, both fail at commit; events cannot be updated or deleted even by the owner; seven transitions (four illegal) behave as the state machine says; the database checks equal the controlled vocabulary (values and all 15 transition pairs); evidence rows accept only sanitised files with a clean or demo scan state, a random object key, an allowed MIME type, and a bounded size; empty, oversized, and malformed content is refused before any write without echoing it.
- **Commands run and results:** `make backend-verify` exit 0; `make openapi-check` exit 0.
- **Tests added or changed:** 37 integration cases.
- **Generated artifacts checked:** OpenAPI unchanged.
- **Known limitations/open decisions:** No endpoint uses the writer yet (BE-063). The tracking-key lookup function and the reporter handle column arrive with BE-065 and BE-066. Reviewer access to contacts is deferred to an audited function (BE-070). Evidence rows cannot represent a file that failed sanitation or scanning, because ADR-0006 persists only sanitised, scanned artifacts. The description key is created before the report because of the foreign key, so a crash between the two statements is prevented only by the single transaction. Reports are not yet linked to the reporter handle.
- **Commit/PR:** `feat: add private report persistence`
- **Next task may rely on:** `ReportWriter.insert` as the one atomic write path for a report and its keys.
- **AI assistance used:** Designed the schema, triggers, writer, and adversarial tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-064 Streaming evidence sanitation pipeline

- **Task:** BE-064 — Streaming evidence sanitation pipeline.
- **Outcome delivered:** `shaidago/files/` with `rules` (limits, type sniffing, polyglot check, file-name sanitising), `sanitise` (Pillow and pikepdf), `scanner` (clamd INSTREAM client, demo, and EICAR test scanners), `storage` (S3 adapter for MinIO/R2 and an in-memory double), and `pipeline` (`EvidencePipeline`, startup sweep).
- **Files changed:** `services/platform/src/shaidago/files/*`, `src/shaidago/shared/config.py` (`CLAMD_HOST`, `CLAMD_PORT`), `.env.example`, `tests/unit/files/test_evidence_pipeline.py`, `tests/integration/test_evidence_storage.py`, `pyproject.toml`, `uv.lock`.
- **Schema/contract changes:** None. OpenAPI unchanged.
- **Dependencies added (build order 1.3):** `pikepdf` (MPL-2.0; strips and rewrites PDFs per ADR-0006), `boto3` (Apache-2.0; S3 API for MinIO locally and R2 hosted; no live R2 call was made), `python-multipart` (Apache-2.0; multipart parsing for BE-063), dev-only `boto3-stubs[s3]` (types). `pip-audit` reported no known vulnerabilities; lockfile updated.
- **Security/privacy impact:** The raw upload exists only in a private temp file that is deleted on success, rejection, timeout, and a failing stream. The size cap is enforced while streaming. The type comes from magic bytes; a declared type that disagrees is refused. Images are decoded under a pixel limit and re-encoded fresh, so EXIF, GPS, and XMP cannot survive. PDFs lose metadata, embedded files, scripts, actions, forms, and annotations, and the output is re-checked. Raw bytes and the stored artifact are both scanned; any scanner error or timeout rejects the file. `not_deployed` scanning is refused in production. Object keys are 128 random bits, uploaded with attachment disposition. Rejections carry only a stable reason code.
- **Failure behaviour verified:** GPS EXIF canary removed; MIME spoof; EICAR; oversized stream (reading stops near the cap); decompression bomb; encrypted, over-long, malformed, and malicious PDFs; SVG, HTML, and executable uploads; script and PDF polyglots; truncated JPEG and PNG; scanner failure, refusal, timeout, and every clamd reply; storage timeout and unreachable store; sanitiser timeout; broken stream. Every rejection leaves the scratch directory empty and stores nothing. A real process pool and a real MinIO round trip also passed.
- **Commands run and results:** `make backend-verify` exit 0 (663 passed). `make backend-integration` exit 0 (254 passed). Circle 0 validators passed.
- **Tests added or changed:** 34 unit and 2 integration tests.
- **Generated artifacts checked:** OpenAPI unchanged.
- **Known limitations/open decisions:** ClamAV was never started locally, so the client is proven only against a local protocol double. A timed-out sanitise call frees the request but the worker process finishes its job. Files are held in memory (10 MB cap) for the sanitiser and scanner. The pipeline returns metadata; writing the `evidence_files` row and the report link is BE-063.
- **Commit/PR:** `feat: add the streaming evidence sanitation pipeline`
- **Next task may rely on:** `EvidencePipeline.process` returning a `StoredEvidence` that matches the `evidence_files` constraints.
- **AI assistance used:** Designed and wrote the pipeline, adapters, and adversarial tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-063 Multipart report submission

- **Task:** BE-063 — Multipart report submission.
- **Outcome delivered:** `POST /v1/reports` (`api/v1/reports.py`), evidence rows through `ReportWriter.attach_evidence`, `PublicProjectRepository.resolve_project_id`, a managed sanitiser process pool and evidence pipeline wired into `api/main.py`.
- **Files changed:** `services/platform/src/shaidago/api/{v1/reports,v1/__init__,dependencies,main}.py`, `src/shaidago/files/pipeline.py`, `src/shaidago/projects/repository.py`, `src/shaidago/reports/persistence.py`, `src/shaidago/shared/config.py`, `tests/integration/test_report_submission.py`, `contracts/openapi.json`, `docs/API.md`.
- **Schema/contract changes:** OpenAPI gains `POST /v1/reports` and its receipt model. No migration.
- **Security/privacy impact:** The public role writes with insert-only access; nothing is read back. The body is capped on the bytes received, not only on Content-Length, before multipart parsing. Only the sniffed evidence types are kept, and each attachment gets a stable outcome code without its name or content. Field errors never echo submitted values or unexpected field names. The response and stored rows hold no IP, user agent, client HMAC, project slug, or internal report ID. The receipt is sealed for replay under the caller's own key; a replay never re-processes files. Contact is optional, validated by channel, and never identity.
- **Failure behaviour verified:** missing, malformed, and reused keys; unknown project, bad category, short and long description, half a contact, bad email and phone, unexpected fields, too many files; non-multipart bodies; declared and chunked oversize bodies; rate limit with `Retry-After`; concurrent duplicate submissions create one report; an unknown project leaves no report or idempotency record and the key stays usable; a database refusal of an evidence row rolls back the report, keys, and tracking key and removes the uploaded object; a duplicate tracking code returns a conflict without echoing the code and rolls back the second report.
- **Commands run and results:** `make backend-integration` exit 0 (283 passed); `make backend-verify` exit 0 (692 passed); `make openapi-generate` then `make openapi-check` clean; Circle 0 validators passed.
- **Tests added or changed:** 29 integration tests.
- **Generated artifacts checked:** `contracts/openapi.json` regenerated and committed.
- **Known limitations/open decisions:** Files are processed while the idempotency transaction is open, so slow files hold a connection for up to their time limits (three files at most). A crash between upload and commit can leave an unreferenced, unguessable object; a retention sweep is not built yet. The request-body schema in OpenAPI is hand-declared because FastAPI cannot describe streamed multipart with per-file limits, so it must be kept in step with `parse_submission`. No BFF exists to forward the client HMAC header, so the rate limit key falls back to `unknown` for direct calls. Reporter handles are BE-066.
- **Commit/PR:** `feat: add multipart private report submission`
- **Next task may rely on:** A tracking code that is generated once and stored only as a keyed lookup HMAC, ready for the BE-065 lookup function.
- **AI assistance used:** Designed and wrote the endpoint and adversarial tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-065 Tracking status lookup

- **Task:** BE-065 — Tracking status lookup.
- **Outcome delivered:** Revision `0011_tracking_lookup` (`app.tracking_lookup(bytea[])`), `reports/status_lookup.py`, `api/v1/report_status.py` (`POST /v1/report-status:lookup`), a shared report test harness, and the `tracking_code_not_recognised` problem.
- **Files changed:** `services/platform/migrations/versions/0011_tracking_lookup.py`, `src/shaidago/reports/status_lookup.py`, `src/shaidago/api/{v1/report_status,v1/__init__,dependencies}.py`, `src/shaidago/shared/problems.py`, `tests/integration/{test_tracking_lookup,report_support,conftest,test_report_submission}.py`, `contracts/openapi.json`, `docs/API.md`.
- **Schema/contract changes:** One `SECURITY DEFINER` function, executable only by `shaidago_public`, taking at most eight lookup digests and returning status, change time, and the newest public message. OpenAPI gains the lookup path.
- **Security/privacy impact:** The code is in the POST body and never echoed; malformed, unknown, and unreachable codes give one identical 404. A malformed code still runs the same single query with random digests. Each call takes at least a fixed floor (0.25 s by default). Attempts are limited per client and per client and code prefix, with the prefix bucket hashed. The function exposes no ID, text, contact, evidence, or which pepper matched, and the public role still cannot read any report table. Responses are `no-store`.
- **Failure behaviour verified:** eight failure kinds (bad checksum, unknown code, empty, prefix only, garbage, 256 characters, truncated, non-ASCII) return byte-identical bodies apart from the request ID; shape errors (extra field, missing code, oversize body, GET, code in path) reveal nothing; a hit and two misses differ in time by under 250 ms with a 300 ms floor; five tries per prefix then 429 with another client unaffected; a report created under a retired pepper is still found after rotation; only the public role may execute the function and more than eight digests return nothing.
- **Commands run and results:** `make backend-integration` exit 0 (296 passed); `make backend-verify` exit 0 (705 passed); `make openapi-generate` then check clean; Circle 0 validators passed. Schemathesis now also exercises the lookup and caught an undocumented 400 that was fixed by documenting it.
- **Tests added or changed:** 13 integration tests; the report-submission tests now use the shared harness.
- **Generated artifacts checked:** `contracts/openapi.json` regenerated and committed.
- **Known limitations/open decisions:** Timing equalisation is a floor, not a proof; a slow database still shows. Rehashing a retired-pepper hit is not built. `follow_up_questions` is always empty until BE-067. The 404 for a wrong code and the 429 for too many tries are distinguishable by design, since abuse must be visible to the person being limited. Without a BFF the client key defaults to `unknown` for direct calls.
- **Commit/PR:** `feat: add tracking status lookup`
- **Next task may rely on:** A lookup that maps a code to its report only through a database function, which BE-066 and BE-067 can extend for handles and follow-up answers.
- **AI assistance used:** Designed and wrote the migration, endpoint, and adversarial tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-066 Optional anonymous reporter handles

- **Task:** BE-066 — Optional anonymous reporter handles.
- **Outcome delivered:** Revision `0012_reporter_handles` (table, `reports.reporter_handle_id`, six `SECURITY DEFINER` functions), `reports/handles.py`, `reports/handle_store.py`, `api/v1/reporter_handles.py` (create, list reports, delete), handle-linked submission in `POST /v1/reports`, a shared `api/rate_limits.py`, the committed EFF long word list, and `docs/evidence/BE-066-wordlist.md`.
- **Files changed:** `services/platform/migrations/versions/0012_reporter_handles.py`, `src/shaidago/reports/{handles,handle_store,persistence}.py`, `src/shaidago/reports/wordlists/eff_large_wordlist.txt`, `src/shaidago/api/{rate_limits,v1/reporter_handles,v1/reports,v1/report_status,v1/__init__}.py`, `src/shaidago/db/report_tables.py`, `src/shaidago/shared/problems.py`, tests, `contracts/openapi.json`, `docs/API.md`, `docs/evidence/BE-066-wordlist.md`.
- **Schema/contract changes:** New table with only id, handle, Argon2id hash, created date, last-used date, and backoff counters; a nullable foreign key from reports that becomes null on delete. OpenAPI gains three paths and two form fields.
- **Security/privacy impact:** Credentials are generated server-side, shown once, sent only in POST bodies, and never logged (tested). The public role can insert but not read, update, or delete handles. All failures are one 403 whether the handle is unknown, wrong, deleted, or in backoff, and every check costs one Argon2 verification and one bookkeeping call. Backoff is three free tries, then 5 seconds doubling to 15 minutes, resets on success or after an hour, and never locks permanently; per-client and per-client-and-handle limits also apply and cover unknown handles. A submission with wrong credentials stores nothing. A handle and a contact channel are mutually exclusive. Deleting unlinks every report and removes the credential in one database function call. Reviewers get counts through a function and cannot read the hash.
- **Dependencies added:** None. The EFF word list is data (CC BY 3.0 US), fetched and hash-checked, not a package.
- **Failure behaviour verified:** schema introspection (exact column set, no identity or recovery names, date-only last use); credential failures indistinguishable across list, delete, and submit; exponential backoff and cap with a manual clock; per-client rate limiting including unknown handles; reports survive deletion and stay trackable by code while the handle can no longer be used; concurrent deletes and creates; concurrent identical submissions with a handle make one report; logs contain no handle or passphrase; the tracking response never mentions the handle; no recovery or reset path exists in OpenAPI.
- **Commands run and results:** `make backend-verify` exit 0 (736 passed); `make openapi-check` clean; Circle 0 validators passed. Two test defects found while running (a stale backoff expectation and a report chosen from other tests' data) were fixed in the tests, not the code.
- **Tests added or changed:** 16 unit and 13 integration tests; migration/model drift test now covers the new table.
- **Generated artifacts checked:** `contracts/openapi.json` regenerated and committed.
- **Known limitations/open decisions:** The word list is unreviewed by a human (offensive or confusable words, licence terms). A stored hash is not upgraded to new Argon2 parameters on success. The passphrase hash is read by the API process through a function, so an API compromise could read one hash at a time for a handle it names. Handle-based listing returns statuses without dates of submission or categories. The reviewer track record is a function only; no reviewer endpoint uses it before BE-070. Handles are built after the anonymous path, as the plan requires.
- **Commit/PR:** `feat: add optional anonymous reporter handles`
- **Next task may rely on:** `ReportWriter` accepting a verified handle ID, and `app.reporter_handle_track_record` for the reviewer queue.
- **AI assistance used:** Designed and wrote the migration, endpoints, and adversarial tests; fetched and structurally verified the word list.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request. The word list in particular needs a human check.

## 2026-09-19 — BE-067 Report follow-up answers

- **Task:** BE-067 — Report follow-up answers.
- **Outcome delivered:** Revision `0013_follow_up_answers` (questions and answers tables, `app.follow_up_submit`, `app.tracking_follow_ups`), `reports/follow_ups.py`, `api/v1/follow_ups.py` (`POST /v1/report-status:answer-follow-up`), and follow-up questions with an acknowledgement state on the tracking lookup.
- **Files changed:** `services/platform/migrations/versions/0013_follow_up_answers.py`, `src/shaidago/reports/{follow_ups,status_lookup}.py`, `src/shaidago/api/v1/{follow_ups,report_status,__init__}.py`, `src/shaidago/db/report_tables.py`, tests (`test_follow_ups.py`, shared harness helpers, a submission log test), `contracts/openapi.json`, `docs/API.md`.
- **Schema/contract changes:** Two tables with forced row security; the public role has no privilege on either and reaches them only through two `SECURITY DEFINER` functions. OpenAPI gains one path and a `state` on tracked questions.
- **Security/privacy impact:** Ownership is decided inside the database function against the caller's tracking-code digests or verified handle, so an answer can only go to a question about the caller's own report. Answers are AES-GCM ciphertext under a per-answer data key that can be shredded alone; skipped and unsafe answers store no text and no key. One answer per question is enforced by a unique index and by `ON CONFLICT`. Tracking shows a question and whether it was answered, never the answer. Every failure gives one generic problem per credential type. The reviewer role can author and withdraw questions and read answers, and cannot write or edit answers or rewrite a question. The reporter-caused status change and an audit event carry no answer text.
- **Failure behaviour verified:** seven ownership failures (another report's question, unknown, already answered, withdrawn, unknown code, malformed code, empty code) return an identical response and write nothing, including no orphan data key; handles: other handle, wrong passphrase, and unknown handle all give the same 403; malformed bodies (text with a skip, answer missing, empty, too long, two credential styles, none, extra field, bad ID) are 422 before storage; replay, key conflict, missing key; four concurrent answers store exactly one and one status event; the report resumes only when the last open question is answered and not from other statuses; body cap; answer, code, and canary text absent from logs; public role denied on both tables and on writes; reviewer denied answer writes.
- **Commands run and results:** `make backend-integration` exit 0 (336 passed); `make backend-verify` exit 0 (761 passed, counted after the log test was added); `make openapi-generate` then check clean; Circle 0 validators passed.
- **Tests added or changed:** 24 integration tests plus one submission log-absence test that closes a Circle 6 gate gap.
- **Generated artifacts checked:** `contracts/openapi.json` regenerated and committed.
- **Known limitations/open decisions:** Reviewer question authoring is a database grant only; the reviewer endpoint and the audited creation belong to BE-071. An `unsafe` answer is recorded but does not itself raise the report's risk level; that is a reviewer or later-task decision. A withdrawn question is not re-checked between the function's read and its insert beyond the row lock. The reporter's status event is timestamped by the API clock, so a badly skewed clock could order it before a reviewer event (the projection check would then fail closed).
- **Commit/PR:** `feat: add private report follow-up answers`
- **Next task may rely on:** Question rows a reviewer can create, an answer decryptable through `read_answer`, and a report that returns to `under_review` when its last question is answered.
- **AI assistance used:** Designed and wrote the migration, functions, endpoint, and adversarial tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — Health probes, live scanner proof, and CI services

- **Task:** Close the remaining partial items in Circles 1 to 3 (health probes, ClamAV, CI evidence).
- **Outcome delivered:** Required readiness probes for Redis, object storage, and the scanner (`shared/probes.py`, `RedisRateLimiter.check`, `S3ObjectStore.check`, `ClamdScanner.ping`); a live ClamAV integration test; MinIO and ClamAV containers in the CI integration job; refreshed task and gate notes.
- **Files changed:** `services/platform/src/shaidago/{api/main,files/scanner,files/storage,shared/probes,shared/ratelimit}.py`, `tests/integration/{test_infrastructure_probes,test_configured_app}.py`, `.github/workflows/backend.yml`, `.env.example`, `docs/API.md`, `docs/BACKEND_BUILD_ORDER.md`.
- **Schema/contract changes:** None. The readiness response gains component names.
- **Security/privacy impact:** Probes report only `ok` or `unavailable`, as before. No credential or endpoint is echoed. The scanner probe treats a non-PONG reply as not ready.
- **Failure behaviour verified:** each probe passes against the real service and fails when it is dead or misconfigured; readiness goes unavailable when one required probe fails; the real ClamAV reports clean content as clean and the EICAR file as malware; a dead scanner fails closed. The configured-app tests now use the Compose services so only the database varies.
- **Commands run and results:** `make infra-up` (ClamAV healthy); `make backend-integration` exit 0 (342 passed); `make backend-verify` exit 0 (767 passed); Circle 0 validators passed. `gh run list` confirmed earlier CI runs green on `main`.
- **Tests added or changed:** 5 new integration tests; 3 configured-app tests updated.
- **Generated artifacts checked:** OpenAPI unchanged.
- **Known limitations/open decisions:** The updated CI job has not run yet, so its MinIO and ClamAV steps are unproven until the next push (ClamAV signature download may make the job slow). ClamAV does not flag EICAR appended to an image; earlier notes that implied it did referred to the test scanner only. `.env.example` now points `CLAMD_PORT` at the Compose host port (53310); an existing local `.env` needs the same edit. Worker-message request-ID propagation waits for BE-090.
- **Commit/PR:** `feat: add infrastructure readiness probes and prove the live scanner`
- **Next task may rely on:** A readiness endpoint that reflects every infrastructure dependency.
- **AI assistance used:** Wrote the probes, tests, and CI steps; started and exercised the local ClamAV.
- **Prompt summary:** Maintainer asked to close the open partial items.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — Reporter-handle word list review recorded

- **Task:** Record the maintainer's review of the passphrase word list.
- **Outcome delivered:** `docs/evidence/BE-066-wordlist.md` and the task and gate notes now record the human approval.
- **Files changed:** `docs/evidence/BE-066-wordlist.md`, `docs/BACKEND_BUILD_ORDER.md`, `docs/AI_BUILD_LOG.md`.
- **Schema/contract changes:** None.
- **Security/privacy impact:** None; documentation only.
- **Failure behaviour verified:** Not applicable.
- **Commands run and results:** Circle 0 validators passed.
- **Tests added or changed:** None.
- **Generated artifacts checked:** None affected.
- **Known limitations/open decisions:** The approval is recorded as stated by the maintainer in the session, without a list of the checks made. The file hash is unchanged, so the approval applies to the committed list.
- **Commit/PR:** `docs: record the maintainer review of the reporter-handle word list`
- **Next task may rely on:** The word list being human-approved.
- **AI assistance used:** Wrote the record only; the review itself was the maintainer's.
- **Prompt summary:** Maintainer confirmed they reviewed and approved the list.
- **Human review:** Maintainer approved the word list on 2026-09-19.

## 2026-09-19 — BE-070 Minimal-data queue and private detail projections

- **Task:** BE-070 — Minimal-data queue and private detail projections.
- **Outcome delivered:** Reviewer queue and report detail endpoints, a `contact_read` capability, revision `0014_reviewer_queue` (`reports.version` with a bump trigger; audited `app.reviewer_read_contact`), `DataKeyService.load_many`, and the `review/` package (`context`, `queue`, `detail`).
- **Files changed:** `services/platform/migrations/versions/0014_reviewer_queue.py`, `src/shaidago/review/{__init__,context,queue,detail}.py`, `src/shaidago/api/v1/{reviewer_reports,__init__}.py`, `src/shaidago/auth/policy.py`, `src/shaidago/db/report_tables.py`, `src/shaidago/shared/data_keys.py`, tests (`test_reviewer_queue.py`, `reviewer_support.py`, `conftest.py`), `contracts/openapi.json`, `docs/API.md`, `docs/BACKEND_BUILD_ORDER.md`.
- **Schema/contract changes:** One column, one trigger, one `SECURITY DEFINER` function (execute granted to the reviewer role only). OpenAPI gains two reviewer paths.
- **Security/privacy impact:** The queue exposes no report text, contact, handle, or object key. The reviewer role still cannot `SELECT` contacts; the only read path writes its audit row in the same transaction first. Contacts need an explicit query flag and their own capability. Detail decrypts only the description and answers. Responses are `no-store`.
- **Failure behaviour verified:** no session and a disabled reviewer give the same 401; unknown or malformed report IDs are 404 or 422; bad filters, unknown parameters, and a cursor replayed under other filters are refused; an anonymous report yields `contact: null` even when asked; the public role cannot call the contact function or read contacts.
- **Commands run and results:** `make backend-verify` exit 0 (791 passed); Circle 0 validators passed.
- **Tests added or changed:** 16 integration tests, including statement counts that do not grow with page size, evidence, questions, or answers.
- **Generated artifacts checked:** `contracts/openapi.json` regenerated and committed; `make openapi-check` is part of `backend-verify`.
- **Known limitations/open decisions:** The queue is oldest first only (no configurable sort). Project shown by slug, not translated title. Handle track record appears only in detail.
- **Commit/PR:** `feat: add the reviewer queue and private report detail`
- **Next task may rely on:** `reports.version`, `ReviewContext`, `actor_of`, the reviewer test harness (`review_world`).
- **AI assistance used:** Designed and wrote the migration, services, endpoints, and tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-071 Report state machine and append-only events

- **Task:** BE-071 — Report state machine and append-only events.
- **Outcome delivered:** A pure state machine, an audited decision service and endpoint with optimistic concurrency, an encrypted private reason kept apart from the reporter-facing message, and reviewer follow-up question authoring and withdrawal.
- **Files changed:** `services/platform/migrations/versions/0015_status_event_reason.py`, `src/shaidago/review/{state_machine,decisions,follow_up_questions,detail}.py`, `src/shaidago/api/v1/{reviewer_decisions,reviewer_reports,__init__}.py`, `src/shaidago/shared/problems.py`, `src/shaidago/db/report_tables.py`, tests (`tests/unit/review/test_state_machine.py`, `tests/integration/test_report_decisions.py`), `contracts/openapi.json`, `docs/API.md`, `docs/BACKEND_BUILD_ORDER.md`.
- **Schema/contract changes:** Three nullable reason columns with a check (all or none, reviewer or admin actor) on `report_status_events`. OpenAPI gains three reviewer paths and two problem codes.
- **Security/privacy impact:** The private reason is ciphertext under its own data key and is read only by the reviewer detail; the tracking function selects only `public_message`. Audit details hold identifiers, command names, and versions, never text. A refused command is audited in its own transaction because the refused transaction rolls back. The state machine denies by default (unknown status, command, or actor).
- **Failure behaviour verified:** stale status or version (nothing written); every disallowed pair (409, unchanged state); reporter-only command refused for a reviewer; bad text, unknown command or status, extra fields (422 before any write); no session (401), no CSRF (403), unknown report (404); four concurrent decisions apply exactly once; history cannot be updated or deleted by the reviewer role; a reporter answer that resumes review still raises the version.
- **Commands run and results:** `make backend-verify` exit 0 (1056 passed); Circle 0 validators passed. A first run found the new POST route lacked a documented `400`, fixed at the cause.
- **Tests added or changed:** 244 unit cases (full status x command x actor matrix, contract parity) and 13 integration tests.
- **Generated artifacts checked:** `contracts/openapi.json` regenerated; `make openapi-check` is part of `backend-verify`.
- **Known limitations/open decisions:** The event time is the later of the API clock and the newest event plus one microsecond, so a reviewer event is never reordered behind history; a reporter answer arriving with a clock earlier than that still fails closed at the database (BE-067's documented limit). `reporter_message` is free text a reviewer is responsible for keeping free of private detail; only length and character rules bound it. No rate limit yet (BE-100).
- **Commit/PR:** `feat: add the report state machine and audited reviewer decisions`
- **Next task may rely on:** `review.decisions.decide`, the encrypted event reason, and `report_version_conflict` semantics.
- **AI assistance used:** Designed and wrote the migration, state machine, service, endpoints, and tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-072 Encrypted reviewer notes

- **Task:** BE-072 — Encrypted reviewer notes.
- **Outcome delivered:** Append-only notes encrypted per note, create and list endpoints with pagination, and a correct `Allow` header for paths that carry several methods.
- **Files changed:** `services/platform/migrations/versions/0016_report_notes.py`, `src/shaidago/review/notes.py`, `src/shaidago/api/v1/{reviewer_notes,__init__}.py`, `src/shaidago/api/errors.py`, `src/shaidago/db/report_tables.py`, tests (`test_report_notes.py`, `tests/unit/api/test_errors.py`), `contracts/openapi.json`, `docs/API.md`, `docs/BACKEND_BUILD_ORDER.md`.
- **Schema/contract changes:** One table with forced row security (reviewer and owner only; the public role has no privilege), an append-only trigger that allows only foreign-key cascades to delete. OpenAPI gains two paths.
- **Security/privacy impact:** Note text is ciphertext under a per-note key that can be shredded alone; markup is refused so a note can never be rendered as HTML; audit and logs carry the note ID only. The public role cannot read the table, and no view, tracking function, or public projection selects from it.
- **Failure behaviour verified:** empty, oversized, markup, and control-character bodies and extra fields are 422 with nothing stored; no session 401, no CSRF 403, unknown report 404; a cursor from another report is 400; the reviewer and owner roles cannot update or directly delete a note; a destroyed key returns the note with `body: null`.
- **Commands run and results:** `make backend-verify` exit 0 (1065 passed); Circle 0 validators passed. The contract test caught a wrong `Allow` header on a path with two methods (Starlette reports only the first route's methods); fixed once in the error boundary using the generated contract.
- **Tests added or changed:** 9 integration tests; the error-boundary unit test now covers a path with two methods.
- **Generated artifacts checked:** `contracts/openapi.json` regenerated; `make openapi-check` passes inside `backend-verify`.
- **Known limitations/open decisions:** Notes cannot be searched. The `Allow` header is computed from the generated contract, which is built once on the first 405. Reading notes is not separately audited (the detail view is).
- **Commit/PR:** `feat: add encrypted append-only reviewer notes`
- **Next task may rely on:** `review/notes.py` and the `report_notes` table for any later reviewer commentary.
- **AI assistance used:** Designed and wrote the migration, service, endpoints, and tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-073 Evidence download broker

- **Task:** BE-073 — Evidence download broker.
- **Outcome delivered:** An authorised, audited download endpoint that streams the sanitised evidence with forced-download headers and an integrity check.
- **Files changed:** `services/platform/src/shaidago/review/evidence.py`, `src/shaidago/api/v1/{reviewer_evidence,__init__}.py`, `src/shaidago/api/{dependencies,main}.py`, tests (`tests/unit/review/test_evidence.py`, `tests/integration/test_evidence_download.py`, `reviewer_support.py`), `contracts/openapi.json`, `docs/API.md`, `docs/BACKEND_BUILD_ORDER.md`.
- **Schema/contract changes:** None to the schema. OpenAPI gains one path; `Dependencies` gains `evidence_store`.
- **Security/privacy impact:** Streaming through the API removes the signed-URL token from the design. Access is deny-by-default (capability, active session, evidence must belong to the named report), audited before the read, and unsafe or mismatched bytes are never served. Headers forbid rendering, caching, and sniffing. The object key and any storage location stay server side.
- **Failure behaviour verified:** see the build order note; unsafe-state serving is refused by `is_servable` (unit) and cannot be produced through the database because of its check constraint.
- **Commands run and results:** `make backend-verify` exit 0 (1093 passed); Circle 0 validators passed.
- **Tests added or changed:** 20 unit and 8 integration tests.
- **Generated artifacts checked:** `contracts/openapi.json` regenerated; `make openapi-check` passes.
- **Known limitations/open decisions:** The whole file (at most 10 MB) is read into memory before it is sent; no `Range` support; no per-reviewer download rate limit yet (BE-100). A short-lived signed URL was considered and not chosen because a streamed response has no bearer token to expire.
- **Commit/PR:** `feat: add the audited reviewer evidence download broker`
- **Next task may rely on:** `evidence_store` in `Dependencies` and `review/evidence.py` rules.
- **AI assistance used:** Designed and wrote the broker and tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-074 Separate public-update publication transaction

- **Task:** BE-074 — Separate public-update publication transaction.
- **Outcome delivered:** Reviewer-authored public-update drafts, an exact preview with a confirmation digest, and one database function that publishes the update with its citations atomically.
- **Files changed:** `services/platform/migrations/versions/0017_public_updates.py`, `src/shaidago/review/{publication,private_references,detail}.py`, `src/shaidago/api/v1/{reviewer_publication,__init__}.py`, `src/shaidago/api/errors.py`, `src/shaidago/shared/problems.py`, `src/shaidago/db/source_tables.py`, tests (`test_public_update_publication.py`, `tests/unit/review/test_private_references.py`), `contracts/openapi.json`, `docs/API.md`, `docs/BACKEND_BUILD_ORDER.md`.
- **Schema/contract changes:** Two tables (forced row security; reviewer and owner only), a guard trigger making a draft's content fixed and its state terminal after publish or withdraw, and `app.publish_public_update` (execute for the reviewer role only). The reviewer role gained no privilege on `project_updates` or `update_citations`. OpenAPI gains five paths and three problem codes.
- **Security/privacy impact:** The link between a public update and its report exists only in a table no public role can read; the public row carries none and shares the draft's ID so the previewed ID is the published ID. Private text is decrypted in memory only to check the statement (a contact read is audited like any other). The publish function re-checks state under locks, so a status change racing a publication either finishes first (and the publication is refused) or after (and the publication stands). Nothing here is called by a status change, worker, or AI path.
- **Failure behaviour verified:** see the build order note. A first full run showed the contract test catching a route ambiguity (`GET .../{id}:publish` matched the preview route and answered 401 instead of 405); the preview route now takes a `uuid`-typed parameter. The same run showed the `Allow` index matching parameters across a colon; fixed.
- **Commands run and results:** `make backend-verify` exit 0 (1143 passed); Circle 0 validators passed.
- **Tests added or changed:** 14 integration tests and 36 unit tests (every branch of the private-reference and guarded-wording checks).
- **Generated artifacts checked:** `contracts/openapi.json` regenerated; `make openapi-check` passes.
- **Known limitations/open decisions:** Neutrality of the statement is the reviewer's responsibility; the deterministic checks are a floor (the guarded word list is a reviewable constant and will produce false blocks, for example on "not complete" without a passage). Refused publication attempts are not audited (only successes, drafts, and withdrawals). Drafts cannot be edited (withdraw and create a new one). Previewing decrypts the report's private material each time.
- **Commit/PR:** `feat: add separately authored, previewed, citation-backed public update publication`
- **Next task may rely on:** `app.project_updates` rows created only through `app.publish_public_update` for report-derived updates, and the reviewer test harness `review_world`.
- **AI assistance used:** Designed and wrote the migration, service, checks, endpoints, and tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-080 Approved source chunk pipeline

- **Task:** BE-080 — Approved source chunk pipeline.
- **Outcome delivered:** Deterministic source chunking and a worker refresh service whose only input is a database view of public-project citations to approved, currently available source versions. Chunks keep exact offsets, hashes, token counts, language, section context, chunker version, and current active state; unchanged refreshes keep the same rows and ineligible material is deactivated.
- **Files changed:** `services/platform/migrations/versions/0018_approved_source_chunks.py`, `src/shaidago/retrieval/{__init__,chunking,corpus}.py`, `src/shaidago/db/source_tables.py`, test support plus `tests/unit/retrieval/test_chunking.py` and `tests/integration/test_source_chunks.py`, `docs/{IMPLEMENTATION_PLAN,BACKEND_BUILD_ORDER,AI_BUILD_LOG}.md`.
- **Schema/contract changes:** `source_versions.language` is an immutable four-locale field (existing rows default to the English source locale). New `app.source_chunks`, an internal approved-document view, and `public_api.source_chunks` carry the corpus; OpenAPI is unchanged.
- **Security/privacy impact:** The worker cannot read source tables or any report table; it reads only the security-barrier approved-document view and may insert/update, but not delete, corpus rows. A security-definer trigger checks active rows against the immutable source text and current eligibility. The public view repeats eligibility at read time, so stale flags cannot expose an unavailable, unapproved, non-public, cross-project, or private record.
- **Failure behaviour verified:** Forged chunk text is rejected at the database boundary; the public role cannot read the corpus table; the worker cannot delete chunks; source language cannot be rewritten; draft claims and pending versions never enter the corpus; availability or approval loss hides and deactivates existing chunks, and re-eligibility reuses the row.
- **Commands run and results:** Targeted retrieval unit tests passed (5); targeted corpus integration tests passed (4); migration/source regressions passed (41); `make backend-verify` exited 0 (1152 passed); all six Circle 0 validators passed.
- **Tests added or changed:** Five unit tests and four integration tests; source-version fixture inserts now supply the appended language column.
- **Generated artifacts checked:** `make openapi-check` passed inside `backend-verify`; OpenAPI was unchanged. Metadata drift, empty-to-head, every-revision downgrade/upgrade, and one-step rollback tests passed.
- **Known limitations/open decisions:** Current reviewed source versions default to English because the source register contains English evidence; adding a differently sourced version requires setting its supported language explicitly. Chunk building is a service for the future worker/maintenance command; scheduling arrives with the worker lifecycle. Embeddings and text-search vectors intentionally remain for BE-081.
- **Commit/PR:** `feat: add approved public source chunk corpus`
- **Next task may rely on:** `CorpusBuilder.refresh`, deterministic `ChunkSpan` values, and `public_api.source_chunks` as the only readable corpus projection.
- **AI assistance used:** Completed the inherited chunker, designed the corpus boundary and migration, and wrote the tests and documentation.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-081 Hybrid retrieval

- **Task:** BE-081 — Hybrid retrieval.
- **Outcome delivered:** Project-isolated full-text and cosine retrieval over the approved public source corpus, combined with reciprocal-rank fusion and an honest keyword-only fallback. Checked-in embeddings are strict, content-hash-keyed fixtures; ordinary seeding loads them without a key and never calls a provider, while generation is a separate explicit command.
- **Files changed:** `Makefile`, `README.md`, `data/embeddings/{README.md,fixture-hash-v1.jsonl}`, `services/platform/{README.md,pyproject.toml,uv.lock}`, migration `0019_hybrid_retrieval.py`, `src/shaidago/db/source_tables.py`, `src/shaidago/retrieval/{corpus,embeddings,generate_embeddings,search}.py`, `src/shaidago/seed/__main__.py`, retrieval unit tests, hybrid retrieval and seed integration tests, and backend execution documentation.
- **Schema/contract changes:** `app.source_chunks` gains a stored `tsvector`, nullable `vector(1536)`, model and generation timestamp, all-or-none embedding checks, and GIN/HNSW indexes. The internal public-role retrieval view exposes only those derived fields on chunks that still pass live project, source, version, and citation eligibility. OpenAPI is unchanged.
- **Security/privacy impact:** Retrieval starts from the allowlisted approved-public-source view, requires the selected project in both keyword and semantic branches, and has no path to reports, contacts, reviewer notes, or discovery. Checked-in files contain hashes and vectors but no source text. Seed never reads an OpenAI key or contacts a provider; the explicit generator selects only already-public chunks and sends only bounded batches of their text. Embeddings are cleared if a chunk's content hash changes.
- **Dependencies added:** `pgvector` Python 0.5.0 supplies the official SQLAlchemy vector type used for metadata and migration drift checks. It is the current locked release from the maintained pgvector Python project, has no runtime dependencies, uses the MIT licence, and adds a 31 KB wheel. `pip-audit --skip-editable` reported no known vulnerability; the lockfile records package hashes. PostgreSQL's pgvector extension was already part of the accepted stack and local image.
- **Failure behaviour verified:** Empty and oversized/control-character queries fail before SQL; malformed, non-finite, out-of-range, or wrong-dimension vectors fail closed; absent or mismatched embeddings retain keyword mode; empty projects return no chunks; source unavailability disappears immediately through the live view even before a refresh; a generated fixture with the wrong shape, model, fields, hash, or duplicate hash is refused; provider index/count errors are refused; seed without a matching file reports keyword fallback rather than attempting generation.
- **Commands run and results:** Targeted Ruff and Pyright checks passed; targeted retrieval, corpus, seed, and migration tests passed (42); `make backend-verify` exited 0 with format, lint, strict type checking, Bandit, `pip-audit`, OpenAPI drift, and 1167 deterministic tests passing; all six Circle 0 validators passed. The explicit OpenAI command was not run against a live provider, as required by the no-live-provider hard stop; its transport was exercised with `httpx.MockTransport`.
- **Tests added or changed:** Six query/vector unit cases, four embedding/generator unit cases, four PostgreSQL hybrid retrieval tests, and one ordinary-seed fallback integration test; existing corpus updates now clear stale embeddings when text changes.
- **Generated artifacts checked:** `uv.lock` was regenerated; `make openapi-check` passed inside the full gate and the OpenAPI artifact was unchanged. The migration suite proved empty-to-head, full downgrade/upgrade, one-step rollback, role ownership, index definitions, and SQLAlchemy metadata parity.
- **Known limitations/open decisions:** The checked-in vector is deliberately synthetic and covers only the synthetic integration document; there is no default-model file because current demo source versions remain pending review, so demo retrieval stays in explicit keyword mode. Query-embedding production belongs to the next provider task. The explicit generation workflow has fixture evidence only and still needs an authorised opt-in live run before any claim about live provider interoperability.
- **Commit/PR:** `feat: add project-scoped hybrid source retrieval`
- **Next task may rely on:** `Retriever.search`, `RetrievalResult.mode`, strict 1,536-dimension vector validation, content-hash fixture loading, and `public_api.source_chunks` as the fail-closed corpus boundary.
- **AI assistance used:** Designed and implemented the schema, retrieval and fixture paths, explicit provider command, tests, dependency review, and documentation.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-082 OpenAI provider and strict schema

- **Task:** BE-082 — OpenAI provider and strict schema.
- **Outcome delivered:** A typed language-model boundary for grounded answers, a deterministic checked-in replay adapter, and a bounded OpenAI Responses API adapter that returns only strictly shaped answer data plus application-owned generation time.
- **Files changed:** `data/qa-fixtures/{README.md,grounded-qa-v1.json}`, `services/platform/src/shaidago/retrieval/{language,openai}.py`, `services/platform/tests/unit/retrieval/{test_language,test_openai}.py`, and backend execution documentation.
- **Schema/contract changes:** No database or HTTP contract change. The internal `grounded-answer-v1` schema contains `answer`, bounded `statements[{text,citation_ids}]`, `insufficient_evidence`, a bounded coverage note, and `generated_at`; every object forbids additional properties and citation IDs use an opaque application format.
- **Security/privacy impact:** The outbound payload is an explicit allowlist of locale, bounded question, up to five approved public passages, opaque citation IDs, and the application timestamp. The request sets `store: false`, supplies no tools, carries no metadata or user identifier, caps generated tokens, and uses a streamed 64 KiB response limit. Provider and transport errors expose stable codes only; neither the adapter nor tests log prompts, passage text, upstream bodies, or credentials. Checked-in replay data stores a fingerprint and synthetic structured output, not the raw question or passage.
- **Dependencies added:** None; the existing `httpx` and Pydantic dependencies implement the transport and strict boundary.
- **Failure behaviour verified:** Timeouts, transport failures, 408/409/429, and 5xx are classified retryable but are not retried by the adapter. Other 4xx, malformed JSON/schema, oversized output, incomplete output, multiple messages, and timestamp changes are non-retryable. Refusals and provider-added tool/action content are policy failures. A missing replay fingerprint is explicit and non-retryable. All failure strings omit upstream and input content.
- **Commands run and results:** Official OpenAI Responses and Structured Outputs documentation was checked before implementation; targeted Ruff and Pyright passed; provider and replay unit tests passed (24); the corrected retrieval unit/integration run passed (47); `make backend-verify` exited 0 with formatting, lint, strict types, Bandit, `pip-audit`, OpenAPI drift, and 1191 deterministic tests passing. No live provider call was made.
- **Tests added or changed:** Seven request/schema/replay fixture tests and seventeen Responses transport tests, including exact outbound shape, `store: false`, empty tools, model selection, body cap, safe classifications, one-attempt behaviour, refusal/action rejection, and timestamp validation.
- **Generated artifacts checked:** `make openapi-check` passed inside the full gate; OpenAPI and lockfiles are unchanged. The replay fixture contains only a synthetic answer and a stable request digest.
- **Known limitations/open decisions:** Shape validation is deliberately not the citation/safety judgement: unknown citations, statement support, guarded language, and approved insufficient-evidence fallback belong to the next validator task. The single replay record proves the adapter path but the four-language evaluation corpus arrives later. Live interoperability remains unclaimed until an authorised opt-in provider run.
- **Commit/PR:** `feat: add strict grounded-answer provider boundary`
- **Next task may rely on:** `GroundedAnswerRequest`, `LanguageModelResult`, `RetryClass`, the exact application timestamp check, and the distinction between replay and live results.
- **AI assistance used:** Used official OpenAI documentation to confirm the current Responses request fields, then designed and implemented the provider boundary, replay fixture, safe parser, and adversarial transport tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-083 Deterministic citation and safety validator

- **Task:** BE-083 — Deterministic citation and safety validator.
- **Outcome delivered:** A fail-closed validator that accepts provider prose only when every statement has unique, available evidence from the selected project, the cited passages deterministically support its meaningful terms and numbers, the answer contains no uncited extra prose, and the content passes the reporting-domain safety rules. Every failure discards the entire provider answer and returns the exact approved insufficient-evidence text plus eligible project source links.
- **Files changed:** `data/qa-fixtures/grounded-qa-v1.json`, `services/platform/src/shaidago/retrieval/{language,openai,validation}.py`, retrieval validator/provider/replay unit tests, and backend execution documentation.
- **Schema/contract changes:** No database or HTTP contract change. The internal provider schema advances to `grounded-answer-v2` and adds a required locale that must exactly match the application request; the replay fingerprint changes accordingly. OpenAPI is unchanged.
- **Security/privacy impact:** Citation resolution is project-scoped and availability-aware, and duplicate or ambiguous identifiers fail closed. Uncited prose, unsupported number changes, guarded completion claims, accusations or guilt, person identification, contact/tracking data, instructions to reveal private material, prompt-injection phrases, and truth scores cannot reach the accepted answer. Failure links are derived only from available evidence already supplied for the selected project; provider prose is never partially returned.
- **Dependencies added:** None.
- **Failure behaviour verified:** Unknown, ambiguous, duplicate, cross-project, unavailable, missing, or unsupported citations; uncited answer additions; insufficient-evidence provider output; locale mismatch; unsafe allegations, identity text, private data/instructions, prompt injection, truth scores, and unsupported completion language all produce one complete fallback. The fallback remains English and reports `served_locale=en` rather than silently claiming the requested locale.
- **Commands run and results:** Targeted validator tests passed with 100% statement and branch coverage (20); targeted retrieval Ruff, Pyright, and unit tests passed (59); `make backend-verify` exited 0 with formatting, lint, strict types, Bandit, `pip-audit`, OpenAPI drift, and 1211 deterministic tests passing; all six Circle 0 validators passed.
- **Tests added or changed:** Twenty validator cases cover every validator branch; provider and replay tests now prove exact locale binding and the versioned fixture digest.
- **Generated artifacts checked:** `make openapi-check` passed inside the full gate; OpenAPI and lockfiles are unchanged. The checked-in replay fixture was regenerated only for the internal schema version and locale field.
- **Known limitations/open decisions:** Passage support is deliberately conservative lexical and numeric linkage, not semantic truth verification. The approved fallback source text is currently English; reviewed Hausa, Igbo, and Yoruba fallback translations and semantic language evaluation remain for the four-language evaluation task and must not be claimed before human review.
- **Commit/PR:** `feat: add fail-closed grounded-answer validation`
- **Next task may rely on:** `validate_answer`, `ValidationDecision`, exact fallback text, requested/served locale disclosure, and eligible `SourceLink` values.
- **AI assistance used:** Designed and implemented the deterministic citation/support and safety rules, locale-bound provider schema, adversarial tests, fixture update, and documentation.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-084 Grounded project question endpoint

- **Task:** BE-084 — Project question endpoint.
- **Outcome delivered:** A rate-limited, no-store project question endpoint that resolves the public project and requested locale, retrieves only approved project chunks, invokes the configured replay or live grounded-answer provider, applies the deterministic validator, and returns either a short answer with resolvable public citations or the complete approved fallback. Retryable provider outages use a dedicated safe problem response.
- **Files changed:** `contracts/openapi.json`, `services/platform/README.md`, migration `0020_question_metrics.py`, database metadata/registry, API dependency/provider wiring, the project-question route and use case, retrieval query handling, safe problem catalogue, endpoint/retrieval/contract-fuzz tests, and backend execution documentation.
- **Schema/contract changes:** OpenAPI gains `POST /v1/projects/{slug}/questions` and its strict request, response, citation, retrieval, and problem shapes. PostgreSQL gains append-only operational table `app.question_runs` with bounded counts, outcome, duration, locale, request ID, and model/prompt/schema metadata; there is deliberately no user question, provider prompt, source passage, client pseudonym, or address field.
- **Security/privacy impact:** The public database role retrieves only through `public_api` views, may insert but cannot select question metrics, and cannot persist question content. The request sends only the normalised question and up to five already-approved public passages to the language provider. Responses expose allowlisted public source fields, set `Cache-Control: no-store`, never expose validator findings or provider bodies, and discard all partial provider prose on failure. Per-client abuse limits use the BFF-provided HMAC only in Redis keys, not PostgreSQL or responses.
- **Dependencies added:** None.
- **Failure behaviour verified:** Missing/hidden projects return the ordinary not-found problem; missing infrastructure fails closed; empty corpora, unsafe answers, malformed provider output, and validation findings return the exact fallback; retryable provider failure returns `question_answering_unavailable`; unknown fields, query parameters, controls, and oversized text are rejected; the rate limit returns `rate_limited`; every error remains no-store and omits the submitted question.
- **Commands run and results:** Targeted Ruff and Pyright passed; targeted retrieval, endpoint, configured-app, hybrid-retrieval, migration, and contract tests passed; `make backend-verify` exited 0 with formatting, lint, strict types, Bandit, `pip-audit`, OpenAPI drift, migration drift/rollback, API fuzzing, and 1218 deterministic tests passing. No live provider call was made.
- **Tests added or changed:** Six real-role endpoint/database integration tests and one keyword-query unit test; the OpenAPI property harness now injects the deterministic replay provider.
- **Generated artifacts checked:** `contracts/openapi.json` was regenerated from FastAPI and passed the committed-contract check. Migration tests passed empty-to-head, every-revision downgrade/upgrade, one-step rollback, ownership, restricted role, index, and metadata parity checks. Lockfiles are unchanged.
- **Known limitations/open decisions:** The request path currently uses the required honest keyword retrieval mode; the hybrid retriever remains available and tested, but a runtime query-embedding adapter is not wired into this endpoint. The exact approved fallback remains English with explicit `served_locale=en` until the next task's four-language corpus and human language review establish safe reviewed alternatives.
- **Commit/PR:** `feat: add grounded project question endpoint`
- **Next task may rely on:** The question contract, `ProjectQuestionService`, privacy-safe `question_runs` metrics, configured replay/live provider wiring, exact fallback behavior, and the safe provider-outage problem code.
- **AI assistance used:** Designed and implemented the endpoint orchestration, metrics boundary and grants, natural-question keyword fallback, contract, adversarial integration tests, and documentation; corrected the database-test environment and contract-fuzzer dependency setup without weakening checks.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-085 Four-language grounded-answer evaluation

- **Task:** BE-085 — Four-language evaluation harness (blocked only on the required human language review).
- **Outcome delivered:** A versioned synthetic golden corpus and strict evaluator that expand eleven answerability, evidence-gap, conflict, injection, citation, fact-change, malformed-output, and timeout scenarios across English, Hausa, Igbo, and Yoruba. Deterministic scoring passes 44/44 cases, 28/28 citation checks, and 44/44 policy checks. A separate explicitly gated live runner accepts an injected provider or `--live` CLI invocation and writes only safe outcomes and model/prompt/schema versions.
- **Files changed:** `data/qa-evaluation/{README.md,golden-v1.json}`, `services/platform/src/shaidago/retrieval/evaluation.py`, multilingual evaluation tests, service documentation, and backend execution documentation.
- **Schema/contract changes:** No database or HTTP contract change. The corpus is version 1 and is locked to `grounded-qa-v1` and `grounded-answer-v2`; strict models reject missing locales, version drift, duplicate or missing scenario kinds, extra fields, and inconsistent review claims.
- **Security/privacy impact:** All cases are visibly synthetic. Deterministic CI reads no provider key and makes no network call. The live path requires explicit `--live`, model, output path, and `OPENAI_API_KEY`; its result contains only synthetic case IDs, safe outcomes, and version identifiers, never questions, passages, provider responses, or a key. No live run was made.
- **Dependencies added:** None.
- **Failure behaviour verified:** Cross-project and unknown citations, unsupported changed names/numbers/dates, prompt-injection output, insufficient/conflicting evidence, and malformed provider output fail closed; retryable timeout is classified unavailable. Pending review records cannot claim a reviewer, date, or findings, while reviewed records require all of them.
- **Commands run and results:** The deterministic command reported 44/44 cases, 28/28 citation checks, 44/44 policy checks, 11/11 per locale, all human-review statuses pending, and `live_provider_called=false`; targeted evaluation tests passed (9); Ruff and Pyright passed; `make backend-verify` exited 0 with formatting, lint, strict types, Bandit, `pip-audit`, OpenAPI drift, API fuzzing, and 1227 deterministic tests passing; all six Circle 0 validators passed.
- **Tests added or changed:** Nine evaluation tests cover full four-locale expansion, machine-checkable invariant names/amounts/dates, pending-review honesty, corpus drift rejection, safe aggregate output, strict checked-in JSON, and injected live-run metadata without a network call.
- **Generated artifacts checked:** OpenAPI and lockfiles are unchanged by this task; `make openapi-check` passed inside the full gate. The golden corpus is hand-reviewable UTF-8 JSON rather than generated output.
- **Known limitations/open decisions:** Hausa, Igbo, Yoruba, and English evaluation copy is machine-assisted draft text and has not received the required fluent human review. All review dimensions remain explicitly pending. The opt-in live OpenAI path was implemented but not executed because live paid-provider calls are a hard stop.
- **Commit/PR:** `test: add multilingual grounded-answer evaluation`
- **Next task may rely on:** Deterministic corpus structure and scoring only. It must not treat any locale copy as reviewed or start Circle 9 until fluent reviewers complete and record all four review entries.
- **AI assistance used:** Designed the synthetic cross-locale corpus, deterministic scenario expansion/scoring, review-state guards, safe aggregate report, opt-in live runner, tests, and documentation; it did not perform human language review.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Completed by the maintainer (Aniekan Winner Anietie) on 2026-09-19, who states they are fluent in the pilot languages and checked all four locale packs. `data/qa-evaluation/golden-v1.json` records each locale as `reviewed` with meaning, names, amounts, dates, uncertainty and safety wording marked `preserved`. The record names the reviewer and is a self-reported review, not an independent one.

## 2026-09-19 — BE-090 Dramatiq broker and job envelope

- **Task:** BE-090 — Dramatiq broker and job envelope.
- **Outcome delivered:** A worker process with identifier-only jobs, persisted run stage and lease, idempotent redelivery, bounded retries, dead-lettering, and a visible exhausted state.
- **Files changed:** `services/platform/migrations/versions/0021_discovery_runs.py`, `src/shaidago/db/{discovery_tables,registry}.py`, `src/shaidago/worker/*`, `src/shaidago/shared/config.py`, tests (`tests/unit/worker/*`, `tests/integration/{discovery_support,test_discovery_worker}.py`), `.env.example`, `Makefile`, `docs/BACKEND_BUILD_ORDER.md`.
- **Schema/contract changes:** `app.discovery_runs` with row security (owner, worker, reviewer; no public role) and a guard trigger; the worker role may update only progress and lifecycle columns, reviewers may insert runs and request cancellation. No OpenAPI change. New optional setting `DATABASE_URL_WORKER`.
- **Security/privacy impact:** The message schema cannot carry private data. The worker uses its own restricted role and cannot create runs or edit their approved query. A finished run is immutable at the database.
- **Failure behaviour verified:** duplicate concurrent delivery, expired versus live lease, a crash between stages (no repeated `start_search`), permanent failure code, attempt cap, finished and unknown runs, cancellation before and between stages (retrieved counts kept), exhausted retries, illegal edges refused for the worker role, and unprivileged writes refused.
- **Commands run and results:** `make backend-verify` exit 0 (1543 passed); Circle 0 validators run at the end of the circle.
- **Tests added or changed:** 16 integration tests; unit tests for the envelope, machine, and broker.
- **Generated artifacts checked:** OpenAPI unchanged.
- **Known limitations/open decisions:** Not exercised against a real Redis broker; the stub broker covers delivery, retry, and dead-letter semantics. The pipeline stages are placeholders that fail closed. The lease is 300 seconds with no renewal, so a stage longer than that could be taken over (stages are idempotent, so the effect is repeated work, not corruption).
- **Commit/PR:** `feat: add the discovery worker, job envelope, and run lifecycle`
- **Next task may rely on:** `RunStore`, `process_run`, and the `DiscoveryPipeline` protocol.
- **AI assistance used:** Designed and wrote the migration, worker modules, and tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-091 Privacy-safe query planner

- **Task:** BE-091 — Privacy-safe query planner.
- **Outcome delivered:** A pure, allowlist-first query planner with sensitive-term detectors, term provenance, an exact-approval digest, and a final outbound check.
- **Files changed:** `services/platform/src/shaidago/discovery/{__init__,planner}.py`, `tests/unit/discovery/test_planner.py`, `docs/BACKEND_BUILD_ORDER.md`.
- **Schema/contract changes:** None (the run table already stores `query_text`, `query_policy_version`, and the approver).
- **Security/privacy impact:** A term is used only if it is public project data or an in-vocabulary neutral concept and passes every detector; an uncertain term is dropped. A model suggestion cannot add a name, place, or identifier because the vocabulary is a closed list.
- **Failure behaviour verified:** 20 obfuscated canaries and generated email and phone variants never pass; over-long, duplicate, empty, and implausible-year inputs are bounded; rejections carry a reason code, never the text.
- **Commands run and results:** `make backend-verify` exit 0.
- **Tests added or changed:** 51 unit tests.
- **Generated artifacts checked:** None.
- **Known limitations/open decisions:** The concept vocabulary (about 40 words) is a reviewable constant and deliberately small; a legitimate concept outside it is excluded. Detectors favour false positives, so an unusual public project title with many digits would be dropped from the query. Name detection for report scope is by allowlist rather than a named-entity model.
- **Commit/PR:** `feat: add the privacy-safe discovery query planner`
- **Next task may rely on:** `plan_public_query`, `plan_report_query`, `assert_query_safe`, and `approval_matches`.
- **AI assistance used:** Designed and wrote the planner and property tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-092 Search provider adapter and budgets

- **Task:** BE-092 — Search provider adapter and budgets.
- **Outcome delivered:** A URL-only search provider interface, a Brave adapter, a labelled replay adapter, and a pure public-run budget decision, with two new settings.
- **Files changed:** `services/platform/src/shaidago/discovery/{search,budget}.py`, `src/shaidago/shared/config.py`, `tests/unit/discovery/test_search.py`, `.env.example`, `docs/BACKEND_BUILD_ORDER.md`.
- **Schema/contract changes:** None.
- **Security/privacy impact:** The adapter refuses any query the planner would refuse, before a request exists; the credential is never in a repr, log, or exception; results cannot carry snippets or ranks.
- **Failure behaviour verified:** see the build order note.
- **Commands run and results:** `make backend-verify` exit 0 (1615 passed).
- **Tests added or changed:** 72 unit tests (adapter, fixtures, budget).
- **Generated artifacts checked:** OpenAPI unchanged.
- **Known limitations/open decisions:** No live Brave call was made (hard stop: live provider). The Brave response shape (`web.results[].url`) follows the provider's documented format and is unverified against a live response. Whether the active Brave plan permits storing snippets is unresolved, so none are stored.
- **Commit/PR:** `feat: add the search provider adapter and public-run budget decision`
- **Next task may rely on:** `SearchProvider`, `FixtureSearchProvider`, and `decide_public_run`.
- **AI assistance used:** Designed and wrote the adapters, decision function, and tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-093 SSRF-safe public fetcher

- **Task:** BE-093 — SSRF-safe public fetcher.
- **Outcome delivered:** A destination guard and a bounded, pinned, robots-respecting fetcher.
- **Files changed:** `services/platform/src/shaidago/discovery/{netguard,fetcher}.py`, `tests/unit/discovery/{test_netguard,test_fetcher}.py`, `docs/BACKEND_BUILD_ORDER.md`.
- **Schema/contract changes:** None.
- **Security/privacy impact:** No request can be made to a non-public destination through any hop; no credential, cookie, or caller header is sent; bodies are bounded compressed and decompressed; errors carry stable codes and never the URL.
- **Failure behaviour verified:** every required fixture (IPv4 and IPv6 local forms, decimal, octal, and hex host confusion, mixed DNS answers, rebinding, redirect to a private IP, metadata IPs, oversized and chunked bodies, compression bombs, slow bodies, unsupported port and scheme, credentials in the URL) plus robots and access-control behaviour.
- **Commands run and results:** `make backend-verify` exit 0 (1747 passed). Branch coverage measured for the guard (100%) and fetcher (98%).
- **Tests added or changed:** 204 unit tests.
- **Generated artifacts checked:** None.
- **Known limitations/open decisions:** Verified against a simulated network only (an `httpx.MockTransport` and a fake resolver); the `sni_hostname` extension and the pinned-IP request path are unproven against a real TLS server in this run. `Content-Encoding` is limited to gzip and deflate (a Brotli-only origin is skipped). Robots parsing uses the standard library parser. Per-host limits are per fetcher instance, not shared across worker processes. Publisher terms are honoured only through robots and access signals; there is no per-publisher terms review.
- **Commit/PR:** `feat: add the SSRF-safe public page fetcher`
- **Next task may rely on:** `SafeFetcher.fetch(url) -> FetchedPage` and the `FetchError` and `UnsafeDestinationError` codes.
- **AI assistance used:** Designed and wrote the guard, fetcher, and adversarial tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-094 Inert extraction and provenance

- **Task:** BE-094 — Inert extraction and provenance.
- **Outcome delivered:** Bounded inert extraction of HTML, PDF, and text with provenance, scoped de-duplication, and stored, unreviewed discovered sources with sightings.
- **Files changed:** `services/platform/migrations/versions/0022_discovered_sources.py`, `src/shaidago/discovery/{extract,dedupe,records}.py`, `src/shaidago/db/discovery_tables.py`, tests (`tests/unit/discovery/test_extract.py`, `tests/integration/test_discovered_sources.py`), `docs/BACKEND_BUILD_ORDER.md`.
- **Schema/contract changes:** Two tables with forced row security (worker inserts and refreshes; reviewers read; no public role) and named constraints. No OpenAPI change.
- **Security/privacy impact:** Page text never becomes instructions; active and hidden content is removed; scopes never mix in de-duplication; only an excerpt and hashes are kept; every result is `not_reviewed`.
- **Failure behaviour verified:** see the build order note.
- **Commands run and results:** `make backend-verify` exit 0 (1789 passed). A first run failed the bandit gate on f-string SQL constants (`B608`); the statements are now literal.
- **Tests added or changed:** 34 unit and 8 integration tests.
- **Generated artifacts checked:** OpenAPI unchanged.
- **Known limitations/open decisions:** The injection heuristic is a phrase list, so it flags obvious attempts and misses novel ones (the analysis stage's isolation and validation are the real defence). The `bit_count` near-duplicate query scans one scope's unmerged rows, fine at pilot size. Stale or unavailable sources are updated by the worker only through the `availability` column; the decision and attachment columns arrive with BE-096. The preliminary type is a domain guess with three outcomes.
- **Commit/PR:** `feat: add inert page extraction, provenance, and scoped de-duplication`
- **Next task may rely on:** `extract`, `ExtractedPage`, `SourceRecorder`, and `Scope`.
- **AI assistance used:** Designed and wrote the extraction, de-duplication, recorder, migration, and tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-095 Structured discovery analysis

- **Task:** BE-095 — Structured discovery analysis.
- **Outcome delivered:** A strict analysis schema, provider adapters (OpenAI and fixture), and a deterministic fail-closed validator.
- **Files changed:** `services/platform/src/shaidago/discovery/analysis.py`, `src/shaidago/retrieval/{openai,validation}.py` (public `send`, `output_text`, `statement_supported`, `safety_findings`; tracking-code false-positive fix), `src/shaidago/review/private_references.py` (same fix), tests (`tests/unit/discovery/test_analysis.py`, regression tests), `docs/BACKEND_BUILD_ORDER.md`.
- **Schema/contract changes:** None.
- **Security/privacy impact:** The provider request holds only opaque IDs, publisher domains, and inert excerpts; injection-flagged pages should be excluded by the caller. Output is never trusted before validation; private terms are refused.
- **Failure behaviour verified:** see the build order note. The tracking-code fix removes a class of false blocks (fail-closed, but wrong) in Q&A and publication text.
- **Commands run and results:** `make backend-verify` exit 0 (1822 passed).
- **Tests added or changed:** 32 new unit tests plus two regression tests.
- **Generated artifacts checked:** OpenAPI unchanged.
- **Known limitations/open decisions:** Not called against the live provider (hard stop). The stance-word list and personal-data question pattern are small reviewable constants. The `needs_review` status is entered only for invalid output; a valid analysis with contradictions completes and shows them, which the maintainer may want to change. The caller (BE-096) must exclude injection-flagged sources from passages.
- **Commit/PR:** `feat: add validated structured discovery analysis`
- **Next task may rely on:** `analyse_sources`, `SourcePassage`, `FixtureAnalyser`, and `OpenAIAnalyser`.
- **AI assistance used:** Designed and wrote the analysis module, adapters, and tests; found and fixed the shared false positive.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-096 Discovery run APIs and state transitions

- **Task:** BE-096 — Discovery run APIs and state transitions.
- **Outcome delivered:** Public and reviewer run APIs, the real search-fetch-extract-analyse pipeline, replay and live provider selection, a job queue for the API, and reviewer decisions on discovered sources.
- **Files changed:** `services/platform/migrations/versions/0023_discovery_review.py`, `src/shaidago/discovery/{pipeline,service,providers,pages,dispositions}.py`, `src/shaidago/worker/{queue,pipeline,store,envelope,entry}.py`, `src/shaidago/api/v1/{discovery,reviewer_discovery,__init__}.py`, `src/shaidago/api/{dependencies,main}.py`, `src/shaidago/db/discovery_tables.py`, tests (`test_discovery_api.py`, `test_discovery_pipeline.py`, `tests/unit/discovery/test_dispositions_and_providers.py`, harness updates), `contracts/openapi.json`, `docs/API.md`, `docs/BACKEND_BUILD_ORDER.md`.
- **Schema/contract changes:** Two public views, a function for creating public runs, a function for attaching a source, decision columns and a guard trigger, an encrypted follow-up answers table. OpenAPI gains 9 paths.
- **Security/privacy impact:** Public and private discovery cannot cross by ID, DTO, or view; reviewer approval is bound to the exact query digest; attach yields only a pending source; decisions and answers are encrypted; the worker still cannot read reports.
- **Failure behaviour verified:** see the build order note. A first full run showed the daily-budget query counting runs on later days (a test artefact of moving the clock, fixed by bounding the day), the decision key being reused for a second decision on one source (each decision now has its own key), and the contract fuzzer needing a queue in its app.
- **Commands run and results:** `make backend-verify` exit 0 (1934 passed).
- **Tests added or changed:** 18 API, 9 pipeline, 85 unit.
- **Generated artifacts checked:** `contracts/openapi.json` regenerated; `make openapi-check` passes.
- **Known limitations/open decisions:** Public cancel and public follow-up answers from the plan are intentionally not offered (a shared anonymous run must not be steerable); the maintainer should confirm. Live search, fetch, and analysis were not exercised. A job lost after commit is recovered only by the next public request (public runs) or a reviewer retry; there is no background sweeper. `needs_review` is entered only for invalid analysis or a missing replay fixture. Decision reasons are visible only to reviewers via decryption not yet exposed by an endpoint.
- **Commit/PR:** `feat: add the discovery run APIs, pipeline, and reviewer source decisions`
- **Next task may rely on:** the run lifecycle and replay providers, ready for fixtures (BE-097).
- **AI assistance used:** Designed and wrote the migration, pipeline, services, endpoints, and tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-097 Replay fixtures and live evidence

- **Task:** BE-097 — Replay fixtures and live evidence.
- **Outcome delivered:** Generated synthetic replay fixtures for all listed scenarios with end-to-end tests, replay labelling, a public-run query stored at creation, and a documented, pending live evidence procedure.
- **Files changed:** `data/discovery-fixtures/*`, `services/platform/scripts/build_discovery_fixtures.py`, `migrations/versions/0024_public_run_query.py`, `src/shaidago/discovery/{pipeline,service,pages}.py`, tests (`test_discovery_replay.py`, `tests/live/test_discovery_live.py`), `docs/evidence/BE-097-live-evidence.md`, `docs/BACKEND_BUILD_ORDER.md`.
- **Schema/contract changes:** The public run creation function now takes and stores the planned query and policy version.
- **Security/privacy impact:** Fixtures use reserved `.test` domains and invented pages; the replay page source refuses private and metadata addresses like the live fetcher.
- **Failure behaviour verified:** all twelve scenarios. The work also found a real gap: public runs were created without a query (so a real run would have failed with `query_not_approved`), fixed by planning the query at creation.
- **Commands run and results:** `make backend-verify` exit 0 (1948 passed, 1 live test deselected); Circle 0 validators passed.
- **Tests added or changed:** 14 replay tests; one skipped opt-in live test.
- **Generated artifacts checked:** the fixtures against their generator; OpenAPI unchanged.
- **Known limitations/open decisions:** **The live search and analysis evidence is pending** (hard stop, live provider). In replay mode with no matching fixture a run finds nothing, which is honest but means the hosted demo shows no discovery results until fixtures for real projects exist or a live run is authorised.
- **Commit/PR:** `feat: add discovery replay fixtures, scenario tests, and the live evidence procedure`
- **Next task may rely on:** replay providers and the fixtures for any discovery test.
- **AI assistance used:** Designed and wrote the generator, fixtures, and tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-100 Central rate limits and abuse budgets

- **Task:** BE-100 — Central rate limits and abuse budgets.
- **Outcome delivered:** An atomic sliding-window Redis limiter, a central policy table with a completeness test, reviewer read and write budgets, a shared Q&A provider budget, and proven fail-closed behaviour.
- **Files changed:** `services/platform/src/shaidago/shared/{ratelimit,config}.py`, `src/shaidago/api/{rate_policy,reviewer_auth}.py`, `src/shaidago/api/v1/project_questions.py`, tests (`test_rate_limits_redis.py`, `test_rate_limits_api.py`), `.env.example`, `docs/BACKEND_BUILD_ORDER.md`.
- **Schema/contract changes:** None. The Q&A limiter key changed shape (`sg:rl:qa:client:` and `sg:rl:qa:global`); old keys simply expire.
- **Security/privacy impact:** Keys hold only pseudonymous or internal identifiers; no raw address or code. Every policy fails closed.
- **Failure behaviour verified:** see the build order note.
- **Commands run and results:** `make backend-verify` exit 0 (1957 passed).
- **Tests added or changed:** 6 Redis integration and 3 API tests.
- **Generated artifacts checked:** OpenAPI unchanged.
- **Known limitations/open decisions:** The reviewer budgets are skipped when no limiter is wired, which happens only in tests (the running service always wires one). The default reviewer budgets (600 reads and 120 writes per minute) are guesses to be tuned with real use. Progressive backoff for sign-in and handle verification remains the earlier per-pair and per-handle design.
- **Commit/PR:** `feat: add an atomic sliding-window limiter, reviewer budgets, and a rate-limit policy table`
- **Next task may rely on:** the policy table and limiter for any new route.
- **AI assistance used:** Designed and wrote the limiter, policy table, and tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-101 Cache and data-leak audit

- **Task:** BE-101 — Cache and data-leak audit.
- **Outcome delivered:** A cache-policy middleware with a four-path public allowlist, plus tests that enumerate every route and prove private responses are `no-store`.
- **Files changed:** `services/platform/src/shaidago/api/{cache_policy,app}.py`, tests (`tests/unit/api/test_cache_policy.py`, `tests/integration/test_cache_audit.py`), `docs/BACKEND_BUILD_ORDER.md`.
- **Schema/contract changes:** None (responses already had explicit headers; the middleware is a backstop).
- **Security/privacy impact:** A private response cannot leave with a public cache header even if a route is written wrongly.
- **Failure behaviour verified:** see the build order note.
- **Commands run and results:** `make backend-verify` exit 0 (1974 passed).
- **Tests added or changed:** 14 unit and 3 integration tests.
- **Generated artifacts checked:** OpenAPI unchanged.
- **Known limitations/open decisions:** The BFF and any CDN must still honour these headers; that boundary is the frontend's and Circle 11's to prove. The allowlist is a regex table that must be updated if a public route is added.
- **Commit/PR:** `feat: enforce an explicit cache policy on every response`
- **Next task may rely on:** the allowlist as the single list of cacheable routes.
- **AI assistance used:** Designed and wrote the middleware and tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-102 Contract fuzzing and public projection proof

- **Task:** BE-102 — Contract fuzzing and public projection proof.
- **Outcome delivered:** Authenticated reviewer contract fuzzing and a composed canary proof that private data never reaches public, tracking, error, or log output.
- **Files changed:** `services/platform/tests/integration/{test_schemathesis_reviewer,test_public_projection_proof}.py`, `src/shaidago/api/v1/reviewer_evidence.py` (documented `422`), `contracts/openapi.json`, `docs/BACKEND_BUILD_ORDER.md`.
- **Schema/contract changes:** One documented status added to one operation.
- **Security/privacy impact:** Proof only; no behaviour change beyond the documented status.
- **Failure behaviour verified:** see the build order note.
- **Commands run and results:** `make backend-verify` exit 0.
- **Tests added or changed:** 1 fuzz test (20 operations) and 2 proof tests.
- **Generated artifacts checked:** `contracts/openapi.json` regenerated.
- **Known limitations/open decisions:** The fuzzer runs 25 examples per operation to keep the suite fast; a longer run (`max_examples` raised) is a manual option. Multipart duplicate-name cases are generated only where the schema describes them (report submission is covered by its own adversarial tests).
- **Commit/PR:** `test: fuzz the reviewer API and prove private canaries never surface publicly`
- **Next task may rely on:** the canary world helper for any later leak test.
- **AI assistance used:** Designed and wrote the fuzz and proof tests.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-103 Concurrency and failure-injection suite

- **Task:** BE-103 — Concurrency and failure-injection suite.
- **Outcome delivered:** A resilience suite, a serialised migration runner, and a stable 503 for an unavailable key version.
- **Files changed:** `services/platform/migrations/env.py`, `src/shaidago/api/errors.py`, `tests/integration/test_resilience.py`, `docs/BACKEND_BUILD_ORDER.md`.
- **Schema/contract changes:** None.
- **Security/privacy impact:** A key-version outage no longer surfaces as an unhandled error; nothing partial is written.
- **Failure behaviour verified:** see the build order note. The concurrent-migration case failed before the fix (two of three runners errored) and passes after.
- **Commands run and results:** `make backend-verify` exit 0 (1985 passed).
- **Tests added or changed:** 8 integration tests.
- **Generated artifacts checked:** OpenAPI unchanged.
- **Known limitations/open decisions:** Migration contention is tested across processes (Alembic's context is process-global, so threads are not a valid model). A real client disconnect mid-multipart was not simulated over ASGI. Timeout of Redis during a request is covered by making the limiter raise, not by a real network stall.
- **Commit/PR:** `test: add concurrency and failure-injection tests and serialise migrations`
- **Next task may rely on:** a single advisory-locked migration path (the pre-deploy step in Circle 11).
- **AI assistance used:** Designed and wrote the suite and fixes.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-104 Performance and resource budgets

- **Task:** BE-104 — Performance and resource budgets.
- **Outcome delivered:** Declared budgets, a scaled-data budget test, and preserved measurements.
- **Files changed:** `docs/PERFORMANCE_BUDGETS.md`, `docs/evidence/BE-104-performance.md`, `services/platform/tests/integration/test_performance_budgets.py`, `docs/BACKEND_BUILD_ORDER.md`.
- **Schema/contract changes:** None.
- **Security/privacy impact:** None.
- **Failure behaviour verified:** Not applicable; the test caught nothing to fix.
- **Commands run and results:** `make backend-verify` exit 0 (1990 passed).
- **Tests added or changed:** 5 tests.
- **Generated artifacts checked:** OpenAPI unchanged.
- **Known limitations/open decisions:** Latency is in-process (no network); the budgets are generous by design; production Argon2 timing must be repeated on the Railway instance size.
- **Commit/PR:** `test: declare performance budgets and measure them on scaled data`
- **Next task may rely on:** the budget table as the reference for Circle 11 sizing.
- **AI assistance used:** Wrote the budgets, test, and evidence note.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-105 Security scanning and dependency review

- **Task:** BE-105 — Security scanning and dependency review.
- **Outcome delivered:** Scanners run and triaged, a narrow secret-scan allowlist, and a security workflow.
- **Files changed:** `.gitleaks.toml`, `.github/workflows/security.yml`, `docs/SECURITY_SCAN_TRIAGE.md`, `docs/BACKEND_BUILD_ORDER.md`.
- **Schema/contract changes:** None.
- **Security/privacy impact:** Confirms no committed secret; documents the scan gaps.
- **Failure behaviour verified:** Not applicable.
- **Commands run and results:** `gitleaks detect` (6 findings, then 0 with the allowlist), `uvx semgrep@1.177.0` (0 findings, 9 partial parses), `make backend-verify` (Bandit, pip-audit, Ruff clean).
- **Tests added or changed:** None.
- **Generated artifacts checked:** The workflow YAML parses.
- **Known limitations/open decisions:** **CodeQL and Trivy are pending** and are open items of the Circle 10 gate. Docker images for Gitleaks were pulled from a public registry to run the scan. The allowlist would hide the same placeholder wherever it appeared, so a real key must never look like it.
- **Commit/PR:** `ci: add secret, static-analysis, and CodeQL scanning with a triage record`
- **Next task may rely on:** the security workflow, where the Trivy job for BE-110 belongs.
- **AI assistance used:** Ran the scanners, triaged the findings, and wrote the workflow and record.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-106 Retention, deletion, and operational privacy

- **Task:** BE-106 — Retention, deletion, and operational privacy.
- **Outcome delivered:** An operator retention command with purges, crypto-shredding, and an access-review list, and a retention policy document with explicit limitations.
- **Files changed:** `services/platform/src/shaidago/retention/{__init__,purge,__main__}.py`, `Makefile`, `tests/integration/test_retention.py`, `docs/RETENTION.md`, `docs/BACKEND_BUILD_ORDER.md`.
- **Schema/contract changes:** None.
- **Security/privacy impact:** Shredding makes private content unreadable by destroying its keys; history and audit stay; nothing runs from the API.
- **Failure behaviour verified:** see the build order note.
- **Commands run and results:** `make backend-verify`; Circle 0 validators.
- **Tests added or changed:** 5 integration tests.
- **Generated artifacts checked:** OpenAPI unchanged.
- **Known limitations/open decisions:** No compliance claim; report and audit retention periods, backup configuration, and scheduling of the purge are open. Report-scoped discovery runs are not deleted (the run guard forbids direct deletes and they hold no private text). Shredding needs the object store credentials to delete evidence objects.
- **Commit/PR:** `feat: add retention purges, report crypto-shredding, and a retention policy`
- **Next task may rely on:** the retention command for the runbooks in BE-113.
- **AI assistance used:** Designed and wrote the module, command, tests, and policy.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-110 Production container and BE-113 Operational runbooks

- **Task:** BE-110 — Production container; BE-113 — Operational runbooks.
- **Outcome delivered:** A verified non-root multi-stage image for the API, worker, and migration job, a container verification script, a Trivy CI job, and eleven runbooks.
- **Files changed:** `services/platform/Dockerfile`, `.dockerignore`, `scripts/verify-container.sh`, `services/platform/src/shaidago/api/serve.py`, `services/platform/migrations/env.py`, `tests/unit/api/test_serve.py`, `.github/workflows/security.yml`, `docs/RUNBOOKS.md`, `docs/DEPLOYMENT.md`, `railway/*.railway.json`, `docs/BACKEND_BUILD_ORDER.md`.
- **Schema/contract changes:** None. The migration environment now requires only `DATABASE_URL`.
- **Security/privacy impact:** The image carries no credentials or build tooling and runs unprivileged on a read-only filesystem; the migration job no longer needs application secrets.
- **Failure behaviour verified:** see the build order note.
- **Commands run and results:** `TRIVY=1 scripts/verify-container.sh` all PASS; `make backend-verify` exit 0 (1996 passed).
- **Tests added or changed:** 1 unit test (dual-stack socket); the container script is the image test.
- **Generated artifacts checked:** OpenAPI unchanged.
- **Known limitations/open decisions:** The image was built and verified for the developer's architecture (arm64); an amd64 build (Railway) was not built locally. The runbook Railway commands are exercised in BE-114 only. Trivy was run from a public image pulled for the purpose.
- **Commit/PR:** `build: add the verified production container, runbooks, and Railway service configuration`
- **Next task may rely on:** the image, `railway/*.railway.json`, and `docs/DEPLOYMENT.md`.
- **AI assistance used:** Wrote the Dockerfile, script, entry point, and runbooks; found and fixed the four defects the build exposed.
- **Prompt summary:** Unattended backend build loop.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-111, BE-112, BE-114 Railway staging, migration gating, rotation and rollback

- **Task:** BE-111 — Railway services and environment matrix; BE-112 — Pre-deploy migration and compatibility; BE-114 — Staging smoke and rollback exercise (partial).
- **Outcome delivered:** A Railway staging environment with private services from the verified image, ordered migration-then-deploy, a rotation and a rollback exercised, and a smoke script ready to run.
- **Files changed:** `docs/DEPLOYMENT.md`, `railway/*.railway.json`, `scripts/railway_staging_variables.py`, `scripts/staging_smoke.py`, `docs/evidence/BE-114-staging-smoke.md`, `docs/BACKEND_BUILD_ORDER.md`.
- **Schema/contract changes:** None.
- **Security/privacy impact:** Hosted resources were created in the maintainer's Railway account with their standing authorisation for the Railway deploy; no public domain exists; no live provider key was used; generated secrets were never printed or committed; the owner credential exists only on the one-shot migration service.
- **Failure behaviour verified:** deploy order, rotation, and rollback on staging; the migration advisory lock and readiness revision check locally.
- **Commands run and results:** see the evidence record; `make backend-verify` (1996 passed) before the deploy.
- **Tests added or changed:** `scripts/staging_smoke.py` (not yet run on staging).
- **Generated artifacts checked:** None.
- **Known limitations/open decisions:** **The staging smoke journey is pending** a registered Railway SSH key (an account change I did not make). The staging environment is a running paid resource until the maintainer removes it. The variables script rotates every secret if re-run. The image was built for the developer's architecture and Railway built its own from the same Dockerfile.
- **Commit/PR:** `build: deploy the backend to Railway staging with gated migrations, rotation, and rollback evidence`
- **Next task may rely on:** the staging environment, the deploy order, and the evidence record for the release gate.
- **AI assistance used:** Provisioned staging with the Railway CLI, exercised rotation and rollback, wrote the smoke script and records.
- **Prompt summary:** Unattended backend build loop; maintainer authorised the Railway deploy.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-120 Canonical backend verification

- **Task:** BE-120 — Canonical backend verification.
- **Outcome delivered:** The local and hosted backend gates share `make backend-verify`; it checks the frozen environment, formatting, lint, strict types, all deterministic test layers with an enforced backend branch-coverage floor, OpenAPI drift, static and dependency security, while the separate container target retains the image/runtime/Trivy proof.
- **Files changed:** `Makefile`, `.github/workflows/backend.yml`, `services/platform/README.md`, `docs/BACKEND_BUILD_ORDER.md`, `docs/AI_BUILD_LOG.md`.
- **Schema/contract changes:** None.
- **Security/privacy impact:** The gate excludes live provider tests, runs public/private leak and role-boundary suites, fails below 85% total branch coverage, audits dependencies, and scans code; it introduces no data flow.
- **Failure behaviour verified:** Every stage stops the gate on a non-zero result; contract drift, a coverage result below 85%, a known dependency vulnerability, or a deterministic test failure blocks the build.
- **Commands run and results:** `make backend-verify` exited 0: frozen sync, Ruff format and lint, Pyright (0 errors), 1,997 deterministic tests passed with one live test deselected and 94.03% total branch coverage, OpenAPI check passed, Bandit passed, and `pip-audit` found no known vulnerability.
- **Tests added or changed:** No behaviour tests; the full suite now runs with coverage measurement and an 85% failure threshold.
- **Generated artifacts checked:** `make openapi-check` passed inside the canonical gate.
- **Known limitations/open decisions:** The branch has not been published, so its first GitHub CI run is pending. The test suite proves empty-to-head migrations in an isolated database; the developer's persistent local volumes were not destroyed merely to call the surrounding services clean.
- **Commit/PR:** `ci: enforce the canonical backend release gate`.
- **Next task may rely on:** one local command and one CI command covering every deterministic backend layer, with container verification remaining explicit because it needs Docker.
- **AI assistance used:** Completed the in-progress gate, added the measurable coverage floor, aligned CI with the canonical target, ran it, and recorded the remaining hosted evidence honestly.
- **Prompt summary:** Continue Circle 12 from the existing branch and in-progress work.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-121 Frontend contract package

- **Task:** BE-121 — Frontend contract package.
- **Outcome delivered:** A frozen frontend handoff: explicit stable operation IDs, a generated and drift-checked operation/response fixture manifest, named MSW-ready UI states, and one document for every browser/BFF semantic not expressible in OpenAPI.
- **Files changed:** `services/platform/src/shaidago/api/{health,openapi}.py`, every route module under `api/v1`, `services/platform/tests/contract/test_openapi.py`, `contracts/{openapi,frontend-fixtures}.json`, `scripts/render_frontend_contract.py`, `Makefile`, `docs/{API,FRONTEND_BACKEND_CONTRACT,BACKEND_BUILD_ORDER,AI_BUILD_LOG}.md`, `README.md`, `services/platform/README.md`.
- **Schema/contract changes:** All 37 existing operations receive explicit stable IDs; their paths, methods, request/response schemas, and runtime behaviour are unchanged. The frontend fixture schema is version 1.
- **Security/privacy impact:** The handoff makes BFF-only tokens, one-time reporter credentials, no-store surfaces, public cache boundaries, partial uploads, private discovery, and citation trust states explicit. Fixtures are visibly synthetic and contain no usable secret or real report.
- **Failure behaviour verified:** Contract tests reject a missing, invalid, or duplicate operation ID; reject a fixture manifest missing any operation or documented response status; and the renderer's check mode fails on drift.
- **Commands run and results:** Targeted Ruff and Pyright passed; 7 targeted contract tests passed; `make openapi-generate`; `python3 scripts/render_frontend_contract.py`; `make backend-verify` exited 0 with 1,999 deterministic tests passed, one live test deselected, 94.03% branch coverage, both generated-contract drift checks, Bandit, and `pip-audit`; all six Circle 0 validators passed.
- **Tests added or changed:** Two contract tests enforce explicit IDs, complete response-fixture coverage, all eight named state fixtures, and generated-file drift.
- **Generated artifacts checked:** `contracts/openapi.json` and `contracts/frontend-fixtures.json` are generated from executable API schemas and checked by `make backend-verify`.
- **Known limitations/open decisions:** The fixture copy is transport-oriented synthetic English, not reviewed locale UI copy. The frontend still owns its accessible presentation and the review status of translations. There is no deployed frontend consumer requiring an operation-ID deprecation window.
- **Commit/PR:** `feat: freeze the frontend backend contract`.
- **Next task may rely on:** generated types from stable operation IDs, exact transport examples for every response status, and documented handling for privacy, retries, polling, and trust states without inspecting backend internals.
- **AI assistance used:** Corrected the inherited generated-ID approach to comply with ADR-0007, built the fixture generator and enforcement, and wrote the frontend handoff semantics.
- **Prompt summary:** Continue Circle 12 from the existing branch and in-progress work.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — BE-122 Final backend evidence review

- **Task:** BE-122 — Final backend evidence review.
- **Outcome delivered:** A reproducible final evidence record, an implemented privacy/safety summary, an explicit public-schema private-field denylist, refreshed repository status/limitations, and a precise list of human/hosted release blockers.
- **Files changed:** `services/platform/tests/contract/test_openapi.py`, `docs/{PRIVACY_AND_SAFETY,THREAT_MODEL,README,BACKEND_BUILD_ORDER,AI_BUILD_LOG}.md`, `docs/evidence/BE-122-final-backend-review.md`, `README.md`.
- **Schema/contract changes:** None. A test now recursively inspects the successful public catalogue, Q&A, and public-discovery schemas and rejects private field names.
- **Security/privacy impact:** Whole-history and tracked-file review found no real secret, contact, report, signed URL, raw credential, or unlabelled private fixture. The document separates implemented prototype controls from the human, provider, legal, and operational gates that still prohibit real data.
- **Failure behaviour verified:** Public schemas fail the contract test if a forbidden private field becomes reachable. The existing runtime canaries prove private values remain absent from public/tracking/error responses and logs; cache auditing proves every documented route declares a policy.
- **Commands run and results:** Gitleaks scanned 83 commits/about 3.67 MB with redaction and found no leak; candidate-pattern inventory was reviewed by file; 15 targeted contract/public-shape/public-canary/cache tests passed after rerunning with the required local environment; `make backend-verify` exited 0 with 2,000 tests passed, one live test deselected, 94.03% branch coverage, generated artifacts clean, Bandit clean, and no known audited dependency vulnerability; all six Circle 0 validators passed.
- **Tests added or changed:** One recursive public-success-schema denylist test covering nine public operations; existing runtime public-shape, canary, and cache tests were rerun together.
- **Generated artifacts checked:** OpenAPI and frontend fixtures remain drift-free; source-register and controlled-vocabulary rendered documents match their JSON sources.
- **Known limitations/open decisions:** BE-122 remains blocked on a named/date-stamped human audit of all six projects, current source passages, public wording, and reuse terms. Locale human review, live providers, hosted CI, and the complete staging smoke also remain open; production and real report data remain prohibited.
- **Commit/PR:** `docs: record the final backend privacy and evidence review`.
- **Next task may rely on:** the automated release evidence and exact blocker list, but may not claim the backend final gate or production readiness closed.
- **AI assistance used:** Ran the redacted repository/history review, classified synthetic candidates, added the public-schema guard, consolidated privacy evidence, and refused to substitute AI review for the required manual source audit.
- **Prompt summary:** Continue Circle 12 from the existing branch and in-progress work.
- **Human review:** Reviewed and merged by the maintainer (Aniekan Winner Anietie) on 2026-09-19; the work reached `main` through its reviewed pull request.

## 2026-09-19 — Groq replaces OpenAI, and the live provider evidence (BE-082, BE-085, BE-097)

- **Task:** BE-082, BE-085, BE-097 — replace the unusable live language provider and record the live evidence the unattended build could not.
- **Outcome delivered:** `GroqLanguageModel` (OpenAI-compatible Chat Completions) for grounded answers and discovery analysis, ADR-0009, live Brave and Groq runs, the maintainer's locale review recorded, and the live-evaluation evidence.
- **Files changed:** `retrieval/groq.py` (replacing `openai.py`), `discovery/analysis.py`, `discovery/providers.py`, `api/main.py`, `shared/config.py`, `retrieval/evaluation.py`, tests, `.env.example`, `docs/decisions/0009-*`, `docs/evidence/BE-085-live-evaluation.md`, `docs/evidence/BE-097-live-evidence.md`, `data/qa-evaluation/golden-v1.json`.
- **Schema/contract changes:** None to the HTTP contract. Environment: `GROQ_API_KEY`, `GROQ_QA_MODEL`, `GROQ_DISCOVERY_MODEL`, `GROQ_BASE_URL` replace the OpenAI variables.
- **Security/privacy impact:** No new destination beyond the provider already allowlisted. The request offers no tools and is deterministic; refusals, tool calls and truncation are classified and fail closed; no prompt or upstream body enters an exception.
- **Failure behaviour verified:** Two defects only a live run revealed: Groq's constrained decoder rejects `pattern` in a schema (`json_validate_failed`), so the wire schema drops it while the same Pydantic models still enforce it; and the analysis token cap of 2,500 truncated a five-source run (now 6,000). Both live pipeline runs ended `needs_review` because our validator rejected the model's analysis, which is the intended fail-closed behaviour.
- **Commands run and results:** live search 10 URLs; live pipeline runs 10/9/7 and 10/7/6 (found/fetched/analysed); live evaluation 4/36 (`gpt-oss-20b`) and 6/36 (`gpt-oss-120b`), 25 of 36 rate limited in each; `make backend-verify` exit 0.
- **Tests added or changed:** adapter tests ported to the chat-completions shape, including truncation, refusal and tool-call cases and a wire-schema test that a pattern violation still fails closed; config and evaluation tests updated.
- **Generated artifacts checked:** OpenAPI and frontend fixtures unchanged.
- **Known limitations/open decisions:** The live model is weak against the golden corpus and the free tier rate-limits hard, so the demo keeps replay as its default. The locale review is the maintainer's alone. Provider-side retention and terms are unreviewed. The maintainer's `.env` had a `GEMINI_API_KEY==…` typo (double `=`) that broke shell sourcing; it and two malformed lines were corrected locally.
- **Commit/PR:** `feat: replace OpenAI with Groq and record the live provider evidence`, `test: assert the recorded locale review instead of a pending one`.
- **Next task may rely on:** a working live language path and honest evidence of its quality.
- **AI assistance used:** Wrote the adapter, migrated its callers and tests, ran the live evaluation and pipeline runs, diagnosed the two live defects, and recorded the evidence without overstating it.
- **Prompt summary:** Use the Groq key instead of OpenAI; a Brave key was supplied; the maintainer stated they reviewed the Hausa, Igbo and Yoruba copy themselves.
- **Human review:** The maintainer reviewed this branch and merged it on 2026-09-20 (pull request #16), as they stated when asking for this record. The locale review itself is the maintainer's own, self-reported; no independent reviewer exists.

## 2026-09-19 — Public evidence path fixes found while staging (BE-041, BE-043 follow-up)

- **Task:** BE-041/BE-043 follow-up — make the seeded, cited facts actually visible, and make the seed runnable in a container and on staging.
- **Outcome delivered:** Cited facts are public with the honest state `awaiting_verification`; public citations expose the approved `source_version_id`; the seed approves hash-verified versions with a recorded note; the seed can target staging only when explicitly flagged; the image ships the register validator.
- **Files changed:** migrations `0025_public_awaiting`, `0026_citation_version_id`; `seed/apply.py`, `seed/plan.py`; `api/v1/projects.py`, `projects/catalogue.py`, `review/publication.py`; `services/platform/Dockerfile`, `.dockerignore`; tests and snapshots; OpenAPI and frontend fixtures.
- **Schema/contract changes:** `ck_project_facts_public_complete` no longer forbids `awaiting_verification`; the two public citation views gain `source_version_id`; `VerificationState` and `CitationOut` gain a value and a field. Both migrations round-trip.
- **Security/privacy impact:** A version id is not private: the same row already publishes the source, URL, passage and retrieval time. The citation trigger still requires an approved version, and a test proves removing the evidence makes the fact unpublishable. `SEED_ALLOW_DEPLOYED=1` plus `APP_ENV=staging` is the only deployed seed target; production is refused with or without the flag.
- **Failure behaviour verified:** Before this, every seeded version was `pending` and every fact `draft`, so public pages showed no facts and nothing in the product could approve a version. The brief requires showing awaiting-verification claims, but a database constraint forbade it.
- **Commands run and results:** `make backend-verify` exit 0 after each stage; staging seeded with 3 projects, 7 facts and 11 citations.
- **Tests added or changed:** seed, public shape snapshot, sources view, public API, publication and configured-app tests; new tests for the staging flag and the approval note.
- **Generated artifacts checked:** `contracts/openapi.json` and `contracts/frontend-fixtures.json` regenerated.
- **Known limitations/open decisions:** Approving a seeded version means only that the quoted text is what the source said, because the register validator re-checks every passage hash; it says nothing about whether the claim is true, which the fact's state carries.
- **Commit/PR:** the maintainer committed the migrations and code themselves as `3085157`; the remaining changes are in later commits on the same branch.
- **Next task may rely on:** a public page that shows cited, honestly labelled facts and a reviewer flow that can cite them.
- **AI assistance used:** Found the invisibility by inspecting a real public page, traced it through the constraint, view and DTO, and wrote both migrations and their tests.
- **Prompt summary:** Review and clear the backend's open items.
- **Human review:** The maintainer committed and pushed the migration and code changes themselves (`3085157`); the rest of this branch is pending review.

## 2026-09-20 — Local embeddings, the fictional smoke fixture, and the staging smoke (BE-081, BE-114)

- **Task:** BE-081 and BE-114 — give retrieval real embeddings without a provider, and run the complete fictional journey on hosted staging.
- **Outcome delivered:** Local embeddings with FastEmbed and `multilingual-e5-small` int8 (ADR-0010), live in the question path; a fictional smoke fixture; the staging smoke at 24 of 24; request-ID propagation into worker messages (BE-023).
- **Files changed:** `retrieval/local_embeddings.py`, `retrieval/fetch_embedding_model.py`, `retrieval/generate_embeddings.py`, `retrieval/questions.py`, `retrieval/embeddings.py`, `seed/staging_fixture.py`, `worker/envelope.py`, `worker/broker.py`, `worker/queue.py`, migration `0027_embedding_384`, `Dockerfile`, `Makefile`, `pyproject.toml` and `uv.lock`, `scripts/staging_smoke.py`, ADR-0010, evidence files, `docs/RUNBOOKS.md`, `AGENTS.md`, `CLAUDE.md`, `README.md`.
- **Schema/contract changes:** `app.source_chunks.embedding` is `vector(384)` (was 1536); vectors cleared, index and view rebuilt. Job envelope gains an optional validated request ID. No HTTP contract change.
- **Security/privacy impact:** A question is embedded in-process and goes to no provider. The model download is pinned to one revision and all five files are SHA-256 verified; a symlink is an integrity failure. The image runs offline (`HF_HUB_OFFLINE=1`). ONNX Runtime telemetry is switched off. The fictional fixture is labelled fictional in every string, uses `.example`, carries its own approval note, and is refused wherever the real seed is refused.
- **Failure behaviour verified:** A missing or broken model degrades readiness and falls back to keyword retrieval; four per-request failure codes fall back and still answer; a burst beyond eight in flight is refused as busy; a timed-out call keeps counting against the cap. The first attempt, with the 2.2 GB `multilingual-e5-large`, was killed for memory in a restart loop on Railway (limit 1,024 MB). Smaller siblings were measured, and the 118 MB model matched it on the probe.
- **Commands run and results:** model comparison probe (3/2/2/1 for small and large; base 3/2/2/3 but too large); in the built image with `--network none --memory 1g`, 200 queries peaked at 0.53 GB; on staging `embedding: ok`, memory peak 849 MB of 1,024 MB; smoke 24 of 24; final `make backend-verify` exit 0 with 2,097 tests, 93.88% coverage, `pip-audit` clean.
- **Tests added or changed:** adapter, download-integrity, loader-registration, config, question-wiring (hybrid, no-overlap recall, four fallbacks), migration round trip, fixture and seed tests, and an opt-in real-model quality guard. Two tests that encoded the old behaviour were corrected, and a leak of the developer's `.env` into tests was fixed by making the test environment explicit.
- **Generated artifacts checked:** OpenAPI and frontend fixtures unchanged by this stage.
- **Known limitations/open decisions:** The probe is three questions per language, so it cannot separate the small model from the large one; Yoruba at 1 of 3 is weak, and the base model (3 of 3) does not fit the memory limit. Retrieval always returns nearest neighbours, with no similarity floor. Replay fixtures were recorded under keyword retrieval. Hosted memory headroom is 17% at peak. `railway ssh` was not exercised. Circle 5's BFF `Set-Cookie` gap belongs to the frontend.
- **Commit/PR:** `feat: run embeddings locally with FastEmbed and multilingual-e5-large`, `docs: align the rulebooks with the accepted decisions and fix a dead link`, `feat: switch local embeddings to multilingual-e5-small to fit the hosted limit`, `feat: seed a fictional fixture project for the staging smoke journey`.
- **Next task may rely on:** hybrid retrieval in the live path, a complete and honest staging record, and the frontend contract unchanged.
- **AI assistance used:** Discovered that query embedding never existed, measured the candidate models rather than assuming, deployed to staging, diagnosed the memory kill from platform metrics, downgraded the two databases before rewriting an applied migration, and recorded what went wrong. Its own informal Hausa, Igbo and Yoruba test sentences are unreviewed and are labelled as such.
- **Prompt summary:** Use FastEmbed for embeddings instead of a paid provider; clear the backend's open items on a new branch and use Railway.
- **Human review:** The maintainer reviewed this branch and merged it on 2026-09-20 (pull request #16), as they stated when asking for this record.

## 2026-09-20 — FE-000 frontend scope and authority reconciliation

- **Task:** FE-000 — Reconcile frontend scope and authority.
- **Outcome delivered:** A frontend traceability contract maps all five journeys, 16 must-have capabilities, Product Brief acceptance criteria, routes, data classes, cache/render rules, backend operations, enforcement boundaries, non-goals, and proof owners before UI or BFF implementation begins.
- **Files changed:** `PRODUCT.md`, `docs/FRONTEND_REQUIREMENTS_TRACEABILITY.md`, `docs/FRONTEND_BUILD_ORDER.md`, `docs/README.md`, `scripts/validate_frontend_traceability.py`, and this log.
- **Contract/schema impact:** No generated contract or runtime schema changed. The register consumes the committed OpenAPI `0.0.0` operation IDs and frontend fixture schema `1` without inspecting backend implementation.
- **Security/privacy impact:** Public, public-after-review, private, one-time-secret, and operational-only fields now have explicit browser/cache handling. The BFF is explicitly excluded as sole domain, authorisation, verification, or publication authority.
- **Accessibility/localisation impact:** Ownership is assigned for keyboard, focus, error association, text-not-colour status, WCAG 2.2 AA, four-locale parity, honest translation status, and source-language preservation; no translated copy or accessibility implementation is claimed yet.
- **Verification:** `python3 scripts/validate_frontend_traceability.py --self-test` validates all frontend task references, all 35 non-health OpenAPI operations, five journeys, 16 capabilities, 29 acceptance criteria, five data classes, eight non-goals, and three negative mutations. JSON/OpenAPI parsing, local Markdown links, Python compilation, whitespace, and staged-diff checks are run before commit.
- **Human review:** The maintainer directed frontend work from the completed backend baseline. The mapping remains reviewable in its task commit; no visual direction or fluent language review has been approved yet.
- **Result:** FE-001 may define the detailed route/journey matrix without inventing backend fields. The evidence register's unresolved human-audit gaps remain visible and are not misrepresented as frontend work.
- **AI assistance used:** Reconciled product, frontend build order, OpenAPI, controlled vocabulary, source register, and backend handoff into one validated authority map; updated stale product evidence wording to match repository reality.
- **Prompt summary:** Create a frontend branch from the maintainer's in-progress backend branch and begin the frontend build order while leaving backend gate-closing work out of scope.

## 2026-09-20 — FE-001 route and user-journey inventory

- **Task:** FE-001 — Route and user-journey inventory.
- **Outcome delivered:** All twelve required routes and seven complete journey sequences now define audience, job, primary action, handoff, backend operations, rendering/cache/authentication, locale/canonical/robots policy, material states, and interruption recovery.
- **Files changed:** `docs/FRONTEND_ROUTE_MATRIX.md`, `docs/FRONTEND_BUILD_ORDER.md`, `docs/README.md`, `scripts/validate_frontend_route_matrix.py`, and this log.
- **Contract/schema impact:** No runtime contract changed. The matrix covers every non-health OpenAPI operation and keeps Source Scout embedded in project/reviewer detail as accepted.
- **Security/privacy impact:** Private/one-time credentials are excluded from paths, queries, canonical metadata, prefetch, and offline caches. Reviewer and reporter routes are dynamic, no-store, and noindex; hidden/unknown public records retain safe not-found handling.
- **Accessibility/localisation impact:** Each route names locale source, no-JavaScript/public behavior, keyboard/error states, and handoff/focus responsibility. Actual UI and translations remain future tasks.
- **Verification:** `python3 scripts/validate_frontend_route_matrix.py --self-test` checks all twelve route IDs/patterns, all 35 non-health operations, seven journey rows, the exit gate, and negative cases for missing route, secret-in-path, and missing operation.
- **Human review:** The route plan follows the maintainer-approved product and backend handoff; interaction and visual presentation remain open to review.
- **Result:** FE-002 can define shared state fixtures per surface without inventing routes or navigation behavior.
- **AI assistance used:** Converted the implementation plan and backend handoff into an App Router ownership and recovery matrix with explicit public/private boundaries.
- **Prompt summary:** Continue the frontend build order from the maintainer's updated backend branch.

## 2026-09-20 — FE-002 frontend state and fixture matrices

- **Task:** FE-002 — Complete state matrices.
- **Outcome delivered:** A stable fixture namespace and 34-state vocabulary now cover 304 explicitly expanded UI fixtures across 28 public, Q&A, reporting, tracking, handle, reviewer, publication, evidence, and Source Scout surfaces.
- **Files changed:** `docs/FRONTEND_STATE_MATRIX.md`, `docs/FRONTEND_BUILD_ORDER.md`, `docs/README.md`, `scripts/validate_frontend_state_matrix.py`, and this log.
- **Contract/schema impact:** Generated transport fixtures remain unchanged. UI fixtures compose their eight documented transport scenarios with browser, locale, cache, connectivity, and interaction context.
- **Security/privacy impact:** Public cached-offline and private unavailable-offline behavior are distinct. Unknown mutation completion preserves idempotency; credentials/private data never gain a cache fallback; session, CSRF, Origin, forbidden, conflict, and provider failures have separate recovery.
- **Accessibility/localisation impact:** State rules cover focus, busy semantics, useful announcements, field-error association, text-not-colour status, long/min/max content, partial translations, machine-assisted labels, no-JavaScript public baselines, and safe locale preservation.
- **Verification:** `python3 scripts/validate_frontend_state_matrix.py --self-test` validates the exact 34-state catalogue, at least 180 expanded fixtures (304 present), all 28 surfaces, all eight transport scenarios, the seven-item exit gate, and three negative mutations.
- **Human review:** The maintainer directed execution of the frontend order. Visible copy, visual treatment, and fluent-language review remain future human decisions.
- **Result:** FE-003 may size content fixtures against stable state names; later component and E2E tests must consume these names rather than invent local error labels.
- **AI assistance used:** Separated materially different recovery paths and converted backend response semantics into implementation-ready UI fixture contracts.
- **Prompt summary:** Continue the frontend Circle 0 inventory from the updated backend handoff.

## 2026-09-20 — Frontend/BFF unattended build-loop command

- **Task:** Repository developer workflow — frontend/BFF loop aligned with the backend loop.
- **User outcome delivered:** A repeatable command now drives eligible frontend tasks through the accepted frontend build order with one coherent task packet, implementation, proof, record, and commit lifecycle.
- **Routes/components changed:** No runtime route, component, BFF handler, or client bundle changed; added `.claude/commands/frontend-build-loop.md`.
- **Backend operations/contract version:** No contract changed. The command requires the committed OpenAPI, frontend fixture, controlled-vocabulary, and frontend-backend handoff contracts before an affected task begins.
- **Public/private data handled:** No data flow changed. The loop explicitly preserves browser-to-Next-only routing, server-only API access, purpose-built BFF handlers, no-store private handling, and prohibited sensitive browser/cache/log locations.
- **States implemented:** No product UI state changed. The workflow requires task packets to enumerate initial, loading, empty, success, stale, partial, validation, denied, rate-limited, offline, dependency-down, and recovery states as applicable.
- **Accessibility evidence:** No UI changed. The command requires semantic, focus, keyboard, assistive announcement, zoom, contrast, reduced-motion, locale-length, mobile, and screenshot evidence for relevant visible tasks.
- **Locales reviewed:** No message or translation changed. The workflow requires parity for `en`, `ha`, `ig`, and `yo` and prevents a claim of fluent human review without that review.
- **Performance/cache impact:** No runtime cache or bundle changed. The command requires public/private cache inspection, server/client boundary checks, and viewport/network evidence when a task affects them.
- **Commands run and results:** Inspected the current `CLAUDE.md`, backend loop command, frontend build order, documentation index, AI log, repository status, and recent commits. No planned frontend build command was run because no `apps/web` package exists yet.
- **Screenshots/traces/artifacts checked:** Reviewed the tracked backend loop and the frontend execution specification; no rendered surface exists to inspect.
- **Known limitations/open decisions:** Circle 1 remains human-directed. An unattended run must record FE-010 as blocked and may continue only with eligible non-visual work; Circle 4 and visible product surfaces wait for approval.
- **Commit/PR:** `docs: add the frontend build loop command`
- **Next task may rely on:** The frontend loop's task-selection, safety-boundary, validation, documentation, commit, blocked-task, and hard-stop rules.
- **AI assistance used:** Mirrored the proven backend loop structure, then adapted it to the frontend's Server Component/BFF boundary, state-matrix proof, four-locale requirements, and mandatory human visual-direction gate.
- **Prompt summary:** Create a frontend loop equivalent to the backend loop.
- **Human review:** the maintainer reviewed this work and merged it on 2026-09-20 (pull requests #17 to #22), as they stated when asking for this record. That review does not cover fluent Hausa, Igbo, or Yoruba review, screen-reader testing, or a live-API run; see the entry "Maintainer review of the merged frontend and backend work".

## 2026-09-20 — Frontend circle branch and commit naming rule

- **Task:** Repository developer workflow — frontend circle isolation and naming.
- **User outcome delivered:** Every frontend build-order circle now receives an outcome-named branch in the form `frontend/<circle-goal>`, while commits continue to describe their delivered outcome without roadmap labels, circle numbers, or task IDs.
- **Routes/components changed:** No runtime route, component, BFF handler, or client bundle changed. The active Circle 0 branch is `frontend/contract-inventory`.
- **Backend operations/contract version:** No backend operation or contract changed.
- **Public/private data handled:** No data flow changed.
- **States implemented:** No product UI state changed.
- **Accessibility evidence:** No UI changed.
- **Locales reviewed:** No message or translation changed.
- **Performance/cache impact:** No runtime cache or bundle changed.
- **Commands run and results:** Confirmed the previous branch was clean and created `frontend/contract-inventory` from its committed frontend baseline; no remote branch was modified.
- **Screenshots/traces/artifacts checked:** Reviewed the frontend loop's branch creation, task commit, and circle-transition rules; no rendered surface exists to inspect.
- **Known limitations/open decisions:** Existing `frontend-build` history remains preserved and unchanged. The frontend loop creates later circle branches only after the previous circle's recorded baseline exists.
- **Commit/PR:** `docs: standardise frontend work branches`
- **Next task may rely on:** Outcome-named, circle-isolated frontend branches and concise outcome-based commit subjects.
- **AI assistance used:** Added the requested branch/commit convention and moved the active Circle 0 checkout to its compliant branch without rewriting or deleting history.
- **Prompt summary:** Require a frontend branch per circle and exclude roadmap names from branch names and commits.
- **Human review:** the maintainer reviewed this work and merged it on 2026-09-20 (pull requests #17 to #22), as they stated when asking for this record. That review does not cover fluent Hausa, Igbo, or Yoruba review, screen-reader testing, or a live-API run; see the entry "Maintainer review of the merged frontend and backend work".

## 2026-09-20 — FE-003 content and range inventory

- **Task:** FE-003 — Content and range inventory.
- **User outcome delivered:** A deterministic, validated minimum/typical/maximum content contract now gives later frontend work safe layout fixtures for public projects/sources, four-language labels, private reporting, tracking, reviewer work, and Source Scout.
- **Routes/components changed:** No runtime route or component changed. Added `data/frontend-content-range-fixtures.json`, `docs/FRONTEND_CONTENT_RANGE_INVENTORY.md`, and `scripts/validate_frontend_content_ranges.py` for future directory, detail, source, report, tracking, reviewer, and discovery tests.
- **Backend operations/contract version:** No generated API contract changed; the inventory is constrained by OpenAPI `0.0.0`, frontend fixture schema `1`, and the documented handoff. It marks currency and reporter-visible tracking history as not exposed by the current public/tracking contracts rather than creating fields.
- **Public/private data handled:** Every fixture is marked synthetic and contains no source-register project/source/fact, report, allegation, identifier, contact value, tracking code, passphrase, session token, CSRF token, signed URL, or file bytes. Private form/reviewer entries are metadata-only local test inputs and never cacheable.
- **States implemented:** Size fixtures complement, but do not replace, the 304 stable UI state fixtures. The registry names minimum/typical/maximum cases for each shared surface and preserves distinct unavailable, validation, offline, and recovery states for later tests.
- **Accessibility evidence:** The inventory specifies long-label wrapping, explicit unknown/omitted values, text status, keyboard/error association, 200% zoom, reduced motion, mobile, and desktop evidence required when components consume a fixture.
- **Locales reviewed:** English is source-locale layout copy; Hausa, Igbo, and Yoruba long labels are explicitly marked machine-assisted and unreviewed. No fluent review or production safety copy is claimed.
- **Performance/cache impact:** No runtime bundle/cache changed. Recipes are deterministic metadata, avoid file bytes, and must be loaded only by local test code once the web package exists; private fixture cases are prohibited from browser/service-worker/persistent caches and artifacts.
- **Commands run and results:** `make frontend-contract-check`; `python3 scripts/validate_frontend_content_ranges.py --self-test`; `python3 scripts/validate_frontend_traceability.py --self-test`; `python3 scripts/validate_frontend_route_matrix.py --self-test`; `python3 scripts/validate_frontend_state_matrix.py --self-test`; and the six existing Circle 0 validators all passed. No planned web command was run because `apps/web` does not exist yet.
- **Screenshots/traces/artifacts checked:** Reviewed the JSON fixture source, generated-free inventory, source-register title separation, documented API field boundaries, and final diff. No rendered frontend exists yet.
- **Known limitations/open decisions:** Fixture recipes are not generated client data and need a future test-factory adapter. Currency UI and reporter-visible status history remain prohibited until an approved contract adds them. Circle 1 visual direction and fluent-language review remain human decisions.
- **Commit/PR:** `docs: define frontend content range fixtures`
- **Next task may rely on:** Stable `content.<surface>.<tier>` names, explicit safe data classifications, contract-absence markers, and three layout-density targets for every requested content family.
- **AI assistance used:** Derived a contract-safe fixture taxonomy from the frontend handoff and task requirements; added an adversarial validator rather than using source-register data as plausible-looking UI content.
- **Prompt summary:** Use the frontend loop and work the next frontend task.
- **Human review:** the maintainer reviewed this work and merged it on 2026-09-20 (pull requests #17 to #22), as they stated when asking for this record. That review does not cover fluent Hausa, Igbo, or Yoruba review, screen-reader testing, or a live-API run; see the entry "Maintainer review of the merged frontend and backend work".

## 2026-09-20 — FE-004 BFF operation map

- **Task:** FE-004 — BFF operation map.
- **User outcome delivered:** Every 35 implemented non-health API operation now has one named direct Server Component read or exact purpose-built same-origin BFF route, with a complete implementation profile before the web app is scaffolded.
- **Routes/components changed:** No runtime route/component changed. Added `docs/FRONTEND_BFF_OPERATION_MAP.md` and `scripts/validate_frontend_bff_operation_map.py`; documented future `app/api/` ownership only.
- **Backend operations/contract version:** No generated contract changed. The map validates exact coverage of OpenAPI `0.0.0` operation IDs excluding health endpoints and preserves generated types as the future source of request/response shapes.
- **Public/private data handled:** Profiles permit only safe request ID, locale, and client-HMAC forwarding; service credentials are added server-side. They block browser cookies/authorisation/arbitrary headers, internal hostnames, report content, contacts, tracking/handle credentials, session/CSRF values, object keys, signed URLs, and evidence bytes from logs/caches/client bundles.
- **States implemented:** No UI state changed. The map defines safe problem mapping, `304` retain-body polling/read behaviour, timeout/cancellation propagation, idempotency replay/conflict handling, session-expiry recovery, and distinct public/private cache rules for later state-matrix consumers.
- **Accessibility evidence:** No UI changed. Future BFF errors use stable localisable codes and request IDs so FE-053 can associate accessible field/status recovery without raw backend detail.
- **Locales reviewed:** No message copy changed. Safe locale forwarding covers `en`, `ha`, `ig`, and `yo`; human translation review remains pending.
- **Performance/cache impact:** Public Server Component reads retain only the documented `ETag`/public response policy. Every mutation, tracking, Q&A, discovery, reviewer, auth, and evidence route is no-store; timeouts are bounded and streaming upload/download avoids full-body buffering.
- **Commands run and results:** `make frontend-contract-check`; `python3 scripts/validate_frontend_bff_operation_map.py --self-test`; the four frontend Circle 0 validators; and the six repository Circle 0 validators passed. No planned web build/test command was run because `apps/web` does not exist yet.
- **Screenshots/traces/artifacts checked:** Reviewed every generated non-health operation, route-matrix ownership, handoff cache/session semantics, and final diff. No runtime BFF/UI exists yet to screenshot or trace.
- **Known limitations/open decisions:** The map is a design/implementation contract, not a Route Handler implementation. Concrete headers, schemas, generated client imports, CSRF token lifecycle, and bundle tests begin in Circle 2/3. Circle 1 visual direction remains human-gated.
- **Commit/PR:** `docs: map frontend BFF operations`
- **Next task may rely on:** Exact BFF path ownership, profile-based guard/caching/redaction rules, and complete operation coverage without a generic proxy.
- **AI assistance used:** Reconciled OpenAPI, route ownership, state rules, and backend handoff into one validator-backed BFF ledger; explicitly excluded unsafe generic forwarding and frontend policy decisions.
- **Prompt summary:** Use the frontend loop and continue the next eligible frontend task.
- **Human review:** the maintainer reviewed this work and merged it on 2026-09-20 (pull requests #17 to #22), as they stated when asking for this record. That review does not cover fluent Hausa, Igbo, or Yoruba review, screen-reader testing, or a live-API run; see the entry "Maintainer review of the merged frontend and backend work".

## 2026-09-20 — FE-010 visual-direction discovery

- **Task:** FE-010 — One-round design discovery.
- **User outcome delivered:** The required human decision is recorded precisely rather than replaced with a generic component-library visual style or an AI-selected identity.
- **Routes/components changed:** No runtime route, component, comp, token, direction contract, or design document changed.
- **Backend operations/contract version:** No backend operation or contract changed.
- **Public/private data handled:** No data flow changed.
- **States implemented:** No UI state changed.
- **Accessibility evidence:** No visual direction was selected; the future direction must state mobile, low-data, reduced-motion, contrast, and keyboard implications before visible implementation begins.
- **Locales reviewed:** No message copy or translation changed.
- **Performance/cache impact:** No runtime bundle or cache changed. The future decision must define a low-data fallback before visual assets/interactions are introduced.
- **Commands run and results:** Confirmed Circle 0 is closed and Circle 1 explicitly requires a human choice. No design-generation, image-generation, external asset, or runtime command was run.
- **Screenshots/traces/artifacts checked:** Reviewed the visual-circle entry/exit criteria. No existing visual surface, design authority, token set, logo, or approved comp exists to inspect.
- **Known limitations/open decisions:** The maintainer must answer: (1) what a resident should feel/understand in the first viewport and what would feel untrustworthy; (2) which Abuja/Nigerian civic, documentary, publication, wayfinding, public-record, or community artifacts the product should sit beside and avoid copying; and (3) whether the standing workflow is comp-led or code-led. Then the maintainer must select one direction. FE-011–FE-013, Circle 4, and visible product surfaces remain blocked.
- **Commit/PR:** `docs: record pending visual direction`
- **Next task may rely on:** Circle 2/3 non-visual work may proceed from the closed Circle 0 contracts; no visual implementation may rely on this blocked task.
- **AI assistance used:** Refused to invent a visual identity and recorded the exact human inputs required by the accepted build order.
- **Prompt summary:** Use the frontend loop and continue after the Circle 0 gate.
- **Human review:** required; maintainer visual-direction decision pending.

## 2026-09-20 — FE-020 deterministic web foundation

- **Task:** FE-020 — Scaffold the pnpm workspace and Next.js app.
- **User outcome delivered:** A clean clone can install a separately managed, strict Next.js foundation and build it while the private API URL is deliberately unreachable; no product UI or BFF route is implied by the scaffold.
- **Routes/components changed:** Added the root pnpm workspace/runtime pin and a non-visual `apps/web` App Router root layout/page, strict TypeScript configuration, standalone Next output, package scripts, and web README.
- **Backend operations/contract version:** No backend operation or generated contract changed. The scaffold has no API fetch, client API configuration, BFF route, or browser-to-backend path.
- **Public/private data handled:** No runtime data flow exists. The `server-only` package is installed for future server modules; the foundation exposes no private URL, credential, provider, storage detail, report, or fixture in a client graph.
- **States implemented:** No product UI state changed. The placeholder page returns no visible product surface until human visual direction and later route tasks are complete.
- **Accessibility evidence:** No visible interactive component was introduced. The root document has semantic `html`/`body`; landmarks, errors, locale routing, and visible surfaces remain later tasks.
- **Locales reviewed:** No locale route, catalog, or translated copy was added. The root document uses `en` only as a temporary scaffold and does not claim language support.
- **Performance/cache impact:** Standalone output is enabled; the scaffold makes no build-time/network API call, has no images/fonts/analytics, and introduces no product cache. The production build succeeds with an unreachable internal API URL.
- **Dependencies:** Added Next 16.3.5 (MIT; App Router/BFF runtime), React/React DOM 19.3.0 (MIT; rendering runtime), TypeScript 5.9.3 (Apache-2.0; strict checking), `server-only` 0.0.1 (MIT; future client-import boundary), and matching MIT DefinitelyTyped packages. Exact versions are locked by pnpm; no dependency is added for a capability the accepted stack does not require.
- **Commands run and results:** `pnpm clean --lockfile`; `pnpm install --lockfile-only`; `pnpm install --frozen-lockfile` from empty `node_modules`; `API_INTERNAL_URL=http://127.0.0.1:1 pnpm --dir apps/web typecheck`; `API_INTERNAL_URL=http://127.0.0.1:1 pnpm --dir apps/web build`; and `pnpm audit --prod --audit-level high` all passed (no known production dependency vulnerability). The first candidate `@types/node@24.13.6` failed pnpm's release-age policy and was replaced with compatible `24.12.0`; no policy exemption was committed.
- **Screenshots/traces/artifacts checked:** Inspected the standalone build output and generated Next types; `.next` and `node_modules` remain ignored. No visual surface exists to screenshot.
- **Known limitations/open decisions:** FE-021 adds lint/test/E2E/a11y tooling and root `make web-*` targets. FE-022–FE-024 add error boundaries, environment validation/bundle proof, and CI. Human visual direction remains required before visible product UI.
- **Commit/PR:** `build: scaffold the strict Next.js web foundation`
- **Next task may rely on:** Node 24.20.0, pnpm 12.4.2, the committed lockfile, `apps/web` package scripts, strict compiler settings, standalone output, and proof that the base build does not require the private API.
- **AI assistance used:** Selected/pinned the accepted stack versions, created the minimal non-visual foundation, diagnosed the supply-chain age-policy failure, and refused to retain the tool-added policy exemption.
- **Prompt summary:** Use the frontend loop and continue with the eligible web foundation task.
- **Human review:** the maintainer reviewed this work and merged it on 2026-09-20 (pull requests #17 to #22), as they stated when asking for this record. That review does not cover fluent Hausa, Igbo, or Yoruba review, screen-reader testing, or a live-API run; see the entry "Maintainer review of the merged frontend and backend work".

## 2026-09-20 — FE-021 quality toolchain and commands

- **Task:** FE-021 — Quality toolchain and commands.
- **User outcome delivered:** The web stack has deterministic, named quality gates before product routes or BFF handlers begin: formatting, linting, strict types, unit/component tests, contract drift, production build, browser smoke, and axe accessibility smoke.
- **Routes/components changed:** No product route or visible component changed. Tooling configuration, root `make web-*` targets, and an empty-by-default MSW server were added.
- **Backend operations/contract version:** No operation changed. `web-contract` delegates to the existing generated frontend-contract drift check.
- **Public/private data handled:** No runtime data flow changed. MSW starts with no handlers so later tests must declare safe fixtures explicitly; unhandled requests are not silently accepted.
- **States implemented:** No product state changed. Empty unit/component/browser test layers exit non-zero rather than claiming coverage they do not have.
- **Accessibility evidence:** axe-core and browser configuration are installed, but no product accessibility result is claimed before FE-022 supplies an accessible rendered surface and tests.
- **Locales reviewed:** No message copy or translation changed.
- **Performance/cache impact:** All additions are development dependencies; they add no production client bundle, browser API, cache, analytics, or provider call.
- **Dependencies:** ESLint/Prettier/Vitest/Testing Library/MSW/Playwright and their adapters are maintained upstream testing or linting tools; all selected direct packages are MIT or Apache-2.0 except `axe-core` and `@axe-core/playwright` (MPL-2.0). They are used unmodified and are licence-compatible with the MIT repository. `pnpm audit` found no known production or full-dependency vulnerabilities. Only `msw` (copies a worker only if a later task explicitly configures one) and `unrs-resolver` (prepares ESLint's platform resolver) may run reviewed install hooks; all other transitive hooks remain denied.
- **Commands run and results:** `pnpm install --lockfile-only` and `pnpm install --frozen-lockfile` passed after explicitly approving two reviewed install hooks. `pnpm --dir apps/web format:check`, `lint`, `typecheck`, and `contract` passed. Empty `unit`, `component`, `e2e`, and `a11y` layers each failed non-zero as designed; `make web-verify` correctly stopped at the empty unit layer. No browser installation or browser test was run. The initial ESLint 10 attempt was incompatible with Next's pinned React lint plugin, so the toolchain uses compatible ESLint 9.39.5 rather than disabling rules.
- **Screenshots/traces/artifacts checked:** No product screenshot, trace, or browser artifact exists. Build output remains ignored.
- **Known limitations/open decisions:** ESLint 9.39.5 is the newest compatible line but is upstream-deprecated in favour of ESLint 10; upgrading requires a compatible Next/React lint-plugin stack and a separate review. The first unit/component/browser/axe tests, browser-install evidence, CI, and coverage proof belong to later tasks.
- **Commit/PR:** `build: add the frontend quality toolchain`
- **Next task may rely on:** FE-022 can add base error/metadata behaviour with component, browser, and axe tests using these exact commands.
- **AI assistance used:** Selected and configured development-only quality tools, identified the ESLint compatibility failure, inspected the two allowed install hooks, and recorded their bounded purpose.
- **Prompt summary:** Use the frontend loop and keep working without stopping.
- **Human review:** the maintainer reviewed this work and merged it on 2026-09-20 (pull requests #17 to #22), as they stated when asking for this record. That review does not cover fluent Hausa, Igbo, or Yoruba review, screen-reader testing, or a live-API run; see the entry "Maintainer review of the merged frontend and backend work".

## 2026-09-20 — FE-022 safe app recovery and metadata boundary

- **Task:** FE-022 — Base App Router error boundaries and metadata.
- **User outcome delivered:** A resident or judge sees a calm, recoverable, non-disclosing response when a base route fails or is unavailable, and can share only a safe operational reference with support.
- **Files changed:** `apps/web/app/{layout,page,error,global-error,loading,not-found,robots}.tsx`, `apps/web/app/_components/recovery-page.tsx`, `apps/web/src/lib/support/request-reference.ts`, the Vitest/Playwright resolver and standalone-server configuration, recovery unit/component/browser/axe tests, `apps/web/README.md`, `docs/FRONTEND_BUILD_ORDER.md`, and this log.
- **Backend operations/contract version:** No backend operation, BFF handler, generated client, or OpenAPI contract changed. The root page makes no API request, including during a production build with `API_INTERNAL_URL=http://127.0.0.1:1`.
- **Public/private data handled:** Request IDs are rendered only after strict canonical UUID validation and normalisation. Route and root error components intentionally ignore `Error.message`, stack data, provider values, and backend details. The generic unavailable surface gives no private-record existence signal; it has no client persistence, cache, analytics, credential, signed URL, report, contact, or attachment flow.
- **States implemented:** Semantic initial shell; polite loading; route/root retry error; generic unavailable/not-found; and safe support-reference present/absent states. A root `main` and `h1` were added after the real axe scan found the empty scaffold lacked required page landmarks.
- **Accessibility evidence:** The recovery surfaces use a named `main`, `h1`, native retry button, native link, text-only status/recovery meaning, and `aria-busy`/`aria-live` loading feedback. `@axe-core/playwright` passes against Chromium and mobile WebKit. Keyboard-operable retry is verified in the component test.
- **Locales reviewed:** English source copy only. The root document remains temporary `en`; FE-050 explicitly owns the `en`/`ha`/`ig`/`yo` route layout, negotiation, message parity, and translation review. This task corrects the earlier overlapping task wording rather than creating a partial locale boundary or claiming translations exist.
- **Performance/cache impact:** No API, image, font, third-party asset, analytics, or client data library was added. Browser tests run the standalone production artifact. `robots.ts` disallows API, reporting, tracking, handle, and reviewer paths; cache directives for implemented BFF/private responses remain the responsibility of their owning tasks.
- **Failure behaviour verified:** Invalid/non-string/noncanonical request IDs, unsupported UUID version/variant, and newline-tainted values do not render. Tests inject a private-looking database/provider error message and assert it is absent from both route and root recovery UIs. Unknown routes return `404` with the same generic unavailable wording.
- **Commands run and results:** `pnpm --dir apps/web format:check`, `lint`, `typecheck`, `unit` (9 passed), `component` (4 passed), `coverage` (13 passed; 100% over the exercised module graph), `contract`, and `API_INTERNAL_URL=http://127.0.0.1:1 pnpm --dir apps/web build` all passed. `pnpm --dir apps/web exec playwright install chromium webkit` completed; `e2e` passed 4 desktop/mobile checks; `a11y` passed 2 desktop/mobile axe checks; and `make web-verify` passed. The Impeccable detector returned no anti-pattern findings for the changed app/tests.
- **Screenshots/traces/artifacts checked:** Browser smoke and axe runs exercised the standalone app in desktop Chromium and mobile WebKit. No screenshot artifact is recorded because this is intentionally an unstyled semantic/error boundary; Playwright failure traces remain ignored and no private synthetic value is retained in a committed artifact.
- **Known limitations/open decisions:** FE-023 still owns startup environment validation and client-bundle secret proof; FE-024 owns CI. FE-040 will apply the maintainer-selected Field Ledger tokens and primitives. The recovery copy requires FE-050 message parity and translation review before public locale routes are enabled.
- **Commit/PR:** `feat: add safe app recovery boundaries`
- **Next task may rely on:** Root metadata/viewport/robots behavior; safe generic unavailable/retry semantics; `toSafeRequestReference`; standalone browser-test configuration; and a real passing test layer.
- **AI assistance used:** Implemented the minimal safety boundary, corrected resolver/standalone test-harness defects revealed by actual tests, and kept locale/design-system scope with their designated tasks.
- **Prompt summary:** Use the frontend loop and keep working without stopping.
- **Human review:** the maintainer reviewed this work and merged it on 2026-09-20 (pull requests #17 to #22), as they stated when asking for this record. That review does not cover fluent Hausa, Igbo, or Yoruba review, screen-reader testing, or a live-API run; see the entry "Maintainer review of the merged frontend and backend work".

## 2026-09-20 — FE-023 server/client environment boundary

- **Task:** FE-023 — Environment and server/client boundary.
- **User outcome delivered:** The web process refuses to start in the Node runtime without valid private API settings, while browser code has one explicit optional public setting and a repeatable proof that internal configuration cannot cross into client chunks.
- **Files changed:** `apps/web/instrumentation.ts`; `apps/web/src/lib/config/{server,public}.ts`; `apps/web/scripts/verify-client-boundary.mjs`; configuration tests and the server-only Vitest shim; browser runtime test configuration; `apps/web/package.json`; root `Makefile`, `.env.example`, and `pnpm-lock.yaml`; `apps/web/README.md`; `docs/FRONTEND_BUILD_ORDER.md`; and this log.
- **Backend operations/contract version:** No FastAPI operation, BFF handler, generated client, database schema, or OpenAPI contract changed. `API_INTERNAL_URL` is read only at Node runtime; no route makes an API request during `next build`.
- **Public/private data handled:** The private schema requires `APP_ENV`, an HTTP(S) `API_INTERNAL_URL`, and a minimum-length `INTERNAL_WEB_CREDENTIAL_CURRENT`; staging/production reject a placeholder credential. Errors report variable names only, never values. The client schema permits only optional `NEXT_PUBLIC_APP_ORIGIN`, rejects unknown public names and secret-like public names, and never returns the private schema. The bundle scan uses synthetic, non-secret canaries for the internal URL, current/previous service credentials, search/provider/embedding keys, and object-storage access/secret keys.
- **States implemented:** Node startup either validates configuration or fails closed before serving requests. Public configuration has valid, absent, unexpected-name, secret-like-name, and invalid-value outcomes. There is no product UI state or new browser storage/cache.
- **Accessibility evidence:** No visible interactive surface changed. The existing semantic shell and accessibility suite remain intact; this task adds no client-side announcement, focus, or motion behavior.
- **Locales reviewed:** No locale message, route, or translation changed. The public origin schema is locale-neutral; `en`, `ha`, `ig`, and `yo` routing remains owned by FE-050.
- **Performance/cache impact:** Zod 4.6.5 (MIT) is the single added production dependency for explicit runtime schemas; it is server-only in current execution and does not enter the verified client chunks. The scanner reads only generated client JavaScript; it makes no provider/API request and stores no sensitive artifact. Browser tests supply fixed synthetic runtime values to the standalone process only.
- **Failure behaviour verified:** Unit tests prove missing Node settings fail closed, valid Node startup succeeds, private values never enter configuration errors, production placeholders fail, and unexpected/unsafe/invalid public values fail without value disclosure. The production-boundary build sets eight private canaries; the scan passes only when every one and the server-only markers are absent from all client chunks.
- **Commands run and results:** `pnpm --dir apps/web format:check`, `lint`, `typecheck`, `unit` (17 passed), `coverage` (21 passed; 96.72% statements, 86.48% branches, 94.44% functions, 96.61% lines), `build:boundary` (13 client chunks verified), `API_INTERNAL_URL=http://127.0.0.1:1 pnpm --dir apps/web build`, `pnpm install --frozen-lockfile`, `pnpm audit --prod --audit-level high`, and full `pnpm audit --audit-level high` passed. Browser/a11y and canonical-gate rechecks are recorded with the final task verification.
- **Screenshots/traces/artifacts checked:** Inspected the generated standalone instrumentation artifact and completed client bundle scan. No screenshot is applicable to a configuration-only change; no trace or generated bundle is committed.
- **Known limitations/open decisions:** FE-024 still owns CI execution. FE-030/FE-031 will consume the validated server settings through a generated private API client; no generic proxy or direct browser API path is introduced here.
- **Commit/PR:** `build: enforce the web environment boundary`
- **Next task may rely on:** Validated runtime/private configuration, the explicit public environment allowlist, `web-boundary`, canary scanning, and stable standalone test-process environment setup.
- **AI assistance used:** Implemented separate runtime/public schemas, added a production-artifact canary scan, and fixed test-runner-only handling of Next's server-only import without altering the production barrier.
- **Prompt summary:** Use the frontend loop and keep working without stopping.
- **Human review:** the maintainer reviewed this work and merged it on 2026-09-20 (pull requests #17 to #22), as they stated when asking for this record. That review does not cover fluent Hausa, Igbo, or Yoruba review, screen-reader testing, or a live-API run; see the entry "Maintainer review of the merged frontend and backend work".

## 2026-09-20 — FE-024 least-privilege frontend CI

- **Task:** FE-024 — Frontend CI foundation.
- **User outcome delivered:** The repository now contains a reviewable frontend CI workflow that reproduces the deterministic web foundation and isolated browser/axe gates without write permission, real secrets, or exported test artifacts.
- **Files changed:** `.github/workflows/frontend.yml`, `scripts/validate_frontend_workflow.py`, root `Makefile`, `apps/web/README.md`, `docs/FRONTEND_BUILD_ORDER.md`, and this log.
- **Backend operations/contract version:** No API operation, BFF handler, generated client, schema, or OpenAPI content changed. The workflow runs the existing contract drift check and private-canary boundary build; it does not contact the private API.
- **Public/private data handled:** Workflow permissions are `contents: read`; each checkout disables persisted credentials. It references no `secrets` context, no live provider, no service credential, and no external artifact upload/download action. The boundary build supplies only synthetic canaries. Browser traces, screenshots, video, coverage, and reports are never uploaded.
- **States implemented:** Foundation failures block browser execution; the required aggregate fails for failed, skipped, cancelled, or otherwise non-successful prerequisite jobs. Browser checks start a standalone app only with synthetic test configuration. No product UI state changed.
- **Accessibility evidence:** CI installs Chromium and WebKit and runs the existing real-browser E2E and axe tests. No visible component changed; the test gate continues to cover the semantic shell and generic unavailable state at desktop/mobile viewports.
- **Locales reviewed:** No locale routing, message, or translation changed. CI preserves the existing English-source-only foundation status; FE-050 remains responsible for `en`, `ha`, `ig`, and `yo` parity.
- **Performance/cache impact:** `setup-node` caches only the pnpm package store keyed by `pnpm-lock.yaml`, not application output or private test data. Browser engines install only in the browser job. The workflow validator is standard-library Python and performs no network request.
- **Failure behaviour verified:** `web-ci-check --self-test` rejects a missing boundary command and an unpinned action reference. Structural checks require exactly four full-SHA action uses, the expected frozen/install/check commands, read-only permissions, disabled checkout credentials, and no artifact, secrets-context, `pull_request_target`, or write-permission use. YAML parsing passed. `actionlint` is not installed locally, so no actionlint result is claimed.
- **Commands run and results:** `git ls-remote` verified `actions/setup-node` v7.0.0 SHA `820762786026740c76f36085b0efc47a31fe5020`; the checked-in `actions/checkout` v7.0.1 SHA was reused. `make web-ci-check`, Ruby YAML parsing, Python compilation, `git diff --check`, and Prettier format checking passed. The existing local foundation/browser/axe gates were passing before workflow creation; the final task gate re-runs them before commit.
- **Screenshots/traces/artifacts checked:** Reviewed the workflow itself and confirmed no artifact action appears. No screenshots/traces are produced or committed by this configuration-only task.
- **Known limitations/open decisions:** The first hosted run is pending because this local branch has not been pushed, and this task does not authorise a push. Circle 2 remains open until GitHub reports the workflow green. A later CI policy change should update the validator in the same commit.
- **Commit/PR:** `feat: implement frontend CI workflow with validation and checks`
- **Next task may rely on:** A SHA-pinned, read-only workflow and local workflow-invariant validator; not on a claimed hosted green result.
- **AI assistance used:** Implemented the workflow and its negative-path validator, resolved the setup action revision, and kept browser data artifacts out of pull-request visibility.
- **Prompt summary:** Use the frontend loop and keep working without stopping.
- **Human review:** the maintainer reviewed this work and merged it on 2026-09-20 (pull requests #17 to #22), as they stated when asking for this record. That review does not cover fluent Hausa, Igbo, or Yoruba review, screen-reader testing, or a live-API run; see the entry "Maintainer review of the merged frontend and backend work".

## 2026-09-20 — FE-010 visual-direction discovery (resolved)

- **Task:** FE-010 — One-round design discovery.
- **User outcome delivered:** The maintainer's Field ledger choice now constrains the public product before any visible component is built.
- **Routes/components changed:** No runtime route or component changed. [`FRONTEND_VISUAL_DIRECTION.md`](FRONTEND_VISUAL_DIRECTION.md) records the accepted pre-implementation constraints.
- **Backend operations/contract version:** No backend operation or contract changed.
- **Public/private data handled:** No runtime data flow changed. The direction explicitly preserves the public-record/private-report boundary.
- **States implemented:** No UI state changed; the decision requires all later visual states to retain text labels, timestamps, and explicit evidence boundaries.
- **Accessibility evidence:** The approved constraints require four-locale typography, text-first public reading, keyboard-visible evidence links, reduced-motion equivalence, and low-data resilience. These are direction requirements, not completed UI evidence.
- **Locales reviewed:** No message copy or translation changed.
- **Performance/cache impact:** No runtime bundle or cache changed. The direction prohibits decorative dependencies as a substitute for evidence and requires a text-first fallback.
- **Commands run and results:** Ran Impeccable's direction concept seed and local decision board. The maintainer selected Field ledger; no generated image, remote asset, runtime UI, or provider data was introduced.
- **Screenshots/traces/artifacts checked:** No product surface exists yet. Temporary local decision-board artifacts were removed after the selection was recorded.
- **Known limitations/open decisions:** FE-011 through FE-013 remain to record the comparison, workflow preference, and implementation contract. `DESIGN.md` remains intentionally absent until Circle 15.
- **Commit/PR:** `docs: record the approved field ledger direction`
- **Next task may rely on:** FE-011 may evaluate the accepted direction against the alternatives; no visible product UI is authorised until the complete Circle 1 gate closes.
- **AI assistance used:** Presented a product-grounded visual-direction hand and translated the maintainer's selection into concrete trust and boundary constraints.
- **Prompt summary:** Using Impeccable, present choices for ShaidaGo's frontend feel, look, and tokens; maintainer selected Field ledger.
- **Human review:** The maintainer explicitly selected Field ledger on 20 September 2026.

## 2026-09-20 — FE-011 compare visual directions

- **Task:** FE-011 — Generate and compare visual directions.
- **User outcome delivered:** Field ledger was selected from a product-grounded hand, with its evidence and privacy behaviour defined before components can dilute it.
- **Routes/components changed:** No runtime route or component changed. [`FRONTEND_VISUAL_DIRECTION.md`](FRONTEND_VISUAL_DIRECTION.md) now records the comparison and cross-surface visual grammar.
- **Backend operations/contract version:** No backend operation or contract changed.
- **Public/private data handled:** No runtime data changed. The selected grammar makes public evidence, private reporting, and reviewer-only material visibly separate without inventing a new authorisation rule.
- **States implemented:** No UI state changed. The contract requires text and icon labels alongside state colour, dated in-place history, and explicit limited-evidence/review states.
- **Accessibility evidence:** Citation stitch is specified as keyboard-operable, programmatically announced, no-JavaScript reachable links; narrow/low-data behaviour is explicit. These requirements await implementation tests.
- **Locales reviewed:** No message copy or translation changed. The typography direction requires all four locale scripts/diacritics to be tested before use.
- **Performance/cache impact:** No runtime bundle, asset, or cache changed. The selected path forbids decorative media or motion from being required for evidence reading.
- **Commands run and results:** The Impeccable direction seed and local decision board completed before the human selection. Documentation validation remains limited to the project validators because no visual implementation exists.
- **Screenshots/traces/artifacts checked:** No product screenshot or comp exists; code-led execution is recorded in FE-012.
- **Known limitations/open decisions:** Exact token values, first-viewport contract, and initial route surface brief are FE-012/FE-013 work. `DESIGN.md` remains intentionally deferred.
- **Commit/PR:** `docs: define the field ledger visual system`
- **Next task may rely on:** FE-012 can select and persist the workflow path without re-opening the visual-world decision.
- **AI assistance used:** Framed and evaluated candidate worlds against audience identification and product clarity, then documented the maintainer's selected system without using unverified cultural or public-record claims.
- **Prompt summary:** Using Impeccable, present choices for ShaidaGo's frontend feel, look, and tokens; maintainer selected Field ledger.
- **Human review:** The maintainer selected Field ledger after the comparison on 20 September 2026.

## 2026-09-20 — FE-012 choose code-led execution

- **Task:** FE-012 — Choose comp-led or code-led execution.
- **User outcome delivered:** The frontend has a durable code-led workflow preference, so future UI work has an explicit fidelity contract instead of treating the absence of a comp as permission to use defaults.
- **Routes/components changed:** No runtime route or component changed. [`.impeccable/config.json`](../.impeccable/config.json) sets the standing workflow; [`FRONTEND_VISUAL_DIRECTION.md`](FRONTEND_VISUAL_DIRECTION.md) explains the execution implications.
- **Backend operations/contract version:** No backend operation or contract changed.
- **Public/private data handled:** No data flow changed.
- **States implemented:** No UI state changed. Future states must preserve the selected world without visual motion or media being necessary to understand a state.
- **Accessibility evidence:** The workflow requires keyboard, semantic, reduced-motion, responsive, and low-data evidence when components are built; none can be claimed before implementation.
- **Locales reviewed:** No message copy or translation changed.
- **Performance/cache impact:** No runtime asset, bundle, or cache changed. Code-led execution avoids making the public experience depend on generated raster imagery.
- **Commands run and results:** Verified the committed JSON is intentionally minimal and valid; project documentation validators remain the available checks before the frontend toolchain branch is integrated.
- **Screenshots/traces/artifacts checked:** None; a code-led direction has no approved comp. Later visual review compares renders to the written direction contract.
- **Known limitations/open decisions:** FE-013 must now define the exact first viewport and token roles. `DESIGN.md` remains deferred until the reviewed product exists.
- **Commit/PR:** `docs: set the code-led visual workflow`
- **Next task may rely on:** FE-013 can write the implementation contract without inventing an execution preference.
- **AI assistance used:** Explained the code-led trade-off and persisted the selection without adding imagery, providers, or runtime dependencies.
- **Prompt summary:** Using Impeccable, present choices for ShaidaGo's frontend feel, look, and tokens; maintainer selected Field ledger.
- **Human review:** The Field ledger decision board recorded code-led execution as the selected build path on 20 September 2026.

## 2026-09-20 — FE-013 Field ledger direction contract

- **Task:** FE-013 — Direction contract and surface brief.
- **User outcome delivered:** Future frontend work now has an exact Field ledger visual contract: semantic starting tokens, a code-led first viewport, evidence interaction, responsive behaviour, mode-specific grammar, and explicit anti-default boundaries.
- **Routes/components changed:** No runtime route or component changed. [`FRONTEND_VISUAL_DIRECTION.md`](FRONTEND_VISUAL_DIRECTION.md) adds the contract and `/{locale}` surface brief; `PRODUCT.md` now records the accepted brand commitment.
- **Backend operations/contract version:** No backend operation or contract changed.
- **Public/private data handled:** No runtime data flow changed. The contract explicitly preserves source attribution, private-report separation, no one-time-secret display, and public/private cache differences.
- **States implemented:** No UI state changed. Later components must implement the named loading, empty, stale, limited-evidence, error, and recovery grammar.
- **Accessibility evidence:** The contract requires visible keyboard focus, semantic citation links, text-plus-icon-plus-colour states, 200% zoom, forced colours, reduced motion, and four-locale text testing. No implementation test is claimed yet.
- **Locales reviewed:** No message copy or translation changed. Noto font coverage and rendered Hausa, Igbo, Yoruba, and English locale expansion are explicit future verification requirements.
- **Performance/cache impact:** No runtime bundle, cache, font, image, or provider request changed. The direction rejects a decorative asset dependency and keeps public pages text-first; private-cache rules remain unchanged.
- **Commands run and results:** Ran all five current frontend contract/inventory validators after the documentation change; each passed. `git diff --check` passed. No planned frontend command or visual test is reported as run.
- **Screenshots/traces/artifacts checked:** No runtime surface, comp, or screenshot exists. `DESIGN.md` is intentionally absent until the Circle 15 render/review gate.
- **Known limitations/open decisions:** Actual primitives, font licensing/subsetting, contrast values, layout implementation, and visual verification belong to Circle 4 and later. The contract is authoritative until a reviewed implementation updates the final design documentation.
- **Commit/PR:** `docs: establish the field ledger direction contract`
- **Next task may rely on:** Circle 4 design-foundation work can implement tokens and primitives; all visible work must preserve this contract.
- **AI assistance used:** Converted the selected direction into a bounded implementation contract and semantic token system while retaining the product's evidence, accessibility, locale, low-data, and privacy constraints.
- **Prompt summary:** Using Impeccable, present choices for ShaidaGo's frontend feel, look, and tokens; maintainer selected Field ledger.
- **Human review:** The maintainer selected Field ledger and the decision board recorded code-led execution on 20 September 2026.

## 2026-09-20 — FE-040 Field Ledger token foundation

- **Task:** FE-040 — Implement tokens from the approved world.
- **User outcome delivered:** The web foundation now has one semantic, Field Ledger token layer for warm paper surfaces, readable evidence/review states, responsive rhythm, motion, focus, selected, disabled, and read-only behaviour. The token stylesheet is compiled into the production standalone output, not merely available during development.
- **Files changed:** `apps/web/app/globals.css`, `apps/web/app/layout.tsx`, `apps/web/postcss.config.mjs`, `apps/web/scripts/prepare-standalone.mjs`, `apps/web/tests/unit/design-tokens.test.ts`, the Playwright configuration and foundation browser assertion, `apps/web/package.json`, `pnpm-lock.yaml`, `apps/web/README.md`, `docs/FRONTEND_BUILD_ORDER.md`, and this log.
- **Backend operations/contract version:** No BFF handler, API operation, generated client, database schema, or OpenAPI contract changed.
- **Public/private data handled:** No data is fetched, stored, logged, cached, or sent to a third party. The layer contains no provider, font, image, or external asset request. It does not create an evidence, report, or publication state.
- **States implemented:** Semantic visual roles cover reviewed, under-review, limited-evidence, unavailable, and problem status; components must still pair those values with explicit text and icons. Focus, selected, disabled, read-only, reduced-motion, increased-contrast, and forced-colour treatments are defined as global foundation behaviour.
- **Accessibility evidence:** Unit tests calculate WCAG AA contrast for thirteen canonical foreground/background state pairs and assert forced-colours, increased-contrast, focus-visible, and reduced-motion overrides. Standalone Chromium and mobile WebKit checks assert the compiled canvas token and fluid title style are present; axe has no automated violations in either target. No claim is made that later interactive primitives have their required keyboard tests.
- **Locales reviewed:** No message or route changed. `Noto Sans`/`Noto Serif` remain local-preference names followed by system fallbacks; no font is downloaded. Fluent rendering and parity for `en`, `ha`, `ig`, and `yo` remain FE-050 work.
- **Performance/cache impact:** Tailwind CSS 4.3.3 and its PostCSS adapter are MIT-licensed build-time dependencies that emit static CSS with no browser runtime. The standalone preparation script copies only local compiled static assets and a future public directory. No cache policy or private response handling changed.
- **Failure behaviour verified:** A real-browser capture exposed that the old standalone test command omitted compiled static assets and therefore rendered without CSS. `start:standalone` now prepares that output before every browser/a11y run, and the browser assertion fails if the computed Field Ledger token is absent. An early token test incorrectly read an increased-contrast override as the base palette; its parser was narrowed to the first root block before acceptance.
- **Commands run and results:** `pnpm --dir apps/web install --frozen-lockfile` passed after lockfile regeneration; `format:check`, lint, strict typecheck, unit (32 tests), component (4 tests), coverage (36 tests; 96.72% statements, 86.48% branches, 94.44% functions, 96.61% lines), contract drift check, boundary build/scan (13 client chunks), E2E (4 tests across Chromium and mobile WebKit), a11y (2 tests across Chromium and mobile WebKit), and `make web-verify` all passed. `git diff --check` is rerun before commit.
- **Screenshots/traces/artifacts checked:** Reviewed a local desktop production-standalone capture after static asset preparation. It shows the warm canvas, constrained gutter, and fluid type foundation; the temporary capture is not committed. Impeccable's mechanical detector reported no generic UI anti-patterns for `apps/web/app`.
- **Known limitations/open decisions:** This is the provisional token foundation, not the complete public shell or first viewport. FE-041 owns accessible primitives, FE-042 evidence components, FE-043 shells, and FE-044 code-led viewport proof. `DESIGN.md` remains intentionally absent until Circle 15.
- **Commit/PR:** `feat: establish field ledger design tokens`
- **Next task may rely on:** Semantic CSS/Tailwind aliases, static standalone asset preparation, and contrast/preference/browser proof. It must not infer product truth or authorisation from a token.
- **AI assistance used:** Implemented the approved semantic system, selected Tailwind's documented v4 PostCSS integration, added deterministic contrast/preference tests, and corrected the standalone browser-serving defect found by visual inspection.
- **Prompt summary:** Continue frontend work through the established task loop after selecting the Field Ledger direction.
- **Human review:** the maintainer reviewed this work and merged it on 2026-09-20 (pull requests #17 to #22), as they stated when asking for this record. That review does not cover fluent Hausa, Igbo, or Yoruba review, screen-reader testing, or a live-API run; see the entry "Maintainer review of the merged frontend and backend work".

## 2026-09-20 — FE-030 Deterministic OpenAPI generation

- **Task:** FE-030 — Deterministic OpenAPI generation.
- **User outcome delivered:** Server code now has one typed, reproducible path to the FastAPI contract, so later BFF and Server Component work cannot drift from `contracts/openapi.json` or hand-mirror backend models.
- **Files changed:** `apps/web/scripts/generate-api-types.mjs`, `apps/web/src/lib/api/generated/{schema,client}.ts`, `apps/web/tests/unit/generated-contract.test.ts`, `apps/web/package.json`, `apps/web/.prettierignore`, `apps/web/README.md`, `pnpm-lock.yaml`, `docs/FRONTEND_BUILD_ORDER.md`, and this log.
- **Backend operations/contract version:** Reads the committed `contracts/openapi.json`; no operation or contract changed.
- **Public/private data handled:** None at runtime. The client is a transport factory taking a base URL argument; it holds no URL, credential, or data.
- **States implemented:** None (non-visual). Problem-details shape is asserted at compile time.
- **Accessibility evidence:** Not applicable; no visible surface.
- **Locales reviewed:** Not applicable.
- **Performance/cache impact:** Build-time tooling only: `openapi-typescript` 7.13.0 (MIT, dev) and `openapi-fetch` 0.17.0 (MIT, tiny fetch wrapper, same maintainer). Both pinned exactly. The generated client is not imported by any client component; FE-031 owns the `server-only` wrapper.
- **Failure behaviour verified:** `api:check` regenerates into a temporary directory and fails on any difference from the committed files; `make web-contract` runs it.
- **Commands run and results:** Frozen install, `api:check`, `format:check`, strict typecheck, unit (33 tests), and `pnpm run contract` passed. Lint has 0 errors and 1 pre-existing unused-import warning in `tests/component/primitives.test.tsx`, which is outside this task. Build, E2E, and browser checks were not rerun because no runtime code changed.
- **Screenshots/traces/artifacts checked:** None; non-visual.
- **Known limitations/open decisions:** Lockfile diff includes peer-suffix churn from resolution with no package version changes. Import restriction to server code is enforced by FE-031.
- **Commit/PR:** `build: generate the typed API client from the OpenAPI contract`
- **Next task may rely on:** `createGeneratedClient(baseUrl)` and the `paths`/`operations`/`components` types.
- **AI assistance used:** Wrote the deterministic generator with drift check and compile-time contract assertions.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** the maintainer reviewed this work and merged it on 2026-09-20 (pull requests #17 to #22), as they stated when asking for this record. That review does not cover fluent Hausa, Igbo, or Yoruba review, screen-reader testing, or a live-API run; see the entry "Maintainer review of the merged frontend and backend work".

## 2026-09-20 — FE-031 Server-only private API client

- **Task:** FE-031 — Server-only private API client.
- **User outcome delivered:** Server Components can read public localities, projects, project detail, and approved sources through one typed, bounded, non-logging path that cannot leak the private URL or credential to the browser.
- **Files changed:** `apps/web/src/lib/api/{server,forwarded-context}.ts`, `apps/web/src/lib/config/server.ts`, `apps/web/tests/unit/{server-api,config-environment}.test.ts`, `apps/web/README.md`, `docs/FRONTEND_BUILD_ORDER.md`, and this log.
- **Backend operations/contract version:** `projects_list_localities`, `projects_list`, `projects_get`, `projects_get_source` (SR-PUBLIC profile); OpenAPI 0.0.0 unchanged.
- **Public/private data handled:** Public catalogue reads only. The bearer credential, internal URL, and client HMAC stay in server execution; nothing is logged. Problem results expose only stable code, status, field paths and codes, request ID, and Retry-After.
- **States implemented:** ok, not_modified (distinct from empty), problem, unavailable (timeout, network, malformed_response) as typed results for later surfaces.
- **Accessibility evidence:** Not applicable; no visible surface.
- **Locales reviewed:** Only `en`, `ha`, `ig`, `yo` are forwarded; anything else is dropped rather than mapped.
- **Performance/cache impact:** No new dependency. Reads pass `next.revalidate: 60` to match the API's public policy; FE-063 must verify this against the Vary/Authorization behaviour of the Next data cache. No client bundle change (boundary scan: 13 chunks clean).
- **Failure behaviour verified:** Header injection attempts, invalid locale/HMAC/ETag, 304, 429 with Retry-After, 404, 422 field errors, 503 retry once, 503 with long Retry-After not retried, network and timeout, HTML gateway errors, invalid JSON, and invalid runtime environment. A test caught a latent FE-023 defect: an empty `API_INTERNAL_URL` raised a raw `Invalid URL` instead of `ServerEnvironmentError`; fixed with a regression test.
- **Commands run and results:** `make web-verify` exit 0 (format, lint, typecheck, unit, component, coverage, contract drift, boundary build). Coverage 94.18% statements, 89.9% branches, 88.4% functions. Lint has 0 errors and one pre-existing unused-import warning in `tests/component/primitives.test.tsx`. Browser E2E/a11y were not separately re-inspected.
- **Screenshots/traces/artifacts checked:** None; non-visual.
- **Known limitations/open decisions:** Reviewer reads are deferred to FE-034 (session extraction). The 60 s Next data-cache behaviour with an Authorization header is unproven until FE-063. The backend `request_id` is ignored in favour of the one we sent.
- **Commit/PR:** `feat: add the server-only private API client`
- **Next task may rely on:** `serverApi()` public reads, `buildForwardedHeaders`, and the typed `ApiResult` for FE-032/FE-033.
- **AI assistance used:** Designed and implemented the transport, its tests, and the boundary test; found and fixed the environment parse defect.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** the maintainer reviewed this work and merged it on 2026-09-20 (pull requests #17 to #22), as they stated when asking for this record. That review does not cover fluent Hausa, Igbo, or Yoruba review, screen-reader testing, or a live-API run; see the entry "Maintainer review of the merged frontend and backend work".

## 2026-09-20 — FE-032 BFF request guard library

- **Task:** FE-032 — BFF request guard library.
- **User outcome delivered:** Every later browser mutation handler can compose the same tested Origin, CSRF, body-limit, idempotency, header, abort, and error-shaping guards, so a forged, oversized, or malformed request is refused before it reaches the private API.
- **Files changed:** `apps/web/src/lib/bff/{origin,csrf,body,idempotency,backend-request,guard,problem}.ts`, `apps/web/tests/unit/bff-guard.test.ts`, `apps/web/README.md`, `docs/FRONTEND_BUILD_ORDER.md`, and this log.
- **Backend operations/contract version:** None called. Idempotency-key format (lower-case canonical UUID) follows the API's behaviour described in `docs/FRONTEND_BACKEND_CONTRACT.md`; OpenAPI 0.0.0 unchanged.
- **Public/private data handled:** Handles CSRF and session values and idempotency keys as opaque secrets: never logged, never echoed, and absent from problem bodies. Browser `Cookie`, `Authorization`, `Host`, `Content-Length`, and `X-Forwarded-*` cannot reach the backend by construction.
- **States implemented:** 400 `invalid_json`/`idempotency_key_invalid`, 403 `origin_forbidden`/`csrf_invalid`, 413, 415, 499 `request_aborted`, 503/504 upstream, and API problems mapped by stable code, all `no-store`.
- **Accessibility evidence:** Not applicable; no visible surface.
- **Locales reviewed:** Problems expose a stable `code` plus an English fallback title; localised text belongs to FE-053. No translation is claimed.
- **Performance/cache impact:** No dependency. Byte caps are enforced on the stream and multipart bodies are not buffered by `limitBodyStream`. Every error response is no-store.
- **Failure behaviour verified:** Spoofed forwarded headers, repeated/null/path/cross-site Origin, unconfigured deployed origin, missing/malformed/mismatched CSRF, wrong content types, oversized declared and chunked bodies, invalid and non-UTF-8 JSON, client abort versus timeout, unsafe problem codes, and out-of-range Retry-After. A test showed that the `Headers` API trims whitespace, so an unreachable padding check was removed.
- **Commands run and results:** Typecheck, lint (0 errors; one pre-existing warning), and coverage passed: 84 tests, 96.11% statements, 93.42% branches, 91.75% functions; `src/lib/bff` 98.5% statements. Prettier applied. `make web-verify` exit 0 (77 unit, 7 component; client-boundary scan clean across 13 chunks).
- **Screenshots/traces/artifacts checked:** None; non-visual.
- **Known limitations/open decisions:** The maintainer must decide how the reviewer's CSRF token reaches the browser (server-rendered token versus an HttpOnly-cookie-only design) before FE-034; `docs/THREAT_MODEL.md` A-15 says it must not be readable by client JavaScript, so `verifyCsrfToken` takes already-resolved values and does not choose. The branch coverage rule of 100% for public-response allowlists and similar security modules is not yet required here since none of those exist. `NEXT_PUBLIC_APP_ORIGIN` must be set in staging and production.
- **Commit/PR:** `feat: add BFF request guards for browser mutations`
- **Next task may rely on:** `guardMutation`, `readBoundedJson`, `buildBackendHeaders`, `backendSignal`, and the problem builders.
- **AI assistance used:** Designed and implemented the guards and adversarial tests.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** the maintainer reviewed this work and merged it on 2026-09-20 (pull requests #17 to #22), as they stated when asking for this record. That review does not cover fluent Hausa, Igbo, or Yoruba review, screen-reader testing, or a live-API run; see the entry "Maintainer review of the merged frontend and backend work".

## 2026-09-20 — FE-033 Purpose-built public mutation handlers

- **Task:** FE-033 — Purpose-built public mutation handlers.
- **User outcome delivered:** Browser code has one same-origin, guarded endpoint per public write or poll (question, discovery, report, tracking, follow-up, handles) with no path to the private API and no generic proxy.
- **Files changed:** nine `apps/web/app/api/**/route.ts` handlers; `apps/web/src/lib/bff/{public-handler,public-schemas,guard,body,problem}.ts`; `apps/web/src/lib/api/server.ts` (shared `execute`, no-retry mutation methods, 204 and replay handling, `aborted` reason); `apps/web/tests/unit/{bff-public-handlers,server-api}.test.ts`; `apps/web/README.md`; `docs/FRONTEND_BUILD_ORDER.md`; this log.
- **Backend operations/contract version:** `projects_ask_question`, `discovery_start_public_run`, `discovery_get_public_run`, `reports_submit`, `report_status_lookup`, `report_status_answer_follow_up`, `reporter_handles_create`, `reporter_handles_list_reports`, `reporter_handles_delete`; OpenAPI 0.0.0 unchanged.
- **Public/private data handled:** Tracking codes, passphrases, follow-up answers, and report multipart bodies exist only in the request body/stream and are never placed in a URL or log; tests assert the URLs and problem bodies never contain them. One-time receipt/handle values are returned once, `no-store`. Browser `Cookie`, `Authorization`, and `X-Forwarded-*` are never forwarded.
- **States implemented:** success (200/201/204, replay flag), 304 poll, 400/403/413/415/422 BFF rejections, mapped API problems (including rate limit Retry-After), 499 cancellation, 503/504 upstream failure, generic 500.
- **Accessibility evidence:** Not applicable; no visible surface.
- **Locales reviewed:** Only a validated `X-Shaidago-Locale` is forwarded; localised copy belongs to FE-053. No translation claimed.
- **Performance/cache impact:** No dependency added. Reports are streamed, not buffered. All nine routes are dynamic and no-store; `next build` still performs no API fetch and the client boundary scan is clean (13 chunks).
- **Failure behaviour verified:** As listed in the build-order note; additionally an empty-body operation rejects a body even when the runtime omits Content-Length, and a streamed report over the cap stops reading (chunks consumed < total) and returns 413.
- **Commands run and results:** `make web-verify` exit 0 (139 unit, 7 component, contract drift, build with nine dynamic API routes, boundary scan); `make web-e2e` 4 passed and `make web-a11y` 2 passed (Chromium and mobile WebKit) on the unchanged foundation page; coverage 96.08% statements, 93.42% branches, 94.59% functions (`src/lib/bff` 96.65%). Lint has 0 errors and the same pre-existing warning.
- **Screenshots/traces/artifacts checked:** None; non-visual. No handler has been exercised against a running FastAPI, so real-integration behaviour (including multipart streaming to uvicorn and the 65 s budget) is unverified.
- **Known limitations/open decisions:** (1) `X-Shaidago-Client-Hmac` is not forwarded: the contract says the BFF supplies a pseudonymous HMAC of the client IP, but no key, rotation scheme, or trusted-proxy IP source is defined in `.env.example` or the ADRs. Until the maintainer decides, backend rate limits cannot distinguish clients. (2) Success bodies are passed through as the typed API response rather than re-picked field by field; the API's Pydantic allowlists remain the only filter. (3) Per-file 10 MiB and file-type checks are enforced by the API (and later client preparation), not by the BFF, because the BFF does not buffer or parse multipart. (4) The locale header is provisional until FE-050/FE-054 define the locale source. (5) Idempotency keys are lower-case UUIDs, matching the API.
- **Commit/PR:** `feat: add same-origin public mutation handlers`
- **Next task may rely on:** the handler paths above, `handlePublicJson`/`handlePublicEmpty`/`handleReportSubmission`, and the `MutationOptions` transport methods for FE-034's reviewer handlers.
- **AI assistance used:** Designed and implemented the handlers, schemas, transport extension, and table-driven adversarial tests.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** the maintainer reviewed this work and merged it on 2026-09-20 (pull requests #17 to #22), as they stated when asking for this record. That review does not cover fluent Hausa, Igbo, or Yoruba review, screen-reader testing, or a live-API run; see the entry "Maintainer review of the merged frontend and backend work".

## 2026-09-20 — FE-034 Reviewer session and mutation handlers

- **Task:** FE-034 — Reviewer session and mutation handlers.
- **User outcome delivered:** A reviewer can (once a UI exists) sign in, act on reports, publish or withdraw a separately authored public update, run report-scoped discovery, and download sanitised evidence through same-origin handlers, with session secrets confined to server memory and `HttpOnly` cookies.
- **Files changed:** 17 `apps/web/app/api/reviewer/**/route.ts` files; `apps/web/src/lib/bff/{reviewer-session,reviewer-session-handler,reviewer-handler,reviewer-schemas,guard}.ts`; `apps/web/src/lib/api/{server,forwarded-context}.ts` (reviewer reads and mutations, sign-in/out, evidence stream, opaque-secret validator); `apps/web/src/lib/bff/backend-request.ts`; `apps/web/tests/unit/bff-reviewer-handlers.test.ts`; `apps/web/README.md`; `docs/FRONTEND_BUILD_ORDER.md`; this log.
- **Backend operations/contract version:** `auth_sign_in`, `auth_sign_out`, `reviewer_notes_create`, `reviewer_evidence_download`, `reviewer_decisions_{ask_follow_up,withdraw_follow_up,transition}`, `reviewer_publication_{create_draft,preview,publish,withdraw}`, `reviewer_discovery_{plan,create,get,cancel,review,answer_follow_up,decide_source}`, plus the reviewer read operations for Server Components (`reviewer_reports_queue`, `reviewer_reports_get`, `reviewer_notes_list`, `reviewer_publication_list`). OpenAPI 0.0.0 unchanged.
- **Public/private data handled:** Private report data, notes, reviewer reasons, evidence bytes, session and CSRF tokens. None is logged, cached, placed in a URL, or returned in a sign-in body; tests assert absence of tokens in bodies and URLs, no `Cookie` forwarded to the API, and no `Set-Cookie` on ordinary responses. Malformed IDs are answered as `not_found` without contacting the API.
- **States implemented:** 201 sign-in with cookies, 204 sign-out (always clearing cookies), 401 with cookie clearing, 403 origin/csrf/forbidden, 404, 409 passed through by stable code, 413/415/422 pre-API rejections, 499/503/504, evidence stream.
- **Accessibility evidence:** Not applicable; no visible surface.
- **Locales reviewed:** Only a validated locale header is forwarded. No translation claimed.
- **Performance/cache impact:** No dependency added. Evidence is streamed, not buffered. All handlers dynamic and `no-store`; boundary scan still clean over 13 client chunks.
- **Failure behaviour verified:** Origin-before-session-before-CSRF ordering; duplicate cookie names discarded; API cookie policy mismatches (name, Secure, HttpOnly, SameSite, path, lifetime, unsafe token characters) refused with best-effort revocation; timeout/network never retried for mutations; reviewer reads retried once on a transient 503; an unexpected evidence content type or disposition is downgraded rather than forwarded.
- **Commands run and results:** `make web-verify` exit 0 (239 unit and 7 component tests at that point; contract, build listing 26 dynamic API routes, boundary scan). Final coverage run: 246 tests passing, 95.55% statements, 91.66% branches, 93.41% functions. Lint 0 errors and the same pre-existing warning. E2E/a11y were run for FE-033 on the unchanged page and not rerun. No handler was run against a live API.
- **Screenshots/traces/artifacts checked:** None; non-visual.
- **Known limitations/open decisions:** (1) CSRF design needs maintainer confirmation: the CSRF token lives in an `HttpOnly` cookie and is forwarded server-side, which satisfies THREAT_MODEL A-15 and the contract's "BFF removes csrf_token from the browser response", and relies on SameSite=Lax plus exact Origin for the browser-facing defence. A synchroniser token rendered into pages would be stronger against subdomain cookie tossing but exposes the token to page script. (2) The operation map lists public-update withdraw as JSON ≤ 1 KiB, but the API takes no body; the handler accepts none (map should be corrected). (3) Reviewer `since_version` polling from the map is not offered because OpenAPI defines no such parameter for `reviewer_discovery_get`. (4) Client HMAC forwarding is still undecided (see FE-033). (5) The reviewer account/role and sign-in policy remain maintainer decisions; nothing here checks a role.
- **Commit/PR:** `feat: add reviewer session and mutation handlers`
- **Next task may rely on:** `handleReviewerJson`/`handleReviewerEmpty`/`handleReviewerGet`, the reviewer cookie helpers, and the server-only reviewer read methods.
- **AI assistance used:** Designed and implemented the session cookie handling, handlers, schemas, and adversarial tests.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** the maintainer reviewed this work and merged it on 2026-09-20 (pull requests #17 to #22), as they stated when asking for this record. That review does not cover fluent Hausa, Igbo, or Yoruba review, screen-reader testing, or a live-API run; see the entry "Maintainer review of the merged frontend and backend work".

## 2026-09-20 — FE-035 BFF contract/security tests

- **Task:** FE-035 — BFF contract/security tests.
- **User outcome delivered:** The BFF boundary is now regression-protected: adding, renaming, or widening a browser route, logging a sensitive value, or leaking a wire detail into client JavaScript fails a check.
- **Files changed:** `apps/web/tests/unit/bff-contract.test.ts`, `apps/web/tests/unit/bff-reviewer-handlers.test.ts`, `apps/web/tests/unit/bff-public-handlers.test.ts`, `apps/web/scripts/verify-client-boundary.mjs`, `docs/FRONTEND_BUILD_ORDER.md`, and this log.
- **Backend operations/contract version:** None called; OpenAPI 0.0.0 and the operation map are read-only inputs.
- **Public/private data handled:** Synthetic canaries only (a fake tracking code, credentials, session cookies, and an internal IP); no real data.
- **States implemented:** Not applicable (tests and a build check).
- **Accessibility evidence:** Not applicable.
- **Locales reviewed:** Not applicable.
- **Performance/cache impact:** No runtime change. The bundle scan adds ten literal markers.
- **Failure behaviour verified:** Map-versus-filesystem drift in either direction; logging via console, logger, or stdout/stderr; canary and internal-host echo in response bodies and headers; reviewer and public cancellation.
- **Commands run and results:** `make web-verify` exit 0: 258 unit and 7 component tests, contract drift check, production build with boundary scan clean across 13 client chunks including the new markers. Lint 0 errors plus the same pre-existing warning.
- **Screenshots/traces/artifacts checked:** None.
- **Known limitations/open decisions:** Same as the Circle 3 gate note: no live-API run, undefined client HMAC, and two decisions pending maintainer confirmation. Log redaction is proven by absence of output rather than by a redaction function, because the BFF deliberately logs nothing; adding logging later must add a central denylist and a test.
- **Commit/PR:** `test: guard the BFF boundary against drift and leaks`
- **Next task may rely on:** The operation-map parity test and the runtime no-output test as guard rails for later route or logging changes.
- **AI assistance used:** Wrote the parity, redaction, and cancellation tests and the bundle markers.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** the maintainer reviewed this work and merged it on 2026-09-20 (pull requests #17 to #22), as they stated when asking for this record. That review does not cover fluent Hausa, Igbo, or Yoruba review, screen-reader testing, or a live-API run; see the entry "Maintainer review of the merged frontend and backend work".

## 2026-09-20 — FE-041 Accessible primitive layer

- **Task:** FE-041 — Accessible primitive layer.
- **User outcome delivered:** Later surfaces get one accessible, token-driven control set in the Field ledger style, with labels/errors wired automatically and no built-in English.
- **Files changed:** `apps/web/src/components/primitives/{primitives.tsx,primitives.css}`, `apps/web/tests/component/primitives.test.tsx`, `apps/web/tests/a11y/primitives.a11y.spec.ts`, `apps/web/tests/support/primitives-sheet.tsx`, `apps/web/tests/unit/primitive-sheet.test.ts`, `apps/web/package.json` (`a11y` renders the fixture first), `.gitignore`, `apps/web/.prettierignore`, `apps/web/eslint.config.mjs`, `docs/FRONTEND_BUILD_ORDER.md`, and this log.
- **Backend operations/contract version:** None.
- **Public/private data handled:** None; fixtures are fictional text.
- **States implemented:** default, hover, focus-visible, disabled, read-only, invalid, required, checked, open/closed overlays, loading, notice tones, status tones.
- **Accessibility evidence:** 19 component tests plus 14 browser checks (axe, target size, reflow at 320 px and 200% text, token styling, focus ring, forced colours, reduced motion) in Chromium and mobile WebKit; screenshots inspected at both widths.
- **Locales reviewed:** All strings are props. The fixture uses one long unbroken Yoruba-diacritic word and a long Yoruba-style label as a worst case; this is a layout probe, not a translation, and no human language review is claimed.
- **Performance/cache impact:** No new dependency; Base UI was already present. CSS is token-only with one gradient chevron and no external asset.
- **Failure behaviour verified:** Screenshots caught default-green progress, a checkbox-looking switch, a required marker missing its space, and a WebKit select ignoring min height and widening the page; each was fixed and re-tested. Pagination was changed from page counts to previous/next links because the API's cursors have no page count.
- **Commands run and results:** `make web-verify` exit 0 (259 unit, 19 component, boundary scan clean), `make web-e2e` 4 passed, `make web-a11y` 14 passed plus the fixture render. Lint 0 errors.
- **Screenshots/traces/artifacts checked:** Desktop Chromium and iPhone 13 WebKit full-sheet captures and a zoomed switch/progress capture; not committed.
- **Known limitations/open decisions:** No screen-reader run; no real 200% browser zoom (emulated by font size and 320 px width); datalist combobox popup is browser-drawn; the generated fixture lives in gitignored `tests/.generated/`.
- **Commit/PR:** `feat: build the accessible primitive layer`
- **Next task may rely on:** Primitive props and classes for FE-042 and FE-043.
- **AI assistance used:** Reworked the primitives, wrote tests, and iterated on screenshots.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** the maintainer reviewed this work and merged it on 2026-09-20 (pull requests #17 to #22), as they stated when asking for this record. That review does not cover fluent Hausa, Igbo, or Yoruba review, screen-reader testing, or a live-API run; see the entry "Maintainer review of the merged frontend and backend work".

## 2026-09-20 — FE-042 Evidence-specific components

- **Task:** FE-042 — Evidence-specific components.
- **User outcome delivered:** Later record, source, and Q&A surfaces can show claims, citations, dates, review state, translation status, AI text, and evidence gaps consistently and without inferring truth.
- **Files changed:** `apps/web/src/components/evidence/{evidence.tsx,evidence.css}`, `apps/web/app/layout.tsx` (stylesheet import), `apps/web/tests/component/evidence.test.tsx`, `apps/web/tests/support/{evidence-labels.ts,primitives-sheet.tsx}`, `apps/web/tests/a11y/primitives.a11y.spec.ts`, `docs/FRONTEND_BUILD_ORDER.md`, and this log.
- **Backend operations/contract version:** None called; types come from the generated OpenAPI schema and the controlled vocabulary.
- **Public/private data handled:** Public evidence only; fixtures are fictional. No component accepts private report data.
- **States implemented:** six verification states, five information classes, five source availabilities, three translation statuses, official versus community timeline origin, three evidence-gap kinds, absent dates.
- **Accessibility evidence:** Component tests for names, descriptions, time elements, external-link name, and note roles; browser axe clean in Chromium and mobile WebKit; a screenshot was inspected; the stitch works by plain anchor and lands on a focusable target.
- **Locales reviewed:** No copy is embedded; label records are typed exhaustively. Test labels are fictional English. Date formatting is injected for FE-052.
- **Performance/cache impact:** Server-renderable, no client JavaScript, one small stylesheet, no dependency.
- **Failure behaviour verified:** Uncited claim renders nothing; missing last-checked shows "not recorded"; a heading-order violation in the fixture was corrected.
- **Commands run and results:** `make web-verify` exit 0; `make web-a11y` 16 passed.
- **Screenshots/traces/artifacts checked:** Evidence-section capture with the stitch target active.
- **Known limitations/open decisions:** Claim-side stitch highlight deferred to FE-071; `SourceCard` uses a fixed `h3`, so pages must place it under an `h2`; `unknownDate` label in `SourceCardLabels` is currently unused and should be removed or used when FE-070 consumes it.
- **Commit/PR:** `feat: add evidence-specific components`
- **Next task may rely on:** the exported components and exhaustive label record types.
- **AI assistance used:** Designed and implemented the components, tests, and fixture.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** the maintainer reviewed this work and merged it on 2026-09-20 (pull requests #17 to #22), as they stated when asking for this record. That review does not cover fluent Hausa, Igbo, or Yoruba review, screen-reader testing, or a live-API run; see the entry "Maintainer review of the merged frontend and backend work".

## 2026-09-20 — FE-043 Public and reviewer shells, FE-044 First-viewport proof, and maintainer-requested changes

- **Task:** FE-043 — Public and reviewer shells; FE-044 — First-viewport proof; plus the maintainer's instructions to move components and styling to Tailwind CSS and shadcn and to resolve the open decisions myself.
- **User outcome delivered:** The public site now has a skip-linked, labelled shell and a Field ledger first viewport with a fictional, labelled example record and dated evidence rail; the reviewer shell and sign-out control exist for later routes; components and styling use Tailwind and shadcn structure; rate limiting can distinguish clients.
- **Files changed:** `apps/web/src/components/{ui,shell,landing,evidence,primitives}/*`, `apps/web/src/content/en/*`, `apps/web/src/lib/{utils,format/date,bff/request-context}.ts`, `apps/web/src/lib/config/server.ts`, BFF handlers (context), `apps/web/app/{page,layout,globals}`, `apps/web/components.json`, `.env.example`, `docs/FRONTEND_BFF_OPERATION_MAP.md`, tests (unit, component, e2e, a11y), `apps/web/README.md`, `docs/FRONTEND_BUILD_ORDER.md`, `package.json`/`pnpm-lock.yaml`, and this log.
- **Backend operations/contract version:** None new. OpenAPI 0.0.0 unchanged; the operation map's public-update withdraw row now says empty body, matching the API.
- **Public/private data handled:** Public page only, with an invented example labelled as such. The client HMAC derives from the trusted edge address, never forwards the address, rotates daily, and is required in deployed stages. The CSRF design is decided: the token stays in an `HttpOnly` cookie and is forwarded server-side, with `SameSite=Lax` and exact Origin as the browser-facing defence.
- **States implemented:** shell landmarks, skip link, current/unavailable/available language items, empty status region, reviewer area, sign-out idle/pending/failed, first viewport wide and narrow.
- **Accessibility evidence:** axe clean on the landing and primitive/evidence fixtures in Chromium and mobile WebKit; component tests for landmarks, skip-link order, language states, sign-out failure; keyboard skip-link test in Chromium; no-JS test; screenshots of desktop and phone inspected.
- **Locales reviewed:** English copy only. `ha`, `ig`, and `yo` are shown as "not yet reviewed" and not machine-translated; fluent review is still required.
- **Performance/cache impact:** Added `class-variance-authority` 0.7.1, `clsx` 2.1.1, `tailwind-merge` 3.5.0 (all MIT, small, pinned) as the shadcn helper set. Landing is static and cacheable; client bundle scan still clean (13 chunks). Removed four custom stylesheets.
- **Failure behaviour verified:** `tailwind-merge` initially dropped `text-primary-foreground` beside the custom `text-ledger-lg` size, making button text unreadable (axe caught it); fixed and tested. Unlayered global rules were overriding utilities and were moved to `@layer base`. The first-viewport screenshot showed the primary action below the fold at 1280x720, so the composition was tightened. iOS WebKit does not Tab to links, so that one browser check is scoped to Chromium (skip stated in the test) with Tab order also proven in jsdom.
- **Commands run and results:** `make web-verify` exit 0 (269 unit, 46 component, contract drift, boundary scan clean); `make web-e2e` 17 passed, 1 skipped as above; `make web-a11y` 16 passed; the frontend validators pass. Live-API run attempted: Postgres, Redis, MinIO, and ClamAV are up, but `make migrate` fails because the local database is at revision `0027_embedding_384`, which this branch does not contain. I did not reset your database, so no handler has run against a live API.
- **Screenshots/traces/artifacts checked:** Landing at 1280x720 and iPhone 13 width, inspected.
- **Known limitations/open decisions:** Live-API integration needs the database migrated from the matching backend branch (or a fresh local database). Nav links to unbuilt routes hit the safe not-found page. No screen-reader run; zoom is emulated. The unused `unknownDate` field in `SourceCardLabels` remains.
- **Commit/PR:** `feat: add shells and the first viewport on Tailwind and shadcn components`
- **Next task may rely on:** `PublicShell`, `ReviewerShell`, `SignOutButton`, the `ui/*` components, `cn`, the English content modules, and the forwarded client HMAC.
- **AI assistance used:** Implemented the shells, first viewport, migration to Tailwind/shadcn, client HMAC, and tests.
- **Prompt summary:** Unattended frontend/BFF build loop; maintainer asked me to finish Circle 4 myself and to use Tailwind and shadcn.
- **Human review:** the maintainer reviewed this work and merged it on 2026-09-20 (pull requests #17 to #22), as they stated when asking for this record. That review does not cover fluent Hausa, Igbo, or Yoruba review, screen-reader testing, or a live-API run; see the entry "Maintainer review of the merged frontend and backend work".

## 2026-09-20 — Open-item closure before locale work

- **Task:** Close the earlier circles' open items that were waiting only on CI or review, before starting Circle 5.
- **User outcome delivered:** The hosted CI gate and the live-API gap are closed with evidence, and two real bugs that only a live run could expose are fixed.
- **Files changed:** `apps/web/src/lib/bff/{guard,origin,public-handler}.ts`, `apps/web/src/components/evidence/evidence.tsx`, `apps/web/src/content/en/evidence.ts`, unit tests, `apps/web/README.md`, `docs/FRONTEND_BUILD_ORDER.md`, and this log.
- **Backend operations/contract version:** No contract change. Exercised through the BFF: question, tracking lookup and follow-up answer, report submission, reporter-handle create/list/delete, public discovery start and poll, and reviewer sign-in, note, transition, conflict, evidence download, follow-up ask, publication-draft refusal, and sign-out.
- **Public/private data handled:** Fictional reports, a 1x1 fictional image, and the local development reviewer only. Tokens, cookies, and tracking codes were read within one shell process, never printed, and the scratch files were deleted.
- **Closed items:** hosted CI for the web workflow (green on PRs #19 to #22 and on `main` at `fe14bf7`); the live-API run; the unused `unknownDate` label.
- **Failure behaviour verified:** a foreign Origin is refused; a session-less reviewer call is 401; a stale transition is a stable conflict code; a used-up follow-up question and a deleted handle return the generic failure; a same-key retry replays.
- **Defects found and fixed:** (1) empty-body POSTs (reporter-handle create, sign-out, cancel, withdraw) returned 413 because the framework always supplies a body stream; the guard now rejects only a declared or chunked body, since these handlers never read or forward one; regression tests added. (2) In development the browser's own `Host` (for example `127.0.0.1`) was refused because the framework reports `localhost`; development and test now also accept it, deployed stages never do.
- **Commands run and results:** `make web-verify` exit 0 (271 unit, 46 component, contract drift, build, boundary scan clean), `make web-e2e` 17 passed and 1 skipped (iOS WebKit Tab-to-link, as before), `make web-a11y` 16 passed. The live run started the API (replay provider mode, so no live provider call) and the built web app on local ports, and both were stopped afterwards.
- **Known limitations/open decisions:** publish, reviewer discovery, and source decisions were not exercised live. The local ClamAV container's mapped port does not match the API's scanner setting, so real scanning was not exercised (demo scanner mode used). Still open and not closable by me: fluent Hausa, Igbo, and Yoruba review; screen-reader testing; real browser zoom; links to routes later work builds; the fictional landing example.
- **Commit/PR:** `fix: accept runtime empty bodies and the browser host locally, and record the open-item closures`
- **AI assistance used:** Ran the live integration, diagnosed the two defects, fixed them with regression tests, and recorded the closures.
- **Prompt summary:** Unattended frontend/BFF build loop for Circle 5; first close any open items that only needed CI or review.
- **Human review:** The maintainer stated that all CI has run and passed and that the earlier work is reviewed; the two bug fixes and this entry have not been reviewed by anyone else.

## 2026-09-20 — FE-050 Locale routing and negotiation

- **Task:** FE-050 — Locale routing and negotiation.
- **User outcome delivered:** Every public page has a language-prefixed URL, a bare visit lands on the visitor's remembered or requested language (else English) with its query intact, and a language without reviewed copy is shown honestly rather than as English dressed up as another language.
- **Files changed:** `apps/web/proxy.ts`, `apps/web/next.config.ts`, `apps/web/src/i18n/{routing,request}.ts`, `apps/web/app/[locale]/**` (layout, landing, not-found, error, catch-all, loading), `apps/web/src/components/shell/shell.tsx`, `apps/web/vitest.unit.config.ts`, tests (proxy unit, shell component, locale e2e, recovery), `apps/web/package.json`, `pnpm-lock.yaml`, `apps/web/README.md`, `docs/PRIVACY_AND_SAFETY.md`, `docs/FRONTEND_BUILD_ORDER.md`, and this log.
- **Backend operations/contract version:** None. The BFF stays unprefixed and unchanged.
- **Public/private data handled:** A language-preference cookie (`NEXT_LOCALE`, one of four codes, one year, `SameSite=Lax`, not `HttpOnly` because it is a preference) is now set on locale-prefixed pages. Its data flow is documented in `docs/PRIVACY_AND_SAFETY.md`. No private data is involved.
- **States implemented:** bare visit, cookie, header, unsupported header/cookie/segment, canonical case, preserved query, reviewed and unreviewed locales, 404 per locale.
- **Accessibility evidence:** `html lang` is the language the text is written in; each locale name in the switcher carries its own `lang`; the "not yet reviewed" note is outside the link and marked `lang="en"`; the notice is a labelled note; axe still passes (16 browser checks plus the existing suites).
- **Locales reviewed:** English only. `ha`, `ig`, and `yo` routes exist but serve the English original with a visible status; no translation was written or simulated.
- **Performance/cache impact:** New dependency `next-intl` 4.14.5 (MIT, peer-compatible with Next 16 and React 19; `pnpm audit --prod` reports no known vulnerabilities). Pages are static per locale (`generateStaticParams`); the not-found page stays static; the client bundle scan is still clean. First-load JavaScript was not measured against the plan's budget in this task.
- **Failure behaviour verified:** hostile and unsupported cookies, `//host`, `/%2F%2Fhost`, `/\host` and similar paths never leave the origin; `/EN` canonicalises; an unknown path under a real locale is a real 404 (a `loading.tsx` at the locale root had turned it into a 200 and was moved into a route group); a not-found page that read request headers made the server log "static to dynamic" errors and was made static. `proxy.ts` never runs for `/api`, so the 26 BFF routes are unchanged.
- **Commands run and results:** `make web-verify` exit 0 (281 unit, 47 component, contract drift, build, boundary scan clean); `make web-e2e` 35 passed and 1 skipped (iOS WebKit Tab-to-link, as before) with no server errors logged; `make web-a11y` 16 passed; lint 0 errors and 0 warnings.
- **Screenshots/traces/artifacts checked:** `/ha` at desktop width inspected (notice, labelled language links, current language marked); not committed.
- **Known limitations/open decisions:** Recovery-page and loading strings are static English until FE-051. The not-found home link is `/`, so it returns to the remembered language through the proxy rather than to a fixed locale. Reviewer routes do not exist yet; when they do they must live under a locale prefix.
- **Commit/PR:** `feat: add locale-prefixed routing and language negotiation`
- **Next task may rely on:** `LOCALES`, `REVIEWED_LOCALES`, `contentLocale`, `isSupportedLocale`, the `[locale]` layout, and `src/i18n/request.ts` as the place FE-051 loads catalogues.
- **AI assistance used:** Configured next-intl, restructured the routes, and wrote the negotiation and open-redirect tests.
- **Prompt summary:** Unattended frontend/BFF build loop for Circle 5.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — Directory hostile-filter fixture correction

- **Task:** Correct a GitGuardian false positive in the FE-061 hostile-input test.
- **User outcome delivered:** The directory filter test still proves query-parameter injection is discarded without resembling a credential to secret scanning.
- **Files changed:** `apps/web/tests/unit/directory-filters.test.ts` and this log.
- **Security/privacy impact:** Replaced the non-secret test string `amac&admin=1` with `amac&unexpected_filter=1`; no credential was present, rotated, or exposed.
- **Verification:** Prettier check, the 11-test directory-filter unit suite, ESLint, strict TypeScript, and whitespace validation passed. TypeScript initially read stale ignored `.next` artifacts from later stack routes; those artifacts were moved to a recoverable temporary directory before the clean check.
- **Commit/PR:** `test: avoid a secret-like directory filter fixture`
- **AI assistance used:** Traced the GitGuardian check-run to the exact fixture and preserved its adversarial coverage while avoiding detector-like syntax.
- **Prompt summary:** Diagnose and repair the GitGuardian failure on PR #25.
- **Human review:** none yet; pending maintainer review.

## 2026-09-20 — FE-051 Message structure and parity tooling

- **Task:** FE-051 — Message structure and parity tooling.
- **User outcome delivered:** Copy is now structured by domain in four catalogues with a machine-checked guarantee that no translation can drift from English, and a locale is served in its own language only when a named reviewer has approved it.
- **Files changed:** `apps/web/messages/{en,ha,ig,yo,status}.json`, `apps/web/scripts/{messages-parity,check-messages}.mjs`, `apps/web/src/i18n/{catalogue,routing}.ts`, landing page and first-viewport component, recovery pages and `RecoveryPage`, the shell test, `apps/web/package.json` and lockfile (dev dependency `@formatjs/icu-messageformat-parser` 3.5.19, MIT, already in the tree via next-intl), tests (parity, catalogue, e2e link name), `apps/web/README.md`, `docs/FRONTEND_BUILD_ORDER.md`, and this log. The old `src/content/en/*.ts` modules were removed.
- **Backend operations/contract version:** None.
- **Public/private data handled:** None; static public copy only.
- **States implemented:** reviewed, machine-assisted, and pending domains; complete versus gapped catalogues; original-with-notice fallback.
- **Accessibility evidence:** unchanged axe results (16 browser checks); the fallback keeps `lang` truthful and shows a visible notice. "Sources 1" became "Source 1" through an ICU `{number, number}` message.
- **Locales reviewed:** English is marked reviewed with the maintainer as reviewer, self-reported on the basis that they reviewed and merged pull requests 17 to 22. `ha`, `ig`, and `yo` are `pending`, every value `null`. I did not write, machine-translate, or simulate any Hausa, Igbo, or Yoruba text, because a wrong safety or status string would mislead residents and CLAUDE.md forbids fabricated translations.
- **Performance/cache impact:** No runtime dependency. The client `error` and `global-error` boundaries import `en.json` (about 5 KB of JSON); the client bundle scan is still clean. First-load JavaScript was not measured against the plan's budget.
- **Failure behaviour verified:** the checker fails on a missing or extra key, a leaf/object mismatch, an empty or non-string leaf, invalid ICU in English or a translation, a renamed or retyped variable, missing `other` branches, unknown plural categories, differing select branches, translated text under `pending`, gaps under `reviewed`, missing reviewer or date, an invalid status value, mismatched domains, and an unreviewed English source. The loader falls back, flagged, when a domain is marked reviewed but still contains nulls.
- **Commands run and results:** `make web-verify` exit 0 (300 unit, 47 component, contract drift plus message check, build, boundary scan clean); `make web-e2e` 35 passed and 1 skipped (iOS WebKit Tab-to-link) on three consecutive runs; `make web-a11y` 16 passed; lint 0 errors and 0 warnings; the frontend workflow validator passes.
- **Screenshots/traces/artifacts checked:** None new; the rendered landing is unchanged apart from the "Source 1" label.
- **Known limitations/open decisions:** Every non-English domain is pending, so the Circle 5 requirement for reviewed critical copy in three languages needs a fluent reviewer. Recovery pages are English-only because reading the locale would make them dynamic. Typed content records for evidence labels remain exhaustive by TypeScript and by the parity check.
- **Commit/PR:** `feat: add domain message catalogues with parity checking and honest review status`
- **Next task may rely on:** `resolveDomain`, `formatMessage`, the catalogue types, and `messages:check` for FE-052 to FE-054.
- **AI assistance used:** Designed the catalogue structure, wrote the parity checker and loader, and migrated the existing copy.
- **Prompt summary:** Unattended frontend/BFF build loop for Circle 5.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-052 Locale-aware formatting

- **Task:** FE-052 — Locale-aware formatting.
- **User outcome delivered:** Dates, times, numbers, lists, and (once the API has one) naira amounts display consistently in the page language without altering the facts they carry.
- **Files changed:** `apps/web/src/lib/format/formatters.ts` (replaces `date.ts`), the landing page, `apps/web/tests/unit/formatters.test.ts`, `docs/FRONTEND_BUILD_ORDER.md`, and this log.
- **Backend operations/contract version:** None. No API field carries money today; `naira` is ready for one.
- **Public/private data handled:** None.
- **States implemented:** instant, calendar date, date-time, relative-with-exact, plain and NGN numbers, lists, language names, unformattable input.
- **Accessibility evidence:** Not applicable to the formatters themselves; consumers should render dates in `<time datetime>` (the evidence components already do).
- **Locales reviewed:** English output is asserted exactly. For `ha`, `ig`, and `yo` the tests assert only invariants (same digits, same order, same year and day), because I cannot verify their CLDR wording and did not want to enshrine possibly wrong text.
- **Performance/cache impact:** Standard `Intl` only; no dependency.
- **Failure behaviour verified:** a UTC instant near midnight lands on the correct Lagos day; a date-only value never shifts; malformed dates come back unchanged; malformed or over-precise amounts, exponent notation, thousands separators, and non-finite numbers throw; a large amount keeps every digit.
- **Commands run and results:** `make web-verify` exit 0 with the new tests included in the unit run. Browser suites are unaffected by this change and were not re-run for this task.
- **Screenshots/traces/artifacts checked:** None.
- **Known limitations/open decisions:** Igbo and Yorùbá CLDR data has visible gaps in the runtime's ICU (relative times, one time format), so their formatted output needs review before those languages are served. Relative months and years are approximate (30 and 365 days), which is why the exact time is always paired with them.
- **Commit/PR:** `feat: add locale-aware formatters that never change the underlying value`
- **AI assistance used:** Designed the formatters and wrote the boundary tests.
- **Prompt summary:** Unattended frontend/BFF build loop for Circle 5.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — Hausa, Igbo, and Yorùbá copy added and served

- **Task:** Bring the maintainer's translations into the build and serve all four locales as themselves (follow-up to FE-050 and FE-051).
- **User outcome delivered:** Residents opening `/ha`, `/ig`, or `/yo` now get the landing page, shell, evidence labels, and recovery pages in that language, with the correct `lang`, and no "showing the original" notice.
- **Files changed:** `apps/web/messages/{ha,ig,yo,status,en}.json`, `apps/web/app/global-error.tsx`, unit, component, browser, and accessibility tests (new `tests/a11y/locales.a11y.spec.ts`), `apps/web/README.md`, `docs/FRONTEND_BUILD_ORDER.md`, and this log.
- **Backend operations/contract version:** None.
- **Public/private data handled:** Public static copy only.
- **States implemented:** reviewed status for every locale and domain; fallback-with-notice remains implemented and is now covered by tests that mock a pending or gapped domain.
- **Accessibility evidence:** axe passes for `en`, `ha`, `ig`, and `yo` in Chromium and mobile WebKit; each locale reflows at 320 px and at 200% text with no horizontal scroll and no clipped link or button; a phone-width screenshot of `/yo` was inspected (diacritics, wrapping, and the language control intact).
- **Locales reviewed:** The text in `ha.json`, `ig.json`, and `yo.json` was written by the maintainer, who asked for it to be recorded as not pending. `messages/status.json` records `reviewed` with the reviewer "maintainer (self-reported: authored and added this copy; no independent fluent reviewer)" on 2026-09-20. I did not write, edit, or check the wording of any Hausa, Igbo, or Yorùbá text; the parity checker verified only structure, ICU syntax, variables, and completeness.
- **Performance/cache impact:** Catalogues are static JSON; the client bundle scan is still clean.
- **Failure behaviour verified:** the checker found that the maintainer's files lacked `recovery.fatal.title`, a key added after translation began. Rather than write the three missing strings, that key was removed and the global error screen reuses the page-error title; the maintainer plans one full translation pass at the end of the build.
- **Commands run and results:** `make web-verify` exit 0 (313 unit, 47 component, catalogues consistent, bundle scan clean); `make web-e2e` 41 passed and 1 skipped (iOS WebKit Tab-to-link); `make web-a11y` 32 passed; `pnpm audit --prod` clean.
- **Known limitations/open decisions:** Igbo and Yorùbá CLDR formatting data in the runtime is thin (for example relative days and one time format); the landing page uses only long dates, which render acceptably, but relative and clock formatting must be reviewed before any surface uses them in those languages. The maintainer plans a full translation pass at the end, including any new keys; new domains added before then must be marked pending and non-critical so they do not flip a locale back to English.
- **Commit/PR:** `feat: serve reviewed Hausa, Igbo, and Yorùbá copy`
- **AI assistance used:** Integrated the maintainer's translations, updated the status and tests, and added per-locale browser checks.
- **Prompt summary:** Maintainer added translations and asked that they not be pending and that the work be committed.
- **Human review:** The maintainer authored the translations and set their status by instruction; the code and test changes have not been reviewed by anyone else.

## 2026-09-20 — FE-053 Localised validation and problem mapping, and pending-key tracking

- **Task:** FE-053 — Localised validation and problem mapping; plus the maintainer's instruction to add all new keys with `null` translations and translate them at the end of the build.
- **User outcome delivered:** A failed action can be explained to a resident from the problem's stable code alone, in reviewed wording, without ever showing backend text, submitted values, or internals; form errors have an accessible summary that moves focus to the field.
- **Files changed:** `apps/web/src/lib/problems/{problem-messages,browser-problem}.ts`, `apps/web/src/components/ui/{error-summary,field}.tsx`, `apps/web/messages/*.json` (new `problems` domain, restored `recovery.fatal.title`, `pendingKeysAllowed`), `apps/web/scripts/{messages-parity.mjs,messages-parity.d.mts,check-messages.mjs}`, `apps/web/app/global-error.tsx`, tests (problem messages, error summary, parity, catalogue), `apps/web/README.md`, `docs/FRONTEND_BUILD_ORDER.md`, and this log.
- **Backend operations/contract version:** None called. Covers the problem codes in `docs/API.md`, `contracts/openapi.json`, and the BFF's own codes.
- **Public/private data handled:** Problem responses only. The parser ignores `title` and `detail` and any submitted value; `preservedValues` never restores secrets, contacts, or files.
- **States implemented:** known code, unknown code with reference, Retry-After, completion-unknown after timeout or network loss, field rule errors, unmapped errors, empty summary, focused summary.
- **Accessibility evidence:** component tests show the summary takes focus and is an alert, each link moves focus to its field by mouse and keyboard, and the field keeps its value, is `aria-invalid`, and has its message as its accessible description. Browser axe and reflow suites for all four locales still pass.
- **Locales reviewed:** English only. The `problems` domain is `null` in `ha`, `ig`, and `yo` and `pending`/non-critical so it does not flip those languages back to English; I wrote no Hausa, Igbo, or Yorùbá text. It must be translated, reviewed, and made critical before the first form ships.
- **Pending keys:** restored `recovery.fatal.title` (English) with `null` in the other three, as instructed. `status.json` now has `pendingKeysAllowed: true`; the checker allows `null` keys in a reviewed domain during the build, lists 36 per language, keeps requiring a reviewer and date, and fails on any `null` once the switch is `false`.
- **Performance/cache impact:** No dependency. The problem code adds no client JavaScript until a form imports it; the bundle scan is clean.
- **Failure behaviour verified:** hostile or malformed problem bodies, a wrong content type, an unsafe request ID, a non-numeric Retry-After, inherited object keys (`constructor`, `__proto__`) used as codes, unmapped and duplicate field errors, and files and secrets in preserved values.
- **Commands run and results:** `make web-verify` exit 0 (331 unit, 51 component, catalogues consistent with 36 pending keys per language, bundle scan clean); `make web-e2e` 41 passed and 1 skipped (iOS WebKit Tab-to-link); `make web-a11y` 32 passed.
- **Known limitations/open decisions:** No form uses this yet, so no page renders a problem message; Circle 9 wires it in. Adding keys to a served domain would show a fallback notice, so new keys go into new domains. The Circle 5 exit criterion for critical validation copy in every language is open until the translation pass.
- **Commit/PR:** `feat: map problem codes to reviewed copy and add an accessible error summary`
- **AI assistance used:** Designed the mapping, parser, and summary, extended the checker, and wrote the tests.
- **Prompt summary:** Unattended frontend/BFF build loop for Circle 5; maintainer asked to keep the fatal key and add all future keys as null.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-054 Language-switch behaviour and the Circle 5 gate

- **Task:** FE-054 — Language-switch behaviour; close Circle 5.
- **User outcome delivered:** A resident can change language and land on the same page in the new language, is warned before losing an unsaved private draft, hears or sees a confirmation, and can do all of it without JavaScript except the warning and announcement.
- **Files changed:** `apps/web/src/i18n/locale-href.ts`, `apps/web/src/lib/draft-guard.ts`, `apps/web/src/components/shell/{language-link,language-announcer,shell}.tsx`, `apps/web/src/components/ui/overlay.tsx` (controlled `ConfirmDialog`), the landing page, `apps/web/messages/*.json` (new `language` domain, `null` in ha, ig, yo), `apps/web/tests/{unit,component,e2e}`, `apps/web/README.md`, `docs/FRONTEND_BUILD_ORDER.md`, and this log.
- **Backend operations/contract version:** None. The cursor rule comes from `docs/FRONTEND_BACKEND_CONTRACT.md`.
- **Public/private data handled:** No private data. Links contain only the route and allowlisted public filters. The draft flag is memory only. One `sessionStorage` key holds a language code for a single navigation and is cleared on read.
- **States implemented:** switch with and without JavaScript, unsaved-draft confirmation (stay, Escape, leave), announcement shown, cleared after 8 seconds, absent on ordinary loads and on reload, storage unavailable.
- **Accessibility evidence:** the confirmation is an `alertdialog` with a title and description, focus returns to the link on cancel, the announcement is in an existing `role=status` polite region and carries the correct `lang`, axe passes for all four locales, and reflow passes at 320 px and 200% text.
- **Locales reviewed:** The switcher and the announcement text use the new `language` domain, which is `null` in `ha`, `ig`, and `yo`, so the announcement appears in English with `lang="en"` until the maintainer translates it. I wrote no translation.
- **Performance/cache impact:** Two small client components (`LanguageLink`, `LanguageAnnouncer`) and the existing dialog; the client bundle scan is clean across 14 chunks. The landing stays static.
- **Failure behaviour verified:** hostile path segments and filter values cannot leave the origin; drafts, tracking codes, and unlisted parameters never appear in a link; a blocked `sessionStorage` does not break the switch; the announcer ignores a flag for another language and clears it.
- **Commands run and results:** `make web-verify` exit 0 (336 unit, 58 component, catalogues consistent with 41 pending keys per language, bundle scan clean); `make web-e2e` 47 passed and 1 skipped (iOS WebKit Tab-to-link); `make web-a11y` 32 passed; `pnpm audit --prod` clean; lint 0 errors.
- **Known limitations/open decisions:** The draft warning is proven at component level only, because no page has a draft yet; re-check it when the report form lands. Nothing on the landing has query filters, so filter preservation is proven by unit tests, not in a browser, until the directory exists. See the Circle 5 gate note for the remaining translation work.
- **Commit/PR:** `feat: switch language to the equivalent page with a draft guard and an announcement`
- **AI assistance used:** Designed and implemented the link builder, guard, link, and announcer and wrote the tests.
- **Prompt summary:** Unattended frontend/BFF build loop for Circle 5.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-060 Landing page, FE-061 URL-owned directory filters, FE-062 Server-rendered directory results, FE-063 Public caching and revalidation, FE-064 Directory accessibility and performance proof

- **Task:** FE-060 to FE-064 (Circle 6). They were delivered as one commit because they share the catalogue keys, the browser mock API, the page shell, and the components.
- **User outcome delivered:** A resident can see what ShaidaGo is, search or browse public records by place, category, status, or verification, share the exact view by URL, and get useful pages with or without JavaScript, on a weak connection, in four language routes.
- **Files changed:** `apps/web/app/[locale]/(site)/{page,projects/page}.tsx`, `apps/web/src/components/{directory,landing,shell}/*`, `apps/web/src/lib/directory/{filters,freshness,format-lite}.ts`, `apps/web/src/lib/api/public-data.ts`, `apps/web/src/lib/api/server.ts` (cache tag), `apps/web/src/lib/bff/{public-cache,reviewer-handler}.ts`, the publish route, `apps/web/src/components/ui/{field,overlay}.tsx` and `shell/language-link.tsx` (lazy dialog, select styling), `apps/web/messages/*` (new `directory` and `home` domains), `apps/web/tests/**` including `support/mock-api.mjs`, both Playwright configs, `apps/web/README.md`, `docs/FRONTEND_BUILD_ORDER.md`, and this log. The old first-viewport component, its tests, and `loading.tsx` were removed.
- **Backend operations/contract version:** `projects_list_localities` and `projects_list` (OpenAPI 0.0.0 unchanged), read from Server Components through the server-only client.
- **Public/private data handled:** Public catalogue data only. The cache holds only successful public reads; a test classifies every server-API method as cached-public or `no-store`, so report, tracking, handle, and reviewer calls cannot enter it. Filters are allowlisted; backend `title`, `detail`, and internals are never shown.
- **States implemented:** results, first-load empty, no matches, invalid cursor, unavailable with retry, stale note, missing check date, original-language and machine-assisted notices, pagination, canonical redirect, no-JavaScript.
- **Accessibility evidence:** axe clean in four languages across five directory states plus the landing; reflow at 320 px and 200% text; 44 px targets; one polite count; distinct link names; reduced motion; a search landmark whose name does not duplicate its field label; desktop and phone screenshots inspected.
- **Locales reviewed:** The landing hero reuses the maintainer's reviewed `landing` translation. `directory` and `home` are `null` in `ha`, `ig`, and `yo` (pending, non-critical), so those pages show the English original with `lang="en"` and a notice. I wrote no translation.
- **Performance/cache impact:** First-load JavaScript is 142.9 KB (landing) and 152.2 KB (directory) gzip against the 170 KB budget, enforced by a test; the first measurement was over budget because of a dialog chunk on every page, now loaded on demand. Public reads are cached 60 seconds per language and filter set and dropped on publication.
- **Failure behaviour verified:** hostile filter values, cursors, and repeated parameters; a stale cursor; an outage (not cached); a response with backend text; a page that never reaches the API during a build; JavaScript disabled.
- **Defects found and fixed:** `loading.tsx` left no-JavaScript visitors on a placeholder (removed); fetch-level caching silently did nothing because of the `Authorization` header and `force-dynamic` (moved to a tagged wrapper); the `:read-only` pseudo-class styled every `<select>` as read-only; the landing search form and field had the same accessible name and the report link appeared twice; a plain GET form drops the results anchor (the canonical redirect re-adds it); the whole dialog implementation was in every page's first load.
- **Commands run and results:** `make web-verify` exit 0 (355 unit, 75 component, catalogues consistent with 116 pending keys per language, bundle scan clean across 17 chunks); `make web-e2e` 89 passed and 1 skipped (iOS WebKit Tab-to-link); `make web-a11y` 84 passed; `pnpm audit --prod` clean. By hand, the built app against the real local API and its seeded records rendered 12 cards, a 6-card category filter, the invalid-cursor state, and `/ha`; both servers were stopped afterwards.
- **Known limitations/open decisions:** No source count or verification on cards because the API summary has neither. Record, trust, and report links show the safe not-found page until later circles. No page-level revalidating or offline indicator. Browser suites use a fictional mock; no screen-reader run.
- **Commit/PR:** `feat: add the public landing and project directory with tagged caching`
- **AI assistance used:** Designed and implemented the filters, directory, landing, caching, and mock API; found and fixed the defects above; measured the budget; wrote the tests.
- **Prompt summary:** Unattended frontend/BFF build loop; maintainer directed the loop to continue through Circle 6 and later circles.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-070 Project detail hierarchy, FE-071 Citation and source interaction, FE-072 Timeline and uncertainty states, FE-073 Trust page, FE-074 Project detail proof

- **Task:** FE-070 to FE-074 (Circle 7), delivered as one commit because they share the catalogue keys, the mock API, and the evidence components.
- **User outcome delivered:** A resident can open a record, see each sourced statement with its own verification label, open the exact cited passage on a source page, understand what is unknown or stale, read how records work, and start a report that keeps the project.
- **Files changed:** `apps/web/app/[locale]/(site)/{projects/[slug]/page,projects/[slug]/sources/[sourceId]/page,trust/page}.tsx`, `apps/web/src/components/project/*`, `apps/web/src/components/evidence/evidence.tsx`, `apps/web/src/lib/{identifiers,directory/freshness,api/public-data,bff/public-schemas}.ts`, `apps/web/messages/*` (domains `project`, `source`, `trust`), `apps/web/tests/**` including `support/mock-api.mjs`, `docs/FRONTEND_BUILD_ORDER.md`, and this log.
- **Backend operations/contract version:** `projects_get` and `projects_get_source` (OpenAPI 0.0.0 unchanged), read from Server Components through the server-only client with 60 s tagged caching; failures and 404s are never cached.
- **Public/private data handled:** Public record and source data only. Slugs and source ids are validated before a call; unknown, hidden, and malformed are the same not-found. No reviewer, internal, or private field is rendered.
- **States implemented:** typical, minimal, and maximal records; no promise; no sourced statements; no updates; awaiting/disputed/outdated statements; stale and never-checked; future-dated update; unavailable, restricted, permanently unavailable, and unchecked sources; long passage; not found; outage with retry.
- **Accessibility evidence:** axe clean, 320 px and 200% reflow for five page states in four languages on Chromium and mobile WebKit; Base UI popovers and native disclosures; 44 px targets; statement-named citation triggers; status in text.
- **Locales reviewed:** `project`, `source`, and `trust` are `null` in ha/ig/yo (pending, non-critical), so those pages show the English original with `lang="en"` and a notice. I wrote no translation. 223 pending keys per language.
- **Performance/cache impact:** No new client JavaScript beyond the existing citation control; budget tests still pass.
- **Failure behaviour verified:** hostile and malformed slugs and source ids, unknown record and source, an outage, JavaScript disabled, and the public-cache test that every server call is a public catalogue endpoint.
- **Defects found and fixed:** a nested-quantifier regex flagged by the security lint in a test (replaced with segment checks); the mock lacked `source_version_id` required by the contract.
- **Commands run and results:** `make web-verify` exit 0 (355 unit, 82 component, bundle scan clean); `make web-e2e` 107 passed and 1 skipped; `make web-a11y` 124 passed; `pnpm audit --prod --audit-level high` clean.
- **Known limitations/open decisions:** No funding, institution, or contractor fields exist in the contract, so they appear only as sourced statements. No publication date on source pages (not returned). Question and Source Scout panels belong to Circles 8 and 9. The real API was not run for this circle; browser suites use a fictional mock.
- **Commit/PR:** `feat: add the project record, source, and trust pages with explicit uncertainty`
- **AI assistance used:** Designed and implemented the pages, components, mock endpoints, and tests.
- **Prompt summary:** Unattended frontend/BFF build loop; maintainer directed the loop to continue through later circles.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-080 Question client island, FE-081 Answer and citation rendering, FE-082 Insufficient and degraded behaviour, FE-083 Q&A tests

- **Task:** FE-080 to FE-083 (Circle 8), delivered as one commit because they share the catalogue keys, the mock API, and one component tree.
- **User outcome delivered:** A resident can ask a question about one record and get either statements that each point to a numbered, checkable source, or a plain statement that the approved sources do not answer it, with the AI's role and limits stated and the record still usable when anything fails.
- **Files changed:** `apps/web/src/components/project/{project-question,question-answer,project-detail}.tsx`, `apps/web/src/lib/qa/answer.ts`, `apps/web/src/lib/problems/browser-problem.ts` (schema library removed), `apps/web/app/[locale]/(site)/projects/[slug]/page.tsx`, `apps/web/messages/*` (domain `qa`), `apps/web/tests/**` including `support/mock-api.mjs`, `docs/FRONTEND_BUILD_ORDER.md`, and this log.
- **Backend operations/contract version:** `projects_ask_question` (OpenAPI 0.0.0 unchanged) through the existing `/api/public/questions` handler; no new route or contract change.
- **Public/private data handled:** The question is browser memory and a same-origin POST body only; it is never in a URL, storage, cookie, cache, or log, and the response is `no-store`. The page never sends private report data. Source text is rendered as inert text.
- **States implemented:** idle, loading, cancelled, supported (keyword and hybrid), several sources, insufficient, citation rejected, unreadable, rate limited, outage, offline, foreign-language answer, long text, retry success, and no JavaScript.
- **Accessibility evidence:** axe clean, 320 px and 200% reflow for eight question states in four languages on Chromium and mobile WebKit; a programmatic label and description; a polite status region; 44 px controls; no animation; keyboard submission on Chromium.
- **Locales reviewed:** `qa` is `null` in ha/ig/yo (pending, non-critical), so the panel shows the English original with `lang="en"` and a notice. I wrote no translation.
- **Performance/cache impact:** The record page's first-load JavaScript is 163.6 KB gzip against the 170 KB budget, now enforced for the record and trust pages. A first version was 252 KB because two browser modules imported a schema library; both are now hand-checked.
- **Failure behaviour verified:** malformed and unresolvable answers, uncited statements, an outage, a rate limit, offline, cancellation, duplicate submit, injected and very long text, and a hostile source link scheme.
- **Defects found and fixed:** the schema library in the browser bundle (see above); a state update inside an effect for hydration detection (replaced with `useSyncExternalStore`); the no-JavaScript message was not visible inside `<noscript>` and is now a paragraph hidden after hydration; the shared mock stats test needed to accept the question endpoint.
- **Commands run and results:** `make web-verify` exit 0 (370 unit, 90 component, bundle scan clean); `make web-e2e` 134 passed and 2 skipped (iOS WebKit Tab-to-focus); `make web-a11y` 190 passed; `pnpm audit --prod --audit-level high` clean.
- **Known limitations/open decisions:** Provider and API outages are one code. The real API and provider were not run for this circle. Client-side citation checking repeats but does not replace the backend validator.
- **Commit/PR:** `feat: add the grounded project question flow with fail-closed citations`
- **AI assistance used:** Designed and implemented the island, renderer, checker, mock scenarios, and tests; diagnosed and fixed the bundle overrun.
- **Prompt summary:** Unattended frontend/BFF build loop; maintainer directed the loop to continue through later circles.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-090 Report flow state machine, FE-091 Anonymous/contact/handle choices, FE-092 Private draft policy, FE-093 Client image preparation, FE-094 Streamed submission and retry, FE-095 One-time confirmation, FE-096 Report accessibility and E2E

- **Task:** FE-090 to FE-096 (Circle 9), delivered as one commit because they share the catalogue keys, the mock API, and one component tree.
- **User outcome delivered:** A person can report a fictional concern about a record without an account: choose how much to reveal, add optional files that are cleaned in the browser, review, send, and be shown a tracking code once, with retry that cannot create a duplicate and no private value left in the URL, storage, or cache.
- **Files changed:** `apps/web/app/[locale]/(site)/report/{page,[slug]/page,complete/page}.tsx`, `apps/web/src/components/report/*`, `apps/web/src/lib/report/{flow,draft,image-prep,submit,receipt-store}.ts`, `apps/web/messages/*` (domain `report`), `apps/web/tests/**` including `support/mock-api.mjs`, `docs/FRONTEND_BUILD_ORDER.md`, and this log.
- **Backend operations/contract version:** `reports_submit` (OpenAPI 0.0.0 unchanged) through the existing `/api/reports` handler; `projects_get` for the record title. No contract change.
- **Public/private data handled:** Private report text, optional contact, optional handle and passphrase, and files exist only in the component's memory and the one multipart body sent to the same-origin handler. The opt-in draft holds only concern and description for 24 hours. The tracking code lives only in page memory. Fictional data only. No value is logged, put in a URL, or stored, except the opt-in draft.
- **States implemented:** notice, each step with validation, file preparation and refusal, review, sending with progress, cancel, offline, unknown completion, rate limit, outage, server validation, refused credentials, partial attachment, confirmation, unrecoverable code, draft found, restored, removed, and unavailable storage, and no JavaScript.
- **Accessibility evidence:** axe clean, 320 px and 200% reflow for eight wizard states and the confirmation in four languages on Chromium and mobile WebKit; focus moves to each step heading or the error summary; a polite status region that never repeats field text; 44 px controls; reduced motion; keyboard completion on Chromium.
- **Locales reviewed:** `report` is `null` in ha/ig/yo (pending, non-critical), so those pages show the English original with `lang="en"` and a notice. I wrote no translation. This copy carries the safety and non-emergency text, so it needs the maintainer's translation pass before any real use.
- **Performance/cache impact:** First-load JavaScript for the form is 169.5 KB gzip against 170 KB (a first version was 173.9 KB; the later steps, the draft panel, the image preparation, and the submission code now load on demand). The confirmation is 164.1 KB. Both budgets are enforced by test. The report routes are dynamic, no-store, and noindex.
- **Failure behaviour verified:** dropped connection with a replayed key, rate limit, outage, server validation, refused credentials, partial attachment, cancel, offline then online, unsupported, mismatched, and surplus files, a GPS photo, a lost receipt on reload and back, unavailable and corrupt draft storage.
- **Defects found and fixed:** a draft saved after mount was deleted as dated in the future; the wait after a rate limit printed raw plural markup (a plain-variable message is used instead); an outage after an unknown completion gave no reassurance that a resend is safe; the browser test for planted metadata was too broad for WebKit's own headers; the confirmation's deferred receipt clear leaked into the next test.
- **Commands run and results:** `make web-verify` exit 0 (421 unit, 103 component, bundle scan clean); `make web-e2e` 181 passed and 3 skipped (iOS WebKit Tab-to-focus, three tests); `make web-a11y` 264 passed; `pnpm audit --prod --audit-level high` clean.
- **Known limitations/open decisions:** The real API and its file sanitation were not run; the browser suites use a fictional mock. Escalation guidance, the handle page, and the status page are later circles. Object-URL revocation and memory cleanup are implemented but not asserted. No screen-reader run.
- **Commit/PR:** `feat: add the private report flow with cleaned attachments, safe retry, and a one-time tracking code`
- **AI assistance used:** Designed and implemented the state machine, draft policy, image preparation, submission, confirmation, and mock scenarios; wrote the tests; found and fixed the defects above.
- **Prompt summary:** Unattended frontend/BFF build loop; maintainer directed the loop to continue through later circles.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-100 Tracking-code lookup, FE-101 Handle creation and one-time credentials, FE-102 Handle report list, FE-103 Handle deletion, FE-104 Tracking/handle test matrix

- **Task:** FE-100 to FE-104 (Circle 10), delivered as one commit because they share the catalogue keys, the mock API, and the request helper.
- **User outcome delivered:** A person can check a report's public-safe status with a tracking code, answer a reviewer's question, create an optional handle that is shown once, list reports by handle, and delete a handle knowing the reports stay, all without a credential ever reaching a URL, storage, or a cache.
- **Files changed:** `apps/web/app/[locale]/(site)/{track,handle}/page.tsx`, `apps/web/src/components/track/*`, `apps/web/src/lib/tracking/{client,normalise}.ts`, `apps/web/src/lib/recovery-copy.ts` and the three error and not-found boundaries, the report entry page (a link to the status page), `apps/web/messages/*` (domains `track` and `handle`), `apps/web/tests/**` including `support/mock-api.mjs`, `docs/FRONTEND_BUILD_ORDER.md`, and this log.
- **Backend operations/contract version:** `report_status_lookup`, `report_status_answer_follow_up`, `reporter_handles_create`, `reporter_handles_list_reports`, `reporter_handles_delete` (OpenAPI 0.0.0 unchanged) through the existing BFF handlers. No contract change.
- **Public/private data handled:** Tracking codes, handles, passphrases, and follow-up answers travel only in same-origin POST bodies (and an `Idempotency-Key` header where required) and live only in component memory. Responses are public-safe by contract and are re-checked by hand. Nothing is stored, logged, or cached; both routes are no-store and noindex. Fictional data only.
- **States implemented:** initial, checking, each of six statuses, follow-up open and answered, response sent, generic not-found, rate limit with wait, outage, offline, unreadable response, handle list empty and populated, one-time credentials, credentials cleared, deletion explained, confirmation required, deleted, and failed, and no JavaScript.
- **Accessibility evidence:** axe clean, 320 px and 200% reflow for the status page (initial, status with a question, failure, handle list) and the handle page (initial, created, deleted) in four languages on Chromium and mobile WebKit; focus moves to the result heading; 44 px controls; a polite status region.
- **Locales reviewed:** `track` and `handle` are `null` in ha/ig/yo (pending, non-critical), so those pages show the English original with `lang="en"` and a notice. I wrote no translation.
- **Performance/cache impact:** The status and handle pages are 151.7 KB and 150.7 KB gzip first load (budget 170 KB). Finding: the client error boundaries imported the entire English catalogue, so every page's first load had grown by about 20 KB (landing 165 KB, then 145 KB after the fix) and would have kept growing with each domain. They now import `src/lib/recovery-copy.ts`, and a unit test asserts it equals the catalogue.
- **Failure behaviour verified:** unknown code, rate limit, outage, malformed response, offline then retry, a failed answer retried with one key, wrong and missing handle indistinguishable, deletion refused generically, refresh after creating a handle.
- **Defects found and fixed:** the whole catalogue in every page's first load (above); a `getByLabel` that also matched a region; several test expectations that assumed one status was visible at a time.
- **Commands run and results:** `make web-verify` exit 0 (439 unit, 113 component, bundle scan clean); `make web-e2e` 213 passed and 3 skipped (iOS WebKit Tab-to-focus); `make web-a11y` 282 passed; `pnpm audit --prod --audit-level high` clean.
- **Known limitations/open decisions:** The real API was not run; the browser suites use a fictional mock. Follow-up answering is by tracking code only. Escalation guidance (FE-141) is a later circle. No screen-reader run.
- **Commit/PR:** `feat: add the tracking status page and reporter handle pages with one-time credentials`
- **AI assistance used:** Designed and implemented the pages, request helper, parsers, and mock scenarios; found the bundle regression and fixed it; wrote the tests.
- **Prompt summary:** Unattended frontend/BFF build loop; maintainer directed the loop to continue through later circles.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-110 Reviewer sign-in and session recovery

- **Task:** FE-110 — Reviewer sign-in and session recovery (Circle 11).
- **User outcome delivered:** An authorised reviewer can sign in with a password manager, is told generically when a sign-in fails, sees how long to wait after a rate limit, and lands only on their own queue or one report, never an arbitrary address.
- **Routes/components changed:** `apps/web/app/[locale]/reviewer/sign-in/page.tsx`, `src/components/reviewer/{frame,sign-in-form}.tsx`, `src/lib/reviewer/{safe-return,session}.ts`, `forwardedContextForHeaders` in `src/lib/bff/request-context.ts`, `messages/*` (new `reviewer` domain), `tests/support/mock-reviewer.mjs` and `mock-api.mjs`, unit, component and e2e tests.
- **Backend operations/contract version:** `auth_sign_in` and `auth_sign_out` through the existing BFF session handler (OpenAPI 0.0.0 unchanged).
- **Public/private data handled:** Reviewer credentials in one same-origin POST body and component memory only; the API's session and CSRF tokens go straight into HttpOnly cookies. Nothing in a URL, storage, log, or client bundle. Fictional demo credentials in the mock only.
- **States implemented:** initial, field validation, submitting, generic credential failure, rate limit with countdown, unreachable service, ended session and signed-out reasons, no JavaScript.
- **Accessibility evidence:** labelled fields with error association, `role="alert"` failure region, text (not colour) for the countdown; unit/component/e2e only. No axe run or screen reader run yet for this page (covered in FE-116).
- **Locales reviewed:** English only. `ha`/`ig`/`yo` `reviewer` keys are `null` and pending; nothing was translated.
- **Performance/cache impact:** Dynamic and no-store; one small client island. No public cache involvement.
- **Commands run and results:** `make web-verify` exit 0; full Chromium and mobile WebKit e2e suite 225 passed, 3 skipped (existing WebKit Tab skips) before the record was written.
- **Screenshots/traces/artifacts checked:** none captured; assertions only.
- **Known limitations/open decisions:** Real API not run. A stale cookie is not cleared by a Server Component redirect (sign-in overwrites it). No axe run yet.
- **Commit/PR:** `feat: add reviewer sign-in with safe return targets and session recovery`
- **Next task may rely on:** `ReviewerFrame`, `reviewerOptionsFor`, `requireSession`, `signInPath`, `safeReviewerTarget`, and `mock-reviewer.mjs`.
- **AI assistance used:** Designed and implemented the sign-in surface, allowlist, session helpers, mock endpoints and tests.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-111 Minimal-data reviewer queue

- **Task:** FE-111 — Minimal-data reviewer queue (Circle 11).
- **User outcome delivered:** A reviewer sees the oldest reports first as scannable cards with status, risk, dates, and counts, can filter and page through them with shareable links, and never sees report text or contact values in the list.
- **Routes/components changed:** `app/[locale]/reviewer/reports/page.tsx`, `app/[locale]/reviewer/loading.tsx`, `src/components/reviewer/queue.tsx`, `src/lib/reviewer/queue-filters.ts`, `messages/*` (`reviewer.queue`), `tests/support/{mock-reviewer.mjs,reviewer-session.ts}`, unit, component and e2e tests.
- **Backend operations/contract version:** `reviewer_reports_queue` via `serverApi().listReviewerReports` (OpenAPI 0.0.0 unchanged).
- **Public/private data handled:** Private triage projection only (identifiers, category, status, risk, dates, counts, contact-exists flag). The address holds only filters and an opaque cursor. The list is never cached, prefetched, or indexed. Fictional mock data.
- **States implemented:** results, empty, filter-empty, stale cursor, forbidden, rate limited, unavailable with retry, signed out, ended session, loading boundary.
- **Accessibility evidence:** semantic list, labelled filter controls, link names that state the report, status and risk as text with shapes, 320 px no horizontal scroll on Chromium and mobile WebKit. No axe or screen-reader run yet (FE-116).
- **Locales reviewed:** English only; `ha`/`ig`/`yo` `reviewer` keys are `null` and pending.
- **Performance/cache impact:** Server-rendered, no client JavaScript on this page beyond the shell's sign-out island; no-store.
- **Commands run and results:** `make web-verify` exit 0 (473 unit, 124 component, bundle scan clean); targeted e2e `reviewer-queue` 20 passed (Chromium and mobile WebKit).
- **Screenshots/traces/artifacts checked:** none captured.
- **Known limitations/open decisions:** The API's queue does not include a handle marker, so none is shown. Real API not run. The queue is oldest first as the API returns it; there is no sort control.
- **Commit/PR:** `feat: add the minimal-data reviewer report queue with URL-owned filters`
- **Next task may rely on:** `parseQueueFilters`/`queueQuery`/`queueHref`, `QueueList`, the mock queue and `signInAs` helper, and the report links `/{locale}/reviewer/reports/{id}`.
- **AI assistance used:** Designed and implemented the queue page, filters, components, mock data and tests.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-112 Report detail information architecture

- **Task:** FE-112 — Report detail information architecture (Circle 11).
- **User outcome delivered:** A reviewer can read one private report in a fixed, scannable order, see file safety states honestly, and reveal contact details only by choice.
- **Routes/components changed:** `app/[locale]/reviewer/reports/[reportId]/page.tsx`, `src/components/reviewer/report-detail.tsx`, `src/lib/reviewer/file-size.ts`, `messages/*` (`reviewer.detail`), mock detail endpoint in `tests/support/mock-reviewer.mjs`, component and e2e tests.
- **Backend operations/contract version:** `reviewer_reports_get` via `serverApi().getReviewerReport`, with and without `include_contact` (OpenAPI 0.0.0 unchanged).
- **Public/private data handled:** Private report text, evidence metadata, private internal reasons, follow-up answers, reviewer-only handle record, and (on request) contact. All server-rendered, no-store, never in a URL beyond the opaque report ID and the word `reveal=contact`. Fictional data only.
- **States implemented:** loaded, not found (same for malformed and unknown), forbidden, rate limited, unavailable with retry, contact hidden/shown/denied/unavailable, no evidence, no questions, no history, no handle, ended session, signed out, loading boundary.
- **Accessibility evidence:** landmarked sections with headings, an in-page jump list, definition lists, text plus shapes for status and risk, 320 px no sideways scroll on Chromium and mobile WebKit. No axe or screen-reader run yet (FE-116).
- **Locales reviewed:** English only; `ha`/`ig`/`yo` `reviewer` keys are `null` and pending.
- **Performance/cache impact:** No client JavaScript added; server-rendered and no-store.
- **Commands run and results:** `make web-verify` exit 0 (473 unit, 134 component, bundle scan clean); targeted e2e `reviewer` 54 passed (sign-in, queue, detail on Chromium and mobile WebKit).
- **Screenshots/traces/artifacts checked:** none captured.
- **Known limitations/open decisions:** A contact reveal is a GET, so the browser history keeps a `reveal=contact` entry that re-requests (and re-audits) the reveal if revisited; a POST-only reveal would need a new BFF handler and is not in the operation map. Source Scout is a stated placeholder until Circle 12. Real API not run.
- **Commit/PR:** `feat: add the reviewer report detail page with progressive contact reveal`
- **Next task may rely on:** `Section`, `detailContext`, `EvidenceSection`'s `renderDownload` slot, the mock detail data (`REPORT_IDS[0]`), and the page's section order and anchors.
- **AI assistance used:** Designed and implemented the detail page, section components, mock data and tests.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-113 Evidence download and notes

- **Task:** FE-113 — Evidence download and notes (Circle 11). It also delivers the reviewer follow-up question controls that FR-12 lists with the notes.
- **User outcome delivered:** A reviewer can download a cleaned evidence file on request, read private notes, append a note or a reporter question only after confirming it, and withdraw a question, without any private value reaching an address or storage.
- **Routes/components changed:** `src/components/reviewer/{evidence-download,note-form,question-controls,action-feedback}.tsx`, `NotesSection` and the `renderActions` slot in `report-detail.tsx`, the detail page, `messages/*` (`reviewer.actions`, `download`, `notes`, `questionActions`), mock notes, evidence and question endpoints, component and e2e tests.
- **Backend operations/contract version:** `reviewer_notes_list` (server read), `reviewer_notes_create`, `reviewer_evidence_download`, `reviewer_decisions_ask_follow_up`, `reviewer_decisions_withdraw_follow_up` through existing handlers (OpenAPI 0.0.0 unchanged).
- **Public/private data handled:** Private notes, question text, and evidence bytes. Notes and questions travel in same-origin POST bodies and component memory; evidence bytes are held in memory only for the save dialog. No storage, address, log, or cache. Fictional data only.
- **States implemented:** note and question form initial, empty, too long or short, confirming, sending, saved, failed with text kept, session ended, markup refused, outage, may-have-completed; notes empty, paged, unavailable with retry, body gone; download idle, preparing, started, failed, session ended.
- **Accessibility evidence:** labelled fields with error association, alertdialog confirmations (Cancel first), `role="status"` and `role="alert"` regions, buttons named for the file or question. Keyboard focus return after the dialogs is Base UI's default and is not yet asserted; axe and screen-reader runs are FE-116.
- **Locales reviewed:** English only; `ha`/`ig`/`yo` keys are `null` and pending.
- **Performance/cache impact:** Client islands are only on the reviewer detail page; no public page changed.
- **Commands run and results:** `make web-verify` exit 0; targeted e2e `reviewer` 68 passed (Chromium and mobile WebKit).
- **Screenshots/traces/artifacts checked:** none captured.
- **Known limitations/open decisions:** The API's note limit is inconsistent in documentation (4,000 in `docs/API.md`, 4,500 in OpenAPI); the UI enforces 4,000, the stricter. Downloads are held in memory, which is fine for the 10 MiB per-file cap. A reload after a network failure re-shows the list, which is how a reviewer checks whether a note landed.
- **Commit/PR:** `feat: add reviewer evidence download, append-only notes, and follow-up question controls`
- **Next task may rely on:** `postJson`-based reviewer mutation pattern, `ActionFeedback`, the `reviewer.actions` copy, and the mock note/question/evidence endpoints.
- **AI assistance used:** Designed and implemented the download, notes, and question components, mock endpoints, and tests.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-114 Status transition controls

- **Task:** FE-114 — Status transition controls (Circle 11).
- **User outcome delivered:** A reviewer can move a report to another status through a confirmed, version-checked action, sees exactly what the reporter will see, and can recover from a stale view without losing their text; no status change ever publishes anything.
- **Routes/components changed:** `src/components/reviewer/status-actions.tsx`, `src/lib/reviewer/transitions.ts`, the detail page's status section, `messages/*` (`reviewer.transition`), mock transition endpoint with a first-attempt race, unit, component and e2e tests.
- **Backend operations/contract version:** `reviewer_decisions_transition` through the existing handler (OpenAPI 0.0.0 unchanged).
- **Public/private data handled:** Reporter-visible message and private internal reason in a same-origin POST body and component memory only; neither is stored or placed in an address. The transition never changes the public record.
- **States implemented:** initial, field validation, confirming, pending lock, success announced, stale/not-allowed conflict with reload, session ended, may-have-completed, unknown status (no controls).
- **Accessibility evidence:** labelled fields with error association and required marking, alertdialog confirmation with Cancel first, result in a status region and failures in an alert region, keyboard Enter/Escape verified on Chromium. No axe or screen-reader run yet (FE-116).
- **Locales reviewed:** English only; `ha`/`ig`/`yo` keys are `null` and pending.
- **Performance/cache impact:** One client island on the reviewer detail only.
- **Commands run and results:** `make web-verify` exit 0; targeted e2e `reviewer` 81 passed on Chromium and mobile WebKit before the final record.
- **Screenshots/traces/artifacts checked:** none captured.
- **Known limitations/open decisions:** The frontend's copy of the allowed transitions is a usability aid and could lag a backend change until the parity test is run. iOS WebKit Tab-focus behaviour is skipped as elsewhere. The real API's problem payloads for `409` were not exercised.
- **Commit/PR:** `feat: add version-checked, confirmed reviewer status transition controls`
- **Next task may rely on:** `REVIEWER_TRANSITIONS`, `StatusActions`, and the mock `changes` state that makes a reload show the new status.
- **AI assistance used:** Designed and implemented the controls, transition table, parity test, mock endpoint and tests.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-115 Public-update composer and exact preview

- **Task:** FE-115 — Public-update composer and exact preview (Circle 11).
- **User outcome delivered:** A reviewer can write a neutral public update, choose only approved citations, see exactly what the public timeline would show, and publish that exact text after a confirmation, with stale or blocked previews refused.
- **Routes/components changed:** `src/components/reviewer/public-update-panel.tsx`, `src/components/project/update-entry.tsx` (extracted; `project-detail.tsx` now uses it), `src/lib/reviewer/publication.ts`, the detail page's public-update section, `messages/*` (`reviewer.publication`), mock draft/preview/publish/withdraw endpoints that also add a published update to the mock public record, unit, component and e2e tests.
- **Backend operations/contract version:** `reviewer_publication_list` (server read), `reviewer_publication_create_draft`, `reviewer_publication_preview`, `reviewer_publication_publish`, `reviewer_publication_withdraw` through the existing handlers (OpenAPI 0.0.0 unchanged); public project detail for citation options.
- **Public/private data handled:** The statement is authored public text; citation passages are already-public approved text. Nothing from the private report is prefilled or sent to the composer. Digests and drafts live in component memory only. Publishing revalidates the public catalogue through the existing handler.
- **States implemented:** blocked (not verified, no citations, citations unavailable), empty composer, validation, creating, preview with and without issues, publish confirmation, publishing, published, stale, discarded, draft list with reopen, malformed response, session ended, failure with may-have-completed.
- **Accessibility evidence:** labelled fields with error association and required marking, fieldset and legend for citations with per-passage descriptions, alertdialog confirmations, status and alert regions, text (not colour) for issues. No axe or screen-reader run yet (FE-116).
- **Locales reviewed:** English only; `ha`/`ig`/`yo` keys are `null` and pending. The preview itself uses the public `project`, `evidence` and `source` copy in the reviewer's language, with the usual original-language notice.
- **Performance/cache impact:** Client JavaScript only on the reviewer detail page (the shared entry and citation components ride along). The public record page renders the same markup as before; its 9 component tests and 12 browser tests pass unchanged.
- **Commands run and results:** `make web-verify` exit 0 (492 unit, 164 component, bundle scan clean); targeted e2e `reviewer project-evidence` 111 passed, three consecutive runs.
- **Screenshots/traces/artifacts checked:** none captured.
- **Known limitations/open decisions:** The API contract has no re-authentication step for publishing, so none is offered; the maintainer should decide if one is required. The statement limit is 2,000 characters per `docs/API.md` (OpenAPI allows 2,100). Citations come from the public record's facts and updates only, so a source not yet shown publicly cannot be cited from here. Preview issue codes beyond those in `docs/API.md` show as an unrecognised issue with its code.
- **Commit/PR:** `feat: add the public-update composer with exact preview and digest-confirmed publishing`
- **Next task may rely on:** `PublicUpdateEntry`/`StatementClaim`/`citationView`, `parsePreview`, `citationOptions`, and the mock publication endpoints.
- **AI assistance used:** Designed and implemented the composer, shared entry extraction, parser, mock endpoints and tests.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-116 Reviewer security, accessibility, and E2E

- **Task:** FE-116 — Reviewer security/accessibility/E2E (Circle 11).
- **User outcome delivered:** The reviewer workspace is proven safe and usable end to end: unauthorised, cross-origin, and CSRF-less requests are refused, sign-out leaves nothing behind, and the pages pass axe, phone-width, 200% text, and keyboard checks in four languages.
- **Routes/components changed:** `tests/e2e/reviewer-security.spec.ts`, `tests/a11y/reviewer.a11y.spec.ts`, the every-transition component test, and one fix: the report-detail failure and not-found states now have a page heading.
- **Backend operations/contract version:** No operation added; OpenAPI 0.0.0 unchanged.
- **Public/private data handled:** Fictional data only. Tests assert that no report text, contact, note, internal reason, or password reaches the console, storage, a URL, a public page, or a public cache.
- **States implemented:** covered by earlier tasks; this task adds the session-without-CSRF, cross-origin, sign-out, back-navigation, and direct-URL states.
- **Accessibility evidence:** `make web-a11y` 312 passed (Chromium and mobile WebKit): axe, 320 px reflow, and 200% text for the reviewer sign-in states, queue states, and detail states in en, ha, ig, and yo, and for the actions, note and status confirmations, composer, preview, and publish confirmation in English; a 44 px control check. One real violation fixed (no page heading on failure states). A narrow, documented exclusion of Base UI focus-guard spans on WebKit in dialog checks.
- **Locales reviewed:** en, ha, ig, yo routes and shell audited. Reviewer body copy in ha/ig/yo is `null` (pending), so those pages show the English original with a notice; no translation was written or claimed.
- **Performance/cache impact:** Reviewer routes are dynamic, no-store, and outside public caches; client JavaScript is only on reviewer pages; `bundle:check` clean (33 chunks).
- **Commands run and results:** `make web-verify` exit 0 (492 unit and 179 component tests in total, message parity, contract drift, client-boundary scan); `make web-e2e` 320 passed and 6 skipped (iOS WebKit Tab-focus, three existing and three new; 110 of the runs are the reviewer's, 55 tests on two browsers); `make web-a11y` 312 passed (30 runs are the reviewer's); the five Circle 0 frontend validators and the workflow validator pass.
- **Screenshots/traces/artifacts checked:** none captured (assertions only); traces are retained only on failure and contain fictional data.
- **Known limitations/open decisions:** Real API not run against these flows; screen-reader output not tested; a contact reveal is a GET (history entry re-audits); the API contract has no re-authentication step for publishing; hidden Tab-focus behaviour on iOS WebKit is skipped; Source Scout for a report is a stated placeholder until Circle 12.
- **Commit/PR:** `test: prove reviewer security, accessibility, and keyboard behaviour end to end`
- **Next task may rely on:** the reviewer detail page's section slots (`scout`), `ReviewerFrame`, the mock reviewer API, `auditDialog`, and `signInAs`.
- **AI assistance used:** Wrote the security, keyboard, and accessibility suites; diagnosed and fixed the missing-heading defect and test races.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-120 Shared discovery state model

- **Task:** FE-120 — Shared discovery state model (Circle 12).
- **User outcome delivered:** Residents and reviewers now have one contract-bound client model for discovery progress that never manufactures a percentage, prolongs an unknown run, enables an unavailable public cancellation, or lets a late/private response replace the active panel.
- **Routes/components changed:** Added `apps/web/src/lib/discovery/run-state.ts` and `tests/unit/discovery-run-state.test.ts`; no route or visible surface changes in this model-only task.
- **Backend operations/contract version:** The existing `discovery_get_public_run` and `reviewer_discovery_get` handoff is modelled without changing OpenAPI 0.0.0, generated types, BFF handlers, or FastAPI policy.
- **Public/private data handled:** The model retains only a run ID, scope, and version in current component memory. Both scopes are explicitly no-store and non-persistent; no run ID is made URL state, and a public/reviewer scope or run-ID mismatch rejects a response.
- **States implemented:** Exact `queued`, `searching`, `analysing`, `needs_review`, `complete`, `failed`, and `cancelled` recognition; 2/3/5/8/10-second polling; valid `Retry-After` precedence; public polling through `needs_review`; reviewer stop at `needs_review`; cancellation-request polling until an API terminal result; reviewer-only cancel/review availability; unknown status fail-closed; and stale-version rejection.
- **Accessibility evidence:** No visible control exists yet. The later panels must expose the returned stage/counts through calm status announcements; this model deliberately provides no invented percentage or motion state.
- **Locales reviewed:** No user-facing copy, translation, or route changed. The next visible tasks must supply all four locale keys and retain the existing human-review status.
- **Performance/cache impact:** A small dependency-free TypeScript module only; no network request, timer, browser storage, cache, image, font, or client dependency is added.
- **Commands run and results:** `pnpm --dir apps/web exec vitest run --project unit tests/unit/discovery-run-state.test.ts` passed (6 tests); `pnpm --dir apps/web typecheck`, `lint`, and `format:check` passed; `git diff --check` passed.
- **Screenshots/traces/artifacts checked:** None applicable: there is no rendered surface in this task.
- **Known limitations/open decisions:** The API's loosely typed `analysis` and result payloads require explicit fail-closed presentation parsers in FE-123. Public cancellation is not exposed because no public cancellation operation exists. Real API polling is not exercised yet.
- **Commit/PR:** `feat: model Source Scout run state safely`
- **Next task may rely on:** `DISCOVERY_STATUSES`, `shouldPoll`, `allowedDiscoveryActions`, `nextPollDelayMs`, `isNewerRunSnapshot`, and `RUN_MEMORY_POLICY`; it must still use the generated DTOs and purpose-built BFF routes.
- **AI assistance used:** Implemented the scope-aware state model and adversarial unit tests from the accepted contract and privacy rules.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-121 Public project discovery panel

- **Task:** FE-121 — Public project discovery panel (Circle 12).
- **User outcome delivered:** A resident can request bounded public-source discovery from a project record, understand that it uses the public record only and remains unverified, see the real returned stage/counts and replay label, and stop future checks on their page without being told that the server work was cancelled.
- **Routes/components changed:** Added `ProjectDiscovery` to `/{locale}/projects/{slug}`, its component and browser tests, public discovery fixtures in the mock API, and the `project.discovery` message domain.
- **Backend operations/contract version:** Uses existing `discovery_start_public_run` and `discovery_get_public_run` only through `/api/public/discovery` and `/api/public/discovery/{runId}`. OpenAPI 0.0.0, generated code, FastAPI, and BFF policy are unchanged.
- **Public/private data handled:** The browser sends only `{ slug }` to the same-origin BFF. Run IDs, versions, and results remain component-memory-only, are never put in a URL/storage/cache, and no report/contact/attachment/tracking text is rendered or sent. The panel declares that boundary before the request.
- **States implemented:** idle, start pending, returned run, unavailable/budget-style no-run, malformed-result fail-closed, network/problem retry, terminal stop, and page-local paused checking. Real backend stage/counts replace percentages; an unknown response is not rendered.
- **Accessibility evidence:** The panel has a labelled section, semantic status text, a polite announcement region, named native controls, no colour-only state, and retains the existing Field Ledger reflow rules. Targeted axe/reflow tests passed for full/minimal records in Chromium and mobile WebKit at 320 px and 200% text.
- **Locales reviewed:** English source copy was added. `ha`, `ig`, and `yo` have matching pending keys and therefore show the existing explicit English-original treatment; no translation was written or claimed.
- **Performance/cache impact:** A small client island is loaded only on project detail. Requests use `no-store`; no polling begins until the resident asks, and there is no image, analytics, provider, persistent cache, or new dependency.
- **Commands run and results:** targeted component test passed (3); `pnpm --dir apps/web typecheck`, `lint`, `format:check`, and `contract` passed; production E2E exercised both new paths in Chromium and mobile WebKit; targeted axe/reflow passed 4 runs; Impeccable detector returned no findings; `git diff --check` passed.
- **Screenshots/traces/artifacts checked:** Production browser harness covered desktop/mobile rendering; no committed screenshot or trace contains discovery data. The panel uses clearly fictional replay fixture data only.
- **Known limitations/open decisions:** Public cancellation is not an API operation, so the control stops only client polling. Results/provenance and analysis are intentionally deferred to FE-123, as is explicit shared-run action wording from the returned DTO. Real API/provider execution is not claimed.
- **Commit/PR:** `feat: add the public Source Scout panel`
- **Next task may rely on:** `ProjectDiscovery`, its narrow parser and no-store memory boundary, the mock public discovery endpoints, and the shared run-state model. It must not display results as approved evidence.
- **AI assistance used:** Implemented the Field Ledger panel, safe response parsing, fixtures, and browser/component coverage from the accepted contract.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-122 Reviewer query preview and approval

- **Task:** FE-122 — Reviewer query preview and approval (Circle 12).
- **User outcome delivered:** A reviewer can prepare, inspect, discard, or explicitly approve the exact privacy-safe outbound discovery query before a private search run starts.
- **Routes/components changed:** Added `src/components/reviewer/discovery-preview.tsx` inside the existing report-detail Scout section, matching `reviewer.detail.scout` locale keys, reviewer discovery mock fixtures, and focused component/E2E tests.
- **Backend operations/contract version:** Existing `reviewer_discovery_plan` and `reviewer_discovery_create` BFF operations only; OpenAPI 0.0.0 and generated client remain unchanged.
- **Public/private data handled:** The client island receives an opaque report ID only. It sends reviewer-entered public concepts and the backend-issued plan digest through same-origin no-store requests. It never receives or stores report text, contacts, evidence, tracking data, or a precise location.
- **States implemented:** idle, plan preparation, exact plan review, revision requiring a new plan, discard, approval confirmation, create pending, started acknowledgement, malformed response, session-ended, and retryable failure.
- **Accessibility evidence:** Labels and help text bind to the only editable field and read-only query; exact-query approval uses a named alertdialog; success is a status region and failures an alert region; native controls retain keyboard operation.
- **Locales reviewed:** English source keys added; matching `null` keys for Hausa, Igbo, and Yoruba remain pending and receive the established English-original notice.
- **Performance/cache impact:** One reviewer-only client island; no new dependency, provider request, browser storage, query-string state, analytics, or cache.
- **Commands run and results:** focused component test passed (2); targeted Chromium/mobile-WebKit E2E passed (2); `make web-verify` passed (498 unit, 184 component, message parity, contract drift, production build, and client-boundary scan).
- **Known limitations/open decisions:** The backend remains authoritative for rejecting unsafe concepts and deciding query construction. Results, cancellation, provenance, analysis, and source decisions are intentionally implemented by FE-123 through FE-126.
- **Commit/PR:** `feat: add reviewer discovery query approval`.
- **AI assistance used:** Implemented the review flow, narrow parser, fictional boundary fixture, and tests.
- **Prompt summary:** Complete Circle 12 unattended.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-123 Results, provenance, and analysis

- **Task:** FE-123 — Results, provenance, and analysis (Circle 12). Delivered in one commit with FE-123 to FE-126 because the shared readers, cards, and run view are the same change.
- **User outcome delivered:** A resident or reviewer sees at most ten discovered sources, each labelled unreviewed with provenance dates and a safe original link, and an analysis kept apart from them that cites only this run's sources.
- **Routes/components changed:** `src/lib/discovery/parse.ts`, `src/components/discovery/results.tsx`, the public panel and reviewer run view, `messages/*` (`discovery`), mock discovery data, unit, component, e2e and a11y tests.
- **Backend operations/contract version:** `discovery_get_public_run`, `reviewer_discovery_get` (OpenAPI 0.0.0 unchanged).
- **Public/private data handled:** Public discovered-source metadata and excerpts (inert text); reviewer runs are private and never cached.
- **States implemented:** results, no results, cap, flagged page, unsafe link, duplicates, invalid analysis, unavailable analysis
- **Accessibility evidence:** axe, 320 px, and 200% text across the public and reviewer Source Scout states in en, ha, ig, and yo, plus the confirmation dialogs (with the documented Base UI focus-guard exclusion) and cancelled state; labelled fields, status and alert regions, text (not colour) for every state.
- **Locales reviewed:** English only; the new `discovery` domain is `null` in ha/ig/yo (pending), so those pages show the English original with a notice. No translation written or claimed.
- **Performance/cache impact:** Client islands only on the reviewer report page and the project page; every run response is no-store and held in memory only.
- **Commands run and results:** `make web-verify` exit 0 (509 unit and 197 component tests in total, message parity, bundle scan); `make web-e2e` 358 passed and 6 skipped; `make web-a11y` 330 passed. The `public-cache` browser file is order-sensitive on a warm build (its shared mock counters are reset by the parallel project) and fails when run alone repeatedly, on the previous commit too; it passes in the full suite.
- **Screenshots/traces/artifacts checked:** none captured.
- **Known limitations/open decisions:** Real API and provider not run (fictional mock and recorded replay only); `analysis`/`result` are free-form in OpenAPI, so their documented shape from the plan and fixtures is checked strictly and anything else shows no analysis; no screen-reader pass.
- **AI assistance used:** Took over the in-progress Source Scout work, replaced the partial results rendering with shared strict readers and components, and wrote the mocks and tests.
- **Commit/PR:** `feat: show discovered sources and analysis, follow-ups, decisions, and failure states for Source Scout`
- **Next task may rely on:** `parseRun`, `SourceList`, `AnalysisSections`, `RunSummary`, `RunOutcome`.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-124 Follow-up questions

- **Task:** FE-124 — Follow-up questions (Circle 12). Delivered in one commit with FE-123 to FE-126 because the shared readers, cards, and run view are the same change.
- **User outcome delivered:** A reviewer can answer, skip, or flag each of up to five follow-up questions without the answer ever leaving component memory except in one POST body.
- **Routes/components changed:** `DiscoveryRun` in `src/components/reviewer/discovery-run.tsx`, tests.
- **Backend operations/contract version:** `reviewer_discovery_answer_follow_up` (OpenAPI 0.0.0 unchanged).
- **Public/private data handled:** Private answers in one same-origin POST body; never in an address, storage, log, or page afterwards.
- **States implemented:** initial, required, too long, sending, acknowledged, skipped, flagged, wrong-run refusal, error
- **Accessibility evidence:** axe, 320 px, and 200% text across the public and reviewer Source Scout states in en, ha, ig, and yo, plus the confirmation dialogs (with the documented Base UI focus-guard exclusion) and cancelled state; labelled fields, status and alert regions, text (not colour) for every state.
- **Locales reviewed:** English only; the new `discovery` domain is `null` in ha/ig/yo (pending), so those pages show the English original with a notice. No translation written or claimed.
- **Performance/cache impact:** Client islands only on the reviewer report page and the project page; every run response is no-store and held in memory only.
- **Commands run and results:** `make web-verify` exit 0 (509 unit and 197 component tests in total, message parity, bundle scan); `make web-e2e` 358 passed and 6 skipped; `make web-a11y` 330 passed. The `public-cache` browser file is order-sensitive on a warm build (its shared mock counters are reset by the parallel project) and fails when run alone repeatedly, on the previous commit too; it passes in the full suite.
- **Screenshots/traces/artifacts checked:** none captured.
- **Known limitations/open decisions:** Real API and provider not run (fictional mock and recorded replay only); `analysis`/`result` are free-form in OpenAPI, so their documented shape from the plan and fixtures is checked strictly and anything else shows no analysis; no screen-reader pass.
- **AI assistance used:** Took over the in-progress Source Scout work, replaced the partial results rendering with shared strict readers and components, and wrote the mocks and tests.
- **Commit/PR:** `feat: show discovered sources and analysis, follow-ups, decisions, and failure states for Source Scout`
- **Next task may rely on:** the run-bound `FollowUp` pattern.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-125 Reviewer source decisions

- **Task:** FE-125 — Reviewer source decisions (Circle 12). Delivered in one commit with FE-123 to FE-126 because the shared readers, cards, and run view are the same change.
- **User outcome delivered:** A reviewer can attach, reject, defer, or reconsider a discovered source with a reason and a confirmation, with attach clearly creating only a pending source.
- **Routes/components changed:** `SourceDecision` in `discovery-run.tsx`, tests.
- **Backend operations/contract version:** `reviewer_discovery_decide_source`, `reviewer_discovery_review` (OpenAPI 0.0.0 unchanged).
- **Public/private data handled:** Private reasons in same-origin POST bodies only.
- **States implemented:** allowed decisions per disposition, reason required, confirming, recorded, conflict reload, run approve and reject
- **Accessibility evidence:** axe, 320 px, and 200% text across the public and reviewer Source Scout states in en, ha, ig, and yo, plus the confirmation dialogs (with the documented Base UI focus-guard exclusion) and cancelled state; labelled fields, status and alert regions, text (not colour) for every state.
- **Locales reviewed:** English only; the new `discovery` domain is `null` in ha/ig/yo (pending), so those pages show the English original with a notice. No translation written or claimed.
- **Performance/cache impact:** Client islands only on the reviewer report page and the project page; every run response is no-store and held in memory only.
- **Commands run and results:** `make web-verify` exit 0 (509 unit and 197 component tests in total, message parity, bundle scan); `make web-e2e` 358 passed and 6 skipped; `make web-a11y` 330 passed. The `public-cache` browser file is order-sensitive on a warm build (its shared mock counters are reset by the parallel project) and fails when run alone repeatedly, on the previous commit too; it passes in the full suite.
- **Screenshots/traces/artifacts checked:** none captured.
- **Known limitations/open decisions:** Real API and provider not run (fictional mock and recorded replay only); `analysis`/`result` are free-form in OpenAPI, so their documented shape from the plan and fixtures is checked strictly and anything else shows no analysis; no screen-reader pass.
- **AI assistance used:** Took over the in-progress Source Scout work, replaced the partial results rendering with shared strict readers and components, and wrote the mocks and tests.
- **Commit/PR:** `feat: show discovered sources and analysis, follow-ups, decisions, and failure states for Source Scout`
- **Next task may rely on:** the disposition-driven decision controls.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-126 Discovery failure, offline, and tests

- **Task:** FE-126 — Discovery failure, offline, and tests (Circle 12). Delivered in one commit with FE-123 to FE-126 because the shared readers, cards, and run view are the same change.
- **User outcome delivered:** Discovery failures, cancellation, budget exhaustion, and going offline are explained and usable, polling stops, and public and report runs never cross.
- **Routes/components changed:** `DiscoveryRun`, `ProjectDiscovery`, mocks with scenario switches, unit, component, e2e and a11y tests.
- **Backend operations/contract version:** `discovery_start_public_run`, `discovery_get_public_run`, `reviewer_discovery_get`, `reviewer_discovery_cancel`, `reviewer_discovery_review` (OpenAPI 0.0.0 unchanged).
- **Public/private data handled:** Nothing stored; run responses no-store; scopes isolated.
- **States implemented:** failed, cancelled partial, budget exhausted, dead letter, offline, outage with retry, stale, needs review, terminal stop
- **Accessibility evidence:** axe, 320 px, and 200% text across the public and reviewer Source Scout states in en, ha, ig, and yo, plus the confirmation dialogs (with the documented Base UI focus-guard exclusion) and cancelled state; labelled fields, status and alert regions, text (not colour) for every state.
- **Locales reviewed:** English only; the new `discovery` domain is `null` in ha/ig/yo (pending), so those pages show the English original with a notice. No translation written or claimed.
- **Performance/cache impact:** Client islands only on the reviewer report page and the project page; every run response is no-store and held in memory only.
- **Commands run and results:** `make web-verify` exit 0 (509 unit and 197 component tests in total, message parity, bundle scan); `make web-e2e` 358 passed and 6 skipped; `make web-a11y` 330 passed. The `public-cache` browser file is order-sensitive on a warm build (its shared mock counters are reset by the parallel project) and fails when run alone repeatedly, on the previous commit too; it passes in the full suite.
- **Screenshots/traces/artifacts checked:** none captured.
- **Known limitations/open decisions:** Real API and provider not run (fictional mock and recorded replay only); `analysis`/`result` are free-form in OpenAPI, so their documented shape from the plan and fixtures is checked strictly and anything else shows no analysis; no screen-reader pass.
- **AI assistance used:** Took over the in-progress Source Scout work, replaced the partial results rendering with shared strict readers and components, and wrote the mocks and tests.
- **Commit/PR:** `feat: show discovered sources and analysis, follow-ups, decisions, and failure states for Source Scout`
- **Next task may rely on:** the scenario switches in `mock-discovery.mjs`, `mock-reviewer.mjs`, and `mock-api.mjs`.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-130 Manifest and installability

- **Task:** FE-130 — Manifest and installability (Circle 13). Initially recorded blocked for lack of an approved icon; the maintainer then asked for a simple letter icon and logo, which were made and the task completed.
- **User outcome delivered:** The app has a valid web app manifest, a simple letter-mark icon set (any, maskable, Apple touch) and a logo, so it can be installed.
- **Routes/components changed:** `apps/web/app/manifest.ts`, icon metadata in the locale layout, `public/icons/*` (SVG and PNG), `scripts/render-icons.mjs`, unit and e2e tests.
- **Backend operations/contract version:** none.
- **Public/private data handled:** none; the manifest is static and public.
- **States implemented:** served, linked, start address resolves to a locale.
- **Accessibility evidence:** not applicable to a manifest.
- **Locales reviewed:** English manifest strings; the start address resolves to any of the four locales.
- **Performance/cache impact:** one small static JSON file.
- **Commands run and results:** `make web-verify` exit 0 (512 unit tests in total); targeted e2e `pwa-manifest` 4 passed (Chromium and mobile WebKit).
- **Screenshots/traces/artifacts checked:** none.
- **Known limitations/open decisions:** The mark is a plain letter S with a double rule, made on the maintainer's instruction; it has had no other visual review. No real install prompt was exercised. The wordmark in `logo.svg` is live text in a generic serif stack, not outlined.
- **Commit/PR:** `feat: add the ShaidaGo letter-mark icons and logo to the manifest`
- **Next task may rely on:** `/manifest.webmanifest` and the approved colours.
- **AI assistance used:** Wrote the manifest and tests; declined to invent an icon.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-131 Explicit service-worker allowlist

- **Task:** FE-131 — Explicit service-worker allowlist (Circle 13). Delivered in one commit with the other service-worker task because they share the worker and the offline page.
- **User outcome delivered:** Recently viewed public pages and framework files are saved for weak connections, and nothing private is ever stored.
- **Routes/components changed:** `public/sw.js`, `public/sw-policy.js`, `next.config.ts` headers, `src/components/pwa/pwa-support.tsx`, unit and e2e tests.
- **Backend operations/contract version:** none (public pages and static files only).
- **Public/private data handled:** Only public catalogue HTML and framework files are stored; cache inspection proves no private URL, body, header, or canary.
- **States implemented:** stored, refused (no-store/private/cookie/redirect/opaque/oversize), stale-while-revalidate, network-first with timeout, error fallback
- **Accessibility evidence:** not applicable to the worker itself
- **Locales reviewed:** English only; the `offline` domain is `null` in ha/ig/yo (pending), so those pages show the English original with a notice.
- **Performance/cache impact:** One small client island on public pages (registration and banner); the worker file is `no-cache`; public pages are revalidated on every request.
- **Commands run and results:** `make web-verify` exit 0 (551 unit tests in total); `make web-e2e` 373 passed and 7 skipped; targeted a11y `offline` 8 passed. (Test count in the FE-131 note: 39 policy unit tests.)
- **Screenshots/traces/artifacts checked:** none captured.
- **Known limitations/open decisions:** Production CDN behaviour not tested; caching relies on Next honouring the `headers()` override for the public routes.
- **Commit/PR:** `feat: add the explicit-allowlist service worker, offline page, and update notice`
- **Next task may rely on:** `SG_POLICY`, the `sg-*-v1` caches, `PwaSupport`, and the `offline` copy domain.
- **AI assistance used:** Wrote the worker, policy, components, and the cache-inspection tests.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-132 Offline and update UX

- **Task:** FE-132 — Offline and update UX (Circle 13). Delivered in one commit with the other service-worker task because they share the worker and the offline page.
- **User outcome delivered:** A reader can revisit a saved public record offline with its saved time, gets a useful offline page otherwise, and is never told a private action succeeded offline.
- **Routes/components changed:** `app/[locale]/(site)/offline/page.tsx`, `src/components/pwa/*`, `messages/*` (`offline`), unit, e2e and a11y tests.
- **Backend operations/contract version:** none.
- **Public/private data handled:** Saved public pages only, in this browser's Cache Storage; no private data.
- **States implemented:** saved copy with date, unsaved offline page, private routes unavailable, update waiting, back online, cleared saved pages
- **Accessibility evidence:** 8 axe runs (four languages) at 320 px and 200% text for the offline page
- **Locales reviewed:** English only; the `offline` domain is `null` in ha/ig/yo (pending), so those pages show the English original with a notice.
- **Performance/cache impact:** One small client island on public pages (registration and banner); the worker file is `no-cache`; public pages are revalidated on every request.
- **Commands run and results:** `make web-verify` exit 0 (551 unit tests in total); `make web-e2e` 373 passed and 7 skipped; targeted a11y `offline` 8 passed. (Test count in the FE-131 note: 39 policy unit tests.)
- **Screenshots/traces/artifacts checked:** none captured.
- **Known limitations/open decisions:** WebKit offline with a service worker is not testable in Playwright; the update prompt is not driven end to end; ha/ig/yo copy pending.
- **Commit/PR:** `feat: add the explicit-allowlist service worker, offline page, and update notice`
- **Next task may rely on:** `SG_POLICY`, the `sg-*-v1` caches, `PwaSupport`, and the `offline` copy domain.
- **AI assistance used:** Wrote the worker, policy, components, and the cache-inspection tests.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-133 Low-data mode

- **Task:** FE-133 — Low-data mode (Circle 13).
- **User outcome delivered:** A reader on a costly connection can turn on a low-data mode that removes motion and slows background refreshing and polling, keeping every fact and action, and the browser's saved-data hint is only a suggestion.
- **Routes/components changed:** `src/lib/low-data.ts`, `src/components/pwa/low-data-control.tsx`, the locale layout head script, `app/globals.css`, polling in the two Source Scout panels, `messages/*` (`offline.lowData`), unit, component and e2e tests.
- **Backend operations/contract version:** none.
- **Public/private data handled:** One functional preference cookie holding `1` or `0`; no identifier, never sent to an API.
- **States implemented:** off, on, suggested by the browser, dismissed, explicit off respected.
- **Accessibility evidence:** the switch is a button with `aria-pressed` and a polite status; motion is fully off. Covered by the public-page axe suites.
- **Locales reviewed:** English only; `offline.lowData` is `null` in ha/ig/yo (pending).
- **Performance/cache impact:** A four-line inline head script and one small client island; the mode saves little today because the app ships no images or web fonts.
- **Commands run and results:** `make web-verify` exit 0; targeted e2e `low-data` 12 passed (Chromium and mobile WebKit).
- **Screenshots/traces/artifacts checked:** none captured.
- **Known limitations/open decisions:** Nothing to remove yet (no images or web fonts). The cookie is set from JavaScript, so it does not exist for visitors who never turn the mode on. A hydration mismatch it caused was fixed with a server-safe external-store read.
- **Commit/PR:** `feat: add low-data mode with a plain preference cookie`
- **Next task may rely on:** `applyLowData`, `scaleDelay`, and `data-low-data` on `<html>`.
- **AI assistance used:** Designed and implemented the mode, and diagnosed the hydration mismatch.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-134 Network resilience

- **Task:** FE-134 — Network resilience (Circle 13).
- **User outcome delivered:** On a poor or flapping connection, Source Scout checking keeps going or stops cleanly, a stuck read is abandoned and can be retried, and pressing a button twice or losing the connection never makes duplicate work or silently loses what was typed.
- **Routes/components changed:** `src/lib/net/timeout.ts`, polling in `project-discovery.tsx` and `discovery-run.tsx`, mock scenarios (a second progressing public run), unit and e2e tests.
- **Backend operations/contract version:** `discovery_start_public_run`, `discovery_get_public_run`, `reviewer_discovery_get`, `projects_ask_question` (unchanged).
- **Public/private data handled:** none new; nothing stored.
- **States implemented:** offline mid-read, flapping, reconnect, not modified, stuck read, retry, offline before a mutation, back online.
- **Accessibility evidence:** status and alert regions announce state changes; covered by the existing axe suites (`make web-a11y` 338 passed).
- **Locales reviewed:** no new copy.
- **Performance/cache impact:** Polling is bounded and scheduled per attempt; reads time out at ten seconds.
- **Commands run and results:** `make web-verify` exit 0 (558 unit and 201 component tests in total); `make web-e2e` 395 passed and 9 skipped; `make web-a11y` 338 passed.
- **Screenshots/traces/artifacts checked:** none captured.
- **Known limitations/open decisions:** No throttled slow-3G profile; the stuck-read test and the offline-with-service-worker tests are Chromium-only because of Playwright WebKit limitations (stated in the tests).
- **Commit/PR:** `fix: keep Source Scout checking through flapping connections and bound browser reads`
- **Next task may rely on:** `withTimeout`, `CLIENT_READ_TIMEOUT_MS`, the per-attempt polling pattern, and `progressSlug`.
- **AI assistance used:** Found the stopped-polling defect while writing the resilience tests and fixed it.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-140 Full accessibility audit

- **Task:** FE-140 — Full accessibility audit (Circle 14). Status: partial. Delivered in one commit with the other Circle 14 tasks; the evidence document is `docs/FRONTEND_HARDENING_AUDIT.md`.
- **User outcome delivered:** Structure, forced-colours, reduced-motion, and touch-target checks pass on all routes in four languages; the manual screen-reader smoke is scripted but not run.
- **Routes/components changed:** `tests/a11y/structure.a11y.spec.ts`.
- **Backend operations/contract version:** none.
- **Public/private data handled:** No new data; the checks assert nothing private reaches a URL, storage, log, cache, or another origin.
- **States implemented:** as audited in the evidence document.
- **Accessibility evidence:** `make web-a11y` 356 passed (Chromium and mobile WebKit).
- **Locales reviewed:** Chromium and mobile WebKit; `make web-a11y` 356 passed.. Fluent review of Hausa, Igbo, and Yoruba has not been obtained.
- **Performance/cache impact:** see the budgets in `docs/FRONTEND_HARDENING_AUDIT.md`.
- **Commands run and results:** `make web-verify` exit 0 (563 unit and 201 component tests in total); `make web-e2e` 422 passed and 10 skipped; `make web-a11y` 356 passed. A first combined run failed only because two suites were started at once on the same ports; the suites were rerun one at a time.
- **Screenshots/traces/artifacts checked:** none captured.
- **Known limitations/open decisions:** Manual desktop and mobile screen-reader smoke needs a person; iOS WebKit Tab focus skipped.
- **Commit/PR:** `feat: harden security headers, budgets, and the composed accessibility and device checks`
- **Next task may rely on:** the evidence document, `SECURITY_HEADERS`, the route budgets, and the structure suite.
- **AI assistance used:** Wrote the audits and tests, found and fixed the catalogue-in-client-bundle regression.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-141 Four-language and content stress pass

- **Task:** FE-141 — Four-language and content stress pass (Circle 14). Status: partial. Delivered in one commit with the other Circle 14 tasks; the evidence document is `docs/FRONTEND_HARDENING_AUDIT.md`.
- **User outcome delivered:** Long unbroken strings and maximum-length inputs wrap at 320 px in every language; translation status is recorded and visible; no fluent review obtained.
- **Routes/components changed:** `tests/a11y/structure.a11y.spec.ts`, `messages/status.json` (read).
- **Backend operations/contract version:** none.
- **Public/private data handled:** No new data; the checks assert nothing private reaches a URL, storage, log, cache, or another origin.
- **States implemented:** as audited in the evidence document.
- **Accessibility evidence:** `make web-a11y` 356 passed (Chromium and mobile WebKit).
- **Locales reviewed:** four languages. Fluent review of Hausa, Igbo, and Yoruba has not been obtained.
- **Performance/cache impact:** see the budgets in `docs/FRONTEND_HARDENING_AUDIT.md`.
- **Commands run and results:** `make web-verify` exit 0 (563 unit and 201 component tests in total); `make web-e2e` 422 passed and 10 skipped; `make web-a11y` 356 passed. A first combined run failed only because two suites were started at once on the same ports; the suites were rerun one at a time.
- **Screenshots/traces/artifacts checked:** none captured.
- **Known limitations/open decisions:** Fluent Hausa, Igbo, and Yoruba review of critical copy is a maintainer action.
- **Commit/PR:** `feat: harden security headers, budgets, and the composed accessibility and device checks`
- **Next task may rely on:** the evidence document, `SECURITY_HEADERS`, the route budgets, and the structure suite.
- **AI assistance used:** Wrote the audits and tests, found and fixed the catalogue-in-client-bundle regression.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-142 Responsive and device matrix

- **Task:** FE-142 — Responsive and device matrix (Circle 14). Status: partial. Delivered in one commit with the other Circle 14 tasks; the evidence document is `docs/FRONTEND_HARDENING_AUDIT.md`.
- **User outcome delivered:** No page scrolls sideways at seven device sizes in four languages, including dense reviewer data.
- **Routes/components changed:** `tests/a11y/structure.a11y.spec.ts`.
- **Backend operations/contract version:** none.
- **Public/private data handled:** No new data; the checks assert nothing private reaches a URL, storage, log, cache, or another origin.
- **States implemented:** as audited in the evidence document.
- **Accessibility evidence:** `make web-a11y` 356 passed (Chromium and mobile WebKit).
- **Locales reviewed:** seven sizes. Fluent review of Hausa, Igbo, and Yoruba has not been obtained.
- **Performance/cache impact:** see the budgets in `docs/FRONTEND_HARDENING_AUDIT.md`.
- **Commands run and results:** `make web-verify` exit 0 (563 unit and 201 component tests in total); `make web-e2e` 422 passed and 10 skipped; `make web-a11y` 356 passed. A first combined run failed only because two suites were started at once on the same ports; the suites were rerun one at a time.
- **Screenshots/traces/artifacts checked:** none captured.
- **Known limitations/open decisions:** No physical low-end device, on-screen keyboard, or safe-area test.
- **Commit/PR:** `feat: harden security headers, budgets, and the composed accessibility and device checks`
- **Next task may rely on:** the evidence document, `SECURITY_HEADERS`, the route budgets, and the structure suite.
- **AI assistance used:** Wrote the audits and tests, found and fixed the catalogue-in-client-bundle regression.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-143 Client privacy and security audit

- **Task:** FE-143 — Client privacy and security audit (Circle 14). Status: complete. Delivered in one commit with the other Circle 14 tasks; the evidence document is `docs/FRONTEND_HARDENING_AUDIT.md`.
- **User outcome delivered:** Every response carries a strict same-origin CSP and the frame, referrer, sniffing, permissions, and opener headers; hostile content never runs; nothing third-party loads; nothing private is left in the browser.
- **Routes/components changed:** `next.config.ts`, `proxy.ts`, `src/lib/bff/problem.ts`, `tests/e2e/client-security.spec.ts`.
- **Backend operations/contract version:** none.
- **Public/private data handled:** No new data; the checks assert nothing private reaches a URL, storage, log, cache, or another origin.
- **States implemented:** as audited in the evidence document.
- **Accessibility evidence:** `make web-a11y` 356 passed (Chromium and mobile WebKit).
- **Locales reviewed:** Chromium and mobile WebKit. Fluent review of Hausa, Igbo, and Yoruba has not been obtained.
- **Performance/cache impact:** see the budgets in `docs/FRONTEND_HARDENING_AUDIT.md`.
- **Commands run and results:** `make web-verify` exit 0 (563 unit and 201 component tests in total); `make web-e2e` 422 passed and 10 skipped; `make web-a11y` 356 passed. A first combined run failed only because two suites were started at once on the same ports; the suites were rerun one at a time.
- **Screenshots/traces/artifacts checked:** none captured.
- **Known limitations/open decisions:** `'unsafe-inline'` remains for scripts and styles (recorded trade-off); HSTS is unproven on a deployed origin.
- **Commit/PR:** `feat: harden security headers, budgets, and the composed accessibility and device checks`
- **Next task may rely on:** the evidence document, `SECURITY_HEADERS`, the route budgets, and the structure suite.
- **AI assistance used:** Wrote the audits and tests, found and fixed the catalogue-in-client-bundle regression.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-144 Performance budgets

- **Task:** FE-144 — Performance budgets (Circle 14). Status: complete. Delivered in one commit with the other Circle 14 tasks; the evidence document is `docs/FRONTEND_HARDENING_AUDIT.md`.
- **User outcome delivered:** Public routes stay under the 170 KB plan budget and the reviewer tools have explicit route budgets; a measured 27 KB regression on the reviewer report page was removed.
- **Routes/components changed:** `src/i18n/format-message.ts`, `tests/e2e/performance.spec.ts`.
- **Backend operations/contract version:** none.
- **Public/private data handled:** No new data; the checks assert nothing private reaches a URL, storage, log, cache, or another origin.
- **States implemented:** as audited in the evidence document.
- **Accessibility evidence:** `make web-a11y` 356 passed (Chromium and mobile WebKit).
- **Locales reviewed:** Chromium; emulated 4x CPU and 1.6 Mbps. Fluent review of Hausa, Igbo, and Yoruba has not been obtained.
- **Performance/cache impact:** see the budgets in `docs/FRONTEND_HARDENING_AUDIT.md`.
- **Commands run and results:** `make web-verify` exit 0 (563 unit and 201 component tests in total); `make web-e2e` 422 passed and 10 skipped; `make web-a11y` 356 passed. A first combined run failed only because two suites were started at once on the same ports; the suites were rerun one at a time.
- **Screenshots/traces/artifacts checked:** none captured.
- **Known limitations/open decisions:** Emulation against a local server under-reports real latency; no Lighthouse or field data.
- **Commit/PR:** `feat: harden security headers, budgets, and the composed accessibility and device checks`
- **Next task may rely on:** the evidence document, `SECURITY_HEADERS`, the route budgets, and the structure suite.
- **AI assistance used:** Wrote the audits and tests, found and fixed the catalogue-in-client-bundle regression.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-145 Error and recovery consistency

- **Task:** FE-145 — Error and recovery consistency (Circle 14). Status: partial. Delivered in one commit with the other Circle 14 tasks; the evidence document is `docs/FRONTEND_HARDENING_AUDIT.md`.
- **User outcome delivered:** Each named failure class has its own sentence, unknown codes get a safe reference, and the completion-unknown hint appears only where it applies.
- **Routes/components changed:** `tests/unit/error-consistency.test.ts`.
- **Backend operations/contract version:** none.
- **Public/private data handled:** No new data; the checks assert nothing private reaches a URL, storage, log, cache, or another origin.
- **States implemented:** as audited in the evidence document.
- **Accessibility evidence:** `make web-a11y` 356 passed (Chromium and mobile WebKit).
- **Locales reviewed:** English copy; parity check for the rest. Fluent review of Hausa, Igbo, and Yoruba has not been obtained.
- **Performance/cache impact:** see the budgets in `docs/FRONTEND_HARDENING_AUDIT.md`.
- **Commands run and results:** `make web-verify` exit 0 (563 unit and 201 component tests in total); `make web-e2e` 422 passed and 10 skipped; `make web-a11y` 356 passed. A first combined run failed only because two suites were started at once on the same ports; the suites were rerun one at a time.
- **Screenshots/traces/artifacts checked:** none captured.
- **Known limitations/open decisions:** The 304 fixtures in the state matrix were not audited one by one.
- **Commit/PR:** `feat: harden security headers, budgets, and the composed accessibility and device checks`
- **Next task may rely on:** the evidence document, `SECURITY_HEADERS`, the route budgets, and the structure suite.
- **AI assistance used:** Wrote the audits and tests, found and fixed the catalogue-in-client-bundle regression.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-150 Deterministic E2E journeys

- **Task:** FE-150 — Deterministic E2E journeys (Circle 15). Status: complete. Delivered in the commits `feat: add the ten end-to-end journeys, the ordered frontend gate, DESIGN.md, and the visual finish fixes` and `test: keep the mock's public request counters independent of reviewer traffic`.
- **User outcome delivered:** The ten build-order journeys pass as continuous paths against fictional data, each checking that its synthetic secrets are nowhere in the browser.
- **Routes/components changed:** `tests/e2e/journeys.spec.ts`.
- **Backend operations/contract version:** none new (OpenAPI 0.0.0 unchanged).
- **Public/private data handled:** Fictional data only; screenshots, traces, and reports contain none that is real or private. Screenshots are committed under `docs/evidence/frontend-visual/`.
- **States implemented:** see the task note in `docs/FRONTEND_BUILD_ORDER.md`.
- **Accessibility evidence:** `make web-a11y` 356 passed; the field-edge contrast fix is pinned by a unit test.
- **Locales reviewed:** English visually inspected; Hausa landing captured; ha/ig/yo copy is pending fluent review.
- **Performance/cache impact:** none beyond the low-data switch moving to the footer.
- **Commands run and results:** clean-checkout `make web-verify-full` exit 0: 765 unit and component tests, coverage 91.4/85.3/91.6/92.0 against 80, bundle scan clean, 443 e2e passed and 11 skipped (WebKit offline, WebKit abort, and Tab-focus limitations, each stated in its test), 357 accessibility passed. In the working tree, `make web-verify` exit 0.
- **Screenshots/traces/artifacts checked:** 20 initial, 8 confirmation, and 2 final screenshots, each opened; the last alignment fix was not re-captured.
- **Known limitations/open decisions:** No independent finish review; the Impeccable detector was not run; CI has not run this branch; the letter-mark icon has had no visual review beyond the instruction.
- **Commit/PR:** `feat: add the ten end-to-end journeys, the ordered frontend gate, DESIGN.md, and the visual finish fixes`
- **Next task may rely on:** `make web-verify-full`, `DESIGN.md`, the journeys suite, and the finish-review packet.
- **AI assistance used:** Wrote the journeys, gate, design record, and fixes; found the three visual defects by inspecting screenshots and the unit-tested edge contrast.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-151 Canonical frontend verification

- **Task:** FE-151 — Canonical frontend verification (Circle 15). Status: complete. Delivered in the commits `feat: add the ten end-to-end journeys, the ordered frontend gate, DESIGN.md, and the visual finish fixes` and `test: keep the mock's public request counters independent of reviewer traffic`.
- **User outcome delivered:** `make web-verify` and `make web-verify-full` run the gate in the documented order, and CI includes the coverage step.
- **Routes/components changed:** `Makefile`, `.github/workflows/frontend.yml`, `scripts/validate_frontend_workflow.py`.
- **Backend operations/contract version:** none new (OpenAPI 0.0.0 unchanged).
- **Public/private data handled:** Fictional data only; screenshots, traces, and reports contain none that is real or private. Screenshots are committed under `docs/evidence/frontend-visual/`.
- **States implemented:** see the task note in `docs/FRONTEND_BUILD_ORDER.md`.
- **Accessibility evidence:** `make web-a11y` 356 passed; the field-edge contrast fix is pinned by a unit test.
- **Locales reviewed:** English visually inspected; Hausa landing captured; ha/ig/yo copy is pending fluent review.
- **Performance/cache impact:** none beyond the low-data switch moving to the footer.
- **Commands run and results:** clean-checkout `make web-verify-full` exit 0: 765 unit and component tests, coverage 91.4/85.3/91.6/92.0 against 80, bundle scan clean, 443 e2e passed and 11 skipped (WebKit offline, WebKit abort, and Tab-focus limitations, each stated in its test), 357 accessibility passed. In the working tree, `make web-verify` exit 0.
- **Screenshots/traces/artifacts checked:** 20 initial, 8 confirmation, and 2 final screenshots, each opened; the last alignment fix was not re-captured.
- **Known limitations/open decisions:** No independent finish review; the Impeccable detector was not run; CI has not run this branch; the letter-mark icon has had no visual review beyond the instruction.
- **Commit/PR:** `feat: add the ten end-to-end journeys, the ordered frontend gate, DESIGN.md, and the visual finish fixes`
- **Next task may rely on:** `make web-verify-full`, `DESIGN.md`, the journeys suite, and the finish-review packet.
- **AI assistance used:** Wrote the journeys, gate, design record, and fixes; found the three visual defects by inspecting screenshots and the unit-tested edge contrast.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-152 Bounded visual inspection

- **Task:** FE-152 — Bounded visual inspection (Circle 15). Status: complete. Delivered in the commits `feat: add the ten end-to-end journeys, the ordered frontend gate, DESIGN.md, and the visual finish fixes` and `test: keep the mock's public request counters independent of reviewer traffic`.
- **User outcome delivered:** One batched capture and one fix round removed three visible problems: the low-data switch above every first viewport, the stacked reviewer filters on a phone, and pale form-field edges.
- **Routes/components changed:** `docs/evidence/frontend-visual/*`, `site-shell.tsx`, `low-data-control.tsx`, `queue.tsx`, `field.tsx`, `globals.css`.
- **Backend operations/contract version:** none new (OpenAPI 0.0.0 unchanged).
- **Public/private data handled:** Fictional data only; screenshots, traces, and reports contain none that is real or private. Screenshots are committed under `docs/evidence/frontend-visual/`.
- **States implemented:** see the task note in `docs/FRONTEND_BUILD_ORDER.md`.
- **Accessibility evidence:** `make web-a11y` 356 passed; the field-edge contrast fix is pinned by a unit test.
- **Locales reviewed:** English visually inspected; Hausa landing captured; ha/ig/yo copy is pending fluent review.
- **Performance/cache impact:** none beyond the low-data switch moving to the footer.
- **Commands run and results:** clean-checkout `make web-verify-full` exit 0: 765 unit and component tests, coverage 91.4/85.3/91.6/92.0 against 80, bundle scan clean, 443 e2e passed and 11 skipped (WebKit offline, WebKit abort, and Tab-focus limitations, each stated in its test), 357 accessibility passed. In the working tree, `make web-verify` exit 0.
- **Screenshots/traces/artifacts checked:** 20 initial, 8 confirmation, and 2 final screenshots, each opened; the last alignment fix was not re-captured.
- **Known limitations/open decisions:** No independent finish review; the Impeccable detector was not run; CI has not run this branch; the letter-mark icon has had no visual review beyond the instruction.
- **Commit/PR:** `feat: add the ten end-to-end journeys, the ordered frontend gate, DESIGN.md, and the visual finish fixes`
- **Next task may rely on:** `make web-verify-full`, `DESIGN.md`, the journeys suite, and the finish-review packet.
- **AI assistance used:** Wrote the journeys, gate, design record, and fixes; found the three visual defects by inspecting screenshots and the unit-tested edge contrast.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-153 Independent finish review

- **Task:** FE-153 — Independent finish review (Circle 15). Status: blocked. Delivered in the commits `feat: add the ten end-to-end journeys, the ordered frontend gate, DESIGN.md, and the visual finish fixes` and `test: keep the mock's public request counters independent of reviewer traffic`.
- **User outcome delivered:** A packet for a fresh reviewer exists; no independent disposition was obtained and none was faked.
- **Routes/components changed:** `docs/FRONTEND_FINISH_REVIEW_PACKET.md`.
- **Backend operations/contract version:** none new (OpenAPI 0.0.0 unchanged).
- **Public/private data handled:** Fictional data only; screenshots, traces, and reports contain none that is real or private. Screenshots are committed under `docs/evidence/frontend-visual/`.
- **States implemented:** see the task note in `docs/FRONTEND_BUILD_ORDER.md`.
- **Accessibility evidence:** `make web-a11y` 356 passed; the field-edge contrast fix is pinned by a unit test.
- **Locales reviewed:** English visually inspected; Hausa landing captured; ha/ig/yo copy is pending fluent review.
- **Performance/cache impact:** none beyond the low-data switch moving to the footer.
- **Commands run and results:** clean-checkout `make web-verify-full` exit 0: 765 unit and component tests, coverage 91.4/85.3/91.6/92.0 against 80, bundle scan clean, 443 e2e passed and 11 skipped (WebKit offline, WebKit abort, and Tab-focus limitations, each stated in its test), 357 accessibility passed. In the working tree, `make web-verify` exit 0.
- **Screenshots/traces/artifacts checked:** 20 initial, 8 confirmation, and 2 final screenshots, each opened; the last alignment fix was not re-captured.
- **Known limitations/open decisions:** No independent finish review; the Impeccable detector was not run; CI has not run this branch; the letter-mark icon has had no visual review beyond the instruction.
- **Commit/PR:** `feat: add the ten end-to-end journeys, the ordered frontend gate, DESIGN.md, and the visual finish fixes`
- **Next task may rely on:** `make web-verify-full`, `DESIGN.md`, the journeys suite, and the finish-review packet.
- **AI assistance used:** Wrote the journeys, gate, design record, and fixes; found the three visual defects by inspecting screenshots and the unit-tested edge contrast.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-154 Write DESIGN.md from shipped reality

- **Task:** FE-154 — Write DESIGN.md from shipped reality (Circle 15). Status: complete. Delivered in the commits `feat: add the ten end-to-end journeys, the ordered frontend gate, DESIGN.md, and the visual finish fixes` and `test: keep the mock's public request counters independent of reviewer traffic`.
- **User outcome delivered:** `DESIGN.md` documents the shipped visual system with measured values and its known gaps.
- **Routes/components changed:** `DESIGN.md`, `docs/FRONTEND_VISUAL_DIRECTION.md`, `docs/README.md`.
- **Backend operations/contract version:** none new (OpenAPI 0.0.0 unchanged).
- **Public/private data handled:** Fictional data only; screenshots, traces, and reports contain none that is real or private. Screenshots are committed under `docs/evidence/frontend-visual/`.
- **States implemented:** see the task note in `docs/FRONTEND_BUILD_ORDER.md`.
- **Accessibility evidence:** `make web-a11y` 356 passed; the field-edge contrast fix is pinned by a unit test.
- **Locales reviewed:** English visually inspected; Hausa landing captured; ha/ig/yo copy is pending fluent review.
- **Performance/cache impact:** none beyond the low-data switch moving to the footer.
- **Commands run and results:** clean-checkout `make web-verify-full` exit 0: 765 unit and component tests, coverage 91.4/85.3/91.6/92.0 against 80, bundle scan clean, 443 e2e passed and 11 skipped (WebKit offline, WebKit abort, and Tab-focus limitations, each stated in its test), 357 accessibility passed. In the working tree, `make web-verify` exit 0.
- **Screenshots/traces/artifacts checked:** 20 initial, 8 confirmation, and 2 final screenshots, each opened; the last alignment fix was not re-captured.
- **Known limitations/open decisions:** No independent finish review; the Impeccable detector was not run; CI has not run this branch; the letter-mark icon has had no visual review beyond the instruction.
- **Commit/PR:** `feat: add the ten end-to-end journeys, the ordered frontend gate, DESIGN.md, and the visual finish fixes`
- **Next task may rely on:** `make web-verify-full`, `DESIGN.md`, the journeys suite, and the finish-review packet.
- **AI assistance used:** Wrote the journeys, gate, design record, and fixes; found the three visual defects by inspecting screenshots and the unit-tested edge contrast.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-160 Production Next.js container/service

- **Task:** FE-160 — Production Next.js container/service (Circle 16). Status: complete locally, not deployed. Delivered in one commit with the other Circle 16 tasks.
- **User outcome delivered:** A hardened, pinned, non-root web image that starts under a read-only filesystem, shuts down gracefully, and passes a vulnerability scan, ready for the maintainer to deploy.
- **Routes/components changed:** `apps/web/Dockerfile`, `Dockerfile.dockerignore`, `scripts/serve.mjs`, `app/health/{live,ready}`, `railway/web.railway.json`, `scripts/verify-web-container.sh`, `Makefile`, `proxy.ts`, unit and e2e tests.
- **Backend operations/contract version:** none (OpenAPI 0.0.0 unchanged; `backend-verify` drift checks pass).
- **Public/private data handled:** Fictional data only; the image holds no secret and the scripts print no environment value.
- **States implemented:** see the task note in `docs/FRONTEND_BUILD_ORDER.md`.
- **Accessibility evidence:** `make web-a11y` 356 passed on the final tree.
- **Locales reviewed:** unchanged; Hausa, Igbo, and Yoruba copy remains largely pending fluent review.
- **Performance/cache impact:** none beyond the health routes and the container.
- **Commands run and results:** `make backend-verify` exit 0 (2,096 passed, 93.9% coverage, pip-audit clean; a first run failed seven integration tests because the local ClamAV container was unhealthy, and passed after restarting it, then `make db-roles` restored the dev logins); `make web-verify` exit 0 (767 tests); `make web-e2e` 447 passed and 11 skipped; `make web-a11y` 356 passed; `make web-container-verify` (with Trivy) all checks passed. Nothing was deployed or pushed.
- **Screenshots/traces/artifacts checked:** the six README screenshots were opened and checked (the Source Scout, record, report, and queue images), all synthetic.
- **Known limitations/open decisions:** No hosted deployment, hosted header check, link check, demo video, clean-clone `make verify` twice, green hosted CI, or submission tag; the Source Scout panel showed its introduction twice and one copy was removed after the screenshot.
- **Commit/PR:** `feat: add the hardened web container, health routes, judge README, and demo script`
- **Next task may rely on:** `make verify`, `make web-container-verify`, `docs/DEPLOYMENT.md`, and `docs/DEMO_SCRIPT.md`.
- **AI assistance used:** Wrote the Dockerfile, entry point, verification script, docs, and found the missing graceful shutdown and the base-image findings.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-161 Public-origin security and cache configuration

- **Task:** FE-161 — Public-origin security and cache configuration (Circle 16). Status: partial. Delivered in one commit with the other Circle 16 tasks.
- **User outcome delivered:** The production headers and cache policy are configured and proven on the local build and inside the container; hosted validation is left to the maintainer.
- **Routes/components changed:** `next.config.ts`, `proxy.ts`, `docs/DEPLOYMENT.md` (hosted verification commands).
- **Backend operations/contract version:** none (OpenAPI 0.0.0 unchanged; `backend-verify` drift checks pass).
- **Public/private data handled:** Fictional data only; the image holds no secret and the scripts print no environment value.
- **States implemented:** see the task note in `docs/FRONTEND_BUILD_ORDER.md`.
- **Accessibility evidence:** `make web-a11y` 356 passed on the final tree.
- **Locales reviewed:** unchanged; Hausa, Igbo, and Yoruba copy remains largely pending fluent review.
- **Performance/cache impact:** none beyond the health routes and the container.
- **Commands run and results:** `make backend-verify` exit 0 (2,096 passed, 93.9% coverage, pip-audit clean; a first run failed seven integration tests because the local ClamAV container was unhealthy, and passed after restarting it, then `make db-roles` restored the dev logins); `make web-verify` exit 0 (767 tests); `make web-e2e` 447 passed and 11 skipped; `make web-a11y` 356 passed; `make web-container-verify` (with Trivy) all checks passed. Nothing was deployed or pushed.
- **Screenshots/traces/artifacts checked:** the six README screenshots were opened and checked (the Source Scout, record, report, and queue images), all synthetic.
- **Known limitations/open decisions:** No hosted deployment, hosted header check, link check, demo video, clean-clone `make verify` twice, green hosted CI, or submission tag; the Source Scout panel showed its introduction twice and one copy was removed after the screenshot.
- **Commit/PR:** `feat: add the hardened web container, health routes, judge README, and demo script`
- **Next task may rely on:** `make verify`, `make web-container-verify`, `docs/DEPLOYMENT.md`, and `docs/DEMO_SCRIPT.md`.
- **AI assistance used:** Wrote the Dockerfile, entry point, verification script, docs, and found the missing graceful shutdown and the base-image findings.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-162 Hosted smoke matrix

- **Task:** FE-162 — Hosted smoke matrix (Circle 16). Status: blocked. Delivered in one commit with the other Circle 16 tasks.
- **User outcome delivered:** Nothing hosted exists; every item in the matrix has a passing local, deterministic equivalent, and the hosted run is scripted for the maintainer.
- **Routes/components changed:** none (docs only).
- **Backend operations/contract version:** none (OpenAPI 0.0.0 unchanged; `backend-verify` drift checks pass).
- **Public/private data handled:** Fictional data only; the image holds no secret and the scripts print no environment value.
- **States implemented:** see the task note in `docs/FRONTEND_BUILD_ORDER.md`.
- **Accessibility evidence:** `make web-a11y` 356 passed on the final tree.
- **Locales reviewed:** unchanged; Hausa, Igbo, and Yoruba copy remains largely pending fluent review.
- **Performance/cache impact:** none beyond the health routes and the container.
- **Commands run and results:** `make backend-verify` exit 0 (2,096 passed, 93.9% coverage, pip-audit clean; a first run failed seven integration tests because the local ClamAV container was unhealthy, and passed after restarting it, then `make db-roles` restored the dev logins); `make web-verify` exit 0 (767 tests); `make web-e2e` 447 passed and 11 skipped; `make web-a11y` 356 passed; `make web-container-verify` (with Trivy) all checks passed. Nothing was deployed or pushed.
- **Screenshots/traces/artifacts checked:** the six README screenshots were opened and checked (the Source Scout, record, report, and queue images), all synthetic.
- **Known limitations/open decisions:** No hosted deployment, hosted header check, link check, demo video, clean-clone `make verify` twice, green hosted CI, or submission tag; the Source Scout panel showed its introduction twice and one copy was removed after the screenshot.
- **Commit/PR:** `feat: add the hardened web container, health routes, judge README, and demo script`
- **Next task may rely on:** `make verify`, `make web-container-verify`, `docs/DEPLOYMENT.md`, and `docs/DEMO_SCRIPT.md`.
- **AI assistance used:** Wrote the Dockerfile, entry point, verification script, docs, and found the missing graceful shutdown and the base-image findings.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-163 Judge-facing evidence package

- **Task:** FE-163 — Judge-facing evidence package (Circle 16). Status: partial. Delivered in one commit with the other Circle 16 tasks.
- **User outcome delivered:** A judge can read the README, see synthetic screenshots, follow a sub-four-minute demo path, and run one documented gate; no video or hosted link exists.
- **Routes/components changed:** `README.md`, `docs/DEMO_SCRIPT.md`, `docs/evidence/frontend-visual/readme/*`, `docs/README.md`.
- **Backend operations/contract version:** none (OpenAPI 0.0.0 unchanged; `backend-verify` drift checks pass).
- **Public/private data handled:** Fictional data only; the image holds no secret and the scripts print no environment value.
- **States implemented:** see the task note in `docs/FRONTEND_BUILD_ORDER.md`.
- **Accessibility evidence:** `make web-a11y` 356 passed on the final tree.
- **Locales reviewed:** unchanged; Hausa, Igbo, and Yoruba copy remains largely pending fluent review.
- **Performance/cache impact:** none beyond the health routes and the container.
- **Commands run and results:** `make backend-verify` exit 0 (2,096 passed, 93.9% coverage, pip-audit clean; a first run failed seven integration tests because the local ClamAV container was unhealthy, and passed after restarting it, then `make db-roles` restored the dev logins); `make web-verify` exit 0 (767 tests); `make web-e2e` 447 passed and 11 skipped; `make web-a11y` 356 passed; `make web-container-verify` (with Trivy) all checks passed. Nothing was deployed or pushed.
- **Screenshots/traces/artifacts checked:** the six README screenshots were opened and checked (the Source Scout, record, report, and queue images), all synthetic.
- **Known limitations/open decisions:** No hosted deployment, hosted header check, link check, demo video, clean-clone `make verify` twice, green hosted CI, or submission tag; the Source Scout panel showed its introduction twice and one copy was removed after the screenshot.
- **Commit/PR:** `feat: add the hardened web container, health routes, judge README, and demo script`
- **Next task may rely on:** `make verify`, `make web-container-verify`, `docs/DEPLOYMENT.md`, and `docs/DEMO_SCRIPT.md`.
- **AI assistance used:** Wrote the Dockerfile, entry point, verification script, docs, and found the missing graceful shutdown and the base-image findings.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

## 2026-09-20 — FE-164 Repository release gate

- **Task:** FE-164 — Repository release gate (Circle 16). Status: partial. Delivered in one commit with the other Circle 16 tasks.
- **User outcome delivered:** `make setup` and `make verify` exist and the gates pass on the final tree; the clean-clone twice run, hosted CI, and tag are the maintainer's.
- **Routes/components changed:** `Makefile`.
- **Backend operations/contract version:** none (OpenAPI 0.0.0 unchanged; `backend-verify` drift checks pass).
- **Public/private data handled:** Fictional data only; the image holds no secret and the scripts print no environment value.
- **States implemented:** see the task note in `docs/FRONTEND_BUILD_ORDER.md`.
- **Accessibility evidence:** `make web-a11y` 356 passed on the final tree.
- **Locales reviewed:** unchanged; Hausa, Igbo, and Yoruba copy remains largely pending fluent review.
- **Performance/cache impact:** none beyond the health routes and the container.
- **Commands run and results:** `make backend-verify` exit 0 (2,096 passed, 93.9% coverage, pip-audit clean; a first run failed seven integration tests because the local ClamAV container was unhealthy, and passed after restarting it, then `make db-roles` restored the dev logins); `make web-verify` exit 0 (767 tests); `make web-e2e` 447 passed and 11 skipped; `make web-a11y` 356 passed; `make web-container-verify` (with Trivy) all checks passed. Nothing was deployed or pushed.
- **Screenshots/traces/artifacts checked:** the six README screenshots were opened and checked (the Source Scout, record, report, and queue images), all synthetic.
- **Known limitations/open decisions:** No hosted deployment, hosted header check, link check, demo video, clean-clone `make verify` twice, green hosted CI, or submission tag; the Source Scout panel showed its introduction twice and one copy was removed after the screenshot.
- **Commit/PR:** `feat: add the hardened web container, health routes, judge README, and demo script`
- **Next task may rely on:** `make verify`, `make web-container-verify`, `docs/DEPLOYMENT.md`, and `docs/DEMO_SCRIPT.md`.
- **AI assistance used:** Wrote the Dockerfile, entry point, verification script, docs, and found the missing graceful shutdown and the base-image findings.
- **Prompt summary:** Unattended frontend/BFF build loop.
- **Human review:** none yet; unattended run, pending maintainer review.

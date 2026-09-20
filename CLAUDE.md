# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md

`AGENTS.md` (imported above) is the binding rulebook: product invariants, architecture boundaries, coding standards, the definition of done, and the blocking code-review rules. This file adds only orientation for Claude Code; it does not override or relax `AGENTS.md`.

## Current state

The backend is built: `services/platform` (FastAPI API, Dramatiq worker, Alembic migrations 0001 to 0027), `contracts/` (generated OpenAPI and frontend fixtures), `data/` (source register, seed vectors, replay and evaluation fixtures), `railway/` (service config), and `docs/` (build orders, ADR-0001 to ADR-0010, threat model, runbooks, and `docs/evidence/`). The frontend, `apps/web`, has **not been started**: nothing under `apps/` is tracked. `docs/FRONTEND_BUILD_ORDER.md` is its plan and `docs/FRONTEND_BACKEND_CONTRACT.md` is the frozen contract it consumes. Each circle's gate note in `docs/BACKEND_BUILD_ORDER.md` says exactly what is proven and what is still open; read it before claiming anything is done.

Commands, from the repository root (Docker is needed for the local services):

```text
cp .env.example .env
make infra-up-core             # PostgreSQL 18 + pgvector, Redis, MinIO (`make infra-up` adds ClamAV, 1.5-3 GB)
make migrate && make db-roles  # schema, then the application-role logins from .env
make seed-demo                 # cited demo data and checked-in vectors; local databases only
make backend-verify            # the canonical gate: format, lint, pyright strict, every test layer,
                               # 85% branch coverage, OpenAPI drift, Bandit, pip-audit
make openapi-generate          # after changing a route or schema (also frontend-contract-generate)
make embedding-model           # optional: 129 MB local embedding model, pinned and SHA-256 verified
make embeddings                # regenerate data/embeddings/*.jsonl after approved chunks change
make worker                    # the discovery worker (needs Redis and DATABASE_URL_WORKER)
```

A single test, from `services/platform`: `uv run pytest tests/unit/path/test_file.py::test_name`. Integration tests need the services and the environment: `uv run --frozen --env-file ../../.env pytest tests/integration/test_x.py`. **The integration suite re-provisions the local database roles with its own throwaway passwords**, so run `make db-roles` again before using the dev database afterwards.

`make verify` (the judge-facing full gate) and `make setup` do not exist yet; they belong to the frontend work.

Dependency-free validators for the design contracts. Run all of them after touching `contracts/`, `docs/THREAT_MODEL.md`, `docs/decisions/`, the source register, or task IDs in the build orders:

```text
python3 scripts/validate_controlled_vocabulary.py --self-test
python3 scripts/render_controlled_vocabulary.py --check   # docs/CONTROLLED_VOCABULARY.md has no drift
python3 scripts/validate_threat_model.py --self-test
python3 scripts/validate_decisions.py --self-test
python3 scripts/validate_source_register.py --self-test
python3 scripts/render_source_register.py --check         # docs/SOURCE_REGISTER.md matches data/source-register.json
```

Work is executed task by task from `docs/BACKEND_BUILD_ORDER.md`. Each task gets a Conventional Commit, an `Execution status` note under its heading, and an entry in `docs/AI_BUILD_LOG.md`. `docs/SOURCE_REGISTER.md` (generated from `data/source-register.json`) holds the six-project register: only facts with a passage verified word for word are seeded, and three projects have none because their sources block automated access. No seed data may be presented as factual beyond that register, and never fabricate project data, sources, escalation routes, or translations.

Hard deadline: **21 September 2026, 23:59 UTC** (hackathon submission). When time is short, follow the plan's scope-cut order; never cut the items it marks as uncuttable.

## Documents and their authority

Read in this order when they conflict (details in `docs/README.md`):

1. `PRODUCT.md`: scope, pilot, users, languages, non-goals.
2. `docs/PRODUCT_BRIEF.md`: journeys, trust model, requirements, acceptance criteria.
3. `docs/IMPLEMENTATION_PLAN.md`: stack, BFF boundary, data model, API list, security controls, test strategy, gates, and scope-cut order.
   - `docs/decisions/` (ADR-0001 to ADR-0010) makes binding the hard-to-reverse backend choices: internal-service auth, DB roles, envelope encryption, tracking codes, sanitation, OpenAPI, providers, the Groq language provider, and local embeddings.
   - `docs/THREAT_MODEL.md` classifies every asset and lists the allowed data per flow and destination.
4. `contracts/openapi.json`, migrations, and tests.

Log material AI assistance in `docs/AI_BUILD_LOG.md` as part of each change.

## Big-picture architecture

- **Two stacks, one authority.** `apps/web` (Next.js App Router, thin BFF) and `services/platform` (FastAPI modular monolith with `api` and Dramatiq `worker` entry points). FastAPI owns every domain, authorisation, visibility, and publication rule; the BFF only handles cookies, CSRF/origin, locale, request IDs, and response shaping.
- **Browser → Next.js origin only.** Server Components call the private API directly; browser mutations, uploads, polling, and reviewer actions go through Next.js Route Handlers to FastAPI.
- **Contract flow.** FastAPI emits `contracts/openapi.json` → the TypeScript client in `apps/web/src/lib/api/generated/` is generated from it. Change the backend schema and regenerate both in one change; never hand-edit generated files.
- **Three trust zones with separate paths.** Public records (projects, facts, citations, approved sources), private reporting (encrypted reports, separate contacts, evidence files, reviewer notes), and discovery (Source Scout runs, discovered sources). Public repositories read only public views; private data never reaches public DTOs, caches, logs, the Q&A index, or search queries.
- **Publication is always a separate human act.** Status changes never publish text; a reviewer authors a separate `public_update` with approved citations.

## Accepted decisions that are easy to miss

These are recorded in `docs/IMPLEMENTATION_PLAN.md` and override the original brief where they differ:

- Tracking lookup is `POST /v1/report-status:lookup` with the code in the body, not the brief's `GET /reports/status/{code}`.
- No page fetches the API during `next build` (Railway private networking is unavailable at build time); public routes render on request and cache afterwards.
- The restricted submission DB role cannot `SELECT`, so private-report inserts generate UUIDv7 in the app and disable implicit `RETURNING`.
- Public Source Scout runs are cached per project for 24 hours and capped by a global daily budget; reviewer runs are separate and audited.
- Hosted demo runs without ClamAV (`SCANNER_MODE=not_deployed`, files labelled `not_scanned_demo`); local and CI scan for real; production refuses that mode.
- Session cookie is `__Host-sg_session` (Secure) in staging/production and plain `sg_session` in development/test so WebKit E2E works on `http://localhost`.
- Language model is Groq (ADR-0009), not OpenAI; the strict schema sent over the wire drops `pattern` because Groq's constrained decoder rejects it, and our own Pydantic models still enforce it.
- Embeddings are local: FastEmbed with `multilingual-e5-small` (int8), 384 dimensions (ADR-0010). `EMBEDDING_BACKEND` is `off` by default; when on, a question is embedded in-process and retrieval is hybrid, otherwise (or on any failure) it falls back to keyword and reports `retrieval_mode`. The 129 MB model is baked into the platform image and fits the hosted service's 1 GB memory limit; the 2.2 GB large model did not (it was killed in a restart loop on Railway), so do not switch to it without raising that limit.
- A cited fact can be public while `awaiting_verification`, and public citations expose `source_version_id` (migrations 0025 and 0026). Seeded source versions are `approved` because the register validator re-checks every passage hash; that approves the quoted text, not the claim.
- The demo seed refuses everything except local databases, plus `APP_ENV=staging` with `SEED_ALLOW_DEPLOYED=1`. Production has no seed mode, with or without the flag.
- Optional anonymous reporter handles: server-generated handle plus six-word passphrase, Argon2id hash, no contact or recovery data, verified only at submission, reviewer-only track record, deletable without deleting reports. Fully anonymous reporting remains the default, and handles are built only after the anonymous path works.

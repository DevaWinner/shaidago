# ShaidaGo platform service

This is ShaidaGo's private FastAPI modular monolith. It owns domain policy, authorisation, visibility, citations, reports, review, publication, and audit history. The same package provides the API and Dramatiq worker entry points.

**Status:** implemented and deployed to staging for the fictional-data proof of concept. The deterministic backend gate, container checks, staging smoke, and remaining production blockers are linked from the repository [documentation index](../../docs/README.md).

## Toolchain

- Python `>=3.14,<3.15` (pinned in `.python-version`), managed by `uv`. The lockfile is `uv.lock`.
- Ruff for formatting and linting, Pyright in strict mode, pytest with `pytest-asyncio`.

Run from this directory:

```text
uv sync --all-groups --frozen
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```

From the repository root, `make backend-verify` runs the canonical backend gate: frozen sync, format check, lint, strict Pyright, every deterministic test layer with branch coverage of at least 85%, committed OpenAPI drift, Bandit, and `pip-audit`. Live-provider tests are excluded. CI invokes this same target with PostgreSQL, Redis, MinIO, and ClamAV; the separate `make container-verify` builds and exercises the production image and includes its Trivy scan. `make help` lists the individual targets. `make seed-demo` never contacts an AI provider: it loads only a matching file from `data/embeddings/` and otherwise enables keyword retrieval. `make embeddings` is the explicit, credentialed command that generates that file.

Every route declares a stable operation ID. `make frontend-contract-generate` renders
`contracts/frontend-fixtures.json`, including every documented success/error status and the named
UI state fixtures; `make frontend-contract-check` is part of the backend gate. Browser/BFF rules
are frozen in `docs/FRONTEND_BACKEND_CONTRACT.md`.

`POST /v1/projects/{slug}/questions` is the private-API boundary for grounded public questions. It accepts one bounded JSON `question`, takes the requested locale from the trusted BFF header, searches only approved source chunks for that public project, and returns a short validated answer with resolvable citations or the exact insufficient-evidence fallback. Responses and errors are `no-store`; requests are rate-limited per BFF-supplied client pseudonym. Operational rows retain counts, outcome, duration, and model/prompt/schema versions, never the question, prompt, passage, client pseudonym, or IP address. Replay mode is the deterministic default; live mode requires `GROQ_API_KEY`.

`uv run python -m shaidago.retrieval.evaluation` runs the checked-in 44-case English, Hausa, Igbo, and Yoruba citation and policy evaluation without a key or network access. The corpus records the maintainer's review for all four locales; this is not an independent language review. The separate `--live` mode is an opt-in maintainer workflow documented in `data/qa-evaluation/README.md` and is excluded from deterministic verification.

## Layout

`src/shaidago/` contains the domain modules. Tests are split by layer under `tests/`: unit, integration, contract, security, evaluation, and fixtures.

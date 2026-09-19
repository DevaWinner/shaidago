# ShaidaGo platform service

The private FastAPI modular monolith that owns every domain, authorisation, visibility, and publication rule for ShaidaGo. The API entry point exists; the Dramatiq worker lifecycle is added by its later build gate.

**Status:** the backend is under active, task-gated implementation. See [`docs/BACKEND_BUILD_ORDER.md`](../../docs/BACKEND_BUILD_ORDER.md) for verified capabilities and open gates.

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

From the repository root, `make backend-verify` runs the canonical backend gate (frozen sync, format check, lint, Pyright, Bandit, pip-audit, tests); `make help` lists the individual targets. `make seed-demo` never contacts an AI provider: it loads only a matching file from `data/embeddings/` and otherwise enables keyword retrieval. `make embeddings` is the explicit, credentialed command that generates that file.

## Layout

`src/shaidago/` holds the package. Domain modules are added by their owning circle (see build order section 2); test directories under `tests/` are split by layer (`unit`, `integration`, `contract`, `security`, `evaluation`, `fixtures`).

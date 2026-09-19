# ShaidaGo platform service

The private FastAPI modular monolith that owns every domain, authorisation, visibility, and publication rule for ShaidaGo. It will expose an `api` and a Dramatiq `worker` entry point; neither exists yet.

**Status (BE-010):** toolchain scaffold only. There are no routes, tables, providers, or secrets. See [`docs/BACKEND_BUILD_ORDER.md`](../../docs/BACKEND_BUILD_ORDER.md) for what each task adds.

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

Canonical `make` targets arrive with BE-011.

## Layout

`src/shaidago/` holds the package. Domain modules are added by their owning circle (see build order section 2); test directories under `tests/` are split by layer (`unit`, `integration`, `contract`, `security`, `evaluation`, `fixtures`).

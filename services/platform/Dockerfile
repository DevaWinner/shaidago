# syntax=docker/dockerfile:1
# One image for the API and the worker (and the one-shot migration job): only the command differs.
# Build from the repository root so the layout matches the source tree, which the code relies on
# for its contract and fixture files:
#   docker build -f services/platform/Dockerfile --build-arg REVISION=$(git rev-parse HEAD) \
#     -t shaidago-platform:$(git rev-parse --short HEAD) .

ARG PYTHON_IMAGE=python:3.14-slim@sha256:caaf356f40667c496d405780745b9ac25771c189a51dfcc42430d531ea09f8a2

# ---- build stage: compilers and uv live here and never reach the final image ------------------
FROM ${PYTHON_IMAGE} AS build
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PYTHON_DOWNLOADS=never UV_NO_CACHE=1
RUN pip install --no-cache-dir uv==0.11.28
WORKDIR /app/services/platform
COPY services/platform/pyproject.toml services/platform/uv.lock ./
# Frozen install of runtime dependencies only (no dev group, no project): the layer is cached until
# the lockfile changes.
RUN uv sync --frozen --no-dev --no-install-project
# Then the project itself, installed editable so its package metadata exists (the API reads its own
# version) while the code stays at its repository-relative path, which the contract and fixture
# lookups depend on. The venv is copied to the same path below, so the link stays valid.
COPY services/platform/README.md ./
COPY services/platform/src ./src
RUN uv sync --frozen --no-dev

# ---- final stage -------------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS final
ARG REVISION=unknown
ARG CREATED=unknown
LABEL org.opencontainers.image.title="shaidago-platform" \
      org.opencontainers.image.description="ShaidaGo private API, worker, and migration job" \
      org.opencontainers.image.source="https://github.com/dev-winner/shaidago" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.revision="${REVISION}" \
      org.opencontainers.image.created="${CREATED}"

# A fixed unprivileged user with no login shell and no home to write to.
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

# The runtime never installs packages: remove the base image's pip, setuptools, and wheel (unused
# tooling that carried the only fixable findings in the vulnerability scan).
RUN python -m pip uninstall -y pip setuptools wheel >/dev/null 2>&1 || true

WORKDIR /app
# Same layout as the repository: the code finds contracts/ and data/ relative to its own path.
COPY --from=build /app/services/platform/.venv /app/services/platform/.venv
COPY services/platform/src /app/services/platform/src
COPY services/platform/migrations /app/services/platform/migrations
COPY services/platform/alembic.ini /app/services/platform/alembic.ini
COPY contracts /app/contracts
COPY data /app/data
# The seed validates the source register with the repository's own validator, so the image
# needs that one script. Nothing else from scripts/ is copied.
COPY scripts/validate_source_register.py /app/scripts/validate_source_register.py

ENV PATH="/app/services/platform/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    TMPDIR=/tmp \
    PORT=8000
WORKDIR /app/services/platform
USER 10001:10001
EXPOSE 8000

# The API by default; the worker and the migration job override the command:
#   dramatiq shaidago.worker.entry --queues discovery --processes 1 --threads 2
#   alembic upgrade head
# python -m shaidago.api.serve binds a dual-stack socket on :: (Railway's private network is IPv6)
# and hands it to uvicorn as PID 1, so SIGTERM reaches it and in-flight requests drain.
CMD ["python", "-m", "shaidago.api.serve"]

HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import os,sys,urllib.request; sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/health/live', timeout=2).status == 200 else 1)"]

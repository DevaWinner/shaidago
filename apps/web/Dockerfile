# syntax=docker/dockerfile:1
# The public web service (Next.js standalone output and the BFF). Build from the repository root:
#   docker build -f apps/web/Dockerfile --build-arg REVISION=$(git rev-parse HEAD) \
#     -t shaidago-web:$(git rev-parse --short HEAD) .
# The build needs no network access to the private API and receives no secret: every private value
# (API_INTERNAL_URL, the internal credential) is read at run time from the platform's secrets.

ARG NODE_IMAGE=node:24.20.0-slim@sha256:ba849c60be29959425b8734d57b8b4b7d56f98edd9504c9af091d5281095a71e

# ---- build stage: the package manager and dev dependencies never reach the final image ---------
FROM ${NODE_IMAGE} AS build
ENV CI=true NEXT_TELEMETRY_DISABLED=1
RUN corepack enable
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc .nvmrc ./
COPY apps/web/package.json apps/web/package.json
# Frozen install, so the lockfile is the only source of versions.
RUN pnpm install --frozen-lockfile --filter @shaidago/web...
COPY apps/web apps/web
RUN pnpm --dir apps/web build

# ---- final stage ---------------------------------------------------------------------------------
FROM ${NODE_IMAGE} AS final
ARG REVISION=unknown
ARG CREATED=unknown
LABEL org.opencontainers.image.title="shaidago-web" \
      org.opencontainers.image.description="ShaidaGo public web service and BFF" \
      org.opencontainers.image.source="https://github.com/dev-winner/shaidago" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.revision="${REVISION}" \
      org.opencontainers.image.created="${CREATED}"

# The pinned base image predates a fixed libpcre2 advisory (three high findings in the scan), so that
# one package is upgraded in place; nothing else is installed and the package lists are removed.
RUN apt-get update \
 && apt-get install -y --no-install-recommends --only-upgrade libpcre2-8-0 \
 && rm -rf /var/lib/apt/lists/*

# A fixed unprivileged user with no login shell. Corepack, npm, and yarn are not needed to run.
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app \
 && rm -rf /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/corepack \
           /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack /opt/yarn* /usr/local/bin/yarn* 2>/dev/null || true

WORKDIR /app
# The standalone output holds only the files the server needs (traced dependencies, no source, no
# tests, no source maps). Static assets and the small public folder are copied beside it.
COPY --from=build --chown=app:app /app/apps/web/.next/standalone ./
COPY --from=build --chown=app:app /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=build --chown=app:app /app/apps/web/public ./apps/web/public
COPY --chown=app:app apps/web/scripts/serve.mjs ./apps/web/serve.mjs
# The one writable place: the framework's data cache. Mount a tmpfs here to run with a read-only
# root filesystem (`docker run --read-only --tmpfs /app/apps/web/.next/cache`).
RUN mkdir -p /app/apps/web/.next/cache && chown -R app:app /app/apps/web/.next/cache

ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
USER app
EXPOSE 3000
# serve.mjs starts the server and, on SIGTERM, drains in-flight requests before exiting 0.
CMD ["node", "apps/web/serve.mjs"]

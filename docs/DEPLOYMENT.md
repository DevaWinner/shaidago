# Backend deployment on Railway

The first part applies to the backend (BE-110 to BE-112); the web service is described at the end. The Next.js service is the only thing that receives the internal API URL and credential; nothing here exposes the API publicly.

## Topology (per environment)

| Service | Source | Command | Network | Holds |
| --- | --- | --- | --- | --- |
| `api` | this repository's image (`railway/api.railway.json`) | `python -m shaidago.api.serve` | private only, no public domain; listens on `::` and IPv4 | API-role database URLs, Redis, object storage, encryption keys, tracking and idempotency peppers, session and cursor keys, internal caller credential, provider keys |
| `worker` | same image (`railway/worker.railway.json`) | `dramatiq shaidago.worker.entry --queues discovery` | private only | worker-role database URL, Redis, provider keys; no encryption keys, no session keys, no owner URL |
| `migrate` | same image (`railway/migrate.railway.json`) | `alembic upgrade head` then role provisioning, restart policy never | private only | the migration-owner database URL and the role passwords, nothing else |
| `postgres` | `pgvector/pgvector:pg18` image with a volume | image default | private only | database data |
| `redis` | Redis image or template | image default | private only | rate-limit and queue state (no durable domain data) |
| object storage | a Railway bucket (or Cloudflare R2 in production) | n/a | S3 API | sanitised evidence only |

Staging and production are separate Railway environments in separate projects where possible, with their own database, Redis, bucket, keys, reviewer accounts, provider keys, and budgets. Nothing is shared or copied between them. Production never auto-seeds and refuses `PROVIDER_MODE=replay`, placeholder keys, and the unscanned-demo scanner mode.

## Secret ownership and rotation

| Secret | Held by | Owner | Rotation |
| --- | --- | --- | --- |
| Migration-owner database URL and role passwords | `migrate` | Maintainer | Change the role password in the database, then the variable; redeploy dependents. Quarterly and on any suspected exposure. |
| `DATABASE_URL_PUBLIC`, `_REVIEWER`, `_WORKER` | `api`, `worker` (each its own) | Maintainer | Same as above per role. |
| `ENCRYPTION_KEKS` and active version | `api` | Maintainer | Add a version, deploy, `make kek-rotate` in the environment, remove the old version ([key management](KEY_MANAGEMENT.md)). |
| `TRACKING_PEPPERS`, `IDEMPOTENCY_PEPPER` | `api` | Maintainer | Versioned ring for tracking peppers; idempotency pepper rotation invalidates replays only. |
| `SESSION_HMAC_KEY`, `CURSOR_HMAC_KEY` | `api` | Maintainer | Rotating signs every reviewer out or invalidates open cursors; do it in a quiet window. |
| `INTERNAL_WEB_CREDENTIAL_CURRENT` (and `_PREVIOUS` during rotation) | `api` and the Next.js service | Maintainer | Set the new value as current and the old as previous on the API, update the web service, then drop the previous one. |
| `OPENAI_API_KEY`, `SEARCH_API_KEY` | `api`, `worker` | Maintainer | Revoke and reissue at the provider; each environment has its own key and budget. |
| Object storage access key | `api`, `worker` | Maintainer | Create a second key, switch the variables, revoke the first. |

## Migrations gate the deploy (BE-112)

1. Deploy `migrate` first. It runs `alembic upgrade head` under the owner role (serialised by an advisory lock, so two runs cannot collide), then provisions role logins. A non-zero exit stops the release: do not deploy `api` or `worker`.
2. Deploy `api` and `worker` only after `migrate` shows success. The API's readiness reports `unavailable` if the database revision is not the one this code expects, so a mismatch never receives traffic.
3. A change that is not backward compatible with the previous app version follows expand, migrate, contract across releases: add the new column or table and keep the old readable; ship code that writes both; backfill; ship code that reads only the new; drop the old in a later release.
4. Take and test-restore a backup before any destructive or irreversible migration.
5. Rollback is an app rollback (redeploy the previous image) plus an explicit decision about the schema. `alembic downgrade` is not the rollback: several revisions delete data structures, and an older app must still run against the newer schema (which the expand step guarantees).
6. Production is never seeded: `make seed-demo` refuses non-local targets.

## Container

`docker build -f services/platform/Dockerfile --build-arg REVISION=$(git rev-parse HEAD) -t shaidago-platform .` from the repository root. `scripts/verify-container.sh` (with `TRIVY=1`) proves the image is non-root, has no build or development tooling, runs the API on a read-only filesystem with no capabilities, starts the worker and the migration job from the same image, drains on SIGTERM, and passes the vulnerability scan.

## Provisioning staging (what was actually done)

`railway init --name shaidago-staging`, rename the environment to `staging`, then `railway add` for `postgres` (`pgvector/pgvector:pg18`, plus a volume at `/var/lib/postgresql/data`), a managed Redis, a bucket in `ams`, and empty `api`, `worker`, and `migrate` services; start commands and restart policies were set through the Railway API to match `railway/*.railway.json`; `scripts/railway_staging_variables.py` generated every key and role password and set the variables without printing them. Deploy order: `migrate` (wait for SUCCESS), then `api` and `worker` (`railway up --service <name> --detach`, then follow the deployment ID to SUCCESS). Two deliberate details: the backend's settings require `DATABASE_URL` to exist, so `api` and `worker` carry the worker role's URL in it (they never connect with it), which keeps the owner URL on `migrate` alone; and no service has a public domain.

Not created: a production project. Production must be its own project with its own database, Redis, bucket, keys, reviewer accounts, provider keys, and budgets, and must start from `PROVIDER_MODE=live`, `SCANNER_MODE=clamd`, and a real scanner service.

# Web service on Railway (FE-160 and FE-161)

The public origin is the Next.js service (`railway/web.railway.json`, image from `apps/web/Dockerfile`). It is the only service with a public domain and the only one that knows the private API address.

## What the image is

Built with `docker build -f apps/web/Dockerfile --build-arg REVISION=$(git rev-parse HEAD) -t shaidago-web .` from the repository root. The build needs no network access to the API and no secret. The final image holds only the framework's standalone output, static files, and the small public folder; it runs as user 10001 with no npm, corepack, or git, no tests, no source maps in served files, and no credential files. `apps/web/scripts/serve.mjs` is the entry point: on SIGTERM it stops accepting connections, lets in-flight requests finish, and exits 0 (after at most 20 s, under the 25 s platform drain). `scripts/verify-web-container.sh` (`make web-container-verify`, with a Trivy scan) proves this on a build, running the container with a read-only root filesystem, no capabilities, and no privilege escalation. Run it with `--read-only --tmpfs /app/apps/web/.next/cache`.

## Variables (names only; values live in Railway secrets)

| Variable | Notes |
| --- | --- |
| `APP_ENV` | `staging` or `production`. Turns on `__Host-` cookies, secure cookies, and HSTS. |
| `API_INTERNAL_URL` | The API's private Railway address. Read at run time only. Never `NEXT_PUBLIC_`. |
| `INTERNAL_WEB_CREDENTIAL_CURRENT` (and `_PREVIOUS` while rotating) | Same value as on the API; at least 32 characters. |
| `CLIENT_HMAC_KEY` | Base64, 32+ random bytes; required in staging and production. |
| `TRUSTED_PROXY_HOPS` | `1` behind the Railway edge. |
| `NEXT_PUBLIC_APP_ORIGIN` | Optional; the public origin only. |

`PORT` is provided by Railway; the image defaults to 3000 and binds all interfaces. Liveness is `/health/live` (no dependency, so an API outage never restarts the web service); `/health/ready` reports only whether this service's own configuration is valid.

## Hosted verification (FE-161): run against the deployed origin, not the config

These checks were run against the deployed staging origin on 2026-09-20 (record: [`evidence/FE-162-hosted-smoke.md`](evidence/FE-162-hosted-smoke.md)). To repeat them from any machine, with `ORIGIN=https://<the public domain>`:

```text
curl -sI $ORIGIN/en | grep -iE 'content-security-policy|x-frame-options|x-content-type-options|referrer-policy|permissions-policy|strict-transport-security|cache-control'
curl -sI $ORIGIN/en/track | grep -i cache-control              # must contain no-store
curl -sI $ORIGIN/en/reviewer/sign-in | grep -i cache-control   # must contain no-store
curl -sI $ORIGIN/sw.js | grep -iE 'cache-control|service-worker-allowed'
curl -s  $ORIGIN/health/live ; curl -s $ORIGIN/health/ready
```

Expected: the CSP allows only `'self'`; `X-Frame-Options: DENY`; `strict-transport-security` is present (HTTPS only); public catalogue pages are `public, max-age=0, must-revalidate` and private routes `no-store`; the worker is `no-cache`. Then confirm the API is unreachable from outside: its private hostname must not resolve or connect from the internet, and a search of the served JavaScript for the API hostname and the credential must find nothing (`pnpm --dir apps/web bundle:check` does the latter for a build). Record the date, commit, image digest, and outcome in the build log.

## Rollback

Redeploy the previous web image. The web service holds no durable state; the only browser-side state is the service-worker caches, which are versioned and cleaned when a new worker activates.

## Provisioning the web service (what was actually done, 2026-09-20)

In the existing `shaidago-staging` project and `staging` environment: `railway add --service web`; variables set with `railway variable set` (`APP_ENV=staging`; `API_INTERNAL_URL=http://api.railway.internal:8080`, because the API listens on the platform's `PORT`, 8080; `INTERNAL_WEB_CREDENTIAL_CURRENT` as a reference to the API's own variable, so the value is never copied or printed; a freshly generated `CLIENT_HMAC_KEY`; `TRUSTED_PROXY_HOPS=1`; `NEXT_PUBLIC_APP_ORIGIN` set to the public origin; `RAILWAY_DOCKERFILE_PATH=apps/web/Dockerfile`); health check `/health/live`, restart on failure (5 retries), and a 25 s drain set on the service; a Railway-generated domain; and `railway up --service web`, followed to a SUCCESS deployment. The public origin is `https://web-staging-0edf.up.railway.app`. The API and worker were not redeployed: they already run the latest backend commit.

**The `migrate` service was deleted** to make room: the Free plan allows five services and the project already had five. It is a finished one-shot job. To run a future migration, re-create it from `railway/migrate.railway.json` (an empty service, the migration-owner variables, start command `alembic upgrade head` then role provisioning), deploy it first, and delete it again if the plan limit requires; or upgrade the plan.

## Degradation drill (2026-09-20)

`API_INTERNAL_URL` was pointed at a port nothing listens on, the web service redeployed, and then restored. While the API was unreachable, `/health/live` stayed 200, `/en/offline` stayed 200, the directory showed "Project records could not be loaded... Nothing has been lost", and a tracking lookup returned a safe 503. After restoring the variable, the records returned.

## Fixture removal and temporary access (2026-09-20)

At the maintainer's request the synthetic record `fixture-scenario-success` was hidden on staging with `update app.projects set visibility='hidden' where slug='fixture-scenario-success'`; reverse it by setting `visibility='public'`. Rows that depend on it (reports, question runs) were left intact. The change was made through `railway ssh` using a temporary key that was removed from the Railway account and deleted locally afterwards. Recorded Source Scout replays exist only for that fixture, so hosted Source Scout now ends in a stated state on real records.

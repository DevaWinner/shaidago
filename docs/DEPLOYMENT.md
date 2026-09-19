# Backend deployment on Railway

Applies to the backend only (BE-110 to BE-112). The Next.js service, when it exists, is the only thing that receives the internal API URL and credential; nothing here exposes the API publicly.

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

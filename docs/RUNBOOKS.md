# Operational runbooks

Each runbook gives the trigger, immediate containment, safe diagnostics, the decision owner, recovery, verification, and follow-up. Commands are read-only unless marked **change**. None of them prints a secret or a private row: they read counts, states, and identifiers. `SVC` means the Railway service name (`api`, `worker`, `migrate`), and every command assumes `railway link` to the right project and environment (check `railway status`). **Decision owner** is the maintainer unless a named role is given.

## 1. API not ready

- **Trigger:** readiness is `unavailable` or `degraded`, the platform health check fails, or the web service reports 503.
- **Contain:** do nothing that widens exposure. If a bad release is suspected, redeploy the previous image (**change**: `railway redeploy --service api` on the previous deployment).
- **Diagnose:** `railway logs --service api --lines 200` (logs are redacted JSON; look for `error_code`); `railway ssh --service api -- python -c "import urllib.request as u,os;print(u.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/health/live').status)"`. Readiness names the failing component (`database`, `migrations`, `redis`, `object_storage`, `scanner`) as `ok` or `unavailable` only; call it with the internal credential from the web service, never paste the credential.
- **Recover:** fix the named component using its runbook (migration: 2; Redis: 3; storage: 4; scanner: 9).
- **Verify:** readiness `ready`; a public project read succeeds through the web service.
- **Follow-up:** record the cause; add a test if it was a code defect.

## 2. Migration failure or lock

- **Trigger:** the `migrate` deployment fails, or the API reports `migrations: unavailable`.
- **Contain:** do not deploy `api` or `worker`. Traffic keeps using the previous release (the previous image tolerates the previous schema).
- **Diagnose:** `railway logs --service migrate --lines 200`. A waiting run is held by the advisory lock: from `railway ssh --service migrate`, `psql "$DATABASE_URL" -Atc "select pid, state, now()-query_start from pg_stat_activity where query like '%alembic%' or query like '%pg_advisory_lock%'"`. `alembic current` shows the applied revision.
- **Recover:** fix the migration in a new revision (never edit an applied one), then redeploy `migrate`. If a partial revision left the database inconsistent, restore from backup (runbook 10) rather than editing rows.
- **Verify:** `migrate` exits 0; `alembic current` equals the code's head; API readiness `ready`.
- **Follow-up:** expand-migrate-contract if the change was not backward compatible.

## 3. Redis, job backlog, or dead letters

- **Trigger:** rate limits return 503, discovery runs stay `queued`, or dead-lettered jobs appear.
- **Contain:** rate-limited routes fail closed by design; do not disable the limiter. Pause the public discovery button in the web service if runs pile up.
- **Diagnose:** `railway logs --service worker --lines 200`; queue depth: `railway ssh --service worker -- python -c "import os,redis;r=redis.Redis.from_url(os.environ['REDIS_URL']);print(r.llen('shaidago:discovery'), r.llen('shaidago:discovery.XQ'))"` (live and dead-letter counts only); stuck runs: `psql` count of `app.discovery_runs` by `status` where `updated_at < now() - interval '15 minutes'`.
- **Recover:** restore Redis if it is down; the API and worker reconnect on their own. A run whose job was lost is re-queued by the next public request for that project or by a reviewer retry. Runs that exhausted retries are already `failed` with `retries_exhausted`.
- **Verify:** queue depth drains; a test run completes.
- **Follow-up:** if dead letters recur, fix the failing stage; do not raise retry limits.

## 4. Object storage unavailable

- **Trigger:** readiness `object_storage: unavailable`; attachments report `storage_failed`; evidence downloads return 503.
- **Contain:** reporting continues without attachments (a report is never lost); tell reporters nothing.
- **Diagnose:** `railway logs --service api --lines 200` for `storage_failed`; provider status page.
- **Recover:** restore access (credentials, bucket, network); rotate the access key if it may be exposed.
- **Verify:** readiness `ready`; a fictional upload is kept; a reviewer download succeeds.
- **Follow-up:** attachments refused during the outage are named in each receipt; no data repair is needed.

## 5. Provider outage or budget exhausted

- **Trigger:** Q&A or discovery returns 503, or runs show `search_rejected` or `analysis_provider_error`; the daily public budget is spent.
- **Contain:** none needed: Q&A falls back to the insufficient-evidence message and discovery shows the latest completed run or `unavailable`. Do not raise budgets to force results.
- **Diagnose:** `railway logs --service worker --lines 200` (provider errors carry codes, never prompts); provider dashboards for quota.
- **Recover:** restore or reissue the key (**change**); raise a budget only by a recorded decision.
- **Verify:** a fixture-free live check by a maintainer ( `tests/live`, opt-in ) or a public run completes.
- **Follow-up:** record spend and the trigger.

## 6. Suspected private-data leak

- **Trigger:** a private value (report text, contact, tracking code, handle, note, evidence) may have reached a public response, a cache, a log, a prompt, or a third party.
- **Contain (first hour):** stop the exposure: redeploy the previous image or scale the affected service to zero (**change**); purge any CDN or cache; rotate the internal credential and session key if reviewer access may be involved. Preserve evidence (runbook 11) before deleting anything.
- **Diagnose:** which value, which path, which time window. Search logs for the request IDs, not the values: `railway logs --service api --lines 1000 --json` filtered by `request_id`; the log redactor removes sensitive fields, so a value in a log is itself a finding. Count affected reports with `psql` (counts only).
- **Decision owner:** the maintainer with the privacy owner; disclosure duties are a legal decision, not a technical one.
- **Recover:** fix and add a canary test (`test_public_projection_proof.py` pattern); shred affected reports if required (`python -m shaidago.retention shred-report <id>`); rotate exposed keys (runbook 7).
- **Verify:** the canary test passes; the previous exposure path returns nothing.
- **Follow-up:** written incident record with timeline, scope, and corrective action.

## 7. Credential and key rotation

- **Trigger:** schedule, suspected exposure, or staff change.
- **Contain:** for a suspected exposure rotate first, investigate second.
- **Steps:** follow the table in [deployment](DEPLOYMENT.md) for the secret. For KEKs: add version, deploy, `railway ssh --service api -- python -m shaidago.shared.rotate_keks` (prints counts only), confirm `remaining 0 unavailable 0`, then remove the old version.
- **Verify:** readiness `ready`; a report detail decrypts; old credential no longer works.
- **Follow-up:** record date and owner.

## 8. Reviewer account disablement and session revocation

- **Trigger:** a reviewer leaves, a device is lost, or an account is suspected compromised.
- **Contain:** disable the account (**change**): `railway ssh --service migrate -- psql "$DATABASE_URL" -c "update app.reviewers set state='disabled', credential_version=credential_version+1, updated_at=now() where identifier='<identifier>'"`; disabling and a credential change revoke their sessions on the next request.
- **Diagnose:** last activity by identifier from the audit log (`select event, count(*) from app.audit_events where actor_id=<id> and occurred_at > now()-interval '7 days' group by 1`); inactive accounts: `python -m shaidago.retention review-reviewers 90`.
- **Verify:** the account cannot sign in; its old session returns 401.
- **Follow-up:** review what the account read (counts by event) with the privacy owner.

## 9. Evidence sanitation or scanner failure

- **Trigger:** readiness `scanner: unavailable` (ClamAV mode), many `scan_failed` or `malware_detected` attachment reasons, or sanitiser timeouts.
- **Contain:** the pipeline fails closed: nothing is stored when the scan cannot run. Never switch to `not_scanned_demo` outside the hosted demo (production refuses it).
- **Diagnose:** `railway logs --service api --lines 200` for `scan_failed`; scanner service logs and signature freshness.
- **Recover:** restore the scanner; refused attachments are named in receipts and need no repair.
- **Verify:** readiness `ready`; an EICAR test file is refused and a clean image is kept (fictional only).
- **Follow-up:** confirm signatures update.

## 10. Database backup and restore

- **Trigger:** data loss, a failed destructive migration, or a restore drill.
- **Contain:** stop writers (scale `api` and `worker` to zero, **change**).
- **Procedure:** restore to a new database from the platform backup or a `pg_dump`, then run `alembic upgrade head` under the owner role, then **replay destructions**: re-shred every report that has a `report_shredded` audit event (`select subject_id from app.audit_events where event='report_shredded'` then `python -m shaidago.retention shred-report <id>`) before serving traffic, because a backup holds keys shredded since it was taken. Re-disable any reviewer disabled since.
- **Verify:** readiness `ready`; row counts by table match expectations; a shredded report is unreadable.
- **Follow-up:** backups are not configured in the prototype; configuring and drill-testing them is a production requirement.

## 11. Rollback and incident evidence preservation

- **Trigger:** a bad release or any incident that may need review.
- **Preserve first:** note the deployment IDs, commit and image digests, and UTC times; export bounded logs to a private location (`railway logs --service <svc> --lines 5000 > incident-<date>.log`, then store it access-controlled, not in the repository); copy audit rows by time window with `psql \copy` of `app.audit_events` (they hold identifiers, not content).
- **Rollback:** redeploy the previous successful `api` and `worker` deployment (**change**); leave the schema as is (the expand step keeps the old app compatible). Decide separately about any schema or data repair.
- **Verify:** readiness `ready`; the smoke checklist in `docs/evidence/BE-114-staging-smoke.md` passes.
- **Follow-up:** incident record; add or extend the regression test.

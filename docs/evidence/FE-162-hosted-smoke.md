# FE-162 hosted smoke record

- **Date:** 2026-09-20 (UTC), staging.
- **Origin:** `https://web-staging-0edf.up.railway.app` (Railway project `shaidago-staging`, environment `staging`).
- **What ran:** the web service built from this repository's `apps/web/Dockerfile` (branch `release/review-close-and-deploy`, based on `main` at `7b7d0ac`), against the private `api` and `worker` already running the latest backend commit. Providers are recorded replays (`PROVIDER_MODE=replay`), the scanner is `not_deployed` (the hosted demo mode), and all data is fictional.
- **Command:** `HOSTED_ORIGIN=https://web-staging-0edf.up.railway.app pnpm --dir apps/web exec playwright test --config tests/playwright.hosted.config.ts` (`apps/web/tests/hosted/hosted-smoke.spec.ts`). Traces, screenshots, and video are off; nothing from the run is retained.
- **Browsers and viewports:** Chromium at 1280x720 (Desktop Chrome) and WebKit as an iPhone 13; the four locales are also checked at 360 px.

## Result: 23 passed, 3 skipped

| Check | Outcome |
| --- | --- |
| Production headers on hosted routes | CSP with `default-src 'self'` and `frame-ancestors 'none'`, `Strict-Transport-Security: max-age=31536000; includeSubDomains`, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy: same-origin`, public pages `public, max-age=0, must-revalidate`, private routes `no-store`, the worker `no-cache` with `Service-Worker-Allowed: /` |
| Private API not reachable or named | `api.railway.internal` does not resolve or connect from outside; the served HTML and every script contain no private hostname, credential name, or key name |
| Four languages | landing, directory, and a cited record open in en, ha, ig, and yo with real seeded data; no horizontal scroll at 360 px |
| Citation to source | a statement's citation opens its source page with the quoted passage |
| Q&A | an unanswerable question is refused ("The approved sources do not answer this"), not guessed |
| Public Source Scout | runs as a labelled replay; every result reads "discovered — not yet reviewed" |
| Report and tracking | a fictional anonymous report is accepted with a one-time code that is in no address or storage, the tracking lookup shows a public-safe status without the report text, a reload cannot show the code again, and an unknown code gets the generic result |
| Offline revisit and low-data (Chromium) | a saved record opens offline with "saved copy from ...", and low-data mode keeps the directory search |
| Service-worker inspection | no `/api`, report, tracking, handle, or reviewer URL is stored |
| Deliberate degradation | see `docs/DEPLOYMENT.md`: liveness and the offline page stay up and the pages say so safely |

**Skipped, stated:** offline navigation on WebKit (Playwright cannot navigate offline with a service worker) and the reviewer steps. The reviewer steps (sign in, queue without report text, open a report, sign out to a dead session) are in the spec and run when `HOSTED_REVIEWER` and `HOSTED_REVIEWER_PASSWORD` are supplied; no reviewer credential was available to this run, and creating a reviewer account is a maintainer decision.

## After the synthetic record was removed

At the maintainer's request `Fixture Scenario Success` was hidden (`visibility = 'hidden'`) in the staging database, so it no longer appears anywhere public. The smoke then used the real seeded record: 21 passed, 3 skipped. The Source Scout step now asserts a stated end state, because recorded replays exist only for the synthetic fixture.

## Limits

Staging on the Free plan: a Railway-generated domain, no custom domain, and one instance per service. HSTS is set for the generated domain only. Real-network Core Web Vitals were measured separately (see the audit).

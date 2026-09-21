# ShaidaGo web

This is ShaidaGo's independently tooled Next.js presentation and BFF stack. It contains the public project experience, private reporting and tracking flows, reviewer workspace, Source Scout interface, four-language catalogues, offline public-record support, and purpose-built same-origin Route Handlers.

The browser calls only this application. Server Components and Route Handlers reach the private FastAPI service through the generated OpenAPI client, while domain policy remains in FastAPI.

## Quality commands

Run from the repository root with pnpm 12.4.2 and Node 24.20.0:

```text
pnpm --dir apps/web dev
make web-format
make web-format-check
make web-lint
pnpm --dir apps/web typecheck
make web-unit
make web-component
make web-contract
make web-boundary
make web-ci-check
make web-e2e
make web-a11y
pnpm --dir apps/web build
make web-verify
```

`web-unit`, `web-component`, `web-e2e`, and `web-a11y` fail when their respective test layer has
no test files. They do not pass silently. Browser checks exercise the standalone production output
in Chromium and a mobile WebKit project; before running them in a new local or CI environment,
install the pinned browsers explicitly:

```text
pnpm --dir apps/web exec playwright install chromium webkit
```

`web-ci-check` validates the committed GitHub Actions workflow without network access. The hosted
workflow repeats frozen install, formatting, lint, types, unit/component, contract, and boundary
checks, then installs the pinned browsers for E2E and axe. It uploads no browser, coverage, or
test artifacts.

The automated tooling is development-only: ESLint checks Next.js, TypeScript, imports,
accessibility, and security rules; Prettier owns formatting; Vitest provides deterministic unit,
component, and coverage runs; MSW provides fixture-backed request interception; and Playwright
with axe-core runs browser and accessibility checks. The pnpm install policy allows only the
reviewed `msw` and `unrs-resolver` install hooks.

Tailwind CSS 4.3.3 and `@tailwindcss/postcss` 4.3.3 are MIT-licensed build tools. They compile the
Field Ledger token layer through `postcss.config.mjs` and add no browser runtime, external font
request, or third-party asset. `start:standalone` copies Next's compiled static assets and the
`public/` directory into the standalone output before browser tests or a local production preview.

## Runtime boundary

`next build` must work when `API_INTERNAL_URL` is unreachable. Server Components call the
private API through a server-only generated client; browsers call only purpose-built same-origin
Route Handlers. Do not add direct browser API, database, provider, or storage access.

At Node runtime, `instrumentation.ts` fails closed unless `APP_ENV`, `API_INTERNAL_URL`, and
`INTERNAL_WEB_CREDENTIAL_CURRENT` pass the server-only Zod schema. The URL and credential are read
at runtime, not build time. `NEXT_PUBLIC_APP_ORIGIN` is the sole optional browser setting; the
explicit public schema rejects every other `NEXT_PUBLIC_*` name and names that look secret-like.
`make web-boundary` builds with synthetic private canaries and scans every client JavaScript chunk
for the internal URL, service credentials, provider keys, storage keys, and server-only module
markers.

Public routes use `en`, `ha`, `ig`, and `yo` catalogues with matching keys and ICU variables.
Recovery views accept only a canonical UUID request ID, never raw error text or backend detail,
and unknown routes disclose nothing about a private record.

## Generated API client

`pnpm run api:generate` regenerates `src/lib/api/generated/schema.ts` and `client.ts` from
`contracts/openapi.json` with pinned `openapi-typescript` 7.13.0 and `openapi-fetch` 0.17.0 (both
MIT). Never edit those files; `pnpm run contract` (`make web-contract`) fails on drift. The
generated client is a transport factory only: FE-031 wraps it in a server-only module.

## Server-only API client

`src/lib/api/server.ts` (`serverApi()`) is the only Server Component path to the private API. It
reads runtime configuration on first call, sends `Authorization: Bearer web.<credential>`, forwards
only validated `X-Request-Id`, `X-Shaidago-Locale`, `X-Shaidago-Client-Hmac`, and `If-None-Match`, and
returns `ok`, `not_modified`, `problem` (stable `code`, never backend text), or `unavailable`.
Reads retry once for a transient 503 or network error; there is no mutation retry and no logging. A
unit test fails if a client component imports it.

## BFF request guards

`src/lib/bff/` holds the shared, domain-free guards every Route Handler composes: `resolveOriginPolicy`
and `checkOrigin` (exact Origin; deployed stages need `NEXT_PUBLIC_APP_ORIGIN` or every browser
mutation is refused; `X-Forwarded-*` is never trusted; development and test also accept the browser's own `Host`), `verifyCsrfToken`, `guardMutation` (Origin,
CSRF, header-only body preflight, idempotency key, in that order), `readBoundedJson`/`limitBodyStream`
(streamed byte caps), `buildBackendHeaders` (allowlist only), `backendSignal` (abort and timeout), and
`problemResponse` (stable code, no backend text, `no-store`). Idempotency keys are lower-case
canonical UUIDs, matching the API.

## Public mutation handlers

The nine handlers under `app/api/` (`public/questions`, `public/discovery`, `public/discovery/[runId]`,
`reports`, `tracking/lookup`, `tracking/follow-up`, `reporter-handle`, `reporter-handle/reports`,
`reporter-handle/delete`) each call one typed operation through `src/lib/bff/public-handler.ts`. Browsers
send an optional `X-Shaidago-Locale` and, for idempotent operations, a lower-case UUID
`Idempotency-Key` that is generated once per user intent and reused only for retries of that intent.
Responses are always `no-store`; failures are `application/problem+json` with a stable `code`.

## Reviewer session and handlers

Reviewer cookies are created and read only in server code (`src/lib/bff/reviewer-session.ts`). The
session token and the CSRF token are both `HttpOnly`; neither reaches JavaScript, a response body,
or a log. Development/test use `sg_session`/`sg_csrf` on `http://localhost`; staging and production
use `__Host-sg_session`/`__Host-sg_csrf` with `Secure`, and `NEXT_PUBLIC_APP_ORIGIN` must be set or
every browser mutation is refused. The 17 handlers under `app/api/reviewer/` call one typed operation
each, apply Origin then session then CSRF then body limits, and never decide roles, transitions, or
publication. Evidence downloads are streamed with re-asserted `attachment`, `nosniff`, sandbox CSP,
and `no-store` headers.

## Styling and components

Styling is Tailwind CSS 4 with shadcn conventions: `components/ui/*` built with `cva` variants,
`cn()` (`clsx` + `tailwind-merge`, aware of the theme's `text-ledger-*` sizes), and `data-slot`
attributes that tests select by. `components.json` records the shadcn setup. The shadcn semantic
names (`bg-primary`, `text-muted-foreground`, `border-border`, ...) are aliases for the approved
Field ledger tokens in `app/globals.css`, so the visual direction stays authoritative. Base element
rules live in `@layer base` so utilities on components win. Every string is a prop or a typed
message record (`src/content/`); nothing hard-codes copy.

## Client HMAC

The BFF forwards `X-Shaidago-Client-Hmac`: HMAC-SHA256 of the client address and the UTC day under
the web-only `CLIENT_HMAC_KEY` (base64, 32+ bytes; required in staging and production). Only the
`X-Forwarded-For` entry `TRUSTED_PROXY_HOPS` places from the right is used (Railway edge: 1), so a
client cannot choose its own address. The address is never forwarded or stored, and the value
rotates daily.

## Locale routing

Public pages live under `/en`, `/ha`, `/ig`, and `/yo`. `proxy.ts` (next-intl) redirects unprefixed
paths using the `NEXT_LOCALE` cookie, then `Accept-Language`, else `en`, keeping the query; it skips
`/api`, `/_next`, and any path with a file extension. `REVIEWED_LOCALES` in `src/i18n/routing.ts`
is derived from `messages/status.json`. All four catalogues currently pass the repository's
maintainer-review gate. Hausa, Igbo, and Yoruba have not received an independent second-language
review, and the public documentation says so.

## Messages

Copy lives in `messages/{en,ha,ig,yo}.json` by domain, with `messages/status.json` recording each
locale's per-domain review status. English is the source. All four locales are marked `reviewed`
by the maintainer; this does not claim independent language review. A value is `null` while a
translation is pending; set a domain to `reviewed` or `machine_assisted` only with a named reviewer
and date. `pnpm run messages:check` (also part of `make web-contract`) enforces identical
keys, valid ICU, the same variables and types, identical `select` branches, and consistent status.
`resolveDomain` in `src/i18n/catalogue.ts` serves a locale's text only when its domain is reviewed
and complete; otherwise it returns the flagged English original and the page says so.

## Adding a key

Add it to `messages/en.json` and to `ha.json`, `ig.json`, and `yo.json` with the value `null`, then run
`pnpm run messages:check`. The current `pendingKeysAllowed: false` setting makes any missing
translation fail the check. Prefer a new domain for a new feature because a served domain with a
`null` key falls back to visibly labelled English.

## Language switching

Language links point at the same route in the other language, built by `localeHref` from parsed route
state: path segments and an allowlist of shareable filters, never the raw URL. A `cursor` is always
dropped, because it is valid only for the same filters and locale. A page that holds an unsaved
private draft calls `setUnsavedDraft(true)` (`src/lib/draft-guard.ts`, memory only); the language link
then asks before leaving. After a switch the next page announces the new language in the shell's
polite status region.

## Public pages and caching

`/{locale}` and `/{locale}/projects` are rendered per request and read the API only from the server.
Public reads are cached by `src/lib/api/public-data.ts` (`unstable_cache`, 60 seconds, key = language and
filters, tag `public-catalogue`), never at the fetch level: Next will not cache a fetch that carries an
`Authorization` header on a dynamic route, and `dynamic = "force-dynamic"` turns caching off entirely, so
do not add it to these pages (use `connection()` when a page needs request-time rendering). Only the
public catalogue reads are wrapped; publishing an update expires the tag. Do not add a `loading.tsx` to a
public route: Next streams its placeholder and swaps the content in with inline script, which leaves a
no-JavaScript visitor on the placeholder.

Browser tests run against `tests/support/mock-api.mjs`, a fictional stand-in for the two public
endpoints, on port 3200 (e2e) or 3201 (accessibility). It has stateless switches: `q=__unavailable`
returns a 503.

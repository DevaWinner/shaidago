# ShaidaGo web

This is the independently tooled Next.js presentation/BFF stack. Its foundation provides a
semantic English-source shell, safe root/route recovery surfaces, metadata, and robots policy;
product routes, the Field Ledger design system, locale routing, and BFF handlers arrive only in
their owning build-order tasks.

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

The automated tooling is development-only: ESLint checks Next.js, TypeScript, import,
accessibility, and security rules; Prettier owns formatting; Vitest provides deterministic
unit/component/coverage execution; MSW provides fixture-backed request interception; and
Playwright plus axe-core owns browser and accessibility smoke tests. The pnpm install policy
allows only reviewed `msw` and `unrs-resolver` install hooks. MSW's hook has no effect until a
future task configures a worker directory; `unrs-resolver` prepares the platform resolver used by
the ESLint import path.

## Runtime boundary

`next build` must work when `API_INTERNAL_URL` is unreachable. Server Components later call the
private API through a server-only generated client; browsers call only purpose-built same-origin
Route Handlers. Do not add direct browser API, database, provider, or storage access.

At Node runtime, `instrumentation.ts` fails closed unless `APP_ENV`, `API_INTERNAL_URL`, and
`INTERNAL_WEB_CREDENTIAL_CURRENT` pass the server-only Zod schema. The URL and credential are read
at runtime, not build time. `NEXT_PUBLIC_APP_ORIGIN` is the sole optional browser setting; the
explicit public schema rejects every other `NEXT_PUBLIC_*` name and names that look secret-like.
`make web-boundary` builds with synthetic private canaries and scans every client JavaScript chunk
for the internal URL, service credentials, provider keys, storage keys, and server-only module
markers.

The root document uses English source copy temporarily. FE-050 owns `en`, `ha`, `ig`, and `yo`
locale routing, message parity, and human review status; do not add a second locale layout or a
silent fallback before then. Recovery views accept only a canonical UUID request ID, never raw
error text or backend detail, and unknown routes disclose nothing about a private record.

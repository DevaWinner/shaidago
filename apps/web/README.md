# ShaidaGo web

This is the independently tooled Next.js presentation/BFF stack. It is intentionally a
non-visual, API-free foundation until the approved frontend build order enables each route and
surface.

## Commands

Run from the repository root with pnpm 12.4.2 and Node 24.20.0:

```text
pnpm --dir apps/web dev
pnpm --dir apps/web typecheck
pnpm --dir apps/web build
```

`next build` must work when `API_INTERNAL_URL` is unreachable. Server Components later call the
private API through a server-only generated client; browsers call only purpose-built same-origin
Route Handlers. Do not add direct browser API, database, provider, or storage access.

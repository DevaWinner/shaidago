# Frontend/backend handoff contract

- **Status:** implemented backend handoff for the frontend build
- **Contract version:** OpenAPI `0.0.0`; frontend fixture schema `1`
- **Authoritative HTTP schema:** [`contracts/openapi.json`](../contracts/openapi.json)
- **Machine values and transitions:** [`contracts/controlled-vocabulary.json`](../contracts/controlled-vocabulary.json)
- **MSW-ready examples:** [`contracts/frontend-fixtures.json`](../contracts/frontend-fixtures.json)

This document records browser and BFF semantics that OpenAPI cannot express completely. The
frontend must use generated OpenAPI types and these rules; it must not inspect Python models,
migrations, database tables, or worker code to infer behaviour.

## Boundary and forwarding

The browser calls only the Next.js origin. Server Components may call the private API directly
through a server-only generated client. Browser mutations, uploads, reviewer requests, and polls
use purpose-built same-origin Route Handlers; there is no generic proxy.

Every private-API request except `GET /health/live` carries the server-only internal bearer
credential. The BFF may forward a validated `X-Request-Id`, `X-Shaidago-Locale`, and a pseudonymous
`X-Shaidago-Client-Hmac`. None of the credential, API hostname, reporter secrets, session token,
CSRF token, private response bodies, or signed/storage details may enter a client bundle, URL,
browser log, analytics event, or persistent browser storage.

## Reviewer sessions, cookies, and CSRF

`POST /v1/auth/sessions` returns the API session token and CSRF token once to the BFF. The BFF sets
the browser cookie using the returned cookie policy and removes `session_token`, `csrf_token`, and
the cookie policy from its browser response. The cookie is `HttpOnly`, `SameSite=Lax`, path `/`, and
is `Secure` with the `__Host-sg_session` name in staging/production; development/test uses
`sg_session` over loopback HTTP.

The BFF sends the session token to reviewer endpoints in `X-Shaidago-Session`. It sends the CSRF
token in `X-Shaidago-Csrf` for every reviewer mutation after applying its same-origin check.
Authentication is never treated as authorisation: a `401` means no usable session and a `403`
means the authenticated role lacks the capability (or CSRF failed). Sign-out revokes the backend
session and clears the browser cookie even if the browser is already unauthenticated.

## Errors and retries

Errors use `application/problem+json`. Branch on `code`, never on the English `title` or `detail`.
Validation errors add `errors[]` with a field path and machine code; they never echo the submitted
value. Preserve and surface `X-Request-Id` for support without exposing request content.

- Retry `429` only after `Retry-After`; do not create a parallel retry timer.
- Retry a safe read or an idempotent mutation after a transient `503` with bounded backoff.
- Do not retry `401`, `403`, `404`, `409`, `413`, `415`, or `422` unchanged.
- Treat network loss after a mutation as unknown completion. Reuse the same `Idempotency-Key`
  where the operation accepts one; otherwise refetch state before offering another mutation.

## Cache policy

Public project catalogue/detail/source `GET` responses are `public, max-age=60`, carry an `ETag`,
and vary on locale. Forward `If-None-Match`; a `304` retains the existing body and is not an empty
state. All errors are `no-store`.

Reviewer data, report submission and tracking, handles, follow-up answers, Q&A, reviewer/public
discovery state, evidence downloads, and auth responses are `no-store`. They must not enter Next.js
data caches, a CDN cache, a service worker, IndexedDB, local/session storage, or a persisted query
cache. Public discovery results may remain in the current in-memory view while offline, but a
report-scoped run must not be persisted.

## Idempotency and one-time responses

Generate a fresh opaque `Idempotency-Key` for each user intent and reuse it only when retrying that
same intent and body. The report submission, reporter-handle creation, and reporter follow-up answer
operations enforce it. A reused key with the same request replays the original response with
`Idempotency-Replayed: true`; a changed request returns `409 idempotency_conflict`.

The following values are one-time display only:

| Operation | Values | Frontend rule |
| --- | --- | --- |
| `reports_submit` | `tracking_code` | Show a save/copy/print step immediately. Never place it in a URL, log, analytics, persisted draft, or browser storage. |
| `reporter_handles_create` | `handle`, `passphrase` | Show both once with `recoverable: false`. Never persist or offer recovery. |
| `auth_sign_in` | `session_token`, `csrf_token` | BFF-only. Convert to the secure session cookie flow and never return them to browser JavaScript. |

The fixture manifest contains synthetic one-time values solely for deterministic tests. Test code
must not assert that those literal values are accepted credentials.

## Cursors and bounded lists

Treat every cursor as opaque. Send only the previous response's `next_cursor`, with exactly the
same filters and locale, and replace rather than concatenate results when filters change. A cursor
that does not match its query returns `400 invalid_cursor`. Project, reviewer queue, and reviewer
note pages default to 20 and cap at 50. Never decode a cursor or construct one in the frontend.

## Status values, transitions, and terminal states

Import machine values from generated OpenAPI types and localise labels by value. The complete
meaning, actors, allowed transitions, and terminal flags are generated in
[`docs/CONTROLLED_VOCABULARY.md`](CONTROLLED_VOCABULARY.md); the JSON contract is authoritative.
Do not infer a transition from the UI or enable one merely because a button is visible. Send the
backend's current status/version and handle a conflict by refetching.

Discovery states are `queued`, `searching`, `analysing`, `needs_review`, `complete`, `failed`, and
`cancelled`. Public polling stops at `complete`, `failed`, or `cancelled`; report-scoped reviewer
polling also stops at `needs_review` until a reviewer acts. Counts are real; the frontend must not
turn stages into invented percentages.

## Polling hints

For an active discovery run, poll after 2 seconds, then 3, 5, 8, and at most every 10 seconds.
Send the last `version` as `since_version`; `304` means keep the current result. Pause when offline
or hidden and resume with the same run ID after reconnect/navigation where the scope permits. Stop
on terminal state, session loss, `404`, or explicit cancellation. Respect `Retry-After` exactly and
never start a second run as a polling fallback. Q&A, tracking, and reviewer report detail are
user-initiated reads, not background polls.

## Uploads and partial attachment handling

Report submission accepts at most three JPEG, PNG, WebP, or PDF attachments, at most 10 MiB each.
The complete multipart request is capped at three file limits plus 64 KiB of fields. The browser may
re-encode images and remove metadata for usability, but the backend repeats type sniffing,
bounded decoding, metadata removal, scanning, and sanitation.

A report can be accepted when one or more attachments are rejected. A `201` receipt contains one
ordered outcome per supplied file (`position`, `kept`, `reason`). Show each outcome and retain the
tracking-code step; do not re-submit the whole report to repair a rejected attachment. A `413`
means the request itself was not accepted. Attachment names/content are never echoed by the API.

## Q&A and discovery citations

Q&A statements refer to opaque citation IDs. Every ID must resolve within the same response's
`sources`, which expose only approved public passages for that project. Render the answer as text,
link citations to their supplied source URL, and show the insufficient-evidence state verbatim when
`insufficient_evidence` is true. AI text is an explanation, never a source or status decision.

Discovery sources are different: every card and analysis remains labelled
`discovered — not yet reviewed`. Analysis citations resolve only to source cards from the same run.
A reviewer `attach` decision creates a pending source; it does not approve a fact or publish an
update. Never render a discovered source with approved-source styling.

## Fixture package

`contracts/frontend-fixtures.json` is generated from OpenAPI. Each operation contains its method,
OpenAPI path, MSW path, and one concrete fixture for every documented response status. The named
scenario set is `success`, `empty`, `stale`, `partial`, `denied`, `rate_limited`,
`dependency_down`, and `validation`. All people, projects, URLs, IDs, report content, and
credentials in it are synthetic.

```text
make frontend-contract-generate  # regenerate after OpenAPI changes
make frontend-contract-check     # drift check; part of make backend-verify
```

The generated file is a transport fixture, not user-facing copy. Frontend tests should override
the requested locale and visible text with the reviewed locale catalog while preserving names,
dates, amounts, uncertainty, and source links.

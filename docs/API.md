# Private API contract

The FastAPI service (`services/platform`) is private: browsers reach only the Next.js origin, and the BFF calls this API. [`contracts/openapi.json`](../contracts/openapi.json) is generated from the application and is the authority for implemented HTTP shapes. Do not edit it by hand.

```text
make openapi-generate   # rewrite contracts/openapi.json
make openapi-check      # fail if it differs from the application (part of make backend-verify)
```

Generation uses fixed synthetic settings, so it needs no environment, database, or provider. Change a route or model, regenerate, and commit both in the same change.

## Calling the API

- Every request except `GET /health/live` needs `Authorization: Bearer <caller-id>.<secret>` ([ADR-0002](decisions/0002-bff-authority-split-and-internal-service-authentication.md)). The pilot caller is `web`. This proves the caller is the BFF only; it grants no reviewer or reporter authority.
- After authentication, the BFF may forward `X-Request-Id` (a lower-case UUID), `X-Shaidago-Locale` (`en`, `ha`, `ig`, or `yo`), and `X-Shaidago-Client-Hmac` (64 lower-case hex characters). Invalid values are replaced or ignored.
- Every response carries `X-Request-Id`.

## Public project endpoints

All are `GET`, read only through the restricted `shaidago_public` database role and the `public_api` views, and return `Cache-Control: public, max-age=60`, an `ETag` that changes exactly when the body changes (send `If-None-Match` for a `304`), and `Vary: X-Shaidago-Locale`. The locale comes from `X-Shaidago-Locale`; text is never labelled as translated when it is an English fallback (`text.is_fallback`, `text.served_locale`).

| Endpoint | Returns |
| --- | --- |
| `/v1/localities` | `items`: slug, name, kind, parent slug, enabled locales |
| `/v1/projects` | A page of project summaries, newest update first (ties broken by ID). Filters: `locality`, `category`, `status`, `verification` (a published fact in that state), `q` (full-text, at most 100 characters). `limit` defaults to 20 and is capped at 50; `cursor` is the opaque `next_cursor` of the previous page and only works for the same filters and locale. Unknown parameters and invalid values are `422`; a bad cursor is `400 invalid_cursor`. |
| `/v1/projects/{slug}` | Text, status, dates, and every published fact and update with its citations (source, exact passage, location, and `information_class`). Facts and updates carry `ai_generated: false`. |
| `/v1/projects/{slug}/sources/{source_id}` | Approved source metadata and only the passages this project cites from it. |

An unknown, hidden, or unpublished project or source returns the same `404 not_found` body. A fact or update with no visible citation is never returned.

## Errors

Every error is `application/problem+json`, `Cache-Control: no-store`, with `type`, `title`, `status`, `code`, `detail`, `request_id`, and, for validation failures, `errors` (`field` and rule `code`, never the submitted value). The `code` is the stable contract; the BFF localises display text from it.

| Status | `code` | Meaning |
| --- | --- | --- |
| 400 | `bad_request` | Request not understood |
| 401 | `unauthenticated` | Missing or invalid internal credential (identical for every cause) |
| 403 | `forbidden` | Not permitted |
| 404 | `not_found` | Unknown resource or route |
| 405 | `method_not_allowed` | Method not supported |
| 409 | `conflict` | Conflicts with current state |
| 413 | `payload_too_large` | Body over the limit |
| 415 | `unsupported_media_type` | Content type not accepted |
| 422 | `validation_failed` | Invalid fields |
| 429 | `rate_limited` | Too many requests (`Retry-After` when known) |
| 500 | `internal_error` | Unexpected failure; no detail is returned |
| 503 | `dependency_unavailable` | A required dependency is down |

## Health

- `GET /health/live`: process responds; no credential and no dependency check.
- `GET /health/ready`: `ready`, `degraded` (only an optional provider is down; HTTP 200), or `unavailable` (a required dependency is down; HTTP 503), with each component reported only as `ok` or `unavailable`. No dependency probes are registered yet, so the running service currently reports `ready` with no components; each probe lands with its owning task (BE-031, BE-033, and the Redis and storage tasks).

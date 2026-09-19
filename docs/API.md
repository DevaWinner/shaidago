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

## Reviewer sign-in

Both endpoints are for the trusted BFF only; the BFF, not the API, sets the browser cookie.

- `POST /v1/auth/sessions` with `{identifier, password}` returns `201` once with `session_token`, `csrf_token`, `expires_at`, `idle_timeout_seconds`, the cookie policy the BFF must apply (`name`, `secure`, `http_only`, `same_site`, `path`, `max_age_seconds`), and `reviewer.role`. It is `no-store`. Every failure (unknown identifier, wrong password, disabled account, malformed identifier) is the same `401 invalid_credentials`. Attempts are limited per client and per client-and-identifier (`429` with `Retry-After`), keyed by the forwarded client HMAC, so an attacker elsewhere cannot lock a reviewer out. Bodies over 2 KiB are `413`. If the limiter's Redis is unreachable the request fails closed (`503`).
- `DELETE /v1/auth/sessions/current` revokes the session (`204`).
- Every later reviewer request carries the session token in `X-Shaidago-Session` and, for state-changing methods, the CSRF token in `X-Shaidago-Csrf` (`403 csrf_invalid` otherwise). The API never reads cookies, and the internal service credential is never reviewer authority (`401 unauthenticated` without a session; `403 forbidden` when the role lacks the capability).

## Private report submission

`POST /v1/reports` (multipart, `Idempotency-Key` required) stores a private report. Fields: `project_slug`, `concern_category`, `description` (10 to 8000 characters), optional `contact_channel` (`email`, `phone`, `messaging_app`) with `contact_value` (both or neither), and up to three `attachments` (10 MB each, JPEG, PNG, WebP, or PDF). Reports are anonymous unless a contact is given, and nothing is published.

- The body is capped while it streams (413 `payload_too_large`); other content types get 415; invalid fields get 422 naming the field and rule only, never the submitted value.
- The 201 receipt holds the tracking code (shown once), `status: received`, `published: false`, `contact_saved`, and one outcome per attachment (`position`, `kept`, and a stable `reason`). A report is accepted even when an attachment is refused, and the receipt says which. No internal ID, name, or content is echoed.
- Retrying with the same key and request within the replay window returns the identical receipt with `Idempotency-Replayed: true`; the same key with a different request is 409 `idempotency_conflict`.
- Submissions are rate limited per client (429 with `Retry-After`). Every response is `Cache-Control: no-store`.

## Tracking status lookup

`POST /v1/report-status:lookup` takes `{"code": "..."}` in the body (never in a path or query string) and returns `status`, `status_updated_at`, the newest reviewer-safe `message`, a `next_action` code, and `follow_up_questions` (empty until BE-067). Codes are accepted in any case and with spaces or hyphens. A malformed, unknown, or unreachable code all give the same 404 `tracking_code_not_recognised`. Lookups are limited per client and per client and code prefix (429 with `Retry-After`), every call takes at least a fixed minimum time, and no response is cacheable or echoes the code.

## Optional reporter handles

A handle is optional and carries no identity: `POST /v1/reporter-handles` (with `Idempotency-Key`) returns a generated `SG-H-XXXX-XXXX` handle and a six-word passphrase exactly once (`recoverable: false`; nobody can show them again). `POST /v1/reporter-handles:list-reports` lists public-safe statuses for the handle's reports and `POST /v1/reporter-handles:delete` unlinks every report and removes the credential; the reports stay, fully anonymous. Credentials go in POST bodies only. A report may carry a handle (`reporter_handle`, `reporter_passphrase` form fields) but not a contact channel as well.

Every credential failure (unknown, wrong, deleted, or in backoff) is the same 403 `invalid_reporter_credentials`, and a rejected submission stores nothing. Failures are limited per client, per client and handle, and per handle with a backoff that starts after three failures, doubles from 5 seconds, is capped at 15 minutes, and never locks permanently. There is no recovery or reset endpoint.

## Follow-up answers

A reviewer's questions appear on the tracking lookup (`follow_up_questions`: `question_id`, `text`, and `state` of `open`, `answered`, `skipped`, or `unsafe`); answers are never returned. `POST /v1/report-status:answer-follow-up` (with `Idempotency-Key`) takes `question_id`, `kind` (`answered`, `skipped`, or `unsafe`), `answer` (only with `answered`, up to 2000 characters), and exactly one credential: a tracking `code`, or a `handle` with its `passphrase`. It answers only a question about the caller's own report, once. Every other case (someone else's question, unknown, already answered, withdrawn, bad credential) is one generic problem: 404 `tracking_code_not_recognised` for a code, 403 `invalid_reporter_credentials` for a handle. The answer is encrypted before storage. Answering the last open question of a report that needs information resumes review.

## Reviewer queue and report detail

Every route needs a reviewer session (`X-Shaidago-Session`) and a role holding the capability; every response is `no-store`.

- `GET /v1/reviewer/reports` returns a page of triage rows, oldest first: `report_id`, `project_slug`, `concern_category`, `risk_level`, `status`, `version`, `created_at`, `status_updated_at`, `has_contact`, `evidence_count`, `open_follow_ups`. No text, contact, handle, or evidence detail. Filters: `status` (repeatable), `risk_level`, `concern_category`, `project`. `limit` defaults to 20 (cap 50); a `cursor` only works for the same filters (`400 invalid_cursor` otherwise); unknown parameters are `422`.
- `GET /v1/reviewer/reports/{report_id}` returns the report with its decrypted description, status history, follow-up questions and answers, evidence metadata (`evidence_id`, name, type, size, sanitation and scan state; never an object key or URL), and the reviewer-only handle track record. `include_contact=true` additionally returns the contact; it needs the `contact_read` capability and is audited by the database before the value is returned. An unknown report is `404 not_found`. Each view writes a `report_detail_viewed` audit event holding identifiers only.
- `version` is the token later commands send back to prove they acted on the current state.

## Reviewer decisions

- `POST /v1/reviewer/reports/{report_id}/status-transitions` takes `command`, `expected_status`, `expected_version` (from the detail response), and optionally `internal_reason` (private, encrypted, never shown to the reporter; required for `reopen`) and `reporter_message` (shown on tracking; a fixed default is used when omitted). The commands and the states they leave are the `report_status` machine in `contracts/controlled-vocabulary.json`. A view that is no longer current is `409 report_version_conflict`; a command that does not exist from the current status for the caller (including the reporter-only `record_follow_up`) is `409 report_status_transition_not_allowed` and is audited. Every response says `published: false`: a decision never publishes text.
- `POST /v1/reviewer/reports/{report_id}/follow-up-questions` (`201`, `question_id`) adds a question the reporter sees on tracking (5 to 500 characters, at most 10 open, not on a closed report). `POST .../follow-up-questions/{question_id}:withdraw` withdraws one (`204`). Neither changes the report's status.

## Reviewer notes

- `POST /v1/reviewer/reports/{report_id}/notes` with `{body}` (plain text up to 4000 characters; markup such as `<b>` or `<script>` is `422 markup_not_allowed`) returns `201` with `note_id` and `created_at`. Notes are append-only: there is no edit or delete, and a correction is a new note.
- `GET /v1/reviewer/reports/{report_id}/notes` pages notes oldest first (`limit`, `cursor`) with `note_id`, `created_at`, the author's reviewer identifier, and the decrypted `body` (`null` if its key was destroyed). Notes never appear on tracking, the public API, or the report detail. Responses are `no-store`; creation is audited by note ID only.

## Reviewer evidence download

`GET /v1/reviewer/reports/{report_id}/evidence/{evidence_id}/content` returns the sanitised file as an attachment (`Content-Disposition: attachment`, the stored type, `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, a sandboxing `Content-Security-Policy`, and `X-Evidence-Scan-State`: `clean` or `not_scanned_demo` on the hosted demo). There is no signed URL: access is checked on every request, the decision is audited before any byte is read (`report_evidence_download_granted` or `_denied`, IDs only), and the object key never leaves the service. An unknown report, an unknown file, and a file that belongs to another report are the same `404 not_found`; bytes that fail the recorded size and SHA-256 check are never served (`503`).

## Reviewer public updates

Publishing is a separate act from any status change, with its own record.

- `POST /v1/reviewer/reports/{report_id}/public-updates` creates a private draft (`201`) from `statement` (10 to 2000 characters, no markup), `effective_on`, optional `last_checked_on` (not in the future), `verification_state`, and 1 to 5 `citations` (`source_version_id`, an exact `passage` of that approved version, and `location_label`; the offset is computed). The report must currently be `verified_for_public_update` (`409 public_update_report_not_verified`). The response is a preview.
- `GET .../public-updates/{update_id}` returns the preview: `update` is the public projection exactly as `GET /v1/projects/{slug}` would show it (same model, same ID), `issues` lists what blocks publication (`field` and stable `code`), `can_publish`, `report_status`, `report_version`, and `preview_digest`. Issues include unmet citation, date, and verification rules; tracking codes, handles, contact values or any email or phone-like text, reviewer names, and six-word runs copied from the report, answers, or notes (`report_text`); and guarded words such as `corrupt`, `fraud`, `complete`, or `abandoned` that no cited passage contains (`unsupported_term_<word>`).
- `POST .../public-updates/{update_id}:publish` with `{preview_digest}` confirms that exact preview. A digest that no longer matches (the text, a source, or the report changed) is `409 preview_stale`; a report no longer verified is `409 public_update_report_not_verified`; a draft already published or withdrawn is `409 public_update_not_draft`; unmet requirements are `422 publication_incomplete` with the same issue codes. On success (`200`) the public update and its citations are written in one transaction with an audit event; the report's status is not changed.
- `POST .../public-updates/{update_id}:withdraw` (`204`) withdraws a draft. `GET .../public-updates` lists the report's drafts (at most 50).

## Source Scout (discovery)

Every result is labelled `discovered — not yet reviewed`; nothing found here is attached, verified, or published. Runs execute in the worker, so responses report progress and a job is identified by the run ID only.

- `POST /v1/projects/{slug}/discovery-runs` starts or re-uses the single shared public run for a project and returns `action`: `create`, `reuse_fresh`, `show_latest_completed` (the daily budget `DISCOVERY_PUBLIC_DAILY_RUNS` is spent), or `unavailable`, with `run_id`, `status`, and `demo_replay` (true when providers are in replay mode). Rate limited per client (`429`).
- `GET /v1/discovery-runs/{run_id}` returns `status`, `version`, `progress` (`results_found`, `fetched`, `analysed`), source cards (URL, publisher domain, title, preliminary type, publication date with provenance and a conflict flag, excerpt, availability), and, only when the run is `complete`, the validated analysis. `?since_version=N` answers `304` when nothing changed. A report-scoped run id is a `404`.
- Public callers cannot cancel a shared run or answer its follow-up questions.
- Reviewer (all `no-store`): `POST /v1/reviewer/reports/{report_id}/discovery-runs:plan` returns the exact outbound query, each term's source (`suggested_by`), the exclusions with a reason code, and `plan_digest`; `POST .../discovery-runs` with `concepts` and `approved_digest` creates a report-scoped run (`409 query_changed` if the query differs from the approved one); `GET /v1/reviewer/discovery-runs/{run_id}`; `POST .../discovery-runs/{run_id}:cancel` (`cancelled` now if queued, else `cancel_requested`); `POST .../{run_id}:review` with `approve_completion` or `reject_run`; `POST .../{run_id}/follow-up-answers` (`answered`, `skipped`, or `unsafe`; answers are encrypted); and `POST /v1/reviewer/discovered-sources/{source_id}/decision` with `attach`, `reject`, `defer`, or `reconsider` and a reason (encrypted). Attaching creates a *pending* source and never approves a fact.

## Errors

Every error is `application/problem+json`, `Cache-Control: no-store`, with `type`, `title`, `status`, `code`, `detail`, `request_id`, and, for validation failures, `errors` (`field` and rule `code`, never the submitted value). The `code` is the stable contract; the BFF localises display text from it.

| Status | `code` | Meaning |
| --- | --- | --- |
| 400 | `bad_request` | Request not understood |
| 401 | `unauthenticated` | Missing or invalid internal credential (identical for every cause) |
| 403 | `forbidden` | Not permitted |
| 404 | `not_found` | Unknown resource or route |
| 405 | `method_not_allowed` | Method not supported (`Allow` lists every method the path supports) |
| 409 | `conflict` | Conflicts with current state |
| 413 | `payload_too_large` | Body over the limit |
| 415 | `unsupported_media_type` | Content type not accepted |
| 422 | `validation_failed` | Invalid fields |
| 429 | `rate_limited` | Too many requests (`Retry-After` when known) |
| 500 | `internal_error` | Unexpected failure; no detail is returned |
| 503 | `dependency_unavailable` | A required dependency is down |

## Health

- `GET /health/live`: process responds; no credential and no dependency check.
- `GET /health/ready`: `ready`, `degraded` (only an optional provider is down; HTTP 200), or `unavailable` (a required dependency is down; HTTP 503), with each component reported only as `ok` or `unavailable`. The running service registers `database`, `migrations`, `redis`, `object_storage`, and `scanner` (the last only when `SCANNER_MODE=clamd`); all are required.

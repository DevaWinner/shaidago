# Frontend BFF operation map

- **Task:** FE-004 — BFF operation map
- **Status:** Active control
- **HTTP contract:** [`contracts/openapi.json`](../contracts/openapi.json), version `0.0.0`
- **Browser/BFF semantics:** [`FRONTEND_BACKEND_CONTRACT.md`](FRONTEND_BACKEND_CONTRACT.md)
- **Route ownership:** [`FRONTEND_ROUTE_MATRIX.md`](FRONTEND_ROUTE_MATRIX.md)

This is the implementation ledger for browser-facing routes and server-rendered reads. It maps
every implemented non-health operation to exactly one transport owner before `apps/web` exists.
The browser communicates only with the Next.js origin. The private FastAPI hostname, service
credential, storage details, and provider credentials remain server-only.

## 1. Boundary rules

- A `Server read` is a Server Component or server action helper calling the private API through
  `src/lib/api/server.ts`; it never calls an application Route Handler. It maps generated API
  types to a smaller allowlisted view model before rendering.
- A `BFF route` is an explicit Next.js Route Handler under `app/api/`. It validates browser input,
  applies the profile in section 2, calls one named operation, and maps only its safe response.
  It does not decide roles, report transitions, verification, citation validity, or publication.
- The BFF creates/replaces `X-Request-Id`, forwards `X-Shaidago-Locale` and
  `X-Shaidago-Client-Hmac`, and adds the internal service credential itself. It forwards only the
  headers named by the profile; browser `Cookie`,
  `Authorization`, `X-Forwarded-*`, `Host`, `Content-Length`, and arbitrary `X-*` headers never
  cross the boundary.
- `Origin` means an exact trusted same-origin match after trusted-proxy host normalisation. A
  missing/invalid/multiple Origin fails a browser mutation safely. CSRF is required only for an
  authenticated reviewer mutation and is checked before reading/forwarding its body.
- All browser-facing errors are a localised safe `application/problem+json` shape containing the
  stable code and safe request ID. Never echo backend detail, invalid fields' values, a secret,
  storage URL, or an internal hostname.

## 2. Transport profiles

| Profile | Browser input and cap | Safe forwarding / session | Origin and CSRF | Timeout | Success and error mapping | Cache and log redaction |
| --- | --- | --- | --- | --- | --- | --- |
| `SR-PUBLIC` | Server-only `GET`; typed query is parsed from route/search params; `q` ≤ 100 characters and opaque cursor ≤ 512 characters. | Add internal bearer, safe request ID, locale, client HMAC; pass `If-None-Match` only for public reads. | Not a browser mutation. | Connect 1 s, total 5 s. | Allowlisted public DTO; `304` retains the current body; safe problem result for route boundary. | API public success policy only; errors no-store. Do not log query text beyond bounded metrics. |
| `SR-REVIEWER` | Server-only `GET`; typed route/query values only. | Add internal bearer, safe request ID, locale, client HMAC, and server-extracted reviewer session; never expose the session. | No CSRF for reads; capability remains backend-owned. | Connect 1 s, total 5 s. | Allowlisted private view model; `401` clears local session and routes safely to sign-in; `403/404` reveal no extra resource detail. | Always `no-store`; no Next data cache/prefetch. Redact IDs/body/headers. |
| `BFF-PUBLIC-JSON` | `POST application/json`, schema-specific body cap in ledger. | Add internal bearer, safe request ID, locale, client HMAC; no browser cookie forwarding. | Exact Origin required; no CSRF because no authenticated cookie is used. | Connect 1 s, total 8 s. | Allowlisted generated/view response; map problem by code; preserve mutation completion uncertainty. | `Cache-Control: no-store`; never log body, credentials, question, answer, or report text. |
| `BFF-PUBLIC-GET` | `GET`; opaque route/query values only; no body. | Add internal bearer, safe request ID, locale, client HMAC; no browser cookie forwarding. | Not a mutation; no CSRF. | Connect 1 s, total 3 s while polling. | Allowlisted public run projection or `304` only; map safe problem by code. | `Cache-Control: no-store`; no persistent public-discovery cache or run-ID logging. |
| `BFF-PUBLIC-IDEMPOTENT` | `POST application/json`, schema-specific cap and validated `Idempotency-Key`. | Same as `BFF-PUBLIC-JSON`; key is validated/generated only for one user intent. | Exact Origin required; no CSRF. | Connect 1 s, total 8 s. | Preserve replay/conflict semantics; never create a fresh key during a retry of the same intent. | `no-store`; redact key and body. |
| `BFF-PUBLIC-IDEMPOTENT-EMPTY` | `POST` with an empty body and validated `Idempotency-Key`. | Same as `BFF-PUBLIC-JSON`; key is validated/generated only for one user intent. | Exact Origin required; no CSRF. | Connect 1 s, total 8 s. | Preserve replay/conflict semantics; never create a fresh key during a retry of the same intent. | `no-store`; redact key and headers. |
| `BFF-REPORT-MULTIPART` | `POST multipart/form-data`; stream ≤ 30 MiB + 64 KiB fields; up to 3 permitted files, each ≤ 10 MiB. | Add internal bearer, safe request ID, locale, client HMAC, and validated idempotency key; do not buffer full files. | Exact Origin required; no CSRF. | Connect 2 s, total 65 s, abort propagates. | Allowlisted receipt only; one-time tracking code is returned once in no-store response; preserve per-file outcomes. | `no-store`; redact every form field, file name/bytes, key, receipt secret, and headers. |
| `BFF-REVIEWER-JSON` | `POST application/json`, schema-specific cap in ledger. | Add internal bearer, safe request ID, locale, client HMAC, and session extracted from the HttpOnly cookie. | Exact Origin plus CSRF required before body forwarding. | Connect 1 s, total 10 s. | Allowlisted result; `401` clears local cookie, `403` remains non-disclosing, `409` preserves conflict recovery. | `no-store`; no private body, cookie, CSRF, report ID, or reviewer identifier in logs. |
| `BFF-REVIEWER-EMPTY` | `POST` with an empty body. | Add internal bearer, safe request ID, locale, client HMAC, and session extracted from the HttpOnly cookie. | Exact Origin plus CSRF required before forwarding. | Connect 1 s, total 10 s. | Allowlisted empty/state result; `401` clears local cookie, `403` remains non-disclosing, `409` preserves conflict recovery. | `no-store`; no cookie, CSRF, report ID, or reviewer identifier in logs. |
| `BFF-REVIEWER-GET` | `GET`; typed opaque route/query values only. | Same server-extracted reviewer session forwarding. | No CSRF for read; backend capability decides access. | Connect 1 s, total 5 s; active discovery polling uses total 3 s. | Allowlisted DTO or safe `304` polling result; no raw private body in an error. | `no-store`; no prefetch/persistent cache. |
| `BFF-EVIDENCE-STREAM` | `GET`; opaque report/evidence IDs from a reviewer route. | Same server-extracted reviewer session forwarding. | No CSRF for read; backend capability decides access. | Connect 1 s; stream abort propagates, maximum 30 s. | Stream only a successful attachment with backend `Content-Disposition`, `Content-Type`, `X-Content-Type-Options`, CSP, scan-state, and no-store headers; map all failure bodies safely. | `no-store`; no signed URL, object key, file name, or bytes in logs/traces. |
| `BFF-AUTH` | `POST application/json` ≤ 2 KiB or `DELETE` empty body. | Sign-in adds internal bearer/client HMAC; later sign-out extracts server cookie session. BFF alone translates the one-time API session response into/clears the HttpOnly same-origin cookie. | Exact Origin on both methods; sign-in has no CSRF, sign-out requires CSRF because it uses the reviewer cookie. | Connect 1 s, total 8 s. | Sign-in strips token/CSRF/cookie-policy fields before browser response; sign-out always clears local cookie. | `no-store`; redact identifier, password, token, CSRF, and cookie headers. |

`BFF-PUBLIC-JSON`, `BFF-PUBLIC-IDEMPOTENT`, `BFF-REVIEWER-JSON`, and `BFF-AUTH` accept
only `application/json`; all other content types receive a safe `415`. Every profile rejects an
oversized declared or streamed body before forwarding and maps backend timeouts/cancellation to a
safe retry-aware problem.

## 3. Operation ledger

| Operation ID | Browser action / transport owner | Exact Next.js owner or server call | Input and cap | Profile | Response allowlist and cache |
| --- | --- | --- | --- | --- | --- |
| `projects_list_localities` | Initial landing/directory locality choices; Server read. | `src/lib/api/server.ts#getLocalities` from landing/directory Server Components. | Typed `GET`; no body. | `SR-PUBLIC` | Locality slug/name/kind/parent/enabled locales only; public `ETag` policy. |
| `projects_list` | Initial landing preview/directory results and filter/cursor navigation; Server read. | `src/lib/api/server.ts#listProjects` from landing/directory Server Components. | Typed allowlisted filters; no body. | `SR-PUBLIC` | Project summary page/opaque next cursor only; public `ETag` policy. |
| `projects_get` | Initial project detail/report context; Server read. | `src/lib/api/server.ts#getProject` from project/detail report-context Server Components. | Opaque slug; no body. | `SR-PUBLIC` | Public project detail/citations only; public `ETag` policy. |
| `projects_get_source` | Initial approved source view; Server read. | `src/lib/api/server.ts#getProjectSource` from source Server Component. | Opaque project/source IDs; no body. | `SR-PUBLIC` | Approved source metadata/passages only; public `ETag` policy. |
| `projects_ask_question` | Submit in-page question. | `POST app/api/public/questions/route.ts`. | JSON ≤ 4 KiB; generated question input only. | `BFF-PUBLIC-JSON` | Grounded answer, supplied sources, retrieval mode, and safe problem only; no-store. |
| `discovery_start_public_run` | Start/reuse public discovery from a project panel. | `POST app/api/public/discovery/route.ts`. | JSON ≤ 2 KiB; opaque slug only. | `BFF-PUBLIC-JSON` | Run action/ID/status/demo flag only; no-store. |
| `discovery_get_public_run` | Poll a public discovery panel. | `GET app/api/public/discovery/[runId]/route.ts`. | Opaque run ID and optional version only; no body. | `BFF-PUBLIC-GET` | Public run projection, `304`, and safe problem only; no-store despite public project context. |
| `reports_submit` | Submit a private anonymous/optional-contact report. | `POST app/api/reports/route.ts`. | Multipart stream ≤ 30 MiB + 64 KiB; validated idempotency key. | `BFF-REPORT-MULTIPART` | One-time receipt and attachment outcomes only; no-store. |
| `report_status_lookup` | Look up a status with a body-only code. | `POST app/api/tracking/lookup/route.ts`. | JSON ≤ 2 KiB; code never enters URL. | `BFF-PUBLIC-JSON` | Safe status/message/next action/follow-ups only; no-store and generic credential failure. |
| `report_status_answer_follow_up` | Answer/skip/flag an approved follow-up. | `POST app/api/tracking/follow-up/route.ts`. | JSON ≤ 8 KiB; validated idempotency key and one body credential form. | `BFF-PUBLIC-IDEMPOTENT` | Allowlisted acknowledgement/safe problem only; no-store and generic credential failure. |
| `reporter_handles_create` | Create optional handle credentials. | `POST app/api/reporter-handle/route.ts`. | Empty body; validated idempotency key. | `BFF-PUBLIC-IDEMPOTENT-EMPTY` | One-time handle/passphrase response only; no-store, never persist. |
| `reporter_handles_list_reports` | List safe statuses through supplied handle credentials. | `POST app/api/reporter-handle/reports/route.ts`. | JSON ≤ 2 KiB; credentials only in body. | `BFF-PUBLIC-JSON` | Safe report-status list only; no-store and generic credential failure. |
| `reporter_handles_delete` | Unlink handle from reports. | `POST app/api/reporter-handle/delete/route.ts`. | JSON ≤ 2 KiB; credentials only in body. | `BFF-PUBLIC-JSON` | Empty/safe acknowledgement only; no-store and generic credential failure. |
| `auth_sign_in` | Reviewer signs in. | `POST app/api/reviewer/session/route.ts`. | JSON ≤ 2 KiB; identifier/password. | `BFF-AUTH` | Reviewer-safe session result plus HttpOnly cookie only; no-store. |
| `auth_sign_out` | Reviewer signs out. | `DELETE app/api/reviewer/session/route.ts`. | Empty body. | `BFF-AUTH` | Empty result; clear cookie even if backend session is gone; no-store. |
| `reviewer_reports_queue` | Initial reviewer queue/filter/cursor render; Server read. | `src/lib/api/server.ts#listReviewerReports` from reviewer queue Server Component. | Typed allowlisted filters/cursor; no body. | `SR-REVIEWER` | Triage projection/opaque cursor only; no-store. |
| `reviewer_reports_get` | Initial reviewer report render; Server read. | `src/lib/api/server.ts#getReviewerReport` from reviewer detail Server Component. | Opaque report ID and explicit contact-read option only; no body. | `SR-REVIEWER` | Allowlisted private report projection; no-store. |
| `reviewer_notes_list` | Initial/refreshed reviewer notes; Server read. | `src/lib/api/server.ts#listReviewerNotes` from reviewer detail Server Component. | Opaque report ID/cursor; no body. | `SR-REVIEWER` | Notes page only; no-store. |
| `reviewer_notes_create` | Append reviewer note. | `POST app/api/reviewer/reports/[reportId]/notes/route.ts`. | JSON ≤ 8 KiB; body field only. | `BFF-REVIEWER-JSON` | New note ID/time only; no-store. |
| `reviewer_evidence_download` | Download one sanitised evidence artifact. | `GET app/api/reviewer/reports/[reportId]/evidence/[evidenceId]/route.ts`. | Opaque IDs; no body. | `BFF-EVIDENCE-STREAM` | Attachment stream/security headers only; no-store. |
| `reviewer_decisions_ask_follow_up` | Add a reviewer follow-up question. | `POST app/api/reviewer/reports/[reportId]/follow-up-questions/route.ts`. | JSON ≤ 2 KiB; question only. | `BFF-REVIEWER-JSON` | New question ID only; no-store. |
| `reviewer_decisions_withdraw_follow_up` | Withdraw one follow-up question. | `POST app/api/reviewer/reports/[reportId]/follow-up-questions/[questionId]/withdraw/route.ts`. | Empty body; no arbitrary command body. | `BFF-REVIEWER-EMPTY` | Empty/safe acknowledgement only; no-store. |
| `reviewer_decisions_transition` | Request a report state transition. | `POST app/api/reviewer/reports/[reportId]/status-transition/route.ts`. | JSON ≤ 4 KiB; command/current status/version/reason/message schema. | `BFF-REVIEWER-JSON` | New status/version/reviewer-safe message/published false only; no-store. |
| `reviewer_publication_list` | Initial publication draft list; Server read. | `src/lib/api/server.ts#listPublicationDrafts` from reviewer detail Server Component. | Opaque report ID; no body. | `SR-REVIEWER` | Draft summaries only; no-store. |
| `reviewer_publication_create_draft` | Create a private public-update preview draft. | `POST app/api/reviewer/reports/[reportId]/public-updates/route.ts`. | JSON ≤ 16 KiB; statement/dates/state/1–5 citations. | `BFF-REVIEWER-JSON` | Draft/preview allowlist only; no-store. |
| `reviewer_publication_preview` | Fetch a selected draft preview. | `GET app/api/reviewer/reports/[reportId]/public-updates/[updateId]/route.ts`. | Opaque IDs; no body. | `BFF-REVIEWER-GET` | Preview/issues/digest/current report version only; no-store. |
| `reviewer_publication_publish` | Confirm the exact preview digest. | `POST app/api/reviewer/reports/[reportId]/public-updates/[updateId]/publish/route.ts`. | JSON ≤ 2 KiB; preview digest only. | `BFF-REVIEWER-JSON` | Published public update projection only; no-store. |
| `reviewer_publication_withdraw` | Withdraw a draft update. | `POST app/api/reviewer/reports/[reportId]/public-updates/[updateId]/withdraw/route.ts`. | JSON ≤ 1 KiB; no arbitrary command body. | `BFF-REVIEWER-JSON` | Empty/safe acknowledgement only; no-store. |
| `reviewer_discovery_plan` | Create an exact reviewer discovery plan. | `POST app/api/reviewer/reports/[reportId]/discovery/plan/route.ts`. | JSON ≤ 4 KiB; bounded concepts only. | `BFF-REVIEWER-JSON` | Query/exclusions/digest only; no-store. |
| `reviewer_discovery_create` | Start a report-scoped discovery run from the approved digest. | `POST app/api/reviewer/reports/[reportId]/discovery/route.ts`. | JSON ≤ 8 KiB; concepts/approved digest only. | `BFF-REVIEWER-JSON` | Run ID/status only; no-store. |
| `reviewer_discovery_get` | Poll a report-scoped discovery run. | `GET app/api/reviewer/discovery/[runId]/route.ts`. | Opaque run ID/optional version; no body. | `BFF-REVIEWER-GET` | Report-scoped run projection or `304` only; no-store. |
| `reviewer_discovery_cancel` | Cancel a report-scoped discovery run. | `POST app/api/reviewer/discovery/[runId]/cancel/route.ts`. | Empty body; no arbitrary command body. | `BFF-REVIEWER-EMPTY` | Cancel state only; no-store. |
| `reviewer_discovery_review` | Approve completion or reject a run. | `POST app/api/reviewer/discovery/[runId]/review/route.ts`. | JSON ≤ 2 KiB; enum decision/reason schema. | `BFF-REVIEWER-JSON` | Updated run state only; no-store. |
| `reviewer_discovery_answer_follow_up` | Answer/skip/flag a discovery follow-up. | `POST app/api/reviewer/discovery/[runId]/follow-up-answers/route.ts`. | JSON ≤ 4 KiB; question ID/kind/conditional answer. | `BFF-REVIEWER-JSON` | Safe acknowledgement only; no-store. |
| `reviewer_discovery_decide_source` | Attach/reject/defer/reconsider a discovered source. | `POST app/api/reviewer/discovered-sources/[sourceId]/decision/route.ts`. | JSON ≤ 4 KiB; enum decision/reason only. | `BFF-REVIEWER-JSON` | Pending-source/decision projection only; no-store; never an approved fact. |

## 4. Deliberate exclusions

The following are forbidden even if they would reduce apparent frontend code:

- `app/api/proxy/[...path]`, an arbitrary URL/method/header/cookie forwarder, or a generic
  REST-client Route Handler;
- any browser import of `src/lib/api/server.ts`, server environment/config, generated service
  credential, storage adapter, private FastAPI hostname, or provider adapter;
- a BFF decision based on reviewer role, report state, citation count, source ranking, AI output,
  or whether a public update should publish;
- private response caching in Next.js, a CDN, service worker, persistent query cache,
  IndexedDB/local/session storage, browser history, screenshots, traces, analytics, or logs; and
- a signed-evidence URL or object key reaching a browser response. Evidence stays a BFF-brokered
  attachment stream.

## 5. FE-004 evidence checklist

- [x] Every 35 non-health OpenAPI operation has one named server-read or purpose-built BFF owner.
- [x] Every BFF operation has an exact method/path, accepted input type, bounded body, safe header/session rule, guard, timeout, response allowlist, cache rule, and redaction rule through its profile and ledger row.
- [x] Public and reviewer reads/mutations have distinct cache, cookie, CSRF, timeout, and failure behavior.
- [x] One-time credentials, tracking, uploads, reviewer data, and evidence streams have no-store and explicit redaction rules.
- [x] No generic proxy, arbitrary forwarding, client-side internal URL, or BFF domain-authority path exists in the design.

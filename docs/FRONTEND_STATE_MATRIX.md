# Frontend state and fixture matrix

- **Task:** FE-002 — Complete state matrices
- **Baseline:** 20 September 2026
- **Transport fixtures:** [`contracts/frontend-fixtures.json`](../contracts/frontend-fixtures.json), schema `1`
- **Route ownership:** [`FRONTEND_ROUTE_MATRIX.md`](FRONTEND_ROUTE_MATRIX.md)

This document names the UI fixtures that component, accessibility, and end-to-end tests must share. Transport fixtures prove an HTTP shape; UI fixtures combine one transport response with connectivity, cache, browser, locale, and interaction context. No fixture name may be repurposed after tests consume it.

## 1. Fixture naming and invariants

The stable format is `ui.<surface>.<state>[.<variant>]`. Use lowercase dot-separated identifiers. In a table cell, a leading full name establishes the surface prefix and each following shorthand such as `.empty` expands to that same prefix (`ui.<surface>.empty`). A test may add implementation details inside a fixture file, but its stable name and user-visible meaning remain fixed.

Backend transport scenarios remain `success`, `empty`, `stale`, `partial`, `denied`, `rate_limited`, `dependency_down`, and `validation`. UI fixtures reference them; they do not edit generated backend fixtures.

Every async state follows these rules:

- state changes are announced only when useful, through a correctly scoped live region; routine initial content is not announced twice;
- focus moves on route/step changes and destructive confirmations, not on background revalidation;
- the current usable content remains visible during safe public revalidation;
- errors say what happened safely, whether work is preserved, and the next action;
- retries are bounded, focusable, disabled while pending, and reuse the same idempotency key for the same mutation intent;
- `401`, `403`, `404`, `409`, `413`, `415`, and `422` are not retried unchanged;
- `429` uses only the server's `Retry-After`; `503` may use bounded retry where the operation is safe/idempotent;
- a safe request ID may be shown for support, but no body, credential, internal hostname, provider detail, or private identifier is echoed;
- status is text plus structure/icon where useful, never colour alone; and
- private/no-store content never falls back to a service-worker, Next.js, CDN, IndexedDB, local/session storage, or persisted query cache.

## 2. Shared state vocabulary

| State | Trigger | Required UI behavior | Recovery and cache rule |
| --- | --- | --- | --- |
| `initial` | Surface has not started its first request or user intent. | Show instructions and primary action, not a spinner pretending work began. | No request/cache mutation. |
| `loading` | First request is pending with no usable data. | Preserve layout landmarks; use labelled busy/skeleton treatment matching final geometry. | One request; no duplicate action. |
| `revalidating` | Safe public data exists and conditional refresh is pending. | Keep content readable, mark refresh non-disruptively, do not reset focus/scroll. | Send ETag; `304` retains body. |
| `empty` | Successful collection has zero records. | Explain what is empty and provide the next relevant action. | Not an error; do not auto-retry. |
| `no_matches` | Filters/search produce zero records while records may exist. | Preserve/removable filters and offer clear/reset; do not call the registry empty. | URL remains source of truth. |
| `success_minimum` | Smallest valid response/content. | No placeholder chrome or invented missing values. | Respect endpoint cache policy. |
| `success_typical` | Representative synthetic or eligible public content. | Default component/E2E fixture. | Respect endpoint cache policy. |
| `success_maximum` | Contract limits and longest planned content. | Paginate/collapse intentionally; no truncation that hides safety/evidence meaning. | No unbounded DOM/request. |
| `stale` | Cached/public data is usable but older than freshness target. | Show saved/checked time and stale label while keeping citations accessible. | Allow public revalidation only. |
| `source_unavailable` | Source availability is restricted/temporary/permanent failure. | Preserve historical citation metadata and availability wording; do not erase verification automatically. | Offer original link only when safe/useful; no retry storm. |
| `partial` | Some fields/files/results succeed and others do not. | Identify each retained/omitted item and preserve the successful outcome. | Retry only the failed retriable sub-action; never duplicate parent mutation. |
| `partial_translation` | Requested locale has only some reviewed content. | Label source-language or English fallback per field; keep original connected. | Never silently claim translation. |
| `machine_assisted_translation` | Visible translation is not fluent-human reviewed. | Show honest machine-assisted label without suggesting factual verification. | Locale remains selected; source stays reachable. |
| `field_validation` | Client usability validation fails. | Associate concise fix text with fields; focus first invalid field after submit. | Preserve all safe input. Backend still validates. |
| `server_validation` | `422` problem fields return. | Map stable field paths/codes, use summary plus field errors, never echo unsafe submitted values from detail. | Preserve safe input; user changes request before retry. |
| `unauthenticated` | Reviewer request returns `401`. | Remove private content immediately and route to sign-in with safe return target. | Clear unusable cookie; no cached private fallback. |
| `forbidden` | Authenticated action returns `403`. | State lack of permission without exposing resource detail; keep safe navigation. | Do not retry unchanged or reveal hidden action data. |
| `session_expired` | Session expires during a private workflow. | Obscure/remove private content, explain sign-in is required, and avoid persisting draft private data. | Sign in again; refetch from authority. |
| `csrf_rejected` | Reviewer mutation is rejected by CSRF policy. | Explain session/request safety failure and preserve no secret token in UI. | Refresh session/page; do not retry same invalid token automatically. |
| `origin_rejected` | BFF rejects cross-origin mutation. | Safe generic request rejection; no internal policy detail. | User returns through same-origin app; no automatic retry. |
| `rate_limited` | `429` with retry information. | Show exact wait in accessible text; disable only affected action; no parallel timer. | Re-enable from `Retry-After`; retain safe work. |
| `backend_unavailable` | API/network dependency is unavailable. | Distinguish public read, unsent private work, and unknown mutation completion. | Bounded retry; never claim completion. |
| `provider_unavailable` | AI/search provider fails while core API remains healthy. | Keep project/report core usable and name only the affected optional feature. | Retry optional feature; do not take down browsing/reporting. |
| `timeout` | Bounded request expires. | State timeout and whether completion is unknown. | Safe read retries; mutation reuses idempotency key or refetches. |
| `cancelled` | User/authorised actor stops a discovery run. | Preserve already retrieved reviewable results and show no future fetches. | No automatic restart; explicit new intent only. |
| `dead_letter` | Discovery job exhausts retries and requires review. | Reviewer-visible failed/exhausted state with safe next action; no invented percentage. | Explicit retry/new run according to backend command availability. |
| `offline_public_cached` | Browser is offline with an allowlisted cached public response. | Show saved time/offline label; links/actions needing network explain limitation. | Revalidate after reconnect; public content only. |
| `offline_public_uncached` | Browser is offline without a cached public response. | Render offline page/shell and safe navigation to cached items. | Retry on reconnect/user action. |
| `offline_private_unavailable` | Private route/action loses connectivity. | Do not reveal a cached response; explain current private data cannot be loaded/sent. | Preserve only policy-approved in-memory/draft fields; retry safely. |
| `retry_success` | A bounded retry succeeds. | Replace error with result, restore focus to meaningful heading/status, announce success once. | Do not append duplicate data or duplicate history. |
| `idempotency_replay` | Same intent/body replays prior successful mutation. | Present the original success normally; optional non-alarming recovery note. | Never resubmit with a fresh key merely to get new output. |
| `idempotency_conflict` | Same key is reused with changed body. | Explain the prior attempt cannot be reused; preserve work and require an explicit new intent. | Refetch authoritative state before new key. |
| `conflict` | Version/state changed concurrently (`409`). | Explain data changed, preserve unsaved safe text separately, and refetch. | Do not overwrite or retry stale transition unchanged. |
| `javascript_disabled` | Client JavaScript is unavailable. | Public purpose/directory/detail/source/trust remain useful; interactive-only features explain requirements safely. | Native HTML navigation/form where contract permits; no false success. |

## 3. Public-read surfaces

| Surface | Stable UI fixtures | Surface-specific behavior |
| --- | --- | --- |
| Landing/localities | `ui.landing.loading`, `.empty`, `.success_minimum`, `.success_typical`, `.stale`, `.backend_unavailable`, `.offline_public_cached`, `.offline_public_uncached`, `.javascript_disabled` | Product purpose/trust content remains readable if project preview fails; locality choices are not invented. |
| Project directory | `ui.project_directory.loading`, `.revalidating`, `.empty`, `.no_matches`, `.success_minimum`, `.success_typical`, `.success_maximum`, `.stale`, `.partial_translation`, `.machine_assisted_translation`, `.field_validation`, `.backend_unavailable`, `.timeout`, `.offline_public_cached`, `.offline_public_uncached`, `.retry_success`, `.javascript_disabled` | Preserve URL filters and prior safe results during revalidation; invalid cursor is a safe recoverable filter/page error, not an empty registry. |
| Project detail | `ui.project_detail.loading`, `.revalidating`, `.success_minimum`, `.success_typical`, `.success_maximum`, `.stale`, `.source_unavailable`, `.partial`, `.partial_translation`, `.machine_assisted_translation`, `.backend_unavailable`, `.offline_public_cached`, `.offline_public_uncached`, `.retry_success`, `.javascript_disabled` | Facts never render without returned citations; unknown/disputed/outdated are distinct; missing optional values are neutral unknowns. |
| Source view | `ui.source_view.loading`, `.success_minimum`, `.success_typical`, `.stale`, `.source_unavailable`, `.partial_translation`, `.machine_assisted_translation`, `.backend_unavailable`, `.offline_public_cached`, `.offline_public_uncached`, `.javascript_disabled` | Approved metadata/passage stays distinct from external-page availability; hidden/unknown uses safe not-found route state. |

## 4. Grounded Q&A

| Fixture | Required behavior |
| --- | --- |
| `ui.project_qa.initial` | Question guidance, evidence scope, privacy caution, and bounded input are visible; no request yet. |
| `ui.project_qa.loading` | Disable duplicate submit, retain question in current memory, announce generation without fake progress. |
| `ui.project_qa.success_typical` | Render answer as text, generated time, retrieval mode, and statement-linked citations that resolve within response sources. |
| `ui.project_qa.partial_translation` / `.machine_assisted_translation` | Preserve source titles, amounts, dates, names, and citations; label language status honestly. |
| `ui.project_qa.server_validation` | Map stable code/path; retain bounded question; no unsafe echo from server detail. |
| `ui.project_qa.rate_limited` | Use only `Retry-After`; project page remains usable. |
| `ui.project_qa.provider_unavailable` / `.timeout` / `.backend_unavailable` | Distinguish optional provider outage from API outage; no fabricated answer. |
| `ui.project_qa.offline_private_unavailable` | No persisted question/answer cache; current rendered answer may remain only in memory. |
| `ui.project_qa.retry_success` | Replace failure with citation-valid result exactly once. |
| `ui.project_qa.insufficient_evidence` | Render backend wording and useful approved source links; never add an inferred answer. |
| `ui.project_qa.citation_rejected` | Fail closed if client mapping finds an unknown citation; show safe error/request ID, never uncited statements. |

## 5. Reporting and one-time confirmation

| Surface | Stable UI fixtures | Surface-specific behavior |
| --- | --- | --- |
| Report project context | `ui.report_context.loading`, `.success_minimum`, `.stale`, `.backend_unavailable`, `.offline_private_unavailable`, `.javascript_disabled` | Public context is minimal; report flow never depends on stale private data. |
| Report steps | `ui.report_wizard.initial`, `.success_minimum`, `.success_typical`, `.success_maximum`, `.field_validation`, `.partial_translation`, `.machine_assisted_translation`, `.offline_private_unavailable`, `.javascript_disabled` | Anonymous is default; contact/handle fields appear only by explicit choice; step changes restore focus; safe draft policy is explained before persistence. |
| Image preparation | `ui.report_evidence.loading`, `.success_minimum`, `.success_maximum`, `.partial`, `.field_validation`, `.timeout`, `.offline_private_unavailable` | Show each local file outcome; browser re-encoding is minimisation, not security proof; attachments never enter draft storage. |
| Submission | `ui.report_submission.loading`, `.partial`, `.server_validation`, `.rate_limited`, `.backend_unavailable`, `.timeout`, `.offline_private_unavailable`, `.retry_success`, `.idempotency_replay`, `.idempotency_conflict` | Unknown completion preserves same intent/key; `201` with rejected files still proceeds to receipt; `413` means no report accepted. |
| Completion | `ui.report_completion.success_typical`, `.partial`, `.copy_failed`, `.direct_entry`, `.javascript_disabled` | Code shown once; per-file outcomes remain; direct/refresh/back entry states say recovery is impossible and never invoke lookup. |

## 6. Tracking and reporter handles

| Surface | Stable UI fixtures | Surface-specific behavior |
| --- | --- | --- |
| Tracking lookup | `ui.tracking.initial`, `.loading`, `.success_minimum`, `.success_typical`, `.server_validation`, `.credential_rejected`, `.rate_limited`, `.backend_unavailable`, `.timeout`, `.offline_private_unavailable`, `.retry_success` | Not-found/inaccessible/wrong credential uses one generic shape; only safe status/message/action returns; secret remains input memory only. |
| Tracking follow-up | `ui.tracking_follow_up.initial`, `.loading`, `.field_validation`, `.server_validation`, `.success_typical`, `.rate_limited`, `.timeout`, `.idempotency_replay`, `.idempotency_conflict`, `.offline_private_unavailable` | Approved question only; answer is private; same-intent retry cannot append twice. |
| Handle creation | `ui.handle_create.initial`, `.loading`, `.success_typical`, `.copy_failed`, `.rate_limited`, `.backend_unavailable`, `.timeout`, `.idempotency_replay`, `.direct_entry` | Show handle/passphrase once with no recovery; literal synthetic test credential is never treated as usable. |
| Handle list | `ui.handle_list.initial`, `.loading`, `.empty`, `.success_minimum`, `.success_typical`, `.success_maximum`, `.credential_rejected`, `.rate_limited`, `.offline_private_unavailable` | Reports sharing a handle are not proof of different people; display only safe projections. |
| Handle deletion | `ui.handle_delete.initial`, `.loading`, `.success_typical`, `.credential_rejected`, `.rate_limited`, `.backend_unavailable`, `.timeout`, `.offline_private_unavailable` | Confirm unlink semantics: reports remain anonymous; completion clears credential fields. |

## 7. Reviewer surfaces and mutations

| Surface | Stable UI fixtures | Surface-specific behavior |
| --- | --- | --- |
| Reviewer sign-in | `ui.reviewer_sign_in.initial`, `.loading`, `.field_validation`, `.credential_rejected`, `.rate_limited`, `.backend_unavailable`, `.timeout`, `.retry_success` | Generic credential error; safe return allowlist; browser never receives API session/CSRF values. |
| Reviewer queue | `ui.reviewer_queue.loading`, `.empty`, `.no_matches`, `.success_minimum`, `.success_typical`, `.success_maximum`, `.unauthenticated`, `.forbidden`, `.session_expired`, `.rate_limited`, `.backend_unavailable`, `.offline_private_unavailable`, `.retry_success` | Minimum triage data only; opaque cursors; session loss removes rows immediately. |
| Reviewer report detail | `ui.reviewer_report.loading`, `.success_minimum`, `.success_typical`, `.success_maximum`, `.partial`, `.unauthenticated`, `.forbidden`, `.session_expired`, `.backend_unavailable`, `.offline_private_unavailable`, `.retry_success` | Information groups remain distinct; private content never survives route exit/cache; missing evidence is not interpreted. |
| Evidence download | `ui.evidence_download.loading`, `.success_typical`, `.source_unavailable`, `.forbidden`, `.session_expired`, `.backend_unavailable`, `.timeout` | Download as attachment; short-lived target never logged/persisted; `not_scanned_demo` is explicit to reviewer. |
| Note/follow-up mutation | `ui.reviewer_note.initial`, `.loading`, `.field_validation`, `.server_validation`, `.success_typical`, `.unauthenticated`, `.forbidden`, `.csrf_rejected`, `.origin_rejected`, `.rate_limited`, `.backend_unavailable`, `.timeout`, `.conflict`, `.retry_success` | Preserve unsent note only in current memory; successful history appends once; refetch on conflict. |
| Status transition | `ui.report_transition.initial`, `.loading`, `.success_typical`, `.forbidden`, `.csrf_rejected`, `.origin_rejected`, `.conflict`, `.rate_limited`, `.backend_unavailable`, `.timeout`, `.retry_success` | Confirm command and safe tracking message; backend decides allowed edge; resulting append-only event is shown. |
| Public update | `ui.public_update.empty`, `.success_minimum`, `.success_typical`, `.success_maximum`, `.field_validation`, `.server_validation`, `.forbidden`, `.csrf_rejected`, `.origin_rejected`, `.conflict`, `.backend_unavailable`, `.timeout`, `.retry_success`, `.preview_mismatch` | Draft is private/public-after-review; exact preview required; publish result must equal preview or fail closed/refetch. |

## 8. Source Scout

| Surface | Stable UI fixtures | Surface-specific behavior |
| --- | --- | --- |
| Public discovery | `ui.public_discovery.initial`, `.loading`, `.queued`, `.searching`, `.analysing`, `.needs_review`, `.success_minimum`, `.success_typical`, `.success_maximum`, `.partial`, `.rate_limited`, `.provider_unavailable`, `.backend_unavailable`, `.timeout`, `.cancelled`, `.dead_letter`, `.offline_public_uncached`, `.retry_success` | Poll 2/3/5/8/≤10 seconds, pause hidden/offline, resume same run, stop terminal; never invent percentages; every result remains discovered/not reviewed. |
| Safe-query plan | `ui.discovery_plan.initial`, `.loading`, `.success_typical`, `.server_validation`, `.forbidden`, `.session_expired`, `.csrf_rejected`, `.origin_rejected`, `.conflict`, `.backend_unavailable`, `.offline_private_unavailable` | Exact terms and excluded private categories visible before approval; stale plan/version cannot run. |
| Reviewer discovery | `ui.reviewer_discovery.loading`, `.queued`, `.searching`, `.analysing`, `.needs_review`, `.success_minimum`, `.success_typical`, `.success_maximum`, `.partial`, `.unauthenticated`, `.forbidden`, `.session_expired`, `.provider_unavailable`, `.backend_unavailable`, `.timeout`, `.cancelled`, `.dead_letter`, `.offline_private_unavailable`, `.retry_success` | Private results disappear on session/offline loss; already retrieved results remain reviewable after cancel; no persistent cache. |
| Discovery analysis | `ui.discovery_analysis.success_minimum`, `.success_typical`, `.success_maximum`, `.partial`, `.citation_rejected`, `.provider_unavailable`, `.needs_review` | Separate supported facts/reported claims/contradictions/gaps/questions; citations resolve only within same run. |
| Discovery follow-up | `ui.discovery_follow_up.initial`, `.loading`, `.success_typical`, `.field_validation`, `.server_validation`, `.forbidden`, `.conflict`, `.rate_limited`, `.backend_unavailable`, `.timeout`, `.retry_success` | Maximum five safe questions; answer/skip/unsafe actions do not solicit identity unnecessarily. |
| Source decision | `ui.source_decision.initial`, `.loading`, `.success_typical`, `.forbidden`, `.csrf_rejected`, `.origin_rejected`, `.conflict`, `.backend_unavailable`, `.timeout`, `.retry_success` | Attach/reject/defer needs explicit human action/reason; attach creates pending source, not fact approval/publication. |

## 9. Fixture implementation contract

1. FE-021 creates the fixture loader and rejects an unknown stable UI fixture name.
2. FE-030/FE-035 bind each UI fixture to a documented generated transport response or explicit browser/network condition.
3. Locale tests substitute reviewed catalog copy while preserving synthetic names, amounts, dates, citations, and uncertainty.
4. Components test the lowest useful state set; route E2E tests compose the journey-critical states without duplicating all component cases.
5. Fixture files display `SYNTHETIC — DEMO/TEST ONLY` metadata and contain no real person, report, contact, credential, or allegation.
6. Private fixtures are never embedded in production client bundles except minimal schema-safe test builds explicitly excluded from release.

## 10. FE-002 exit gate

- [x] First load, revalidation, empty/no-match, min/typical/max success, stale, partial, validation, denial, rate limit, dependency, timeout, cancellation/dead-letter, offline, retry/idempotency, and no-JavaScript behavior are named.
- [x] Public cached-offline and private unavailable-offline behavior cannot be confused.
- [x] Q&A has insufficient-evidence and citation-rejection states distinct from provider failure.
- [x] Report submission preserves partial attachment success and unknown-completion idempotency semantics.
- [x] Reviewer session/CSRF/origin/forbidden/conflict states have different recovery paths.
- [x] Discovery uses real lifecycle states without invented percentages and preserves unreviewed labels.
- [x] Stable fixture naming is shared by component, accessibility, and E2E tests.

FE-002 reopens when a material HTTP status, domain state, offline/cache rule, retry semantic, locale status, or asynchronous surface changes.

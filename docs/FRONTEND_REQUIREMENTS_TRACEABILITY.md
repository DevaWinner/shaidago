# Frontend scope and authority traceability

- **Task:** FE-000 — Reconcile frontend scope and authority
- **Status:** implemented planning control; update when an accepted frontend requirement or backend handoff changes
- **Baseline:** 20 September 2026
- **Authoritative inputs:** [`PRODUCT.md`](../PRODUCT.md), [`PRODUCT_BRIEF.md`](PRODUCT_BRIEF.md), [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md), [`FRONTEND_BUILD_ORDER.md`](FRONTEND_BUILD_ORDER.md), [`FRONTEND_BACKEND_CONTRACT.md`](FRONTEND_BACKEND_CONTRACT.md), [`contracts/openapi.json`](../contracts/openapi.json)

This register assigns every accepted user-facing outcome to a frontend task, route or surface, backend operation, data class, render/cache rule, and proof. It prevents the browser or BFF from becoming a second domain authority and prevents a visible feature from depending on a database field that is absent from the OpenAPI handoff.

## 1. Task packet

| Field | FE-000 decision |
| --- | --- |
| User | Resident, reporter, repeat reporter, reviewer, journalist/civic user, and hackathon judge. |
| User outcome | Every later frontend task can identify its authoritative data, privacy boundary, owning route, backend operation, and required proof without inspecting backend implementation. |
| Dependencies | Backend Circle 12 handoff, OpenAPI `0.0.0`, frontend fixture schema `1`, controlled vocabulary schema `1`, product and implementation documents. |
| Route/surface | All public, report, tracking, handle, trust, reviewer, and embedded Source Scout surfaces. This task creates no UI. |
| States | Ownership for initial, loading, empty, success, stale, partial, validation, denied, rate-limited, offline, dependency-down, conflict, cancelled, and recovery states is assigned below; FE-002 defines their complete fixture matrix. |
| Data classification | `public`, `public_after_review`, `private`, `one_time_secret`, and `operational_only`; rules are in section 6. |
| Accessibility | Semantic status values and stable field-error paths come from the backend; frontend tasks own labels, focus, keyboard, announcements, contrast, zoom, and reduced motion. |
| Localisation | English is the source locale. `en`, `ha`, `ig`, and `yo` require key/ICU parity; machine-assisted or unavailable content stays visibly labelled. |
| Performance | Server-render public reads; isolate client interactions; keep private operations no-store; public first-load compressed JavaScript remains below 170 KB. |
| Verification | `python3 scripts/validate_frontend_traceability.py --self-test`, frontend contract drift check, Markdown-link check, and `git diff --check`. |
| Evidence | This register, the generated OpenAPI/fixture package, backend handoff contract, and validation output. |
| Handoff | FE-001 may build the detailed route/journey matrix; FE-002 may name state fixtures; FE-004 may map every browser action to a purpose-built BFF handler. No later task may infer fields from Python models or database tables. |

## 2. Authority boundary

| Concern | Frontend/BFF responsibility | FastAPI responsibility | Prohibited frontend interpretation |
| --- | --- | --- | --- |
| Public facts and project status | Render the returned value, evidence label, citation control, dates, uncertainty, and locale honestly. | Decide visibility, verification, citations, public status, and the allowlisted public projection. | Inferring completion, trust, or verification from wording, source availability, report count, or UI state. |
| Authentication and authorisation | BFF owns the secure browser cookie, Origin/CSRF guard, safe redirects, and browser-safe errors. UI hides unavailable actions for clarity. | Create/revoke sessions, validate CSRF/session, enforce role, capability, and object scope for every operation. | Treating a cookie, route, visible button, or client role value as permission. |
| Report submission | Explain privacy, validate for usability, stream the bounded request, preserve same-intent idempotency, and display attachment outcomes. | Validate again, encrypt, sanitise/scan files, issue tracking credentials, persist privately, rate-limit, and audit. | Claiming client image processing makes an upload safe or public. |
| Report/reviewer state | Render allowed commands returned or documented by contract, confirm intent, submit current version, refetch on conflict, and show history. | Enforce the canonical state machine, actor, version, transaction, audit event, and safe tracking projection. | Enabling or accepting a transition because the UI can draw it. |
| Public update | Provide a separate composer and exact preview/confirmation surface. | Enforce state, citations, private-field exclusion, human actor, and atomic publication/withdrawal. | Copying private report text into public copy automatically or publishing on status change. |
| Grounded Q&A | Collect a bounded question, render structured answer/citations, and show the exact insufficient-evidence state. | Scope retrieval to approved project sources, call the configured provider, validate every citation/statement, and fail closed. | Treating model output as a source, status decision, or truth score. |
| Source Scout | Show safe-query preview, real progress states, unreviewed labels, source decisions, and recovery controls. | Build/validate privacy-safe queries, fetch safely, isolate hostile content, validate analysis/citations, enforce scope, and require human source decisions. | Sending private fields directly, inventing progress percentages, or treating search rank/repetition as verification. |
| Caching/offline | Apply documented public caching, private no-store behavior, and explicit service-worker allowlist. | Return cache headers/ETags and safe public/private projections. | Persisting private responses, credentials, signed URLs, Q&A bodies, or report-scoped discovery. |
| Localisation | Route, format, and render all four locale catalogs; preserve names, amounts, dates, and source-language attribution. | Return stable machine values, locale/translation status, and localised content where the contract provides it. | Silently calling English fallback translated or marking machine output human-reviewed. |

## 3. Complete journey ownership

| ID | Journey and success condition | Routes/surfaces | Frontend owners | Backend operations | Proof |
| --- | --- | --- | --- | --- | --- |
| FJ-01 | A resident finds an AMAC/Bwari project, understands the promise/current evidence, and opens the supporting source. | `/{locale}`, `/{locale}/projects`, project detail, source view, trust page | FE-050, FE-060, FE-061, FE-062, FE-070, FE-071, FE-072, FE-073, FE-074 | `projects_list_localities`, `projects_list`, `projects_get`, `projects_get_source` | Server-rendered mobile/desktop E2E; every fact citation resolves; stale/unavailable/translation labels shown. |
| FJ-02 | A resident asks a project question and receives a citation-valid answer or explicit insufficient evidence. | Project detail Q&A island | FE-080, FE-081, FE-082, FE-083 | `projects_ask_question` | Supported, unsupported, cross-project, malformed, rate-limited, provider-down, offline, and citation-link tests. |
| FJ-03 | A reporter submits a fictional private concern without an account, sees per-file outcomes, receives a one-time code, and can check a public-safe status. | Report wizard, one-time completion, tracking, optional handle | FE-090, FE-091, FE-092, FE-093, FE-094, FE-095, FE-096, FE-100, FE-101, FE-102, FE-103, FE-104 | `reports_submit`, `report_status_lookup`, `report_status_answer_follow_up`, `reporter_handles_create`, `reporter_handles_list_reports`, `reporter_handles_delete` | No-account E2E; private-cache/storage inspection; idempotent retry; one-time-secret and generic-lookup tests. |
| FJ-04 | An authorised reviewer signs in, sees minimum case data, reviews evidence, records notes/status/follow-up, and publishes only a separate exact-preview update. | Reviewer sign-in, queue, report detail | FE-110, FE-111, FE-112, FE-113, FE-114, FE-115, FE-116 | `auth_sign_in`, `auth_sign_out`, `reviewer_reports_queue`, `reviewer_reports_get`, `reviewer_evidence_download`, `reviewer_notes_list`, `reviewer_notes_create`, `reviewer_decisions_ask_follow_up`, `reviewer_decisions_withdraw_follow_up`, `reviewer_decisions_transition`, `reviewer_publication_list`, `reviewer_publication_create_draft`, `reviewer_publication_preview`, `reviewer_publication_publish`, `reviewer_publication_withdraw` | Auth/session/CSRF/role tests; queue/detail snapshots; evidence download audit; preview-equals-public E2E; no private public fields. |
| FJ-05 | Public and report-scoped Source Scout runs expose provenance, contradictions/gaps, citations, safe questions, and human source decisions without leaking a report. | Embedded project and reviewer detail panels | FE-120, FE-121, FE-122, FE-123, FE-124, FE-125, FE-126 | `discovery_start_public_run`, `discovery_get_public_run`, `reviewer_discovery_plan`, `reviewer_discovery_create`, `reviewer_discovery_get`, `reviewer_discovery_cancel`, `reviewer_discovery_review`, `reviewer_discovery_answer_follow_up`, `reviewer_discovery_decide_source` | Polling/reconnect/terminal-state tests; exact query approval; all results visibly unreviewed; private-run cache/storage inspection. |

## 4. Must-have capability map

| ID | Accepted capability | Frontend task owner | Required backend authority/handoff | Observable frontend proof |
| --- | --- | --- | --- | --- |
| FCAP-01 | Browse/search a small local-project registry. | FE-060, FE-061, FE-062, FE-064 | `projects_list_localities`, `projects_list`; opaque cursors and bounded filters | URL-owned filters, paginated results, empty/no-match, no-JS public baseline, narrow-mobile keyboard flow. |
| FCAP-02 | Open a profile with promise, funding, responsible body, dates, status, location, and sources. | FE-070, FE-071, FE-074 | `projects_get`, `projects_get_source`; citation-complete public DTO | Evidence-first hierarchy with unknown fields omitted or labelled, not invented. |
| FCAP-03 | Separate official updates from reviewed community evidence. | FE-042, FE-072 | Typed information/update classes and approved public timeline only | Text and structural distinction that does not rely on colour. |
| FCAP-04 | Explain difficult source material plainly. | FE-070, FE-073, FE-081 | Reviewed translation/summary status or citation-valid generated answer | Plain explanation remains visibly linked to original source and review status. |
| FCAP-05 | Ask limited grounded project questions. | FE-080, FE-081, FE-082, FE-083 | `projects_ask_question`; scoped citations and insufficient-evidence contract | Sentence-linked citations or verbatim insufficient-evidence state; no uncited factual rendering. |
| FCAP-06 | Submit anonymously first. | FE-090, FE-091, FE-094, FE-096 | `reports_submit`; no account required; backend privacy authority | Anonymous selected by default; contact and handle are explicit alternatives. |
| FCAP-07 | Remove image metadata before storage. | FE-093, FE-094 | Backend repeats authoritative sanitation/scan and returns ordered outcomes | Browser preparation is explained as minimisation, never the security guarantee. |
| FCAP-08 | Keep new reports private in reviewer queue. | FE-094, FE-111, FE-112, FE-143 | Private DTOs, reviewer authorisation, no-store | No report body on public route/cache/client bundle; queue shows minimum triage data. |
| FCAP-09 | Give a random non-identifying tracking code. | FE-095, FE-100 | `reports_submit`, `report_status_lookup`; one-time code and keyed storage | Code shown once with copy/print/save guidance; absent from URL and persistence. |
| FCAP-10 | Show appropriate escalation options. | FE-090, FE-100, FE-141 | Verified locality/category/locale escalation DTO and non-emergency disclaimer | Clear next action without promising protection, dispatch, or response. |
| FCAP-11 | Let reviewers validate evidence and change report status. | FE-112, FE-113, FE-114, FE-116 | Reviewer detail/evidence/transition operations and canonical state/version | Confirmed command, conflict refetch, resulting append-only history. |
| FCAP-12 | Show trust labels, timestamps, citations, verification states. | FE-042, FE-070, FE-071, FE-072, FE-073 | Controlled vocabulary and public trust metadata | Labels are textual, dates formatted in Africa/Lagos, citations operable by keyboard. |
| FCAP-13 | Run controlled public-web search. | FE-121, FE-122, FE-126 | Public/reviewer discovery operations; budgets and safe fetch are backend-owned | Bounded start/reuse/cancel/poll UI; report-scoped exact query requires approval. |
| FCAP-14 | Preserve discovered-source provenance and retrieval status. | FE-123 | Scope-safe discovery result DTO | Publisher/type/dates/excerpt/availability/original link shown without approved-source styling. |
| FCAP-15 | Show cited synthesis, agreements, contradictions, and gaps. | FE-123, FE-126 | Strict analysis and same-run citation validation | Separate semantic sections; unresolved conflicts remain visible. |
| FCAP-16 | Ask focused safe follow-up questions. | FE-124 | At most five backend-validated questions and scoped answer operations | Answer/skip/unsafe controls never pressure identity disclosure. |

## 5. Acceptance-criterion ownership

### Trust and accuracy

| ID | Criterion | Frontend owner and proof | Backend enforcement |
| --- | --- | --- | --- |
| FAC-TRUST-01 | Every public project fact has a visible source. | FE-070, FE-071, FE-074: fact/citation component tests and project E2E. | Public DTO excludes uncited facts. |
| FAC-TRUST-02 | Q&A cites sources or reports insufficient evidence. | FE-081, FE-082, FE-083: citation and fallback fixtures. | Output/citation validator fails closed. |
| FAC-TRUST-03 | Unverified reports never appear publicly. | FE-143, FE-150: public canary and route/cache inspection. | Public views/DTOs and publication transaction exclude them. |
| FAC-TRUST-04 | Last-checked dates remain visible. | FE-042, FE-062, FE-070, FE-123. | API requires relevant checked/retrieved timestamps. |
| FAC-TRUST-05 | Each discovery-analysis statement links to a source or is labelled inference/gap. | FE-123, FE-126. | Same-run citation and structured-analysis validation. |
| FAC-TRUST-06 | Discovered sources remain unverified until review. | FE-123, FE-125. | Attach creates a pending source and never approves a fact. |
| FAC-TRUST-07 | Contradictory sources remain visibly separate. | FE-072, FE-123, FE-145. | Backend analysis preserves contradictions rather than resolving them. |

### Safety and privacy

| ID | Criterion | Frontend owner and proof | Backend enforcement |
| --- | --- | --- | --- |
| FAC-SAFE-01 | Anonymous reporting works without authentication. | FE-090, FE-091, FE-094, FE-096 no-account E2E. | `reports_submit` accepts anonymous public role. |
| FAC-SAFE-02 | Demo image location metadata is removed. | FE-093 shows prepared preview; FE-096 uses EXIF fixture. | Server sanitation is authoritative and only safe derivative persists. |
| FAC-SAFE-03 | Optional contact never enters public output. | FE-143 public response/cache/bundle canary inspection. | Separate encrypted contact store and public allowlists. |
| FAC-SAFE-04 | Reviewer operations reject unauthorised users. | FE-110, FE-116 exercise `401`, `403`, expired session, and safe recovery. | Session, role, capability, object scope, CSRF, and Origin enforcement. |
| FAC-SAFE-05 | Tracking credentials resist enumeration and leakage. | FE-095, FE-100, FE-104 generic response and URL/storage/log checks. | Random checked code, HMAC lookup, rate limit, generic projection. |
| FAC-SAFE-06 | External search queries contain no private reporter data. | FE-122 exact safe-query preview and approval; FE-143 outbound UI audit. | Privacy-safe builder and deterministic denylist are authoritative. |
| FAC-SAFE-07 | Private incidents/discovery are inaccessible publicly. | FE-126, FE-143 route/cache/service-worker inspection. | Scope-aware DTOs, database roles, reviewer/reporter credentials. |
| FAC-SAFE-08 | Unsafe fetch targets and content cannot become instructions. | FE-123 labels retrieved material; FE-145 renders safe failures. | SSRF guard, inert extraction, no tools, provider/output validation. |
| FAC-SAFE-09 | No AI/search/worker action publishes automatically. | FE-115, FE-125 use explicit human preview/confirmation and accurate copy. | Human-only publication and source-decision transactions. |

### Connectivity, accessibility, localisation, and demo

| ID | Criterion | Frontend owner and proof | Backend handoff |
| --- | --- | --- | --- |
| FAC-RES-01 | Main pages remain readable at narrow mobile widths. | FE-044, FE-064, FE-074, FE-142 at 320 CSS px and representative mobile WebKit. | Bounded paginated, text-first DTOs. |
| FAC-RES-02 | A recently opened public project can be revisited offline. | FE-130, FE-131, FE-132 service-worker inspection/E2E. | Public cache headers/ETag; no private content in public DTO. |
| FAC-RES-03 | Failed submission has a clear non-duplicating retry path. | FE-094, FE-096 unknown-completion/idempotency fixtures. | Idempotency-Key replay/conflict contract. |
| FAC-RES-04 | Low-data mode removes non-essential media. | FE-133, FE-144 network and bundle evidence. | Core operations require no media. |
| FAC-A11Y-01 | All forms complete with keyboard. | FE-041, FE-064, FE-083, FE-096, FE-104, FE-116, FE-140. | Stable operations/errors; no backend-only keyboard concern. |
| FAC-A11Y-02 | Inputs have names, labels, descriptions, and associated errors. | FE-041, FE-053, FE-140 component/axe/manual proof. | Stable field paths and machine error codes. |
| FAC-A11Y-03 | Status uses text and structure, not colour alone. | FE-042, FE-072, FE-120, FE-140. | Semantic machine values and information classes. |
| FAC-A11Y-04 | WCAG 2.2 AA contrast/zoom/focus/motion checks pass. | FE-040, FE-041, FE-044, FE-140, FE-142. | Not delegated to backend. |
| FAC-LANG-01 | Essential journeys work in `en`, `ha`, `ig`, and `yo` without silent fallback. | FE-050, FE-051, FE-052, FE-053, FE-054, FE-141. | Stable machine values; translation status; localised content where available. |
| FAC-DEMO-01 | A fresh judge can follow verified setup. | FE-151, FE-163, FE-164. | Backend release commands/fixtures remain deterministic. |
| FAC-DEMO-02 | Demo uses cited projects and visibly fictional reports. | FE-062, FE-070, FE-096, FE-150, FE-163. | Source register/seed eligibility and labelled fictional fixtures. |
| FAC-DEMO-03 | Public-to-private-to-review flow fits the rehearsed demonstration. | FE-150, FE-162, FE-163. | All required operations and deterministic fixtures. |
| FAC-DEMO-04 | Public links, hosted revision, and checks are verified before release. | FE-162, FE-164. | Private API health/release evidence. |

## 6. Route ownership and data classification baseline

FE-001 expands this into the complete route matrix. This baseline fixes authority and caching now.

| Route/surface | Primary owner | Data displayed or accepted | Class | Render and cache rule |
| --- | --- | --- | --- | --- |
| `/{locale}` | FE-060 | Product purpose, locality choices, trust promise, public project entry | `public` | Request-time Server Component; public cache; useful without JavaScript. |
| `/{locale}/projects` | FE-061, FE-062 | Public project summaries, filters, opaque cursor | `public` | Server-render initial page; URL-owned filters; public cache/ETag; no build-time API fetch. |
| `/{locale}/projects/{slug}` | FE-070, FE-072 | Approved facts, timeline, sources, Q&A/discovery launch controls | `public` plus request-only Q&A/discovery state | Server-render public projection with tag revalidation; POST interactions no-store and client-isolated. |
| Source view | FE-071 | Approved source metadata and permitted excerpt | `public` | Server-render only if API returns approved public source; public cache/ETag. |
| Report wizard | FE-090 through FE-094 | Private description, category, optional bounded evidence/contact/handle credential | `private`; handle/passphrase input is `one_time_secret` | Dynamic and no-store; optional 24-hour local draft only after warning and excluding contact/attachments/credentials. |
| One-time report completion | FE-095 | Tracking code and safe guidance | `one_time_secret` | Dynamic/no-store; navigation state only; no URL or persistent browser storage; back-navigation protected. |
| Tracking | FE-100, FE-102 | Credential input and public-safe status/list | Input `one_time_secret`; response `private` scoped projection | POST-backed, dynamic, no-store, never service-worker/Next/CDN/persisted-query cached. |
| Handle | FE-101, FE-103 | One-time handle/passphrase; delete credential | `one_time_secret` and `security_metadata` represented as `private` in UI | Dynamic/no-store; show once; no recovery or browser persistence. |
| Trust | FE-073 | Trust labels, privacy, AI limits, human review, prototype limits | `public` | Static/server-rendered public cache. |
| Reviewer sign-in | FE-110 | Username/password input; BFF-only session/CSRF response | `one_time_secret` | Dynamic/no-store; secrets converted to HttpOnly cookie and never returned to browser JavaScript. |
| Reviewer queue | FE-111 | Minimum private triage projection | `private` | Authenticated dynamic/no-store; no prefetch/offline/persisted cache. |
| Reviewer detail | FE-112 through FE-125 | Report/evidence/notes/history/public-update/discovery scope | `private` and `public_after_review` | Authenticated dynamic/no-store; downloads short-lived/attachment; public preview does not change class before publish. |
| Global errors/health feedback | FE-022, FE-145 | Stable problem code, safe request ID, recovery action | `operational_only` | Errors no-store; never echo request content, internal host, credential, or stack. |
| Low-data preference | FE-133 | Boolean user preference only | `public` non-sensitive preference | May persist locally; it cannot contain route history, identity, report, credential, or project-private context. |

### Field-level classification rules

| Field group | Class | Browser rule |
| --- | --- | --- |
| Approved project/locality/fact/update/source public DTO fields | `public` | Render only returned allowlisted fields; preserve citations and dates. |
| Candidate public update, discovered source decision, and report-derived public copy before publication | `public_after_review` | Treat exactly as private until backend publication/approval returns a public projection. |
| Report description/category, contact, files, notes, risk, follow-up answers, reviewer identity/work, report-scoped queries/results | `private` | Memory/request only unless the narrowly approved draft policy applies; no public/client logs, analytics, service worker, URL, or persisted query cache. |
| Tracking code, handle passphrase, reviewer password, API session/CSRF token, signed evidence URL | `one_time_secret` | Never URL/log/analytics/persistent storage; session/CSRF stay BFF-only; signed URL is short-lived and no-store. |
| Request ID, stable problem code, retry time, bounded job status/version | `operational_only` | Safe to display when useful; never combine with private values or use as cross-session tracking. |
| Public Q&A question | `private` for request handling | No persistence by default; screen and send only through the documented no-store operation. |
| Public Q&A answer and public discovery result | `public` content delivered through a no-store interactive response | May remain in current memory view; not a source or verification decision and not persisted offline. |

## 7. Route-to-contract availability check

| Surface need | Documented operation(s) | Result |
| --- | --- | --- |
| Localities, directory, detail, source | `projects_list_localities`, `projects_list`, `projects_get`, `projects_get_source` | Available in OpenAPI. |
| Grounded Q&A | `projects_ask_question` | Available; no-store interactive operation. |
| Report submission and tracking follow-up | `reports_submit`, `report_status_lookup`, `report_status_answer_follow_up` | Available; one-time/idempotency rules documented. |
| Handle create/list/delete | `reporter_handles_create`, `reporter_handles_list_reports`, `reporter_handles_delete` | Available; one-time and generic failure rules documented. |
| Reviewer auth and queue/detail | `auth_sign_in`, `auth_sign_out`, `reviewer_reports_queue`, `reviewer_reports_get` | Available; cookie conversion remains BFF-owned. |
| Evidence, notes, follow-up, transitions | `reviewer_evidence_download`, `reviewer_notes_list`, `reviewer_notes_create`, `reviewer_decisions_ask_follow_up`, `reviewer_decisions_withdraw_follow_up`, `reviewer_decisions_transition` | Available. |
| Public-update draft/preview/publish/withdraw | `reviewer_publication_list`, `reviewer_publication_create_draft`, `reviewer_publication_preview`, `reviewer_publication_publish`, `reviewer_publication_withdraw` | Available. |
| Public discovery | `discovery_start_public_run`, `discovery_get_public_run` | Available. |
| Reviewer report-scoped discovery | `reviewer_discovery_plan`, `reviewer_discovery_create`, `reviewer_discovery_get`, `reviewer_discovery_cancel`, `reviewer_discovery_review`, `reviewer_discovery_answer_follow_up`, `reviewer_discovery_decide_source` | Available. |

No accepted route requires a database/table read or an undocumented HTTP field. The completion route is intentionally a one-time client presentation of the successful `reports_submit` receipt, not a fetchable recovery endpoint. Direct navigation without that receipt must explain that the code cannot be recovered and link to a new report or tracking entry; it must not invent a lookup.

## 8. Non-goals and prohibited frontend scope

| ID | Non-goal | Frontend control |
| --- | --- | --- |
| FNG-01 | Public accounts, profiles, comments, likes, or feeds | No route, component, auth state, or API request is assigned. |
| FNG-02 | Real whistleblower data in the hackathon environment | Fixtures and screenshots are synthetic/fictional; report UI warns this is a prototype. |
| FNG-03 | Emergency dispatch or protection guarantee | Non-emergency disclaimer and verified escalation guidance; no live-response language. |
| FNG-04 | Truth, corruption, guilt, or legal scoring | No score/gauge/badge; use exact verification and uncertainty vocabulary. |
| FNG-05 | Automatic source approval, status change, or publication | Only explicit authorised human commands are represented; output never implies automation made the decision. |
| FNG-06 | Nationwide ingestion, arbitrary URL fetch, maps, analytics, blockchain, native app | No routes, dependencies, or placeholders for these features. |
| FNG-07 | Direct browser access to FastAPI/providers/storage | Browser calls same-origin BFF only; public Server Components use server-only API client. |
| FNG-08 | Generic BFF proxy or frontend domain authority | Purpose-built handlers only; domain failures are mapped, never re-decided. |

## 9. Known inputs and honest constraints

- The backend handoff exists and is the only frontend data contract: 37 operations in OpenAPI `0.0.0`, controlled values, and generated synthetic fixtures.
- The source register contains six AMAC/Bwari candidate records, but as of 19 September 2026 three include source-access or exact-passage gaps. Frontend layout testing uses clearly synthetic fixtures; public rendering must use only backend-seed-eligible facts and must preserve `awaiting_verification`, source availability, and unresolved gaps.
- Hausa, Igbo, and Yoruba human review is not recorded. Future catalogs may start as machine-assisted drafts but cannot carry `reviewed` status without a fluent reviewer record.
- No approved logo, token system, type system, or visual direction exists. Circle 1 must obtain human choice before Circle 4 or visible product surfaces.
- Backend gate-closing work may update the generated contract. FE-030 must regenerate the TypeScript client and fail on drift; frontend work never patches generated OpenAPI or fixture JSON by hand.

## 10. FE-000 exit gate

- [x] All five complete journeys have frontend tasks, routes/surfaces, backend operations, and proof.
- [x] All 16 must-have capabilities have a frontend owner and backend authority/handoff.
- [x] Every Product Brief acceptance criterion has a frontend proof task and enforcement boundary.
- [x] Route ownership, render mode, cache policy, and data class are explicit at baseline level.
- [x] Public, public-after-review, private, one-time-secret, and operational-only fields have browser handling rules.
- [x] Every required backend operation exists in the committed OpenAPI contract.
- [x] No requirement is assigned to the BFF as sole domain, authorisation, verification, or publication authority.
- [x] Non-goals and unresolved inputs are visible and cannot be mistaken for implemented features.

FE-000 reopens if an accepted route, operation, data field, provider-visible payload, cache path, locale requirement, or user journey is added or repurposed. Update this register, the detailed Circle 0 artifact that owns the change, generated contracts where applicable, tests, and the AI build log in the same review.

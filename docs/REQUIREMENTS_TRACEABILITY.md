# Backend requirements traceability

- **Task:** BE-000 — Reconcile backend scope
- **Status:** implemented for planning baseline; update with every accepted requirement change
- **Authoritative inputs:** [`PRODUCT.md`](../PRODUCT.md), [`PRODUCT_BRIEF.md`](PRODUCT_BRIEF.md), [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md), [`BACKEND_BUILD_ORDER.md`](BACKEND_BUILD_ORDER.md)
- **Last reviewed:** 19 September 2026

This register assigns every backend-owned or shared proof-of-concept requirement to a concrete backend task and observable proof. It prevents a user-visible feature from being treated as frontend-only when trust, privacy, persistence, or publication enforcement belongs in FastAPI and PostgreSQL.

## 1. How to use the register

- `backend` means FastAPI, worker, database, or object storage must enforce the requirement.
- `shared` means the backend enforces the rule and the frontend must also represent it accurately.
- `frontend` appears only in the explicit handoff table; it is not evidence that the backend can omit an enforcement rule.
- A requirement is implemented only when the listed backend task, test/evidence, and owning circle exit gate pass.
- When an accepted requirement changes, update its row, task owner, tests, OpenAPI contract where applicable, and AI build log in the same commit.
- New requirements must receive a stable ID. Never recycle an old ID for different behaviour.

## 2. Five complete journeys

| Journey | Backend outcome | Primary backend tasks | Required proof |
| --- | --- | --- | --- |
| J-01 Public project read | Return paginated AMAC/Bwari projects and a citation-complete public projection without private data | BE-040–BE-045 | Idempotent six-project seed; public DTO snapshots; fact/update citation tests; query-plan evidence |
| J-02 Grounded project Q&A | Retrieve approved project evidence only and return validated statement-level citations or insufficient evidence | BE-080–BE-085 | Cross-project isolation; citation-validator suite; four-language golden corpus; provider fixture replay |
| J-03 Anonymous report and tracking | Accept a private fictional report without an account, sanitise evidence, issue a one-time non-sequential code, and expose only a public-safe status | BE-060–BE-067 | Restricted-role insert test; tracking property/enumeration tests; file fixtures; public-field denylist snapshots |
| J-04 Reviewer processing and publication | Authenticate/authorise a reviewer, preserve append-only decisions, and publish only a separately authored citation-backed update | BE-050–BE-054, BE-070–BE-074 | Role matrix; state-transition matrix; private evidence access tests; exact public-preview/publication transaction tests |
| J-05 Source Scout | Build/approve a privacy-safe query, fetch public pages safely, preserve provenance, analyse with citations, and require review before attachment/publication | BE-090–BE-097 | PII canary suite; SSRF fixtures; provenance/dedup tests; analysis citation tests; public/private scope isolation |

All five journeys converge in BE-100–BE-106 hardening, BE-110–BE-114 deployment/operations, and BE-120–BE-122 release/handoff evidence.

## 3. Proof-of-concept must-have capabilities

| ID | Requirement | Ownership | Backend task owner | Backend proof |
| --- | --- | --- | --- | --- |
| CAP-01 | Search or browse the local project registry | shared | BE-040, BE-043–BE-045 | Cursor/filter/text-query contract tests and indexed query plans |
| CAP-02 | Return project promise, funding, responsible body, dates, status, location, and sources | shared | BE-040–BE-045 | Public project schema plus cited seed and public projection snapshots |
| CAP-03 | Separate official updates from reviewed community evidence | shared | BE-041, BE-044 | Typed update classes, visibility constraints, citations, DTO tests |
| CAP-04 | Explain difficult source material in plain language using grounded AI | shared | BE-080–BE-085 | Approved-chunk retrieval, strict structured output, citation validation, locale evaluation |
| CAP-05 | Answer limited project questions with source-linked responses | shared | BE-080–BE-085 | Project-scoped retrieval and insufficient-evidence/citation test corpus |
| CAP-06 | Accept anonymous-first concern/evidence submission | shared | BE-060–BE-064 | No-auth submission E2E, encrypted-row integration test, idempotency test |
| CAP-07 | Strip image metadata before evidence is stored | backend | BE-064 | GPS EXIF fixture absent from sanitised object; raw temporary file deletion proof |
| CAP-08 | Keep reports private and place them in a reviewer queue | backend | BE-032, BE-061, BE-070 | Restricted grants/RLS, public-field snapshots, authorised queue tests |
| CAP-09 | Issue a random tracking code that reveals no identity | backend | BE-062–BE-065 | Entropy/checksum/HMAC tests, one-time response, enumeration controls |
| CAP-10 | Provide pilot-appropriate reporting/escalation options | shared | BE-001, BE-042–BE-043 | Cited/dated escalation records; unverified contact rejection; locale projection |
| CAP-11 | Support reviewer evidence validation and report-status changes | shared | BE-050–BE-054, BE-070–BE-074 | Reviewer policy/state matrix, append-only events, evidence download audit |
| CAP-12 | Return trust labels, timestamps, citations, and verification states | shared | BE-002, BE-040–BE-045 | Controlled values, required fields, citation completeness, DTO examples |
| CAP-13 | Search controlled public web sources for project/incident information | backend | BE-090–BE-093, BE-096 | Safe-query, provider adapter, cap/budget, SSRF and lifecycle tests |
| CAP-14 | Preserve discovered URL, publisher, dates, excerpt, and retrieval status | backend | BE-094, BE-096 | Provenance schema, extraction fixtures, immutable discovery/retrieval records |
| CAP-15 | Produce cited discovery summary with agreements, contradictions, and gaps | backend | BE-095–BE-097 | Structured schema, deterministic citation validator, contradiction/gap fixtures |
| CAP-16 | Ask focused follow-up questions without leaking report details | backend | BE-091, BE-095–BE-096 | Five-question cap, sensitivity/PII canaries, scope/ownership tests |
| LANG-01 | Support English, Hausa, Igbo, and Yoruba essential content honestly | shared | BE-040, BE-042–BE-045, BE-084–BE-085 | Translation-status contract, four-language seeds/evals, preserved names/numbers/citations |

## 4. Public registry and project-detail requirements

| ID | Requirement | Backend tasks | Proof |
| --- | --- | --- | --- |
| PUB-01 | Filter by locality, category, public status, and verification state | BE-044–BE-045 | Allowlisted filter contract and malformed/unknown filter tests |
| PUB-02 | Search by project name or keyword | BE-044–BE-045 | Bounded Unicode query tests and indexed plan |
| PUB-03 | Paginate deterministically | BE-034, BE-044–BE-045 | Tamper-protected cursor and stable ID tie-breaker tests |
| PUB-04 | Return last-checked date and source count | BE-040–BE-045 | Non-null public schema/seed checks |
| PUB-05 | Return plain-language project title/summary per selected locale | BE-040, BE-043–BE-044 | Locale projection and translation-status tests |
| PUB-06 | Return promised deliverable and category/locality | BE-040, BE-043–BE-044 | Seed schema and public DTO contract |
| PUB-07 | Return budget/allocation only when sourced | BE-041, BE-043–BE-045 | Fact citation completeness and absent-when-unknown fixtures |
| PUB-08 | Return responsible authority/contractor only when sourced | BE-041, BE-043–BE-045 | Fact citation completeness and neutral missing state |
| PUB-09 | Return planned dates and evidence-backed current status | BE-002, BE-040–BE-045 | Vocabulary constraints and cited fact/update tests |
| PUB-10 | Return a source-backed official/reviewed-community timeline | BE-041, BE-044 | Update class/visibility/citation constraints |
| PUB-11 | Return direct approved source metadata/excerpt | BE-041, BE-044 | Source approval/availability guard and permitted-excerpt tests |
| PUB-12 | Keep unknown, disputed, outdated, and unavailable information distinct | BE-002, BE-041–BE-045 | Controlled-state fixtures and public schema examples |
| PUB-13 | Hidden and unknown public records use equivalent not-found behaviour | BE-024, BE-044 | Response/status/timing-shape tests |
| PUB-14 | Public response contains no private report/reviewer/storage field | BE-032, BE-045, BE-101–BE-102 | Database-view restrictions and canary denylist snapshots |

## 5. Safe-reporting and tracking requirements

| ID | Requirement | Backend tasks | Proof |
| --- | --- | --- | --- |
| REP-01 | Anonymous submission requires no account/email/phone | BE-061–BE-063 | No-auth/no-contact submission integration test |
| REP-02 | Optional contact is stored separately from report content | BE-060–BE-063 | Separate encrypted table/repository and public denylist test |
| REP-03 | Report includes category, description, and optional attachment | BE-002, BE-061, BE-063–BE-064 | Strict request schema and multipart boundary tests |
| REP-04 | Report creation is idempotent and retry-safe | BE-034, BE-063, BE-103 | Matching replay, fingerprint conflict, concurrent duplicate tests |
| REP-05 | New report is private and receives initial `received` event | BE-061, BE-063 | Same-transaction integration and public-access denial |
| REP-06 | File name/type/size/content are validated and sanitised | BE-064 | MIME spoof, malformed, oversized, active-content fixtures |
| REP-07 | Only the sanitised artifact reaches private object storage | BE-064 | Storage spy/hash test and raw-temp cleanup assertions |
| REP-08 | Hosted-demo scan limitation is explicit; production refuses it | BE-020, BE-064, BE-122 | Environment fail-fast and reviewer-visible state test |
| REP-09 | Private fields are encrypted independently with key versioning | BE-060–BE-061 | Known-answer/tamper/context/rotation tests |
| TRK-01 | Tracking code uses secure random entropy and typo checksum | BE-062 | Property and deterministic randomness-adapter tests |
| TRK-02 | Raw tracking code is returned once and keyed at rest | BE-062–BE-063 | Response/repository/log assertions |
| TRK-03 | Lookup uses POST body and `no-store`, never a path/query | BE-065, BE-101 | OpenAPI/cache-header tests |
| TRK-04 | Invalid/missing/inaccessible lookup is generic and rate-limited | BE-065, BE-100 | Shape/timing/backoff/enumeration tests |
| TRK-05 | Successful lookup returns only safe status/message/next action | BE-065, BE-102 | Public-safe projection and canary denylist tests |
| HDL-01 | Optional handle contains no identity or recovery field | BE-066 | Schema introspection and public/log absence tests |
| HDL-02 | Handle/passphrase are server-generated and shown once | BE-066 | Generation entropy/wordlist/one-time response tests |
| HDL-03 | Wrong handle credentials do not create a linked report silently | BE-066 | Generic failure plus no-insert/kept-draft contract test |
| HDL-04 | Reviewer history is context, not proof | BE-066, BE-070 | DTO wording/aggregation rule tests |
| HDL-05 | Handle deletion unlinks but does not delete reports | BE-066 | Transactional unlink and retained-report tests |

## 6. Reviewer and publication requirements

| ID | Requirement | Backend tasks | Proof |
| --- | --- | --- | --- |
| REV-01 | Reviewer access requires protected authentication | BE-050–BE-054 | Password/session/auth endpoint tests |
| REV-02 | Every private operation uses explicit role policy | BE-053, BE-070–BE-074 | Horizontal/vertical allow/deny matrix |
| REV-03 | Queue returns minimal triage data and supports status filters | BE-070 | Projection snapshot, cursor/filter and N+1 tests |
| REV-04 | Detail returns project/source context and authorised private evidence | BE-070, BE-073 | Role tests and explicit projection/download tests |
| REV-05 | Internal notes are encrypted, append-only, and never public | BE-060, BE-072 | Encryption/audit/public-denylist tests |
| REV-06 | Status changes follow one state machine and append history | BE-002, BE-071 | Complete transition/role/concurrency matrix |
| REV-07 | Reporter message is separate from internal reason | BE-061, BE-071 | Schema and public projection tests |
| REV-08 | Public update is separately authored, previewed, cited, and confirmed | BE-041, BE-074 | Private-field/stale-preview/concurrent/publication transaction tests |
| REV-09 | Status change, AI, search, or worker cannot publish automatically | BE-071, BE-074, BE-095–BE-096 | Negative publication tests at each path |
| REV-10 | Reviewer action has a sensitive-data-safe audit trail | BE-003, BE-023, BE-070–BE-074 | Append-only audit and log canary tests |

## 7. Grounded AI requirements

| ID | Requirement | Backend tasks | Proof |
| --- | --- | --- | --- |
| AI-01 | Q&A index contains approved public project chunks only | BE-080 | Corpus membership/source-approval tests |
| AI-02 | Retrieval is restricted to the selected project | BE-081 | Cross-project adversarial tests |
| AI-03 | Keyword fallback works without an embeddings/provider key | BE-081 | Empty-key deterministic integration test |
| AI-04 | Provider receives minimum passages, opaque citations, no tools, `store: false` | BE-082 | Provider request fixture assertions |
| AI-05 | Every factual statement has valid source citation | BE-083–BE-085 | Unknown/cross-project/uncited/citation-forgery tests |
| AI-06 | Unsupported/invalid output returns insufficient evidence | BE-083–BE-085 | Fallback golden cases |
| AI-07 | AI does not identify suspects, infer guilt, or expose private reports | BE-083, BE-085, BE-102 | Safety corpus and private canary tests |
| AI-08 | Selected locale preserves source titles, names, amounts, and dates | BE-084–BE-085 | Four-language golden/human-review record |
| AI-09 | Raw question is not retained by default | BE-084, BE-101 | Repository/log/telemetry absence test |

## 8. Source Scout requirements

| ID | Requirement | Backend tasks | Proof |
| --- | --- | --- | --- |
| DSC-01 | Project query uses allowlisted public fields | BE-091 | Term-provenance and reject-unknown-field tests |
| DSC-02 | Report-scoped query excludes identity, contacts, codes, attachments, exact private address, and notes | BE-091 | Canary/obfuscation property suite |
| DSC-03 | Exact report-scoped query requires preview/approval | BE-091, BE-096 | State/approval/version tests |
| DSC-04 | Worker payload contains IDs, not private report text | BE-090 | Broker/message capture test |
| DSC-05 | Provider returns at most ten bounded results | BE-092 | Adapter contract/cap tests |
| DSC-06 | Public runs reuse one fresh project run per 24 hours and enforce daily budget | BE-092, BE-096 | Cache/concurrency/budget tests |
| DSC-07 | Reviewer runs are authenticated, audited, separately capped | BE-053, BE-092, BE-096 | Policy/rate/audit tests |
| DSC-08 | Fetcher blocks unsafe destinations/redirects/content | BE-093 | Complete SSRF/timeout/size/content fixture suite |
| DSC-09 | Fetch respects access controls, robots, rate limits, and terms | BE-093 | Policy adapter and blocked-access fixtures |
| DSC-10 | Extraction produces inert text and preserves provenance | BE-094 | Hostile markup/PDF and provenance tests |
| DSC-11 | Duplicate/near-duplicate sources are grouped without losing discovery history | BE-094 | URL/hash/SimHash fixtures |
| DSC-12 | Analysis separates facts, reported claims, contradictions, gaps, questions, and safety note | BE-095 | Strict schema and labelled fixture tests |
| DSC-13 | Analysis citations and five-question limit validate deterministically | BE-095 | Unknown-citation/question-cap tests |
| DSC-14 | Results remain `discovered — not yet reviewed` until reviewer decision | BE-094–BE-096 | State/DTO/negative publication tests |
| DSC-15 | Public and report-scoped runs cannot cross through IDs/caches | BE-096, BE-101–BE-103 | Scope-isolation and cache-key tests |
| DSC-16 | Cancellation stops future work and preserves retrieved review data | BE-090, BE-096 | Per-stage cancellation/crash tests |
| DSC-17 | Fixture replay works without provider keys and is visibly labelled | BE-097 | Offline replay E2E and response-label test |

## 9. Trust, security, resilience, and release requirements

| ID | Requirement | Backend tasks | Proof |
| --- | --- | --- | --- |
| TRUST-01 | Every public project fact has visible approved evidence | BE-041, BE-043–BE-045 | Publication constraint and public DTO tests |
| TRUST-02 | Last-checked/publication/retrieval dates remain distinct | BE-001–BE-002, BE-041, BE-094 | Schema/vocabulary and fixture tests |
| TRUST-03 | Conflicting sources remain visible, not silently merged | BE-095 | Contradiction fixtures and cited analysis schema |
| TRUST-04 | Source availability is separate from fact verification | BE-002, BE-041 | Controlled-value and service-policy tests |
| SEC-01 | API trusts internal caller credentials, not network location alone | BE-022 | Missing/malformed/rotated credential tests |
| SEC-02 | Logs/errors contain no secret or private report value | BE-023–BE-024, BE-102 | Recursive canary redaction and problem snapshots |
| SEC-03 | Reviewer sessions are opaque, keyed at rest, revocable, and expire | BE-051–BE-054 | Token/rotation/revocation/expiry/replay tests |
| SEC-04 | Database roles/views/RLS provide defence in depth | BE-032–BE-033 | Per-role allow/deny integration tests |
| SEC-05 | Private response and signed evidence are no-store/short-lived | BE-073, BE-101 | Header/expiry/replay tests |
| SEC-06 | Rate limits are shared, atomic, bounded, and privacy-safe | BE-100 | Redis concurrency/key-content tests |
| SEC-07 | Contract fuzzing rejects malformed/oversized/unknown input safely | BE-024, BE-102 | Schemathesis and boundary fixtures |
| SEC-08 | High/critical exploitable scan findings block release | BE-105, BE-120 | CI scanner gates and triage record |
| RES-01 | Dependency outages have bounded timeout and explicit degradation | BE-025, BE-082, BE-090–BE-103 | Failure-injection suite |
| RES-02 | Retried mutations/jobs are idempotent and never retry forever | BE-034, BE-063, BE-090, BE-103 | Concurrent retry/dead-letter tests |
| RES-03 | Public list/detail payloads are paginated and bounded | BE-034, BE-044–BE-045 | Cursor/page-size/property tests |
| RES-04 | Clean database reaches head and seed runs twice identically | BE-033, BE-043, BE-120 | Migration/seed hashes and counts |
| OPS-01 | API and worker run from the same non-root image | BE-110 | Container user/command/build/scan tests |
| OPS-02 | Migrations gate deployment and production never auto-seeds | BE-112 | Pre-deploy/abort/config tests |
| OPS-03 | Staging rollback, secret rotation, and complete smoke are exercised | BE-113–BE-114 | Timestamped runbook/smoke evidence |
| REL-01 | One deterministic backend gate verifies static, tests, contract, migration, security, and image | BE-120 | Local and CI `backend-verify` evidence |
| REL-02 | Frontend receives generated contract, examples, status semantics, fixtures, and cache rules | BE-121 | Committed contract package and drift check |
| REL-03 | Final evidence review finds no secret/private/unsupported claim | BE-122 | Search results, manual audit, updated limitations |

## 10. Demo and definition-of-done requirements

| ID | Requirement | Backend tasks | Proof |
| --- | --- | --- | --- |
| DEMO-01 | A clean environment can install, migrate, seed, and verify | BE-010–BE-012, BE-030–BE-034, BE-120 | Clean-checkout local and CI evidence |
| DEMO-02 | Seed command uses cited projects and clearly fictional reports | BE-001, BE-043, BE-122 | Source audit, fictional labels, idempotency result |
| DEMO-03 | Demo reviewer credentials are environment-provided, not real or committed | BE-020, BE-050, BE-122 | Secret scan and bootstrap environment test |
| DEMO-04 | Complete public-to-private-to-review flow supports a sub-four-minute demonstration | BE-114, BE-120–BE-122 | Staging smoke timestamps and fixture path |
| DOD-01 | At least five projects have traceable sources | BE-001, BE-043–BE-045 | Six-project register and seed audit |
| DOD-02 | Q&A uses project sources and citations only | BE-080–BE-085 | Golden corpus and citation validator |
| DOD-03 | Source Scout preserves provenance, deduplicates, cites, identifies gaps/conflicts, and asks relevant questions | BE-090–BE-097 | Deterministic replay journey |
| DOD-04 | Anonymous fictional report, tracking, and reviewer processing work end to end | BE-060–BE-074, BE-114, BE-120 | Integration/staging smoke |
| DOD-05 | No private report data is publicly exposed | BE-032, BE-045, BE-065, BE-101–BE-103, BE-122 | Role tests, public snapshots, canary search |
| DOD-06 | Failure states and low-bandwidth API constraints are tested | BE-034, BE-044, BE-063, BE-084, BE-096, BE-103–BE-104 | Pagination/retry/failure/performance evidence |

## 11. Explicit non-goals and enforcement

| ID | Non-goal | Enforcement owner |
| --- | --- | --- |
| NG-01 | Public user accounts, profiles, comments, likes, or social feed | BE-000 scope review; reject new public-auth/social tables/endpoints in architecture review |
| NG-02 | Real whistleblower data in prototype | BE-001 fictional-data rule, BE-043 seed refusal, BE-122 evidence review |
| NG-03 | Emergency response or guaranteed reporter protection | BE-042 verified non-emergency escalation copy; no dispatch/SLA endpoint |
| NG-04 | Automatic truth/corruption/guilt/legal judgement | BE-002 vocabulary, BE-083/BE-095 output validation |
| NG-05 | Automatic publication by AI/search/worker/status change | BE-071, BE-074, BE-095–BE-096 negative publication tests |
| NG-06 | Nationwide ingestion or generic crawling | BE-040 AMAC/Bwari locality constraints; BE-091 allowlisted project query; BE-093 bounded fetch |
| NG-07 | Live maps, complex predictive analytics, blockchain, or native app backend | BE-004 ADR review required before any dependency/schema/API addition |
| NG-08 | Full third-party page storage without reuse rights | BE-001 reuse notes; BE-094 bounded permitted excerpt policy |
| NG-09 | Production handling of real sensitive reports before legal/privacy/operational/security readiness | BE-106 documented closed production gate; BE-122 visible limitation |

## 12. Frontend-only and shared handoff

The following acceptance criteria are not backend implementation tasks, but the backend must provide contracts that allow the frontend to prove them:

| Frontend concern | Frontend owner | Required backend handoff |
| --- | --- | --- |
| Keyboard, focus, labels, error association, contrast, zoom | FE-040–FE-044, FE-140 | Stable problem codes/field paths and semantic status values from BE-002, BE-024, BE-121 |
| Narrow mobile and responsive layouts | FE-060–FE-064, FE-142 | Bounded paginated DTOs from BE-034, BE-044, BE-121 |
| Offline public revisit and private-cache exclusion | FE-130–FE-134 | Explicit cache/no-store contract from BE-044, BE-065, BE-101, BE-121 |
| Low-data mode | FE-133, FE-144 | Text-first DTOs, bounded pages/results, no mandatory media |
| Four-locale interface and human copy review | FE-050–FE-054, FE-141 | Locale/translation status and stable message codes from BE-002, BE-040, BE-084–BE-085, BE-121 |
| One-time tracking/handle credential presentation | FE-095, FE-101 | One-time `no-store` response contract from BE-062–BE-066, BE-121 |
| Visual distinction without colour-only meaning | FE-040–FE-044 | Explicit information/verification/update classes from BE-002, BE-041, BE-121 |

## 13. Orphan and change-control checklist

Before closing any build circle or accepting a requirement change:

- [ ] Every backend-owned requirement has at least one `BE-*` implementation task.
- [ ] Every shared requirement has a backend enforcement task and frontend representation task.
- [ ] Every task reference exists in `BACKEND_BUILD_ORDER.md`.
- [ ] Every security/privacy requirement names an adversarial test, not only a policy statement.
- [ ] Every public claim requirement names its citation/source proof.
- [ ] Every mutation names idempotency, authorisation, failure, and audit behaviour where relevant.
- [ ] Every provider-dependent feature has deterministic replay and explicit live-test policy.
- [ ] Every state/value change updates the vocabulary, migrations/schema, OpenAPI examples, frontend messages, and tests.
- [ ] Explicit non-goals remain absent or receive an accepted ADR/product-scope change before implementation.
- [ ] No acceptance criterion is assigned to the BFF as the sole domain/security authority.

BE-000 fails if any box cannot be checked for the current accepted scope.

# Privacy and safety controls

- **Status:** implemented prototype controls, reviewed 19 September 2026
- **Scope:** backend and its frontend handoff contract
- **Production status:** closed to real report data

This is a technical control summary, not a legal-compliance claim. The authoritative asset and
flow analysis is [`THREAT_MODEL.md`](THREAT_MODEL.md); retention and deletion limits are in
[`RETENTION.md`](RETENTION.md). ShaidaGo is not an emergency service and does not promise
protection, investigation, or response. The prototype accepts fictional reports only.

## Data minimisation and separation

- Anonymous reporting needs no account, email address, or phone number. Contact is optional and
  encrypted separately from the report.
- Report descriptions, contacts, notes, follow-up answers, decision reasons, and discovery reasons
  use independently wrapped data keys. Destroying those keys makes the fields unreadable while
  preserving non-sensitive status and audit history.
- Tracking codes are displayed once. Only a keyed lookup value is stored. Optional reporter
  passphrases are stored as Argon2id hashes and have no recovery flow.
- Raw uploads exist only during bounded processing. Durable object storage receives a sanitised
  artifact under a random key with no report, person, or project name.
- PostgreSQL roles separate migration, public, submission, reviewer, and worker capabilities.
  Public reads use allowlisted views; private submissions cannot read reports back.
- Redis contains bounded jobs, leases, and rate-limit counters, never durable report truth or
  report bodies. Worker messages carry identifiers, not private content.

## Public and reviewer boundaries

Public project facts and updates require visible approved citations. A report status change never
publishes text. A reviewer must author a separate update, inspect the exact public projection, and
confirm its digest; the transaction rechecks citations, report version, and private-reference
guards before publication.

Reviewer access is capability-based. Sessions are opaque, rotated/revocable, idle/absolute
bounded, and represented in the browser by a secure `HttpOnly` cookie through the future BFF.
Reviewer mutations require origin enforcement in the BFF and a separate CSRF token at the API.
Evidence downloads are authorised and audited on every request; no object-store URL is exposed.

### Browser cookies

The web app sets at most three first-party cookies, all `SameSite=Lax`, none read by a third party:

| Cookie | Purpose | Contents | Lifetime | Readable by page script |
| --- | --- | --- | --- | --- |
| `NEXT_LOCALE` | Remembers the chosen language so `/` redirects to it | One of `en`, `ha`, `ig`, `yo` | 1 year | Yes (a preference, not a secret) |
| `sg_session` / `__Host-sg_session` | Reviewer session (reviewers only) | Opaque token | Session policy from the API | No (`HttpOnly`) |
| `sg_csrf` / `__Host-sg_csrf` | Reviewer CSRF token, forwarded server-side | Opaque token | Same as the session | No (`HttpOnly`) |

Residents who only read pages or submit anonymous reports receive only the language cookie, and only
after they open a locale-prefixed page. It contains no identifier, no contact detail, and no report
data, and it is set by the proxy that negotiates language (`proxy.ts`).

## Providers and hostile content

Public Q&A receives only approved passages for one project. Strict structured output, citation
resolution, lexical/numeric support, locale binding, and guarded wording fail closed to the
approved insufficient-evidence response. The raw question, prompts, and output are not persisted.

Source Scout builds an allowlisted public query. Report identity, contacts, tracking credentials,
private text, notes, attachments, and precise private locations are forbidden. Its fetcher blocks
private/reserved networks and unsafe ports, revalidates DNS and every redirect, and bounds bytes,
time, compression, and content type. Retrieved text is inert untrusted data. Search results stay
`discovered — not yet reviewed`; AI and ranking cannot attach, verify, publish, or change status.

Embeddings are computed locally (ADR-0010). When `EMBEDDING_BACKEND=fastembed`, the screened,
bounded question is turned into a vector inside the API process by an ONNX model read from disk, and
the approved public chunks were embedded the same way ahead of time. No provider, key or network
call is involved, so embedding adds nothing to what any third party sees. The vector is used to
rank approved public passages and is neither stored nor logged; only the retrieval mode is recorded.
When the backend is off, or a call fails, retrieval falls back to keyword search and says so.

Replay providers and synthetic fixtures are the deterministic default. Live Groq and Brave were
exercised once, on 2026-09-19, with the maintainer's authorisation; the safe evidence is in
`docs/evidence/BE-097-live-evidence.md`. That record includes two live runs whose analysis our own
validator rejected and withheld, which is the intended behaviour.

## Caches, logs, and operational data

Errors, auth, reports, tracking, handles, Q&A, reviewer data, evidence, and discovery state are
`no-store`. Only approved public project reads have the documented short public cache. The frontend
must not persist private data in Next.js caches, a CDN, a service worker, browser storage, or a
query cache.

Structured logs use a sensitive-field denylist and record bounded request/route/error metadata,
not bodies, credentials, contacts, codes, prompts, signed URLs, or full IP addresses. Rate limiting
uses a BFF-supplied client HMAC and bounded Redis counters. Operational metrics contain counts,
durations, versions, and outcome classes only.

## Implemented evidence

- Public response shape snapshots and explicit DTO allowlists.
- Private canaries exercised across public APIs, logs, worker envelopes, search queries, and AI
  boundaries.
- Restricted-role, horizontal/vertical authorisation, CSRF, session revocation, rate-limit,
  citation, publication, SSRF, sanitation, migration, contract-fuzzing, and failure-injection tests.
- Whole-history Gitleaks, Ruff security rules, Bandit, `pip-audit`, Semgrep, CodeQL workflow, and
  container Trivy workflow.
- A canonical deterministic gate with an 85% minimum backend branch-coverage threshold.

Exact commands and current results are recorded in [`AI_BUILD_LOG.md`](AI_BUILD_LOG.md) and
[`evidence/BE-122-final-backend-review.md`](evidence/BE-122-final-backend-review.md).

## Known limitations and production blockers

- Human review of English, Hausa, Igbo, and Yoruba Q&A evaluation copy is pending.
- Three of six source-register projects have no verified fact because their candidate pages were
  access-restricted. A fresh manual audit of all six project records and reuse terms is pending.
- The hosted demo uses `SCANNER_MODE=not_deployed`; sanitised attachments are visibly marked
  `not_scanned_demo`. Production refuses this mode and needs a deployed malware scanner.
- Live Groq/Brave interoperability was exercised once (see BE-097). Provider-side retention and terms have not been reviewed.
- The complete fictional staging smoke journey is pending private-network access through a
  maintainer-registered Railway SSH key.
- Production has not been created. Legal basis, privacy notice, real retention periods, backup and
  restore operations, incident staffing, provider agreements, access review, and an independent
  security/operational review remain mandatory before real data.
- The Next.js BFF and browser application are built and tested locally but not deployed, so cookie
  setting, same-origin/CSRF enforcement, client cache behaviour, accessibility, localisation, and
  low-bandwidth behaviour have no deployed evidence.

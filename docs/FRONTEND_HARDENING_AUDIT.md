# Frontend hardening audit (Circle 14)

- **Date:** 2026-09-20
- **Scope:** every public and reviewer route in `apps/web`, against a fictional mock API and recorded replay data.
- **Status:** evidence for FE-140 to FE-145. Automated proof is listed with the command that produces it. Items that need a person (screen-reader smoke, fluent-language review) are written as scripts below and are **not** claimed as done.

## 1. Accessibility (FE-140)

| Requirement | Evidence |
| --- | --- |
| Landmarks, one title, one `h1`, no skipped heading level, skip link first, valid `lang` | `tests/a11y/structure.a11y.spec.ts`: 12 routes in each of four languages on Chromium and mobile WebKit |
| Axe zero violations | `tests/a11y/*.a11y.spec.ts` (state by state; `make web-a11y`) |
| 200% text and 320 px reflow | every axe audit also checks both; plus the device matrix in section 3 |
| Keyboard, focus restoration | reviewer security suite (Chromium): sign-in, queue, report, actions, dialog Escape returns focus, skip link; public suites for report and tracking |
| Reduced motion, forced colours | `structure.a11y.spec.ts`: no transition or animation under `prefers-reduced-motion`; every control keeps a border and axe passes under forced colours |
| Touch targets | `structure.a11y.spec.ts`: every button, link-button, and field is at least 44 px; no rule reveals content on hover alone |
| Status not by colour alone | status labels are words plus a shape everywhere; asserted in the queue, detail, and discovery suites |

**Known gap:** iOS WebKit Tab-key focus tests are skipped in the runner (a known limitation of that engine's automation). Base UI's nameless focus-guard spans on iOS WebKit are excluded from dialog axe checks only.

### Manual screen-reader smoke (to be run by a person)

Automated zero violations does not replace this. Run once on **desktop (NVDA or VoiceOver + Safari/Chrome)** and once on **mobile (TalkBack or VoiceOver iOS)**, in English and one other language:

1. Landing: heading list, then the language switch; confirm the current language is announced.
2. Directory: search, apply a filter, confirm the results region is announced and the count is stated.
3. Project record: read a statement, follow a citation, confirm the source entry is announced and Back returns to the statement; start Source Scout and confirm the stage announcement is calm (one message per stage, no chatter).
4. Report: complete the fictional report by keyboard/touch; confirm each step name, each error, the one-time code screen, and that the code is not read again after leaving.
5. Tracking: look up a code; confirm the result heading receives focus.
6. Reviewer: sign in, open a report, reveal contact, add a note (confirm dialog is announced and focus returns), change a status, preview and publish an update.
7. Offline: turn the network off on a saved record; confirm the banner is announced.

Record: reader, browser, OS, route, what was announced, and any confusing step. Nothing above has been recorded yet.

## 2. Four languages and content stress (FE-141)

- All four languages are audited for structure, axe, reflow, and overflow (sections 1 and 3).
- Long, unbroken strings (480 characters), a 100-character search, a 960-character note, and a 360-character reason are typed at 320 px in every language with no horizontal scroll (`structure.a11y.spec.ts`). Overflow is fixed by wrapping (`overflow-wrap`), not by ellipsis.
- Plural branches, NGN, and dates: `tests/unit/formatters.test.ts` and the ICU parity check (`pnpm messages:check`).
- **Translation status (visible in `apps/web/messages/status.json`):** English is complete. Hausa, Igbo, and Yoruba have reviewed critical domains (`shell`, `evidence`, `recovery`, `landing`) recorded as maintainer self-review, and **every other domain is pending** (`null`); those pages show the English original with a translation notice and the correct `lang`. No fluent-reviewer sign-off has been obtained. **A fluent Hausa, Igbo, and Yoruba review of safety, trust, status, and escalation copy is a maintainer action.**

## 3. Responsive and device matrix (FE-142)

Seven sizes (320x568 low-end phone, 360x640, 390x844, 844x390 landscape phone, 768x1024 tablet, 1024x768 narrow desktop, 1440x900) across seven routes in four languages, including the dense reviewer queue and detail: no horizontal page scroll at any size (`structure.a11y.spec.ts`). Mobile WebKit runs the same suite as an iPhone 13 (touch, no hover). **Not covered:** a physical low-end device, the on-screen keyboard, and safe-area insets on a notched phone (no automation for these here); CPU and network throttling are emulated only (section 6).

## 4. Client privacy and security (FE-143)

| Check | Evidence |
| --- | --- |
| CSP, frame denial, referrer, nosniff, permissions, COOP on every response class | `tests/e2e/client-security.spec.ts` (`next.config.ts` `SECURITY_HEADERS`). Only this origin is allowed; nothing third-party can load. |
| HSTS | Sent only when `APP_ENV` is `staging` or `production` (`proxy.ts`, BFF responses); asserted absent on local HTTP. The production contract is unproven until a deployed check. |
| No CSP violation on any route; no request to another origin | same suite, 14 routes |
| External links | every external `<a>` has `noopener noreferrer`; no third-party script, font, style, image, or frame in any page |
| XSS | hostile text in a report, note, source excerpt, and discovered page renders as text; no dialog, no executed script |
| Clickjacking | framing the site from another origin shows nothing |
| Cache poisoning and `Vary` | a spoofed host, language header, and locale cookie change neither the body nor the `Vary` set |
| Signed links | no page or evidence response holds a signed URL, credential, or session name |
| Storage, IndexedDB, cookies, address, console, Cache Storage | `client-security.spec.ts`, `pwa-cache.spec.ts`, and the per-flow suites |
| CSRF, origin, open redirect, service-worker scope, bundle secrets | reviewer security suite, sign-in suite, `pwa-cache.spec.ts`, `pnpm bundle:check` |

**Recorded trade-off:** the CSP keeps `'unsafe-inline'` for scripts and styles because the framework emits inline bootstrap data and the low-data head script; per-request nonces would make every page dynamic (and the offline page and service-worker precache rely on static pages). Remove it if the framework and the head script are moved to nonces.

## 5. Performance budgets (FE-144)

Measured on the built app (gzip, first load, Chromium, local server, 2026-09-20):

| Route | JavaScript | Budget |
| --- | --- | --- |
| `/en`, `/en/projects` | 149.0 KB | 170 KB (plan) |
| `/en/projects/{record}` (with Source Scout and Q&A) | 159.6 KB | 170 KB (plan) |
| `/en/report/{record}` | 154.6 KB | 170 KB (plan) |
| `/en/track` | 153.7 KB | 170 KB (plan) |
| `/en/offline` | 148.7 KB | 170 KB (plan) |
| `/en/reviewer/sign-in` | 171.3 KB | 180 KB (route) |
| `/en/reviewer/reports` | 169.0 KB | 180 KB (route) |
| `/en/reviewer/reports/{id}` | 198.7 KB | 210 KB (route) |

**Optimised on a measured cause:** the reviewer report page was 225.5 KB because the public-update preview imported the message formatter from the module that also bundles every language's copy; it now imports a catalogue-free formatter (-26.8 KB). The shared floor is React and Next at about 113 KB.

Other budgets enforced in `tests/e2e/performance.spec.ts`: no API request on page load (nothing to multiply), at most 12 directory results and 20 queue items on a page, polling at spaced intervals that stop at a terminal state, and under 4x CPU throttling on a 1.6 Mbps profile (LCP under 4 s, CLS under 0.1). Measured LCP was 0.45 to 0.49 s and CLS 0.000 to 0.009 for landing, record, and report form.

**Caveats:** the throttled run uses Chromium's emulation against a local server, so it under-reports real latency; no Lighthouse or field data was collected; there are no images and the app uses system fonts, so image and font budgets are trivially met and unmeasured beyond that.

## 6. Error and recovery consistency (FE-145)

`tests/unit/error-consistency.test.ts` proves that expired sign-in, forbidden, not found, wrong credentials, rate limit, conflict, not-allowed-now, validation, markup, unverifiable request, dependency down, timeout, offline, and internal failures each have their own sentence; every code the contract or the boundary can return has reviewed copy; an unknown code shows the generic sentence with a safe support reference and never the code; the "check before sending again" hint appears only where a mutation may have completed; and a wait time appears only when the API gave one. Surface-level recovery is proven in the suites that own each flow (report, tracking, reviewer, discovery, offline). A line-by-line audit of all 304 named fixtures in `docs/FRONTEND_STATE_MATRIX.md` against tests was **not** done; it remains an open item.

## 7. Open findings for the maintainer

1. Screen-reader smoke (section 1) and fluent-language review (section 2) need people.
2. Confirm the `'unsafe-inline'` CSP trade-off or fund the nonce work.
3. Confirm the HSTS contract on the deployed origin.
4. Run Lighthouse or field measurement on the deployed staging origin.
5. Decide whether a state-matrix fixture-by-fixture audit is required before submission.

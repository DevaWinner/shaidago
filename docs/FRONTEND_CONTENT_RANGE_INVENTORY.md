# Frontend content and range inventory

- **Task:** FE-003 — Content and range inventory
- **Status:** Active control
- **Fixture source:** [`frontend-content-range-fixtures.json`](../data/frontend-content-range-fixtures.json), schema `1`
- **State contract:** [`FRONTEND_STATE_MATRIX.md`](FRONTEND_STATE_MATRIX.md)
- **Transport contract:** [`FRONTEND_BACKEND_CONTRACT.md`](FRONTEND_BACKEND_CONTRACT.md)

This is the pre-component fixture contract for content size, density, and wrapping. It makes
minimum, typical, and maximum cases available before `apps/web` exists. The JSON source is
hand-maintained and checked by
[`validate_frontend_content_ranges.py`](../scripts/validate_frontend_content_ranges.py).

## 1. Fixture safety and use

Every record is labelled **SYNTHETIC LAYOUT FIXTURE — NOT A PROJECT, SOURCE, REPORT, OR
CREDENTIAL**. These fixtures are neither demo seed data nor source evidence. They must not be
shown as a real Abuja project, used to exercise an external provider, copied into a public record,
or joined to the six source-register projects.

`minimum`, `typical`, and `maximum` mean a visual and interaction test target, not a promise that
the current API accepts or publishes every displayed field. A `*_recipe` is deterministic test
data: repeat its safe seed to `target_characters`, truncate exactly, and add no person, project,
claim, URL, credential, or contact value. File entries are metadata only; no file bytes exist.

The source register has six controlled candidate records. This inventory intentionally contains no
source-register title, source passage, report fixture, allegation, identifier, or credential. Only
the pilot localities `AMAC` and `Bwari` appear as route/filter values.

## 2. Range matrix

| Surface and content | Minimum fixture | Typical fixture | Maximum fixture | Rendering and truth rule |
| --- | --- | --- | --- | --- |
| Project title, locality, institution, contractor, facts, sources, timeline, dates | `content.project.minimum` — 0 facts/sources/timeline and absent optional institution/contractor | `content.project.typical` — 3 facts, 2 sources, 4 timeline dates | `content.project.maximum` — 160-character title, 120-character optional names, 12 facts/sources/timeline dates | The current public DTO does not expose institution, contractor, or summary counts. They are view-model layout stress inputs only; a missing returned value is explicit unknown/omitted, and a derived source count never implies verification. |
| NGN amount | `content.project.minimum` — absent | `content.project.typical` — `12,500,000` raw NGN fixture | `content.project.maximum` — `987,654,321,012` raw NGN fixture | The current public DTO does not expose an amount. Use only formatter/unit tests until an approved contract exposes one; never infer it from a source or project. |
| English and long locale labels | `content.locale.minimum` — short English source copy | `content.locale.typical` — long Hausa layout copy | `content.locale.maximum` — long Hausa, Igbo, and Yoruba layout copy | Non-English strings are machine-assisted and unreviewed layout stress data, not shippable safety copy. Preserve literal text, test wrapping at 200% zoom, and do not silently fall back. |
| Approved-source identity, passage, and unavailability | `content.source.minimum` — 80-character passage | `content.source.typical` — 320-character passage | `content.source.maximum` — 180-character title, 120-character publisher, 1,000-character passage, restricted availability | Availability never proves/disproves a statement. Keep cited metadata and neutral unavailable wording; do not invent a live source URL. |
| Report description, category, contact choice, files, and errors | `content.report.minimum` — 10-character description, anonymous, no files | `content.report.typical` — 900-character description, 2 metadata-only files, 2 field errors | `content.report.maximum` — 8,000-character description, 3 × 10 MiB metadata-only files, 8 field errors | Private form fixtures contain no contact value, tracking code, handle, passphrase, or report. Contact is a choice only; attachments never enter draft storage. |
| Reporter tracking status, message, follow-ups, history | `content.tracking.minimum` — current status, 60-character message, 0 follow-ups | `content.tracking.typical` — 220-character message, 2 follow-ups | `content.tracking.maximum` — 400-character message, 10 follow-ups | The current tracking contract returns a current status/message and follow-up questions, not reporter-visible status history. `history` is intentionally `not_exposed_by_current_tracking_contract`; no history UI may be invented. |
| Reviewer queue, notes, evidence, status history | `content.reviewer.minimum` — 1 queue row, 0 notes/evidence, 1 event | `content.reviewer.typical` — 20 rows, 4 notes, 2 evidence items, 4 events | `content.reviewer.maximum` — 50 rows/notes, 3 evidence items, 12 event layout target, 4,000-character note | All reviewer cases are no-store, synthetic, and private. The 12-event target is a layout stress case, not a backend event cap; evidence metadata never contains an object key or URL. |
| Source Scout results, citations, contradictions, gaps, questions | `content.discovery.minimum` — 0 of each | `content.discovery.typical` — 4 cards, 8 citations, 2 contradictions, 3 gaps, 3 questions | `content.discovery.maximum` — 10 cards, 24 citations, 5 contradictions, 8 gaps, 5 questions | Every card is labelled `discovered — not yet reviewed`. Citation IDs resolve only within the same run; no discovery item becomes approved evidence or a public fact. |

## 3. Fixture registry

| Surface | Minimum | Typical | Maximum | Consumers |
| --- | --- | --- | --- | --- |
| Public project | `content.project.minimum` | `content.project.typical` | `content.project.maximum` | Directory, detail, evidence timeline, responsive cards |
| Locale copy | `content.locale.minimum` | `content.locale.typical` | `content.locale.maximum` | Shell, controls, errors, zoom and wrapping tests |
| Approved source | `content.source.minimum` | `content.source.typical` | `content.source.maximum` | Source view, citation trigger, unavailable-source state |
| Private report | `content.report.minimum` | `content.report.typical` | `content.report.maximum` | Wizard, evidence picker, validation summary, upload states |
| Tracking | `content.tracking.minimum` | `content.tracking.typical` | `content.tracking.maximum` | Lookup result, follow-up list, privacy-safe recovery |
| Reviewer workspace | `content.reviewer.minimum` | `content.reviewer.typical` | `content.reviewer.maximum` | Queue, detail, notes, evidence and status-event layout |
| Source Scout | `content.discovery.minimum` | `content.discovery.typical` | `content.discovery.maximum` | Public/reviewer discovery cards, analysis, gaps and follow-ups |

## 4. Implementation rules for later circles

- Test every component with its row's three named fixtures before treating it as reusable. Pair
  them with the appropriate `ui.<surface>.*` state from the state matrix; a size fixture does not
  replace an error, offline, stale, forbidden, or loading fixture.
- Use a generated API type plus a narrow view model for returned fields. These fixtures identify
  stress cases; they do not author a hidden API field or widen a public response.
- Render public project/source examples only through synthetic labels until the source-register
  review makes a real fact eligible. Keep source passages exact if a later test uses an approved
  DTO; do not translate names, dates, amounts, or quoted claims.
- Do not persist report, reviewer, tracking, handle, or discovery fixtures in a browser cache,
  screenshot artifact, trace, or service worker. Test fixtures may be loaded only by local test
  code once the web package exists.
- For accessible tests, check keyboard order, error association, status text, long-label wrapping,
  200% zoom, reduced motion, and both a narrow mobile viewport and desktop viewport. The visual
  direction remains a human approval dependency; these fixtures do not choose it.

## 5. FE-003 evidence checklist

- [x] All requested content families have explicit minimum, typical, and maximum synthetic fixtures.
- [x] Long Hausa, Igbo, and Yoruba labels are marked machine-assisted and unreviewed.
- [x] Contract-absent currency and tracking history are marked as unavailable rather than invented.
- [x] Private/one-time values and source-register records are excluded from every fixture.
- [x] A dependency-free validator checks fixture shape, source-register separation, documentation coverage, and negative mutations.

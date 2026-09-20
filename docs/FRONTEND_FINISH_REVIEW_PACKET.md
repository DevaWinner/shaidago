# Independent finish review packet (FE-153)

**Status: reviewed once, disposition `fix` (2026-09-20); see the end of this file.** The build order requires a fresh reviewer, not the author, to give a disposition of `recapture`, `rebuild`, `fix`, or `ship`. None has been obtained. This packet is what that reviewer needs. Until a disposition exists the visual finish is **not** accepted, and nothing here may be described as approved.

## Inputs

- **Original brief:** [`PRODUCT.md`](../PRODUCT.md), [`docs/PRODUCT_BRIEF.md`](PRODUCT_BRIEF.md).
- **Confirmed visual answers and direction contract:** [`docs/FRONTEND_VISUAL_DIRECTION.md`](FRONTEND_VISUAL_DIRECTION.md) (Field ledger, code-led, `.impeccable/config.json`). No approved comp exists.
- **What shipped, with measured values:** [`DESIGN.md`](../DESIGN.md).
- **Valid screenshots** (all opened and checked; fictional data only), in [`docs/evidence/frontend-visual/`](evidence/frontend-visual/):
  - `before/`: desktop 1440x900 and mobile 390x844 of landing (English and Hausa), directory, record, report step 1, tracking, reviewer queue, reviewer report, offline, and trust, captured at the top with motion reduced.
  - `after/`: landing, report, queue, and the bottom of trust after the fix batch.
  - `final/`: mobile queue and landing after the last field-edge and alignment fixes.
- **Craft floor:** the accessibility, overflow, and contrast checks in [`FRONTEND_HARDENING_AUDIT.md`](FRONTEND_HARDENING_AUDIT.md).
- **Detector findings:** the Impeccable detector was not run (no hook is installed and the tool was not invoked); nothing is claimed about it.

## What the author found and changed (one batched round, one confirmation capture)

1. The low-data switch sat above the first viewport on every public page and pushed the emergency-service notice down on the report page. It moved to the page footer; only a browser data-saving suggestion appears at the top, and only when triggered.
2. Reviewer queue filters stacked four fields on a phone and pushed the list below the fold. They are two columns from 360 px (a browser test now requires the first row to be visible at 390 x 844).
3. Form-field edges used the pale rule colour (1.43:1 against the page). They now use the muted colour (5.75:1), and a unit test pins it.
4. After the last capture: `items-start` on the filter grid, to fix a misaligned select. Not re-captured.

## What the reviewer should judge

Hierarchy and a product-specific first viewport (the landing is a left-aligned reading column with a large empty right side on desktop); typography (system fonts only; Noto is named but not shipped); spacing and rhythm; evidence clarity and status language; form craft; consistency of states; translation lengths; mobile transformations; reviewer density; and whether the plain letter-mark icon and logo (`apps/web/public/icons`) are acceptable.

## Disposition

`recapture` / `rebuild` / `fix` / `ship`: **pending.** A `fix` verdict covers only the named fixes. If a round creates raster assets, keep their provenance and delete abandoned ones.

## Result (2026-09-20)

A fresh reviewer context judged the hosted staging site and returned **`fix`**, covering only the named fixes recorded under FE-153 in `docs/FRONTEND_BUILD_ORDER.md`. Applied: two-column directory filters, and the offline page left out of the saved-pages list. Open: the Hausa landing strings (the maintainer's translation pass), a product-specific landing first viewport, a compact mobile header with a distinct report control, an explicit verification-state label on the record summary, one page-title size, and a recapture. The visual finish is therefore not accepted as `ship`.

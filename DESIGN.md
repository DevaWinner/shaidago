# ShaidaGo design: the Field ledger as shipped

This describes what `apps/web` actually renders on 2026-09-20, not the earlier intention. The approved direction is [`docs/FRONTEND_VISUAL_DIRECTION.md`](docs/FRONTEND_VISUAL_DIRECTION.md); the tokens live in [`apps/web/app/globals.css`](apps/web/app/globals.css) and are checked by `apps/web/tests/unit/design-tokens.test.ts`. Screenshots of the final render are in [`docs/evidence/frontend-visual/`](docs/evidence/frontend-visual/) (fictional data only).

## 1. Thesis and modes

A field notebook for public records: warm paper, dark ink, one deep teal, ruled lines, and text that says what it means. Evidence is the interface: every statement carries its own status in words, its sources beside it, and its date. Nothing is decorative, and nothing implies more certainty than the source gives.

Three modes share one system:

- **Public reading**: record, directory, trust, Source Scout. Calm, single column with an evidence rail on wide screens.
- **Private reporting**: report, tracking, handle. Step by step, one decision at a time, safety notice first.
- **Reviewer**: queue, report, publication. Denser, marked by a double rule under the header and a "Not for sharing" banner.

There is no dark mode. `forced-colors` and `prefers-contrast: more` are supported.

## 2. Palette and token roles (measured)

Contrast is computed from the token values (WCAG relative luminance).

| Role | Token | Value | Used for | Contrast |
| --- | --- | --- | --- | --- |
| Page | `--color-canvas` | `#F7F2E8` | page background | text on it 14.47:1 |
| Surface | `--color-surface` | `#FFFCF6` | cards, fields, dialogs | text on it 15.76:1 |
| Text | `--color-text` | `#172323` | body, headings | |
| Muted | `--color-muted` | `#526260` | secondary text, **field edges** | 5.75:1 on page, 6.26:1 on surface |
| Rule | `--color-rule` | `#D4CCBE` | dividers only | 1.43:1 (never a control edge) |
| Accent | `--color-accent` | `#006E65` | links, primary buttons | 5.51:1 on page; white on it 6.14:1 |
| Accent strong | `--color-accent-strong` | `#004F49` | hover, icon mark | 8.50:1 on page; white on it 9.48:1 |
| Danger | `--color-danger` | `#A7383B` | errors, high risk | 6.27:1 on surface |
| Warning | `--color-warning` | `#9D5C16` | under review, caution | 5.16:1 on surface |
| Information | `--color-information` | `#005FCC` | limited evidence, focus ring | 5.84:1 on surface |
| Selected | `--state-selected-*` | `#003D37` on `#D9EBE7` | selected state | 9.86:1 |
| Read-only | `--state-read-only-*` | `#384746` on `#EEE8DC` | read-only fields | 7.98:1 |

Rules: colour reinforces a state and never carries it (every status is words plus a shape). Field edges use the muted colour so they reach 3:1 (WCAG 1.4.11); this was corrected in the finish round after the pale rule colour was found on fields. With `prefers-contrast: more` the muted and rule colours darken and borders widen.

## 3. Typography

System fonts only: no web font is shipped, requested, or subset. The stacks name Noto Sans (interface) and Noto Serif (quoted source passages, the "documentary" face) and fall back to `system-ui` and `Georgia`, so on a device without Noto the platform font renders. Scale: `xs .75`, `sm .875`, `base 1`, `lg 1.25`, `xl 1.75`, display `clamp(2rem, 5vw, 4rem)` rem; line height 1.1 (headings), 1.55 (body), 1.7 (quoted passages); prose measure 68 ch. Long words and codes wrap (`overflow-wrap: anywhere`); text is never truncated with an ellipsis where meaning would be lost.

## 4. Spacing, layout, and density

An 8-step space scale (`.25` to `6` rem), a `76 rem` content maximum, and a fluid gutter `clamp(1rem, 3vw, 2rem)`. Public pages are a reading column; a record page adds an evidence rail at large widths and stacks it below on phones. Reviewer pages use cards, not tables, so a queue row stays scannable on a phone; the filter form is two columns from 360 px. Controls are at least 44 px tall (tested). Density tokens (`0.875` compact, `1` comfortable) exist; only comfortable is used today.

## 5. Evidence and status language

Five information classes and six verification states are written out in words (`/trust` explains them) and never shortened to a colour. A statement without a citation does not render. Every discovered result carries "discovered — not yet reviewed" until a reviewer decides, and even then an attached source reads "not verified". Analysis is labelled "an explanation, not a source" and is shown as separate sections (supported facts, reported claims, contradictions, gaps, safety note) with no rank or score. Dates are exact and in `Africa/Lagos`; a copy saved for offline use says when it was saved.

## 6. Primitives and states

`apps/web/src/components/primitives` and `ui`: button (primary, secondary, danger), button-link, field (label, description, error, required), input, select, textarea, checkbox, radio, switch, callout (information, warning, danger), status label, disclosure, live region, toast, confirm dialog, modal, pagination. Grammar: 1 px paper edges, 4 px control corners, 8 px notices, a heavier left bar for notices and evidence entries, a double rule for the reviewer header and preview frame. Every control has hover-independent meaning, a 3 px focus ring offset 3 px in `#005FCC`, and a disabled state that stays legible. Dialogs are alert dialogs whose Cancel comes first.

## 7. Surface adaptations

- **Public**: language switch first on the right, low-data switch in the page footer (a data-saving suggestion appears at the top only when the browser asks for it), source citations as in-page links that work without JavaScript.
- **Report**: the emergency-service limit is the first thing after the step list; one question per step; the tracking code appears once and never again.
- **Reviewer**: private banner, jump list, progressive reveal for contact and evidence, one confirmation for every consequential action, and a visibly separate public-update composer with an exact preview drawn by the public timeline's own component.
- **Read-only and offline**: saved copies carry a banner with the saved time; the offline page is static and lists saved pages.

## 8. Motion

Almost none. The motion tokens are 120 and 180 ms; where a transition is used it is on state only (focus, open). `prefers-reduced-motion`, and the low-data switch, remove every transition and animation. Nothing moves to attract attention, and progress is shown as a stage and real counts, never a percentage that is not measured.

## 9. Responsive transformations

Tested from 320 px to 1440 px, including landscape phone and 200% text: navigation wraps instead of collapsing into a hidden menu, the record's evidence rail moves below the record, reviewer filters go two-up, and tables do not exist. No page scrolls sideways at any size.

## 10. Accessibility, low data, and assets

WCAG 2.2 AA is the bar: one `h1`, one `main`, a first-focus skip link, labelled fields with associated errors, status and alert regions, reduced motion, forced colours, and 44 px targets are tested on every route in four languages. Low-data mode is one plain cookie and removes motion and slows polling. **Assets:** the only images are the letter-mark icons and logo in `apps/web/public/icons`, drawn as SVG from the accent and canvas colours (a plain "S" with a double rule, made on the maintainer's instruction with no font or external source) and rendered to PNG by `scripts/render-icons.mjs`; there is no photograph, illustration, web font, or third-party asset, and none has raster provenance beyond that script. The letter mark has had no visual review beyond the instruction to make it.

## 11. What would dilute the identity

Colour-only status; a score, rank, or "AI confidence"; decorative imagery or gradients; a dark theme or glass surfaces; icon-only controls; a loading spinner that stands in for a stage; animated attention cues; alarmist language about people or projects; a marketing tone; and any control edge lighter than 3:1.

## 12. Known gaps

The independent finish review (FE-153) has not been done, so the visual finish has not been accepted by anyone but its author. Hausa, Igbo, and Yoruba lengths are stress-tested for overflow but their copy is not fluently reviewed.

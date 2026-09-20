# ShaidaGo frontend visual direction

- **Status:** accepted direction; implementation has not started
- **Decision date:** 20 September 2026
- **Owner:** maintainer
- **Build-order tasks:** FE-010 through FE-013

This document is the pre-implementation visual authority for ShaidaGo. It records an approved direction and constraints; it is not `DESIGN.md`. `DESIGN.md` is reserved for Circle 15, after a reviewed implementation exists.

## FE-010 discovery outcome

The maintainer selected **Field ledger** as ShaidaGo's visual world.

The first viewport must make a resident feel oriented, not persuaded by a campaign: it must show that a project record has a promise, an evidence-backed state, sources, a last-checked date, and a safe next action. A generic civic-tech dashboard, an official-looking seal, a flag-derived scheme, a dramatic allegation feed, a startup gradient, or a glossy glass-card treatment would make that promise less trustworthy.

The selected world belongs beside public registers, reporting notebooks, source dossiers, and carefully marked community records. It takes their structural discipline—dates, rules, annotations, and traceable entries—without impersonating any government document or copying a specific Nigerian institution's visual identity. It must remain useful on a low-end mobile device, in all four public locales, with reduced motion and without client JavaScript for essential public reading.

The selected execution path is documented separately under FE-012. The selected world, token roles, route-specific modes, and first-viewport contract are documented in later sections of this file as their tasks close.

## FE-011 direction comparison and selection

The direction workshop evaluated each option on exactly two axes: whether Abuja residents can identify it as a calm civic record they can use, and whether it makes ShaidaGo's source-before-claim mechanism clearer rather than merely more decorative.

| Direction | Audience identification | Product clarity | Decision |
| --- | --- | --- | --- |
| **Field ledger** | Strong: a register and source dossier are familiar ways to check a public record. | Strong: the source, date, review state, and safe action can sit together. | **Selected by the maintainer.** |
| District index | Strong: locality-first wayfinding suits AMAC and Bwari discovery. | Moderate: it risks putting location navigation ahead of evidence. | Retained as a navigation discipline, not the visual world. |
| Evidence panes | Moderate: bounded panes make public/private separation tangible. | Strong: a fact can remain visibly attached to its source and state. | Retained for reviewer-density boundaries, not the public identity. |
| Accountability board | Moderate: fixed rows make history legible. | Strong: a state changes in place rather than disappearing. | Retained for queue and timeline alignment, without real-time theatre. |
| Data field, pixel bulletin, unfolding sheet, annotated spread | Weak for a safety-sensitive civic tool. | Mixed to weak: each privileges an aesthetic mechanism over plain-language evidence. | Declined; their useful disciplines are retained only where stated above. |
| Category-standard portal | Familiar, but generic. | Adequate, but it makes no product-specific promise. | Kept as the conventional exit and not selected. |

### Selected visual world

**Field ledger** treats every public claim as an entry that must earn its place beside an evidence label, last-checked date, and a reachable source. Its materials are a warm mineral-paper ground, quiet ruled divisions, annotation-sized metadata, and citation slips—not faux parchment, official stamps, or nostalgic document decoration. A sober humanist sans carries interfaces and the four locales; a restrained reading serif is reserved for quoted source passages so the interface never mistakes a source for a platform claim.

Public navigation begins with locality and project discovery, then moves through the record in the order a resident needs: promise, current known state, responsibility, dated evidence, unknowns, and safe next action. Forms use labelled fields, inline privacy/safety notices, one clear primary action, and a visible review step. Reviewer queues use aligned metadata rows and named state labels; source pages use a reading column with an evidence rail. Teal is reserved for source-backed or verified context, amber for review/limited evidence, and red only for errors or safety warnings; text and icons always carry the state too.

The signature interaction is the **citation stitch**: activating a claim's cited-source control gives that claim and its source entry the same persistent identifier and visible focus treatment. It must work by keyboard, announce the relationship programmatically, never rely on hover, and reduce to ordinary in-page links with no JavaScript. On narrow screens, the evidence rail becomes an ordered section directly below the claim; in low-data mode it has no decorative media or motion. The honest risk is over-documentation: the system must preserve breathing room, clear language, and an obvious safe action rather than becoming an expert archive.

## FE-012 execution path

The standing workflow is **code-led** and is committed in [`.impeccable/config.json`](../.impeccable/config.json). This is a quality requirement, not a lower-fidelity exception: the code must fulfil the exact first-viewport composition, evidence topology, citation-stitch behaviour, responsive transformations, and reduced-motion rules recorded under FE-013. Future visual tasks do not require a generated image before implementation, and no raster asset is required to establish the identity.

Code-led is appropriate for the hackathon proof of concept because the product's trust mechanism is primarily typographic and structural, public reading must work without decorative media, and the first-load budget cannot depend on a visual-asset pipeline. If a later task deliberately changes to comp-led, that task must obtain a new human approval and must not silently replace this standing preference.

## FE-013 direction contract

The following contract is the source for the first emitted body comment when `apps/web` is integrated. It is intentionally written now; its eventual rendered form must remain no more than 150 words and survive the production build. `DESIGN.md` must not be created from this intent: Circle 15 writes it from the reviewed implementation.

```html
<!--
THESIS: ShaidaGo presents a public claim as a field-ledger entry with its evidence, date, uncertainty, and safe next action; it rejects the generic civic dashboard.
OWN-WORLD: Warm mineral paper, fine ledger rules, humanist UI text, source-reading serif, citation slips, and named status markers make provenance visible without official mimicry.
STORY: A resident locates a project, sees what is known and unknown, reaches its source, and can choose a safe action without exposing a private report.
FIRST VIEWPORT: A locality-tagged project record occupies the reading field; a dated evidence rail sits beside it on wide screens and follows it on small screens; browse is primary and private reporting is clearly secondary.
FORM: Field ledger, selected through direction seed 7158e1bb; code-led execution with citation stitch as the signature interaction.
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
-->
```

### Approved starting tokens

These are semantic starting values for Circle 4, not evidence that contrast, font loading, or rendered layout has already passed. The implementation must test every applied foreground/background pair at WCAG 2.2 AA, self-host/subset any chosen font under its verified licence, and adjust only through the semantic roles below.

| Role | Token | Starting value | Use |
| --- | --- | --- | --- |
| Page ground | `--color-canvas` | `#F7F2E8` | Warm mineral background for public reading. |
| Reading surface | `--color-surface` | `#FFFCF6` | Record sheets, forms, and source extracts. |
| Primary ink | `--color-ink` | `#172323` | Headings, body, and high-emphasis controls. |
| Supporting ink | `--color-ink-muted` | `#526260` | Metadata only; never the sole carrier of important information. |
| Ledger rule | `--color-rule` | `#D4CCBE` | Dividers, tables, and citation boundaries. |
| Evidence/action | `--color-evidence` | `#006E65` | Source-backed links and primary public actions, with text labels. |
| Evidence/action strong | `--color-evidence-strong` | `#004F49` | Hover/focus-adjacent emphasis where contrast testing permits. |
| Limited/review | `--color-review` | `#9D5C16` | Awaiting review, limited evidence, or stale context—never a verdict. |
| Error/safety | `--color-danger` | `#A7383B` | Validation failure and safety-critical warning only, never an allegation state. |
| Keyboard focus | `--color-focus` | `#005FCC` | Visible focus ring on every interactive element. |

| Foundation | Tokens | Direction |
| --- | --- | --- |
| Typography | `--font-ui: "Noto Sans"`, `--font-source: "Noto Serif"`, system fallbacks | Sans for all interface text and locale labels; serif only for quoted source passages and longer reading extracts. Test Hausa, Igbo, Yoruba, and English diacritics before shipping. |
| Type scale | `--text-xs: 0.75rem`, `--text-sm: 0.875rem`, `--text-base: 1rem`, `--text-lg: 1.25rem`, `--text-xl: 1.75rem`, `--text-display: clamp(2rem, 5vw, 4rem)` | Body remains at least 16px; metadata does not become unreadable to create a dense ledger effect. |
| Space | `--space-1` through `--space-9`: `4, 8, 12, 16, 24, 32, 48, 64, 96px` | Rules and metadata use the small scale; record sections use 24px or more. |
| Shape | `--radius-none: 0`, `--radius-control: 4px`, `--radius-notice: 8px`, `--border: 1px` | Records stay square and structural; avoid pill-heavy controls and floating-card stacks. |
| Focus/elevation | `--focus-width: 3px`, `--focus-offset: 3px`, `--shadow: none` by default | Rules, spacing, and contrast create hierarchy; shadows never stand in for containment. |
| Motion | `--motion-none: 0ms`, `--motion-fast: 120ms`, `--motion-standard: 180ms` | Only non-essential opacity/colour changes; reduced motion and low-data mode use `--motion-none`. |

### First viewport and surface brief

The initial public surface is `/{locale}` in **Persuade** mode. Its job is to let a resident understand, within one viewport, that ShaidaGo is a source-backed AMAC/Bwari project record—not a news feed—and to choose either project discovery or a private concern route safely.

On a wide viewport, a 12-column, text-first canvas starts with one quiet navigation row: product name, locality entry, trust explanation, locale control, and the private-report action. Below it, a seven-column record field holds the locality label, public-project-record label, promise/state summary, source count, last-checked date, and primary **Browse project records** action. A four-column evidence rail carries the named verification state, citation path, and a clearly secondary **Report a concern privately** action; the remaining column is the inter-column breathing rule. The first viewport never uses an unsupported statistic, a decorative map, or a hero image in place of a record.

On small screens, navigation retains the name, locale, and safe report access; the record reads before its metadata; the evidence rail becomes an ordered section immediately after the summary; and actions become full-width without becoming visually equal in risk or purpose. Public content remains legible without JavaScript. Private routes, reviewer surfaces, and one-time-secret flows never reuse public caching or public-record styling in a way that implies publication.

### Cross-surface component grammar

- **Persuade — landing and directory:** one lead record, locality filters in the URL, record rows rather than generic feature cards, and a clear source/trust path.
- **Read — project, source, and trust:** an 8/4 reading/evidence topology on wide screens; source quotations are visually distinct from platform summaries; citations are keyboard-reachable ledger entries.
- **Operate — reviewer:** dense aligned rows, persistent case metadata, named state changes, append-only history, and internal/private surfaces with no public cache semantics.
- **Report:** a quiet, stepwise paper form with the privacy warning before any draft persistence, explicit labels, inline errors, and no visual language that turns a private concern into a public claim.
- **States:** loading uses stable rules and text, empty states explain the absence, stale/limited evidence preserves the latest safe date, errors state recovery, and status is never colour alone.

### Implementation and review boundaries

No logo, raster, external font request, icon library, chart, or decorative asset is authorised by this document. Circle 4 owns the actual design primitives and must keep this direction's values semantic. Every visual surface must test keyboard access, focus restoration, 200% zoom, four-locale expansion, reduced motion, forced colours, narrow mobile, low-data mode, and public/private cache boundaries. The visual review in Circle 15 is the first point at which a finished render may update `DESIGN.md`.

## Implemented reality

The approved direction was built as described here with these recorded corrections: the pale rule colour was found on form-field edges (1.43:1) and replaced with the muted colour (5.75:1) in the finish round; the low-data switch moved from the top of every public page to its footer so it does not compete with the first viewport; and the reviewer filter form is two columns from 360 px. The shipped system, with measured values, is described in [`../DESIGN.md`](../DESIGN.md).

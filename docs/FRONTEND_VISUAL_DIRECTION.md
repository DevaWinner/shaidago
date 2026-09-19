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

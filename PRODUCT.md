# ShaidaGo product

ShaidaGo is a working hackathon proof of concept for civic accountability and safe reporting. The hosted staging application and repository use public source material and fictional reports. Real reporting remains out of scope until the production blockers in [`docs/PRIVACY_AND_SAFETY.md`](docs/PRIVACY_AND_SAFETY.md) are closed.

## Platform

web

## Stack

ShaidaGo uses a TypeScript Next.js frontend and BFF with a separate Python FastAPI domain backend. PostgreSQL is the authoritative datastore, and a Python worker handles bounded source-discovery and file-processing jobs. FastAPI generates the browser contract from OpenAPI so the frontend does not maintain a second copy of backend models. The rationale and boundaries are in [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md).

## Users

- Community residents who need to understand local public projects and compare promises with evidence. The initial judge dataset starts in Abuja.
- Affected people and whistleblowers who may need to report concerns without exposing their identity.
- Journalists and civic organisations that need traceable sources, structured histories, and reviewed evidence.
- Authorised reviewers who validate private reports and approve only public-safe updates.
- Public institutions are future stakeholders, not the primary proof-of-concept user.

## Product purpose

ShaidaGo helps people move from scattered public-project information to a source-backed understanding and a safer next action. A successful proof of concept lets a resident find a project, understand the promise and responsible institution, inspect the evidence, ask a grounded question, submit a private concern, track it without an account, and see an authorised reviewer process it without exposing private details.

## Positioning

ShaidaGo connects three activities that are usually separated: understanding an official project record, contributing protected community evidence, and following a human-reviewed accountability trail. Source Scout expands the evidence available for review without treating search results as verified facts or leaking private report information.

## Operating context

- ShaidaGo is location-configurable and is not branded or architecturally tied to one council. The initial judge dataset uses Abuja's AMAC and Bwari Area Councils as two configured localities.
- The public experience supports English (`en`), Hausa (`ha`), Igbo (`ig`), and Yoruba (`yo`).
- The source register contains six candidate projects across the two area councils. Only facts with an approved, exact passage are eligible for public display.
- Core use is mobile-first and may happen on low-end devices or unreliable connections.
- Public project records, private reports, reviewer work, grounded AI answers, and public-web discovery have different trust and access boundaries.
- The repository and a complete public-to-private-to-review demonstration are hackathon judging artifacts.

## Capabilities and constraints

- Public project discovery, filtering, project profiles, source-backed facts, timelines, citations, timestamps, and verification states.
- Grounded project Q&A that uses only approved sources and fails closed when evidence is insufficient.
- Anonymous-first reporting with optional contact data kept separately, private attachments, a non-sequential tracking code, and public-safe status lookup. An optional anonymous reporter handle (server-generated handle and passphrase, no email or phone, no recovery) lets repeat reporters build a reviewer-visible track record; fully anonymous reporting remains the default.
- Reviewer authentication, a minimal-data queue, evidence review, append-only status history, internal notes, and a separately authored public-safe update.
- Source Scout with a previewed privacy-safe query, at most ten results per run, provenance capture, safe fetching, deduplication, cited synthesis, contradiction and gap reporting, and focused follow-up questions.
- Human review is required before a private report or discovered source can affect the public record.
- The product is not an emergency service and must show appropriate escalation guidance.
- No native mobile application, public allegation feed, autonomous publication, legal judgment, nationwide data claim, blockchain, or complex predictive analytics in the proof of concept.
- Remaining validation: an independent source and language review, a manual screen-reader pass, and the legal, privacy, security, and operational work required before real reports.

## Brand commitments

- Product name: **ShaidaGo**.
- Tagline: **Track promises. Verify progress. Take action.**
- Tone: plain, calm, specific, neutral, evidence-led, and safety-conscious. Never sensationalise an allegation or imply certainty that the evidence does not support.
- Visual direction: **Field ledger** — an evidence-first public record with warm mineral surfaces, restrained rules, visible provenance, and safe action. Its accepted pre-implementation contract is in [`docs/FRONTEND_VISUAL_DIRECTION.md`](docs/FRONTEND_VISUAL_DIRECTION.md); the standing workflow is code-led.

## Evidence on hand

- [`docs/PRODUCT_BRIEF.md`](docs/PRODUCT_BRIEF.md) is the current product and technical source brief.
- [`docs/SOURCE_REGISTER.md`](docs/SOURCE_REGISTER.md) records six AMAC/Bwari candidate projects, exact retrieved passages where available, source availability, seed eligibility, and unresolved gaps. The maintainer reviewed the register and its available passages were rechecked on 19 September 2026. This is not an independent source audit, and ineligible facts must not be presented as verified.
- [`contracts/openapi.json`](contracts/openapi.json), [`contracts/frontend-fixtures.json`](contracts/frontend-fixtures.json), and [`docs/FRONTEND_BACKEND_CONTRACT.md`](docs/FRONTEND_BACKEND_CONTRACT.md) form the implemented frontend handoff.
- The Field Ledger visual system and complete English, Hausa, Igbo, and Yoruba interface catalogues are implemented. All four catalogues were maintainer-reviewed on 2026-09-20; the non-English copy has not received an independent second-language review. Future work must not overstate that review, overstate source verification, or present fictional reports as real.

## Product principles

- Source before claim.
- Privacy before publicity.
- Human review before publication.
- State uncertainty and provenance explicitly.
- Make the next safe action clear, even on a weak connection.

## Accessibility and inclusion

- Target WCAG 2.2 AA for the public and reviewer experiences.
- All core flows must work with keyboard and assistive technology, at 200% text zoom, and without colour or animation as the only signal.
- Essential public content and safety guidance must be available in English, Hausa, Igbo, and Yoruba; factual source material remains visibly attributed in its original language when no reviewed translation exists.
- Low-data mode, small paginated payloads, offline revisit of public project pages, resilient form retry, and text-first presentation are product requirements.

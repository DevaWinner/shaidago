# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Delegated: use a modern, stable split stack with a TypeScript Next.js frontend/BFF and a Python FastAPI domain backend. PostgreSQL is the authoritative datastore; a Python worker handles slow source-discovery and file-processing jobs. Browser-to-backend contracts are generated from the backend OpenAPI schema rather than duplicated by hand. The full decision and its boundaries are recorded in `docs/IMPLEMENTATION_PLAN.md`.

## Users

- Community residents in Abuja who need to understand local public projects and compare promises with evidence.
- Affected people and whistleblowers who may need to report concerns without exposing their identity.
- Journalists and civic organisations that need traceable sources, structured histories, and reviewed evidence.
- Authorised reviewers who validate private reports and approve only public-safe updates.
- Public institutions are future stakeholders, not the primary proof-of-concept user.

## Product Purpose

ShaidaGo helps people move from scattered public-project information to a source-backed understanding and a safer next action. A successful proof of concept lets a resident find a project, understand the promise and responsible institution, inspect the evidence, ask a grounded question, submit a private concern, track it without an account, and see an authorised reviewer process it without exposing private details.

## Positioning

ShaidaGo connects three activities that are usually separated: understanding an official project record, contributing protected community evidence, and following a human-reviewed accountability trail. Source Scout expands the evidence available for review without treating search results as verified facts or leaking private report information.

## Operating Context

- The pilot is Abuja and covers AMAC and Bwari Area Councils as two configurable localities within one product.
- The public experience supports English (`en`), Hausa (`ha`), Igbo (`ig`), and Yoruba (`yo`).
- The proof of concept should contain six to eight public projects across the two area councils, each backed by public, non-sensitive sources.
- Core use is mobile-first and may happen on low-end devices or unreliable connections.
- Public project records, private reports, reviewer work, grounded AI answers, and public-web discovery have different trust and access boundaries.
- The repository and a complete public-to-private-to-review demonstration are hackathon judging artifacts.

## Capabilities and Constraints

- Public project discovery, filtering, project profiles, source-backed facts, timelines, citations, timestamps, and verification states.
- Grounded project Q&A that uses only approved sources and fails closed when evidence is insufficient.
- Anonymous-first reporting with optional contact data kept separately, private attachments, a non-sequential tracking code, and public-safe status lookup. An optional anonymous reporter handle (server-generated handle and passphrase, no email or phone, no recovery) lets repeat reporters build a reviewer-visible track record; fully anonymous reporting remains the default.
- Reviewer authentication, a minimal-data queue, evidence review, append-only status history, internal notes, and a separately authored public-safe update.
- Source Scout with a previewed privacy-safe query, at most ten results per run, provenance capture, safe fetching, deduplication, cited synthesis, contradiction and gap reporting, and focused follow-up questions.
- Human review is required before a private report or discovered source can affect the public record.
- The product is not an emergency service and must show appropriate escalation guidance.
- No native mobile application, public allegation feed, autonomous publication, legal judgment, nationwide coverage, blockchain, or complex predictive analytics in the proof of concept.
- Open decisions: human audit/approval of the six source-register candidates; reviewed translations; remaining hosted-service evidence; visual direction; and the standing comp-first or code-first UI workflow preference.

## Brand Commitments

- Product name: **ShaidaGo**.
- Tagline: **Track promises. Verify progress. Take action.**
- Tone: plain, calm, specific, neutral, evidence-led, and safety-conscious. Never sensationalise an allegation or imply certainty that the evidence does not support.

## Evidence on Hand

- [`docs/PRODUCT_BRIEF.md`](docs/PRODUCT_BRIEF.md) is the current product and technical source brief.
- [`docs/SOURCE_REGISTER.md`](docs/SOURCE_REGISTER.md) records six AMAC/Bwari candidate projects, exact retrieved passages where available, source availability, seed eligibility, and unresolved gaps. It is not a completed human audit; facts marked ineligible or awaiting verification must not be presented as verified.
- [`contracts/openapi.json`](contracts/openapi.json), [`contracts/frontend-fixtures.json`](contracts/frontend-fixtures.json), and [`docs/FRONTEND_BACKEND_CONTRACT.md`](docs/FRONTEND_BACKEND_CONTRACT.md) form the implemented frontend handoff.
- No approved logo, visual system, or human-reviewed Hausa, Igbo, and Yoruba translation pack exists yet. Future work must not fabricate these assets, overstate source verification, or present fictional reports as real.

## Product Principles

- Source before claim.
- Privacy before publicity.
- Human review before publication.
- State uncertainty and provenance explicitly.
- Make the next safe action clear, even on a weak connection.

## Accessibility & Inclusion

- Target WCAG 2.2 AA for the public and reviewer experiences.
- All core flows must work with keyboard and assistive technology, at 200% text zoom, and without colour or animation as the only signal.
- Essential public content and safety guidance must be available in English, Hausa, Igbo, and Yoruba; factual source material remains visibly attributed in its original language when no reviewed translation exists.
- Low-data mode, small paginated payloads, offline revisit of public project pages, resilient form retry, and text-first presentation are product requirements.

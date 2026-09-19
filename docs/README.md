# Documentation index

This directory contains the evidence, decisions, and operating rules needed to build and judge ShaidaGo. Keep documents specific, link to authoritative details instead of duplicating them, and update affected documents in the same pull request as a behaviour change.

## Source-of-truth order

When documents overlap, use this order:

1. [`PRODUCT.md`](../PRODUCT.md) for product identity, pilot scope, users, capabilities, and non-goals.
2. [`PRODUCT_BRIEF.md`](PRODUCT_BRIEF.md) for detailed journeys, trust model, requirements, and acceptance criteria.
3. [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) for accepted technical choices, boundaries, data model, quality gates, and build order.
4. [`BACKEND_BUILD_ORDER.md`](BACKEND_BUILD_ORDER.md) and [`FRONTEND_BUILD_ORDER.md`](FRONTEND_BUILD_ORDER.md) for task-level execution. They operationalise the implementation plan and do not override it.
5. The generated OpenAPI contract for implemented HTTP shapes once `contracts/openapi.json` exists.
6. Migrations and executable tests for implemented behaviour.

If implementation reveals a conflict, do not silently choose one version. Correct the higher-level document or record the decision, then update code and tests together.

## Current documents

| Document | Status | Owner question |
| --- | --- | --- |
| [`PRODUCT_BRIEF.md`](PRODUCT_BRIEF.md) | Active | What problem and user outcome are we building? |
| [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) | Accepted architecture | How will the separate frontend/BFF and backend stacks deliver it safely? |
| [`BACKEND_BUILD_ORDER.md`](BACKEND_BUILD_ORDER.md) | Execution specification | In what exact order should the API, worker, persistence, security, and operations be implemented and proven? |
| [`FRONTEND_BUILD_ORDER.md`](FRONTEND_BUILD_ORDER.md) | Execution specification | In what exact order should the UI/BFF, visual system, four-language experience, PWA, and reviewer surfaces be implemented and proven? |
| [`REQUIREMENTS_TRACEABILITY.md`](REQUIREMENTS_TRACEABILITY.md) | Active control | Which backend task and proof owns every accepted capability, acceptance criterion, journey, and non-goal? |
| [`FRONTEND_REQUIREMENTS_TRACEABILITY.md`](FRONTEND_REQUIREMENTS_TRACEABILITY.md) | Active control | Which frontend task, route, operation, data class, cache rule, and proof owns every user-facing requirement? |
| [`FRONTEND_ROUTE_MATRIX.md`](FRONTEND_ROUTE_MATRIX.md) | Active control | What does each route do, how is it rendered/cached/localised, which operations does it call, and where does it hand off? |
| [`FRONTEND_STATE_MATRIX.md`](FRONTEND_STATE_MATRIX.md) | Active control | Which stable fixtures and recovery behavior must every async public, report, tracking, reviewer, and discovery surface implement? |
| [`decisions/`](decisions/README.md) | Accepted decision records | Which hard-to-reverse backend choices are binding, what was rejected, and which tasks enforce them? |
| [`THREAT_MODEL.md`](THREAT_MODEL.md) | Design contract | Which data is private or secret, where may it flow, how is it deleted, and which task proves each control? |
| [`PRIVACY_AND_SAFETY.md`](PRIVACY_AND_SAFETY.md) | Implemented prototype controls | Which privacy controls exist, what evidence proves them, and what still blocks production? |
| [`CONTROLLED_VOCABULARY.md`](CONTROLLED_VOCABULARY.md) | Generated active contract | Which machine values, actors, transitions, audit events, visibility rules, and failure codes are permitted? |
| [`API.md`](API.md) | Active | How is the private API called, what does it return on error, and how is the OpenAPI contract generated and checked? |
| [`KEY_MANAGEMENT.md`](KEY_MANAGEMENT.md) | Active | How are private-field keys held, rotated, destroyed, and later moved to a managed KMS? |
| [`SOURCE_REGISTER.md`](SOURCE_REGISTER.md) | Generated, active | Which real sources support each seed fact, with exact passages, dates, availability, and gaps? |
| [`AI_BUILD_LOG.md`](AI_BUILD_LOG.md) | Active log | Where did AI assist, what was reviewed, and what was the result? |

## Planned evidence documents

Create these when the corresponding build gate produces real evidence; do not add empty placeholders:

- `TRUST_MODEL.md` when the frontend trust explanation and presentation are implemented and tested. `THREAT_MODEL.md` is the design contract; `PRIVACY_AND_SAFETY.md` records implemented backend controls and limitations.
- `DEMO_SCRIPT.md` when the end-to-end scenario is working.
- further architecture decision records under `decisions/` when a durable choice changes the accepted plan.

## Documentation standards

- Use repository-relative links and meaningful link text.
- State dates as absolute dates and record `Africa/Lagos` for local operational time; store application timestamps in UTC.
- Separate verified facts, design decisions, assumptions, open questions, and future work.
- Cite the exact public source supporting each seeded project fact. A resolved URL alone is not evidence of the claim.
- Never copy private report content, contact data, secrets, tracking codes, raw prompts containing sensitive data, or exploit details into public documentation.
- Mark fictional demo records and replayed provider responses prominently.
- Do not claim a command, test, deployment, or feature works until it has been run and the result has been checked.

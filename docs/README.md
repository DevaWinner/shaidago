# Documentation index

This directory contains the evidence, decisions, and operating rules needed to build and judge ShaidaGo. Keep documents specific, link to authoritative details instead of duplicating them, and update affected documents in the same pull request as a behaviour change.

## Source-of-truth order

When documents overlap, use this order:

1. [`PRODUCT.md`](../PRODUCT.md) for product identity, pilot scope, users, capabilities, and non-goals.
2. [`PRODUCT_BRIEF.md`](PRODUCT_BRIEF.md) for detailed journeys, trust model, requirements, and acceptance criteria.
3. [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) for accepted technical choices, boundaries, data model, quality gates, and build order.
4. The generated OpenAPI contract for implemented HTTP shapes once `contracts/openapi.json` exists.
5. Migrations and executable tests for implemented behaviour.

If implementation reveals a conflict, do not silently choose one version. Correct the higher-level document or record the decision, then update code and tests together.

## Current documents

| Document | Status | Owner question |
| --- | --- | --- |
| [`PRODUCT_BRIEF.md`](PRODUCT_BRIEF.md) | Active | What problem and user outcome are we building? |
| [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) | Accepted architecture | How will the separate frontend/BFF and backend stacks deliver it safely? |
| [`AI_BUILD_LOG.md`](AI_BUILD_LOG.md) | Active log | Where did AI assist, what was reviewed, and what was the result? |

## Planned evidence documents

Create these when the corresponding build gate produces real evidence; do not add empty placeholders:

- `SOURCE_REGISTER.md` or a structured equivalent during Gate 0.
- `TRUST_MODEL.md`, `PRIVACY_AND_SAFETY.md`, and `THREAT_MODEL.md` when their controls are implemented and tested.
- `API.md` when the first OpenAPI contract is generated.
- `DEMO_SCRIPT.md` when the end-to-end scenario is working.
- architecture decision records under `decisions/` when a durable choice changes the accepted plan.

## Documentation standards

- Use repository-relative links and meaningful link text.
- State dates as absolute dates and record `Africa/Lagos` for local operational time; store application timestamps in UTC.
- Separate verified facts, design decisions, assumptions, open questions, and future work.
- Cite the exact public source supporting each seeded project fact. A resolved URL alone is not evidence of the claim.
- Never copy private report content, contact data, secrets, tracking codes, raw prompts containing sensitive data, or exploit details into public documentation.
- Mark fictional demo records and replayed provider responses prominently.
- Do not claim a command, test, deployment, or feature works until it has been run and the result has been checked.

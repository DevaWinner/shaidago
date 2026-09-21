# ShaidaGo documentation

The root [`README.md`](../README.md) is the starting point for judges. It links to the hosted prototype, explains what to try, and provides the verified local setup. This index separates the short reviewer path from the engineering records behind it.

## Reviewer path

| Document                                                               | What it answers                                                                                 |
| ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| [`PRODUCT.md`](../PRODUCT.md)                                          | Who is ShaidaGo for, what does it do, and where does the proof of concept stop?                 |
| [`PRODUCT_BRIEF.md`](PRODUCT_BRIEF.md)                                 | Which user journeys, trust rules, and acceptance criteria shaped the product?                   |
| [`../DESIGN.md`](../DESIGN.md)                                         | How does the shipped Field Ledger interface support trust, accessibility, and low-data use?     |
| [`SOURCE_REGISTER.md`](SOURCE_REGISTER.md)                             | Which public passages support the seeded records, and where is evidence unavailable?            |
| [`PRIVACY_AND_SAFETY.md`](PRIVACY_AND_SAFETY.md)                       | Which privacy controls are implemented, and what still blocks real reporting?                   |
| [`evidence/FE-162-hosted-smoke.md`](evidence/FE-162-hosted-smoke.md)   | What worked on the hosted web application, and which reviewer checks were skipped?              |
| [`evidence/BE-114-staging-smoke.md`](evidence/BE-114-staging-smoke.md) | What worked across the API, worker, database, reporting, review, Q&A, and Source Scout journey? |

The reviewer path is deliberately short. It distinguishes implemented behaviour from requirements, and it keeps prototype limits beside the evidence rather than hiding them in a final disclaimer.

## Engineering reference

| Document                                                       | Purpose                                                                            |
| -------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md)             | Architecture, stack decisions, data model, security boundaries, and proof strategy |
| [`API.md`](API.md)                                             | Private API conventions and implemented operation groups                           |
| [`FRONTEND_BACKEND_CONTRACT.md`](FRONTEND_BACKEND_CONTRACT.md) | Browser, BFF, generated-client, and backend ownership boundaries                   |
| [`THREAT_MODEL.md`](THREAT_MODEL.md)                           | Assets, trust boundaries, abuse cases, and required controls                       |
| [`CONTROLLED_VOCABULARY.md`](CONTROLLED_VOCABULARY.md)         | Generated state machines, actors, events, visibility rules, and error codes        |
| [`DEPLOYMENT.md`](DEPLOYMENT.md)                               | Railway service topology and deployment procedure                                  |
| [`RUNBOOKS.md`](RUNBOOKS.md)                                   | Rotation, rollback, failure, and recovery procedures                               |
| [`decisions/`](decisions/README.md)                            | Accepted architecture decisions and their consequences                             |

The route, state, content-range, requirements, and BFF-operation matrices are implementation controls. They are useful when reviewing a particular boundary, but they are not required reading for the product story.

## Build and verification history

[`BACKEND_BUILD_ORDER.md`](BACKEND_BUILD_ORDER.md) and [`FRONTEND_BUILD_ORDER.md`](FRONTEND_BUILD_ORDER.md) record the work in the order it was completed. Status statements inside an earlier task describe that point in time; later gate entries and evidence files supersede them.

[`AI_BUILD_LOG.md`](AI_BUILD_LOG.md) records material AI assistance, maintainer decisions, verification results, and known gaps. It is a chronological audit log, not a product narrative.

The final backend review is in [`evidence/BE-122-final-backend-review.md`](evidence/BE-122-final-backend-review.md). Accessibility, responsive behaviour, privacy, and performance evidence for the frontend is in [`FRONTEND_HARDENING_AUDIT.md`](FRONTEND_HARDENING_AUDIT.md).

## Authority order

When documents disagree, use this order:

1. [`PRODUCT.md`](../PRODUCT.md) for product scope and non-goals.
2. [`PRODUCT_BRIEF.md`](PRODUCT_BRIEF.md) for detailed requirements.
3. [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) and accepted [decision records](decisions/README.md) for architecture.
4. The generated [`contracts/openapi.json`](../contracts/openapi.json) for implemented HTTP shapes.
5. Migrations and executable tests for implemented behaviour.

Build orders and audit logs explain how the repository reached its current state. They do not override the product, architecture, contract, or tests.

## Documentation rules

- Separate sourced facts, product decisions, assumptions, and open work.
- Cite the exact public passage behind each seeded project fact. A URL alone is not evidence.
- Use fictional reports in documentation and tests.
- Never include contacts, tracking codes, credentials, signed URLs, private report text, or exploit details.
- Record commands only after they have been run, with failures and skipped checks stated plainly.
- Use absolute dates for evidence and operational records.

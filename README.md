# ShaidaGo

> Track promises. Verify progress. Take action.

ShaidaGo is a low-bandwidth civic accountability platform for understanding local public projects, checking the evidence behind public claims, and reporting concerns through a private, human-reviewed workflow.

The hackathon pilot covers Abuja's AMAC and Bwari Area Councils. The public experience is designed for English, Hausa, Igbo, and Yoruba.

## Repository status

The backend (`services/platform`) and the frontend (`apps/web`) are both built and verified locally against fictional data and recorded replay providers. `apps/web` is a Next.js app and thin BFF with public records, cited Q&A, a private anonymous report flow, tracking and optional reporter handles, a reviewer workspace with publication, Source Scout, an offline-capable public shell, and English, Hausa, Igbo, and Yoruba routes. Hausa, Igbo, and Yoruba copy is largely pending fluent review (see the limitations). The complete gate is `make verify`; the last full run of the frontend gate from a clean checkout is recorded in [`docs/AI_BUILD_LOG.md`](docs/AI_BUILD_LOG.md) and [`docs/FRONTEND_BUILD_ORDER.md`](docs/FRONTEND_BUILD_ORDER.md).

Not yet done, and stated plainly: nothing has been deployed or run against a hosted origin, the first hosted CI run has not happened, the independent visual finish review has not been done, and human source, language, screen-reader, legal, privacy, and security reviews are outstanding. Public seed facts remain limited to the exact evidence and caveats recorded in the source register.

## Run it

Needs Docker, Node (see `.nvmrc`), `pnpm`, and `uv`. Everything uses fictional data and recorded replay providers, so no API key is needed.

```text
make setup           # .env from the example, dependencies, local services, migrations, cited demo data
make backend-verify  # the backend gate (needs the local services)
make web-verify      # the frontend gate that needs only Node
make web-verify-full # ...plus the browser suites (run once: pnpm --dir apps/web exec playwright install chromium webkit)
make verify          # backend and full frontend gate
```

To look around without the backend, `pnpm --dir apps/web build` and the standalone server work against the fictional mock used by the browser tests (`apps/web/tests/support/mock-api.mjs`). The demonstration path is in [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md).

## Screenshots

All screenshots use the synthetic "Synthetic full record" and other clearly fictional data, captured with motion reduced, and show no one-time credential. They are in [`docs/evidence/frontend-visual/readme/`](docs/evidence/frontend-visual/readme/).

| Narrow phone, a record | Desktop, project evidence |
| --- | --- |
| ![A project record at 360 px](docs/evidence/frontend-visual/readme/record-mobile-narrow.png) | ![A project record with its evidence rail](docs/evidence/frontend-visual/readme/record-desktop.png) |

| Report: safety first | Reviewer queue |
| --- | --- |
| ![The report form's emergency-service notice](docs/evidence/frontend-visual/readme/report-safety-mobile.png) | ![The reviewer queue](docs/evidence/frontend-visual/readme/reviewer-queue.png) |

| Reviewer report detail | Source Scout (labelled, unreviewed) |
| --- | --- |
| ![A reviewer report detail](docs/evidence/frontend-visual/readme/reviewer-detail.png) | ![Source Scout results](docs/evidence/frontend-visual/readme/source-scout.png) |

## The problem

Information about local projects is fragmented across budgets, procurement records, public statements, and institutional websites. Residents may see that reality does not match a public promise but still lack a clear way to verify the record, understand uncertainty, contribute evidence safely, or follow up.

ShaidaGo brings the public project record, citations, plain-language explanations, community evidence, and safe reporting into one trust-aware journey.

## Core journeys

1. Browse or search cited projects in AMAC and Bwari.
2. Inspect facts, status, responsible institutions, timelines, and original sources.
3. Ask a question answered only from approved project evidence.
4. Submit a fictional anonymous-first concern and receive a non-identifying tracking code.
5. Track the public-safe status without an account.
6. Review evidence privately and publish only a separately authored, approved update.
7. Use Source Scout to discover public information through a previewed privacy-safe query.

## Architecture

```mermaid
flowchart LR
    B[Browser] -->|one public origin| W[Next.js web + BFF]
    W -->|private generated contract| A[FastAPI domain API]
    A --> D[(PostgreSQL + pgvector)]
    A --> R[(Redis)]
    A --> O[(Private object storage)]
    R --> K[Python worker]
    K --> S[Search provider]
    K --> L[Groq language models]
```

- **Frontend/BFF:** Next.js App Router, React, strict TypeScript, Tailwind CSS, accessible project-owned components, and `next-intl`.
- **Backend:** FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, Redis, and Dramatiq.
- **Contract:** FastAPI owns domain rules and emits OpenAPI; the web client is generated from that schema.
- **Boundary:** browsers call only the Next.js origin. The BFF handles browser concerns, while FastAPI remains the sole authority for domain policy, authorisation, privacy, and publication.

The rationale, exact boundaries, rejected alternatives, data model, tests, deployment model, and build order are in [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).

## Trust and safety commitments

- Every public project fact must resolve to approved evidence.
- Private reports never publish automatically.
- AI does not decide whether an allegation is true and cannot publish a claim.
- Anonymous reporting does not require an account, email address, or phone number.
- Contact details, report content, attachments, tracking codes, and reviewer notes stay outside public responses, logs, caches, analytics, and public AI retrieval.
- Search results remain “discovered — not yet reviewed” until a reviewer makes an explicit decision.
- This proof of concept is not an emergency service and must use only fictional report data.

## Documentation

Start with the [documentation index](docs/README.md).

| Document | Purpose |
| --- | --- |
| [PRODUCT.md](PRODUCT.md) | Durable product scope, users, operating context, and non-goals |
| [Product brief](docs/PRODUCT_BRIEF.md) | Detailed problem, journeys, functional requirements, and acceptance criteria |
| [Implementation plan](docs/IMPLEMENTATION_PLAN.md) | Chosen stack, architecture, security model, quality gates, and build order |
| [Backend build order](docs/BACKEND_BUILD_ORDER.md) | Closed implementation circles for the FastAPI API, worker, data, security, tests, and deployment |
| [Frontend build order](docs/FRONTEND_BUILD_ORDER.md) | Closed implementation circles for the Next.js UI/BFF, localisation, accessibility, PWA, and visual finish |
| [AGENTS.md](AGENTS.md) | Repository-wide implementation and code-review rules for coding agents |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Human contribution workflow and pull-request expectations |
| [SECURITY.md](SECURITY.md) | Private vulnerability reporting and prototype data policy |
| [Privacy and safety](docs/PRIVACY_AND_SAFETY.md) | Implemented privacy controls, evidence, and production blockers |
| [AI build log](docs/AI_BUILD_LOG.md) | Transparent record of AI-assisted engineering work and human review status |

## Accessibility and low bandwidth

WCAG 2.2 AA is the bar. Every public and reviewer route is checked in four languages for structure, axe, 320 px reflow, 200% text, forced colours, reduced motion, and 44 px targets (`make web-a11y`). The manual screen-reader smoke is scripted in [`docs/FRONTEND_HARDENING_AUDIT.md`](docs/FRONTEND_HARDENING_AUDIT.md) and **has not been run**. For weak connections: public pages are server-rendered and work without JavaScript where feasible, first-load JavaScript is under 170 KB on every public route, a service worker saves recently viewed public records for offline reading (and never stores anything private, proven by cache inspection), and a low-data switch removes motion and slows background checking. The app ships no images or web fonts beyond a small letter-mark icon.

## How AI was used

AI assisted the design, code, tests, and documentation of this repository, and it is used inside the product only to explain source-grounded answers, never as a source. The full record, including what a human still has to review, is [`docs/AI_BUILD_LOG.md`](docs/AI_BUILD_LOG.md). Human review of the unattended frontend work is **pending** and is not claimed anywhere.

## Demo and links

The demo path is in [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md). **No hosted demo URL and no video exist yet**; this section will link them once they do, and only after every link has been checked signed out.

## Unattended build loops

The tracked Claude commands [`backend-build-loop`](.claude/commands/backend-build-loop.md) and [`frontend-build-loop`](.claude/commands/frontend-build-loop.md) execute the respective build orders task by task. Each requires an explicit task packet, verification evidence, documentation, and one Conventional Commit per task; neither may publish, deploy, or substitute human decisions for source, language, or visual review. The frontend loop uses one `frontend/<circle-goal>` branch per circle and excludes roadmap labels, circle numbers, and task IDs from branch names and commit subjects.

## Development

`services/platform` has a pinned Python toolchain (see its README); the root `Makefile` provides `make backend-*` targets (`make backend-verify` is the backend gate); `make setup` and `make verify` are the judge-facing entry points (see "Run it"). The frozen frontend handoff is [`docs/FRONTEND_BACKEND_CONTRACT.md`](docs/FRONTEND_BACKEND_CONTRACT.md), backed by generated OpenAPI and MSW-ready response fixtures. `make infra-up-core` (after `cp .env.example .env`) starts local PostgreSQL 18 + pgvector, Redis, and MinIO through Docker Compose on loopback-only ports; `make infra-up` adds the ClamAV scanner, which needs 1.5-3 GB of memory. `make migrate` then `make db-roles` prepare the database (schema, roles, and role logins), and `make seed-demo` loads local demo data, refreshes approved public source chunks, and loads the checked-in vectors for those chunks. It never calls an AI provider and needs no model. Embeddings run locally with FastEmbed and multilingual-e5-small (ADR-0010): `make embedding-model` downloads the 129 MB model once (pinned and checksum-verified), `make embeddings` regenerates the checked-in vectors, and `EMBEDDING_BACKEND=fastembed` turns on hybrid retrieval, which is what lets a Hausa, Igbo or Yoruba question find English source passages. It is off by default, and retrieval then runs keyword-only and says so in `retrieval_mode`. No key, no network at run time, and no question leaves the server to be embedded.

When implementation starts, the separate stacks remain independently owned:

- `pnpm` manages `apps/web`.
- `uv` manages `services/platform`.
- root `make` targets orchestrate cross-stack judge workflows only.

## Known limitations

This remains a fictional-data prototype, not an emergency service.

- **Sources.** Three of the six source-register projects have no verified fact, because their sources block automated access.
- **Languages.** The Hausa, Igbo and Yoruba copy for the shell, evidence labels, recovery, and landing was reviewed by the maintainer alone, with no independent second review; every other domain (forms, tracking, reviewer, Source Scout, offline) is still pending and shows the English original with a visible notice.
- **Frontend.** Nothing is deployed; the visual finish has had no independent review; the screen-reader smoke has not been run; the CSP keeps `unsafe-inline` for scripts and styles (a recorded trade-off); and Playwright cannot test offline navigation with a service worker on WebKit, so that proof is Chromium-only.
- **Language model.** Live Groq and Brave runs were made once, and the model's answers were weak against the golden corpus (see [BE-085](docs/evidence/BE-085-live-evaluation.md)), so the demo defaults to replay and labels it.
- **Retrieval.** Local embeddings let a Hausa, Igbo or Yoruba question find English passages that keyword search misses, measured on a small sample only (see [BE-081](docs/evidence/BE-081-local-embeddings.md)).
- **Hosting.** The hosted demo has no malware scanner, and the API service uses about 65% of its 1 GB memory limit at rest and 83% at peak.
- **Production** is closed until legal, privacy, security, and operational review.

See the [`BE-122 evidence review`](docs/evidence/BE-122-final-backend-review.md) for the exact release items, and the staging record in [BE-114](docs/evidence/BE-114-staging-smoke.md) (24 of 24 smoke steps passed).

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before making changes. Do not put vulnerabilities or sensitive report scenarios in a public issue; follow [SECURITY.md](SECURITY.md).

## License

ShaidaGo's original code and documentation are available under the [MIT License](LICENSE). Copyright © 2026 Aniekan Winner Anietie. Third-party source material and datasets retain their own terms and attribution requirements.

# ShaidaGo

## Civic Project Accountability and Safe Reporting Platform

### Detailed Product and Technical Build Brief

- **Project name:** ShaidaGo
- **Tagline:** *Track promises. Verify progress. Take action.*
- **Hackathon:** OSF × Andela — *Information You Can Trust*
- **Primary track:** Transparency & Accountability
- **Secondary track:** Safety, Reporting & Protection
- **Submission deadline:** 21 September 2026 at 23:59 UTC
- **Project type:** Individual hackathon proof of concept
- **Pilot location:** Abuja — AMAC and Bwari Area Councils

> **Name meaning:** “Shaida” means evidence, proof, testimony, or witness in Hausa. “Go” expresses movement from trusted information to practical action. The pilot location can be changed, while the central concept remains focused on helping communities monitor local government projects and report concerns more safely.

---

## 1. Product vision

ShaidaGo is a low-bandwidth civic accountability platform that helps people understand what local government projects were promised, how much was allocated, who is responsible, what progress has been reported, and what they can do when reality does not match the official record.

The platform brings official project information, source documents, plain-language explanations, community evidence, and safe reporting into one clear workflow. It is designed for community residents, affected people and whistleblowers, journalists, and civic organisations.

ShaidaGo also includes a controlled public-source discovery feature called **Source Scout**. When a project or incident is submitted, Source Scout searches permitted public web sources for potentially relevant information, records where and when each item was found, removes duplicates, and uses AI to create a cited summary. It then identifies missing or conflicting details and asks the user or reviewer targeted follow-up questions. Discovered information remains unverified until it passes the platform's review process.

The proof of concept should demonstrate one complete accountability journey:

1. A resident finds a local project.
2. They see the promise, budget, responsible institution, expected timeline, current status, and original sources.
3. They compare the official record with verified community evidence.
4. They submit a concern privately or contribute non-sensitive evidence.
5. They receive a tracking code and clear next steps.
6. An authorised reviewer assesses the report before any safe, verified update is published.

## 2. Problem statement

Information about local government projects is often spread across budget documents, procurement notices, public statements, social posts, and institutional websites. These sources may be difficult to find, written in technical language, outdated, or unclear about who is responsible.

Community members may see that a road, health centre, school, water project, or other public service has not been delivered as promised, but they may not know:

- what was officially approved;
- how much money was allocated;
- the expected delivery date;
- which office or contractor is responsible;
- whether a delay has been officially explained;
- where to report a problem;
- whether reporting could expose them to retaliation or unwanted attention; or
- how to follow up after making a report.

Journalists and civic organisations also spend significant time collecting and checking fragmented information. Meanwhile, institutions may lack a trusted and structured channel for receiving evidence-backed community feedback.

The information gap is therefore not only about access. It is about trust, comprehension, safety, verification, and the ability to take a meaningful next step.

## 3. Target users

### 3.1 Community residents

People who want to know what projects were promised in their area, what stage those projects have reached, and how to raise a concern.

### 3.2 Affected people and whistleblowers

People with direct information or evidence about an abandoned, unsafe, incomplete, falsely reported, or poorly delivered project who may need identity protection.

### 3.3 Journalists and civic organisations

Reviewers who need traceable sources, structured reports, project histories, and evidence that can support further investigation or community engagement.

### 3.4 Public institutions

Local government departments or oversight bodies that may use verified feedback to understand complaints, correct public records, and communicate updates. They are a future stakeholder rather than the main user of the initial proof of concept.

## 4. Primary user needs

The platform should help users answer five questions quickly:

1. **What was promised?**
2. **What reliable evidence supports that claim?**
3. **What is happening now?**
4. **How can I safely contribute information or report a concern?**
5. **What should I do next?**

## 5. Product principles

### Source before claim

Every official claim must point to a source. The interface must clearly distinguish official records, verified community evidence, unverified submissions, and platform-generated summaries.

### Plain language by default

Budgets, contracts, and policies should be explained in simple language without removing important details.

### Privacy before publicity

Sensitive reports must be private by default. A submission must never become public automatically.

### Human review before publication

AI may organise or summarise information, but it must not decide that an allegation is true or publish one without review.

### Useful under weak connectivity

Core project pages and reporting forms should remain usable on low-end mobile devices and unreliable networks.

### Clear status and uncertainty

The interface should show when information was last checked and when a claim is incomplete, disputed, outdated, or awaiting verification.

### Action, not passive information

Each project page and report outcome should explain the next safe step available to the user.

## 6. Proof-of-concept scope

The initial proof of concept should run as one Abuja deployment covering AMAC and Bwari Area Councils and contain approximately five to eight seeded public projects across both localities. Use only publicly available, non-sensitive information for the demo.

### Must-have capabilities

1. Search or browse a small registry of local government projects.
2. Open a project profile containing the official promise, funding, responsible body, dates, status, location, and sources.
3. Display a timeline that separates official updates from reviewed community evidence.
4. Explain difficult source material in plain language using grounded AI.
5. Allow users to ask limited questions about a project and receive source-linked answers.
6. Allow anonymous-first submission of a concern or evidence.
7. Strip image metadata before evidence is stored.
8. Keep new reports private and place them in a reviewer queue.
9. Give the reporter a random tracking code that does not reveal their identity.
10. Provide clear reporting and escalation options appropriate to the pilot location.
11. Provide a reviewer screen for validating evidence and changing report status.
12. Show visible trust labels, timestamps, citations, and verification states.
13. Run a controlled public-web search for information related to a selected project or reported incident.
14. Preserve the URL, publisher, publication date, discovery date, excerpt, and retrieval status for every discovered item.
15. Use AI to summarise discovered material with citations, highlight agreements or contradictions, and identify information gaps.
16. Ask the reporter or reviewer focused follow-up questions without revealing sensitive report details in search queries.

### Required language coverage

Provide English, Hausa, Igbo, and Yoruba for essential interface text, safety guidance, validation messages, and project summaries. Machine-assisted translations must be labelled honestly and reviewed by fluent speakers before the final demonstration; original source titles and excerpts remain visibly attributed in their source language.

### Out of scope for the sprint

- Nationwide project coverage.
- Automated legal judgments or findings of corruption.
- Publishing unreviewed allegations.
- Emergency response or real-time law-enforcement dispatch.
- A full social network or public comment feed.
- Complex predictive analytics.
- Blockchain or other infrastructure that does not directly improve the user journey.
- Real whistleblower data during the demonstration.
- Native mobile applications; a responsive progressive web app is sufficient.

## 7. Core user journeys

### Journey A: Understand a local project

1. User enters a location, project name, or service category.
2. The platform returns relevant project cards.
3. User opens a project and sees a one-paragraph plain-language summary.
4. User sees the amount, timeline, responsible institution, contractor if available, and current verification status.
5. User opens the source panel to inspect the original evidence.
6. User sees the last-checked date and any unresolved information gaps.

**Success condition:** The user can explain what was promised, who is responsible, and where the information came from.

### Journey B: Ask a trusted question

1. User asks a question such as, “When was this project expected to finish?”
2. The system searches only the approved source set for that project.
3. It returns a short answer with citations.
4. If the sources do not support an answer, it says so clearly and suggests where the user can check next.

**Success condition:** The system never presents unsupported content as fact.

### Journey C: Report a problem safely

1. User selects “Report a concern.”
2. The form explains privacy, what will happen, and what not to upload.
3. User chooses a category such as no visible work, incomplete work, unsafe construction, suspected false status, access barrier, or another concern.
4. User describes what they observed and may attach a photo or document.
5. The app removes available image metadata and shows a preview.
6. The user chooses anonymous submission or optional contact details.
7. The report is stored privately and receives a random tracking code.
8. The app gives clear follow-up and safety guidance.

**Success condition:** No report becomes public automatically, and the reporter can check its status without creating an account.

### Journey D: Review submitted evidence

1. An authorised reviewer signs in.
2. The reviewer sees a queue with minimal identifying information.
3. The reviewer examines the claim, evidence, project record, and safety flags.
4. The reviewer marks the report as received, needs more information, under review, verified for public update, referred, or closed.
5. Only a safe summary approved by the reviewer can appear on the public project timeline.

**Success condition:** The public record never exposes a reporter's private data or raw allegation by default.

### Journey E: Discover related public information

1. A reporter or authorised reviewer chooses “Find related public information.”
2. The platform generates a privacy-safe search plan using the project name, public location, responsible institution, service category, relevant dates, and non-sensitive incident keywords.
3. The user previews and approves the search terms before any incident-related search runs.
4. Source Scout queries a search provider and fetches only permitted public pages while respecting access rules, rate limits, and publisher terms.
5. The system removes duplicate results, extracts source metadata and relevant passages, and assigns a preliminary source type.
6. AI produces a short cited summary that separates confirmed facts, reported claims, contradictions, and unknowns.
7. The system asks targeted questions such as, “What date did you first observe the problem?” or “Can you confirm whether this is the same project location?”
8. A reviewer decides whether any discovered source should be attached to the project record or used during report review.

**Success condition:** The feature improves the evidence available for review without leaking reporter information, treating search results as verified facts, or publishing allegations automatically.

## 8. Information and trust model

### 8.1 Information classes

Every item should carry one of these labels:

- **Official source:** Published by a government institution or recognised public body.
- **Independent source:** Published by a credible media, civic, research, or oversight organisation.
- **Community evidence — reviewed:** Submitted by a community member and assessed by an authorised reviewer.
- **Community report — unverified:** Private information still awaiting review; never shown publicly.
- **AI-generated explanation:** A summary or answer produced from cited sources; not an independent source.

### 8.2 Verification states

- Verified from official source
- Corroborated by multiple sources
- Community evidence reviewed
- Awaiting verification
- Disputed
- Outdated
- Source unavailable

### 8.3 Required source metadata

Each source record should contain:

- title;
- publisher;
- source type;
- original URL or document reference;
- publication date, if available;
- date added;
- date last checked;
- geographic relevance;
- extracted text or notes used by the platform;
- reviewer; and
- availability status.

### 8.4 Grounded AI rules

The AI assistant must:

- answer only from sources attached to the selected project;
- cite the source or sources used;
- separate confirmed facts from interpretation;
- say “The available sources do not confirm this” when evidence is insufficient;
- never identify a suspected person, infer guilt, or generate accusations;
- never expose private reports or reporter information;
- display when its answer was generated; and
- allow the user to open the underlying source.

For the proof of concept, retrieval over curated text chunks is enough. A complex autonomous agent is unnecessary.

### 8.5 Public-source discovery rules

Source Scout must follow these rules:

- Search only public information using privacy-safe terms.
- Never include a reporter's name, contact information, device metadata, exact private address, attachment contents, or tracking code in an external query.
- Prefer official government, procurement, budget, audit, legislative, court, established media, and recognised civic-organisation sources.
- Record source provenance before generating a summary.
- Label newly discovered information as `discovered — not yet reviewed`.
- Separate a publisher's factual claims from opinions, allegations, and quoted third-party statements.
- Show publication date, discovery date, last-checked date, and source availability.
- Do not bypass paywalls, logins, CAPTCHAs, access controls, `robots.txt`, or website terms.
- Store only the metadata and limited excerpts needed for review unless reuse of full content is permitted.
- Let reviewers reject irrelevant, duplicated, unsafe, or low-quality sources.
- Never use web popularity or search ranking as proof that a claim is true.
- Require human approval before discovered information changes a project's public status.

### 8.6 AI analysis and follow-up questions

For each discovery run, AI should return structured output containing:

- `summary`: a neutral explanation of what the retrieved sources say;
- `supported_facts`: claims directly supported by one or more citations;
- `reported_claims`: statements made by a source but not independently confirmed;
- `contradictions`: material differences between sources;
- `information_gaps`: details needed to assess relevance or accuracy;
- `follow_up_questions`: up to five clear questions for the reporter or reviewer;
- `source_citations`: source IDs linked to each statement;
- `safety_note`: any reason the output should receive additional human review; and
- `confidence_note`: a plain-language description of source coverage, not a numerical truth score.

Follow-up questions must request only information that is necessary, safe, and relevant. They should not pressure a reporter to reveal their identity or collect sensitive details without a clear reason.

## 9. Functional requirements

### Public project registry

- Filter by location, category, status, and verification state.
- Search by project name or keyword.
- Use compact project cards suitable for mobile screens.
- Show “last checked” and source count on each card.

### Project detail page

- Project title and plain-language description.
- Location and service category.
- Promised deliverable.
- Budget or allocation, where available.
- Responsible authority and contractor, where available.
- Planned start and completion dates.
- Current status with a visible evidence label.
- Source-backed timeline.
- Source list with direct links.
- Trusted question box.
- “Report a concern” action.

### Safe report form

- Short privacy notice in plain language.
- Anonymous mode selected by default.
- Optional contact channel stored separately from report content.
- Concern category and description.
- Optional attachment.
- Confirmation before submission.
- Metadata-removal notice for images.
- Warning not to upload information that could endanger the user.
- Generated tracking code and recovery warning.

### Report status lookup

- Tracking-code input.
- Status and last update.
- Reviewer-safe message.
- Next action, if any.
- No exposure of reporter identity or internal reviewer notes.

### Reviewer dashboard

- Protected sign-in.
- Report queue with status filters.
- Project and source context beside each report.
- Evidence preview.
- Private internal notes.
- Status update control.
- Safe public-summary field.
- Audit trail showing who changed what and when.

### Source Scout

- “Find related information” action on project and private report-review pages.
- Privacy-safe query preview before an incident-related search.
- Search scope controls for official sources, credible media, civic organisations, and a date range.
- Maximum of ten retrieved results for the proof of concept.
- Result cards showing publisher, source type, date, excerpt, and original link.
- Duplicate and near-duplicate grouping.
- AI summary with sentence-level citations.
- Separate sections for supported facts, reported claims, contradictions, and unknowns.
- Suggested follow-up questions that the user or reviewer can answer, skip, or mark unsafe.
- Reviewer controls to attach, reject, or defer a discovered source.
- Discovery status: `queued`, `searching`, `analysing`, `needs review`, `complete`, or `failed`.

### Accessibility and language

- Keyboard-accessible controls.
- Strong colour contrast.
- Clear focus states and form labels.
- Error messages that explain how to fix the issue.
- No colour-only status indicators.
- Plain-language copy.
- Text-size support without broken layouts.
- Optional language switch for key content.

## 10. Suggested screens

1. **Landing page:** Purpose, location selector, search, trust promise, and key project categories.
2. **Project directory:** Search and filters with project cards.
3. **Project detail:** Summary, official facts, timeline, sources, trusted Q&A, and reporting action.
4. **Source viewer:** Source metadata, relevant excerpt, date checked, and original link.
5. **Safe reporting form:** Privacy-first, mobile-friendly multi-step form.
6. **Submission confirmation:** Tracking code, safety note, and expected next step.
7. **Report status page:** Public-safe progress view.
8. **Reviewer sign-in:** Demo credentials documented safely for judges.
9. **Reviewer dashboard:** Queue and report detail.
10. **About trust page:** Explanation of sources, verification labels, AI limits, and privacy.
11. **Source Scout panel:** Query preview, discovery progress, cited summary, evidence gaps, and follow-up questions.

## 11. Data model

### `projects`

- `id`
- `slug`
- `title`
- `summary_plain`
- `category`
- `location_name`
- `latitude` and `longitude` — optional
- `promised_deliverable`
- `allocated_amount`
- `currency`
- `responsible_authority`
- `contractor_name` — nullable
- `planned_start_date` — nullable
- `planned_end_date` — nullable
- `public_status`
- `verification_state`
- `last_checked_at`
- `created_at`
- `updated_at`

### `sources`

- `id`
- `project_id`
- `title`
- `publisher`
- `source_type`
- `url`
- `published_at` — nullable
- `last_checked_at`
- `verification_state`
- `excerpt`
- `content_text`
- `is_public`
- `created_at`

### `project_updates`

- `id`
- `project_id`
- `source_id` — nullable
- `update_type`
- `summary`
- `event_date`
- `verification_state`
- `is_public`
- `created_at`

### `reports`

- `id`
- `tracking_code_hash`
- `project_id`
- `category`
- `description_encrypted` or protected text field
- `status`
- `risk_level`
- `is_anonymous`
- `contact_reference_id` — nullable
- `submitted_at`
- `updated_at`

### `report_contacts`

- `id`
- `report_id`
- `contact_type`
- `contact_value_encrypted`
- `created_at`

Keep this table logically separate and restrict access more tightly than the main report record.

### `evidence_files`

- `id`
- `report_id`
- `storage_key`
- `original_filename_sanitised`
- `mime_type`
- `size_bytes`
- `metadata_stripped`
- `malware_scan_state` — simulated or documented for the proof of concept
- `created_at`

### `report_reviews`

- `id`
- `report_id`
- `reviewer_id`
- `previous_status`
- `new_status`
- `internal_note`
- `public_safe_summary` — nullable
- `created_at`

### `users`

- `id`
- `display_name`
- `role`
- `created_at`

Roles for the proof of concept: `reviewer` and `admin`. Public users do not require accounts.

### `discovery_runs`

- `id`
- `project_id` — nullable
- `report_id` — nullable and reviewer-restricted
- `requested_by_user_id` — nullable for approved public project searches
- `status`
- `search_scope`
- `safe_query_terms`
- `date_from` and `date_to` — nullable
- `started_at`
- `completed_at` — nullable
- `error_code` — nullable and free of sensitive data
- `created_at`

### `discovered_sources`

- `id`
- `discovery_run_id`
- `canonical_url`
- `title`
- `publisher`
- `source_type`
- `published_at` — nullable
- `discovered_at`
- `last_checked_at`
- `excerpt`
- `content_hash`
- `retrieval_status`
- `review_status`
- `relevance_note`
- `is_duplicate_of` — nullable
- `attached_source_id` — nullable

### `discovery_analyses`

- `id`
- `discovery_run_id`
- `summary`
- `supported_facts_json`
- `reported_claims_json`
- `contradictions_json`
- `information_gaps_json`
- `source_citations_json`
- `safety_note`
- `confidence_note`
- `model_name`
- `prompt_version`
- `created_at`

### `follow_up_questions`

- `id`
- `discovery_run_id`
- `question_text`
- `reason`
- `sensitivity_level`
- `answer_text_protected` — nullable
- `answer_status`
- `created_at`
- `answered_at` — nullable

## 12. Suggested technical architecture

Use a deliberately small architecture that can be completed and demonstrated reliably.

### Frontend

- React with TypeScript and Vite
- Tailwind CSS and shadcn/ui or an equivalent accessible component set
- React Router
- TanStack Query
- PWA service worker for app-shell and selected project-page caching
- Client-side image metadata removal before upload where practical

### Backend

- FastAPI with Python
- Pydantic request and response models
- SQLAlchemy or a managed PostgreSQL client
- PostgreSQL database
- Simple role-based access control for reviewers
- Object storage for evidence files

### AI layer

- A small retrieval pipeline over curated project sources
- Source chunking and embeddings, or lightweight keyword retrieval if setup time is limited
- One constrained prompt for plain-language summaries and question answering
- Structured output containing `answer`, `citations`, `confidence_note`, and `insufficient_evidence`
- A Source Scout pipeline with query planning, search-result retrieval, permitted-page extraction, canonical URL normalisation, duplicate detection, relevance filtering, cited synthesis, and follow-up-question generation
- A strict separation between the private incident context used internally to create safe queries and the reduced terms sent to an external search provider

### Public-source discovery services

- Search-provider adapter that can be replaced without changing the application workflow
- Fetcher limited to public HTTP pages and permitted document types
- Parser for HTML and public PDF text
- Per-domain rate limiting, timeouts, response-size limits, and retry caps
- Canonical URL and content-hash deduplication
- Background job or simple queued task so slow discovery does not block the reporting form
- Source allowlist and blocklist configuration
- Audit record of the exact safe query, provider, retrieval time, and result decision

### Deployment

- Static frontend hosting
- Managed backend hosting
- Managed PostgreSQL
- Environment variables for secrets
- Seed script for demo data

### Architecture rule

Prefer a reliable end-to-end flow over extra infrastructure. The judges must be able to run or access the project and understand the trust model quickly.

## 13. Suggested API surface

### Public endpoints

- `GET /api/projects`
- `GET /api/projects/{slug}`
- `GET /api/projects/{id}/sources`
- `POST /api/projects/{id}/ask`
- `POST /api/reports`
- `GET /api/reports/status/{tracking_code}`
- `POST /api/projects/{id}/discover`
- `GET /api/discovery-runs/{id}`
- `GET /api/discovery-runs/{id}/results`
- `POST /api/discovery-runs/{id}/follow-up-answers`
- `GET /api/health`

### Reviewer endpoints

- `POST /api/auth/login`
- `GET /api/reviewer/reports`
- `GET /api/reviewer/reports/{id}`
- `PATCH /api/reviewer/reports/{id}/status`
- `POST /api/reviewer/reports/{id}/public-summary`
- `POST /api/reviewer/reports/{id}/discover`
- `PATCH /api/reviewer/discovered-sources/{id}`
- `POST /api/reviewer/discovered-sources/{id}/attach`

## 14. Privacy and security requirements

- Anonymous reporting must not require an account, email address, or phone number.
- Generate tracking codes using a cryptographically secure random function.
- Store only a hash of the tracking code where practical.
- Separate optional contact information from report content.
- Remove EXIF and GPS metadata from uploaded images before storage.
- Sanitize filenames and validate MIME type and file size.
- Do not log report contents, contact information, tracking codes, or raw attachments.
- Rate-limit reporting and status-check endpoints.
- Protect reviewer routes with authentication and role checks.
- Use generic error responses that do not reveal whether private records exist.
- Add an audit record for reviewer actions.
- Do not expose raw reports through the AI retrieval layer.
- Seed the demo with fictional reports and clearly label them as demonstration data.
- Provide a visible warning that the prototype is not an emergency service.
- Remove sensitive fields before creating an external search query and show the safe query for approval.
- Never send uploaded evidence, private report descriptions, reporter contact data, tracking codes, or internal reviewer notes to a search provider.
- Treat web content as untrusted input: strip active content, block scripts, validate redirects, restrict supported schemes, and protect against server-side request forgery.
- Do not fetch local, private-network, loopback, metadata-service, or non-HTTP destinations.
- Apply timeouts, maximum response sizes, content-type validation, and per-domain rate limits.
- Prevent retrieved page text from overriding system instructions or changing the trust and publication rules.
- Keep discovery results private when they originate from a private report until a reviewer explicitly approves a public-safe source or summary.

## 15. Low-bandwidth strategy

- Design mobile-first.
- Keep the initial JavaScript bundle small.
- Use compressed images and avoid autoplay media.
- Load project lists in small pages.
- Cache the app shell and recently viewed public project pages.
- Save an unfinished report locally until the user submits it, with a privacy warning for shared devices.
- Show upload progress and allow retry after network failure.
- Use text before maps or heavy charts.
- Ensure the core journey works without animations.
- Add a “low-data mode” that hides non-essential images.
- Show discovery results as text-first cards and fetch page images only when requested.
- Allow the user to stop a discovery run or continue reviewing already retrieved results if connectivity fails.

## 16. AI coding-tool usage plan

The competition evaluates how well AI coding tools are used. Document usage clearly without claiming that AI created the core idea.

Use OpenAI Codex or another permitted coding tool to assist with:

- scaffolding the frontend and backend;
- generating typed API clients from the backend schema;
- implementing and testing form validation;
- building accessible components;
- writing database migrations and seed scripts;
- creating unit and integration tests;
- reviewing privacy and authorisation boundaries;
- debugging build and deployment failures;
- simplifying code and improving documentation; and
- preparing setup instructions.

Maintain a short `AI_BUILD_LOG.md` containing:

- the date;
- the engineering task;
- the prompt or a short prompt summary;
- the AI-generated suggestion used;
- what the developer reviewed, changed, or rejected; and
- the result.

This demonstrates thoughtful AI collaboration rather than unreviewed code generation.

## 17. Seed-data plan

Choose five to eight real public projects from the selected pilot area. Only include information that can be cited from public sources.

For each project, capture:

- project name;
- community or ward;
- category;
- promised output;
- allocation or contract value, if published;
- responsible institution;
- contractor, if published;
- official dates;
- status stated by the source;
- source URL or document;
- date last checked; and
- unresolved information gaps.

Do not label a project corrupt, fraudulent, abandoned, or completed unless reliable evidence directly supports the label. Use neutral language such as “No public completion update found as of [date]” where appropriate.

## 18. Testing and acceptance criteria

### Trust and accuracy

- Every public project fact has at least one visible source.
- AI answers contain citations or return an insufficient-evidence response.
- Unverified reports are never shown on public pages.
- “Last checked” dates are visible.
- Every AI discovery-summary statement links to at least one retrieved source or is clearly labelled as an inference or information gap.
- Newly discovered sources remain unverified until reviewed.
- Contradictory sources are shown rather than silently merged into one conclusion.

### Safety and privacy

- Anonymous submission works without authentication.
- Uploaded demo images have location metadata removed.
- Optional contact data is not returned by public APIs.
- Reviewer endpoints reject unauthorised users.
- Tracking codes cannot be guessed sequentially.
- External search queries contain no reporter identity, contact information, private attachments, tracking codes, or unnecessary precise-location data.
- Private incident details and discovery results are inaccessible from public endpoints.
- The fetcher rejects private-network targets, unsupported schemes, oversized responses, and unsafe redirects.
- Retrieved page content cannot change system instructions or automatically publish a claim.

### Low bandwidth and resilience

- The main pages remain readable on a narrow mobile viewport.
- A recently opened project page can be revisited after connectivity is lost.
- A failed submission produces a clear retry path without silent data loss.
- Low-data mode removes non-essential media.

### Accessibility

- All forms can be completed using a keyboard.
- Inputs have programmatic labels.
- Status is communicated with text as well as colour.
- Contrast meets WCAG AA for primary content.

### Demo readiness

- A fresh reviewer can follow the README and run the application.
- Seed data loads with one documented command.
- Demo credentials contain no real secret and work only with demonstration data.
- The complete public-to-private-to-review flow can be shown in under four minutes.

## 19. Build sequence for the invention sprint

### Phase 1: Lock the story and evidence

1. Select the pilot LGA or Area Council.
2. Select five to eight public projects with usable sources.
3. Define the user story and write the one-sentence value proposition.
4. Confirm the public status labels and report categories.

### Phase 2: Build the public accountability flow

1. Create project and source schemas.
2. Load seed data.
3. Build the project directory and project detail page.
4. Add source cards, timestamps, and verification labels.
5. Add constrained AI summaries and Q&A.
6. Add a minimal Source Scout flow for public projects using a maximum of ten results and one cited summary.

### Phase 3: Build protected reporting

1. Build the privacy notice and report form.
2. Implement anonymous submission and tracking codes.
3. Add safe attachment handling and metadata removal.
4. Build status lookup.
5. Build the reviewer queue and public-safe summary workflow.
6. Add reviewer-controlled incident discovery with query preview, privacy redaction, and follow-up questions.

### Phase 4: Harden and polish

1. Test access control and public API responses.
2. Test mobile layout, slow network, offline revisit, and accessibility.
3. Add empty, loading, error, disputed, and insufficient-evidence states.
4. Add a clear “How trust works” page.
5. Replace all placeholder copy and check every source link.
6. Test unsafe URLs, prompt injection in retrieved pages, duplicate sources, conflicting claims, stale pages, and accidental inclusion of private fields in search queries.

### Phase 5: Prepare the submission

1. Finalise the public GitHub repository and README.
2. Record a short demo video.
3. Export the pitch deck as PDF.
4. Write the summary covering the tracks, information sources, trust model, and AI-tool usage.
5. Test every submission link in a private or signed-out browser window.

## 20. Repository structure

```text
shaidago/
├── apps/
│   ├── web/
│   └── api/
├── data/
│   ├── seed-projects.json
│   └── source-notes/
├── docs/
│   ├── PRODUCT_BRIEF.md
│   ├── TRUST_MODEL.md
│   ├── PRIVACY_AND_SAFETY.md
│   ├── AI_BUILD_LOG.md
│   └── DEMO_SCRIPT.md
├── tests/
├── .env.example
├── docker-compose.yml
├── LICENSE
└── README.md
```

A simpler two-folder structure is acceptable if it makes delivery faster. The README must remain the single starting point for judges.

## 21. README requirements

The public README should include:

1. Project name and one-sentence value proposition.
2. The community problem.
3. Target users.
4. Selected hackathon tracks.
5. Screenshots or a short visual walkthrough.
6. How the solution works.
7. How information is sourced and verified.
8. Privacy and safety decisions.
9. Low-bandwidth and accessibility decisions.
10. Where AI is used in the product.
11. How AI coding tools supported development.
12. Technical architecture.
13. Local setup instructions.
14. Test instructions.
15. Known limitations.
16. Future development.
17. Demo link and video link.

## 22. Demo-video narrative

Keep the video direct and evidence-led.

1. **Problem:** Local residents struggle to connect public promises with reliable, current evidence and safe reporting channels.
2. **Project discovery:** Search for a local project.
3. **Trust:** Show the plain-language facts, source labels, citations, and last-checked date.
4. **Grounded AI:** Ask a question and open the cited source.
5. **Protection:** Submit a fictional anonymous report and show the privacy protections.
6. **Accountability:** Use the tracking code, then show the reviewer workflow and safe public update.
7. **Source discovery:** Run Source Scout for the project, show its privacy-safe query, cited summary, conflicting or missing information, and one useful follow-up question.
8. **Impact:** Explain how the model can be adapted to another LGA by changing the project data, local sources, language, and escalation directory.
9. **AI coding usage:** Briefly show the build log and tests produced with AI assistance and developer review.

## 23. Pitch-deck outline

1. Title and one-sentence value proposition.
2. The local information and safety problem.
3. Intended users and a short real-world scenario.
4. Why existing channels are insufficient.
5. Product workflow.
6. Trust and verification model.
7. Privacy and safe-reporting model.
8. Low-bandwidth, language, and accessibility design.
9. Working proof-of-concept screenshots.
10. Technical architecture and AI usage.
11. Pilot scope and early validation plan.
12. Scalability across local governments and countries.
13. Limitations and responsible next steps.
14. Closing impact statement.

## 24. Written-summary outline

### Track

State that the project is cross-track, combining Transparency & Accountability with Safety, Reporting & Protection.

### Community problem

Describe the selected pilot community and the specific difficulty people face when trying to verify local project promises or report concerns.

### Solution

Explain the project registry, source-backed project pages, grounded explanations, private reports, tracking codes, and human review.

### Information sources

List the official and credible independent sources used, how each was checked, how update dates are displayed, and how Source Scout discovers additional public information without automatically verifying it.

### Trust and accuracy

Explain source labels, verification states, citation requirements, insufficient-evidence behaviour, discovery-result labelling, contradiction handling, and human review.

### Safety and privacy

Explain anonymous-first reporting, separated contact information, attachment sanitisation, private-by-default reports, safe-query generation, external-search data minimisation, and controlled public summaries.

### AI tools

Separate user-facing AI from AI coding assistance. State that the core idea came from the developer's selected community problem. Explain how AI coding tools supported implementation, testing, debugging, documentation, and review.

### Scalability

Explain that each new location can provide a source registry, local institution directory, language pack, project dataset, and escalation pathways while keeping the core platform unchanged.

## 25. Judging alignment

### Uniqueness

The project connects three activities that are usually separated: understanding official project information, contributing protected community evidence, and following a human-reviewed accountability trail. Its distinction should come from the specific local workflow and trust model, not from making unsupported “first” or “only” claims.

### Scalability

The platform is location-configurable. Project categories, authorities, languages, sources, and escalation routes can change without rebuilding the core application.

### AI coding usage

The AI build log, test coverage, architecture decisions, code-review history, and clear explanation of what the developer accepted or changed will demonstrate meaningful usage.

### Presentation

Use one coherent scenario across the application, video, deck, README, and summary. Every claim in the presentation should be visible in the working proof of concept.

## 26. Key risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Unverified accusations cause harm | Keep reports private; require human review; publish only neutral, evidence-backed summaries. |
| Reporter identity is exposed | Anonymous-first design, separated optional contact data, metadata stripping, minimal logs, and access controls. |
| Official information is outdated | Display publication and last-checked dates; mark stale or unavailable sources. |
| AI invents an answer | Retrieval limited to approved sources, mandatory citations, and explicit insufficient-evidence responses. |
| Public-web discovery repeats a false allegation | Label results as unverified, distinguish reported claims from supported facts, require citations, and require human review before publication. |
| Search queries expose a reporter | Generate reduced privacy-safe queries, show them before incident searches, and never send private fields or attachments externally. |
| A malicious page attempts prompt injection | Treat retrieved text as untrusted data, isolate it from instructions, use structured extraction, and prohibit tool or publication actions from page content. |
| The fetcher accesses an unsafe internal address | Allow only public HTTP/HTTPS destinations and block private, loopback, link-local, and metadata-service networks. |
| Scope becomes too large | One pilot locality, five to eight projects, and five complete user journeys, with Source Scout limited to ten results per run in the proof of concept. |
| Demo depends on live third-party sites | Store permitted excerpts and metadata locally while linking to the original source. |
| Poor connectivity breaks reporting | Small payloads, retry states, progress feedback, and local draft support with a shared-device warning. |
| The prototype is mistaken for an emergency service | Prominent disclaimer and direct referral to appropriate official emergency or support channels. |

## 27. Definition of done

The proof of concept is ready to submit when:

- the public GitHub repository can be opened by judges;
- setup instructions work from a clean environment;
- at least five projects have traceable public sources;
- the end-to-end public project journey works;
- the AI answers only from project sources and cites them;
- Source Scout can find a small set of public results, preserve provenance, remove duplicates, and create a cited summary;
- Source Scout identifies missing or conflicting information and asks relevant follow-up questions;
- incident-related search queries are privacy-safe, previewed, and reviewer-controlled;
- an anonymous fictional report can be submitted;
- report status can be checked with a tracking code;
- an authorised reviewer can process the report;
- no private report data is exposed publicly;
- mobile, accessibility, low-data, and failure states have been tested;
- the demo video, PDF deck, and written summary are complete; and
- every public link has been tested before 21 September 2026 at 23:59 UTC.

## 28. Master instruction for an AI coding agent

Use the following after selecting the pilot location and collecting the seed sources:

> Build a polished hackathon proof of concept for ShaidaGo, a low-bandwidth platform that helps residents understand and monitor local government projects and safely report concerns. Use the tagline “Track promises. Verify progress. Take action.” Follow `PRODUCT.md`, this brief, and `docs/IMPLEMENTATION_PLAN.md` in the precedence documented by `AGENTS.md`. Use a strict TypeScript Next.js frontend and browser-facing BFF; use FastAPI, Pydantic, PostgreSQL, and a Python worker for the separate domain backend. Generate the browser client from the backend OpenAPI contract instead of duplicating types. Prioritise five complete flows: browse a project, verify its sources, ask a grounded source-linked question, submit and review a protected report, and use Source Scout to discover related public information. Source Scout must create a privacy-safe query, search only permitted public sources, preserve provenance, remove duplicates, label results as unverified, produce a neutral cited summary, identify contradictions and information gaps, and ask up to five targeted follow-up questions. Never send reporter identities, contact data, private attachments, tracking codes, internal notes, or unnecessary precise locations to an external search provider. Treat retrieved web content as untrusted input, defend against unsafe URLs and prompt injection, and require human review before discovered information changes any public status. Keep reports private by default, make anonymous reporting available without an account, strip image metadata, separate optional contact details, use secure random tracking codes, and never expose reports to the public AI retrieval layer. The AI question-answering feature must use only approved project sources, include citations, and return an explicit insufficient-evidence response when the sources do not support an answer. Make the application mobile-first, accessible, useful on unreliable connections, and complete in English, Hausa, Igbo, and Yoruba. Seed it with five to eight cited projects across AMAC and Bwari and fictional reporting data. Do not add unrelated features or make accusations not supported by sources. Include tests, `.env.example`, seed instructions, an AI build log, and a README that a judge can follow from a clean environment. Work in small, verifiable milestones and run relevant tests after each milestone.

---

## Final positioning statement

ShaidaGo helps communities move from rumours and scattered documents to evidence, understanding, and safer action. It makes local government project information easier to verify, gives residents a protected way to contribute what they observe, and creates a transparent human-reviewed path from report to public accountability: **Track promises. Verify progress. Take action.**

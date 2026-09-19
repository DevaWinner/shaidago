# ADR-0008: Provider isolation, replay fixtures, and live-test policy

- **Status:** accepted
- **Date:** 2026-09-19
- **Task:** BE-004
- **Supersedes:** none
- **Amended by:** [ADR-0009](0009-groq-as-the-language-provider.md), which replaces OpenAI with Groq as the live language provider and moves embeddings behind their own optional key. Every other decision here still applies.

## Context

ShaidaGo depends on external services: OpenAI for answers, analysis, and embeddings; Brave for search; public web pages; Cloudflare R2 for storage; and ClamAV for scanning. Judges must be able to run and verify the repository without credentials. CI must be deterministic. Provider outages must degrade only the affected feature. Recorded responses must never be presented as live results.

## Decision

1. **Interfaces.** Each external capability sits behind a typed `Protocol` in the owning module:

   | Interface | Module | Live adapter | Fixture adapter |
   | --- | --- | --- | --- |
   | `LanguageModel` | `retrieval` / `discovery` | OpenAI Responses API | Recorded structured outputs keyed by request fingerprint |
   | `EmbeddingModel` | `retrieval` | OpenAI embeddings | Checked-in vectors in `data/embeddings/`, keyed by chunk hash |
   | `SearchProvider` | `discovery` | Brave Search API | Recorded result sets in `data/discovery-fixtures/` |
   | `PageFetcher` | `discovery` | SSRF-safe HTTP fetcher | Recorded pages served from fixtures |
   | `ObjectStore` | `files` | S3 API (R2 or MinIO) | In-memory store |
   | `MalwareScanner` | `files` | clamd | Deterministic verdicts, including EICAR |

2. **Selection.** `PROVIDER_MODE` is `live` or `replay`. `replay` is the default in development and test and is used when a live credential is missing outside production. Production requires `live` for search, language, and storage.
3. **Honest labelling.** Any response built from replay data carries `demo_replay: true` in its API contract, and the UI shows "demo replay". A replay result is never labelled as a live search or live answer.
4. **Adapter responsibilities.** Every adapter defines timeout, retry classification (retryable, non-retryable, policy failure), result caps, and byte limits. Policy or validation failures are never retried. Adapters never log prompts, source text, or credentials.
5. **Model IDs and budgets** come from configuration, never from domain code.
6. **Tests have no network.** The test suite blocks outbound sockets except to local service containers. Live tests are marked `live`, skipped unless `SHAIDAGO_LIVE_TESTS=1` and the needed credential are set, and never run in required CI checks.
7. **Live evidence.** Before submission, at least one live Q&A and one live public Source Scout run are executed. Only safe evidence is kept: timestamp, model and prompt versions, counts, and reviewed public URLs.
8. **Fixture hygiene.** Fixtures contain only public or synthetic data, are sanitised of provider identifiers and credentials, and carry a `fixture_version`. Updating a fixture is a reviewed change.

## Alternatives considered

| Alternative | Reason rejected |
| --- | --- |
| Call providers directly from domain code | Untestable without credentials; outages spread into unrelated code. |
| HTTP-level recording (VCR cassettes) | Records raw requests that can contain prompts or keys, and couples tests to wire formats. |
| Mocks written per test | Inconsistent behaviour across tests; replay adapters give one realistic fake per provider. |
| Require credentials for judges | Makes the repository unverifiable for anyone without paid accounts. |

## Consequences

- `make verify` passes from a clean clone with no credentials.
- Provider outages surface as a feature-level retryable state; project browsing and reporting stay up.
- Replay data can go stale against the live provider; the opt-in live run before submission catches that.

## Migration impact

Switching provider (for example, a different search API) means a new live adapter and new fixtures behind the same interface; domain code and contracts do not change.

## Enforcement

| Control | Owning task | Planned verification |
| --- | --- | --- |
| Adapter timeouts, caps, retry classes | BE-082, BE-092 | Adapter tests for timeout, rate limit, invalid output, and oversized response. |
| Replay labelled in contract | BE-097 | Contract test asserts `demo_replay` on every replay-derived response. |
| No network in tests | BE-010, BE-012 | Socket-block fixture; a test that attempts a live call fails. |
| Production refuses replay | BE-020 | Settings test for `APP_ENV=production` with `PROVIDER_MODE=replay`. |
| Keyword fallback without embeddings | BE-081 | Test without an OpenAI key returns `retrieval_mode: "keyword"`. |
| Live evidence recorded safely | BE-097 | Checked-in live-run record contains no secret, prompt, or private value. |

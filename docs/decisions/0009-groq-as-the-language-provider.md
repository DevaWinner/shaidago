# ADR-0009: Groq as the language provider, and embeddings as a separate optional key

- **Status:** accepted
- **Date:** 2026-09-19
- **Task:** BE-004
- **Supersedes:** the provider choice in [ADR-0008](0008-provider-isolation-replay-fixtures-and-live-tests.md); everything else in ADR-0008 (interfaces, replay fixtures, honest labelling, live-test policy) still stands

## Context

ADR-0008 named the OpenAI Responses API as the live language provider. The maintainer has a Groq key and no OpenAI key, so the live path the repository documented could not be exercised: BE-097's live discovery evidence and BE-085's live evaluation both stayed pending for want of a credential. Groq serves an OpenAI-compatible Chat Completions API with strict `json_schema` response formats on the `openai/gpt-oss-*` models, which is what the grounded-answer and discovery-analysis schemas need.

Groq serves no embedding model. The corpus pipeline is hybrid (PostgreSQL full-text plus pgvector), and it already degrades honestly to keyword-only when no embedding vector exists.

## Decision

1. **Groq replaces OpenAI as the language provider.** `GroqLanguageModel` (`retrieval/groq.py`) is the only live language transport. `retrieval/openai.py` is deleted rather than kept as dead code; the Responses-API shape is recoverable from git history if it is ever needed again.
2. **One transport, two models.** The transport takes a `StructuredCall` (schema name, schema, instructions, payload, token cap, optional model override), so grounded Q&A and the discovery analyser share one HTTP client and one failure classifier. `LiveAnalyser` replaces `OpenAIAnalyser`.
3. **Defaults:** `GROQ_QA_MODEL=openai/gpt-oss-20b` for short answers and explanations, `GROQ_DISCOVERY_MODEL=openai/gpt-oss-120b` for discovery synthesis, both overridable, with `GROQ_BASE_URL` configurable for a compatible endpoint. `GROQ_API_KEY` replaces `OPENAI_API_KEY` in live mode and in the redaction denylist.
4. **Request shape keeps every control ADR-0008 required:** strict JSON schema, no `tools` key at all, `temperature: 0` for deterministic decoding, a bounded token cap, a bounded response body, and no prompt or upstream body in any exception. A refusal, a tool call, or a truncated (`finish_reason: length`) answer is classified and fails closed; only timeouts, transport errors, 408/409/429 and 5xx are retryable.
5. **Embeddings move behind their own optional key.** `EMBEDDING_API_KEY`, `EMBEDDING_BASE_URL`, and `EMBEDDING_MODEL` drive `make embeddings`, which stays an explicit, credentialed command. Without that key the seed loads checked-in vectors when they match, and retrieval runs keyword-only and reports `retrieval_mode: "keyword"`. Live mode does not require an embedding key.
6. **Groq is not treated as more trustworthy than OpenAI was.** Output is still untrusted: the deterministic citation and safety validator (BE-083) and the discovery analysis validator (BE-095) decide what reaches a person, and an invalid analysis still becomes `needs_review`.

## Alternatives considered

| Alternative | Reason rejected |
| --- | --- |
| Keep OpenAI and ask the maintainer to buy a key | Leaves the live evidence items open for a credential the project does not have. |
| Gemini as the language provider | Its native API is not OpenAI-shaped, so it needs a different request and response mapping; Groq's compatibility layer reuses the existing strict-schema plumbing. Gemini remains a candidate for embeddings. |
| Keep both adapters behind a provider switch | Two live paths, one of them untestable here, and twice the failure-classification surface to keep correct. |
| Drop embeddings entirely | Hybrid retrieval is already built and tested; keeping the optional key preserves it without requiring a credential. |
| Use Gemini for embeddings now | Another live adapter and fixture set, for a quality gain the pilot corpus does not need. Recorded as the next step instead. |

## Consequences

- The live language path is exercisable with the credential the project actually has, which is what closes BE-097's and BE-085's live items.
- Hybrid retrieval runs keyword-only in live mode unless an OpenAI-compatible embedding key is supplied. The API says so in `retrieval_mode`, and the Circle 8 gate already treats keyword mode as honest.
- Model identifiers change in stored analysis rows and evaluation records. Older rows keep the model they were produced with, which is why the column exists.
- A Groq outage degrades Q&A and discovery only. Project browsing, reporting, tracking, and review are unaffected.

## Migration impact

No schema change. `.env.example`, the Railway staging variables, and the deployment runbook change key names; a deployment that still sets `OPENAI_API_KEY` with `PROVIDER_MODE=live` now fails startup validation with `GROQ_API_KEY: required when PROVIDER_MODE=live`, which is the intended loud failure.

## Enforcement

| Control | Owning task | Planned verification |
| --- | --- | --- |
| Strict schema, no tools, deterministic decoding | BE-082, BE-095 | Adapter and analyser tests assert the exact request body, including that no `tools` key is sent. |
| Failure classification without leaking bodies | BE-082 | Retryable, non-retryable, policy-failure, timeout, truncation and oversized-body tests with upstream canaries. |
| Live mode requires the Groq key | BE-020 | Settings test asserts `GROQ_API_KEY: required when PROVIDER_MODE=live`. |
| Key never logged | BE-023 | Redaction denylist covers `GROQ_API_KEY` and `EMBEDDING_API_KEY`; canary tests run over logs and exceptions. |
| Keyword fallback stays honest | BE-081 | Test without an embedding key returns `retrieval_mode: "keyword"`. |
| Live evidence records only safe fields | BE-097, BE-085 | Checked-in live records contain model, prompt and schema versions, counts and public URLs, and no prompt or key. |

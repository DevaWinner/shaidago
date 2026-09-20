# ADR-0010: Local embeddings with FastEmbed and multilingual-e5-large

- **Status:** accepted
- **Date:** 2026-09-20
- **Task:** BE-004
- **Supersedes:** the embedding part of [ADR-0009](0009-groq-as-the-language-provider.md) (an optional OpenAI-compatible embeddings key). Everything else in ADR-0009 and ADR-0008 still applies.

## Context

ADR-0009 left embeddings behind an optional key for an OpenAI-compatible endpoint, because Groq serves no embedding model. Two things were found while replacing that:

1. **The live Q&A endpoint never embedded a question.** `ProjectQuestionService` called `Retriever.search` without a `query_embedding`, so retrieval in the running API was always keyword-only. Hybrid retrieval existed and was tested, but only with synthetic vectors in tests. There was no code path that produced a real query vector, whatever provider was configured.
2. **Keyword search cannot serve Hausa, Igbo or Yoruba.** The source passages are English. A question in another language becomes an OR of its own words matched against English text, and retrieves nothing unless it happens to contain a shared proper noun such as a place name.

A local model removes the provider key, the per-request cost, and the fact that every question would otherwise leave the server to be embedded. FastEmbed runs ONNX models in-process on a CPU, with no PyTorch.

## Decision

1. **FastEmbed with `intfloat/multilingual-e5-large`** (1024 dimensions), in-process. No provider key, no network at run time, no cost per request. A question is embedded on the server that received it and goes nowhere else.
2. **The model is fixed, not configurable.** The vector column, the checked-in vectors and the adapter must all agree on one width, so the model id and dimension are constants (`retrieval/local_embeddings.py`, `retrieval/search.py`). Migration `0027_embedding_1024` changes the column from `vector(1536)` to `vector(1024)`, clears the old vectors (a different model's vectors cannot be compared with these), and rebuilds the HNSW index and the public view. Downgrade restores the width and leaves the vectors cleared.
3. **Off by default.** `EMBEDDING_BACKEND` is `off` or `fastembed`; `fastembed` needs `EMBEDDING_MODEL_PATH`. Anyone can run and verify the repository without a 2.2 GB download, and retrieval then reports `retrieval_mode: "keyword"`.
4. **Optional at run time, never a reason to fail.** If the model cannot be loaded the API still starts, readiness reports a non-required `embedding` component as degraded, and every question falls back to keyword retrieval. Any per-request failure (not loaded, busy, timed out, malformed vector) is caught in the question service and falls back the same way. The answer states which mode ran.
5. **Inference never blocks the event loop.** It runs on a dedicated two-thread pool with a hard cap of eight queued or running calls, refusing further work as "busy" instead of building a backlog. A timed-out call keeps counting against the cap until its thread actually finishes. The question is embedded *before* the database session opens, so a slow inference never holds a connection.
6. **Vectors are L2-normalised and validated.** The raw model output is not unit length (norm about 28). Wrong width, non-finite values, out-of-range values and zero vectors are refused.
7. **Stored vectors are generated explicitly and checked in.** `make embeddings` embeds the approved public chunks with the local model and writes `data/embeddings/intfloat__multilingual-e5-large.jsonl`, keyed by the SHA-256 of each chunk's exact text. `make seed-demo` loads that file and needs no model. A changed chunk has no vector until the command is run again, and retrieval degrades to keyword for it rather than guessing.
8. **The download is pinned and verified.** `make embedding-model` fetches one exact Hugging Face revision of `qdrant/multilingual-e5-large-onnx` (Apache-2.0; the original weights are MIT) as real files and refuses to finish unless all six files match SHA-256 pins recorded in the code. Real files matter: ONNX Runtime 1.30 rejects the symlinked layout of the default Hugging Face cache ("External data path escapes model directory"). A symlink is treated as an integrity failure.
9. **Baked into the API image only.** The Dockerfile takes `WITH_EMBEDDING_MODEL=1` to include the model; the default is an empty directory, so the worker and migration job share the same image without carrying 2.2 GB. The image sets `HF_HUB_OFFLINE=1`.
10. **ONNX Runtime telemetry is switched off.** It logs "Failed to persist telemetry device ID" at load. Nothing here needs it and `AGENTS.md` forbids undocumented telemetry, so the loader calls `onnxruntime.disable_telemetry_events()` before creating the model, and a test locks that together with `local_files_only=True`. This was not an audit of ONNX Runtime's source; the offline container run is the evidence that nothing is required from the network.
11. **`fastembed` is pinned `>=0.8,<0.9`.** FastEmbed changed this model's pooling from CLS to mean between releases (it warns at load). Mean pooling is what e5 is trained with, so 0.8 is correct, but the vectors depend on the library version, so the range is pinned and the checked-in file must be regenerated if it ever changes.

## What was measured

Cross-lingual retrieval, using the maintainer-reviewed questions in `data/qa-evaluation/golden-v1.json`. Each question should rank its English answer first among 12 documents (the answers plus real seeded passages as distractors). Top-1 hits out of 3:

| Retrieval | English | Hausa | Igbo | Yoruba |
| --- | --- | --- | --- | --- |
| Keyword (previous behaviour) | 3 | 0 | 0 | 0 |
| `paraphrase-multilingual-MiniLM-L12-v2` (0.22 GB) | 3 | 0 | 0 | 0 |
| `paraphrase-multilingual-mpnet-base-v2` (1.0 GB) | 3 | 0 | 0 | 0 |
| **`multilingual-e5-large` (2.2 GB)** | 3 | **2** | **2** | **1** |

Against real project chunks, with questions that name no place: for Hausa, Yoruba and Igbo, keyword retrieval returned **0 chunks** and hybrid retrieval returned the project's passages, so the language model gets evidence to answer from. Measured cost on a development laptop: peak 1.75 GB of RAM, about 15 ms per query, model load 1 to 2 seconds. Measured in the built image, as the unprivileged user with `--network none` and two threads: load 3.3 s, first query 61 ms, and a **peak container memory of 2.12 GB** (page cache included).

## Limits, stated plainly

- **The sample is tiny** (three questions per language). It shows direction, not precision. Yoruba at 1 of 3 is weak.
- **The claim is better recall, not better ranking.** Each project has one to two chunks, so which chunk ranks first is not a meaningful signal yet.
- **Semantic search always returns nearest neighbours.** There is no similarity floor, so an off-topic question still sends the project's passages to the language model. The deterministic citation validator and the insufficient-evidence fallback are what stop an unsupported answer, exactly as before. A similarity threshold is a sensible next step but needs more data than exists.
- **The `query:`/`passage:` prefixes changed no score on this sample.** They are kept because the model card says the model is trained with them, not because the probe proves it.
- **When a question already names a project or place, keyword search already works** in every language. The benefit is for questions that do not.
- **Replay fixtures were recorded under keyword retrieval.** Enabling embeddings in `PROVIDER_MODE=replay` can change which passages, or their order, reach the recorded request, so a replayed answer may fall back honestly instead of matching.
- **The API service needs at least 3 GB of memory, and the hosted plan is unverified.** In a Docker VM with 4 GB total and about 2.4 GB already in use, the process was killed (exit 137) until memory was freed. Request latency on Railway's shared CPUs has not been measured; the 15 ms and 61 ms figures are from a laptop and a local container.
- **Hausa, Igbo and Yoruba questions in the informal check were written by the assistant and are unreviewed.** The reviewed evidence is the golden corpus probe.

## Alternatives considered

| Alternative | Reason rejected |
| --- | --- |
| An OpenAI-compatible embeddings API (ADR-0009's optional key) | Costs money per request, needs a credential nobody here has, and sends every question to a third party to be embedded. |
| `paraphrase-multilingual-MiniLM-L12-v2` or `-mpnet-base-v2` | Small and fast, but they were not trained on Hausa, Igbo or Yoruba and measured 0 of 3, no better than keyword search. |
| `jina-embeddings-v3` (2.29 GB) | Not evaluated. Its quality depends on task-specific adapters that FastEmbed's plain interface may not select, and it is the same size as the model chosen. |
| Translating the question to English with the language model, then keyword search | Sends the question to a provider on every request and adds a model call, latency and failure mode. Not measured; still a candidate if embeddings prove too heavy to host. |
| Keep keyword-only retrieval | Zero recall for non-English questions that name nothing shared. |
| Make the model id and dimension configurable | The column width is a hard constraint; a configurable model invites a silent mismatch. |

## Consequences

- Hybrid retrieval finally runs in the live path, and costs nothing per question.
- The API image grows by about 2.2 GB when built with the model, and the first build downloads it (about five minutes on an unauthenticated connection).
- The API needs roughly 2 GB of memory more than before when the model is on.
- The privacy story improves: embedding a question involves no third party. The threat model's AI-provider allowlist is unchanged, because nothing new is sent to one.
- `make embeddings` no longer needs a key, so it can be run by anyone with the model downloaded.

## Migration impact

`0027_embedding_1024` clears stored vectors, which is safe because they are derived data regenerable with `make embeddings`. The environment variables `EMBEDDING_API_KEY`, `EMBEDDING_BASE_URL` and `EMBEDDING_MODEL`, introduced by ADR-0009 the day before, are removed rather than deprecated; nothing had deployed them. Deployments that want hybrid retrieval set `EMBEDDING_BACKEND=fastembed` on a service built with `WITH_EMBEDDING_MODEL=1`.

## Enforcement

| Control | Owning task | Planned verification |
| --- | --- | --- |
| Vector width, normalisation and refusal of unusable vectors | BE-081 | Unit tests refuse wrong size, NaN, infinity, out-of-range and zero vectors; the checked-in file is asserted 1024-wide and unit length. |
| Never blocks, never unbounded | BE-081, BE-103 | Tests for timeout that still counts against the cap, and a burst beyond eight refused as busy. |
| A missing or broken model never stops the API or a question | BE-081, BE-025 | Load-failure test degrades without raising or logging the message; four failure codes fall back to keyword and still answer. |
| Only the screened question is embedded, locally | BE-084 | Integration test asserts the embedder received exactly the normalised question. |
| Download integrity | BE-110 | Tests refuse a missing file, a tampered file and a symlink; the pins are 64-hex digests and the revision is a 40-character commit. |
| Migration width change | BE-033 | Round trip tested with a real 1536-wide vector present: cleared, retyped, index and view rebuilt, downgrade restores. |
| Cross-lingual quality has not regressed | BE-085 | Opt-in test on the real model (skipped without it) asserts the measured minimum per language. |
| The API image carries the model and stays offline | BE-110 | Built with `WITH_EMBEDDING_MODEL=1` (4.3 GB) and run as uid 10001 with `--network none` and `HF_HUB_OFFLINE=1`: loads, embeds, and cannot reach the network. |
| Telemetry off, loads never download | BE-081 | Unit test asserts `disable_telemetry_events` runs before the model is built and that `local_files_only` is true. |

# BE-081 local embeddings evidence

**Status: complete.** Hybrid retrieval runs in the live question path, with embeddings computed locally. The decision, alternatives and limits are in [ADR-0010](../decisions/0010-local-embeddings-with-fastembed.md); this is the evidence and how to reproduce it.

## What was found

Before this work, `ProjectQuestionService` called the retriever without a query embedding, so the running API was always keyword-only. Hybrid retrieval existed and was tested, but only with synthetic vectors. Keyword search also retrieves nothing for a Hausa, Igbo or Yoruba question that shares no place name with the English source text.

## Model comparison

Cross-lingual retrieval on the maintainer-reviewed questions in `data/qa-evaluation/golden-v1.json`: each question should rank its English answer first among 12 documents (the answers plus real seeded passages as distractors). Top-1 hits out of 3, and memory after loading measured in a fresh process:

| Retrieval | English | Hausa | Igbo | Yoruba | Memory after load | Fits the hosted 1 GB limit |
| --- | --- | --- | --- | --- | --- | --- |
| Keyword search | 3 | 0 | 0 | 0 | none | yes |
| `paraphrase-multilingual-MiniLM-L12-v2` | 3 | 0 | 0 | 0 | not measured | not measured |
| `paraphrase-multilingual-mpnet-base-v2` | 3 | 0 | 0 | 0 | not measured | not measured |
| `multilingual-e5-large` (fp32, 2.2 GB) | 3 | 2 | 2 | 1 | 1.4 GB (peak 1.75) | no |
| `multilingual-e5-base` (int8, 279 MB) | 3 | 2 | 2 | 3 | 0.92 GB (peak 1.12) | no |
| **`multilingual-e5-small` (int8, 118 MB)** | 3 | 2 | 2 | 1 | 0.64 GB (peak 0.87) | yes |

Three questions per language is a small sample. It shows direction, not precision, and cannot separate the small model from the large one. The base model's 3 of 3 on Yoruba may be real or luck.

## Verified in the built image

Run as uid 10001, `--network none --memory 1g`, two threads, 200 queries in 25 bursts of 8 concurrent questions:

- model loaded from disk in 0.6 s with `HF_HUB_OFFLINE=1`; no symlinks in the model directory;
- burst median 16 ms, worst 18 ms; vectors 384-wide and unit length;
- **peak container memory 0.53 GB** of the 1.00 GB limit; the network was confirmed unreachable;
- image size 930 MB (4.3 GB with the large model).

## Verified on the hosted platform

Railway staging (Linux x86, so the int8 file, which its publisher quantised for AVX512-VNNI CPUs, is genuinely exercised):

- `/health/ready` reports `ready` with `embedding: ok`;
- questions with no place name, in English, Hausa, Yoruba and Igbo, all ran with `retrieval: {"mode": "hybrid", "chunks_considered": 2}` and took about 0.9 to 1.0 s end to end from a laptop;
- the `api` service settled at about 660 MB and peaked at 849 MB of its 1,024 MB limit.

The first attempt, with the 2.2 GB model, was killed for memory in a restart loop on the same service. That failure is why the small model is used.

## Reproduce it

```text
make embedding-model          # downloads the 129 MB model; every file is checked against a pinned SHA-256
make embeddings               # regenerates data/embeddings/intfloat__multilingual-e5-small.jsonl
EMBEDDING_BACKEND=fastembed   # in .env, then start the API; /health/ready shows the embedding component
```

The quality guard is `services/platform/tests/evaluation/test_local_embedding_quality.py`. It runs the production adapter on the real model, skips when the model is not downloaded, and asserts the measured minimum per language (3, 2, 2, 1). It catches a gross regression only: removing the `query:`/`passage:` prefixes changed no score on this sample.

## Limits

- A tiny sample; Yoruba at 1 of 3 is weak.
- The claim is better recall, not better ranking: each project has one to two chunks.
- Semantic search returns nearest neighbours whatever the question, so an off-topic question still sends the project's passages to the language model. The citation validator and the insufficient-evidence fallback are what stop an unsupported answer.
- Replay fixtures were recorded under keyword retrieval, so enabling embeddings in replay mode can make a replayed answer fall back instead of matching.
- Memory headroom on the hosted service is 17% at peak.
- The Hausa, Igbo and Yoruba questions in the informal side check were written by the assistant and are unreviewed. The reviewed evidence is the golden corpus probe.

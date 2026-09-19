# BE-085 language review and live evaluation evidence

**Status: complete, with a measured model-quality limitation.** The four locale review records are filled in, and the opt-in live evaluation has been run against the real provider. Nothing here claims an independent review.

## Human language review

| Field | Value |
| --- | --- |
| Reviewer | Aniekan Winner Anietie, maintainer |
| Review date | 2026-09-19 |
| Locales reviewed | `en`, `ha`, `ig`, `yo` |
| Dimensions recorded | meaning, names, amounts, dates, uncertainty, safety wording — each `preserved` |
| Record | `data/qa-evaluation/golden-v1.json`, `human_reviews` |

The maintainer states they are fluent in the pilot languages and reviewed all four locale packs themselves. The record names them as the reviewer and describes the review as self-reported. It is not an independent review by a second fluent speaker, and the repository does not claim one. If an independent reviewer is engaged later, add a second record rather than overwriting this one.

## Live evaluation over the golden corpus

Run with `uv run python -m shaidago.retrieval.evaluation --live --model <model> --output <file>` on 2026-09-19, after the maintainer authorised live provider spend.

| Model | Cases attempted | Passed | `answered` where the corpus expects a refusal or fallback | `fallback` | `provider_unavailable` (rate limited) |
| --- | --- | --- | --- | --- | --- |
| `openai/gpt-oss-20b` | 36 | 4 | 7 | 4 | 25 |
| `openai/gpt-oss-120b` | 36 | 6 | 7 | 4 | 25 |

Corpus version, prompt version and schema version were unchanged (`grounded-qa-v1`, `grounded-answer-v2`). Only case identifiers, outcomes and version strings are recorded; no question, passage, answer or key is stored.

### What this means

- **The live provider integration works.** Requests are accepted, the strict schema is honoured, and answers parse.
- **The models are weaker than the corpus expects.** Of the eleven cases that were not rate limited, roughly half failed. The important failures are the cases where the model answered although the corpus expects an explicit insufficient-evidence response. In production those answers still pass through the deterministic citation and safety validator, which is what actually protects the public record, but the model itself is not reliably fail-closed.
- **Groq's free tier rate-limits hard.** 25 of 36 cases returned `provider_unavailable` in both runs. A full live pass needs a paid tier or a slow, throttled run.

### Consequence for the demo

The deterministic evaluation (44/44 cases, 28/28 citation checks, 44/44 policy checks against recorded outputs) remains the gate, and the demo keeps `PROVIDER_MODE=replay` so answers are reproducible and labelled `demo replay`. Live mode is proven to work but is not the demo default, and this file is the reason.

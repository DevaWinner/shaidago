# Grounded Q&A evaluation corpus

`golden-v1.json` is a synthetic, versioned test corpus. Its locale text is machine-assisted draft
copy, not public content and not a reviewed translation pack. The deterministic harness expands
every scenario across English, Hausa, Igbo, and Yoruba and scores citation and policy behaviour.

Human review is intentionally separate. A fluent reviewer must update only the corresponding
locale review record after checking meaning, names, amounts, dates, uncertainty, and safety
wording. Do not change `status` to `reviewed` without the reviewer name, review date, and all six
dimensions marked `preserved` (or `issue` where correction is needed).

Deterministic CI runs `python -m shaidago.retrieval.evaluation`; it never reads a provider key or
contacts a network service. A live run is deliberately opt-in and must name its model and a local
result path: `python -m shaidago.retrieval.evaluation --live --model MODEL --output RESULT.json`.
It requires `OPENAI_API_KEY`, records only case IDs, outcomes, and model/prompt/schema versions,
and never writes questions, passages, responses, or the key. Do not run it without explicit
maintainer authorisation.

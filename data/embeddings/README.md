# Checked-in embedding vectors

Files are JSON Lines keyed by the SHA-256 hash of the exact approved chunk text. Ordinary seed and
request paths load these files but never contact a provider, and loading needs no model.

Vectors come from a local model, not a provider (ADR-0010): FastEmbed with
`intfloat/multilingual-e5-small` (int8), 384 dimensions, unit length. The checked-in file for it is
`intfloat__multilingual-e5-small.jsonl` (a Hugging Face id's `/` becomes `__`). Regenerate it with:

```text
make embedding-model   # once: downloads the 129 MB model, pinned to one revision and SHA-256 verified
make embeddings        # embeds every approved public chunk locally; no key, no network
```

A chunk whose text changes has no vector until `make embeddings` is run again, and retrieval
honestly falls back to keyword mode for it. The vectors depend on the FastEmbed version (it changed
this model's pooling between releases), so `fastembed` is pinned and this file must be regenerated
if that pin ever moves.

`fixture-hash-v1.jsonl` is a deterministic synthetic 384-dimension vector for the synthetic
integration-test document. It proves the offline loader and hybrid ranker without pretending to be
a real model's vector or describing a real project.

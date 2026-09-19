# Checked-in embedding fixtures

Files are JSON Lines keyed by the SHA-256 hash of the exact approved chunk text. Ordinary seed
and request paths may load these files but never contact a provider. `make embeddings` is the
only provider-backed generation workflow and requires an explicit OpenAI key.

`fixture-hash-v1.jsonl` is a deterministic synthetic 1,536-dimension vector for the synthetic
integration-test document. It proves the offline loader and hybrid ranker without pretending to
be an OpenAI vector or describing a real project. The current demo sources remain pending human
approval, so the default `text-embedding-3-small` file is intentionally absent and retrieval
honestly uses keyword mode until approved chunks and reviewed generated vectors exist.

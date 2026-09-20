"""Cross-lingual retrieval quality of the real local model (ADR-0010).

This is the evidence behind choosing multilingual-e5-small. It runs the production adapter on the
real model, so it needs the 129 MB download (``make embedding-model``) and is skipped without it,
the way live-provider tests are.

What it guards, and what it does not. It catches a *gross* regression: swapping in a multilingual
model that was not trained on these languages (MiniLM and mpnet score 0 of 3 on Hausa, Igbo and
Yoruba, no better than keyword search), or a library upgrade that changes the vectors enough to
lose the cross-lingual match. It
does not detect subtle mistakes: removing the ``query:``/``passage:`` prefixes changed no score on
this sample, so the prefixes are kept because the model card says the model is trained with them,
not because this test proves it.

The queries are the maintainer-reviewed questions in ``golden-v1.json``; the documents are their
English answers mixed with real seeded passages as distractors. Three questions per language is a
small sample, so the thresholds are the measured results, not a claim of precision.
"""

import json
import os
from pathlib import Path

import pytest

from shaidago.retrieval.local_embeddings import FastEmbedModel

REPOSITORY = Path(__file__).resolve().parents[4]
MODEL_PATH = Path(
    os.environ.get("EMBEDDING_MODEL_PATH", REPOSITORY / ".models" / "multilingual-e5-small")
)
GOLDEN = REPOSITORY / "data" / "qa-evaluation" / "golden-v1.json"
REGISTER = REPOSITORY / "data" / "source-register.json"

pytestmark = [
    pytest.mark.model,
    pytest.mark.skipif(
        not (MODEL_PATH / "onnx" / "model_qint8_avx512_vnni.onnx").is_file(),
        reason="the embedding model is not downloaded; run `make embedding-model`",
    ),
]

KINDS = ("date", "budget", "responsibility")
# Measured on 2026-09-19 with fastembed 0.8.0. English is exact; the others must beat the keyword
# baseline, which scores 0 of 3 in every language but English.
MINIMUM_HITS = {"en": 3, "ha": 2, "ig": 2, "yo": 1}


def _dot(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


async def test_questions_in_hausa_igbo_and_yoruba_reach_the_english_answer() -> None:
    corpus = json.loads(GOLDEN.read_text(encoding="utf-8"))
    english = corpus["locales"]["en"]
    answers = [english[f"{kind}_statement"] for kind in KINDS]
    register = json.loads(REGISTER.read_text(encoding="utf-8"))
    distractors = [
        passage["text"]
        for project in register["projects"]
        for fact in project.get("facts", [])
        for source in fact.get("sources", [])
        for passage in source.get("passages", [])
    ][:8]
    documents = [*answers, english["changed_statement"], *distractors]

    model = FastEmbedModel(MODEL_PATH, threads=4)
    await model.open()
    try:
        assert model.available, "the model directory exists but did not load"
        vectors = [tuple(v) for v in await model.embed(documents)]
        hits: dict[str, int] = {}
        for locale in MINIMUM_HITS:
            hits[locale] = 0
            for index, kind in enumerate(KINDS):
                question = corpus["locales"][locale][f"{kind}_question"]
                query = tuple(await model.embed_query(question))
                scores = [_dot(query, vector) for vector in vectors]
                hits[locale] += int(scores.index(max(scores)) == index)
    finally:
        await model.close()

    for locale, minimum in MINIMUM_HITS.items():
        assert hits[locale] >= minimum, f"{locale}: {hits[locale]}/3 (measured minimum {minimum})"

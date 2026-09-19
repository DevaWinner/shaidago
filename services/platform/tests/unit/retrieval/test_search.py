import math

import pytest

from shaidago.retrieval.search import (
    EMBEDDING_DIMENSIONS,
    MAX_QUERY_CHARS,
    normalise_query,
    vector_literal,
)


def test_query_normalisation_is_bounded_unicode_aware_and_deterministic() -> None:
    assert normalise_query("  \uff21\uff2d\uff21\uff23 road  ") == "AMAC road"
    assert normalise_query("a\u0301") == "á"


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("", "must not be empty"),
        ("   ", "must not be empty"),
        ("bad\x00query", "control characters"),
        ("x" * (MAX_QUERY_CHARS + 1), "too long"),
    ],
)
def test_query_normalisation_rejects_empty_controlled_or_oversized_input(
    value: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        normalise_query(value)


def test_vector_literal_requires_the_exact_finite_bounded_dimension() -> None:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[0] = 0.125
    assert vector_literal(vector).startswith("[0.125,0,")

    for invalid in (
        vector[:-1],
        [math.inf, *vector[1:]],
        [math.nan, *vector[1:]],
        [101.0, *vector[1:]],
    ):
        with pytest.raises(ValueError, match=r"embedding (must|contains)"):
            vector_literal(invalid)

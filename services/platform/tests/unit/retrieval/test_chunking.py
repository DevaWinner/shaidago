import hashlib

from shaidago.retrieval.chunking import MAX_CHUNK_CHARS, approximate_tokens, chunk_text


def test_empty_or_heading_only_text_has_no_evidence_chunk() -> None:
    assert chunk_text("") == []
    assert chunk_text("  \n\n  ") == []
    assert chunk_text("Short heading") == []


def test_chunks_are_exact_deterministic_slices_with_hashes_and_tokens() -> None:
    content = "  A sourced first sentence.\n\nA second sourced paragraph with ₦500.  "

    first = chunk_text(content)
    second = chunk_text(content)

    assert first == second
    assert len(first) == 1
    chunk = first[0]
    assert chunk.text == content[chunk.start : chunk.end]
    assert chunk.text_sha256 == hashlib.sha256(chunk.text.encode()).hexdigest()
    assert chunk.token_count == approximate_tokens(chunk.text)
    assert chunk.index == 0


def test_a_short_heading_labels_following_chunks_without_becoming_evidence() -> None:
    content = "Delivery record\n\nThe synthetic works began in March.\n\nThey remain under review."

    chunks = chunk_text(content)

    assert len(chunks) == 1
    assert chunks[0].section_label == "Delivery record"
    assert "Delivery record" not in chunks[0].text
    assert chunks[0].text == content[chunks[0].start : chunks[0].end]


def test_oversized_text_splits_at_sentence_then_whitespace_boundaries() -> None:
    sentence = "Evidence " * 80 + "ends here. "
    content = sentence * 4

    chunks = chunk_text(content)

    assert len(chunks) > 1
    assert all(0 < len(chunk.text) <= MAX_CHUNK_CHARS for chunk in chunks)
    assert [chunk.index for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.text == content[chunk.start : chunk.end] for chunk in chunks)


def test_a_long_unbroken_run_is_hard_split_without_losing_text() -> None:
    content = "x" * (MAX_CHUNK_CHARS * 2 + 17)

    chunks = chunk_text(content)

    assert [len(chunk.text) for chunk in chunks] == [MAX_CHUNK_CHARS, MAX_CHUNK_CHARS, 17]
    assert "".join(chunk.text for chunk in chunks) == content

"""Deterministic chunking of approved source text.

A chunk is always a contiguous slice of the source text (``text == content[start:end]``), so it
can be checked against the immutable version it came from and cited by offset. Boundaries depend
only on the text: paragraphs are packed up to a size limit, an oversized paragraph is split at
sentence ends and then at whitespace, and the same input always gives the same chunks, so an
unchanged version reprocesses to identical hashes.
"""

import hashlib
import re
from dataclasses import dataclass
from typing import Final

MAX_CHUNK_CHARS: Final = 900
MIN_CHUNK_CHARS: Final = 40
CHUNKER_VERSION: Final = "paragraph-sentence-v1"
_PARAGRAPH_BREAK: Final = re.compile(r"\n\s*\n")
_SENTENCE_END: Final = re.compile(r"(?<=[.!?])\s+")
_TOKEN: Final = re.compile(r"\w+|[^\w\s]", re.UNICODE)
_HEADING_MAX_CHARS: Final = 80


@dataclass(frozen=True)
class ChunkSpan:
    index: int
    start: int
    end: int
    text: str
    text_sha256: str
    token_count: int
    section_label: str | None


def approximate_tokens(value: str) -> int:
    """Words and punctuation marks. An approximation for budgeting, not a model tokenizer."""
    return len(_TOKEN.findall(value))


def _paragraphs(content: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    cursor = 0
    for match in _PARAGRAPH_BREAK.finditer(content):
        spans.append((cursor, match.start()))
        cursor = match.end()
    spans.append((cursor, len(content)))
    return [(s, e) for s, e in spans if content[s:e].strip()]


def _whitespace_split(content: str, start: int, end: int) -> list[tuple[int, int]]:
    """Cut an over-long run at the last space inside the limit (or hard at the limit)."""
    spans: list[tuple[int, int]] = []
    cursor = start
    while end - cursor > MAX_CHUNK_CHARS:
        cut = content.rfind(" ", cursor + 1, cursor + MAX_CHUNK_CHARS)
        cut = cursor + MAX_CHUNK_CHARS if cut <= cursor else cut + 1
        spans.append((cursor, cut))
        cursor = cut
    spans.append((cursor, end))
    return spans


def _units(content: str) -> list[tuple[int, int]]:
    """Smallest packing units: whole paragraphs, or sentences of an over-long paragraph."""
    units: list[tuple[int, int]] = []
    for start, end in _paragraphs(content):
        if end - start <= MAX_CHUNK_CHARS:
            units.append((start, end))
            continue
        cursor = start
        for match in [*_SENTENCE_END.finditer(content, start, end), None]:
            stop = end if match is None else match.end()
            if stop > cursor:
                units += _whitespace_split(content, cursor, stop)
            cursor = stop
    return units


def _packed(content: str) -> list[tuple[int, int]]:
    packed: list[tuple[int, int]] = []
    for start, end in _units(content):
        text = content[start:end].strip()
        is_heading = _is_heading(text) and len(text) < MIN_CHUNK_CHARS
        previous_is_heading = bool(packed) and _is_heading(
            content[packed[-1][0] : packed[-1][1]].strip()
        )
        if (
            packed
            and not is_heading
            and not previous_is_heading
            and end - packed[-1][0] <= MAX_CHUNK_CHARS
        ):
            packed[-1] = (packed[-1][0], end)
        else:
            packed.append((start, end))
    return packed


def _is_heading(text: str) -> bool:
    return (
        len(text) <= _HEADING_MAX_CHARS
        and "\n" not in text
        and not text.endswith((".", "!", "?", ",", ";", ":"))
    )


def chunk_text(content: str) -> list[ChunkSpan]:
    """Chunks in order. Empty or whitespace-only text has none."""
    chunks: list[ChunkSpan] = []
    heading: str | None = None
    heading_spans: set[tuple[int, int]] = set()
    for raw_start, raw_end in _paragraphs(content):
        raw = content[raw_start:raw_end]
        text = raw.strip()
        start = raw_start + (len(raw) - len(raw.lstrip()))
        if _is_heading(text) and len(text) < MIN_CHUNK_CHARS:
            heading_spans.add((start, start + len(text)))
    for raw_start, raw_end in _packed(content):
        raw = content[raw_start:raw_end]
        text = raw.strip()
        start = raw_start + (len(raw) - len(raw.lstrip()))
        if (start, start + len(text)) in heading_spans:
            heading = text  # a bare heading labels what follows; it is not evidence itself
            continue
        chunks.append(
            ChunkSpan(
                index=len(chunks),
                start=start,
                end=start + len(text),
                text=text,
                text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                token_count=approximate_tokens(text),
                section_label=heading,
            )
        )
    return chunks

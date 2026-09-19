"""Reads ``contracts/controlled-vocabulary.json``, the canonical source of machine values.

Migrations embed their own literal copies (a revision must not change after it is applied);
tests compare those literals with this file so a vocabulary change cannot pass unnoticed.
"""

import json
from functools import cache
from pathlib import Path
from typing import Any

CONTRACT = Path(__file__).parents[5] / "contracts" / "controlled-vocabulary.json"


@cache
def _document() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(CONTRACT.read_text(encoding="utf-8"))
    return loaded


def values(vocabulary: str) -> tuple[str, ...]:
    """The allowed machine values of one vocabulary, in contract order."""
    entries: list[dict[str, Any]] = _document()["vocabularies"][vocabulary]["values"]
    return tuple(str(entry["value"]) for entry in entries)

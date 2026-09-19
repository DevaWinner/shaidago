"""Reporter handle and passphrase generation: entropy source, format, and the word list."""

import hashlib
from importlib.resources import files

import pytest
from hypothesis import given
from hypothesis import strategies as st

from shaidago.reports import handles
from shaidago.reports.tracking import ALPHABET

WORDLIST_SHA256 = "addd35536511597a02fa0a9ff1e5284677b8883b83e986e43f15a3db996b903e"
RESOURCE = files("shaidago.reports").joinpath("wordlists/eff_large_wordlist.txt")


def test_the_word_list_is_the_unmodified_eff_long_list() -> None:
    raw = RESOURCE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == WORDLIST_SHA256
    lines = raw.decode().splitlines()
    assert len(lines) == 7776
    keys = [line.split("\t")[0] for line in lines]
    expected = [
        "".join(str(1 + (index // 6**place) % 6) for place in range(4, -1, -1))
        for index in range(7776)
    ]
    assert keys == expected, "dice keys 11111 to 66666 in order"
    words = handles.wordlist()
    assert len(set(words)) == 7776
    assert (words[0], words[-1]) == ("abacus", "zoom")
    assert all(word == word.lower() and word.isascii() and 3 <= len(word) <= 9 for word in words)


def test_a_handle_has_the_documented_shape_and_uses_the_alphabet() -> None:
    for _ in range(200):
        handle = handles.generate_handle()
        assert len(handle) == len("SG-H-XXXX-XXXX")
        assert handle.startswith("SG-H-")
        assert handle[9] == "-"
        assert set(handle[5:9] + handle[10:]) <= set(ALPHABET)


def test_generation_uses_the_injected_source_and_covers_the_whole_range() -> None:
    draws: list[int] = []

    def fake(limit: int) -> int:
        draws.append(limit)
        return limit - 1

    assert handles.generate_handle(fake) == "SG-H-ZZZZ-ZZZZ"
    assert draws == [32] * 8
    draws.clear()
    assert handles.generate_passphrase(fake) == " ".join(["zoom"] * 6)
    assert draws == [7776] * 6


def test_a_passphrase_is_six_listed_words_and_almost_never_repeats() -> None:
    words = set(handles.wordlist())
    seen: set[str] = set()
    for _ in range(300):
        phrase = handles.generate_passphrase()
        assert len(phrase.split(" ")) == 6
        assert set(phrase.split(" ")) <= words
        seen.add(phrase)
    assert len(seen) == 300


@given(st.lists(st.sampled_from(ALPHABET), min_size=8, max_size=8))
def test_any_handle_round_trips_through_lenient_input(symbols: list[str]) -> None:
    canonical = f"SG-H-{''.join(symbols[:4])}-{''.join(symbols[4:])}"
    for variant in (
        canonical,
        canonical.lower(),
        canonical.replace("-", " "),
        canonical.replace("-", ""),
        "".join(symbols),
        f"  {canonical}  ",
    ):
        assert handles.normalise_handle(variant) == canonical


def test_a_body_that_happens_to_start_with_the_prefix_letters_is_not_stripped() -> None:
    assert handles.normalise_handle("SGHSGHSG") == "SG-H-SGHS-GHSG"
    assert handles.normalise_handle("SGHSGHSGHXX") == "SG-H-SGHS-GHXX", "11 symbols: prefix"
    assert handles.normalise_handle("SGHSGHSGH") is None, "9 symbols is neither"


@pytest.mark.parametrize(
    "bad", ["", "SG-H-", "SG-H-ABCD", "SG-H-ABCD-EFGH-J", "SG-H-ABCU-EFGH", "é" * 8, "*" * 8]
)
def test_malformed_handles_are_none_without_an_explanation(bad: str) -> None:
    assert handles.normalise_handle(bad) is None


def test_lookalike_letters_map_like_tracking_codes() -> None:
    assert handles.normalise_handle("SG-H-OIL0-1ABC") == "SG-H-0110-1ABC"


def test_passphrase_normalisation_forgives_case_and_spacing_only() -> None:
    assert handles.normalise_passphrase("  Abacus   ABDOMEN\tzoom ") == "abacus abdomen zoom"
    assert handles.normalise_passphrase("drop-down") == "drop-down"


def test_credentials_never_show_in_repr_or_format() -> None:
    new = handles.generate()
    for rendered in (repr(new), str(new), f"{new}", repr([new])):
        assert new.handle not in rendered
        assert new.passphrase not in rendered

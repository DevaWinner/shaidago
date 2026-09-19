import itertools
import re
from collections.abc import Callable

import pytest
from hypothesis import given
from hypothesis import strategies as st

from shaidago.reports import tracking
from shaidago.reports.tracking import (
    ALPHABET,
    CodeGenerationError,
    InvalidTrackingCodeError,
    TrackingCode,
    generate,
    generate_unique,
    lookup_candidates,
    lookup_key,
    normalise,
)

FORMAT = re.compile(r"^SG-[0-9A-HJKMNP-TV-Z]{5}(-[0-9A-HJKMNP-TV-Z]{5}){3}-[0-9A-HJKMNP-TV-Z]$")
FIXED = bytes(range(1, 14))
PEPPER = b"p" * 32


def rejected(text: str) -> None:
    with pytest.raises(InvalidTrackingCodeError) as raised:
        normalise(text)
    assert text.strip() == "" or text not in str(raised.value)


def test_the_alphabet_is_crockford_base32_without_ambiguous_letters() -> None:
    assert len(ALPHABET) == 32
    assert len(set(ALPHABET)) == 32
    assert not set("ILOU") & set(ALPHABET)


def test_generation_uses_the_injected_source_exactly_once_for_thirteen_bytes() -> None:
    calls: list[int] = []

    def source(count: int) -> bytes:
        calls.append(count)
        return FIXED[:count]

    code = generate(source)
    assert calls == [13]
    assert generate(lambda n: FIXED[:n]) == code, "deterministic for a fixed source"


def test_formatted_codes_match_the_documented_shape() -> None:
    for _ in range(200):
        assert FORMAT.fullmatch(generate().formatted)


@given(st.binary(min_size=13, max_size=13))
def test_generate_format_normalise_round_trips_for_any_entropy(entropy: bytes) -> None:
    code = generate(lambda _n: entropy)
    assert normalise(code.formatted) == code
    assert normalise(code.canonical) == code


def test_only_the_top_hundred_bits_of_entropy_matter() -> None:
    assert generate(lambda _n: b"\xff" * 12 + b"\x0f") == generate(
        lambda _n: b"\xff" * 12 + b"\x00"
    )


def test_random_codes_are_distinct_at_scale() -> None:
    assert len({generate().canonical for _ in range(5000)}) == 5000


VARIANTS: list[Callable[[str], str]] = [
    str.lower,
    lambda s: s.replace("-", " "),
    lambda s: s.replace("-", ""),
    lambda s: f"  {s}  ",
    lambda s: s.replace("-", " - "),
]


@pytest.mark.parametrize("variant", VARIANTS)
def test_case_spaces_and_hyphens_are_accepted(variant: Callable[[str], str]) -> None:
    code = generate()
    assert normalise(variant(code.formatted)) == code


def test_the_prefix_is_optional_and_recognised_by_length_only() -> None:
    code = generate()
    assert normalise(code.canonical) == normalise("SG" + code.canonical) == code
    rejected("XX" + code.canonical)  # 23 symbols but not the SG prefix


def test_crockford_lookalikes_map_and_everything_else_is_rejected() -> None:
    code = generate(lambda _n: b"\x00" * 13)  # body of twenty zeros
    zeros = code.canonical
    assert zeros[:20] == "0" * 20
    assert normalise(zeros.replace("0", "O")) == code
    ones = generate(lambda _n: bytes.fromhex("08421084210842108421084210")[:13])
    assert normalise(ones.canonical.replace("1", "l")) == ones
    assert normalise(ones.canonical.replace("1", "I")) == ones
    for bad in ("U", "u", "*", "\u00e9", chr(0x661), "\x00", "@", " "):
        rejected(code.canonical[:5] + bad + code.canonical[6:])


@pytest.mark.parametrize(
    "bad", ["", "SG", "SG-", "SG-1", "x" * 22, "x" * 24, "0" * 20, "0" * 22, "SG-" + "0" * 30]
)
def test_wrong_lengths_and_empty_input_are_rejected(bad: str) -> None:
    rejected(bad)


def test_every_single_symbol_typo_is_detected() -> None:
    code = generate(lambda _n: bytes(range(50, 63)))
    text = code.canonical
    misses = 0
    for index, symbol in itertools.product(range(len(text)), ALPHABET):
        if symbol == text[index]:
            continue
        try:
            normalise(text[:index] + symbol + text[index + 1 :])
            misses += 1
        except InvalidTrackingCodeError:
            pass
    assert misses == 0


@given(
    st.binary(min_size=13, max_size=13),
    st.integers(min_value=0, max_value=19),
    st.integers(min_value=1, max_value=31),
)
def test_any_single_symbol_substitution_is_detected(entropy: bytes, index: int, shift: int) -> None:
    text = generate(lambda _n: entropy).canonical
    replacement = ALPHABET[(ALPHABET.index(text[index]) + shift) % 32]
    with pytest.raises(InvalidTrackingCodeError):
        normalise(text[:index] + replacement + text[index + 1 :])


def test_adjacent_transpositions_are_almost_always_detected() -> None:
    total = missed = 0
    for seed in range(300):
        text = generate(
            lambda _n, s=seed: bytes((s * 7 + i * 13) % 256 for i in range(13))
        ).canonical
        for i in range(len(text) - 1):
            if text[i] == text[i + 1]:
                continue
            swapped = text[:i] + text[i + 1] + text[i] + text[i + 2 :]
            total += 1
            try:
                normalise(swapped)
                missed += 1
            except InvalidTrackingCodeError:
                pass
    assert missed / total < 0.05, (
        f"Luhn mod 32 detects most transpositions ({missed}/{total} missed)"
    )


@given(st.text(max_size=60))
def test_arbitrary_text_is_either_a_valid_code_or_a_generic_rejection(text: str) -> None:
    try:
        code = normalise(text)
    except InvalidTrackingCodeError:
        return
    assert FORMAT.fullmatch(code.formatted)


def test_a_code_never_shows_itself_in_repr_str_or_f_strings() -> None:
    code = generate()
    for rendered in (
        repr(code),
        str(code),
        f"{code}",
        f"{code!r}",
        repr([code]),
        repr({"c": code}),
    ):
        assert code.canonical not in rendered
        assert code.formatted not in rendered


def test_collisions_are_retried_a_bounded_number_of_times() -> None:
    seen: list[TrackingCode] = []
    entropies = iter([bytes([1] * 13), bytes([1] * 13), bytes([2] * 13)])

    def taken(candidate: TrackingCode) -> bool:
        if not seen:
            seen.append(candidate)
            return False
        return candidate in seen

    first = generate_unique(taken, lambda _n: next(entropies))
    second = generate_unique(taken, lambda _n: next(entropies))
    assert first != second
    with pytest.raises(CodeGenerationError):
        generate_unique(lambda _c: True)


def test_lookup_keys_are_keyed_deterministic_and_reveal_nothing_about_the_code() -> None:
    code = generate()
    digest = lookup_key(PEPPER, code)
    assert digest == lookup_key(PEPPER, code)
    assert digest != lookup_key(b"q" * 32, code)
    assert digest != lookup_key(PEPPER, generate())
    assert len(digest) == 32
    assert code.canonical.encode() not in digest
    assert digest != tracking.hashlib.sha256(code.canonical.encode()).digest(), (
        "not an unkeyed hash"
    )


def test_candidates_try_the_active_pepper_first_then_retired_ones() -> None:
    code = generate()
    peppers = {"p-1": b"1" * 32, "p-2": b"2" * 32, "p-3": b"3" * 32}
    candidates = lookup_candidates(peppers, "p-2", code)
    assert [version for version, _ in candidates] == ["p-2", "p-1", "p-3"]
    assert dict(candidates)["p-1"] == lookup_key(peppers["p-1"], code)

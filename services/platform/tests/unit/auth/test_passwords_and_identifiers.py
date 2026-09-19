import pytest
from hypothesis import given
from hypothesis import strategies as st

from shaidago.auth.passwords import (
    MIN_PASSWORD_CHARS,
    PasswordPolicy,
    PasswordVerifier,
    WeakPasswordError,
    validate_new_password,
)
from shaidago.auth.reviewers import IdentifierError, normalise_identifier

# Cheap parameters keep the suite fast; production uses the defaults.
FAST = PasswordPolicy(time_cost=1, memory_cost_kib=1024, parallelism=1)
PASSWORD = "correct horse battery staple"


def test_hashes_are_argon2id_salted_and_never_contain_the_password() -> None:
    verifier = PasswordVerifier(FAST)
    first, second = verifier.hash(PASSWORD), verifier.hash(PASSWORD)
    assert first.startswith("$argon2id$")
    assert first != second
    assert PASSWORD not in first


def test_default_policy_uses_the_owasp_minimum_parameters() -> None:
    policy = PasswordPolicy()
    assert (policy.time_cost, policy.memory_cost_kib, policy.parallelism) == (2, 19_456, 1)


def test_correct_password_verifies_and_wrong_or_unknown_ones_do_not() -> None:
    verifier = PasswordVerifier(FAST)
    stored = verifier.hash(PASSWORD)
    assert verifier.verify(stored, PASSWORD).matches
    assert not verifier.verify(stored, PASSWORD + "x").matches
    assert not verifier.verify(stored, "").matches
    assert not verifier.verify(None, PASSWORD).matches, "an unknown identifier never matches"
    assert not verifier.verify("not-a-hash", PASSWORD).matches


def test_a_hash_from_older_parameters_is_rehashed_on_success_only() -> None:
    old = PasswordVerifier(PasswordPolicy(time_cost=1, memory_cost_kib=1024, parallelism=1))
    current = PasswordVerifier(PasswordPolicy(time_cost=2, memory_cost_kib=2048, parallelism=1))
    stale = old.hash(PASSWORD)
    upgraded = current.verify(stale, PASSWORD)
    assert upgraded.matches
    assert upgraded.new_hash is not None
    assert upgraded.new_hash != stale
    assert current.verify(upgraded.new_hash, PASSWORD).new_hash is None
    assert current.verify(stale, "wrong password here").new_hash is None


def test_short_and_oversized_passwords_are_refused_everywhere() -> None:
    for bad in ("", "a" * (MIN_PASSWORD_CHARS - 1), "a" * 257):
        with pytest.raises(WeakPasswordError):
            validate_new_password(bad, deployed=False)


def test_placeholder_passwords_are_refused_only_outside_development() -> None:
    validate_new_password("change-me-reviewer-bootstrap", deployed=False)
    for placeholder in (
        "change-me-reviewer-bootstrap",
        "My-PASSWORD-is-long-1",
        "reviewer-demo-pass1",
    ):
        with pytest.raises(WeakPasswordError, match="placeholder"):
            validate_new_password(placeholder, deployed=True)
    validate_new_password("a-genuinely-random-pass-9xQ", deployed=True)


def test_refusal_messages_never_repeat_the_password() -> None:
    with pytest.raises(WeakPasswordError) as raised:
        validate_new_password("Password123456", deployed=True)
    assert "Password123456" not in str(raised.value)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("  Reviewer.One  ", "reviewer.one"), ("A_b-c@d+e", "a_b-c@d+e"), ("abc", "abc")],
)
def test_identifiers_are_trimmed_and_lower_cased(raw: str, expected: str) -> None:
    assert normalise_identifier(raw) == expected


@pytest.mark.parametrize(
    "raw", ["", "ab", " ", "-leading", "has space", "semi;colon", "x" * 129, "é-accent", "a\nb"]
)
def test_malformed_identifiers_are_refused_without_echoing_them(raw: str) -> None:
    with pytest.raises(IdentifierError) as raised:
        normalise_identifier(raw)
    assert raw.strip() == "" or raw not in str(raised.value)


@given(st.text(max_size=200))
def test_normalisation_is_idempotent_and_only_ever_returns_valid_identifiers(raw: str) -> None:
    try:
        once = normalise_identifier(raw)
    except IdentifierError:
        return
    assert normalise_identifier(once) == once
    assert once == once.lower()

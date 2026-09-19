# ruff: noqa: RUF001
"""The query planner: canary private values never leave, obfuscation included; approval is exact."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from shaidago.discovery.planner import (
    CONCEPT_VOCABULARY,
    MAX_QUERY_CHARS,
    POLICY_VERSION,
    PublicProjectTerms,
    UnsafeQueryError,
    approval_matches,
    assert_query_safe,
    plan_public_query,
    plan_report_query,
    screen_term,
    sensitive_reason,
)

PROJECT = PublicProjectTerms(
    title="Synthetic Primary Health Clinic",
    locality="Synthetic Council",
    authority="Synthetic Ministry",
    category="health",
    years=(2024, 2026),
)
CANARIES = [
    "fictional.reporter@example.test",
    "fictional dot reporter at example dot test",
    "fictional.reporter [at] example [dot] test",
    "fictional．reporter＠example．test",
    "+234 801 234 5678",
    "0801-234-5678",
    "o8o1 234 56l8",
    "0 8 0 1 2 3 4 5 6 7 8",
    "８０１２３４５６７８９",
    "SG-ABCDE-FGHJK-MNPQR-STVWX-2",
    "s g a b c d e f g h",
    "SG-H-ABCD-2345",
    "https://user:hunter2@example.test/path",
    "www.example.test/private",
    "example.ng",
    "my password is hunter2",
    "Authorization: Bearer abcdef",
    "AKIAIOSFODNN7EXAMPLE1234",
    "9.0765, 7.3986",
    "9,0765 7,3986",
]


@pytest.mark.parametrize("canary", CANARIES)
def test_every_canary_is_flagged_and_screened_out(canary: str) -> None:
    assert sensitive_reason(canary) is not None
    cleaned, rejection = screen_term(canary, source="incident_concept")
    assert cleaned is None
    assert rejection is not None
    assert canary not in repr(rejection)
    with pytest.raises(UnsafeQueryError):
        assert_query_safe(f"clinic {canary}")


@pytest.mark.parametrize("canary", CANARIES)
def test_a_canary_suggested_as_a_concept_never_reaches_the_query(canary: str) -> None:
    plan = plan_report_query(PROJECT, [canary, f"clinic {canary}", f"delay {canary}"])
    assert canary not in plan.query
    assert all(t.source != "incident_concept" for t in plan.terms)
    assert {r.reason for r in plan.rejected} - {"empty"}


def test_a_public_query_uses_only_the_allowlisted_public_fields() -> None:
    plan = plan_public_query(PROJECT)
    assert (
        plan.query
        == "Synthetic Primary Health Clinic Synthetic Council Synthetic Ministry health 2024 2026"
    )
    assert [t.source for t in plan.terms] == [
        "project_title", "locality", "authority", "category", "public_year", "public_year"
    ]  # fmt: skip
    assert plan.policy_version == POLICY_VERSION
    assert plan.rejected == ()


def test_a_report_query_adds_only_neutral_vocabulary_concepts() -> None:
    plan = plan_report_query(
        PROJECT,
        ["Delayed construction", "unfinished", "the supervisor Mr Ade", "drainage works", ""],
    )
    concepts = [t.text for t in plan.terms if t.source == "incident_concept"]
    assert concepts == ["delayed construction", "unfinished", "drainage works"]
    assert all(
        t.suggested_by == "ai_suggestion" for t in plan.terms if t.source == "incident_concept"
    )
    assert "Ade" not in plan.query
    assert {r.reason for r in plan.rejected} == {"not_in_vocabulary", "empty"}


def test_a_name_or_place_is_never_a_concept_even_if_it_is_not_flagged_as_sensitive() -> None:
    plan = plan_report_query(
        PROJECT, ["Chukwuemeka", "Ibrahim Musa", "12 Fictional Street", "fraud"]
    )
    assert [t for t in plan.terms if t.source == "incident_concept"] == []


def test_long_and_duplicate_terms_are_bounded_and_deduplicated() -> None:
    long = PublicProjectTerms(title="word " * 30)
    assert plan_public_query(long).terms == ()
    twice = plan_report_query(PROJECT, ["health", "Health", "road", "road"])
    texts = [t.text.casefold() for t in twice.terms]
    assert len(texts) == len(set(texts))
    many = PublicProjectTerms(
        title="clinic", locality="a" * 79, authority="b" * 79, category="c" * 79
    )
    assert len(plan_public_query(many).query) <= MAX_QUERY_CHARS


def test_an_unsafe_public_field_is_dropped_not_sent() -> None:
    plan = plan_public_query(
        PublicProjectTerms(title="Clinic mail a@b.example", locality="Fine Place")
    )
    assert plan.query == "Fine Place"
    assert [r.reason for r in plan.rejected] == ["email"]


def test_years_outside_a_plausible_range_are_ignored() -> None:
    plan = plan_public_query(PublicProjectTerms(title="Clinic", years=(1200, 2026, 99999)))
    assert plan.query == "Clinic 2026"


def test_the_outbound_check_refuses_empty_oversized_and_sensitive_queries() -> None:
    for query in ("", "   ", "x " * 200, "clinic 08012345678"):
        with pytest.raises(UnsafeQueryError):
            assert_query_safe(query)
    assert_query_safe("clinic health 2026")


def test_an_approval_covers_exactly_one_query_and_policy() -> None:
    plan = plan_report_query(PROJECT, ["delayed"])
    assert approval_matches(plan, plan.query, POLICY_VERSION)
    changed = plan_report_query(PROJECT, ["delayed", "road"])
    assert changed.digest != plan.digest
    assert not approval_matches(changed, plan.query, POLICY_VERSION)
    assert not approval_matches(plan, plan.query, "older-policy")
    assert not approval_matches(plan, None, None)


@settings(max_examples=200, deadline=None)
@given(
    prefix=st.sampled_from(["", "clinic ", "delayed construction "]),
    local=st.text(alphabet="abcdefghijklmnop", min_size=3, max_size=10),
    domain=st.text(alphabet="qrstuvwxyz", min_size=3, max_size=8),
    join=st.sampled_from(["@", " at ", "[at]", "(at)", "＠"]),
    dot=st.sampled_from([".", " dot ", "[dot]", "(dot)", "．"]),
)
def test_generated_obfuscated_emails_never_pass(
    prefix: str, local: str, domain: str, join: str, dot: str
) -> None:
    canary = f"{prefix}{local}{join}{domain}{dot}test"
    with pytest.raises(UnsafeQueryError):
        assert_query_safe(canary)
    assert local + domain not in plan_report_query(PROJECT, [canary]).query


@settings(max_examples=200, deadline=None)
@given(
    digits=st.text(alphabet="0123456789", min_size=7, max_size=13),
    separator=st.sampled_from(["", " ", "-", ".", "\u200b", "()"]),
    swap=st.booleans(),
)
def test_generated_phone_like_runs_never_pass(digits: str, separator: str, swap: bool) -> None:
    text = separator.join(digits)
    if swap:
        text = text.replace("0", "o").replace("1", "l")
    with pytest.raises(UnsafeQueryError):
        assert_query_safe(f"clinic {text}")


@settings(max_examples=100, deadline=None)
@given(words=st.lists(st.sampled_from(sorted(CONCEPT_VOCABULARY)), min_size=1, max_size=3))
def test_vocabulary_concepts_are_accepted_in_any_case(words: list[str]) -> None:
    plan = plan_report_query(PROJECT, [" ".join(w.upper() for w in words)])
    phrase = " ".join(words).casefold()
    # A concept identical to a public term (for example "health") is deduplicated, not dropped.
    assert (
        any(t.source == "incident_concept" for t in plan.terms) or phrase in plan.query.casefold()
    )

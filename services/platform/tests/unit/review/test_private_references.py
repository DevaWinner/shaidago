"""The private-reference and guarded-wording checks: every branch, with adversarial inputs."""

import pytest

from shaidago.review.private_references import (
    GUARDED_TERMS,
    PrivateContext,
    find_private_references,
    unsupported_terms,
)

REPORT_TEXT = "FICTIONAL: the fictional gate was locked all week and nobody answered the phone."
CONTEXT = PrivateContext(
    texts=(REPORT_TEXT, "Short one."),
    contact_values=("email", "Fictional.Reporter@Example.test", "+234 801 234 5678", "ab"),
    handles=("SG-H-ABCD-2345", ""),
    reviewer_names=("rev-abc123", "ab"),
)
CLEAN = "The clinic's opening was recorded in the cited source on 1 March 2026."


def test_a_neutral_statement_has_no_findings() -> None:
    assert find_private_references(CLEAN, CONTEXT) == ()
    assert find_private_references(CLEAN, PrivateContext()) == ()


@pytest.mark.parametrize(
    "statement",
    [
        "See SG-ABCDE-FGHJK-MNPQR-STVWX-2 for details",
        "sg abcde fghjk mnpqr stvwx 2",
        "code SGABCDEFGHJKMNPQRSTVWX2",
    ],
)
def test_a_tracking_code_in_any_format_is_found(statement: str) -> None:
    assert "tracking_code" in find_private_references(statement, PrivateContext())


@pytest.mark.parametrize(
    "statement", ["handle SG-H-ABCD-2345 said", "sg h abcd 2345", "another SG-H-WXYZ-9876 here"]
)
def test_a_reporter_handle_is_found_even_when_it_is_not_the_reports_own(statement: str) -> None:
    assert "reporter_handle" in find_private_references(statement, CONTEXT)


@pytest.mark.parametrize(
    "statement",
    [
        "Write to fictional.reporter@example.test",
        "write to FICTIONAL.REPORTER@EXAMPLE.TEST now",
        "call +234 801 234 5678",
        "call 2348012345678",
        "mail someone@other.example",
        "call 0803 123 4567 today",
    ],
)
def test_contact_values_and_any_email_or_phone_like_text_are_found(statement: str) -> None:
    assert "contact" in find_private_references(statement, CONTEXT)


def test_a_short_contact_value_never_causes_a_false_match() -> None:
    assert find_private_references("the ab section", CONTEXT) == ()


def test_a_reviewers_name_is_found_as_a_whole_token_only() -> None:
    assert "reviewer_name" in find_private_references("Checked by rev-abc123.", CONTEXT)
    assert "reviewer_name" in find_private_references("REV-ABC123 checked", CONTEXT)
    assert "reviewer_name" not in find_private_references("prev-abc1234 is different", CONTEXT)
    assert "reviewer_name" not in find_private_references("the ab team", CONTEXT)


def test_copied_report_text_is_found_from_six_shared_words() -> None:
    copied = "A source says the fictional gate was locked all week."
    assert find_private_references(copied, CONTEXT) == ("report_text",)
    five = "the fictional gate was locked"
    assert "report_text" not in find_private_references(five, CONTEXT)


def test_a_short_private_text_is_found_only_when_repeated_whole() -> None:
    assert "report_text" in find_private_references("It said: short one", CONTEXT)
    assert "report_text" not in find_private_references("Only one short thing", CONTEXT)


def test_empty_inputs_are_safe() -> None:
    assert find_private_references("", CONTEXT) == ()
    assert find_private_references(CLEAN, PrivateContext(texts=("",))) == ()


def test_findings_are_sorted_and_unique() -> None:
    found = find_private_references(
        "SG-ABCDE-FGHJK-MNPQR-STVWX-2 and a@b.example and the fictional gate was locked all week",
        CONTEXT,
    )
    assert found == ("contact", "report_text", "tracking_code")


def test_the_context_never_prints_its_contents() -> None:
    assert "FICTIONAL" not in repr(CONTEXT)
    assert "Example" not in repr(CONTEXT)


@pytest.mark.parametrize("term", GUARDED_TERMS)
def test_every_guarded_word_needs_a_passage_that_contains_it(term: str) -> None:
    statement = f"The record shows the project is {term}."
    assert unsupported_terms(statement, ["An unrelated passage."]) == (term,)
    assert unsupported_terms(statement, [f"The source itself says {term.upper()}."]) == ()


def test_only_the_unsupported_guarded_words_are_reported() -> None:
    statement = "It was completed and abandoned, said to be corrupt."
    assert unsupported_terms(statement, ["The site was completed in May."]) == (
        "abandoned",
        "corrupt",
    )
    assert unsupported_terms("Neutral wording only.", []) == ()
    assert unsupported_terms("A corruption inquiry", ["corrupt practices"]) == ("corruption",)


def test_ordinary_prose_containing_sg_is_not_mistaken_for_a_tracking_code() -> None:
    prose = "The two pages give different award dates and amounts for the works."
    assert find_private_references(prose, PrivateContext()) == ()

from datetime import date
from uuid import uuid4

from shaidago.sources.publication import Citation, publication_gaps


def cite(cls: str = "official_source", publisher: str = "A", state: str = "approved") -> Citation:
    return Citation(uuid4(), publisher, cls, state)


def codes(
    state: str, citations: list[Citation], *, effective: date | None = date(2026, 3, 1)
) -> set[str]:
    return {
        gap.code
        for gap in publication_gaps(
            verification_state=state,
            citations=citations,
            effective_on=effective,
            last_checked_on=None,
        )
    }


def test_a_verified_official_fact_needs_an_official_citation() -> None:
    assert codes("verified_official", [cite()]) == set()
    assert codes("verified_official", [cite("independent_source")]) == {"official_source_required"}


def test_corroboration_needs_two_distinct_sources_and_two_publishers() -> None:
    assert codes("corroborated", [cite(publisher="A"), cite(publisher="B")]) == set()
    assert codes("corroborated", [cite(publisher="A"), cite(publisher="A")]) == {
        "independent_sources_required"
    }
    only = cite(publisher="A")
    assert codes("corroborated", [only, only]) == {"independent_sources_required"}


def test_disputed_and_outdated_still_need_a_citation_and_a_date() -> None:
    for state in ("disputed", "outdated"):
        assert codes(state, [cite()]) == set()
        assert codes(state, []) == {"approved_citation_required"}
        assert codes(state, [cite()], effective=None) == {"visible_date_required"}


def test_only_approved_or_superseded_citations_count() -> None:
    assert codes("disputed", [cite(state="pending"), cite(state="rejected")]) == {
        "approved_citation_required"
    }
    assert codes("disputed", [cite(state="superseded")]) == set()

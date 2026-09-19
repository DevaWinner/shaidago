from shaidago.db import source_tables as tables
from shaidago.shared.vocabulary import values


def test_source_value_lists_match_the_controlled_vocabulary() -> None:
    assert values("source_type") == tables.SOURCE_TYPES
    assert values("source_availability") == tables.SOURCE_AVAILABILITIES
    assert values("source_review_state") == tables.SOURCE_REVIEW_STATES
    assert values("verification_state") == tables.VERIFICATION_STATES


def test_public_source_classes_are_a_subset_that_excludes_private_and_ai_classes() -> None:
    all_classes = values("information_class")
    assert set(tables.PUBLIC_INFORMATION_CLASSES) <= set(all_classes)
    assert not {"community_report_unverified", "ai_generated_explanation"} & set(
        tables.PUBLIC_INFORMATION_CLASSES
    )


def test_only_approved_or_superseded_versions_are_citable() -> None:
    assert set(tables.CITABLE_REVIEW_STATES) == {"approved", "superseded"}

from datetime import date

import pytest

from shaidago.projects import trust


def test_a_cited_item_carries_its_class_state_and_dates_and_is_not_ai() -> None:
    labels = trust.for_cited_item(
        "official_source",
        verification_state="verified_official",
        effective_on=date(2026, 3, 1),
        last_checked_on=None,
        translation_status="reviewed",
    )
    assert labels.information_class == "official_source"
    assert labels.has_visible_date
    assert not labels.ai_generated


def test_private_or_ai_classes_can_never_label_a_cited_item() -> None:
    for bad in ("community_report_unverified", "ai_generated_explanation", "unknown"):
        with pytest.raises(ValueError, match="public source classes"):
            trust.for_cited_item(
                bad, verification_state="corroborated", effective_on=None, last_checked_on=None
            )


def test_ai_explanations_are_flagged_unverified_and_undated() -> None:
    labels = trust.for_ai_explanation(translation_status="machine_assisted")
    assert labels.ai_generated
    assert labels.information_class == "ai_generated_explanation"
    assert labels.verification_state is None
    assert not labels.has_visible_date

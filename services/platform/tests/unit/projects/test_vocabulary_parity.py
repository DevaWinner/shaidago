from typing import get_args

from shaidago.db import project_tables as tables
from shaidago.projects import models
from shaidago.shared.vocabulary import values


def test_table_value_lists_match_the_controlled_vocabulary() -> None:
    assert values("project_category") == tables.PROJECT_CATEGORIES
    assert values("project_public_status") == tables.PROJECT_PUBLIC_STATUSES
    assert values("translation_status") == tables.TRANSLATION_STATUSES


def test_model_literal_types_match_the_controlled_vocabulary() -> None:
    assert get_args(models.ProjectCategory) == values("project_category")
    assert get_args(models.PublicStatus) == values("project_public_status")
    assert get_args(models.TranslationStatus) == values("translation_status")


def test_supported_locales_are_the_four_public_locales() -> None:
    assert models.LOCALES == ("en", "ha", "ig", "yo")
    assert tables.LOCALES == models.LOCALES
    assert get_args(models.Locale) == models.LOCALES

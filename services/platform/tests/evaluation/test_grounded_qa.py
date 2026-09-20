import json
from pathlib import Path

import pytest
from _pytest.capture import CaptureFixture

from shaidago.projects.models import LOCALES
from shaidago.retrieval.evaluation import (
    GOLDEN_CORPUS,
    GoldenCorpus,
    evaluate,
    evaluate_live,
    load_corpus,
    main,
)
from shaidago.retrieval.language import (
    GroundedAnswer,
    GroundedAnswerRequest,
    LanguageModelResult,
)


def test_every_scenario_passes_deterministically_in_every_locale() -> None:
    corpus = load_corpus()
    summary = evaluate(corpus)

    assert summary.total == 44
    assert summary.passed == summary.total
    assert summary.citation_passed == summary.citation_total == 28
    assert summary.policy_passed == summary.policy_total == 44
    assert summary.by_locale == dict.fromkeys(LOCALES, (11, 11))
    assert {case.scenario for case in summary.cases} == {
        "answerable_date",
        "answerable_budget",
        "answerable_responsibility",
        "insufficient_evidence",
        "conflicting_sources",
        "cross_project_injection",
        "prompt_injection_source",
        "changed_facts",
        "unknown_citation",
        "invalid_output",
        "provider_timeout",
    }


def test_locale_drafts_keep_machine_checkable_names_amounts_dates_and_review_status() -> None:
    corpus = load_corpus()
    for locale in LOCALES:
        pack = corpus.locales[locale]
        assert pack.entity_name in pack.date_statement
        assert pack.changed_entity_name in pack.changed_statement
        assert pack.entity_name not in pack.changed_statement
        assert "NGN 12,000" in pack.budget_statement
        assert "1" in pack.date_statement
        assert "2026" in pack.date_statement
        assert "2" in pack.changed_statement
        assert "2027" in pack.changed_statement
        # The maintainer recorded a self-reported fluent review on 2026-09-19
        # (docs/evidence/BE-085-live-evaluation.md). It names its reviewer and date and marks every
        # dimension, which the model validator requires; it is not claimed to be independent.
        review = corpus.human_reviews[locale]
        assert review.status == "reviewed"
        assert review.reviewer is not None
        assert review.reviewed_on is not None
        assert {
            review.meaning,
            review.names,
            review.amounts,
            review.dates,
            review.uncertainty,
            review.safety_wording,
        } == {"preserved"}
    assert evaluate(corpus).human_review_status == dict.fromkeys(LOCALES, "reviewed")


@pytest.mark.parametrize("mutation", ["version", "locale", "review", "duplicate"])
def test_corpus_rejects_version_locale_review_and_scenario_claim_drift(
    mutation: str, tmp_path: Path
) -> None:
    payload = json.loads(GOLDEN_CORPUS.read_text(encoding="utf-8"))
    if mutation == "version":
        payload["schema_version"] = "grounded-answer-v999"
    elif mutation == "locale":
        del payload["locales"]["yo"]
    elif mutation == "review":
        # A review claim with no reviewer behind it is refused, whichever way it is written.
        payload["human_reviews"]["ha"]["reviewer"] = None
    else:
        payload["scenarios"].append(payload["scenarios"][0])
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="corpus is invalid"):
        load_corpus(path)


def test_command_reports_safe_aggregate_without_a_live_provider(
    capsys: CaptureFixture[str],
) -> None:
    assert main([]) == 0
    body = json.loads(capsys.readouterr().out)
    assert body["deterministic"] == {"passed": 44, "total": 44}
    assert body["human_review_status"] == dict.fromkeys(LOCALES, "reviewed")
    assert body["live_provider_called"] is False
    rendered = json.dumps(body)
    for forbidden in ("question", "passage", "GROQ_API_KEY", "Synthetic Clinic"):
        assert forbidden not in rendered


def test_checked_in_json_is_strictly_described_by_the_versioned_model() -> None:
    assert (
        GoldenCorpus.model_validate_json(GOLDEN_CORPUS.read_text(encoding="utf-8")).corpus_version
        == 1
    )


class InsufficientModel:
    model_id = "synthetic-live-evaluation"

    async def answer(self, request: GroundedAnswerRequest) -> LanguageModelResult:
        return LanguageModelResult(
            answer=GroundedAnswer(
                answer="",
                statements=(),
                insufficient_evidence=True,
                confidence_note="Synthetic insufficient coverage.",
                generated_at=request.generated_at,
                locale=request.locale,
            ),
            model_id=self.model_id,
            prompt_version="grounded-qa-v1",
            schema_version="grounded-answer-v2",
            demo_replay=True,
        )


async def test_live_runner_is_injected_and_records_only_versions_and_outcomes() -> None:
    summary = await evaluate_live(load_corpus(), InsufficientModel())
    assert summary.total == 36
    assert summary.model_ids == ("synthetic-live-evaluation",)
    assert summary.prompt_versions == ("grounded-qa-v1",)
    assert summary.schema_versions == ("grounded-answer-v2",)
    assert all(len(case) == 3 for case in summary.cases)


def test_a_pending_review_cannot_claim_a_reviewer(tmp_path: Path) -> None:
    """The other direction of the same rule: `pending` must not carry a name or findings."""
    payload = json.loads(GOLDEN_CORPUS.read_text(encoding="utf-8"))
    payload["human_reviews"]["ig"]["status"] = "pending"
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="corpus is invalid"):
        load_corpus(path)

"""Deterministic RulePackV1.1 predicate evaluation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.procore.criterion_evaluation import (
    ALLOWED_EXTRACTION_QUALITIES,
    CriterionEvaluation,
    build_evaluation,
)

PredicateEvaluator = Callable[
    [dict[str, Any], dict[str, Any], str, str],
    CriterionEvaluation,
]


def _matched_terms(text: str, terms: list[str]) -> list[str]:
    text_lower = text.casefold()
    return [term for term in terms if term.casefold() in text_lower]


def _confidence(extraction_quality: str) -> str:
    return "high" if extraction_quality == "good" else "medium"


def _poor_extraction(
    criterion: dict[str, Any],
    extraction_quality: str,
) -> CriterionEvaluation:
    return build_evaluation(
        criterion,
        extraction_quality=extraction_quality,
        result="unclear",
        evidence_sufficiency="absent",
        confidence="low",
        evidence_refs=[],
        reason_code="extraction_quality_low",
        requires_human_confirmation=True,
    )


def _term_present(
    criterion: dict[str, Any],
    predicate: dict[str, Any],
    text: str,
    extraction_quality: str,
) -> CriterionEvaluation:
    matches = _matched_terms(text, predicate["terms"])
    if matches:
        return build_evaluation(
            criterion,
            extraction_quality=extraction_quality,
            result="partial",
            evidence_sufficiency="insufficient",
            confidence=_confidence(extraction_quality),
            evidence_refs=matches,
            reason_code="keyword_match",
            requires_human_confirmation=True,
        )
    return build_evaluation(
        criterion,
        extraction_quality=extraction_quality,
        result="missing",
        evidence_sufficiency="absent",
        confidence=_confidence(extraction_quality),
        evidence_refs=[],
        reason_code="no_match",
        requires_human_confirmation=extraction_quality != "good",
    )


def _term_absent(
    criterion: dict[str, Any],
    predicate: dict[str, Any],
    text: str,
    extraction_quality: str,
) -> CriterionEvaluation:
    matches = _matched_terms(text, predicate["terms"])
    if matches:
        return build_evaluation(
            criterion,
            extraction_quality=extraction_quality,
            result="missing",
            evidence_sufficiency="sufficient",
            confidence=_confidence(extraction_quality),
            evidence_refs=matches,
            reason_code="prohibited_term_present",
            requires_human_confirmation=extraction_quality != "good",
        )
    if extraction_quality == "good":
        return build_evaluation(
            criterion,
            extraction_quality=extraction_quality,
            result="aligned",
            evidence_sufficiency="sufficient",
            confidence="high",
            evidence_refs=[],
            reason_code="term_absent_confirmed",
            requires_human_confirmation=False,
        )
    return build_evaluation(
        criterion,
        extraction_quality=extraction_quality,
        result="partial",
        evidence_sufficiency="insufficient",
        confidence="medium",
        evidence_refs=[],
        reason_code="term_absent_unconfirmed",
        requires_human_confirmation=True,
    )


def _term_co_present(
    criterion: dict[str, Any],
    predicate: dict[str, Any],
    text: str,
    extraction_quality: str,
) -> CriterionEvaluation:
    terms = predicate["terms"]
    matches = _matched_terms(text, terms)
    if not matches:
        return build_evaluation(
            criterion,
            extraction_quality=extraction_quality,
            result="missing",
            evidence_sufficiency="absent",
            confidence=_confidence(extraction_quality),
            evidence_refs=[],
            reason_code="no_match",
            requires_human_confirmation=extraction_quality != "good",
        )
    partial_match = predicate["match_mode"] == "all" and len(matches) < len(terms)
    return build_evaluation(
        criterion,
        extraction_quality=extraction_quality,
        result="partial",
        evidence_sufficiency="insufficient",
        confidence=_confidence(extraction_quality),
        evidence_refs=matches,
        reason_code="partial_keyword_match" if partial_match else "keyword_match",
        requires_human_confirmation=True,
    )


def _stop_work_trigger(
    criterion: dict[str, Any],
    predicate: dict[str, Any],
    text: str,
    extraction_quality: str,
) -> CriterionEvaluation:
    matches = _matched_terms(text, predicate["trigger_terms"])
    if matches:
        return build_evaluation(
            criterion,
            extraction_quality=extraction_quality,
            result="partial",
            evidence_sufficiency="insufficient",
            confidence=_confidence(extraction_quality),
            evidence_refs=matches,
            reason_code="stop_work_phrase_found",
            requires_human_confirmation=True,
        )
    return build_evaluation(
        criterion,
        extraction_quality=extraction_quality,
        result="missing",
        evidence_sufficiency="absent",
        confidence=_confidence(extraction_quality),
        evidence_refs=[],
        reason_code="no_match",
        requires_human_confirmation=extraction_quality != "good",
    )


def _hrcw_class_present(
    criterion: dict[str, Any],
    predicate: dict[str, Any],
    text: str,
    extraction_quality: str,
) -> CriterionEvaluation:
    classes = predicate["hrcw_classes"]
    class_terms = [hrcw_class.replace("_", " ") for hrcw_class in classes]
    matches = _matched_terms(text, class_terms)
    if not matches:
        return build_evaluation(
            criterion,
            extraction_quality=extraction_quality,
            result="missing",
            evidence_sufficiency="absent",
            confidence=_confidence(extraction_quality),
            evidence_refs=[],
            reason_code="no_match",
            requires_human_confirmation=extraction_quality != "good",
        )
    return build_evaluation(
        criterion,
        extraction_quality=extraction_quality,
        result="partial",
        evidence_sufficiency="insufficient",
        confidence=_confidence(extraction_quality),
        evidence_refs=matches,
        reason_code=(
            "hrcw_classes_confirmed"
            if len(matches) == len(class_terms)
            else "partial_hrcw_match"
        ),
        requires_human_confirmation=True,
    )


def _external_reference_present(
    criterion: dict[str, Any],
    predicate: dict[str, Any],
    text: str,
    extraction_quality: str,
) -> CriterionEvaluation:
    matches = _matched_terms(text, predicate["reference_terms"])
    if matches:
        return build_evaluation(
            criterion,
            extraction_quality=extraction_quality,
            result="partial",
            evidence_sufficiency="unverifiable",
            confidence=_confidence(extraction_quality),
            evidence_refs=matches,
            reason_code="external_ref_present_unverified",
            requires_human_confirmation=True,
        )
    return build_evaluation(
        criterion,
        extraction_quality=extraction_quality,
        result="missing",
        evidence_sufficiency="absent",
        confidence=_confidence(extraction_quality),
        evidence_refs=[],
        reason_code="no_match",
        requires_human_confirmation=extraction_quality != "good",
    )


def _human_only(
    criterion: dict[str, Any],
    predicate: dict[str, Any],
    text: str,
    extraction_quality: str,
) -> CriterionEvaluation:
    return build_evaluation(
        criterion,
        extraction_quality=extraction_quality,
        result="unsupported",
        evidence_sufficiency="not_applicable",
        confidence="not_applicable",
        evidence_refs=[],
        reason_code="human_judgment_required",
        requires_human_confirmation=True,
    )


PREDICATE_DISPATCH: dict[str, PredicateEvaluator] = {
    "term_present": _term_present,
    "term_absent": _term_absent,
    "term_co_present": _term_co_present,
    "stop_work_trigger": _stop_work_trigger,
    "hrcw_class_present": _hrcw_class_present,
    "external_reference_present": _external_reference_present,
    "human_only": _human_only,
}


def evaluate_criterion(
    text: str,
    criterion: dict[str, Any],
    extraction_quality: str,
) -> CriterionEvaluation:
    """Evaluate one validated criterion, with a defensive unknown-type path."""

    if extraction_quality not in ALLOWED_EXTRACTION_QUALITIES:
        raise ValueError(f"Unsupported extraction_quality: {extraction_quality}")

    predicate = criterion.get("predicate", {})
    predicate_type = predicate.get("predicate_type", "")
    evaluator = PREDICATE_DISPATCH.get(predicate_type)
    if evaluator is None:
        return build_evaluation(
            criterion,
            extraction_quality=extraction_quality,
            result="unsupported",
            evidence_sufficiency="not_applicable",
            confidence="not_applicable",
            evidence_refs=[],
            reason_code="predicate_unrecognised",
            requires_human_confirmation=True,
        )

    if extraction_quality == "poor" and predicate_type != "human_only":
        return _poor_extraction(criterion, extraction_quality)
    return evaluator(criterion, predicate, text, extraction_quality)


def evaluate_criteria(
    text: str,
    pack: dict[str, Any],
    extraction_quality: str,
) -> list[dict[str, Any]]:
    """Return exactly one schema-valid evaluation for every criterion."""

    return [
        evaluate_criterion(text, criterion, extraction_quality).to_dict()
        for criterion in pack.get("criteria", [])
    ]

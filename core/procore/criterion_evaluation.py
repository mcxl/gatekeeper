"""CriterionEvaluation construction and schema validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from jsonschema import Draft202012Validator

from core.procore.rule_pack import _validator

ALLOWED_EXTRACTION_QUALITIES = frozenset({"good", "degraded", "poor"})


@dataclass(frozen=True)
class CriterionEvaluation:
    criterion_id: str
    requirement: str
    severity: str
    basis: str
    predicate_type: str
    machine_evaluable: bool
    criterion_result: str
    evidence_sufficiency: str
    extraction_quality: str
    evaluation_confidence: str
    workflow_recommendation: str
    evidence_refs: list[str]
    reason_code: str
    requires_human_confirmation: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_criterion_evaluation(evaluation: dict[str, Any]) -> list[str]:
    """Return schema errors for one CriterionEvaluation mapping."""

    schema = _validator().schema["$defs"]["CriterionEvaluation"]
    validator = Draft202012Validator(schema)
    return sorted(
        f"{'.'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
        for error in validator.iter_errors(evaluation)
    )


def workflow_recommendation(
    *,
    result: str,
    severity: str,
    extraction_quality: str,
    confidence: str,
) -> str:
    """Resolve a conservative per-criterion workflow recommendation."""

    if result == "unsupported" and severity == "mandatory":
        return "hold"
    if extraction_quality == "poor" and severity == "mandatory":
        return "hold"
    if result == "missing" and severity == "mandatory" and confidence == "high":
        return "escalate"
    if result in {"partial", "missing", "unclear", "unsupported"}:
        return "review_required"
    return "proceed"


def build_evaluation(
    criterion: dict[str, Any],
    *,
    extraction_quality: str,
    result: str,
    evidence_sufficiency: str,
    confidence: str,
    evidence_refs: list[str],
    reason_code: str,
    requires_human_confirmation: bool,
) -> CriterionEvaluation:
    """Build a CriterionEvaluation and reject any contract violation."""

    predicate_type = criterion.get("predicate", {}).get("predicate_type", "")
    evaluation = CriterionEvaluation(
        criterion_id=criterion.get("criterion_id", ""),
        requirement=criterion.get("requirement", ""),
        severity=criterion.get("severity", "advisory"),
        basis=criterion.get("basis", "reviewer_judgment"),
        predicate_type=predicate_type,
        machine_evaluable=bool(criterion.get("machine_evaluable", False)),
        criterion_result=result,
        evidence_sufficiency=evidence_sufficiency,
        extraction_quality=extraction_quality,
        evaluation_confidence=confidence,
        workflow_recommendation=workflow_recommendation(
            result=result,
            severity=criterion.get("severity", "advisory"),
            extraction_quality=extraction_quality,
            confidence=confidence,
        ),
        evidence_refs=evidence_refs,
        reason_code=reason_code,
        requires_human_confirmation=requires_human_confirmation,
    )
    errors = validate_criterion_evaluation(evaluation.to_dict())
    if errors:
        raise ValueError("Invalid CriterionEvaluation: " + "; ".join(errors))
    return evaluation

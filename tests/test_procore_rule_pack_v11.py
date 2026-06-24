"""Focused contract tests for RulePackV1.1 evaluation."""

import pytest

from core.procore.criterion_evaluation import validate_criterion_evaluation
from core.procore.predicate_dispatch import evaluate_criteria, evaluate_criterion


def _criterion(
    predicate_type,
    *,
    severity="high",
    machine_evaluable=True,
    **predicate_fields,
):
    return {
        "criterion_id": f"C-{predicate_type}",
        "requirement": f"Test {predicate_type}",
        "severity": severity,
        "basis": "project_rule",
        "machine_evaluable": machine_evaluable,
        "predicate": {
            "predicate_type": predicate_type,
            **predicate_fields,
        },
    }


@pytest.mark.parametrize(
    ("quality", "text", "expected_result", "expected_confidence"),
    [
        ("good", "A rescue plan is referenced.", "partial", "high"),
        ("degraded", "A rescue plan is referenced.", "partial", "medium"),
        ("poor", "A rescue plan is referenced.", "unclear", "low"),
        ("good", "No relevant wording.", "missing", "high"),
        ("degraded", "No relevant wording.", "missing", "medium"),
        ("poor", "No relevant wording.", "unclear", "low"),
    ],
)
def test_term_present_truth_table(
    quality,
    text,
    expected_result,
    expected_confidence,
):
    criterion = _criterion("term_present", terms=["rescue plan"])
    result = evaluate_criterion(text, criterion, quality).to_dict()
    assert result["criterion_result"] == expected_result
    assert result["evaluation_confidence"] == expected_confidence


@pytest.mark.parametrize(
    ("quality", "text", "result", "reason"),
    [
        ("good", "Use scaffold access.", "aligned", "term_absent_confirmed"),
        ("degraded", "Use scaffold access.", "partial", "term_absent_confirmed"),
        ("poor", "Use scaffold access.", "unclear", "extraction_quality_low"),
        ("good", "Do not use a ladder as work platform.", "missing", "prohibited_term_present"),
        ("degraded", "Use a ladder as work platform.", "missing", "prohibited_term_present"),
        ("poor", "Use a ladder as work platform.", "unclear", "extraction_quality_low"),
    ],
)
def test_term_absent_is_only_aligned_path(quality, text, result, reason):
    criterion = _criterion("term_absent", terms=["ladder as work platform"])
    evaluation = evaluate_criterion(text, criterion, quality).to_dict()
    assert evaluation["criterion_result"] == result
    assert evaluation["reason_code"] == reason


@pytest.mark.parametrize(
    ("mode", "text", "result", "reason"),
    [
        ("any", "Scaffold erection.", "partial", "keyword_match"),
        ("any", "No matching wording.", "missing", "no_match"),
        ("all", "Scaffold design provided.", "partial", "keyword_match"),
        ("all", "Scaffold erection.", "partial", "partial_keyword_match"),
        ("all", "No matching wording.", "missing", "no_match"),
    ],
)
def test_term_co_present_truth_table(mode, text, result, reason):
    criterion = _criterion(
        "term_co_present",
        terms=["scaffold", "design"],
        match_mode=mode,
    )
    evaluation = evaluate_criterion(text, criterion, "good").to_dict()
    assert evaluation["criterion_result"] == result
    assert evaluation["reason_code"] == reason


@pytest.mark.parametrize(
    ("criterion", "text", "expected_reason"),
    [
        (
            _criterion("stop_work_trigger", trigger_terms=["stop work"]),
            "Stop work if edge protection fails.",
            "stop_work_phrase_found",
        ),
        (
            _criterion(
                "hrcw_class_present",
                hrcw_classes=["working_at_heights"],
            ),
            "This SWMS covers working at heights.",
            "hrcw_classes_confirmed",
        ),
        (
            _criterion(
                "external_reference_present",
                reference_terms=["hot work permit"],
            ),
            "A hot work permit is required.",
            "external_ref_present_unverified",
        ),
    ],
)
def test_keyword_predicates_never_align(criterion, text, expected_reason):
    evaluation = evaluate_criterion(text, criterion, "good").to_dict()
    assert evaluation["criterion_result"] == "partial"
    assert evaluation["reason_code"] == expected_reason


@pytest.mark.parametrize(
    "criterion",
    [
        _criterion("term_present", terms=["rescue plan"]),
        _criterion("term_absent", terms=["ladder as work platform"]),
        _criterion(
            "term_co_present",
            terms=["scaffold", "design"],
            match_mode="all",
        ),
        _criterion("stop_work_trigger", trigger_terms=["stop work"]),
        _criterion(
            "hrcw_class_present",
            hrcw_classes=["working_at_heights"],
        ),
        _criterion(
            "external_reference_present",
            reference_terms=["hot work permit"],
        ),
    ],
)
def test_poor_extraction_is_unclear_for_machine_predicates(criterion):
    evaluation = evaluate_criterion(
        "All configured terms may be present.",
        criterion,
        "poor",
    ).to_dict()
    assert evaluation["criterion_result"] == "unclear"
    assert evaluation["evaluation_confidence"] == "low"
    assert evaluation["reason_code"] == "extraction_quality_low"
    assert evaluation["requires_human_confirmation"] is True


@pytest.mark.parametrize(
    ("criterion", "text", "result", "reason", "sufficiency"),
    [
        (
            _criterion("stop_work_trigger", trigger_terms=["stop work"]),
            "No trigger wording.",
            "missing",
            "no_match",
            "absent",
        ),
        (
            _criterion(
                "hrcw_class_present",
                hrcw_classes=["working_at_heights", "confined_space"],
            ),
            "Working at heights is declared.",
            "partial",
            "partial_hrcw_match",
            "insufficient",
        ),
        (
            _criterion(
                "hrcw_class_present",
                hrcw_classes=["working_at_heights"],
            ),
            "No matching class.",
            "missing",
            "no_match",
            "absent",
        ),
        (
            _criterion(
                "external_reference_present",
                reference_terms=["hot work permit"],
            ),
            "No permit reference.",
            "missing",
            "no_match",
            "absent",
        ),
    ],
)
def test_remaining_good_extraction_branches(
    criterion,
    text,
    result,
    reason,
    sufficiency,
):
    evaluation = evaluate_criterion(text, criterion, "good").to_dict()
    assert evaluation["criterion_result"] == result
    assert evaluation["reason_code"] == reason
    assert evaluation["evidence_sufficiency"] == sufficiency


@pytest.mark.parametrize(
    ("criterion", "text", "result", "reason"),
    [
        (
            _criterion("stop_work_trigger", trigger_terms=["stop work"]),
            "No trigger wording.",
            "missing",
            "no_match",
        ),
        (
            _criterion(
                "hrcw_class_present",
                hrcw_classes=["working_at_heights", "confined_space"],
            ),
            "Working at heights is declared.",
            "partial",
            "partial_hrcw_match",
        ),
        (
            _criterion(
                "external_reference_present",
                reference_terms=["hot work permit"],
            ),
            "A hot work permit is required.",
            "partial",
            "external_ref_present_unverified",
        ),
        (
            _criterion(
                "external_reference_present",
                reference_terms=["hot work permit"],
            ),
            "No permit reference.",
            "missing",
            "no_match",
        ),
    ],
)
def test_remaining_degraded_extraction_branches(
    criterion,
    text,
    result,
    reason,
):
    evaluation = evaluate_criterion(text, criterion, "degraded").to_dict()
    assert evaluation["criterion_result"] == result
    assert evaluation["evaluation_confidence"] == "medium"
    assert evaluation["reason_code"] == reason
    assert evaluation["requires_human_confirmation"] is True


def test_human_only_is_explicit_unsupported():
    criterion = _criterion(
        "human_only",
        severity="mandatory",
        machine_evaluable=False,
    )
    evaluation = evaluate_criterion("Any text", criterion, "good").to_dict()
    assert evaluation["criterion_result"] == "unsupported"
    assert evaluation["reason_code"] == "human_judgment_required"
    assert evaluation["evaluation_confidence"] == "not_applicable"
    assert evaluation["workflow_recommendation"] == "hold"
    assert validate_criterion_evaluation(evaluation) == []


def test_unknown_dispatch_is_defensive_unsupported():
    criterion = _criterion("future_predicate", severity="mandatory")
    evaluation = evaluate_criterion("Any text", criterion, "good").to_dict()
    assert evaluation["criterion_result"] == "unsupported"
    assert evaluation["reason_code"] == "predicate_unrecognised"
    assert validate_criterion_evaluation(evaluation) == []


def test_every_criterion_emits_one_schema_valid_row():
    criteria = [
        _criterion("term_present", terms=["rescue plan"]),
        _criterion("term_absent", terms=["ladder as work platform"]),
        _criterion(
            "term_co_present",
            terms=["scaffold", "design"],
            match_mode="all",
        ),
        _criterion("stop_work_trigger", trigger_terms=["stop work"]),
        _criterion(
            "hrcw_class_present",
            hrcw_classes=["working_at_heights"],
        ),
        _criterion(
            "external_reference_present",
            reference_terms=["hot work permit"],
        ),
        _criterion("human_only", machine_evaluable=False),
    ]
    evaluations = evaluate_criteria(
        "Rescue plan. Scaffold design. Stop work. Working at heights.",
        {"criteria": criteria},
        "good",
    )
    assert len(evaluations) == len(criteria)
    assert len({row["criterion_id"] for row in evaluations}) == len(criteria)
    assert all(validate_criterion_evaluation(row) == [] for row in evaluations)


def test_unsupported_contract_rejects_real_confidence():
    criterion = _criterion("human_only", machine_evaluable=False)
    evaluation = evaluate_criterion("Any text", criterion, "good").to_dict()
    evaluation["evaluation_confidence"] = "high"
    assert validate_criterion_evaluation(evaluation)


def test_non_unsupported_contract_rejects_not_applicable():
    criterion = _criterion("term_present", terms=["rescue plan"])
    evaluation = evaluate_criterion("A rescue plan exists.", criterion, "good").to_dict()
    evaluation["evidence_sufficiency"] = "not_applicable"
    assert validate_criterion_evaluation(evaluation)


def test_unknown_extraction_quality_rejected():
    criterion = _criterion("term_present", terms=["rescue plan"])
    with pytest.raises(ValueError, match="Unsupported extraction_quality"):
        evaluate_criterion("Text", criterion, "excellent")

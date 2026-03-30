#!/usr/bin/env python3
"""
core/validator_runner.py — Internal SWMS validator wrapper + retry orchestrator.

Wraps the existing issue-gate checker (src/issue_gate.py) into a structured
ValidatorResult with defect classification and retry logic.

Runs as a synchronous post-processing / pre-handoff step.
Does NOT modify the SSE stream or governance register.

Usage:
    from core.validator_runner import run_internal_validator, run_validator_loop

    result = run_internal_validator(docx_path, tasks, stream_config)
    # or with retry:
    result = run_validator_loop(docx_path, tasks, stream_config, max_retries=2)
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# Ensure src/ is importable
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.issue_gate import (
    CheckResult,
    Classification,
    GateResult,
    Stage,
    run_issue_gate,
)


# ── Constants ────────────────────────────────────────────────────────────────

MAX_RETRIES = 2


# ── Enums and data classes ───────────────────────────────────────────────────

class ValidatorStatus(Enum):
    PASS_INTERNAL = "PASS_INTERNAL"
    RETRY_INTERNAL = "RETRY_INTERNAL"
    ESCALATE_EXTERNAL = "ESCALATE_EXTERNAL"


class DefectType(Enum):
    DETERMINISTIC_FIX = "deterministic_fix"
    ISSUE_GATE_CANDIDATE = "issue_gate_candidate"
    PROMPT_DECOMPOSER_FIX = "prompt_decomposer_fix"
    CASE_SPECIFIC_FIX = "case_specific_fix"
    EXPERT_REVIEW_ONLY = "expert_review_only"
    PRODUCT_INVESTMENT_GAP = "product_investment_gap"
    DETERMINISTIC_LIMIT_REACHED = "deterministic_limit_reached"


@dataclass
class ValidatorResult:
    status: ValidatorStatus
    failing_checks: list[str] = field(default_factory=list)
    review_checks: list[str] = field(default_factory=list)
    suggested_action: str = ""
    retry_recommended: bool = False
    defect_classifications: list[dict] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Validator: {self.status.value} "
            f"(fail={len(self.failing_checks)}, review={len(self.review_checks)})"
        ]
        if self.suggested_action:
            lines.append(f"  Action: {self.suggested_action}")
        for dc in self.defect_classifications:
            lines.append(f"  [{dc['type']}] {dc['check']}: {dc.get('detail', '')[:60]}")
        return "\n".join(lines)


# ── Stream config ────────────────────────────────────────────────────────────

@dataclass
class StreamConfig:
    """Stream-specific settings for the validator."""
    stage: Stage = Stage.BENCHMARK
    wah_threshold: int = 50
    allowed_keywords: tuple[str, ...] = ()
    job_type: str = ""  # maps to classify_swms_scope() job_type output
    reference_swms_path: str = ""  # path to reference SWMS if available


# ── Defect classification ────────────────────────────────────────────────────

# Map issue-gate check names to likely defect types when they fail.
# This is a heuristic — the classifier uses the check name and detail
# to make a best-effort classification.
_CHECK_TO_DEFECT_TYPE = {
    "access_before_dependents": DefectType.DETERMINISTIC_FIX,
    "no_coat_reinstate_merge": DefectType.DETERMINISTIC_FIX,
    "no_prestart_in_demob": DefectType.DETERMINISTIC_FIX,
    "ccvs_coverage": DefectType.DETERMINISTIC_FIX,
    "ccvs_alignment": DefectType.DETERMINISTIC_FIX,
    "ccvs_completeness": DefectType.DETERMINISTIC_FIX,
    "wah_percentage": DefectType.PROMPT_DECOMPOSER_FIX,
    "unsupported_controls": DefectType.DETERMINISTIC_FIX,
    "latent_condition_packaging": DefectType.PROMPT_DECOMPOSER_FIX,
    "responsibility_field": DefectType.CASE_SPECIFIC_FIX,
    "footer_version": DefectType.DETERMINISTIC_FIX,
}


def _classify_defect(check_name: str, detail: str) -> DefectType:
    """Classify a failing check into the defect taxonomy."""
    # Expert-review-only signals
    _EXPERT_KEYWORDS = ("consultant", "expert", "manual review")
    if any(kw in detail.lower() for kw in _EXPERT_KEYWORDS):
        return DefectType.EXPERT_REVIEW_ONLY

    return _CHECK_TO_DEFECT_TYPE.get(check_name, DefectType.CASE_SPECIFIC_FIX)


def _is_fixable(defect_type: DefectType) -> bool:
    """Return True if this defect type is worth retrying."""
    return defect_type in (
        DefectType.DETERMINISTIC_FIX,
        DefectType.ISSUE_GATE_CANDIDATE,
    )


# ── Phase 1: Validator wrapper ───────────────────────────────────────────────

def run_internal_validator(
    docx_path: Optional[str] = None,
    tasks: Optional[list[dict]] = None,
    stream_config: Optional[StreamConfig] = None,
    json_path: Optional[str] = None,
) -> ValidatorResult:
    """Run the internal validator on a SWMS output.

    Calls the existing issue gate and wraps the result into a ValidatorResult
    with defect classification and status decision.

    Args:
        docx_path: Path to rendered .docx (optional)
        tasks: Task list from JSON (optional)
        stream_config: Stream-specific settings
        json_path: Path to task JSON file (optional, alternative to tasks)

    Returns:
        ValidatorResult with status, defects, and suggested action.
    """
    if stream_config is None:
        stream_config = StreamConfig()

    # Run existing issue gate
    gate_result: GateResult = run_issue_gate(
        docx_path=docx_path,
        json_path=json_path,
        tasks=tasks,
        stage=stream_config.stage,
        wah_threshold=stream_config.wah_threshold,
        allowed_keywords=stream_config.allowed_keywords,
    )

    # Extract failing and review checks
    failing = [c for c in gate_result.checks if c.result == CheckResult.FAIL]
    reviews = [c for c in gate_result.checks if c.result == CheckResult.REVIEW]

    failing_names = [f"{c.name}: {c.detail}" for c in failing]
    review_names = [f"{c.name}: {c.detail}" for c in reviews]

    # Classify each failing check
    classifications = []
    for c in failing:
        dt = _classify_defect(c.name, c.detail)
        classifications.append({
            "check": c.name,
            "detail": c.detail,
            "type": dt.value,
        })

    # Determine status
    has_expert_only = any(
        dc["type"] == DefectType.EXPERT_REVIEW_ONLY.value
        for dc in classifications
    )
    has_fixable = any(
        _is_fixable(DefectType(dc["type"]))
        for dc in classifications
    )

    if has_expert_only:
        status = ValidatorStatus.ESCALATE_EXTERNAL
        action = "Expert-review-only defects found — escalate to external reviewer"
        retry = False
    elif len(failing) == 0:
        # No hard failures — check if reviews are acceptable
        if len(reviews) == 0:
            status = ValidatorStatus.PASS_INTERNAL
            action = "All checks pass — ready for external review"
            retry = False
        else:
            # Reviews only — acceptable at benchmark stage
            status = ValidatorStatus.ESCALATE_EXTERNAL
            action = (f"{len(reviews)} review item(s) at {stream_config.stage.value} stage "
                      f"— acceptable, escalate to external review")
            retry = False
    elif has_fixable:
        status = ValidatorStatus.RETRY_INTERNAL
        fixable_checks = [dc["check"] for dc in classifications if _is_fixable(DefectType(dc["type"]))]
        action = f"Fixable defects: {', '.join(fixable_checks[:3])} — retry recommended"
        retry = True
    else:
        status = ValidatorStatus.ESCALATE_EXTERNAL
        action = "No fixable defects remaining — escalate to external review"
        retry = False

    return ValidatorResult(
        status=status,
        failing_checks=failing_names,
        review_checks=review_names,
        suggested_action=action,
        retry_recommended=retry,
        defect_classifications=classifications,
    )


# ── Phase 2: Retry orchestrator ──────────────────────────────────────────────

def run_validator_loop(
    docx_path: Optional[str] = None,
    tasks: Optional[list[dict]] = None,
    stream_config: Optional[StreamConfig] = None,
    json_path: Optional[str] = None,
    max_retries: int = MAX_RETRIES,
) -> ValidatorResult:
    """Run the validator with retry logic.

    On RETRY_INTERNAL, identifies the single most important fixable defect,
    classifies its fix layer, and reports what should be fixed. Does NOT
    automatically apply fixes (that requires the orchestrator or operator).

    If the same defect survives after max_retries, classifies it as
    deterministic_limit_reached and escalates.

    Args:
        docx_path: Path to rendered .docx
        tasks: Task list from JSON
        stream_config: Stream-specific settings
        json_path: Path to task JSON file
        max_retries: Maximum retry attempts (default: MAX_RETRIES = 2)

    Returns:
        ValidatorResult with final status after retries exhausted or resolved.
    """
    seen_defects: dict[str, int] = {}  # check_name -> retry count

    for attempt in range(max_retries + 1):
        result = run_internal_validator(
            docx_path=docx_path,
            tasks=tasks,
            stream_config=stream_config,
            json_path=json_path,
        )

        # If not RETRY_INTERNAL, return immediately
        if result.status != ValidatorStatus.RETRY_INTERNAL:
            return result

        # If this is the last attempt, escalate
        if attempt >= max_retries:
            # Mark all remaining fixable defects as deterministic_limit_reached
            for dc in result.defect_classifications:
                if _is_fixable(DefectType(dc["type"])):
                    dc["type"] = DefectType.DETERMINISTIC_LIMIT_REACHED.value
            result.status = ValidatorStatus.ESCALATE_EXTERNAL
            result.retry_recommended = False
            result.suggested_action = (
                f"Retry cap ({max_retries}) reached — remaining defects classified "
                f"as deterministic_limit_reached. Escalate to external review."
            )
            return result

        # Track which defects persist across retries
        for dc in result.defect_classifications:
            check = dc["check"]
            seen_defects[check] = seen_defects.get(check, 0) + 1
            if seen_defects[check] > max_retries:
                dc["type"] = DefectType.DETERMINISTIC_LIMIT_REACHED.value

        # The loop continues — caller would need to apply fixes between iterations.
        # Since we don't auto-fix, we return RETRY with the classification
        # so the operator/orchestrator can decide what to do.
        return result

    # Should not reach here, but return the last result as safety
    return result

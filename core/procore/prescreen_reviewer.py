"""
core/procore/prescreen_reviewer.py — Bounded SWMS pre-screen review for Phase 1.

Takes extracted SWMS text + a project rule pack and produces a structured
reviewer-facing artifact. Does not make approval decisions.

Human review is mandatory. Status vocabulary is restricted to:
- Ready for Human Review
- Return for Amendment
- Escalate
"""

from __future__ import annotations

import re
from typing import Optional

from core.procore.webhook_handler import (
    ALLOWED_STATUSES,
    MAX_REQUIRED_AMENDMENTS,
    REVIEW_DISCLAIMER,
)


def _check_structural_sequence(text: str) -> tuple[str, list[str]]:
    """Basic structural sequence check on SWMS text."""
    findings = []
    text_lower = text.lower()

    # Check for obvious sequence issues
    if "demob" in text_lower:
        demob_pos = text_lower.index("demob")
        # Check if setup/erect appears after demob
        for kw in ("erect", "install", "commence"):
            if kw in text_lower[demob_pos:]:
                findings.append(f"'{kw}' appears after demobilisation")

    return ("ISSUES FOUND" if findings else "No issues detected", findings)


def _check_hrcw_alignment(text: str) -> tuple[str, list[str]]:
    """Check whether HRCW declarations align with method content."""
    findings = []
    text_lower = text.lower()

    # Check for WAH content without HRCW declaration
    wah_signals = ["scaffold", "ewp", "rope access", "harness", "fall arrest"]
    has_wah_content = any(s in text_lower for s in wah_signals)

    hrcw_signals = ["hrcw", "high risk construction work", "high risk work"]
    has_hrcw_ref = any(s in text_lower for s in hrcw_signals)

    if has_wah_content and not has_hrcw_ref:
        findings.append("WAH content present but no HRCW declaration found")

    return ("ISSUES FOUND" if findings else "No issues detected", findings)


def _check_control_credibility(text: str) -> tuple[str, list[str]]:
    """Check for generic/filler controls."""
    findings = []
    _FILLER = [
        "follow swms", "use ppe as required", "supervisor to monitor",
        "ensure area is safe", "maintain situational awareness",
    ]
    text_lower = text.lower()
    for filler in _FILLER:
        if filler in text_lower:
            findings.append(f"Generic filler control: '{filler}'")

    return ("ISSUES FOUND" if findings else "No issues detected", findings)


def _check_unsupported_controls(text: str) -> tuple[str, list[str]]:
    """Check for controls that are likely unsupported/drifted."""
    findings = []
    _UNSUPPORTED = [
        "council permit", "epa notification", "asbestos clearance",
        "demolition supervisor", "utility disconnection certificate",
    ]
    text_lower = text.lower()
    for term in _UNSUPPORTED:
        if term in text_lower:
            findings.append(f"Potentially unsupported: '{term}'")

    return ("ISSUES FOUND" if findings else "No issues detected", findings)


def _check_project_rules(text: str, rules: list[dict]) -> list[dict]:
    """Check extracted text against project-specific rules."""
    amendments = []
    text_lower = text.lower()

    for rule in rules:
        rule_id = rule.get("rule_id", "")
        requirement = rule.get("requirement", "")
        category = rule.get("category", "")
        severity = rule.get("severity", "advisory")
        basis = rule.get("basis", "project rule")

        # Category-specific checks
        if category == "fall_prevention":
            if any(kw in text_lower for kw in ("scaffold", "ewp", "harness", "rope access")):
                if "rescue plan" not in text_lower and "rescue" not in text_lower:
                    amendments.append({
                        "title": f"Missing rescue plan ({rule_id})",
                        "severity": severity,
                        "reason": "SWMS involves WAH but no rescue plan reference found.",
                        "project_rule": requirement,
                        "evidence_ref": "WAH content without rescue plan",
                        "basis": basis,
                    })

        elif category == "scaffold":
            if "scaffold" in text_lower:
                if "design" not in text_lower and "engineer" not in text_lower and "certification" not in text_lower:
                    amendments.append({
                        "title": f"Missing scaffold design reference ({rule_id})",
                        "severity": severity,
                        "reason": "Scaffold SWMS does not reference design drawings or engineer certification.",
                        "project_rule": requirement,
                        "evidence_ref": "Scaffold content without design/engineer reference",
                        "basis": basis,
                    })

        elif category == "ladder_restriction":
            if "ladder" in text_lower:
                if "work platform" in text_lower or "working from ladder" in text_lower:
                    amendments.append({
                        "title": f"Ladder used as work platform ({rule_id})",
                        "severity": severity,
                        "reason": "Project rule prohibits ladders as work platforms.",
                        "project_rule": requirement,
                        "evidence_ref": "Ladder as work platform reference",
                        "basis": basis,
                    })

        elif category == "hrcw_declaration":
            hrcw_ref = any(kw in text_lower for kw in ("hrcw", "high risk construction work"))
            has_high_risk = any(kw in text_lower for kw in (
                "scaffold", "crane", "excavation", "demolition",
                "confined space", "asbestos", "energised",
            ))
            if has_high_risk and not hrcw_ref:
                amendments.append({
                    "title": f"HRCW declaration missing ({rule_id})",
                    "severity": severity,
                    "reason": "SWMS appears to involve HRCW activities but no HRCW declaration found.",
                    "project_rule": requirement,
                    "evidence_ref": "High-risk content without HRCW declaration",
                    "basis": "HRCW gap",
                })

        elif category == "permits":
            if any(kw in text_lower for kw in ("weld", "cut", "grind", "hot work")):
                if "hot work permit" not in text_lower:
                    amendments.append({
                        "title": f"Missing hot work permit reference ({rule_id})",
                        "severity": severity,
                        "reason": "SWMS involves hot work but no permit reference found.",
                        "project_rule": requirement,
                        "evidence_ref": "Hot work content without permit reference",
                        "basis": basis,
                    })

    return amendments[:MAX_REQUIRED_AMENDMENTS]


def _check_structural_expectations(text: str, expectations: list[str]) -> list[dict]:
    """Check for structural expectation mismatches."""
    mismatches = []
    text_lower = text.lower()

    for exp in expectations:
        exp_lower = exp.lower()
        if "chronological" in exp_lower or "sequence" in exp_lower:
            seq_status, seq_findings = _check_structural_sequence(text)
            if seq_findings:
                mismatches.append({
                    "issue": "; ".join(seq_findings),
                    "project_rule": exp,
                    "evidence_ref": "Structural sequence check",
                })
        elif "physical hazard" in exp_lower or "not admin" in exp_lower:
            ctrl_status, ctrl_findings = _check_control_credibility(text)
            if ctrl_findings:
                mismatches.append({
                    "issue": "; ".join(ctrl_findings[:2]),
                    "project_rule": exp,
                    "evidence_ref": "Control credibility check",
                })

    return mismatches[:5]


def run_prescreen_review(
    swms_text: str,
    project_rule_pack: dict,
) -> dict:
    """Run a bounded pre-screen review of SWMS text against a project rule pack.

    Returns a structured reviewer-facing artifact.
    Human review is mandatory. Does not make approval decisions.
    """
    rules = project_rule_pack.get("rules", [])
    expectations = project_rule_pack.get("structural_expectations", [])

    # Structural checks
    seq_status, seq_findings = _check_structural_sequence(swms_text)
    hrcw_status, hrcw_findings = _check_hrcw_alignment(swms_text)
    ctrl_status, ctrl_findings = _check_control_credibility(swms_text)
    unsup_status, unsup_findings = _check_unsupported_controls(swms_text)

    # Project rule checks
    required_amendments = _check_project_rules(swms_text, rules)
    project_mismatches = _check_structural_expectations(swms_text, expectations)

    # Determine status recommendation
    mandatory_count = sum(
        1 for a in required_amendments if a.get("severity") == "mandatory"
    )
    structural_issues = sum(
        1 for s in [seq_status, hrcw_status, ctrl_status, unsup_status]
        if s == "ISSUES FOUND"
    )

    if mandatory_count >= 3 or structural_issues >= 3:
        status = "Return for Amendment"
        confidence = "HIGH"
    elif mandatory_count >= 1 or structural_issues >= 1:
        status = "Ready for Human Review"
        confidence = "MEDIUM"
    else:
        status = "Ready for Human Review"
        confidence = "HIGH"

    # Build summary
    total_issues = mandatory_count + len(project_mismatches) + structural_issues
    if total_issues == 0:
        summary = "No mandatory project-rule gaps or structural defects detected in pre-screen."
    elif total_issues <= 2:
        summary = f"{total_issues} issue(s) detected — minor gaps for human review."
    else:
        summary = f"{total_issues} issue(s) detected — recommend return for amendment before approval."

    return {
        "review_summary": summary,
        "status_recommendation": status,
        "required_amendments": required_amendments,
        "project_specific_mismatches": project_mismatches,
        "structural_findings": {
            "sequence": seq_status,
            "hrcw_alignment": hrcw_status,
            "control_credibility": ctrl_status,
            "unsupported_controls": unsup_status,
        },
        "review_confidence": confidence,
        "review_disclaimer": REVIEW_DISCLAIMER,
        "requires_human_review": True,
    }

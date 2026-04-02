"""
core/procore/prescreen_reviewer.py — SWMS pre-screen review for principal-contractor workflow.

Phase 2: Reviewer-facing structured artifact with workflow state,
prioritized amendments, project-specific mismatch separation, and
explicit human review gate.

Human review is mandatory. Safe Method does not make approval decisions.

Status vocabulary (restricted):
- Ready for Human Review
- Return for Amendment
- Escalate

Workflow states (restricted):
- reviewed_pending_human
- returned_for_amendment_recommended
- escalated_for_attention
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

from core.procore.webhook_handler import (
    ALLOWED_STATUSES,
    ALLOWED_WORKFLOW_STATES,
    MAX_REQUIRED_AMENDMENTS,
    REVIEW_DISCLAIMER,
)


# ── Structural checks ──────────────────────────────────────────────────────

def _check_structural_sequence(text: str) -> tuple[str, list[str]]:
    """Basic structural sequence check on SWMS text."""
    findings = []
    text_lower = text.lower()

    if "demob" in text_lower:
        demob_pos = text_lower.index("demob")
        for kw in ("erect", "install", "commence"):
            if kw in text_lower[demob_pos:]:
                findings.append(f"'{kw}' appears after demobilisation")

    return ("ISSUES FOUND" if findings else "No issues detected", findings)


def _check_hrcw_alignment(text: str) -> tuple[str, list[str]]:
    """Check whether HRCW declarations align with method content."""
    findings = []
    text_lower = text.lower()

    wah_signals = ["scaffold", "ewp", "rope access", "harness", "fall arrest"]
    has_wah_content = any(s in text_lower for s in wah_signals)

    hrcw_signals = ["hrcw", "high risk construction work", "high risk work"]
    has_hrcw_ref = any(s in text_lower for s in hrcw_signals)

    if has_wah_content and not has_hrcw_ref:
        findings.append("WAH content present but no HRCW declaration found")

    # Check for crane/excavation/demolition without HRCW
    for activity, signal in [("crane", "crane"), ("excavation", "excavat"),
                              ("demolition", "demolit"), ("confined space", "confined space")]:
        if signal in text_lower and not has_hrcw_ref:
            findings.append(f"{activity} content present but no HRCW declaration found")

    return ("ISSUES FOUND" if findings else "No issues detected", findings)


def _check_control_credibility(text: str) -> tuple[str, list[str]]:
    """Check for generic/filler controls."""
    findings = []
    _FILLER = [
        "follow swms", "use ppe as required", "supervisor to monitor",
        "ensure area is safe", "maintain situational awareness",
        "comply with legislation", "implement controls as necessary",
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
        "nata certificate",
    ]
    text_lower = text.lower()
    for term in _UNSUPPORTED:
        if term in text_lower:
            findings.append(f"Potentially unsupported: '{term}'")

    return ("ISSUES FOUND" if findings else "No issues detected", findings)


# ── Project rule checks ─────────────────────────────────────────────────────

def _check_project_rules(text: str, rules: list[dict]) -> list[dict]:
    """Check extracted text against project-specific rules. Returns prioritized amendments."""
    amendments: list[dict] = []
    text_lower = text.lower()

    for rule in rules:
        rule_id = rule.get("rule_id", "")
        requirement = rule.get("requirement", "")
        category = rule.get("category", "")
        severity = rule.get("severity", "advisory")
        basis = rule.get("basis", "project rule")

        amendment: Optional[dict] = None

        if category == "fall_prevention":
            if any(kw in text_lower for kw in ("scaffold", "ewp", "harness", "rope access")):
                if "rescue plan" not in text_lower and "rescue" not in text_lower:
                    amendment = {
                        "title": f"Missing rescue plan ({rule_id})",
                        "reason": "SWMS involves WAH but no rescue plan reference found.",
                        "evidence_ref": "WAH content without rescue plan",
                    }

        elif category == "scaffold":
            if "scaffold" in text_lower:
                if not any(kw in text_lower for kw in ("design", "engineer", "certification")):
                    amendment = {
                        "title": f"Missing scaffold design reference ({rule_id})",
                        "reason": "Scaffold SWMS does not reference design drawings or engineer certification.",
                        "evidence_ref": "Scaffold content without design/engineer reference",
                    }

        elif category == "ladder_restriction":
            if "ladder" in text_lower:
                if "work platform" in text_lower or "working from ladder" in text_lower:
                    amendment = {
                        "title": f"Ladder used as work platform ({rule_id})",
                        "reason": "Project rule prohibits ladders as work platforms.",
                        "evidence_ref": "Ladder as work platform reference",
                    }

        elif category == "hrcw_declaration":
            hrcw_ref = any(kw in text_lower for kw in ("hrcw", "high risk construction work"))
            has_high_risk = any(kw in text_lower for kw in (
                "scaffold", "crane", "excavation", "demolition",
                "confined space", "asbestos", "energised",
            ))
            if has_high_risk and not hrcw_ref:
                amendment = {
                    "title": f"HRCW declaration missing ({rule_id})",
                    "reason": "SWMS appears to involve HRCW activities but no HRCW declaration found.",
                    "evidence_ref": "High-risk content without HRCW declaration",
                    "basis": "HRCW gap",
                }

        elif category == "permits":
            if any(kw in text_lower for kw in ("weld", "cut", "grind", "hot work")):
                if "hot work permit" not in text_lower:
                    amendment = {
                        "title": f"Missing hot work permit reference ({rule_id})",
                        "reason": "SWMS involves hot work but no permit reference found.",
                        "evidence_ref": "Hot work content without permit reference",
                    }

        if amendment:
            amendment.setdefault("severity", severity)
            amendment.setdefault("basis", basis)
            amendment["project_rule"] = requirement
            amendments.append(amendment)

    # Sort: mandatory first, then by rule_id order
    amendments.sort(key=lambda a: (0 if a.get("severity") == "mandatory" else 1))

    # Add priority numbers
    for i, a in enumerate(amendments[:MAX_REQUIRED_AMENDMENTS], 1):
        a["priority"] = i

    return amendments[:MAX_REQUIRED_AMENDMENTS]


def _check_structural_expectations(text: str, expectations: list[str]) -> list[dict]:
    """Check for structural expectation mismatches."""
    mismatches = []

    for exp in expectations:
        exp_lower = exp.lower()
        if "chronological" in exp_lower or "sequence" in exp_lower:
            _, seq_findings = _check_structural_sequence(text)
            if seq_findings:
                mismatches.append({
                    "issue": "; ".join(seq_findings),
                    "project_rule": exp,
                    "evidence_ref": "Structural sequence check",
                })
        elif "physical hazard" in exp_lower or "not admin" in exp_lower:
            _, ctrl_findings = _check_control_credibility(text)
            if ctrl_findings:
                mismatches.append({
                    "issue": "; ".join(ctrl_findings[:2]),
                    "project_rule": exp,
                    "evidence_ref": "Control credibility check",
                })
        elif "hold point" in exp_lower or "approval authority" in exp_lower:
            if "hold point" not in text.lower() and "hold-point" not in text.lower():
                mismatches.append({
                    "issue": "No hold point references found in SWMS",
                    "project_rule": exp,
                    "evidence_ref": "Hold point text search",
                })
        elif "stop work" in exp_lower or "stop-work" in exp_lower:
            if "stop work" not in text.lower() and "stop-work" not in text.lower():
                mismatches.append({
                    "issue": "No stop-work trigger references found in SWMS",
                    "project_rule": exp,
                    "evidence_ref": "Stop-work text search",
                })

    return mismatches[:5]


# ── Main review function ────────────────────────────────────────────────────

def run_prescreen_review(
    swms_text: str,
    project_rule_pack: dict,
    job_id: str = "",
    document_reference: str = "",
) -> dict:
    """Run a bounded pre-screen review of SWMS text against a project rule pack.

    Returns a Phase 2 structured reviewer-facing artifact with workflow state,
    prioritized amendments, and explicit human review gate.

    Human review is mandatory. Does not make approval decisions.
    """
    project_id = project_rule_pack.get("project_id", "")
    rules = project_rule_pack.get("rules", [])
    expectations = project_rule_pack.get("structural_expectations", [])
    has_rule_pack = bool(rules or expectations)

    # Structural checks
    seq_status, _ = _check_structural_sequence(swms_text)
    hrcw_status, _ = _check_hrcw_alignment(swms_text)
    ctrl_status, _ = _check_control_credibility(swms_text)
    unsup_status, _ = _check_unsupported_controls(swms_text)

    # Project rule checks
    required_amendments = _check_project_rules(swms_text, rules)
    project_mismatches = _check_structural_expectations(swms_text, expectations)

    # Determine status and workflow state
    mandatory_count = sum(1 for a in required_amendments if a.get("severity") == "mandatory")
    structural_issues = sum(
        1 for s in [seq_status, hrcw_status, ctrl_status, unsup_status]
        if s == "ISSUES FOUND"
    )

    if mandatory_count >= 3 or structural_issues >= 3:
        status = "Return for Amendment"
        workflow_state = "returned_for_amendment_recommended"
        confidence = "HIGH"
    elif mandatory_count >= 1 or structural_issues >= 2:
        status = "Return for Amendment"
        workflow_state = "returned_for_amendment_recommended"
        confidence = "MEDIUM"
    elif structural_issues == 1 or required_amendments:
        status = "Ready for Human Review"
        workflow_state = "reviewed_pending_human"
        confidence = "MEDIUM"
    else:
        status = "Ready for Human Review"
        workflow_state = "reviewed_pending_human"
        confidence = "HIGH"

    # Build summary
    total_issues = mandatory_count + len(project_mismatches) + structural_issues
    if total_issues == 0:
        summary = "No mandatory project-rule gaps or structural defects detected."
    elif total_issues <= 2:
        summary = f"{total_issues} issue(s) detected — minor gaps for human review."
    else:
        summary = f"{total_issues} issue(s) detected — recommend return for amendment."

    if not has_rule_pack:
        summary += " Note: no project rule pack available — structural review only."

    # Build document fingerprint for later version comparison
    doc_fingerprint = hashlib.sha256(swms_text.encode("utf-8")).hexdigest()[:16]

    return {
        "review_version": "2.0",
        "job_id": job_id,
        "project_id": str(project_id),
        "document_reference": document_reference,
        "document_fingerprint": doc_fingerprint,
        "reviewed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "workflow_state": workflow_state,
        "status_recommendation": status,
        "review_summary": summary,
        "project_rule_pack_available": has_rule_pack,
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

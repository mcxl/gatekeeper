"""
core/procore/prescreen_reviewer.py — SWMS pre-screen review for principal-contractor workflow.

Phase 2 (refined): Reviewer-facing structured artifact with explicit workflow
state precedence, controlled basis vocabulary, deterministic amendment ordering,
top-5 visible amendments with suppressed count, and stable identifiers for
later resubmission comparison.

Human review is mandatory. Safe Method does not make approval decisions.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional

from core.procore.webhook_handler import (
    ALLOWED_STATUSES,
    ALLOWED_WORKFLOW_STATES,
    MAX_REQUIRED_AMENDMENTS,
    REVIEW_DISCLAIMER,
)

# ── Controlled vocabularies ─────────────────────────────────────────────────

ALLOWED_BASIS = frozenset({
    "issue_gate_check",
    "project_rule",
    "structural_defect",
    "hrcw_gap",
    "reviewer_judgment",
})

_BASIS_RELIABILITY_RANK = {
    "issue_gate_check": 0,
    "project_rule": 1,
    "hrcw_gap": 2,
    "structural_defect": 3,
    "reviewer_judgment": 4,
}

REVIEW_DISCLAIMER_LOW = (
    "Safe Method provides pre-screening support only and does not make "
    "binding approval decisions. Review confidence is LOW — this submission "
    "requires careful human review before any decision is made."
)


# ── Basis normalization ─────────────────────────────────────────────────────

def _normalize_basis(raw: str) -> str:
    """Normalize a basis value to the controlled vocabulary."""
    raw_lower = raw.lower().strip()
    _MAP = {
        "project rule": "project_rule",
        "project_rule": "project_rule",
        "hrcw gap": "hrcw_gap",
        "hrcw_gap": "hrcw_gap",
        "issue_gate_check": "issue_gate_check",
        "structural_defect": "structural_defect",
        "structural defect": "structural_defect",
        "reviewer_judgment": "reviewer_judgment",
        "reviewer judgment": "reviewer_judgment",
    }
    return _MAP.get(raw_lower, "reviewer_judgment")


# ── Structural checks ──────────────────────────────────────────────────────

def _check_structural_sequence(text: str) -> tuple[str, list[str]]:
    findings = []
    text_lower = text.lower()
    if "demob" in text_lower:
        demob_pos = text_lower.index("demob")
        for kw in ("erect", "install", "commence"):
            if kw in text_lower[demob_pos:]:
                findings.append(f"'{kw}' appears after demobilisation")
    return ("ISSUES FOUND" if findings else "PASS", findings)


def _check_hrcw_alignment(text: str) -> tuple[str, list[str]]:
    findings = []
    text_lower = text.lower()
    wah_signals = ["scaffold", "ewp", "rope access", "harness", "fall arrest"]
    hrcw_signals = ["hrcw", "high risk construction work", "high risk work"]
    has_wah = any(s in text_lower for s in wah_signals)
    has_hrcw = any(s in text_lower for s in hrcw_signals)
    if has_wah and not has_hrcw:
        findings.append("WAH content present but no HRCW declaration found")
    for activity, signal in [("crane", "crane"), ("excavation", "excavat"),
                              ("demolition", "demolit"), ("confined space", "confined space")]:
        if signal in text_lower and not has_hrcw:
            findings.append(f"{activity} content without HRCW declaration")
    return ("ISSUES FOUND" if findings else "PASS", findings)


def _check_control_credibility(text: str) -> tuple[str, list[str]]:
    findings = []
    _FILLER = [
        "follow swms", "use ppe as required", "supervisor to monitor",
        "ensure area is safe", "maintain situational awareness",
        "comply with legislation", "implement controls as necessary",
    ]
    text_lower = text.lower()
    for filler in _FILLER:
        if filler in text_lower:
            findings.append(f"Generic filler: '{filler}'")
    return ("ISSUES FOUND" if findings else "PASS", findings)


def _check_unsupported_controls(text: str) -> tuple[str, list[str]]:
    findings = []
    _UNSUPPORTED = [
        "council permit", "epa notification", "asbestos clearance",
        "demolition supervisor", "utility disconnection certificate",
        "nata certificate",
    ]
    text_lower = text.lower()
    for term in _UNSUPPORTED:
        if term in text_lower:
            findings.append(f"Unsupported: '{term}'")
    return ("ISSUES FOUND" if findings else "PASS", findings)


# ── Project rule checks ─────────────────────────────────────────────────────

def _check_project_rules(text: str, rules: list[dict]) -> list[dict]:
    """Check text against project rules. Returns all amendments (before cap)."""
    amendments: list[dict] = []
    text_lower = text.lower()

    for rule in rules:
        rule_id = rule.get("rule_id", "")
        requirement = rule.get("requirement", "")
        category = rule.get("category", "")
        severity = rule.get("severity", "advisory")
        raw_basis = rule.get("basis", "project_rule")
        basis = _normalize_basis(raw_basis)

        amendment: Optional[dict] = None

        if category == "fall_prevention":
            if any(kw in text_lower for kw in ("scaffold", "ewp", "harness", "rope access")):
                if "rescue plan" not in text_lower and "rescue" not in text_lower:
                    amendment = {
                        "title": f"Missing rescue plan ({rule_id})",
                        "reason": "SWMS involves WAH but no rescue plan reference found.",
                        "evidence_ref": "WAH keywords without 'rescue plan' or 'rescue'",
                    }

        elif category == "scaffold":
            if "scaffold" in text_lower:
                if not any(kw in text_lower for kw in ("design", "engineer", "certification")):
                    amendment = {
                        "title": f"Missing scaffold design reference ({rule_id})",
                        "reason": "Scaffold SWMS without design drawings or engineer certification.",
                        "evidence_ref": "'scaffold' present, 'design'/'engineer'/'certification' absent",
                    }

        elif category == "ladder_restriction":
            if "ladder" in text_lower and ("work platform" in text_lower or "working from ladder" in text_lower):
                amendment = {
                    "title": f"Ladder as work platform ({rule_id})",
                    "reason": "Project rule prohibits ladders as work platforms.",
                    "evidence_ref": "'ladder' + 'work platform' or 'working from ladder'",
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
                    "reason": "High-risk activities present but no HRCW declaration.",
                    "evidence_ref": "High-risk keywords without 'HRCW'/'high risk construction work'",
                    "basis": "hrcw_gap",
                    "severity": "high",
                }

        elif category == "permits":
            if any(kw in text_lower for kw in ("weld", "cut", "grind", "hot work")):
                if "hot work permit" not in text_lower:
                    amendment = {
                        "title": f"Missing hot work permit ({rule_id})",
                        "reason": "Hot work activities without permit reference.",
                        "evidence_ref": "Hot work keywords without 'hot work permit'",
                    }

        if amendment:
            amendment.setdefault("severity", severity)
            amendment.setdefault("basis", basis)
            amendment["project_rule"] = requirement
            amendments.append(amendment)

    return amendments


def _check_structural_expectations(text: str, expectations: list[str]) -> list[dict]:
    mismatches = []
    for exp in expectations:
        exp_lower = exp.lower()
        if "chronological" in exp_lower or "sequence" in exp_lower:
            _, findings = _check_structural_sequence(text)
            if findings:
                mismatches.append({"issue": "; ".join(findings), "project_rule": exp,
                                   "evidence_ref": "Sequence check"})
        elif "physical hazard" in exp_lower or "not admin" in exp_lower:
            _, findings = _check_control_credibility(text)
            if findings:
                mismatches.append({"issue": "; ".join(findings[:2]), "project_rule": exp,
                                   "evidence_ref": "Control credibility check"})
        elif "hold point" in exp_lower or "approval authority" in exp_lower:
            if "hold point" not in text.lower() and "hold-point" not in text.lower():
                mismatches.append({"issue": "No hold point references found", "project_rule": exp,
                                   "evidence_ref": "Text search for 'hold point'"})
        elif "stop work" in exp_lower or "stop-work" in exp_lower:
            if "stop work" not in text.lower() and "stop-work" not in text.lower():
                mismatches.append({"issue": "No stop-work triggers found", "project_rule": exp,
                                   "evidence_ref": "Text search for 'stop work'"})
    return mismatches[:5]


# ── Workflow state resolution ───────────────────────────────────────────────

def resolve_workflow_state(
    confidence: str,
    amendments: list[dict],
    structural_issue_count: int,
) -> tuple[str, str]:
    """Determine workflow_state and status_recommendation.

    Precedence:
    1. LOW confidence -> escalated_for_attention / Escalate
    2. Any high severity or hrcw_gap -> escalated_for_attention / Escalate
    3. Any amendments -> returned_for_amendment_recommended / Return for Amendment
    4. Otherwise -> reviewed_pending_human / Ready for Human Review
    """
    has_high = any(a.get("severity") == "high" for a in amendments)
    has_hrcw_gap = any(a.get("basis") == "hrcw_gap" for a in amendments)

    if confidence == "LOW":
        return ("escalated_for_attention", "Escalate")
    if has_high or has_hrcw_gap:
        return ("escalated_for_attention", "Escalate")
    if amendments or structural_issue_count >= 2:
        return ("returned_for_amendment_recommended", "Return for Amendment")
    if structural_issue_count == 1:
        return ("reviewed_pending_human", "Ready for Human Review")
    return ("reviewed_pending_human", "Ready for Human Review")


# ── Deterministic amendment ordering ────────────────────────────────────────

def _sort_amendments(amendments: list[dict]) -> list[dict]:
    """Sort amendments deterministically: severity -> basis reliability -> source order."""
    _SEV_RANK = {"high": 0, "mandatory": 1, "advisory": 2}

    def sort_key(a):
        sev = _SEV_RANK.get(a.get("severity", "advisory"), 2)
        basis = _BASIS_RELIABILITY_RANK.get(a.get("basis", "reviewer_judgment"), 4)
        return (sev, basis)

    return sorted(amendments, key=sort_key)


# ── Project review status ───────────────────────────────────────────────────

def _assess_project_review_status(rule_pack: dict) -> str:
    """Determine project review availability."""
    rules = rule_pack.get("rules", [])
    expectations = rule_pack.get("structural_expectations", [])
    if rules and expectations:
        return "AVAILABLE"
    if rules or expectations:
        return "PARTIAL"
    return "UNAVAILABLE"


# ── Main review function ────────────────────────────────────────────────────

def run_prescreen_review(
    swms_text: str,
    project_rule_pack: dict,
    job_id: str = "",
    document_reference: str = "",
    source_surface: str = "submittals",
    source_item_id: str = "",
) -> dict:
    """Run a bounded pre-screen review of SWMS text against a project rule pack.

    Returns a Phase 2 refined artifact with workflow state precedence,
    controlled basis vocabulary, deterministic amendment ordering,
    top-5 visible amendments, and stable identifiers.

    Human review is mandatory. Does not make approval decisions.
    """
    project_id = project_rule_pack.get("project_id", "")
    rules = project_rule_pack.get("rules", [])
    expectations = project_rule_pack.get("structural_expectations", [])

    # Structural checks
    seq_status, _ = _check_structural_sequence(swms_text)
    hrcw_status, _ = _check_hrcw_alignment(swms_text)
    ctrl_status, _ = _check_control_credibility(swms_text)
    unsup_status, _ = _check_unsupported_controls(swms_text)

    structural_issue_count = sum(
        1 for s in [seq_status, hrcw_status, ctrl_status, unsup_status]
        if s == "ISSUES FOUND"
    )

    # Project rule checks
    all_amendments = _check_project_rules(swms_text, rules)
    project_mismatches = _check_structural_expectations(swms_text, expectations)

    # Normalize all basis values
    for a in all_amendments:
        a["basis"] = _normalize_basis(a.get("basis", "reviewer_judgment"))

    # Deterministic ordering
    sorted_amendments = _sort_amendments(all_amendments)

    # Top-5 visible with suppressed count
    visible = sorted_amendments[:MAX_REQUIRED_AMENDMENTS]
    suppressed = len(sorted_amendments) - len(visible)
    for i, a in enumerate(visible, 1):
        a["priority"] = i

    # Determine confidence
    mandatory_count = sum(1 for a in all_amendments if a.get("severity") in ("mandatory", "high"))
    if mandatory_count >= 3 or structural_issue_count >= 3:
        confidence = "HIGH"
    elif mandatory_count >= 1 or structural_issue_count >= 1:
        confidence = "MEDIUM"
    else:
        confidence = "HIGH"

    # Check for LOW confidence signals
    if not swms_text.strip() or len(swms_text.strip()) < 100:
        confidence = "LOW"

    # Workflow state with explicit precedence
    workflow_state, status = resolve_workflow_state(
        confidence, all_amendments, structural_issue_count,
    )

    # Build summary
    total_issues = len(all_amendments) + len(project_mismatches) + structural_issue_count
    if total_issues == 0:
        summary = "No mandatory project-rule gaps or structural defects detected."
    elif total_issues <= 2:
        summary = f"{total_issues} issue(s) detected — minor gaps for human review."
    else:
        summary = f"{total_issues} issue(s) detected — recommend return for amendment."

    project_review_status = _assess_project_review_status(project_rule_pack)
    if project_review_status == "UNAVAILABLE":
        summary += " Note: no project rule pack — structural review only."

    # Disclaimer — strengthen for LOW confidence
    disclaimer = REVIEW_DISCLAIMER_LOW if confidence == "LOW" else REVIEW_DISCLAIMER

    # Stable identifiers
    document_hash = hashlib.sha256(swms_text.encode("utf-8")).hexdigest()[:16]
    review_run_id = str(uuid.uuid4())[:12]

    return {
        "review_version": "2.0",
        "review_run_id": review_run_id,
        "job_id": job_id,
        "project_id": str(project_id),
        "source_surface": source_surface,
        "source_item_id": source_item_id,
        "document_reference": document_reference,
        "document_hash": document_hash,
        "reviewed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "workflow_state": workflow_state,
        "status_recommendation": status,
        "project_review_status": project_review_status,
        "review_summary": summary,
        "required_amendments": visible,
        "suppressed_issue_count": suppressed,
        "project_specific_mismatches": project_mismatches,
        "structural_findings": {
            "sequence": seq_status,
            "hrcw_alignment": hrcw_status,
            "control_credibility": ctrl_status,
            "unsupported_controls": unsup_status,
        },
        "review_confidence": confidence,
        "review_disclaimer": disclaimer,
        "requires_human_review": True,
    }

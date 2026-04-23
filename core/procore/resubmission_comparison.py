"""
core/procore/resubmission_comparison.py — Phase 3 resubmission comparison.

Compares current SWMS review against the previous reviewed version for the
same Procore item. Classifies issues as fixed, still_open, or new.

Uses full internal issue inventories for comparison, not just the top-5
visible display amendments.

Human review is mandatory. Safe Method does not make approval decisions.
"""

from __future__ import annotations

import difflib

COMPARISON_DISCLAIMER = (
    "This comparison is system-generated and requires qualified human review "
    "before any amendment decision. Classification of issues as fixed is based "
    "on structured comparison and may not reflect actual resolution of the "
    "underlying defect."
)

# Macro similarity threshold — bypass granular comparison if too different
_MACRO_SIMILARITY_BYPASS = 0.60  # below this = net-new review

# Issue matching thresholds
_STRONG_MATCH = 0.85
_WEAK_MATCH = 0.50

# Scope reduction threshold
_SCOPE_REDUCTION_PCT = 0.15


# ── Issue matching ──────────────────────────────────────────────────────────

def _match_issues(
    previous_issues: list[dict],
    current_issues: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    """Match previous and current issue inventories.

    Returns (fixed_issues, still_open_issues, new_issues).
    Conservative: a false "fixed" is worse than an extra "still open".
    """
    prev_matched = set()
    curr_matched = set()

    fixed: list[dict] = []
    still_open: list[dict] = []
    new_issues: list[dict] = []

    # Tier 1: exact issue_key match
    prev_by_key = {}
    for i, p in enumerate(previous_issues):
        key = p.get("issue_key", "")
        if key:
            prev_by_key.setdefault(key, []).append(i)

    for j, c in enumerate(current_issues):
        c_key = c.get("issue_key", "")
        if c_key and c_key in prev_by_key:
            candidates = prev_by_key[c_key]
            for pi in candidates:
                if pi not in prev_matched:
                    prev_matched.add(pi)
                    curr_matched.add(j)
                    # Determine match type
                    basis = c.get("basis", "")
                    if basis in ("project_rule", "issue_gate_check"):
                        mc = "exact"
                        mb = "project_rule" if basis == "project_rule" else "deterministic_check"
                    else:
                        mc = "strong"
                        mb = "fuzzy_title_reason"
                    still_open.append({
                        **c,
                        "match_confidence": mc,
                        "match_basis": mb,
                    })
                    break

    # Tier 2: fuzzy title+reason match for unmatched
    unmatched_prev = [(i, p) for i, p in enumerate(previous_issues) if i not in prev_matched]
    unmatched_curr = [(j, c) for j, c in enumerate(current_issues) if j not in curr_matched]

    for j, c in list(unmatched_curr):
        c_text = (c.get("title", "") + " " + c.get("reason", "")).strip()
        best_ratio = 0.0
        best_pi = -1
        for i, p in unmatched_prev:
            if i in prev_matched:
                continue
            p_text = (p.get("title", "") + " " + p.get("reason", "")).strip()
            ratio = difflib.SequenceMatcher(None, p_text, c_text).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_pi = i

        if best_ratio >= _STRONG_MATCH and best_pi >= 0:
            prev_matched.add(best_pi)
            curr_matched.add(j)
            still_open.append({
                **c,
                "match_confidence": "strong",
                "match_basis": "fuzzy_title_reason",
            })
        elif best_ratio >= _WEAK_MATCH and best_pi >= 0:
            # Weak match — conservatively keep as still_open, do NOT mark fixed
            curr_matched.add(j)
            still_open.append({
                **c,
                "match_confidence": "weak",
                "match_basis": "fuzzy_title_reason",
            })
        # else: unmatched current issue -> new

    # Previous issues not matched to any current issue -> fixed
    for i, p in enumerate(previous_issues):
        if i not in prev_matched:
            fixed.append({
                **p,
                "match_confidence": "unmatched",
                "match_basis": "none",
            })

    # Current issues not matched to any previous issue -> new
    for j, c in enumerate(current_issues):
        if j not in curr_matched:
            new_issues.append({
                **c,
                "match_confidence": "unmatched",
                "match_basis": "none",
            })

    return fixed, still_open, new_issues


# ── Macro similarity ────────────────────────────────────────────────────────

def _compute_document_similarity(prev_hash: str, curr_hash: str,
                                  prev_text: str = "", curr_text: str = "") -> float:
    """Compute document similarity. Uses text if available, else hash comparison."""
    if prev_text and curr_text:
        return difflib.SequenceMatcher(None, prev_text[:5000], curr_text[:5000]).ratio()
    # If only hashes, can only detect exact match
    return 1.0 if prev_hash == curr_hash else 0.5


# ── Main comparison function ────────────────────────────────────────────────

def compare_reviews(
    current_artifact: dict,
    previous_artifact: dict | None = None,
    current_swms_text: str = "",
    previous_swms_text: str = "",
) -> dict:
    """Compare current review against previous for the same Procore item.

    If no previous artifact exists, returns a comparison-unavailable result.
    Uses full internal issue inventories (_all_amendments), not just visible top-5.

    Human review is mandatory. Does not make approval decisions.
    """
    # Handle missing previous
    if previous_artifact is None:
        return _no_previous_result(current_artifact)

    # Extract full inventories (use _all_amendments if available, else required_amendments)
    prev_all = previous_artifact.get("_all_amendments",
                                      previous_artifact.get("required_amendments", []))
    curr_all = current_artifact.get("_all_amendments",
                                     current_artifact.get("required_amendments", []))

    # Macro similarity check
    prev_hash = previous_artifact.get("document_hash", "")
    curr_hash = current_artifact.get("document_hash", "")
    doc_sim = _compute_document_similarity(prev_hash, curr_hash,
                                            previous_swms_text, current_swms_text)
    doc_sim_warning = doc_sim < _MACRO_SIMILARITY_BYPASS
    bypass = doc_sim_warning

    # Rule pack version check
    prev_pack_ver = previous_artifact.get("rule_pack_version", "")
    curr_pack_ver = current_artifact.get("rule_pack_version", "")
    rule_pack_changed = bool(prev_pack_ver and curr_pack_ver and prev_pack_ver != curr_pack_ver)

    warnings: list[str] = []
    if rule_pack_changed:
        warnings.append("Project rule pack version changed between reviews")
    if doc_sim_warning:
        warnings.append(f"Document similarity {doc_sim:.0%} below threshold — treating as net-new review")

    # Compare issues (unless bypassed)
    if bypass:
        fixed, still_open, new_issues = [], [], curr_all
    else:
        fixed, still_open, new_issues = _match_issues(prev_all, curr_all)

    # Scope reduction check
    prev_task_count = previous_artifact.get("_task_count", len(prev_all))
    curr_task_count = current_artifact.get("_task_count", len(curr_all))
    scope_reduction = False
    if prev_task_count > 0:
        reduction = (prev_task_count - curr_task_count) / prev_task_count
        if reduction > _SCOPE_REDUCTION_PCT:
            scope_reduction = True
            warnings.append(f"Task count dropped {reduction:.0%} ({prev_task_count} -> {curr_task_count})")

    # Regression detection
    new_mandatory = [i for i in new_issues if i.get("severity") in ("mandatory", "high")]
    has_regression = len(new_mandatory) > 0
    regression_summary = ""
    if has_regression:
        titles = [i.get("title", "?") for i in new_mandatory[:3]]
        regression_summary = f"New mandatory/high issues: {'; '.join(titles)}"

    # Comparison confidence
    if bypass or (rule_pack_changed and len(fixed) > 0):
        confidence = "LOW"
    elif rule_pack_changed or any(i.get("match_confidence") == "weak" for i in still_open):
        confidence = "MEDIUM"
    else:
        confidence = "HIGH"

    # Recommendation — driven by current state + delta context
    if bypass:
        workflow_state = "escalated_for_attention"
        status = "Escalate"
    elif confidence == "LOW":
        workflow_state = "escalated_for_attention"
        status = "Escalate"
    elif has_regression:
        workflow_state = "escalated_for_attention"
        status = "Escalate"
    elif still_open:
        workflow_state = "returned_for_amendment_recommended"
        status = "Return for Amendment"
    else:
        workflow_state = "reviewed_pending_human"
        status = "Ready for Human Review"

    summary_parts = []
    if fixed:
        summary_parts.append(f"{len(fixed)} fixed")
    if still_open:
        summary_parts.append(f"{len(still_open)} still open")
    if new_issues:
        summary_parts.append(f"{len(new_issues)} new")

    return {
        "comparison_version": "1.0",
        "previous_review_version": previous_artifact.get("review_version", ""),
        "current_review_version": current_artifact.get("review_version", ""),
        "project_id": current_artifact.get("project_id", ""),
        "source_surface": current_artifact.get("source_surface", ""),
        "source_item_id": current_artifact.get("source_item_id", ""),
        "previous_review_run_id": previous_artifact.get("review_run_id", ""),
        "current_review_run_id": current_artifact.get("review_run_id", ""),
        "previous_workflow_state": previous_artifact.get("workflow_state", ""),
        "rule_pack_version_previous": prev_pack_ver,
        "rule_pack_version_current": curr_pack_ver,
        "rule_pack_changed": rule_pack_changed,
        "comparison_summary": {
            "fixed_count": len(fixed),
            "still_open_count": len(still_open),
            "new_count": len(new_issues),
            "previous_issue_count": len(prev_all),
            "current_issue_count": len(curr_all),
            "scope_reduction_flag": scope_reduction,
        },
        "comparison_confidence": confidence,
        "comparison_warnings": warnings,
        "match_method_note": "Tier 1: exact issue_key. Tier 2: fuzzy title+reason (>=0.85 strong, >=0.50 weak). Weak matches stay still_open.",
        "document_similarity_warning": doc_sim_warning,
        "comparison_bypassed_as_net_new_review": bypass,
        "has_regression": has_regression,
        "regression_summary": regression_summary,
        "fixed_issues": fixed,
        "still_open_issues": still_open,
        "new_issues": new_issues,
        "status_recommendation": status,
        "workflow_state": workflow_state,
        "requires_human_review": True,
        "comparison_disclaimer": COMPARISON_DISCLAIMER,
    }


def _no_previous_result(current_artifact: dict) -> dict:
    """Return when no previous artifact exists for comparison."""
    return {
        "comparison_version": "1.0",
        "previous_review_version": "",
        "current_review_version": current_artifact.get("review_version", ""),
        "project_id": current_artifact.get("project_id", ""),
        "source_surface": current_artifact.get("source_surface", ""),
        "source_item_id": current_artifact.get("source_item_id", ""),
        "previous_review_run_id": "",
        "current_review_run_id": current_artifact.get("review_run_id", ""),
        "previous_workflow_state": "",
        "rule_pack_version_previous": "",
        "rule_pack_version_current": current_artifact.get("rule_pack_version", ""),
        "rule_pack_changed": False,
        "comparison_summary": {
            "fixed_count": 0,
            "still_open_count": 0,
            "new_count": 0,
            "previous_issue_count": 0,
            "current_issue_count": len(current_artifact.get("_all_amendments",
                                                             current_artifact.get("required_amendments", []))),
            "scope_reduction_flag": False,
        },
        "comparison_confidence": "LOW",
        "comparison_warnings": ["No previous review artifact available for comparison"],
        "match_method_note": "Comparison unavailable — first review or prior data missing",
        "document_similarity_warning": False,
        "comparison_bypassed_as_net_new_review": True,
        "has_regression": False,
        "regression_summary": "",
        "fixed_issues": [],
        "still_open_issues": [],
        "new_issues": [],
        "status_recommendation": current_artifact.get("status_recommendation", "Ready for Human Review"),
        "workflow_state": current_artifact.get("workflow_state", "reviewed_pending_human"),
        "requires_human_review": True,
        "comparison_disclaimer": COMPARISON_DISCLAIMER,
    }

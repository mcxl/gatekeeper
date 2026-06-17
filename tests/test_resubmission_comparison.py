"""
tests/test_resubmission_comparison.py — Tests for Phase 3 resubmission comparison.
"""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.procore.resubmission_comparison import (
    COMPARISON_DISCLAIMER,
    _match_issues,
    compare_reviews,
)
from core.procore.review_store import clear_store, find_previous_artifact, store_artifact
from core.procore.webhook_handler import ALLOWED_STATUSES, ALLOWED_WORKFLOW_STATES


# ── Helpers ─────────────────────────────────────────────────────────────────

def _make_artifact(
    run_id: str = "run-1",
    project_id: str = "123",
    source_item_id: str = "456",
    amendments: list[dict] | None = None,
    document_hash: str = "abc123",
    workflow_state: str = "returned_for_amendment_recommended",
    rule_pack_version: str = "1.0",
    reviewed_at: str = "2026-04-01T10:00:00Z",
) -> dict:
    amendments = amendments or []
    return {
        "review_version": "2.0",
        "review_run_id": run_id,
        "job_id": f"procore-{project_id}-{source_item_id}",
        "project_id": project_id,
        "source_surface": "submittals",
        "source_item_id": source_item_id,
        "document_reference": "SWMS_v1.pdf",
        "document_hash": document_hash,
        "reviewed_at": reviewed_at,
        "workflow_state": workflow_state,
        "status_recommendation": "Return for Amendment",
        "required_amendments": amendments[:5],
        "_all_amendments": amendments,
        "rule_pack_version": rule_pack_version,
        "suppressed_issue_count": max(0, len(amendments) - 5),
        "structural_findings": {"sequence": "PASS", "hrcw_alignment": "PASS",
                                "control_credibility": "PASS", "unsupported_controls": "PASS"},
        "review_confidence": "HIGH",
        "requires_human_review": True,
    }


def _make_issue(key: str, title: str, basis: str = "project_rule",
                severity: str = "mandatory") -> dict:
    return {"issue_key": key, "title": title, "basis": basis,
            "severity": severity, "reason": title, "evidence_ref": "test",
            "project_rule": "test rule"}


# ── Issue matching ──────────────────────────────────────────────────────────

class TestIssueMatching:
    def test_exact_key_match_still_open(self):
        prev = [_make_issue("project_rule:R01", "Missing rescue plan")]
        curr = [_make_issue("project_rule:R01", "Missing rescue plan")]
        fixed, still_open, new = _match_issues(prev, curr)
        assert len(still_open) == 1
        assert len(fixed) == 0
        assert len(new) == 0

    def test_issue_fixed_when_absent(self):
        prev = [_make_issue("project_rule:R01", "Missing rescue plan")]
        curr = []
        fixed, still_open, new = _match_issues(prev, curr)
        assert len(fixed) == 1
        assert fixed[0]["issue_key"] == "project_rule:R01"

    def test_new_issue_when_not_in_previous(self):
        prev = []
        curr = [_make_issue("project_rule:R02", "Missing scaffold design")]
        fixed, still_open, new = _match_issues(prev, curr)
        assert len(new) == 1
        assert new[0]["issue_key"] == "project_rule:R02"

    def test_strong_fuzzy_match_still_open(self):
        prev = [{"title": "Missing rescue plan for scaffold work", "reason": "No rescue plan",
                 "basis": "structural_defect", "severity": "mandatory"}]
        curr = [{"title": "Missing rescue plan for scaffold work", "reason": "No rescue plan reference",
                 "basis": "structural_defect", "severity": "mandatory"}]
        fixed, still_open, new = _match_issues(prev, curr)
        assert len(still_open) == 1
        assert still_open[0]["match_confidence"] in ("strong", "exact")

    def test_weak_fuzzy_match_stays_still_open(self):
        """Weak match must not be classified as fixed."""
        prev = [{"title": "Missing rescue plan", "reason": "WAH without rescue",
                 "basis": "reviewer_judgment", "severity": "advisory"}]
        curr = [{"title": "Rescue plan partially addressed", "reason": "Plan exists but incomplete",
                 "basis": "reviewer_judgment", "severity": "advisory"}]
        fixed, still_open, new = _match_issues(prev, curr)
        # Should NOT be in fixed — weak match stays still_open or new
        for f in fixed:
            assert f.get("match_confidence") != "weak"

    def test_match_confidence_present(self):
        prev = [_make_issue("project_rule:R01", "Issue A")]
        curr = [_make_issue("project_rule:R01", "Issue A")]
        _, still_open, _ = _match_issues(prev, curr)
        assert "match_confidence" in still_open[0]

    def test_match_basis_present(self):
        prev = [_make_issue("project_rule:R01", "Issue A")]
        curr = [_make_issue("project_rule:R01", "Issue A")]
        _, still_open, _ = _match_issues(prev, curr)
        assert "match_basis" in still_open[0]

    def test_full_inventory_used_not_just_top5(self):
        """Comparison must use all issues, not just top-5 display."""
        prev = [_make_issue(f"project_rule:R{i:02d}", f"Issue {i}") for i in range(8)]
        curr = [_make_issue(f"project_rule:R{i:02d}", f"Issue {i}") for i in range(8)]
        fixed, still_open, new = _match_issues(prev, curr)
        assert len(still_open) == 8
        assert len(fixed) == 0


# ── Full comparison ─────────────────────────────────────────────────────────

class TestCompareReviews:
    def test_no_previous_returns_unavailable(self):
        current = _make_artifact(run_id="run-2")
        result = compare_reviews(current, None)
        assert result["comparison_bypassed_as_net_new_review"] is True
        assert result["requires_human_review"] is True
        assert "No previous" in result["comparison_warnings"][0]

    def test_basic_comparison(self):
        base_text = "SWMS Scaffold Erection with edge protection and harness controls."
        amended_text = "SWMS Scaffold Erection with edge protection, harness, and rescue plan."
        prev = _make_artifact(run_id="run-1", amendments=[
            _make_issue("project_rule:R01", "Missing rescue plan"),
            _make_issue("project_rule:R02", "Missing scaffold design"),
        ])
        curr = _make_artifact(run_id="run-2", document_hash="def456", amendments=[
            _make_issue("project_rule:R01", "Missing rescue plan"),
        ], reviewed_at="2026-04-02T10:00:00Z")
        result = compare_reviews(curr, prev, current_swms_text=amended_text,
                                  previous_swms_text=base_text)
        assert result["comparison_summary"]["fixed_count"] == 1
        assert result["comparison_summary"]["still_open_count"] == 1
        assert result["requires_human_review"] is True

    def test_regression_detected(self):
        prev = _make_artifact(run_id="run-1", amendments=[])
        curr = _make_artifact(run_id="run-2", document_hash="new", amendments=[
            _make_issue("hrcw_gap:hrcw_declaration", "HRCW missing", "hrcw_gap", "high"),
        ], reviewed_at="2026-04-02T10:00:00Z")
        result = compare_reviews(curr, prev)
        assert result["has_regression"] is True
        assert result["regression_summary"]

    def test_rule_pack_changed_flagged(self):
        prev = _make_artifact(run_id="run-1", rule_pack_version="1.0")
        curr = _make_artifact(run_id="run-2", rule_pack_version="2.0",
                               document_hash="new", reviewed_at="2026-04-02T10:00:00Z")
        result = compare_reviews(curr, prev)
        assert result["rule_pack_changed"] is True
        assert any("rule pack" in w.lower() for w in result["comparison_warnings"])

    def test_scope_reduction_flagged(self):
        prev = _make_artifact(run_id="run-1",
                               amendments=[_make_issue(f"r:{i}", f"I{i}") for i in range(10)])
        curr = _make_artifact(run_id="run-2", document_hash="new",
                               amendments=[_make_issue("r:0", "I0")],
                               reviewed_at="2026-04-02T10:00:00Z")
        result = compare_reviews(curr, prev)
        assert result["comparison_summary"]["scope_reduction_flag"] is True

    def test_document_similarity_warning_on_major_rewrite(self):
        prev = _make_artifact(run_id="run-1", document_hash="aaa")
        curr = _make_artifact(run_id="run-2", document_hash="zzz",
                               reviewed_at="2026-04-02T10:00:00Z")
        # With very different text
        result = compare_reviews(curr, prev,
                                  current_swms_text="Completely different document about plumbing",
                                  previous_swms_text="Original scaffold erection SWMS with harness")
        # May or may not bypass depending on similarity
        assert "document_similarity_warning" in result

    def test_low_confidence_forces_escalated(self):
        prev = _make_artifact(run_id="run-1", rule_pack_version="1.0",
                               amendments=[_make_issue("r:1", "I1")])
        curr = _make_artifact(run_id="run-2", rule_pack_version="2.0",
                               document_hash="new",
                               reviewed_at="2026-04-02T10:00:00Z")
        result = compare_reviews(curr, prev)
        if result["comparison_confidence"] == "LOW":
            assert result["workflow_state"] == "escalated_for_attention"

    def test_comparison_disclaimer_always_present(self):
        curr = _make_artifact(run_id="run-2")
        result = compare_reviews(curr, None)
        assert result["comparison_disclaimer"] == COMPARISON_DISCLAIMER
        assert result["comparison_disclaimer"]

    def test_status_never_uses_approval_language(self):
        prev = _make_artifact(run_id="run-1", amendments=[_make_issue("r:1", "I1")])
        curr = _make_artifact(run_id="run-2", document_hash="new",
                               reviewed_at="2026-04-02T10:00:00Z")
        result = compare_reviews(curr, prev)
        full = json.dumps(result).lower()
        for banned in ("approved", "accepted", "compliant"):
            assert f'"{banned}"' not in full

    def test_requires_human_review_always_true(self):
        prev = _make_artifact(run_id="run-1")
        curr = _make_artifact(run_id="run-2", document_hash="new",
                               reviewed_at="2026-04-02T10:00:00Z")
        result = compare_reviews(curr, prev)
        assert result["requires_human_review"] is True

    def test_comparison_confidence_present(self):
        curr = _make_artifact()
        result = compare_reviews(curr, None)
        assert result["comparison_confidence"] in ("HIGH", "MEDIUM", "LOW")

    def test_workflow_state_in_allowed(self):
        prev = _make_artifact(run_id="run-1")
        curr = _make_artifact(run_id="run-2", document_hash="new",
                               reviewed_at="2026-04-02T10:00:00Z")
        result = compare_reviews(curr, prev)
        assert result["workflow_state"] in ALLOWED_WORKFLOW_STATES

    def test_status_in_allowed(self):
        prev = _make_artifact(run_id="run-1")
        curr = _make_artifact(run_id="run-2", document_hash="new",
                               reviewed_at="2026-04-02T10:00:00Z")
        result = compare_reviews(curr, prev)
        assert result["status_recommendation"] in ALLOWED_STATUSES


# ── Review store ────────────────────────────────────────────────────────────

class TestReviewStore:
    @pytest.fixture(autouse=True)
    def _enable_local_jsonl(self, monkeypatch):
        # These tests exercise the local JSONL store/find roundtrip, which is
        # gated off by default (T5); enable it for this class.
        monkeypatch.setenv("PROCORE_LOCAL_JSONL_ENABLED", "true")

    def setup_method(self):
        clear_store()

    def teardown_method(self):
        clear_store()

    def test_store_and_find(self):
        artifact = _make_artifact(run_id="run-1", project_id="P1", source_item_id="S1")
        store_artifact(artifact)
        found = find_previous_artifact("P1", "submittals", "S1", exclude_run_id="run-2")
        assert found is not None
        assert found["review_run_id"] == "run-1"

    def test_find_excludes_current_run(self):
        artifact = _make_artifact(run_id="run-1", project_id="P1", source_item_id="S1")
        store_artifact(artifact)
        found = find_previous_artifact("P1", "submittals", "S1", exclude_run_id="run-1")
        assert found is None

    def test_find_returns_most_recent(self):
        store_artifact(_make_artifact(run_id="run-1", project_id="P1", source_item_id="S1",
                                       reviewed_at="2026-04-01T10:00:00Z"))
        store_artifact(_make_artifact(run_id="run-2", project_id="P1", source_item_id="S1",
                                       reviewed_at="2026-04-02T10:00:00Z"))
        found = find_previous_artifact("P1", "submittals", "S1", exclude_run_id="run-3")
        assert found["review_run_id"] == "run-2"

    def test_find_returns_none_when_empty(self):
        found = find_previous_artifact("P1", "submittals", "S1")
        assert found is None

    def test_find_filters_by_item(self):
        store_artifact(_make_artifact(run_id="run-1", project_id="P1", source_item_id="S1"))
        found = find_previous_artifact("P1", "submittals", "S2")
        assert found is None

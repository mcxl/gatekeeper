"""
tests/test_rule_library.py — Tests for the rule library overlay v1.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rule_library.rule_library import (
    _find_by_finding_key,
    _reload,
    annotate_finding,
    annotate_findings,
    list_active,
    list_by_layer,
    load,
    lookup,
    map_finding_to_rule,
)


# ── Load ────────────────────────────────────────────────────────────────────

class TestLoad:
    def test_load_returns_dict(self):
        lib = load()
        assert isinstance(lib, dict)
        assert "library_version" in lib
        assert "rules" in lib

    def test_load_has_rules(self):
        lib = load()
        assert len(lib["rules"]) >= 32  # at least all issue gate checks

    def test_library_version(self):
        lib = load()
        assert lib["library_version"] == "1.0"


# ── Lookup ──────────────────────────────────────────────────────────────────

class TestLookup:
    def test_known_rule_id(self):
        rule = lookup("IG-001")
        assert rule is not None
        assert rule["finding_key"] == "access_before_dependents"

    def test_unknown_rule_id(self):
        assert lookup("IG-999") is None

    def test_reviewer_rule(self):
        rule = lookup("RV-001")
        assert rule is not None
        assert rule["layer"] == "reviewer"


# ── List active ─────────────────────────────────────────────────────────────

class TestListActive:
    def test_excludes_inactive(self):
        active = list_active()
        for r in active:
            assert r["active"] is True

    def test_all_rules_currently_active(self):
        lib = load()
        assert len(list_active()) == len(lib["rules"])


# ── List by layer ───────────────────────────────────────────────────────────

class TestListByLayer:
    def test_issue_gate_layer(self):
        ig = list_by_layer("issue_gate")
        assert len(ig) >= 31  # 31 unique check names (unsupported_controls covers json+docx)
        for r in ig:
            assert r["layer"] == "issue_gate"

    def test_reviewer_layer(self):
        rv = list_by_layer("reviewer")
        assert len(rv) >= 10
        for r in rv:
            assert r["layer"] == "reviewer"

    def test_empty_layer(self):
        assert list_by_layer("nonexistent") == []


# ── Map finding to rule ─────────────────────────────────────────────────────

class TestMapFinding:
    def test_finding_key_exact_match(self):
        finding = {"name": "ccvs_coverage", "detail": "Tasks without monitoring"}
        rule = map_finding_to_rule(finding)
        assert rule is not None
        assert rule["rule_id"] == "IG-004"

    def test_finding_key_via_check_field(self):
        finding = {"check": "unsupported_controls", "detail": "test"}
        rule = map_finding_to_rule(finding)
        assert rule is not None
        assert rule["rule_id"] == "IG-007"

    def test_no_match_returns_none(self):
        finding = {"name": "totally_unknown_check"}
        assert map_finding_to_rule(finding) is None

    def test_precedence_finding_key_first(self):
        """finding_key match takes priority over rule_family."""
        finding = {"name": "late_isolation", "rule_family": "sequence"}
        rule = map_finding_to_rule(finding)
        assert rule["rule_id"] == "IG-028"  # exact match, not generic sequence


# ── Annotate ────────────────────────────────────────────────────────────────

class TestAnnotate:
    def test_annotate_adds_metadata(self):
        finding = {"name": "ccvs_coverage", "detail": "Tasks without monitoring"}
        annotated = annotate_finding(finding)
        assert annotated["rule_id"] == "IG-004"
        assert annotated["finding_key"] == "ccvs_coverage"
        assert annotated["library_version"] == "1.0"

    def test_annotate_preserves_existing_fields(self):
        finding = {"name": "ccvs_coverage", "detail": "Tasks without monitoring",
                    "custom_field": "preserved"}
        annotated = annotate_finding(finding)
        assert annotated["custom_field"] == "preserved"
        assert annotated["detail"] == "Tasks without monitoring"

    def test_annotate_null_rule_id_for_unknown(self):
        finding = {"name": "unknown_check"}
        annotated = annotate_finding(finding)
        assert annotated["rule_id"] is None
        assert annotated["library_version"] == "1.0"

    def test_annotate_findings_list(self):
        findings = [
            {"name": "ccvs_coverage"},
            {"name": "late_isolation"},
            {"name": "unknown"},
        ]
        annotated = annotate_findings(findings)
        assert len(annotated) == 3
        assert annotated[0]["rule_id"] == "IG-004"
        assert annotated[1]["rule_id"] == "IG-028"
        assert annotated[2]["rule_id"] is None

    def test_basis_retained_when_rule_id_added(self):
        """Rule library is additive — existing fields like basis are not removed."""
        finding = {"name": "ccvs_coverage", "basis": "structural_defect"}
        annotated = annotate_finding(finding)
        assert annotated["basis"] == "structural_defect"
        assert annotated["rule_id"] == "IG-004"


# ── Issue gate wiring ───────────────────────────────────────────────────────

class TestIssueGateWiring:
    def test_gate_checks_have_rule_id(self):
        from src.issue_gate import Stage, run_issue_gate
        tasks = [
            {"step": "1.1", "task": "Erect scaffold", "ccvs_code": "WAH-H6",
             "controls": [], "admin": [], "hold_points": [], "stop_work": [],
             "hazards": ["fall"], "monitoring": {}, "responsibility": {}},
        ]
        result = run_issue_gate(tasks=tasks, stage=Stage.BENCHMARK)
        # At least some checks should have rule_id populated
        annotated = [c for c in result.checks if c.rule_id]
        assert len(annotated) > 0

    def test_every_active_ig_check_has_library_rule(self):
        """Every active issue gate check name should have a corresponding rule."""
        ig_rules = list_by_layer("issue_gate")
        ig_keys = {r["finding_key"] for r in ig_rules}
        # Known issue gate check names from the gate
        _KNOWN_CHECKS = [
            "access_before_dependents", "no_coat_reinstate_merge",
            "no_prestart_in_demob", "ccvs_coverage", "ccvs_alignment",
            "ccvs_completeness", "unsupported_controls", "responsibility_field",
            "footer_version", "latent_condition_packaging", "wah_percentage",
            "dominant_control_family", "hrcw_undercall",
            "unsupported_admin_controls", "framework_control_misuse",
            "wah_dominance_extended", "filler_controls",
            "job_type_mandatory_steps", "orphan_reinstatement",
            "late_protection_or_exposure", "sequence_rule_pack_violations",
            "monitoring_copy_paste", "p2_on_chm_task",
            "prerequisite_contradiction", "generic_responsibility",
            "late_isolation", "prerequisite_self_reference",
            "unresolved_placeholders", "risk_code_consistency",
            "scaffold_control_copy_paste", "nsw_terminology",
        ]
        for check_name in _KNOWN_CHECKS:
            assert check_name in ig_keys, f"Missing library rule for check: {check_name}"


# ── Procore artifact wiring ─────────────────────────────────────────────────

class TestProcoreWiring:
    def test_procore_artifact_has_library_version(self):
        from core.procore.prescreen_reviewer import run_prescreen_review
        result = run_prescreen_review(
            "SWMS scaffold erection with harness.",
            {"rules": [], "structural_expectations": []},
        )
        assert "rule_library_version" in result
        assert result["rule_library_version"] == "1.0"


# ── Canonical vs project separation ─────────────────────────────────────────

class TestCanonicalSeparation:
    def test_canonical_has_no_pr_prefix(self):
        """Canonical library should not contain PR- prefix rules in v1."""
        lib = load()
        for rule in lib["rules"]:
            assert not rule["rule_id"].startswith("PR-"), \
                f"Canonical library should not contain project rules: {rule['rule_id']}"

    def test_ig_and_rv_prefixes_only(self):
        lib = load()
        for rule in lib["rules"]:
            assert rule["rule_id"].startswith(("IG-", "RV-")), \
                f"Unexpected prefix: {rule['rule_id']}"

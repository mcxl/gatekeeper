"""
tests/test_issue_gate.py — Tests for the deterministic SWMS issue-gate checker.
"""

import os
import sys
from io import BytesIO

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.issue_gate import (
    CheckResult, Classification, GateResult, Stage,
    _check_access_before_dependents,
    _check_no_coat_reinstate_merge,
    _check_no_prestart_in_demob,
    _check_ccvs_coverage,
    _check_ccvs_alignment,
    _check_ccvs_completeness,
    _check_wah_percentage,
    _check_unsupported_controls_json,
    _check_responsibility_field,
    _check_footer,
    _check_latent_condition_packaging,
    run_issue_gate,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _tasks(*names_and_ccvs):
    """Build minimal task dicts: _tasks(("Paint wall", "CHM-H6"), ...)"""
    tasks = []
    for i, item in enumerate(names_and_ccvs, 1):
        if isinstance(item, tuple):
            name, ccvs = item
        else:
            name, ccvs = item, "N/A"
        tasks.append({
            "step": f"1.{i}",
            "task": name,
            "ccvs_code": ccvs,
            "controls": [],
            "admin": [],
            "monitoring": {
                "critical_control": "",
                "who_checks": "",
                "frequency": "",
                "what_to_look_for": "",
            },
        })
    return tasks


# ── C1: Access before dependents ─────────────────────────────────────────────

class TestAccessBeforeDependents:
    def test_pass_scaffold_before_paint(self):
        t = _tasks("Erect scaffolding", "Paint masonry")
        assert _check_access_before_dependents(t).result == CheckResult.PASS

    def test_fail_paint_before_scaffold(self):
        t = _tasks("Paint masonry", "Erect scaffolding")
        assert _check_access_before_dependents(t).result == CheckResult.FAIL

    def test_review_no_scaffold(self):
        t = _tasks("Establish site", "Paint masonry")
        assert _check_access_before_dependents(t).result == CheckResult.REVIEW


# ── C2: No coat+reinstate merge ─────────────────────────────────────────────

class TestNoCoatReinstateMerge:
    def test_pass_separate(self):
        t = _tasks("Paint masonry", "Reinstate green wall")
        assert _check_no_coat_reinstate_merge(t).result == CheckResult.PASS

    def test_fail_merged(self):
        t = _tasks("Paint and reinstate green wall")
        assert _check_no_coat_reinstate_merge(t).result == CheckResult.FAIL


# ── C3: No pre-start in demob ───────────────────────────────────────────────

class TestNoPrestartInDemob:
    def test_pass_clean_demob(self):
        t = _tasks("Dismantle scaffold and demobilise")
        assert _check_no_prestart_in_demob(t).result == CheckResult.PASS

    def test_fail_resident_in_demob(self):
        t = _tasks("Demobilise site")
        t[0]["admin"] = ["Notify resident of completion"]
        assert _check_no_prestart_in_demob(t).result == CheckResult.FAIL

    def test_pass_resident_in_setup(self):
        t = _tasks("Establish site")
        t[0]["admin"] = ["Notify resident of work start"]
        assert _check_no_prestart_in_demob(t).result == CheckResult.PASS


# ── C4: CCVS coverage ───────────────────────────────────────────────────────

class TestCcvsCoverage:
    def test_pass_all_monitored(self):
        t = _tasks(("Paint", "CHM-H6"))
        t[0]["monitoring"]["critical_control"] = "SDS on site"
        assert _check_ccvs_coverage(t).result == CheckResult.PASS

    def test_fail_missing_monitoring(self):
        t = _tasks("Paint")
        t[0]["monitoring"] = None
        assert _check_ccvs_coverage(t).result == CheckResult.FAIL


# ── C5: CCVS alignment ──────────────────────────────────────────────────────

class TestCcvsAlignment:
    def test_pass_sil_with_dust(self):
        t = _tasks(("Repoint brickwork", "SIL-H6"))
        t[0]["monitoring"]["critical_control"] = "Dust extraction running"
        assert _check_ccvs_alignment(t).result == CheckResult.PASS

    def test_fail_sil_with_harness(self):
        t = _tasks(("Repoint brickwork", "SIL-H6"))
        t[0]["monitoring"]["critical_control"] = "Harness clipped to anchor"
        assert _check_ccvs_alignment(t).result == CheckResult.FAIL

    def test_pass_chm_with_sds(self):
        t = _tasks(("Paint masonry", "CHM-H6"))
        t[0]["monitoring"]["critical_control"] = "SDS on site, PPE matched"
        assert _check_ccvs_alignment(t).result == CheckResult.PASS

    def test_fail_sys_with_dust(self):
        t = _tasks(("Check defects", "SYS-M3"))
        t[0]["monitoring"]["critical_control"] = "Dust extraction running"
        assert _check_ccvs_alignment(t).result == CheckResult.FAIL


# ── C6: WAH percentage ──────────────────────────────────────────────────────

class TestWahPercentage:
    def test_pass_low_wah(self):
        t = _tasks(("Scaffold", "WAH-H6"), ("Paint", "CHM-H6"), ("Seal", "CHM-H6"))
        assert _check_wah_percentage(t).result == CheckResult.PASS

    def test_fail_high_wah(self):
        t = _tasks(("T1", "WAH-H6"), ("T2", "WAH-H6"), ("T3", "WAH-H6"))
        assert _check_wah_percentage(t).result == CheckResult.FAIL


# ── C8: Responsibility field (stage-aware) ───────────────────────────────────

class TestResponsibilityField:
    def _make_doc(self, supervisor_text: str):
        """Create a minimal .docx with a cover table where R4C1 = supervisor_text."""
        from docx import Document
        doc = Document()
        table = doc.add_table(rows=5, cols=2)
        table.cell(4, 1).text = supervisor_text
        return doc

    def test_pass_populated(self):
        doc = self._make_doc("Les Robertson")
        assert _check_responsibility_field(doc, Stage.BENCHMARK).result == CheckResult.PASS

    def test_fail_blank(self):
        doc = self._make_doc("")
        assert _check_responsibility_field(doc, Stage.BENCHMARK).result == CheckResult.FAIL

    def test_review_placeholder_at_benchmark(self):
        doc = self._make_doc("[Insert Supervisor name here]")
        result = _check_responsibility_field(doc, Stage.BENCHMARK)
        assert result.result == CheckResult.REVIEW

    def test_fail_placeholder_at_issue_ready(self):
        doc = self._make_doc("[Insert Supervisor name here]")
        result = _check_responsibility_field(doc, Stage.ISSUE_READY)
        assert result.result == CheckResult.FAIL


# ── C9: Footer ───────────────────────────────────────────────────────────────

class TestFooter:
    def _make_doc_with_footer(self, filename: str, version: str):
        from docx import Document
        from docx.shared import Cm
        doc = Document()
        section = doc.sections[0]
        footer = section.footer
        footer.is_linked_to_previous = False
        table = footer.add_table(rows=1, cols=4, width=Cm(16))
        table.cell(0, 0).text = filename
        table.cell(0, 1).text = version
        return doc

    def test_pass_populated(self):
        doc = self._make_doc_with_footer("SWMS-29032026-V1.docx", "Version: 1")
        assert _check_footer(doc).result == CheckResult.PASS

    def test_fail_placeholder(self):
        doc = self._make_doc_with_footer("[DOCUMENT_FILENAME]", "[DOCUMENT_VERSION]")
        assert _check_footer(doc).result == CheckResult.FAIL

    def test_fail_empty(self):
        doc = self._make_doc_with_footer("", "")
        assert _check_footer(doc).result == CheckResult.FAIL


# ── Integration: run_issue_gate ──────────────────────────────────────────────

class TestRunIssueGate:
    def test_json_only_returns_result(self, tmp_path):
        """Minimal JSON-only run returns structured result."""
        tasks = _tasks(
            ("Erect scaffold", "WAH-H6"),
            ("Repair concrete", "SIL-H6"),
            ("Paint masonry", "CHM-H6"),
        )
        for t in tasks:
            t["monitoring"]["critical_control"] = (
                "Dust extraction" if t["ccvs_code"].startswith("SIL")
                else "SDS on site" if t["ccvs_code"].startswith("CHM")
                else "Scaffold tag checked"
            )
        data = {"tasks": tasks}
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps(data), encoding="utf-8")

        result = run_issue_gate(json_path=str(json_path))
        assert isinstance(result, GateResult)
        assert result.task_count == 3
        assert len(result.checks) == 9  # C1-C6 + C5b + C7-json + C10

    def test_classification_pass(self, tmp_path):
        """All-pass JSON produces READY_FOR_EXPERT_REVIEW."""
        tasks = _tasks(
            ("Erect scaffold", "WAH-H6"),
            ("Repair concrete", "SIL-H6"),
            ("Paint masonry", "CHM-H6"),
        )
        tasks[0]["monitoring"]["critical_control"] = "Scaffold tag current"
        tasks[1]["monitoring"]["critical_control"] = "Dust extraction running, P2 fitted"
        tasks[2]["monitoring"]["critical_control"] = "SDS on site, ventilation confirmed"
        data = {"tasks": tasks}
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps(data), encoding="utf-8")

        result = run_issue_gate(json_path=str(json_path))
        assert result.classification == Classification.READY_FOR_EXPERT_REVIEW

    def test_classification_fail(self, tmp_path):
        """A failure produces FAIL_INTERNAL."""
        tasks = _tasks(("Paint masonry", "WAH-H6"), ("T2", "WAH-H6"), ("T3", "WAH-H6"))
        for t in tasks:
            t["monitoring"]["critical_control"] = "Harness check"
        data = {"tasks": tasks}
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps(data), encoding="utf-8")

        result = run_issue_gate(json_path=str(json_path))
        assert result.classification == Classification.FAIL_INTERNAL

    def test_summary_string(self, tmp_path):
        """summary() returns a human-readable string."""
        tasks = _tasks(("Erect scaffold", "WAH-H6"))
        tasks[0]["monitoring"]["critical_control"] = "Tag checked"
        data = {"tasks": tasks}
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps(data), encoding="utf-8")

        result = run_issue_gate(json_path=str(json_path))
        s = result.summary()
        assert "Issue Gate:" in s
        assert "PASS" in s or "FAIL" in s


# ── Integration: run on real benchmark output ────────────────────────────────

class TestRealBenchmarkOutput:
    """Run the gate on actual Danks Street benchmark output if available."""

    @pytest.fixture(autouse=True)
    def _check_files(self):
        self.docx = "src/outputs/SWMS_18_Danks_St_Benchmark_Latest.docx"
        self.json = "src/outputs/SWMS_18_Danks_St_Benchmark_Latest.json"
        if not os.path.exists(self.docx) or not os.path.exists(self.json):
            pytest.skip("Benchmark output files not available")

    def test_real_output_runs(self):
        result = run_issue_gate(docx_path=self.docx, json_path=self.json)
        assert isinstance(result, GateResult)
        assert result.task_count > 0
        assert len(result.checks) == 12  # C1-C6 + C5b + C7-json + C10 + C7-docx + C8 + C9

    def test_real_output_no_hard_failures(self):
        """Real benchmark output should not have hard failures."""
        result = run_issue_gate(docx_path=self.docx, json_path=self.json)
        # Allow REVIEW (placeholders at benchmark stage) but not FAIL
        hard_fails = [c for c in result.checks if c.result == CheckResult.FAIL]
        if hard_fails:
            details = "; ".join(f"{c.name}: {c.detail}" for c in hard_fails)
            pytest.fail(f"Hard failures in benchmark output: {details}")


# ── C5 strengthened: CCVS-task cross-check ───────────────────────────────────

class TestCcvsAlignmentStrengthened:
    def test_wah_on_paint_task_flagged(self):
        """WAH code on a paint task should be flagged (expects CHM)."""
        t = _tasks(("Paint exterior masonry", "WAH-H6"))
        t[0]["monitoring"]["critical_control"] = "Harness check"
        result = _check_ccvs_alignment(t)
        assert result.result == CheckResult.FAIL
        assert "suggests CHM but coded WAH" in result.detail

    def test_sil_on_repoint_passes(self):
        t = _tasks(("Repoint brickwork", "SIL-H6"))
        t[0]["monitoring"]["critical_control"] = "Dust extraction running"
        assert _check_ccvs_alignment(t).result == CheckResult.PASS

    def test_wah_on_scaffold_passes(self):
        """WAH on a scaffold task is correct."""
        t = _tasks(("Erect scaffolding", "WAH-H6"))
        t[0]["monitoring"]["critical_control"] = "Scaffold tag checked"
        assert _check_ccvs_alignment(t).result == CheckResult.PASS


# ── C5b: CCVS completeness ──────────────────────────────────────────────────

class TestCcvsCompleteness:
    def test_pass_all_have_ccvs(self):
        t = _tasks(("Paint", "CHM-H6"), ("Scaffold", "WAH-H6"))
        t[0]["hazards"] = ["Chemical exposure"]
        t[1]["hazards"] = ["Fall from height"]
        assert _check_ccvs_completeness(t).result == CheckResult.PASS

    def test_fail_na_with_hazards(self):
        t = _tasks(("Repair concrete", "N/A"))
        t[0]["hazards"] = ["Silica dust", "Falling objects"]
        result = _check_ccvs_completeness(t)
        assert result.result == CheckResult.FAIL
        assert "N/A CCVS" in result.detail

    def test_pass_na_without_hazards(self):
        t = _tasks(("Demobilise", "N/A"))
        t[0]["hazards"] = []
        assert _check_ccvs_completeness(t).result == CheckResult.PASS


# ── C10: Latent-condition packaging ──────────────────────────────────────────

class TestLatentConditionPackaging:
    def test_review_standalone_latent_task(self):
        t = _tasks("Latent conditions check — stop work if toxic materials found")
        result = _check_latent_condition_packaging(t)
        assert result.result == CheckResult.REVIEW

    def test_pass_no_latent_tasks(self):
        t = _tasks("Paint masonry", "Repair concrete")
        assert _check_latent_condition_packaging(t).result == CheckResult.PASS

    def test_review_hazmat_survey_task(self):
        t = _tasks("Survey and identify hazardous material")
        t[0]["scope"] = "Asbestos survey before work starts"
        result = _check_latent_condition_packaging(t)
        assert result.result == CheckResult.REVIEW


# ── C7 strengthened: JSON-based unsupported controls ─────────────────────────

class TestUnsupportedControlsJson:
    def test_pass_clean(self):
        t = _tasks("Paint masonry")
        t[0]["controls"] = ["Wear harness", "Check scaffold tag"]
        assert _check_unsupported_controls_json(t).result == CheckResult.PASS

    def test_fail_utility_isolation(self):
        t = _tasks("Establish site")
        t[0]["controls"] = ["Verify utility isolation certificate"]
        result = _check_unsupported_controls_json(t)
        assert result.result == CheckResult.FAIL

    def test_fail_structural_engineer_in_admin(self):
        t = _tasks("Repoint brickwork")
        t[0]["admin"] = ["Obtain structural engineer approval before starting"]
        result = _check_unsupported_controls_json(t)
        assert result.result == CheckResult.FAIL

    def test_fail_membrane_in_controls(self):
        t = _tasks("Apply sealant")
        t[0]["controls"] = ["Apply membrane where required"]
        result = _check_unsupported_controls_json(t)
        assert result.result == CheckResult.FAIL

    def test_irrigation_ok_for_green_wall(self):
        t = _tasks("Remove green wall")
        t[0]["controls"] = ["Check irrigation before removal"]
        assert _check_unsupported_controls_json(t).result == CheckResult.PASS


import json

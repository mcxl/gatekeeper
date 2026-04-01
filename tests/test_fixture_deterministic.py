"""
tests/test_fixture_deterministic.py — Fixture-based tests for deterministic logic.

Runs issue gate checks, CCVS correction, and sequence scoring against
saved pipeline output fixtures. No LLM calls required.
"""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "pipeline_outputs"


def _load_fixture(name: str) -> dict:
    path = FIXTURES_DIR / f"{name}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── Issue gate on fixtures ──────────────────────────────────────────────────

from src.issue_gate import (
    CheckResult,
    Stage,
    run_issue_gate,
    _check_unsupported_controls_json,
    _check_unsupported_admin_controls,
    _check_orphan_reinstatement,
    _check_generic_responsibility,
    _check_prerequisite_self_reference,
    _check_risk_code_consistency,
    _check_monitoring_copy_paste,
    _check_scaffold_control_on_non_scaffold,
)


class TestTiltupFixture:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = _load_fixture("tiltup_panel")
        self.tasks = self.data["tasks"]

    def test_membrane_not_flagged_on_concrete_scope(self):
        """Curing membrane in concrete scope should not trigger unsupported controls."""
        result = _check_unsupported_controls_json(self.tasks)
        if result.result == CheckResult.FAIL:
            assert "membrane" not in result.detail.lower()

    def test_casting_bed_ccvs_corrected(self):
        """Set out casting bed task should get SYS-M3 after correction."""
        from core.orchestrator import _correct_ccvs_by_task_type
        tb = dict(self.tasks[1])  # "Set out casting bed..."
        assert tb["ccvs_code"] == "N/A"
        _correct_ccvs_by_task_type(tb)
        assert tb["ccvs_code"] == "SYS-M3"

    def test_strip_formwork_gets_sil(self):
        """Strip formwork is a removal task — should get SIL-H6."""
        from core.orchestrator import _correct_ccvs_by_task_type
        tb = dict(self.tasks[0])  # "Strip formwork..."
        _correct_ccvs_by_task_type(tb)
        assert tb["ccvs_code"] == "SIL-H6"

    def test_demob_gets_sys(self):
        """Demobilise crane and clear site should get SYS-M3."""
        from core.orchestrator import _correct_ccvs_by_task_type
        tb = dict(self.tasks[-1])  # "Demobilise crane..."
        _correct_ccvs_by_task_type(tb)
        assert tb["ccvs_code"] == "SYS-M3"

    def test_sequence_erect_before_remove_bracing(self):
        """Erect panels must phase before remove bracing."""
        from core.orchestrator import _task_phase_score
        erect = _task_phase_score(self.tasks[6])  # "Erect panels..."
        remove = _task_phase_score(self.tasks[7])  # "Remove temporary bracing..."
        assert erect <= remove


class TestCivilDrillingFixture:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = _load_fixture("civil_drilling")
        self.tasks = self.data["tasks"]

    def test_council_permit_not_flagged_in_civil_scope(self):
        """Council permit should be allowed when road/traffic tasks are present."""
        result = _check_unsupported_admin_controls(self.tasks)
        assert result.result != CheckResult.FAIL or "council permit" not in result.detail.lower()

    def test_drill_bore_ccvs_corrected_to_sil(self):
        """Drill pilot bore should get SIL-H6 after correction."""
        from core.orchestrator import _correct_ccvs_by_task_type
        tb = dict(self.tasks[2])  # "Drill pilot bore..."
        assert tb["ccvs_code"] == "N/A"
        _correct_ccvs_by_task_type(tb)
        assert tb["ccvs_code"] == "SIL-H6"

    def test_ream_bore_ccvs_corrected_to_sil(self):
        from core.orchestrator import _correct_ccvs_by_task_type
        tb = dict(self.tasks[3])  # "Ream bore..."
        _correct_ccvs_by_task_type(tb)
        assert tb["ccvs_code"] == "SIL-H6"

    def test_verify_conduit_ccvs_corrected_to_sys(self):
        from core.orchestrator import _correct_ccvs_by_task_type
        tb = dict(self.tasks[5])  # "Verify conduit continuity..."
        _correct_ccvs_by_task_type(tb)
        assert tb["ccvs_code"] == "SYS-M3"

    def test_generic_responsibility_flagged(self):
        """Supervise Drill pilot bore... should trigger generic responsibility."""
        result = _check_generic_responsibility(self.tasks)
        assert result.result == CheckResult.REVIEW

    def test_risk_code_consistency_flagged(self):
        """SYS-M3 on High risk_pre should trigger review."""
        result = _check_risk_code_consistency(self.tasks)
        assert result.result == CheckResult.REVIEW


class TestHydraulicRemedialFixture:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = _load_fixture("hydraulic_remedial")
        self.tasks = self.data["tasks"]

    def test_pumpout_ccvs_corrected(self):
        """Replace pump-out should get SYS-M3 after correction."""
        from core.orchestrator import _correct_ccvs_by_task_type
        tb = dict(self.tasks[2])  # "Replace pump-out..."
        assert tb["ccvs_code"] == "N/A"
        _correct_ccvs_by_task_type(tb)
        assert tb["ccvs_code"] == "SYS-M3"

    def test_orphan_reinstatement_not_flagged_on_handover(self):
        """Clean/cap/handover reinstatement should not trigger orphan check."""
        result = _check_orphan_reinstatement(self.tasks)
        assert result.result == CheckResult.PASS

    def test_monitoring_copy_paste_same_family_passes(self):
        """Same monitoring on same CCVS family (SIL+SIL) should not trigger."""
        result = _check_monitoring_copy_paste(self.tasks)
        # Fixture has same monitoring on SIL tasks only — not cross-family
        assert result.result == CheckResult.PASS

    def test_full_gate_runs_without_error(self):
        """Full issue gate should run cleanly on fixture data."""
        result = run_issue_gate(tasks=self.tasks, stage=Stage.BENCHMARK)
        assert result.task_count == len(self.tasks)
        assert len(result.checks) > 0


class TestAllFixturesLoadCleanly:
    """Ensure all pipeline output fixtures are valid JSON with expected structure."""

    @pytest.fixture(params=list(FIXTURES_DIR.glob("*.json")))
    def fixture_path(self, request):
        return request.param

    def test_fixture_loads(self, fixture_path):
        with open(fixture_path, encoding="utf-8") as f:
            data = json.load(f)
        assert "tasks" in data
        assert isinstance(data["tasks"], list)

    def test_fixture_tasks_have_required_fields(self, fixture_path):
        with open(fixture_path, encoding="utf-8") as f:
            data = json.load(f)
        for t in data["tasks"]:
            assert "step" in t
            assert "task" in t

    def test_fixture_gate_runs(self, fixture_path):
        with open(fixture_path, encoding="utf-8") as f:
            data = json.load(f)
        result = run_issue_gate(tasks=data["tasks"], stage=Stage.BENCHMARK)
        assert result.task_count == len(data["tasks"])

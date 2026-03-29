"""
tests/test_validator_runner.py — Tests for the internal SWMS validator wrapper + retry orchestrator.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.validator_runner import (
    DefectType,
    StreamConfig,
    ValidatorResult,
    ValidatorStatus,
    run_internal_validator,
    run_validator_loop,
    _classify_defect,
    _is_fixable,
    MAX_RETRIES,
)
from src.issue_gate import Stage


# ── Helpers ──────────────────────────────────────────────────────────────────

def _clean_tasks():
    """Return a minimal task set that passes all issue-gate checks."""
    return [
        {
            "step": "1.1", "task": "Erect scaffolding",
            "ccvs_code": "WAH-H6", "hazards": ["Fall from height"],
            "controls": ["Wear harness"], "admin": [], "hold_points": [],
            "stop_work": [],
            "monitoring": {
                "critical_control": "Scaffold tag checked and current",
                "who_checks": "Supervisor", "who": "Supervisor",
                "frequency": "daily",
                "what_to_look_for": "Tag visible", "evidence": "Tag visible",
            },
            "responsibility": {"SUP": "Check scaffold", "WKR": "Report defects"},
        },
        {
            "step": "1.2", "task": "Paint masonry surfaces",
            "ccvs_code": "CHM-H6", "hazards": ["Chemical exposure"],
            "controls": ["Wear respirator"], "admin": [], "hold_points": [],
            "stop_work": [],
            "monitoring": {
                "critical_control": "SDS on site, ventilation confirmed",
                "who_checks": "Supervisor", "who": "Supervisor",
                "frequency": "daily",
                "what_to_look_for": "SDS visible", "evidence": "SDS visible",
            },
            "responsibility": {"SUP": "Check PPE", "WKR": "Wear RPE"},
        },
        {
            "step": "1.3", "task": "Dismantle scaffold and demobilise",
            "ccvs_code": "WAH-H6", "hazards": ["Fall from height"],
            "controls": ["Wear harness"], "admin": [], "hold_points": [],
            "stop_work": [],
            "monitoring": {
                "critical_control": "Exclusion zone barriers in place",
                "who_checks": "Supervisor", "who": "Supervisor",
                "frequency": "daily",
                "what_to_look_for": "Barriers intact", "evidence": "Barriers intact",
            },
            "responsibility": {"SUP": "Supervise", "WKR": "Follow plan"},
        },
    ]


def _failing_tasks():
    """Return tasks that will trigger issue-gate failures."""
    tasks = _clean_tasks()
    # Make task 2 have SIL code but chemical monitoring → alignment fail
    tasks[1]["ccvs_code"] = "SIL-H6"
    tasks[1]["monitoring"]["critical_control"] = "SDS on site"  # SIL should have dust evidence
    # Add a task with N/A ccvs but hazards → completeness fail
    tasks.append({
        "step": "1.4", "task": "Repair concrete",
        "ccvs_code": "N/A", "hazards": ["Silica dust"],
        "controls": ["Wear mask"], "admin": [], "hold_points": [],
        "stop_work": [],
        "monitoring": {
            "critical_control": "Dust extraction", "who_checks": "Supervisor",
            "who": "Supervisor", "frequency": "daily",
            "what_to_look_for": "Extraction running", "evidence": "Extraction running",
        },
        "responsibility": {"SUP": "Check", "WKR": "Report"},
    })
    return tasks


# ── Phase 1: Validator wrapper ───────────────────────────────────────────────

class TestValidatorStatus:
    def test_pass_internal_on_clean_tasks(self, tmp_path):
        tasks = _clean_tasks()
        jp = tmp_path / "clean.json"
        jp.write_text(json.dumps({"tasks": tasks}), encoding="utf-8")
        result = run_internal_validator(
            json_path=str(jp),
            stream_config=StreamConfig(stage=Stage.BENCHMARK, wah_threshold=90),
        )
        # No hard failures with relaxed WAH threshold → PASS or ESCALATE
        assert result.status in (ValidatorStatus.PASS_INTERNAL, ValidatorStatus.ESCALATE_EXTERNAL)
        assert len(result.failing_checks) == 0

    def test_retry_internal_on_fixable_defects(self, tmp_path):
        tasks = _failing_tasks()
        jp = tmp_path / "fail.json"
        jp.write_text(json.dumps({"tasks": tasks}), encoding="utf-8")
        result = run_internal_validator(
            json_path=str(jp),
            stream_config=StreamConfig(stage=Stage.BENCHMARK),
        )
        assert result.status == ValidatorStatus.RETRY_INTERNAL
        assert len(result.failing_checks) > 0
        assert result.retry_recommended is True

    def test_escalate_on_review_only(self, tmp_path):
        """Tasks with no hard fails but review items → ESCALATE."""
        tasks = _clean_tasks()
        jp = tmp_path / "review.json"
        jp.write_text(json.dumps({"tasks": tasks}), encoding="utf-8")
        # At benchmark stage, clean tasks may have review items
        result = run_internal_validator(
            json_path=str(jp),
            stream_config=StreamConfig(stage=Stage.BENCHMARK),
        )
        # Should be PASS or ESCALATE (not RETRY)
        assert result.status != ValidatorStatus.RETRY_INTERNAL


class TestDefectClassification:
    def test_ccvs_alignment_is_deterministic(self):
        dt = _classify_defect("ccvs_alignment", "no dust evidence")
        assert dt == DefectType.DETERMINISTIC_FIX

    def test_wah_percentage_is_prompt(self):
        dt = _classify_defect("wah_percentage", "WAH: 8/10")
        assert dt == DefectType.PROMPT_DECOMPOSER_FIX

    def test_expert_keyword_overrides(self):
        dt = _classify_defect("ccvs_alignment", "requires consultant manual review")
        assert dt == DefectType.EXPERT_REVIEW_ONLY

    def test_unknown_check_is_case_specific(self):
        dt = _classify_defect("unknown_check", "something")
        assert dt == DefectType.CASE_SPECIFIC_FIX

    def test_fixable_deterministic(self):
        assert _is_fixable(DefectType.DETERMINISTIC_FIX) is True

    def test_not_fixable_expert(self):
        assert _is_fixable(DefectType.EXPERT_REVIEW_ONLY) is False

    def test_not_fixable_prompt(self):
        assert _is_fixable(DefectType.PROMPT_DECOMPOSER_FIX) is False


class TestValidatorResult:
    def test_summary_contains_status(self):
        r = ValidatorResult(
            status=ValidatorStatus.PASS_INTERNAL,
            failing_checks=[],
            review_checks=[],
            suggested_action="Ready",
        )
        assert "PASS_INTERNAL" in r.summary()

    def test_summary_contains_defects(self):
        r = ValidatorResult(
            status=ValidatorStatus.RETRY_INTERNAL,
            failing_checks=["ccvs_alignment: mismatch"],
            defect_classifications=[{
                "check": "ccvs_alignment",
                "detail": "mismatch",
                "type": "deterministic_fix",
            }],
        )
        s = r.summary()
        assert "deterministic_fix" in s
        assert "ccvs_alignment" in s


# ── Phase 2: Retry orchestrator ──────────────────────────────────────────────

class TestValidatorLoop:
    def test_clean_tasks_pass_immediately(self, tmp_path):
        tasks = _clean_tasks()
        jp = tmp_path / "clean.json"
        jp.write_text(json.dumps({"tasks": tasks}), encoding="utf-8")
        result = run_validator_loop(
            json_path=str(jp),
            stream_config=StreamConfig(stage=Stage.BENCHMARK),
            max_retries=2,
        )
        assert result.status != ValidatorStatus.RETRY_INTERNAL

    def test_failing_tasks_return_retry_or_escalate(self, tmp_path):
        tasks = _failing_tasks()
        jp = tmp_path / "fail.json"
        jp.write_text(json.dumps({"tasks": tasks}), encoding="utf-8")
        result = run_validator_loop(
            json_path=str(jp),
            stream_config=StreamConfig(stage=Stage.BENCHMARK),
            max_retries=0,  # no retries → should escalate
        )
        assert result.status == ValidatorStatus.ESCALATE_EXTERNAL
        # Defects should be marked as limit reached
        limit_defects = [
            dc for dc in result.defect_classifications
            if dc["type"] == DefectType.DETERMINISTIC_LIMIT_REACHED.value
        ]
        assert len(limit_defects) > 0

    def test_max_retries_constant(self):
        assert MAX_RETRIES == 2

    def test_stream_config_defaults(self):
        sc = StreamConfig()
        assert sc.stage == Stage.BENCHMARK
        assert sc.wah_threshold == 50
        assert sc.allowed_keywords == ()


# ── Integration: real benchmark output ───────────────────────────────────────

class TestRealBenchmarkValidation:
    @pytest.fixture(autouse=True)
    def _check_files(self):
        self.json = "src/outputs/SWMS_Lingate_Benchmark.json"
        if not os.path.exists(self.json):
            pytest.skip("Lingate benchmark output not available")

    def test_lingate_validates(self):
        result = run_internal_validator(
            json_path=self.json,
            stream_config=StreamConfig(
                stage=Stage.BENCHMARK,
                allowed_keywords=("waterproof", "membrane"),
            ),
        )
        assert isinstance(result, ValidatorResult)
        assert result.status in (
            ValidatorStatus.PASS_INTERNAL,
            ValidatorStatus.ESCALATE_EXTERNAL,
            ValidatorStatus.RETRY_INTERNAL,
        )

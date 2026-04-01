"""
tests/test_batch_harness.py — Tests for the batch comparison harness.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.run_batch_harness import (
    BatchReport,
    JobResult,
    RunOptions,
    _estimate_cost,
    build_summary,
    discover_briefs,
    format_markdown,
    load_brief,
)


# ── Discovery ───────────────────────────────────────────────────────────────

class TestDiscovery:
    def test_discover_finds_briefs(self):
        briefs = discover_briefs()
        assert len(briefs) >= 11

    def test_discover_returns_paths(self):
        briefs = discover_briefs()
        for b in briefs:
            assert b.suffix == ".json"
            assert b.exists()

    def test_load_brief_has_required_fields(self):
        briefs = discover_briefs()
        brief = load_brief(briefs[0])
        assert "customer" in brief
        assert "job_type" in brief


# ── Summary ─────────────────────────────────────────────────────────────────

class TestSummary:
    def _make_results(self) -> list[JobResult]:
        return [
            JobResult(brief_id="job_a", customer="A", job_type="new_build",
                      task_count=10, validator_status="PASS_INTERNAL",
                      gate_fail=0, gate_review=3, elapsed_seconds=45.0,
                      control_writer_input_tokens=5000, control_writer_output_tokens=2000,
                      control_writer_calls=10, control_writer_estimated_cost=0.012),
            JobResult(brief_id="job_b", customer="B", job_type="civil",
                      task_count=8, validator_status="RETRY_INTERNAL",
                      gate_fail=2, gate_review=5, elapsed_seconds=60.0,
                      control_writer_input_tokens=4000, control_writer_output_tokens=1500,
                      control_writer_calls=8, control_writer_estimated_cost=0.0092),
            JobResult(brief_id="job_c", customer="C", job_type="remedial",
                      task_count=12, validator_status="ESCALATE_EXTERNAL",
                      gate_fail=0, gate_review=4, elapsed_seconds=50.0,
                      control_writer_input_tokens=6000, control_writer_output_tokens=2500,
                      control_writer_calls=12, control_writer_estimated_cost=0.0148),
        ]

    def test_total_counts(self):
        s = build_summary(self._make_results())
        assert s["total_jobs"] == 3
        assert s["completed"] == 3

    def test_validator_breakdown(self):
        s = build_summary(self._make_results())
        assert s["validator_pass_internal"] == 1
        assert s["validator_retry_internal"] == 1
        assert s["validator_escalate_external"] == 1

    def test_gate_totals(self):
        s = build_summary(self._make_results())
        assert s["total_gate_fails"] == 2
        assert s["total_gate_reviews"] == 12

    def test_zero_fail_count(self):
        s = build_summary(self._make_results())
        assert s["zero_fail_jobs"] == 2

    def test_most_fails_job(self):
        s = build_summary(self._make_results())
        assert s["most_fails_job"] == "job_b"

    def test_empty_results(self):
        s = build_summary([])
        assert s["total_jobs"] == 0

    def test_errored_excluded(self):
        results = [
            JobResult(brief_id="ok", validator_status="PASS_INTERNAL",
                      gate_fail=0, gate_review=2, elapsed_seconds=30.0),
            JobResult(brief_id="bad", error="SomeError: failed"),
        ]
        s = build_summary(results)
        assert s["completed"] == 1
        assert s["errored"] == 1

    def test_token_cost_summary(self):
        s = build_summary(self._make_results())
        assert s["total_cw_input_tokens"] == 15000
        assert s["total_cw_output_tokens"] == 6000
        assert s["jobs_with_cw_cost_data"] == 3
        assert s["total_cw_estimated_cost"] > 0
        assert s["avg_cw_cost_per_job"] > 0

    def test_reviewer_and_edit_capture_counts(self):
        results = [
            JobResult(brief_id="a", reviewer_status="STRONG_WORKING_DRAFT",
                      edit_capture_available=True),
            JobResult(brief_id="b", reviewer_status=""),
        ]
        s = build_summary(results)
        assert s["jobs_with_reviewer_runs"] == 1
        assert s["jobs_with_edit_capture"] == 1


# ── Cost estimation ─────────────────────────────────────────────────────────

class TestCostEstimation:
    def test_zero_tokens(self):
        assert _estimate_cost(0, 0) == 0.0

    def test_known_cost(self):
        # 1M input @ $0.80 + 1M output @ $4.00 = $4.80
        cost = _estimate_cost(1_000_000, 1_000_000)
        assert cost == pytest.approx(4.80, abs=0.01)

    def test_small_tokens(self):
        cost = _estimate_cost(5000, 2000)
        assert cost > 0
        assert cost < 0.05


# ── Markdown format ─────────────────────────────────────────────────────────

class TestMarkdown:
    def test_markdown_has_header(self):
        report = BatchReport(
            timestamp="2026-04-02T12:00:00Z",
            total_jobs=1, completed=1, concurrency=2,
            results=[{
                "brief_id": "test_job", "customer": "Test", "project": "P",
                "job_type": "civil", "task_count": 8,
                "validator_status": "PASS_INTERNAL",
                "validator_fail_count": 0, "validator_review_count": 2,
                "gate_classification": "REVIEW_INTERNAL",
                "gate_pass": 28, "gate_fail": 0, "gate_review": 4,
                "gate_fail_checks": [], "gate_review_checks": [],
                "escalated": False, "elapsed_seconds": 45.0, "error": "",
                "reviewer_status": "", "reviewer_hard_fails": 0,
                "reviewer_review_items": 0, "docx_rendered": False,
                "edit_capture_available": False, "edit_changed_task_count": 0,
                "edit_average_similarity": 0.0, "edit_changed_responsibilities": 0,
                "edit_major_rewrite": False, "edit_categories": [],
                "control_writer_input_tokens": 5000,
                "control_writer_output_tokens": 2000,
                "control_writer_calls": 8,
                "control_writer_estimated_cost": 0.012,
            }],
            summary=build_summary([
                JobResult(brief_id="test_job", customer="Test", job_type="civil",
                          task_count=8, validator_status="PASS_INTERNAL",
                          gate_fail=0, gate_review=4, elapsed_seconds=45.0,
                          control_writer_input_tokens=5000,
                          control_writer_output_tokens=2000,
                          control_writer_calls=8,
                          control_writer_estimated_cost=0.012),
            ]),
        )
        md = format_markdown(report)
        assert "Batch Comparison Report" in md
        assert "test_job" in md
        assert "CW Cost" in md
        assert "Concurrency" in md
        assert "Control Writer Cost" in md


# ── Report structure ────────────────────────────────────────────────────────

class TestReportStructure:
    def test_batch_report_serializes(self):
        from dataclasses import asdict
        report = BatchReport(
            timestamp="2026-04-02T12:00:00Z",
            total_jobs=1, completed=1, concurrency=2,
            results=[{"brief_id": "x"}],
            summary={"total_jobs": 1},
        )
        s = json.dumps(asdict(report))
        assert "x" in s

    def test_job_result_has_optional_fields(self):
        from dataclasses import asdict
        r = JobResult(
            brief_id="test", customer="C", gate_fail=2,
            reviewer_status="STRONG_WORKING_DRAFT",
            control_writer_estimated_cost=0.015,
            edit_capture_available=True,
        )
        d = asdict(r)
        assert d["reviewer_status"] == "STRONG_WORKING_DRAFT"
        assert d["control_writer_estimated_cost"] == 0.015
        assert d["edit_capture_available"] is True

    def test_backward_compatible_fields(self):
        """Original fields still present."""
        from dataclasses import asdict
        r = JobResult(brief_id="t", gate_fail=1, gate_review=3)
        d = asdict(r)
        assert "gate_fail" in d
        assert "gate_review" in d
        assert "gate_fail_checks" in d
        assert "elapsed_seconds" in d


# ── RunOptions ──────────────────────────────────────────────────────────────

class TestRunOptions:
    def test_defaults_all_false(self):
        o = RunOptions()
        assert o.with_reviewer is False
        assert o.with_docx is False
        assert o.with_edit_capture is False

    def test_edit_capture_missing_artifact(self):
        """When no reviewed_docx_path in brief, edit capture should be skipped gracefully."""
        r = JobResult(brief_id="no_edit")
        assert r.edit_capture_available is False
        assert r.edit_changed_task_count == 0


# ── Token tracking in control writer ────────────────────────────────────────

class TestControlWriterTokenTracking:
    def test_reset_and_get(self):
        from agents.control_writer import get_token_usage, reset_token_usage
        reset_token_usage()
        usage = get_token_usage()
        assert usage["input_tokens"] == 0
        assert usage["output_tokens"] == 0
        assert usage["calls"] == 0

    def test_record_usage(self):
        from agents.control_writer import _record_usage, get_token_usage, reset_token_usage

        class FakeUsage:
            input_tokens = 100
            output_tokens = 50

        class FakeMessage:
            usage = FakeUsage()

        reset_token_usage()
        _record_usage(FakeMessage())
        _record_usage(FakeMessage())
        usage = get_token_usage()
        assert usage["input_tokens"] == 200
        assert usage["output_tokens"] == 100
        assert usage["calls"] == 2

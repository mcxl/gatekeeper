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
    build_summary,
    discover_briefs,
    format_markdown,
    load_brief,
)


# ── Discovery ───────────────────────────────────────────────────────────────

class TestDiscovery:
    def test_discover_finds_briefs(self):
        briefs = discover_briefs()
        assert len(briefs) >= 11  # C1-C11

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
        assert "scope_of_works" in brief or "project" in brief


# ── Summary ─────────────────────────────────────────────────────────────────

class TestSummary:
    def _make_results(self) -> list[JobResult]:
        return [
            JobResult(brief_id="job_a", customer="A", job_type="new_build",
                      task_count=10, validator_status="PASS_INTERNAL",
                      gate_fail=0, gate_review=3, elapsed_seconds=45.0),
            JobResult(brief_id="job_b", customer="B", job_type="civil",
                      task_count=8, validator_status="RETRY_INTERNAL",
                      gate_fail=2, gate_review=5, elapsed_seconds=60.0),
            JobResult(brief_id="job_c", customer="C", job_type="remedial",
                      task_count=12, validator_status="ESCALATE_EXTERNAL",
                      gate_fail=0, gate_review=4, elapsed_seconds=50.0),
        ]

    def test_total_counts(self):
        s = build_summary(self._make_results())
        assert s["total_jobs"] == 3
        assert s["completed"] == 3
        assert s["errored"] == 0

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

    def test_averages(self):
        s = build_summary(self._make_results())
        assert s["avg_gate_fails"] == pytest.approx(0.7, abs=0.1)
        assert s["avg_elapsed_seconds"] == pytest.approx(51.7, abs=0.1)

    def test_empty_results(self):
        s = build_summary([])
        assert s["total_jobs"] == 0
        assert s["completed"] == 0

    def test_errored_excluded(self):
        results = [
            JobResult(brief_id="ok", validator_status="PASS_INTERNAL",
                      gate_fail=0, gate_review=2, elapsed_seconds=30.0),
            JobResult(brief_id="bad", error="SomeError: failed"),
        ]
        s = build_summary(results)
        assert s["completed"] == 1
        assert s["errored"] == 1


# ── Markdown format ─────────────────────────────────────────────────────────

class TestMarkdown:
    def test_markdown_has_header(self):
        report = BatchReport(
            timestamp="2026-04-01T12:00:00Z",
            total_jobs=1,
            completed=1,
            results=[{
                "brief_id": "test_job", "customer": "Test", "project": "P",
                "job_type": "civil", "task_count": 8,
                "validator_status": "PASS_INTERNAL",
                "validator_fail_count": 0, "validator_review_count": 2,
                "gate_classification": "REVIEW_INTERNAL",
                "gate_pass": 28, "gate_fail": 0, "gate_review": 4,
                "gate_fail_checks": [], "gate_review_checks": [],
                "escalated": False, "elapsed_seconds": 45.0, "error": "",
            }],
            summary=build_summary([
                JobResult(brief_id="test_job", customer="Test", job_type="civil",
                          task_count=8, validator_status="PASS_INTERNAL",
                          gate_fail=0, gate_review=4, elapsed_seconds=45.0),
            ]),
        )
        md = format_markdown(report)
        assert "Batch Comparison Report" in md
        assert "test_job" in md
        assert "PASS_INTERNAL" in md
        assert "Zero-FAIL" in md

    def test_markdown_table_rows(self):
        results = [
            {"brief_id": f"job_{i}", "customer": f"C{i}", "project": "P",
             "job_type": "new_build", "task_count": 10,
             "validator_status": "RETRY_INTERNAL",
             "validator_fail_count": 1, "validator_review_count": 3,
             "gate_classification": "FAIL_INTERNAL",
             "gate_pass": 26, "gate_fail": 1, "gate_review": 5,
             "gate_fail_checks": ["ccvs_completeness: N/A"], "gate_review_checks": [],
             "escalated": False, "elapsed_seconds": 50.0, "error": ""}
            for i in range(3)
        ]
        report = BatchReport(
            timestamp="now", total_jobs=3, completed=3,
            results=results, summary={"zero_fail_jobs": 0},
        )
        md = format_markdown(report)
        assert md.count("job_") == 3


# ── Report structure ────────────────────────────────────────────────────────

class TestReportStructure:
    def test_batch_report_serializes(self):
        from dataclasses import asdict
        report = BatchReport(
            timestamp="2026-04-01T12:00:00Z",
            total_jobs=1, completed=1,
            results=[{"brief_id": "x"}],
            summary={"total_jobs": 1},
        )
        d = asdict(report)
        s = json.dumps(d)
        assert "x" in s

    def test_job_result_serializes(self):
        from dataclasses import asdict
        r = JobResult(brief_id="test", customer="C", gate_fail=2)
        d = asdict(r)
        assert d["gate_fail"] == 2

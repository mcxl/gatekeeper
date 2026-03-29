"""
tests/test_regression_runner.py — Thin tests for the regression runner module.
Verifies the runner can be imported and produces structured results.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.regression_runner import (
    RegressionReport, StreamReport, StreamResult,
    run_regression, _STREAMS,
)


class TestRegressionRunnerStructure:
    def test_streams_defined(self):
        assert len(_STREAMS) >= 4

    def test_all_streams_have_name(self):
        for s in _STREAMS:
            assert "name" in s
            assert "product_mode" in s

    def test_report_summary_is_string(self):
        report = RegressionReport(streams=[
            StreamReport("Test", "SWMS", StreamResult.PASS, 5, 5, 0),
        ])
        s = report.summary()
        assert "ALL PASS" in s
        assert "Test" in s

    def test_report_all_pass_true(self):
        report = RegressionReport(streams=[
            StreamReport("A", "SWMS", StreamResult.PASS, 1, 1, 0),
            StreamReport("B", "RA", StreamResult.PASS, 1, 1, 0),
        ])
        assert report.all_pass is True

    def test_report_all_pass_false_on_failure(self):
        report = RegressionReport(streams=[
            StreamReport("A", "SWMS", StreamResult.PASS, 1, 1, 0),
            StreamReport("B", "RA", StreamResult.FAIL, 1, 0, 1),
        ])
        assert report.all_pass is False

    def test_total_tests(self):
        report = RegressionReport(streams=[
            StreamReport("A", "SWMS", StreamResult.PASS, 10, 10, 0),
            StreamReport("B", "RA", StreamResult.PASS, 5, 5, 0),
        ])
        assert report.total_tests == 15


class TestRegressionRunnerLive:
    """Run the actual regression runner on RA streams (fastest subset)."""

    def test_ra_streams_pass(self):
        report = run_regression(stream_filter="ra")
        assert len(report.streams) >= 2
        assert report.all_pass, report.summary()
        assert report.total_tests > 0

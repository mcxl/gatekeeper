#!/usr/bin/env python3
"""
src/regression_runner.py — Closed-stream benchmark regression runner.

Runs all regression checks for closed benchmark streams in one invocation.
Pure Python, no API calls. Returns structured pass/fail per stream.

Streams covered:
  1. Facade remedial SWMS (reference jobs 01-08 + renderer fixtures)
  2. Data centre RA (TestDataCentreRetrofit)
  3. Withers Road RA (TestCivilInfrastructure)
  4. Withers Road control pack (TestBuildControlPack + renderer + endpoint)

Usage:
    python src/regression_runner.py           # Run all closed streams
    python src/regression_runner.py --stream ra  # Run RA streams only
    python src/regression_runner.py --verbose    # Show individual test results
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class StreamResult(Enum):
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass
class StreamReport:
    name: str
    product_mode: str
    result: StreamResult = StreamResult.PASS
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    detail: str = ""


@dataclass
class RegressionReport:
    streams: list[StreamReport] = field(default_factory=list)

    @property
    def all_pass(self) -> bool:
        return all(s.result == StreamResult.PASS for s in self.streams)

    @property
    def total_tests(self) -> int:
        return sum(s.tests_run for s in self.streams)

    def summary(self) -> str:
        status = "ALL PASS" if self.all_pass else "REGRESSION DETECTED"
        lines = [f"Regression Runner: {status} "
                 f"({sum(1 for s in self.streams if s.result == StreamResult.PASS)}"
                 f"/{len(self.streams)} streams, "
                 f"{self.total_tests} tests)"]
        for s in self.streams:
            marker = "OK" if s.result == StreamResult.PASS else "FAIL"
            lines.append(f"  [{marker}] {s.name} ({s.product_mode}) "
                         f"— {s.tests_passed}/{s.tests_run} tests")
            if s.detail:
                lines.append(f"         {s.detail}")
        return "\n".join(lines)


# ── Stream definitions ───────────────────────────────────────────────────────

_STREAMS = [
    {
        "name": "Facade remedial SWMS",
        "product_mode": "SWMS",
        "pytest_args": [
            "tests/test_renderer.py",
            "tests/test_negation_exclusion.py",
        ],
        "filter": None,
        "tags": ["swms"],
    },
    {
        "name": "SWMS reference jobs",
        "product_mode": "SWMS",
        "pytest_args": [],
        "script": "tests/run_reference_jobs.py",
        "tags": ["swms"],
    },
    {
        "name": "Data centre RA",
        "product_mode": "RA",
        "pytest_args": [
            "tests/test_ra_reference_jobs.py::TestDataCentreRetrofit",
            "tests/test_ra_classifier.py",
        ],
        "filter": None,
        "tags": ["ra"],
    },
    {
        "name": "Withers Road RA",
        "product_mode": "RA",
        "pytest_args": [
            "tests/test_ra_reference_jobs.py::TestFacadeRemedial",
            "tests/test_ra_reference_jobs.py::TestCivilInfrastructure",
        ],
        "filter": None,
        "tags": ["ra"],
    },
    {
        "name": "Withers Road control pack",
        "product_mode": "Project WHS",
        "pytest_args": [
            "tests/test_control_pack.py",
            "tests/test_control_pack_renderer.py",
            "tests/test_control_pack_endpoint.py",
        ],
        "filter": None,
        "tags": ["project"],
    },
]


# ── Runner ───────────────────────────────────────────────────────────────────

def _run_pytest(args: list[str], verbose: bool = False) -> tuple[int, int, int]:
    """Run pytest with given args. Returns (total, passed, failed)."""
    cmd = [sys.executable, "-m", "pytest"] + args + ["-q", "--tb=no", "--no-header"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    output = result.stdout + result.stderr

    # Parse "X passed, Y failed" from pytest output
    passed = failed = 0
    for line in output.splitlines():
        line = line.strip()
        if "passed" in line or "failed" in line:
            import re
            m_passed = re.search(r'(\d+)\s+passed', line)
            m_failed = re.search(r'(\d+)\s+failed', line)
            if m_passed:
                passed = int(m_passed.group(1))
            if m_failed:
                failed = int(m_failed.group(1))

    if verbose and result.returncode != 0:
        return (passed + failed, passed, failed)

    return (passed + failed, passed, failed)


def _run_script(script: str) -> tuple[int, int, int]:
    """Run a standalone script. Returns (total, passed, failed)."""
    result = subprocess.run(
        [sys.executable, script],
        capture_output=True, text=True, timeout=60,
    )
    output = result.stdout
    # Parse "Results: X/Y passed, Z failed" from run_reference_jobs.py
    import re
    m = re.search(r'(\d+)/(\d+)\s+passed,\s+(\d+)\s+failed', output)
    if m:
        passed = int(m.group(1))
        total = int(m.group(2))
        failed = int(m.group(3))
        return (total, passed, failed)
    # Fallback: if script exits 0, assume pass
    return (1, 1 if result.returncode == 0 else 0, 0 if result.returncode == 0 else 1)


def run_regression(
    stream_filter: Optional[str] = None,
    verbose: bool = False,
) -> RegressionReport:
    """Run regression checks for closed streams.

    Args:
        stream_filter: Optional filter — "swms", "ra", "project", or None for all.
        verbose: Show individual test failures.

    Returns:
        RegressionReport with per-stream results.
    """
    report = RegressionReport()

    for stream_def in _STREAMS:
        # Apply filter
        if stream_filter and stream_filter not in stream_def.get("tags", []):
            continue

        sr = StreamReport(
            name=stream_def["name"],
            product_mode=stream_def["product_mode"],
        )

        try:
            if "script" in stream_def:
                total, passed, failed = _run_script(stream_def["script"])
            else:
                total, passed, failed = _run_pytest(
                    stream_def["pytest_args"], verbose=verbose
                )
            sr.tests_run = total
            sr.tests_passed = passed
            sr.tests_failed = failed
            sr.result = StreamResult.PASS if failed == 0 else StreamResult.FAIL
            if failed > 0:
                sr.detail = f"{failed} test(s) failed"
        except subprocess.TimeoutExpired:
            sr.result = StreamResult.FAIL
            sr.detail = "Timeout"
        except Exception as e:
            sr.result = StreamResult.FAIL
            sr.detail = str(e)

        report.streams.append(sr)

    return report


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Closed-stream benchmark regression runner"
    )
    parser.add_argument(
        "--stream", choices=["swms", "ra", "project"],
        help="Filter to a specific product mode"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Show detailed failure output"
    )
    args = parser.parse_args()

    report = run_regression(
        stream_filter=args.stream,
        verbose=args.verbose,
    )
    print(report.summary())
    sys.exit(0 if report.all_pass else 1)


if __name__ == "__main__":
    main()

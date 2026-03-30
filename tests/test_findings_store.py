"""
tests/test_findings_store.py — Tests for the append-only findings store.
"""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.findings_store import FindingRecord, append_finding, load_findings, _FINDINGS_FILE, _DATA_DIR


@pytest.fixture
def clean_store(tmp_path, monkeypatch):
    """Redirect findings store to a temp directory."""
    import core.findings_store as fs
    monkeypatch.setattr(fs, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(fs, "_FINDINGS_FILE", tmp_path / "findings_log.jsonl")
    return tmp_path / "findings_log.jsonl"


class TestAppendAndLoad:
    def test_append_one_load_back(self, clean_store):
        rec = FindingRecord(
            stream_name="test", job_type="remedial", task_name="Remove membrane",
            defect_type="deterministic_fix", check_name="ccvs_alignment",
            finding_text="SIL expected but CHM found", source="validator",
            severity="hard_fail",
        )
        append_finding(rec)
        results = load_findings()
        assert len(results) == 1
        assert results[0].stream_name == "test"
        assert results[0].finding_text == "SIL expected but CHM found"

    def test_append_multiple_filter_by_job_type(self, clean_store):
        append_finding(FindingRecord(stream_name="a", job_type="remedial", source="validator"))
        append_finding(FindingRecord(stream_name="b", job_type="new_build", source="validator"))
        append_finding(FindingRecord(stream_name="c", job_type="remedial", source="validator"))
        results = load_findings(job_type="remedial")
        assert len(results) == 2

    def test_filter_resolved_false(self, clean_store):
        append_finding(FindingRecord(stream_name="a", resolved=False, source="validator"))
        append_finding(FindingRecord(stream_name="b", resolved=True, source="validator"))
        results = load_findings(resolved=False)
        assert len(results) == 1
        assert results[0].stream_name == "a"

    def test_filter_by_source(self, clean_store):
        append_finding(FindingRecord(stream_name="a", source="validator"))
        append_finding(FindingRecord(stream_name="b", source="reviewer_agent"))
        results = load_findings(source="validator")
        assert len(results) == 1


class TestFingerprint:
    def test_same_logical_defect_same_fingerprint(self, clean_store):
        r1 = FindingRecord(defect_type="deterministic_fix", check_name="ccvs",
                           job_type="remedial", task_name="Remove membrane")
        r2 = FindingRecord(defect_type="deterministic_fix", check_name="ccvs",
                           job_type="remedial", task_name="Remove membrane")
        assert r1.fingerprint == r2.fingerprint

    def test_different_task_different_fingerprint(self, clean_store):
        r1 = FindingRecord(defect_type="deterministic_fix", check_name="ccvs",
                           job_type="remedial", task_name="Remove membrane")
        r2 = FindingRecord(defect_type="deterministic_fix", check_name="ccvs",
                           job_type="remedial", task_name="Apply membrane")
        assert r1.fingerprint != r2.fingerprint

    def test_fingerprint_excludes_timestamp(self, clean_store):
        r1 = FindingRecord(defect_type="x", check_name="y", job_type="z",
                           task_name="t", timestamp="2026-01-01T00:00:00")
        r2 = FindingRecord(defect_type="x", check_name="y", job_type="z",
                           task_name="t", timestamp="2026-12-31T23:59:59")
        # Force recompute since __post_init__ already ran with the timestamps
        assert r1._compute_fingerprint() == r2._compute_fingerprint()


class TestEdgeCases:
    def test_load_empty_file(self, clean_store):
        assert load_findings() == []

    def test_append_creates_directory(self, tmp_path, monkeypatch):
        import core.findings_store as fs
        new_dir = tmp_path / "new_subdir" / "data"
        monkeypatch.setattr(fs, "_DATA_DIR", new_dir)
        monkeypatch.setattr(fs, "_FINDINGS_FILE", new_dir / "findings_log.jsonl")
        append_finding(FindingRecord(stream_name="test", source="validator"))
        assert (new_dir / "findings_log.jsonl").exists()

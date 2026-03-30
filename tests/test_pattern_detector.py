"""
tests/test_pattern_detector.py — Tests for the pattern detector.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.findings_store import FindingRecord, append_finding
from core.pattern_detector import RuleCandidate, detect_patterns, load_candidates, _CANDIDATES_FILE


@pytest.fixture
def clean_stores(tmp_path, monkeypatch):
    """Redirect both findings store and candidates file to temp directory."""
    import core.findings_store as fs
    import core.pattern_detector as pd
    monkeypatch.setattr(fs, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(fs, "_FINDINGS_FILE", tmp_path / "findings_log.jsonl")
    monkeypatch.setattr(pd, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(pd, "_CANDIDATES_FILE", tmp_path / "rule_candidates.jsonl")
    return tmp_path


def _make_finding(**kwargs) -> FindingRecord:
    defaults = dict(
        stream_name="test", job_type="remedial", defect_type="deterministic_fix",
        check_name="ccvs_alignment", source="validator", severity="hard_fail",
        finding_text="SIL expected but CHM found",
    )
    defaults.update(kwargs)
    return FindingRecord(**defaults)


class TestDetectPatterns:
    def test_three_findings_same_key_returns_candidate(self, clean_stores):
        for _ in range(3):
            append_finding(_make_finding())
        candidates = detect_patterns(min_occurrences=3)
        assert len(candidates) == 1
        assert candidates[0].occurrences == 3
        assert candidates[0].defect_family == "deterministic_fix"

    def test_two_findings_below_threshold(self, clean_stores):
        for _ in range(2):
            append_finding(_make_finding())
        candidates = detect_patterns(min_occurrences=3)
        assert len(candidates) == 0

    def test_systemic_scores_higher_than_review_flag(self, clean_stores):
        for _ in range(3):
            append_finding(_make_finding(severity="systemic"))
        for _ in range(3):
            append_finding(_make_finding(
                severity="review_flag", check_name="other_check",
            ))
        candidates = detect_patterns(min_occurrences=3)
        assert len(candidates) == 2
        # systemic should be first (higher score)
        assert candidates[0].severity_score > candidates[1].severity_score

    def test_validator_scores_higher_than_reviewer_agent(self, clean_stores):
        for _ in range(3):
            append_finding(_make_finding(source="validator", check_name="chk_a"))
        for _ in range(3):
            append_finding(_make_finding(source="reviewer_agent", check_name="chk_b"))
        candidates = detect_patterns(min_occurrences=3)
        assert len(candidates) == 2
        validator_cand = [c for c in candidates if c.check_name == "chk_a"][0]
        reviewer_cand = [c for c in candidates if c.check_name == "chk_b"][0]
        assert validator_cand.severity_score > reviewer_cand.severity_score

    def test_external_review_scores_highest(self, clean_stores):
        for _ in range(3):
            append_finding(_make_finding(source="external_review", check_name="ext"))
        for _ in range(3):
            append_finding(_make_finding(source="validator", check_name="val"))
        candidates = detect_patterns(min_occurrences=3)
        ext = [c for c in candidates if c.check_name == "ext"][0]
        val = [c for c in candidates if c.check_name == "val"][0]
        assert ext.severity_score > val.severity_score

    def test_candidates_written_to_jsonl(self, clean_stores):
        for _ in range(3):
            append_finding(_make_finding())
        detect_patterns(min_occurrences=3)
        candidates_file = clean_stores / "rule_candidates.jsonl"
        assert candidates_file.exists()
        lines = [l for l in candidates_file.read_text().splitlines() if l.strip()]
        assert len(lines) == 1

    def test_unresolved_only_excludes_resolved(self, clean_stores):
        for _ in range(3):
            append_finding(_make_finding(resolved=True))
        candidates = detect_patterns(min_occurrences=3, unresolved_only=True)
        assert len(candidates) == 0

    def test_empty_findings_returns_empty(self, clean_stores):
        candidates = detect_patterns()
        assert candidates == []


class TestLoadCandidates:
    def test_load_by_status(self, clean_stores):
        for _ in range(3):
            append_finding(_make_finding())
        detect_patterns(min_occurrences=3)
        pending = load_candidates(status="pending")
        assert len(pending) == 1
        approved = load_candidates(status="approved_for_implementation")
        assert len(approved) == 0

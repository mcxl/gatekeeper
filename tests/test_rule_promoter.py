"""
tests/test_rule_promoter.py — Tests for the rule promoter.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.findings_store import FindingRecord, append_finding
from core.pattern_detector import RuleCandidate, detect_patterns, load_candidates
from core.rule_promoter import (
    PromotionProposal,
    list_candidates,
    approve_candidate,
    reject_candidate,
    _PROMOTION_LOG,
)


@pytest.fixture
def clean_stores(tmp_path, monkeypatch):
    """Redirect all stores to temp directory."""
    import core.findings_store as fs
    import core.pattern_detector as pd
    import core.rule_promoter as rp
    monkeypatch.setattr(fs, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(fs, "_FINDINGS_FILE", tmp_path / "findings_log.jsonl")
    monkeypatch.setattr(pd, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(pd, "_CANDIDATES_FILE", tmp_path / "rule_candidates.jsonl")
    monkeypatch.setattr(rp, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(rp, "_PROMOTION_LOG", tmp_path / "promotion_log.jsonl")
    return tmp_path


def _seed_candidate(clean_stores) -> str:
    """Seed findings + detect to create a candidate. Return candidate_id."""
    for _ in range(3):
        append_finding(FindingRecord(
            stream_name="test", job_type="remedial", defect_type="deterministic_fix",
            check_name="ccvs_alignment", source="validator", severity="hard_fail",
            finding_text="SIL expected but CHM found",
        ))
    candidates = detect_patterns(min_occurrences=3)
    assert len(candidates) == 1
    return candidates[0].candidate_id


class TestListCandidates:
    def test_list_pending(self, clean_stores):
        _seed_candidate(clean_stores)
        pending = list_candidates(status="pending")
        assert len(pending) == 1

    def test_list_approved_empty(self, clean_stores):
        _seed_candidate(clean_stores)
        approved = list_candidates(status="approved_for_implementation")
        assert len(approved) == 0


class TestApproveCandidate:
    def test_returns_proposal_with_all_fields(self, clean_stores):
        cid = _seed_candidate(clean_stores)
        proposal = approve_candidate(cid)
        assert isinstance(proposal, PromotionProposal)
        assert proposal.candidate_id == cid
        assert proposal.target != ""
        assert len(proposal.files_to_change) > 0
        assert proposal.proposal_text != ""
        assert len(proposal.implementation_notes) > 0
        assert proposal.generated_patch_stub != ""
        assert proposal.status == "approved_for_implementation"

    def test_updates_candidate_status(self, clean_stores):
        cid = _seed_candidate(clean_stores)
        approve_candidate(cid)
        approved = load_candidates(status="approved_for_implementation")
        assert len(approved) == 1
        assert approved[0].candidate_id == cid

    def test_writes_to_promotion_log(self, clean_stores):
        cid = _seed_candidate(clean_stores)
        approve_candidate(cid)
        log_file = clean_stores / "promotion_log.jsonl"
        assert log_file.exists()
        entries = [json.loads(l) for l in log_file.read_text().splitlines() if l.strip()]
        assert len(entries) == 1
        assert entries[0]["action"] == "approve"
        assert entries[0]["candidate_id"] == cid

    def test_does_not_modify_agents_or_src(self, clean_stores, tmp_path):
        """approve_candidate must NOT modify any file in agents/ or src/."""
        # Create sentinel files
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        sentinel = agents_dir / "control_writer.py"
        sentinel.write_text("original")
        src_dir = tmp_path / "src"
        src_dir.mkdir(exist_ok=True)
        src_sentinel = src_dir / "issue_gate.py"
        src_sentinel.write_text("original")

        cid = _seed_candidate(clean_stores)
        approve_candidate(cid)

        assert sentinel.read_text() == "original"
        assert src_sentinel.read_text() == "original"

    def test_does_not_modify_prompts(self, clean_stores, tmp_path):
        """approve_candidate must NOT modify any file in prompts/."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        sentinel = prompts_dir / "swms.py"
        sentinel.write_text("original")

        cid = _seed_candidate(clean_stores)
        approve_candidate(cid)

        assert sentinel.read_text() == "original"

    def test_does_not_mark_findings_resolved(self, clean_stores):
        cid = _seed_candidate(clean_stores)
        approve_candidate(cid)
        from core.findings_store import load_findings
        findings = load_findings(resolved=False)
        assert len(findings) == 3  # all still unresolved

    def test_patch_stub_non_empty_for_auto_generatable(self, clean_stores):
        cid = _seed_candidate(clean_stores)
        proposal = approve_candidate(cid)
        # ccvs_alignment is in _AUTO_GENERATABLE_CHECKS
        assert proposal.generated_patch_stub != ""


class TestRejectCandidate:
    def test_updates_status_to_rejected(self, clean_stores):
        cid = _seed_candidate(clean_stores)
        reject_candidate(cid, "not actionable")
        rejected = load_candidates(status="rejected")
        assert len(rejected) == 1
        assert rejected[0].candidate_id == cid

    def test_writes_reason_to_promotion_log(self, clean_stores):
        cid = _seed_candidate(clean_stores)
        reject_candidate(cid, "not actionable")
        log_file = clean_stores / "promotion_log.jsonl"
        entries = [json.loads(l) for l in log_file.read_text().splitlines() if l.strip()]
        assert len(entries) == 1
        assert entries[0]["action"] == "reject"
        assert entries[0]["reason"] == "not actionable"

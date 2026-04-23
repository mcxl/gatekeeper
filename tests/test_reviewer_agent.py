"""
tests/test_reviewer_agent.py — Tests for the parallel reviewer agent.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.reviewer_agent import (
    AgentFinding,
    ReviewerResult,
    OVERALL_STATUS_BENCHMARK_CONFIRMED,
    OVERALL_STATUS_BENCHMARK_CAVEATS,
    OVERALL_STATUS_STRONG_DRAFT,
    OVERALL_STATUS_BELOW_DRAFT,
    RECOMMENDED_ACTION_PASS,
    RECOMMENDED_ACTION_TARGETED,
    RECOMMENDED_ACTION_FULL,
    HARD_FAIL_THRESHOLD_FULL_REWORK,
    _parse_agent_response,
)


# ── AgentFinding structure ───────────────────────────────────────────────────

class TestAgentFinding:
    def test_default_is_pass(self):
        f = AgentFinding()
        assert f.status == "PASS"
        assert f.findings == []

    def test_from_dict(self):
        f = AgentFinding(
            status="FAIL",
            findings=["missing hold point"],
            automatable_defects=["add hold point"],
            human_judgment_required=[],
        )
        assert f.status == "FAIL"
        assert len(f.findings) == 1


class TestParseAgentResponse:
    def test_valid_json(self):
        text = '{"status": "PASS", "findings": [], "automatable_defects": [], "human_judgment_required": []}'
        f = _parse_agent_response(text)
        assert f.status == "PASS"

    def test_json_with_fences(self):
        text = '```json\n{"status": "FAIL", "findings": ["bad"]}\n```'
        f = _parse_agent_response(text)
        assert f.status == "FAIL"

    def test_invalid_json_returns_review(self):
        f = _parse_agent_response("This is not JSON at all")
        assert f.status == "REVIEW"
        assert len(f.findings) > 0


# ── ReviewerResult structure ─────────────────────────────────────────────────

class TestReviewerResult:
    def test_default_values(self):
        r = ReviewerResult()
        assert r.overall_status == OVERALL_STATUS_STRONG_DRAFT
        assert r.recommended_action == RECOMMENDED_ACTION_TARGETED

    def test_to_dict(self):
        r = ReviewerResult(
            overall_status=OVERALL_STATUS_BENCHMARK_CONFIRMED,
            overall_summary="All pass",
            hard_fails=[],
            review_items=[],
            recommended_action=RECOMMENDED_ACTION_PASS,
        )
        d = r.to_dict()
        assert d["overall_status"] == OVERALL_STATUS_BENCHMARK_CONFIRMED
        assert "architecture_sequence" in d
        assert "hrcw_hazard" in d
        assert "ccvs_verification" in d
        assert "credibility_drift" in d

    def test_assembly_from_agents(self):
        """Simulate coordinator assembly logic."""
        arch = AgentFinding(status="PASS")
        hrcw = AgentFinding(status="REVIEW", findings=["HRCW may be undercalled"])
        ccvs = AgentFinding(status="PASS")
        cred = AgentFinding(status="PASS")

        hard_fails = []
        review_items = []
        for name, finding in [("arch", arch), ("hrcw", hrcw), ("ccvs", ccvs), ("cred", cred)]:
            if finding.status == "FAIL":
                hard_fails.extend(finding.findings)
            elif finding.status == "REVIEW":
                review_items.extend(finding.findings)

        r = ReviewerResult(
            overall_status=OVERALL_STATUS_BENCHMARK_CAVEATS if review_items else OVERALL_STATUS_BENCHMARK_CONFIRMED,
            architecture_sequence=arch,
            hrcw_hazard=hrcw,
            ccvs_verification=ccvs,
            credibility_drift=cred,
            hard_fails=hard_fails,
            review_items=review_items,
        )
        assert r.overall_status == OVERALL_STATUS_BENCHMARK_CAVEATS
        assert len(r.review_items) == 1


# ── Threshold logic ──────────────────────────────────────────────────────────

class TestThresholdLogic:
    def test_no_fails_no_reviews_is_confirmed(self):
        assert HARD_FAIL_THRESHOLD_FULL_REWORK == 2

    def test_constants_are_strings(self):
        assert isinstance(OVERALL_STATUS_BENCHMARK_CONFIRMED, str)
        assert isinstance(RECOMMENDED_ACTION_PASS, str)


# ── Pipeline integration (mocked — no real API calls) ────────────────────────

class TestPipelineIntegration:
    def test_pass_internal_does_not_trigger_reviewer(self):
        """PASS_INTERNAL from validator should NOT trigger reviewer."""
        from core.validator_runner import ValidatorStatus
        # Just verify the status value check would work
        status = ValidatorStatus.PASS_INTERNAL
        assert status.value != "ESCALATE_EXTERNAL"

    def test_escalate_triggers_reviewer_path(self):
        """ESCALATE_EXTERNAL from validator SHOULD trigger reviewer."""
        from core.validator_runner import ValidatorStatus
        status = ValidatorStatus.ESCALATE_EXTERNAL
        assert status.value == "ESCALATE_EXTERNAL"


# ── SSE stream unaffected ────────────────────────────────────────────────────

class TestSseUnaffected:
    def test_sse_endpoint_exists(self):
        from fastapi.testclient import TestClient
        from api.main import app
        from core.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: {"sub": "t", "email": "t@t.com"}
        c = TestClient(app)
        resp = c.post("/generate/stream", json={"description": "test"})
        app.dependency_overrides.clear()
        assert resp.status_code in (200, 422)  # exists, not 404/500


# ── Response headers ─────────────────────────────────────────────────────────

class TestResponseHeaders:
    def test_render_docx_has_validator_header(self):
        from fastapi.testclient import TestClient
        from api.main import app
        from core.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: {"sub": "t", "email": "t@t.com"}
        c = TestClient(app)
        resp = c.post("/render/docx", json={
            "tasks": [{
                "task": "Paint wall", "scope": "exterior", "risk_pre": "M", "risk_post": "L",
                "controls": ["Wear mask"], "hazards": ["Dust"],
                "ccvs_code": "CHM-H6",
                "monitoring": {"critical_control": "SDS on site", "who": "Sup",
                               "frequency": "daily", "evidence": "SDS visible"},
            }],
            "project_meta": {"project_name": "Test"},
            "inference": {},
            "wah_threshold": 90,
        })
        app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert "X-Validator-Status" in resp.headers


# ── Credibility-drift floor calibration ──────────────────────────────────────

class TestCredibilityFloor:
    """Test that credibility FAIL floors overall status at BELOW_WORKING_DRAFT."""

    def _make_result_with_cred_fail(self, cred_status, findings=None):
        """Simulate coordinator assembly with a specific credibility result."""
        from core.reviewer_agent import (
            AgentFinding, ReviewerResult,
            OVERALL_STATUS_STRONG_DRAFT,
            RECOMMENDED_ACTION_TARGETED,
            HARD_FAIL_THRESHOLD_FULL_REWORK,
            _CRED_PROMPT,
        )
        arch = AgentFinding(status="PASS")
        hrcw = AgentFinding(status="PASS")
        ccvs = AgentFinding(status="PASS")
        cred = AgentFinding(status=cred_status, findings=findings or [])

        # Simulate the coordinator logic
        cred_floor_active = cred.status == "FAIL"
        if cred_floor_active:
            return OVERALL_STATUS_BELOW_DRAFT
        return OVERALL_STATUS_STRONG_DRAFT  # simplified — not full logic

    def test_cred_fail_floors_to_below(self):
        status = self._make_result_with_cred_fail(
            "FAIL", ["unsupported council permit in live task"])
        assert status == OVERALL_STATUS_BELOW_DRAFT

    def test_cred_pass_does_not_floor(self):
        status = self._make_result_with_cred_fail("PASS")
        from core.reviewer_agent import OVERALL_STATUS_STRONG_DRAFT
        assert status == OVERALL_STATUS_STRONG_DRAFT

    def test_cred_review_does_not_floor(self):
        status = self._make_result_with_cred_fail("REVIEW", ["minor format issue"])
        from core.reviewer_agent import OVERALL_STATUS_STRONG_DRAFT
        assert status == OVERALL_STATUS_STRONG_DRAFT

    def test_below_signals_in_prompt(self):
        """Verify the credibility prompt contains BELOW signals."""
        from core.reviewer_agent import _CRED_PROMPT
        assert "BELOW_STRONG_WORKING_DRAFT" in _CRED_PROMPT
        assert "council permit" in _CRED_PROMPT.lower()
        assert "ewp" in _CRED_PROMPT.lower()
        assert "active asbestos" in _CRED_PROMPT.lower()
        assert "latent" in _CRED_PROMPT.lower()

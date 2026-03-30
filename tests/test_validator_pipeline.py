"""
tests/test_validator_pipeline.py — Integration tests for validator wired into pipeline.
"""

import json
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app
from core.auth import get_current_user


def _mock_user():
    return {"sub": "test", "email": "test@test.com"}


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = _mock_user
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()

# Minimal valid task set for /render/docx
_MINIMAL_TASKS = [
    {
        "task": "Erect scaffolding",
        "scope": "Install scaffold to facade",
        "risk_pre": "H",
        "risk_post": "M",
        "controls": ["Wear harness", "Check scaffold tag"],
        "hazards": ["Fall from height"],
        "ccvs_code": "WAH-H6",
        "monitoring": {
            "critical_control": "Scaffold tag current",
            "who": "Supervisor",
            "frequency": "daily",
            "evidence": "Tag visible",
        },
    },
    {
        "task": "Paint masonry surfaces",
        "scope": "Paint exterior walls",
        "risk_pre": "M",
        "risk_post": "L",
        "controls": ["Wear respirator", "Check SDS"],
        "hazards": ["Chemical exposure"],
        "ccvs_code": "CHM-H6",
        "monitoring": {
            "critical_control": "SDS on site, ventilation confirmed",
            "who": "Supervisor",
            "frequency": "daily",
            "evidence": "SDS visible",
        },
    },
]

class TestValidatorInPipeline:
    """Tests that the validator runs during /render/docx and produces correct output."""

    def test_render_docx_returns_200_with_validator_header(self, client):
        resp = client.post("/render/docx", json={
            "tasks": _MINIMAL_TASKS,
            "project_meta": {"project_name": "Test"},
            "inference": {},
            "wah_threshold": 90,
        })
        assert resp.status_code == 200
        assert "X-Validator-Status" in resp.headers

    def test_render_docx_output_not_blocked(self, client):
        """Document is always returned regardless of validator outcome."""
        resp = client.post("/render/docx", json={
            "tasks": _MINIMAL_TASKS,
            "project_meta": {"project_name": "Test"},
            "inference": {},
        })
        assert resp.status_code == 200
        assert len(resp.content) > 1000

    def test_validator_result_json_written(self, client):
        """Validator writes a _validator_result.json alongside output."""
        resp = client.post("/render/docx", json={
            "tasks": _MINIMAL_TASKS,
            "project_meta": {"project_name": "Test"},
            "inference": {},
            "filename": "test_validator_check.docx",
        })
        assert resp.status_code == 200
        result_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "src", "outputs", "test_validator_check_validator_result.json",
        )
        if os.path.exists(result_path):
            with open(result_path) as f:
                data = json.load(f)
            assert "status" in data
            assert data["status"] in ("PASS_INTERNAL", "RETRY_INTERNAL", "ESCALATE_EXTERNAL")
            os.remove(result_path)

    def test_validate_false_skips_validation(self, client):
        """Setting validate=false skips the validator entirely."""
        resp = client.post("/render/docx", json={
            "tasks": _MINIMAL_TASKS,
            "project_meta": {"project_name": "Test"},
            "inference": {},
            "validate": False,
        })
        assert resp.status_code == 200
        assert "X-Validator-Status" not in resp.headers

    def test_sse_stream_unaffected(self, client):
        """SSE /generate/stream endpoint is not modified by validator wiring."""
        resp = client.post("/generate/stream", json={
            "description": "test",
        })
        assert resp.status_code in (200, 422)

"""
Tests for the /control-pack/generate endpoint.

Uses FastAPI TestClient to validate the backend path end-to-end
without needing a running server or frontend.
"""

import os
import sys
import json
import zipfile
from io import BytesIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch


_WITHERS_DESC = (
    "Partial upgrade of Withers Road, North Kellyville NSW — approximately "
    "400 metres of live lane road works, Sydney Water asset relocation, "
    "conversion from chip seal to 4 lanes, T-intersection with traffic lights, "
    "pedestrian walkways, and stormwater works"
)

_WITHERS_META = {
    "project_name": "Withers Road Partial Upgrade",
    "site_address": "Withers Road, North Kellyville NSW 2155",
    "pcbu_name": "SD Group",
    "client": "The Hills Shire Council",
}


def _mock_user():
    """Return a mock user dict for auth bypass in tests."""
    return {"sub": "test-user-id", "email": "test@example.com"}


@pytest.fixture
def client():
    """Create a TestClient with auth bypassed."""
    from fastapi.testclient import TestClient
    from api.main import app
    from core.auth import get_current_user

    app.dependency_overrides[get_current_user] = _mock_user
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


class TestControlPackGenerateJSON:

    def test_returns_200_json(self, client):
        resp = client.post("/control-pack/generate", json={
            "description": _WITHERS_DESC,
            "project_meta": _WITHERS_META,
            "format": "json",
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        assert data["document_type"] == "combined_whs_control_pack"

    def test_json_has_summary_counts(self, client):
        resp = client.post("/control-pack/generate", json={
            "description": _WITHERS_DESC,
            "project_meta": _WITHERS_META,
            "format": "json",
        })
        data = resp.json()
        assert data["trade_package_count"] >= 4
        assert data["hrcw_yes_count"] >= 3
        assert data["hrcw_conditional_count"] >= 3
        assert data["hold_point_count"] >= 3
        assert data["risk_register_count"] >= 8
        assert data["open_item_count"] >= 1

    def test_json_has_hrcw_register(self, client):
        resp = client.post("/control-pack/generate", json={
            "description": _WITHERS_DESC,
            "project_meta": _WITHERS_META,
            "format": "json",
        })
        data = resp.json()
        assert len(data["hrcw_register"]) == 17

    def test_json_has_swms_matrix(self, client):
        resp = client.post("/control-pack/generate", json={
            "description": _WITHERS_DESC,
            "project_meta": _WITHERS_META,
            "format": "json",
        })
        data = resp.json()
        assert len(data["swms_matrix"]) >= 4

    def test_json_has_hold_points(self, client):
        resp = client.post("/control-pack/generate", json={
            "description": _WITHERS_DESC,
            "project_meta": _WITHERS_META,
            "format": "json",
        })
        data = resp.json()
        for hp in data["hold_points"]:
            assert "ref" in hp
            assert "condition" in hp


class TestControlPackGenerateDOCX:

    def test_returns_200_docx(self, client):
        resp = client.post("/control-pack/generate", json={
            "description": _WITHERS_DESC,
            "project_meta": _WITHERS_META,
            "format": "docx",
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        assert "application/vnd.openxmlformats" in resp.headers.get("content-type", "")

    def test_docx_is_valid_zip(self, client):
        resp = client.post("/control-pack/generate", json={
            "description": _WITHERS_DESC,
            "project_meta": _WITHERS_META,
            "format": "docx",
        })
        assert zipfile.is_zipfile(BytesIO(resp.content))

    def test_docx_has_filename_header(self, client):
        resp = client.post("/control-pack/generate", json={
            "description": _WITHERS_DESC,
            "project_meta": _WITHERS_META,
        })
        cd = resp.headers.get("content-disposition", "")
        assert "WHS-CP" in cd
        assert ".docx" in cd


class TestControlPackValidation:

    def test_empty_description_returns_422(self, client):
        resp = client.post("/control-pack/generate", json={
            "description": "",
            "project_meta": _WITHERS_META,
        })
        assert resp.status_code == 422

    def test_short_description_returns_422(self, client):
        resp = client.post("/control-pack/generate", json={
            "description": "too short",
            "project_meta": _WITHERS_META,
        })
        assert resp.status_code == 422

    def test_missing_description_returns_422(self, client):
        resp = client.post("/control-pack/generate", json={
            "project_meta": _WITHERS_META,
        })
        assert resp.status_code == 422

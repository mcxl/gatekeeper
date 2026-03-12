"""
Tests for authentication on protected endpoints.

T1 — Auth guard
  • Anonymous POST /generate/auto returns 401.
  • Authenticated POST /generate/auto does not return 401.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    from api.main import app
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def auth_client():
    """TestClient with get_current_user overridden to return a fake user."""
    from api.main import app
    from core.auth import get_current_user

    async def _fake_user():
        return {"user_id": "test-user-001", "email": "test@example.com"}

    app.dependency_overrides[get_current_user] = _fake_user
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


# ── T1-A: anonymous request ────────────────────────────────────────────────────

def test_generate_auto_anonymous_returns_401(client):
    """POST /generate/auto without a token must return 401."""
    resp = client.post("/generate/auto", json={"description": "Painting work"})
    assert resp.status_code == 401


# ── T1-B: authenticated request ───────────────────────────────────────────────

def test_generate_auto_authenticated_not_401(auth_client, monkeypatch):
    """POST /generate/auto with a valid token must not return 401."""
    from core import orchestrator

    async def _fake_generate(*args, **kwargs):
        return {"route": "simple", "tasks": [], "inference": {}, "task_count": 0}

    monkeypatch.setattr(orchestrator, "generate_swms", _fake_generate)

    resp = auth_client.post(
        "/generate/auto",
        json={"description": "Painting work on facade"},
    )
    assert resp.status_code != 401

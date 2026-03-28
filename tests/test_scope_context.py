"""
Tests that scope_context is forwarded correctly by streaming and full-pipeline endpoints.

T3 — Scope context forwarding
  • /generate/stream passes scope_context to generate_swms_stream.
  • /generate/full passes scope_context to generate_swms.
  • Absent scope_context passes None without raising an error.

Note: /generate/stream and /generate/full currently do NOT forward scope_context.
These tests document the intended behaviour and will fail until the endpoints
are updated to include scope_context forwarding.
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def auth_client():
    from api.main import app
    from core.auth import get_current_user

    async def _fake_user():
        return {"user_id": "test-scope-001", "email": "test@example.com"}

    app.dependency_overrides[get_current_user] = _fake_user
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


# ── T3-A: /generate/stream forwards scope_context ────────────────────────────

def test_stream_forwards_scope_context(auth_client, monkeypatch):
    """POST /generate/stream must pass scope_context through to generate_swms_stream."""
    from core import orchestrator

    captured = {}

    async def _fake_stream(*args, **kwargs):
        captured["scope_context"] = kwargs.get("scope_context")
        yield {"type": "done", "task_count": 0, "route": "simple"}

    monkeypatch.setattr(orchestrator, "generate_swms_stream", _fake_stream)

    scope = {"document": "spec.pdf", "text": "Waterproofing Level B1"}
    resp = auth_client.post(
        "/generate/stream",
        json={
            "description": "Waterproofing works to level B1 basement car park areas",
            "scope_context": scope,
        },
    )

    # Consume the stream
    _ = resp.text

    ctx = captured.get("scope_context")
    assert ctx is not None, "scope_context not forwarded at all"
    # The orchestrator enriches scope_context with classification fields.
    # Check that the original user-provided fields are still present.
    for key, val in scope.items():
        assert ctx.get(key) == val, (
            f"scope_context['{key}'] not forwarded: expected {val}, got {ctx.get(key)}"
        )


# ── T3-B: /generate/full forwards scope_context ──────────────────────────────

def test_full_forwards_scope_context(auth_client, monkeypatch):
    """POST /generate/full must pass scope_context through to generate_swms."""
    from core import orchestrator

    captured = {}

    async def _fake_generate(*args, **kwargs):
        captured["scope_context"] = kwargs.get("scope_context")
        return {"route": "full", "tasks": [], "inference": {}, "task_count": 0}

    monkeypatch.setattr(orchestrator, "generate_swms", _fake_generate)

    scope = {"document": "drawings.pdf", "text": "Structural crack repair"}
    resp = auth_client.post(
        "/generate/full",
        json={
            "description": "Structural remediation",
            "scope_context": scope,
        },
    )

    assert resp.status_code != 401
    assert captured.get("scope_context") == scope, (
        f"scope_context not forwarded: captured={captured.get('scope_context')}"
    )


# ── T3-C: absent scope_context passes None without error ─────────────────────

def test_stream_absent_scope_context_passes_none(auth_client, monkeypatch):
    """When scope_context is omitted, /generate/stream must pass None without raising."""
    from core import orchestrator

    captured = {"scope_context": "NOT_SET"}

    async def _fake_stream(*args, **kwargs):
        captured["scope_context"] = kwargs.get("scope_context")
        yield {"type": "done", "task_count": 0, "route": "simple"}

    monkeypatch.setattr(orchestrator, "generate_swms_stream", _fake_stream)

    resp = auth_client.post(
        "/generate/stream",
        json={"description": "General painting works"},
    )

    # Must not error
    assert resp.status_code != 500
    # scope_context should be None (not some unexpected default)
    assert captured["scope_context"] is None, (
        f"Expected None, got {captured['scope_context']!r}"
    )

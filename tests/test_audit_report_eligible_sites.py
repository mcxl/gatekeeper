"""Tests for GET /pims/sites/eligible: must filter out null-project_value sites.

The handler delegates filtering to Supabase via PostgREST params
(`project_value=not.is.null` and `active=eq.true`). This test captures the
outgoing params and asserts the filter is present, so the contract can't
silently regress.
"""
from __future__ import annotations

import asyncio
import json

import pytest


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200
        self.text = json.dumps(payload)

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeClient:
    """Captures the last GET params so the test can assert on them."""
    last_params: dict | None = None
    next_payload: list[dict] = []

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, headers=None, params=None):
        _FakeClient.last_params = dict(params or {})
        return _FakeResp(_FakeClient.next_payload)


@pytest.fixture
def patched_routes(monkeypatch):
    try:
        from pims import routes
    except ModuleNotFoundError as e:
        pytest.skip(f"pims.routes unavailable: {e}")
    monkeypatch.setattr(routes, "RPD_SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(routes, "RPD_SUPABASE_SERVICE_KEY", "test-key")
    monkeypatch.setattr(routes, "verify_session_cookie", lambda _: True)
    monkeypatch.setattr(routes.httpx, "AsyncClient", _FakeClient)
    _FakeClient.last_params = None
    _FakeClient.next_payload = []
    return routes


def test_eligible_sites_filters_null_project_value(patched_routes):
    _FakeClient.next_payload = [
        {"id": "11111111-1111-1111-1111-111111111111",
         "address_raw": "1 Valid St", "project_value": 300000},
    ]
    result = asyncio.run(patched_routes.list_eligible_sites(pims_sess="cookie"))
    assert result == _FakeClient.next_payload
    params = _FakeClient.last_params or {}
    assert params.get("project_value") == "not.is.null"
    assert params.get("active") == "eq.true"
    assert params.get("order") == "address_raw.asc"


def test_eligible_sites_requires_session(patched_routes, monkeypatch):
    from fastapi import HTTPException
    monkeypatch.setattr(patched_routes, "verify_session_cookie", lambda _: False)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(patched_routes.list_eligible_sites(pims_sess=None))
    assert exc.value.status_code == 401

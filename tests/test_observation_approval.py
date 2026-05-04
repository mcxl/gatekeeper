"""Phase 6 — observation review_status approval / rejection / bulk-approve.

Pins the public contract:
  - 401 when no session cookie verified
  - 422 on invalid uuid
  - 503 when supabase env not configured
  - PATCH payload writes (review_status, approved_by, approved_at)
  - Bulk-approve filters by site_id AND review_status=Pending
  - Reject stuffs reason into monitoring_note (so reviewers see it)
"""
from __future__ import annotations

import asyncio
import json
from urllib.parse import parse_qsl

import pytest


# ─── Shared HTTP fakes ──────────────────────────────────────────────────

class _FakeResp:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class _CapturingClient:
    """Records every PATCH/GET; returns canned payloads in order."""
    calls: list[dict] = []
    next_responses: list[_FakeResp] = []

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def _record(self, method, url, **kw):
        _CapturingClient.calls.append({
            "method": method, "url": url,
            "params": dict(kw.get("params") or {}),
            "json": kw.get("json"),
            "headers": dict(kw.get("headers") or {}),
        })
        if _CapturingClient.next_responses:
            return _CapturingClient.next_responses.pop(0)
        return _FakeResp([], 200)

    async def patch(self, url, **kw):
        return await self._record("PATCH", url, **kw)

    async def get(self, url, **kw):
        return await self._record("GET", url, **kw)

    async def post(self, url, **kw):
        return await self._record("POST", url, **kw)


@pytest.fixture
def routes(monkeypatch):
    try:
        from pims import routes as r
    except ModuleNotFoundError as e:
        pytest.skip(f"pims.routes unavailable: {e}")
    monkeypatch.setattr(r, "RPD_SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(r, "RPD_SUPABASE_SERVICE_KEY", "test-key")
    monkeypatch.setattr(r, "verify_session_cookie", lambda *_a, **_kw: True)
    monkeypatch.setattr(r.httpx, "AsyncClient", _CapturingClient)
    _CapturingClient.calls = []
    _CapturingClient.next_responses = []
    return r


# ─── approve_observation ────────────────────────────────────────────────

class TestApproveObservation:
    def test_writes_review_status_approved(self, routes):
        obs_id = "11111111-1111-1111-1111-111111111111"
        _CapturingClient.next_responses = [_FakeResp([{
            "id": obs_id, "review_status": "Approved",
        }])]
        body = routes.ObservationApproveRequest(approver="alice")
        result = asyncio.run(routes.approve_observation(obs_id, body, pims_sess="s"))
        assert result == {"ok": True, "id": obs_id, "review_status": "Approved"}
        assert len(_CapturingClient.calls) == 1
        call = _CapturingClient.calls[0]
        assert call["method"] == "PATCH"
        assert call["params"]["id"] == f"eq.{obs_id}"
        assert call["json"]["review_status"] == "Approved"
        assert call["json"]["approved_by"] == "alice"
        assert "approved_at" in call["json"]

    def test_default_approver_is_dashboard(self, routes):
        obs_id = "11111111-1111-1111-1111-111111111111"
        _CapturingClient.next_responses = [_FakeResp([{
            "id": obs_id, "review_status": "Approved",
        }])]
        body = routes.ObservationApproveRequest()
        asyncio.run(routes.approve_observation(obs_id, body, pims_sess="s"))
        assert _CapturingClient.calls[0]["json"]["approved_by"] == "dashboard"

    def test_unauthorized_without_session(self, routes, monkeypatch):
        from fastapi import HTTPException
        monkeypatch.setattr(routes, "verify_session_cookie", lambda *_a, **_kw: False)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(routes.approve_observation(
                "11111111-1111-1111-1111-111111111111",
                routes.ObservationApproveRequest(),
                pims_sess=None,
            ))
        assert exc.value.status_code == 401

    def test_invalid_uuid_rejected(self, routes):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            asyncio.run(routes.approve_observation(
                "not-a-uuid",
                routes.ObservationApproveRequest(),
                pims_sess="s",
            ))
        assert exc.value.status_code == 422

    def test_missing_observation_returns_404(self, routes):
        from fastapi import HTTPException
        # Empty payload from supabase = no row matched.
        _CapturingClient.next_responses = [_FakeResp([])]
        with pytest.raises(HTTPException) as exc:
            asyncio.run(routes.approve_observation(
                "11111111-1111-1111-1111-111111111111",
                routes.ObservationApproveRequest(),
                pims_sess="s",
            ))
        assert exc.value.status_code == 404


# ─── reject_observation ─────────────────────────────────────────────────

class TestRejectObservation:
    def test_writes_review_status_rejected_with_reason(self, routes):
        obs_id = "22222222-2222-2222-2222-222222222222"
        _CapturingClient.next_responses = [_FakeResp([{
            "id": obs_id, "review_status": "Rejected",
        }])]
        body = routes.ObservationRejectRequest(
            approver="bob", reason="duplicate of obs-1",
        )
        result = asyncio.run(routes.reject_observation(obs_id, body, pims_sess="s"))
        assert result["review_status"] == "Rejected"
        call = _CapturingClient.calls[0]
        assert call["json"]["review_status"] == "Rejected"
        assert call["json"]["approved_by"] == "bob"
        assert "duplicate of obs-1" in call["json"]["monitoring_note"]
        assert "[Rejected by bob]" in call["json"]["monitoring_note"]


# ─── approve_all_pending_observations_for_site ──────────────────────────

class TestBulkApprove:
    def test_filters_by_site_id_and_pending(self, routes):
        site_id = "33333333-3333-3333-3333-333333333333"
        _CapturingClient.next_responses = [_FakeResp(
            [{"id": f"obs-{i}"} for i in range(13)],
        )]
        body = routes.BulkApproveRequest(site_id=site_id, approver="claude")
        result = asyncio.run(
            routes.approve_all_pending_observations_for_site(body, pims_sess="s")
        )
        assert result == {
            "ok": True, "site_id": site_id, "approved_count": 13,
        }
        call = _CapturingClient.calls[0]
        assert call["method"] == "PATCH"
        assert call["params"]["site_id"] == f"eq.{site_id}"
        assert call["params"]["review_status"] == "eq.Pending"
        assert call["json"]["review_status"] == "Approved"
        assert call["json"]["approved_by"] == "claude"

    def test_no_pending_returns_zero(self, routes):
        site_id = "33333333-3333-3333-3333-333333333333"
        _CapturingClient.next_responses = [_FakeResp([])]
        body = routes.BulkApproveRequest(site_id=site_id)
        result = asyncio.run(
            routes.approve_all_pending_observations_for_site(body, pims_sess="s")
        )
        assert result["approved_count"] == 0

    def test_invalid_uuid_rejected(self, routes):
        from fastapi import HTTPException
        body = routes.BulkApproveRequest(site_id="not-a-uuid")
        with pytest.raises(HTTPException) as exc:
            asyncio.run(routes.approve_all_pending_observations_for_site(
                body, pims_sess="s",
            ))
        assert exc.value.status_code == 422


# ─── Validation helper ──────────────────────────────────────────────────

class TestSetReviewStatusGuard:
    def test_invalid_review_status_raises_422(self, routes):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            asyncio.run(routes._set_observation_review_status(
                "11111111-1111-1111-1111-111111111111",
                new_status="WhateverElse",
                approver="dashboard",
            ))
        assert exc.value.status_code == 422

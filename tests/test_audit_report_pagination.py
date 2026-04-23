"""Tests for _fetch_observations_for_site pagination (Codex P2).

A WHS audit report must not silently truncate findings. These tests simulate
multi-page Supabase responses via a fake httpx.AsyncClient and assert:
  1. Multiple pages are concatenated into a single result list.
  2. The 50-page safety cap raises cleanly rather than returning truncated data.
"""
from __future__ import annotations

import asyncio

import pytest


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _PagedClient:
    """Returns a deterministic sequence of pages on successive .get() calls."""
    pages: list[list[dict]] = []
    calls: list[dict] = []

    def __init__(self, *a, **kw):
        self._idx = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, headers=None, params=None):
        _PagedClient.calls.append({"headers": dict(headers or {}),
                                   "params": dict(params or {})})
        page = _PagedClient.pages[self._idx] if self._idx < len(_PagedClient.pages) else []
        self._idx += 1
        return _FakeResp(page)


@pytest.fixture
def patched_routes(monkeypatch):
    try:
        from pims import routes
    except ModuleNotFoundError as e:
        pytest.skip(f"pims.routes unavailable: {e}")
    monkeypatch.setattr(routes, "RPD_SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(routes, "RPD_SUPABASE_SERVICE_KEY", "test-key")
    monkeypatch.setattr(routes.httpx, "AsyncClient", _PagedClient)
    _PagedClient.pages = []
    _PagedClient.calls = []
    return routes


def test_paginates_three_pages(patched_routes):
    page1 = [{"seq_no": i} for i in range(1000)]
    page2 = [{"seq_no": i} for i in range(1000, 2000)]
    page3 = [{"seq_no": i} for i in range(2000, 2237)]  # short -> stop
    _PagedClient.pages = [page1, page2, page3]

    site_id = "11111111-1111-1111-1111-111111111111"
    result = asyncio.run(patched_routes._fetch_observations_for_site(site_id))

    assert len(result) == 2237
    assert result[0]["seq_no"] == 0
    assert result[-1]["seq_no"] == 2236
    assert len(_PagedClient.calls) == 3
    # Range headers should step by 1000 and be items-unit.
    ranges = [c["headers"].get("Range") for c in _PagedClient.calls]
    assert ranges == ["0-999", "1000-1999", "2000-2999"]
    for c in _PagedClient.calls:
        assert c["headers"].get("Range-Unit") == "items"
    # Filters preserved
    p = _PagedClient.calls[0]["params"]
    assert p["site_id"] == f"eq.{site_id}"
    assert p["staging"] == "eq.false"
    assert p["source_pdf"] == "is.null"
    assert p["review_status"] == "eq.Approved"
    assert p["order"] == "observation_date.asc"
    assert "limit" not in p  # no explicit limit when paginating


def test_safety_cap_raises_rather_than_truncating(patched_routes, monkeypatch):
    from fastapi import HTTPException
    # Always return a full page — loop would run forever without the cap.
    full_page = [{"seq_no": i} for i in range(1000)]
    monkeypatch.setattr(patched_routes, "_OBS_MAX_PAGES", 3)
    _PagedClient.pages = [full_page] * 10

    with pytest.raises(HTTPException) as exc:
        asyncio.run(patched_routes._fetch_observations_for_site(
            "22222222-2222-2222-2222-222222222222"))
    assert exc.value.status_code == 500
    assert "exceeded" in exc.value.detail.lower()
    assert len(_PagedClient.calls) == 3  # cap honoured, not silently truncated

"""Tests for pims/services/site_resolver.py — Phase 7."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from pims.services.site_resolver import canonicalise_address, resolve_site_id


# ── canonicalise_address ─────────────────────────────────────────────


def test_canonicalise_strips_whitespace_and_lowercases():
    assert canonicalise_address("  96-98 Hampden Rd Russel Lea  ") == "96-98 hampden rd russel lea"


def test_canonicalise_normalises_road_to_rd():
    assert canonicalise_address("96-98 Hampden Road Russel Lea") == "96-98 hampden rd russel lea"


def test_canonicalise_applies_hampton_alias():
    assert canonicalise_address("96-98 Hampton Rd Russel Lea") == "96-98 hampden rd russel lea"


def test_canonicalise_strips_punctuation():
    assert canonicalise_address("96-98 Hampton Road, Russel Lea") == "96-98 hampden rd russel lea"


def test_canonicalise_empty_returns_none():
    assert canonicalise_address("") is None
    assert canonicalise_address(None) is None
    assert canonicalise_address("   ") is None


def test_canonicalise_street_avenue():
    assert canonicalise_address("1 Albert Avenue") == "1 albert ave"


# ── resolve_site_id ──────────────────────────────────────────────────


def _mock_client(rows):
    """Build a mock httpx.AsyncClient whose .get returns the given rows."""
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status = MagicMock()
    response.json = MagicMock(return_value=rows)
    client = MagicMock()
    client.get = AsyncMock(return_value=response)
    return client


def test_resolve_exact_match_returns_site_id():
    rows = [
        {"id": "site-1", "address_raw": "96-98 Hampden Rd Russel Lea"},
        {"id": "site-2", "address_raw": "12 Other St Manly"},
    ]
    client = _mock_client(rows)
    result = asyncio.run(resolve_site_id(
        "96-98 Hampden Rd Russel Lea",
        supabase_url="https://example", supabase_key="k", client=client,
    ))
    assert result == "site-1"


def test_resolve_alias_hampton_to_hampden():
    rows = [{"id": "site-1", "address_raw": "96-98 Hampden Rd Russel Lea"}]
    client = _mock_client(rows)
    result = asyncio.run(resolve_site_id(
        "96-98 Hampton Road, Russel Lea",
        supabase_url="https://example", supabase_key="k", client=client,
    ))
    assert result == "site-1"


def test_resolve_ambiguous_returns_none():
    rows = [
        {"id": "site-1", "address_raw": "96-98 Hampden Rd Russel Lea"},
        {"id": "site-2", "address_raw": "96-98 Hampden Road Russel Lea"},  # canonicalises to same
    ]
    client = _mock_client(rows)
    result = asyncio.run(resolve_site_id(
        "96-98 Hampden Rd Russel Lea",
        supabase_url="https://example", supabase_key="k", client=client,
    ))
    assert result is None  # two matches → ambiguous


def test_resolve_no_match_returns_none():
    rows = [{"id": "site-1", "address_raw": "12 Other St Manly"}]
    client = _mock_client(rows)
    result = asyncio.run(resolve_site_id(
        "99 Unknown Ave Nowhere",
        supabase_url="https://example", supabase_key="k", client=client,
    ))
    assert result is None


def test_resolve_empty_input_returns_none_without_calling_supabase():
    client = _mock_client([])
    result = asyncio.run(resolve_site_id(
        None,
        supabase_url="https://example", supabase_key="k", client=client,
    ))
    assert result is None
    client.get.assert_not_called()


def test_resolve_missing_config_returns_none():
    client = _mock_client([])
    result = asyncio.run(resolve_site_id(
        "anything",
        supabase_url=None, supabase_key=None, client=client,
    ))
    assert result is None

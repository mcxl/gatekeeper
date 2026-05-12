"""pims/services/site_resolver.py

Phase 7 of docs/plans/PIMS_ENRICHMENT_AND_SITE_LINKAGE_FIX.md.

Resolves a free-text address (from staging.site_address, an xlsx upload
row, or a PDF promote payload) to the canonical sites.id UUID. Used by
every backend path that creates a live pims_observations row, so live
rows always carry site_id when the address resolves unambiguously.

Conservative by design: returns None on no match OR ambiguous match.
Callers decide what to do with None (e.g. approve_staging_rpd returns
409 if site_address is blank AND audit fallback also fails).

Alias table is a Python dict — small, reviewed in code, no DB churn.
"""

from __future__ import annotations

import os
import re
from typing import Optional

import httpx

# Address aliases for known typos. Keys must be lowercase canonical
# tokens; values are the canonical replacement. Applied AFTER lowercase
# + whitespace collapse, BEFORE the sites table lookup.
#
# Add aliases only after confirming a real production typo. Each entry
# is a maintenance burden — keep this dict short.
ADDRESS_ALIASES: dict[str, str] = {
    "hampton": "hampden",  # 96-98 Hampden Rd Russel Lea (2026-05-12)
}

# Common street-type contractions normalised to short form so "Road"
# and "Rd" canonicalise to the same key.
STREET_SUFFIX_MAP: dict[str, str] = {
    "road":     "rd",
    "street":   "st",
    "avenue":   "ave",
    "crescent": "cr",
    "drive":    "dr",
    "highway":  "hwy",
    "place":    "pl",
    "boulevard": "blvd",
    "court":    "ct",
    "parade":   "pde",
    "terrace":  "tce",
    "lane":     "ln",
}

_WHITESPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[,;.]")


def canonicalise_address(address_raw: Optional[str]) -> Optional[str]:
    """Lowercase, strip punctuation, collapse whitespace, apply aliases,
    and normalise street-type suffixes. Returns None for empty input."""
    if not address_raw:
        return None
    s = address_raw.strip().lower()
    if not s:
        return None
    s = _PUNCT_RE.sub(" ", s)
    s = _WHITESPACE_RE.sub(" ", s).strip()
    tokens = s.split(" ")
    tokens = [ADDRESS_ALIASES.get(t, t) for t in tokens]
    tokens = [STREET_SUFFIX_MAP.get(t, t) for t in tokens]
    return " ".join(tokens) or None


async def resolve_site_id(
    address_raw: Optional[str],
    *,
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None,
    client: Optional[httpx.AsyncClient] = None,
) -> Optional[str]:
    """Look up sites.id for the canonical form of address_raw.
    Returns None if address is empty, no match, or ambiguous (>1 active
    match on canonical form)."""
    canonical = canonicalise_address(address_raw)
    if not canonical:
        return None

    url = (supabase_url or os.getenv("RPD_SUPABASE_URL") or "").rstrip("/")
    key = supabase_key or os.getenv("RPD_SUPABASE_SERVICE_KEY")
    if not url or not key:
        return None

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }
    params = {
        "active": "eq.true",
        "select": "id,address_raw",
    }

    async def _fetch(c: httpx.AsyncClient) -> list[dict]:
        r = await c.get(f"{url}/rest/v1/sites", headers=headers, params=params)
        r.raise_for_status()
        return r.json()

    if client is None:
        async with httpx.AsyncClient(timeout=10) as c:
            rows = await _fetch(c)
    else:
        rows = await _fetch(client)

    matches = [r["id"] for r in rows if canonicalise_address(r.get("address_raw")) == canonical]
    if len(matches) == 1:
        return matches[0]
    return None

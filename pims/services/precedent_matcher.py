"""pims/services/precedent_matcher.py

Raw-text-first precedent retrieval for live PIMS enrichment.

Public surface
--------------
    async find_precedents(observation_text, supabase_url, service_key, *, top_k=3)
        -> list[PrecedentMatch]

Ranking model
-------------
1. Token Jaccard score on normalized text.
2. +0.10 boost when ccvs_category matches a deterministic guess from
   the observation text.
3. +0.05 boost when section_name overlaps with section keywords found
   in the observation text.

ccvs_code/category are OPTIONAL boosts only. The live request to
this function carries only raw observation text.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import httpx

from pims.services.precedent_classifier import deterministic_classify
from pims.services.precedent_importer import normalize_key

log = logging.getLogger(__name__)


# Section keywords (lowercase) → canonical section_name fragment.
# Used for the +0.05 section boost only — never as a hard filter.
SECTION_KEYWORDS: dict[str, str] = {
    "rope access":               "rope access",
    "scaffold":                  "general work at height",
    "ladder":                    "general work at height",
    "ewp":                       "general work at height",
    "fall":                      "general work at height",
    "harness":                   "rope access",
    "irata":                     "rope access",
    "silica":                    "hazardous substances",
    "sds":                       "hazardous substances",
    "chemical":                  "hazardous substances",
    "induction":                 "worker competency",
    "swms":                      "worker competency",
    "ppe":                       "worker competency",
    "white card":                "worker competency",
    "first aid":                 "planning and site",
    "emergency":                 "planning and site",
    "electrical":                "energy and services",
    "test and tag":              "energy and services",
    "demolition":                "demolition",
    "propping":                  "demolition",
}


@dataclass
class PrecedentMatch:
    id: str
    score: float
    finding_text: Optional[str]
    recommendation_text: Optional[str]
    observation_text: Optional[str]
    section_name: Optional[str]
    ccvs_code: Optional[str]
    ccvs_category: Optional[str]
    match_reasons: list[str] = field(default_factory=list)

    def to_summary(self) -> dict:
        return {
            "id":      self.id,
            "score":   round(self.score, 4),
            "reasons": self.match_reasons,
        }


# ---- Token utilities ----

_TOK_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    if not text:
        return set()
    return set(_TOK_RE.findall(text.lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


# ---- Section-keyword guess ----

def _section_hints(observation_text: str) -> set[str]:
    """Return the set of section_name fragments suggested by the obs text."""
    t = (observation_text or "").lower()
    hits: set[str] = set()
    for kw, sec in SECTION_KEYWORDS.items():
        if kw in t:
            hits.add(sec)
    return hits


# ---- Candidate fetch ----

def _supabase_headers(key: str) -> dict:
    return {"apikey": key, "Content-Type": "application/json"}


async def _fetch_candidates(
    url: str, key: str, observation_text: str, *, max_candidates: int = 80,
) -> list[dict]:
    """Pull a candidate window using cheap server-side filters.

    Strategy: union of (a) rows whose section_name OR ccvs_category matches
    one of the section hints, and (b) a fallback newest-N window. The fallback
    ensures we still return something for novel topics.
    """
    headers = _supabase_headers(key)
    select = ("id,finding_text,recommendation_text,observation_text,"
              "normalized_key,section_name,ccvs_code,ccvs_category,"
              "status_normalized")
    seen: dict[str, dict] = {}

    hints = _section_hints(observation_text)

    async with httpx.AsyncClient(timeout=15) as c:
        # Section-targeted fetch.
        for hint in hints:
            params = {
                "select": select,
                "section_name": f"ilike.*{hint}*",
                "limit": "30",
            }
            r = await c.get(f"{url}/rest/v1/pims_precedent_examples",
                            headers=headers, params=params)
            if r.status_code == 200:
                for row in r.json():
                    seen[row["id"]] = row

        # Fallback: most recently-imported window so a totally novel obs
        # still has *something* to score against.
        if len(seen) < 20:
            params = {
                "select": select,
                "order": "imported_at.desc",
                "limit": str(max_candidates),
            }
            r = await c.get(f"{url}/rest/v1/pims_precedent_examples",
                            headers=headers, params=params)
            if r.status_code == 200:
                for row in r.json():
                    seen.setdefault(row["id"], row)
    return list(seen.values())


# ---- Ranking ----

def _score(observation_text: str, row: dict, hints: set[str]) -> tuple[float, list[str]]:
    obs_tokens = _tokens(normalize_key(observation_text))
    cand_text = (row.get("normalized_key")
                 or row.get("finding_text")
                 or row.get("observation_text") or "")
    cand_tokens = _tokens(cand_text)
    j = _jaccard(obs_tokens, cand_tokens)
    reasons = [f"token-overlap:{j:.2f}"]

    # +0.10 ccvs_category boost.
    guess = deterministic_classify(observation_text, None)
    if guess and row.get("ccvs_category") and guess.ccvs_category == row["ccvs_category"]:
        j += 0.10
        reasons.append(f"ccvs-boost:{guess.ccvs_code}")

    # +0.05 section overlap boost.
    sec = (row.get("section_name") or "").lower()
    for hint in hints:
        if hint in sec:
            j += 0.05
            reasons.append(f"section:{row['section_name']}")
            break

    return j, reasons


# ---- Public API ----

async def find_precedents(
    observation_text: str,
    supabase_url: str,
    service_key: str,
    *,
    top_k: int = 3,
) -> list[PrecedentMatch]:
    """Return up to top_k precedents ranked by Jaccard + boosts.

    Failure-tolerant: returns [] on any error rather than raising.
    """
    if not observation_text or not supabase_url or not service_key:
        return []
    try:
        candidates = await _fetch_candidates(
            supabase_url, service_key, observation_text)
        if not candidates:
            return []
        hints = _section_hints(observation_text)
        scored: list[PrecedentMatch] = []
        for row in candidates:
            score, reasons = _score(observation_text, row, hints)
            scored.append(PrecedentMatch(
                id=row["id"],
                score=score,
                finding_text=row.get("finding_text"),
                recommendation_text=row.get("recommendation_text"),
                observation_text=row.get("observation_text"),
                section_name=row.get("section_name"),
                ccvs_code=row.get("ccvs_code"),
                ccvs_category=row.get("ccvs_category"),
                match_reasons=reasons,
            ))
        scored.sort(key=lambda m: m.score, reverse=True)
        # Drop zero-overlap noise.
        scored = [m for m in scored if m.score > 0.05]
        return scored[:top_k]
    except Exception as e:
        log.warning(f"find_precedents failed: {e}")
        return []

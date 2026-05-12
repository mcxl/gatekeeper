"""pims/services/ccvs_fallback.py

Phase 9 of docs/plans/PIMS_ENRICHMENT_AND_SITE_LINKAGE_FIX.md.

Deterministic CCVS code fallback applied AFTER Haiku enrichment when
ccvs_code is null. Pure safety net — never overrides a code Haiku
actually returned.

Trigger sequence in enrich_observation:
    1. Haiku call returns parsed dict.
    2. If parsed["ccvs_code"] is None/missing AND conformance_status
       is in {NCR, Compliant, Conditional, Info}, run
       apply_ccvs_fallback(parsed, observation_text). It mutates
       parsed in-place with code + category if a keyword matches.
    3. If no keyword matches, code stays null (legitimate uncoded
       observation, surfaced by the Phase 5.5 chip).

Keyword table is intentionally short and human-reviewable. Add new
entries as new gaps surface — keep it the canonical reference for the
deterministic mapping.
"""

from __future__ import annotations

from typing import Optional


# Order matters: first matching keyword wins. Put more specific terms
# before more general ones (e.g. "first aid" before "aid").
KEYWORD_TO_CCVS: list[tuple[str, str, str]] = [
    # (keyword substring, ccvs_code, ccvs_category)
    # Emergency response — SYS-H6
    ("fire extinguisher",  "SYS-H6", "Systems"),
    ("first aid",          "SYS-H6", "Systems"),
    ("emergency contact",  "SYS-H6", "Systems"),
    ("emergency",          "SYS-H6", "Systems"),
    # Inspections / scaffold / permit — SYS-M4
    ("scaff tag",          "SYS-M4", "Systems"),
    ("scaffold inspect",   "SYS-M4", "Systems"),
    ("permit",             "SYS-M4", "Systems"),
    ("scaffold access",    "SYS-M4", "Systems"),
    # Documentation / SWMS / toolbox / risk-assessment / SDS / signage — SYS-M3
    ("swms",               "SYS-M3", "Systems"),
    ("toolbox",            "SYS-M3", "Systems"),
    ("risk assessment",    "SYS-M3", "Systems"),
    ("sds",                "SYS-M3", "Systems"),
    ("safety data sheet",  "SYS-M3", "Systems"),
    ("signage",            "SYS-M3", "Systems"),
    ("notice",             "SYS-M3", "Systems"),
    # Induction / register / sign-in — SYS-L1
    ("white card",         "SYS-L1", "Systems"),
    ("induction",          "SYS-L1", "Systems"),
    ("sign in",            "SYS-L1", "Systems"),
    ("sign-in",            "SYS-L1", "Systems"),
    ("daily sign",         "SYS-L1", "Systems"),
    ("daly sign",          "SYS-L1", "Systems"),  # observed misspelling in production
    ("checkout",           "SYS-L1", "Systems"),
    ("check-out",          "SYS-L1", "Systems"),
    ("register",           "SYS-L1", "Systems"),
    # Energy / electrical — ENE-M4
    ("rcd",                "ENE-M4", "Energy"),
    ("electrical lead",    "ENE-M4", "Energy"),
    ("electrical supply",  "ENE-M4", "Energy"),
    ("gpo",                "ENE-M4", "Energy"),
    ("electrical",         "ENE-M4", "Energy"),
]


def apply_ccvs_fallback(parsed: dict, observation_text: Optional[str]) -> Optional[str]:
    """If parsed has no ccvs_code, scan observation_text for a known
    keyword and set ccvs_code + ccvs_category in place.

    Returns the keyword that matched, or None if nothing changed.
    Caller should log the match (or non-match) for observability.

    Safety rules:
        - Never overrides a non-null ccvs_code.
        - Only fires when conformance_status is set to a non-Pending
          value (NCR / Compliant / Conditional / Info) — uncoded
          Pending records are still in-progress.
        - Returns None and makes no change if observation_text is empty.
    """
    if parsed.get("ccvs_code"):
        return None
    status = parsed.get("conformance_status")
    if status not in {"NCR", "Compliant", "Conditional", "Info"}:
        return None
    text = (observation_text or "").lower()
    if not text:
        return None
    for keyword, code, category in KEYWORD_TO_CCVS:
        if keyword in text:
            parsed["ccvs_code"] = code
            parsed["ccvs_category"] = category
            parsed["ccvs_confidence"] = parsed.get("ccvs_confidence") or "Medium"
            return keyword
    return None

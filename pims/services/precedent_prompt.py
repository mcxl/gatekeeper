"""pims/services/precedent_prompt.py

Build the per-request dynamic prompt supplement that ships top-K
precedent examples into the Haiku call as adaptation references —
NOT as templates to copy verbatim. The supplement is appended to the
USER message, never to the system prompt — so ENRICHMENT_SYSTEM stays
fixed and cacheable.
"""

from __future__ import annotations

from typing import Iterable

from pims.services.precedent_matcher import PrecedentMatch


_ANTI_CARRYOVER = (
    "ANTI-CARRYOVER (mandatory): DO NOT carry over from the precedents "
    "any of the following — site names, building/unit/apartment numbers "
    "(e.g. '1B', 'Apt 3'), directional references "
    "(north/south/east/west, level/floor numbers, balconies), specific "
    "dates, occupant or location-specific identifiers, or named "
    "persons. Use ONLY facts present in the current observation. "
    "Anything site-specific MUST come from the new observation."
)

_ADAPT_INSTRUCTIONS = (
    "Use the precedents below as STYLE / STRUCTURE references for tone, "
    "depth, legal-reference patterning, and recommendation wording. "
    "Do NOT copy them verbatim. Apply their pattern to the current "
    "observation."
)


def _clamp(text: str | None, n: int) -> str:
    if not text:
        return ""
    if len(text) <= n:
        return text
    return text[:n].rstrip() + "…"


def build_supplement(
    observation_text: str,
    precedents: Iterable[PrecedentMatch],
    *,
    per_example_clamp: int = 600,
) -> str:
    """Return text block to append to the user message.

    Returns "" when there are no precedents — caller should pass through
    unchanged in that case.
    """
    precedents = list(precedents or [])
    if not precedents:
        return ""

    parts: list[str] = []
    parts.append("CURRENT OBSERVATION (verbatim):")
    parts.append(observation_text.strip())
    parts.append("")
    parts.append(f"PRECEDENT EXAMPLES (top {len(precedents)}):")
    for i, p in enumerate(precedents, 1):
        parts.append(f"--- Precedent {i} (score {p.score:.2f}) ---")
        if p.section_name:
            parts.append(f"section: {p.section_name}")
        if p.ccvs_code:
            parts.append(f"ccvs: {p.ccvs_code}")
        finding = _clamp(p.finding_text or p.observation_text, per_example_clamp)
        if finding:
            parts.append(f"finding: {finding}")
        recommendation = _clamp(p.recommendation_text, per_example_clamp)
        if recommendation:
            parts.append(f"recommendation: {recommendation}")
    parts.append("")
    parts.append(_ADAPT_INSTRUCTIONS)
    parts.append("")
    parts.append(_ANTI_CARRYOVER)
    return "\n".join(parts)

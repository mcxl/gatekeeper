"""Canonical CCVS coding taxonomy for SSA audit deliverables.

Source of truth: ``renderers/docx_renderer.py`` ``_VALID_CCVS_STREAMS``
(24 streams) plus ``SYS`` (Systems / Compliance Records) which the
``PIMS-Enriched - Sample.xlsx`` confirms is in active use on the
audit side even though the SWMS-side validator rejects it.

A CCVS code is ``<STREAM>-<TIER>`` where ``STREAM`` is one of the 25
3-letter prefixes listed below and ``TIER`` is one of the 6 valid
severity-ordering suffixes (H6/H9 high, M3/M4 medium, L1/L2 low).

Plain-English category names are reviewer-facing labels that appear in
the ``CCVS Category`` column of the PIMS-Enriched workbook and the
``ccvs_category`` column of the staging xlsx. They are short trade or
hazard-family names, not the long SWMS-side section headings.
"""
from __future__ import annotations

import re

# Stream prefix → reviewer-facing category. Keys MUST match the
# ``_VALID_CCVS_STREAMS`` list in ``renderers/docx_renderer.py`` plus
# the audit-side ``SYS`` extension.
STREAM_TO_CATEGORY: dict[str, str] = {
    "WFR": "Worker Facilities",
    "WFA": "Worker Amenities",
    "WAH": "Work at Height",
    "IRA": "Industrial Rope Access",
    "ELE": "Electrical",
    "SIL": "Silica Dust",
    "STR": "Structural",
    "CFS": "Confined Space",
    "ENE": "Energy and Services",
    "HOT": "Hot Works",
    "MOB": "Mobile Plant",
    "ASB": "Asbestos",
    "LED": "Lead Hazard",
    "TRF": "Traffic Management",
    "ENV": "Environmental",
    "CHM": "Chemical / Hazardous Substances",
    "SCF": "Scaffold",
    "CRN": "Crane and Lifting",
    "EXC": "Excavation and Trenching",
    "MNH": "Manual Handling",
    "NOI": "Noise",
    "TLT": "Tilt-up and Precast",
    "DEM": "Demolition",
    "FMW": "Formwork",
    "SYS": "Systems",
}

VALID_STREAMS: frozenset[str] = frozenset(STREAM_TO_CATEGORY)

# Severity-ordered tier suffixes. Letter = severity (H/M/L), digit =
# ordering within tier. Reviewers pick the tier from observed evidence.
VALID_TIERS: frozenset[str] = frozenset({"H6", "H9", "M3", "M4", "L1", "L2"})

# Reviewer-facing severity descriptions — used in LLM prompts so the
# model picks a tier consistent with what the photo + observation show.
TIER_DESCRIPTION: dict[str, str] = {
    "H6": "High severity — immediate non-conformance, stop-work or NCR",
    "H9": "High severity — uncontrolled risk, NCR with urgent remediation",
    "M3": "Medium severity — non-conformance with managed risk, conditional",
    "M4": "Medium severity — observation needing controls, conditional",
    "L1": "Low severity — minor finding or compliant-with-notes",
    "L2": "Low severity — record-keeping or systems compliance item",
}

# Conformance status canonical set. The LLM picks one per observation.
VALID_STATUSES: frozenset[str] = frozenset(
    {"Compliant", "Conditional", "NCR", "Info", "Unmatched"}
)

_CCVS_RE = re.compile(
    r"^(" + "|".join(sorted(VALID_STREAMS)) + r")-(H6|H9|M3|M4|L1|L2)$"
)


def is_valid_code(code: str) -> bool:
    """Return True iff ``code`` is one of the 25 × 6 = 150 valid codes."""
    return bool(code) and bool(_CCVS_RE.match(code))


def category_for(code: str) -> str:
    """Plain-English category for a CCVS code. Returns ``""`` on invalid."""
    if not code:
        return ""
    m = _CCVS_RE.match(code)
    if not m:
        return ""
    return STREAM_TO_CATEGORY.get(m.group(1), "")


def stream_of(code: str) -> str:
    """Return the 3-letter stream prefix or ``""`` on invalid."""
    if not code:
        return ""
    m = _CCVS_RE.match(code)
    return m.group(1) if m else ""

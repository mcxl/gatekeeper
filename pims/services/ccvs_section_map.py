"""CCVS code → eligible section names.

Used as a deterministic pre-filter when building the AI-mapping candidate
slot set. Keys are CCVS codes (uppercase). Values are sets of section names
exactly as they appear in RPD_SSA_template-inserted.docx.

If a code is missing from this map, callers fall back to the full catalog
for that observation rather than dropping it.
"""
from __future__ import annotations

# Canonical section names (must match template_index section names).
PLANNING_HIGH = "Planning and risk management (project value >$250K)"
PLANNING_LOW = "Planning and risk management (project value <$250K)"
WORKER_PPE = "Worker competency and PPE"
WAH = "General work at height"
HAZSUB = "Hazardous substances and silica control"
ROPE = "Rope access"
PLANT = "Plant and equipment safety"
DEMO = "Demolition and temporary works"
ENERGY = "Energy and services"

PLANNING_BOTH = {PLANNING_HIGH, PLANNING_LOW}

CCVS_TO_SECTIONS: dict[str, set[str]] = {
    "PLN-RA":   PLANNING_BOTH,
    "PLN-SSMP": PLANNING_BOTH,
    "PLN-EMRG": PLANNING_BOTH,
    "PLN-FA":   PLANNING_BOTH,
    "PLN-AMEN": PLANNING_BOTH,
    "PLN-SIGN": PLANNING_BOTH,
    "PLN-NOTE": PLANNING_BOTH,
    "PLN-WST":  PLANNING_BOTH,
    "PLN-ENV":  PLANNING_BOTH,
    "PLN-REC":  PLANNING_BOTH,
    "PLN-TM":   PLANNING_BOTH,
    "PLN-FENC": PLANNING_BOTH,
    "PLN-OHL":  PLANNING_BOTH,
    "PLN-PEN":  PLANNING_BOTH,
    "PLN-REV":  PLANNING_BOTH,
    "WKR-IND":  {WORKER_PPE},
    "WKR-PPE":  {WORKER_PPE},
    "WKR-LIC":  {WORKER_PPE},
    "WKR-COMP": {WORKER_PPE},
    "WKR-REC":  {WORKER_PPE},
    "WAH-RA":   {WAH},
    "WAH-FALL": {WAH},
    "WAH-EDGE": {WAH},
    "WAH-SCAF": {WAH},
    "WAH-LAD":  {WAH},
    "WAH-EWP":  {WAH, PLANT},
    "WAH-MESH": {WAH},
    "WAH-HARN": {WAH, ROPE},
    "WAH-RESC": {WAH, ROPE},
    "ROPE":     {ROPE},
    "ROPE-RIG": {ROPE},
    "ROPE-RESC":{ROPE},
    "PLNT":     {PLANT},
    "PLNT-EWP": {PLANT, WAH},
    "PLNT-CRN": {PLANT},
    "PLNT-MOB": {PLANT},
    "DEM":      {DEMO},
    "DEM-TEMP": {DEMO},
    "DEM-PROP": {DEMO},
    "ENRG":     {ENERGY},
    "ENRG-LOTO":{ENERGY},
    "ENRG-ELEC":{ENERGY},
    "HAZ":      {HAZSUB},
    "HAZ-SIL":  {HAZSUB},
    "HAZ-CHEM": {HAZSUB},
    "HAZ-SDS":  {HAZSUB},
}


def sections_for(ccvs_code: str) -> set[str] | None:
    """Return the eligible section set, or None if code is missing/unknown.

    None signals 'fall back to full catalog'.
    """
    code = (ccvs_code or "").strip().upper()
    if not code:
        return None
    return CCVS_TO_SECTIONS.get(code)

"""
core/project_requirements.py — Project Requirements Intake v1.

Create a reviewable project rule pack from a single text-bearing source,
with explicit uncertainty, while keeping the core Safe Method workflow unchanged.

The pack is used downstream to review subcontractor SWMS against:
- principal contractor requirements
- site constraints
- project-specific rules
- RA / project safety expectations

Human review/confirmation is mandatory before the pack is treated as active.
"""

from __future__ import annotations

import re
from pathlib import Path

from core.intake_extractor import ExtractionResult

# ── Output paths ────────────────────────────────────────────────────────────

_DATA_DIR = Path(__file__).parent.parent / "src" / "data"


# ── Field builder ───────────────────────────────────────────────────────────

def _field(value, status: str = "unresolved", confidence: str = "low") -> dict:
    return {"value": value, "status": status, "confidence": confidence}


# ── Rule extraction patterns ────────────────────────────────────────────────

_HRCW_SIGNAL_MAP = {
    "fall_prevention": [
        "fall from height", "working at height", "fall prevention",
        "edge protection", "harness", "scaffold", "ewp", "rope access",
    ],
    "crane_hoist": [
        "crane", "hoist", "lifting", "rigging", "dogman", "slew",
    ],
    "excavation": [
        "excavation", "trench", "trenching", "shoring",
    ],
    "demolition": [
        "demolition", "demolish", "strip-out",
    ],
    "confined_space": [
        "confined space", "tank entry", "pit entry",
    ],
    "asbestos": [
        "asbestos", "acm", "friable", "non-friable", "class a", "class b",
    ],
    "electrical": [
        "live electrical", "energised", "high voltage", "hv ",
    ],
    "structural_alteration": [
        "structural alteration", "load-bearing", "temporary support",
        "propping", "shoring",
    ],
}

_SITE_CONSTRAINT_PATTERNS = {
    "occupied_building": [
        "occupied", "tenants", "residents", "operational", "live building",
    ],
    "live_traffic": [
        "live traffic", "traffic management", "road corridor", "ctmp",
    ],
    "restricted_hours": [
        "restricted hours", "night works", "noise curfew", "after hours",
        "weekend works", "work hours",
    ],
    "heritage_listed": [
        "heritage", "conservation", "heritage-listed",
    ],
    "contaminated_site": [
        "contaminated", "remediation", "hazmat", "contaminated land",
    ],
    "adjacent_rail": [
        "rail corridor", "rail interface", "track possession",
    ],
    "public_interface": [
        "public interface", "pedestrian", "public access", "footpath",
    ],
}

_HOLD_POINT_PATTERNS = [
    r"hold[\s-]?point[:\s]+([^\n.]{10,150})",
    r"(?:do not proceed|do not commence|must not start)[^.]{5,120}(?:until|unless)[^.]{5,120}",
    r"(?:engineer|consultant|inspector)\s+(?:approval|sign[\s-]?off|inspection)\s+(?:required|before)[^.]{5,100}",
]

_PERMIT_PATTERNS = [
    r"(?:permit|licence|license|certificate|approval)\s+(?:required|needed|must be obtained)[^.]{5,100}",
    r"(?:hot work|confined space|excavation|crane)\s+permit[^.]{0,80}",
]

_PPE_PATTERNS = [
    r"(?:ppe|personal protective equipment)[:\s]+([^\n]{10,200})",
    r"(?:mandatory|minimum|required)\s+ppe[:\s]+([^\n]{10,200})",
]

_INDUCTION_PATTERNS = [
    r"(?:site induction|project induction|induction required)[^.]{0,100}",
    r"(?:white card|cpccwhs1001|construction induction)[^.]{0,80}",
]


def _extract_rules(text: str, patterns: list[str]) -> list[str]:
    """Extract rule-like statements from text using regex patterns."""
    found = []
    for pat in patterns:
        matches = re.findall(pat, text, re.IGNORECASE | re.MULTILINE)
        for m in matches:
            clean = m.strip() if isinstance(m, str) else m
            if clean and len(clean) > 10:
                found.append(clean[:200])
    return list(dict.fromkeys(found))  # dedupe preserving order


def _detect_hrcw_requirements(text: str) -> list[dict]:
    """Detect HRCW categories mentioned in the project requirements."""
    text_lower = text.lower()
    found = []
    for category, signals in _HRCW_SIGNAL_MAP.items():
        matches = [s for s in signals if s in text_lower]
        if matches:
            found.append({
                "category": category,
                "evidence": matches[:3],
                "status": "extracted",
                "confidence": "high" if len(matches) >= 2 else "medium",
            })
    return found


def _detect_site_constraints(text: str) -> list[dict]:
    """Detect site constraints from the project requirements text."""
    text_lower = text.lower()
    found = []
    for constraint, signals in _SITE_CONSTRAINT_PATTERNS.items():
        matches = [s for s in signals if s in text_lower]
        if matches:
            found.append({
                "constraint": constraint,
                "evidence": matches[:2],
                "status": "extracted",
                "confidence": "high" if len(matches) >= 2 else "medium",
            })
    return found


def _extract_named_authorities(text: str) -> list[dict]:
    """Extract named approval/inspection authorities."""
    patterns = [
        r"((?:engineer|consultant|inspector|supervisor|certifier|auditor)\s*(?:name|:)\s*[^\n,]{3,60})",
        r"((?:[A-Z][a-z]+ (?:and |& )?(?:Associates|Engineering|Consulting|Inspections))[^\n,]{0,40})",
    ]
    authorities = []
    for pat in patterns:
        for m in re.findall(pat, text, re.IGNORECASE):
            clean = m.strip()
            if clean and len(clean) > 5:
                authorities.append({
                    "authority": clean[:80],
                    "status": "extracted",
                    "confidence": "medium",
                })
    return list({a["authority"]: a for a in authorities}.values())[:10]


def _extract_project_identity(text: str) -> tuple[str, str, str]:
    """Extract project name/title."""
    patterns = [
        r"(?:project|project name|project title)[:\s]+([^\n]{5,120})",
        r"(?:re|subject)[:\s]+([^\n]{5,120})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return (m.group(1).strip(), "extracted", "medium")
    lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 20]
    if lines:
        return (lines[0][:120], "inferred", "low")
    return ("", "unresolved", "low")


def _extract_principal_contractor(text: str) -> tuple[str, str, str]:
    """Extract principal contractor name."""
    patterns = [
        r"(?:principal contractor|head contractor|builder|main contractor)[:\s]+([^\n,]{3,80})",
        r"(?:pc|principal)[:\s]+([^\n,]{3,80})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return (m.group(1).strip(), "extracted", "medium")
    return ("", "unresolved", "low")


def _extract_site_address(text: str) -> tuple[str, str, str]:
    """Extract site address."""
    patterns = [
        r"(?:site address|address|site|location)[:\s]+(\d+[^\n]{5,80}(?:NSW|QLD|VIC|SA|WA|TAS|NT|ACT)[^\n]{0,30})",
        r"(\d+\s+[A-Z][a-zA-Z]+\s+(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Lane|Ln|Way|Highway|Hwy)[^\n]{0,60})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return (m.group(1).strip(), "extracted", "medium")
    return ("", "unresolved", "low")


def _generate_review_prompts(pack: dict) -> list[str]:
    """Generate review prompts for unresolved or low-confidence fields."""
    prompts = []
    identity = pack.get("project_identity", {})
    if identity.get("project_name", {}).get("status") == "unresolved":
        prompts.append("REQUIRED: confirm project name")
    if identity.get("principal_contractor", {}).get("status") == "unresolved":
        prompts.append("REQUIRED: confirm principal contractor")
    if identity.get("site_address", {}).get("status") == "unresolved":
        prompts.append("REQUIRED: confirm site address")

    if not pack.get("hrcw_requirements"):
        prompts.append("REVIEW: no HRCW requirements detected — confirm applicable HRCW categories")
    if not pack.get("site_constraints"):
        prompts.append("REVIEW: no site constraints detected — confirm any occupancy, access, or environmental constraints")
    if not pack.get("hold_points"):
        prompts.append("REVIEW: no hold points detected — confirm any required inspection or approval gates")
    if not pack.get("permit_requirements"):
        prompts.append("REVIEW: no permit requirements detected — confirm any permits needed")

    prompts.append("CONFIRM: all extracted rules are correct and complete before activating this pack")
    return prompts


def normalize_project_requirements(
    extraction: ExtractionResult,
    clarification_note: str = "",
) -> dict:
    """Produce a reviewable project rule pack from an extraction result.

    Returns a structured artifact with field-level uncertainty.
    Human review is mandatory before the pack is treated as active.
    """
    text = extraction.raw_text
    if clarification_note:
        text = text + "\n\nClarification: " + clarification_note.strip()

    # Extract project identity
    proj_name, proj_status, proj_conf = _extract_project_identity(text)
    pc_name, pc_status, pc_conf = _extract_principal_contractor(text)
    addr_val, addr_status, addr_conf = _extract_site_address(text)

    # Extract structured rules
    hrcw_reqs = _detect_hrcw_requirements(text)
    site_constraints = _detect_site_constraints(text)
    hold_points = _extract_rules(text, _HOLD_POINT_PATTERNS)
    permits = _extract_rules(text, _PERMIT_PATTERNS)
    ppe_rules = _extract_rules(text, _PPE_PATTERNS)
    induction_rules = _extract_rules(text, _INDUCTION_PATTERNS)
    named_authorities = _extract_named_authorities(text)

    pack = {
        "project_identity": {
            "project_name": _field(proj_name, proj_status, proj_conf),
            "principal_contractor": _field(pc_name, pc_status, pc_conf),
            "site_address": _field(addr_val, addr_status, addr_conf),
        },
        "hrcw_requirements": hrcw_reqs,
        "site_constraints": site_constraints,
        "hold_points": hold_points,
        "permit_requirements": permits,
        "ppe_rules": ppe_rules,
        "induction_rules": induction_rules,
        "named_authorities": named_authorities,
        "raw_requirements_text": text[:5000] if len(text) > 5000 else text,
    }

    # Collect unresolved fields
    unresolved = []
    for field_name in ("project_name", "principal_contractor", "site_address"):
        if pack["project_identity"][field_name]["status"] == "unresolved":
            unresolved.append(field_name)
    if not hrcw_reqs:
        unresolved.append("hrcw_requirements")
    if not site_constraints:
        unresolved.append("site_constraints")

    review_prompts = _generate_review_prompts(pack)

    return {
        "pack_version": "1.0",
        "source_metadata": {
            "source_type": extraction.source_type,
            "source_label": extraction.source_label,
            "ingested_at": extraction.ingested_at,
            "source_fingerprint": extraction.source_fingerprint,
            "parser_mode": extraction.parser_mode,
            "text_extraction_succeeded": extraction.text_extraction_succeeded,
        },
        "project_rule_pack": pack,
        "extraction_warnings": extraction.warnings,
        "unresolved_fields": unresolved,
        "review_prompts": review_prompts,
        "requires_review": True,
        "status": "draft",
    }

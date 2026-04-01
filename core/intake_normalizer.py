"""
core/intake_normalizer.py — Produce a reviewable job-brief draft from extracted text.

Creates a draft intake artifact with explicit extracted/inferred/unresolved fields.
Consultant review is mandatory before generation.
Does not infer HRCW, CCVS, risk ratings, or responsibilities.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict
from typing import Optional

from core.intake_extractor import ExtractionResult

# ── Job type inference ──────────────────────────────────────────────────────

_JOB_TYPE_SIGNALS = {
    "new_build": [
        "new build", "new construction", "greenfield", "erection",
        "structural steel", "tilt-up", "formwork", "slab pour",
        "new dwelling", "new warehouse", "new building",
    ],
    "remedial": [
        "remedial", "repair", "rectification", "restoration",
        "replacement", "refurbishment", "waterproofing membrane",
        "spalling", "crack repair", "re-roof", "reroof",
    ],
    "demolition": [
        "demolition", "demolish", "strip-out", "strip out",
        "deconstruct", "pull down",
    ],
    "maintenance": [
        "maintenance", "servicing", "inspection", "cleaning",
        "filter replacement", "painting", "rope access",
        "hvac maintenance", "planned maintenance",
    ],
    "fit_out": [
        "fit-out", "fit out", "fitout", "internal works",
        "partition", "ceiling", "carpet", "joinery",
        "office refurbishment", "tenancy works",
    ],
    "civil": [
        "civil", "road", "pavement", "earthworks", "drainage",
        "stormwater", "kerb", "footpath", "excavation",
        "directional drill", "boring", "pipeline",
    ],
}

_SCOPE_MODIFIER_SIGNALS = {
    "occupied_building": [
        "occupied", "tenants", "residents", "live building",
        "operational building", "tenancy", "occupants",
    ],
    "building_under_construction": [
        "under construction", "construction site", "building site",
        "partially complete", "active site",
    ],
    "live_services_interface": [
        "live services", "energised", "pressurised", "active services",
        "service isolation",
    ],
    "confined_space_interface": [
        "confined space", "tank entry", "pit entry", "riser access",
    ],
    "working_at_heights": [
        "scaffold", "ewp", "rope access", "roof access",
        "elevated work", "work at height",
    ],
    "traffic_management": [
        "traffic management", "traffic control", "road corridor",
        "live traffic", "ctmp",
    ],
}


def _infer_job_type(text: str) -> tuple[str, str, str]:
    """Infer job_type from text. Returns (value, status, confidence)."""
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for jt, signals in _JOB_TYPE_SIGNALS.items():
        score = sum(1 for s in signals if s in text_lower)
        if score > 0:
            scores[jt] = score

    if not scores:
        return ("", "unresolved", "low")

    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    best_score = scores[best]

    # Check if clearly dominant
    runner_up = sorted(scores.values(), reverse=True)
    if len(runner_up) > 1 and runner_up[0] <= runner_up[1]:
        return (best, "inferred", "low")
    if best_score >= 3:
        return (best, "inferred", "high")
    if best_score >= 2:
        return (best, "inferred", "medium")
    return (best, "inferred", "low")


def _infer_scope_modifiers(text: str) -> tuple[list[str], str, str]:
    """Infer scope modifiers from text."""
    text_lower = text.lower()
    found = []
    for mod, signals in _SCOPE_MODIFIER_SIGNALS.items():
        if any(s in text_lower for s in signals):
            found.append(mod)

    if not found:
        return ([], "unresolved", "low")
    return (found, "inferred", "medium")


def _extract_field(text: str, patterns: list[str]) -> Optional[str]:
    """Try to extract a field value using regex patterns."""
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return None


def _extract_customer(text: str) -> tuple[str, str, str]:
    """Try to extract customer/company name."""
    patterns = [
        r"(?:client|customer|company|contractor|prepared for|attention)[:\s]+([^\n,]{3,60})",
        r"(?:from|sender|on behalf of)[:\s]+([^\n,]{3,60})",
    ]
    val = _extract_field(text, patterns)
    if val:
        return (val, "extracted", "medium")
    return ("", "unresolved", "low")


def _extract_project(text: str) -> tuple[str, str, str]:
    """Try to extract project name/description."""
    patterns = [
        r"(?:project|re|subject|scope of works|scope)[:\s]+([^\n]{5,120})",
        r"(?:works at|work at|project at)[:\s]+([^\n]{5,120})",
    ]
    val = _extract_field(text, patterns)
    if val:
        return (val, "extracted", "medium")
    # Fall back to first substantial line
    lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 20]
    if lines:
        return (lines[0][:120], "inferred", "low")
    return ("", "unresolved", "low")


def _extract_address(text: str) -> tuple[str, str, str]:
    """Try to extract site address."""
    patterns = [
        r"(?:address|site|location|at)[:\s]+(\d+[^\n]{5,80}(?:NSW|QLD|VIC|SA|WA|TAS|NT|ACT)[^\n]{0,30})",
        r"(\d+\s+[A-Z][a-zA-Z]+\s+(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Lane|Ln|Way|Place|Pl|Highway|Hwy|Boulevard|Blvd)[^\n]{0,60})",
    ]
    val = _extract_field(text, patterns)
    if val:
        return (val, "extracted", "medium")
    return ("", "unresolved", "low")


def _build_field(value, status: str, confidence: str) -> dict:
    return {"value": value, "status": status, "confidence": confidence}


def _generate_review_prompts(draft: dict) -> list[str]:
    """Generate review prompts based on unresolved/inferred fields."""
    prompts = []
    for field_name, label in [
        ("customer", "customer name"),
        ("project", "project name/description"),
        ("address", "site address"),
        ("job_type", "job type"),
        ("scope_of_works", "scope of works completeness"),
        ("scope_modifiers", "scope modifiers (occupancy, live site, etc.)"),
    ]:
        f = draft.get(field_name, {})
        status = f.get("status", "unresolved")
        if status == "unresolved":
            prompts.append(f"REQUIRED: confirm or provide {label}")
        elif status == "inferred":
            conf = f.get("confidence", "low")
            if conf in ("low", "medium"):
                prompts.append(f"REVIEW: confirm inferred {label}: {f.get('value', '')}")
    return prompts


def normalize_intake(
    extraction: ExtractionResult,
    clarification_note: str = "",
) -> dict:
    """Produce a reviewable job-brief draft from an extraction result.

    Returns a structured intake artifact with field-level uncertainty.
    Consultant review is mandatory before generation.
    """
    text = extraction.raw_text
    if clarification_note:
        text = text + "\n\nClarification: " + clarification_note.strip()

    # Extract / infer fields
    customer_val, customer_status, customer_conf = _extract_customer(text)
    project_val, project_status, project_conf = _extract_project(text)
    address_val, address_status, address_conf = _extract_address(text)
    jt_val, jt_status, jt_conf = _infer_job_type(text)
    sm_val, sm_status, sm_conf = _infer_scope_modifiers(text)

    # Scope of works — use the bulk of the extracted text
    scope_val = text.strip()
    scope_status = "extracted" if extraction.text_extraction_succeeded else "unresolved"
    scope_conf = "high" if len(scope_val) > 100 else "low"

    # Quick scan focus — inferred from job type
    qsf: list[str] = []
    if jt_val:
        qsf = _suggest_quick_scan_focus(jt_val, sm_val)

    draft = {
        "customer": _build_field(customer_val, customer_status, customer_conf),
        "project": _build_field(project_val, project_status, project_conf),
        "address": _build_field(address_val, address_status, address_conf),
        "job_type": _build_field(jt_val, jt_status, jt_conf),
        "scope_modifiers": _build_field(sm_val, sm_status, sm_conf),
        "scope_of_works": _build_field(scope_val, scope_status, scope_conf),
        "quick_scan_focus": _build_field(
            qsf, "inferred" if qsf else "unresolved",
            "medium" if qsf else "low",
        ),
    }

    # Collect warnings and unresolved fields
    unresolved = [
        k for k, v in draft.items()
        if v.get("status") == "unresolved"
    ]
    review_prompts = _generate_review_prompts(draft)

    return {
        "intake_version": "1.0",
        "source_metadata": {
            "source_type": extraction.source_type,
            "source_label": extraction.source_label,
            "ingested_at": extraction.ingested_at,
            "source_fingerprint": extraction.source_fingerprint,
            "parser_mode": extraction.parser_mode,
            "text_extraction_succeeded": extraction.text_extraction_succeeded,
        },
        "job_brief_draft": draft,
        "document_signals": [],
        "extraction_warnings": extraction.warnings,
        "unresolved_fields": unresolved,
        "review_prompts": review_prompts,
        "requires_consultant_review": True,
    }


def _suggest_quick_scan_focus(job_type: str, modifiers: list[str]) -> list[str]:
    """Suggest quick-scan focus areas based on job type and modifiers."""
    focus: list[str] = []
    _BASE = {
        "new_build": [
            "temporary works and structural sequence",
            "crane and lift interface controls",
            "edge protection and fall prevention",
        ],
        "remedial": [
            "removal and reinstatement sequence",
            "occupied building interface",
            "substrate inspection hold points",
        ],
        "demolition": [
            "asbestos survey and clearance sequence",
            "structural stability during progressive demolition",
            "exclusion zones and public interface",
        ],
        "maintenance": [
            "service isolation and lock-out sequence",
            "access method and rescue provisions",
            "live plant interface controls",
        ],
        "fit_out": [
            "services coordination and trade interface",
            "dust and noise management in occupied building",
            "fire protection during hot works",
        ],
        "civil": [
            "traffic management and pedestrian interface",
            "service proving before excavation",
            "reinstatement and as-built verification",
        ],
    }
    focus.extend(_BASE.get(job_type, []))

    if "occupied_building" in modifiers:
        focus.append("resident/tenant interface and notification")
    if "confined_space_interface" in modifiers:
        focus.append("confined space atmospheric testing and permits")
    if "live_services_interface" in modifiers:
        focus.append("staged service isolation and recommissioning")

    return focus[:6]

#!/usr/bin/env python3
"""
RPD SWMS Controlled Vocabulary

Single source of truth for hazard descriptions, control measures,
PPE items, and STOP WORK conditions used across all SWMS documents.

Every worker reading any RPD SWMS sees identical wording for identical
hazards, regardless of which document they are reading.

Usage:
    from swms_vocabulary import get_hazard, get_control, get_ppe, get_stop_work
    from swms_vocabulary import build_engineering, build_admin

Rules:
    - Always use vocabulary keys where a canonical phrase exists
    - Raw strings are permitted for task-specific content but trigger WARNING
    - Missing keys raise ValueError — add to vocabulary before using
    - Run: python src/vocab_tool.py scan  to check for unregistered phrases
"""

# ============================================================
# TAXONOMY v2.0 — Hazard families, scope, and retired codes
# ============================================================

HAZARD_FAMILIES = [
    "WAH", "IRA", "ELE", "SIL", "STR", "CFS", "ENE",
    "HOT", "MOB", "ASB", "LED", "TRF", "ENV", "CHM", "SYS"
]

HAZARD_CODE_SCOPE = {
    "WAH": "All elevated work, fall restraint, fall arrest, EWP, scaffold, ladder, roof, edge protection",
    "IRA": "Rope access positioning, anchor systems, descent, ascent, facade work",
    "ELE": "Isolation, LOTO, portable tools, overhead powerlines, test-for-dead, RCD",
    "SIL": "Grinding, drilling, jackhammering, abrasive blasting, surface prep, wet suppression",
    "STR": "Demolition, temporary works, propping, shoring, tilt-up, precast, concrete cancer repair",
    "CFS": "Entry, atmosphere testing, rescue procedures, standby person, SCBA",
    "ENE": "Hydraulic, pneumatic, gravity loads, spring-loaded, pressure systems, high-pressure washing",
    "HOT": "Welding, cutting, grinding ignition risk, open flame, fire blankets, fire watch",
    "MOB": "Excavators, cranes, forklifts, telehandlers, EWP, exclusion zones, spotter",
    "ASB": "Bonded or friable assessment, removal, painting over, encapsulation, air monitoring",
    "LED": "Paint testing, remediation, overcoating, contamination, blood lead monitoring",
    "TRF": "TPMP, pedestrian controls, public interface, road or rail corridor, spotters",
    "ENV": "Spill control, overspray, stormwater, contaminated soil, waste management",
    "CHM": "Solvents, coatings, adhesives, resins, cleaning agents, all SDS-controlled substances",
    "SYS": "Pre-start verification, site establishment, EMR, induction, permits",
}

RETIRED_CODES = {
    "WFA": "WAH",
    "HAZ": "CHM",
    "PRE": "ENE",
    "WFR": "WAH",
    "EMR": "SYS",
}


# ============================================================
# HAZARDS — Canonical hazard descriptions
# ============================================================

HAZARDS = {
    # Chemical / Substance
    "chemical_primers_solvents": {
        "canonical": "Chemical exposure from primers, membranes, and solvents",
    },
    "epoxy_resin_exposure": {
        "canonical": "Epoxy and resin chemical exposure",
    },
    "epoxy_skin_sensitisation": {
        "canonical": "Skin sensitisation from epoxy resin — Allergic contact dermatitis",
    },
    "silica_dust_cutting": {
        "canonical": "Silica dust from slot cutting",
    },
    "silica_dust_concrete": {
        "canonical": "Silica dust from concrete removal — Silicosis risk",
    },
    "dust_loading_handling": {
        "canonical": "Dust during loading and handling",
    },
    "fumes_enclosed": {
        "canonical": "Fumes in enclosed areas",
    },
    "contaminated_media": {
        "canonical": "Contaminated recycled media",
    },
    "solvent_vapour": {
        "canonical": "Solvent vapour inhalation",
    },
    "lead_dust_fume": {
        "canonical": "Lead dust and fume inhalation — Lead poisoning",
    },
    "isocyanate_inhalation": {
        "canonical": "Respiratory sensitisation from isocyanate inhalation — Occupational asthma, irreversible airway damage",
    },
    "concrete_alkaline_burns": {
        "canonical": "Chemical burns from wet concrete (alkaline)",
    },

    # Physical — Manual handling
    "manual_handling_membrane": {
        "canonical": "Manual handling of membrane rolls and equipment",
    },
    "manual_handling_heavy_bags": {
        "canonical": "Manual handling of heavy media bags (25–50kg)",
    },
    "manual_handling_heavy_forms": {
        "canonical": "Manual handling of heavy forms and steel",
    },
    "manual_handling_heavy_components": {
        "canonical": "Manual handling of heavy components",
    },
    "manual_handling_pipes": {
        "canonical": "Manual handling of pipes and pit components",
    },

    # Physical — Slip / Trip
    "slip_wet_surfaces": {
        "canonical": "Slip hazard on wet/coated surfaces",
    },
    "slip_spilled_media": {
        "canonical": "Slip hazard from spilled media",
    },
    "slip_wet_concrete": {
        "canonical": "Slip hazard on wet concrete",
    },

    # Physical — Noise / Vibration
    "noise_cutting": {
        "canonical": "Noise from cutting equipment",
    },
    "noise_general": {
        "canonical": "Noise exposure",
    },
    "vibration_power_tools": {
        "canonical": "Hand-arm vibration from power tools",
    },

    # Physical — Impact / Debris
    "eye_injury_particles": {
        "canonical": "Eye injury from loose particles",
    },
    "flying_debris": {
        "canonical": "Flying debris and fragments",
    },
    "struck_by_falling": {
        "canonical": "Struck by falling objects",
    },

    # Structural / Height
    "working_at_height": {
        "canonical": "Working at height",
    },
    "working_at_height_facade": {
        "canonical": "Working at height during façade repairs",
    },
    "structural_instability": {
        "canonical": "Structural instability during repair",
    },
    "structural_collapse_breakout": {
        "canonical": "Structural collapse if load-bearing element undermined during breakout",
    },
    "fall_unprotected_edge": {
        "canonical": "Fall from unprotected edge",
    },
    "fall_into_excavation": {
        "canonical": "Fall into excavation",
    },
    "excavation_collapse": {
        "canonical": "Collapse of excavation walls — Burial and suffocation",
    },
    "formwork_collapse": {
        "canonical": "Collapse of formwork during pour",
    },

    # Equipment
    "high_pressure_injection": {
        "canonical": "High-pressure injection injury (skin penetration)",
    },
    "hose_failure": {
        "canonical": "Hose failure/whip",
    },
    "electrical_hazard_equipment": {
        "canonical": "Electrical hazard from equipment",
    },

    # Environmental
    "overspray_drift": {
        "canonical": "Overspray drift to adjacent properties, vehicles, and persons",
    },
    "stormwater_contamination": {
        "canonical": "Environmental contamination of stormwater and waterways",
    },

    # Services
    "underground_services": {
        "canonical": "Contact with underground services",
    },
    "overhead_powerlines": {
        "canonical": "Overhead power line contact",
    },
}


# ============================================================
# CONTROLS — Canonical control measures (engineering + admin)
# ============================================================

CONTROLS = {
    # Engineering — Ventilation / Dust
    "ventilation_enclosed": {
        "canonical": "Ventilation maintained in enclosed application areas — Mechanical ventilation if natural airflow insufficient",
    },
    "dust_extraction_power_tools": {
        "canonical": "Dust extraction on all power tools — Vacuum-attached scabblers and needle guns",
    },
    "water_suppression": {
        "canonical": "Water suppression where dust extraction not practicable",
    },
    "vacuum_blade_guard": {
        "canonical": "Slot cutting with vacuum-attached blade guard — No dry cutting",
    },
    "dust_extraction_loading": {
        "canonical": "Dust extraction at blast pot loading point",
    },

    # Engineering — Physical barriers / containment
    "non_slip_paths": {
        "canonical": "Non-slip walking paths maintained around wet membrane areas",
    },
    "drainage_uncured": {
        "canonical": "Drainage provisions to prevent water pooling on uncured membrane",
    },
    "debris_containment": {
        "canonical": "Physical barriers to contain debris — Mesh screens on scaffold, drop sheets below work zone",
    },
    "epoxy_waste_containment": {
        "canonical": "Containment of epoxy/grout waste",
    },
    "media_storage_dry": {
        "canonical": "Media storage on pallets, covered, and dry",
    },

    # Engineering — Equipment settings
    "depth_stop_cutting": {
        "canonical": "Depth stop set on cutting equipment per engineering specification — Typically 25–35mm into mortar beds",
    },
    "services_scan": {
        "canonical": "Services scan (CAT/Genny) before cutting into any substrate",
    },
    "mechanical_lifting_25kg": {
        "canonical": "Mechanical lifting for bags >25kg",
    },
    "bulk_delivery_hopper": {
        "canonical": "Bulk media delivery where possible — Hopper or silo feed to blast pot",
    },

    # Admin — Documentation
    "sds_reviewed": {
        "canonical": "SDS for all products reviewed before use",
    },
    "sds_epoxy_reviewed": {
        "canonical": "SDS for all epoxy, grout, and primer products reviewed — Fosroc Nitoprime, Renderox, WHO-60 or equivalent",
    },
    "specification_reviewed": {
        "canonical": "Engineering specification and drawings reviewed before commencement — Slot depths, bar sizes, spacing, grout product confirmed",
    },
    "waterproofing_spec_reviewed": {
        "canonical": "Waterproofing specification and system data sheet reviewed — Substrate preparation, primer, membrane type, application rates, cure times confirmed",
    },
    "crack_monitoring": {
        "canonical": "Crack monitoring record completed before and after stitching",
    },
    "engineer_signoff_tolerance": {
        "canonical": "Structural engineer sign-off required before proceeding if crack width exceeds specification tolerance",
    },

    # Admin — Conditions / checks
    "temp_humidity_check": {
        "canonical": "Ambient temperature and substrate moisture checked before application — No application outside product parameters",
    },
    "wet_film_check": {
        "canonical": "Wet film thickness checks during application",
    },
    "anticarbonation_coating": {
        "canonical": "For concrete cancer remediation: anti-carbonation coating applied to cured repair mortar per engineer specification before membrane or final coating — Product and coverage rate as specified",
    },

    # Admin — Media / material
    "media_sds_silica": {
        "canonical": "Media SDS reviewed — Confirm no free crystalline silica",
    },
    "media_spec_match": {
        "canonical": "Media specification matches coating manufacturer requirements — Type, particle size, hardness confirmed",
    },
    "media_contamination_test": {
        "canonical": "Recycled media tested for contamination before re-use (lead, asbestos, other hazardous coatings)",
    },
    "media_waste_classified": {
        "canonical": "Waste media classified per EPA guidelines — Disposal to licensed facility if contaminated",
    },
}


# ============================================================
# PPE ITEMS — Canonical PPE descriptions
# ============================================================

PPE_ITEMS = {
    # Footwear
    "steel_cap": "Steel-capped footwear",
    "non_slip_footwear": "Non-slip footwear",
    "waterproof_boots": "Waterproof boots",

    # Head
    "hard_hat": "Hard hat",

    # Eye / Face
    "eye_protection": "Eye protection",
    "eye_protection_goggles": "Eye protection or goggles",
    "face_shield": "Face shield",

    # Hearing
    "hearing_protection": "Hearing protection",
    "hearing_class5": "Hearing protection (Class 5 minimum)",

    # Respiratory
    "p2_respirator": "P2 respirator (minimum)",
    "p2_dust_mask": "P2 respirator (minimum)",
    "p2_ov_respirator": "P2 respirator with organic vapour cartridge",
    "half_face_p2_ov": "Half-face respirator with P2/OV cartridge",
    "half_face_p3": "Half-face P3 with particulate filter",
    "full_face_ov_p3": "Full-face respirator with combination OV/P3 cartridge",
    "supplied_air": "Supplied-air respirator (positive-pressure airline)",

    # Hands
    "cut_resistant_gloves": "Cut-resistant gloves",
    "nitrile_gloves": "Nitrile gloves",
    "chemical_resistant_gloves": "Nitrile chemical-resistant gloves",
    "leather_gloves": "Leather gloves",
    "insulated_gloves": "Insulated gloves",

    # Body
    "hi_vis": "High-vis vest or shirt",
    "long_sleeves": "Long sleeves",
    "disposable_coveralls": "Disposable coveralls",
}


# ============================================================
# P2 VARIANT DETECTION — auto-replace non-canonical P2 terms
# ============================================================
# format_swms.py uses this list to find and replace P2 variants
# in generated documents.  Longest matches first to avoid
# partial replacement (e.g. "P2 dust mask" before "dust mask").

P2_CANONICAL = "P2 respirator (minimum)"

P2_VARIANTS = [
    # Longest first — order matters
    "P2 dust mask",
    "P2 face mask",
    "P2 mask",
    "dust mask",
    "face mask",
]


# ============================================================
# STOP WORK CONDITIONS — Canonical stop work triggers
# ============================================================

STOP_WORK = {
    # Temperature / Environment
    "temp_outside_range": "Temperature outside product application range",
    "substrate_moisture_exceeds": "Substrate moisture exceeds product tolerance",
    "rain_uncured_membrane": "Rain imminent on uncured membrane",
    "ventilation_fails": "Ventilation fails in enclosed area",
    "product_expired": "Product shelf life expired",

    # Structural
    "crack_exceeds_tolerance": "Crack width or depth exceeds engineering specification tolerance",
    "unexpected_movement": "Unexpected movement or displacement observed",
    "engineer_hold": "Structural engineer advises hold",
    "structural_concern": "Structural concern — Unexpected cracking, movement, or voids encountered",

    # Services / Cutting
    "services_in_path": "Services detected in cutting path",
    "product_temp_outside": "Product temperature outside application range",

    # Media / Material
    "media_free_silica": "Media contains free silica",
    "media_contaminated": "Recycled media contaminated",
    "media_wet_clumped": "Media wet or clumped",
    "sds_not_available": "SDS not available",
    "manual_handling_no_aids": "Manual handling of >25kg bags without mechanical aids",

    # Dust / Silica
    "dust_not_controlled": "Dust extraction fails or is inadequate — Visible dust plume beyond immediate work zone",
    "silica_visible_dust": "Silica controls not in place or visible dust present",

    # Equipment
    "equipment_fault": "Equipment fault or safety device failure",

    # General
    "exclusion_zone_breached": "Exclusion zone breached — Unauthorised entry to work zone",
}


# ============================================================
# RESOLVER FUNCTIONS
# ============================================================

def get_hazard(key):
    """Return canonical hazard phrase for key.
    Raises ValueError if key not found — forces developer
    to add to vocabulary before using."""
    if key not in HAZARDS:
        raise ValueError(
            f"Hazard key '{key}' not in swms_vocabulary.py. "
            f"Add canonical phrase before using in generator."
        )
    return HAZARDS[key]["canonical"]


def get_control(key):
    """Return canonical control phrase."""
    if key not in CONTROLS:
        raise ValueError(
            f"Control key '{key}' not in swms_vocabulary.py. "
            f"Add canonical phrase before using in generator."
        )
    return CONTROLS[key]["canonical"]


def get_ppe(*keys):
    """Return comma-joined PPE string from keys.
    Example: get_ppe("steel_cap", "p2_respirator", "eye_protection")
    Returns: "Steel-capped footwear, P2 respirator, Eye protection"
    """
    missing = [k for k in keys if k not in PPE_ITEMS]
    if missing:
        raise ValueError(
            f"PPE keys not in swms_vocabulary.py: {missing}"
        )
    return ", ".join(PPE_ITEMS[k] for k in keys)


def get_stop_work(*keys):
    """Return em dash joined STOP WORK string from keys.
    Example: get_stop_work("silica_no_controls", "edge_no_protection")
    Returns: "Silica controls not in place — No compliant edge protection"
    """
    missing = [k for k in keys if k not in STOP_WORK]
    if missing:
        raise ValueError(
            f"STOP WORK keys not in swms_vocabulary.py: {missing}"
        )
    return " \u2014 ".join(STOP_WORK[k] for k in keys)


def build_engineering(*phrases):
    """Join engineering controls as em dash chain.
    Accepts mix of vocabulary keys and raw strings.
    Raw strings are flagged as warnings — use keys where possible."""
    resolved = []
    for p in phrases:
        if p in CONTROLS:
            resolved.append(CONTROLS[p]["canonical"])
        else:
            print(f"  WARNING: Raw string in engineering controls: '{p[:60]}'")
            print(f"  Consider adding to swms_vocabulary.py CONTROLS dict")
            resolved.append(p)
    return " \u2014 ".join(resolved)


def build_admin(*phrases):
    """Same as build_engineering but for admin controls."""
    resolved = []
    for p in phrases:
        if p in CONTROLS:
            resolved.append(CONTROLS[p]["canonical"])
        else:
            print(f"  WARNING: Raw string in admin controls: '{p[:60]}'")
            resolved.append(p)
    return " \u2014 ".join(resolved)


# ============================================================
# PLAIN ENGLISH — WorkCover NSW Guidelines
# ============================================================
# Appendix 1: Formal → plain substitutions
# Appendix 2: Redundant phrases to eliminate

PLAIN_ENGLISH_SUBSTITUTIONS = {
    "ensure": "make sure",
    "commence": "start",
    "utilise": "use",
    "prior to": "before",
    "rectify": "fix",
    "discontinue": "stop",
    "relocate": "move",
    "at all times": "always",
    "in accordance with": "according to",
    "in the event that": "if",
    "due to the fact that": "because",
    "at this point in time": "now",
    "without further delay": "immediately",
    "in the near future": "soon",
    "for the purpose of": "for",
    "subsequent to": "after",
    "notify": "tell",
    "require": "need",
    "shall": "must",
    "inspect": "check",
    "dispatch": "send",
    "adhere to": "follow",
    "regarding": "about",
    "in reference to": "about",
    "observe": "follow",
    "calculate": "work out",
    "allocate": "give",
    "assist": "help",
    # Conjugated forms (word-boundary matching misses these)
    "commencing": "starting",
    "utilising": "using",
    "ensuring": "making sure",
    "rectifying": "fixing",
    "relocating": "moving",
    "notifying": "telling",
    # PPE controlled vocabulary
    "safety glasses": "eye protection",
    "safety goggles": "eye protection",
    "steel-capped safety boots": "steel-capped footwear",
    "Steel-capped safety boots": "steel-capped footwear",
    "safety boots": "steel-capped footwear",
    "steel cap boots": "steel-capped footwear",
    "steel capped boots": "steel-capped footwear",
    "steel toe boots": "steel-capped footwear",
    "work boots": "steel-capped footwear",
    "safety footwear": "steel-capped footwear",
    "P2 respirator": "P2 mask/respirator (fit-tested)",
    "P2 mask": "P2 mask/respirator (fit-tested)",
    "half-face respirator": "P2 mask/respirator (fit-tested)",
    "safety gloves": "cut-resistant gloves",
    "work gloves": "cut-resistant gloves",
    "protective gloves": "cut-resistant gloves",
    "nitrile gloves": "chemical-resistant gloves",
    "chemical resistant gloves": "chemical-resistant gloves",
    "long sleeve shirt": "hi-viz shirt or vest",
    "long sleeved shirt": "hi-viz shirt or vest",
    "long sleeves": "hi-viz shirt or vest",
    "high-vis vest": "hi-viz shirt or vest",
    "high visibility vest": "hi-viz shirt or vest",
    "hi-vis vest": "hi-viz shirt or vest",
    "high-vis shirt": "hi-viz shirt or vest",
    "goggles": "eye protection",
}

REDUNDANCIES = [
    "absolutely essential",   # use: essential
    "advance warning",        # use: warning
    "end result",             # use: result
    "final outcome",          # use: outcome
    "past history",           # use: history
    "repeat again",           # use: repeat
    "refer back",             # use: refer
    "each and every",         # use: each
    "completely eliminate",   # use: eliminate
    "consensus of opinion",   # use: consensus
]

# Map redundancies to their simpler replacements
_REDUNDANCY_REPLACEMENTS = {
    "absolutely essential": "essential",
    "advance warning": "warning",
    "end result": "result",
    "final outcome": "outcome",
    "past history": "history",
    "repeat again": "repeat",
    "refer back": "refer",
    "each and every": "each",
    "completely eliminate": "eliminate",
    "consensus of opinion": "consensus",
}


def check_vocabulary(text: str) -> list[str]:
    """
    Scan text for vocabulary issues. Returns list of warning strings.
    Checks for:
    - Plain English substitution opportunities (WorkCover NSW Appendix 1)
    - Redundant phrases (WorkCover NSW Appendix 2)
    """
    import re as _re
    warnings = []

    # Check substitutions (longer phrases first, word-boundary matching)
    for formal in sorted(PLAIN_ENGLISH_SUBSTITUTIONS, key=len, reverse=True):
        if len(formal.split()) > 1:
            pattern = _re.compile(_re.escape(formal), _re.IGNORECASE)
        else:
            pattern = _re.compile(r'\b' + _re.escape(formal) + r'\b', _re.IGNORECASE)
        if pattern.search(text):
            plain = PLAIN_ENGLISH_SUBSTITUTIONS[formal]
            warnings.append(
                f"Plain English: replace '{formal}' with '{plain}'"
            )

    # Check redundancies
    for phrase in REDUNDANCIES:
        if _re.search(_re.escape(phrase), text, _re.IGNORECASE):
            replacement = _REDUNDANCY_REPLACEMENTS.get(phrase, phrase.split()[-1])
            warnings.append(
                f"Redundancy: '{phrase}' — use '{replacement}' instead"
            )

    return warnings



# Phrases that must never be touched by further substitution once present
_DO_NOT_SUBSTITUTE = [
    "P2 mask/respirator (fit-tested)",
    "chemical-resistant gloves",
    "cut-resistant gloves",
    "steel-capped footwear",
    "eye protection",
    "hi-viz shirt or vest",
]


def enforce_vocabulary(text: str) -> str:
    """
    Auto-replace formal phrases with plain English equivalents.
    Processes longest phrases first to avoid partial matches.
    Uses word-boundary matching for ALL rules to prevent partial-word corruption.
    Also replaces redundant phrases and normalises PPE terms.
    """
    import re

    # Protect already-correct phrases by replacing with placeholders
    _placeholders = {}
    for i, phrase in enumerate(_DO_NOT_SUBSTITUTE):
        placeholder = f"\x00PHOLD{i}\x00"
        _placeholders[placeholder] = phrase
        text = text.replace(phrase, placeholder)

    # Skip rules whose target is already present (prevents double-substitution)
    _SKIP_IF_PRESENT = {
        "P2 respirator": "fit-tested",
        "P2 mask": "fit-tested",
        "half-face respirator": "fit-tested",
    }

    # Replace multi-word phrases first (longest first) — word-boundary matching
    for formal in sorted(PLAIN_ENGLISH_SUBSTITUTIONS, key=len, reverse=True):
        if len(formal.split()) > 1:
            skip_marker = _SKIP_IF_PRESENT.get(formal)
            if skip_marker and skip_marker in text.lower():
                continue
            pattern = re.compile(r'\b' + re.escape(formal) + r'\b', re.IGNORECASE)
            text = pattern.sub(PLAIN_ENGLISH_SUBSTITUTIONS[formal], text)

    # Replace single-word substitutions (whole word only)
    for formal in sorted(PLAIN_ENGLISH_SUBSTITUTIONS, key=len, reverse=True):
        if len(formal.split()) == 1:
            skip_marker = _SKIP_IF_PRESENT.get(formal)
            if skip_marker and skip_marker in text.lower():
                continue
            pattern = re.compile(r'\b' + re.escape(formal) + r'\b', re.IGNORECASE)
            text = pattern.sub(PLAIN_ENGLISH_SUBSTITUTIONS[formal], text)

    # Replace redundancies
    for phrase, replacement in _REDUNDANCY_REPLACEMENTS.items():
        pattern = re.compile(r'\b' + re.escape(phrase) + r'\b', re.IGNORECASE)
        text = pattern.sub(replacement, text)

    # Restore protected phrases from placeholders
    for placeholder, phrase in _placeholders.items():
        text = text.replace(placeholder, phrase)

    # PPE cleanup pass — normalise suffixed variants
    text = re.sub(r'closed[- ]toe\s+steel', 'steel', text, flags=re.IGNORECASE)
    text = re.sub(r'steel-capped footwear\b[^,;\n\u2014]*', 'steel-capped footwear', text)
    text = re.sub(r'eye protection\b[^,;\n\u2014]*', 'eye protection', text)
    text = re.sub(r'long[- ]sleeved? shirts?', 'hi-viz shirt or vest', text, flags=re.IGNORECASE)
    text = re.sub(r'hi-viz shirt or vest\b[^,;\n\u2014]*', 'hi-viz shirt or vest', text)

    return text

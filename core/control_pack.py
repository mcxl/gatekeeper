"""
core/control_pack.py — Combined WHS Control Pack data layer.

Assembles the structured data for a project-level WHS control pack
from classification, inference, and user-confirmed trade packages.

Does NOT render documents — produces a plain dict contract that
a renderer or API endpoint can consume.
"""

from datetime import date as _date


# ── SWMS Matrix Builder ──────────────────────────────────────────────────────

# Deterministic mapping: trade package keyword → HRCW references + default SWMS title
# Used when trade packages are extracted from scope text.
# User confirmation overrides these defaults.

_TRADE_PACKAGE_DEFAULTS = {
    "traffic management": {
        "hrcw_refs": ["H14", "H15"],
        "swms_title": "Traffic Management SWMS — Live Lane Works",
        "required_before": "Before any works commence in the road corridor",
    },
    "live lane": {
        "hrcw_refs": ["H14", "H15"],
        "swms_title": "Traffic Management SWMS — Live Lane Works",
        "required_before": "Before any works commence in the road corridor",
    },
    "road works": {
        "hrcw_refs": ["H14", "H15"],
        "swms_title": "Traffic Management SWMS — Live Lane Works",
        "required_before": "Before any works commence in the road corridor",
    },
    "service location": {
        "hrcw_refs": ["H07", "H09", "H11"],
        "swms_title": "Service Location and NDD SWMS",
        "required_before": "Before any machine excavation commences in the road corridor",
    },
    "ndd": {
        "hrcw_refs": ["H07", "H11"],
        "swms_title": "Service Location and NDD SWMS",
        "required_before": "Before any machine excavation commences",
    },
    "sydney water": {
        "hrcw_refs": ["H01", "H07"],
        "swms_title": "Sydney Water Main Relocation SWMS",
        "required_before": "Before commencement of Sydney Water main relocation works",
    },
    "water main": {
        "hrcw_refs": ["H07"],
        "swms_title": "Water Main Relocation SWMS",
        "required_before": "Before commencement of water main relocation works",
    },
    "stormwater": {
        "hrcw_refs": ["H01", "H06", "H07"],
        "swms_title": "Stormwater Drainage Installation SWMS",
        "required_before": "Before commencement of stormwater pit and pipe excavation",
    },
    "drainage": {
        "hrcw_refs": ["H07"],
        "swms_title": "Stormwater Drainage Installation SWMS",
        "required_before": "Before commencement of drainage works",
    },
    "earthworks": {
        "hrcw_refs": ["H14", "H15"],
        "swms_title": "Bulk Earthworks and Pavement Construction SWMS",
        "required_before": "Before commencement of earthworks or pavement construction",
    },
    "pavement": {
        "hrcw_refs": ["H14", "H15"],
        "swms_title": "Pavement Construction SWMS",
        "required_before": "Before commencement of pavement works",
    },
    "intersection": {
        "hrcw_refs": ["H11", "H14", "H15"],
        "swms_title": "T-Intersection Reconstruction SWMS — Geometry, Kerb, Drainage and Pavement",
        "required_before": "Before commencement of intersection reconstruction works",
    },
    "traffic signal": {
        "hrcw_refs": ["H11", "H14"],
        "swms_title": "Traffic Signal Installation and Commissioning SWMS",
        "required_before": "Before commencement of traffic signal pole installation or electrical connection",
    },
    "kerb": {
        "hrcw_refs": ["H14", "H15"],
        "swms_title": "Kerb, Gutter and Footpath Construction SWMS",
        "required_before": "Before commencement of kerb and footpath works",
    },
    "footpath": {
        "hrcw_refs": ["H14"],
        "swms_title": "Footpath and Pedestrian Infrastructure SWMS",
        "required_before": "Before commencement of pedestrian infrastructure works",
    },
    "line marking": {
        "hrcw_refs": ["H14"],
        "swms_title": "Line Marking and Signage SWMS",
        "required_before": "Before commencement of line marking in live road environment",
    },
    "signage": {
        "hrcw_refs": ["H14"],
        "swms_title": "Line Marking and Signage SWMS",
        "required_before": "Before commencement of signage installation",
    },
    "scaffold": {
        "hrcw_refs": ["H01"],
        "swms_title": "Scaffold Erection and Dismantling SWMS",
        "required_before": "Before commencement of scaffold erection",
    },
    "facade": {
        "hrcw_refs": ["H01"],
        "swms_title": "Facade Remedial Works SWMS",
        "required_before": "Before commencement of facade access or remedial works",
    },
    "electrical": {
        "hrcw_refs": ["H11"],
        "swms_title": "Electrical Installation SWMS",
        "required_before": "Before commencement of electrical work",
    },
    "gas": {
        "hrcw_refs": ["H09"],
        "swms_title": "Gas Main Works SWMS",
        "required_before": "Before commencement of work on or near gas assets",
    },
    "demolition": {
        "hrcw_refs": ["H03"],
        "swms_title": "Demolition SWMS",
        "required_before": "Before commencement of demolition works",
    },
    "confined space": {
        "hrcw_refs": ["H06"],
        "swms_title": "Confined Space Entry SWMS",
        "required_before": "Before any confined space entry",
    },
    "asbestos": {
        "hrcw_refs": ["H04"],
        "swms_title": "Asbestos Management SWMS",
        "required_before": "Before any disturbance of identified or suspected ACM",
    },
}


def _identify_trade_packages(description: str, hrcw_register: list[dict]) -> list[str]:
    """
    Extract candidate trade packages from the description text.
    Returns a list of trade package keywords that match.

    This is the extraction step — user confirmation happens downstream.
    """
    text = description.lower()
    matched = []
    seen_titles = set()

    def _add(keyword):
        defaults = _TRADE_PACKAGE_DEFAULTS.get(keyword, {})
        title = defaults.get("swms_title", keyword)
        if title not in seen_titles:
            matched.append(keyword)
            seen_titles.add(title)

    # Direct keyword matches
    for keyword in _TRADE_PACKAGE_DEFAULTS:
        if keyword in text:
            _add(keyword)

    # Civil infrastructure implied packages — standard packages for road upgrade jobs
    _CIVIL_IMPLIED = {
        # If scope mentions road works/live lane, these are almost always needed:
        "road works": ["service location", "earthworks", "line marking"],
        "live lane": ["service location", "earthworks", "line marking"],
        # If scope mentions intersection, traffic signal is separate
        "intersection": ["traffic signal"],
        # If scope mentions stormwater, drainage is included
        "stormwater": [],
        # If scope mentions pedestrian/walkway, kerb/footpath likely needed
        "pedestrian": ["kerb"],
        "walkway": ["kerb"],
        "footpath": ["kerb"],
        # If scope mentions 4 lanes / widening, earthworks + pavement implied
        "4 lanes": ["earthworks", "pavement"],
        "lane": ["earthworks"],
    }
    for trigger, implied in _CIVIL_IMPLIED.items():
        if trigger in text:
            for pkg in implied:
                _add(pkg)

    # Packages implied by CONDITIONAL/YES HRCW categories
    _HRCW_TO_TRADE = {
        "H04": "asbestos",
        "H06": "confined space",
        "H09": "gas",
    }
    for entry in hrcw_register:
        if entry["status"] in ("YES", "CONDITIONAL"):
            trade = _HRCW_TO_TRADE.get(entry["ref"])
            if trade:
                _add(trade)

    return matched


def build_swms_matrix(
    trade_packages: list[str],
    hrcw_register: list[dict],
) -> list[dict]:
    """
    Build the SWMS matrix from confirmed trade packages.

    Args:
        trade_packages: list of trade package keywords (user-confirmed)
        hrcw_register: HRCW register from _build_ra_hrcw_register()

    Returns:
        list of SWMS matrix entries per the contract schema.
    """
    # Build lookup for HRCW references that are YES or CONDITIONAL
    active_hrcw = {
        h["ref"] for h in hrcw_register
        if h["status"] in ("YES", "CONDITIONAL")
    }

    matrix = []
    seen_titles = set()

    for pkg_keyword in trade_packages:
        defaults = _TRADE_PACKAGE_DEFAULTS.get(pkg_keyword.lower())
        if not defaults:
            matrix.append({
                "trade_package": pkg_keyword.replace("_", " ").title(),
                "hrcw_refs": [],
                "swms_title": f"{pkg_keyword.replace('_', ' ').title()} SWMS",
                "submitted_by": "[Insert subcontractor]",
                "reviewed_by": "Site Manager",
                "required_before": "Before commencement of relevant works",
                "status": "provisional",
            })
            continue

        title = defaults["swms_title"]
        if title in seen_titles:
            continue
        seen_titles.add(title)

        # Filter HRCW refs to only those that are active
        relevant_refs = [r for r in defaults["hrcw_refs"] if r in active_hrcw]

        # Determine if this package is from a conditional HRCW
        all_conditional = all(
            any(h["ref"] == r and h["status"] == "CONDITIONAL" for h in hrcw_register)
            for r in relevant_refs
        ) if relevant_refs else False

        matrix.append({
            "trade_package": pkg_keyword.replace("_", " ").title(),
            "hrcw_refs": relevant_refs,
            "swms_title": title,
            "submitted_by": "[Insert subcontractor]",
            "reviewed_by": "Site Manager",
            "required_before": defaults["required_before"],
            "status": "provisional" if all_conditional else "confirmed",
        })

    return matrix


# ── Control Pack Builder ─────────────────────────────────────────────────────

def build_control_pack(
    description: str,
    project_meta: dict,
    trade_packages: list[str] | None = None,
    jurisdiction: str = "AU",
) -> dict:
    """
    Assemble the complete control pack data structure.

    Args:
        description: project scope description
        project_meta: project metadata (name, address, pcbu, client, etc.)
        trade_packages: user-confirmed trade packages (if None, auto-extracted)
        jurisdiction: jurisdiction code

    Returns:
        dict matching the control pack output contract.
    """
    from core.inference_matrix import (
        infer_to_dict_ra,
        classify_ra_scope,
    )

    # Step 1: Classification and inference
    result = infer_to_dict_ra(description, jurisdiction=jurisdiction)
    classification = result.get("ra_classification", classify_ra_scope(description))
    hrcw_register = result.get("ra_hrcw_register", [])
    hazard_list = result.get("hazard_list", [])
    phase_groups = result.get("phase_groups", [])

    # Step 2: Trade packages — extract if not provided
    if trade_packages is None:
        trade_packages = _identify_trade_packages(description, hrcw_register)

    # Step 3: SWMS matrix
    swms_matrix = build_swms_matrix(trade_packages, hrcw_register)

    # Step 4: Hold points — derive from classification and hazards
    hold_points = _build_control_pack_hold_points(classification, hazard_list, trade_packages)

    # Step 4b: Crosswalk — link hold points to SWMS packages
    _crosswalk_hold_points_to_packages(swms_matrix, hold_points)

    # Step 5: Risk register — reformat hazard list + seed benchmark risks
    risk_register = _build_risk_register(hazard_list, phase_groups, swms_matrix)

    # Step 6: Scope summary
    scope_summary = _build_scope_summary(description, classification)

    # Step 7: Review metadata
    review_meta = _build_review_metadata(
        hrcw_register, hazard_list, project_meta, trade_packages
    )

    # Step 8: Assemble
    doc_date = project_meta.get("date", _date.today().strftime("%d/%m/%Y"))

    return {
        "document_type": "combined_whs_control_pack",
        "version": project_meta.get("version", "1.0"),
        "generated_at": _date.today().isoformat(),

        "project_meta": {
            "project_name": project_meta.get("project_name", "[To be confirmed]"),
            "site_address": project_meta.get("site_address", "[To be confirmed]"),
            "pcbu": project_meta.get("pcbu_name", project_meta.get("pcbu", "[To be confirmed]")),
            "client": project_meta.get("client", "[To be confirmed]"),
            "jurisdiction": jurisdiction,
            "version": project_meta.get("version", "1.0"),
            "date": doc_date,
            "prepared_by": project_meta.get("manager_name", project_meta.get("prepared_by", "[To be confirmed]")),
        },

        "scope_summary": scope_summary,
        "ra_classification": classification,
        "hrcw_register": hrcw_register,
        "swms_matrix": swms_matrix,
        "hold_points": hold_points,
        "risk_register": risk_register,
        "review_meta": review_meta,
        "inference": result,
    }


# ── Hold Points ──────────────────────────────────────────────────────────────

def _build_control_pack_hold_points(
    classification: dict, hazards: list[dict], trade_packages: list[str],
) -> list[dict]:
    """Build structured hold points for the control pack."""
    modifiers = set(classification.get("scope_modifiers", []))
    job_type = classification.get("job_type", "")
    hold_points = []
    hp_num = 1

    def _add(name, packages, condition, authorised, evidence, hp_type="whs_critical"):
        nonlocal hp_num
        hold_points.append({
            "ref": f"HP-{hp_num:02d}",
            "name": name,
            "type": hp_type,  # "whs_critical" or "qa_authority"
            "trade_packages": packages if isinstance(packages, list) else [packages],
            "condition": condition,
            "authorised_by": authorised,
            "evidence_required": evidence,
        })
        hp_num += 1

    # WHS-critical hold points
    if job_type == "civil_infrastructure" or "road_corridor" in modifiers or "live_lanes" in modifiers:
        _add(
            "Current Traffic Management Arrangement Accepted Before Works In Road Corridor",
            "All trade packages",
            "A current, accepted traffic management arrangement is in place for the specific works about to commence",
            "Site Manager + Traffic Management Subcontractor",
            "CTMP accepted for the current stage. Traffic management inspection completed.",
            "whs_critical",
        )

    # Trench / excavation — WHS critical
    if any("excavat" in h.get("hazard", "").lower() or "trench" in h.get("hazard", "").lower() for h in hazards):
        _add(
            "Trench Or Excavation Inspection Before Worker Entry",
            "All packages involving excavation",
            "Competent person has inspected the relevant trench or excavation and confirmed it is safe for worker entry or approach",
            "Competent person appointed by the relevant subcontractor",
            "Trench/excavation inspection record signed and dated before entry",
            "whs_critical",
        )

    # Service proving — WHS critical
    if any("excavat" in h.get("hazard", "").lower() for h in hazards):
        _add(
            "Service Proving Completed Before Machine Excavation",
            "All packages involving machine excavation",
            "All utilities in the proposed excavation zone have been positively identified by non-destructive digging",
            "Site Manager",
            "NDD/potholing records with service locations, depths and offsets",
            "whs_critical",
        )

    # Sydney Water — Authority gate
    if "utility_relocation" in modifiers or any("sydney water" in h.get("hazard", "").lower() for h in hazards):
        _add(
            "Sydney Water Hold Points And Witness Points Satisfied",
            "Sydney Water Asset Relocation",
            "All Sydney Water mandatory hold points and witness points satisfied before connection to or disconnection from live main",
            "Sydney Water Asset Protection representative",
            "Sydney Water hold point sign-off records on site",
            "qa_authority",
        )

    # Compaction — QA gate
    if any("pavement" in h.get("hazard", "").lower() for h in hazards):
        _add(
            "Pavement Layer Compaction Testing Accepted",
            "Earthworks and Pavement",
            "Compaction testing for the current layer meets the specified requirements before next layer is placed",
            "Site Manager",
            "Compaction test results signed and accepted",
            "qa_authority",
        )

    # Traffic signal commissioning — Authority gate
    if "traffic_signals" in modifiers:
        _add(
            "Traffic Signal Commissioning Accepted Before Energisation",
            "Traffic Signal Installation",
            "Traffic signal installation is complete and has been inspected and accepted by the relevant authority",
            "Transport for NSW or relevant authority",
            "Signal commissioning acceptance record",
            "qa_authority",
        )

    return hold_points


# ── Crosswalk ────────────────────────────────────────────────────────────────

def _crosswalk_hold_points_to_packages(swms_matrix: list[dict], hold_points: list[dict]) -> None:
    """Add linked_hold_points to each SWMS matrix entry based on trade_packages overlap."""
    for entry in swms_matrix:
        pkg_name = entry.get("trade_package", "").lower()
        linked = []
        for hp in hold_points:
            hp_packages = " ".join(hp.get("trade_packages", [])).lower()
            if pkg_name in hp_packages or "all" in hp_packages:
                linked.append(hp["ref"])
        entry["linked_hold_points"] = linked


# ── Risk Register ────────────────────────────────────────────────────────────

# Map hazard keywords to trade package groups for risk register
_HAZARD_TO_PACKAGE = [
    # Civil infrastructure packages (ordered by construction sequence)
    ("Traffic Management", ["traffic", "live lane", "live road", "road corridor"]),
    ("Service Location and NDD", ["service location", "ndd", "potholing", "dial before",
                                   "existing services", "service strike"]),
    ("Sydney Water Asset Relocation", ["sydney water", "water main", "water asset"]),
    ("Stormwater Drainage", ["stormwater", "drainage", "culvert", "headwall"]),
    ("Bulk Earthworks and Pavement", ["pavement", "earthworks", "compaction", "subbase",
                                       "road base", "asphalt", "chip seal", "road surface"]),
    ("T-Intersection Reconstruction", ["intersection"]),
    ("Traffic Signal Installation", ["traffic signal", "traffic light", "signal installation"]),
    ("Kerb, Gutter and Footpath", ["kerb", "footpath", "pedestrian ramp", "pedestrian"]),
    ("Line Marking and Reinstatement", ["line marking", "road sign", "signage"]),
    # Utility packages
    ("Gas Main Works", ["gas main", "gas pipe", "pressurised gas"]),
    ("Electrical Works", ["electrical", "energised", "switchboard", "cable"]),
    # Building / access packages
    ("Scaffold and Access", ["scaffold", "ewp", "access platform"]),
    ("Facade Works", ["facade", "external wall", "coating", "waterproof", "spalling"]),
    # Standing hazards (cross-cutting)
    ("All Packages — Standing Hazards", ["mobile plant", "excavat", "trench",
                                          "manual handling", "silica", "heat",
                                          "near public", "near waterway", "road opening"]),
]


# Benchmark risk entries per package — seeded when a package is in the SWMS matrix
# but the inference engine didn't produce a matching hazard.
# These are minimum-standard risks that a consultant would expect.
_PACKAGE_BENCHMARK_RISKS = {
    "Traffic Management": [
        {"activity": "Establishment of live lane closures and temporary traffic arrangements",
         "controls": "CTMP prepared by qualified traffic management designer. Workers must not enter live lane area until traffic management is in place and accepted.",
         "initial_risk": "High", "residual_risk": "Medium"},
        {"activity": "Pedestrian management at intersection and along works corridor",
         "controls": "Temporary pedestrian pathways maintained throughout. Pedestrian exclusion from active work zones with physical barriers.",
         "initial_risk": "High", "residual_risk": "Medium"},
    ],
    "Service Location and NDD": [
        {"activity": "DBYD enquiry, NDD/potholing and marking of all utilities in excavation zone",
         "controls": "DBYD completed before any excavation. NDD to positively identify all services. No machine excavation within 500mm of confirmed service — hand dig only.",
         "initial_risk": "High", "residual_risk": "Medium"},
    ],
    "Sydney Water Asset Relocation": [
        {"activity": "Excavation of relocation trench for Sydney Water main",
         "controls": "Shoring/battering per geotechnical assessment. Sydney Water representative on site during excavation within 2m of asset.",
         "initial_risk": "High", "residual_risk": "Medium"},
        {"activity": "Connection to and disconnection from live Sydney Water main",
         "controls": "Sydney Water hold points satisfied before connection. Exclusion zone and dewatering plan for uncontrolled water release.",
         "initial_risk": "High", "residual_risk": "Medium"},
    ],
    "Stormwater Drainage": [
        {"activity": "Excavation of stormwater pit and pipe trenches in road corridor",
         "controls": "Shoring/battering for depths >1.5m. Traffic management in place before excavation in road reserve.",
         "initial_risk": "High", "residual_risk": "Medium"},
    ],
    "Bulk Earthworks and Pavement": [
        {"activity": "Removal of existing chip seal pavement and earthworks to design level",
         "controls": "Silica dust controls — wet cutting, RPE where RCS exposure possible. Plant-pedestrian separation maintained.",
         "initial_risk": "Medium", "residual_risk": "Low"},
        {"activity": "Road pavement construction — subbase, base course, wearing course",
         "controls": "Compaction testing accepted before next layer placed. Traffic management maintained during all pavement works.",
         "initial_risk": "Medium", "residual_risk": "Low"},
    ],
    "T-Intersection Reconstruction": [
        {"activity": "Intersection reconstruction — kerb, drainage, pavement and geometry changes",
         "controls": "Staged construction with traffic management for each phase. Plant exclusion zones around workers on foot.",
         "initial_risk": "High", "residual_risk": "Medium"},
    ],
    "Traffic Signal Installation": [
        {"activity": "Traffic signal pole installation — EWP or crane operations at intersection",
         "controls": "Licensed electrician for all electrical connections. Commissioning acceptance by Transport for NSW before energisation.",
         "initial_risk": "High", "residual_risk": "Medium"},
    ],
    "Kerb, Gutter and Footpath": [
        {"activity": "Kerb, gutter, footpath and pedestrian ramp construction",
         "controls": "Pedestrian pathways maintained during construction. DDA-compliant temporary access where existing paths are disrupted.",
         "initial_risk": "Medium", "residual_risk": "Low"},
    ],
    "Line Marking and Reinstatement": [
        {"activity": "Line marking and road sign installation in live road environment",
         "controls": "Traffic management in place for all line marking operations. Workers in hi-vis with traffic controller escort.",
         "initial_risk": "Medium", "residual_risk": "Low"},
    ],
}


def _assign_package_group(hazard_name: str) -> str:
    """Assign a hazard to the most relevant trade package group."""
    nl = hazard_name.lower()
    for group, keywords in _HAZARD_TO_PACKAGE:
        if any(kw in nl for kw in keywords):
            return group
    return "General Construction"


def _build_risk_register(hazards: list[dict], phase_groups: list[dict],
                         swms_matrix: list[dict] | None = None) -> list[dict]:
    """Build risk register grouped by trade package, seeded with benchmark risks."""
    # First assign inference-derived hazards to package groups
    entries = []
    covered_groups = set()

    for h in hazards:
        ctrls = h.get("controls", {})
        eng = ctrls.get("engineering", [])
        adm = ctrls.get("admin", [])
        control_summary = ". ".join(eng[:1] + adm[:1]) if (eng or adm) else "Refer to site-specific controls"

        group = _assign_package_group(h.get("hazard", ""))
        confidence = h.get("confidence", "if_applicable")
        covered_groups.add(group)

        entries.append({
            "group": group,
            "activity": h.get("hazard", ""),
            "hrcw_category": h.get("phase", ""),
            "initial_risk": h.get("risk_level", "Medium"),
            "controls": control_summary,
            "residual_risk": h.get("residual_level", "Low"),
            "responsible": "All relevant packages",
            "status": "confirmed" if confidence == "confirmed" else "provisional",
        })

    # Seed benchmark risks for packages in the SWMS matrix that have no entries
    if swms_matrix:
        # Map SWMS package display names to benchmark group names
        _PKG_TO_GROUP = {
            "live lane": "Traffic Management",
            "traffic management": "Traffic Management",
            "road works": "Traffic Management",
            "service location": "Service Location and NDD",
            "ndd": "Service Location and NDD",
            "sydney water": "Sydney Water Asset Relocation",
            "water main": "Sydney Water Asset Relocation",
            "stormwater": "Stormwater Drainage",
            "drainage": "Stormwater Drainage",
            "earthworks": "Bulk Earthworks and Pavement",
            "pavement": "Bulk Earthworks and Pavement",
            "intersection": "T-Intersection Reconstruction",
            "traffic signal": "Traffic Signal Installation",
            "kerb": "Kerb, Gutter and Footpath",
            "footpath": "Kerb, Gutter and Footpath",
            "line marking": "Line Marking and Reinstatement",
            "signage": "Line Marking and Reinstatement",
        }

        for entry in swms_matrix:
            pkg = entry.get("trade_package", "").lower()
            group = _PKG_TO_GROUP.get(pkg)
            if group and group not in covered_groups:
                benchmarks = _PACKAGE_BENCHMARK_RISKS.get(group, [])
                for br in benchmarks:
                    entries.append({
                        "group": group,
                        "activity": br["activity"],
                        "hrcw_category": "",
                        "initial_risk": br.get("initial_risk", "Medium"),
                        "controls": br["controls"],
                        "residual_risk": br.get("residual_risk", "Low"),
                        "responsible": "Relevant subcontractor",
                        "status": "benchmark",
                    })
                covered_groups.add(group)

    # Sort by construction sequence
    _GROUP_ORDER = [g for g, _ in _HAZARD_TO_PACKAGE] + ["General Construction"]
    entries.sort(key=lambda e: (
        _GROUP_ORDER.index(e["group"]) if e["group"] in _GROUP_ORDER else 99,
        e["activity"]
    ))

    register = []
    ref_num = 1
    for e in entries:
        e["ref"] = f"RR-{ref_num:02d}"
        register.append(e)
        ref_num += 1

    return register


# ── Scope Summary ────────────────────────────────────────────────────────────

def _build_scope_summary(description: str, classification: dict) -> str:
    """Build a concise scope summary from description and classification."""
    job_type = classification.get("job_type", "construction")
    modifiers = classification.get("scope_modifiers", [])

    _JT_LABELS = {
        "civil_infrastructure": "Civil infrastructure construction",
        "remedial": "Remedial and repair works",
        "fit_out": "Fit-out and services installation",
        "retrofit": "Retrofit and upgrade works",
        "maintenance": "Maintenance and repair",
        "demolition": "Demolition works",
        "upgrade": "Upgrade and extension works",
        "new_build": "New construction",
    }

    summary = _JT_LABELS.get(job_type, job_type.replace("_", " ").title())
    summary += ". " + description.strip()

    if len(summary) > 500:
        # Truncate at sentence boundary
        truncated = summary[:500]
        last_stop = truncated.rfind(". ")
        if last_stop > 200:
            summary = truncated[:last_stop + 1]
        else:
            summary = truncated.rstrip() + "..."

    return summary


# ── Review Metadata ──────────────────────────────────────────────────────────

def _build_review_metadata(
    hrcw_register: list[dict],
    hazards: list[dict],
    project_meta: dict,
    trade_packages: list[str],
) -> dict:
    """Build review metadata with open items from missing/conditional data."""
    open_items = []

    # Missing project fields
    _FIELD_LABELS = {
        "project_name": "Project name",
        "site_address": "Site address",
        "pcbu_name": "PCBU / Principal Contractor",
        "client": "Client / Principal",
    }
    for field in ("project_name", "site_address", "pcbu_name", "client"):
        val = project_meta.get(field, "")
        if not val or val == "[To be confirmed]":
            open_items.append({
                "item": f"{_FIELD_LABELS.get(field, field)} \u2014 confirm before issue",
                "source": "extraction",
                "resolved": False,
            })

    # Conditional HRCW — use specific reason from register
    for h in hrcw_register:
        if h["status"] == "CONDITIONAL":
            reason = h.get("reason", "confirm on site")
            open_items.append({
                "item": f"{h['ref']}: {h['name']} \u2014 {reason}",
                "source": "hrcw_register",
                "resolved": False,
            })

    # Hazards requiring verification
    for h in hazards:
        conf = h.get("confidence", "")
        if conf == "requires_verification":
            open_items.append({
                "item": f"{h['hazard']} — confirm whether this hazard is present",
                "source": "risk_register",
                "resolved": False,
            })

    # Trade packages not user-confirmed (all auto-extracted)
    if trade_packages:
        open_items.append({
            "item": "Trade packages have been auto-extracted — confirm before issue",
            "source": "extraction",
            "resolved": False,
        })

    fields_confirmed = sum(1 for f in ("project_name", "site_address", "pcbu_name", "client")
                           if project_meta.get(f) and project_meta.get(f) != "[To be confirmed]")
    fields_missing = 4 - fields_confirmed

    return {
        "source_documents": [],
        "reviewed_by": None,
        "reviewed_at": None,
        "review_status": "draft",
        "open_items": open_items,
        "confidence_summary": {
            "fields_confirmed": fields_confirmed,
            "fields_inferred": 0,
            "fields_missing": fields_missing,
        },
    }

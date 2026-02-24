#!/usr/bin/env python3
"""
SWMS_TEST_Waterproofing.py — Job-specific SWMS generation
Generated from SWMS_BASE_GENERAL.py v16.3

Job: General waterproofing to balcony slabs
Site: 45 Construction Ave, Parramatta NSW 2150
PBCU: RPD Pty Ltd
Date: 24/02/2026
"""

import sys
import os

# Add src to path so we can import the engine
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from swms_generator import (
    generate_swms, _generate_short_code,
)


# ══════════════════════════════════════════════════════════════════════════════
# ✏️  SECTION 1 — PROJECT
# ══════════════════════════════════════════════════════════════════════════════

PROJECT = {
    "pbcu_line": (
        "■ PBCU: RPD Pty Ltd "
        "1 Safety Street Sydney NSW 2000 "
        "Phone: 02 9000 0000 | ABN: 12 345 678 901"
    ),
    "site":       "45 Construction Ave, Parramatta NSW 2150",
    "pc":         "SD Group",
    "date":       "24/02/2026",
    "manager":    "Alan Richardson",
    "supervisor": "Alan Richardson",
    "reviewer":   "Alan Richardson",
    "activity": (
        "General waterproofing to balcony slabs. "
        "Access via ground level and ladders. "
        "Surface preparation, primer application, and liquid membrane application. "
        "Approximately 3 days duration."
    ),
    "emergency_contact": "000 / Site Supervisor Alan Richardson",
    "assembly_point":    "Front footpath — 45 Construction Ave (briefed at site induction)",

    # ── HRCW — tick True for any that apply ──────────────────────────────────
    "hrcw": {
        "falling_2m":             True,   # Ladder use — risk of fall >2m
        "telecom_tower":          False,
        "demolition":             False,
        "disturb_asbestos":       False,
        "load_bearing":           False,
        "confined_space":         False,
        "shaft_trench":           False,
        "explosives":             False,
        "pressurised_gas":        False,
        "chemical_lines":         False,
        "near_powerlines":        False,
        "flammable_atmosphere":   False,
        "tilt_up_precast":        False,
        "traffic_corridor":       False,
        "powered_mobile_plant":   False,
        "artificial_temperature": False,
        "water_drowning":         False,
        "diving":                 False,
    },

    # ── Output filenames ─────────────────────────────────────────────────────
    "output_standard": "SWMS_TEST_Waterproofing_24022026_Standard",
    "output_ccvs":     "SWMS_TEST_Waterproofing_24022026_CCVS",
    "title_prefix":    "SWMS — Balcony Waterproofing — 45 Construction Ave Parramatta",
}


# ══════════════════════════════════════════════════════════════════════════════
# ✏️  SECTION 2 — TASKS
#     SYS and EMR are auto-injected. Do not add them here.
#     Tasks are not numbered — engine numbers after SYS injection.
# ══════════════════════════════════════════════════════════════════════════════

TASKS_STANDARD = [

    # ── Task: Ladder Use — Short Duration (WAH-3) ────────────────────────────
    {
        "task": (
            "Ladder Use — Short Duration Only\n"
            "A-frame or extension ladder for balcony access where EWP or scaffold "
            "is not reasonably practicable."
        ),
        "hazard": (
            "Fall from height. "
            "Kick-out or instability. "
            "Overreaching. "
            "Dropped tools striking persons below."
        ),
        "pre": 6,
        "controls": (
            "WAH (High — C=3): Controls in place.\n"
            "Eliminate: Use EWP or scaffold first — ladder only where not practicable.\n"
            "Engineering: Industrial-rated ladder, correct angle (4:1 extension), "
            "non-slip feet, secured where possible.\n"
            "Admin: Site-specific WaH RA completed before use — confirms ladder is "
            "only practicable method. Three points of contact at all times. "
            "No top two rungs. No overreaching. Barricade area below.\n"
            "PPE: Non-slip footwear, helmet, tool lanyards.\n"
            "Remove from exposure and rectify if ladder is damaged or conditions unsafe."
        ),
        "post": 2,
        "resp": "Alan Richardson",
        "audit": "STD-6-3-WAH",
        "hazard_summary": "Fall from ladder — kick-out, overreaching, dropped tools onto persons below.",
        "control_summary": "EWP or scaffold first; WaH RA required; 4:1 angle; three points contact; barricade below.",
    },

    # ── Task: Surface Preparation — Balcony Substrate (SIL-3) ────────────────
    {
        "task": (
            "Surface Preparation — Balcony Substrate\n"
            "Grinding, sanding, and cleaning concrete balcony slabs prior to "
            "waterproofing membrane application."
        ),
        "hazard": (
            "Silica dust inhalation from grinding concrete — silicosis risk. "
            "Flying debris and sparks. "
            "Chemical exposure from cleaners. "
            "Noise and vibration from angle grinder."
        ),
        "pre": 6,
        "controls": (
            "SIL (High — C=3): Controls in place.\n"
            "Eliminate: Wet sanding where practicable — no dry grinding.\n"
            "Engineering: On-tool extraction (HEPA vacuum) or wet suppression on grinder. "
            "Blade guard fitted and intact.\n"
            "Admin: P2 or P3 respirator — fit-tested where required. "
            "Eye and face protection. Hearing protection. "
            "Exclusion zone around grinder for debris. "
            "Inspect wheel before fitting — no cracks or damage. "
            "Test for lead or assume present if pre-2000 building — lead-safe procedures apply.\n"
            "PPE: P2/P3 respirator, face shield, hearing protection, gloves.\n"
            "Remove from exposure and rectify if dust controls fail."
        ),
        "post": 2,
        "resp": "Alan Richardson",
        "audit": "STD-6-3-SIL",
        "hazard_summary": "Silica dust inhalation from grinding concrete balcony slabs — silicosis risk.",
        "control_summary": "On-tool extraction or wet suppression; P2/P3 respirator; face shield; exclusion zone.",
    },

    # ── Task: Waterproofing Membrane Application (ENV-4) ─────────────────────
    {
        "task": (
            "Waterproofing Membrane Application\n"
            "Apply liquid waterproofing primer and membrane to balcony slabs."
        ),
        "hazard": (
            "Solvent vapour inhalation in semi-enclosed balcony spaces. "
            "Skin sensitisation from isocyanates or epoxy components. "
            "Ignition of flammable membrane products. "
            "Slip on wet or uncured membrane."
        ),
        "pre": 6,
        "controls": (
            "ENV (High — C=3): Controls in place.\n"
            "Engineering: Forced ventilation in semi-enclosed balcony spaces. "
            "Continuous air monitoring if isocyanate-based product used.\n"
            "Admin: SDS reviewed for primer and membrane — confirm if isocyanate, "
            "epoxy, or solvent-based. "
            "Medical fitness confirmed for isocyanate exposure. "
            "Ignition sources eliminated before application. "
            "No walking on uncured membrane — barricade until cured.\n"
            "PPE: Supplied-air respirator or half-face with appropriate cartridge (per SDS), "
            "chemical-resistant gloves, coveralls, eye protection."
        ),
        "post": 2,
        "resp": "Alan Richardson",
        "audit": "STD-6-3-ENV",
        "hazard_summary": "Solvent vapour in enclosed balcony, isocyanate sensitisation, ignition risk, slip on uncured membrane.",
        "control_summary": "Forced ventilation; SDS controls; isocyanate fitness check; ignition eliminated; barricade until cured.",
    },

    # ── Task: Chemical Application — Solvents (ENV-1) ────────────────────────
    {
        "task": (
            "Chemical Application — Solvents and Cleaning Agents\n"
            "Use of mineral turpentine, primers, and cleaning agents during "
            "waterproofing preparation and application."
        ),
        "hazard": (
            "Solvent vapour inhalation. "
            "Skin and eye contact. "
            "Ignition of flammable vapours. "
            "Environmental contamination — spill to stormwater or drain."
        ),
        "pre": 4,
        "controls": (
            "ENV (Medium — C=2): Controls in place.\n"
            "Admin: SDS reviewed before use — controls confirmed. "
            "Ventilation confirmed adequate before application. "
            "Ignition sources eliminated before opening solvent-based products. "
            "Spill kit on site. No disposal to drain or stormwater.\n"
            "PPE: Respirator per SDS, chemical-resistant gloves, eye protection, coveralls.\n"
            "Remove from exposure and rectify if ventilation inadequate."
        ),
        "post": 1,
        "resp": "Alan Richardson",
        "audit": "STD-4-2-ENV",
        "hazard_summary": "Solvent vapour inhalation, skin contact, ignition risk, spill to stormwater.",
        "control_summary": "SDS reviewed; ventilation confirmed; ignition sources eliminated; spill kit on site.",
    },

    # ── Task: Public Interface — Residential (TRF-2) ─────────────────────────
    {
        "task": (
            "Public Interface — Residential Premises\n"
            "Works on balconies of occupied residential building with public nearby."
        ),
        "hazard": (
            "Public or occupant entry into work zone. "
            "Dropped objects or debris reaching public areas. "
            "Noise, dust, or fume impact on occupants. "
            "Slips and trips — tools, leads, debris in public areas."
        ),
        "pre": 4,
        "controls": (
            "TRF (Medium — C=2): Controls in place.\n"
            "Engineering: Hoarding, barriers, or screens to fully separate public from work zone. "
            "Overhead catch protection where drop risk to public areas.\n"
            "Admin: Coordinate work hours with building manager. "
            "Noise, dust, and fume management — schedule high-impact work for agreed times. "
            "Work zone inspected and secured at end of each shift. "
            "Clear and maintain emergency egress at all times. "
            "Residents notified before commencement.\n"
            "PPE: Hi-vis, safety boots, appropriate dust/fume controls."
        ),
        "post": 1,
        "resp": "Alan Richardson",
        "audit": "STD-4-2-TRF",
        "hazard_summary": "Public or occupant entry into work zone — dropped objects — noise and dust impact.",
        "control_summary": "Hoarding or barriers to separate public; overhead catch protection; coordinate hours; secure site each shift.",
    },

]

# CCVS variants — same tasks with CCVS hold point language for eligible tasks
TASKS_CCVS = [

    # ── Task: Ladder Use — CCVS (WAH-3) ──────────────────────────────────────
    {
        "task": (
            "Ladder Use — Short Duration Only\n"
            "A-frame or extension ladder for balcony access where EWP or scaffold "
            "is not reasonably practicable."
        ),
        "hazard": (
            "Fall from height. "
            "Kick-out or instability. "
            "Overreaching. "
            "Dropped tools striking persons below."
        ),
        "pre": 6,
        "controls": (
            "WAH (High — C=3) CCVS HOLD POINTS:\n"
            "Work must not commence until:\n"
            "(1) WaH RA completed — confirms ladder is only practicable method.\n"
            "(2) Industrial-rated ladder inspected — no defects, correct angle (4:1), non-slip feet.\n"
            "(3) Area below barricaded — exclusion zone maintained.\n"
            "(4) All workers briefed — three points of contact, no top two rungs, no overreaching.\n"
            "Confirmation retained in site diary or digital system.\n"
            "Remove from exposure and rectify if ladder is damaged or conditions unsafe."
        ),
        "post": 2,
        "resp": "Alan Richardson",
        "audit": "CCVS-6-3-WAH",
        "hazard_summary": "Fall from ladder — kick-out, overreaching, dropped tools onto persons below.",
        "control_summary": "WaH RA completed; ladder inspected (4:1, non-slip); barricade below; three points contact; stop-work if damaged or unsafe.",
    },

    # ── Task: Surface Preparation — CCVS (SIL-3) ─────────────────────────────
    {
        "task": (
            "Surface Preparation — Balcony Substrate\n"
            "Grinding, sanding, and cleaning concrete balcony slabs prior to "
            "waterproofing membrane application."
        ),
        "hazard": (
            "Silica dust inhalation from grinding concrete — silicosis risk. "
            "Flying debris and sparks. "
            "Chemical exposure from cleaners. "
            "Noise and vibration from angle grinder."
        ),
        "pre": 6,
        "controls": (
            "SIL (High — C=3) CCVS HOLD POINTS:\n"
            "Work must not commence until:\n"
            "(1) Wet suppression or on-tool HEPA extraction confirmed operational.\n"
            "(2) Blade guard fitted and intact — wheel inspected, no cracks or damage.\n"
            "(3) P2/P3 respirator fit-tested and worn.\n"
            "(4) Exclusion zone established around grinder work area.\n"
            "(5) Lead status confirmed — if pre-2000 building, assume present, lead-safe procedures apply.\n"
            "Confirmation retained in site diary or digital system.\n"
            "Remove from exposure and rectify if dust controls fail."
        ),
        "post": 2,
        "resp": "Alan Richardson",
        "audit": "CCVS-6-3-SIL",
        "hazard_summary": "Silica dust inhalation from grinding concrete balcony slabs — silicosis risk.",
        "control_summary": "Wet suppression or HEPA extraction confirmed; P2/P3 fit-tested; exclusion zone; lead status confirmed; stop-work if dust controls fail.",
    },

    # ── Task: Waterproofing Membrane — CCVS (ENV-4) ──────────────────────────
    # Note: ENV does NOT trigger CCVS per locked list (TRF and ENV excluded).
    # Using STD controls even in CCVS version per MASTER rules.
    {
        "task": (
            "Waterproofing Membrane Application\n"
            "Apply liquid waterproofing primer and membrane to balcony slabs."
        ),
        "hazard": (
            "Solvent vapour inhalation in semi-enclosed balcony spaces. "
            "Skin sensitisation from isocyanates or epoxy components. "
            "Ignition of flammable membrane products. "
            "Slip on wet or uncured membrane."
        ),
        "pre": 6,
        "controls": (
            "ENV (High — C=3): Controls in place.\n"
            "Engineering: Forced ventilation in semi-enclosed balcony spaces. "
            "Continuous air monitoring if isocyanate-based product used.\n"
            "Admin: SDS reviewed for primer and membrane — confirm if isocyanate, "
            "epoxy, or solvent-based. "
            "Medical fitness confirmed for isocyanate exposure. "
            "Ignition sources eliminated before application. "
            "No walking on uncured membrane — barricade until cured.\n"
            "PPE: Supplied-air respirator or half-face with appropriate cartridge (per SDS), "
            "chemical-resistant gloves, coveralls, eye protection."
        ),
        "post": 2,
        "resp": "Alan Richardson",
        "audit": "STD-6-3-ENV",
        "hazard_summary": "Solvent vapour in enclosed balcony, isocyanate sensitisation, ignition risk, slip on uncured membrane.",
        "control_summary": "Forced ventilation; SDS controls; isocyanate fitness check; ignition eliminated; barricade until cured.",
    },

    # ── Task: Chemical Application — Solvents (ENV-1) — same as STD ──────────
    {
        "task": (
            "Chemical Application — Solvents and Cleaning Agents\n"
            "Use of mineral turpentine, primers, and cleaning agents during "
            "waterproofing preparation and application."
        ),
        "hazard": (
            "Solvent vapour inhalation. "
            "Skin and eye contact. "
            "Ignition of flammable vapours. "
            "Environmental contamination — spill to stormwater or drain."
        ),
        "pre": 4,
        "controls": (
            "ENV (Medium — C=2): Controls in place.\n"
            "Admin: SDS reviewed before use — controls confirmed. "
            "Ventilation confirmed adequate before application. "
            "Ignition sources eliminated before opening solvent-based products. "
            "Spill kit on site. No disposal to drain or stormwater.\n"
            "PPE: Respirator per SDS, chemical-resistant gloves, eye protection, coveralls.\n"
            "Remove from exposure and rectify if ventilation inadequate."
        ),
        "post": 1,
        "resp": "Alan Richardson",
        "audit": "STD-4-2-ENV",
        "hazard_summary": "Solvent vapour inhalation, skin contact, ignition risk, spill to stormwater.",
        "control_summary": "SDS reviewed; ventilation confirmed; ignition sources eliminated; spill kit on site.",
    },

    # ── Task: Public Interface — Residential (TRF-2) — same as STD ───────────
    {
        "task": (
            "Public Interface — Residential Premises\n"
            "Works on balconies of occupied residential building with public nearby."
        ),
        "hazard": (
            "Public or occupant entry into work zone. "
            "Dropped objects or debris reaching public areas. "
            "Noise, dust, or fume impact on occupants. "
            "Slips and trips — tools, leads, debris in public areas."
        ),
        "pre": 4,
        "controls": (
            "TRF (Medium — C=2): Controls in place.\n"
            "Engineering: Hoarding, barriers, or screens to fully separate public from work zone. "
            "Overhead catch protection where drop risk to public areas.\n"
            "Admin: Coordinate work hours with building manager. "
            "Noise, dust, and fume management — schedule high-impact work for agreed times. "
            "Work zone inspected and secured at end of each shift. "
            "Clear and maintain emergency egress at all times. "
            "Residents notified before commencement.\n"
            "PPE: Hi-vis, safety boots, appropriate dust/fume controls."
        ),
        "post": 1,
        "resp": "Alan Richardson",
        "audit": "STD-4-2-TRF",
        "hazard_summary": "Public or occupant entry into work zone — dropped objects — noise and dust impact.",
        "control_summary": "Hoarding or barriers to separate public; overhead catch protection; coordinate hours; secure site each shift.",
    },

]


# ══════════════════════════════════════════════════════════════════════════════
# ✏️  SECTION 3 — REQUIREMENTS CONTENT
# ══════════════════════════════════════════════════════════════════════════════

PPE_CONTENT = (
    "Hard hat AS/NZS 1801; "
    "Safety glasses or goggles; "
    "Chemical-resistant gloves; "
    "Steel cap safety boots AS/NZS 2210.3; "
    "Hi-vis vest; "
    "P2/P3 respirator (grinding and membrane application); "
    "Hearing protection (grinding); "
    "Coveralls (membrane application); "
    "Face shield (grinding); "
    "Non-slip footwear (ladder use)."
)

PERMITS_CONTENT = (
    "PC site induction — ALL workers on first day; "
    "SWMS sign-on — ALL workers before commencing work each day; "
    "Toolbox talk pre-commencement — conducted and recorded daily.\n"
    "GOVERNANCE (CCVS v16.0): Critical controls for high-risk work must be verified "
    "prior to commencement; verification recorded via documented or digital system."
)

QUALS_CONTENT = (
    "White Card (Construction Industry Induction) — ALL workers; "
    "First Aid Certificate HLTAID011 — minimum one worker on site at all times."
)

PLANT_CONTENT = (
    "Angle grinder (with HEPA vacuum extraction or wet suppression); "
    "Hand tools — scrapers, trowels, rollers, brushes."
)

SUBSTANCES_CONTENT = (
    "Waterproofing primer (confirm SDS on site before use); "
    "Waterproofing membrane — liquid applied (confirm SDS on site before use); "
    "Mineral turpentine (confirm SDS on site before use)."
)

LEGISLATION_APPEND = (
    ", WHS Regulation 2017 Part 6.3 r299 (SWMS)"
    ", AS/NZS 1891 (industrial fall protection)"
    ", SafeWork NSW Code of Practice: Managing the Risk of Falls at Workplaces"
)


# ══════════════════════════════════════════════════════════════════════════════
# RUNNER
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    TEMPLATE = os.path.join(os.path.dirname(__file__), "..", "docs", "SWMS_Template.docx")
    OUT_DIR  = os.path.dirname(os.path.abspath(__file__))
    OUT_STD  = os.path.join(OUT_DIR, PROJECT["output_standard"] + ".docx")
    OUT_CCVS = os.path.join(OUT_DIR, PROJECT["output_ccvs"]     + ".docx")

    kwargs = dict(
        project=PROJECT,
        ppe=PPE_CONTENT,
        permits=PERMITS_CONTENT,
        quals=QUALS_CONTENT,
        plant=PLANT_CONTENT,
        substances=SUBSTANCES_CONTENT,
        leg_append=LEGISLATION_APPEND,
    )

    print("=" * 60)
    print(f"  {PROJECT['title_prefix']}")
    print("=" * 60)

    generate_swms(TEMPLATE, OUT_STD,  TASKS_STANDARD, use_ccvs=False, **kwargs)
    generate_swms(TEMPLATE, OUT_CCVS, TASKS_CCVS,     use_ccvs=True,  **kwargs)

    print("\n" + "=" * 60)
    print("  Complete.")
    print("=" * 60)

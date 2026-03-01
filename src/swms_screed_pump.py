#!/usr/bin/env python3
"""
SWMS Generic Template — Concrete Screed Pump Operations
Sand/cement screed placement for tile beds using line pump
(e.g. Putzmeister M740, worm pump).

Non-structural screeds, typically 40mm+ thickness, 1:3 or 1:4 mix.
Line pump delivers 3-5 m3/hr, reaches 150m vertical / 200m horizontal.

Template: fill in [bracketed] fields before issuing.
Engine: SWMS_BASE_GENERAL.py v16.4
"""

import os
import sys

# Add src directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from SWMS_BASE_GENERAL import generate_swms


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — PROJECT
# ══════════════════════════════════════════════════════════════════════════════

PROJECT = {
    "pbcu_line": (
        "■ PBCU: Robertson's Remedial and Painting Pty Ltd "
        "10/56 Buffalo Road, Gladesville NSW 2111 "
        "Phone: (02) 9181 3519 | ABN: 16 140 746 247"
    ),
    "site":       "[Site Address]",
    "pc":         "[Principal Contractor]",
    "date":       "[DD/MM/YYYY]",
    "manager":    "Jim Georgiadis",
    "supervisor": "[Supervisor Name]",
    "reviewer":   "Alan Richardson",
    "activity": (
        "Concrete screed pump operations — sand/cement screed placement "
        "for tile beds using line pump (e.g. Putzmeister M740). "
        "Non-structural screeds, typically 40mm+ thickness."
    ),
    "emergency_contact": "000 / [Site Office Contact]",
    "assembly_point":    "[Assembly Point — briefed at induction]",

    # ── HRCW ──────────────────────────────────────────────────────────────────
    "hrcw": {
        "falling_2m":             False,
        "telecom_tower":          False,
        "demolition":             False,
        "disturb_asbestos":       False,
        "load_bearing":           False,
        "confined_space":         False,
        "shaft_trench":           False,
        "explosives":             False,
        "pressurised_gas":        True,   # Pump operates under high pressure
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

    # ── Output filenames ──────────────────────────────────────────────────────
    "output_standard": "SWMS_ScreedPump_Template_Standard",
    "output_ccvs":     "SWMS_ScreedPump_Template_CCVS",
    "title_prefix":    "SWMS — Concrete Screed Pump Operations — [Site]",
}


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — TASKS
#     SYS and EMR auto-injected. Do not add them here.
#     Task numbering applied by engine after SYS injection.
# ══════════════════════════════════════════════════════════════════════════════

TASKS = [

    # ── Task: Screed Pump Setup, Hose Connection and Pressure Testing ────
    # Code: ENE | Pre: 6 | C=3 | CCVS
    # High-pressure injection injury is potentially fatal — CCVS triggered
    {
        "task": (
            "Screed Pump Setup, Hose Connection and Pressure Testing\n"
            "Position line pump, connect delivery hoses, inspect all "
            "couplings and safety clips, pressure test before pumping."
        ),
        "hazard": (
            "High-pressure injection injury from pump line — sand/cement "
            "injected under skin causes tissue necrosis, compartment "
            "syndrome, potential amputation or death. "
            "Hose whip from coupling failure. "
            "Manual handling of pump components and delivery hoses. "
            "Electrical hazard from pump motor."
        ),
        "pre": 6,
        "controls": (
            "ENE (High — C=3) CCVS HOLD POINTS:\n"
            "Work must not commence until:\n"
            "1. Pump operator trained and competent in specific pump model "
            "— training records sighted.\n"
            "2. All delivery line couplings inspected, secured, and safety "
            "clips/pins confirmed — no worn or damaged fittings.\n"
            "3. Pressure test completed at rated working pressure before "
            "pumping screed — no leaks, no coupling movement.\n"
            "4. Exclusion zone established around pump and full length of "
            "delivery line — no personnel in hose whip zone during "
            "start-up and priming.\n"
            "Confirmation retained in site diary or digital system.\n"
            "Engineering: Hose clamps and couplings rated to pump maximum "
            "pressure — safety whip checks on all hose joints — delivery "
            "line secured and supported to prevent movement — RCD "
            "protection on electric pump.\n"
            "Admin: Pump manufacturer operating manual on site — daily "
            "pre-start inspection recorded — hose and coupling replacement "
            "schedule maintained — emergency shutdown procedure briefed "
            "to all workers.\n"
            "PPE: Steel-capped footwear, eye protection, hearing "
            "protection (>85 dB), cut-resistant gloves, hi-vis vest "
            "or shirt.\n"
            "STOP WORK if: Hose coupling leaking or damaged — pump "
            "pressure exceeds rated limit — delivery line unsecured or "
            "unsupported — blockage in line (do not attempt to clear "
            "under pressure) — electrical fault on pump motor."
        ),
        "post": 2,
        "resp": "Supervisor / Pump Operator",
        "audit": "CCVS-6-3-ENE",
        "hazard_summary": (
            "High-pressure injection injury — hose whip from coupling "
            "failure — manual handling of pump and hoses."
        ),
        "control_summary": (
            "Operator competency confirmed, couplings inspected and "
            "secured, pressure test before pumping, exclusion zone "
            "during start-up, emergency shutdown briefed."
        ),
    },

    # ── Task: Material Preparation and Mesh Placement ────────────────────
    # Code: ENV | Pre: 4 | C=2 | STD
    {
        "task": (
            "Material Preparation and Mesh Placement\n"
            "Handle and stage cement and sand bags, cut and lay "
            "galvanised steel mesh reinforcement to specification."
        ),
        "hazard": (
            "Manual handling of cement and sand bags (20-25 kg). "
            "Cement dust inhalation and alkaline skin/eye contact. "
            "Cut and puncture injuries from mesh handling and cutting. "
            "Slip and trip on materials and offcuts."
        ),
        "pre": 4,
        "controls": (
            "ENV (Medium — C=2): Controls in place.\n"
            "Engineering: Mechanical aids for repetitive bag handling "
            "where available — mesh cut with bolt cutters (not angle "
            "grinder) to reduce sparks and noise — material staged to "
            "minimise carry distances.\n"
            "Admin: SDS for cement reviewed — correct mix ratio confirmed "
            "(1:3 or 1:4 cement:sand per specification) — mesh "
            "specification and lap requirements confirmed before "
            "placement — rotate workers on manual handling tasks.\n"
            "PPE: P2 dust mask (dry cement handling), eye protection, "
            "chemical-resistant gloves (nitrile), steel-capped footwear, "
            "long sleeves."
        ),
        "post": 1,
        "resp": "Supervisor / Worker",
        "audit": "STD-4-2-ENV",
        "hazard_summary": (
            "Manual handling of bags — cement dust inhalation — cut "
            "injuries from mesh — slips on materials."
        ),
        "control_summary": (
            "Mechanical aids where available, bolt cutters for mesh, "
            "SDS reviewed, P2 dust mask and nitrile gloves."
        ),
    },

    # ── Task: Screed Pumping, Placement and Levelling ────────────────────
    # Code: ENV | Pre: 4 | C=2 | STD
    {
        "task": (
            "Screed Pumping, Placement and Levelling\n"
            "Pump sand/cement screed via delivery line, place to "
            "specified thickness, screed and level to falls."
        ),
        "hazard": (
            "Alkaline burns from wet cement screed (pH 12-13). "
            "Slip hazard on wet screed surface. "
            "Noise from pump operation. "
            "Manual handling strain from screeding and levelling. "
            "Hose movement and trip hazard."
        ),
        "pre": 4,
        "controls": (
            "ENV (Medium — C=2): Controls in place.\n"
            "Engineering: Delivery hose routed and secured to prevent "
            "trip hazard — non-slip walkways maintained around pour "
            "area — pump operator maintains visual contact with nozzle "
            "operator at all times.\n"
            "Admin: Pour sequence planned to avoid workers walking on "
            "fresh screed — nozzle operator and pump operator "
            "communicate via agreed signals (radio or hand) — skin "
            "contact with wet screed washed immediately with clean "
            "water — screed thickness confirmed against specification "
            "during placement.\n"
            "PPE: Waterproof boots, chemical-resistant gloves (nitrile), "
            "eye protection, hearing protection (>85 dB), hi-vis vest "
            "or shirt, long sleeves.\n"
            "STOP WORK if: Communication between pump and nozzle "
            "operator fails — screed mix consistency incorrect (too wet "
            "or too dry to pump) — hose unsecured or moved from "
            "supported position."
        ),
        "post": 1,
        "resp": "Supervisor / Pump Operator / Worker",
        "audit": "STD-4-2-ENV",
        "hazard_summary": (
            "Alkaline burns — slip on wet screed — noise — manual "
            "handling strain — hose trip hazard."
        ),
        "control_summary": (
            "Hose secured, non-slip walkways, pump-nozzle comms, "
            "pour sequence planned, waterproof boots and nitrile gloves."
        ),
    },

    # ── Task: Pump Cleanup, Washout and Demobilisation ───────────────────
    # Code: ENV | Pre: 4 | C=2 | STD
    {
        "task": (
            "Pump Cleanup, Washout and Demobilisation\n"
            "Flush delivery lines, contain washout water, disconnect "
            "hoses, clean and remove pump from site."
        ),
        "hazard": (
            "Alkaline washout water — environmental contamination if "
            "discharged to stormwater. "
            "High-pressure water during line flush. "
            "Manual handling during hose disconnection and pump removal. "
            "Slip on wet surfaces."
        ),
        "pre": 4,
        "controls": (
            "ENV (Medium — C=2): Controls in place.\n"
            "Engineering: Washout water contained in designated bund or "
            "container — no discharge to stormwater drains, gutters, or "
            "ground — pump depressurised before disconnecting any "
            "coupling.\n"
            "Admin: Washout location agreed before pumping commences — "
            "washout water pH tested if discharge to sewer required "
            "(council approval) — all hoses and couplings cleaned, "
            "inspected, and stored — site left clean and free of screed "
            "residue.\n"
            "PPE: Waterproof boots, chemical-resistant gloves (nitrile), "
            "eye protection, hi-vis vest or shirt.\n"
            "STOP WORK if: No containment available for washout water — "
            "pump not fully depressurised before disconnection."
        ),
        "post": 1,
        "resp": "Supervisor / Pump Operator",
        "audit": "STD-4-2-ENV",
        "hazard_summary": (
            "Alkaline washout to stormwater — high-pressure flush — "
            "manual handling during demobilisation."
        ),
        "control_summary": (
            "Washout contained in bund, no stormwater discharge, pump "
            "depressurised before disconnection, site left clean."
        ),
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — REQUIREMENTS
# ══════════════════════════════════════════════════════════════════════════════

PPE_CONTENT = (
    "Hard hat AS/NZS 1801; "
    "Hi-vis vest or shirt; "
    "Steel-capped footwear AS/NZS 2210.3; "
    "Waterproof boots (placement and washout); "
    "Eye protection; "
    "P2 dust mask (dry cement handling); "
    "Hearing protection >85 dB (pump operation); "
    "Chemical-resistant gloves (nitrile); "
    "Long sleeves (alkaline burn protection)."
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
    "First Aid Certificate HLTAID011 — minimum one worker on site at all times; "
    "Screed pump operator competency — manufacturer-specific training or "
    "demonstrated equivalent experience."
)

PLANT_CONTENT = (
    "Concrete screed pump (line pump, e.g. Putzmeister M740); "
    "Delivery hoses and couplings (rated to pump max pressure); "
    "Screeding rails and straightedge; "
    "Bolt cutters (mesh cutting); "
    "Wheelbarrow; "
    "Extension leads (tested and tagged AS/NZS 3760); "
    "RCD safety switches."
)

SUBSTANCES_CONTENT = (
    "Portland cement — SDS on site; "
    "Sharp sand (washed); "
    "Galvanised steel mesh reinforcement."
)

LEGISLATION_APPEND = (
    ", WHS Regulation 2017 Part 6.3 r299 (SWMS)"
    ", SafeWork NSW Code of Practice — Managing the Risks of Plant in the Workplace"
)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — RUNNER
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    TEMPLATE = os.path.join(SCRIPT_DIR, "..", "docs", "SWMS_Template.docx")
    OUT_DIR  = os.path.join(SCRIPT_DIR, "outputs")
    os.makedirs(OUT_DIR, exist_ok=True)

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

    print("Generating Standard output...")
    generate_swms(TEMPLATE, OUT_STD, TASKS, use_ccvs=False, **kwargs)
    print(f"  Saved: {OUT_STD}")

    print("Generating CCVS output...")
    generate_swms(TEMPLATE, OUT_CCVS, TASKS, use_ccvs=True, **kwargs)
    print(f"  Saved: {OUT_CCVS}")

    print("\nDone. Run bulletizer and PPE validator on both outputs.")

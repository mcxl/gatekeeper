#!/usr/bin/env python3
"""
SWMS Job Instance — 22 Smith Street Surry Hills NSW 2010
Concrete Spalling Repairs and Epoxy Crack Injection
PC: Mirvac | Access: EWP Only | Pre-2003 Building — Lead Paint Assumed

Generated: 27/02/2026
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
    "site":       "22 Smith Street, Surry Hills NSW 2010",
    "pc":         "Mirvac",
    "date":       "27/02/2026",
    "manager":    "Alan Richardson",
    "supervisor": "Alan Richardson",
    "reviewer":   "Alan Richardson",
    "activity": (
        "Concrete spalling repairs and epoxy crack injection to exterior "
        "façade elements. EWP (boom lift) access. Pre-2003 building — "
        "lead paint assumed present. Surry Hills urban location — "
        "public and pedestrian interface managed."
    ),
    "emergency_contact": "000 / Mirvac Site Office",
    "assembly_point":    "Footpath assembly area — Smith Street frontage (briefed at induction)",

    # ── HRCW ──────────────────────────────────────────────────────────────────
    "hrcw": {
        "falling_2m":             True,   # EWP work above 2m
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
        "powered_mobile_plant":   True,   # EWP is powered mobile plant
        "artificial_temperature": False,
        "water_drowning":         False,
        "diving":                 False,
    },

    # ── Output filenames ──────────────────────────────────────────────────────
    "output_standard": "SWMS_22Smith_SpallingRepair_27022026_Standard",
    "output_ccvs":     "SWMS_22Smith_SpallingRepair_27022026_CCVS",
    "title_prefix":    "SWMS — Concrete Spalling Repairs & Epoxy Injection — 22 Smith St Surry Hills",
}


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — TASKS
#     SYS and EMR auto-injected. Do not add them here.
#     Task numbering applied by engine after SYS injection.
# ══════════════════════════════════════════════════════════════════════════════

TASKS = [

    # ── Task: Site Setup and Public Protection ─────────────────────────────
    # Code: TRF | Pre: 4 | C=2 | STD
    # Surry Hills is dense urban — public/pedestrian interface
    {
        "task": (
            "Site Setup and Public Protection\n"
            "Establish exclusion zones, barricades, and overhead protection. "
            "Surry Hills urban location — pedestrian and public interface."
        ),
        "hazard": (
            "Worker or pedestrian struck by vehicle. "
            "Public entry into work zone. "
            "Dropped objects or debris falling to footpath. "
            "Slips and trips during setup."
        ),
        "pre": 4,
        "controls": (
            "TRF (Medium — C=2): Controls in place.\n"
            "Engineering: Barricade and signage — controlled work area. "
            "Pedestrian diversion around exclusion zone. "
            "Overhead protection (catch scaffold or debris netting) where work is "
            "above footpath or public area — no unprotected drop zone.\n"
            "Admin: Traffic management plan (TPMP) implemented per Mirvac requirements. "
            "Schedule deliveries off-peak. "
            "Coordinate with Mirvac site office for pedestrian management. "
            "HOLD POINT: If exclusion zone cannot be maintained without encroaching "
            "on footpath or roadway — STOP and implement approved TPMP before continuing.\n"
            "PPE: Hi-vis vest or shirt, steel-capped footwear, hard hat."
        ),
        "post": 1,
        "resp": "Supervisor",
        "audit": "STD-4-2-TRF",
        "hazard_summary": "Pedestrian or worker struck by vehicle — public entering work zone — dropped objects to footpath.",
        "control_summary": "Barricade, signage, overhead protection, TPMP per Mirvac, pedestrian diversion, HOLD POINT if zone compromised.",
    },

    # ── Task: EWP Operation — Boom Lift ────────────────────────────────────
    # Code: WAH | Pre: 6 | C=3 | CCVS (pre ≥ 6, C=3, WAH in critical list)
    {
        "task": (
            "EWP Operation — Boom Lift\n"
            "Boom lift EWP for access to exterior façade — concrete spalling "
            "repairs and crack injection. All height work via EWP only."
        ),
        "hazard": (
            "Fall from basket (>2m). "
            "Tip-over or instability on uneven or soft ground. "
            "Entrapment or crush against building façade or overhead structure. "
            "Dropped objects to ground level. "
            "Collision with pedestrians or plant."
        ),
        "pre": 6,
        "controls": (
            "WAH (High — C=3) CCVS HOLD POINTS:\n"
            "Work must not commence until:\n"
            "1. Daily pre-start inspection completed — defects nil — recorded.\n"
            "2. Ground confirmed firm and level on hardstand — outriggers fully deployed.\n"
            "3. Competent operator — WP licence sighted and confirmed.\n"
            "4. Overhead clearances and façade setbacks measured and confirmed safe.\n"
            "5. Harness inspected — lanyard clipped to manufacturer anchor point.\n"
            "6. Exclusion zone established — spotter confirmed on station.\n"
            "Confirmation retained in site diary or digital system.\n"
            "Engineering: Daily pre-start inspection completed and recorded. "
            "Ground firm and level — hardstand only. "
            "Outriggers and stabilisers deployed per manufacturer.\n"
            "Admin: Competent operator — WP licence sighted. "
            "Spotter mandatory when manoeuvring near building façade. "
            "Exclusion zone around EWP — barricaded from public access. "
            "Tools and materials secured in basket — no loose items on platform edge.\n"
            "PPE: Harness clipped to manufacturer anchor, hard hat, hi-vis vest or shirt, "
            "steel-capped footwear.\n"
            "Remove from exposure and rectify if ground unstable or fault detected."
        ),
        "post": 2,
        "resp": "Supervisor / Operator",
        "audit": "CCVS-6-3-WAH",
        "hazard_summary": "Fall from basket, tip-over, entrapment against façade — dropped objects to public below.",
        "control_summary": "CCVS HOLD POINTS Pre-start check, firm ground, WP licence, spotter, harness clipped, exclusion zone confirmed.",
    },

    # ── Task: Lead Paint — Testing and Controls ────────────────────────────
    # Code: LED | Pre: 6 | C=3 | CCVS (pre ≥ 6, C=3, LED in critical list)
    # Pre-2003 building — lead assumed until tested
    {
        "task": (
            "Lead Paint — Testing and Controls\n"
            "Pre-2003 building — lead paint assumed present on all painted surfaces. "
            "Lead-safe work practices for all surface disturbance activities."
        ),
        "hazard": (
            "Lead dust inhalation — lead poisoning, neurological damage. "
            "Lead ingestion — hand-to-mouth contamination. "
            "Lead contamination of work area, clothing, and public areas below. "
            "Environmental contamination — lead dust or debris to stormwater."
        ),
        "pre": 6,
        "controls": (
            "LED (High — C=3) CCVS HOLD POINTS:\n"
            "Work must not commence until:\n"
            "1. Lead testing completed (XRF or lab) OR lead-safe controls applied "
            "as default for all surface disturbance on this pre-2003 building.\n"
            "2. Containment sheeting installed to prevent lead dust spread to "
            "public areas and stormwater.\n"
            "3. P2 respirators (minimum) confirmed fit-tested and available for all workers.\n"
            "4. HEPA vacuum confirmed on site and operational.\n"
            "5. Decontamination procedure briefed — coveralls removed before leaving "
            "work area, hands and face washed before eating or drinking.\n"
            "6. Lead waste disposal method confirmed — labelled containers on site.\n"
            "Confirmation retained in site diary or digital system.\n"
            "Engineering: Wet methods only — no dry sanding, scraping, or grinding "
            "of painted surfaces. HEPA vacuum for all dust collection. "
            "Containment sheeting below all work areas.\n"
            "Admin: Test for lead before work or assume present (pre-2003 default). "
            "Decontamination mandatory — coveralls removed in work zone, "
            "wash hands and face before eating or drinking. "
            "Lead waste labelled and disposed per EPA guidelines. "
            "Air monitoring if extensive disturbance.\n"
            "PPE: P2 respirator (minimum), disposable coveralls, cut-resistant gloves, "
            "eye protection. P3 for extensive removal or elevated concentrations.\n"
            "Remove from exposure and rectify if dust controls fail."
        ),
        "post": 2,
        "resp": "Supervisor",
        "audit": "CCVS-6-3-LED",
        "hazard_summary": "Lead dust inhalation and ingestion — pre-2003 building, lead paint assumed on all surfaces.",
        "control_summary": "CCVS HOLD POINTS Lead test or assume present, wet methods only, HEPA vac, containment sheeting, P2 minimum, decontamination enforced.",
    },

    # ── Task: Concrete Breakout and Surface Preparation ────────────────────
    # Code: SIL | Pre: 6 | C=3 | CCVS (pre ≥ 6, C=3, SIL in critical list)
    # Breaking out delaminated concrete, grinding to sound substrate
    {
        "task": (
            "Concrete Breakout and Surface Preparation\n"
            "Remove delaminated and spalled concrete back to sound substrate. "
            "Grind edges and prepare surface for repair mortar application."
        ),
        "hazard": (
            "Silica dust inhalation — silicosis, lung cancer. "
            "Lead dust from painted surfaces (see LED controls). "
            "Flying debris and concrete fragments. "
            "Noise and vibration — HAVS from extended grinding. "
            "Dropped debris to ground level. "
            "Striking concealed reinforcement or services."
        ),
        "pre": 6,
        "controls": (
            "SIL (High — C=3) CCVS HOLD POINTS:\n"
            "Work must not commence until:\n"
            "1. On-tool HEPA extraction or wet suppression confirmed fitted and operational "
            "on all grinders and breakers.\n"
            "2. P2/P3 respirators confirmed fit-tested and available.\n"
            "3. Exclusion zone established below work area — debris catch "
            "or overhead protection in place.\n"
            "4. Lead-safe controls confirmed active (see LED task) — wet methods "
            "for all surface disturbance on painted substrates.\n"
            "5. Services scan completed — confirm no live services in breakout zone.\n"
            "Confirmation retained in site diary or digital system.\n"
            "Engineering: On-tool HEPA extraction or wet suppression on all grinders "
            "and breakers. Blade guard fitted and intact. "
            "Debris catch below EWP to prevent fallout to public.\n"
            "Admin: P2 or P3 respirator — fit-tested. "
            "Eye and face protection mandatory. Hearing protection (>85 dB). "
            "Exclusion zone around work area for debris. "
            "Inspect grinding wheels before fitting — no cracks or damage. "
            "Vibration rotation — limit individual exposure, maintain tooling.\n"
            "PPE: P2/P3 respirator, face shield, hearing protection, "
            "cut-resistant gloves, steel-capped footwear.\n"
            "Remove from exposure and rectify if dust controls fail."
        ),
        "post": 2,
        "resp": "Supervisor",
        "audit": "CCVS-6-3-SIL",
        "hazard_summary": "Silica dust from concrete breakout — lead dust from painted surfaces — flying debris — vibration.",
        "control_summary": "CCVS HOLD POINTS On-tool extraction or wet suppression, P2/P3 RPE, lead-safe controls active, exclusion zone, services scan.",
    },

    # ── Task: Concrete Spalling Repair — Structural ────────────────────────
    # Code: STR | Pre: 6 | C=3 | CCVS (pre ≥ 6, C=3, STR in critical list)
    # Repair of structural concrete elements — rebar treatment and mortar
    {
        "task": (
            "Concrete Spalling Repair — Structural\n"
            "Treat exposed reinforcement, apply bonding agent and repair mortar "
            "to restore structural concrete profile. Engineering assessment required."
        ),
        "hazard": (
            "Structural deterioration beyond assessed extent — hidden corrosion. "
            "Further delamination during repair — uncontrolled concrete fall. "
            "Chemical exposure from repair mortar, bonding agents, and rust inhibitor. "
            "Manual handling of repair materials at height in EWP basket."
        ),
        "pre": 6,
        "controls": (
            "STR (High — C=3) CCVS HOLD POINTS:\n"
            "Work must not commence until:\n"
            "1. Structural engineer assessment completed — repair specification "
            "and extent of breakout confirmed in writing.\n"
            "2. Repair method statement reviewed and approved by Mirvac.\n"
            "3. Repair materials confirmed on site and matching specification "
            "(bonding agent, rust inhibitor, repair mortar).\n"
            "4. Exclusion zone confirmed below all repair areas.\n"
            "Confirmation retained in site diary or digital system.\n"
            "Engineering: Structural engineer to assess and specify repair extent — "
            "written confirmation on file before commencing. "
            "Repair materials per engineer specification — no substitution.\n"
            "Admin: Clean exposed rebar to bright metal — wire brush or needle gun. "
            "Apply rust inhibitor per manufacturer instructions. "
            "Apply bonding agent to prepared surface before mortar. "
            "Repair mortar applied in lifts per specification — do not overload. "
            "SDS reviewed for all repair products. "
            "If deterioration exceeds assessed extent — STOP WORK: notify engineer "
            "and Mirvac before continuing.\n"
            "PPE: Eye protection, chemical-resistant gloves, P2 respirator "
            "(dust from wire brushing), steel-capped footwear.\n"
            "STOP WORK: Any unassessed structural deterioration, excessive rebar "
            "corrosion, or cracking beyond repair scope — stop and notify engineer."
        ),
        "post": 2,
        "resp": "Supervisor",
        "audit": "CCVS-6-3-STR",
        "hazard_summary": "Hidden structural deterioration — uncontrolled concrete fall — chemical exposure from repair products.",
        "control_summary": "CCVS HOLD POINTS Engineer assessment and written specification, Mirvac-approved method, materials per spec, STOP WORK if extent exceeded.",
    },

    # ── Task: Epoxy Crack Injection ────────────────────────────────────────
    # Code: ENV | Pre: 4 | C=2 | STD
    # Epoxy resin injection into concrete cracks
    {
        "task": (
            "Epoxy Crack Injection\n"
            "Identify and mark cracks, install injection ports, seal crack face, "
            "inject epoxy resin under low pressure, remove ports and finish."
        ),
        "hazard": (
            "Skin sensitisation from epoxy resin — allergic dermatitis. "
            "Eye contact with epoxy hardener — chemical burns. "
            "Solvent vapour inhalation from injection products. "
            "Injection equipment under pressure — hose failure. "
            "Manual handling of injection equipment at height."
        ),
        "pre": 4,
        "controls": (
            "ENV (Medium — C=2): Controls in place.\n"
            "Engineering: Injection equipment maintained per manufacturer — "
            "pressure relief valve functional. Hose connections checked before use.\n"
            "Admin: SDS reviewed for epoxy resin and hardener before use — "
            "controls confirmed and SDS on site. "
            "Ventilation confirmed adequate — outdoor work via EWP. "
            "No ignition sources near solvent-based products. "
            "Drill injection ports using dust-controlled method (see SIL task). "
            "Spill kit on site — epoxy drips contained by drop sheet below.\n"
            "PPE: Chemical-resistant gloves (nitrile minimum), eye protection "
            "(safety glasses or goggles), P2 respirator if in semi-enclosed area, "
            "disposable coveralls recommended.\n"
            "Remove from exposure and rectify if ventilation inadequate. "
            "First aid: skin contact — wash immediately with soap and water. "
            "Eye contact — flush 15 minutes, seek medical attention."
        ),
        "post": 1,
        "resp": "Supervisor",
        "audit": "STD-4-2-ENV",
        "hazard_summary": "Epoxy skin sensitisation — chemical burns from hardener — solvent vapour — injection pressure.",
        "control_summary": "SDS on site, chemical-resistant gloves, eye protection, equipment maintained, spill kit, first aid for contact.",
    },

    # ── Task: Portable Electrical Tools and Leads ──────────────────────────
    # Code: ELE | Pre: 4 | C=2 | STD
    {
        "task": (
            "Portable Electrical Tools and Extension Leads\n"
            "Use of 240V grinders, drills, needle guns, and extension leads on site."
        ),
        "hazard": (
            "Electric shock from damaged tools or leads. "
            "RCD failure — unprotected circuit. "
            "Leads in wet conditions from pressure washing or wet grinding. "
            "Overloaded circuits — fire risk."
        ),
        "pre": 4,
        "controls": (
            "ELE (Medium — C=2): Controls in place.\n"
            "Engineering: All 240V tools and leads protected by RCD — tested before use. "
            "Use battery tools where practicable.\n"
            "Admin: All tools and leads tested and tagged AS/NZS 3760 — "
            "construction site minimum 3-monthly. "
            "Visual inspection pre-use — no damaged plugs, cords, or housings. "
            "No daisy-chaining extension leads. Keep leads off ground where possible. "
            "Isolate before clearing jams or changing attachments. "
            "Keep electrical equipment away from water — use battery tools in wet areas.\n"
            "PPE: Steel-capped footwear."
        ),
        "post": 1,
        "resp": "Supervisor",
        "audit": "STD-4-2-ELE",
        "hazard_summary": "Electric shock from damaged tools — RCD failure — leads in wet conditions.",
        "control_summary": "RCD on all 240V, tested and tagged AS/NZS 3760, battery tools where practicable, visual inspection pre-use.",
    },

]


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — REQUIREMENTS CONTENT
# ══════════════════════════════════════════════════════════════════════════════

PPE_CONTENT = (
    "Hard hat AS/NZS 1801; "
    "Hi-vis vest or shirt; "
    "Steel-capped footwear AS/NZS 2210.3; "
    "Eye protection (safety glasses or goggles); "
    "P2/P3 respirator (concrete grinding, lead paint disturbance); "
    "Hearing protection >85 dB (grinding, breaking); "
    "Cut-resistant gloves (general); "
    "Chemical-resistant gloves (epoxy, coatings); "
    "Disposable coveralls (lead paint work); "
    "Full body harness and lanyard (EWP — clipped to manufacturer anchor)."
)

PERMITS_CONTENT = (
    "PC site induction (Mirvac) — ALL workers on first day; "
    "SWMS sign-on — ALL workers before commencing work each day; "
    "Toolbox talk pre-commencement — conducted and recorded daily; "
    "EWP permit or logbook — daily pre-start recorded; "
    "Lead-safe work notification — SafeWork NSW if required.\n"
    "GOVERNANCE (CCVS v16.0): Critical controls for high-risk work must be verified "
    "prior to commencement; verification recorded via documented or digital system."
)

QUALS_CONTENT = (
    "White Card (Construction Industry Induction) — ALL workers; "
    "First Aid Certificate HLTAID011 — minimum one worker on site at all times; "
    "EWP licence (WP class) — all EWP operators; "
    "Lead-safe work training — all workers disturbing painted surfaces."
)

PLANT_CONTENT = (
    "Boom lift EWP (WP licence required); "
    "Angle grinders (dust extraction fitted); "
    "Needle gun / wire brush (rebar preparation); "
    "Hammer drill / rotary hammer; "
    "Epoxy crack injection pump and fittings; "
    "HEPA vacuum; "
    "Extension leads (tested and tagged AS/NZS 3760); "
    "RCD safety switches."
)

SUBSTANCES_CONTENT = (
    "Epoxy crack injection resin and hardener — SDS on site; "
    "Structural repair mortar — SDS on site; "
    "Bonding agent / primer — SDS on site; "
    "Rust inhibitor (rebar treatment) — SDS on site; "
    "Lead paint dust — assume present (pre-2003 building); "
    "Silica dust — concrete grinding and breakout."
)

LEGISLATION_APPEND = (
    ", WHS Regulation 2017 Part 6.3 r299 (SWMS)"
    ", SafeWork NSW Code of Practice — Managing Risks of Falls in Workplaces"
    ", SafeWork NSW Code of Practice — Managing the Risk of Lead in the Workplace"
    ", AS/NZS 4836 Safe Working on or Near Low-Voltage Electrical Installations"
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

    print("=" * 60)
    print(f"  {PROJECT['title_prefix']}")
    print("=" * 60)

    generate_swms(TEMPLATE, OUT_STD,  TASKS, use_ccvs=False, **kwargs)
    generate_swms(TEMPLATE, OUT_CCVS, TASKS, use_ccvs=True,  **kwargs)

    print("\n" + "=" * 60)
    print("  Complete.")
    print("=" * 60)

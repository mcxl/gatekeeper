#!/usr/bin/env python3
"""
core/inference_matrix.py
Maps work type keywords to mandatory WHS requirements.

Sources:
  - WHS Regulation 2017 (NSW) Schedule 3 — High Risk Construction Work
  - SafeWork NSW High Risk Work Licence classes
  - SafeWork NSW Codes of Practice
  - WHS Act 2011 (NSW) s.20 PCBU duties

Usage:
    from core.inference_matrix import infer_requirements
    result = infer_requirements("lead paint encapsulation ground floor")
    # result.hrcw_category, result.ppe, result.certs, result.permits, result.licenses
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import re

MODEL = 'claude-sonnet-4-6'

# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Requirements:
    hrcw: bool = False
    hrcw_category: Optional[str] = None          # WHS Reg 2017 Sch 3 ref
    hrcw_license_class: Optional[str] = None     # SafeWork NSW HRW class
    ppe: list[str] = field(default_factory=list)
    certs: list[str] = field(default_factory=list)
    permits: list[str] = field(default_factory=list)
    qualifications: list[str] = field(default_factory=list)
    notifications: list[str] = field(default_factory=list)
    safework_notification: bool = False
    epa_license: bool = False
    notes: list[str] = field(default_factory=list)
    plant: list[str] = field(default_factory=list)
    hrcw_flags: dict = field(default_factory=dict)

# ── Baseline PPE (all construction work) ─────────────────────────────────────

BASELINE_PPE = [
    "Safety glasses or goggles",
    "High-visibility vest or shirt",
    "Steel-capped safety boots",
    "Hard hat where overhead risk present",
]

BASELINE_CERTS = [
    "White Card (CPCCWHS1001) — general construction induction",
]

# ── Master inference matrix ───────────────────────────────────────────────────
# Each entry: keyword triggers (any match), requirements

MATRIX = [

    # ── LEAD PAINT ─────────────────────────────────────────────────────────
    {
        "keywords": ["lead paint", "lead-based paint", "lead encapsulat", "lead coat",
                     "lead seal", "lead strip", "lead removal", "lead abatement"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "P2 half-face respirator — fit-tested before first use",
            "Disposable Tyvek coveralls — taped at wrists and ankles",
            "Nitrile gloves — double glove when handling waste",
            "Safety glasses — full seal where dust risk present",
            "Decon station at zone exit — boots and coveralls removed there",
        ],
        "certs": [
            "Lead Assessor Class A (NSW EPA) — site assessment before work starts",
            "Lead-Safe Work Practices training (AS 4361.2)",
        ],
        "permits": [],
        "qualifications": [
            "Supervisor — Lead-Safe Work Practices competency",
        ],
        "notifications": [
            "NSW EPA — lead paint removal notification where >10m² disturbed",
        ],
        "safework_notification": False,
        "epa_license": True,
        "notes": [
            "WHS Reg 2017 s.420 — lead risk assessment required before work",
            "AS 4361.2 — Guide to lead paint management in residential buildings",
            "Exclusion zone mandatory — 3m minimum around work area",
        ],
    },

    # ── ASBESTOS ────────────────────────────────────────────────────────────
    {
        "keywords": ["asbestos", "asb removal", "asb abatement", "fibro", "super six",
                     "asbestos cement", "ace sheet", "asbest"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.18 — Asbestos removal work",
        "hrcw_license_class": "Asbestos Removal Licence — Class A (friable) or Class B (non-friable)",
        "ppe": [
            "P2 half-face respirator — fit-tested before each shift",
            "Disposable Tyvek coveralls — taped at wrists and ankles",
            "Nitrile gloves — double layer when handling friable material",
            "Safety glasses — full seal",
            "Decon unit mandatory at zone exit",
        ],
        "certs": [
            "Asbestos Removal Licence — Class A or B (SafeWork NSW)",
            "CPCCDE3002 — Remove non-friable asbestos (Class B minimum)",
            "CPCCDE3014 — Remove friable asbestos (Class A)",
            "Asbestos Assessor accreditation — Class A air monitoring",
        ],
        "permits": [
            "Asbestos removal permit — required before any licensed removal",
        ],
        "qualifications": [
            "Licensed supervisor on site at all times during removal",
            "Asbestos Assessor — clearance inspection before re-occupation",
        ],
        "notifications": [
            "SafeWork NSW — 5 business days notice before Class A removal",
            "SafeWork NSW — 1 business day notice before Class B removal >10m²",
        ],
        "safework_notification": True,
        "epa_license": True,
        "notes": [
            "WHS Reg 2017 Part 8.3 — asbestos removal duties",
            "SafeWork NSW Code of Practice: How to Safely Remove Asbestos",
            "Air monitoring required during all Class A removal",
            "Clearance certificate required before re-occupation",
        ],
    },

    # ── DEMOLITION ──────────────────────────────────────────────────────────
    {
        "keywords": ["demolition", "demolish", "strip out", "structural removal",
                     "building removal", "wall removal", "slab removal"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.10 — Demolition of load-bearing structure",
        "hrcw_license_class": "Demolition Licence — Class B (up to 15m) or Class C (unrestricted)",
        "ppe": [
            "P2 dust respirator — mandatory during demolition dust generation",
            "Impact-resistant safety glasses or goggles",
            "Cut-resistant gloves — Level D minimum",
            "Steel-capped boots — crush-resistant",
            "Hard hat — mandatory on demolition sites",
        ],
        "certs": [
            "Demolition Licence — Class B or C (SafeWork NSW)",
            "CPCCDE3016 — Demolition (restricted)",
            "Asbestos Removal Licence — if ACM identified in pre-demolition survey",
        ],
        "permits": [
            "Council development consent — where required",
            "SafeWork NSW demolition notification — structures over 6m",
            "Pre-demolition hazardous materials survey — by licensed assessor, completed and reviewed before any work",
            "Utility isolation certificates — electricity, gas, water, and telecommunications confirmed disconnected before demolition",
            "Council development consent — for demolition affecting the public realm or Class 1/10 buildings",
        ],
        "qualifications": [
            "Licensed demolition supervisor — on site at all times",
            "Structural engineer sign-off — pre-demolition engineering assessment",
            "Structural monitoring — where adjacent structures at risk, engineer-specified monitoring regime in place before demolition",
            "Falling object exclusion zone — established and maintained for full height of demolition face plus 5m",
            "Demolition sequence — engineer-approved order of operations; no deviation without engineer sign-off",
        ],
        "notifications": [
            "SafeWork NSW — 5 business days notice for structures over 6m",
            "Utility services disconnection confirmation before start",
        ],
        "safework_notification": True,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 s.292 — demolition SWMS required before work",
            "Pre-demolition hazardous materials survey mandatory",
            "Structural engineer — signed shoring plan required",
            "WHS Reg 2017 r.291-297 — structural alterations and temporary support obligations",
            "SafeWork NSW Code of Practice: Demolition Work",
            "Pre-demolition survey — must identify ACM, lead paint, PCB, synthetic mineral fibre, and structural hazards",
            "Robotic demolition — where space confined or structural collapse risk elevated; operator remains outside exclusion zone",
            "Progressive demolition — top-down sequence unless engineer specifies otherwise",
            "Overhead powerlines — request de-energisation before demolition plant operates within exclusion zone",
            "Dust suppression — water suppression mandatory during demolition; not optional for urban sites",
            "Waste management — hazardous demolition waste (ACM, lead, PCB) must be segregated and disposed per EPA license requirements",
        ],
    },

    # ── EXCAVATION ──────────────────────────────────────────────────────────
    {
        "keywords": ["excavat", "trench", "dig", "earthwork", "ground penetrat",
                     "soil removal", "cut and fill", "bore", "boring"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.12 — Excavation deeper than 1.5m",
        "hrcw_license_class": None,
        "ppe": [
            "Hard hat — mandatory in excavation zones",
            "High-visibility vest",
            "Safety boots — steel-capped and ankle support",
            "P2 dust respirator — where dust generation occurs",
        ],
        "certs": [
            "Dial Before You Dig (1100) — mandatory before any excavation",
            "Excavator operator — relevant HRW plant licence",
        ],
        "permits": [
            "Dial Before You Dig clearance — services identification",
            "Council permit — where excavation affects public land or footpath",
            "Excavation permit — for any excavation >300mm deep near known services",
            "Dewatering approval — where groundwater expected; EPA trade waste permit may be required for dewatering discharge",
        ],
        "qualifications": [
            "Competent person — shoring and battering assessment for >1.5m depth",
            "Traffic management plan — where excavation affects traffic",
            "Zone of Influence — for excavations >1.5m, zone of influence extends: 1:1 for clay soils, 1:2 for sand/gravel; all structures, footings, and services within this zone require engineer assessment",
            "Batter angle — maximum safe batter per soil type: clay 1V:1H, loose sand 1V:2H, rock face per geotechnical assessment",
            "Competent person inspection — trench/excavation inspected before workers enter, after rain, and at start of each shift",
        ],
        "notifications": [
            "Utility authorities — notification 2 business days before ground break",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 s.306 — excavation deeper than 1.5m triggers HRCW",
            "SafeWork NSW Code of Practice: Excavation Work",
            "Shoring or battering required — competent person sign-off",
            "WHS Reg 2017 r.306-309 — excavation work obligations; >1.5m depth triggers HRCW",
            "SafeWork NSW Code of Practice: Excavation Work",
            "Benching prohibited — no personnel in unsupported excavation >1.5m without shoring or adequate batter",
            "Adjacent structure monitoring — where excavation within Zone of Influence; survey pins installed before excavation, monitored daily",
            "Dewatering — pump discharge must not cause erosion, sedimentation, or discharge to stormwater without approval",
            "Backfill — compaction testing per AS 3798 required for excavations under or adjacent to structures",
        ],
    },

    # ── SWING STAGE / SUSPENDED SCAFFOLD ────────────────────────────────────
    {
        "keywords": ["swing stage", "suspended scaffold", "suspended platform",
                     "boatswain chair", "bosun chair", "rope access", "rappel"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.5 — Work on suspended scaffold",
        "hrcw_license_class": "Scaffolding Licence — Basic (SB), Intermediate (SI), or Advanced (SA)",
        "ppe": [
            "Full-body harness — AS/NZS 1891.1 compliant",
            "Energy-absorbing lanyard — double lanyard where continuous attachment required",
            "Helmet with chin strap — AS/NZS 1801",
            "Non-slip footwear — safety boots",
            "Gloves — cut-resistant minimum",
        ],
        "certs": [
            "Scaffolding Licence — Advanced class (SA) for swing stage erection",
            "Dogman Licence — where crane-lifted platform involved",
            "Working at heights — verified current competency (RIIOHS204E or equivalent per current RII Training Package)",
        ],
        "permits": [
            "Swing stage erection permit — signed by licenced scaffolder",
            "Load test certification — before first use and after relocation",
        ],
        "qualifications": [
            "Rescue plan — swing stage rescue procedure documented and practiced",
            "Competent person — daily pre-use inspection before each shift",
            "Structural engineer — tie-back anchor point certification",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 Part 4.4 — fall prevention hierarchy applies to all fall risk",
            "SafeWork NSW Code of Practice: Managing the Risk of Falls at Workplaces",
            "Rescue plan — documented, communicated to all workers before first use",
            "Anchor points — engineered certification required, not just visual inspection",
        ],
    },

    # ── SCAFFOLDING ──────────────────────────────────────────────────────────
    {
        "keywords": ["scaffold", "scaffolding", "tube and coupler", "system scaffold",
                     "modular scaffold", "kwikstage", "cuplock"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.6 — Work on scaffold over 4m",
        "hrcw_license_class": "Scaffolding Licence — Basic (SB), Intermediate (SI), or Advanced (SA)",
        "ppe": [
            "Full-body harness — when erecting or dismantling above 4m",
            "Hard hat — mandatory on scaffold",
            "Non-slip safety boots",
            "High-visibility vest",
        ],
        "certs": [
            "Scaffolding Licence — class appropriate to scaffold type and height",
            "Working at heights — verified current competency (RIIOHS204E or equivalent per current RII Training Package)",
        ],
        "permits": [
            "Scaffold erection permit — signed by licenced scaffolder before use",
            "Handover certificate — before any worker uses completed scaffold",
        ],
        "qualifications": [
            "Competent person — weekly inspection and after adverse weather",
            "Structural engineer — where scaffold exceeds 15m or non-standard loading",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 Part 4.4 — fall prevention hierarchy applies to all fall risk",
            "Scaffold handover certificate — mandatory before any use",
            "Load calculations — mandatory for heavy-duty or non-standard scaffold",
        ],
    },

    # ── HOT WORK ─────────────────────────────────────────────────────────────
    {
        "keywords": ["welding", "cutting", "grinding", "hot work", "oxy", "acetylene",
                     "plasma cut", "angle grinder", "disc cutter", "brazing", "soldering"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Welding helmet or face shield — AS/NZS 1337.1",
            "Leather welding gloves",
            "Flame-resistant clothing — no synthetic fabrics",
            "Safety boots — steel-capped",
            "P2 fume respirator — where ventilation inadequate",
        ],
        "certs": [
            "Hot Work Permit — issued by site supervisor before each job",
            "Welding qualification — relevant if structural welding",
        ],
        "permits": [
            "Hot Work Permit — mandatory before welding or cutting in any building",
            "Fire watch — 30 minutes minimum after hot work ceases",
        ],
        "qualifications": [
            "Fire warden designation — person assigned before work starts",
            "Fire extinguisher — 9L water or 9kg CO2 within 3m of work",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "SafeWork NSW — Hot Work Code of Practice",
            "Fire watch mandatory — 30 minutes minimum after work stops",
            "Flammable materials — remove or shield within 5m of hot work",
        ],
    },

    # ── CONFINED SPACE ───────────────────────────────────────────────────────
    {
        "keywords": ["confined space", "manhole", "pit", "tank entry", "sewer entry",
                     "void entry", "tunnel", "cistern"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.15 — Work in confined space",
        "hrcw_license_class": None,
        "ppe": [
            "Self-contained breathing apparatus (SCBA) — where atmosphere unknown",
            "Full-body harness — for retrieval",
            "Hard hat",
            "Non-sparking tools — where flammable atmosphere possible",
        ],
        "certs": [
            "Confined Space Entry training — MSMWHS217 or equivalent",
            "Atmospheric testing competency — gas detector calibration",
        ],
        "permits": [
            "Confined Space Entry Permit — mandatory before every entry",
            "Isolation permit — lock-out tag-out before entry",
        ],
        "qualifications": [
            "Standby person — trained in rescue, stationed at entry point at all times",
            "Rescue plan — documented and rehearsed before first entry",
            "Emergency services — notified of confined space entry and location",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 Part 4.3 — confined space duties",
            "SafeWork NSW Code of Practice: Confined Spaces",
            "Atmosphere — test for O2, CO, H2S, LEL before every entry",
            "Rescue plan — must be documented before permit is issued",
        ],
    },

    # ── ELECTRICAL ───────────────────────────────────────────────────────────
    {
        "keywords": ["electrical", "switchboard", "live work", "energised", "HV",
                     "high voltage", "cable", "conduit", "distribution board",
                     "circuit breaker", "isolat"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.16 — Work involving electrical installation",
        "hrcw_license_class": "Electrician Licence (NSW Fair Trading) — A-grade or equivalent",
        "ppe": [
            "Arc flash PPE — Class 2 minimum for HV work",
            "Insulated gloves — voltage-rated",
            "Safety glasses",
            "Flame-resistant clothing",
        ],
        "certs": [
            "Electrician Licence — NSW Fair Trading (not SafeWork NSW)",
            "High Voltage Switching authority — where HV work involved",
        ],
        "permits": [
            "Electrical isolation permit — lock-out tag-out before work",
            "Live work permit — where de-energisation not reasonably practicable",
        ],
        "qualifications": [
            "Verification of isolation — two-person check before commencing",
        ],
        "notifications": [
            "Energy provider — notification before work on supply authority assets",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 s.164 — electrical risk management",
            "AS/NZS 3000 — Wiring Rules",
            "Live work — must be last resort, requires specific permit and PPE",
        ],
    },

    # ── SPRAY PAINTING ───────────────────────────────────────────────────────
    {
        "keywords": ["spray paint", "spray coat", "airless spray", "hvlp", "spray apply",
                     "spray encapsulant", "spray primer", "spray sealer", "spray finish"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Half-face respirator with organic vapour cartridge — where solvent-based product",
            "P2 respirator — where water-based product with fine mist",
            "Chemical-resistant gloves — nitrile minimum",
            "Safety glasses or goggles — full seal",
            "Coveralls — disposable or washable",
        ],
        "certs": [
            "SDS training — safety data sheet for each product used",
        ],
        "permits": [
            "Hot work exclusion — no ignition sources within 10m of solvent spray",
            "Ventilation plan — documented before spraying in enclosed space",
        ],
        "qualifications": [
            "Spray equipment inspection — before each shift",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 s.350 — hazardous chemicals duties",
            "SDS mandatory on site for every product in use",
            "Flammable products — eliminate ignition sources, ventilate",
        ],
    },

    # ── ABRASIVE BLASTING ────────────────────────────────────────────────────
    {
        "keywords": ["abrasive blast", "sandblast", "grit blast", "shot blast",
                     "pressure blast", "wet blast", "dry blast"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Blast helmet with supplied air — AS/NZS 1716 compliant",
            "P3 respirator — standby person outside blast zone",
            "Blast-resistant coveralls",
            "Hearing protection — >85dB noise exposure",
            "Steel-capped boots",
        ],
        "certs": [
            "Abrasive Blasting Licence — SafeWork NSW where required",
            "Noise monitoring — baseline audiogram for workers before first shift",
        ],
        "permits": [
            "Containment plan — before any open-air blasting",
            "EPA approval — where blasting generates regulated waste",
        ],
        "qualifications": [
            "Air compressor operator — competency before operating blast equipment",
            "Waste disposal — classified waste must go to licensed facility",
        ],
        "notifications": [
            "EPA — notification where blasting generates hazardous waste stream",
        ],
        "safework_notification": False,
        "epa_license": True,
        "notes": [
            "WHS Reg 2017 s.420 — lead dust exposure standard 0.05 mg/m³",
            "Silica — abrasive media must not contain free silica >1%",
            "Containment — mandatory for any lead or hazardous coating removal",
        ],
    },

    # ── WATERPROOFING ────────────────────────────────────────────────────────
    {
        "keywords": ["waterproof", "membrane", "tanking", "wet area", "balcony seal",
                     "deck seal", "podium waterproof", "below-slab", "liquid membrane"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Chemical-resistant gloves — nitrile or neoprene",
            "Safety glasses or goggles",
            "Organic vapour respirator — solvent-based products",
            "Coveralls — chemical splash protection",
        ],
        "certs": [
            "SDS training — safety data sheet for membrane product",
            "Licensed waterproofer — where AS 3740 compliance required",
        ],
        "permits": [],
        "qualifications": [
            "Applicator certification — manufacturer certification for warranty purposes",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 3740 — Waterproofing of domestic wet areas",
            "AS 4654.2 — Waterproofing membranes for external above-ground use",
            "Product SDS — on site before application starts",
        ],
    },

    # ── CONCRETE REPAIR / SPALLING ───────────────────────────────────────────
    {
        "keywords": ["concrete repair", "spalling", "crack stitch", "crack repair",
                     "concrete cancer", "carbonation", "rebar repair", "patch repair",
                     "structural repair", "helical bar", "epoxy inject"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Safety glasses or goggles — concrete dust and chemical splash",
            "P2 dust respirator — grinding and cutting operations",
            "Chemical-resistant gloves — when handling epoxy or chemical anchors",
            "Hard hat — overhead concrete removal",
            "Steel-capped boots",
        ],
        "certs": [
            "SDS training — epoxy resins, chemical anchors, concrete admixtures",
        ],
        "permits": [],
        "qualifications": [
            "Structural engineer — sign-off where load-bearing elements affected",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 3600 — Concrete structures — repair must match original structural intent",
            "Silica dust — P2 respirator mandatory for all grinding and cutting",
            "Epoxy products — 2-part systems, strict pot life management",
        ],
    },

    # ── WORK ENVIRONMENT — HEIGHT ────────────────────────────────────────────
    {
        "keywords": ["at height", "above ground", "elevated", "roof", "rooftop",
                     "ladder", "platform", "mezzanine", "elevated work platform",
                     "ewp", "boom lift", "scissor lift", "cherry picker"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.3 — Work at height with risk of fall >2m",
        "hrcw_license_class": "EWP Licence — WP class (boom over 11m)",
        "ppe": [
            "Full-body harness — AS/NZS 1891.1 compliant",
            "Energy-absorbing lanyard — double lanyard where continuous attachment required",
            "Helmet with chin strap — AS/NZS 1801",
        ],
        "certs": [
            "Working at heights — verified current competency (RIIOHS204E or equivalent per current RII Training Package)",
            "EWP operator licence — WP class where boom exceeds 11m",
        ],
        "permits": [
            "Working at heights permit — signed before each elevated task",
            "Working at heights permit — signed by supervisor before any work >2m commences",
        ],
        "qualifications": [
            "Competent person — pre-use inspection of fall arrest equipment",
            "Rescue plan — documented before work above 2m begins",
            "Rescue plan — documented before work commences; includes how to retrieve worker from harness/EWP/suspended scaffold if incapacitated",
            "Rescue equipment — on site and ready for immediate deployment before any elevated work starts",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 Part 4.4 — fall prevention hierarchy applies to all fall risk",
            "SafeWork NSW Code of Practice: Managing the Risk of Falls at Workplaces",
            "Harness inspection — pre-use check logged before each shift",
            "WHS Reg 2017 r.305 — rescue procedure required before commencing work at height",
            "Suspension trauma — incapacitated worker must be lowered within 15 minutes; harness straps can cause positional asphyxia",
            "Emergency contacts — on-site personnel trained in rescue procedure before elevated work begins",
            "WHS Reg 2017 r.291-303 — fall prevention hierarchy: (1) eliminate, (2) passive edge protection/guardrail, (3) restraint system, (4) fall arrest, (5) administrative",
            "Edge protection first — guardrails preferred over harness where work area permits fixed barriers",
            "Control line — 2m setback from edge, used only when guardrail not practicable",
            "Exclusion zone required below WAH operations — size proportional to fall/drop zone; physical barrier where practicable, flagging/bunting as minimum",
            "Emergency access must be maintained to all work zones including WAH exclusion zones",
        ],
    },

    # ── ROPE ACCESS ───────────────────────────────────────────────────────────
    {
        "keywords": ["rope access", "irata", "abseiling", "rappelling",
                     "industrial rope access", "facade rope access",
                     "rope descent", "rope work"],
        "hrcw": True,
        "hrcw_category": "Schedule 3 cl.2 — Work at height with risk of fall >2m",
        "hrcw_license_class": "IRATA certification — Level 1 (supervised), Level 2 (independent), Level 3 (supervisor/rescue)",
        "ppe": [
            "Full body harness — rope access rated, inspected before each use",
            "Rope access helmet with chin strap",
            "Gloves — rope access rated",
            "Safety glasses",
            "Non-slip footwear",
        ],
        "certs": [
            "IRATA International Rope Access certification — minimum Level 1 (supervised by Level 3)",
            "Working at heights certificate — as baseline",
        ],
        "permits": [
            "Rope access work permit — signed by IRATA Level 3 supervisor before descent",
            "Working at heights permit — signed before work commences",
        ],
        "qualifications": [
            "IRATA Level 3 technician — must be on site and supervising all rope access operations",
            "Rescue plan — documented by IRATA Level 3, rescue equipment rigged before any descent",
            "Anchor system inspection — independent anchor assessment by Level 3 before system loaded",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 r.291-306 — fall prevention hierarchy applies; rope access is fall arrest system",
            "IRATA Code of Practice — two independent anchor systems required (primary + backup)",
            "Exclusion zone below rope access operations — public and workers kept clear",
            "Equipment inspection — all rope access equipment inspected and tagged before each use",
            "Suspension trauma protocol — rescue must be achievable within 15 minutes",
            "Night work — additional lighting required; permits must specify lighting arrangements",
        ],
    },

    # ── WORK ENVIRONMENT — INDOOR / ENCLOSED ────────────────────────────────
    {
        "keywords": ["indoor", "enclosed", "internal", "inside building", "ceiling space",
                     "roof space", "subfloor", "basement", "underground", "plant room"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "P2 respirator — enclosed space dust accumulation",
        ],
        "certs": [],
        "permits": [
            "Ventilation plan — documented before work in enclosed space",
        ],
        "qualifications": [
            "Atmospheric test — O2 and contaminant levels checked before entry",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Enclosed spaces — ventilation mandatory, cross-ventilation preferred",
            "Dust — accumulates faster indoors, respiratory protection mandatory",
            "Noise — reverberant environments may exceed 85dB even at low source levels",
        ],
    },

    # ── WORK ENVIRONMENT — OCCUPIED BUILDING ────────────────────────────────
    {
        "keywords": ["occupied", "tenanted", "residents present", "public access",
                     "strata", "apartment", "live building", "operational building"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [],
        "permits": [
            "Noise management plan — required where work affects occupants",
            "Dust containment plan — hoarding or plastic sheeting before work starts",
            "After-hours work permit — council consent where applicable",
        ],
        "qualifications": [
            "Occupant notification — 48 hours minimum before noisy or dusty work",
            "Exclusion zone — clearly marked, prevents public access to work area",
        ],
        "notifications": [
            "Building manager — written notification before work commences",
            "Occupants — letterbox drop 48 hours before disruptive work",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Strata schemes — notify strata manager and obtain by-law compliance",
            "Noise curfew — residential: 8am–5pm weekdays, 8am–1pm Saturday, no Sunday",
            "Dust — full hoarding required where public or occupant exposure possible",
        ],
    },

    # ── WORK ENVIRONMENT — NEAR PUBLIC ──────────────────────────────────────
    {
        "keywords": ["near public", "footpath", "pedestrian", "public domain",
                     "road adjacent", "street frontage", "public space", "school nearby",
                     "childcare nearby", "hospital nearby"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [
            "Traffic Control accreditation — where work affects traffic flow",
        ],
        "permits": [
            "Council hoarding permit — where hoarding encroaches on footpath",
            "Traffic Management Plan — approved by council before work starts",
        ],
        "qualifications": [
            "Traffic controller — accredited, on site when traffic affected",
            "Exclusion zone — public excluded from falling object zone",
        ],
        "notifications": [
            "Council — hoarding licence application minimum 10 business days before",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Falling objects — overhead protection mandatory where public below",
            "Signage — worksite boundary clearly signed, pedestrian path maintained",
        ],
    },

    # ── STRUCTURAL — LOAD-BEARING ────────────────────────────────────────────
    {
        "keywords": ["load bearing", "load-bearing", "structural wall", "structural slab",
                     "structural beam", "structural column", "transfer slab", "core wall",
                     "shear wall", "moment frame", "structural element"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [],
        "permits": [
            "Structural engineer sign-off — before any penetration or modification",
        ],
        "qualifications": [
            "Structural engineer — review and approve method statement before work",
            "NCC compliance — any modification must maintain structural adequacy",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 3600 — Concrete structures — no penetration without engineer approval",
            "Load path — must be maintained or temporarily supported during work",
            "Propping — temporary works design required where load path interrupted",
        ],
    },

    # ── STRUCTURAL — POST-TENSION SLAB ──────────────────────────────────────
    {
        "keywords": ["post tension", "post-tension", "pt slab", "prestressed",
                     "post-tensioned", "tendon", "stressing"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Face shield — full face protection where tendon stress risk",
        ],
        "certs": [],
        "permits": [
            "PT slab penetration permit — structural engineer sign-off mandatory",
            "GPR scan — ground penetrating radar survey before any penetration",
        ],
        "qualifications": [
            "Structural engineer — approve all penetrations in writing before drill",
            "GPR operator — scan and mark tendon locations before work",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Post-tension tendons — cutting live tendon is catastrophic, potentially fatal",
            "GPR scan — mandatory before any core drill or penetration in PT slab",
            "No penetrations without structural engineer written approval",
        ],
    },

    # ── STRUCTURAL — HERITAGE ────────────────────────────────────────────────
    {
        "keywords": ["heritage", "heritage listed", "conservation area", "historic",
                     "heritage order", "state heritage", "local heritage"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [
            "Heritage consultant — engaged before any work affecting heritage fabric",
        ],
        "permits": [
            "Heritage Council approval — Section 60 permit where State Heritage Register",
            "Council heritage approval — Section 4.55 modification where local listing",
        ],
        "qualifications": [
            "Heritage architect — review method statement before work commences",
            "Conservation specialist — on site for any work to heritage fabric",
        ],
        "notifications": [
            "NSW Heritage Council — notification before work on State Heritage items",
            "Local council — notification before work on locally listed items",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Heritage Act 1977 (NSW) — penalties for unauthorised damage to heritage",
            "Reversible methods preferred — avoid irreversible changes to heritage fabric",
            "Documentation — photographic record before, during and after all works",
        ],
    },

    # ── HAZARDOUS MATERIALS — SILICA ─────────────────────────────────────────
    {
        "keywords": ["silica", "crystalline silica", "respirable silica", "quartz",
                     "sandstone", "granite", "concrete cutting", "concrete grinding",
                     "masonry cutting", "brick cutting", "tile cutting"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "P2 respirator — mandatory for all silica dust generating tasks",
            "Safety glasses — full seal during cutting and grinding",
        ],
        "certs": [
            "Silica dust awareness training — all workers before first exposure",
            "Health monitoring — baseline lung function test before first exposure",
        ],
        "permits": [
            "Silica dust management plan — documented before cutting or grinding",
        ],
        "qualifications": [
            "Wet cutting method — preferred over dry cutting to suppress dust",
            "On-tool extraction — vacuum with H-class filter where wet method not practicable",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 s.49 — WES for respirable crystalline silica 0.05 mg/m³",
            "SafeWork NSW — Crystalline Silica and Silicosis prevention guidelines",
            "Engineered stone — banned in NSW workplaces from 1 July 2024",
            "Health monitoring — mandatory where regular silica exposure occurs",
        ],
    },

    # ── HAZARDOUS MATERIALS — SYNTHETIC MINERAL FIBRE ───────────────────────
    {
        "keywords": ["glasswool", "glass wool", "rockwool", "rock wool", "mineral wool",
                     "insulation batt", "fibreglass insulation", "smf", "synthetic mineral"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "P2 respirator — SMF fibre inhalation risk",
            "Long-sleeve clothing — skin irritation prevention",
            "Safety glasses — eye irritation prevention",
            "Gloves — nitrile or cotton, SMF skin penetration",
        ],
        "certs": [
            "SMF awareness training — before first handling",
        ],
        "permits": [],
        "qualifications": [],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "SMF — not classified as carcinogen at current fibre dimensions, but respiratory protection mandatory",
            "Waste — bag and seal before disposal, standard landfill accepted",
        ],
    },

    # ── HAZARDOUS MATERIALS — PCBs ───────────────────────────────────────────
    {
        "keywords": ["pcb", "polychlorinated biphenyl", "old caulking", "old sealant",
                     "old transformer", "electrical transformer", "pcb contaminated"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Chemical-resistant gloves — nitrile, minimum 0.3mm",
            "Coveralls — disposable, sealed at wrists",
            "P2 respirator with organic vapour cartridge",
            "Safety glasses — full seal",
        ],
        "certs": [
            "PCB awareness training — before handling suspected PCB materials",
        ],
        "permits": [
            "EPA PCB waste disposal — licensed waste contractor required",
            "EPA contaminated material transport — licensed carrier",
        ],
        "qualifications": [
            "Licensed waste contractor — PCB materials must go to licensed facility",
        ],
        "notifications": [
            "NSW EPA — notification before removal of >1kg PCB material",
        ],
        "safework_notification": False,
        "epa_license": True,
        "notes": [
            "Protection of the Environment Operations Act 1997 — PCB disposal regulated",
            "PCBs in caulking — common in buildings constructed before 1980",
            "Sampling — test suspect caulking before removal, confirm PCB content",
        ],
    },

    # ── HAZARDOUS MATERIALS — MOULD ─────────────────────────────────────────
    {
        "keywords": ["mould", "mold", "fungal", "black mould", "mould remediation",
                     "mould removal", "biological contamination", "water damage"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "P2 respirator — mould spore inhalation",
            "Nitrile gloves — biological contamination",
            "Coveralls — disposable, sealed at wrists and ankles",
            "Safety glasses — full seal",
        ],
        "certs": [
            "Mould remediation training — IICRC S520 or equivalent",
        ],
        "permits": [
            "Containment plan — negative pressure containment before disturbance",
        ],
        "qualifications": [
            "Hygienist assessment — post-remediation clearance inspection",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "IICRC S520 — Standard for Professional Mould Remediation",
            "Containment — negative air pressure unit mandatory before disturbance",
            "Clearance — independent hygienist clearance before re-occupation",
            "Source — moisture source must be fixed before remediation begins",
        ],
    },

    # ── ENVIRONMENTAL — NEAR WATERWAY ────────────────────────────────────────
    {
        "keywords": ["near waterway", "near creek", "near river", "near drain",
                     "stormwater", "harbour", "foreshore", "water sensitive",
                     "near water", "coastal", "riparian"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [],
        "permits": [
            "EPA stormwater controls — erosion and sediment control plan before work",
            "Water licence — where work involves water extraction or diversion",
        ],
        "qualifications": [
            "Spill kit — on site before work near waterway begins",
            "Sediment fence — installed before ground disturbance",
        ],
        "notifications": [
            "NSW EPA — notification where work may affect waterway",
            "WaterNSW — notification where work is within 40m of waterway",
        ],
        "safework_notification": False,
        "epa_license": True,
        "notes": [
            "Protection of the Environment Operations Act 1997 — waterway pollution offence",
            "Erosion and sediment control — mandatory before any ground disturbance near water",
            "Chemical storage — bunded storage mandatory within 40m of waterway",
        ],
    },

    # ── ENVIRONMENTAL — CONTAMINATED LAND ───────────────────────────────────
    {
        "keywords": ["contaminated", "contaminated soil", "contaminated land",
                     "remediation", "former industrial", "underground storage tank",
                     "ust removal", "hydrocarbon", "petroleum contamination"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Chemical-resistant boots — contaminated soil contact",
            "Chemical-resistant gloves — nitrile minimum",
            "P2 respirator with organic vapour cartridge — VOC exposure",
            "Coveralls — disposable where heavy contamination",
        ],
        "certs": [
            "Site contamination assessment — accredited site auditor before work",
        ],
        "permits": [
            "EPA remediation action plan — approved before soil disturbance",
            "Contaminated waste transport — EPA licensed carrier",
        ],
        "qualifications": [
            "Accredited site auditor — engaged before and after remediation",
            "Licensed waste facility — contaminated soil disposal",
        ],
        "notifications": [
            "NSW EPA — notification of contaminated land discovery s.60 CLMA",
            "Council — notification where contamination may affect adjoining land",
        ],
        "safework_notification": False,
        "epa_license": True,
        "notes": [
            "Contaminated Land Management Act 1997 (NSW)",
            "EPA Guidelines — Assessment, Classification and Management of Liquid Wastes",
            "Unexpected finds — stop work protocol if unanticipated contamination found",
        ],
    },

    # ── WORKFORCE — NESB WORKERS ─────────────────────────────────────────────
    {
        "keywords": ["nesb", "non-english speaking", "language barrier", "interpreter",
                     "translated", "multilingual", "culturally diverse", "migrant worker"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [],
        "permits": [],
        "qualifications": [
            "Translated toolbox talk — in workers' primary language before first shift",
            "Pictogram-based SWMS — visual controls alongside text",
            "Interpreter — available for safety-critical instructions",
            "Buddy system — English-speaking buddy assigned to NESB workers",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Act 2011 s.46 — PCBU must ensure information is accessible to all workers",
            "SafeWork NSW — Language and literacy in the workplace guidance",
            "Pictograms — use AS 1319 safety signs as visual supplement to text SWMS",
        ],
    },

    # ── WORKFORCE — YOUNG WORKERS ────────────────────────────────────────────
    {
        "keywords": ["young worker", "apprentice", "trainee", "under 18", "junior",
                     "school-based", "work experience", "new to industry"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [],
        "permits": [],
        "qualifications": [
            "Increased supervision ratio — young workers not to work unsupervised",
            "Induction — extended induction before first task assignment",
            "Prohibited tasks — young workers under 18 must not operate certain plant",
            "Parent/guardian consent — where worker is under 18",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Act 2011 — PCBU duty of care extends to inexperienced workers",
            "Children and Young Persons (Care and Protection) Act 1998 (NSW)",
            "Prohibited equipment — check plant operator age minimums before assignment",
        ],
    },

    # ── WORKFORCE — LONE WORKER ──────────────────────────────────────────────
    {
        "keywords": ["lone worker", "working alone", "solo worker", "isolated worker",
                     "remote location", "after hours alone", "single worker"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [],
        "permits": [],
        "qualifications": [
            "Check-in schedule — mandatory, documented before lone work begins",
            "Emergency contact — designated person on call during lone work",
            "Communication device — mobile phone or radio confirmed working before start",
            "Duress alarm — where work is in isolated or high-risk location",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Act 2011 s.19 — PCBU must ensure lone workers are not at increased risk",
            "Check-in interval — maximum 2 hours for high-risk lone work",
            "No lone work — for confined space, live electrical, or work at height tasks",
        ],
    },

    # ── TIME-BASED — NIGHT WORK ──────────────────────────────────────────────
    {
        "keywords": ["night work", "night shift", "after hours", "overnight",
                     "out of hours", "after dark", "evening work", "nocturnal"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "High-visibility vest or shirt — Class N (night-rated) minimum",
            "Head torch or task lighting — minimum 200 lux at work face",
        ],
        "certs": [],
        "permits": [
            "After-hours work permit — council noise exemption where applicable",
            "Lighting plan — documented minimum lux levels before night work starts",
            "Security plan — site secured against unauthorised access during night work",
        ],
        "qualifications": [
            "Site lighting — minimum 200 lux at work face, 50 lux in access areas",
            "Fatigue management — maximum shift lengths documented and enforced",
        ],
        "notifications": [
            "Council — noise exemption application minimum 10 business days before",
            "Neighbours — notification of after-hours work at least 48 hours before",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Protection of the Environment Operations Act 1997 — noise curfew offences",
            "AS 1680 — Interior lighting — minimum lux levels for task visibility",
            "Fatigue — high-risk work (WAH, confined space) must not be performed when fatigued",
        ],
    },

    # ── TIME-BASED — WEEKEND WORK ────────────────────────────────────────────
    {
        "keywords": ["weekend", "saturday", "sunday", "public holiday",
                     "weekend work", "saturday work", "sunday work"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [],
        "permits": [
            "Council noise permit — Saturday after 1pm and all Sunday work",
            "Building manager approval — weekend access to strata or commercial buildings",
        ],
        "qualifications": [],
        "notifications": [
            "Neighbours — notification of Saturday or Sunday work 48 hours before",
            "Building manager — written consent for weekend site access",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "NSW noise curfew — residential: no work Sunday or public holidays",
            "Saturday — permitted 8am–1pm residential, check council DCP for commercial",
            "Public holidays — treat same as Sunday for noise purposes",
        ],
    },


    # ── CIVIL — ROCK BREAKING ────────────────────────────────────────────────
    {
        "keywords": ["rock break", "rock hammer", "rock breaking", "hydraulic hammer",
                     "rock excavat", "hard rock", "jack hammer", "jackhammer",
                     "pneumatic drill", "rock drill", "blasting"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Hearing protection — mandatory, rock breaking exceeds 100dB",
            "Safety glasses — full seal, rock fragment projectile risk",
            "Hard hat — falling rock fragments",
            "Steel-capped boots — heavy plant operation",
            "P2 dust respirator — silica dust from rock breaking",
        ],
        "certs": [
            "Noise monitoring — baseline audiogram before first exposure",
            "Vibration assessment — where breaking adjacent to existing structures",
        ],
        "permits": [
            "Exclusion zone — minimum 15m from rock breaking operation",
            "Vibration monitoring plan — where within 50m of existing structures",
        ],
        "qualifications": [
            "Competent person — vibration monitoring and threshold assessment",
            "Structural condition survey — before rock breaking adjacent to buildings",
        ],
        "notifications": [
            "Neighbours — vibration and noise notification before rock breaking commences",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 s.56 — vibration exposure standard 5 m/s² A(8)",
            "Blasting — separate licensing regime, SafeWork NSW blasting licence required",
            "Pre-break survey — photographic dilapidation survey of adjacent structures",
        ],
    },

    # ── CIVIL — DEWATERING — GENERAL ────────────────────────────────────────
    {
        "keywords": ["dewater", "dewatering", "groundwater removal", "pump out",
                     "groundwater control", "water table", "site dewatering"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Chemical-resistant boots — groundwater contact",
            "Nitrile gloves — pump and hose handling",
            "Safety glasses — discharge point splash risk",
        ],
        "certs": [
            "EPA Environment Protection Licence — required before any discharge to stormwater, waterway or sewer",
        ],
        "permits": [
            "EPA EPL application — minimum 60 days before dewatering commences",
            "Discharge point approval — confirmed in writing before pumping starts",
            "Sediment control — treatment system installed and tested before first pump",
        ],
        "qualifications": [
            "Water quality testing — pH and turbidity before every discharge event",
            "Discharge log — daily records of volume, pH, turbidity, destination",
            "Pump maintenance — daily pre-use check, spare pump on site",
        ],
        "notifications": [
            "NSW EPA — EPL application lodged minimum 60 days before start",
            "Sydney Water — trade waste agreement where discharge to sewer",
            "Council — stormwater discharge notification where applicable",
        ],
        "safework_notification": False,
        "epa_license": True,
        "notes": [
            "Protection of the Environment Operations Act 1997 — unlawful discharge offence",
            "Turbidity — discharge must not exceed 50 NTU to stormwater without treatment",
            "Three-stage settling minimum before any discharge",
            "pH — discharge must be between 6.5 and 8.5 before release",
        ],
    },

    # ── CIVIL — DEWATERING — WELLPOINT SYSTEM ───────────────────────────────
    {
        "keywords": ["wellpoint", "well point", "wellpoint system", "header pipe",
                     "vacuum dewatering", "wellpoint dewatering", "jetting wellpoint"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Hearing protection — vacuum pump noise typically exceeds 85dB",
            "Safety glasses — pressurised jetting operations",
            "Chemical-resistant gloves",
        ],
        "certs": [
            "Geotechnical engineer — wellpoint design and spacing before installation",
            "Water Access Licence — WaterNSW where extraction exceeds threshold",
        ],
        "permits": [
            "Aquifer interference approval — NSW DPE before wellpoint into aquifer",
            "WaterNSW water access licence — where groundwater extraction is ongoing",
            "EPA EPL — discharge of extracted groundwater",
        ],
        "qualifications": [
            "Specialist dewatering contractor — wellpoint installation is specialist work",
            "Draw-down monitoring — piezometers installed before system starts",
            "Settlement monitoring — survey points on adjacent structures before start",
            "24-hour monitoring — wellpoint systems require continuous supervision",
        ],
        "notifications": [
            "WaterNSW — bore licence application before wellpoint installation",
            "NSW DPE — aquifer interference approval application",
            "Neighbours — notification before dewatering adjacent to boundary",
        ],
        "safework_notification": False,
        "epa_license": True,
        "notes": [
            "Water Management Act 2000 (NSW) — aquifer interference approval required",
            "Draw-down radius — can extend 50–200m, affecting neighbouring foundations",
            "Artesian conditions — if bore flows uncontrolled, call WaterNSW immediately",
            "System failure — backup pump and generator mandatory for continuous systems",
        ],
    },

    # ── CIVIL — DEWATERING — DEEP WELL ──────────────────────────────────────
    {
        "keywords": ["deep well", "deep well dewatering", "bore pump", "submersible bore",
                     "deep groundwater", "aquifer dewatering", "deep bore dewatering"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Chemical-resistant boots and gloves — groundwater contact",
            "Hearing protection — pump motor noise",
        ],
        "certs": [
            "Licensed driller — bore installation requires NSW licensed driller",
            "Water Access Licence — mandatory for extraction from aquifer",
            "Aquifer interference approval — NSW DPE before bore drilled",
        ],
        "permits": [
            "Bore construction licence — NSW DPE before drilling",
            "Water Access Licence — WaterNSW for ongoing extraction",
            "EPA EPL — discharge of extracted groundwater",
            "Decommissioning plan — bore must be decommissioned after use per WaterNSW",
        ],
        "qualifications": [
            "Hydrogeologist — groundwater assessment before deep well design",
            "Draw-down modelling — predict impact radius before drilling",
            "Monitoring bores — installed around perimeter before main bore activated",
            "Decommissioning — licensed driller must decommission bore after use",
        ],
        "notifications": [
            "WaterNSW — bore licence notification before drilling",
            "NSW DPE — aquifer interference approval",
            "EPA — EPL for discharge of extracted water",
        ],
        "safework_notification": False,
        "epa_license": True,
        "notes": [
            "Water Management Act 2000 (NSW) — bore without licence is offence",
            "Aquifer interference — can affect water supply bores up to 1km away",
            "Artesian pressure — uncontrolled flow risk in Great Artesian Basin proximity",
            "Bore decommissioning — must be grouted by licensed driller after use",
        ],
    },

    # ── CIVIL — DEWATERING — CONTAMINATED GROUNDWATER ───────────────────────
    {
        "keywords": ["contaminated groundwater", "contaminated water", "hydrocarbon groundwater",
                     "petroleum groundwater", "groundwater contamination",
                     "polluted groundwater", "chemical groundwater"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Chemical-resistant suit — Tyvek minimum, chemical splash rated where solvents present",
            "Chemical-resistant boots — above-ankle protection",
            "Nitrile gloves — double layer",
            "Full-face respirator with organic vapour cartridge — VOC vapour exposure",
            "Safety glasses — full seal under respirator",
        ],
        "certs": [
            "Site contamination assessment — accredited site auditor before dewatering",
            "Waste classification — NATA laboratory analysis before disposal",
        ],
        "permits": [
            "EPA EPL — contaminated water discharge licence",
            "Licensed waste carrier — contaminated water transported by EPA licensed carrier only",
            "Licensed treatment facility — contaminated water to licensed facility only",
            "On-site treatment approval — EPA approval before any on-site treatment system",
        ],
        "qualifications": [
            "No discharge to stormwater or sewer — contaminated water requires specialist disposal",
            "Tanker collection — licensed liquid waste tanker for contaminated volumes",
            "Air monitoring — VOC monitoring where organic contaminants present",
            "Exclusion zone — no ignition sources where petroleum hydrocarbons present",
        ],
        "notifications": [
            "NSW EPA — contaminated water management plan before dewatering",
            "EPA — notification of unexpected contamination discovery s.60 CLMA",
        ],
        "safework_notification": False,
        "epa_license": True,
        "notes": [
            "Protection of the Environment Operations Act 1997 — contaminated discharge offence",
            "Contaminated Land Management Act 1997 — notification obligations on discovery",
            "Stop work immediately if unexpected contamination encountered",
            "LEL monitoring — mandatory where petroleum hydrocarbons in groundwater",
        ],
    },

    # ── CIVIL — DEWATERING — DISCHARGE TREATMENT ────────────────────────────
    {
        "keywords": ["discharge treatment", "settling tank", "sedimentation tank",
                     "flocculation", "ph correction", "water treatment dewatering",
                     "turbidity treatment", "filter sock", "sediment basin dewatering"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Chemical-resistant gloves — pH correction chemical handling",
            "Safety glasses — acid or alkali splash risk",
            "Chemical-resistant apron — dosing operations",
        ],
        "certs": [
            "Chemical storage compliance — bunded storage for pH correction chemicals",
        ],
        "permits": [
            "Treatment system design — engineer-designed settling tank before use",
            "Spill kit — on site before any chemical dosing commences",
        ],
        "qualifications": [
            "Settling tank sizing — minimum 24-hour hydraulic retention time",
            "Three-stage settling — primary, secondary, polishing before discharge",
            "pH correction — acid (HCl) or alkali (NaOH) dosing as required",
            "Turbidity testing — NTU meter calibrated before each discharge",
            "Discharge record — volume, pH, turbidity, time logged for every discharge",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": True,
        "notes": [
            "EPA EPL conditions — discharge limits typically pH 6.5–8.5, turbidity <50 NTU",
            "Flocculation — polyacrylamide flocculant used to accelerate settling",
            "Bunded storage — acid and alkali stored in separate bunded areas",
            "Emergency bypass — alarm and auto-shutoff where treatment system fails",
        ],
    },

    # ── CIVIL — DEWATERING — DRAW-DOWN SETTLEMENT ───────────────────────────
    {
        "keywords": ["draw-down", "drawdown", "settlement monitoring dewatering",
                     "groundwater settlement", "foundation settlement dewatering",
                     "adjacent structure dewatering", "pore pressure monitoring"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [
            "Geotechnical engineer — draw-down settlement analysis before dewatering",
        ],
        "permits": [
            "Settlement monitoring plan — engineer-designed before dewatering commences",
            "Dilapidation survey — photographic and measurement survey before start",
            "Trigger levels — green/amber/red thresholds defined before pumping starts",
        ],
        "qualifications": [
            "Survey monuments — installed on adjacent structures before dewatering",
            "Monitoring frequency — daily readings during active dewatering",
            "Amber trigger — reduce pumping rate and notify engineer",
            "Red trigger — immediate pump shutdown, notify engineer and structure owner",
            "Piezometers — groundwater level monitoring around perimeter of dewatering zone",
        ],
        "notifications": [
            "Adjoining owners — written notification and dilapidation survey before start",
            "Structural engineer — immediate notification if amber trigger reached",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Draw-down settlement — can occur up to 200m from dewatering zone",
            "Fine-grained soils — most susceptible to settlement from draw-down",
            "Dilapidation survey — legal protection against third-party damage claims",
            "Stop-work threshold — defined in geotechnical report, communicated to supervisor",
        ],
    },

    # ── CIVIL — DEWATERING — SUMP PUMPING ───────────────────────────────────
    {
        "keywords": ["sump pump", "sump pumping", "excavation sump", "temporary sump",
                     "pit dewatering", "trench dewatering", "surface water removal"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Rubber boots — sump area water contact",
            "Safety glasses",
            "Nitrile gloves",
        ],
        "certs": [],
        "permits": [
            "Sump design — lined sump with sediment trap before pump installation",
            "Discharge approval — confirmed before pumping starts",
            "Sediment sock or filter — on discharge hose before any release",
        ],
        "qualifications": [
            "Sump liner — impermeable liner in all temporary sumps",
            "Overflow protection — berm or secondary containment around sump",
            "Pump capacity — sized for maximum expected inflow plus 50% contingency",
            "Backup pump — standby pump on site for continuous dewatering operations",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": True,
        "notes": [
            "Sump liner — prevents contamination of surrounding soil",
            "Discharge hose — direct to treatment system, never direct to stormwater",
            "Sediment accumulation — desludge sump when >30% capacity reached",
        ],
    },

    # ── CIVIL — DEWATERING — SEWER DISCHARGE ────────────────────────────────
    {
        "keywords": ["sewer discharge", "trade waste", "sydney water discharge",
                     "discharge to sewer", "trade waste agreement"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [
            "Sydney Water trade waste agreement — mandatory before sewer discharge",
        ],
        "permits": [
            "Trade waste agreement — Sydney Water approval before any discharge to sewer",
            "Pre-treatment — trade waste conditions specify pre-treatment requirements",
            "Flow meter — metered discharge required under most trade waste agreements",
        ],
        "qualifications": [
            "pH and temperature compliance — Sydney Water limits pH 6–10, temp <45°C",
            "No contaminants — no petroleum, solvents or hazardous chemicals to sewer",
            "Monthly reporting — volume and quality data submitted to Sydney Water",
        ],
        "notifications": [
            "Sydney Water — trade waste application minimum 20 business days before discharge",
            "Sydney Water — notification of any accidental non-compliant discharge",
        ],
        "safework_notification": False,
        "epa_license": True,
        "notes": [
            "Sydney Water Act 1994 — trade waste discharge without agreement is offence",
            "Trade waste agreement — specifies daily volume, pH, temperature, contaminant limits",
            "Non-compliance — Sydney Water can terminate agreement and disconnect access",
        ],
    },


    # ── SYDNEY WATER — ASSET PROTECTION ─────────────────────────────────────
    {
        "keywords": ["sydney water asset", "sydney water main", "water main",
                     "sydney water pipe", "near water main", "water pipe protection",
                     "sydney water clearance", "asset protection sydney water"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [
            "Sydney Water Asset Protection — approval before any work near Sydney Water assets",
        ],
        "permits": [
            "Sydney Water asset protection application — submit before work commences",
            "Minimum clearances — horizontal 1m, vertical 0.5m from any Sydney Water asset",
            "Pipe protection plan — engineer-designed where clearances cannot be achieved",
            "Sydney Water representative — on site during any excavation within 2m of asset",
        ],
        "qualifications": [
            "Licensed plumber — any connection or work on Sydney Water infrastructure",
            "As-built drawings — Sydney Water asset locations confirmed before excavation",
            "Dial Before You Dig — mandatory in addition to Sydney Water asset search",
        ],
        "notifications": [
            "Sydney Water — asset protection application minimum 10 business days before",
            "Sydney Water — immediate notification if asset damaged or exposed",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Sydney Water Act 1994 — damage to assets is offence, full cost recovery applies",
            "Asset search — sydneywater.com.au asset map before any ground penetration",
            "Clearance violation — Sydney Water can issue stop work order immediately",
            "Emergency — 13 20 90 Sydney Water 24-hour emergency line",
        ],
    },

    # ── SYDNEY WATER — BUILD OVER AGREEMENT ─────────────────────────────────
    {
        "keywords": ["build over", "build-over", "structure over water main",
                     "building over sewer", "build over agreement", "structure over asset",
                     "encroachment sydney water"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [],
        "permits": [
            "Sydney Water build-over agreement — mandatory before any structure over Sydney Water asset",
            "Structural engineer certification — submitted with build-over application",
            "CCTV inspection — Sydney Water CCTV of asset before and after construction",
        ],
        "qualifications": [
            "No structures permitted — within 1m horizontal of Sydney Water main without agreement",
            "Access maintained — Sydney Water must be able to access asset at all times",
            "Agreement registration — build-over agreement registered on property title",
        ],
        "notifications": [
            "Sydney Water — build-over application minimum 20 business days before work",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Sydney Water Act 1994 — building over asset without agreement is offence",
            "Build-over agreement — runs with land, disclosed on property searches",
            "CCTV inspection — pre and post construction, cost borne by applicant",
            "Refusal — Sydney Water may refuse agreement for assets >300mm diameter",
        ],
    },

    # ── SYDNEY WATER — SEWER PROTECTION ─────────────────────────────────────
    {
        "keywords": ["sydney water sewer", "near sewer", "sewer main", "sewer protection",
                     "sewer crossing", "sewer diversion", "sewer relocation",
                     "gravity sewer", "rising main sewer"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Chemical-resistant boots — sewer exposure risk",
            "Nitrile gloves",
            "P2 respirator — H2S exposure near sewer",
            "Safety glasses",
        ],
        "certs": [
            "Licensed plumber — any work on Sydney Water sewer infrastructure",
            "Sydney Water approval — before any work within 2m of sewer main",
        ],
        "permits": [
            "Sewer protection plan — before any excavation within 2m of sewer",
            "CCTV inspection — sewer CCTV before and after work near asset",
            "Sewer support — temporary support designed before excavation adjacent to sewer",
        ],
        "qualifications": [
            "Gas monitoring — H2S and methane monitoring near any sewer excavation",
            "Confined space entry — if sewer entered, full confined space permit required",
            "Emergency isolation — sewer isolation procedure known before work starts",
        ],
        "notifications": [
            "Sydney Water — notification before any excavation within 2m of sewer",
            "Sydney Water — immediate notification if sewer damaged or breached",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "H2S — hydrogen sulfide from sewer, toxic above 10ppm, fatal above 100ppm",
            "Sewer breach — immediate notification to Sydney Water 13 20 90",
            "CCTV — pre-work condition record protects against liability for pre-existing damage",
        ],
    },

    # ── SYDNEY WATER — MAIN CONNECTION ──────────────────────────────────────
    {
        "keywords": ["water main connection", "sydney water connection", "tap main",
                     "service connection", "water service installation",
                     "new water connection", "water meter installation"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Safety glasses — pressurised connection splash risk",
            "Nitrile gloves",
        ],
        "certs": [
            "Licensed plumber — mandatory for any Sydney Water connection",
            "Sydney Water approval — connection approval before any tap to main",
            "Water meter — Sydney Water supplied and installed meter only",
        ],
        "permits": [
            "Sydney Water connection approval — minimum 15 business days before connection",
            "Pressure test — connection tested before commissioning",
            "Backflow prevention — device installed and certified before first use",
        ],
        "qualifications": [
            "Sydney Water supervision — Sydney Water representative required at time of connection",
            "Disinfection — new pipe flushed and disinfected per AS/NZS 3500",
            "Water quality test — bacteriological test before connection to network",
        ],
        "notifications": [
            "Sydney Water — connection application minimum 15 business days before",
            "Sydney Water — 48 hours notice before connection date confirmed",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Sydney Water Act 1994 — unauthorised connection is offence",
            "Licensed plumber — must hold current NSW plumbing licence",
            "Backflow prevention — mandatory for all new connections, AS/NZS 2845.1",
        ],
    },

    # ── TRANSPORT FOR NSW — ROAD CORRIDOR PERMIT ────────────────────────────
    {
        "keywords": ["road corridor", "road reserve", "classified road", "state road",
                     "transport for nsw", "rms permit", "roads and maritime",
                     "section 138", "roads act consent", "road corridor permit"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "High-visibility vest — Class D minimum in road corridor",
            "Hard hat",
            "Steel-capped boots",
        ],
        "certs": [
            "Traffic Control accreditation — TCP and TCS minimum",
            "Roads Act s.138 consent — before any work in road reserve",
        ],
        "permits": [
            "Section 138 Roads Act consent — Transport for NSW before any road reserve work",
            "Road corridor permit — Transport for NSW minimum 20 business days before",
            "Reinstatement bond — lodged with Transport for NSW before work commences",
            "Traffic Management Plan — TfNSW-approved before any work affecting traffic",
        ],
        "qualifications": [
            "Accredited TCP preparer — Traffic Control Plan prepared by accredited person",
            "Reinstatement standard — must meet AustRoads and TfNSW specifications",
            "Hold point — TfNSW inspection of reinstatement before bond release",
        ],
        "notifications": [
            "Transport for NSW — s.138 application minimum 20 business days before",
            "TfNSW network operations — 5 business days before work on state road",
            "Emergency services — notification of road works affecting access routes",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Roads Act 1993 (NSW) s.138 — works in road reserve without consent is offence",
            "Classified roads — different approval stream to council local roads",
            "Reinstatement — permanent reinstatement within 30 days, TfNSW inspection",
            "Bond — held until TfNSW satisfied with reinstatement quality",
        ],
    },

    # ── TRANSPORT FOR NSW — BRIDGE ADJACENT WORK ────────────────────────────
    {
        "keywords": ["bridge", "bridge adjacent", "near bridge", "bridge protection",
                     "bridge abutment", "bridge pier", "bridge deck",
                     "culvert", "overpass", "underpass", "viaduct"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Hard hat — overhead structure risk",
            "High-visibility vest",
            "Safety boots",
        ],
        "certs": [
            "Transport for NSW approval — before any work within bridge protection zone",
        ],
        "permits": [
            "Bridge protection plan — structural engineer designed before work near bridge",
            "Load limit compliance — no plant exceeding bridge load limit on structure",
            "Vibration monitoring — adjacent to bridge abutments or piers",
            "Transport for NSW bridge inspection — condition survey before and after work",
        ],
        "qualifications": [
            "Structural engineer — review method statement before work near bridge",
            "Vibration threshold — defined by engineer, monitoring continuous during work",
            "Exclusion zone — no heavy plant within engineer-specified distance of piers",
        ],
        "notifications": [
            "Transport for NSW bridges — notification before work within 50m of bridge",
            "TfNSW network operations — road impacts from bridge adjacent work",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Bridge protection zone — typically 50m each side, confirm with TfNSW",
            "Heavy plant — ground vibration from piling or rock breaking can damage bridge",
            "Waterway — works near bridge over waterway also requires WaterNSW notification",
        ],
    },

    # ── TRANSPORT FOR NSW — MOTORWAY / LANE CLOSURE ─────────────────────────
    {
        "keywords": ["motorway", "freeway", "highway", "lane closure", "lane closures",
                     "motorway works", "expressway", "m1", "m2", "m4", "m5", "m7",
                     "tunnel work", "motorway maintenance"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.1 — Construction work on or adjacent to road used by traffic",
        "hrcw_license_class": None,
        "ppe": [
            "High-visibility vest — Class D (night-rated) minimum on motorway",
            "Hard hat",
            "Steel-capped boots",
        ],
        "certs": [
            "Traffic Control accreditation — TCP and TCS minimum",
            "Transport for NSW motorway corridor access — separate approval to road corridor permit",
        ],
        "permits": [
            "TfNSW motorway lane closure application — minimum 6 weeks before closure",
            "Network Operations approval — TfNSW network operations sign-off required",
            "Variable Message Sign approval — TfNSW approval for any VMS deployment",
            "Traffic Management Plan — TfNSW-approved, specific to motorway requirements",
            "Night works approval — most motorway lane closures restricted to off-peak hours",
        ],
        "qualifications": [
            "TfNSW accredited TCP preparer — motorway-specific traffic control plan",
            "Police notification — where lane closure affects traffic flow significantly",
            "Speed reduction — TfNSW approval for reduced speed zone in work area",
            "Incident response plan — documented before any motorway work commences",
        ],
        "notifications": [
            "TfNSW network operations — minimum 6 weeks before motorway lane closure",
            "NSW Police — where closures affect major traffic flow",
            "511 traffic — work to be listed on TfNSW traffic information service",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Motorway lane closures — minimum 6 weeks approval lead time, often longer",
            "Off-peak only — most motorway work restricted to 9pm–5am weekdays",
            "Incident response — documented procedure for breakdown or accident in work zone",
            "TfNSW Road Occupancy Licence — required for any motorway corridor access",
        ],
    },

    # ── TRAFFIC CONTROL — TCP PREPARATION ───────────────────────────────────
    {
        "keywords": ["traffic control plan", "tcp", "traffic management plan", "tmp",
                     "tcp preparer", "traffic control preparation", "tcp design"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [
            "Accredited TCP preparer — AS 1742.3 traffic control plan accreditation",
            "Traffic Controller (TCS) — separate accreditation to TCP preparer",
        ],
        "permits": [
            "TCP approval — relevant authority approval before implementation",
            "Site-specific TCP — generic plans not acceptable on state roads",
        ],
        "qualifications": [
            "TCP preparer — accredited by Transport for NSW or Roads Authority",
            "As-built TCP — record of actual implementation kept on site",
            "Daily review — TCP reviewed at start of each shift for changed conditions",
        ],
        "notifications": [
            "Relevant authority — TCP submitted for approval minimum 5 business days before",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 1742.3 — Manual of uniform traffic control devices — works on roads",
            "TCP must be site-specific — generic templates not accepted on classified roads",
            "TCP preparer accreditation — check current status on TfNSW register before engaging",
        ],
    },

    # ── TRAFFIC CONTROL — PEDESTRIAN MANAGEMENT ─────────────────────────────
    {
        "keywords": ["pedestrian management", "pedestrian path", "pedestrian access",
                     "pedestrian diversion", "footpath closure", "pedestrian safety",
                     "accessible route", "disability access works"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "High-visibility vest",
        ],
        "certs": [
            "Traffic Control accreditation — TCS minimum where pedestrians redirected",
        ],
        "permits": [
            "Pedestrian management plan — approved by council before footpath closure",
            "Alternative pedestrian path — safe, accessible alternative before closure",
            "Tactile ground surface indicators — at diversions for vision-impaired users",
        ],
        "qualifications": [
            "DDA compliance — alternative route must meet Disability Discrimination Act",
            "Lighting — pedestrian diversion lit to minimum 50 lux after dark",
            "Signage — clear directional signs at every decision point on diversion route",
            "Council approval — footpath closure approved before implementation",
        ],
        "notifications": [
            "Council — pedestrian management plan submission before footpath closure",
            "Disability organisations — notification where accessible routes affected",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Disability Discrimination Act 1992 — accessible alternative route mandatory",
            "Tactile indicators — required at all kerb ramps on diversion route",
            "School zones — no footpath closure during school hours without council approval",
        ],
    },

    # ── TRAFFIC CONTROL — SCHOOL ZONE ───────────────────────────────────────
    {
        "keywords": ["school zone", "near school", "school adjacent", "school frontage",
                     "primary school", "high school", "school hours", "school traffic"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "High-visibility vest — Class D in school zone",
        ],
        "certs": [
            "Traffic Control accreditation — mandatory near school",
        ],
        "permits": [
            "School zone work permit — council and school principal approval before work",
            "No lane closures during school hours — 8–9:30am and 2:30–4pm Monday–Friday",
            "Traffic controller — mandatory during school hours if any work affects traffic",
        ],
        "qualifications": [
            "School principal notification — written consent before work near school",
            "Dust and noise controls — enhanced controls during school hours",
            "Delivery restriction — no heavy vehicles during school arrival/departure times",
        ],
        "notifications": [
            "School principal — written notification minimum 5 business days before work",
            "Council — school zone works approval before commencing",
            "Parents — via school newsletter where work affects school access",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "School zone speed — 40 km/h during school hours, work must not obstruct signs",
            "Children — heightened duty of care where children present near work zone",
            "No horn or reversing alarms — near school during school hours where avoidable",
        ],
    },

    # ── TRAFFIC CONTROL — VARIABLE MESSAGE SIGNS ────────────────────────────
    {
        "keywords": ["variable message sign", "vms", "portable vms", "electronic sign",
                     "message board", "dynamic message sign", "trailer vms"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "High-visibility vest — Class D when deploying VMS on road",
        ],
        "certs": [
            "Transport for NSW VMS approval — before any VMS on state road",
        ],
        "permits": [
            "TfNSW VMS content approval — messages pre-approved before display",
            "VMS placement approval — location approved as part of TCP",
            "Power source — generator or solar, no connection to road infrastructure",
        ],
        "qualifications": [
            "Message content — approved messages only, no unapproved custom text",
            "Placement — minimum 500m before work zone on arterial roads",
            "Visibility — unobstructed sightlines, no blocking signs or signals",
        ],
        "notifications": [
            "TfNSW — VMS deployment notification as part of TCP approval",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 1742.3 — VMS placement and message standards",
            "TfNSW approved messages — standard message library, no free text without approval",
            "Trailer stability — VMS trailer stabilised and chocked before display",
        ],
    },

    # ── TRAFFIC CONTROL — NIGHT WORKS TRAFFIC ───────────────────────────────
    {
        "keywords": ["night works traffic", "night traffic management", "after hours traffic",
                     "overnight traffic", "night lane closure", "night road works"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "High-visibility vest — Class D night-rated mandatory",
            "Hard hat — with retro-reflective strips",
            "Head torch — for personal visibility and task lighting",
        ],
        "certs": [
            "Traffic Control accreditation — TCS mandatory for night traffic control",
            "Night works TCP — separate night-specific traffic control plan required",
        ],
        "permits": [
            "Night works permit — council or TfNSW approval for after-hours road work",
            "Enhanced lighting plan — minimum 200 lux at work face, 50 lux in transition zones",
            "Reduced speed zone — additional speed reduction for night work zones",
        ],
        "qualifications": [
            "Additional signage — increased sign spacing for night conditions",
            "Delineation — additional cones and barriers for reduced visibility",
            "Fatigue management plan — night shift rotation and maximum hours documented",
            "Spotter — additional spotter for reversing plant at night",
        ],
        "notifications": [
            "TfNSW — night works notification as part of road occupancy licence",
            "Residents — letterbox drop minimum 48 hours before first night shift",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Night visibility — driver reaction times longer, increased signage spacing required",
            "Fatigue — high-risk tasks must not be assigned to fatigued night workers",
            "Lighting — AS 1680 minimum lux levels, measured at work face not overhead",
        ],
    },


    {
        "keywords": ["ground anchor", "tieback", "tie-back", "soil nail", "rock anchor",
                     "anchor pile", "strand anchor", "bar anchor", "ground anchor testing"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Face shield — during stressing operations",
            "Hard hat — anchor head failure risk during proof testing",
            "Safety glasses",
        ],
        "certs": [],
        "permits": [
            "Structural engineer design — every anchor must have engineered design",
            "Proof test certification — before anchor put into service",
        ],
        "qualifications": [
            "Structural engineer — design and witness proof testing",
            "Specialist contractor — ground anchor installation requires specialist",
            "Settlement monitoring — adjacent structures during anchor installation",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 4678 — Earth retaining structures — anchor design requirements",
            "Proof test — each anchor tested to 1.5x working load before acceptance",
            "Dial Before You Dig — mandatory before any drilling for anchors",
        ],
    },

    # ── POOL — DESIGN & APPROVAL ────────────────────────────────────────────
    {
        "keywords": ["pool construction", "pool build", "pool installation", "inground pool",
                     "above ground pool", "swimming pool construction", "pool design",
                     "pool approval", "pool da", "pool permit"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [
            "Council DA or CDC — before any pool construction commences",
            "Principal Certifier appointment — before Construction Certificate issued",
            "BASIX pool — pools >40,000L require BASIX water commitments",
        ],
        "permits": [
            "Development Application or CDC — council approval before excavation",
            "Construction Certificate — before physical work commences",
            "Long Service Levy — 0.35% of construction cost before CC",
            "BASIX certificate — pools >40,000L include water efficiency commitments",
            "Flood planning certificate — required where pool in flood zone",
        ],
        "qualifications": [
            "Setback compliance — confirm pool setbacks from boundaries per council LEP",
            "Equipment enclosure — pump and filter within council-approved setback",
            "Council conditions — DA conditions read and complied with before each stage",
        ],
        "notifications": [
            "Council — DA or CDC application minimum 40 business days before construction",
            "Principal Certifier — appointment notified before CC issued",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Environmental Planning and Assessment Act 1979 (NSW) — pool approval obligations",
            "SEPP (Exempt and Complying Development) 2008 — check if pool is exempt or complying",
            "Flood zone — additional requirements, pool may need to be anchored against uplift",
        ],
    },

    # ── POOL — GEOTECHNICAL & STRUCTURAL DESIGN ──────────────────────────────
    {
        "keywords": ["pool structural", "pool shell design", "pool engineer",
                     "pool geotechnical", "soil report pool", "pool hydrostatic",
                     "pool structural design", "pool shell engineer"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [
            "Geotechnical report — soil classification before pool shell design",
            "Structural engineer — pool shell design certified before construction",
        ],
        "permits": [
            "Structural engineer certification — shell design lodged with CC application",
            "Hydrostatic uplift design — engineer calculation where high water table",
            "Hydrostatic valve — passive valve in pool base, engineer-specified",
        ],
        "qualifications": [
            "Soil classification — AS 2870 site classification before structural design",
            "Reactive soils — additional design requirements for Class M, H, E sites",
            "Hydrostatic uplift — pool must be anchored or drained if water table high",
            "Adjacent structures — setback and load impact on neighbouring footings assessed",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 2870 — Residential slabs and footings — soil classification",
            "Hydrostatic uplift — empty pool can float out of ground if water table rises",
            "Hydrostatic valve — opens automatically when groundwater pressure exceeds pool weight",
        ],
    },

    # ── POOL — EXCAVATION ───────────────────────────────────────────────────
    {
        "keywords": ["pool excavation", "dig pool", "pool dig", "excavate pool",
                     "pool hole", "pool cut", "rock pool excavation"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.12 — Excavation deeper than 1.5m",
        "hrcw_license_class": None,
        "ppe": [
            "Hard hat — mandatory in excavation zone",
            "High-visibility vest",
            "Steel-capped boots",
            "P2 dust respirator — silica dust from excavation",
        ],
        "certs": [
            "Dial Before You Dig — mandatory before any pool excavation",
            "Excavator operator licence — relevant HRW plant licence",
        ],
        "permits": [
            "Dial Before You Dig clearance — services confirmed before dig",
            "Shoring plan — engineer-designed if adjacent to structures or >1.5m depth",
            "Dewatering plan — if groundwater encountered during excavation",
            "Vibration monitoring — where rock breaking adjacent to existing structures",
        ],
        "qualifications": [
            "Excavation depth — pool excavations typically 1.8–2.2m, triggers HRCW",
            "Benching — safety benches cut during excavation for worker access",
            "Battering — sides battered at safe angle if no shoring used",
            "Adjacent footings — minimum 600mm clearance from neighbouring footings",
            "Spoil — spoil stockpiled minimum 1m from excavation edge",
        ],
        "notifications": [
            "Dial Before You Dig — 2 business days before excavation commences",
            "Neighbours — notification before rock breaking or heavy excavation adjacent to boundary",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 s.306 — excavation deeper than 1.5m is HRCW",
            "SafeWork NSW Code of Practice: Excavation Work",
            "Rock excavation — blasting requires separate licence, rock breaker requires vibration monitoring",
        ],
    },

    # ── POOL — CONCRETE SHELL (SHOTCRETE/GUNITE) ─────────────────────────────
    {
        "keywords": ["shotcrete pool", "gunite pool", "concrete pool shell",
                     "pool concrete", "pool shell concrete", "pool spray concrete",
                     "pool reinforcement", "pool rebar", "pool steel"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Safety glasses — full seal, shotcrete rebound risk",
            "Hard hat — overhead shotcrete spray",
            "Chemical-resistant gloves — cement contact dermatitis",
            "P2 dust respirator — concrete dust and silica during application",
            "Rubber boots — concrete immersion",
            "Knee pads — pool floor finishing work",
        ],
        "certs": [
            "Licensed shotcrete applicator — ACI or ACRA certified nozzleman",
            "Principal Certifier inspection hold point — steel and formwork before shotcrete",
            "Concrete mix design — engineer-approved mix before application",
        ],
        "permits": [
            "PC hold point — steel inspection before any concrete placed",
            "Concrete test cylinders — minimum 3 cylinders per pour for strength testing",
            "Curing plan — wet curing minimum 7 days before filling",
        ],
        "qualifications": [
            "Steel cover — minimum 40mm concrete cover to all reinforcement",
            "Rebound — shotcrete rebound must not be incorporated back into shell",
            "Waterproofing coat — render or membrane before tiling",
            "Curing — pool shell must be fully cured before water fill",
        ],
        "notifications": [
            "Principal Certifier — 48 hours notice before shotcrete inspection hold point",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 3600 — Concrete structures — shell design requirements",
            "Shotcrete rebound — highly alkaline, causes chemical burns, full PPE mandatory",
            "Shrinkage cracks — normal in pool shells, address before tiling with flexible render",
        ],
    },

    # ── POOL — FIBREGLASS SHELL ──────────────────────────────────────────────
    {
        "keywords": ["fibreglass pool", "fiberglass pool", "fibreglass shell",
                     "pool crane lift", "pool delivery", "gel coat pool",
                     "one piece pool", "moulded pool"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.8 — Work involving use of crane",
        "hrcw_license_class": "Crane Licence — C6 mobile crane",
        "ppe": [
            "Hard hat — crane lift zone",
            "High-visibility vest",
            "Safety boots",
            "Nitrile gloves — fibreglass handling, skin irritation",
            "Safety glasses — fibreglass strand inhalation risk",
        ],
        "certs": [
            "Crane operator licence — C6 mobile crane (SafeWork NSW)",
            "Dogman licence — DG class for directing crane during shell placement",
            "Lift study — documented before crane delivery and placement",
            "Ground bearing assessment — engineer certification before crane set-up",
        ],
        "permits": [
            "Crane exclusion zone — established before lift commences",
            "Road occupancy — council permit if crane blocks road during delivery",
            "Neighbour notification — crane oversailing adjacent property",
        ],
        "qualifications": [
            "Footings — concrete footings poured and cured before shell placed",
            "Level — shell level checked immediately after placement before backfill",
            "Backfill — engineered backfill mix, placed evenly both sides simultaneously",
            "Water fill — pool filled simultaneously with backfill to prevent shell distortion",
        ],
        "notifications": [
            "Council — road occupancy licence if crane requires road closure",
            "Neighbours — notification if crane oversails neighbouring property",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Fibreglass shell — simultaneous water fill and backfill mandatory to prevent distortion",
            "Crane lift — pool shells up to 5 tonnes, minimum C6 mobile crane licence",
            "Oversailing — crane oversailing neighbouring property requires written consent",
        ],
    },

    # ── POOL — HYDRAULICS & EQUIPMENT ───────────────────────────────────────
    {
        "keywords": ["pool hydraulics", "pool pump", "pool filter", "pool plumbing",
                     "pool pipework", "pool equipment", "pool plant", "pool circulation",
                     "pool backwash", "pool suction", "pool return"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Safety glasses — pressurised system testing",
            "Nitrile gloves — chemical contact",
        ],
        "certs": [
            "Licensed plumber — all pool hydraulics by licensed plumber",
            "AS 1926.3 compliance — hydraulic design must meet entrapment prevention standard",
            "Plumbing compliance certificate — issued by plumber after hydraulic completion",
        ],
        "permits": [
            "Council inspection — hydraulics inspection hold point before backfill",
            "Backwash discharge approval — council approval before backwash connected to drain",
            "Pressure test — all pipework pressure tested before backfill",
        ],
        "qualifications": [
            "Dual main drains — AS 1926.3 anti-entrapment, minimum two main drains",
            "Suction fittings — AS 1926.3 compliant anti-vortex covers on all suction points",
            "Pipe sizing — hydraulic design by licensed plumber, sized for flow rates",
            "Equipment pad — concrete equipment pad, level and drained",
            "Backwash — discharged to council-approved point, not to stormwater",
        ],
        "notifications": [
            "Council — hydraulics inspection hold point notification 48 hours before",
            "Principal Certifier — hydraulics completion before fill hold point",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 1926.3 — Water recirculation systems for swimming pools",
            "Anti-entrapment — dual main drains mandatory, single drain is drowning risk",
            "Backwash — must not discharge to stormwater, council approval required",
        ],
    },

    # ── POOL — HEATING ───────────────────────────────────────────────────────
    {
        "keywords": ["pool heating", "pool heater", "pool heat pump", "pool solar heating",
                     "pool gas heater", "pool electric heating", "pool temperature"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Safety glasses",
            "Gas detector — calibrated before gas heater commissioning",
        ],
        "certs": [
            "Licensed gasfitter — gas pool heater installation by licensed gasfitter",
            "Licensed electrician — electric heat pump installation by licensed electrician",
            "Gas compliance certificate — issued after gas heater installation",
            "CCEW — Certificate of Compliance Electrical Work for heat pump",
        ],
        "permits": [
            "Gas compliance certificate — mandatory before gas heater commissioned",
            "Electrical approval — where heat pump exceeds 10A circuit",
            "Ventilation — gas heater requires adequate combustion air per manufacturer",
        ],
        "qualifications": [
            "Flue clearances — gas heater flue minimum clearances from openings",
            "Heat pump location — minimum clearances for air intake and discharge",
            "Timer — heating timer installed to limit operating hours",
        ],
        "notifications": [
            "Jemena — new gas service connection for gas heater",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Gas Supply Act 1996 (NSW) — gas heater must be installed by licensed gasfitter",
            "Heat pump — COP typically 5:1, most energy efficient heating option",
            "Solar heating — no licence required for solar panels, but plumber for connections",
        ],
    },

    # ── POOL — CHEMICAL SYSTEM ───────────────────────────────────────────────
    {
        "keywords": ["pool chemical", "pool chlorine", "pool dosing", "pool chemical system",
                     "pool sanitiser", "pool salt chlorinator", "pool chemical storage",
                     "pool water treatment", "pool ph", "pool balance"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Chemical-resistant gloves — pool chemical handling",
            "Safety glasses — full seal, chemical splash",
            "P2 respirator — chlorine gas inhalation risk when handling concentrated chemicals",
            "Chemical-resistant apron — dosing operations",
        ],
        "certs": [
            "SDS review — Safety Data Sheet for every chemical used reviewed before handling",
        ],
        "permits": [
            "Chemical storage — bunded, locked, ventilated storage before chemicals on site",
            "Spill kit — on site before any pool chemicals delivered",
            "Separate storage — oxidisers and acids must not be stored together",
        ],
        "qualifications": [
            "Chlorine and acid — never mixed directly, causes toxic gas release",
            "Chemical dosing — automated dosing system preferred over manual",
            "Emergency procedure — chlorine gas spill response documented before commissioning",
            "Bunded storage — minimum 110% capacity bund around chemical storage area",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 s.350 — hazardous chemicals management",
            "Chlorine and acid — mixing causes chlorine gas, immediately dangerous to life",
            "SDS — on site for every chemical, accessible to all workers",
        ],
    },

    # ── POOL — SAFETY BARRIER ────────────────────────────────────────────────
    {
        "keywords": ["pool barrier", "pool fence", "pool safety fence",
                     "pool gate", "pool fencing", "pool safety barrier",
                     "non-climbable zone", "ncz pool", "pool barrier inspection"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [
            "Pool barrier certification — accredited certifier inspection before water added",
            "AS 1926.1 compliance — barrier height, gate, NCZ all certified",
        ],
        "permits": [
            "Barrier inspection hold point — certifier inspection before pool filled",
            "Temporary barrier — mandatory during construction before permanent fence installed",
            "Council inspection — barrier inspection before occupation certificate",
        ],
        "qualifications": [
            "Barrier height — minimum 1200mm from finished ground level",
            "Non-climbable zone — 900mm NCZ on outside of barrier, 300mm on inside",
            "Gate — self-closing, self-latching, opens away from pool, latch >1500mm or child-proof",
            "CPR sign — current waterproof CPR chart posted at pool before first use",
            "No climbable objects — no furniture, BBQs or equipment within NCZ",
            "Temporary barrier — erected immediately after excavation commences",
        ],
        "notifications": [
            "Council — barrier inspection before occupation certificate issued",
            "NSW pool register — registration within 1 month of completion",
            "Principal Certifier — barrier inspection hold point 48 hours notice",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Swimming Pools Act 1992 (NSW) — barrier mandatory, no water without certified barrier",
            "AS 1926.1 — Safety barriers for swimming pools",
            "Temporary barrier — required from day of excavation, not just when pool is filled",
            "Drowning — young children can drown in as little as 20mm of water",
        ],
    },

    # ── POOL — SURROUNDS & FINISHING ─────────────────────────────────────────
    {
        "keywords": ["pool surrounds", "pool coping", "pool paving", "pool tiling",
                     "pool finish", "pool plaster", "pool render", "pool pebblecrete",
                     "pool mosaic", "pool deck surrounds", "pool concretor"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Safety glasses — tile cutting and grinding",
            "P2 dust respirator — silica in tile cutting and concrete grinding",
            "Hearing protection — angle grinder and tile saw exceed 85dB",
            "Knee pads — pool floor tiling",
            "Chemical-resistant gloves — grout and adhesive handling",
        ],
        "certs": [
            "Licensed concretor — pool surrounds require licensed contractor",
            "Slip resistance testing — minimum R11 wet slip resistance around pool",
        ],
        "permits": [
            "Principal Certifier inspection — surrounds and coping before occupation certificate",
        ],
        "qualifications": [
            "Slip resistance — AS 4586 minimum R11 for wet pool surrounds",
            "Coping — cantilevered coping requires engineer certification",
            "Expansion joints — between pool shell and surrounds, flexible sealant",
            "Wet cutting — tile and concrete cutting must use wet cutting to suppress silica dust",
            "Drainage — surrounds drain away from pool, no ponding",
        ],
        "notifications": [
            "Principal Certifier — surrounds inspection hold point 48 hours notice",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 4586 — Slip resistance classification of new pedestrian surfaces",
            "Silica — tile and pebblecrete cutting generates respirable silica, wet cutting mandatory",
            "Expansion joint — pool shell moves independently of surrounds, joint prevents cracking",
        ],
    },

    # ── POOL — UNDERWATER LIGHTING ───────────────────────────────────────────
    {
        "keywords": ["pool lighting", "underwater light", "pool light",
                     "pool led light", "pool niche", "submersible light",
                     "pool electrical", "pool low voltage"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.16 — Electrical installation in or near water",
        "hrcw_license_class": "Electrician Licence — NSW Fair Trading A-grade",
        "ppe": [
            "Insulated gloves — voltage-rated",
            "Safety glasses",
        ],
        "certs": [
            "Licensed electrician — all pool electrical by A-grade licensed electrician",
            "CCEW — Certificate of Compliance Electrical Work issued after installation",
            "IP68 rating — all underwater fittings IP68 minimum",
        ],
        "permits": [
            "Electrical approval — pool electrical as part of construction certificate",
            "CCEW — provided to owner before pool commissioned",
            "Isolation transformer — mandatory for all pool lighting circuits",
        ],
        "qualifications": [
            "Low voltage — maximum 12V AC or 12V DC for underwater luminaires",
            "Isolation transformer — separates pool lighting from mains supply",
            "Bonding — all metallic pool components bonded to equipotential bonding network",
            "RCD protection — all pool electrical circuits protected by 30mA RCD",
            "Niche installation — waterproof niche installed before shell concrete placed",
        ],
        "notifications": [
            "Principal Certifier — electrical inspection hold point 48 hours notice",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS/NZS 3000 — Wiring rules — pool electrical requirements Section 6.0",
            "Equipotential bonding — prevents voltage gradients in pool water",
            "Electric shock drowning — risk where bonding or isolation is inadequate",
            "IP68 — fully submersible rating required for all underwater fittings",
        ],
    },

    # ── POOL — REGISTRATION & CERTIFICATION ─────────────────────────────────
    {
        "keywords": ["pool registration", "pool register", "pool certificate",
                     "pool occupation certificate", "pool certifier",
                     "pool final inspection", "pool compliance"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [
            "Occupation Certificate — includes pool where pool is part of building works",
            "Pool barrier certificate — accredited certifier before water added",
            "NSW pool register — mandatory registration within 1 month of completion",
        ],
        "permits": [
            "Final inspection — PC final inspection before occupation certificate",
            "Pool barrier inspection — certifier inspection of AS 1926.1 compliance",
            "NSW pool register — registration at swimmingpoolregister.nsw.gov.au",
        ],
        "qualifications": [
            "Certifier hold points — shell, hydraulics, barrier, electrical, final",
            "All trades compliance certificates — plumbing, electrical, gas held before OC",
            "Council inspection — pool barrier inspection before OC issued",
        ],
        "notifications": [
            "NSW pool register — register within 1 month of pool completion",
            "Council — pool barrier inspection before occupation certificate",
            "Principal Certifier — final inspection 48 hours notice",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Swimming Pools Act 1992 (NSW) — pool registration mandatory",
            "Barrier non-compliance — council can issue prohibition order preventing pool use",
            "OC — occupation certificate cannot be issued without pool compliance",
        ],
    },

    # ── RESIDENTIAL — OWNER BUILDER ─────────────────────────────────────────
    {
        "keywords": ["owner builder", "owner-builder", "owner build", "self build",
                     "owner built", "owner building permit"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [
            "Owner Builder Permit — NSW Fair Trading, required for work >$10,000",
            "Owner Builder course — 6-hour approved course before permit issued",
        ],
        "permits": [
            "Owner Builder Permit — NSW Fair Trading before any licensed trade work",
            "Construction Certificate — before physical work commences",
            "Principal Certifier appointment — before CC issued",
        ],
        "qualifications": [
            "HBC insurance — owner builder cannot provide statutory warranty, disclosure required on sale",
            "Owner builder limit — one permit per 5 years per owner",
            "Licensed trades — all electrical, plumbing, gas must be done by licensed contractors",
            "Sale restriction — cannot sell within 7.5 years without HBC insurance",
        ],
        "notifications": [
            "NSW Fair Trading — owner builder permit application before work",
            "Council — DA or CDC before any structural work",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Home Building Act 1989 (NSW) — owner builder obligations",
            "Owner builder permit — not a licence, does not exempt from building standards",
            "Defects — owner builder personally liable for defects for 6 years",
        ],
    },

    # ── RESIDENTIAL — LICENSED CONTRACTOR ───────────────────────────────────
    {
        "keywords": ["residential contractor", "home builder", "licensed builder",
                     "building contractor residential", "hbc licence", "contractor licence",
                     "building licence nsw", "fair trading licence"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [
            "Contractor Licence — NSW Fair Trading, class appropriate to work value",
            "Home Building Compensation (HBC) insurance — mandatory for work >$20,000",
        ],
        "permits": [
            "HBC insurance certificate — provided to client before contract signed",
            "Residential building contract — mandatory for work >$5,000, HBC Act compliant",
        ],
        "qualifications": [
            "Licence check — verify contractor licence on NSW Fair Trading register before engaging",
            "Deposit limit — maximum 10% deposit for work >$20,000",
            "Contract inclusions — plans, specifications, start/finish dates mandatory in contract",
            "Statutory warranty — 6-year major defects, 2-year other defects from completion",
        ],
        "notifications": [
            "NSW Fair Trading — complaint pathway if licence or insurance breach suspected",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Home Building Act 1989 (NSW) — contractor licence and HBC insurance obligations",
            "Licence classes — contractor licence (unlimited), supervisor licence, tradesperson licence",
            "HBC insurance — protects homeowner if builder dies, disappears or becomes insolvent",
        ],
    },

    # ── RESIDENTIAL — PRINCIPAL CERTIFIER & CC ──────────────────────────────
    {
        "keywords": ["principal certifier", "construction certificate", "cc approval",
                     "certifier", "pca", "occupation certificate", "oc residential",
                     "complying development certificate", "cdc", "building approval"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [
            "Construction Certificate — issued by Principal Certifier before physical work",
            "Principal Certifier appointment — EPA Act s.6.6, appointed before CC issued",
        ],
        "permits": [
            "Construction Certificate or CDC — mandatory before any building work commences",
            "Council or accredited certifier — PC must be appointed before first inspection",
            "Long Service Levy — paid before CC issued, 0.35% of construction cost",
            "BASIX certificate — energy and water commitments lodged with CC application",
        ],
        "qualifications": [
            "Hold points — mandatory inspections at footing, frame, waterproofing, final",
            "Occupation Certificate — issued by PC before building occupied",
            "Principal Certifier — independent of builder, cannot be owner",
        ],
        "notifications": [
            "Council — CC or CDC application before any physical work",
            "PC — 48 hours notice before each mandatory inspection hold point",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Environmental Planning and Assessment Act 1979 (NSW) — building approval obligations",
            "No CC = illegal building work — council can issue stop work order and demolition order",
            "BASIX — Building Sustainability Index, mandatory for all NSW residential work >$50,000",
        ],
    },


    # ── RESIDENTIAL — RETAINING WALL ────────────────────────────────────────
    {
        "keywords": ["retaining wall", "retain wall", "retaining structure",
                     "retaining soil", "retaining earth", "residential retaining"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Safety glasses — concrete and masonry work",
            "Safety boots",
            "Gloves — masonry handling",
        ],
        "certs": [
            "Structural engineer — required for retaining walls >1m height in NSW",
        ],
        "permits": [
            "Council DA — retaining walls >1m typically require development approval",
            "Engineer design — certification required before construction above 1m",
            "Drainage — engineered drainage behind wall before backfill placed",
        ],
        "qualifications": [
            "Engineer certification — walls >1m require engineer sign-off",
            "Drainage layer — 300mm gravel drainage blanket mandatory behind wall",
            "Subsoil drain — slotted pipe at base of drainage layer before backfill",
            "Surcharge — no structures within H distance of top of wall without engineer approval",
        ],
        "notifications": [
            "Council — DA or exempt development check before construction",
            "Neighbour — notification where retaining wall is on or near boundary",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 4678 — Earth retaining structures",
            "Exempt development — check council LEP for height thresholds before assuming exempt",
            "Boundary walls — Dividing Fences Act may apply, joint cost obligations",
        ],
    },

    # ── RESIDENTIAL — DECK AND PERGOLA ──────────────────────────────────────
    {
        "keywords": ["deck", "decking", "pergola", "elevated deck", "timber deck",
                     "composite deck", "deck construction", "deck repair", "deck replacement"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Safety boots",
            "Safety glasses — timber cutting",
            "Hearing protection — power tools",
            "Full-body harness — elevated deck construction above 2m",
        ],
        "certs": [
            "Council complying development or DA — decks above exempt development thresholds",
        ],
        "permits": [
            "Council approval — decks >1m above ground or >25m² typically require approval",
            "Engineer design — elevated decks >2m above ground require engineer certification",
            "Principal Certifier — for approved decks, PC inspection at frame and final",
        ],
        "qualifications": [
            "Exempt development check — confirm council LEP thresholds before building",
            "Balustrade — mandatory above 1m, AS 1657 height and load requirements",
            "Ledger connection — structural connection to house must be engineer-certified",
        ],
        "notifications": [
            "Council — DA or CDC application if above exempt thresholds",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 1684 — Residential timber framing — span tables for deck framing",
            "Balustrade — minimum 1m high, max 125mm gap, 1.5kN/m horizontal load",
            "Exempt development — check SEPP (Exempt and Complying Development) 2008",
        ],
    },

    # ── RESIDENTIAL — PLUMBING & DRAINAGE ───────────────────────────────────
    {
        "keywords": ["residential plumbing", "drainage residential", "domestic plumbing",
                     "house plumbing", "bathroom plumbing", "kitchen plumbing",
                     "stormwater residential", "sewer connection residential"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Chemical-resistant gloves — drain cleaning chemical handling",
            "Safety glasses",
            "Nitrile gloves — sewer work",
        ],
        "certs": [
            "Licensed plumber — all residential plumbing and drainage by licensed plumber",
            "Plumbing compliance certificate — issued by plumber after completion",
        ],
        "permits": [
            "Council plumbing approval — required before new drainage or sewer connection",
            "Sydney Water approval — new or modified connection to Sydney Water sewer",
            "Council inspection hold points — at drain before backfill, final completion",
        ],
        "qualifications": [
            "Licensed plumber — check licence on NSW Fair Trading register",
            "AS/NZS 3500 — Plumbing and drainage, compliance mandatory",
            "Compliance certificate — plumber must issue before council final inspection",
        ],
        "notifications": [
            "Council — plumbing application before any new drainage or sewer work",
            "Sydney Water — connection approval before tapping sewer main",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Home Building Act 1989 — plumbing is licensed trade, unlicensed work is offence",
            "AS/NZS 3500 — National plumbing and drainage standard",
            "Compliance certificate — mandatory document, keep for life of building",
        ],
    },

    # ── RESIDENTIAL — DOMESTIC ELECTRICAL ───────────────────────────────────
    {
        "keywords": ["domestic electrical", "residential electrical", "house wiring",
                     "home electrical", "power point installation", "light installation",
                     "switchboard upgrade", "electrical upgrade residential"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.16 — Electrical installation work",
        "hrcw_license_class": "Electrician Licence — NSW Fair Trading A-grade or equivalent",
        "ppe": [
            "Insulated gloves — voltage-rated",
            "Safety glasses",
            "Arc flash PPE — switchboard work",
        ],
        "certs": [
            "Electrician Licence — NSW Fair Trading, mandatory for all electrical work",
            "Certificate of Compliance Electrical Work (CCEW) — issued after completion",
            "Network operator approval — Ausgrid or Endeavour Energy for new metering",
        ],
        "permits": [
            "Electrical approval — council or accredited certifier for major electrical work",
            "Network operator notification — Ausgrid or Endeavour Energy for new connection",
            "CCEW — Certificate of Compliance issued by licensed electrician to homeowner",
        ],
        "qualifications": [
            "Licensed electrician — check licence on NSW Fair Trading register",
            "Isolation — double isolation before any work on existing circuits",
            "Test and tag — all new installations tested before energising",
        ],
        "notifications": [
            "Network operator — Ausgrid 13 13 65 or Endeavour Energy 13 22 29 for new connections",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Home Building Act 1989 — electrical is licensed trade, all work by licensed electrician",
            "CCEW — must be provided to homeowner within 4 days of completing work",
            "DIY electrical — illegal in NSW, insurance void if unlicensed work causes fire",
        ],
    },

    # ── RESIDENTIAL — DOMESTIC GAS ───────────────────────────────────────────
    {
        "keywords": ["domestic gas", "residential gas", "gas appliance", "gas installation",
                     "gas fitting", "gas heater", "gas cooktop", "gas hot water",
                     "lpg residential", "natural gas residential"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Gas detector — calibrated before any gas work",
            "Safety glasses",
        ],
        "certs": [
            "Licensed gasfitter — all gas work by NSW Fair Trading licensed gasfitter",
            "Gas compliance certificate — issued by gasfitter after every job",
        ],
        "permits": [
            "Gas compliance certificate — mandatory before appliance commissioned",
            "Jemena or APA approval — new gas connection to network",
            "Council approval — new gas installation as part of building works",
        ],
        "qualifications": [
            "Licensed gasfitter — check licence on NSW Fair Trading register",
            "Pressure test — all new gas lines pressure tested before commissioning",
            "Ventilation — gas appliances require adequate combustion air and fluing",
        ],
        "notifications": [
            "Jemena — 1800 427 532 for new natural gas connections",
            "APA Group — LPG network connection notification",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Gas Supply Act 1996 (NSW) — unlicensed gas work is offence",
            "Gas compliance certificate — must be provided to homeowner after every job",
            "Gas smell — evacuate, no ignition sources, call 1800 GAS LEAK immediately",
        ],
    },

    # ── RESIDENTIAL — DIVIDING FENCES ────────────────────────────────────────
    {
        "keywords": ["dividing fence", "boundary fence", "neighbour fence",
                     "fence replacement", "dividing fences act", "adjoining fence",
                     "boundary wall residential"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Safety glasses — post driving and concrete work",
            "Safety boots",
            "Gloves",
        ],
        "certs": [],
        "permits": [
            "Fencing notice — served on neighbour before work commences",
            "Council approval — fences above exempt height require DA",
            "NCAT application — if neighbour disputes, apply to NSW Civil and Administrative Tribunal",
        ],
        "qualifications": [
            "Joint cost — neighbours share cost equally under Dividing Fences Act",
            "Fencing notice — must include description, materials, cost estimate",
            "Response period — neighbour has 30 days to respond to fencing notice",
            "Urgent repairs — can proceed without notice if fence is dangerous",
        ],
        "notifications": [
            "Neighbour — fencing notice served minimum 30 days before work",
            "NCAT — application if dispute not resolved within 30 days",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Dividing Fences Act 1991 (NSW) — joint cost obligations",
            "Exempt development — check SEPP for height and material thresholds",
            "Heritage — fences on heritage properties may require Heritage Council approval",
        ],
    },

    # ── CLASS 2 — PRINCIPAL CONTRACTOR OBLIGATIONS ───────────────────────────
    {
        "keywords": ["class 2", "class 2 building", "apartment construction",
                     "multi residential", "multi-residential", "unit construction",
                     "apartment building", "residential flat building",
                     "principal contractor class 2"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Part 6.4 — Principal contractor obligations for construction projects",
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [
            "WHS Management Plan — prepared by principal contractor before work starts",
            "Site Induction — all workers inducted before first day on site",
        ],
        "permits": [
            "WHS Management Plan — documented before physical work commences",
            "Construction Certificate — before any physical work on Class 2 building",
            "Long Service Levy — 0.35% of construction cost paid before CC issued",
            "BASIX certificate — energy and water commitments with CC application",
            "Principal Certifier appointment — before CC issued",
            "Sydney Water building plan approval — before CC for multi-residential",
        ],
        "qualifications": [
            "Principal contractor — nominated before work starts, name displayed on site",
            "WHS induction — site-specific induction for every worker before first entry",
            "Emergency plan — documented and communicated before first day on site",
            "Visitors register — all site visitors signed in before entering",
        ],
        "notifications": [
            "SafeWork NSW — notification of notifiable incidents within 48 hours",
            "Council — construction certificate application before work",
        ],
        "safework_notification": True,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 Part 6.4 — principal contractor must have WHS management plan",
            "Design registration — plant and structures designed for construction must be registered",
            "Notifiable incidents — death, serious injury, dangerous incident reported to SafeWork NSW",
        ],
    },

    # ── CLASS 2 — STRATA AND COMMON PROPERTY ─────────────────────────────────
    {
        "keywords": ["strata", "common property", "owners corporation", "body corporate",
                     "strata plan", "lot owner", "strata by-law", "strata manager",
                     "common area", "strata scheme"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [],
        "permits": [
            "Owners corporation consent — special resolution required for common property works",
            "Strata by-law compliance — check all applicable by-laws before work",
            "Building manager approval — written consent before work in common areas",
        ],
        "qualifications": [
            "Lot boundary — confirm lot vs common property boundary before any work",
            "Strata manager — notify minimum 5 business days before work",
            "Noise — strata by-laws typically restrict work to 8am–5pm weekdays",
            "Rubbish — waste must not be stored in common areas, remove daily",
        ],
        "notifications": [
            "Strata manager — written notification minimum 5 business days before work",
            "Owners corporation — special resolution for any common property alteration",
            "All lot owners — notification where work affects common areas or facilities",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Strata Schemes Management Act 2015 (NSW) — common property obligations",
            "Common property — owners corporation owns and is responsible for common property",
            "By-laws — non-compliance can result in NCAT order to make good",
        ],
    },

    # ── CLASS 2 — FIRE SAFETY DURING CONSTRUCTION ────────────────────────────
    {
        "keywords": ["fire safety construction", "fire plan construction", "fire class 2",
                     "stairwell access", "fire egress", "emergency egress construction",
                     "temporary fire safety", "fire safety building works"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Fire extinguisher — minimum 4.5kg ABE at each level during construction",
        ],
        "certs": [
            "Fire safety plan — documented before work on any occupied or partially occupied building",
        ],
        "permits": [
            "Fire safety plan — before work commences on occupied Class 2 building",
            "Emergency egress — maintained at all times, no stairwell obstructions",
            "Fire warden — designated for each floor before work starts",
            "Temporary fire detection — portable detector in work area where system isolated",
        ],
        "qualifications": [
            "Fire system isolation — only by licensed fire protection contractor",
            "Hot work permit — mandatory before any welding or cutting near fire-sensitive areas",
            "Stairwell — must remain clear and accessible as emergency egress at all times",
            "Sprinkler isolation — SafeWork NSW notification where system isolated >8 hours",
        ],
        "notifications": [
            "NSW Fire and Rescue — notification where fire suppression system isolated >8 hours",
            "Building manager — notification before any fire system isolation",
            "Residents — notification of fire system isolation at least 24 hours before",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "BCA Section C — fire resistance requirements maintained during construction",
            "Stairwell access — never obstruct stairwells with materials or plant",
            "Fire warden — must know evacuation procedures and assembly point",
        ],
    },

    # ── CLASS 2 — FAÇADE AND BALCONY ACCESS ──────────────────────────────────
    {
        "keywords": ["facade", "façade", "external facade", "facade repair",
                     "facade access", "balcony repair", "balcony waterproof",
                     "external wall class 2", "cladding class 2", "spandrel"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.3 — Work at height, risk of fall >2m",
        "hrcw_license_class": None,
        "ppe": [
            "Full-body harness — AS/NZS 1891.1 compliant",
            "Double lanyard — continuous attachment on facade",
            "Helmet with chin strap",
            "Non-slip footwear",
        ],
        "certs": [
            "Anchor point engineering certification — before any anchor used for fall arrest",
            "Structural engineer — façade anchor point design and certification",
        ],
        "permits": [
            "Façade access plan — documented before work commences",
            "Resident exclusion zone — balconies below work area excluded before start",
            "Overhead protection — catch platform or debris netting below work zone",
            "Council hoarding permit — where access scaffold encroaches on footpath",
        ],
        "qualifications": [
            "Rescue plan — specific to façade access, practiced before first use",
            "Resident notification — all balconies below work zone notified and cleared",
            "Debris containment — sheeting or netting on all scaffold faces",
            "Rescue plan — documented before work commences; includes how to retrieve worker from harness/EWP/suspended scaffold if incapacitated",
            "Rescue equipment — on site and ready for immediate deployment before any elevated work starts",
        ],
        "notifications": [
            "Residents — balcony exclusion zone notification minimum 48 hours before",
            "Council — hoarding permit application before footpath encroachment",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Falling objects — debris from Class 2 facade work can fall 20+ metres",
            "Balcony exclusion — residents must not use balconies while overhead work active",
            "Anchor points — must be tested to 6kN minimum, engineer certification required",
            "WHS Reg 2017 r.305 — rescue procedure required before commencing work at height",
            "Suspension trauma — incapacitated worker must be lowered within 15 minutes; harness straps can cause positional asphyxia",
            "Emergency contacts — on-site personnel trained in rescue procedure before elevated work begins",
            "WHS Reg 2017 r.291-303 — fall prevention hierarchy: (1) eliminate, (2) passive edge protection/guardrail, (3) restraint system, (4) fall arrest, (5) administrative",
            "Edge protection first — guardrails preferred over harness where work area permits fixed barriers",
            "Control line — 2m setback from edge, used only when guardrail not practicable",
        ],
    },

    # ── CLASS 2 — WATERPROOFING WET AREAS ────────────────────────────────────
    {
        "keywords": ["wet area waterproofing", "bathroom waterproofing", "laundry waterproofing",
                     "waterproofing class 2", "AS 3740", "membrane bathroom",
                     "shower membrane", "balcony membrane class 2"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Chemical-resistant gloves — membrane product handling",
            "Safety glasses — splash risk",
            "Organic vapour respirator — solvent-based membrane products",
        ],
        "certs": [
            "Licensed waterproofer — AS 3740 compliance requires licensed applicator",
            "Principal Certifier inspection — hold point before tiling over membrane",
        ],
        "permits": [
            "Hold point — PC inspection of membrane before tiles or substrate applied",
            "Manufacturer certification — applicator certified by membrane manufacturer",
        ],
        "qualifications": [
            "AS 3740 compliance — minimum membrane thickness, upstand heights, bond breakers",
            "Flood test — 24-hour flood test of shower before tiling",
            "Upstand — minimum 150mm upstand at shower walls, 75mm at doorways",
        ],
        "notifications": [
            "Principal Certifier — 48 hours notice before waterproofing hold point inspection",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 3740 — Waterproofing of domestic wet areas",
            "Flood test — mandatory before tiling, 24-hour minimum retention",
            "Failed membrane — leading cause of building defects in Class 2 buildings",
        ],
    },

    # ── CLASS 2 — STRUCTURAL ALTERATIONS ────────────────────────────────────
    {
        "keywords": ["structural alteration class 2", "apartment structural",
                     "unit structural", "class 2 structural", "remove wall apartment",
                     "structural modification apartment", "open plan conversion"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.10 — Demolition or alteration of load-bearing structure",
        "hrcw_license_class": None,
        "ppe": [
            "Hard hat — structural work overhead risk",
            "Safety glasses",
            "P2 dust respirator — structural demolition dust",
            "Safety boots",
        ],
        "certs": [
            "Structural engineer — design and certification before any structural alteration",
            "Development consent — DA required for structural alterations in Class 2",
            "Construction Certificate — before physical structural work commences",
        ],
        "permits": [
            "DA approval — structural alterations require development consent",
            "CC — Construction Certificate before physical work on structure",
            "Owners corporation consent — where common property or structure affected",
            "Engineer certification — at each stage of structural work",
        ],
        "qualifications": [
            "Temporary propping — engineer-designed propping before any load-bearing element removed",
            "BCA compliance — structural alterations must maintain BCA compliance",
            "Fire resistance — structural elements must maintain fire resistance rating",
        ],
        "notifications": [
            "Council — DA application before structural alteration",
            "Strata manager — notification before any structural work affecting common property",
            "Neighbours — notification where structural work may cause vibration or noise",
        ],
        "safework_notification": True,
        "epa_license": False,
        "notes": [
            "Class 2 buildings — structural alterations affect multiple lots above and below",
            "Load path — must be maintained or re-engineered, never assumed",
            "Owners corporation — must consent to any work on common property structure",
        ],
    },

    # ── BOTH — LONG SERVICE LEVY ─────────────────────────────────────────────
    {
        "keywords": ["long service levy", "lsl levy", "construction levy",
                     "long service corporation", "levy certificate"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [
            "Long Service Levy receipt — mandatory before Construction Certificate issued",
        ],
        "permits": [
            "Long Service Levy payment — 0.35% of construction cost before CC",
            "Levy exemption — applies for work under $250,000 (check current threshold)",
        ],
        "qualifications": [
            "Online payment — longservice.nsw.gov.au before lodging CC application",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Building and Construction Industry Long Service Payments Act 1986 (NSW)",
            "Current rate — 0.35% of total construction cost",
            "Threshold — check current exemption threshold at longservice.nsw.gov.au",
        ],
    },

    # ── BOTH — BASIX CERTIFICATE ─────────────────────────────────────────────
    {
        "keywords": ["basix", "basix certificate", "energy efficiency residential",
                     "water efficiency residential", "basix commitments",
                     "sustainability residential"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [
            "BASIX certificate — generated at basix.nsw.gov.au before DA or CDC lodgement",
        ],
        "permits": [
            "BASIX certificate — mandatory for all NSW residential work >$50,000",
            "BASIX commitments — all commitments shown on plans and met during construction",
            "PC inspection — certifier verifies BASIX commitments at final inspection",
        ],
        "qualifications": [
            "BASIX commitments — must be shown on construction drawings",
            "Substitution — any BASIX item changed during construction requires BASIX amendment",
        ],
        "notifications": [
            "Council or certifier — BASIX certificate lodged with DA or CDC",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "BASIX — Building Sustainability Index, mandatory for residential >$50,000 in NSW",
            "Targets — thermal comfort, water, energy targets set in certificate",
            "Non-compliance — occupation certificate cannot be issued without BASIX compliance",
        ],
    },

    # ── CIVIL — UNDERPINNING ─────────────────────────────────────────────────
    {
        "keywords": ["underpin", "underpinning", "foundation repair", "foundation strengthening",
                     "pier and beam", "mass concrete underpin", "micropile", "mini pile"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.12 — Excavation adjacent to load-bearing structure",
        "hrcw_license_class": None,
        "ppe": [
            "Hard hat — overhead structural risk",
            "Safety boots — steel-capped",
            "Safety glasses",
        ],
        "certs": [],
        "permits": [
            "Structural engineer design — staged underpinning sequence mandatory",
            "Settlement monitoring plan — before, during and after underpinning",
        ],
        "qualifications": [
            "Structural engineer — on-call during underpinning operations",
            "Staged works — maximum bay width strictly followed per engineer instruction",
            "Propping — temporary support in place before any excavation under footing",
        ],
        "notifications": [
            "Neighbours — notification before underpinning adjacent to boundary",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 2159 — Piling design and installation",
            "Settlement — monitoring points installed before work, readings taken daily",
            "Stop work threshold — defined in engineer's report, must be known by supervisor",
        ],
    },

    # ── CIVIL — ROAD OPENING ─────────────────────────────────────────────────
    {
        "keywords": ["road opening", "road work", "road repair", "pavement repair",
                     "asphalt", "bitumen", "road surface", "carriageway",
                     "road cut", "road opening permit"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "High-visibility vest — Class D (day/night rated) for road work",
            "Hard hat",
            "Steel-capped boots",
        ],
        "certs": [
            "Traffic Control accreditation — TCP and TCS minimum",
            "Roads and Maritime Services road opening permit",
        ],
        "permits": [
            "Road opening permit — Transport for NSW or council before any road cut",
            "Traffic Management Plan — approved before work commences",
            "Lane closure approval — Transport for NSW where state road affected",
        ],
        "qualifications": [
            "Accredited traffic controller — on site whenever traffic affected",
            "Reinstatement — temporary reinstatement within 24 hours of completion",
        ],
        "notifications": [
            "Transport for NSW — 5 business days before state road work",
            "Council — road opening permit application minimum 5 business days",
            "Utility authorities — Dial Before You Dig before any road cutting",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Roads Act 1993 (NSW) — road opening permit mandatory",
            "AS 1742.3 — Traffic control devices for works on roads",
            "Permanent reinstatement — within 30 days of temporary reinstatement",
        ],
    },

    # ── CIVIL — WORKING NEAR LIVE TRAFFIC ────────────────────────────────────
    {
        "keywords": ["live traffic", "near traffic", "traffic management", "lane closure",
                     "road closure", "traffic control", "traffic controller",
                     "traffic management plan", "tmp", "speed reduction"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "High-visibility vest — Class D (day/night rated) minimum",
            "Hard hat",
        ],
        "certs": [
            "Traffic Control accreditation — TCP (Traffic Control Plans) and TCS (Traffic Controller)",
            "First aid — at least one trained first aider on site",
        ],
        "permits": [
            "Traffic Management Plan — approved by relevant authority before work",
            "Speed reduction approval — Transport for NSW or council",
        ],
        "qualifications": [
            "Accredited traffic controller — on site at all times when traffic affected",
            "Exclusion zone — minimum distance from live traffic lanes enforced",
        ],
        "notifications": [
            "Transport for NSW — notification before work on state roads",
            "Emergency services — notification of road closures affecting access",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 1742.3 — Traffic control devices for works on roads",
            "SafeWork NSW — Traffic Management Code of Practice",
            "Exclusion zone — minimum 1m from live traffic lane edge, barriers preferred",
        ],
    },

    # ── UNDERGROUND SERVICES ──────────────────────────────────────────────────
    {
        "keywords": ["underground services", "buried services", "underground pipe",
                     "underground cable", "service locate", "dbyd", "dial before you dig",
                     "potholing", "service excavation", "near services"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Insulating gloves — Class 00 minimum when working within Zone A of electrical services",
            "Hard hat",
            "Safety boots",
        ],
        "certs": [
            "Dial Before You Dig (1100) — mandatory; obtain plans minimum 2 business days before excavation",
        ],
        "permits": [
            "Service locate — private locator engaged for potholing to confirm exact location before mechanical excavation",
            "Asset owner notification — direct notification to relevant asset owner (Ausgrid, Jemena, Sydney Water, Telstra) for work near critical infrastructure",
        ],
        "qualifications": [
            "Zone A (0-500mm from service) — hand digging only, no mechanical plant",
            "Zone B (500mm-1m from service) — mechanical plant allowed with spotter and reduced speed; hand expose service before mechanical work restarts",
            "Zone C (1m-3m from service) — normal mechanical plant with care; locate plans must be on site",
            "Service damage — immediate shutdown, isolate area, call asset owner emergency line and 000 if electrical or gas",
        ],
        "notifications": [
            "Ausgrid — 1300 137 163 — notify before work near electricity infrastructure",
            "Jemena — 1800 GAS LEAK — gas emergency; 132 080 — general enquiries",
            "Sydney Water — 13 20 92 — notify before work near water/sewer mains",
            "Telstra — 1800 810 443 — notify before work near telecommunications infrastructure",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "DBYD plans — indicative only; ±500mm positional accuracy typical; physical confirmation required",
            "Potholing — expose services by hand or vacuum excavation before any mechanical work in Zone B",
            "Unmarked services — stop work if unidentified service encountered; notify asset owners",
            "Electrical cable damage — do not touch cable; treat as live; evacuate area; call 000",
            "Gas line damage — evacuate, no ignition sources, call 000 and Jemena emergency",
            "Water main damage — isolate area, call Sydney Water emergency",
        ],
    },

    # ── CIVIL — OVERHEAD POWERLINES ─────────────────────────────────────────
    {
        "keywords": ["overhead powerline", "overhead line", "overhead cable",
                     "power line", "powerline", "electrical overhead",
                     "hv overhead", "transmission line", "distribution line"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.16 — Work near energised electrical installation",
        "hrcw_license_class": None,
        "ppe": [
            "Non-conductive PPE — where within exclusion zone",
            "High-visibility vest",
            "Hard hat — non-metallic where near energised lines",
        ],
        "certs": [
            "SafeWork NSW notification — before work within 4m of overhead powerlines",
        ],
        "permits": [
            "Network operator approval — Ausgrid or Endeavour Energy before work near lines",
            "Spotter — designated, trained spotter on site at all times near lines",
        ],
        "qualifications": [
            "Exclusion zone — minimum 3m from 11kV line, 6m from 33kV and above",
            "Spotter — must have unobstructed view of plant and lines at all times",
            "Plant height restriction — confirm maximum height before mobilising",
            "Zone A (0-3m from 11kV, 0-6m from 33kV, 0-8m from 132kV+) — no work; de-energisation or insulated barrier required before any entry",
            "Zone B (3-6m from 11kV, 6-10m from 33kV) — work only with spotter maintaining exclusion; no plant in this zone without network operator approval",
            "Zone C (approach zone) — spotter and supervisor awareness required; plant operators briefed on powerline location before commencing",
            "De-energisation request — submitted to network operator (Ausgrid/Essential Energy) minimum 48 hours before work requiring Zone A entry",
        ],
        "notifications": [
            "SafeWork NSW — notification mandatory before work within 4m of powerlines",
            "Network operator (Ausgrid/Endeavour Energy) — contact before work near lines",
        ],
        "safework_notification": True,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 s.163 — overhead powerline exclusion distances",
            "SafeWork NSW Code of Practice: Working Near Overhead Power Lines",
            "De-energisation — request from network operator where practicable",
            "Exclusion distance — 3m to 11kV, 6m to 33kV, 8m to 132kV and above",
            "WHS Reg 2017 r.163-165 — overhead powerline exclusion distances",
            "SafeWork NSW Code of Practice: Working Near Overhead Power Lines",
            "Exclusion distances — 3m from powerlines up to 11kV; 6m from 11kV to 33kV; 8m from 33kV to 132kV; 10m from 132kV and above",
            "Ausgrid contact — 13 13 65 — to arrange de-energisation or insulated barriers for Zone A work",
            "Essential Energy contact — 13 23 91 — for regional NSW network operator notifications",
            "Plant height check — all plant and loads (crane jibs, scaffold, tipping trucks) measured for clearance before entering approach zone",
            "Insulated barriers — only approved by network operator; contractor cannot install their own barriers without network operator approval",
        ],
    },

    # ── CIVIL — GAS SERVICES ─────────────────────────────────────────────────
    {
        "keywords": ["gas line", "gas pipe", "gas service", "gas main", "natural gas",
                     "lpg", "gas detection", "gas leak", "gas exposure"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Gas detector — calibrated LEL/O2/H2S meter before entering work area",
            "P2 respirator with organic vapour cartridge — where gas exposure possible",
        ],
        "certs": [],
        "permits": [
            "Gas line locate — Dial Before You Dig plus direct Jemena/APA notification",
            "Emergency shutdown plan — documented before any work near gas mains",
        ],
        "qualifications": [
            "Gas fitter licence — any work on gas lines requires licensed gas fitter",
            "Emergency response — stop work, evacuate, call 000 if gas smell detected",
        ],
        "notifications": [
            "Jemena/APA Group — direct notification before work near gas mains",
            "Dial Before You Dig — 2 business days before ground penetration",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Gas lines — no mechanical excavation within 500mm of confirmed gas main",
            "Gas smell — immediate evacuation, no ignition sources, call 000 and 1800 GAS LEAK",
            "Licensed gas fitter — any connection, disconnection or repair to gas line",
        ],
    },

    # ── CIVIL — CRANES & LIFTING ─────────────────────────────────────────────
    {
        "keywords": ["crane", "mobile crane", "tower crane", "franna", "all terrain crane",
                     "pick and carry", "crane lift", "critical lift", "heavy lift"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.8 — Work involving use of explosives or crane",
        "hrcw_license_class": "Crane Licence — C6 (mobile crane), C2 (tower crane), or relevant class",
        "ppe": [
            "Hard hat — mandatory in crane exclusion zone",
            "High-visibility vest",
            "Safety boots",
        ],
        "certs": [
            "Crane operator licence — C6 mobile crane or C2 tower crane (SafeWork NSW)",
            "Dogman licence — DG class (SafeWork NSW)",
            "Rigger licence — RB basic, RI intermediate, or RA advanced (SafeWork NSW)",
        ],
        "permits": [
            "Lift study — documented before every critical lift",
            "Ground bearing assessment — engineer certification before mobile crane setup",
            "Crane exclusion zone — established and enforced before lift commences",
            "Outrigger mat design — engineer-certified where soft or uncertain ground",
            "Lift study — documented for any lift where load exceeds 75% SWL, multi-crane lift, or lift over energised services/public areas",
            "Crane set-up permit — ground bearing capacity confirmed before outriggers deployed",
        ],
        "qualifications": [
            "Lift supervisor — responsible person designated for every lift",
            "Wind speed limit — maximum defined in lift study, anemometer on site",
            "Pre-lift inspection — daily pre-use check logged before first lift",
            "Exclusion zone — established and enforced for the full swing radius plus load overhang; nobody under suspended load at any time",
            "Outrigger pads — design verified for ground bearing capacity by competent person before lift",
            "Communication — dogman/rigger on continuous two-way communication with crane operator during lift",
        ],
        "notifications": [
            "Council — notification where crane oversails public land or adjacent property",
            "Airspace authority — CASA notification where crane exceeds 110m AGL",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 2550 — Cranes, hoists and winches — safe use",
            "Critical lift — any lift over 75% capacity, tandem lift, or near powerlines",
            "Exclusion zone — minimum 1.5x load radius, enforced during all lifts",
            "Dogman — must maintain visual contact with load at all times",
            "WHS Reg 2017 r.211-240 — plant with potential to cause harm; registration, inspection, and operator licence obligations",
            "Critical lift threshold — any lift over 75% SWL or involving multiple cranes requires formal lift study signed by engineer",
            "Wind limits — all crane operations suspended in sustained winds exceeding manufacturer's rated limit (typically 48-72km/h depending on crane and jib configuration)",
            "Tagline required — unguided loads create uncontrolled swing hazard; taglines used on all loads except where impracticable",
            "Load chart — operator must verify SWL for the specific radius and jib configuration before lift",
        ],
    },

    # ── PRECAST AND TILT-UP ───────────────────────────────────────────────────
    {
        "keywords": ["precast", "tilt-up", "tilt up", "precast panel",
                     "precast concrete", "tilt panel", "precast beam",
                     "precast column", "precast wall", "concrete panel",
                     "panel erection", "panel installation"],
        "hrcw": True,
        "hrcw_category": "Schedule 3 cl.5 — Tilt-up or precast concrete",
        "hrcw_license_class": "Crane Licence — C6 or C2 class for crane used in erection; DG/RI for dogman/rigger",
        "ppe": [
            "Hard hat — mandatory in precast exclusion zone",
            "Hi-vis vest",
            "Safety boots — steel capped",
            "Full body harness — when working at height attaching or releasing lifting inserts",
        ],
        "certs": [
            "Dogman licence — DG class (SafeWork NSW) for all persons directing panel lifts",
            "Rigger licence — RB minimum (SafeWork NSW) for rigging precast elements",
            "Crane operator licence — class appropriate to crane used",
        ],
        "permits": [
            "Lift study — engineer-prepared for each panel type and crane configuration",
            "Bracing design — engineer-certified bracing layout required before first panel erected",
            "Engineer approval — written approval from structural engineer required before any temporary bracing removed",
            "Written approval from project design engineer or independent qualified engineer — required before removing temporary bracing from precast elements",
        ],
        "qualifications": [
            "Erection sequence — engineer-certified sequence; no deviation without engineer sign-off",
            "Brace footings — must achieve specified concrete strength before bracing is loaded; verified by engineer",
            "Panel exclusion zone — full panel height plus 20% maintained around erection area; no personnel within zone while panel is suspended",
            "Lifting insert testing — pull-out capacity tested to AS 3850 before panel is lifted",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 Schedule 3 cl.5 — tilt-up and precast is notifiable HRCW",
            "AS 3850 — Tilt-up concrete and precast concrete elements — lifting insert requirements",
            "Shop drawings — must be approved by structural engineer and on site before erection commences",
            "Birth certificates — required for each precast element; records mix design, strength test results, and lifting insert certification",
            "Concrete strength — must reach design MPa (verified by compressive strength test report) before any element is lifted",
            "Temporary bracing — remains in place until engineer certifies permanent structure can take load",
            "Tag lines — required on all panels to control rotation during lift",
            "Wind speed — erection suspended in sustained winds exceeding manufacturer/engineer limits for the specific panel size",
            "Adjacent panel bracing — brace second panel before unhooking crane from first panel",
        ],
    },

    # ── CIVIL — RIGGING & DOGGING ────────────────────────────────────────────
    {
        "keywords": ["rigging", "dogging", "sling", "shackle", "lifting gear",
                     "load shifting", "rigging gear", "chain block", "come-along",
                     "below-the-hook", "spreader bar"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": "Dogman Licence — DG class (SafeWork NSW)",
        "ppe": [
            "Hard hat — mandatory during rigging and lifting operations",
            "Gloves — cut-resistant, rigging gear handling",
            "Safety boots",
            "High-visibility vest",
        ],
        "certs": [
            "Dogman licence — DG class required for directing crane with load",
            "Rigger licence — RB/RI/RA class required for rigging work",
            "Rigging gear inspection — pre-use inspection logged before each use",
        ],
        "permits": [],
        "qualifications": [
            "Rigging register — all lifting gear tagged and within inspection period",
            "SWL marking — every sling, shackle and hook must show SWL",
            "Discard criteria — rigging gear with cuts, kinks or corrosion must be removed",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 3569 — Steel wire ropes",
            "AS 1353 — Flat webbing slings",
            "AS 4497 — Round slings",
            "SWL — never exceed Safe Working Load, apply derated values for angled slings",
        ],
    },

    # ── CIVIL — ACID SULFATE SOILS ───────────────────────────────────────────
    {
        "keywords": ["acid sulfate", "acid sulphate", "ass soil", "acid sulfate soil",
                     "coastal soil", "tidal flat", "estuarine soil", "pyritic soil"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Chemical-resistant boots — acid soil contact",
            "Chemical-resistant gloves",
            "Safety glasses",
        ],
        "certs": [
            "Acid sulfate soil assessment — qualified consultant before excavation",
        ],
        "permits": [
            "Acid sulfate soil management plan — approved by council before work",
            "EPA approval — where acid sulfate soil disturbance exceeds thresholds",
        ],
        "qualifications": [
            "Lime treatment — neutralisation of excavated ASS before disposal",
            "pH monitoring — continuous monitoring during excavation and treatment",
        ],
        "notifications": [
            "Council — ASS management plan submission before work in ASS area",
            "NSW EPA — notification where ASS disturbance may affect waterway",
        ],
        "safework_notification": False,
        "epa_license": True,
        "notes": [
            "Environmental Planning and Assessment Act 1979 — ASS triggers in coastal areas",
            "ASS maps — check SixMaps before any coastal excavation",
            "pH — excavated ASS with pH <4 must be treated before disposal or reuse",
        ],
    },

    # ── CIVIL — FILL PLACEMENT ───────────────────────────────────────────────
    {
        "keywords": ["fill placement", "compaction", "engineered fill", "bulk fill",
                     "controlled fill", "subgrade preparation", "embankment",
                     "fill material", "compaction testing", "cbr test"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Hard hat — plant operation zone",
            "High-visibility vest",
            "Steel-capped boots",
            "P2 dust respirator — fill placement dust generation",
        ],
        "certs": [
            "NATA-accredited laboratory — compaction testing required",
        ],
        "permits": [
            "Fill material certification — Virgin Excavated Natural Material (VENM) or equivalent",
            "Contamination clearance — fill material tested before placement",
        ],
        "qualifications": [
            "Compaction testing — minimum density ratio per engineer specification",
            "Lift thickness — maximum 300mm compacted layers unless specified otherwise",
            "Hold point — engineer sign-off on each layer before next lift placed",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 3798 — Guidelines on earthworks for commercial and residential developments",
            "VENM — Virgin Excavated Natural Material, no contamination, EPA definition",
            "Contaminated fill — illegal to place, EPA penalty applies",
        ],
    },

    # ── CIVIL — EROSION & SEDIMENT CONTROL ──────────────────────────────────
    {
        "keywords": ["erosion", "sediment", "erosion control", "sediment control",
                     "cescp", "silt fence", "sediment fence", "sediment basin",
                     "turbid water", "soil disturbance", "bare soil"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [
            "Certified Erosion and Sediment Control Lead (CESCL) — for large sites",
        ],
        "permits": [
            "Certified Erosion and Sediment Control Plan (CESCP) — before any ground disturbance",
            "Council approval — CESCP submitted with DA or construction certificate",
        ],
        "qualifications": [
            "Sediment fence — installed before any ground disturbance commences",
            "Stabilised entry/exit — installed before trucks leave site",
            "Inspection — after every rainfall event, defects repaired same day",
        ],
        "notifications": [
            "Council — CESCP submission with development application",
            "NSW EPA — notification where sediment discharge reaches waterway",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Managing Urban Stormwater — Soils and Construction (Blue Book) NSW",
            "Sediment fence — installed on downslope side before work begins",
            "Stabilised entry — 20m minimum length, 50mm crushed rock on geotextile",
        ],
    },


    # ── ROOFING — METAL ROOF FALL PREVENTION ────────────────────────────────
    {
        "keywords": ["metal roof", "metal roofing", "corrugated roof", "colorbond roof",
                     "zincalume roof", "roof sheet", "roofing work", "roof installation",
                     "roof replacement", "roof repair", "commercial roof", "industrial roof"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.3 — Work at height with risk of fall >2m",
        "hrcw_license_class": None,
        "ppe": [
            "Full-body harness — AS/NZS 1891.1 compliant, fitted before roof access",
            "Energy-absorbing lanyard — double lanyard for continuous attachment",
            "Helmet with chin strap — AS/NZS 1801",
            "Non-slip footwear — soft-soled boots, no hard soles on metal roof",
            "UV-rated clothing — long sleeves, metal roof radiant heat in summer",
            "High-visibility vest",
        ],
        "certs": [
            "Working at heights — verified current competency (RIIOHS204E or equivalent per current RII Training Package)",
            "Roof anchor installation — engineer-certified anchor points before use",
        ],
        "permits": [
            "Working at heights permit — signed before each roof access",
            "Roof safety plan — documented fall prevention hierarchy before work starts",
            "Edge protection — installed before workers access roof perimeter",
        ],
        "qualifications": [
            "Rescue plan — documented for roof work, reviewed before each shift",
            "Competent person — daily pre-use inspection of all fall arrest equipment",
            "Anchor point certification — engineer or manufacturer certification required",
            "Rescue plan — documented before work commences; includes how to retrieve worker from harness/EWP/suspended scaffold if incapacitated",
            "Rescue equipment — on site and ready for immediate deployment before any elevated work starts",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 Part 4.4 — fall prevention hierarchy applies to all fall risk",
            "SafeWork NSW Code of Practice: Managing the Risk of Falls at Workplaces",
            "Metal roofing — purlin-to-purlin fall risk even with harness if lanyard too long",
            "Roof perimeter — edge protection or safety mesh mandatory before work begins",
            "WHS Reg 2017 r.305 — rescue procedure required before commencing work at height",
            "Suspension trauma — incapacitated worker must be lowered within 15 minutes; harness straps can cause positional asphyxia",
            "Emergency contacts — on-site personnel trained in rescue procedure before elevated work begins",
            "WHS Reg 2017 r.291-303 — fall prevention hierarchy: (1) eliminate, (2) passive edge protection/guardrail, (3) restraint system, (4) fall arrest, (5) administrative",
            "Edge protection first — guardrails preferred over harness where work area permits fixed barriers",
            "Control line — 2m setback from edge, used only when guardrail not practicable",
        ],
    },

    # ── ROOFING — FRAGILE ROOF SURFACES ─────────────────────────────────────
    {
        "keywords": ["fragile roof", "fibreglass panel", "translucent panel", "skylight",
                     "roof light", "corroded sheet", "corroded roof", "fragile surface",
                     "asbestos roof", "super six roof", "fibro roof"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.3 — Work at height, fragile surface fall risk",
        "hrcw_license_class": None,
        "ppe": [
            "Full-body harness — mandatory, fragile surface fall-through is fatal",
            "Double lanyard — continuous attachment, no unclipped movement on fragile roof",
        ],
        "certs": [
            "Fragile surface assessment — competent person assessment before access",
        ],
        "permits": [
            "Fragile roof work permit — specific permit before any access to fragile surface",
            "Roof boards or crawl boards — load-spreading boards over fragile panels",
            "Skylight covers — fixed, load-rated covers over all skylights before access",
        ],
        "qualifications": [
            "No direct foot traffic — crawl boards or roof ladders mandatory on fragile panels",
            "Skylight survey — all skylights mapped and marked before roof access",
            "Safety mesh — installed below fragile panels before work commences",
            "Rescue plan — documented before work commences; includes how to retrieve worker from harness/EWP/suspended scaffold if incapacitated",
            "Rescue equipment — on site and ready for immediate deployment before any elevated work starts",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "SafeWork NSW — fragile roof fall-throughs are frequently fatal",
            "Skylight covers — must be load-rated to 250kg minimum",
            "Fibreglass panels — may appear solid but carry no load, treat as open hole",
            "Corroded sheets — corrosion reduces load capacity, treat as fragile",
            "WHS Reg 2017 r.305 — rescue procedure required before commencing work at height",
            "Suspension trauma — incapacitated worker must be lowered within 15 minutes; harness straps can cause positional asphyxia",
            "Emergency contacts — on-site personnel trained in rescue procedure before elevated work begins",
            "WHS Reg 2017 r.291-303 — fall prevention hierarchy: (1) eliminate, (2) passive edge protection/guardrail, (3) restraint system, (4) fall arrest, (5) administrative",
            "Edge protection first — guardrails preferred over harness where work area permits fixed barriers",
            "Control line — 2m setback from edge, used only when guardrail not practicable",
        ],
    },

    # ── ROOFING — STRUCTURAL ASSESSMENT ─────────────────────────────────────
    {
        "keywords": ["roof structure", "roof purlin", "roof truss", "roof loading",
                     "roof capacity", "existing roof structure", "purlin condition",
                     "truss condition", "roof dead load", "roof live load"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [],
        "permits": [
            "Structural engineer assessment — roof load capacity before any plant or materials on roof",
            "Anchor pull-out test — before any anchor point is used for fall arrest",
        ],
        "qualifications": [
            "Structural engineer — written advice on safe working load for roof zone",
            "Purlin inspection — visual and physical inspection before personnel access",
            "Materials staging — maximum distributed load confirmed before staging on roof",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 4600 — Cold-formed steel structures — purlin capacity assessment",
            "Anchor pull-out — test to 6kN minimum before use for fall arrest",
            "Old roofs — purlins may be corroded, load capacity unknown without assessment",
        ],
    },

    # ── ROOFING — THERMAL & HEAT STRESS ─────────────────────────────────────
    {
        "keywords": ["hot roof", "heat stress", "summer roofing", "radiant heat",
                     "metal surface heat", "roof temperature", "heat illness",
                     "heat exhaustion", "heat stroke", "thermal risk"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "UV-rated long-sleeve shirt — minimum UPF 50",
            "Broad-brim hat or helmet with brim",
            "Sunscreen SPF 50+ — reapplied every 2 hours",
            "Insulated gloves — metal surface contact burns above 50°C",
        ],
        "certs": [],
        "permits": [
            "Heat management plan — documented when ambient temperature exceeds 35°C",
            "Work suspension criteria — temperature and humidity threshold defined before work",
        ],
        "qualifications": [
            "Acclimatisation — new workers on hot roofs require 5-day acclimatisation period",
            "Hydration — minimum 250ml water every 20 minutes in heat",
            "Buddy system — workers monitored for heat illness symptoms at all times",
            "Cool rest area — shaded rest area within 2 minutes of work area",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "SafeWork NSW — Heat stress in the workplace guidance",
            "Metal roof surface — can exceed 80°C in summer, burns on contact",
            "Heat stroke — medical emergency, call 000 immediately if suspected",
            "Work hours — consider early morning start to avoid peak heat 11am–3pm",
        ],
    },

    # ── ROOFING — WIND LOADING ───────────────────────────────────────────────
    {
        "keywords": ["wind", "wind loading", "wind speed", "wind risk", "high wind",
                     "wind suspension", "wind criteria", "roof wind", "exposed roof"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [],
        "permits": [
            "Wind speed limit — maximum defined in SWMS before work commences",
            "Anemometer — on site for any elevated or exposed roof work",
        ],
        "qualifications": [
            "Work suspension — mandatory when wind exceeds 40 km/h for roof work",
            "Loose materials — secured or removed before forecast wind events",
            "Sheet handling — two-person minimum for any sheet over 2m in wind",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS/NZS 1170.2 — Wind actions — design wind speeds for NSW regions",
            "40 km/h threshold — general roof work suspension trigger",
            "Roof sheets — act as sails, extreme uplift and handling risk in wind",
        ],
    },

    # ── ROOFING — CONTAMINATED RUNOFF ────────────────────────────────────────
    {
        "keywords": ["roof runoff", "roof coating removal", "old roof paint",
                     "roof paint", "roof coating", "zinc runoff", "lead roof",
                     "roof wash", "roof cleaning", "roof contaminant"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Chemical-resistant gloves — roof coating chemical contact",
            "Safety glasses — full seal during chemical application or removal",
            "P2 respirator — where dust or fume generation during coating removal",
        ],
        "certs": [],
        "permits": [
            "Stormwater containment plan — before any roof coating removal or washing",
            "EPA approval — where runoff contains lead, zinc or other regulated contaminants",
        ],
        "qualifications": [
            "Containment — bunding or collection system before water-based cleaning",
            "Waste water — collected and disposed via licensed facility, not to stormwater",
        ],
        "notifications": [
            "NSW EPA — notification where contaminated runoff may reach waterway",
        ],
        "safework_notification": False,
        "epa_license": True,
        "notes": [
            "Zinc — naturally present in Zincalume, toxic to aquatic life in stormwater",
            "Lead paint — any water-based cleaning of lead-coated roof must be contained",
            "Protection of the Environment Operations Act 1997 — stormwater pollution offence",
        ],
    },

    # ── ROOFING — ZINCALUME / COLORBOND MATERIALS ────────────────────────────
    {
        "keywords": ["zincalume", "colorbond", "zinc coating", "galvanised",
                     "galvanized", "zinc fume", "welding galvanised", "cutting colorbond",
                     "cutting zincalume", "zinc oxide fume"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "P2 respirator with organic vapour cartridge — zinc fume during cutting or welding",
            "Safety glasses — full seal during cutting",
            "Welding helmet — full shade during any welding on zinc-coated material",
            "Gloves — cut-resistant for sheet metal handling",
        ],
        "certs": [
            "SDS review — Zincalume and Colorbond SDS reviewed before work",
        ],
        "permits": [
            "Ventilation plan — no welding or cutting of zinc-coated material in enclosed space without extraction",
        ],
        "qualifications": [],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Zinc oxide fume — causes metal fume fever, symptoms within 4–12 hours",
            "No open flame cutting — Zincalume and Colorbond must not be oxy-cut",
            "Plasma or guillotine preferred — minimises fume generation",
            "SDS — BlueScope Steel SDS for Zincalume and Colorbond available at bluescopesteel.com.au",
        ],
    },

    # ── ROOFING — OLD CORRUGATED IRON ────────────────────────────────────────
    {
        "keywords": ["old corrugated iron", "oci", "corrugated iron", "old iron roof",
                     "asbestos backed", "asbestos insulation", "old roof removal",
                     "demolish old roof", "strip old roof"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "P2 half-face respirator — lead paint and possible asbestos dust",
            "Disposable coveralls — taped at wrists and ankles",
            "Nitrile gloves — double layer",
            "Safety glasses — full seal",
            "Full-body harness — fragile and corroded surfaces, fall-through risk",
        ],
        "certs": [
            "Hazardous materials survey — before removal of any old corrugated roof",
            "Lead Assessor Class A — where lead paint confirmed or suspected",
            "Asbestos inspection — where asbestos-backed insulation suspected",
        ],
        "permits": [
            "Hazmat removal plan — documented before old roof removal commences",
        ],
        "qualifications": [
            "Asbestos check — insulation blanket behind old iron often chrysotile asbestos",
            "Lead paint check — most pre-1970 roofs painted with lead-based paint",
        ],
        "notifications": [
            "NSW EPA — notification where asbestos or lead removal exceeds thresholds",
        ],
        "safework_notification": False,
        "epa_license": True,
        "notes": [
            "Pre-1980 corrugated iron — assume lead paint until tested",
            "Asbestos insulation blanket — common behind corrugated iron in industrial buildings pre-1980",
            "Sample before disturb — always test before removal, do not assume clean",
        ],
    },

    # ── ROOFING — ROOF ACCESS LADDER ─────────────────────────────────────────
    {
        "keywords": ["roof ladder", "roof access", "ladder access", "access ladder",
                     "fixed ladder", "temporary ladder", "lean ladder", "extension ladder"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Three points of contact — mandatory on all ladder access",
            "Full-body harness — where ladder exceeds 3m height",
        ],
        "certs": [
            "Ladder safety training — pre-use inspection and safe use training",
        ],
        "permits": [],
        "qualifications": [
            "Ladder secured — tied or footed at base before use",
            "Ladder angle — 1:4 ratio (75 degrees) for lean-to ladders",
            "Ladder overhang — minimum 1m above landing point at top",
            "Tools and materials — use tool belt or hoist, never carry on ladder",
            "Pre-use inspection — check rungs, feet and stiles before every use",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS/NZS 1892.1 — Portable ladders — aluminium",
            "WHS Reg 2017 Part 4.4 — ladder use is last resort in fall prevention hierarchy",
            "Fixed roof ladders — must comply with AS 1657 fixed platforms and walkways",
        ],
    },

    # ── ROOFING — SOLAR PANELS ───────────────────────────────────────────────
    {
        "keywords": ["solar panel", "solar pv", "photovoltaic", "solar array",
                     "solar installation", "solar roof", "pv system",
                     "solar inverter", "dc isolator", "solar wiring"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.16 — Work involving energised electrical installation",
        "hrcw_license_class": "Electrician Licence (NSW Fair Trading) — A-grade, solar endorsement preferred",
        "ppe": [
            "Insulated gloves — voltage-rated for DC circuits",
            "Arc flash PPE — where working near energised DC bus",
            "Safety glasses",
            "Full-body harness — roof access",
        ],
        "certs": [
            "Electrician Licence — NSW Fair Trading, solar endorsement",
            "Clean Energy Council accreditation — installer and designer accreditation",
            "DC isolation — solar panels generate DC even with AC isolator off",
        ],
        "permits": [
            "Electrical isolation permit — AC side isolated before roof work near panels",
            "Note: DC side cannot be fully isolated in daylight — treat as live",
        ],
        "qualifications": [
            "DC live work — assume panels are live at all times in daylight",
            "Shade or cover — panels covered where personnel work near DC conductors",
            "Emergency shutdown — AC main switch location known before work starts",
        ],
        "notifications": [
            "Network operator — notification before grid-connected system work",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Solar DC circuits — cannot be switched off by AC isolator, live in daylight",
            "Voltage — residential systems 600V DC, commercial up to 1500V DC",
            "Clean Energy Council — accreditation required for grid-connected PV work",
            "AS/NZS 5033 — Installation and safety requirements for PV arrays",
        ],
    },

    # ── ROOFING — LIGHTNING RISK ─────────────────────────────────────────────
    {
        "keywords": ["lightning", "thunderstorm", "electrical storm", "storm risk",
                     "weather risk", "exposed roof storm", "lightning protection"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [],
        "permits": [
            "Weather monitoring — BOM forecast checked before each roof shift",
            "Work suspension criteria — thunderstorm within 10km triggers immediate roof evacuation",
        ],
        "qualifications": [
            "Evacuation procedure — route from roof to shelter defined before work starts",
            "30-30 rule — if thunder within 30 seconds of lightning, evacuate; wait 30 minutes after last strike",
            "Earthing — metal roof may be earthed via lightning protection system, do not assume safe",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Metal roofs — highly conductive, elevated lightning strike risk",
            "BOM — check Bureau of Meteorology forecast and lightning tracker before start",
            "Lightning tracker — lightningmaps.org or BOM lightning app recommended",
        ],
    },

    # ── RETAIL FITOUT — APPROVALS & CHANGE OF USE ────────────────────────────
    {
        "keywords": ["retail fitout", "shop fitout", "tenancy fitout", "retail fit out",
                     "shop fit out", "tenancy fit out", "retail construction",
                     "fitout works", "fit out works", "change of use retail"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [
            "Principal Certifier appointment — before Construction Certificate issued",
            "BCA compliance — Parts D, E, F assessed before fitout design finalised",
        ],
        "permits": [
            "Development Application or CDC — change of use approval before any work",
            "Construction Certificate — before physical fitout work commences",
            "Long Service Levy — 0.35% of construction cost before CC",
            "Landlord fitout approval — landlord written approval before any work on base building",
            "Centre management approval — shopping centre fitout guide compliance before start",
        ],
        "qualifications": [
            "Landlord fitout guide — read and signed off before design commences",
            "Base building protection — base building finishes protected before work starts",
            "Hoarding — tenancy hoarding installed before any strip out or fitout work",
            "Working hours — centre management approved working hours, typically after trade",
        ],
        "notifications": [
            "Council — DA or CDC application before change of use",
            "Centre management — fitout application lodged minimum 20 business days before start",
            "Landlord — written notification before any work on base building services",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Environmental Planning and Assessment Act 1979 (NSW) — change of use requires DA",
            "BCA — Building Code of Australia compliance mandatory for all fitout work",
            "Landlord fitout guide — typically specifies approved contractors, materials, hours",
        ],
    },

    # ── RETAIL FITOUT — FIRE SAFETY ──────────────────────────────────────────
    {
        "keywords": ["retail fire safety", "fire system fitout", "sprinkler fitout",
                     "fire panel fitout", "fhr panel", "fire hydrant fitout",
                     "exit light fitout", "emergency light fitout", "fire compliance fitout",
                     "essential services fitout", "fire sprinkler", "fire detection fitout",
                     "emergency lighting fitout", "exit sign fitout", "fire safety schedule"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Hard hat — ceiling work during fire system installation",
            "Safety glasses",
        ],
        "certs": [
            "Fire engineer — fire engineering assessment where performance solution used",
            "Licensed fire protection contractor — all fire system work by licensed installer",
            "AS 2293 — emergency lighting and exit signs design and installation",
            "AS 1670.1 — fire detection and alarm systems design",
        ],
        "permits": [
            "Fire system modification approval — base building fire contractor approval",
            "Council fire safety — fire safety schedule submitted with CC",
            "Fire safety certificate — issued by certifier after fire system commissioning",
            "Hot work permit — mandatory before any soldering or welding near fire systems",
        ],
        "qualifications": [
            "Sprinkler modification — licensed fire sprinkler contractor only",
            "Base building FIP tie-in — base building fire contractor must do FIP connections",
            "Exit signs — AS 2293.1, illuminated, on emergency power, at every exit",
            "Emergency lighting — minimum 0.2 lux at floor level, 90-minute battery backup",
            "Occupant notification — base building fire system isolated, occupants notified",
        ],
        "notifications": [
            "Base building fire contractor — notification before any fire system work",
            "NSW Fire and Rescue — notification where fire suppression isolated >8 hours",
            "Centre management — fire system isolation notification minimum 24 hours before",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "BCA Section E — fire safety requirements for retail tenancies",
            "Essential services — exit lighting, emergency lighting, sprinklers, FHR — all require annual certification",
            "Fire safety certificate — must be issued before occupation certificate",
        ],
    },

    # ── RETAIL FITOUT — ACCESSIBILITY ────────────────────────────────────────
    {
        "keywords": ["dda fitout", "accessibility fitout", "disabled access fitout",
                     "wheelchair access", "accessible toilet", "ramp fitout",
                     "AS 1428", "accessibility compliance", "disability access retail"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [
            "Accessibility consultant — DDA compliance review before design finalised",
        ],
        "permits": [
            "CC accessibility compliance — AS 1428.1 compliance confirmed in CC application",
            "Access path of travel — accessible path from street to tenancy confirmed",
        ],
        "qualifications": [
            "Ramp gradient — maximum 1:14 for ramps, 1:8 for kerb ramps",
            "Doorway clear width — minimum 850mm clear opening",
            "Accessible toilet — AS 1428.1 dimensions, grabrails, turning circle",
            "Tactile indicators — at all steps, ramps and hazard locations",
            "Contrast — tonal contrast at all steps, door frames and hazards",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Disability Discrimination Act 1992 — accessible premises mandatory",
            "AS 1428.1 — Design for access and mobility",
            "BCA Part D3 — access and egress requirements for retail premises",
            "Unjustifiable hardship — only exemption from DDA compliance, high bar to meet",
        ],
    },

    # ── RETAIL FITOUT — FOOD PREMISES ────────────────────────────────────────
    {
        "keywords": ["food premises", "commercial kitchen", "cafe fitout", "restaurant fitout",
                     "food business", "food preparation area", "food retail",
                     "canteen fitout", "bakery fitout", "food court fitout"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Chemical-resistant gloves — commercial kitchen cleaning chemical handling",
            "Safety glasses — chemical splash risk",
            "Non-slip footwear — wet kitchen floors",
        ],
        "certs": [
            "Council food premises approval — before food business commences operation",
            "Food Standards Code AS 4674 — commercial kitchen construction standard",
            "Council health inspection — pre-opening inspection by council environmental health officer",
        ],
        "permits": [
            "Council food business registration — before any food is prepared or sold",
            "Food premises fitout approval — council approval of kitchen plans before construction",
            "Grease trap — council approval and licensed plumber installation",
            "Mechanical exhaust — commercial kitchen canopy and exhaust system approval",
            "Pest management plan — documented before council inspection",
        ],
        "qualifications": [
            "Wall and floor finishes — smooth, impervious, washable surfaces mandatory",
            "Floor drainage — graded to floor waste at minimum 1:60 fall",
            "Hand wash basin — dedicated hand wash basin in every food preparation area",
            "Temperature control — cold storage and hot holding equipment validated",
            "Clearances — minimum 500mm clearance behind cooking equipment for cleaning",
        ],
        "notifications": [
            "Council — food premises fitout plans lodged minimum 20 business days before construction",
            "Council environmental health — pre-opening inspection notification",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Australia New Zealand Food Standards Code — Standard 3.2.3 food premises requirements",
            "AS 4674 — Design, construction and fit-out of food premises",
            "Council inspection — mandatory before food business opens, cannot trade without approval",
            "Food safety supervisor — certified food safety supervisor must be nominated before opening",
        ],
    },

    # ── RETAIL FITOUT — GREASE TRAP ──────────────────────────────────────────
    {
        "keywords": ["grease trap", "grease interceptor", "fat trap", "grease arrestor",
                     "kitchen drainage", "commercial kitchen drain", "trade waste kitchen"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Chemical-resistant gloves — grease trap cleaning",
            "P2 respirator — H2S exposure during grease trap work",
            "Safety glasses — splash risk",
            "Nitrile gloves — biological contamination",
        ],
        "certs": [
            "Licensed plumber — grease trap installation by licensed plumber",
            "Sydney Water trade waste agreement — grease trap required before approval",
            "Council approval — grease trap sizing and location approved before installation",
        ],
        "permits": [
            "Sydney Water trade waste agreement — mandatory for commercial kitchen",
            "Grease trap sizing — Sydney Water design requirements before installation",
            "Council plumbing approval — grease trap installation as part of hydraulic approval",
        ],
        "qualifications": [
            "Grease trap sizing — sized for peak meal period flow rate per Sydney Water",
            "Inspection port — accessible inspection port required for maintenance",
            "Pump-out contract — licensed grease trap pump-out contractor engaged before opening",
            "Pump-out frequency — minimum quarterly, Sydney Water trade waste conditions",
        ],
        "notifications": [
            "Sydney Water — trade waste agreement application minimum 20 business days before",
            "Council — grease trap as part of food premises fitout approval",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Sydney Water trade waste — commercial kitchen cannot trade without agreement",
            "Grease trap — prevents fats, oils and grease entering sewer system",
            "Pump-out records — must be kept and available for Sydney Water inspection",
        ],
    },

    # ── RETAIL FITOUT — BASE BUILDING SERVICES INTERFACE ────────────────────
    {
        "keywords": ["base building services", "base building fitout", "landlord services",
                     "tenancy services", "building services connection", "hvac connection fitout",
                     "electrical connection fitout", "hydraulic connection fitout",
                     "base building electrical", "base building hvac"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [
            "Base building as-installed drawings — obtained from landlord before design",
            "Services engineer — mechanical, electrical, hydraulic design by registered engineer",
        ],
        "permits": [
            "Landlord services approval — all base building service connections approved in writing",
            "Electrical metering — separate tenant meter, network operator approval",
            "Base building fire contractor — FIP tie-in by base building fire contractor only",
            "HVAC balancing — air balance test and report before occupation",
        ],
        "qualifications": [
            "Shutdown coordination — base building service shutdowns coordinated with centre management",
            "Surge protection — tenant electrical install must not affect base building power quality",
            "As-installed drawings — all services documented as-installed before handover",
            "Commissioning — all base building service connections commissioned and tested",
        ],
        "notifications": [
            "Landlord — minimum 5 business days notice before any base building service shutdown",
            "Centre management — shutdown notification to affected tenants minimum 48 hours",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Landlord fitout guide — base building service connection specifications mandatory",
            "Metering — all tenant services separately metered, landlord requirement",
            "As-installed — landlord typically requires as-installed drawings within 30 days of completion",
        ],
    },

    # ── RETAIL FITOUT — HVAC & MECHANICAL ───────────────────────────────────
    {
        "keywords": ["retail hvac", "tenancy hvac", "fitout mechanical", "air conditioning fitout",
                     "hvac fitout", "kitchen exhaust canopy", "commercial exhaust",
                     "mechanical fitout", "hvac balancing", "fresh air fitout"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Hearing protection — HVAC plant noise during commissioning",
            "Safety glasses",
            "Hard hat — ceiling space access",
        ],
        "certs": [
            "Licensed refrigeration mechanic — split system and refrigerant handling",
            "ARC licence — refrigerant handling licence mandatory",
            "Mechanical engineer — HVAC design and balancing report",
        ],
        "permits": [
            "Landlord HVAC approval — connection to base building system approved",
            "Refrigerant handling — ARC licence before any refrigerant work",
            "Kitchen exhaust MCA — mechanical contractor approval for canopy sizing",
            "HVAC balancing report — air balance test before occupation certificate",
        ],
        "qualifications": [
            "Refrigerant type — check refrigerant type before commencing, F-gas regulations",
            "Canopy sizing — commercial kitchen canopy sized per AS 1668.2",
            "Grease filters — stainless steel grease filters, cleanable, minimum weekly",
            "Make-up air — replacement air designed to prevent negative pressure in kitchen",
            "Access panels — HVAC ductwork access panels at maximum 3m intervals",
        ],
        "notifications": [
            "Landlord — HVAC connection to base building system 5 business days notice",
            "ARC — refrigerant handling records maintained and available for inspection",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 1668.2 — Mechanical ventilation in buildings — retail and commercial",
            "ARC — Australian Refrigeration Council, refrigerant handling licence mandatory",
            "Kitchen exhaust — grease-laden exhaust is fire risk, AS 1668.1 compliance",
        ],
    },

    # ── RETAIL FITOUT — ELECTRICAL ───────────────────────────────────────────
    {
        "keywords": ["retail electrical", "fitout electrical", "shop electrical",
                     "tenancy electrical", "illuminated signage", "feature lighting fitout",
                     "data cabling fitout", "pos electrical", "retail power"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.16 — Electrical installation work",
        "hrcw_license_class": "Electrician Licence — NSW Fair Trading A-grade",
        "ppe": [
            "Insulated gloves — voltage-rated",
            "Safety glasses",
            "Arc flash PPE — switchboard work",
        ],
        "certs": [
            "Licensed electrician — A-grade, all retail electrical work",
            "CCEW — Certificate of Compliance Electrical Work before occupation",
            "Network operator approval — Ausgrid or Endeavour Energy for metering",
        ],
        "permits": [
            "Electrical approval — part of Construction Certificate",
            "CCEW — issued to owner before occupation certificate",
            "Surge protection — SPD on tenant switchboard, landlord requirement",
            "RCD protection — all circuits RCD protected, AS/NZS 3000",
        ],
        "qualifications": [
            "Separate metering — tenant meter installed, landlord requirement",
            "Signage circuits — illuminated signage on dedicated circuit with isolator",
            "Data cabling — structured cabling to AS/ACIF S008 or Cat6 minimum",
            "Emergency lighting — AS 2293.1, on base building emergency power where possible",
            "Test and tag — all portable equipment tested before commissioning",
        ],
        "notifications": [
            "Network operator — Ausgrid 13 13 65 or Endeavour Energy 13 22 29 for metering",
            "Landlord — electrical design approval before installation commences",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS/NZS 3000 — Wiring rules — all retail electrical must comply",
            "CCEW — mandatory, provided to owner within 4 days of completing electrical work",
            "Landlord meter — metering typically base building responsibility, confirm in lease",
        ],
    },

    # ── RETAIL FITOUT — STRUCTURAL — MEZZANINE ───────────────────────────────
    {
        "keywords": ["mezzanine", "mezzanine level", "mezzanine floor",
                     "retail mezzanine", "fitout mezzanine", "internal mezzanine",
                     "storage mezzanine", "office mezzanine"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.10 — Construction of mezzanine floor",
        "hrcw_license_class": None,
        "ppe": [
            "Full-body harness — mezzanine steel erection above 2m",
            "Hard hat",
            "Safety glasses",
            "Steel-capped boots",
        ],
        "certs": [
            "Structural engineer — mezzanine design certification before construction",
            "Council DA or CDC — mezzanine requires development consent",
            "Construction Certificate — before mezzanine construction commences",
            "Fire engineer — mezzanine may affect BCA fire compartment, fire engineering required",
        ],
        "permits": [
            "DA or CDC — development consent before mezzanine construction",
            "CC — Construction Certificate before physical work",
            "Landlord approval — structural engineer and landlord approval before any floor penetrations",
            "Principal Certifier — hold points at steel erection and completion",
            "Base building load check — engineer confirm base building can take mezzanine load",
        ],
        "qualifications": [
            "Floor loading — mezzanine designed for minimum 3.0 kPa live load (retail)",
            "Balustrade — minimum 1100mm high, AS 1657",
            "Stair — minimum 1000mm wide, AS 1657 compliant",
            "Fire rating — mezzanine floor may require FRL if part of fire compartment",
            "Slab penetrations — structural engineer approval and PT scan before any penetrations",
        ],
        "notifications": [
            "Council — DA or CDC application before mezzanine construction",
            "Landlord — structural engineer certification and landlord approval before work",
            "Principal Certifier — 48 hours notice before each hold point inspection",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "BCA Section B — structural provisions for mezzanine floors",
            "Fire compartment — mezzanine may create new fire compartment, fire engineer required",
            "PT slab — GPR scan mandatory before any anchor or penetration in post-tension slab",
        ],
    },

    # ── RETAIL FITOUT — PARTITION WALLS & CEILINGS ───────────────────────────
    {
        "keywords": ["partition wall fitout", "stud wall fitout", "demountable wall",
                     "suspended ceiling fitout", "ceiling grid fitout", "plasterboard fitout",
                     "glazed partition", "glass partition fitout", "ceiling tile fitout"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Safety glasses — plasterboard and ceiling grid installation",
            "P2 respirator (minimum) — plasterboard cutting dust",
            "Hearing protection — power screwdrivers and cutting",
            "Full-body harness — where ceiling work above 2m on elevated platform",
        ],
        "certs": [
            "Structural engineer — where partition walls are load-bearing or fire-rated",
            "Fire rating — fire-rated walls must be installed by certified installer",
        ],
        "permits": [
            "Fire-rated partition certification — certifier hold point for fire-rated walls",
            "Acoustic testing — where acoustic partition performance is specified",
        ],
        "qualifications": [
            "Fire-rated walls — AS 1530.4 compliant installation, no penetrations without fire collars",
            "Suspended ceiling — seismic restraint per AS 1170.4 in commercial buildings",
            "Glazing — AS 1288 safety glazing in all human impact locations",
            "Frameless glass — structural engineer certification for frameless glass installations",
            "Access panels — ceiling access panels at all service access points",
        ],
        "notifications": [
            "Principal Certifier — fire-rated wall inspection hold point 48 hours notice",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 1288 — Glass in buildings — safety glazing requirements",
            "BCA Section C — fire-rated construction requirements",
            "Seismic — suspended ceilings in commercial buildings require seismic restraint per AS 1170.4",
        ],
    },

    # ── RETAIL FITOUT — FLOOR FINISHES ──────────────────────────────────────
    {
        "keywords": ["retail floor", "floor finish fitout", "floor tile retail",
                     "vinyl floor fitout", "epoxy floor retail", "timber floor retail",
                     "floor levelling", "floor screed", "floor preparation fitout"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "P2 dust respirator — floor grinding and preparation silica dust",
            "Knee pads — floor laying",
            "Safety glasses — grinding and cutting",
            "Hearing protection — floor grinder noise",
            "Chemical-resistant gloves — adhesive and epoxy handling",
        ],
        "certs": [
            "Slip resistance testing — AS 4586 compliance, wet and dry tested before occupation",
        ],
        "permits": [],
        "qualifications": [
            "Slip resistance — minimum R10 dry areas, R11 wet areas, R12 commercial kitchens",
            "Transition strips — required at all floor finish junctions, flush or ramped",
            "DDA compliance — no abrupt transitions >5mm, ramp >5mm and <20mm",
            "Floor levelness — maximum 5mm deviation under 1800mm straight edge",
            "Wet cutting — all tile and stone cutting must use wet method, silica dust",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 4586 — Slip resistance classification of new pedestrian surface materials",
            "Silica — floor grinding and tile cutting generates respirable silica, wet method mandatory",
            "DDA — floor transitions must not create trip hazard for mobility aid users",
        ],
    },

    # ── RETAIL FITOUT — SIGNAGE ──────────────────────────────────────────────
    {
        "keywords": ["retail signage", "shop signage", "illuminated sign", "shopfront sign",
                     "fascia sign", "pylon sign", "projecting sign", "LED sign retail",
                     "neon sign", "lightbox sign"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Full-body harness — elevated signage installation above 2m",
            "Hard hat",
            "Safety glasses",
        ],
        "certs": [
            "Council signage DA or exempt development — signage requires approval",
            "Licensed electrician — illuminated signage electrical connection",
            "Engineer certification — projecting or cantilevered signs >10kg",
        ],
        "permits": [
            "Council signage approval — DA or exempt development check before installation",
            "Centre management signage approval — shopping centre brand guidelines compliance",
            "Structural certification — projecting signs require engineer certification",
            "Electrical approval — illuminated signage as part of electrical CC",
        ],
        "qualifications": [
            "Height — projecting signs above 2.5m require structural engineer certification",
            "Wind loading — signs designed to AS 1170.2 wind loads for location",
            "Isolation switch — accessible isolation switch within 1m of every illuminated sign",
            "Landlord approval — centre management signage guide compliance before installation",
        ],
        "notifications": [
            "Council — signage DA lodged minimum 40 business days before installation",
            "Centre management — signage approval before any installation",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "State Environmental Planning Policy — signage controls for commercial premises",
            "Centre signage guide — typically specifies font, colour, illumination type and size",
            "Wind loading — freestanding and projecting signs frequently fail in high wind events",
        ],
    },

    # ── RETAIL FITOUT — STRIP OUT & DEMOLITION ───────────────────────────────
    {
        "keywords": ["strip out", "strip-out", "demolish fitout", "fitout demolition",
                     "tenancy strip", "retail demolition", "shop strip out",
                     "remove fitout", "fitout removal"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.10 — Demolition of fitout involving asbestos risk assessment",
        "hrcw_license_class": None,
        "ppe": [
            "P2 respirator — dust and possible asbestos during strip out",
            "Safety glasses",
            "Hard hat — overhead demolition risk",
            "Disposable coveralls — where hazmat suspected",
            "Safety boots",
        ],
        "certs": [
            "Hazardous materials survey — before any strip out of existing fitout",
            "Asbestos survey — friable and non-friable asbestos identification before work",
            "Demolition licence — where structural elements being removed",
        ],
        "permits": [
            "Hazmat survey — completed and reviewed before any demolition commences",
            "Services isolation — all electrical, gas, hydraulic isolated before strip out",
            "Waste management plan — licensed waste contractor engaged before work",
            "Landlord approval — strip out methodology approved before commencing",
        ],
        "qualifications": [
            "Services isolation — isolation certificates for all services before strip out",
            "Asbestos — asbestos removal by licensed removalist before any other demolition",
            "Waste — segregated waste bins, recycling plan, licensed waste contractor",
            "Existing services — photograph all existing services before removal for as-built record",
            "Structural — do not remove anything structural without engineer approval",
        ],
        "notifications": [
            "Landlord — strip out methodology and program approved in writing before start",
            "Centre management — strip out notification, approved working hours only",
            "SafeWork NSW — notification if asbestos removal >10m²",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Asbestos — retail fitouts pre-2003 may contain asbestos in vinyl tiles, texture coat, sealants",
            "Services isolation — never assume services are isolated, test before cutting",
            "Waste — fitout waste is C&D waste, licensed facility required for disposal",
        ],
    },

    # ── RETAIL FITOUT — LIQUOR LICENCE ──────────────────────────────────────
    {
        "keywords": ["liquor licence", "liquor fitout", "bar fitout", "licensed premises",
                     "bottle shop fitout", "hotel fitout", "pub fitout",
                     "nightclub fitout", "igla", "liquor and gaming"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [
            "ILGA licence — NSW Independent Liquor and Gaming Authority approval",
            "Council development consent — licensed premises require DA",
            "Responsible Service of Alcohol — RSA certification for all staff",
        ],
        "permits": [
            "ILGA liquor licence — application before licensed premises open",
            "Council DA — change of use to licensed premises",
            "Plans approval — ILGA approved plans before fitout commences",
            "Amenities — BCA compliant amenities for patron numbers",
            "Noise management plan — ILGA and council requirement for licensed premises",
        ],
        "qualifications": [
            "Security — licensed security where required by ILGA conditions",
            "Patron capacity — maximum capacity set by ILGA, must be displayed",
            "CCTV — ILGA typically requires CCTV at all entries, operational before opening",
            "Minors — signage and controls for minors as per ILGA licence conditions",
        ],
        "notifications": [
            "ILGA — liquor licence application minimum 60 days before proposed opening",
            "Council — DA for change of use to licensed premises",
            "NSW Police — ILGA notifies police as part of licence application process",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Liquor Act 2007 (NSW) — ILGA approval mandatory before any licensed premises operates",
            "RSA — all staff serving alcohol must hold current RSA certificate",
            "ILGA conditions — conditions vary, read before commencing fitout design",
        ],
    },

    # ── RETAIL FITOUT — OUTDOOR DINING ──────────────────────────────────────
    {
        "keywords": ["outdoor dining", "alfresco dining", "footpath dining",
                     "outdoor seating", "council outdoor dining", "street furniture",
                     "footpath seating", "outdoor furniture retail"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [
            "Council outdoor dining approval — before any furniture placed on footpath",
        ],
        "permits": [
            "Council outdoor dining permit — annual permit, application before use",
            "Footpath licence — council licence for use of public footpath",
            "Public liability insurance — minimum $20M, required with permit application",
            "DDA compliance — 1800mm minimum clear footpath width maintained at all times",
            "Liquor extension — ILGA approval to extend liquor licence to outdoor area",
        ],
        "qualifications": [
            "Clear path — minimum 1800mm clear pedestrian path at all times",
            "Furniture — approved furniture type per council outdoor dining policy",
            "Umbrellas — maximum height and setback from road per council requirements",
            "Heaters — gas heaters require gas compliance certificate",
        ],
        "notifications": [
            "Council — outdoor dining permit application minimum 20 business days before",
            "ILGA — liquor licence extension to outdoor area before serving alcohol outside",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Local Government Act 1993 (NSW) — council permits required for footpath use",
            "DDA — accessible path of travel must be maintained past outdoor dining area",
            "Gas heaters — outdoor gas heaters require gas compliance certificate from licensed gasfitter",
        ],
    },

    # ══════════════════════════════════════════════════════════════════════
    # STREAM: Electrical (6 categories)
    # ══════════════════════════════════════════════════════════════════════

    # ── ENERGISED ELECTRICAL ──────────────────────────────────────────────
    {
        "keywords": ["energised electrical", "live electrical", "live work",
                     "energised work", "electrical energised"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.16 — Work on or near energised electrical installations",
        "hrcw_license_class": "Licensed Electrician — NSW Fair Trading",
        "ppe": [
            "Insulated gloves — rated to working voltage",
            "Arc-flash rated clothing — Category 2 minimum",
            "Face shield — arc-flash rated",
            "Insulated footwear",
        ],
        "certs": [
            "Licensed Electrician — NSW Fair Trading",
        ],
        "permits": [
            "Energised Electrical Work Permit — signed before any live work",
        ],
        "qualifications": [],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS/NZS 3000 — Wiring rules",
            "SafeWork NSW Code of Practice: Managing Electrical Risks in the Workplace",
            "Energised work only permitted where de-energisation creates greater risk",
        ],
    },

    # ── LOCKOUT TAGOUT ────────────────────────────────────────────────────
    {
        "keywords": ["lockout", "tagout", "loto", "lock out tag out",
                     "isolation procedure", "energy isolation"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Safety glasses",
            "Insulated gloves — where electrical isolation",
        ],
        "certs": [],
        "permits": [
            "Isolation permit — lock and tag applied before work commences",
        ],
        "qualifications": [
            "Competent person — trained in LOTO procedures",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 s.203 — Isolation of plant from energy sources",
            "Isolation locks and tags — personal locks for each worker",
        ],
    },

    # ── OVERHEAD POWERLINES ───────────────────────────────────────────────
    {
        "keywords": ["overhead powerline", "overhead power line", "powerline exclusion",
                     "near powerlines", "power line clearance", "safe approach distance"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.16 — Work near energised electrical installations",
        "hrcw_license_class": None,
        "ppe": [
            "Hard hat — mandatory near overhead lines",
        ],
        "certs": [],
        "permits": [],
        "qualifications": [
            "Spotter — trained in safe approach distances and exclusion zones",
            "Zone A (0-3m from 11kV, 0-6m from 33kV, 0-8m from 132kV+) — no work; de-energisation or insulated barrier required before any entry",
            "Zone B (3-6m from 11kV, 6-10m from 33kV) — work only with spotter maintaining exclusion; no plant in this zone without network operator approval",
            "Zone C (approach zone) — spotter and supervisor awareness required; plant operators briefed on powerline location before commencing",
            "De-energisation request — submitted to network operator (Ausgrid/Essential Energy) minimum 48 hours before work requiring Zone A entry",
        ],
        "notifications": [
            "Ausgrid/Endeavour Energy — notification required for work within safe approach distance",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "SafeWork NSW Code of Practice: Managing Electrical Risks in the Workplace",
            "Exclusion zone <6.4m from overhead powerlines — no work without DNSP approval",
            "AS 5488 — Classification of subsurface utility information",
            "WHS Reg 2017 r.163-165 — overhead powerline exclusion distances",
            "SafeWork NSW Code of Practice: Working Near Overhead Power Lines",
            "Exclusion distances — 3m from powerlines up to 11kV; 6m from 11kV to 33kV; 8m from 33kV to 132kV; 10m from 132kV and above",
            "Ausgrid contact — 13 13 65 — to arrange de-energisation or insulated barriers for Zone A work",
            "Essential Energy contact — 13 23 91 — for regional NSW network operator notifications",
            "Plant height check — all plant and loads (crane jibs, scaffold, tipping trucks) measured for clearance before entering approach zone",
            "Insulated barriers — only approved by network operator; contractor cannot install their own barriers without network operator approval",
        ],
    },

    # ── LEVEL 2 ASP ───────────────────────────────────────────────────────
    {
        "keywords": ["level 2 asp", "l2 asp", "authorised service provider",
                     "asp works", "contestable electrical"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.16 — Electrical installation work",
        "hrcw_license_class": "Level 2 ASP Licence — NSW Fair Trading",
        "ppe": [
            "Insulated gloves — rated to working voltage",
            "Arc-flash rated clothing",
        ],
        "certs": [
            "Level 2 ASP licence — NSW Fair Trading",
        ],
        "permits": [],
        "qualifications": [],
        "notifications": [
            "DNSP notification required — Ausgrid/Endeavour Energy before contestable work",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Service and Installation Rules of NSW",
            "Level 2 ASP works include metering, service lines, and point of attachment",
        ],
    },

    # ── SWITCHBOARD ───────────────────────────────────────────────────────
    {
        "keywords": ["switchboard", "distribution board", "meter board",
                     "db upgrade", "switchboard upgrade"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.16 — Electrical installation work",
        "hrcw_license_class": "Licensed Electrician — NSW Fair Trading",
        "ppe": [
            "Insulated gloves — rated to working voltage",
            "Arc-flash rated face shield",
        ],
        "certs": [
            "Licensed Electrician — NSW Fair Trading",
        ],
        "permits": [],
        "qualifications": [],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS/NZS 3000 — Wiring rules",
            "Isolation required before switchboard work — LOTO procedure applies",
        ],
    },

    # ── UNDERGROUND CABLE ─────────────────────────────────────────────────
    {
        "keywords": ["underground cable", "cable strike", "buried cable",
                     "underground electrical", "cable location"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.16 — Work near energised electrical installations",
        "hrcw_license_class": None,
        "ppe": [
            "Insulated footwear",
            "Safety glasses",
        ],
        "certs": [],
        "permits": [],
        "qualifications": [
            "Competent person — cable locator operator",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Dial Before You Dig — DBYD enquiry required before any excavation",
            "AS 5488 — Classification of subsurface utility information",
            "Cable location scan required before mechanical excavation within 1m of services",
        ],
    },

    # ══════════════════════════════════════════════════════════════════════
    # STREAM: Confined Space (4 categories)
    # ══════════════════════════════════════════════════════════════════════

    # ── CONFINED SPACE ENTRY ──────────────────────────────────────────────
    {
        "keywords": ["confined space entry", "confined space work", "enter confined space",
                     "pit entry", "stormwater pit", "tank entry", "vault entry",
                     "manhole entry", "sewer entry"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.15 — Work in or near a confined space",
        "hrcw_license_class": None,
        "ppe": [
            "Full-body harness — retrieval attachment point",
            "P2 respirator (minimum) — upgrade to SCBA where oxygen deficiency risk",
            "Safety glasses",
            "Hard hat — low clearance areas",
        ],
        "certs": [
            "Confined Space Entry and Rescue — RIIWHS202E or equivalent",
        ],
        "permits": [
            "Confined Space Entry Permit — signed before every entry",
        ],
        "qualifications": [
            "Standby person — trained in emergency procedures, stationed at entry point",
            "Rescue plan — documented before entry, tested with team",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 Part 4.3 — Confined spaces",
            "SafeWork NSW Code of Practice: Managing Risks in Confined Spaces",
            "Atmospheric monitor (4-gas) — continuous monitoring during entry",
            "Communication system between entrant and standby person required",
        ],
    },

    # ── CONFINED SPACE RESCUE ─────────────────────────────────────────────
    {
        "keywords": ["confined space rescue", "rescue plan confined", "retrieval system",
                     "confined rescue equipment"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.15 — Work in or near a confined space",
        "hrcw_license_class": None,
        "ppe": [
            "Full-body harness — retrieval attachment point",
            "SCBA — self-contained breathing apparatus for rescue entry",
        ],
        "certs": [
            "Confined Space Entry and Rescue — RIIWHS202E or equivalent",
        ],
        "permits": [],
        "qualifications": [
            "Standby person — stationed at entry point at all times during work",
            "Rescue team — trained and equipped, available within response time",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 s.74 — Rescue procedures for confined spaces",
            "Retrieval equipment — mechanical advantage system or tripod at entry",
            "Practice rescue drill required before first entry on each site",
        ],
    },

    # ── CONFINED SPACE ATMOSPHERIC ────────────────────────────────────────
    {
        "keywords": ["atmospheric testing", "atmospheric monitoring", "gas testing confined",
                     "oxygen monitoring", "4-gas monitor", "four gas monitor"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.15 — Work in or near a confined space",
        "hrcw_license_class": None,
        "ppe": [
            "P2 respirator (minimum) — upgrade based on atmospheric results",
        ],
        "certs": [],
        "permits": [],
        "qualifications": [
            "Competent person — atmospheric testing and monitor calibration",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 s.67 — Atmospheric testing before entry",
            "Monitor continuously during work — O2, LEL, CO, H2S minimum",
            "Alarm set points: O2 <19.5%, LEL >10%, CO >30ppm, H2S >10ppm",
        ],
    },

    # ── CONFINED SPACE HOT WORK ───────────────────────────────────────────
    {
        "keywords": ["hot work confined", "welding confined space", "cutting confined space",
                     "grinding confined space", "confined space hot work"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.15 — Work in or near a confined space",
        "hrcw_license_class": None,
        "ppe": [
            "Full-body harness — retrieval attachment point",
            "Welding helmet or face shield",
            "Fire-resistant clothing",
            "SCBA or supplied air — where flammable atmosphere risk",
        ],
        "certs": [
            "Confined Space Entry and Rescue — RIIWHS202E or equivalent",
        ],
        "permits": [
            "Confined Space Entry Permit — signed before entry",
            "Hot Works Permit — dual permit required for hot work inside confined space",
        ],
        "qualifications": [
            "Fire watch — continuous during and 30 minutes after hot work",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 Part 4.3 — Confined spaces",
            "LEL must be <5% before and during hot work — continuous monitoring",
            "Forced ventilation mandatory — natural ventilation insufficient for hot work",
        ],
    },

    # ══════════════════════════════════════════════════════════════════════
    # STREAM: Asbestos (5 categories)
    # ══════════════════════════════════════════════════════════════════════

    # ── ASBESTOS SURVEY ───────────────────────────────────────────────────
    {
        "keywords": ["asbestos survey", "asbestos audit", "pre-demolition survey",
                     "asbestos register", "asbestos inspection", "acm survey"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [
            "Asbestos Assessor — accredited under WHS Reg 2017",
        ],
        "permits": [],
        "qualifications": [
            "Asbestos Assessor — competent to identify and classify ACMs",
        ],
        "notifications": [
            "SafeWork NSW notification if asbestos identified and removal >10m²",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "SafeWork NSW Code of Practice: How to Manage and Control Asbestos in the Workplace",
            "WHS Reg 2017 s.425 — Asbestos register must be maintained",
            "Pre-demolition survey mandatory before any demolition or refurbishment",
        ],
    },

    # ── ASBESTOS CLASS A (FRIABLE) ────────────────────────────────────────
    {
        "keywords": ["class a removal", "class a asbestos", "friable asbestos",
                     "friable removal", "asbestos class a"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.18 — Asbestos removal work (friable)",
        "hrcw_license_class": "Asbestos Removal Licence — Class A (friable)",
        "ppe": [
            "Full-face powered air-purifying respirator (PAPR) — P3 filter",
            "Disposable Tyvek coveralls — taped at wrists and ankles",
            "Nitrile gloves — double layer",
            "Safety boots — decontaminated at zone exit",
        ],
        "certs": [
            "Asbestos Removal Licence — Class A (SafeWork NSW)",
            "CPCCDE3014 — Remove friable asbestos",
            "Asbestos Assessor — accredited for air monitoring",
        ],
        "permits": [
            "Asbestos removal permit — Class A",
        ],
        "qualifications": [
            "Licensed supervisor on site at all times",
            "Asbestos Assessor — clearance inspection and certificate before re-occupation",
        ],
        "notifications": [
            "SafeWork NSW — 5 business days notice before Class A removal",
        ],
        "safework_notification": True,
        "epa_license": True,
        "notes": [
            "WHS Reg 2017 Part 8.3 — Asbestos removal duties",
            "Air monitoring required during all Class A removal",
            "Clearance certificate required before re-occupation",
            "Negative pressure enclosure required for indoor friable removal",
        ],
    },

    # ── ASBESTOS CLASS B (NON-FRIABLE) ────────────────────────────────────
    {
        "keywords": ["class b removal", "class b asbestos", "non-friable asbestos",
                     "non-friable removal", "asbestos class b", "bonded asbestos removal"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.18 — Asbestos removal work (non-friable)",
        "hrcw_license_class": "Asbestos Removal Licence — Class B (non-friable)",
        "ppe": [
            "P2 half-face respirator — fit-tested",
            "Disposable Tyvek coveralls — taped at wrists and ankles",
            "Nitrile gloves",
            "Safety glasses — full seal",
        ],
        "certs": [
            "Asbestos Removal Licence — Class B (SafeWork NSW)",
            "CPCCDE3002 — Remove non-friable asbestos",
        ],
        "permits": [
            "Asbestos removal permit — Class B",
        ],
        "qualifications": [
            "Licensed supervisor on site during removal",
        ],
        "notifications": [
            "SafeWork NSW — 1 business day notice before Class B removal >10m²",
        ],
        "safework_notification": True,
        "epa_license": True,
        "notes": [
            "WHS Reg 2017 Part 8.3 — Asbestos removal duties",
            "SafeWork NSW Code of Practice: How to Safely Remove Asbestos",
            "Wet removal methods — keep ACM damp to minimise fibre release",
        ],
    },

    # ── ASBESTOS ENCAPSULATION ────────────────────────────────────────────
    {
        "keywords": ["asbestos encapsulat", "seal asbestos", "paint over asbestos",
                     "asbestos coating", "encapsulate acm"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "P2 half-face respirator — fit-tested",
            "Disposable Tyvek coveralls",
            "Nitrile gloves",
            "Safety glasses — full seal",
        ],
        "certs": [],
        "permits": [],
        "qualifications": [
            "Competent person — trained in asbestos awareness",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "SafeWork NSW Code of Practice: How to Manage and Control Asbestos in the Workplace",
            "Encapsulation is not removal — does not require removal licence",
            "Asbestos register must be updated to record encapsulated material and location",
        ],
    },

    # ── ASBESTOS UNEXPECTED ───────────────────────────────────────────────
    {
        "keywords": ["unexpected asbestos", "suspected asbestos", "asbestos discovery",
                     "found asbestos", "possible acm", "suspected acm"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "P2 half-face respirator — immediately upon discovery",
            "Disposable coveralls — if contact with material",
        ],
        "certs": [],
        "permits": [],
        "qualifications": [],
        "notifications": [
            "SafeWork NSW — if asbestos confirmed and removal required",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "STOP WORK immediately — evacuate area and restrict access",
            "Do not disturb suspected material — leave in place",
            "Engage Asbestos Assessor for sampling and identification",
            "WHS Reg 2017 s.422 — Duty to identify asbestos before disturbance",
        ],
    },

    # ══════════════════════════════════════════════════════════════════════
    # STREAM: Crane and Lifting (4 categories)
    # ══════════════════════════════════════════════════════════════════════

    # ── MOBILE CRANE ──────────────────────────────────────────────────────
    {
        "keywords": ["mobile crane lift", "crane lift plan", "crane operation",
                     "crane rigging", "crane exclusion zone"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.8 — Work involving use of crane",
        "hrcw_license_class": "Crane Licence — CN/C2/C6 class",
        "ppe": [
            "Hard hat — mandatory in crane exclusion zone",
            "High-visibility vest or shirt",
            "Steel-capped safety boots",
        ],
        "certs": [
            "Dogging licence (DG) — SafeWork NSW",
            "Rigging licence (RB/RI/RE) — SafeWork NSW",
            "Crane licence (CN/C2/C6) — SafeWork NSW",
        ],
        "permits": [
            "Lift plan — documented and signed before each lift",
            "Lift study — documented for any lift where load exceeds 75% SWL, multi-crane lift, or lift over energised services/public areas",
            "Crane set-up permit — ground bearing capacity confirmed before outriggers deployed",
        ],
        "qualifications": [
            "Lift supervisor — responsible for exclusion zone and lift coordination",
            "Exclusion zone — established and enforced for the full swing radius plus load overhang; nobody under suspended load at any time",
            "Outrigger pads — design verified for ground bearing capacity by competent person before lift",
            "Communication — dogman/rigger on continuous two-way communication with crane operator during lift",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 Part 5.2 — General duties for plant",
            "SafeWork NSW Code of Practice: Managing Risks of Plant in the Workplace",
            "Exclusion zone required — no personnel under suspended loads",
            "Crane set-up on firm level ground — outrigger pads required",
            "WHS Reg 2017 r.211-240 — plant with potential to cause harm; registration, inspection, and operator licence obligations",
            "Critical lift threshold — any lift over 75% SWL or involving multiple cranes requires formal lift study signed by engineer",
            "Wind limits — all crane operations suspended in sustained winds exceeding manufacturer's rated limit (typically 48-72km/h depending on crane and jib configuration)",
            "Tagline required — unguided loads create uncontrolled swing hazard; taglines used on all loads except where impracticable",
            "Load chart — operator must verify SWL for the specific radius and jib configuration before lift",
        ],
    },

    # ── FRANNA PICK AND CARRY ─────────────────────────────────────────────
    {
        "keywords": ["franna", "pick and carry", "pick carry crane",
                     "franna crane", "non-slewing crane"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.8 — Work involving use of crane",
        "hrcw_license_class": "Crane Licence — CN class (non-slewing mobile crane >3t)",
        "ppe": [
            "Hard hat — mandatory in crane exclusion zone",
            "High-visibility vest or shirt",
            "Steel-capped safety boots",
        ],
        "certs": [
            "Crane licence — CN class (SafeWork NSW)",
            "Dogging licence (DG) — for directing crane movement",
        ],
        "permits": [
            "Lift study — documented for any lift where load exceeds 75% SWL, multi-crane lift, or lift over energised services/public areas",
            "Crane set-up permit — ground bearing capacity confirmed before outriggers deployed",
        ],
        "qualifications": [
            "Spotter — for pick and carry operations near structures",
            "Exclusion zone — established and enforced for the full swing radius plus load overhang; nobody under suspended load at any time",
            "Outrigger pads — design verified for ground bearing capacity by competent person before lift",
            "Communication — dogman/rigger on continuous two-way communication with crane operator during lift",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Pick and carry — travel path must be assessed for ground bearing capacity",
            "Load chart — verify SWL for pick and carry radius",
            "WHS Reg 2017 r.211-240 — plant with potential to cause harm; registration, inspection, and operator licence obligations",
            "Critical lift threshold — any lift over 75% SWL or involving multiple cranes requires formal lift study signed by engineer",
            "Wind limits — all crane operations suspended in sustained winds exceeding manufacturer's rated limit (typically 48-72km/h depending on crane and jib configuration)",
            "Tagline required — unguided loads create uncontrolled swing hazard; taglines used on all loads except where impracticable",
            "Load chart — operator must verify SWL for the specific radius and jib configuration before lift",
        ],
    },

    # ── TOWER CRANE ───────────────────────────────────────────────────────────
    {
        "keywords": ["tower crane", "luffing jib", "hammerhead crane",
                     "self-erecting crane", "climbing crane", "crane base"],
        "hrcw": True,
        "hrcw_category": "Schedule 3 cl.2 — Work involving use of a crane",
        "hrcw_license_class": "Crane Licence — C2 class (tower crane operator, SafeWork NSW)",
        "ppe": [
            "Hard hat — mandatory within crane exclusion/swing zone",
            "Hi-vis vest",
            "Safety boots",
        ],
        "certs": [
            "Tower crane operator licence — C2 class (SafeWork NSW)",
            "Dogman licence — DG class for all persons directing lifts",
            "Rigger licence — RB/RI/RE class for rigging operations",
        ],
        "permits": [
            "Lift study — required for each crane configuration; reviewed when crane climbs",
            "Crane base engineering certificate — structural engineer sign-off before crane erected",
            "Crane erection/dismantling SWMS — required; crane erection is HRCW",
        ],
        "qualifications": [
            "SafeWork NSW — tower crane registration required; plant registration number on all permits",
            "Crane coordinator — nominated responsible person on site for crane operations",
            "Jib clearance — engineer-verified clearance from adjacent structures, powerlines, and other cranes",
        ],
        "notifications": [
            "SafeWork NSW — tower crane erection notification required before erection commences",
        ],
        "safework_notification": True,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 r.211-240 — plant with potential to cause harm; registration required",
            "SafeWork NSW — tower cranes must be registered plant; design registration number required",
            "Crane base design — engineer-certified, with geotechnical report for foundation conditions",
            "Anti-collision system — required where two or more cranes operate in overlapping zones",
            "Out-of-hours slewing — jib must be free to weathervane in free-slew mode when unattended",
            "Exclusion zone — swing radius plus jib length; no public access within zone",
            "Climbing sequence — engineer-approved climbing procedure; crane must be re-certified after each climb",
        ],
    },

    # ── EWP BOOM ──────────────────────────────────────────────────────────
    {
        "keywords": ["ewp boom", "boom lift", "boom ewp", "cherry picker",
                     "knuckle boom", "articulated boom"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.3 — Work at height with risk of fall >2m",
        "hrcw_license_class": "EWP Licence — WP class (boom over 11m)",
        "ppe": [
            "Full-body harness — short-lanyard attachment to EWP anchor point",
            "Hard hat — mandatory",
            "High-visibility vest or shirt",
        ],
        "certs": [
            "EWP operator licence — WP class where boom exceeds 11m",
        ],
        "permits": [
            "Working at heights permit — signed before elevated work",
        ],
        "qualifications": [
            "Competent person — pre-start inspection of EWP",
            "Rescue plan — documented before work commences; includes how to retrieve worker from harness/EWP/suspended scaffold if incapacitated",
            "Rescue equipment — on site and ready for immediate deployment before any elevated work starts",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Pre-start checklist — completed and signed before each shift",
            "Exclusion zone below work area — barricaded",
            "Wind limit — manufacturer specified, typically 45km/h for boom EWP",
            "WHS Reg 2017 r.305 — rescue procedure required before commencing work at height",
            "Suspension trauma — incapacitated worker must be lowered within 15 minutes; harness straps can cause positional asphyxia",
            "Emergency contacts — on-site personnel trained in rescue procedure before elevated work begins",
            "WHS Reg 2017 r.291-303 — fall prevention hierarchy: (1) eliminate, (2) passive edge protection/guardrail, (3) restraint system, (4) fall arrest, (5) administrative",
            "Edge protection first — guardrails preferred over harness where work area permits fixed barriers",
            "Control line — 2m setback from edge, used only when guardrail not practicable",
        ],
    },

    # ── EWP SCISSOR ───────────────────────────────────────────────────────
    {
        "keywords": ["scissor lift", "ewp scissor", "scissor ewp",
                     "vertical lift platform"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.3 — Work at height with risk of fall >2m",
        "hrcw_license_class": "EWP Licence — WP class (if platform height >11m)",
        "ppe": [
            "Hard hat — mandatory",
            "High-visibility vest or shirt",
            "Full body harness + double lanyard — mandatory for EWP-to-roof transfer",
        ],
        "certs": [
            "EWP competency — EWPA Yellow Card or equivalent documented competency for scissor lift class",
            "Working at heights competency — current (RIIOHS204E or equivalent)",
            "EWP operator licence — WP class where boom platform exceeds 11m (not required for scissor lifts under 11m)",
        ],
        "permits": [
            "Working at heights permit — signed before elevated work",
            "Engineer confirmation — roof structure adequate at transfer point where EWP-to-roof transfer is planned",
        ],
        "qualifications": [
            "EWP pre-start inspection — completed and signed by operator before each shift per AS 2550",
            "OEM operator manual — on site and available to operator at all times",
            "EWP specifications confirmed: [INSERT MAKE/MODEL/SERIAL], platform rated capacity [INSERT kg], max working height [INSERT m], max wind speed [INSERT km/h per OEM]",
            "Current inspection certificate — AS 2550 major inspection within date",
            "Rescue plan — documented before work commences; includes how to retrieve worker from harness/EWP if incapacitated",
            "Rescue equipment — on site and ready for immediate deployment before any elevated work starts",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Pre-start checklist — completed and signed before each shift",
            "Scissor lifts — guardrails provide primary fall protection, harness not typically required",
            "Level ground required — check manufacturer slope limit",
            "WHS Reg 2017 r.305 — rescue procedure required before commencing work at height",
            "Suspension trauma — incapacitated worker must be lowered within 15 minutes; harness straps can cause positional asphyxia",
            "Emergency contacts — on-site personnel trained in rescue procedure before elevated work begins",
            "WHS Reg 2017 r.291-303 — fall prevention hierarchy: (1) eliminate, (2) passive edge protection/guardrail, (3) restraint system, (4) fall arrest, (5) administrative",
            "Edge protection first — guardrails preferred over harness where work area permits fixed barriers",
            "Control line — 2m setback from edge, used only when guardrail not practicable",
        ],
    },

    # ══════════════════════════════════════════════════════════════════════
    # STREAM: Formwork and Falsework (2 categories)
    # ══════════════════════════════════════════════════════════════════════

    # ── FORMWORK ──────────────────────────────────────────────────────────
    {
        "keywords": ["formwork", "formwork erection", "slab formwork",
                     "beam formwork", "column formwork", "strip formwork"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Hard hat — mandatory during formwork erection and stripping",
            "Steel-capped safety boots",
            "Safety glasses",
            "Cut-resistant gloves",
        ],
        "certs": [
            "Formwork licence — Intermediate (FI) or Basic (FB) where applicable",
        ],
        "permits": [
            "Strip Formwork work permit — required before any formwork stripping; must confirm concrete strength adequate and PT stressing records satisfactory",
        ],
        "qualifications": [
            "Temporary works engineer — sign-off required before concrete pour",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 3610 — Formwork for concrete",
            "SafeWork NSW Code of Practice: Managing Risks of Plant in the Workplace",
            "Formwork design certification required for heights >2m or non-standard configurations",
            "Drop stripping prohibited — formwork must be stripped progressively per methodology",
            "Engineer in-person inspection required before stripping any load-bearing formwork system",
            "Engineer inspection required before concrete placement — verify formwork/reinforcement/PT installation",
            "Handover inspection by formworker required before any proceeding trade accesses the deck",
            "Perimeter screens — handover certificate required where multi-level screens installed",
            "Exclusion zone under live deck — solid barrier directly above any work zone or walkway below",
        ],
    },

    # ── FALSEWORK ─────────────────────────────────────────────────────────
    {
        "keywords": ["falsework", "temporary works", "propping",
                     "temporary support structure", "shoring formwork"],
        "hrcw": True,
        "hrcw_category": "Schedule 3 cl.8 — Structural alterations or repairs requiring temporary support to prevent collapse",
        "hrcw_license_class": None,
        "ppe": [
            "Hard hat — mandatory",
            "Steel-capped safety boots",
            "Safety glasses",
        ],
        "certs": [],
        "permits": [],
        "qualifications": [
            "Temporary works engineer — design and sign-off of falsework system",
            "Competent person — inspection before loading and at regular intervals",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 3610 — Formwork for concrete (includes falsework requirements)",
            "Engineer sign-off required before loading falsework",
            "Progressive stripping sequence documented by engineer",
        ],
    },

    # ══════════════════════════════════════════════════════════════════════
    # STREAM: Fire Systems (3 categories)
    # ══════════════════════════════════════════════════════════════════════

    # ── SPRINKLER ISOLATION ───────────────────────────────────────────────
    {
        "keywords": ["sprinkler isolation", "fire suppression isolation",
                     "isolate sprinkler", "fire system isolation", "sprinkler impairment"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [],
        "certs": [],
        "permits": [
            "Fire suppression isolation permit — signed by building manager",
            "Hot Works Permit — required if welding or cutting near suppression system",
        ],
        "qualifications": [
            "Fire warden — notified of impairment, fire watch posted during isolation",
        ],
        "notifications": [
            "FRA/BCA compliance — fire brigade notification if system impaired >4 hours",
        ],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 2118 — Automatic fire sprinkler systems",
            "Maximum isolation period — restore system within shift unless 24hr fire watch",
            "Impairment log — record isolation start/end, reason, and responsible person",
        ],
    },

    # ── PASSIVE FIRE ──────────────────────────────────────────────────────
    {
        "keywords": ["passive fire", "fire stopping", "penetration seal",
                     "fire door installation", "fire collar", "intumescent",
                     "fire barrier", "fire compartment"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "P2 respirator (minimum) — during fire-stop product application",
            "Safety glasses",
            "Nitrile gloves",
        ],
        "certs": [
            "Passive fire installer — accredited to product manufacturer specifications",
        ],
        "permits": [],
        "qualifications": [],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "BCA Section C — Fire resistance and compartmentation",
            "AS 1530.4 — Fire-resistance tests of elements of building construction",
            "All penetration seals must be fire-rated to match the element penetrated",
            "Photographic evidence of each penetration seal required for certification",
        ],
    },

    # ── HOT WORKS NEAR SUPPRESSION ────────────────────────────────────────
    {
        "keywords": ["hot work suppression", "hot works near sprinkler",
                     "welding near sprinkler", "hot works fire system"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Fire-resistant clothing",
            "Welding helmet or face shield",
        ],
        "certs": [],
        "permits": [
            "Hot Works Permit — signed before any hot work",
            "Fire suppression isolation permit — dual permit required",
        ],
        "qualifications": [
            "Fire watch — continuous during and 30 minutes after hot work completion",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Sprinkler heads within 3m of hot work — cover with wet cloth or isolate zone",
            "Fire extinguisher — minimum 4.5kg ABE within 3m of hot work location",
            "Fire watch duration — minimum 30 minutes after hot work ceases",
        ],
    },

    # ── MOBILE PLANT ──────────────────────────────────────────────────────────
    {
        "keywords": ["mobile plant", "excavator", "bobcat", "skid steer",
                     "telehandler", "forklift", "posi-track", "loader",
                     "backhoe", "grader", "roller", "compactor",
                     "spider hoist", "personnel hoist", "materials hoist"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Hard hat — all persons in plant operating zone",
            "Hi-vis vest — mandatory when working near plant",
            "Safety boots",
        ],
        "certs": [
            "Excavator / backhoe — Plant operator licence (EX class, SafeWork NSW) where rated capacity >10t",
            "Telehandler — Forklift licence (LF class) or VOC per site requirement",
            "Forklift — Forklift licence (LF class, SafeWork NSW) — mandatory",
            "Skid steer / Bobcat — VOC required; no HRW licence but site VOC mandatory",
            "Posi-track — VOC required; no HRW licence but site VOC mandatory",
            "Roller / compactor — VOC required; no HRW licence",
            "Grader / loader — VOC required; no HRW licence",
        ],
        "permits": [
            "Pre-start checklist — completed by operator before each shift, faults reported and rectified before use",
            "Plant set-up permit — where plant operates near excavations, overhead services, or public areas",
        ],
        "qualifications": [
            "Exclusion zone — established around all mobile plant operating areas; size based on plant swing radius and visibility",
            "Spotter — required where plant operates in reverse, near people, or in areas with restricted visibility",
            "Two-person rule — no single-person operation of plant in areas where a second person cannot see the machine",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 r.211-240 — plant with potential to cause harm",
            "SafeWork NSW Code of Practice: Managing Risks of Plant in the Workplace",
            "Exclusion zone colour convention — physical barriers (concrete/water-filled) for HRCW areas; barrier mesh minimum for general exclusion",
            "Plant refuelling — away from open drains and waterways; spill kit on site",
            "Plant travel on public roads — must be registered or on a low-loader with escort if required",
            "Pre-start defect — any red-tagged defect means plant is out of service until repaired and cleared",
            "Night operations — additional lighting required; plant fitted with working reverse alarm and flashing beacon",
            "Physical barriers (solid — concrete/water-filled barriers or solid fencing) must be used to delineate HRCW areas where mobile plant operates — barrier mesh alone is insufficient for plant exclusion zones",
            "Exclusion zone colour convention — red bunting/flags/tape for restricted/exclusion zones, green for safe pedestrian walkways",
        ],
    },

    # ── CONCRETE POUR ─────────────────────────────────────────────────────────
    {
        "keywords": ["concrete pour", "concrete placement", "slab pour",
                     "concrete slab", "concrete footing", "concrete works",
                     "concrete pump", "concrete delivery"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Rubber boots — concrete work (alkali protection)",
            "Chemical-resistant gloves — fresh concrete",
            "Safety glasses",
            "Waterproof overalls if prolonged concrete exposure",
        ],
        "certs": [],
        "permits": [],
        "qualifications": [
            "Concrete tester/sampler — slump, cylinders per specification frequency",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Hold point — subgrade inspection before covering",
            "Hold point — membrane on subgrade before covering",
            "Hold point — formwork/reinforcement/post-tensioning inspected and approved by engineer before pour",
            "Hold point — concrete mix design approved before first pour",
            "Water must not be added to concrete on site unless approved by engineer or tester",
            "Concrete compressive test samples — frequency per specification",
            "Pour plan required — specify RLs, direction of pour, rate of rise for columns/walls",
            "Concrete must be adequately vibrated — no cold joints",
            "Curing — curing compound approved; curing application to be verified and recorded",
            "Excavations for drainage and service trenches — backfilled per AS 3798",
        ],
    },

    # ── POST-TENSIONING ───────────────────────────────────────────────────────
    {
        "keywords": ["post tension", "post-tension", "post tensioning", "post-tensioning",
                     "pt slab", "stressed slab", "prestressed concrete",
                     "tendons", "stressing", "anchorage", "dead end"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Full face shield — during stressing operations and tendon cutting",
            "Heavy-duty leather gloves — stressing and cutting",
            "Hard hat",
            "Safety boots — steel capped",
        ],
        "certs": [],
        "permits": [
            "Strip Formwork work permit — must include verification of concrete compressive strength AND PT stressing extension records, approved by engineer",
        ],
        "qualifications": [
            "Post-tensioning operator — trained and competent in stressing jack operation and extension recording",
            "Structural engineer — must approve stressing records and authorise stripping",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Anchorages must be securely fixed and anti-burst reinforcement installed before stressing",
            "Tendons must be installed to correct profile, supported by chairs per design",
            "Grout hoses to be installed with anchorages sealed (unbonded PT: pocket formers sealed)",
            "Initial and full stresses carried out per specification — not combined into single operation",
            "Extensions recorded on stressing records; engineer must review and approve before sign-off",
            "Tendons cut, sealed, and grouted/patched only after all stressing complete and approved",
            "Exclusion zone required during stressing — dead end zone particularly dangerous (tendon can project if anchor fails)",
            "Strip permit must reference both concrete strength result AND stressing records before engineer signs",
        ],
    },

    # ── MASONRY WALL CONSTRUCTION ─────────────────────────────────────────────
    {
        "keywords": ["masonry wall", "brick wall", "blockwork", "block wall",
                     "masonry construction", "brickwork", "freestanding wall",
                     "masonry structure", "retaining wall masonry"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Hard hat — mandatory during masonry construction",
            "Safety glasses — cutting and grinding",
            "P2 respirator — where cutting, grinding, or silica-containing materials in use",
            "Hearing protection — angle grinder/saw operations",
        ],
        "certs": [],
        "permits": [],
        "qualifications": [
            "Structural engineer or competent person — must assess and provide temporary bracing recommendations for freestanding walls",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "AS 3700 — Masonry Structures",
            "Masonry mortar curing period — 3-7 days after application; highest risk of collapse during this period",
            "Freestanding walls without returns or cross-walls — require engineer-assessed temporary bracing",
            "Temporary bracing must withstand likely wind forces for the specific site and stage of construction",
            "Wall height, reduced mortar strength, and wind forces must all be considered in the bracing design",
            "Steel reinforcement and core filling as construction progresses is an accepted bracing method",
        ],
    },

    # ── TEMPORARY WORKS — ENGINEERED DESIGN ──────────────────────────────────
    {
        "keywords": ["temporary support", "temporary works", "shoring", "propping",
                     "façade retention", "facade retention", "needling",
                     "structural propping", "prop system", "site hoarding",
                     "overhead protection gantry", "gantry", "crane landing platform",
                     "tower crane base", "piling platform"],
        "hrcw": True,
        "hrcw_category": "Schedule 3 cl.8 — Structural alterations or repairs requiring temporary support to prevent collapse",
        "hrcw_license_class": None,
        "ppe": [
            "Hard hat",
            "Safety boots — steel capped",
            "Hi-vis vest",
        ],
        "certs": [
            "Qualified designer (professional engineer or competent person) — must design temporary works",
            "Geotechnical engineer report — where required by foundation conditions",
        ],
        "permits": [
            "Temporary works handover certificate — completed by competent installer and verifying person before use",
            "Engineer inspection and authorisation — required before dismantling any load-bearing temporary works (formwork, falsework, props, shoring)",
        ],
        "qualifications": [
            "Competent person inspection — before use, during regular periodic inspections, and after any event affecting stability (weather, impact)",
            "Competent person verification — must confirm installation matches design/drawings before any works proceed",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 r.291-297 — structural alterations and temporary support obligations",
            "AS 3610 — Formwork for concrete (referenced under temporary works design)",
            "Design drawings must be up to date, communicated to workers, and available on site",
            "Changes to temporary works design — must be authorised by designer before change is made",
            "Materials/components — inspect before installation; damaged components must not be used",
            "Hoardings and gantries — must comply with local council requirements, approval before erection",
            "Gantry design load — minimum 10kPa live load during construction",
            "Hoardings and fencing — compliant with AS 4687, NATA test certificates required for temporary fencing",
            "Temporary structures incorporating fabric/shade-cloth — flame retardant material required",
        ],
    },

    # ── SCAFFOLD ─────────────────────────────────────────────────────────────
    {
        "keywords": ["scaffold", "scaffolding", "tube and coupler", "kwikstage",
                     "modular scaffold", "swing stage", "suspended scaffold",
                     "hung scaffold", "mast climbing", "perimeter screen scaffold",
                     "birdcage scaffold", "cantilever scaffold", "spur scaffold"],
        "hrcw": True,
        "hrcw_category": "Schedule 3 cl.2 — Work at height with risk of fall >2m",
        "hrcw_license_class": "Scaffolding high risk work licence (class per scaffold type — Basic, Intermediate, or Advanced)",
        "ppe": [
            "Full body harness with double lanyard — when working on incomplete scaffold",
            "Hard hat",
            "Non-slip safety boots",
            "Hi-vis vest",
        ],
        "certs": [
            "Scaffolding high risk work licence — Basic (modular, prefab, bracket, fall arrest)",
            "Scaffolding high risk work licence — Intermediate (cantilever, spur, mast climbing, tube and coupler, perimeter screens)",
            "Scaffolding high risk work licence — Advanced (hung, suspended, cantilevered hoists)",
        ],
        "permits": [
            "Scaffold handover certificate — completed by competent person before scaffold used",
            "Scaffold permit to strip — required before dismantling any scaffold from which a person or object could fall >4m",
        ],
        "qualifications": [
            "Scaffold inspection — competent person with scaffolding licence, before first use and after any incident",
            "30-day periodic inspection — licensed competent person, inspection certificate completed and scaffold tag updated",
            "Changes to scaffold design — authorised and signed off by competent person before changes made",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 r.314-318 — scaffolding licence classes and inspection obligations",
            "AS 4576 — Guidelines for scaffolding",
            "Scaffold >4m fall risk — handover inspection certificate AND scaffold tag required before use",
            "Exclusion zones during erection and dismantling — signage required, nobody below without PPE",
            "Mobile scaffolds — castors locked when in use, not moved with workers on scaffold",
            "Free-standing scaffold max height — 3× least base dimension",
            "Scaffold from which fall >4m possible — re-inspect after severe weather event or impact by plant",
            "Incomplete scaffold left unattended — danger tags and warning signs at access points to prevent unauthorised access",
        ],
    },

    # ── ROOFING ───────────────────────────────────────────────────────────────
    {
        "keywords": ["roofing", "roof installation", "roof sheeting", "metal roofing",
                     "colorbond", "corrugated iron", "roof cladding", "roof fixing",
                     "roof flashing", "guttering", "downpipe", "sarking",
                     "roof insulation", "roof anchor", "roof access"],
        "hrcw": True,
        "hrcw_category": "Schedule 3 cl.2 — Work at height with risk of fall >2m",
        "hrcw_license_class": None,
        "ppe": [
            "Full body harness with double lanyard — all workers on roof surface",
            "Non-slip safety boots — mandatory on roof",
            "Hard hat",
            "Hi-vis vest",
            "UV protection — long sleeves, sunscreen, wide-brim hat where harness permits",
            "Safety glasses — cutting and drilling operations",
        ],
        "certs": [
            "Working at heights — certificate of training (roof work)",
        ],
        "permits": [
            "Roof access permit — before any worker accesses roof",
        ],
        "qualifications": [
            "Anchor point inspection — roof anchors inspected and certified per AS/NZS 1891.4 before use",
            "Perimeter edge protection — installed before workers access roof, maintained throughout",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 r.291-306 — Falls — hierarchy of controls applies to all roof work",
            "AS/NZS 1891.4 — Industrial fall-arrest systems — anchor point requirements",
            "Hold point — roof structure and structural steel erection complete and approved for loading before any materials placed",
            "Hold point — roof structure accepted by roofing subcontractor before commencing",
            "Hold point — roof and wall insulation inspected before covering",
            "Hold point — first roof sheet installed signed off by superintendent/client",
            "Perimeter safety handrails to be installed as per manufacturer requirements before roof access",
            "Roof anchors must be fixed to roof structure as specified — not to cladding or purlins alone",
            "Roofing fixings at required spacing for wind load — per specification; not to be reduced on site",
            "Bolts checked and torque verified 24 hours after erection",
            "Sealant — correct grade, type, and colour; sealed guttering and downpipe joints",
            "Wind conditions — work suspended in sustained winds exceeding safe limit for harness effectiveness",
            "Skylights and penetrations — barricaded or covered before roof access to prevent fall-through",
            "Sarking/insulation certificate of compliance required",
            "Roofing material, roof anchor, and installation warranties required as project documentation",
        ],
    },

    # ── CIVIL INFRASTRUCTURE HAZARD FAMILIES ────────────────────────────────
    # Categories for road works, utility relocation, stormwater, and civil construction.

    # 1. Live road corridor / traffic management
    {
        "keywords": ["live lane", "live road", "live traffic", "traffic management",
                     "traffic corridor", "road works", "lane closure", "road closure",
                     "detour", "traffic control"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.14 — Work on, in or adjacent to a road or traffic corridor",
        "hrcw_license_class": None,
        "ppe": [
            "Hi-vis Class D day/night vest or shirt",
            "Hard hat",
            "Steel-capped safety boots",
        ],
        "certs": [
            "Traffic controller accreditation — current TCS (Traffic Controller) and TCP (Traffic Control Plan) certification",
        ],
        "permits": [
            "Construction Traffic Management Plan (CTMP) — prepared by qualified traffic management designer",
            "Road opening permit — Transport for NSW or local council before any road cut",
            "Lane closure approval — Transport for NSW where state road affected",
        ],
        "qualifications": [
            "Traffic management arrangement accepted by principal contractor before any works in road corridor",
            "Temporary speed zone signs installed and confirmed before workers enter live lane area",
        ],
        "notifications": [
            "SafeWork NSW notification — where road works are notifiable HRCW",
        ],
        "safework_notification": True,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 Sch 3 cl.14 — work on or adjacent to a traffic corridor is HRCW",
            "AS 1742.3 — Traffic control devices for works on roads",
            "Workers must not enter live lane area until traffic management is in place and accepted",
        ],
    },

    # 2. Excavation / trenching >1.5m
    {
        "keywords": ["excavation", "excavate", "trench", "trenching", "dig",
                     "open cut", "service trench", "pipe trench", "drain trench"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.7 — Work in or near a shaft or trench deeper than 1.5m",
        "hrcw_license_class": None,
        "ppe": [
            "Hard hat",
            "Hi-vis vest",
            "Steel-capped safety boots",
        ],
        "certs": [
            "Excavator operator — VOC/Statement of Attainment for plant class",
        ],
        "permits": [
            "Excavation permit — before breaking ground",
            "Dial Before You Dig (DBYD) — completed before any excavation",
            "Service location scan — non-destructive digging (NDD) to prove services before machine excavation",
        ],
        "qualifications": [
            "Competent person — trench inspection before worker entry or approach",
            "Shoring / battering / benching — per geotechnical assessment for depths >1.5m",
            "Spotter — required when excavating near confirmed or suspected services",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 Sch 3 cl.7 — trench or excavation deeper than 1.5m is HRCW",
            "Service proving (potholing) completed before machine excavation in identified service zones",
            "No worker entry to trench >1.5m without shoring, battering, or benching in place",
        ],
    },

    # 3. Utility relocation — water mains (Sydney Water)
    {
        "keywords": ["water main", "sydney water", "water asset", "water relocation",
                     "water pipe", "water service", "water connection"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Hard hat",
            "Hi-vis vest",
            "Steel-capped safety boots",
            "Waterproof gloves — where handling live water connections",
        ],
        "certs": [],
        "permits": [
            "Sydney Water asset protection application — submitted and approved before work commences",
            "Sydney Water representative on site during excavation within 2m of Sydney Water asset",
        ],
        "qualifications": [
            "Sydney Water hold points and witness points satisfied before connection to live main",
            "Minimum clearances — horizontal 1m, vertical 0.5m from any Sydney Water asset",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Sydney Water Act 1994 — damage to assets is an offence, full cost recovery applies",
            "Asset search — sydneywater.com.au asset map before any ground penetration near Sydney Water infrastructure",
            "Uncontrolled water release during connection/disconnection — exclusion zone and dewatering plan required",
        ],
    },

    # 4. Utility relocation — gas mains
    {
        "keywords": ["gas main", "gas pipe", "gas asset", "pressurised gas",
                     "gas service", "gas relocation"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.9 — Work on or near pressurised gas mains or piping",
        "hrcw_license_class": None,
        "ppe": [
            "Hard hat",
            "Hi-vis vest",
            "Steel-capped safety boots",
            "Non-sparking tools — where gas exposure possible",
        ],
        "certs": [],
        "permits": [
            "Gas asset protection — utility owner approval before excavation near gas mains",
            "Dial Before You Dig — gas assets identified before any ground disturbance",
        ],
        "qualifications": [
            "No mechanical excavation within 500mm of confirmed gas main — hand dig only",
            "Gas detection equipment on site and calibrated — continuous monitoring during exposure",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 Sch 3 cl.9 — work on or near pressurised gas mains is HRCW",
            "Gas leak emergency — evacuate, do not use ignition sources, call 000 and gas utility emergency line",
        ],
    },

    # 5. Energised electrical / traffic signals
    {
        "keywords": ["traffic signal", "traffic light", "signal installation",
                     "street lighting", "electrical service", "power cable",
                     "energised cable", "electrical asset"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.11 — Work on or near energised electrical installations",
        "hrcw_license_class": None,
        "ppe": [
            "Insulated gloves — rated for voltage class",
            "Safety glasses — arc flash rated where applicable",
        ],
        "certs": [
            "Licensed electrician — all electrical work by or under supervision of licensed electrical worker",
        ],
        "permits": [
            "Electrical isolation permit — before work on or near energised installations",
            "Traffic signal commissioning acceptance — Transport for NSW or relevant authority before energisation",
        ],
        "qualifications": [
            "Test before touch — all circuits verified de-energised before work",
            "Commissioning sequence documented and accepted by authority before energisation",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 Sch 3 cl.11 — work on or near energised electrical installations is HRCW",
            "Traffic signal energisation requires Transport for NSW or council acceptance before power-on",
        ],
    },

    # 6. Powered mobile plant in road corridor
    {
        "keywords": ["mobile plant", "excavator", "roller", "grader", "loader",
                     "backhoe", "bobcat", "skid steer", "dump truck", "tipper",
                     "road plant", "paving machine", "asphalt paver"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.15 — Work in an area with movement of powered mobile plant",
        "hrcw_license_class": None,
        "ppe": [
            "Hi-vis Class D day/night vest or shirt",
            "Hard hat",
            "Steel-capped safety boots",
        ],
        "certs": [
            "Plant operator — VOC/Statement of Attainment or HRWL for relevant plant class",
        ],
        "permits": [],
        "qualifications": [
            "Plant-pedestrian separation — physical barriers or exclusion zones between mobile plant and workers on foot",
            "Spotter — required when plant operates near workers, structures, or services",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 Sch 3 cl.15 — work in an area with movement of powered mobile plant is HRCW",
            "Plant-pedestrian interaction is the highest-frequency serious incident category on civil sites",
        ],
    },

    # 7. Stormwater / drainage works
    {
        "keywords": ["stormwater", "storm water", "drainage", "stormwater pit",
                     "drainage pit", "culvert", "headwall", "stormwater pipe",
                     "drainage pipe", "stormwater channel"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Hard hat",
            "Hi-vis vest",
            "Steel-capped safety boots",
            "Waterproof gloves",
        ],
        "certs": [],
        "permits": [
            "EPA stormwater controls — erosion and sediment control plan before ground disturbance",
        ],
        "qualifications": [
            "Confined space entry permit — where pit or chamber entry is required",
            "Atmospheric testing — O2 and contaminant levels checked before entry to pits or chambers",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Stormwater pit and chamber entry may trigger confined space HRCW — assess per WHS Reg 2017 Sch 3 cl.6",
            "Erosion and sediment control must be maintained throughout works and until site is stabilised",
        ],
    },

    # 8. Pedestrian interface near live works
    {
        "keywords": ["pedestrian", "footpath", "walkway", "pedestrian crossing",
                     "pedestrian management", "shared path", "pedestrian ramp"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Hi-vis vest",
        ],
        "certs": [],
        "permits": [
            "Pedestrian management plan — maintained throughout works where public pedestrian access is affected",
        ],
        "qualifications": [
            "Temporary pedestrian pathways maintained throughout — minimum 1.2m clear width, DDA compliant",
            "Pedestrian exclusion from active work zones — physical barriers, not just signage",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Pedestrian safety in live road corridor requires continuous management, not just initial setup",
            "Temporary pedestrian detours must be DDA compliant and signed",
        ],
    },

    # 9. Pavement / earthworks / silica standing hazard
    {
        "keywords": ["pavement", "asphalt", "bitumen", "chip seal", "road base",
                     "subbase", "subgrade", "earthworks", "compaction",
                     "road surface", "wearing course", "base course"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "P2 respirator — silica dust during pavement cutting, grinding, or sawing",
            "Hard hat",
            "Hi-vis vest",
            "Steel-capped safety boots",
            "Hearing protection — during compaction and paving operations",
        ],
        "certs": [],
        "permits": [],
        "qualifications": [
            "Compaction testing accepted before next pavement layer placed",
            "Silica dust controls — wet cutting, dust extraction, or RPE where RCS exposure possible",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Respirable crystalline silica (RCS) — SafeWork NSW workplace exposure standard applies to all concrete and pavement cutting",
            "Compaction testing must meet specification requirements before next layer is placed",
        ],
    },

    # ── RETROFIT / FIT-OUT HAZARD FAMILIES ────────────────────────────────────
    # These categories target retrofit, fit-out, and services-installation work
    # in existing buildings. They are NOT new-build construction categories.

    # 1. Structural suitability / slab loading / penetrations
    {
        "keywords": ["slab loading", "structural suitability", "floor loading",
                     "penetration", "core drill", "slab penetration",
                     "fixing into existing", "anchor into concrete",
                     "structural assessment", "load bearing"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Hard hat",
            "Safety glasses — during drilling/cutting",
            "Hearing protection — during core drilling",
            "P2 respirator — silica dust during concrete cutting",
        ],
        "certs": [],
        "permits": [
            "Structural engineer assessment — confirm slab/floor capacity before heavy equipment placed",
            "Penetration permit — before any coring, drilling, or cutting into existing structure",
        ],
        "qualifications": [
            "Existing services scan (GPR or similar) — before any penetration into slab or wall",
            "Structural engineer sign-off — required before loading exceeds design capacity",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Confirm existing slab design load before placing heavy equipment (UPS, generators, cooling plant)",
            "Core drilling into post-tensioned slabs requires specialist assessment — risk of tendon strike",
        ],
    },

    # 2. Heavy plant delivery and movement
    {
        "keywords": ["heavy equipment delivery", "plant delivery", "equipment placement",
                     "forklift", "pallet jack", "loading dock", "heavy lift",
                     "equipment move", "machinery installation", "plant room"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Hard hat",
            "Hi-vis vest",
            "Safety boots — steel capped",
        ],
        "certs": [
            "Forklift licence — LF class where forklift used for equipment movement",
        ],
        "permits": [
            "Traffic management plan — delivery vehicle routes through existing site",
        ],
        "qualifications": [
            "Lift plan — for equipment over 500kg or requiring crane/hoist",
            "Spotter — required when moving heavy equipment through occupied areas",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Confirm floor loading capacity along delivery route — not just final position",
            "Coordinate delivery timing with existing site operations to minimise interface risk",
        ],
    },

    # 3. Existing services / service strike / isolation
    {
        "keywords": ["existing services", "service strike", "service location",
                     "underground services", "dial before you dig",
                     "live services", "service isolation",
                     "unknown services", "concealed services",
                     "hydraulic services", "existing electrical"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Safety glasses",
            "Insulated gloves — if electrical services suspected",
        ],
        "certs": [],
        "permits": [
            "Service location scan — before any penetration, excavation, or drilling",
            "Isolation permit — lock-out tag-out before work on or near existing services",
        ],
        "qualifications": [
            "Service location by competent person — GPR, cable locator, or as-built drawings verified on site",
            "Confirm isolation before breaking into any existing service run",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Existing services may not match as-built drawings — physical verification required",
            "Assume services are live until confirmed isolated and tested dead",
        ],
    },

    # 4. Electrical installation / switchboards / energisation
    {
        "keywords": ["electrical install", "switchboard", "power distribution",
                     "cable tray", "cable pull", "electrical fit",
                     "electrical tie-in", "energisation", "energise",
                     "energize", "power on", "mains connection",
                     "distribution board", "sub-board"],
        "hrcw": True,
        "hrcw_category": "WHS Reg 2017 Sch 3 cl.1 — Work on or near energised electrical installations",
        "hrcw_license_class": None,
        "ppe": [
            "Insulated gloves — rated for voltage class",
            "Safety glasses — arc flash rated where applicable",
            "Arc flash PPE — where risk assessment requires",
        ],
        "certs": [
            "Licensed electrician — all electrical work by or under supervision of licensed electrical worker",
        ],
        "permits": [
            "Electrical isolation permit — lock-out tag-out before work on existing switchboard",
            "Energisation permit — signed by project manager and electrician before first energisation",
        ],
        "qualifications": [
            "Test before touch — all circuits verified de-energised before work",
            "Energisation sequence — documented and approved before power-on",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "WHS Reg 2017 Sch 3 cl.1 — work on or near energised electrical installations is HRCW",
            "Treat all existing circuits as live until proven otherwise",
            "Arc flash risk assessment required for work on switchboards rated >415V",
        ],
    },

    # 5. UPS / battery installation
    {
        "keywords": ["ups ", "ups install", "battery install", "battery room",
                     "uninterruptible power", "battery rack", "lithium battery",
                     "lead acid battery", "battery storage"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Insulated gloves — battery handling",
            "Safety glasses — acid splash or arc flash",
            "Chemical-resistant gloves — where lead-acid batteries handled",
        ],
        "certs": [
            "Licensed electrician — UPS connection and commissioning",
        ],
        "permits": [
            "Structural engineer confirmation — floor loading for battery weight",
        ],
        "qualifications": [
            "Battery handling training — risk of chemical burn (lead-acid) or thermal runaway (lithium)",
            "Ventilation assessment — hydrogen gas accumulation risk for lead-acid battery rooms",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "UPS battery weight may exceed floor design load — confirm before placement",
            "Lead-acid batteries produce hydrogen gas — ventilation per AS/NZS 2676 required",
            "Lithium battery installations require thermal runaway management plan",
        ],
    },

    # 6. HVAC / mechanical plant / cooling systems
    {
        "keywords": ["hvac", "air conditioning", "cooling system", "chiller",
                     "mechanical install", "mechanical fit", "ductwork",
                     "refrigerant", "cooling plant", "air handler",
                     "crac unit", "precision cooling", "mechanical services"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Hard hat — overhead work",
            "Safety glasses",
            "Hearing protection — mechanical plant rooms",
        ],
        "certs": [
            "Refrigerant handling licence — ARC licence for refrigerant work",
        ],
        "permits": [
            "Hot work permit — where brazing or welding refrigerant lines",
            "Crane/hoist permit — where lifting plant to roof or mezzanine",
        ],
        "qualifications": [
            "Refrigerant leak detection — before and after commissioning",
            "Crane lift plan — if rooftop plant placement required",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Refrigerant handling restricted to ARC-licensed technicians",
            "Rooftop plant placement may require crane — separate lift plan and SWMS",
            "Coordinate HVAC commissioning with electrical energisation sequence",
        ],
    },

    # 7. Fire services / suppression / testing
    {
        "keywords": ["fire services", "fire suppression", "sprinkler",
                     "fire detection", "smoke detection", "fire alarm",
                     "gaseous suppression", "fm200", "novec", "inert gas",
                     "fire panel", "vesda", "fire install"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Safety glasses",
            "Hearing protection — during alarm testing",
        ],
        "certs": [
            "Licensed fire protection contractor — fire system design and installation",
        ],
        "permits": [
            "Fire system impairment notice — before isolating existing fire services for tie-in",
            "Hot work permit — where brazing or welding sprinkler lines",
        ],
        "qualifications": [
            "Fire system isolation procedure — building fire panel must be managed during installation",
            "Gaseous suppression commissioning — room integrity test required before system active",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Existing fire services must remain operational during fit-out unless formally impaired",
            "Gaseous suppression systems — ensure room is sealed and warning signage in place before commissioning",
            "Coordinate fire alarm testing with building management and occupants",
        ],
    },

    # 8. Interface with existing operations / occupied site
    {
        "keywords": ["occupied site", "occupied building", "tenanted",
                     "existing operations", "operational facility",
                     "live building", "interface with existing",
                     "shared access", "public access", "tenant"],
        "hrcw": False,
        "hrcw_category": None,
        "hrcw_license_class": None,
        "ppe": [
            "Hi-vis vest — all workers in shared-access areas",
        ],
        "certs": [],
        "permits": [
            "Access management plan — define work zones vs occupied zones",
            "Noise management plan — if work affects existing occupants",
        ],
        "qualifications": [
            "Hoarding / physical separation — between construction zone and occupied area",
            "Communication plan — notify building occupants of work schedule, access restrictions, and emergency procedures",
        ],
        "notifications": [],
        "safework_notification": False,
        "epa_license": False,
        "notes": [
            "Construction zone must be physically separated from occupied areas at all times",
            "Maintain existing emergency egress routes — no blocking of fire stairs or exits",
            "Dust, noise, and fume controls required where work may affect occupants",
        ],
    },

]

# ── Improvement 1: Synonym expansion map ─────────────────────────────────────
# Maps alternate phrasings to canonical keywords present in MATRIX entries.
# Applied as a pre-pass before keyword matching.

SYNONYM_MAP: dict[str, str] = {
    # Asbestos
    "fibro":                    "asbestos cement",
    "super six":                "asbestos cement",
    "asbestos cement sheet":    "asbestos cement",
    "fibrous cement":           "asbestos cement",
    "ac sheet":                 "asbestos cement",
    # Concrete
    "gunite":                   "shotcrete pool",
    "wet-mix concrete":         "shotcrete pool",
    "concrete spraying":        "shotcrete pool",
    "reo":                      "pool reinforcement",
    "reinforcement bar":        "pool rebar",
    # Electrical
    "ewp":                      "elevated work platform",
    "mewp":                     "elevated work platform",
    "scissor lift":             "elevated work platform",
    "switchboard":              "switchboard upgrade",
    # Lifting / cranes
    "franna":                   "mobile crane",
    "pick and carry":           "mobile crane",
    "all terrain crane":        "mobile crane",
    "atc":                      "mobile crane",
    "rigging gear":             "rigging",
    "below the hook":           "rigging",
    # Roofing
    "metal deck":               "metal roofing",
    "roof sheet":               "metal roofing",
    "colorbond":                "colorbond roof",
    "zincalume":                "zincalume roof",
    "corrugated roof":          "metal roofing",
    "box gutter":               "metal roofing",
    # Civil / traffic
    "rms":                      "transport for nsw",
    "roads and maritime":       "transport for nsw",
    "tfnsw":                    "transport for nsw",
    "tcp":                      "traffic control plan",
    "tmp":                      "traffic management plan",
    "tcs":                      "traffic controller",
    "vms":                      "variable message sign",
    "lane closure":             "lane closure",
    # Sydney Water
    "sw asset":                 "sydney water asset",
    "water authority":          "sydney water asset",
    "water corp":               "sydney water asset",
    # Dewatering
    "pump down":                "dewatering",
    "groundwater pump":         "dewatering",
    "site pump":                "sump pump",
    # Demolition
    "strip out":                "strip-out",
    "fit out removal":          "fitout removal",
    "gut the tenancy":          "strip-out",
    # WAH
    "harness work":             "at height",
    # Excavation
    "dig":                      "excavation",
    "trenching":                "excavation",
    "trench":                   "excavation",
    "cut and fill":             "excavation",
    # Masonry / concrete
    "tuckpointing":             "concrete repair",
    "repointing":               "concrete repair",
    "spalling repair":          "concrete repair",
    "crack stitching":          "concrete repair",
    "epoxy injection":          "concrete repair",
    # Waterproofing
    "membrane":                 "waterproofing",
    "tanking":                  "waterproofing",
    "wet area":                 "waterproofing",
    # Hot work
    "oxy cutting":              "hot work",
    "oxy-acetylene":            "hot work",
    "grinding sparks":          "hot work",
    "angle grinder":            "hot work",
    # Concrete grinding → silica (primary hazard is dust, not sparks)
    "angle grinding concrete":  "concrete grinding",
    "surface grinding":         "concrete grinding",
    "floor grinding":           "concrete grinding",
    # Confined space
    "manhole":                  "confined space",
    "pit entry":                "confined space",
    "tank entry":               "confined space",
    "sewer entry":              "confined space",
    # Pool
    "swimming pool":            "pool construction",
    "inground pool":            "pool construction",
    "above ground pool":        "pool construction",
    "fibreglass pool":          "fibreglass pool",
    "concrete pool":            "concrete pool shell",
    "pool plumbing":            "pool hydraulics",
    "pool electrics":           "pool electrical",
    "pool fencing":             "pool barrier",
    # Retail fitout
    "shop fit out":             "retail fitout",
    "tenancy fit out":          "tenancy fitout",
    "commercial fitout":        "retail fitout",
    "office fitout":            "retail fitout",
    "fitout works":             "retail fitout",
    # Structural
    "knock down wall":          "structural alteration class 2",
    "remove load bearing":      "load-bearing",
    "core drill":               "post-tension slab",
    # Hazmat
    "engineered stone":         "silica",
    "benchtop":                 "silica",
    "caesarstone":              "silica",
    # Electrical stream
    "live electrical work":     "energised electrical",
    "working live":             "live electrical",
    "isolation locks":          "lockout",
    "energy isolation":         "lockout",
    "lock and tag":             "lockout",
    "near power lines":         "overhead powerline",
    "close to powerlines":      "overhead powerline",
    "power line exclusion":     "overhead powerline",
    "asp level 2":              "level 2 asp",
    "authorised service":       "level 2 asp",
    "cable locate":             "underground cable",
    # Confined space stream
    "stormwater pit":           "confined space entry",
    "pump station entry":       "confined space entry",
    "below ground entry":       "confined space entry",
    "vault entry":              "confined space entry",
    "gas test":                 "atmospheric testing",
    "gas monitor":              "atmospheric monitoring",
    # Asbestos stream
    "acm inspection":           "asbestos survey",
    "asbestos check":           "asbestos survey",
    "friable removal":          "class a removal",
    "non-friable removal":      "class b removal",
    "bonded asbestos":          "class b removal",
    "seal over asbestos":       "asbestos encapsulat",
    "paint asbestos":           "asbestos encapsulat",
    "found asbestos":           "unexpected asbestos",
    "suspected acm":            "unexpected asbestos",
    # Crane and lifting stream
    "crane lift":               "mobile crane lift",
    "lift plan":                "mobile crane lift",
    "dogman":                   "mobile crane lift",
    "cherry picker":            "ewp boom",
    "knuckle boom":             "ewp boom",
    "articulated boom":         "ewp boom",
    "vertical lift":            "scissor lift",
    # Formwork stream
    "concrete pour":            "formwork",
    "temporary propping":       "falsework",
    "temp works":               "falsework",
    # Fire systems stream
    "isolate sprinklers":       "sprinkler isolation",
    "sprinkler impairment":     "sprinkler isolation",
    "fire stopping":            "passive fire",
    "penetration sealing":      "passive fire",
    "fire collar":              "passive fire",
    "welding near sprinkler":   "hot work suppression",
    # ── Block 4b Batch 1 — SYNONYM_MAP additions (Section 12) ────────────────
    # Rope access stream
    "rope access":              "rope access",
    "abseiling":                "rope access",
    "rappelling":               "rope access",
    "irata":                    "rope access",
    "facade access rope":       "rope access",
    # Tower crane stream
    "tower crane":              "tower crane",
    "luffing jib":              "tower crane",
    "luffing crane":            "tower crane",
    "hammerhead crane":         "tower crane",
    "self-erecting crane":      "tower crane",
    # Precast/tilt-up stream
    "tilt-up":                  "precast",
    "tilt up":                  "precast",
    "tilt panel":               "precast",
    "precast panel":            "precast",
    "concrete panel":           "precast",
    "panel erection":           "precast",
    "precast beam":             "precast",
    "precast column":           "precast",
    # Mobile plant stream
    "bobcat":                   "mobile plant",
    "skid steer":               "mobile plant",
    "telehandler":              "mobile plant",
    "posi-track":               "mobile plant",
    "loader":                   "mobile plant",
    "backhoe":                  "mobile plant",
    "grader":                   "mobile plant",
    "roller":                   "mobile plant",
    "compactor":                "mobile plant",
    "spider hoist":             "mobile plant",
    "materials hoist":          "mobile plant",
    # Underground services stream
    "dbyd":                     "underground services",
    "dial before you dig":      "underground services",
    "service locate":           "underground services",
    "potholing":                "underground services",
    "buried services":          "underground services",
    "underground cable":        "underground services",
    "underground pipe":         "underground services",
    # Overhead powerline stream
    "power pole":               "overhead powerline",
    "power line":               "overhead powerline",
    "powerline":                "overhead powerline",
    "overhead cable":           "overhead powerline",
    "aerial bundle cable":      "overhead powerline",
    "ausgrid":                  "overhead powerline",
    "essential energy":         "overhead powerline",
    # ── Block 4b Batch 2 — SYNONYM_MAP additions (Section 10) ────────────────
    # Scaffold stream
    "staging":                      "scaffold",
    "tube and coupler scaffold":    "scaffold",
    "kwikstage":                    "scaffold",
    "suspended scaffold":           "scaffold",
    "swing stage":                  "scaffold",
    "scaffold erection":            "scaffold",
    "scaffold dismantling":         "scaffold",
    "perimeter screen":             "scaffold",
    "birdcage":                     "scaffold",
    # Temporary works stream
    "shoring":                      "temporary works",
    "propping":                     "temporary works",
    "façade retention":             "temporary works",
    "facade retention":             "temporary works",
    "needling":                     "temporary works",
    "tower crane base":             "temporary works",
    "piling platform":              "temporary works",
    "overhead protection":          "temporary works",
    "site hoarding":                "temporary works",
    # Masonry stream
    "brickwork":                    "masonry wall",
    "blockwork":                    "masonry wall",
    "brick wall":                   "masonry wall",
    "block wall":                   "masonry wall",
    # Concrete pour stream
    "concrete placement":           "concrete pour",
    "slab pour":                    "concrete pour",
    "footing pour":                 "concrete pour",
    "concrete deck":                "concrete pour",
    # Post-tensioning stream
    "post tension":                 "post tensioning",
    "pt slab":                      "post tensioning",
    "stressed slab":                "post tensioning",
    "prestressed":                  "post tensioning",
    "tendon stressing":             "post tensioning",
    "stressing records":            "post tensioning",
    # Roofing stream
    "roof sheeting":                "roofing",
    "colorbond roofing":            "roofing",
    "metal roof":                   "roofing",
    "roof cladding":                "roofing",
    "roof flashings":               "roofing",
    "guttering":                    "roofing",
    "downpipes":                    "roofing",
    "sarking":                      "roofing",
    "roof insulation installation": "roofing",
    "roof anchors":                 "roofing",

    # Retrofit / fit-out synonyms
    "data centre":                  "electrical install",
    "data center":                  "electrical install",
    "server room":                  "electrical install",
    "comms room":                   "electrical install",

    # Civil infrastructure synonyms
    "road upgrade":                 "road works",
    "road widening":                "road works",
    "lane widening":                "road works",
    "4 lanes":                      "road works",
    "four lanes":                   "road works",
    "chip seal":                    "pavement",
    "t-intersection":               "intersection",
    "t intersection":               "intersection",
    "stormwater works":             "stormwater",
}


# ── Improvement 2: Inference chaining map ────────────────────────────────────
# Maps a keyword present in one category to additional keywords that should
# also be injected into the expanded description, triggering related categories
# automatically without them appearing in the original description.

CHAIN_MAP: dict[str, list[str]] = {
    # Commercial kitchen always needs grease trap + hvac canopy
    "commercial kitchen":       ["grease trap", "retail hvac", "food premises"],
    "food premises":            ["grease trap", "retail hvac"],
    "cafe fitout":              ["grease trap", "food premises", "retail hvac"],
    "restaurant fitout":        ["grease trap", "food premises", "retail hvac"],
    "food court fitout":        ["grease trap", "food premises", "retail hvac"],
    # Pool construction always needs barrier, hydraulics, registration
    "pool construction":        ["pool barrier", "pool hydraulics", "pool registration"],
    "inground pool":            ["pool barrier", "pool hydraulics", "pool excavation"],
    "fibreglass pool":          ["pool barrier", "pool hydraulics", "fibreglass pool"],
    "concrete pool shell":      ["pool barrier", "pool hydraulics", "pool excavation"],
    "shotcrete pool":           ["pool barrier", "pool hydraulics"],
    # Swing stage always needs WAH + rescue plan
    "swing stage":              ["at height", "rescue plan"],
    # Asbestos fibro often has lead paint too
    "asbestos cement":          ["lead paint"],
    # Scaffolding needs WAH
    "scaffolding":              ["at height"],
    # Demolition needs hazmat survey + WAH (Batch 1 merged)
    "demolition":               ["hazardous materials survey", "working at height"],
    "strip-out":                ["hazardous materials survey"],
    "fitout removal":           ["hazardous materials survey"],
    # Concrete grinding generates silica dust — primary hazard
    "concrete grinding":        ["silica"],
    # Rock breaking generates silica and vibration
    "rock break":               ["silica", "vibration"],
    "rock hammer":              ["silica"],
    "pool excavation":          ["dewatering", "underground services"],
    # PT slab needs engineer
    "post-tension":             ["structural engineer", "post-tension slab"],
    "post tension":             ["structural engineer", "post-tension slab"],
    # Mezzanine needs fire engineer
    "mezzanine":                ["fire sprinkler", "structural engineer"],
    # Class 2 structural needs strata
    "structural alteration class 2": ["strata", "owners corporation"],
    # Confined space needs rescue
    "confined space":           ["atmospheric test", "rescue plan"],
    # Crane lifts need dogman
    "mobile crane":             ["dogging", "rigging", "lift study"],
    # Waterway needs erosion
    "near waterway":            ["erosion", "sediment"],
    "near creek":               ["erosion", "sediment"],
    # Sewer discharge needs trade waste
    "discharge to sewer":       ["trade waste", "sydney water"],
    # Night work needs fatigue and lighting
    "night work":               ["fatigue", "lighting plan"],
    # Occupied building needs resident management
    "occupied":                 ["resident", "noise"],
    # Solar panels need bonding
    "solar panel":              ["equipotential bonding"],
    # Acid sulfate near waterway
    "acid sulfate":             ["near waterway"],
    # Class 2 apartment needs principal contractor
    "apartment construction":   ["principal contractor class 2", "strata"],
    # Retail fitout baseline
    "retail fitout":            ["principal certifier"],
    "tenancy fitout":           ["principal certifier"],
    # ── Block 4b Batch 1 — CHAIN_MAP additions (Section 13) ──────────────────
    # Rope access always triggers WAH and rescue plan
    "rope access":              ["working at height", "rescue plan", "fall prevention"],
    # Tower crane triggers crane and WAH (erection involves height)
    "tower crane":              ["mobile crane", "working at height"],
    # Precast/tilt-up triggers crane (you need a crane to erect panels)
    "precast":                  ["mobile crane", "working at height"],
    "tilt-up":                  ["mobile crane", "working at height"],
    # Underground services triggers overhead powerline check
    "underground services":     ["overhead powerline"],
    # Mobile plant triggers exclusion zone and VOC
    "mobile plant":             ["exclusion zone", "voc"],
    # Any crane lift triggers dogging/rigging and exclusion zone
    "crane lift":               ["dogging", "rigging", "exclusion zone"],
    "lift study":               ["mobile crane"],
    # ── Block 4b Batch 2 — CHAIN_MAP additions (Section 11) ──────────────────
    # Scaffold chains — scaffold work always involves WAH and requires exclusion zones
    "scaffold":                 ["working at height", "fall prevention", "exclusion zone"],
    # Temporary works chain — engineered TW requires fall prevention consideration
    "temporary works":          ["fall prevention"],
    "shoring":                  ["temporary works", "working at height"],
    "propping":                 ["temporary works"],
    # Masonry bracing chain — masonry construction triggers silica (cutting) and WAH (if elevated)
    "masonry wall":             ["silica", "cutting grinding"],
    # Concrete pour chains — pour requires formwork, which may require WAH
    "concrete pour":            ["formwork"],
    # Post-tensioning chain — PT always involves concrete pour and formwork strip
    "post tensioning":          ["concrete pour", "formwork"],
    # Roofing chains — always WAH, may involve overhead services (skylights/electrical)
    "roofing":                  ["working at height", "fall prevention", "roof edge protection"],

    # Retrofit / fit-out chains — data centre triggers related services
    "data centre":              ["electrical install", "ups ", "hvac", "fire services",
                                 "existing services", "slab loading", "heavy equipment delivery"],
    "data center":              ["electrical install", "ups ", "hvac", "fire services",
                                 "existing services", "slab loading", "heavy equipment delivery"],
    "server room":              ["electrical install", "ups ", "hvac", "fire services",
                                 "existing services"],
    "electrical install":       ["existing services"],

    # Civil infrastructure chains
    "road works":               ["live lane", "mobile plant", "pavement", "pedestrian"],
    "live lane":                ["traffic management", "mobile plant", "pedestrian"],
    "intersection":             ["traffic signal", "pedestrian", "traffic management"],
    "sydney water":             ["water main", "excavation"],
    "asset relocation":         ["excavation", "live lane"],
}


# ── Improvement 3: Negation patterns ─────────────────────────────────────────
# If these patterns precede a keyword in the description, suppress that category.

NEGATION_PREFIXES = (
    "no ", "not ", "without ", "none ", "zero ", "absent ",
    "confirmed no ", "survey confirmed ", "no identified ",
    "has been removed", "previously removed", "not present",
    "not applicable", "n/a",
)

# Broader exclusion/variation context — keywords mentioned in these contexts
# should be treated as latent conditions, not confirmed scope.
_EXCLUSION_CONTEXT_PATTERNS = (
    "subject to additional cost",
    "deemed variation",
    "latent condition",
    "variation to the contract",
    "additional costs and time",
    "subject to additional",
    "excluded from",
    "not included in",
    "outside the scope",
    "not part of the scope",
    "if uncovered during",
    "if identified during",
    "pre-existing toxic",
)


def _expand_description(text: str) -> str:
    """
    Improvement 1+2: Apply synonym expansion and inference chaining.
    Returns an augmented lowercase text string with additional trigger
    keywords injected, ready for matching.
    """
    expanded = text

    # Synonym pass — replace alternate phrasings with canonical keywords
    for synonym, canonical in SYNONYM_MAP.items():
        if synonym in expanded:
            expanded = expanded + " " + canonical

    # Chaining pass — inject downstream keywords for matched triggers
    # Run twice to allow one level of chaining (A→B, B→C)
    for _ in range(2):
        additions = []
        for trigger, downstream in CHAIN_MAP.items():
            if trigger in expanded:
                for kw in downstream:
                    if kw not in expanded:
                        additions.append(kw)
        if additions:
            expanded = expanded + " " + " ".join(additions)
        else:
            break

    return expanded


def _is_negated(keyword: str, text: str) -> bool:
    """
    Improvement 4: Check if a keyword is negated or appears in an
    exclusion/variation/latent-condition context.
    Returns True if keyword should be suppressed.
    """
    idx = text.find(keyword)
    if idx == -1:
        return False
    # Check direct negation (within 60 chars before)
    preceding = text[max(0, idx - 60):idx]
    if any(neg in preceding for neg in NEGATION_PREFIXES):
        return True
    # Check broader exclusion/variation context (within 200 chars around)
    context = text[max(0, idx - 200):idx + len(keyword) + 200].lower()
    if any(pat in context for pat in _EXCLUSION_CONTEXT_PATTERNS):
        return True
    return False


def _normalise_item(item: str) -> str:
    """
    Improvement 5: Return a normalised version of a list item for
    deduplication — lowercase, strip leading category prefix (before —),
    collapse whitespace, remove punctuation noise.
    """
    # Take just the first meaningful segment before any dash separator
    core = re.split(r"\s+—\s+|\s+-\s+", item.lower())[0]
    core = re.sub(r"[^a-z0-9 ]", "", core)
    core = re.sub(r"\s+", " ", core).strip()
    return core


def _dedup_list(items: list[str]) -> list[str]:
    """
    Improvement 5: Remove near-duplicate items from a merged list.
    Keeps first occurrence when normalised forms are identical or one
    normalised form is a substring of another (≥12 chars).
    """
    seen_normalised: list[str] = []
    output: list[str] = []
    for item in items:
        norm = _normalise_item(item)
        # Exact normalised duplicate
        if norm in seen_normalised:
            continue
        # Substring duplicate — suppress if a longer seen item contains this norm
        # or this norm contains a seen item (both ≥12 chars to avoid false matches)
        skip = False
        if len(norm) >= 12:
            for seen in seen_normalised:
                if len(seen) >= 12 and (norm in seen or seen in norm):
                    skip = True
                    break
        if skip:
            continue
        seen_normalised.append(norm)
        output.append(item)
    return output


# ── Improvement 6 — confidence scoring ───────────────────────────────────────
# Score each MATRIX entry against the expanded description.
# Multi-word phrases score higher than single words.
# Categories below CONFIDENCE_THRESHOLD are suppressed.

CONFIDENCE_THRESHOLD = 1.0   # minimum score to include a category

def _score_entry(entry: dict, expanded_text: str) -> float:
    """
    Return a confidence score for a MATRIX entry against the expanded text.
    Multi-word keywords (phrase hits) score 2.0, single-word hits score 1.0.
    Score is the sum of all hits — first hit already meets threshold.
    """
    score = 0.0
    for kw in entry["keywords"]:
        if kw in expanded_text:
            words = kw.strip().split()
            score += 2.0 if len(words) >= 2 else 1.0
    return score


# ── Master inference engine ───────────────────────────────────────────────────

def infer_requirements(work_description: str) -> Requirements:
    """
    Infer mandatory WHS requirements from a plain-text work description.

    Improvements applied:
      1. Synonym expansion   — alternate phrasings mapped to canonical keywords
      2. Inference chaining  — matched categories trigger related categories
      3. Negation detection  — "no asbestos" suppresses asbestos category
      4. Deduplication       — near-duplicate PPE/cert/permit items collapsed
      5. Confidence scoring  — weighted match score, threshold filters noise
      6. Claude API pass     — available via infer_with_claude() for /infer endpoint

    Returns a Requirements object with all matched fields populated.
    """
    original_text = work_description.lower()

    # Improvement 1+2: expand synonyms and inject chained keywords
    expanded = _expand_description(original_text)

    result = Requirements()
    result.ppe = list(BASELINE_PPE)
    result.certs = list(BASELINE_CERTS)

    for entry in MATRIX:
        # Improvement 5: score-based matching — must exceed threshold
        score = _score_entry(entry, expanded)
        if score < CONFIDENCE_THRESHOLD:
            continue

        # Improvement 3: negation check — suppress if primary keyword is negated
        # Check against the ORIGINAL text only (not expanded, to avoid false suppression)
        primary_kw = entry["keywords"][0]
        if _is_negated(primary_kw, original_text):
            continue

        # Merge matched entry into result
        if entry["hrcw"]:
            result.hrcw = True
        if entry["hrcw_category"] and not result.hrcw_category:
            result.hrcw_category = entry["hrcw_category"]
        if entry["hrcw_license_class"] and not result.hrcw_license_class:
            result.hrcw_license_class = entry["hrcw_license_class"]
        for item in entry["ppe"]:
            if item not in result.ppe:
                result.ppe.append(item)
        for item in entry["certs"]:
            if item not in result.certs:
                result.certs.append(item)
        for item in entry["permits"]:
            if item not in result.permits:
                result.permits.append(item)
        for item in entry["qualifications"]:
            if item not in result.qualifications:
                result.qualifications.append(item)
        for item in entry["notifications"]:
            if item not in result.notifications:
                result.notifications.append(item)
        if entry["safework_notification"]:
            result.safework_notification = True
        if entry["epa_license"]:
            result.epa_license = True
        for item in entry.get("notes", []):
            if item not in result.notes:
                result.notes.append(item)

    # Suppress hot work when silica/concrete grinding is the primary activity
    # and no actual hot work keywords (welding, oxy, torch, cutting metal) are present
    _HOT_WORK_CONFIRM = [r"\bweld", r"\boxy\b", r"\bacetylene\b", r"\btorch\b",
                         r"\bbraz", r"\bsolder", r"\bcutting metal", r"\bmetal cutting",
                         r"\bplasma cut"]
    _is_silica_primary = any(k in expanded for k in
        ("silica", "concrete grinding", "concrete cutting", "masonry cutting"))
    _has_real_hot_work = any(re.search(pat, original_text) for pat in _HOT_WORK_CONFIRM)
    if _is_silica_primary and not _has_real_hot_work:
        _HOT_PHRASES = {"hot work", "welding", "fire watch", "fire warden",
                        "flame", "ignition", "flammable"}
        result.ppe = [p for p in result.ppe
                      if not any(hw in p.lower() for hw in _HOT_PHRASES)]
        result.certs = [c for c in result.certs
                        if not any(hw in c.lower() for hw in _HOT_PHRASES)]
        result.permits = [p for p in result.permits
                          if not any(hw in p.lower() for hw in _HOT_PHRASES)]
        result.qualifications = [q for q in result.qualifications
                                 if not any(hw in q.lower() for hw in _HOT_PHRASES)]
        result.notes = [n for n in result.notes
                        if not any(hw in n.lower() for hw in _HOT_PHRASES)]

    # Improvement 4: deduplicate all merged lists
    result.ppe           = _dedup_list(result.ppe)
    result.certs         = _dedup_list(result.certs)
    result.permits       = _dedup_list(result.permits)
    result.qualifications = _dedup_list(result.qualifications)
    result.notifications = _dedup_list(result.notifications)
    result.notes         = _dedup_list(result.notes)

    # Infer plant and equipment from matched keywords and licence class
    _PLANT_RULES = [
        (lambda: result.hrcw_license_class and "ewp" in result.hrcw_license_class.lower(),
         "Elevated Work Platform (EWP)"),
        (lambda: any(k in expanded for k in ("scaffold", "mobile scaffold")),
         "Scaffolding"),
        (lambda: any(k in expanded for k in ("crane", "rigging", "franna")),
         "Mobile crane"),
        (lambda: any(k in expanded for k in ("concrete", "grinding", "grinder", "angle grind")),
         "Angle grinder"),
        (lambda: any(k in expanded for k in ("concrete saw", "concrete cut", "demolition saw")),
         "Concrete saw"),
        (lambda: any(k in expanded for k in ("excavat", "trench", "dig")),
         "Excavator"),
        (lambda: any(k in expanded for k in ("traffic", "tcp", "traffic control")),
         "Traffic control equipment"),
    ]
    for check, item in _PLANT_RULES:
        if check() and item not in result.plant:
            result.plant.append(item)

    # Compute individual HRCW boolean flags for checkbox ticking
    result.hrcw_flags = {}
    # falling_2m — from keywords or category
    result.hrcw_flags["falling_2m"] = any(k in expanded for k in (
        "at height", "above ground", "elevated", "roof", "ewp", "boom lift",
        "scissor lift", "cherry picker", "ladder", "scaffold", "platform",
        "mezzanine", "working at heights"))
    # tiltup_precast
    result.hrcw_flags["tiltup_precast"] = any(k in expanded for k in (
        "tilt-up", "tilt up", "tiltup", "precast", "precast concrete",
        "tilt-up panel", "precast panel", "concrete panel", "panel erection"))
    # mobile_plant
    result.hrcw_flags["mobile_plant"] = any(k in expanded for k in (
        "crane", "mobile crane", "franna", "ewp", "boom lift", "scissor lift",
        "cherry picker", "mobile plant", "forklift", "telehandler", "excavat"))
    # demolition
    result.hrcw_flags["demolition"] = any(k in expanded for k in (
        "demolition", "demolish", "strip out", "strip-out"))
    # asbestos
    result.hrcw_flags["asbestos"] = any(k in expanded for k in (
        "asbestos", "acm", "fibro", "asbestos cement"))
    # confined_space
    result.hrcw_flags["confined_space"] = any(k in expanded for k in (
        "confined space", "confined", "tank entry", "sewer", "manhole"))
    # electrical
    result.hrcw_flags["electrical"] = any(k in expanded for k in (
        "electrical", "live electrical", "switchboard", "high voltage"))
    # shaft_trench
    result.hrcw_flags["shaft_trench"] = any(k in expanded for k in (
        "trench", "shaft", "tunnel", "excavat"))
    # chemical_fuel
    result.hrcw_flags["chemical_fuel"] = any(k in expanded for k in (
        "chemical", "fuel", "flammable", "combustible"))
    # traffic_corridor
    result.hrcw_flags["traffic_corridor"] = any(k in expanded for k in (
        "traffic", "roadway", "road work", "public road"))
    # temp_support
    result.hrcw_flags["temp_support"] = any(k in expanded for k in (
        "temporary support", "falsework", "propping"))

    return result


async def infer_with_claude(work_description: str, api_key: str = "") -> dict:
    """
    Improvement 6: Claude API reasoning pass for the /infer endpoint.
    Runs keyword inference first, then asks Claude to validate and refine.
    Async — not used in the synchronous SWMS pipeline.
    Requires httpx: pip install httpx
    """
    import json as _json
    try:
        import httpx
    except ImportError:
        return infer_to_dict(work_description)

    # Step 1: fast keyword pre-filter
    keyword_result = infer_to_dict(work_description)

    # Step 2: Claude reasoning pass
    system_prompt = (
        "You are an Australian WHS compliance expert specialising in NSW construction. "
        "You will receive a work description and a preliminary inference result from a "
        "keyword matching system. Your job is to:\n"
        "1. Confirm which inferred requirements genuinely apply\n"
        "2. Add any requirements the keyword system missed\n"
        "3. Remove any requirements that are clearly inapplicable\n"
        "4. Return ONLY a valid JSON object with the same keys as the input result.\n"
        "Do not add commentary. Return only the JSON object."
    )

    user_prompt = (
        f"Work description: {work_description}\n\n"
        f"Keyword inference result:\n{_json.dumps(keyword_result, indent=2)}\n\n"
        "Return the corrected JSON object."
    )

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json={
                    "model": MODEL,
                    "max_tokens": 2048,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
            )
        data = resp.json()
        text = data["content"][0]["text"].strip()
        # Strip markdown fences if present
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        return _json.loads(text)
    except Exception:
        # Fallback to keyword result if Claude pass fails
        return keyword_result


def infer_to_dict(work_description: str, jurisdiction: str = "AU") -> dict:
    """Return inference result as a plain dict for JSON serialisation."""
    r = infer_requirements(work_description)
    result = {
        "hrcw": r.hrcw,
        "hrcw_category": r.hrcw_category,
        "hrcw_license_class": r.hrcw_license_class,
        "hrcw_flags": getattr(r, "hrcw_flags", {}),
        "safework_notification_required": r.safework_notification,
        "epa_license_required": r.epa_license,
        "ppe": r.ppe,
        "certifications": r.certs,
        "permits": r.permits,
        "qualifications": r.qualifications,
        "notifications": r.notifications,
        "regulatory_notes": r.notes,
        "plant": r.plant,
        "jurisdiction": jurisdiction,
        "jurisdiction_notes": [],
    }

    # Append jurisdiction-specific regulatory notes based on matched categories
    if jurisdiction != "AU":
        result["jurisdiction_notes"] = _jurisdiction_notes(
            jurisdiction, work_description.lower(), result
        )

    return result


def _jurisdiction_notes(jurisdiction: str, text: str, inference: dict) -> list[str]:
    """Generate jurisdiction-specific regulatory notes based on matched hazard categories."""
    notes: list[str] = []

    if jurisdiction == "NZ":
        notes.append("Health and Safety at Work Act 2015 (HSWA) — PCBU duties")
        if inference.get("hrcw"):
            notes.append("WorkSafe NZ Approved Code of Practice applies to this high-risk work")
        if any(k in text for k in ("asbestos", "fibro", "ace sheet")):
            notes.append("WorkSafe NZ ACP: Management and Removal of Asbestos")
        if any(k in text for k in ("height", "elevated", "roof", "scaffold", "ewp", "ladder")):
            notes.append("WorkSafe NZ ACP: Working at Height")
        if any(k in text for k in ("confined space", "confined", "tank", "vessel")):
            notes.append("WorkSafe NZ ACP: Confined Spaces")
        if any(k in text for k in ("crane", "rigging", "lift", "hoist")):
            notes.append("WorkSafe NZ ACP: Cranes")
        if any(k in text for k in ("excavat", "trench", "dig")):
            notes.append("WorkSafe NZ ACP: Excavation Safety")
        if any(k in text for k in ("electri", "power", "switchboard", "cable")):
            notes.append("Electricity Act 1992 (NZ)")

    elif jurisdiction == "UK":
        notes.append("CDM Regulations 2015 — Principal Designer and Principal Contractor duties")
        if any(k in text for k in ("chemical", "hazardous substance", "solvent", "epoxy", "resin")):
            notes.append("COSHH Regulations 2002 — Control of Substances Hazardous to Health")
        if any(k in text for k in ("height", "elevated", "roof", "scaffold", "ewp", "ladder")):
            notes.append("Work at Height Regulations 2005")
        if any(k in text for k in ("confined space", "confined", "tank", "vessel")):
            notes.append("Confined Spaces Regulations 1997")
        if any(k in text for k in ("asbestos", "fibro")):
            notes.append("Control of Asbestos Regulations 2012")
        if any(k in text for k in ("silica", "dust", "grinding", "cutting")):
            notes.append("BS EN 689 — Workplace exposure assessment")
        if any(k in text for k in ("scaffold",)):
            notes.append("BS EN 12811 — Temporary works equipment: Scaffolds")

    elif jurisdiction == "US":
        notes.append("OSHA 29 CFR 1926 — Construction Industry Standards")
        if any(k in text for k in ("fall", "height", "elevated", "roof", "scaffold", "ewp", "ladder")):
            notes.append("29 CFR 1926.502 — Fall Protection Systems Criteria")
        if any(k in text for k in ("scaffold",)):
            notes.append("29 CFR 1926.451 — Scaffolds — General Requirements")
        if any(k in text for k in ("excavat", "trench", "dig")):
            notes.append("29 CFR 1926.651 — Excavations — General Requirements")
        if any(k in text for k in ("confined space", "confined", "tank", "vessel")):
            notes.append("29 CFR 1926.1201 — Confined Spaces in Construction")
        if any(k in text for k in ("crane", "rigging", "hoist")):
            notes.append("29 CFR 1926.1400 — Cranes and Derricks in Construction")
        if any(k in text for k in ("silica", "grinding", "cutting", "concrete")):
            notes.append("29 CFR 1926.1153 — Respirable Crystalline Silica")
        if any(k in text for k in ("asbestos", "fibro")):
            notes.append("29 CFR 1926.1101 — Asbestos")
        if any(k in text for k in ("electri", "power", "switchboard", "cable")):
            notes.append("29 CFR 1926.400 — Electrical — General Requirements")

    elif jurisdiction == "CA":
        notes.append("Canada Labour Code Part II — employer duties")
        notes.append("WHMIS 2015 — Hazardous Products Regulations")
        if any(k in text for k in ("confined space", "confined", "tank", "vessel")):
            notes.append("CSA Z1006 — Management of Work in Confined Spaces")
        if any(k in text for k in ("height", "elevated", "roof", "scaffold", "ewp", "ladder")):
            notes.append("Fall protection requirements per provincial OHS regulation")
        if any(k in text for k in ("excavat", "trench", "dig")):
            notes.append("Excavation and trenching requirements per provincial OHS regulation")
        if any(k in text for k in ("asbestos", "fibro")):
            notes.append("Provincial asbestos abatement regulations apply")
        if any(k in text for k in ("silica", "grinding", "cutting", "concrete")):
            notes.append("Silica exposure limits per provincial OHS regulation")
        if any(k in text for k in ("crane", "rigging", "hoist")):
            notes.append("CSA Z150 — Safety Code on Mobile Cranes")
        if any(k in text for k in ("electri", "power", "switchboard", "cable")):
            notes.append("CSA C22.1 — Canadian Electrical Code")

    return notes


# ── Risk Assessment hazard list generation ───────────────────────────────────

def _risk_level(score: int) -> str:
    """Return risk level string from L x C score."""
    if score >= 17:
        return "Extreme"
    elif score >= 10:
        return "High"
    elif score >= 5:
        return "Medium"
    else:
        return "Low"


# ── SWMS Scope Classifier ─────────────────────────────────────────────────────

def classify_swms_scope(description: str) -> dict:
    """
    Deterministic scope classifier for SWMS input.
    Returns {job_type, building_context, occupancy_context, scope_modifiers}.
    """
    text = description.lower()

    # — Job type (first match wins, ordered by specificity) —
    _JOB_TYPE_RULES = [
        ("demolition",   ["demolition", "demolish", "strip out", "strip-out", "pull down"]),
        ("remedial",     ["remedial", "spalling", "concrete repair", "facade repair",
                          "crack repair", "patch repair", "protective coating"]),
        ("fit_out",      ["fit-out", "fit out", "fitout", "installing into", "install into",
                          "data centre", "data center", "server room", "tenant fit",
                          "shop fit", "office fit"]),
        ("retrofit",     ["retrofit", "retro-fit", "refurbish", "renovation",
                          "upgrade existing", "modify existing"]),
        ("maintenance",  ["maintenance", "repair", "service existing", "replace existing",
                          "routine inspection"]),
        ("civil_infrastructure", ["road works", "road work", "road upgrade", "road widening",
                          "lane widening", "live lane", "road construction", "civil works",
                          "intersection", "stormwater works", "pavement"]),
        ("upgrade",      ["upgrade", "extension", "addition"]),
        ("new_build",    ["new build", "new construction", "greenfield", "ground-up",
                          "erect", "erection", "pour slab", "formwork"]),
    ]
    job_type = "new_build"
    for jt, keywords in _JOB_TYPE_RULES:
        if any(kw in text for kw in keywords):
            job_type = jt
            break

    # — Building context —
    _EXISTING = ["existing", "into an existing", "occupied", "operational",
                 "current building", "live building"]
    _NEW = ["new build", "greenfield", "ground-up", "vacant lot"]
    has_existing = any(s in text for s in _EXISTING)
    has_new = any(s in text for s in _NEW)
    building_context = "mixed" if (has_existing and has_new) else ("existing" if has_existing else "new")

    # — Occupancy context —
    _OCCUPIED = ["occupied", "tenanted", "residents", "occupants", "live building",
                 "operational", "strata"]
    _UNOCCUPIED = ["unoccupied", "vacant", "empty building"]
    has_occ = any(s in text for s in _OCCUPIED)
    has_unocc = any(s in text for s in _UNOCCUPIED)
    occupancy_context = "mixed" if (has_occ and has_unocc) else ("occupied" if has_occ else "unoccupied")

    # — Scope modifiers —
    _MODIFIER_RULES = {
        "facade_work":       ["facade", "external wall", "external envelope", "curtain wall",
                              "cladding", "render", "external render"],
        "scaffold_access":   ["scaffold", "scaffolding"],
        "rope_access":       ["rope access", "abseil", "irata"],
        "ewp_access":        ["ewp", "elevated work platform", "boom lift", "scissor lift",
                              "cherry picker"],
        "work_at_height":    ["work at height", "working at height", "above 2m",
                              "above 2 metres", "fall risk"],
        "residential":       ["residential", "apartment", "unit", "dwelling", "house"],
        "commercial":        ["commercial", "office", "retail", "shop"],
        "strata":            ["strata", "body corporate", "owners corporation"],
        "external_envelope": ["facade", "external wall", "roof", "balcony", "balustrade"],
        "concrete_repair":   ["spalling", "concrete repair", "crack repair", "patch",
                              "concrete cancer", "carbonation"],
        "waterproofing":     ["waterproof", "membrane", "sealant", "balcony waterproof"],
        "protective_coating": ["protective coating", "anti-carbonation", "paint system",
                               "coating system"],
        "occupied_interface": ["occupied", "residents", "tenants", "strata",
                               "body corporate", "occupants"],
        "high_rise":         ["storey", "story", "floor", "level", "high-rise", "high rise",
                              "multi-storey", "multi-story"],
        "ewp_transfer":      ["ewp transfer", "transfer to roof", "transfer from ewp",
                              "guardrail opening", "platform to roof", "roof transfer",
                              "transfer through guardrail", "transfer via guardrail"],
        "civil_infrastructure": ["road works", "road work", "road upgrade", "road widening",
                                  "lane widening", "intersection", "roundabout", "road construction",
                                  "road corridor", "road pavement", "civil works", "civil construction"],
        "road_corridor":     ["road", "lane", "live lane", "traffic corridor", "carriageway",
                              "roadway", "road reserve"],
        "live_lanes":        ["live lane", "live traffic", "live road", "live works"],
        "utility_relocation": ["asset relocation", "service relocation", "utility relocation",
                               "water main", "sydney water", "gas main", "sewer",
                               "service diversion", "pipe relocation"],
        "stormwater":        ["stormwater", "storm water", "drainage", "stormwater pit",
                              "drainage pit", "culvert", "headwall"],
        "traffic_signals":   ["traffic light", "traffic signal", "signal installation",
                              "signalised intersection", "signalized intersection"],
        "pedestrian_interface": ["pedestrian", "footpath", "walkway", "pedestrian crossing",
                                  "pedestrian management", "shared path"],
    }
    scope_modifiers = []
    for mod, keywords in _MODIFIER_RULES.items():
        if any(kw in text for kw in keywords):
            scope_modifiers.append(mod)

    # Compound detection: EWP + transfer context = ewp_transfer
    if "ewp_transfer" not in scope_modifiers:
        has_ewp = any(kw in text for kw in ["ewp", "scissor lift", "boom lift", "elevated work platform"])
        has_transfer = any(kw in text for kw in ["transfer", "roof access", "access to roof"])
        if has_ewp and has_transfer:
            scope_modifiers.append("ewp_transfer")

    return {
        "job_type": job_type,
        "building_context": building_context,
        "occupancy_context": occupancy_context,
        "scope_modifiers": scope_modifiers,
    }


# ── RA Job-Type Classifier ────────────────────────────────────────────────────

def classify_ra_scope(description: str) -> dict:
    """
    Deterministic job-type classifier for RA input.
    Returns {job_type, building_context, scope_modifiers}.
    """
    text = description.lower()

    # — Job type detection (first match wins, ordered by specificity) —
    _JOB_TYPE_RULES = [
        ("demolition",   ["demolition", "demolish", "strip out", "strip-out", "pull down"]),
        ("fit_out",      ["fit-out", "fit out", "fitout", "installing into", "install into",
                          "data centre", "data center", "server room", "comms room",
                          "tenant fit", "shop fit", "office fit"]),
        ("retrofit",     ["retrofit", "retro-fit", "remedial", "refurbish", "renovation",
                          "upgrade existing", "modify existing", "alter existing"]),
        ("maintenance",  ["maintenance", "repair", "service existing", "replace existing",
                          "routine inspection"]),
        ("civil_infrastructure", ["road works", "road work", "road upgrade", "road widening",
                          "lane widening", "live lane", "road construction", "civil works",
                          "intersection", "stormwater works", "pavement"]),
        ("upgrade",      ["upgrade", "extension", "addition to existing"]),
        ("new_build",    ["new build", "new construction", "greenfield", "ground-up",
                          "erect", "erection", "pour slab", "formwork"]),
    ]
    job_type = "new_build"  # default if no rule matches
    for jt, keywords in _JOB_TYPE_RULES:
        if any(kw in text for kw in keywords):
            job_type = jt
            break

    # — Building context —
    _EXISTING_SIGNALS = ["existing", "into an existing", "within existing",
                         "inside existing", "current building", "occupied",
                         "operational", "live building"]
    _NEW_SIGNALS = ["new build", "greenfield", "ground-up", "vacant lot"]
    has_existing = any(s in text for s in _EXISTING_SIGNALS)
    has_new = any(s in text for s in _NEW_SIGNALS)
    if has_existing and has_new:
        building_context = "mixed"
    elif has_existing:
        building_context = "existing"
    else:
        building_context = "new"

    # — Scope modifiers —
    _MODIFIER_RULES = {
        "occupied_site":       ["occupied", "tenanted", "residents", "operational facility"],
        "tilt_up_context":     ["tilt-up", "tilt up", "tiltup", "precast"],
        "live_services":       ["live services", "live electrical", "energised", "energized",
                                "existing services", "service connections"],
        "commissioning":       ["commissioning", "testing and commissioning", "energise",
                                "energize", "power on", "handover"],
        "warehouse":           ["warehouse", "distribution centre", "distribution center",
                                "logistics", "storage facility"],
        "industrial":          ["industrial", "factory", "manufacturing", "plant room"],
        "electrical_install":  ["electrical install", "power distribution", "switchboard",
                                "cable tray", "data centre", "data center", "ups ",
                                "generator install", "electrical fit"],
        "mechanical_install":  ["mechanical install", "hvac", "air conditioning",
                                "ductwork", "chiller", "cooling system", "mechanical fit"],
        "fire_services":       ["fire services", "sprinkler", "fire detection",
                                "fire suppression", "smoke detect"],
        "structural_mod":      ["structural modification", "structural alteration",
                                "penetration", "core drill", "slab penetration"],
        "civil_infrastructure": ["road works", "road work", "road upgrade", "road widening",
                                  "lane widening", "intersection", "road construction",
                                  "road corridor", "civil works"],
        "road_corridor":     ["road", "lane", "live lane", "traffic corridor", "carriageway"],
        "live_lanes":        ["live lane", "live traffic", "live road", "live works"],
        "utility_relocation": ["asset relocation", "service relocation", "utility relocation",
                               "water main", "sydney water", "gas main", "sewer",
                               "pipe relocation"],
        "stormwater":        ["stormwater", "storm water", "drainage", "stormwater pit",
                              "drainage pit", "culvert"],
        "traffic_signals":   ["traffic light", "traffic signal", "signal installation"],
        "pedestrian_interface": ["pedestrian", "footpath", "walkway", "pedestrian crossing"],
    }
    scope_modifiers = []
    for mod, keywords in _MODIFIER_RULES.items():
        if any(kw in text for kw in keywords):
            scope_modifiers.append(mod)

    return {
        "job_type": job_type,
        "building_context": building_context,
        "scope_modifiers": scope_modifiers,
    }


# Categories to suppress when job is NOT new-build but mentions
# construction materials as existing-building context.
# Key = frozenset of primary keywords from MATRIX entries to suppress.
_RA_NEWBUILD_ONLY_KEYWORDS = frozenset([
    "precast", "tilt-up", "tilt up", "tilt panel", "precast panel",
    "precast concrete", "precast beam", "precast column", "precast wall",
    "concrete panel", "formwork", "pour concrete", "concrete pour",
    "steel erection", "structural steel erection",
    "crane lift", "tower crane", "mobile crane",
])


def _should_suppress_for_ra(entry: dict, classification: dict) -> bool:
    """Return True if this MATRIX entry should be suppressed given the RA classification."""
    job_type = classification["job_type"]
    building_context = classification["building_context"]

    # Only suppress when building is existing and job is not new-build
    if building_context == "new" or job_type == "new_build":
        return False

    # Suppress new-build-only categories when working in/on existing building
    entry_keywords = set(entry.get("keywords", []))
    if entry_keywords & _RA_NEWBUILD_ONLY_KEYWORDS:
        # Check if the entry is genuinely a construction/erection category
        # by looking at its hrcw_category or notes
        hrcw_cat = (entry.get("hrcw_category") or "").lower()
        if any(term in hrcw_cat for term in
               ["tilt-up", "precast", "formwork", "erection", "crane"]):
            return True

    return False


# Keywords that describe scope actions (the work itself), not building context
_SCOPE_ACTION_KEYWORDS = frozenset([
    "install", "installing", "erect", "erection", "demolish", "demolition",
    "excavat", "excavation", "pour", "strip", "remove", "removal",
    "paint", "weld", "cut", "grind", "drill", "lift", "crane",
    "scaffold", "rope access", "work at height", "confined space entry",
    "asbestos removal", "electrical work", "trenching", "roofing",
])

# Keywords that describe building/site context, not the scope of work
_CONTEXT_ONLY_KEYWORDS = frozenset([
    "warehouse", "industrial", "tilt-up", "tilt up", "concrete",
    "commercial", "residential", "multi-storey", "multi storey",
    "heritage", "hospital", "school", "existing",
])


def _assign_ra_confidence(
    entry: dict,
    match_score: float,
    raw_text: str,
    expanded_text: str,
    classification: dict,
) -> str:
    """
    Assign confidence level to an RA hazard match.

    Returns one of:
      confirmed             — hazard is directly and clearly stated in the scope
      likely                — hazard is strongly implied by the stated work type
      if_applicable         — hazard may apply depending on site conditions
      requires_verification — hazard triggered only by building context, not scope
    """
    entry_keywords = entry.get("keywords", [])
    primary_kw = entry_keywords[0] if entry_keywords else ""
    job_type = classification.get("job_type", "new_build")

    # 1. Check if primary keyword is directly stated as a scope action
    #    e.g. "asbestos removal", "electrical work", "scaffold erection"
    primary_in_raw = primary_kw in raw_text
    has_phrase_match = match_score >= 2.0

    # 2. Check if match came from a scope-action keyword or context-only keyword
    #    and whether the match is in the raw text or only in expanded text
    matched_as_scope = False
    matched_as_context = False
    any_kw_in_raw = False
    for kw in entry_keywords:
        if kw in expanded_text:
            if kw in raw_text:
                any_kw_in_raw = True
            if kw in _SCOPE_ACTION_KEYWORDS or any(a in kw for a in _SCOPE_ACTION_KEYWORDS):
                matched_as_scope = True
            if kw in _CONTEXT_ONLY_KEYWORDS or any(c in kw for c in _CONTEXT_ONLY_KEYWORDS):
                matched_as_context = True

    # 3. Assign confidence
    if primary_in_raw and has_phrase_match:
        # Directly stated in the description as a clear phrase
        return "confirmed"

    if has_phrase_match and matched_as_scope and any_kw_in_raw:
        # Strong phrase match on a scope-action keyword that appears in raw text
        return "confirmed"

    if has_phrase_match and matched_as_scope:
        # Phrase match on scope keyword, but only via chain expansion — likely, not confirmed
        return "likely"

    if matched_as_scope and not matched_as_context:
        # Scope action keyword matched (single word), not just context
        return "likely"

    if matched_as_context and not matched_as_scope:
        # Only matched because of building context, not stated scope
        return "requires_verification"

    # Default: matched but not clearly from scope or context
    # — could apply depending on site conditions
    return "if_applicable"


# Terms that describe existing building materials/context — chain expansion
# from these should be suppressed in RA because the building is already built.
_RA_CONTEXT_CHAIN_BLOCKERS = frozenset([
    "precast", "tilt-up", "tilt up", "concrete", "steel frame",
    "masonry", "brick", "timber frame", "heritage", "asbestos",
])


def _expand_description_ra(text: str, classification: dict) -> str:
    """
    RA-specific expansion: applies synonym expansion but suppresses
    chain expansion from context-only terms when building_context is existing.

    For retrofit/fit-out in an existing building, 'tilt-up' should expand
    to 'precast' (synonym) but NOT chain to 'mobile crane', 'working at height',
    'dogging', 'rigging' — those are construction-phase chains, not fit-out scope.
    """
    expanded = text

    # Synonym pass — same as standard
    for synonym, canonical in SYNONYM_MAP.items():
        if synonym in expanded:
            expanded = expanded + " " + canonical

    # Chain pass — skip chains triggered by context-only terms in existing buildings
    skip_chains = (classification.get("building_context") == "existing"
                   and classification.get("job_type") != "new_build")

    # Track terms injected from blocked context sources (should not chain further)
    _blocked_injections: set[str] = set()

    for _ in range(2):
        additions = []
        for trigger, downstream in CHAIN_MAP.items():
            if trigger in expanded:
                if skip_chains and trigger in _RA_CONTEXT_CHAIN_BLOCKERS:
                    # Block chain from context-only term; mark its downstream as blocked
                    for kw in downstream:
                        _blocked_injections.add(kw)
                    continue
                if skip_chains and trigger in _blocked_injections:
                    # This trigger was injected from a blocked context chain — block it too
                    continue
                for kw in downstream:
                    if kw not in expanded:
                        additions.append(kw)
        if additions:
            expanded = expanded + " " + " ".join(additions)
        else:
            break

    return expanded


# ── RA Display Names ─────────────────────────────────────────────────────────
# Maps primary keywords to professional hazard names for RA output.

_RA_DISPLAY_NAMES: dict[str, str] = {
    "slab loading":              "Existing Structure / Slab Loading",
    "heavy equipment delivery":  "Heavy Equipment Delivery and Movement",
    "existing services":         "Existing Services / Service Strike",
    "electrical":                "Electrical Installation / Distribution Works",
    "electrical install":        "Electrical Installation / Switchboard Work",
    "ups ":                      "UPS / Battery Installation",
    "hvac":                      "HVAC / Cooling Systems",
    "fire services":             "Fire Services / Suppression Systems",
    "occupied site":             "Interface with Existing Operations",
    "at height":                 "Work at Height",
    "scaffold":                  "Scaffold Work",
    "rigging":                   "Rigging / Lifting Operations",
    "crane":                     "Crane Operations",
    "asbestos":                  "Asbestos Management",
    "confined space":            "Confined Space Entry",
    "demolition":                "Demolition Work",
    "excavat":                   "Excavation / Trenching",
}


# ── RA Control Language Overrides ─────────────────────────────────────────────
# Maps primary keyword prefixes to RA-appropriate control wording.
# Entries here override the default notes/qualifications scraping.
# Controls should read as practical site actions, not compliance fragments.

_RA_CONTROL_OVERRIDES: dict[str, dict] = {
    "at height": {
        "engineering": [
            "Fall prevention hierarchy: eliminate work at height where possible, then passive fall prevention (guardrails), then fall arrest (harness) as last resort",
            "Verify anchor points are engineer-certified before use",
        ],
        "admin": [
            "Working at heights permit signed before each elevated task",
            "Rescue plan documented and practiced before work at height begins",
        ],
    },
    "scaffold": {
        "engineering": [
            "Scaffold erected by licensed scaffolder to AS/NZS 4576",
            "Handover certificate and scaffold tag inspected before each use",
        ],
        "admin": [
            "Scaffold inspection by competent person before first use and after any incident",
            "Exclusion zone maintained during erection and dismantling",
        ],
    },
    "electrical": {
        "engineering": [
            "All electrical work by or under direct supervision of licensed electrician",
            "Test-before-touch on all circuits — verify de-energised before work",
        ],
        "admin": [
            "Electrical isolation permit (LOTO) before work on existing switchboard or circuits",
            "Energisation sequence documented and approved before first power-on",
        ],
    },
    "asbestos": {
        "engineering": [
            "Hazardous materials survey by licensed assessor before any disturbance of suspect material",
            "Containment / enclosure established before removal — negative pressure where required",
        ],
        "admin": [
            "Asbestos removal licence (Class A or B as applicable) held before removal work starts",
            "Air monitoring during and after removal — clearance certificate before re-occupation",
        ],
    },
    "confined space": {
        "engineering": [
            "Atmospheric testing (O2, CO, H2S, LEL) before every entry and continuous monitoring during",
            "Mechanical ventilation to maintain safe atmosphere throughout entry",
        ],
        "admin": [
            "Confined space entry permit signed before every entry",
            "Rescue plan documented, practiced, and standby person stationed at entry point",
        ],
    },
    "demolition": {
        "engineering": [
            "Pre-demolition hazardous materials survey completed and reviewed before any work",
            "Structural engineer demolition sequence approved — no deviation without sign-off",
        ],
        "admin": [
            "Utility isolation certificates (electrical, gas, water, telecom) confirmed before demolition",
            "Exclusion zone established for full height of demolition face plus 5m",
        ],
    },
    "excavat": {
        "engineering": [
            "Dial Before You Dig (DBYD) enquiry completed and services located before excavation",
            "Shoring / benching / battering as per geotechnical assessment for depths >1.5m",
        ],
        "admin": [
            "Excavation permit issued before breaking ground",
            "Spotter required when excavating near known or suspected services",
        ],
    },
    "crane": {
        "engineering": [
            "Lift study completed by competent person for each critical lift",
            "Crane on firm, level ground — outrigger pads sized to ground bearing capacity",
        ],
        "admin": [
            "Crane operator holds appropriate HRWL for crane class used",
            "Dogman/rigger licensed and on site for all lifts",
        ],
    },
    "rigging": {
        "engineering": [
            "Lifting gear inspected and within test date before each use",
            "SWL/WLL not exceeded — load weight confirmed before lift",
        ],
        "admin": [
            "Licensed rigger (minimum RB class) for all rigging operations",
            "Tag lines used on all suspended loads",
        ],
    },
}


def _build_ra_controls(entry: dict, primary_kw: str, classification: dict) -> dict:
    """
    Build RA-appropriate controls for a hazard.

    Uses _RA_CONTROL_OVERRIDES where a match is found on the primary keyword.
    Falls back to the entry's notes/qualifications/ppe fields for entries
    that already have RA-quality controls (e.g. the retrofit fit-out entries).
    """
    # Check for override match (prefix matching)
    for override_kw, override_controls in _RA_CONTROL_OVERRIDES.items():
        if override_kw in primary_kw.lower():
            return {
                "engineering": override_controls.get("engineering", []),
                "admin": override_controls.get("admin", []),
                "ppe": entry.get("ppe", [])[:3],  # PPE still from entry
            }

    # No override — use entry fields directly
    # New retrofit entries already have RA-quality notes/qualifications
    return {
        "engineering": entry.get("notes", [])[:2] if entry.get("notes") else ["Refer to site-specific controls"],
        "admin": entry.get("qualifications", [])[:2] if entry.get("qualifications") else [],
        "ppe": entry.get("ppe", [])[:3],
    }


def _build_hazard_list(work_description: str, inference: dict) -> list[dict]:
    """
    Build a structured hazard list for Risk Assessment documents.
    Derives hazards from the same inference categories used for SWMS,
    with likelihood/consequence scores based on the H/M/L risk scoring.
    """
    text = work_description.lower()
    hazards: list[dict] = []

    # Classify scope to suppress irrelevant new-build categories
    classification = classify_ra_scope(work_description)

    # Map MATRIX entries to RA hazard rows — use RA-specific expansion
    # that suppresses chain expansion from context-only terms
    expanded = _expand_description_ra(text, classification)

    for entry in MATRIX:
        score = _score_entry(entry, expanded)
        if score < CONFIDENCE_THRESHOLD:
            continue
        primary_kw = entry["keywords"][0]
        if _is_negated(primary_kw, text):
            continue
        if _should_suppress_for_ra(entry, classification):
            continue

        # Derive hazard description from entry keywords and category
        hazard_name = _RA_DISPLAY_NAMES.get(primary_kw)
        if not hazard_name:
            hazard_name = primary_kw.replace("_", " ").title()
            if entry.get("hrcw_category"):
                cat = entry["hrcw_category"]
                if "\u2014" in cat:
                    hazard_name = cat.split("\u2014", 1)[1].strip()
                elif "\u2014" in cat:
                    hazard_name = cat.split("\u2014", 1)[1].strip()
                else:
                    hazard_name = cat

        # —— Confidence assignment ——————————————————————————————————————
        # Determine how certain we are that this hazard applies to the
        # stated scope, not just the building/site context.
        confidence = _assign_ra_confidence(
            entry, score, text, expanded, classification
        )

        # Score based on HRCW status and hazard severity
        _SEVERE_KEYWORDS = ("silica", "asbestos", "lead paint", "confined space",
                            "electrical", "excavat", "demolition", "crane")
        is_severe = any(k in primary_kw.lower() for k in _SEVERE_KEYWORDS)
        if entry.get("hrcw"):
            likelihood, consequence = 4, 5
        elif entry.get("safework_notification") or is_severe:
            likelihood, consequence = 4, 4
        else:
            likelihood, consequence = 3, 3

        risk_rating = likelihood * consequence

        # Build controls hierarchy — use RA-specific overrides where available,
        # otherwise fall back to SWMS-style notes/qualifications
        controls = _build_ra_controls(entry, primary_kw, classification)

        # Residual risk after controls
        res_likelihood = max(1, likelihood - 2)
        res_consequence = max(1, consequence - 1)
        residual_risk = res_likelihood * res_consequence

        who_at_risk_parts = ["Workers performing task"]
        if any(k in text for k in ("public", "traffic", "occupied")):
            who_at_risk_parts.append("public/occupants")
        if any(k in text for k in ("nearby", "adjacent")):
            who_at_risk_parts.append("nearby workers")

        hazards.append({
            "hazard": hazard_name,
            "confidence": confidence,
            "who_at_risk": ", ".join(who_at_risk_parts),
            "likelihood": likelihood,
            "consequence": consequence,
            "risk_rating": risk_rating,
            "risk_level": _risk_level(risk_rating),
            "controls": controls,
            "residual_likelihood": res_likelihood,
            "residual_consequence": res_consequence,
            "residual_risk": residual_risk,
            "residual_level": _risk_level(residual_risk),
            "responsible": "Supervisor",
        })

    # Always add baseline construction hazards if none matched
    if not hazards:
        hazards.append({
            "hazard": "General construction hazards",
            "confidence": "confirmed",
            "who_at_risk": "All workers on site",
            "likelihood": 2,
            "consequence": 3,
            "risk_rating": 6,
            "risk_level": "Medium",
            "controls": {
                "engineering": ["Site-specific risk controls as per project requirements"],
                "admin": ["Site induction completed", "Toolbox talk before work"],
                "ppe": list(BASELINE_PPE),
            },
            "residual_likelihood": 1,
            "residual_consequence": 2,
            "residual_risk": 2,
            "residual_level": "Low",
            "responsible": "Supervisor",
        })

    return hazards


# ── RA Phase Grouping ─────────────────────────────────────────────────────────

_RA_PHASE_EXISTING = "Existing building / structural suitability"
_RA_PHASE_INSTALL  = "Installation and fit-out"
_RA_PHASE_LIVE     = "Live services / commissioning"
_RA_PHASE_INTERFACE = "Interface with existing operations"

# Map primary keywords (or substrings) to phases
_RA_PHASE_RULES: list[tuple[str, list[str]]] = [
    # Existing building phase
    (_RA_PHASE_EXISTING, [
        "slab loading", "structural suitability", "floor loading",
        "penetration", "core drill", "load bearing",
        "existing services", "service strike", "service location",
        "unknown services", "concealed services",
        "asbestos",  # existing-building hazmat survey
    ]),
    # Live services / commissioning phase
    (_RA_PHASE_LIVE, [
        "energised", "energise", "energize", "energisation",
        "commissioning", "power on", "mains connection",
        "live services", "live electrical",
        "switchboard",  # tie-in to live board
    ]),
    # Interface with existing operations
    (_RA_PHASE_INTERFACE, [
        "occupied", "tenanted", "tenant", "operational facility",
        "live building", "interface with existing",
        "shared access", "public access",
        "existing operations",
    ]),
    # Installation and fit-out (broadest — checked last)
    (_RA_PHASE_INSTALL, [
        "install", "delivery", "equipment", "forklift", "plant room",
        "electrical", "ups", "battery", "hvac", "cooling", "chiller",
        "ductwork", "mechanical", "fire", "sprinkler", "suppression",
        "scaffold", "rigging", "cable", "generator",
        "at height", "fall",
    ]),
]


def _assign_ra_phase(hazard: dict) -> str:
    """Assign a phase to an RA hazard based on its name and entry keywords."""
    name = hazard.get("hazard", "").lower()
    for phase, keywords in _RA_PHASE_RULES:
        if any(kw in name for kw in keywords):
            return phase
    return _RA_PHASE_INSTALL  # default


def group_ra_hazards_by_phase(hazards: list[dict]) -> list[dict]:
    """
    Group a flat hazard list into phase buckets.

    Returns list of:
      {"phase": str, "hazards": [hazard_dict, ...]}

    Phases appear in the canonical order. Empty phases are omitted.
    """
    _PHASE_ORDER = [
        _RA_PHASE_EXISTING,
        _RA_PHASE_INSTALL,
        _RA_PHASE_LIVE,
        _RA_PHASE_INTERFACE,
    ]
    buckets: dict[str, list[dict]] = {p: [] for p in _PHASE_ORDER}

    for h in hazards:
        phase = _assign_ra_phase(h)
        h["phase"] = phase  # tag each hazard with its phase
        buckets.setdefault(phase, []).append(h)

    return [
        {"phase": p, "hazards": buckets[p]}
        for p in _PHASE_ORDER
        if buckets.get(p)
    ]


# ── RA HRCW Register ─────────────────────────────────────────────────────────

# All 17 WHS Reg 2017 Schedule 1 HRCW categories
_HRCW_CATEGORIES = [
    {"ref": "H01", "name": "Work involving a risk of a person falling more than 2 metres",
     "flag": "falling_2m",
     "conditional_triggers": ["excavation", "trench", "open cut", "pit",
                              "stormwater", "drainage", "road works"],
     "conditional_reason": "Falls into open excavations or trenches possible across multiple trade packages \u2014 confirm depth exceeds 2m at specific locations"},
    {"ref": "H02", "name": "Work on a telecommunication tower", "flag": "telecom_tower"},
    {"ref": "H03", "name": "Demolition of a load-bearing structure", "flag": "demolition"},
    {"ref": "H04", "name": "Work involving disturbance of asbestos", "flag": "asbestos",
     "conditional_triggers": ["existing road", "chip seal", "existing infrastructure",
                              "existing pavement", "pre-1990", "pre-2000", "renovation",
                              "demolition", "refurbish"],
     "conditional_reason": "Existing road surface or infrastructure may contain ACM \u2014 hazmat survey required before any disturbance of existing materials"},
    {"ref": "H05", "name": "Structural alterations requiring temporary support",
     "flag": "temp_support",
     "conditional_triggers": ["utility relocation", "sydney water", "water main",
                              "pipe relocation", "asset relocation"],
     "conditional_reason": "Temporary support may be required where utility relocation involves structural modification to existing chambers, headwalls, or thrust blocks \u2014 confirm with design engineer"},
    {"ref": "H06", "name": "Work in or near a confined space", "flag": "confined_space",
     "conditional_triggers": ["stormwater pit", "drainage pit", "chamber", "manhole",
                              "valve vault", "stormwater", "sewer"],
     "conditional_reason": "Stormwater pits, drainage chambers, and valve vaults may require confined space entry \u2014 assess each structure per AS 2865 before entry"},
    {"ref": "H07", "name": "Work in or near a shaft or trench deeper than 1.5m",
     "flag": "shaft_trench"},
    {"ref": "H08", "name": "Use of explosives", "flag": "explosives"},
    {"ref": "H09", "name": "Work on or near pressurised gas mains or piping",
     "flag": "pressurised_gas",
     "conditional_triggers": ["road corridor", "road works", "live lane",
                              "utility", "service relocation"],
     "conditional_reason": "Gas assets are commonly present in road corridors \u2014 DBYD and service proving required to confirm presence, location, and protection requirements in the excavation zone"},
    {"ref": "H10", "name": "Work on or near chemical, fuel or refrigerant lines",
     "flag": "chemical_fuel"},
    {"ref": "H11", "name": "Work on or near energised electrical installations",
     "flag": "electrical",
     "conditional_triggers": ["traffic signal", "traffic light", "street lighting",
                              "road works", "intersection", "signal installation"],
     "conditional_reason": "Traffic signal installation and street lighting involve energised electrical work \u2014 confirm whether scope includes connection, commissioning, or work near existing electrical assets"},
    {"ref": "H12", "name": "Work in an area with contaminated or flammable atmosphere",
     "flag": "contaminated_atmo",
     "conditional_triggers": ["sewer", "stormwater", "drainage", "confined space",
                              "pit", "chamber"],
     "conditional_reason": "Sewer and stormwater infrastructure may have contaminated or oxygen-deficient atmosphere \u2014 atmospheric testing required before entry to any enclosed structure"},
    {"ref": "H13", "name": "Work involving tilt-up or precast concrete", "flag": "tiltup_precast"},
    {"ref": "H14", "name": "Work on, in or adjacent to a road or traffic corridor",
     "flag": "traffic_corridor"},
    {"ref": "H15", "name": "Work in an area with movement of powered mobile plant",
     "flag": "mobile_plant"},
    {"ref": "H16", "name": "Work in areas with artificial extremes of temperature",
     "flag": "extreme_temp"},
    {"ref": "H17", "name": "Work involving diving", "flag": "diving"},
]


def _build_ra_hrcw_register(
    hrcw_flags: dict, classification: dict, text: str,
) -> list[dict]:
    """
    Build a structured HRCW register for RA output.

    Each entry has: ref, name, status (YES/CONDITIONAL/NO), reason.
    """
    text_lower = text.lower()
    modifiers = set(classification.get("scope_modifiers", []))
    register = []

    for cat in _HRCW_CATEGORIES:
        ref = cat["ref"]
        name = cat["name"]
        flag = cat["flag"]
        flag_active = hrcw_flags.get(flag, False)
        conditional_triggers = cat.get("conditional_triggers", [])

        if flag_active:
            register.append({
                "ref": ref, "name": name, "status": "YES",
                "reason": "Triggered by scope description",
            })
        elif conditional_triggers and any(t in text_lower for t in conditional_triggers):
            reason = cat.get("conditional_reason",
                             "May apply depending on site conditions \u2014 confirm before work")
            register.append({
                "ref": ref, "name": name, "status": "CONDITIONAL",
                "reason": reason,
            })
        else:
            register.append({
                "ref": ref, "name": name, "status": "NO",
                "reason": "",
            })

    return register


def infer_to_dict_ra(work_description: str, jurisdiction: str = "AU",
                     ca_province: str = "") -> dict:
    """Return inference result with hazard_list and phase_groups for RA documents."""
    result = infer_to_dict(work_description, jurisdiction=jurisdiction)
    result["ra_classification"] = classify_ra_scope(work_description)
    result["hazard_list"] = _build_hazard_list(work_description, result)
    result["phase_groups"] = group_ra_hazards_by_phase(result["hazard_list"])
    result["ra_hrcw_register"] = _build_ra_hrcw_register(
        result.get("hrcw_flags", {}),
        result["ra_classification"],
        work_description,
    )
    result["document_type"] = "ra"
    return result


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json, sys
    desc = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "lead paint encapsulation ground floor exterior"
    print(f"\nWork description: {desc}\n")
    result = infer_to_dict(desc)
    print(json.dumps(result, indent=2))

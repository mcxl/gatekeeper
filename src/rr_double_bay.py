#!/usr/bin/env python3
"""Risk Register — 409-411 New South Head Road, Double Bay NSW 2028.

Scope:
  - Concrete spalling repairs to balcony soffits (jackhammer, Nitoprime
    Zincrich, Nitobond HAR, Renderox HB40)
  - Balcony waterproofing (pressure wash, Nitoseal MS250, Parchem membrane)
  - External painting (Acratex Green Render Sealer, Weathershield Low Sheen)
  - Access via industrial rope access throughout

Generates both .docx and .xlsx to the output/ folder.
"""

from src.risk_register_to_docx import build_document
from src.risk_register_to_xlsx import build_workbook

# ── Risk data ─────────────────────────────────────────────────────
RISKS = [
    {
        "no": 1,
        "task": (
            "Industrial rope access — rigging, descent, work positioning, "
            "and ascent for all façade and balcony soffit works"
        ),
        "code": "WAH",
        "hazard": (
            "Fall from height due to anchor failure, rope failure, or "
            "equipment malfunction; pendulum swing into structure or adjacent "
            "surfaces; contact with building edges causing rope abrasion or "
            "severance; electrical hazard from proximity to overhead electric "
            "lines; environmental hazards — wind causing rope tangle or worker "
            "instability, wet ropes reducing device performance, heat stress "
            "and UV degradation of ropes and equipment"
        ),
        "likelihood_pre": "B \u2014 Likely",
        "consequence_pre": "3 \u2014 Major",
        "risk_pre": "Critical (5)",
        "controls": (
            "Engineering: Two independent anchor points per worker \u2014 one for "
            "working line, one for safety line (Safe Work Australia Guide to "
            "Industrial Rope Access Systems s4.5); all anchors and supporting "
            "structure load tested to minimum 15 kN before first use and "
            "annually thereafter; rope edge protection \u2014 davit arms, rollers, "
            "or textile sheaths at all contact points; exclusion zone "
            "established and barricaded below rope access work area; all tools "
            "secured to harness via lanyards or tool bags.\n"
            "Admin: HOLD POINT \u2014 anchor installation certified by qualified "
            "engineer or competent person per WHS Reg r213; all rope access "
            "workers hold current certificate of competency \u2014 verified before "
            "commencement; equipment inspection by competent person before and "
            "after each use \u2014 harnesses, lanyards, descenders, back-up "
            "devices, ropes, slings, anchor devices; ropes packed after each "
            "shift; SWMS prepared \u2014 IRA is HRCW per WHS Reg r299; weather "
            "forecast checked before commencement; equipment stored protected "
            "from heat, UV, moisture, and chemicals.\n"
            "PPE: Full body harness (AS/NZS 1891.4); helmet AS/NZS 1801; "
            "safety glasses; hi-vis vest; safety boots; gloves.\n"
            "STOP WORK: Anchor certification not sighted; worker competency "
            "not verified; equipment defect identified; wind >40 km/h or "
            "causing instability; electrical storm; ropes wet and device "
            "performance compromised."
        ),
        "residual_risk": "Medium (3)",
        "responsible": "Site Supervisor / Rope Access Supervisor / Qualified Engineer (anchors)",
    },
    {
        "no": 2,
        "task": (
            "Industrial rope access — emergency rescue, suspension "
            "intolerance response, and environmental monitoring"
        ),
        "code": "WAH",
        "hazard": (
            "Suspension intolerance (suspension trauma) \u2014 blood pooling in "
            "lower legs during harness suspension reducing cardiac output, "
            "leading to fainting, renal failure, and death; delayed rescue of "
            "incapacitated worker suspended on rope; worker isolation \u2014 "
            "inability to communicate distress; environmental deterioration "
            "during work \u2014 sudden wind, rain, or electrical storm increasing "
            "rescue difficulty"
        ),
        "likelihood_pre": "C \u2014 Possible",
        "consequence_pre": "3 \u2014 Major",
        "risk_pre": "High (4)",
        "controls": (
            "Engineering: Working and safety lines rigged for rescue \u2014 "
            "releasable anchors to allow lowering or raising of injured worker "
            "without rescuer needing to descend; rescue equipment present and "
            "rigged for immediate use at all times; harness with suspension "
            "relief straps or footholds.\n"
            "Admin: Emergency rescue plan prepared, documented, and tested "
            "before rope access work commences \u2014 plan covers rescue from any "
            "situation on site per WHS Reg r42; rope access workers never work "
            "alone \u2014 minimum two workers with line-of-sight or communication "
            "at all times; all workers trained in emergency procedures "
            "including rope rescue techniques; rescue to be completed within "
            "5 minutes where practicable; weather monitored continuously \u2014 "
            "immediate descent if conditions deteriorate; communication system "
            "confirmed operative before descent.\n"
            "PPE: Full body harness with suspension relief capability; helmet; "
            "first aid kit accessible at anchor station.\n"
            "STOP WORK: Rescue plan not documented or tested; fewer than two "
            "rope access workers on site; communication system failure; "
            "weather deterioration (wind, wet, lightning)."
        ),
        "residual_risk": "Medium (3)",
        "responsible": "Site Supervisor / Rope Access Supervisor / First Aid Officer",
    },
    {
        "no": 3,
        "task": (
            "Jackhammer defective concrete from balcony soffits to expose "
            "reinforcement steel \u2014 overhead work from rope access position"
        ),
        "code": "SIL",
        "hazard": (
            "Respirable crystalline silica (RCS) from jackhammering concrete "
            "soffits \u2014 silicosis risk (irreversible lung disease); whole-body "
            "and hand-arm vibration from jackhammer; noise >85 dB(A); flying "
            "concrete fragments from overhead demolition; falling concrete "
            "debris from soffits onto persons below; electrical hazard \u2014 "
            "striking concealed services during demolition"
        ),
        "likelihood_pre": "A \u2014 Almost Certain",
        "consequence_pre": "3 \u2014 Major",
        "risk_pre": "Critical (6)",
        "controls": (
            "Engineering: H-class dust extraction connected to jackhammer "
            "shroud or wet suppression at point of demolition \u2014 no dry "
            "demolition permitted; RCD-protected power supply; exclusion zone "
            "barricaded below soffit work area; overhead protection for "
            "adjacent areas; jackhammer anti-vibration mounts.\n"
            "Admin: Air monitoring where demolition >30 min/shift \u2014 RCS "
            "exposure standard 0.05 mg/m\u00b3 TWA; silica register; health "
            "monitoring \u2014 lung function baseline and periodic per WHS Reg "
            "Part 8.4; services scan before demolition at each new location; "
            "task rotation to limit vibration exposure; debris contained and "
            "removed at end of each shift.\n"
            "PPE: P2 respirator (fit-tested); face shield AS/NZS 1337; "
            "hearing protection (Class 5); anti-vibration gloves; helmet; "
            "safety boots with metatarsal protection.\n"
            "STOP WORK: Dust extraction/suppression fails; services detected "
            "in demolition zone; air monitoring exceeds 0.05 mg/m\u00b3 RCS; "
            "exclusion zone breached."
        ),
        "residual_risk": "Medium (3)",
        "responsible": "Site Supervisor / Lead Technician / Occupational Hygienist",
    },
    {
        "no": 4,
        "task": (
            "Treat exposed reinforcement with Nitoprime Zincrich, prime "
            "substrate with Nitobond HAR bonding agent, patch with Renderox "
            "HB40 repair mortar \u2014 overhead application from rope access"
        ),
        "code": "ENV",
        "hazard": (
            "Chemical exposure \u2014 Nitoprime Zincrich (zinc-rich primer, "
            "flammable, respiratory irritant); Nitobond HAR (acrylic bonding "
            "agent, skin/eye irritant); Renderox HB40 (cementitious repair "
            "mortar, alkaline \u2014 skin and eye irritant, contains chromium VI); "
            "overhead application \u2014 drips and splashes onto face, eyes, and "
            "skin; manual handling at height \u2014 mixing and carrying materials "
            "while suspended"
        ),
        "likelihood_pre": "B \u2014 Likely",
        "consequence_pre": "2 \u2014 Moderate",
        "risk_pre": "High (4)",
        "controls": (
            "Engineering: Drip containment below work area; RCD-protected "
            "power supply for mixing equipment.\n"
            "Admin: SDS for Nitoprime Zincrich, Nitobond HAR, and Renderox "
            "HB40 reviewed and on site; workers briefed on chemical hazards, "
            "first aid, and spill procedures for each product; chemical "
            "register maintained; no ignition sources within 5 m when using "
            "Nitoprime Zincrich; materials pre-mixed at ground level where "
            "practicable \u2014 minimise mixing at height; eye wash station within "
            "20 m.\n"
            "PPE: P2 respirator; face shield for overhead application; "
            "chemical-resistant nitrile gloves; long sleeves; safety glasses "
            "AS/NZS 1337.\n"
            "STOP WORK: SDS not on site for any product; eye wash not "
            "accessible; worker reports skin or eye irritation."
        ),
        "residual_risk": "Low (2)",
        "responsible": "Site Supervisor / Lead Technician",
    },
    {
        "no": 5,
        "task": (
            "Pressure wash concrete balcony surfaces to remove loose material, "
            "contaminants, and failed coatings before waterproofing"
        ),
        "code": "ENV",
        "hazard": (
            "High-pressure water injection injury; overspray drift onto "
            "public areas, balconies, and vehicles below; slip hazard on wet "
            "surfaces; electrical hazard \u2014 water ingress to electrical "
            "fittings; environmental contamination \u2014 wash water containing "
            "concrete dust and coating residue entering stormwater"
        ),
        "likelihood_pre": "B \u2014 Likely",
        "consequence_pre": "2 \u2014 Moderate",
        "risk_pre": "High (4)",
        "controls": (
            "Engineering: Fan nozzle (not zero-degree); containment sheeting "
            "to prevent overspray; wash water captured and filtered \u2014 sediment "
            "trap or bunded collection; RCD-protected power supply; electrical "
            "fittings in wash zone isolated or protected.\n"
            "Admin: Wash water disposal per NSW EPA requirements; overspray "
            "management plan \u2014 stop if wind >25 km/h; never direct pressure "
            "washer at persons; occupant notification before commencement; "
            "adjacent balconies checked and protected.\n"
            "PPE: Safety glasses/face shield; waterproof gloves and coveralls; "
            "safety boots with non-slip sole.\n"
            "STOP WORK: Wash water containment fails; wind >25 km/h; "
            "electrical fittings not isolated in wash zone."
        ),
        "residual_risk": "Low (2)",
        "responsible": "Site Supervisor / Lead Technician",
    },
    {
        "no": 6,
        "task": (
            "Rake out failed sealant from balcony joints, prepare joint "
            "surfaces, apply Fosroc Nitoseal MS250 sealant, tool to profile"
        ),
        "code": "ENV",
        "hazard": (
            "Chemical exposure \u2014 Nitoseal MS250 solvent vapours and "
            "isocyanate content; skin sensitisation; eye contact; manual "
            "handling of caulking guns at height; slip hazard from sealant "
            "on surfaces"
        ),
        "likelihood_pre": "B \u2014 Likely",
        "consequence_pre": "2 \u2014 Moderate",
        "risk_pre": "High (4)",
        "controls": (
            "Substitute: Select low-VOC sealant variant where specified "
            "product allows.\n"
            "Engineering: Natural ventilation confirmed adequate; RCD-"
            "protected power tools.\n"
            "Admin: SDS for Nitoseal MS250 reviewed and on site; workers "
            "briefed on chemical hazards, first aid, spill procedures; "
            "sealant waste disposed per EPA requirements; chemical register "
            "maintained.\n"
            "PPE: Nitrile gloves; safety glasses AS/NZS 1337; P2 respirator "
            "if confined/recessed joint areas.\n"
            "STOP WORK: SDS not on site; ventilation inadequate in enclosed "
            "areas; worker reports symptoms of sensitisation."
        ),
        "residual_risk": "Low (2)",
        "responsible": "Site Supervisor / Lead Technician",
    },
    {
        "no": 7,
        "task": (
            "Apply Parchem waterproofing membrane to prepared balcony "
            "surfaces \u2014 primer, membrane coats, and protection layer"
        ),
        "code": "ENV",
        "hazard": (
            "Chemical exposure \u2014 Parchem membrane system (solvent/water-based "
            "depending on product variant, respiratory and skin irritant); "
            "vapour accumulation in sheltered balcony areas; skin contact "
            "during roller/brush application; slip hazard from wet membrane "
            "on balcony surfaces"
        ),
        "likelihood_pre": "C \u2014 Possible",
        "consequence_pre": "2 \u2014 Moderate",
        "risk_pre": "Medium (3)",
        "controls": (
            "Engineering: Adequate ventilation confirmed \u2014 fans if enclosed "
            "balcony; drip containment below work area.\n"
            "Admin: SDS for all Parchem membrane products reviewed and on "
            "site; apply during favourable weather \u2014 manufacturer temperature "
            "and humidity requirements checked; chemical register; area "
            "barricaded until membrane cured.\n"
            "PPE: Organic vapour respirator (A1P2) if enclosed area; safety "
            "glasses; nitrile gloves; long sleeves.\n"
            "STOP WORK: SDS not on site; ventilation inadequate; temperature "
            "outside manufacturer\u2019s range."
        ),
        "residual_risk": "Low (1)",
        "responsible": "Site Supervisor / Lead Applicator",
    },
    {
        "no": 8,
        "task": (
            "Prepare external concrete render and masonry surfaces, apply "
            "Acratex Green Render Sealer via spray or roller from rope access"
        ),
        "code": "ENV",
        "hazard": (
            "Chemical exposure \u2014 Acratex Green Render Sealer (water-based "
            "acrylic, low VOC but respiratory irritant in spray application); "
            "overspray drift onto public areas, adjacent properties, and "
            "vehicles; environmental contamination from overspray and "
            "equipment wash; manual handling at height \u2014 carrying spray "
            "equipment while suspended"
        ),
        "likelihood_pre": "B \u2014 Likely",
        "consequence_pre": "2 \u2014 Moderate",
        "risk_pre": "High (4)",
        "controls": (
            "Engineering: Containment sheeting on rope access zone to capture "
            "overspray; RCD-protected power supply for spray equipment.\n"
            "Admin: SDS reviewed and on site; wind check before spray "
            "application \u2014 stop if >25 km/h; overspray management plan; "
            "occupant and neighbour notification; equipment wash water "
            "captured and disposed per NSW EPA.\n"
            "PPE: P2 respirator during spray application; safety glasses "
            "AS/NZS 1337; nitrile gloves; long sleeves; coveralls.\n"
            "STOP WORK: Wind >25 km/h during spray application; overspray "
            "reaching public areas or adjacent properties; SDS not on site."
        ),
        "residual_risk": "Low (2)",
        "responsible": "Site Supervisor / Lead Painter",
    },
    {
        "no": 9,
        "task": (
            "Apply Dulux Weathershield Exterior Low Sheen topcoat to "
            "external concrete render and masonry surfaces from rope access"
        ),
        "code": "ENV",
        "hazard": (
            "Chemical exposure \u2014 Weathershield Low Sheen (water-based acrylic, "
            "low VOC); overspray drift from height; drips from rope access "
            "work position onto persons or property below; manual handling of "
            "paint and equipment at height"
        ),
        "likelihood_pre": "C \u2014 Possible",
        "consequence_pre": "2 \u2014 Moderate",
        "risk_pre": "Medium (3)",
        "controls": (
            "Engineering: Containment sheeting; drip trays below work zone.\n"
            "Admin: SDS reviewed and on site; apply during favourable weather "
            "\u2014 wind <25 km/h, temperature per manufacturer spec; overspray "
            "cleaned immediately; equipment wash water captured.\n"
            "PPE: Safety glasses; nitrile gloves; P2 respirator if spray "
            "application in enclosed areas.\n"
            "STOP WORK: Wind >25 km/h; overspray or drips reaching public "
            "areas; temperature outside manufacturer\u2019s range."
        ),
        "residual_risk": "Low (1)",
        "responsible": "Site Supervisor / Lead Painter",
    },
    {
        "no": 10,
        "task": (
            "Surface preparation of existing painted concrete and masonry "
            "\u2014 abrasion, sanding, or mechanical preparation of coatings "
            "of unknown age"
        ),
        "code": "LED",
        "hazard": (
            "CRITICAL \u2014 Existing coatings on pre-1997 surfaces may contain "
            "lead paint. Respirable lead dust from abrading, sanding, or "
            "mechanical preparation \u2014 lead poisoning (neurological damage, "
            "kidney damage, reproductive harm); dust inhalation; skin and eye "
            "contact with lead-contaminated dust"
        ),
        "likelihood_pre": "B \u2014 Likely",
        "consequence_pre": "3 \u2014 Major",
        "risk_pre": "Critical (5)",
        "controls": (
            "Eliminate: HOLD POINT \u2014 Test existing coatings for lead before "
            "any abrasion or mechanical preparation. If pre-1997 or unknown "
            "age, XRF testing or NATA-accredited lab analysis required. If "
            "lead confirmed (>1% by weight): lead risk work per WHS Reg "
            "Part 8.5; lead risk control plan; air monitoring; blood lead "
            "monitoring; wet methods mandatory; HEPA vacuum; hazardous waste "
            "disposal; notify SafeWork NSW.\n"
            "Engineering (if lead-free): Wet abrasion; RCD-protected tools; "
            "dust extraction; adequate ventilation.\n"
            "Admin: Lead test results on site; lead register if detected; "
            "health monitoring per WHS Reg Part 8.5.\n"
            "PPE: P2 respirator (fit-tested); safety glasses; nitrile gloves; "
            "disposable coveralls if lead risk work.\n"
            "STOP WORK: Lead test results not available; lead detected and "
            "control plan not in place; air monitoring exceeds lead exposure "
            "standard."
        ),
        "residual_risk": "Medium (3)",
        "responsible": "Site Supervisor / Occupational Hygienist (if lead confirmed)",
    },
    {
        "no": 11,
        "task": (
            "Manage pedestrian and vehicle interface around work zone at "
            "409-411 New South Head Road, Double Bay \u2014 high-traffic "
            "commercial and residential streetscape"
        ),
        "code": "TRF",
        "hazard": (
            "Pedestrian struck by falling object from rope access work zone; "
            "vehicle collision with work zone equipment; public accessing "
            "exclusion zone below overhead work; overspray, wash water, or "
            "debris affecting pedestrians, vehicles, and adjacent commercial "
            "premises; noise and dust affecting residents and businesses"
        ),
        "likelihood_pre": "B \u2014 Likely",
        "consequence_pre": "3 \u2014 Major",
        "risk_pre": "Critical (5)",
        "controls": (
            "Engineering: Physical barricading \u2014 hoarding or A-class barriers "
            "below overhead work zones; overhead protection gantry where "
            "footpath cannot be closed; containment sheeting on rope access "
            "zone to capture debris and overspray.\n"
            "Admin: Traffic management plan (TMP) where works encroach on "
            "road or footpath \u2014 Woollahra Municipal Council approval required; "
            "spotter during overhead rope access work where public below; "
            "signage at all access points; daily barricade inspection; "
            "occupant and adjacent business notification before noisy, dusty, "
            "or spray work; work scheduled to minimise disruption to "
            "commercial peak hours.\n"
            "PPE: Hi-vis vest; helmet mandatory in drop zones.\n"
            "STOP WORK: Exclusion zone barricading not in place; overhead "
            "protection not installed where footpath open; TMP not approved "
            "where works encroach on road."
        ),
        "residual_risk": "Medium (3)",
        "responsible": "Site Supervisor / Traffic Controller (if TMP required)",
    },
    {
        "no": 12,
        "task": (
            "Manual handling of materials, tools, chemicals, and equipment "
            "across all scope items \u2014 ground to rope access transfer"
        ),
        "code": "STR",
        "hazard": (
            "Musculoskeletal injury from repetitive lifting, carrying, and "
            "overhead work; back injury from awkward postures during rope "
            "access material transfer; fatigue from sustained physical work "
            "at height; dropped materials during transfer between ground and "
            "rope access position"
        ),
        "likelihood_pre": "B \u2014 Likely",
        "consequence_pre": "2 \u2014 Moderate",
        "risk_pre": "High (4)",
        "controls": (
            "Eliminate: Deliver materials by mechanical means (hoist line, "
            "haul bag on separate anchored line) \u2014 minimise manual carrying "
            "while suspended.\n"
            "Engineering: Mechanical lifting aids for items >20 kg; tool bags "
            "and haul bags rated for load; separate anchor for material "
            "hauling line.\n"
            "Admin: Team lifts for items >15 kg at ground level; task "
            "rotation; correct manual handling technique briefed; rest breaks "
            "scheduled; materials pre-staged at ground level in manageable "
            "quantities.\n"
            "PPE: Rigger\u2019s gloves; safety boots.\n"
            "STOP WORK: Material haul line not independently anchored; loads "
            "exceed rated capacity of haul equipment."
        ),
        "residual_risk": "Low (1)",
        "responsible": "Site Supervisor / Rope Access Supervisor",
    },
]


# ── Project configuration ─────────────────────────────────────────
DOUBLE_BAY_CONFIG = {
    "project_name": (
        "Remedial Building Works \u2014 409-411 New South Head Road, "
        "Double Bay NSW 2028"
    ),
    "pcbu": "Robertson\u2019s Remedial and Painting Pty Ltd",
    "jurisdiction": "NSW \u2014 WHS Act 2011 (NSW), WHS Regulation 2017 (NSW)",
    "date": "23 February 2026",
    "prepared_by": "Gatekeeper Risk Assessment System",
    "risks": RISKS,
    "pre_summary": [
        ("Critical (5\u20136)", "4"),
        ("High (4)", "6"),
        ("Medium (3)", "2"),
        ("Low (1\u20132)", "0"),
    ],
    "post_summary": [
        ("Critical (5\u20136)", "0"),
        ("High (4)", "0"),
        ("Medium (3)", "5"),
        ("Low (1\u20132)", "7"),
    ],
    "hold_points": [
        (
            "Industrial rope access \u2014 anchor installation certified by "
            "qualified engineer, load tested to 15 kN minimum (WHS Reg r213)"
        ),
        (
            "Existing coatings \u2014 test for lead paint before any abrasion "
            "or mechanical preparation (WHS Reg Part 8.5)"
        ),
        (
            "All silica-generating tasks \u2014 air monitoring and health "
            "surveillance required (WHS Reg Part 8.4)"
        ),
        (
            "Pressure washing \u2014 wash water containment and disposal plan "
            "verified before commencement (NSW EPA)"
        ),
    ],
    "references": [
        "Work Health and Safety Act 2011 (NSW) \u2014 s19, s28, s38",
        (
            "Work Health and Safety Regulation 2017 (NSW) \u2014 Part 3.1, "
            "Part 6.3, Part 6.4, Part 8.4, Part 8.5"
        ),
        "Code of Practice: Managing the Risk of Falls at Workplaces (Safe Work Australia)",
        (
            "Code of Practice: Managing Risks of Hazardous Chemicals in the "
            "Workplace (Safe Work Australia)"
        ),
        (
            "Guide to Managing Risks of Industrial Rope Access Systems "
            "(Safe Work Australia, June 2022)"
        ),
        "AS/NZS ISO 22846 \u2014 Rope access systems",
        (
            "AS/NZS 1891.4 \u2014 Industrial fall-arrest systems and devices "
            "\u2014 Selection, use and maintenance"
        ),
        "AS/NZS 1801 \u2014 Occupational protective helmets",
        "AS/NZS 1337 \u2014 Personal eye protection",
    ],
}


if __name__ == "__main__":
    docx_path = "output/Risk_Register_409_New_South_Head_Rd_Double_Bay.docx"
    xlsx_path = "output/Risk_Register_409_New_South_Head_Rd_Double_Bay.xlsx"

    doc = build_document(DOUBLE_BAY_CONFIG)
    doc.save(docx_path)
    print(f"Risk register (Word) saved to {docx_path}")

    wb = build_workbook(DOUBLE_BAY_CONFIG)
    wb.save(xlsx_path)
    print(f"Risk register (Excel) saved to {xlsx_path}")

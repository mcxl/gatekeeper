#!/usr/bin/env python3
"""
RPD Master SWMS Generator
Builds 7 standalone Master SWMS documents from the V1 template.
Each document reuses common tasks from the painting master and adds
work-type-specific tasks with full control text.
"""

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from lxml import etree
import copy
import os
import sys

# Controlled vocabulary — canonical phrases for hazards, controls, PPE, STOP WORK
try:
    from swms_vocabulary import (
        get_hazard, get_control, get_ppe, get_stop_work,
        build_engineering, build_admin, HAZARDS, CONTROLS,
        PPE_ITEMS, STOP_WORK,
    )
except ImportError:
    print("WARNING: swms_vocabulary.py not found — new_task() will not be available.")
    print("  Existing raw-string task definitions will still work.")

TEMPLATE_PATH = "/mnt/user-data/uploads/RPD_MASTER_SWMS_TEMPLATE_V1.docx"
OUTPUT_DIR = "/mnt/user-data/outputs"

# ============================================================
# XML HELPERS
# ============================================================

def make_run(text, bold=False, italic=False, font='Aptos', size='16', color=None):
    """Create a w:r element"""
    r = etree.Element(qn('w:r'))
    rPr = etree.SubElement(r, qn('w:rPr'))
    rFonts = etree.SubElement(rPr, qn('w:rFonts'))
    rFonts.set(qn('w:ascii'), font)
    rFonts.set(qn('w:hAnsi'), font)
    sz = etree.SubElement(rPr, qn('w:sz'))
    sz.set(qn('w:val'), size)
    szCs = etree.SubElement(rPr, qn('w:szCs'))
    szCs.set(qn('w:val'), size)
    if bold:
        etree.SubElement(rPr, qn('w:b'))
    if italic:
        etree.SubElement(rPr, qn('w:i'))
    if color:
        c = etree.SubElement(rPr, qn('w:color'))
        c.set(qn('w:val'), color)
    t = etree.SubElement(r, qn('w:t'))
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    t.text = text
    return r

def make_para(spacing_before='20', spacing_after='20', line='276'):
    """Create empty w:p with spacing and hanging indent.
    Spacing: 1pt before/after, 1.15 line spacing.
    Indent: 0.4cm hanging (227 DXA)."""
    p = etree.Element(qn('w:p'))
    pPr = etree.SubElement(p, qn('w:pPr'))
    sp = etree.SubElement(pPr, qn('w:spacing'))
    sp.set(qn('w:before'), spacing_before)
    sp.set(qn('w:after'), spacing_after)
    sp.set(qn('w:line'), line)
    sp.set(qn('w:lineRule'), 'auto')
    ind = etree.SubElement(pPr, qn('w:ind'))
    ind.set(qn('w:left'), '227')
    ind.set(qn('w:hanging'), '227')
    return p

def make_header_para(text):
    """Bold header paragraph - e.g. 'PRE (Medium-4): Controls in place.'"""
    p = make_para()
    p.append(make_run(text, bold=True))
    return p

def make_label_para(label, content):
    """Paragraph with bold label + regular content"""
    p = make_para()
    p.append(make_run(label + ' ', bold=True))
    p.append(make_run(content))
    return p

def make_stop_work_para(conditions):
    """STOP WORK if: paragraph"""
    p = make_para()
    p.append(make_run('STOP WORK if:', bold=True))
    p.append(make_run(' ', bold=True))
    p.append(make_run(conditions))
    return p

def make_ccvs_header_para(code, level, score):
    """CCVS header: 'WAH (High-6) CCVS HOLD POINTS:'"""
    p = make_para()
    p.append(make_run(f'{code} ({level}-{score}) CCVS HOLD POINTS:', bold=True))
    return p

def make_hold_point_para():
    """HOLD POINT — Do not commence until:"""
    p = make_para()
    p.append(make_run('HOLD POINT ', bold=True))
    p.append(make_run('—', bold=True))
    p.append(make_run(' Do not commence until:', bold=True))
    p.append(make_run(' ', bold=True))
    return p

def make_numbered_para(text, num_id, ilvl='0'):
    """Numbered list paragraph - used for HOLD POINTS with decimal 1. 2. 3. format.
    num_id must reference a valid <w:num> pointing to a decimal abstractNum."""
    p = make_para()
    pPr = p.find(qn('w:pPr'))
    numPr = etree.SubElement(pPr, qn('w:numPr'))
    ilvl_elem = etree.SubElement(numPr, qn('w:ilvl'))
    ilvl_elem.set(qn('w:val'), ilvl)
    numId_elem = etree.SubElement(numPr, qn('w:numId'))
    numId_elem.set(qn('w:val'), str(num_id))
    p.append(make_run(text))
    return p

def make_bullet_para(text, num_id, ilvl='0'):
    """Bullet list paragraph - used for Eng/Admin/PPE/STOP WORK with open circle 'o' format.
    num_id must reference a valid <w:num> pointing to a bullet abstractNum."""
    p = make_para()
    pPr = p.find(qn('w:pPr'))
    numPr = etree.SubElement(pPr, qn('w:numPr'))
    ilvl_elem = etree.SubElement(numPr, qn('w:ilvl'))
    ilvl_elem.set(qn('w:val'), ilvl)
    numId_elem = etree.SubElement(numPr, qn('w:numId'))
    numId_elem.set(qn('w:val'), str(num_id))
    p.append(make_run(text))
    return p

def make_section_label_para(label):
    """Section label paragraph - bold label only"""
    p = make_para()
    p.append(make_run(label, bold=True))
    p.append(make_run(' '))
    return p

def set_cell_text(tc, paragraphs):
    """Replace all paragraphs in a tc with new ones"""
    for p in tc.findall(qn('w:p')):
        tc.remove(p)
    for p in paragraphs:
        tc.append(p)

def set_cell_simple(tc, text, bold=False):
    """Set cell to single paragraph with text"""
    for p in tc.findall(qn('w:p')):
        tc.remove(p)
    p = make_para()
    p.append(make_run(text, bold=bold))
    tc.append(p)

def set_cell_shading(tc, fill_color, text_color='000000'):
    """Set cell background shading"""
    tcPr = tc.find(qn('w:tcPr'))
    if tcPr is None:
        tcPr = etree.SubElement(tc, qn('w:tcPr'))
        tc.insert(0, tcPr)
    shd = tcPr.find(qn('w:shd'))
    if shd is None:
        shd = etree.SubElement(tcPr, qn('w:shd'))
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_color)

def get_risk_color(level):
    """Return fill color for risk level"""
    if level.startswith('High'):
        return 'FF0000'
    elif level.startswith('Medium'):
        return 'FFFF00'
    else:
        return '00FF00'

def get_risk_text_color(level):
    if level.startswith('High'):
        return 'FFFFFF'
    return '000000'

def set_cell_text_color(tc, color):
    """Set font colour on all runs in all paragraphs in cell"""
    for p in tc.findall(qn('w:p')):
        for r in p.findall(qn('w:r')):
            rPr = r.find(qn('w:rPr'))
            if rPr is None:
                rPr = etree.SubElement(r, qn('w:rPr'))
                r.insert(0, rPr)
            c = rPr.find(qn('w:color'))
            if c is None:
                c = etree.SubElement(rPr, qn('w:color'))
            c.set(qn('w:val'), color)

def remove_cell_shading(tc):
    """Remove any shading from a cell"""
    tcPr = tc.find(qn('w:tcPr'))
    if tcPr is not None:
        shd = tcPr.find(qn('w:shd'))
        if shd is not None:
            tcPr.remove(shd)

# ============================================================
# VOCABULARY-BASED TASK BUILDER
# ============================================================

def new_task(
    name,
    scope,
    hazard_keys,
    risk_pre,
    risk_code,
    engineering,
    admin,
    ppe_keys,
    stop_work_keys,
    responsibility="Supervisor / Worker / Sub-Contract Worker",
    risk_post="Low (2)",
    ccvs=False,
    hold_points=None,
):
    """
    Create a new SWMS task using controlled vocabulary.

    Args:
        name:           Task name string (bold in Col 0)
        scope:          Scope description — goes in [brackets], italic
                        Use None or '' if no scope description needed
        hazard_keys:    List of keys from HAZARDS dict
                        e.g. ["fall_unprotected_edge", "silica_dust_cutting"]
        risk_pre:       Pre-control risk string e.g. "High (6)"
        risk_code:      Risk code e.g. "STR-H6"
        engineering:    List of vocabulary keys OR raw strings
                        Joined as em dash chain (non-CCVS)
                        or bullet list (CCVS)
        admin:          List of vocabulary keys OR raw strings
        ppe_keys:       List of PPE_ITEMS keys
                        e.g. ["steel_cap", "p2_respirator", "eye_protection"]
        stop_work_keys: List of STOP_WORK keys
                        e.g. ["silica_no_controls", "edge_no_protection"]
        responsibility: Responsibility string (default shown)
        risk_post:      Post-control risk string (default "Low (2)")
        ccvs:           True if this is a CCVS task with hold points
        hold_points:    List of hold point verification strings (CCVS only)

    Returns:
        dict compatible with build_all_swms.py row builders.
        Keys: task, task_desc, hazard, risk_pre, risk_post, code,
              resp, type, and either 'control' (STD) or
              'hold_points'/'eng'/'admin'/'ppe'/'stop_work' (CCVS).

    Raises:
        ValueError if any key not found in vocabulary
    """
    # Resolve hazards — each key must exist in HAZARDS
    hazards = [get_hazard(k) for k in hazard_keys]
    hazard_string = '. '.join(hazards)

    # Resolve PPE — comma-joined canonical items
    ppe_string = get_ppe(*ppe_keys)

    # Resolve STOP WORK — em dash joined canonical conditions
    stop_string = get_stop_work(*stop_work_keys)

    # Base dict — compatible with build_new_std_row / build_new_ccvs_row
    result = {
        'task': name,
        'task_desc': scope or '',
        'hazard': hazard_string,
        'risk_pre': risk_pre,
        'risk_post': risk_post,
        'code': risk_code,
        'resp': responsibility,
    }

    if ccvs:
        result['type'] = 'CCVS'
        result['hold_points'] = hold_points or []
        # CCVS: engineering/admin stay as lists (one per bullet)
        result['eng'] = [
            CONTROLS[e]["canonical"] if e in CONTROLS else e
            for e in engineering
        ]
        result['admin'] = [
            CONTROLS[a]["canonical"] if a in CONTROLS else a
            for a in admin
        ]
        result['ppe'] = [ppe_string]
        result['stop_work'] = [stop_string]
    else:
        result['type'] = 'STD'
        # STD: engineering/admin joined as em dash chains
        eng_string = build_engineering(*engineering)
        adm_string = build_admin(*admin)
        result['control'] = [
            ('Engineering:', eng_string),
            ('Admin:', adm_string),
            ('PPE:', ppe_string),
            ('STOP WORK if:', stop_string),
        ]

    return result


# ============================================================
# TASK DATA - NEW TASKS FOR EACH SWMS
# ============================================================

def build_std_control(code, level, score, sections):
    """Build standard task control paragraphs.
    sections: list of (label, content) tuples
    Last item should be STOP WORK
    """
    paras = []
    paras.append(make_header_para(f'{code} ({level}-{score}): Controls in place.'))
    for label, content in sections:
        if label == 'STOP WORK if:':
            paras.append(make_stop_work_para(content))
        else:
            paras.append(make_label_para(label, content))
    return paras

def build_ccvs_control(code, level, score, hold_points, eng, admin, ppe, stop_work, decimal_num_id, bullet_num_id):
    """Build CCVS HOLD POINT control paragraphs.
    hold_points: list of strings (numbered items)
    eng, admin, ppe, stop_work: lists of strings (bullet items)
    decimal_num_id: numId for HOLD POINTS (decimal format)
    bullet_num_id: numId for Eng/Admin/PPE/STOP WORK (bullet format)
    """
    paras = []
    paras.append(make_ccvs_header_para(code, level, score))
    paras.append(make_hold_point_para())
    for hp in hold_points:
        paras.append(make_numbered_para(hp, num_id=decimal_num_id))
    
    paras.append(make_section_label_para('Engineering:'))
    for e in eng:
        paras.append(make_bullet_para(e, num_id=bullet_num_id))
    
    paras.append(make_section_label_para('Admin:'))
    for a in admin:
        paras.append(make_bullet_para(a, num_id=bullet_num_id))
    
    paras.append(make_section_label_para('PPE:'))
    for pp in ppe:
        paras.append(make_bullet_para(pp, num_id=bullet_num_id))
    
    paras.append(make_section_label_para('STOP WORK if:'))
    for sw in stop_work:
        paras.append(make_bullet_para(sw, num_id=bullet_num_id))
    
    return paras

# ============================================================
# NEW TASK DEFINITIONS
# ============================================================

# --- REMEDIAL WORKS NEW TASKS ---
REMEDIAL_NEW = {
    'concrete_breakout': {
        'task': 'Concrete Breakout and Spalling Repair',
        'task_desc': 'Mechanical removal of deteriorated concrete to sound substrate using jackhammers, scabblers, and needle guns. Preparation and passivation of exposed reinforcement. Application of repair mortars to restore structural profile. Temporary propping where load-bearing elements affected.',
        'hazard': 'Structural collapse if load-bearing element undermined during breakout. Silica dust from concrete removal — Silicosis risk. Flying debris and fragments. Noise exposure. Hand-arm vibration from power tools. Working at height during façade repairs. Hidden deterioration beyond assessed extent.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'STR-H6', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'CCVS',
        'hold_points': [
            'Structural engineer repair specification and drawings on site — Depth of breakout, reinforcement treatment, repair mortar system confirmed in writing before breakout commences',
            'For Class 2 buildings: Construction Issued Regulated Design (CIRD) lodged on NSW Planning Portal per DBP Act 2020 before physical work commences',
            'Temporary propping confirmed in place where breakout affects load-bearing elements (beams, columns, slabs) — Propping design by competent person, installed and inspected before any concrete removed',
            'Exclusion zone confirmed below work area — Debris catch or overhead protection in place where work is above public or occupied areas',
        ],
        'eng': [
            'Dust extraction on all power tools — Vacuum-attached scabblers and needle guns. Water suppression where dust extraction not practicable. Physical barriers to contain debris — Mesh screens on scaffold, drop sheets below work zone. Vibration-dampened tool handles where available.',
            'Minimum 25mm clearance around exposed reinforcement — Confirmed before mortar application. Clearance allows proper cleaning, priming, and mortar encapsulation of rebar.',
        ],
        'admin': [
            'Silica dust exposure assessment completed — Air monitoring if breakout exceeds 4 hours continuous. Vibration exposure log maintained — Tool rotation every 30 minutes. Spotter below when working at height.',
            'Rebar cleaned to bright metal (SA 2.5 or equivalent). Passivation primer (zinc-rich or epoxy per engineer specification) applied within product open time — No contamination of prepared surface between cleaning and priming. Product must match specification — No substitution without engineer approval.',
            'Repair mortar applied in lifts per specification — Product and method matching engineer design. Mortar to fully encapsulate rebar with no voids. Cure time observed between lifts per product TDS. Surface finished to match surrounding profile. Repair area cured per product specification before coating or waterproofing applied.',
        ],
        'ppe': [
            'P2 respirator (minimum) — Half-face P3 with particulate filter if air monitoring indicates. Eye protection and face shield during breakout. Hearing protection (>85 dB, Class 5 minimum). Cut-resistant gloves. Steel-capped footwear.',
        ],
        'stop_work': [
            'Dust extraction fails or is inadequate — Visible dust plume beyond immediate work zone. Reinforcement cross-section loss exceeds 20% or engineer tolerance — Stop work, notify engineer for supplementary reinforcement design before proceeding. Structural concern, unexpected cracking, movement, or voids encountered during breakout — Evacuate, do not re-enter without engineer assessment. Vibration exposure limit reached. Extent of deterioration exceeds engineer specification. Unexpected services encountered.',
        ]
    },
    'crack_stitching': new_task(
        name='Crack Stitching and Structural Reinforcement',
        scope='Installation of helical bars, carbon fibre reinforcement, or stainless steel pins into prepared slots/holes to restore structural integrity of cracked masonry and concrete elements.',
        hazard_keys=[
            'silica_dust_cutting',
            'noise_cutting',
            'epoxy_resin_exposure',
            'working_at_height',
            'structural_instability',
        ],
        risk_pre='Medium (4)',
        risk_code='PRE-M4',
        engineering=[
            'vacuum_blade_guard',
            'depth_stop_cutting',
            'services_scan',
            'epoxy_waste_containment',
        ],
        admin=[
            'specification_reviewed',
            'sds_epoxy_reviewed',
            'crack_monitoring',
            'engineer_signoff_tolerance',
        ],
        ppe_keys=[
            'p2_respirator',
            'nitrile_gloves',
            'eye_protection',
            'hearing_protection',
            'steel_cap',
        ],
        stop_work_keys=[
            'crack_exceeds_tolerance',
            'unexpected_movement',
            'services_in_path',
            'engineer_hold',
            'product_temp_outside',
        ],
    ),
    'epoxy_injection': {
        'task': 'Epoxy Crack Injection',
        'task_desc': 'Identification and marking of cracks, installation of injection ports, sealing of crack face with epoxy paste, injection of epoxy resin under low pressure, removal of ports and surface finishing. Includes structural and non-structural crack injection.',
        'hazard': 'Skin sensitisation from epoxy resin — Allergic contact dermatitis. Eye contact with epoxy hardener — Chemical burns. Solvent vapour inhalation from injection products. Injection equipment under pressure — Hose or fitting failure. Exothermic reaction in large resin volumes. Silica dust from port drilling (cross-reference SIL task).',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'PRE-M4', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Injection equipment maintained per manufacturer — Pressure relief valve functional, hose connections checked before use. Mixing ratios per product data sheet — Do not exceed pot life. Resin mixed in small batches to control exotherm. Port drilling dust-controlled (HEPA shroud or wet method per SIL task).'),
            ('Admin:', 'SDS for epoxy resin, hardener, and crack sealer reviewed before use — On site and accessible. Ventilation confirmed adequate — Outdoor work preferred. Injection pressure monitored — Do not exceed manufacturer limit. Crack width and depth assessed against engineer specification before injection. Workers trained in epoxy handling and first aid for chemical contact.'),
            ('PPE:', 'Nitrile chemical-resistant gloves (minimum) — No skin contact with uncured resin. Eye protection (safety glasses or goggles). P2 respirator if in semi-enclosed area or extended exposure. Disposable coveralls recommended.'),
            ('STOP WORK if:', 'Skin contact with uncured resin — Wash immediately with soap and water, do not use solvent. Eye contact — Flush 15 minutes, seek medical attention immediately. Injection pressure exceeds manufacturer limit. Crack leaking resin externally — Depressurise and reseal. Product temperature outside application range. Exothermic reaction detected in mixing container — Do not handle, allow to cool in safe location.')
        ]
    },
    'waterproofing': new_task(
        name='Waterproofing and Membrane Application',
        scope='Application of liquid-applied or sheet membrane waterproofing systems to balconies, podiums, planter boxes, wet areas, and below-grade elements. Includes anti-carbonation coatings to cured concrete repair areas. Surface preparation, primer, membrane, and protection layers.',
        hazard_keys=[
            'chemical_primers_solvents',
            'slip_wet_surfaces',
            'fumes_enclosed',
            'manual_handling_membrane',
        ],
        risk_pre='Medium (4)',
        risk_code='PRE-M4',
        engineering=[
            'ventilation_enclosed',
            'non_slip_paths',
            'drainage_uncured',
        ],
        admin=[
            'waterproofing_spec_reviewed',
            'sds_reviewed',
            'temp_humidity_check',
            'wet_film_check',
            'anticarbonation_coating',
        ],
        ppe_keys=[
            'chemical_resistant_gloves',
            'p2_ov_respirator',
            'eye_protection',
            'non_slip_footwear',
            'disposable_coveralls',
        ],
        stop_work_keys=[
            'temp_outside_range',
            'substrate_moisture_exceeds',
            'rain_uncured_membrane',
            'ventilation_fails',
            'product_expired',
        ],
    ),
    'expansion_joint': {
        'task': 'Expansion Joint Replacement',
        'task_desc': 'Removal of failed expansion joint systems and installation of new joint sealant, backer rod, or proprietary joint covers to building façade, podium, and structural movement joints.',
        'hazard': 'Working at height during façade joint replacement. Chemical exposure from sealants and primers. Noise from cutting/grinding old joint material. Debris and dust. Hand tool injuries.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'PRE-M4', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Dust extraction during mechanical removal of old sealant. Containment of removed sealant and debris — No material to fall below. Backer rod sized correctly to joint width — Minimum 25% compression. Joint faces clean, dry, and primed before sealant application.'),
            ('Admin:', 'Joint schedule and sealant specification reviewed — Joint widths, depths, sealant type, primer compatibility confirmed. SDS for sealant, primer, and backer rod products reviewed. Joint movement range confirmed with structural engineer if movement exceeds original design. Weather check — No application in rain or below product minimum temperature.'),
            ('PPE:', 'Nitrile gloves for sealant and primer handling. Eye protection. P2 respirator if solvent-based primer. Steel capped footwear. Cut-resistant gloves for mechanical removal.'),
            ('STOP WORK if:', 'Joint movement exceeds design parameters — Substrate condition prevents proper adhesion — Rain during application — Product outside temperature range — Joint depth or width significantly different from specification.')
        ]
    },
}

# --- SPRAY PAINTING NEW TASKS ---
SPRAY_NEW = {
    'airless_setup': {
        'task': 'Airless Spray Unit Setup and Operation',
        'task_desc': 'Setup, operation, and maintenance of high-pressure airless spray equipment including pump unit, hoses, guns, and tips. Covers pressure testing, tip selection, and safe operating procedures.',
        'hazard': 'High-pressure injection injury (skin penetration). Hose failure/whip. Electrical hazard from pump motor. Noise exposure. Tip blockage and uncontrolled release.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'PRE-H6', 'resp': 'Supervisor / Worker',
        'type': 'CCVS',
        'hold_points': [
            'Operator competency confirmed: trained in airless spray equipment operation — Manufacturer training or demonstrated competence sighted',
            'Equipment pre-start completed: pump, hoses, fittings, tip guard, trigger lock, pressure relief all inspected and serviceable',
            'Maximum operating pressure confirmed and not exceeded — Pressure gauge functional and visible to operator',
            'Injection injury first aid procedure briefed to all crew — Nearest hospital with hand surgery capability identified',
        ],
        'eng': [
            'Tip guard fitted at all times — Never removed during operation. Trigger lock engaged when not actively spraying. Pressure relief valve functional. Hose whip checks fitted to all high-pressure connections. Earthing/grounding strap connected to prevent static discharge — Critical with solvent-based products.',
        ],
        'admin': [
            'Exclusion zone around spray unit — Minimum 3m from pump and hose connections. Pressure bleed-down procedure followed before any tip change, filter clean, or maintenance. Never point gun at any person. Two-person operation when spraying at height.',
        ],
        'ppe': [
            'Leather gloves when handling hoses and connections. Eye protection. Hearing protection (>85 dB, Class 5). Steel capped footwear. P2 respirator minimum — Upgrade to half-face with OV/P3 cartridge for solvent-based products.',
        ],
        'stop_work': [
            'Hose damage, kink, or abrasion detected — Pressure gauge not functioning — Tip guard missing or damaged — Any injection injury (treat as medical emergency — Do not wait for symptoms) — Earthing strap disconnected with solvent-based products — Operator not trained.',
        ]
    },
    'spray_exterior': {
        'task': 'Spray Application — Exterior (Open Air)',
        'task_desc': 'Airless spray application of paints, primers, sealers, and texture coatings to exterior surfaces in open-air conditions. Includes overspray management and environmental controls. Electrostatic spray application is excluded from this SWMS — Requires separate risk assessment and equipment-specific controls.',
        'hazard': 'Overspray drift to adjacent properties, vehicles, and persons. Paint mist inhalation. Slip hazard from overspray on walkways. Wind-driven spray. Working at height.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'PRE-M4', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Overspray containment: scaffold shrink-wrap, drop sheets, and masking to all adjacent surfaces, windows, vehicles, and property. Surface preparation completed and accepted before spraying — Clean, dry, free of contaminants. Wind breaks where practicable. Spray tip selected for minimum overspray — Correct fan width and orifice size for product. Tip condition checked — Replace when worn (indicated by distorted fan pattern or increased overspray).'),
            ('Admin:', 'Wind speed monitored — No spraying above 15 km/h or per product data sheet limit, whichever is lower. Application temperature and humidity within product data sheet limits — Check before each spray session. Recoat windows observed per product TDS. DFT (dry film thickness) checked with calibrated gauge at frequency specified by coating specification. Adjacent property and vehicle owners notified 48 hours before spraying. Spotter positioned to warn of pedestrians and wind changes. Overspray inspection after each spray session — Immediate clean-up of any overspray. Spray-specific emergency procedures briefed: (a) skin injection injury — Do not apply pressure, do not wait for symptoms, transport to hospital with hand/microsurgery capability immediately; (b) solvent fire — CO2 or dry chemical extinguisher only, no water on solvent fire, evacuate if not immediately controlled.'),
            ('PPE:', 'Half-face respirator with P2/OV cartridge. Eye protection or goggles. Disposable spray suit or coveralls. Nitrile gloves. Head cover.'),
            ('STOP WORK if:', 'Wind exceeds limit — Overspray escaping containment — Adjacent property complaint — Rain during application — Pedestrians entering spray zone — Containment failure — Suspected skin injection injury (treat as medical emergency — Do not wait for symptoms, transport to hospital with hand surgery capability immediately).')
        ]
    },
    'spray_interior': {
        'task': 'Spray Application — Interior (Enclosed/Confined)',
        'task_desc': 'Airless spray application inside buildings, enclosed plant rooms, stairwells, basements, and areas with limited natural ventilation. Includes mandatory ventilation and atmospheric monitoring requirements. Electrostatic spray application is excluded from this SWMS — Requires separate risk assessment and equipment-specific controls.',
        'hazard': 'Solvent vapour accumulation — Explosive atmosphere risk with solvent-based products. Paint mist inhalation in enclosed space. Reduced visibility. Oxygen depletion in confined areas. Ignition sources.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'HAZ-H6', 'resp': 'Supervisor / Worker',
        'type': 'CCVS',
        'hold_points': [
            'Ventilation assessment completed: mechanical ventilation sized for room volume and product vapour generation rate — Minimum 20 air changes per hour for active spray zones (AS 1668.2). Ventilation design documented',
            'Atmospheric monitoring in place if solvent-based products used — LEL monitor calibrated and alarming at 10% LEL',
            'All ignition sources eliminated: no hot work, no unsealed electrical, no mobile phones in spray zone if solvent-based',
            'Emergency egress routes clear and marked — Minimum two exits from spray area where practicable',
            'Confined space assessment completed per WHS Regulation Part 4.3 for any area with restricted entry/exit (fewer than 2 standard exits, or exit requires climbing/crawling/travel >10m). If confined space: entry permit, standby person, and atmospheric monitoring required before spraying commences',
        ],
        'eng': [
            'Mechanical exhaust ventilation running before, during, and 30 minutes after spraying. Fresh air intake positioned to create cross-flow ventilation — Extraction discharges externally, no recirculation. Explosion-proof electrical fittings in spray zone if solvent-based products. LEL monitor with audible alarm at 10% LEL — Calibrated for primary solvent in product SDS. Continuous LEL monitoring during active spraying and for 30 minutes after last spray pass.',
        ],
        'admin': [
            'Water-based products preferred over solvent-based for interior work. Application temperature and humidity within product data sheet limits. Recoat windows observed per product TDS. DFT checked with calibrated gauge per coating specification. Spray schedule coordinated to minimise exposure duration. Buddy system — No solo interior spraying.',
        ],
        'ppe': [
            'Full-face respirator with combination OV/P3 cartridge for solvent-based. Half-face with P2/OV for water-based. Disposable spray suit. Nitrile gloves. Eye protection under full-face respirator.',
        ],
        'stop_work': [
            'LEL alarm activates — Ventilation fails or reduces — Any worker reports dizziness, nausea, or irritation — Visibility drops below 3m — Ignition source identified in spray zone — Single exit only and no buddy available — Area determined to be confined space and no confined space entry permit in force.',
        ]
    },
    'overspray_env': {
        'task': 'Overspray and Environmental Protection',
        'task_desc': 'Protection of adjacent properties, vehicles, landscaping, waterways, and stormwater systems from paint overspray, wash-water, and waste materials during spray painting operations.',
        'hazard': 'Environmental contamination of stormwater and waterways. Property damage from overspray. Paint waste and wash-water disposal. Community complaint.',
        'risk_pre': 'Medium (3)', 'risk_post': 'Low (1)',
        'code': 'ENV-M3', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Stormwater drains bunded and covered within 10m of spray zone. Wash-water captured in containment — No discharge to stormwater. Drop sheets and masking on all adjacent surfaces. Scaffold shrink-wrap where exterior spraying from scaffold.'),
            ('Admin:', 'Environmental management plan reviewed — Stormwater protection, waste disposal, noise management. Paint waste and wash-water disposed of as trade waste — Not to sewer or stormwater. Adjacent property register maintained — Pre/post condition photos. Resident/tenant notification 48 hours before spray operations.'),
            ('PPE:', 'As per spray application task requirements.'),
            ('STOP WORK if:', 'Overspray escapes containment — Paint or wash-water enters stormwater — Community complaint not resolved — Containment fails — Wind exceeds spray limit.')
        ]
    },
    'spray_cleaning': {
        'task': 'Spray Equipment Cleaning and Solvent Use',
        'task_desc': 'Flushing, cleaning, and maintenance of airless spray equipment including pumps, hoses, guns, filters, and tips. Use of thinners, solvents, and cleaning agents.',
        'hazard': 'Solvent vapour inhalation. Skin contact with solvents and uncured coatings. High-pressure fluid during flush cycle. Solvent waste disposal. Fire risk from solvent-soaked rags.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'HAZ-M4', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Cleaning in well-ventilated area only — Outdoors preferred. Solvent waste captured in sealed metal containers — Not poured to drain. Pressure bled down before disassembly. Solvent-soaked rags in self-closing metal bin — Removed from site daily.'),
            ('Admin:', 'SDS for all solvents and thinners reviewed. Minimum solvent quantity used — Water flush first where possible with water-based products. Solvent waste disposal via licensed contractor. No smoking or ignition sources within 5m of cleaning area. Solvent fire emergency: CO2 or dry chemical extinguisher only — No water. Fire extinguisher within 5m of cleaning area. Solvent splash to eyes: flush with water for 20 minutes, seek medical attention.'),
            ('PPE:', 'Nitrile chemical-resistant gloves. P2 respirator with organic vapour cartridge. Eye protection. Disposable coveralls if splash risk.'),
            ('STOP WORK if:', 'Solvent spill not contained — Ventilation inadequate — Ignition source near cleaning area — Solvent waste container full or unsealed.')
        ]
    },
    'isocyanate_2pack': {
        'task': 'Isocyanate / 2-Pack Coating Application',
        'task_desc': 'Spray application of isocyanate-containing products (2-pack polyurethane, 2K epoxy-urethane, isocyanate hardeners) and anti-graffiti coatings. Includes mandatory health surveillance, supplied-air respiratory protection, and continuous air monitoring.',
        'hazard': 'Respiratory sensitisation from isocyanate inhalation — Occupational asthma, irreversible airway damage. Skin sensitisation. Exothermic reaction during mixing. Vapour accumulation in enclosed spaces.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'HAZ-H6', 'resp': 'Supervisor / Worker',
        'type': 'CCVS',
        'hold_points': [
            'Product SDS reviewed — Isocyanate component identified (HDI, MDI, TDI, or polymeric isocyanate). Isocyanate-specific controls activated',
            'Workers confirmed medically fit for isocyanate exposure — Pre-employment respiratory assessment (spirometry/lung function) completed. No worker with known respiratory sensitisation to isocyanates permitted in spray zone',
            'Supplied-air respiratory protection confirmed: positive-pressure airline system or PAPR with combination OV/P3. Half-face cartridge respirator is NOT adequate for spray application of isocyanates',
            'Continuous isocyanate air monitoring arranged — Colorimetric tubes or real-time monitor. National WES: 0.02 mg/m\u00b3 (8hr TWA) for monomeric HDI, 0.07 mg/m\u00b3 for polymeric HDI',
        ],
        'eng': [
            'Supplied-air respirator (positive-pressure airline) for all workers in spray zone. Local exhaust ventilation or spray booth with external discharge — No recirculation. Mixing of 2-pack components in ventilated area with spill containment. Isocyanate-specific spill kit available.',
        ],
        'admin': [
            'Health surveillance program per WHS Regulation Schedule 14: baseline spirometry before first exposure, annual review by medical practitioner. Health surveillance records retained for 30 years minimum. Air monitoring results recorded and communicated to workers — Any exceedance triggers immediate work cessation and control review. Product-specific application windows (temperature, humidity, pot life) checked before mixing.',
        ],
        'ppe': [
            'Supplied-air respirator (positive-pressure airline or PAPR with OV/P3). Disposable Type 5/6 coveralls — Removed before leaving spray zone. Nitrile chemical-resistant gloves. Eye protection or full-face supplied-air hood. Steel capped footwear.',
        ],
        'stop_work': [
            'Any respiratory symptoms in spray zone (wheeze, chest tightness, cough, shortness of breath) — Treat as sensitisation event, remove worker, seek medical assessment. Air monitoring exceeds WES — Supplied-air system fault — Ventilation fails — Product mixed outside pot life — Worker without medical fitness clearance — SDS not available for product.',
        ]
    },
}

# --- GROUNDWORKS NEW TASKS ---
GROUND_NEW = {
    'excavation': {
        'task': 'Excavation and Trenching',
        'task_desc': 'Open-cut excavation, trenching for services, footings, and drainage. Includes benching, battering, and shoring of excavation walls deeper than 1.5m.',
        'hazard': 'Collapse of excavation walls — Burial and suffocation. Fall into excavation. Contact with underground services. Flooding/water ingress. Ground vibration from adjacent plant. Atmospheric contamination — Build-up of gases, fumes, oxygen depletion. Impact on adjacent buildings and structures.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'WAH-H6', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'CCVS',
        'hold_points': [
            'Ground Works Permit raised and approved per HY Works Permit procedure — Permit in hard copy with operator/excavation crew, with current DBYD, as-built drawings, services layouts, and engineers report attached',
            'Geotechnical assessment reviewed: soil classification confirmed — Batter angles and shoring requirements determined before excavation commences',
            'Adjacent buildings and structures assessed by competent person (structural/geotechnical engineer) before excavation commences — Vibration monitoring and structural integrity controls implemented per engineer\'s assessment',
            'Dial Before You Dig (DBYD) plans obtained and current (within 30 days). Service locations confirmed by non-destructive potholing within 1m of any indicated service',
            'Excavation deeper than 1.5m: shoring, benching, or battering designed by competent person per AS 4678 and WHS Regulation Chapter 6',
            'Barricading per HY tiered system: up to 1m deep — Bunting/barrier mesh (star pickets with safety caps at max 2.5m spacing, at least 1m from edge); greater than 1m deep — Crowd control barriers, water-filled barriers, or 1.8m high interlockable hard fencing. Excavations >1.5m: "DANGER DEEP EXCAVATION" signage',
        ],
        'eng': [
            'Shoring installed progressively as depth increases. Benching/battering angles per geotechnical report — Never steeper than soil classification allows. Dewatering active if water table encountered. Edge protection: spoil stockpile setback from excavation edge — Minimum 1m or equal to excavation depth, whichever is greater. Safe access/egress for excavations >1.5m — Ladders secured to trench shields extending minimum 1m above top of excavation, or ramps/steps as appropriate. Controls to prevent objects falling on workers in excavations >1.5m — Toe boards, guard rails at excavation edge, trench box sheets extending above trench depth.',
        ],
        'admin': [
            'Daily inspection of excavation walls by competent person before any worker entry. After rain: re-inspection before re-entry. Excavation permit system in place for depths >1.5m. Emergency rescue plan for excavation entrapment — Rescue equipment on site (ladder, harness, retrieval line). Excavation assessed for confined space classification per HY Confined Space procedure. Atmospheric testing conducted before worker entry where gas or oxygen risk identified. No combustion engine plant operated in excavation while workers are inside. Excavations isolated and made safe at end of each shift/day and when not in use — Barriers, covers, or backfill as appropriate.',
        ],
        'ppe': [
            'Steel capped footwear. Hard hat. High-vis vest or shirt. Cut-resistant gloves. Harness and retrieval line if entering excavation >1.5m without shoring.',
        ],
        'stop_work': [
            'Wall cracking, slumping, or movement observed — Water ingress not controlled by dewatering — Shoring damaged or displaced — Services exposed and not confirmed de-energised — Spoil encroaching on edge setback — Any worker in excavation >1.5m without shoring/benching — Atmospheric testing indicates unsafe conditions (oxygen depletion, gas detection, engine fumes in excavation) — Ground Works Permit not raised — Adjacent structure integrity concern identified.',
        ]
    },
    'services_location': {
        'task': 'Underground and Overhead Services Location and Protection',
        'task_desc': 'Location, identification, and protection of underground and overhead services including electrical, gas, water, sewer, telecommunications, and stormwater during ground disturbance activities. Includes overhead power line management per HY Underground and Overhead Services procedure.',
        'hazard': 'Electrocution from contact with underground power cables or overhead power lines. Gas main rupture — Explosion and fire. Water main burst — Flooding. Telecommunications damage — Service disruption. Sewer damage — Contamination. Plant contact with overhead conductors.',
        'risk_pre': 'High (9)', 'risk_post': 'Low (2)',
        'code': 'ELE-H9', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'CCVS',
        'hold_points': [
            'DBYD plans obtained, current, and reviewed by all workers involved in ground disturbance. Plans less than 30 days old',
            'Service locator (CAT/Genny or GPR) used to confirm locations before any mechanical excavation. Services marked on ground with paint/flags',
            'Hand dig/vacuum excavation (potholing) within 1m horizontal and 300mm vertical of any indicated service — No mechanical excavation within this zone',
            'Service owner contacted and clearance obtained for work near high-risk services (HV power, high-pressure gas)',
            'Overhead services identified: approach distances and work zones (Zone A/B/C) established per HY Underground and Overhead Services procedure. Electrical spotters required in Zone B. Plant fitted with limiting/slowing devices where it can reach Zone C',
        ],
        'eng': [
            'Services physically exposed by hand/vacuum excavation before mechanical plant operates within proximity. Exposed services supported and protected from damage. Isolation of services where practicable — De-energise, shut off, or depressurise.',
        ],
        'admin': [
            'Competent spotter required when working within 500mm of underground asset per HY Underground Services procedure. Excavators not to be used within distances specified by state legislation and asset owners. Service strike emergency procedure briefed to all workers — Isolation points identified. Gas: evacuate, no ignition, call 000 and gas authority. Electrical: do not approach, isolate at source, call 000 and network provider. All workers inducted on service locations (underground and overhead) marked on site plan.',
        ],
        'ppe': [
            'Steel capped footwear. Hard hat. High-vis vest or shirt. Insulated gloves if working near suspected electrical services. Cut-resistant gloves.',
        ],
        'stop_work': [
            'Service encountered not shown on DBYD plans — Any service contact (even minor) — Odour of gas detected — Water flow from unknown source — Service locator readings inconsistent with plans — Mechanical plant within 1m of unconfirmed service — Plant approaching overhead power line safe approach distance — Spotter not available within 500mm of underground asset.',
        ]
    },
    'mobile_plant': {
        'task': 'Powered Mobile Plant — Excavators, Loaders, Rollers',
        'task_desc': 'Operation of excavators, backhoes, skid steers, front-end loaders, rollers, and other powered mobile plant on construction sites. Includes delivery, setup, operation, and demobilisation.',
        'hazard': 'Collision with workers, structures, or other plant. Rollover. Overhead power line contact. Crush injury. Noise. Vibration. Blind spots.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'MOB-H6', 'resp': 'Supervisor / Operator / Worker',
        'type': 'CCVS',
        'hold_points': [
            'Operator holds current HRWL where required by legislation, or VOC/Statement of Attainment issued by an RTO for the specific plant class (e.g. excavator LE, roller LR, loader LL/LS, dozer LZ) — Licence/VOC sighted and recorded. VOC assessments not undertaken by an RTO will not be accepted per HY',
            'Plant safety verification completed upon arrival per HY procedure — Plant approved for use by HY, verification sticker displayed. Plant Setup permit issued where required (piling rigs, mobile cranes, concrete boom pumps)',
            'Plant pre-start inspection completed and recorded — All safety systems functional (ROPS, FOPS, seatbelt, reversing alarm, camera/mirrors)',
            'Exclusion zones established: minimum 3m from operating plant for pedestrians — Spotter in place when pedestrians must enter zone',
            'Overhead power line assessment completed — Safe approach distances confirmed per AS/NZS 4576',
        ],
        'eng': [
            'ROPS and FOPS fitted and certified. Reversing camera and alarm operational. Rotating beacon active during operation. Physical barriers between plant operating zone and pedestrian areas where practicable. Outriggers deployed for lifting operations.',
        ],
        'admin': [
            'Plant movement plan reviewed — Travel paths, exclusion zones, overhead hazards, underground services all identified. Spotter assigned for reversing and blind spot operations. Communication between operator and ground crew — Hand signals or two-way radio. Daily pre-start log maintained. Zone of influence calculated for plant operating near excavations and underground pipes per HY Mobile Plant procedure (clay 1:1 ratio, sand/fill 2:1 ratio). Physical barriers (wheel stoppers, berms) installed to restrict plant movement within zone of influence. Plant work zones established based on geotechnical information — Ground bearing capacity confirmed adequate for plant type.',
        ],
        'ppe': [
            'Operator: seatbelt worn at all times. Hard hat, steel capped footwear, high-vis vest or shirt for all ground personnel. Hearing protection (>85 dB) within 10m of operating plant.',
        ],
        'stop_work': [
            'Licence not current — Pre-start defect not rectified — Pedestrian in exclusion zone — Spotter not available for reversing — Overhead power line approach distance compromised — Ground conditions unsafe (soft, unstable) — Operator fatigued.',
        ]
    },
    'formwork': {
        'task': 'Formwork and Steel Fixing',
        'task_desc': 'Erection, inspection, and stripping of formwork for concrete footings, slabs, walls, and columns. Installation of reinforcement steel (rebar), mesh, and embedments.',
        'hazard': 'Collapse of formwork during pour. Struck by falling formwork components. Puncture wounds from rebar and tie wire. Manual handling of heavy forms and steel. Working at height on formwork.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'STR-M4', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Formwork designed by competent person — Load calculations for concrete head and pump pressure. Props and bracing per formwork design. Rebar caps on all exposed vertical reinforcement. Mechanical lifting for formwork panels >25kg.'),
            ('Admin:', 'Formwork inspection by competent person before pour — Checklist completed and signed. Strip sequence planned — No early stripping before concrete reaches minimum strength. Steel fixing schedule and bar schedule checked against engineering drawings.'),
            ('PPE:', 'Steel capped footwear. Hard hat. Cut-resistant gloves. Long sleeves. Eye protection when cutting tie wire or reinforcement.'),
            ('STOP WORK if:', 'Formwork movement, bulging, or deflection during pour — Props not plumb or bracing inadequate — Rebar caps missing on vertical bars — Concrete strength not confirmed before stripping — Formwork design not available for inspection.')
        ]
    },
    'concrete_pour': {
        'task': 'Concrete Pouring and Finishing',
        'task_desc': 'Placement of ready-mix concrete by pump, crane-and-kibble, or direct discharge. Includes vibration, screeding, floating, and finishing of concrete surfaces.',
        'hazard': 'Concrete pump line failure — High-pressure release. Chemical burns from wet concrete (alkaline). Manual handling — Vibrator, screeds. Slip hazard on wet concrete. Noise.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'PRE-M4', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Concrete pump lines secured at all connections — Safety chains or clips. Pump line whip restraints at bends. Formwork bracing checked immediately before pour. Vibrator connected to safety line to prevent loss into pour.'),
            ('Admin:', 'Pour plan reviewed — Sequence, volume, timing, finishing requirements. Formwork pre-pour inspection completed and signed off. Concrete docket checked on arrival — Slump, strength, admixtures match specification. Wash-out area prepared — No wash-out to stormwater.'),
            ('PPE:', 'Waterproof boots (gumboots) when standing in wet concrete. Nitrile gloves — No skin contact with wet concrete (pH 12-13 causes chemical burns). Eye protection. Long sleeves.'),
            ('STOP WORK if:', 'Pump line blockage with pressure build-up — Formwork movement during pour — Concrete strength/slump does not match specification — Rain affecting finish quality — Wash-out entering stormwater.')
        ]
    },
    'backfill': {
        'task': 'Backfill, Compaction, and Grading',
        'task_desc': 'Placement and compaction of fill material including sand, gravel, road base, and select fill. Grading of surfaces to design levels. Use of compaction equipment (plate compactor, roller, rammer).',
        'hazard': 'Hand-arm vibration from compaction equipment. Noise exposure. Dust generation. Struck by mobile plant during backfill. Trench collapse during backfill operations.',
        'risk_pre': 'Medium (3)', 'risk_post': 'Low (1)',
        'code': 'PRE-M3', 'resp': 'Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Compaction equipment with vibration-dampened handles. Dust suppression with water spray during dry conditions. Backfill placed in controlled lifts — Maximum layer thickness per geotechnical specification.'),
            ('Admin:', 'Compaction testing at specified intervals and depths per geotechnical requirements — Test results recorded and compared to specification before next lift placed. Fill material source and quality confirmed — No contaminated or unsuitable material. Vibration exposure log maintained — Tool rotation every 30 minutes. Level checks against survey marks — Final levels verified by surveyor before handover.'),
            ('PPE:', 'Steel capped footwear. Hearing protection (>85 dB). P2 dust mask in dry/dusty conditions. Cut-resistant gloves. High-vis vest or shirt.'),
            ('STOP WORK if:', 'Vibration exposure limit reached — Contaminated or unsuitable fill material identified — Compaction test failures — Trench wall movement during backfill — Dust not controlled.')
        ]
    },
    'drainage': {
        'task': 'Drainage and Stormwater Installation',
        'task_desc': 'Installation of stormwater pipes, pits, grates, and associated drainage infrastructure. Includes pipe laying, jointing, bedding, and connection to existing systems.',
        'hazard': 'Working in trenches — Collapse risk. Manual handling of pipes and pit components. Exposure to existing sewer or contaminated water. Crush injury during pipe lowering.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'PRE-M4', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Trench shored or battered per excavation task requirements. Mechanical lifting for pipes >25kg. Pipe bedding material placed and compacted before pipe laying. Existing services located and protected per services task requirements.'),
            ('Admin:', 'Pipe grades and falls checked against hydraulic design. Jointing method confirmed — Solvent cement, rubber ring, or mechanical coupling per specification. No entry to live sewer pit without confined space assessment. CCTV inspection of completed pipework where specified.'),
            ('PPE:', 'Steel capped footwear. Cut-resistant gloves. Eye protection when cutting pipe. High-vis vest or shirt. Waterproof boots if working in water.'),
            ('STOP WORK if:', 'Trench not shored when depth requires it — Connection to live sewer without isolation — Pipe grade incorrect — Existing services not confirmed before crossing — Water ingress not controlled.')
        ]
    },
    'dewatering': {
        'task': 'Dewatering Operations',
        'task_desc': 'Removal of groundwater, surface water, and stormwater from excavations, trenches, and work areas using pumps and associated equipment. Includes water disposal and environmental controls.',
        'hazard': 'Electrical hazard from pumps in water. Excavation instability from water removal. Contaminated water handling. Erosion and sediment runoff. Noise from pump operation.',
        'risk_pre': 'Medium (3)', 'risk_post': 'Low (1)',
        'code': 'ENV-M3', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Electric pumps on RCD-protected circuits — Leads clear of water. Pump intake screened to prevent blockage. Discharge via sediment control — Silt fence, sediment basin, or filter sock. No direct discharge to stormwater without filtration.'),
            ('Admin:', 'Dewatering and discharge conducted in accordance with project Erosion and Sediment Control Plan (ESCP/SWMP) per HY Environmental standard. Dewatering licence or approval obtained if required by local authority. Water quality tested if contamination suspected — Disposal via licensed facility if contaminated. Pump operation monitored — Excavation stability checked during dewatering. Discharge location and flow rate recorded.'),
            ('PPE:', 'Waterproof boots. Cut-resistant gloves. Hearing protection (>85 dB) near pump.'),
            ('STOP WORK if:', 'Electrical fault on pump — Discharge entering stormwater without filtration — Excavation instability during dewatering — Contaminated water identified — Pump discharge flooding adjacent property.')
        ]
    },
    'shoring': {
        'task': 'Shoring and Temporary Support',
        'task_desc': 'Installation, inspection, and removal of temporary structural support systems including trench shoring, propping of existing structures, underpinning support, and temporary bracing.',
        'hazard': 'Collapse of unsupported excavation or structure. Crush injury during installation. Failure of shoring system under load. Working in confined trench. Manual handling of heavy components.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'STR-H6', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'CCVS',
        'hold_points': [
            'Shoring system designed by competent person or structural engineer — Design documentation on site and current for ground conditions',
            'Shoring components inspected before installation — Certified, rated, and matched to design specification',
            'Installation supervised by competent person — Progressive installation from top down in trenches',
            'No worker entry to unshored excavation >1.5m depth',
        ],
        'eng': [
            'Hydraulic or mechanical shoring systems rated for soil type and depth. Props and struts positioned per design — Bearing plates on all contact surfaces. Waling and sheeting per design specification. Shoring to remain in place until backfill reaches safe height.',
        ],
        'admin': [
            'Shoring managed per HY Temporary Works procedure. Any changes to shoring design or installed system authorised and signed off by qualified engineer. Daily inspection of shoring by competent person — Condition, alignment, load, ground movement. Subcontractor to submit competency records for nominated inspection personnel per HY procedure. Shoring removal sequence planned — Never remove from bottom up. After rain or seismic event — Re-inspection before re-entry. Load monitoring where specified by engineer.',
        ],
        'ppe': [
            'Steel capped footwear. Hard hat. Cut-resistant gloves. High-vis vest or shirt.',
        ],
        'stop_work': [
            'Shoring movement, displacement, or deformation — Ground cracking or slumping adjacent to excavation — Shoring components damaged or not matched to design — Competent person not available for inspection — Water ingress undermining shoring foundations.',
        ]
    },
    'contaminated_soil': {
        'task': 'Contaminated Soil Management',
        'task_desc': 'Identification, handling, stockpiling, and disposal of potentially contaminated soil encountered during earthworks. Includes asbestos-containing soil, hydrocarbon-contaminated material, and acid sulphate soils.',
        'hazard': 'Exposure to asbestos fibres in soil. Hydrocarbon vapour inhalation. Skin contact with contaminated material. Incorrect disposal — Environmental and legal liability.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'HAZ-M4', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Contaminated soil stockpiled on plastic sheeting — Covered when not being loaded. Dust suppression during excavation and loading. Separate stockpiles for different contamination types. Stormwater controls to prevent contaminated runoff.'),
            ('Admin:', 'Contamination assessment report reviewed before earthworks — Known contamination areas mapped on site plan. Unexpected finds protocol: stop work, isolate area, notify supervisor, test before proceeding. Waste classification per EPA guidelines — Disposal to licensed facility with tracking documentation. Chain of custody records maintained.'),
            ('PPE:', 'P2 respirator minimum — Upgrade to half-face P3 if asbestos suspected. Nitrile gloves. Disposable coveralls if handling known contaminated material. Steel capped footwear.'),
            ('STOP WORK if:', 'Unexpected odour, discolouration, or material inconsistent with contamination report — Suspected asbestos encountered — No waste classification available — Disposal facility not confirmed — Dust from contaminated material not controlled.')
        ]
    },
}

# --- CLADDING WORKS NEW TASKS ---
CLADDING_NEW = {
    'panel_install': {
        'task': 'Cladding Panel Lifting and Installation',
        'task_desc': 'Mechanical lifting, positioning, and fixing of cladding panels including metal composite, fibre cement, terracotta, timber, and aluminium systems. Includes crane, hoist, and manual lifting operations.',
        'hazard': 'Falling panel during lift — Struck by. Panel caught by wind. Crush injury during positioning. Working at height during installation. Overloading of scaffold or EWP with panel weight.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'STR-H6', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'CCVS',
        'hold_points': [
            'Lift plan completed: panel weights confirmed, lifting equipment rated and certified, rigging method and attachment points verified',
            'Wind speed monitored — No lifting above 30 km/h or panel manufacturer limit, whichever is lower. Large panels (>5m²): no lifting above 20 km/h',
            'Structural engineer wind loading sign-off obtained for panel installation sequence — Temporary and permanent wind loading conditions verified for panels during and after installation',
            'Exclusion zone established below lifting zone — No workers beneath suspended panel at any time',
            'Scaffold or EWP load rating confirmed adequate for panel weight plus worker weight plus tools',
        ],
        'eng': [
            'Panel handling equipment (suction cups, clamps, lifting frames) rated for panel weight and type. Tag lines on all panels during crane lifts. Temporary fixing/bracing immediately on placement — Panel not released from lifting equipment until minimum fixings installed per design. Bracing props locked (not hand-tight) and inspected per design — Bracing design by competent person, removal only with structural engineer approval.',
        ],
        'admin': [
            'Installation sequence per cladding design — Verified with structural engineer for load distribution. Curtain wall and unitised systems: building tolerance survey completed before fabrication — Floor-to-floor heights, slab edges, column positions verified against design tolerances. Bracing inspection regime maintained — Daily check of all temporary bracing until permanent fixings complete and engineer confirms bracing can be removed. Glazing panels: suction cup lifters rated for glass weight and surface condition, protective covers maintained until handover, no handling in rain or with wet gloves. Panel storage on site — Stacked per manufacturer requirements, secured against wind. Oversized panel delivery: route survey from truck to installation point — Access width, overhead clearance, floor loading confirmed. Lifting and handling method statement for panels exceeding 100kg or 3m length. Delivery coordination — Just-in-time where possible to minimise on-site storage.',
        ],
        'ppe': [
            'Hard hat. Cut-resistant gloves. Steel capped footwear. Eye protection. Harness when working at height. High-vis vest or shirt.',
        ],
        'stop_work': [
            'Wind exceeds lift limit — Rigging equipment defective — Panel damaged and structural integrity compromised — Exclusion zone breached — Scaffold/EWP overloaded — Fixing system not per design specification — Bracing removed without engineer approval — Bracing props found unlocked or displaced.',
        ]
    },
    'panel_removal': {
        'task': 'Cladding Panel Removal and Demolition',
        'task_desc': 'Controlled removal and demolition of existing cladding systems including assessment for hazardous materials, sequencing, and structural stability during progressive removal.',
        'hazard': 'Falling panels — Uncontrolled release. Asbestos or lead in existing cladding. Structural instability during progressive removal. Dust and debris. Working at height.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'STR-H6', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'CCVS',
        'hold_points': [
            'Hazardous materials assessment completed: existing cladding tested for asbestos and lead — Clearance obtained or licensed removal arranged before general demolition',
            'Demolition sequence designed by competent person — Structural engineer consulted if cladding contributes to building stability',
            'Exclusion zone established below removal zone — Barricading and signage in place',
            'All panels secured before fixing removal commences — No unsecured panels at any time',
        ],
        'eng': [
            'Panels secured with temporary fixings or restraint before permanent fixings removed. Controlled lowering — No dropping or throwing panels. Debris containment — Scaffold netting, catch platforms, enclosed chutes for waste material. Dust suppression during cutting.',
        ],
        'admin': [
            'Demolition plan reviewed by all workers. Removal sequence strictly followed — Top to bottom, one panel at a time. Asbestos or lead identified: licensed removalist engaged per WHS Regulation. Waste segregation — Recyclable, hazardous, general.',
        ],
        'ppe': [
            'Hard hat. Cut-resistant gloves. Steel capped footwear. Eye protection and face shield during cutting. P2 respirator. Harness when working at height.',
        ],
        'stop_work': [
            'Suspected asbestos identified during removal — Structural concern raised by competent person — Panel release not controlled — Exclusion zone breached — Wind making panel handling unsafe — Dust not controlled.',
        ]
    },
    'fixing_fastening': {
        'task': 'Fixing and Fastening — Drilling, Screwing, Riveting',
        'task_desc': 'Mechanical fixing of cladding panels, subframes, brackets, and components using power drills, screw guns, rivet guns, and pneumatic tools. Includes chemical anchoring and structural fixings.',
        'hazard': 'Drill bit breakage — Flying fragments. Noise exposure. Hand-arm vibration. Struck by rivet or screw. Electrical hazard from power tools. Working at height.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'PRE-M4', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Drill bits and fasteners matched to substrate — Masonry, steel, or timber. Depth stop set for all chemical anchor drilling. Vibration-dampened tool handles where available. All power tools test-tagged current per AS/NZS 3012 — 3-monthly on construction sites.'),
            ('Admin:', 'Fixing schedule and specification reviewed — Fastener type, size, spacing, edge distance, embedment depth per cladding design. Panel alignment and plumb checked against design tolerances before fixing — Laser level or string line. Pull-out testing at specified frequency per design. Services scan before drilling into any unknown substrate. Swarf and debris cleaned up progressively.'),
            ('PPE:', 'Eye protection and face shield when drilling overhead. Hearing protection (>85 dB). Cut-resistant gloves. Steel capped footwear.'),
            ('STOP WORK if:', 'Substrate different from specification — Fixing pull-out failure — Services detected in drilling path — Power tool defective — Drill bit breakage frequency indicates wrong bit/substrate combination.')
        ]
    },
    'metal_cutting': {
        'task': 'Metal Cutting and Fabrication On-Site',
        'task_desc': 'Cutting, grinding, and fabrication of metal cladding components, subframes, and flashings on site using angle grinders, tin snips, nibblers, and guillotines.',
        'hazard': 'Hot sparks and swarf — Fire risk and burns. Noise exposure. Sharp edges on cut metal. Eye injury from grinding. Kickback from angle grinder.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'PRE-M4', 'resp': 'Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Designated cutting area with fire-resistant surface. Guard fitted on all angle grinders — Correct disc type for material (metal cutting disc, not masonry). Fire extinguisher within 5m of hot work area. Sharp edge protection — Deburring after cutting.'),
            ('Admin:', 'Hot work assessment completed if cutting near combustibles. Fire watch maintained for 30 minutes after hot work ceases. Cutting scheduled to minimise impact on adjacent work — Noise and spark management. Off-site prefabrication preferred where possible.'),
            ('PPE:', 'Face shield and eye protection. Hearing protection (>85 dB, Class 5). Leather or cut-resistant gloves. Long sleeves — No synthetic clothing near sparks. Steel capped footwear.'),
            ('STOP WORK if:', 'Grinder guard missing or damaged — Wrong disc type for material — Combustibles in spark path — Fire extinguisher not available — Synthetic clothing being worn near sparks.')
        ]
    },
    'weatherproofing': {
        'task': 'Weatherproofing and Flashing Installation',
        'task_desc': 'Installation of flashings, weatherseals, cavity closers, sarking, and weather barriers to cladding systems. Includes window and door head/sill/jamb flashings and parapet cappings.',
        'hazard': 'Sharp edges on flashings — Lacerations. Manual handling of long flashing pieces. Wind catching flashing during installation. Working at height. Sealant chemical exposure.',
        'risk_pre': 'Medium (3)', 'risk_post': 'Low (1)',
        'code': 'PRE-M3', 'resp': 'Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Flashings pre-formed to correct profile — Minimal on-site bending. Long flashings handled by two workers minimum. Tag lines on flashings being installed at height in wind. Sharp edges deburred before installation.'),
            ('Admin:', 'Flashing installation sequence per cladding design — Installed before panel closure. Overlap direction and weatherlap dimensions confirmed per specification. Sealant compatibility with cladding system verified — No silicone on painted surfaces unless specified.'),
            ('PPE:', 'Cut-resistant gloves. Eye protection. Steel capped footwear. Harness when working at height.'),
            ('STOP WORK if:', 'Flashing profile incorrect — Wind making handling unsafe — Sealant compatibility not confirmed — Overlap direction wrong (will trap water).')
        ]
    },
    'acm_cladding': {
        'task': 'Asbestos Cement Sheet — Identification and Management',
        'task_desc': 'Identification, assessment, and management of asbestos-containing materials (ACM) encountered during cladding works. Includes non-friable ACM handling under 10m² and interface with licensed asbestos removalists for larger quantities or friable material.',
        'hazard': 'Inhalation of asbestos fibres — Mesothelioma, asbestosis, lung cancer. Uncontrolled fibre release during disturbance. Contamination of work area. Incorrect disposal.',
        'risk_pre': 'High (9)', 'risk_post': 'Low (2)',
        'code': 'HAZ-H9', 'resp': 'Supervisor / Worker',
        'type': 'CCVS',
        'hold_points': [
            'Hazardous materials survey completed by competent person (occupational hygienist or licensed assessor) — All ACM identified, labelled, and documented in asbestos register',
            'If ACM identified: asbestos management plan in place per WHS Regulation Chapter 8. Non-friable <10m²: Class B licence holder on site. Friable or >10m²: Class A licence holder required',
            'Air monitoring arranged for removal works per SafeWork NSW Code of Practice — Clearance certificate required before general work resumes in area',
            'Workers involved in ACM work hold current asbestos awareness training (minimum) — Removal workers hold appropriate licence class',
        ],
        'eng': [
            'Wet methods for all ACM disturbance — PVA spray before cutting or drilling. No power tools on ACM unless equipped with HEPA-filtered dust extraction. Containment enclosure for removal works. HEPA vacuum for clean-up — No dry sweeping.',
        ],
        'admin': [
            'Asbestos register reviewed before any cladding removal commences. Any suspected ACM tested before disturbance — Presume asbestos until tested. Waste double-bagged in labelled asbestos bags, disposed of at licensed facility with tracking documentation. Clearance inspection and certificate before area released for general work.',
        ],
        'ppe': [
            'P2 respirator minimum for non-friable ACM work. Half-face P3 with particulate filter for friable ACM. Disposable Type 5/6 coveralls — Removed and bagged before leaving work area. Eye protection. Cut-resistant gloves.',
        ],
        'stop_work': [
            'Suspected ACM encountered without prior identification — Any ACM found friable or damaged — Removal area not enclosed — Air monitoring not in place — Workers without appropriate training or licence — ACM waste not correctly contained — Clearance certificate not obtained before area released.',
        ]
    },
}

# --- EWP STANDALONE NEW TASKS ---
EWP_NEW = {
    'ewp_selection': {
        'task': 'EWP Selection and Suitability Assessment',
        'task_desc': 'Assessment of work requirements and selection of appropriate EWP type (boom lift, scissor lift, mast lift, truck-mounted) based on reach, capacity, ground conditions, and site access constraints.',
        'hazard': 'Wrong EWP type for task — Insufficient reach, capacity, or stability. Ground conditions not suitable for EWP weight. Access route inadequate for EWP dimensions.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'WAH-H6', 'resp': 'Supervisor',
        'type': 'CCVS',
        'hold_points': [
            'EWP type selected matches task requirements: working height, horizontal reach, platform capacity (workers + tools + materials), and indoor/outdoor use',
            'Ground bearing capacity confirmed adequate for EWP fully loaded weight including outriggers — Geotechnical advice where ground conditions uncertain',
            'Site access assessed: delivery route, gates, ramps, overhead clearance, and storage/charging location confirmed before EWP arrives on site',
            'EWP manufacturer specifications reviewed — Operating envelope, wind limits, slope limits confirmed suitable for site conditions',
        ],
        'eng': [
            'Ground preparation: compacted hardstand or steel plates under outriggers/wheels on soft ground. Overhead hazard survey: power lines, structures, tree canopy — Safe clearance distances confirmed. Level/slope assessment for scissor lifts — Maximum slope per manufacturer specification.',
        ],
        'admin': [
            'EWP selection documented in work plan — Type, model, capacity, reach, and hire company recorded. Delivery/collection schedule coordinated with site logistics. Charging infrastructure for electric EWPs confirmed. Insurance and registration current for truck-mounted EWPs.',
        ],
        'ppe': [
            'As per EWP operation tasks below.',
        ],
        'stop_work': [
            'EWP delivered does not match specification — Ground conditions not suitable — Access route inadequate — Overhead hazards not cleared — EWP capacity insufficient for task requirements.',
        ]
    },
    'ewp_delivery': {
        'task': 'EWP Delivery, Positioning, and Setup',
        'task_desc': 'Delivery, unloading, transport to work position, and setup of EWP including outrigger deployment, levelling, and securing. Covers both self-propelled and trailer-mounted EWPs.',
        'hazard': 'Crush during unloading. Tip-over during transport to work position. Damage to underground services from EWP weight. Collision with structures during positioning. Unauthorised movement.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'MOB-H6', 'resp': 'Supervisor / Operator',
        'type': 'CCVS',
        'hold_points': [
            'HY Plant Safety Verification completed upon EWP arrival — Plant approved for use by HY, verification sticker displayed, registered in HammerTech',
            'Delivery vehicle access route confirmed clear: overhead clearance, ground capacity, turning circles assessed',
            'Unloading area level, firm, and clear of workers — Spotter in place during unloading',
            'Underground services confirmed clear under EWP operating position — No positioning over pits, trenches, or voids',
            'Outriggers fully deployed on firm ground or rated packing — Spirit level used to confirm EWP level within manufacturer tolerance',
        ],
        'eng': [
            'Outrigger pads or steel plates sized for ground bearing capacity. Wheel chocks on trailer-mounted units. Stabiliser interlocks confirmed functional. EWP positioned on level ground — Maximum slope per manufacturer specification for travel.',
        ],
        'admin': [
            'Traffic management plan if EWP positioned on road or footpath. Overnight security — Keys removed, controls locked, area barricaded. Daily setup check before first use each day. Ground conditions re-assessed after rain. Insurance and registration current for all EWPs.',
        ],
        'ppe': [
            'Hard hat and steel capped footwear during setup. High-vis vest or shirt. Cut-resistant gloves.',
        ],
        'stop_work': [
            'Ground soft or unstable — Outriggers not fully deployed — EWP not level — Underground services not confirmed clear — Unloading area not clear of workers — Stabiliser interlock not functioning.',
        ]
    },
    'ewp_prestart': {
        'task': 'EWP Pre-Start Inspection and Daily Checks',
        'task_desc': 'Daily pre-start inspection of EWP covering structural, mechanical, hydraulic, electrical, and safety systems. Includes function testing of all controls (ground and platform), emergency lowering, and safety devices.',
        'hazard': 'Undetected defect leading to platform failure, collapse, or entrapment. Hydraulic failure at height. Electrical fault. Brake failure. Control malfunction.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'WAH-H6', 'resp': 'Operator',
        'type': 'CCVS',
        'hold_points': [
            'Pre-start checklist completed before first use each day — All items inspected and recorded',
            'Emergency lowering system tested from platform and ground controls — Confirmed functional',
            'Platform guardrails, mid-rails, toe boards, and gate/chain complete and secure',
            'Secondary operator protective devices checked — Guards that protect operator from entrapment/crush between platform and structures confirmed functional per HY EWP Quick Guide',
            'Scissor lift platform controls protection checked — Guards around controls to prevent accidental operation or snagging confirmed in place',
            'Hydraulic system: no leaks, hoses not abraded, fluid level correct',
        ],
        'eng': [
            'All structural pins and bolts inspected — No cracks, deformation, or missing pins. Tyres/wheels — Condition and inflation correct. Battery charge adequate for planned work duration (electric units). Boom/scissor mechanism — Smooth operation, no jerking or unusual noise.',
        ],
        'admin': [
            'Pre-start checklist recorded in EWP log book. Any defect: EWP locked out and tagged — Not used until repaired by qualified technician. Operator familiarisation completed for EWP model — Controls, capacity, wind limits. Current 10-year major inspection certificate sighted. Manufacturer service intervals confirmed current — Service log checked on delivery.',
        ],
        'ppe': [
            'Harness and lanyard (boom lifts) — Inspected before each use. Hard hat. Steel capped footwear.',
        ],
        'stop_work': [
            'Any pre-start defect not rectified — Emergency lowering not functional — Guardrails incomplete — Hydraulic leak — 10-year inspection overdue — Operator unfamiliar with EWP model.',
        ]
    },
    'ewp_boom': {
        'task': 'EWP Operation — Boom Lift',
        'task_desc': 'Operation of articulated and telescopic boom lifts for work at height. Covers platform loading, operation, positioning, and safe work practices at height.',
        'hazard': 'Fall from platform. Platform tip-over. Entrapment/crush against structures. Electrocution from overhead power lines. Ejection from platform during operation.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'WAH-H6', 'resp': 'Supervisor / Operator',
        'type': 'CCVS',
        'hold_points': [
            'Operator holds current SafeWork NSW HRW licence — WP class for boom lift',
            'Harness and short lanyard attached to designated anchor point on platform — Lanyard length prevents ejection',
            'Platform load does not exceed rated capacity — Workers, tools, and materials weighed/estimated and confirmed within limit',
            'Overhead power line safe approach distances confirmed — Minimum distances per AS/NZS 4576 (Table 3.1)',
        ],
        'eng': [
            'Platform gate/chain closed during operation. Harness lanyard attached to manufacturer-designated anchor point only — Never to guardrail. Outriggers fully deployed where fitted. Ground-level emergency controls accessible and unobstructed at all times.',
        ],
        'admin': [
            'Spotter on ground during operation near structures, overhead hazards, or in traffic areas. Support personnel for boom lifts >11m must hold WP HRWL per HY Work at Height procedure. Communication between operator and ground crew — Radio or hand signals. Wind monitoring — Cease operations above 40 km/h or manufacturer limit. No modification to platform (planks, ladders, or boxes to extend reach).',
        ],
        'ppe': [
            'Full body harness (AS/NZS 1891.1) with short restraint lanyard. Hard hat — Chinstrap in windy conditions. Steel capped footwear. High-vis vest or shirt.',
        ],
        'stop_work': [
            'Wind exceeds limit — Operator not licenced — Harness not worn or not attached — Platform overloaded — Approaching power lines closer than safe distance — Ground conditions changed (rain, soft ground) — Any mechanical, hydraulic, or electrical fault — Worker attempts to climb out of platform at height.',
        ]
    },
    'ewp_scissor': {
        'task': 'EWP Operation — Scissor Lift',
        'task_desc': 'Operation of scissor lifts (slab, rough terrain, and narrow) for work at height. Covers travel, elevation, positioning, and safe work practices at height.',
        'hazard': 'Tip-over on uneven ground or slope. Fall from platform. Crush between platform and structure. Pothole or edge roll-off. Unauthorised use.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'WAH-H6', 'resp': 'Supervisor / Operator',
        'type': 'CCVS',
        'hold_points': [
            'Operator holds current EWPA Yellow Card — SL class for scissor lift. (Note: WP HRWL is for boom lifts >11m only — Not required for scissor lifts.)',
            'Ground/floor surface assessed: level within manufacturer tolerance, firm, no potholes/edges/voids within travel path',
            'Platform load confirmed within rated capacity',
            'Outriggers or pothole guards deployed as required by manufacturer for operating height',
        ],
        'eng': [
            'Guardrails, mid-rails, toe boards, and gate complete. Pothole guards deployed when elevated. No travel while elevated unless manufacturer permits — And then only on confirmed level surface. Tilt alarm and cut-out functional.',
        ],
        'admin': [
            'Operating area inspected for floor openings, edges, and overhead hazards before elevating. Barricading around base if operating in traffic area. No driving near edges, ramps, or loading docks when elevated. Battery charge checked — Adequate for planned duration.',
        ],
        'ppe': [
            'Hard hat. Steel capped footwear. High-vis vest or shirt. Harness and lanyard required only if manufacturer specifies or if working above guardrail height.',
        ],
        'stop_work': [
            'Ground/floor not level — Pothole guards not deployed — Tilt alarm sounding — Operating near unprotected edge — Wind exceeding manufacturer limit — Any mechanical fault — Operator not licenced.',
        ]
    },
    'ewp_truck': {
        'task': 'EWP Operation — Truck-Mounted / Trailer-Mounted',
        'task_desc': 'Operation of vehicle-mounted EWPs (truck-mounted boom lifts, cherry pickers, trailer-mounted units) on public roads, footpaths, and construction sites. Includes traffic management requirements.',
        'hazard': 'Vehicle instability — Outrigger failure or soft ground. Traffic collision. Overhead power line contact. Pedestrian interaction on footpath. Vehicle roll-away.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'WAH-H6', 'resp': 'Supervisor / Operator',
        'type': 'CCVS',
        'hold_points': [
            'Vehicle registration and insurance current. Operator holds HRW licence (WP class) plus appropriate vehicle licence class',
            'Traffic management plan (TMP) implemented: council permit obtained, signage and cones deployed per AS 1742.3, traffic controller engaged if required',
            'Outriggers on firm ground — Full deployment on all four corners. Steel plates or packing under outriggers on soft or uneven surfaces',
            'Overhead power line clearance confirmed — No operation within safe approach distance per AS/NZS 4576 without network operator approval',
        ],
        'eng': [
            'Vehicle handbrake engaged and wheel chocks in place. Outriggers fully extended and locked — Level confirmed. PTO and hydraulic system pre-checked. Ground bearing capacity assessed — Steel plates deployed.',
        ],
        'admin': [
            'Council road/footpath occupation permit obtained. Traffic management plan implemented — Signs, cones, traffic controllers per permit conditions. Pedestrian detour in place if footpath occupied. Vehicle inspection by operator before road travel. After-hours work conditions checked if applicable.',
        ],
        'ppe': [
            'Full body harness with restraint lanyard (boom-type truck mounts). Hard hat. High-vis vest or shirt — Class D/N as required for road work. Steel capped footwear.',
        ],
        'stop_work': [
            'Outriggers not fully deployed — Vehicle not level — Traffic management not in place — Approaching power lines — Council permit not current — Wind exceeds limit — Pedestrians entering work zone — Ground soft or unstable.',
        ]
    },
    'ewp_rescue': {
        'task': 'EWP Rescue Procedures',
        'task_desc': 'Emergency rescue of incapacitated operator from elevated EWP platform. Covers ground-level override controls, emergency lowering procedures, and medical emergency response at height.',
        'hazard': 'Delayed rescue — Suspension trauma in harness (positional asphyxia). Inability to reach incapacitated operator. Ground-level controls obstructed or not functional. Medical emergency at height.',
        'risk_pre': 'High (9)', 'risk_post': 'Low (2)',
        'code': 'WAH-H9', 'resp': 'Supervisor / Worker',
        'type': 'CCVS',
        'hold_points': [
            'Rescue plan addresses three distinct scenarios per HY Work at Height procedure: (a) rescue of incapacitated operator from platform via ground-level override, (b) rescue of operator suspended in harness after ejection/fall from platform, (c) medical emergency at height requiring casualty lowering',
            'Ground-level emergency controls location confirmed by all crew — Tested before each shift',
            'Rescue procedure rehearsed by all workers on site who may need to perform rescue — Minimum quarterly practice',
            'Suspension trauma awareness: all harness wearers briefed on symptoms and relief procedures — Trauma straps fitted to harnesses',
            'Emergency services contact confirmed — Nearest hospital with trauma capability identified',
        ],
        'eng': [
            'Ground-level emergency lowering controls accessible and unobstructed at all times — Keys available on site. Emergency lowering speed adequate to recover operator within 6 minutes of suspension onset.',
        ],
        'admin': [
            'Rescue procedure documented and displayed at EWP ground-level controls. Minimum two persons on site when EWP in use — One at ground level at all times. First aid trained person on site. Emergency lowering procedure practised at start of each new project or EWP model.',
        ],
        'ppe': [
            'Trauma straps fitted to harnesses — Operator trained in self-deployment.',
        ],
        'stop_work': [
            'Ground-level controls not functional — No second person available on site — Rescue procedure not rehearsed — Trauma straps not fitted to harnesses — Emergency lowering not tested.',
        ]
    },
    'ewp_traffic': {
        'task': 'EWP and Pedestrian/Vehicle Interface',
        'task_desc': 'Management of interaction between operating EWP and pedestrians, vehicles, and other site traffic. Includes exclusion zones, traffic management, and spotter requirements.',
        'hazard': 'Collision between EWP and pedestrian. Vehicle striking EWP or outriggers. Objects falling from platform onto persons below. Outriggers encroaching on traffic lane.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'TRF-M4', 'resp': 'Supervisor / Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Physical barricading around EWP operating area — Mesh fence or water barriers for roadside. Outrigger visibility: reflective markers on extended outriggers. Drop zone containment — Toe boards on platform, tool lanyards, no loose items on platform.'),
            ('Admin:', 'Exclusion zone maintained during operation — Minimum 3m from base plus swing radius. Spotter assigned in pedestrian areas. Traffic management plan if operating on or adjacent to roadway. Communication between operator and ground crew at all times. Pedestrian detour signage if footpath blocked.'),
            ('PPE:', 'High-vis vest or shirt — Class D/N if roadside. Hard hat for all ground personnel in exclusion zone.'),
            ('STOP WORK if:', 'Pedestrians breaching exclusion zone — Traffic management not in place — Spotter not available in pedestrian area — Barricading displaced — Objects falling from platform — Vehicle approaching outriggers.')
        ]
    },
    'ewp_overhead': {
        'task': 'EWP Overhead Hazards — Electrical, Structures',
        'task_desc': 'Management of overhead hazards when operating EWP including power lines, building structures, tree canopy, cranes, and other overhead equipment.',
        'hazard': 'Electrocution from contact with overhead power lines (highest risk). Crush between platform and building structure, soffit, or beam. Entanglement with cables or conduit. Platform contact with tree branches.',
        'risk_pre': 'High (9)', 'risk_post': 'Low (2)',
        'code': 'ELE-H9', 'resp': 'Supervisor / Operator',
        'type': 'CCVS',
        'hold_points': [
            'Overhead power line survey completed: all lines within EWP operating radius identified, voltages confirmed with network operator, safe approach distances per AS/NZS 4576 Table 3.1 confirmed',
            'If safe approach distance cannot be maintained: line de-energisation or insulation arranged with network operator — Written confirmation obtained before work commences',
            'Height limiter set on EWP to prevent approach to overhead structure where crush risk exists',
            'Spotter on ground with clear view of boom tip/platform and overhead hazards — Continuous communication with operator',
        ],
        'eng': [
            'Tiger tails or visual markers on power lines where approved by network operator. Height limiter or zone restriction set on EWP where overhead structures present. Insulated platform (if available) for work near energised lines.',
        ],
        'admin': [
            'Power line safety plan documented — Safe approach distances displayed at ground-level controls. All crew briefed on power line locations and safe distances before work commences. Dial Before You Dig and network operator consulted. Emergency procedure for electrical contact briefed: do not touch EWP, operator to jump clear if safe to do so, call 000.',
        ],
        'ppe': [
            'Harness and lanyard. Hard hat. Insulating gloves if working near energised equipment (by qualified electrician only). Steel capped footwear.',
        ],
        'stop_work': [
            'Safe approach distance to power line compromised — Spotter not in position — Power line not identified on safety plan — Height limiter not set — Any contact with overhead structure — Platform operator cannot see boom tip.',
        ]
    },
    'ewp_ground': {
        'task': 'EWP Ground Conditions and Stability',
        'task_desc': 'Assessment and management of ground conditions for EWP stability including soft ground, slopes, underground voids, recently excavated areas, and changing conditions from weather.',
        'hazard': 'EWP tip-over from ground failure. Outrigger sinking. Travel over soft or uneven ground. Instability from underground void or recently backfilled area.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'WAH-H6', 'resp': 'Supervisor / Operator',
        'type': 'CCVS',
        'hold_points': [
            'Ground assessment completed: surface type, bearing capacity, slope, underground services/voids identified and documented',
            'Outrigger pad size and material confirmed adequate for ground bearing capacity — Engineering advice if soft or uncertain ground',
            'No operation over or adjacent to recent excavation, backfill, or underground void without engineering confirmation of bearing capacity',
            'After rain: ground conditions re-assessed before operation — Soft areas identified and avoided or reinforced',
        ],
        'eng': [
            'Steel plates or engineered packing under outriggers on all surfaces except confirmed concrete or bitumen. Ground reinforcement (geotextile, crushed rock, or engineered platform) where soft ground and extended EWP use planned. Level monitoring — Spirit level on platform checked periodically during operation.',
        ],
        'admin': [
            'Ground condition assessment documented in EWP daily log. Geotechnical advice obtained where ground conditions uncertain. Travel routes surveyed for potholes, edges, and soft spots. Drain covers and pit lids assessed for EWP wheel loads.',
        ],
        'ppe': [
            'Steel capped footwear for all ground crew. Hard hat. High-vis vest or shirt.',
        ],
        'stop_work': [
            'Outrigger sinking or ground deformation observed — EWP not level — Soft ground after rain not assessed — Operating over unconfirmed backfill or void — Slope exceeds manufacturer tolerance — Ground cracking.',
        ]
    },
}

# --- SWING STAGE NEW TASKS ---
SWING_NEW = {
    'ss_design': {
        'task': 'Swing Stage Design and Engineering Certification',
        'task_desc': 'Engineering design, certification, and documentation of swing stage (suspended scaffold) systems including load calculations, structural adequacy of building for suspension loads, and compliance with AS/NZS 1576.4.',
        'hazard': 'Platform failure due to inadequate design. Building structure unable to support suspension loads. Incorrect load calculations. Use of non-certified or modified equipment.',
        'risk_pre': 'High (9)', 'risk_post': 'Low (2)',
        'code': 'WAH-H9', 'resp': 'Supervisor / Engineer',
        'type': 'CCVS',
        'hold_points': [
            'Swing stage system designed and certified by registered professional engineer — Design documentation on site and current',
            'Building structural assessment completed: roof/parapet/anchor points confirmed adequate for suspension loads (dead load + live load + dynamic factors) by structural engineer',
            'Equipment certification current: all components (platform, hoist motors, wire ropes, safety devices) tested and tagged by competent person',
            'Design compliant with AS/NZS 1576.4 Scaffolding — Suspended scaffolding and AS 2550.10 Cranes — Suspended personnel platforms',
        ],
        'eng': [
            'Rated suspension points with SWL clearly marked. Wire ropes certified for breaking strain — Minimum 10:1 safety factor. Hoist motors rated for platform load. Secondary safety (fall arrest) wire rope independent of working rope.',
        ],
        'admin': [
            'Engineering drawings and load tables available on site. Design review if any modification to platform size, worker numbers, or tools/materials on platform. Design verified against actual building geometry — Not assumed from plans. Design engineer contact details on site for consultation.',
        ],
        'ppe': [
            'As per operation tasks below.',
        ],
        'stop_work': [
            'Engineering design not available or not current — Building structural capacity not confirmed — Equipment certification expired — Any modification to platform not approved by design engineer — Equipment damaged or not matching design specification.',
        ]
    },
    'ss_anchor': {
        'task': 'Roof Anchor and Suspension Point Setup',
        'task_desc': 'Installation, inspection, and certification of roof-mounted anchor points, parapet clamps, outrigger beams, and counterweight systems for swing stage suspension. Includes structural assessment of anchor substrates.',
        'hazard': 'Anchor failure — Catastrophic platform drop. Roof edge fall during anchor installation. Incorrect counterweight calculation. Parapet or roof structure failure. Unauthorised access to roof plant area.',
        'risk_pre': 'High (9)', 'risk_post': 'Low (2)',
        'code': 'WAH-H9', 'resp': 'Lead Technician / Supervisor',
        'type': 'CCVS',
        'hold_points': [
            'Anchor point type and location per engineering design — No variation without engineer approval. Anchor substrate (concrete, steel, masonry) confirmed adequate for suspension loads',
            'Counterweight system: weight calculated per design (minimum 3:1 safety factor against overturning). Counterweights secured and cannot shift — No loose or improvised weights',
            'Outrigger beams: correct span, overhang, and bearing confirmed per design. Beams secured against lateral movement. Bearing pads on parapet/roof edge',
            'All anchor points load tested or proof-loaded before first use — Test certificate on site',
        ],
        'eng': [
            'Engineered anchor points — Cast-in, chemical anchor, or bolted to certified substrate. Outrigger beams spanning across building structure (not bearing on parapet only). Counterweights: purpose-built certified weights — Not improvised from construction materials.',
        ],
        'admin': [
            'Roof access controlled — Permit system. Fall protection in place for all workers on roof during anchor installation (harness to independent anchor, guardrails, or travel restraint). Anchor inspection by competent person before each use. Anchor point register maintained.',
        ],
        'ppe': [
            'Full body harness with fall arrest — Anchored to independent point during roof work. Hard hat with chin strap. Steel capped footwear with non-slip sole. High-vis vest or shirt.',
        ],
        'stop_work': [
            'Anchor substrate cracked, spalled, or suspect — Counterweight incorrect or unsecured — Outrigger bearing on parapet only without structural confirmation — Anchor not tested — Any modification not approved by engineer — Roof access uncontrolled.',
        ]
    },
    'ss_install': {
        'task': 'Swing Stage Installation and Rigging',
        'task_desc': 'Assembly of swing stage platform, connection of wire ropes to hoist motors and suspension points, installation of safety devices (overspeed governor, tilt switch, rope lock), and rigging of secondary safety lines.',
        'hazard': 'Fall during rigging at roof edge. Wire rope failure. Incorrect assembly — Platform collapse. Safety device malfunction. Platform swing or spin during lowering.',
        'risk_pre': 'High (9)', 'risk_post': 'Low (2)',
        'code': 'WAH-H9', 'resp': 'Lead Technician / Supervisor',
        'type': 'CCVS',
        'hold_points': [
            'Rigging performed by workers holding Advanced Scaffolding licence (SA) and competent in suspended scaffold systems',
            'Wire ropes: correct diameter, construction, and length per design — Inspected for damage, kinks, broken wires before reeving. Wire rope certificates current',
            'Safety devices installed and tested: overspeed governor, tilt switch, upper/lower limit switches, rope lock on secondary safety line — All confirmed functional before platform loaded',
            'Platform assembled per manufacturer instructions — All pins, bolts, guardrails, toe boards, and deck panels confirmed secure',
        ],
        'eng': [
            'Working rope and safety rope independently suspended — No common failure point. Rope guides installed to prevent rope snagging. Platform levelling system functional. Hoist motors tested for smooth operation — No jerking or slipping.',
        ],
        'admin': [
            'Rigging checklist completed and signed by competent person. Platform not used until competent person sign-off. Rigging inspection before each use and after any incident or weather event. Wire rope replacement: per manufacturer specification or when any of the following observed — 6 or more broken wires in one lay length, strand breakage, kinking, birdcaging, corrosion pitting, or diameter reduction >10%.',
        ],
        'ppe': [
            'Full body harness with fall arrest to independent anchor during rigging. Hard hat with chin strap. Steel capped footwear. Gloves — Leather for wire rope handling.',
        ],
        'stop_work': [
            'Wire rope damaged (broken wires, kinks, corrosion) — Safety device not functional — Platform assembly incomplete — Rigger not holding SA licence — Safety rope not independent of working rope — Competent person sign-off not obtained.',
        ]
    },
    'ss_prestart': {
        'task': 'Swing Stage Pre-Start and Daily Inspection',
        'task_desc': 'Daily inspection of swing stage system before each use covering platform, wire ropes, hoist motors, safety devices, anchor points, and counterweights.',
        'hazard': 'Undetected defect leading to platform failure. Wire rope deterioration between inspections. Safety device failure. Weather damage overnight.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'WAH-H6', 'resp': 'Lead Technician / Operator',
        'type': 'CCVS',
        'hold_points': [
            'Daily pre-start checklist completed and recorded before any worker boards platform',
            'Wire ropes inspected full length: no broken wires, kinks, corrosion, or abrasion. Rope terminations secure',
            'Safety devices tested: overspeed governor, tilt switch, rope lock — Confirmed functional',
            'Anchor points and counterweights inspected: no movement, damage, or displacement since last use',
        ],
        'eng': [
            'Hoist motors run at no-load to confirm smooth operation. Brakes tested — Platform holds position when motor stopped. Platform level checked. Guardrails, toe boards, and deck panels secure.',
        ],
        'admin': [
            'Pre-start log maintained — Competent person signature required. Any defect: platform locked out — Not used until repaired. After storm, heavy rain, or strong wind: additional inspection before use. Weekly detailed inspection by competent person in addition to daily pre-start.',
        ],
        'ppe': [
            'Full body harness with fall arrest to independent safety line before boarding platform.',
        ],
        'stop_work': [
            'Any pre-start defect — Safety device not functional — Wire rope damage — Anchor point movement — Platform not level — Hoist motor fault — Brake not holding — Pre-start not signed off.',
        ]
    },
    'ss_operation': {
        'task': 'Swing Stage Operation and Repositioning',
        'task_desc': 'Operation of swing stage for work at height including ascending, descending, working position, lateral repositioning, and work activities from the platform.',
        'hazard': 'Platform failure during operation. Fall from platform. Entrapment between platform and building. Platform swing or pendulum effect. Overloading. Wind.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'WAH-H6', 'resp': 'Operator / Worker',
        'type': 'CCVS',
        'hold_points': [
            'All workers on platform attached to independent safety line via full body harness and rope grab — Never attached to platform structure or working rope',
            'Platform load confirmed within rated capacity before each descent — Workers, tools, and materials',
            'Wind monitoring active — Cease operations above 40 km/h or design limit, whichever is lower',
            'Communication system in place between platform and ground/roof crew — Radio or visual signals',
        ],
        'eng': [
            'Safety line rope grab adjusted to each worker. Platform level maintained during descent — Simultaneous hoist operation. Building face rollers or guide rails to prevent platform spin. Tool and material restraint on platform — Nothing unsecured.',
        ],
        'admin': [
            'Maximum two workers on standard platform unless design permits more. No leaning over guardrails — Work within arm reach. No jumping or sudden movements on platform. Repositioning: platform raised to roof level, moved along building face, then lowered to work position. No lateral movement while lowered.',
        ],
        'ppe': [
            'Full body harness (AS/NZS 1891.1) with rope grab on independent safety line. Hard hat with chin strap. Steel capped footwear with non-slip sole. Tool lanyard for all tools.',
        ],
        'stop_work': [
            'Worker not attached to safety line — Platform overloaded — Wind exceeds limit — Platform not level (differential >150mm) — Platform spinning or swinging uncontrolled — Communication with ground/roof lost — Hoist motor fault — Any safety device activation.',
        ]
    },
    'ss_rescue': {
        'task': 'Swing Stage Rescue Procedures',
        'task_desc': 'Emergency rescue of incapacitated worker from suspended swing stage platform. Covers rescue from platform, rescue from safety line (suspended in harness), and medical emergency at height.',
        'hazard': 'Suspension trauma (positional asphyxia) — Onset within 5 minutes of suspension in harness. Delayed rescue. Platform inaccessible from ground. Multiple casualty scenario.',
        'risk_pre': 'High (9)', 'risk_post': 'Low (2)',
        'code': 'WAH-H9', 'resp': 'Supervisor / Lead Technician',
        'type': 'CCVS',
        'hold_points': [
            'Rescue plan documented and specific to this swing stage installation — Not generic. Three distinct rescue scenarios addressed per HY Work at Height procedure: (a) rescue of incapacitated worker from platform, (b) rescue of worker suspended on independent safety line (harness suspension), (c) medical emergency at height requiring casualty lowering',
            'Rescue equipment on site and accessible: second means of access to platform height (adjacent building access, EWP on standby, or rope rescue capability)',
            'All crew trained in rescue procedure and rehearsed at project commencement — Rescue drill completed and recorded',
            'Suspension trauma awareness: trauma straps fitted to all harnesses, all workers briefed on self-deployment and symptoms',
        ],
        'eng': [
            'Emergency lowering by platform hoist — Operable from ground level. If hoist fails: alternative rescue method (rope rescue, EWP, or adjacent access) available within 6 minutes. Trauma straps on all harnesses.',
        ],
        'admin': [
            'Rescue procedure displayed at ground level and on platform. Minimum two persons on site when swing stage in use — One at ground level. Emergency services pre-notified of swing stage work (location, height, access). First aid trained person on site. HY Strip Scaffold Work Permit obtained where required per HY Temporary Works procedure.',
        ],
        'ppe': [
            'Trauma straps fitted and deployed. Rescue harness for rescuer if rope rescue method used.',
        ],
        'stop_work': [
            'Rescue plan not documented — Rescue drill not completed — No second means of access available — Trauma straps not fitted — Solo worker on swing stage — Emergency lowering not functional — First aid not available on site.',
        ]
    },
    'ss_wind': {
        'task': 'Wind and Weather Monitoring',
        'task_desc': 'Continuous monitoring of wind speed, gusts, rain, and storm activity during swing stage operations. Includes criteria for operational limits and suspension of work.',
        'hazard': 'Platform swing and instability in wind. Lightning strike on elevated platform and wire ropes. Rain making platform slippery. Sudden wind change/gust. Reduced visibility in fog or heavy rain.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'ENV-M4', 'resp': 'Supervisor / Operator',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Anemometer (wind speed meter) on platform or at working height — Continuous reading visible to operator. Platform tie-off points for securing to building face in high wind. Wire ropes and platform secured when not in use.'),
            ('Admin:', 'Wind limits documented and briefed to all crew: sustained >40 km/h or gusts >50 km/h — Cease operations and secure platform. BOM weather forecast checked before each shift. Lightning: cease operations immediately, lower platform to ground, all workers off roof and platform. Rain: assess slip risk, reduce operations if platform slippery. Daily wind monitoring log recorded.'),
            ('PPE:', 'Wet weather gear if operating in light rain. Non-slip footwear.'),
            ('STOP WORK if:', 'Wind sustained >40 km/h or gusts >50 km/h — Lightning detected within 10km — Heavy rain reducing visibility — Storm warning issued — Wind direction change causing platform instability — Operator feels unsafe due to weather conditions.')
        ]
    },
    'ss_exclusion': {
        'task': 'Exclusion Zone and Drop Zone Management',
        'task_desc': 'Establishment and maintenance of exclusion zones below and around swing stage operations to protect ground-level workers, residents, and public from falling objects and equipment.',
        'hazard': 'Falling tools, materials, or debris from platform. Wire rope or equipment failure — Falling components. Platform swing path at ground level. Unauthorised access to exclusion zone.',
        'risk_pre': 'Medium (3)', 'risk_post': 'Low (1)',
        'code': 'SYS-M3', 'resp': 'Supervisor / Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Physical barricading of exclusion zone: mesh fence, water barriers, or hoarding — Not tape alone. Catch platform or fan at occupied building entries if within drop zone. Scaffold netting on platform perimeter. Tool lanyards for all hand tools on platform.'),
            ('Admin:', 'Exclusion zone extends minimum 3m from platform edge plus the lesser of half the platform height or 6m (per SafeWork NSW guidance). Signage: "Danger — Overhead Work — No Entry". Resident/public notification before commencement. Spotter at ground level if pedestrians near exclusion zone. No material throwing or dropping from platform.'),
            ('PPE:', 'Hard hat for all persons within or adjacent to exclusion zone.'),
            ('STOP WORK if:', 'Exclusion zone breached — Barricading displaced — Tool or material dropped from platform — Pedestrians or residents in drop zone — Signage removed.')
        ]
    },
    'ss_electrical': {
        'task': 'Electrical Hazard Clearance',
        'task_desc': 'Identification and management of electrical hazards during swing stage operations including building-mounted wiring, external lighting, power lines, and electrical equipment on building façade.',
        'hazard': 'Electrocution from contact with energised conductors. Wire rope contact with power lines. Platform contact with external lighting or conduit. Wet conditions increasing electrical risk.',
        'risk_pre': 'High (9)', 'risk_post': 'Low (2)',
        'code': 'ELE-H9', 'resp': 'Supervisor / Operator',
        'type': 'CCVS',
        'hold_points': [
            'Electrical survey completed: all building-mounted and adjacent electrical hazards identified — External lighting, power points, conduit, switchboards, and overhead lines mapped',
            'Energised equipment within platform travel path: de-energised and locked out by licensed electrician, or physical protection installed to prevent contact',
            'Overhead power lines: safe approach distances confirmed per AS/NZS 4576 — Platform travel limits set to prevent approach',
            'Wet weather: all exposed electrical connections protected or de-energised',
        ],
        'eng': [
            'Platform travel limits set to maintain clearance from electrical hazards. Physical guards over building-mounted wiring in platform travel path. Wire ropes routed clear of any electrical equipment.',
        ],
        'admin': [
            'Electrical hazard map displayed on platform and at ground level. Electrician engaged to isolate and de-energise equipment in platform path where possible. Emergency procedure for electrical contact briefed: do not touch wire ropes or platform, lower platform from ground controls only if safe to do so, call 000.',
        ],
        'ppe': [
            'Insulating gloves if any electrical work (by licensed electrician only). Standard PPE for all other workers.',
        ],
        'stop_work': [
            'Electrical hazard not identified on survey — Energised equipment in platform path not isolated — Wire rope approaching power line — Wet conditions and exposed wiring — Electrical contact of any kind.',
        ]
    },
}

# --- ABRASIVE BLASTING NEW TASKS ---
BLASTING_NEW = {
    'blast_setup': {
        'task': 'Blasting Equipment Setup — Compressor, Pot, Lines',
        'task_desc': 'Setup, commissioning, and operation of abrasive blasting equipment including air compressor, blast pot (pressure vessel), blast hoses, nozzles, moisture separators, and dead-man controls.',
        'hazard': 'High-pressure air release — Hose whip. Pressure vessel failure. Noise from compressor and blasting. Hose connection failure. Dead-man control malfunction — Uncontrolled blast.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'PRE-H6', 'resp': 'Supervisor / Blaster',
        'type': 'CCVS',
        'hold_points': [
            'Blast pot (pressure vessel) has current registration and inspection certificate per WHS Regulation Chapter 5 — Plant',
            'All hose connections fitted with safety clips/whip checks — Dead-man control fitted to nozzle and tested functional',
            'Compressor capacity matched to nozzle size — Correct operating pressure set and pressure relief valve functional',
            'Operator holds demonstrated competence in abrasive blasting equipment operation — Training records sighted',
        ],
        'eng': [
            'Whip checks on all hose connections. Safety pins/clips on all couplings. Dead-man handle on nozzle — Blast stops within 1 second of release. Moisture separator and air dryer in line. Pressure relief valve set to maximum operating pressure. Earthing/bonding of all metallic components to prevent static discharge.',
        ],
        'admin': [
            'Equipment pre-start inspection completed and recorded. Hoses inspected full length — No damage, kinks, or excessive wear. Nozzle bore checked — Replaced when worn beyond 20% of original diameter. Compressor maintenance log current. Exclusion zone around compressor — Noise and exhaust fumes.',
        ],
        'ppe': [
            'Hearing protection (>85 dB, Class 5) near compressor. Steel capped footwear. Eye protection during setup.',
        ],
        'stop_work': [
            'Pressure vessel registration expired — Dead-man control not functional — Hose damage or coupling failure — Pressure relief valve not working — Whip checks missing — Operator not competent.',
        ]
    },
    'blast_open': {
        'task': 'Abrasive Blasting Operations — Open Air',
        'task_desc': 'Abrasive blasting of surfaces in open-air conditions using garnet, glass bead, steel shot, crushed slag, or soda media. Includes surface preparation to specified profile for coating application.',
        'hazard': 'Respirable dust — Silicosis (if silica media used), general respiratory hazard from all media. Noise >115 dB(A). Ricochet — High-velocity particles. Skin abrasion from blast media. Dust affecting adjacent properties and persons.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'SIL-H6', 'resp': 'Supervisor / Blaster',
        'type': 'CCVS',
        'hold_points': [
            'Asbestos register reviewed and existing coating tested for asbestos content before blasting commences per HY Asbestos standard. If asbestos detected: cease — Engage licensed asbestos removalist. Abrasive blasting is a prohibited method for asbestos-containing material removal',
            'Blast media confirmed: NO free silica content (crystalline silica banned for abrasive blasting per WHS Regulation). Material safety data sheet confirms silica-free',
            'Air monitoring plan in place: personal and boundary monitoring for respirable dust. Monitoring results reviewed by occupational hygienist',
            'Containment assessed: full containment if within 50m of occupied premises, public areas, or sensitive environments. Partial containment where open-air blasting is practicable',
            'All workers within 15m of blasting operations wearing appropriate respiratory protection',
        ],
        'eng': [
            'Blast containment: tarps, mesh screens, or full enclosure depending on location and media. Dust suppression: wet blasting (vapour blasting) where practicable to reduce airborne dust. Media recovery system where possible — Vacuum or sweep recovery. Blast area physically barricaded — Minimum 10m exclusion zone.',
        ],
        'admin': [
            'Blast plan documented: surface area, media type and consumption, profile required, containment method, waste disposal. Neighbours notified 48 hours before blasting commences. Blast times restricted per council/permit conditions — Typically 7am–5pm. Dust monitoring results actioned same day — Work adjusted if results exceed exposure standards. Post-blast surface profile checked with comparator gauge — Profile within coating manufacturer specification range. Coating application commenced within maximum flash-rust window per coating specification (typically 4–8 hours depending on conditions). Competent person directly supervises all abrasive blasting operations per SafeWork NSW requirements.',
        ],
        'ppe': [
            'Blaster: AS/NZS 1337-approved blast helmet with supplied air (Class 2B minimum), leather blast suit, leather gloves, steel capped boots. Assistants within 15m: half-face P3 respirator, eye protection, hearing protection (>85 dB, Class 5), long sleeves.',
        ],
        'stop_work': [
            'Silica-containing media identified — Asbestos detected or suspected in substrate coating (cease blasting immediately — Treat as asbestos removal work per WHS Regulation) — Air monitoring exceeds exposure standard — Containment failure — Dust escaping to adjacent properties — Dead-man control malfunction — Supplied air system fault — Blast helmet visor damaged — Wind exceeds containment capability.',
        ]
    },
    'blast_enclosed': {
        'task': 'Abrasive Blasting — Enclosed/Contained Environment',
        'task_desc': 'Abrasive blasting inside containment enclosures, blast rooms, tanks, or confined structures. Includes ventilation, visibility, and confined space management.',
        'hazard': 'Extreme dust concentration in enclosed space. Reduced visibility — Zero visibility common. Noise amplification in enclosure. Oxygen depletion. Confined space hazards. Heat stress inside blast suit.',
        'risk_pre': 'High (9)', 'risk_post': 'Low (2)',
        'code': 'HAZ-H9', 'resp': 'Supervisor / Blaster',
        'type': 'CCVS',
        'hold_points': [
            'Asbestos register reviewed and existing coating tested for asbestos content before enclosed blasting commences. If asbestos detected: cease — Engage licensed asbestos removalist. Abrasive blasting is a prohibited method for asbestos-containing material removal',
            'Enclosed blasting ventilation system operational: negative pressure maintained within enclosure, exhaust air filtered before discharge. Minimum 20 air changes per hour',
            'Confined space assessment completed if applicable per WHS Regulation Chapter 4 Part 4.3 — Entry permit system in place',
            'Supplied air breathing apparatus confirmed: air quality tested (Grade D breathing air), flow rate adequate, emergency air reserve available',
            'Communication system between blaster inside enclosure and standby person outside — Tested before entry. Standby person remains at entry point at all times',
        ],
        'eng': [
            'Extraction ventilation with HEPA filtration — Negative pressure prevents dust escape. Lighting rated for hazardous atmosphere if combustible media. Emergency air supply — Minimum 10 minutes reserve. Blast containment sealed — No gaps allowing dust escape.',
        ],
        'admin': [
            'Maximum continuous blast time per session — Heat stress management. Work/rest rotation schedule. Visibility check — Cease blasting if visibility <1m and allow dust to settle. Dust monitoring inside and outside containment. Emergency extraction procedure rehearsed. Competent person directly supervises all abrasive blasting operations per SafeWork NSW requirements.',
        ],
        'ppe': [
            'Blaster: Type CE supplied-air blast helmet with positive pressure, full leather blast suit, leather gauntlet gloves, steel capped boots, hearing protection (>85 dB). Standby person: half-face P3 respirator, hearing protection (>85 dB), eye protection.',
        ],
        'stop_work': [
            'Ventilation system fails — Positive pressure in helmet lost — Air supply quality alarm — Asbestos detected or suspected in substrate coating (cease blasting immediately — Treat as asbestos removal work per WHS Regulation) — Visibility zero for >5 minutes — Confined space entry permit not current — Standby person leaves position — Heat stress symptoms — Enclosure seal breached — Dust escaping containment.',
        ]
    },
    'blast_media': new_task(
        name='Blast Media Selection and Handling',
        scope='Selection, storage, handling, and loading of abrasive blast media including garnet, glass bead, steel shot, soda, and crushed slag. Includes media quality control and waste management.',
        hazard_keys=[
            'manual_handling_heavy_bags',
            'dust_loading_handling',
            'contaminated_media',
            'slip_spilled_media',
            'eye_injury_particles',
        ],
        risk_pre='Medium (4)',
        risk_code='HAZ-M4',
        responsibility='Worker / Sub-Contract Worker',
        engineering=[
            'bulk_delivery_hopper',
            'mechanical_lifting_25kg',
            'dust_extraction_loading',
            'media_storage_dry',
        ],
        admin=[
            'media_sds_silica',
            'media_spec_match',
            'media_contamination_test',
            'media_waste_classified',
        ],
        ppe_keys=[
            'p2_dust_mask',
            'eye_protection',
            'cut_resistant_gloves',
            'steel_cap',
        ],
        stop_work_keys=[
            'media_free_silica',
            'media_contaminated',
            'media_wet_clumped',
            'sds_not_available',
            'manual_handling_no_aids',
        ],
    ),
    'blast_containment': {
        'task': 'Containment and Environmental Controls',
        'task_desc': 'Erection, maintenance, and removal of blast containment systems including full enclosures, tarps, screens, and environmental protection measures for dust, noise, and waste.',
        'hazard': 'Containment failure — Dust release to environment. Working at height during containment erection. Wind damage to containment. Stormwater contamination from blast waste. Community complaint.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'ENV-M4', 'resp': 'Supervisor / Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Containment structure designed for wind loading — Secured to scaffold or independent frame. Containment sealed at all joints — Overlap and tape/clamp. Stormwater protection: bunding around blast area, drain covers within 10m. Waste collection system within containment — Prevent media and coating waste reaching ground/stormwater.'),
            ('Admin:', 'Environmental management plan reviewed — Containment method per EPA and council requirements. Boundary dust monitoring during blasting — Results compared against PM10 criteria. Noise monitoring at site boundary. Containment inspected daily — Repairs before blasting resumes. Waste manifest maintained — Media, coating waste, and contaminated water tracked from generation to disposal.'),
            ('PPE:', 'As per blasting tasks.'),
            ('STOP WORK if:', 'Containment breach — Dust visible outside containment — Boundary monitoring exceeds criteria — Wind damaging containment — Stormwater contamination — Community complaint not resolved.')
        ]
    },
    'dust_monitoring': {
        'task': 'Dust Suppression and Air Monitoring',
        'task_desc': 'Personal and boundary air monitoring during abrasive blasting operations. Includes respirable dust, total inhalable dust, and specific contaminant monitoring (lead, asbestos, silica). Dust suppression methods.',
        'hazard': 'Respirable dust exposure exceeding workplace exposure standard (WES). Lead or asbestos fibre release from existing coatings. Crystalline silica exposure. Environmental dust impact beyond site boundary.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'SIL-H6', 'resp': 'Supervisor / Occupational Hygienist',
        'type': 'CCVS',
        'hold_points': [
            'Air monitoring plan developed by occupational hygienist — Personal and boundary monitoring locations and frequency specified',
            'Baseline coating analysis completed before blasting: tested for lead, asbestos, chromium, and other hazardous substances. Results reviewed and control measures adjusted accordingly',
            'If lead detected: lead risk assessment per WHS Regulation Chapter 7 Part 7.2. Blood lead monitoring program in place for workers',
            'Dust monitoring results reviewed same-day — Exceedance triggers immediate cessation and control review',
        ],
        'eng': [
            'Wet blasting (vapour blasting) or water injection at nozzle where practicable. HEPA-filtered exhaust on enclosed containment. Dust suppression sprays at containment openings. Real-time dust monitoring where available.',
        ],
        'admin': [
            'Exposure standards referenced: respirable dust 1mg/m³ (8hr TWA), lead 0.05mg/m³, crystalline silica 0.05mg/m³. Personal monitoring results recorded and communicated to workers. Health surveillance program per WHS Regulation if trigger levels reached. Monitoring records retained for 30 years (lead and asbestos).',
        ],
        'ppe': [
            'Supplied-air respiratory protection for blaster (minimum). Half-face P3 for assistants and workers in vicinity. Upgrade to supplied air if monitoring indicates elevated exposure.',
        ],
        'stop_work': [
            'Monitoring exceeds WES — Lead or asbestos detected in coating without prior assessment — Monitoring equipment fault — Supplied air quality test failed — Dust escaping containment boundary.',
        ]
    },
    'lead_blasting': {
        'task': 'Lead Paint and Hazardous Coating Removal by Blasting',
        'task_desc': 'Removal of lead-containing paint and other hazardous coatings by abrasive blasting. Includes full containment, air monitoring, worker health surveillance, and hazardous waste disposal requirements.',
        'hazard': 'Lead dust and fume inhalation — Lead poisoning. Lead contamination of site and surrounds. Asbestos co-contamination in old coatings. Hazardous waste generation. Worker take-home contamination.',
        'risk_pre': 'High (9)', 'risk_post': 'Low (2)',
        'code': 'HAZ-H9', 'resp': 'Supervisor / Blaster / Occupational Hygienist',
        'type': 'CCVS',
        'hold_points': [
            'Lead risk assessment completed per WHS Regulation Chapter 7 Part 7.2 — Lead content of coating quantified by laboratory analysis',
            'Full containment required: Class 1 enclosure with negative pressure ventilation and HEPA filtration per AS 4361.2',
            'Worker health surveillance: blood lead levels tested before commencement and at intervals per WHS Regulation. Workers with blood lead >20 µg/dL reviewed by medical practitioner',
            'Decontamination facility established: three-stage decontamination unit for workers exiting containment (dirty, shower, clean)',
        ],
        'eng': [
            'Full containment enclosure with negative pressure — Minimum 4 Pascal negative pressure maintained and continuously monitored. HEPA filtration on exhaust. Decontamination shower unit at enclosure exit. Wet methods supplementary to containment — Water injection at nozzle.',
        ],
        'admin': [
            'Lead removal work plan documented — Approved by occupational hygienist. Clearance air monitoring before enclosure dismantled — Results below clearance criteria. Waste classified as hazardous — Double-bagged, labelled, and disposed of at licensed facility with EPA tracking. Decontamination procedure: workers shower and change clothes before leaving site — No work clothes worn home. Laundry service for work clothes provided.',
        ],
        'ppe': [
            'Supplied-air blast helmet (minimum Class 2B). Disposable coveralls removed and bagged before decontamination. Nitrile gloves under leather blast gloves. Steel capped boots dedicated to blast work — Left on site.',
        ],
        'stop_work': [
            'Containment pressure loss — Air monitoring exceeds WES — Blood lead level exceeds action level — Decontamination facility not functional — HEPA filter not changed per schedule — Waste not correctly contained — Any containment breach.',
        ]
    },
    'noise_mgmt': {
        'task': 'Noise Management — Hearing Conservation',
        'task_desc': 'Assessment and management of noise exposure from abrasive blasting operations including compressor, blasting, and media handling. Covers worker exposure and community noise impact.',
        'hazard': 'Noise-induced hearing loss from prolonged exposure >85 dB(A). Tinnitus. Communication difficulty in high-noise environment. Community noise complaint.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'PRE-M4', 'resp': 'Supervisor / Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Compressor positioned maximum distance from occupied areas — Exhaust directed away. Noise attenuation on compressor where available. Blast nozzle selection for minimum noise — Venturi nozzles quieter than straight bore. Containment enclosure provides noise reduction to surrounds.'),
            ('Admin:', 'Noise assessment completed — Personal exposure levels documented. Hearing conservation program in place if exposure >85 dB(A) 8hr TWA: audiometric testing baseline and annual. Work hours restricted per council/EPA noise conditions — Typically 7am–5pm. Noise monitoring at site boundary if near residential. Communication in blast zone: hand signals or radio — Verbal communication not possible.'),
            ('PPE:', 'Class 5 hearing protection (>85 dB) minimum for blaster and assistants. Dual protection (plugs + muffs) where exposure >100 dB(A). Hearing protection (>85 dB) for all workers within 15m of blasting operations.'),
            ('STOP WORK if:', 'Worker not wearing hearing protection (>85 dB) in blast zone — Noise monitoring exceeds council limits at boundary — Audiometric testing shows threshold shift — Communication system failure in blast zone.')
        ]
    },
}


# ============================================================
# SCREED PUMP — Concrete Screed Pump Operations (MSW-009)
# ============================================================

SCREED_NEW = {
    'screed_pump_setup': {
        'task': 'Screed Pump Setup, Hose Connection and Pressure Testing',
        'task_desc': 'Position line pump, connect delivery hoses, inspect all couplings and safety clips, pressure test before pumping.',
        'hazard': 'High-pressure injection injury from pump line \u2014 Sand/cement injected under skin causes tissue necrosis, compartment syndrome, potential amputation or death. Hose whip from coupling failure. Manual handling of pump components and delivery hoses. Electrical hazard from pump motor.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'ENE-H6', 'resp': 'Supervisor / Pump Operator',
        'type': 'CCVS',
        'hold_points': [
            'Pump operator trained and competent in specific pump model \u2014 Training records sighted',
            'All delivery line couplings inspected, secured, and safety clips/pins confirmed \u2014 No worn or damaged fittings',
            'Pressure test completed at rated working pressure before pumping screed \u2014 No leaks, no coupling movement',
            'Exclusion zone established around pump and full length of delivery line \u2014 No personnel in hose whip zone during start-up and priming',
        ],
        'eng': [
            'Hose clamps and couplings rated to pump maximum pressure \u2014 Safety whip checks on all hose joints \u2014 Delivery line secured and supported to prevent movement \u2014 RCD protection on electric pump',
        ],
        'admin': [
            'Pump manufacturer operating manual on site \u2014 Daily pre-start inspection recorded \u2014 Hose and coupling replacement schedule maintained \u2014 Emergency shutdown procedure briefed to all workers',
        ],
        'ppe': [
            'Steel-capped footwear, eye protection, hearing protection (>85 dB), cut-resistant gloves, hi-vis vest or shirt',
        ],
        'stop_work': [
            'Hose coupling leaking or damaged \u2014 Pump pressure exceeds rated limit \u2014 Delivery line unsecured or unsupported \u2014 Blockage in line (do not attempt to clear under pressure) \u2014 Electrical fault on pump motor',
        ],
    },
    'screed_material_prep': {
        'task': 'Material Preparation and Mesh Placement',
        'task_desc': 'Handle and stage cement and sand bags, cut and lay galvanised steel mesh reinforcement to specification.',
        'hazard': 'Manual handling of cement and sand bags (20\u201325 kg). Cement dust inhalation and alkaline skin/eye contact. Cut and puncture injuries from mesh handling and cutting. Slip and trip on materials and offcuts.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (1)',
        'code': 'ENV-M4', 'resp': 'Supervisor / Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Mechanical aids for repetitive bag handling where available \u2014 Mesh cut with bolt cutters (not angle grinder) to reduce sparks and noise \u2014 Material staged to minimise carry distances'),
            ('Admin:', 'SDS for cement reviewed \u2014 Correct mix ratio confirmed (1:3 or 1:4 cement:sand per specification) \u2014 Mesh specification and lap requirements confirmed before placement \u2014 Rotate workers on manual handling tasks'),
            ('PPE:', 'P2 dust mask (dry cement handling), eye protection, chemical-resistant gloves (nitrile), steel-capped footwear, long sleeves'),
            ('STOP WORK if:', 'SDS not available for cement product \u2014 Mesh specification not confirmed \u2014 Manual handling of bags >25 kg without mechanical aids'),
        ]
    },
    'screed_pumping': {
        'task': 'Screed Pumping, Placement and Levelling',
        'task_desc': 'Pump sand/cement screed via delivery line, place to specified thickness, screed and level to falls.',
        'hazard': 'Alkaline burns from wet cement screed (pH 12\u201313). Slip hazard on wet screed surface. Noise from pump operation. Manual handling strain from screeding and levelling. Hose movement and trip hazard.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (1)',
        'code': 'ENV-M4', 'resp': 'Supervisor / Pump Operator / Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Delivery hose routed and secured to prevent trip hazard \u2014 Non-slip walkways maintained around pour area \u2014 Pump operator maintains visual contact with nozzle operator at all times'),
            ('Admin:', 'Pour sequence planned to avoid workers walking on fresh screed \u2014 Nozzle operator and pump operator communicate via agreed signals (radio or hand) \u2014 Skin contact with wet screed washed immediately with clean water \u2014 Screed thickness confirmed against specification during placement'),
            ('PPE:', 'Waterproof boots, chemical-resistant gloves (nitrile), eye protection, hearing protection (>85 dB), hi-vis vest or shirt, long sleeves'),
            ('STOP WORK if:', 'Communication between pump and nozzle operator fails \u2014 Screed mix consistency incorrect (too wet or too dry to pump) \u2014 Hose unsecured or moved from supported position'),
        ]
    },
    'screed_cleanup': {
        'task': 'Pump Cleanup, Washout and Demobilisation',
        'task_desc': 'Flush delivery lines, contain washout water, disconnect hoses, clean and remove pump from site.',
        'hazard': 'Alkaline washout water \u2014 Environmental contamination if discharged to stormwater. High-pressure water during line flush. Manual handling during hose disconnection and pump removal. Slip on wet surfaces.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (1)',
        'code': 'ENV-M4', 'resp': 'Supervisor / Pump Operator',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Washout water contained in designated bund or container \u2014 No discharge to stormwater drains, gutters, or ground \u2014 Pump depressurised before disconnecting any coupling'),
            ('Admin:', 'Washout location agreed before pumping commences \u2014 Washout water pH tested if discharge to sewer required (council approval) \u2014 All hoses and couplings cleaned, inspected, and stored \u2014 Site left clean and free of screed residue'),
            ('PPE:', 'Waterproof boots, chemical-resistant gloves (nitrile), eye protection, hi-vis vest or shirt'),
            ('STOP WORK if:', 'No containment available for washout water \u2014 Pump not fully depressurised before disconnection'),
        ]
    },
}


# Save task data for reference
print("Task definitions loaded:")
print(f"  Remedial: {len(REMEDIAL_NEW)} new tasks")
print(f"  Spray: {len(SPRAY_NEW)} new tasks")
print(f"  Groundworks: {len(GROUND_NEW)} new tasks")
print(f"  Cladding: {len(CLADDING_NEW)} new tasks")
print(f"  EWP: {len(EWP_NEW)} new tasks")
print(f"  Swing Stage: {len(SWING_NEW)} new tasks")
print(f"  Blasting: {len(BLASTING_NEW)} new tasks")
print(f"  Screed Pump: {len(SCREED_NEW)} new tasks")
print(f"  TOTAL: {len(REMEDIAL_NEW)+len(SPRAY_NEW)+len(GROUND_NEW)+len(CLADDING_NEW)+len(EWP_NEW)+len(SWING_NEW)+len(BLASTING_NEW)+len(SCREED_NEW)} new tasks")

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

TEMPLATE_PATH = "/mnt/user-data/uploads/RPD_MASTER_SWMS_TEMPLATE_V1.docx"
OUTPUT_DIR = "/mnt/user-data/outputs"

# ============================================================
# XML HELPERS
# ============================================================

def make_run(text, bold=False, font='Aptos', size='16', color=None):
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
    if color:
        c = etree.SubElement(rPr, qn('w:color'))
        c.set(qn('w:val'), color)
    t = etree.SubElement(r, qn('w:t'))
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    t.text = text
    return r

def make_para(spacing_before='20', spacing_after='20', line='276'):
    """Create empty w:p with spacing"""
    p = etree.Element(qn('w:p'))
    pPr = etree.SubElement(p, qn('w:pPr'))
    sp = etree.SubElement(pPr, qn('w:spacing'))
    sp.set(qn('w:before'), spacing_before)
    sp.set(qn('w:after'), spacing_after)
    sp.set(qn('w:line'), line)
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
        'task_desc': 'Mechanical removal of deteriorated concrete to sound substrate using jackhammers, scabblers, and needle guns. Preparation of exposed reinforcement and application of repair mortars.',
        'hazard': 'Silica dust from concrete removal. Flying debris and fragments. Noise exposure. Hand-arm vibration from power tools. Working at height during façade repairs.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'PRE-M4', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Dust extraction on all power tools — vacuum-attached scabblers and needle guns. Water suppression where dust extraction not practicable. Physical barriers to contain debris — mesh screens on scaffold, drop sheets below work zone. Vibration-dampened tool handles where available.'),
            ('Admin:', 'Concrete repair specification reviewed before commencement — depth of breakout, reinforcement treatment, repair mortar system confirmed. Silica dust exposure assessment completed — air monitoring if breakout exceeds 4 hours continuous. Vibration exposure log maintained — tool rotation every 30 minutes. Spotter below when working at height.'),
            ('PPE:', 'P2 respirator (minimum) — half-face P3 with particulate filter if air monitoring indicates. Eye protection and face shield during breakout. Hearing protection (>85 dB, Class 5 minimum). Cut-resistant gloves. Steel capped footwear.'),
            ('STOP WORK if:', 'Dust extraction fails or is inadequate — visible dust plume beyond immediate work zone — reinforcement condition worse than specification anticipated — structural concern identified during breakout — vibration exposure limit reached — unexpected services or voids encountered.')
        ]
    },
    'crack_stitching': {
        'task': 'Crack Stitching and Structural Reinforcement',
        'task_desc': 'Installation of helical bars, carbon fibre reinforcement, or stainless steel pins into prepared slots/holes to restore structural integrity of cracked masonry and concrete elements.',
        'hazard': 'Silica dust from slot cutting. Noise from cutting equipment. Epoxy and resin chemical exposure. Working at height. Structural instability during repair.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'PRE-M4', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Slot cutting with vacuum-attached blade guard — no dry cutting. Depth stop set on cutting equipment per engineering specification — typically 25–35mm into mortar beds. Services scan (CAT/Genny) before cutting into any substrate. Containment of epoxy/grout waste.'),
            ('Admin:', 'Engineering specification and drawings reviewed before commencement — slot depths, bar sizes, spacing, grout product confirmed. SDS for all epoxy, grout, and primer products reviewed — Fosroc Nitoprime, Renderox, WHO-60 or equivalent. Crack monitoring record completed before and after stitching. Structural engineer sign-off required before proceeding if crack width exceeds specification tolerance.'),
            ('PPE:', 'P2 respirator during cutting operations. Nitrile gloves for epoxy and grout handling — no skin contact with uncured resin. Eye protection. Hearing protection (>85 dB) during cutting. Steel capped footwear.'),
            ('STOP WORK if:', 'Crack width or depth exceeds engineering specification tolerance — unexpected movement or displacement observed — services detected in cutting path — structural engineer advises hold — product temperature outside application range.')
        ]
    },
    'waterproofing': {
        'task': 'Waterproofing and Membrane Application',
        'task_desc': 'Application of liquid-applied or sheet membrane waterproofing systems to balconies, podiums, planter boxes, wet areas, and below-grade elements. Includes surface preparation, primer, membrane, and protection layers.',
        'hazard': 'Chemical exposure from primers, membranes, and solvents. Slip hazard on wet/coated surfaces. Fumes in enclosed areas. Manual handling of membrane rolls and equipment.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'PRE-M4', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Ventilation maintained in enclosed application areas — mechanical ventilation if natural airflow insufficient. Non-slip walking paths maintained around wet membrane areas. Drainage provisions to prevent water pooling on uncured membrane.'),
            ('Admin:', 'Waterproofing specification and system data sheet reviewed — substrate preparation, primer, membrane type, application rates, cure times confirmed. SDS for all products reviewed before use. Ambient temperature and substrate moisture checked before application — no application outside product parameters. Wet film thickness checks during application.'),
            ('PPE:', 'Nitrile gloves — chemical-resistant. P2 respirator with organic vapour cartridge if solvent-based products. Eye protection. Non-slip footwear. Disposable overalls where splash risk exists.'),
            ('STOP WORK if:', 'Temperature outside product application range — substrate moisture exceeds product tolerance — rain imminent on uncured membrane — ventilation fails in enclosed area — product shelf life expired.')
        ]
    },
    'expansion_joint': {
        'task': 'Expansion Joint Replacement',
        'task_desc': 'Removal of failed expansion joint systems and installation of new joint sealant, backer rod, or proprietary joint covers to building façade, podium, and structural movement joints.',
        'hazard': 'Working at height during façade joint replacement. Chemical exposure from sealants and primers. Noise from cutting/grinding old joint material. Debris and dust. Hand tool injuries.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'PRE-M4', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Dust extraction during mechanical removal of old sealant. Containment of removed sealant and debris — no material to fall below. Backer rod sized correctly to joint width — minimum 25% compression. Joint faces clean, dry, and primed before sealant application.'),
            ('Admin:', 'Joint schedule and sealant specification reviewed — joint widths, depths, sealant type, primer compatibility confirmed. SDS for sealant, primer, and backer rod products reviewed. Joint movement range confirmed with structural engineer if movement exceeds original design. Weather check — no application in rain or below product minimum temperature.'),
            ('PPE:', 'Nitrile gloves for sealant and primer handling. Eye protection. P2 respirator if solvent-based primer. Steel capped footwear. Cut-resistant gloves for mechanical removal.'),
            ('STOP WORK if:', 'Joint movement exceeds design parameters — substrate condition prevents proper adhesion — rain during application — product outside temperature range — joint depth or width significantly different from specification.')
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
            'Operator competency confirmed: trained in airless spray equipment operation — manufacturer training or demonstrated competence sighted',
            'Equipment pre-start completed: pump, hoses, fittings, tip guard, trigger lock, pressure relief all inspected and serviceable',
            'Maximum operating pressure confirmed and not exceeded — pressure gauge functional and visible to operator',
            'Injection injury first aid procedure briefed to all crew — nearest hospital with hand surgery capability identified',
        ],
        'eng': [
            'Tip guard fitted at all times — never removed during operation. Trigger lock engaged when not actively spraying. Pressure relief valve functional. Hose whip checks fitted to all high-pressure connections. Earthing/grounding strap connected to prevent static discharge — critical with solvent-based products.',
        ],
        'admin': [
            'Exclusion zone around spray unit — minimum 3m from pump and hose connections. Pressure bleed-down procedure followed before any tip change, filter clean, or maintenance. Never point gun at any person. Two-person operation when spraying at height.',
        ],
        'ppe': [
            'Leather gloves when handling hoses and connections. Eye protection. Hearing protection (>85 dB, Class 5). Steel capped footwear. P2 respirator minimum — upgrade to half-face with OV/P3 cartridge for solvent-based products.',
        ],
        'stop_work': [
            'Hose damage, kink, or abrasion detected — pressure gauge not functioning — tip guard missing or damaged — any injection injury (treat as medical emergency — do not wait for symptoms) — earthing strap disconnected with solvent-based products — operator not trained.',
        ]
    },
    'spray_exterior': {
        'task': 'Spray Application — Exterior (Open Air)',
        'task_desc': 'Airless spray application of paints, primers, sealers, and texture coatings to exterior surfaces in open-air conditions. Includes overspray management and environmental controls.',
        'hazard': 'Overspray drift to adjacent properties, vehicles, and persons. Paint mist inhalation. Slip hazard from overspray on walkways. Wind-driven spray. Working at height.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'PRE-M4', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Overspray containment: scaffold shrink-wrap, drop sheets, and masking to all adjacent surfaces, windows, vehicles, and property. Wind breaks where practicable. Spray tip selected for minimum overspray — correct fan width and orifice size for product.'),
            ('Admin:', 'Wind speed monitored — no spraying above 15 km/h or per product data sheet limit, whichever is lower. Adjacent property and vehicle owners notified 48 hours before spraying. Spotter positioned to warn of pedestrians and wind changes. Overspray inspection after each spray session — immediate clean-up of any overspray.'),
            ('PPE:', 'Half-face respirator with P2/OV cartridge. Eye protection or goggles. Disposable spray suit or coveralls. Nitrile gloves. Head cover.'),
            ('STOP WORK if:', 'Wind exceeds limit — overspray escaping containment — adjacent property complaint — rain during application — pedestrians entering spray zone — containment failure.')
        ]
    },
    'spray_interior': {
        'task': 'Spray Application — Interior (Enclosed/Confined)',
        'task_desc': 'Airless spray application inside buildings, enclosed plant rooms, stairwells, basements, and areas with limited natural ventilation. Includes mandatory ventilation and atmospheric monitoring requirements.',
        'hazard': 'Solvent vapour accumulation — explosive atmosphere risk with solvent-based products. Paint mist inhalation in enclosed space. Reduced visibility. Oxygen depletion in confined areas. Ignition sources.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'HAZ-H6', 'resp': 'Supervisor / Worker',
        'type': 'CCVS',
        'hold_points': [
            'Ventilation assessment completed: mechanical ventilation sized for room volume and product vapour generation rate — air changes per hour confirmed adequate',
            'Atmospheric monitoring in place if solvent-based products used — LEL monitor calibrated and alarming at 10% LEL',
            'All ignition sources eliminated: no hot work, no unsealed electrical, no mobile phones in spray zone if solvent-based',
            'Emergency egress routes clear and marked — minimum two exits from spray area where practicable',
        ],
        'eng': [
            'Mechanical exhaust ventilation running before, during, and 30 minutes after spraying. Fresh air intake positioned to create cross-flow ventilation. Explosion-proof electrical fittings in spray zone if solvent-based products. LEL monitor with audible alarm at 10% LEL.',
        ],
        'admin': [
            'Confined space risk assessment completed if area meets confined space definition per WHS Regulation. Water-based products preferred over solvent-based for interior work. Spray schedule coordinated to minimise exposure duration. Buddy system — no solo interior spraying.',
        ],
        'ppe': [
            'Full-face respirator with combination OV/P3 cartridge for solvent-based. Half-face with P2/OV for water-based. Disposable spray suit. Nitrile gloves. Eye protection under full-face respirator.',
        ],
        'stop_work': [
            'LEL alarm activates — ventilation fails or reduces — any worker reports dizziness, nausea, or irritation — visibility drops below 3m — ignition source identified in spray zone — single exit only and no buddy available.',
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
            ('Engineering:', 'Stormwater drains bunded and covered within 10m of spray zone. Wash-water captured in containment — no discharge to stormwater. Drop sheets and masking on all adjacent surfaces. Scaffold shrink-wrap where exterior spraying from scaffold.'),
            ('Admin:', 'Environmental management plan reviewed — stormwater protection, waste disposal, noise management. Paint waste and wash-water disposed of as trade waste — not to sewer or stormwater. Adjacent property register maintained — pre/post condition photos. Resident/tenant notification 48 hours before spray operations.'),
            ('PPE:', 'As per spray application task requirements.'),
            ('STOP WORK if:', 'Overspray escapes containment — paint or wash-water enters stormwater — community complaint not resolved — containment fails — wind exceeds spray limit.')
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
            ('Engineering:', 'Cleaning in well-ventilated area only — outdoors preferred. Solvent waste captured in sealed metal containers — not poured to drain. Pressure bled down before disassembly. Solvent-soaked rags in self-closing metal bin — removed from site daily.'),
            ('Admin:', 'SDS for all solvents and thinners reviewed. Minimum solvent quantity used — water flush first where possible with water-based products. Solvent waste disposal via licensed contractor. No smoking or ignition sources within 5m of cleaning area.'),
            ('PPE:', 'Nitrile chemical-resistant gloves. P2 respirator with organic vapour cartridge. Eye protection. Disposable coveralls if splash risk.'),
            ('STOP WORK if:', 'Solvent spill not contained — ventilation inadequate — ignition source near cleaning area — solvent waste container full or unsealed.')
        ]
    },
}

# --- GROUNDWORKS NEW TASKS ---
GROUND_NEW = {
    'excavation': {
        'task': 'Excavation and Trenching',
        'task_desc': 'Open-cut excavation, trenching for services, footings, and drainage. Includes benching, battering, and shoring of excavation walls deeper than 1.5m.',
        'hazard': 'Collapse of excavation walls — burial and suffocation. Fall into excavation. Contact with underground services. Flooding/water ingress. Ground vibration from adjacent plant.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'WAH-H6', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'CCVS',
        'hold_points': [
            'Geotechnical assessment reviewed: soil classification confirmed — batter angles and shoring requirements determined before excavation commences',
            'Dial Before You Dig (DBYD) plans obtained and current (within 30 days). Service locations confirmed by non-destructive potholing within 1m of any indicated service',
            'Excavation deeper than 1.5m: shoring, benching, or battering designed by competent person per AS 4678 and WHS Regulation Chapter 6',
            'Barricading: full perimeter barricade with warning signage before any excavation left unattended',
        ],
        'eng': [
            'Shoring installed progressively as depth increases. Benching/battering angles per geotechnical report — never steeper than soil classification allows. Dewatering active if water table encountered. Edge protection: minimum 1m setback for spoil stockpile from excavation edge.',
        ],
        'admin': [
            'Daily inspection of excavation walls by competent person before any worker entry. After rain: re-inspection before re-entry. Excavation permit system in place for depths >1.5m. Emergency rescue plan for excavation entrapment — rescue equipment on site (ladder, harness, retrieval line).',
        ],
        'ppe': [
            'Steel capped footwear. Hard hat. High-vis vest or shirt. Cut-resistant gloves. Harness and retrieval line if entering excavation >1.5m without shoring.',
        ],
        'stop_work': [
            'Wall cracking, slumping, or movement observed — water ingress not controlled by dewatering — shoring damaged or displaced — services exposed and not confirmed de-energised — spoil encroaching on edge setback — any worker in excavation >1.5m without shoring/benching.',
        ]
    },
    'services_location': {
        'task': 'Underground Services Location and Protection',
        'task_desc': 'Location, identification, and protection of underground services including electrical, gas, water, sewer, telecommunications, and stormwater during ground disturbance activities.',
        'hazard': 'Electrocution from contact with underground power cables. Gas main rupture — explosion and fire. Water main burst — flooding. Telecommunications damage — service disruption. Sewer damage — contamination.',
        'risk_pre': 'High (9)', 'risk_post': 'Low (2)',
        'code': 'ELE-H9', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'CCVS',
        'hold_points': [
            'DBYD plans obtained, current, and reviewed by all workers involved in ground disturbance. Plans less than 30 days old',
            'Service locator (CAT/Genny or GPR) used to confirm locations before any mechanical excavation. Services marked on ground with paint/flags',
            'Hand dig/vacuum excavation (potholing) within 1m horizontal and 300mm vertical of any indicated service — no mechanical excavation within this zone',
            'Service owner contacted and clearance obtained for work near high-risk services (HV power, high-pressure gas)',
        ],
        'eng': [
            'Services physically exposed by hand/vacuum excavation before mechanical plant operates within proximity. Exposed services supported and protected from damage. Isolation of services where practicable — de-energise, shut off, or depressurise.',
        ],
        'admin': [
            'Service strike emergency procedure briefed to all workers — isolation points identified. Gas: evacuate, no ignition, call 000 and gas authority. Electrical: do not approach, isolate at source, call 000 and network provider. All workers inducted on service locations marked on site plan.',
        ],
        'ppe': [
            'Steel capped footwear. Hard hat. High-vis vest or shirt. Insulated gloves if working near suspected electrical services. Cut-resistant gloves.',
        ],
        'stop_work': [
            'Service encountered not shown on DBYD plans — any service contact (even minor) — odour of gas detected — water flow from unknown source — service locator readings inconsistent with plans — mechanical plant within 1m of unconfirmed service.',
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
            'Operator holds current SafeWork NSW HRW licence for plant class being operated — licence sighted and recorded',
            'Plant pre-start inspection completed and recorded — all safety systems functional (ROPS, FOPS, seatbelt, reversing alarm, camera/mirrors)',
            'Exclusion zones established: minimum 3m from operating plant for pedestrians — spotter in place when pedestrians must enter zone',
            'Overhead power line assessment completed — safe approach distances confirmed per AS/NZS 4576',
        ],
        'eng': [
            'ROPS and FOPS fitted and certified. Reversing camera and alarm operational. Rotating beacon active during operation. Physical barriers between plant operating zone and pedestrian areas where practicable. Outriggers deployed for lifting operations.',
        ],
        'admin': [
            'Plant movement plan reviewed — travel paths, exclusion zones, overhead hazards, underground services all identified. Spotter assigned for reversing and blind spot operations. Communication between operator and ground crew — hand signals or two-way radio. Daily pre-start log maintained.',
        ],
        'ppe': [
            'Operator: seatbelt worn at all times. Hard hat, steel capped footwear, high-vis vest or shirt for all ground personnel. Hearing protection (>85 dB) within 10m of operating plant.',
        ],
        'stop_work': [
            'Licence not current — pre-start defect not rectified — pedestrian in exclusion zone — spotter not available for reversing — overhead power line approach distance compromised — ground conditions unsafe (soft, unstable) — operator fatigued.',
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
            ('Engineering:', 'Formwork designed by competent person — load calculations for concrete head and pump pressure. Props and bracing per formwork design. Rebar caps on all exposed vertical reinforcement. Mechanical lifting for formwork panels >25kg.'),
            ('Admin:', 'Formwork inspection by competent person before pour — checklist completed and signed. Strip sequence planned — no early stripping before concrete reaches minimum strength. Steel fixing schedule and bar schedule checked against engineering drawings.'),
            ('PPE:', 'Steel capped footwear. Hard hat. Cut-resistant gloves. Long sleeves. Eye protection when cutting tie wire or reinforcement.'),
            ('STOP WORK if:', 'Formwork movement, bulging, or deflection during pour — props not plumb or bracing inadequate — rebar caps missing on vertical bars — concrete strength not confirmed before stripping — formwork design not available for inspection.')
        ]
    },
    'concrete_pour': {
        'task': 'Concrete Pouring and Finishing',
        'task_desc': 'Placement of ready-mix concrete by pump, crane-and-kibble, or direct discharge. Includes vibration, screeding, floating, and finishing of concrete surfaces.',
        'hazard': 'Concrete pump line failure — high-pressure release. Chemical burns from wet concrete (alkaline). Manual handling — vibrator, screeds. Slip hazard on wet concrete. Noise.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'PRE-M4', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Concrete pump lines secured at all connections — safety chains or clips. Pump line whip restraints at bends. Formwork bracing checked immediately before pour. Vibrator connected to safety line to prevent loss into pour.'),
            ('Admin:', 'Pour plan reviewed — sequence, volume, timing, finishing requirements. Formwork pre-pour inspection completed and signed off. Concrete docket checked on arrival — slump, strength, admixtures match specification. Wash-out area prepared — no wash-out to stormwater.'),
            ('PPE:', 'Waterproof boots (gumboots) when standing in wet concrete. Nitrile gloves — no skin contact with wet concrete (pH 12-13 causes chemical burns). Eye protection. Long sleeves.'),
            ('STOP WORK if:', 'Pump line blockage with pressure build-up — formwork movement during pour — concrete strength/slump does not match specification — rain affecting finish quality — wash-out entering stormwater.')
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
            ('Engineering:', 'Compaction equipment with vibration-dampened handles. Dust suppression with water spray during dry conditions. Backfill placed in controlled lifts — maximum layer thickness per geotechnical specification.'),
            ('Admin:', 'Compaction testing at specified intervals and depths per geotechnical requirements. Fill material source and quality confirmed — no contaminated or unsuitable material. Vibration exposure log maintained — tool rotation schedule. Level checks against survey marks.'),
            ('PPE:', 'Steel capped footwear. Hearing protection (>85 dB). P2 dust mask in dry/dusty conditions. Cut-resistant gloves. High-vis vest or shirt.'),
            ('STOP WORK if:', 'Vibration exposure limit reached — contaminated or unsuitable fill material identified — compaction test failures — trench wall movement during backfill — dust not controlled.')
        ]
    },
    'drainage': {
        'task': 'Drainage and Stormwater Installation',
        'task_desc': 'Installation of stormwater pipes, pits, grates, and associated drainage infrastructure. Includes pipe laying, jointing, bedding, and connection to existing systems.',
        'hazard': 'Working in trenches — collapse risk. Manual handling of pipes and pit components. Exposure to existing sewer or contaminated water. Crush injury during pipe lowering.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'PRE-M4', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Trench shored or battered per excavation task requirements. Mechanical lifting for pipes >25kg. Pipe bedding material placed and compacted before pipe laying. Existing services located and protected per services task requirements.'),
            ('Admin:', 'Pipe grades and falls checked against hydraulic design. Jointing method confirmed — solvent cement, rubber ring, or mechanical coupling per specification. No entry to live sewer pit without confined space assessment. CCTV inspection of completed pipework where specified.'),
            ('PPE:', 'Steel capped footwear. Cut-resistant gloves. Eye protection when cutting pipe. High-vis vest or shirt. Waterproof boots if working in water.'),
            ('STOP WORK if:', 'Trench not shored when depth requires it — connection to live sewer without isolation — pipe grade incorrect — existing services not confirmed before crossing — water ingress not controlled.')
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
            ('Engineering:', 'Electric pumps on RCD-protected circuits — leads clear of water. Pump intake screened to prevent blockage. Discharge via sediment control — silt fence, sediment basin, or filter sock. No direct discharge to stormwater without filtration.'),
            ('Admin:', 'Dewatering licence or approval obtained if required by local authority. Water quality tested if contamination suspected — disposal via licensed facility if contaminated. Pump operation monitored — excavation stability checked during dewatering. Discharge location and flow rate recorded.'),
            ('PPE:', 'Waterproof boots. Cut-resistant gloves. Hearing protection (>85 dB) near pump.'),
            ('STOP WORK if:', 'Electrical fault on pump — discharge entering stormwater without filtration — excavation instability during dewatering — contaminated water identified — pump discharge flooding adjacent property.')
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
            'Shoring system designed by competent person or structural engineer — design documentation on site and current for ground conditions',
            'Shoring components inspected before installation — certified, rated, and matched to design specification',
            'Installation supervised by competent person — progressive installation from top down in trenches',
            'No worker entry to unshored excavation >1.5m depth',
        ],
        'eng': [
            'Hydraulic or mechanical shoring systems rated for soil type and depth. Props and struts positioned per design — bearing plates on all contact surfaces. Waling and sheeting per design specification. Shoring to remain in place until backfill reaches safe height.',
        ],
        'admin': [
            'Daily inspection of shoring by competent person — condition, alignment, load, ground movement. Shoring removal sequence planned — never remove from bottom up. After rain or seismic event — re-inspection before re-entry. Load monitoring where specified by engineer.',
        ],
        'ppe': [
            'Steel capped footwear. Hard hat. Cut-resistant gloves. High-vis vest or shirt.',
        ],
        'stop_work': [
            'Shoring movement, displacement, or deformation — ground cracking or slumping adjacent to excavation — shoring components damaged or not matched to design — competent person not available for inspection — water ingress undermining shoring foundations.',
        ]
    },
    'contaminated_soil': {
        'task': 'Contaminated Soil Management',
        'task_desc': 'Identification, handling, stockpiling, and disposal of potentially contaminated soil encountered during earthworks. Includes asbestos-containing soil, hydrocarbon-contaminated material, and acid sulphate soils.',
        'hazard': 'Exposure to asbestos fibres in soil. Hydrocarbon vapour inhalation. Skin contact with contaminated material. Incorrect disposal — environmental and legal liability.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'HAZ-M4', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Contaminated soil stockpiled on plastic sheeting — covered when not being loaded. Dust suppression during excavation and loading. Separate stockpiles for different contamination types. Stormwater controls to prevent contaminated runoff.'),
            ('Admin:', 'Contamination assessment report reviewed before earthworks — known contamination areas mapped on site plan. Unexpected finds protocol: stop work, isolate area, notify supervisor, test before proceeding. Waste classification per EPA guidelines — disposal to licensed facility with tracking documentation. Chain of custody records maintained.'),
            ('PPE:', 'P2 respirator minimum — upgrade to half-face P3 if asbestos suspected. Nitrile gloves. Disposable coveralls if handling known contaminated material. Steel capped footwear.'),
            ('STOP WORK if:', 'Unexpected odour, discolouration, or material inconsistent with contamination report — suspected asbestos encountered — no waste classification available — disposal facility not confirmed — dust from contaminated material not controlled.')
        ]
    },
}

# --- CLADDING WORKS NEW TASKS ---
CLADDING_NEW = {
    'panel_install': {
        'task': 'Cladding Panel Lifting and Installation',
        'task_desc': 'Mechanical lifting, positioning, and fixing of cladding panels including metal composite, fibre cement, terracotta, timber, and aluminium systems. Includes crane, hoist, and manual lifting operations.',
        'hazard': 'Falling panel during lift — struck by. Panel caught by wind. Crush injury during positioning. Working at height during installation. Overloading of scaffold or EWP with panel weight.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'STR-H6', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'CCVS',
        'hold_points': [
            'Lift plan completed: panel weights confirmed, lifting equipment rated and certified, rigging method and attachment points verified',
            'Wind speed monitored — no lifting above 30 km/h or panel manufacturer limit, whichever is lower. Large panels (>5m²): no lifting above 20 km/h',
            'Exclusion zone established below lifting zone — no workers beneath suspended panel at any time',
            'Scaffold or EWP load rating confirmed adequate for panel weight plus worker weight plus tools',
        ],
        'eng': [
            'Panel handling equipment (suction cups, clamps, lifting frames) rated for panel weight and type. Tag lines on all panels during crane lifts. Temporary fixing/bracing immediately on placement — panel not released from lifting equipment until minimum fixings installed per design.',
        ],
        'admin': [
            'Installation sequence per cladding design — verified with structural engineer for load distribution. Panel storage on site — stacked per manufacturer requirements, secured against wind. Delivery coordination — just-in-time where possible to minimise on-site storage.',
        ],
        'ppe': [
            'Hard hat. Cut-resistant gloves. Steel capped footwear. Eye protection. Harness when working at height. High-vis vest or shirt.',
        ],
        'stop_work': [
            'Wind exceeds lift limit — rigging equipment defective — panel damaged and structural integrity compromised — exclusion zone breached — scaffold/EWP overloaded — fixing system not per design specification.',
        ]
    },
    'panel_removal': {
        'task': 'Cladding Panel Removal and Demolition',
        'task_desc': 'Controlled removal and demolition of existing cladding systems including assessment for hazardous materials, sequencing, and structural stability during progressive removal.',
        'hazard': 'Falling panels — uncontrolled release. Asbestos or lead in existing cladding. Structural instability during progressive removal. Dust and debris. Working at height.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'STR-H6', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'CCVS',
        'hold_points': [
            'Hazardous materials assessment completed: existing cladding tested for asbestos and lead — clearance obtained or licensed removal arranged before general demolition',
            'Demolition sequence designed by competent person — structural engineer consulted if cladding contributes to building stability',
            'Exclusion zone established below removal zone — barricading and signage in place',
            'All panels secured before fixing removal commences — no unsecured panels at any time',
        ],
        'eng': [
            'Panels secured with temporary fixings or restraint before permanent fixings removed. Controlled lowering — no dropping or throwing panels. Debris containment — scaffold netting, catch platforms, enclosed chutes for waste material. Dust suppression during cutting.',
        ],
        'admin': [
            'Demolition plan reviewed by all workers. Removal sequence strictly followed — top to bottom, one panel at a time. Asbestos or lead identified: licensed removalist engaged per WHS Regulation. Waste segregation — recyclable, hazardous, general.',
        ],
        'ppe': [
            'Hard hat. Cut-resistant gloves. Steel capped footwear. Eye protection and face shield during cutting. P2 respirator. Harness when working at height.',
        ],
        'stop_work': [
            'Suspected asbestos identified during removal — structural concern raised by competent person — panel release not controlled — exclusion zone breached — wind making panel handling unsafe — dust not controlled.',
        ]
    },
    'fixing_fastening': {
        'task': 'Fixing and Fastening — Drilling, Screwing, Riveting',
        'task_desc': 'Mechanical fixing of cladding panels, subframes, brackets, and components using power drills, screw guns, rivet guns, and pneumatic tools. Includes chemical anchoring and structural fixings.',
        'hazard': 'Drill bit breakage — flying fragments. Noise exposure. Hand-arm vibration. Struck by rivet or screw. Electrical hazard from power tools. Working at height.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'PRE-M4', 'resp': 'Supervisor / Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Drill bits and fasteners matched to substrate — masonry, steel, or timber. Depth stop set for all chemical anchor drilling. Vibration-dampened tool handles where available. All power tools test-tagged current per AS/NZS 3012 — 3-monthly on construction sites.'),
            ('Admin:', 'Fixing schedule and specification reviewed — fastener type, size, spacing, edge distance, embedment depth per cladding design. Pull-out testing at specified frequency per design. Services scan before drilling into any unknown substrate. Swarf and debris cleaned up progressively.'),
            ('PPE:', 'Eye protection and face shield when drilling overhead. Hearing protection (>85 dB). Cut-resistant gloves. Steel capped footwear.'),
            ('STOP WORK if:', 'Substrate different from specification — fixing pull-out failure — services detected in drilling path — power tool defective — drill bit breakage frequency indicates wrong bit/substrate combination.')
        ]
    },
    'metal_cutting': {
        'task': 'Metal Cutting and Fabrication On-Site',
        'task_desc': 'Cutting, grinding, and fabrication of metal cladding components, subframes, and flashings on site using angle grinders, tin snips, nibblers, and guillotines.',
        'hazard': 'Hot sparks and swarf — fire risk and burns. Noise exposure. Sharp edges on cut metal. Eye injury from grinding. Kickback from angle grinder.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'PRE-M4', 'resp': 'Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Designated cutting area with fire-resistant surface. Guard fitted on all angle grinders — correct disc type for material (metal cutting disc, not masonry). Fire extinguisher within 5m of hot work area. Sharp edge protection — deburring after cutting.'),
            ('Admin:', 'Hot work assessment completed if cutting near combustibles. Fire watch maintained for 30 minutes after hot work ceases. Cutting scheduled to minimise impact on adjacent work — noise and spark management. Off-site prefabrication preferred where possible.'),
            ('PPE:', 'Face shield and eye protection. Hearing protection (>85 dB, Class 5). Leather or cut-resistant gloves. Long sleeves — no synthetic clothing near sparks. Steel capped footwear.'),
            ('STOP WORK if:', 'Grinder guard missing or damaged — wrong disc type for material — combustibles in spark path — fire extinguisher not available — synthetic clothing being worn near sparks.')
        ]
    },
    'weatherproofing': {
        'task': 'Weatherproofing and Flashing Installation',
        'task_desc': 'Installation of flashings, weatherseals, cavity closers, sarking, and weather barriers to cladding systems. Includes window and door head/sill/jamb flashings and parapet cappings.',
        'hazard': 'Sharp edges on flashings — lacerations. Manual handling of long flashing pieces. Wind catching flashing during installation. Working at height. Sealant chemical exposure.',
        'risk_pre': 'Medium (3)', 'risk_post': 'Low (1)',
        'code': 'PRE-M3', 'resp': 'Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Flashings pre-formed to correct profile — minimal on-site bending. Long flashings handled by two workers minimum. Tag lines on flashings being installed at height in wind. Sharp edges deburred before installation.'),
            ('Admin:', 'Flashing installation sequence per cladding design — installed before panel closure. Overlap direction and weatherlap dimensions confirmed per specification. Sealant compatibility with cladding system verified — no silicone on painted surfaces unless specified.'),
            ('PPE:', 'Cut-resistant gloves. Eye protection. Steel capped footwear. Harness when working at height.'),
            ('STOP WORK if:', 'Flashing profile incorrect — wind making handling unsafe — sealant compatibility not confirmed — overlap direction wrong (will trap water).')
        ]
    },
    'acm_cladding': {
        'task': 'Asbestos Cement Sheet — Identification and Management',
        'task_desc': 'Identification, assessment, and management of asbestos-containing materials (ACM) encountered during cladding works. Includes non-friable ACM handling under 10m² and interface with licensed asbestos removalists for larger quantities or friable material.',
        'hazard': 'Inhalation of asbestos fibres — mesothelioma, asbestosis, lung cancer. Uncontrolled fibre release during disturbance. Contamination of work area. Incorrect disposal.',
        'risk_pre': 'High (9)', 'risk_post': 'Low (2)',
        'code': 'HAZ-H9', 'resp': 'Supervisor / Worker',
        'type': 'CCVS',
        'hold_points': [
            'Hazardous materials survey completed by competent person (occupational hygienist or licensed assessor) — all ACM identified, labelled, and documented in asbestos register',
            'If ACM identified: asbestos management plan in place per WHS Regulation Chapter 8. Non-friable <10m²: Class B licence holder on site. Friable or >10m²: Class A licence holder required',
            'Air monitoring arranged for removal works per SafeWork NSW Code of Practice — clearance certificate required before general work resumes in area',
            'Workers involved in ACM work hold current asbestos awareness training (minimum) — removal workers hold appropriate licence class',
        ],
        'eng': [
            'Wet methods for all ACM disturbance — PVA spray before cutting or drilling. No power tools on ACM unless equipped with HEPA-filtered dust extraction. Containment enclosure for removal works. HEPA vacuum for clean-up — no dry sweeping.',
        ],
        'admin': [
            'Asbestos register reviewed before any cladding removal commences. Any suspected ACM tested before disturbance — presume asbestos until tested. Waste double-bagged in labelled asbestos bags, disposed of at licensed facility with tracking documentation. Clearance inspection and certificate before area released for general work.',
        ],
        'ppe': [
            'P2 respirator minimum for non-friable ACM work. Half-face P3 with particulate filter for friable ACM. Disposable Type 5/6 coveralls — removed and bagged before leaving work area. Eye protection. Cut-resistant gloves.',
        ],
        'stop_work': [
            'Suspected ACM encountered without prior identification — any ACM found friable or damaged — removal area not enclosed — air monitoring not in place — workers without appropriate training or licence — ACM waste not correctly contained — clearance certificate not obtained before area released.',
        ]
    },
}

# --- EWP STANDALONE NEW TASKS ---
EWP_NEW = {
    'ewp_selection': {
        'task': 'EWP Selection and Suitability Assessment',
        'task_desc': 'Assessment of work requirements and selection of appropriate EWP type (boom lift, scissor lift, mast lift, truck-mounted) based on reach, capacity, ground conditions, and site access constraints.',
        'hazard': 'Wrong EWP type for task — insufficient reach, capacity, or stability. Ground conditions not suitable for EWP weight. Access route inadequate for EWP dimensions.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'WAH-H6', 'resp': 'Supervisor',
        'type': 'CCVS',
        'hold_points': [
            'EWP type selected matches task requirements: working height, horizontal reach, platform capacity (workers + tools + materials), and indoor/outdoor use',
            'Ground bearing capacity confirmed adequate for EWP fully loaded weight including outriggers — geotechnical advice where ground conditions uncertain',
            'Site access assessed: delivery route, gates, ramps, overhead clearance, and storage/charging location confirmed before EWP arrives on site',
            'EWP manufacturer specifications reviewed — operating envelope, wind limits, slope limits confirmed suitable for site conditions',
        ],
        'eng': [
            'Ground preparation: compacted hardstand or steel plates under outriggers/wheels on soft ground. Overhead hazard survey: power lines, structures, tree canopy — safe clearance distances confirmed. Level/slope assessment for scissor lifts — maximum slope per manufacturer specification.',
        ],
        'admin': [
            'EWP selection documented in work plan — type, model, capacity, reach, and hire company recorded. Delivery/collection schedule coordinated with site logistics. Charging infrastructure for electric EWPs confirmed. Insurance and registration current for truck-mounted EWPs.',
        ],
        'ppe': [
            'As per EWP operation tasks below.',
        ],
        'stop_work': [
            'EWP delivered does not match specification — ground conditions not suitable — access route inadequate — overhead hazards not cleared — EWP capacity insufficient for task requirements.',
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
            'Delivery vehicle access route confirmed clear: overhead clearance, ground capacity, turning circles assessed',
            'Unloading area level, firm, and clear of workers — spotter in place during unloading',
            'Underground services confirmed clear under EWP operating position — no positioning over pits, trenches, or voids',
            'Outriggers fully deployed on firm ground or rated packing — spirit level used to confirm EWP level within manufacturer tolerance',
        ],
        'eng': [
            'Outrigger pads or steel plates sized for ground bearing capacity. Wheel chocks on trailer-mounted units. Stabiliser interlocks confirmed functional. EWP positioned on level ground — maximum slope per manufacturer specification for travel.',
        ],
        'admin': [
            'Traffic management plan if EWP positioned on road or footpath. Overnight security — keys removed, controls locked, area barricaded. Daily setup check before first use each day. Ground conditions re-assessed after rain.',
        ],
        'ppe': [
            'Hard hat and steel capped footwear during setup. High-vis vest or shirt. Cut-resistant gloves.',
        ],
        'stop_work': [
            'Ground soft or unstable — outriggers not fully deployed — EWP not level — underground services not confirmed clear — unloading area not clear of workers — stabiliser interlock not functioning.',
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
            'Pre-start checklist completed before first use each day — all items inspected and recorded',
            'Emergency lowering system tested from platform and ground controls — confirmed functional',
            'Platform guardrails, mid-rails, toe boards, and gate/chain complete and secure',
            'Hydraulic system: no leaks, hoses not abraded, fluid level correct',
        ],
        'eng': [
            'All structural pins and bolts inspected — no cracks, deformation, or missing pins. Tyres/wheels — condition and inflation correct. Battery charge adequate for planned work duration (electric units). Boom/scissor mechanism — smooth operation, no jerking or unusual noise.',
        ],
        'admin': [
            'Pre-start checklist recorded in EWP log book. Any defect: EWP locked out and tagged — not used until repaired by qualified technician. Operator familiarisation completed for EWP model — controls, capacity, wind limits. Current 10-year major inspection certificate sighted.',
        ],
        'ppe': [
            'Harness and lanyard (boom lifts) — inspected before each use. Hard hat. Steel capped footwear.',
        ],
        'stop_work': [
            'Any pre-start defect not rectified — emergency lowering not functional — guardrails incomplete — hydraulic leak — 10-year inspection overdue — operator unfamiliar with EWP model.',
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
            'Harness and short lanyard attached to designated anchor point on platform — lanyard length prevents ejection',
            'Platform load does not exceed rated capacity — workers, tools, and materials weighed/estimated and confirmed within limit',
            'Overhead power line safe approach distances confirmed — minimum distances per AS/NZS 4576 (Table 3.1)',
        ],
        'eng': [
            'Platform gate/chain closed during operation. Harness lanyard attached to manufacturer-designated anchor point only — never to guardrail. Outriggers fully deployed where fitted. Ground-level emergency controls accessible and unobstructed at all times.',
        ],
        'admin': [
            'Spotter on ground during operation near structures, overhead hazards, or in traffic areas. Communication between operator and ground crew — radio or hand signals. Wind monitoring — cease operations above 40 km/h or manufacturer limit. No modification to platform (planks, ladders, or boxes to extend reach).',
        ],
        'ppe': [
            'Full body harness (AS/NZS 1891.1) with short restraint lanyard. Hard hat — chinstrap in windy conditions. Steel capped footwear. High-vis vest or shirt.',
        ],
        'stop_work': [
            'Wind exceeds limit — operator not licenced — harness not worn or not attached — platform overloaded — approaching power lines closer than safe distance — ground conditions changed (rain, soft ground) — any mechanical, hydraulic, or electrical fault — worker attempts to climb out of platform at height.',
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
            'Operator holds current SafeWork NSW HRW licence — WP class',
            'Ground/floor surface assessed: level within manufacturer tolerance, firm, no potholes/edges/voids within travel path',
            'Platform load confirmed within rated capacity',
            'Outriggers or pothole guards deployed as required by manufacturer for operating height',
        ],
        'eng': [
            'Guardrails, mid-rails, toe boards, and gate complete. Pothole guards deployed when elevated. No travel while elevated unless manufacturer permits — and then only on confirmed level surface. Tilt alarm and cut-out functional.',
        ],
        'admin': [
            'Operating area inspected for floor openings, edges, and overhead hazards before elevating. Barricading around base if operating in traffic area. No driving near edges, ramps, or loading docks when elevated. Battery charge checked — adequate for planned duration.',
        ],
        'ppe': [
            'Hard hat. Steel capped footwear. High-vis vest or shirt. Harness and lanyard required only if manufacturer specifies or if working above guardrail height.',
        ],
        'stop_work': [
            'Ground/floor not level — pothole guards not deployed — tilt alarm sounding — operating near unprotected edge — wind exceeding manufacturer limit — any mechanical fault — operator not licenced.',
        ]
    },
    'ewp_truck': {
        'task': 'EWP Operation — Truck-Mounted / Trailer-Mounted',
        'task_desc': 'Operation of vehicle-mounted EWPs (truck-mounted boom lifts, cherry pickers, trailer-mounted units) on public roads, footpaths, and construction sites. Includes traffic management requirements.',
        'hazard': 'Vehicle instability — outrigger failure or soft ground. Traffic collision. Overhead power line contact. Pedestrian interaction on footpath. Vehicle roll-away.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'WAH-H6', 'resp': 'Supervisor / Operator',
        'type': 'CCVS',
        'hold_points': [
            'Vehicle registration and insurance current. Operator holds HRW licence (WP class) plus appropriate vehicle licence class',
            'Traffic management plan (TMP) implemented: council permit obtained, signage and cones deployed per AS 1742.3, traffic controller engaged if required',
            'Outriggers on firm ground — full deployment on all four corners. Steel plates or packing under outriggers on soft or uneven surfaces',
            'Overhead power line clearance confirmed — no operation within safe approach distance per AS/NZS 4576 without network operator approval',
        ],
        'eng': [
            'Vehicle handbrake engaged and wheel chocks in place. Outriggers fully extended and locked — level confirmed. PTO and hydraulic system pre-checked. Ground bearing capacity assessed — steel plates deployed.',
        ],
        'admin': [
            'Council road/footpath occupation permit obtained. Traffic management plan implemented — signs, cones, traffic controllers per permit conditions. Pedestrian detour in place if footpath occupied. Vehicle inspection by operator before road travel. After-hours work conditions checked if applicable.',
        ],
        'ppe': [
            'Full body harness with restraint lanyard (boom-type truck mounts). Hard hat. High-vis vest or shirt — Class D/N as required for road work. Steel capped footwear.',
        ],
        'stop_work': [
            'Outriggers not fully deployed — vehicle not level — traffic management not in place — approaching power lines — council permit not current — wind exceeds limit — pedestrians entering work zone — ground soft or unstable.',
        ]
    },
    'ewp_rescue': {
        'task': 'EWP Rescue Procedures',
        'task_desc': 'Emergency rescue of incapacitated operator from elevated EWP platform. Covers ground-level override controls, emergency lowering procedures, and medical emergency response at height.',
        'hazard': 'Delayed rescue — suspension trauma in harness (positional asphyxia). Inability to reach incapacitated operator. Ground-level controls obstructed or not functional. Medical emergency at height.',
        'risk_pre': 'High (9)', 'risk_post': 'Low (2)',
        'code': 'WAH-H9', 'resp': 'Supervisor / Worker',
        'type': 'CCVS',
        'hold_points': [
            'Ground-level emergency controls location confirmed by all crew — tested before each shift',
            'Rescue procedure rehearsed by all workers on site who may need to perform rescue — minimum quarterly practice',
            'Suspension trauma awareness: all harness wearers briefed on symptoms and relief procedures — trauma straps fitted to harnesses',
            'Emergency services contact confirmed — nearest hospital with trauma capability identified',
        ],
        'eng': [
            'Ground-level emergency lowering controls accessible and unobstructed at all times — keys available on site. Emergency lowering speed adequate to recover operator within 6 minutes of suspension onset.',
        ],
        'admin': [
            'Rescue procedure documented and displayed at EWP ground-level controls. Minimum two persons on site when EWP in use — one at ground level at all times. First aid trained person on site. Emergency lowering procedure practised at start of each new project or EWP model.',
        ],
        'ppe': [
            'Trauma straps fitted to harnesses — operator trained in self-deployment.',
        ],
        'stop_work': [
            'Ground-level controls not functional — no second person available on site — rescue procedure not rehearsed — trauma straps not fitted to harnesses — emergency lowering not tested.',
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
            ('Engineering:', 'Physical barricading around EWP operating area — mesh fence or water barriers for roadside. Outrigger visibility: reflective markers on extended outriggers. Drop zone containment — toe boards on platform, tool lanyards, no loose items on platform.'),
            ('Admin:', 'Exclusion zone maintained during operation — minimum 3m from base plus swing radius. Spotter assigned in pedestrian areas. Traffic management plan if operating on or adjacent to roadway. Communication between operator and ground crew at all times. Pedestrian detour signage if footpath blocked.'),
            ('PPE:', 'High-vis vest or shirt — Class D/N if roadside. Hard hat for all ground personnel in exclusion zone.'),
            ('STOP WORK if:', 'Pedestrians breaching exclusion zone — traffic management not in place — spotter not available in pedestrian area — barricading displaced — objects falling from platform — vehicle approaching outriggers.')
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
            'If safe approach distance cannot be maintained: line de-energisation or insulation arranged with network operator — written confirmation obtained before work commences',
            'Height limiter set on EWP to prevent approach to overhead structure where crush risk exists',
            'Spotter on ground with clear view of boom tip/platform and overhead hazards — continuous communication with operator',
        ],
        'eng': [
            'Tiger tails or visual markers on power lines where approved by network operator. Height limiter or zone restriction set on EWP where overhead structures present. Insulated platform (if available) for work near energised lines.',
        ],
        'admin': [
            'Power line safety plan documented — safe approach distances displayed at ground-level controls. All crew briefed on power line locations and safe distances before work commences. Dial Before You Dig and network operator consulted. Emergency procedure for electrical contact briefed: do not touch EWP, operator to jump clear if safe to do so, call 000.',
        ],
        'ppe': [
            'Harness and lanyard. Hard hat. Insulating gloves if working near energised equipment (by qualified electrician only). Steel capped footwear.',
        ],
        'stop_work': [
            'Safe approach distance to power line compromised — spotter not in position — power line not identified on safety plan — height limiter not set — any contact with overhead structure — platform operator cannot see boom tip.',
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
            'Outrigger pad size and material confirmed adequate for ground bearing capacity — engineering advice if soft or uncertain ground',
            'No operation over or adjacent to recent excavation, backfill, or underground void without engineering confirmation of bearing capacity',
            'After rain: ground conditions re-assessed before operation — soft areas identified and avoided or reinforced',
        ],
        'eng': [
            'Steel plates or engineered packing under outriggers on all surfaces except confirmed concrete or bitumen. Ground reinforcement (geotextile, crushed rock, or engineered platform) where soft ground and extended EWP use planned. Level monitoring — spirit level on platform checked periodically during operation.',
        ],
        'admin': [
            'Ground condition assessment documented in EWP daily log. Geotechnical advice obtained where ground conditions uncertain. Travel routes surveyed for potholes, edges, and soft spots. Drain covers and pit lids assessed for EWP wheel loads.',
        ],
        'ppe': [
            'Steel capped footwear for all ground crew. Hard hat. High-vis vest or shirt.',
        ],
        'stop_work': [
            'Outrigger sinking or ground deformation observed — EWP not level — soft ground after rain not assessed — operating over unconfirmed backfill or void — slope exceeds manufacturer tolerance — ground cracking.',
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
            'Swing stage system designed and certified by registered professional engineer — design documentation on site and current',
            'Building structural assessment completed: roof/parapet/anchor points confirmed adequate for suspension loads (dead load + live load + dynamic factors) by structural engineer',
            'Equipment certification current: all components (platform, hoist motors, wire ropes, safety devices) tested and tagged by competent person',
            'Design compliant with AS/NZS 1576.4 Scaffolding — Suspended scaffolding and AS 2550.10 Cranes — Suspended personnel platforms',
        ],
        'eng': [
            'Rated suspension points with SWL clearly marked. Wire ropes certified for breaking strain — minimum 10:1 safety factor. Hoist motors rated for platform load. Secondary safety (fall arrest) wire rope independent of working rope.',
        ],
        'admin': [
            'Engineering drawings and load tables available on site. Design review if any modification to platform size, worker numbers, or tools/materials on platform. Design verified against actual building geometry — not assumed from plans. Design engineer contact details on site for consultation.',
        ],
        'ppe': [
            'As per operation tasks below.',
        ],
        'stop_work': [
            'Engineering design not available or not current — building structural capacity not confirmed — equipment certification expired — any modification to platform not approved by design engineer — equipment damaged or not matching design specification.',
        ]
    },
    'ss_anchor': {
        'task': 'Roof Anchor and Suspension Point Setup',
        'task_desc': 'Installation, inspection, and certification of roof-mounted anchor points, parapet clamps, outrigger beams, and counterweight systems for swing stage suspension. Includes structural assessment of anchor substrates.',
        'hazard': 'Anchor failure — catastrophic platform drop. Roof edge fall during anchor installation. Incorrect counterweight calculation. Parapet or roof structure failure. Unauthorised access to roof plant area.',
        'risk_pre': 'High (9)', 'risk_post': 'Low (2)',
        'code': 'WAH-H9', 'resp': 'Lead Technician / Supervisor',
        'type': 'CCVS',
        'hold_points': [
            'Anchor point type and location per engineering design — no variation without engineer approval. Anchor substrate (concrete, steel, masonry) confirmed adequate for suspension loads',
            'Counterweight system: weight calculated per design (minimum 3:1 safety factor against overturning). Counterweights secured and cannot shift — no loose or improvised weights',
            'Outrigger beams: correct span, overhang, and bearing confirmed per design. Beams secured against lateral movement. Bearing pads on parapet/roof edge',
            'All anchor points load tested or proof-loaded before first use — test certificate on site',
        ],
        'eng': [
            'Engineered anchor points — cast-in, chemical anchor, or bolted to certified substrate. Outrigger beams spanning across building structure (not bearing on parapet only). Counterweights: purpose-built certified weights — not improvised from construction materials.',
        ],
        'admin': [
            'Roof access controlled — permit system. Fall protection in place for all workers on roof during anchor installation (harness to independent anchor, guardrails, or travel restraint). Anchor inspection by competent person before each use. Anchor point register maintained.',
        ],
        'ppe': [
            'Full body harness with fall arrest — anchored to independent point during roof work. Hard hat with chin strap. Steel capped footwear with non-slip sole. High-vis vest or shirt.',
        ],
        'stop_work': [
            'Anchor substrate cracked, spalled, or suspect — counterweight incorrect or unsecured — outrigger bearing on parapet only without structural confirmation — anchor not tested — any modification not approved by engineer — roof access uncontrolled.',
        ]
    },
    'ss_install': {
        'task': 'Swing Stage Installation and Rigging',
        'task_desc': 'Assembly of swing stage platform, connection of wire ropes to hoist motors and suspension points, installation of safety devices (overspeed governor, tilt switch, rope lock), and rigging of secondary safety lines.',
        'hazard': 'Fall during rigging at roof edge. Wire rope failure. Incorrect assembly — platform collapse. Safety device malfunction. Platform swing or spin during lowering.',
        'risk_pre': 'High (9)', 'risk_post': 'Low (2)',
        'code': 'WAH-H9', 'resp': 'Lead Technician / Supervisor',
        'type': 'CCVS',
        'hold_points': [
            'Rigging performed by workers holding Advanced Scaffolding licence (SA) and competent in suspended scaffold systems',
            'Wire ropes: correct diameter, construction, and length per design — inspected for damage, kinks, broken wires before reeving. Wire rope certificates current',
            'Safety devices installed and tested: overspeed governor, tilt switch, upper/lower limit switches, rope lock on secondary safety line — all confirmed functional before platform loaded',
            'Platform assembled per manufacturer instructions — all pins, bolts, guardrails, toe boards, and deck panels confirmed secure',
        ],
        'eng': [
            'Working rope and safety rope independently suspended — no common failure point. Rope guides installed to prevent rope snagging. Platform levelling system functional. Hoist motors tested for smooth operation — no jerking or slipping.',
        ],
        'admin': [
            'Rigging checklist completed and signed by competent person. Platform not used until competent person sign-off. Rigging inspection before each use and after any incident or weather event. Wire rope replacement schedule per manufacturer specification.',
        ],
        'ppe': [
            'Full body harness with fall arrest to independent anchor during rigging. Hard hat with chin strap. Steel capped footwear. Gloves — leather for wire rope handling.',
        ],
        'stop_work': [
            'Wire rope damaged (broken wires, kinks, corrosion) — safety device not functional — platform assembly incomplete — rigger not holding SA licence — safety rope not independent of working rope — competent person sign-off not obtained.',
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
            'Safety devices tested: overspeed governor, tilt switch, rope lock — confirmed functional',
            'Anchor points and counterweights inspected: no movement, damage, or displacement since last use',
        ],
        'eng': [
            'Hoist motors run at no-load to confirm smooth operation. Brakes tested — platform holds position when motor stopped. Platform level checked. Guardrails, toe boards, and deck panels secure.',
        ],
        'admin': [
            'Pre-start log maintained — competent person signature required. Any defect: platform locked out — not used until repaired. After storm, heavy rain, or strong wind: additional inspection before use. Weekly detailed inspection by competent person in addition to daily pre-start.',
        ],
        'ppe': [
            'Full body harness with fall arrest to independent safety line before boarding platform.',
        ],
        'stop_work': [
            'Any pre-start defect — safety device not functional — wire rope damage — anchor point movement — platform not level — hoist motor fault — brake not holding — pre-start not signed off.',
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
            'All workers on platform attached to independent safety line via full body harness and rope grab — never attached to platform structure or working rope',
            'Platform load confirmed within rated capacity before each descent — workers, tools, and materials',
            'Wind monitoring active — cease operations above 40 km/h or design limit, whichever is lower',
            'Communication system in place between platform and ground/roof crew — radio or visual signals',
        ],
        'eng': [
            'Safety line rope grab adjusted to each worker. Platform level maintained during descent — simultaneous hoist operation. Building face rollers or guide rails to prevent platform spin. Tool and material restraint on platform — nothing unsecured.',
        ],
        'admin': [
            'Maximum two workers on standard platform unless design permits more. No leaning over guardrails — work within arm reach. No jumping or sudden movements on platform. Repositioning: platform raised to roof level, moved along building face, then lowered to work position. No lateral movement while lowered.',
        ],
        'ppe': [
            'Full body harness (AS/NZS 1891.1) with rope grab on independent safety line. Hard hat with chin strap. Steel capped footwear with non-slip sole. Tool lanyard for all tools.',
        ],
        'stop_work': [
            'Worker not attached to safety line — platform overloaded — wind exceeds limit — platform not level (differential >150mm) — platform spinning or swinging uncontrolled — communication with ground/roof lost — hoist motor fault — any safety device activation.',
        ]
    },
    'ss_rescue': {
        'task': 'Swing Stage Rescue Procedures',
        'task_desc': 'Emergency rescue of incapacitated worker from suspended swing stage platform. Covers rescue from platform, rescue from safety line (suspended in harness), and medical emergency at height.',
        'hazard': 'Suspension trauma (positional asphyxia) — onset within 5 minutes of suspension in harness. Delayed rescue. Platform inaccessible from ground. Multiple casualty scenario.',
        'risk_pre': 'High (9)', 'risk_post': 'Low (2)',
        'code': 'WAH-H9', 'resp': 'Supervisor / Lead Technician',
        'type': 'CCVS',
        'hold_points': [
            'Rescue plan documented and specific to this swing stage installation — not generic. Plan covers: rescue from platform, rescue of worker suspended on safety line, and medical emergency at height',
            'Rescue equipment on site and accessible: second means of access to platform height (adjacent building access, EWP on standby, or rope rescue capability)',
            'All crew trained in rescue procedure and rehearsed at project commencement — rescue drill completed and recorded',
            'Suspension trauma awareness: trauma straps fitted to all harnesses, all workers briefed on self-deployment and symptoms',
        ],
        'eng': [
            'Emergency lowering by platform hoist — operable from ground level. If hoist fails: alternative rescue method (rope rescue, EWP, or adjacent access) available within 6 minutes. Trauma straps on all harnesses.',
        ],
        'admin': [
            'Rescue procedure displayed at ground level and on platform. Minimum two persons on site when swing stage in use — one at ground level. Emergency services pre-notified of swing stage work (location, height, access). First aid trained person on site.',
        ],
        'ppe': [
            'Trauma straps fitted and deployed. Rescue harness for rescuer if rope rescue method used.',
        ],
        'stop_work': [
            'Rescue plan not documented — rescue drill not completed — no second means of access available — trauma straps not fitted — solo worker on swing stage — emergency lowering not functional — first aid not available on site.',
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
            ('Engineering:', 'Anemometer (wind speed meter) on platform or at working height — continuous reading visible to operator. Platform tie-off points for securing to building face in high wind. Wire ropes and platform secured when not in use.'),
            ('Admin:', 'Wind limits documented and briefed to all crew: sustained >40 km/h or gusts >50 km/h — cease operations and secure platform. BOM weather forecast checked before each shift. Lightning: cease operations immediately, lower platform to ground, all workers off roof and platform. Rain: assess slip risk, reduce operations if platform slippery. Daily wind monitoring log recorded.'),
            ('PPE:', 'Wet weather gear if operating in light rain. Non-slip footwear.'),
            ('STOP WORK if:', 'Wind sustained >40 km/h or gusts >50 km/h — lightning detected within 10km — heavy rain reducing visibility — storm warning issued — wind direction change causing platform instability — operator feels unsafe due to weather conditions.')
        ]
    },
    'ss_exclusion': {
        'task': 'Exclusion Zone and Drop Zone Management',
        'task_desc': 'Establishment and maintenance of exclusion zones below and around swing stage operations to protect ground-level workers, residents, and public from falling objects and equipment.',
        'hazard': 'Falling tools, materials, or debris from platform. Wire rope or equipment failure — falling components. Platform swing path at ground level. Unauthorised access to exclusion zone.',
        'risk_pre': 'Medium (3)', 'risk_post': 'Low (1)',
        'code': 'SYS-M3', 'resp': 'Supervisor / Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Physical barricading of exclusion zone: mesh fence, water barriers, or hoarding — not tape alone. Catch platform or fan at occupied building entries if within drop zone. Scaffold netting on platform perimeter. Tool lanyards for all hand tools on platform.'),
            ('Admin:', 'Exclusion zone extends minimum 3m from platform edge plus the lesser of half the platform height or 6m (per SafeWork NSW guidance). Signage: "Danger — Overhead Work — No Entry". Resident/public notification before commencement. Spotter at ground level if pedestrians near exclusion zone. No material throwing or dropping from platform.'),
            ('PPE:', 'Hard hat for all persons within or adjacent to exclusion zone.'),
            ('STOP WORK if:', 'Exclusion zone breached — barricading displaced — tool or material dropped from platform — pedestrians or residents in drop zone — signage removed.')
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
            'Electrical survey completed: all building-mounted and adjacent electrical hazards identified — external lighting, power points, conduit, switchboards, and overhead lines mapped',
            'Energised equipment within platform travel path: de-energised and locked out by licensed electrician, or physical protection installed to prevent contact',
            'Overhead power lines: safe approach distances confirmed per AS/NZS 4576 — platform travel limits set to prevent approach',
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
            'Electrical hazard not identified on survey — energised equipment in platform path not isolated — wire rope approaching power line — wet conditions and exposed wiring — electrical contact of any kind.',
        ]
    },
}

# --- ABRASIVE BLASTING NEW TASKS ---
BLASTING_NEW = {
    'blast_setup': {
        'task': 'Blasting Equipment Setup — Compressor, Pot, Lines',
        'task_desc': 'Setup, commissioning, and operation of abrasive blasting equipment including air compressor, blast pot (pressure vessel), blast hoses, nozzles, moisture separators, and dead-man controls.',
        'hazard': 'High-pressure air release — hose whip. Pressure vessel failure. Noise from compressor and blasting. Hose connection failure. Dead-man control malfunction — uncontrolled blast.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'PRE-H6', 'resp': 'Supervisor / Blaster',
        'type': 'CCVS',
        'hold_points': [
            'Blast pot (pressure vessel) has current registration and inspection certificate per WHS Regulation Chapter 5 — Plant',
            'All hose connections fitted with safety clips/whip checks — dead-man control fitted to nozzle and tested functional',
            'Compressor capacity matched to nozzle size — correct operating pressure set and pressure relief valve functional',
            'Operator holds demonstrated competence in abrasive blasting equipment operation — training records sighted',
        ],
        'eng': [
            'Whip checks on all hose connections. Safety pins/clips on all couplings. Dead-man handle on nozzle — blast stops within 1 second of release. Moisture separator and air dryer in line. Pressure relief valve set to maximum operating pressure. Earthing/bonding of all metallic components to prevent static discharge.',
        ],
        'admin': [
            'Equipment pre-start inspection completed and recorded. Hoses inspected full length — no damage, kinks, or excessive wear. Nozzle bore checked — replaced when worn beyond 20% of original diameter. Compressor maintenance log current. Exclusion zone around compressor — noise and exhaust fumes.',
        ],
        'ppe': [
            'Hearing protection (>85 dB, Class 5) near compressor. Steel capped footwear. Eye protection during setup.',
        ],
        'stop_work': [
            'Pressure vessel registration expired — dead-man control not functional — hose damage or coupling failure — pressure relief valve not working — whip checks missing — operator not competent.',
        ]
    },
    'blast_open': {
        'task': 'Abrasive Blasting Operations — Open Air',
        'task_desc': 'Abrasive blasting of surfaces in open-air conditions using garnet, glass bead, steel shot, crushed slag, or soda media. Includes surface preparation to specified profile for coating application.',
        'hazard': 'Respirable dust — silicosis (if silica media used), general respiratory hazard from all media. Noise >115 dB(A). Ricochet — high-velocity particles. Skin abrasion from blast media. Dust affecting adjacent properties and persons.',
        'risk_pre': 'High (6)', 'risk_post': 'Low (2)',
        'code': 'SIL-H6', 'resp': 'Supervisor / Blaster',
        'type': 'CCVS',
        'hold_points': [
            'Blast media confirmed: NO free silica content (crystalline silica banned for abrasive blasting per WHS Regulation). Material safety data sheet confirms silica-free',
            'Air monitoring plan in place: personal and boundary monitoring for respirable dust. Monitoring results reviewed by occupational hygienist',
            'Containment assessed: full containment if within 50m of occupied premises, public areas, or sensitive environments. Partial containment where open-air blasting is practicable',
            'All workers within 15m of blasting operations wearing appropriate respiratory protection',
        ],
        'eng': [
            'Blast containment: tarps, mesh screens, or full enclosure depending on location and media. Dust suppression: wet blasting (vapour blasting) where practicable to reduce airborne dust. Media recovery system where possible — vacuum or sweep recovery. Blast area physically barricaded — minimum 10m exclusion zone.',
        ],
        'admin': [
            'Blast plan documented: surface area, media type and consumption, profile required, containment method, waste disposal. Neighbours notified 48 hours before blasting commences. Blast times restricted per council/permit conditions — typically 7am–5pm. Dust monitoring results actioned same day — work adjusted if results exceed exposure standards. Post-blast surface profile checked with comparator gauge.',
        ],
        'ppe': [
            'Blaster: AS/NZS 1337-approved blast helmet with supplied air (Class 2B minimum), leather blast suit, leather gloves, steel capped boots. Assistants within 15m: half-face P3 respirator, eye protection, hearing protection (>85 dB, Class 5), long sleeves.',
        ],
        'stop_work': [
            'Silica-containing media identified — air monitoring exceeds exposure standard — containment failure — dust escaping to adjacent properties — dead-man control malfunction — supplied air system fault — blast helmet visor damaged — wind exceeds containment capability.',
        ]
    },
    'blast_enclosed': {
        'task': 'Abrasive Blasting — Enclosed/Contained Environment',
        'task_desc': 'Abrasive blasting inside containment enclosures, blast rooms, tanks, or confined structures. Includes ventilation, visibility, and confined space management.',
        'hazard': 'Extreme dust concentration in enclosed space. Reduced visibility — zero visibility common. Noise amplification in enclosure. Oxygen depletion. Confined space hazards. Heat stress inside blast suit.',
        'risk_pre': 'High (9)', 'risk_post': 'Low (2)',
        'code': 'HAZ-H9', 'resp': 'Supervisor / Blaster',
        'type': 'CCVS',
        'hold_points': [
            'Enclosed blasting ventilation system operational: negative pressure maintained within enclosure, exhaust air filtered before discharge. Minimum 20 air changes per hour',
            'Confined space assessment completed if applicable per WHS Regulation Chapter 4 Part 4.3 — entry permit system in place',
            'Supplied air breathing apparatus confirmed: air quality tested (Grade D breathing air), flow rate adequate, emergency air reserve available',
            'Communication system between blaster inside enclosure and standby person outside — tested before entry. Standby person remains at entry point at all times',
        ],
        'eng': [
            'Extraction ventilation with HEPA filtration — negative pressure prevents dust escape. Lighting rated for hazardous atmosphere if combustible media. Emergency air supply — minimum 10 minutes reserve. Blast containment sealed — no gaps allowing dust escape.',
        ],
        'admin': [
            'Maximum continuous blast time per session — heat stress management. Work/rest rotation schedule. Visibility check — cease blasting if visibility <1m and allow dust to settle. Dust monitoring inside and outside containment. Emergency extraction procedure rehearsed.',
        ],
        'ppe': [
            'Blaster: Type CE supplied-air blast helmet with positive pressure, full leather blast suit, leather gauntlet gloves, steel capped boots, hearing protection (>85 dB). Standby person: half-face P3 respirator, hearing protection (>85 dB), eye protection.',
        ],
        'stop_work': [
            'Ventilation system fails — positive pressure in helmet lost — air supply quality alarm — visibility zero for >5 minutes — confined space entry permit not current — standby person leaves position — heat stress symptoms — enclosure seal breached — dust escaping containment.',
        ]
    },
    'blast_media': {
        'task': 'Blast Media Selection and Handling',
        'task_desc': 'Selection, storage, handling, and loading of abrasive blast media including garnet, glass bead, steel shot, soda, and crushed slag. Includes media quality control and waste management.',
        'hazard': 'Manual handling of heavy media bags (25–50kg). Dust during loading and handling. Contaminated recycled media. Slip hazard from spilled media. Eye injury from loose particles.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'HAZ-M4', 'resp': 'Worker / Sub-Contract Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Bulk media delivery where possible — hopper or silo feed to blast pot. Mechanical lifting for bags >25kg. Dust extraction at blast pot loading point. Media storage on pallets, covered, and dry.'),
            ('Admin:', 'Media SDS reviewed — confirm no free crystalline silica. Media specification matches coating manufacturer requirements — type, particle size, hardness confirmed. Recycled media tested for contamination before re-use (lead, asbestos, other hazardous coatings). Waste media classified per EPA guidelines — disposal to licensed facility if contaminated.'),
            ('PPE:', 'P2 dust mask during loading and handling. Eye protection. Cut-resistant gloves. Steel capped footwear.'),
            ('STOP WORK if:', 'Media contains free silica — recycled media contaminated — media wet or clumped — SDS not available — manual handling of >25kg bags without mechanical aids.')
        ]
    },
    'blast_containment': {
        'task': 'Containment and Environmental Controls',
        'task_desc': 'Erection, maintenance, and removal of blast containment systems including full enclosures, tarps, screens, and environmental protection measures for dust, noise, and waste.',
        'hazard': 'Containment failure — dust release to environment. Working at height during containment erection. Wind damage to containment. Stormwater contamination from blast waste. Community complaint.',
        'risk_pre': 'Medium (4)', 'risk_post': 'Low (2)',
        'code': 'ENV-M4', 'resp': 'Supervisor / Worker',
        'type': 'STD',
        'control': [
            ('Engineering:', 'Containment structure designed for wind loading — secured to scaffold or independent frame. Containment sealed at all joints — overlap and tape/clamp. Stormwater protection: bunding around blast area, drain covers within 10m. Waste collection system within containment — prevent media and coating waste reaching ground/stormwater.'),
            ('Admin:', 'Environmental management plan reviewed — containment method per EPA and council requirements. Boundary dust monitoring during blasting — results compared against PM10 criteria. Noise monitoring at site boundary. Containment inspected daily — repairs before blasting resumes. Waste manifest maintained — media, coating waste, and contaminated water tracked from generation to disposal.'),
            ('PPE:', 'As per blasting tasks.'),
            ('STOP WORK if:', 'Containment breach — dust visible outside containment — boundary monitoring exceeds criteria — wind damaging containment — stormwater contamination — community complaint not resolved.')
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
            'Air monitoring plan developed by occupational hygienist — personal and boundary monitoring locations and frequency specified',
            'Baseline coating analysis completed before blasting: tested for lead, asbestos, chromium, and other hazardous substances. Results reviewed and control measures adjusted accordingly',
            'If lead detected: lead risk assessment per WHS Regulation Chapter 7 Part 7.2. Blood lead monitoring program in place for workers',
            'Dust monitoring results reviewed same-day — exceedance triggers immediate cessation and control review',
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
            'Monitoring exceeds WES — lead or asbestos detected in coating without prior assessment — monitoring equipment fault — supplied air quality test failed — dust escaping containment boundary.',
        ]
    },
    'lead_blasting': {
        'task': 'Lead Paint and Hazardous Coating Removal by Blasting',
        'task_desc': 'Removal of lead-containing paint and other hazardous coatings by abrasive blasting. Includes full containment, air monitoring, worker health surveillance, and hazardous waste disposal requirements.',
        'hazard': 'Lead dust and fume inhalation — lead poisoning. Lead contamination of site and surrounds. Asbestos co-contamination in old coatings. Hazardous waste generation. Worker take-home contamination.',
        'risk_pre': 'High (9)', 'risk_post': 'Low (2)',
        'code': 'HAZ-H9', 'resp': 'Supervisor / Blaster / Occupational Hygienist',
        'type': 'CCVS',
        'hold_points': [
            'Lead risk assessment completed per WHS Regulation Chapter 7 Part 7.2 — lead content of coating quantified by laboratory analysis',
            'Full containment required: Class 1 enclosure with negative pressure ventilation and HEPA filtration per AS 4361.2',
            'Worker health surveillance: blood lead levels tested before commencement and at intervals per WHS Regulation. Workers with blood lead >20 µg/dL reviewed by medical practitioner',
            'Decontamination facility established: three-stage decontamination unit for workers exiting containment (dirty, shower, clean)',
        ],
        'eng': [
            'Full containment enclosure with negative pressure — minimum 4 Pascal negative pressure maintained and continuously monitored. HEPA filtration on exhaust. Decontamination shower unit at enclosure exit. Wet methods supplementary to containment — water injection at nozzle.',
        ],
        'admin': [
            'Lead removal work plan documented — approved by occupational hygienist. Clearance air monitoring before enclosure dismantled — results below clearance criteria. Waste classified as hazardous — double-bagged, labelled, and disposed of at licensed facility with EPA tracking. Decontamination procedure: workers shower and change clothes before leaving site — no work clothes worn home. Laundry service for work clothes provided.',
        ],
        'ppe': [
            'Supplied-air blast helmet (minimum Class 2B). Disposable coveralls removed and bagged before decontamination. Nitrile gloves under leather blast gloves. Steel capped boots dedicated to blast work — left on site.',
        ],
        'stop_work': [
            'Containment pressure loss — air monitoring exceeds WES — blood lead level exceeds action level — decontamination facility not functional — HEPA filter not changed per schedule — waste not correctly contained — any containment breach.',
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
            ('Engineering:', 'Compressor positioned maximum distance from occupied areas — exhaust directed away. Noise attenuation on compressor where available. Blast nozzle selection for minimum noise — venturi nozzles quieter than straight bore. Containment enclosure provides noise reduction to surrounds.'),
            ('Admin:', 'Noise assessment completed — personal exposure levels documented. Hearing conservation program in place if exposure >85 dB(A) 8hr TWA: audiometric testing baseline and annual. Work hours restricted per council/EPA noise conditions — typically 7am–5pm. Noise monitoring at site boundary if near residential. Communication in blast zone: hand signals or radio — verbal communication not possible.'),
            ('PPE:', 'Class 5 hearing protection (>85 dB) minimum for blaster and assistants. Dual protection (plugs + muffs) where exposure >100 dB(A). Hearing protection (>85 dB) for all workers within 15m of blasting operations.'),
            ('STOP WORK if:', 'Worker not wearing hearing protection (>85 dB) in blast zone — noise monitoring exceeds council limits at boundary — audiometric testing shows threshold shift — communication system failure in blast zone.')
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
print(f"  TOTAL: {len(REMEDIAL_NEW)+len(SPRAY_NEW)+len(GROUND_NEW)+len(CLADDING_NEW)+len(EWP_NEW)+len(SWING_NEW)+len(BLASTING_NEW)} new tasks")

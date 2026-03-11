#!/usr/bin/env python3
"""
renderers/docx_renderer.py — TaskBlock -> .docx bytes

Builds a SWMS Word table (header + data row) plus optional monitoring table.
A4 landscape, 1cm margins, Aptos 8pt throughout.

Uses RPD-MSW-002 as template base — inherits style "a" (single spacing,
zero margins). All borders use dotted grey matching RPD document pattern.
No amber fill on data rows. Risk cells Aptos 10pt bold.
"""

import os
import sys
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt, RGBColor
from lxml import etree

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.schema import TaskBlock, MonitoringEntry

# ── Constants ─────────────────────────────────────────────────────────────────────────────

FONT      = "Aptos"
FONT_SIZE = Pt(8)
RED       = RGBColor(0xC0, 0x00, 0x00)
BLACK     = RGBColor(0x00, 0x00, 0x00)
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
GREY      = RGBColor(0x44, 0x44, 0x44)

# ── Field placeholder fallback ────────────────────────────────────────────────────────────

FIELD_PLACEHOLDERS = {
    'pcbu_name':            '[Insert PCBU here]',
    'manager_name':         '[Insert Manager name here]',
    'project_address':      '[Insert Site Address Here]',
    'description':          '[Insert description here]',
    'principal_contractor': '[Insert Principal Contractor Name Here]',
    'supervisor_name':      '[Insert Supervisor name here]',
    'reviewer_name':        '[Insert Manager name here]',
    'work_activity':        '[Insert work activity here]',
    'swms_date':            None,  # use today's date — never placeholder
}


def resolve_field(value: str, field_key: str) -> tuple[str, bool]:
    """
    Returns (text_to_render, is_placeholder).
    Caller applies italic formatting if is_placeholder is True.
    """
    if value and value.strip():
        return value.strip(), False
    if field_key == 'swms_date':
        from datetime import date
        return date.today().strftime('%d/%m/%Y'), False
    placeholder = FIELD_PLACEHOLDERS.get(field_key, '[Insert here]')
    return placeholder, True


def _summarise_work_activity(text: str, max_lines: int = 8, max_chars: int = 800) -> str:
    """Truncate work activity text to max_lines / max_chars.
    Cuts at last full stop within the limit — never mid-sentence."""
    result = text.strip()
    # Cap lines first
    lines = result.split("\n")
    if len(lines) > max_lines:
        result = "\n".join(lines[:max_lines])
    # Cap chars at last full stop
    if len(result) > max_chars:
        truncated = result[:max_chars]
        last_stop = truncated.rfind(".")
        result = truncated[:last_stop + 1] if last_stop > 0 else truncated.rsplit(" ", 1)[0]
    return result


# ── Text sanitisation — catches duplicate tokens before they reach the document ──
_DUPLICATE_TOKENS = [
    ("steel-capped steel-capped", "steel-capped"),
    ("cut-resistant cut-resistant", "cut-resistant"),
    ("high-visibility high-visibility", "high-visibility"),
    ("chemical-resistant chemical-resistant", "chemical-resistant"),
    ("  ", " "),
]

import re as _re_audit
_AUDIT_PATTERN = _re_audit.compile(r'AUDIT:\s*[\w\-|,\s]+$', _re_audit.MULTILINE)

def sanitise_text(text: str) -> str:
    """Remove duplicate tokens, double spaces, and legacy AUDIT metadata from generated text."""
    # Strip legacy AUDIT: metadata lines
    text = _AUDIT_PATTERN.sub('', text).strip()
    for bad, good in _DUPLICATE_TOKENS:
        while bad in text:
            text = text.replace(bad, good)
    return text

# ── CCVS code validator ──────────────────────────────────────────────────────
import re as _re_ccvs

_VALID_CCVS_STREAMS = [
    'WFR', 'WFA', 'WAH', 'IRA', 'ELE', 'SIL', 'STR', 'CFS',
    'ENE', 'HOT', 'MOB', 'ASB', 'LED', 'TRF', 'ENV', 'CHM',
    'SCF', 'CRN', 'EXC', 'MNH', 'NOI', 'TLT', 'DEM', 'FMW',
]
_VALID_CCVS_PATTERN = _re_ccvs.compile(
    r'^(' + '|'.join(_VALID_CCVS_STREAMS) + r')-(H6|H9|M3|M4|L1|L2)$'
)

def validate_ccvs_code(code: str) -> str:
    """Normalise and validate a CCVS code. Fixes missing hyphen."""
    if not code or code == 'N/A':
        return 'N/A'
    if _VALID_CCVS_PATTERN.match(code):
        return code
    upper = code.upper().strip()
    for stream in _VALID_CCVS_STREAMS:
        if upper.startswith(stream):
            suffix = upper[len(stream):].lstrip('- ')
            repaired = f"{stream}-{suffix}"
            if _VALID_CCVS_PATTERN.match(repaired):
                return repaired
    import logging
    logging.warning(f"Invalid CCVS code could not be repaired: {repr(code)}")
    return 'N/A'

BLUE   = "DBE5F1"
RED_BG = "FF0000"
YLW_BG = "FFFF00"
GRN_BG = "00FF00"

_USABLE_CM   = 27.7
_COL_PCT     = [10, 15, 8, 35, 8, 14, 10]
_COL_W       = [_USABLE_CM * p / 100 for p in _COL_PCT]
_HEADERS     = ["Task", "Hazard", "Risk\n(Pre)", "Controls", "Risk\n(Post)", "Responsibility", "CCVS\nCode"]
_MON_PCT     = [16, 28, 14, 14, 28]
_MON_W       = [_USABLE_CM * p / 100 for p in _MON_PCT]
_MON_HEADERS = ["Task", "Critical Control", "Who Checks", "How Often", "What They Look For"]

# ── XML fragments ──────────────────────────────────────────────────────────────────

_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

_BORDER_TBL = (
    '<w:tblBorders {ns}>'
    '<w:top    w:val="dotted" w:sz="6" w:space="0" w:color="808080"/>'
    '<w:left   w:val="dotted" w:sz="4" w:space="0" w:color="A6A6A6"/>'
    '<w:bottom w:val="dotted" w:sz="6" w:space="0" w:color="808080"/>'
    '<w:right  w:val="dotted" w:sz="4" w:space="0" w:color="A6A6A6"/>'
    '<w:insideH w:val="dotted" w:sz="4" w:space="0" w:color="A6A6A6"/>'
    '<w:insideV w:val="dotted" w:sz="4" w:space="0" w:color="A6A6A6"/>'
    '</w:tblBorders>'
).format(ns=_NS)

_LOOK = (
    '<w:tblLook {ns} w:val="0000" w:firstRow="0" w:lastRow="0" '
    'w:firstColumn="0" w:lastColumn="0" w:noHBand="0" w:noVBand="0"/>'
).format(ns=_NS)

_SPACING = '<w:spacing {ns} w:line="240" w:lineRule="auto"/>'.format(ns=_NS)

# ── Helpers ──────────────────────────────────────────────────────────────────────────────

def _shade(cell, hex_color: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    for e in tcPr.findall(qn("w:shd")):
        tcPr.remove(e)
    tcPr.append(parse_xml(
        '<w:shd {ns} w:val="clear" w:color="auto" w:fill="{c}"/>'.format(ns=_NS, c=hex_color)
    ))

def _fix_spacing(para) -> None:
    pPr = para._p.get_or_add_pPr()
    for s in pPr.findall(qn("w:spacing")):
        pPr.remove(s)
    pPr.append(parse_xml(_SPACING))

def _run(para, text: str, bold=False, color: RGBColor = None,
         size_pt: int = 8, highlight: bool = False) -> None:
    run = para.add_run(sanitise_text(text))
    run.font.name = FONT
    run.font.size = Pt(size_pt)
    run.bold = bold
    if color:
        run.font.color.rgb = color
    if highlight:
        rpr = run._r.get_or_add_rPr()
        hl = etree.SubElement(rpr, qn("w:highlight"))
        hl.set(qn("w:val"), "yellow")
    _fix_spacing(para)

def _format_table(table) -> None:
    """Apply style a, dotted grey borders, fixed layout, disabled tblLook."""
    tbl = table._tbl
    tblPr = tbl.find(qn("w:tblPr"))
    if tblPr is None:
        tblPr = parse_xml('<w:tblPr {ns}/>'.format(ns=_NS))
        tbl.insert(0, tblPr)
    for tag in ("w:tblStyle", "w:tblLook", "w:tblBorders", "w:tblLayout"):
        for el in tblPr.findall(qn(tag)):
            tblPr.remove(el)
    tblPr.insert(0, parse_xml('<w:tblStyle {ns} w:val="a"/>'.format(ns=_NS)))
    tblPr.append(parse_xml(_BORDER_TBL))
    tblPr.append(parse_xml('<w:tblLayout {ns} w:type="fixed"/>'.format(ns=_NS)))
    tblPr.append(parse_xml(_LOOK))
    for row in table.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                _fix_spacing(para)

def _add_section_rule(para) -> None:
    """Dotted grey top rule between Controls sections."""
    ppr = para._p.get_or_add_pPr()
    for e in ppr.findall(qn("w:pBdr")):
        ppr.remove(e)
    ppr.append(parse_xml(
        '<w:pBdr {ns}>'
        '<w:top w:val="dotted" w:sz="4" w:space="1" w:color="A6A6A6"/>'
        '</w:pBdr>'.format(ns=_NS)
    ))

# ── Cell builders ───────────────────────────────────────────────────────────────────────

def _header_cell(cell, text: str, size_pt: int = 8) -> None:
    _shade(cell, BLUE)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(p, text, bold=True, size_pt=size_pt)

def _risk_cell(cell, text: str, size_pt: int = 10) -> None:
    s = text.strip()
    # Expand single-letter codes to full words
    _RISK_LABELS = {
        "H": "High", "M": "Medium", "L": "Low",
        "High": "High", "Medium": "Medium", "Low": "Low",
    }
    # Handle formats like "H", "High", "High(6)", "M" etc.
    key = s.split("(")[0].strip()
    label = _RISK_LABELS.get(key, s)
    # Preserve score suffix if present e.g. "High(6)"
    if "(" in s:
        label = label + s[s.index("("):]

    if label.startswith("High"):     bg, fg = RED_BG, WHITE
    elif label.startswith("Medium"): bg, fg = YLW_BG, BLACK
    else:                            bg, fg = GRN_BG, BLACK
    _shade(cell, bg)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(p, label, bold=True, color=fg, size_pt=size_pt)

def _set_table_cell_margins(table, top=0, start=108, bottom=0, end=108):
    """Set uniform cell margins on every cell in a table. Values in DXA."""
    tbl = table._tbl
    tblPr = tbl.find(qn('w:tblPr'))
    if tblPr is None:
        tblPr = OxmlElement('w:tblPr')
        tbl.insert(0, tblPr)
    for existing in tblPr.findall(qn('w:tblCellMar')):
        tblPr.remove(existing)
    tblCellMar = OxmlElement('w:tblCellMar')
    for side, val in [('top', top), ('start', start),
                      ('bottom', bottom), ('end', end)]:
        node = OxmlElement(f'w:{side}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tblCellMar.append(node)
    tblPr.append(tblCellMar)


def _strip_para_indent(para) -> None:
    """Remove any explicit indent from a paragraph so it inherits cell margin."""
    para.paragraph_format.left_indent = None
    para.paragraph_format.first_line_indent = None
    pPr = para._p.find(qn('w:pPr'))
    if pPr is not None:
        for ind in pPr.findall(qn('w:ind')):
            pPr.remove(ind)


def _clear_cell_default_indent(cell) -> None:
    """Remove any default indent from cell paragraphs so bullet indent sticks."""
    tc = cell._tc
    for p in tc.findall('.//' + qn('w:p')):
        pPr = p.find(qn('w:pPr'))
        if pPr is not None:
            for ind_el in pPr.findall(qn('w:ind')):
                pPr.remove(ind_el)


def _apply_bullet_indent(para) -> None:
    """Set hanging indent on paragraph via XML + paragraph_format.

    Pt(18) = 360 DXA left, Pt(-9) = -180 DXA first_line (= hanging 180).
    Bullet at 180 DXA, text starts at 360 DXA, wrapped lines return to 360.
    """
    pPr = para._p.get_or_add_pPr()
    # Remove pStyle so cell default style cannot override
    for ps in pPr.findall(qn('w:pStyle')):
        pPr.remove(ps)
    # Clear any existing indent
    for existing in pPr.findall(qn('w:ind')):
        pPr.remove(existing)
    ind = OxmlElement('w:ind')
    ind.set(qn('w:left'), '360')
    ind.set(qn('w:hanging'), '180')
    pPr.append(ind)
    # Also set via paragraph_format (these produce identical DXA values)
    para.paragraph_format.left_indent = Pt(18)
    para.paragraph_format.first_line_indent = Pt(-9)


def _write_bullet_para(cell, text: str, size_pt: int = 9, bold: bool = False,
                       color: RGBColor = None, highlight: bool = False,
                       first: bool = False, rule: bool = False):
    """Write a single bullet paragraph with correct hanging indent.

    Nuclear approach: clears paragraph style, sets indent via XML AND
    paragraph_format, re-applies indent after adding runs.
    left=360 DXA, hanging=180 DXA.
    """
    para = cell.paragraphs[0] if first else cell.add_paragraph()

    if rule:
        _add_section_rule(para)

    # 1. Clear paragraph style so cell default cannot override
    pPr = para._p.get_or_add_pPr()
    for ps in pPr.findall(qn('w:pStyle')):
        pPr.remove(ps)

    # 2. Set indent BEFORE adding runs
    _apply_bullet_indent(para)

    # 3. Set spacing
    for sp in pPr.findall(qn('w:spacing')):
        pPr.remove(sp)
    pPr.append(parse_xml(
        '<w:spacing {ns} w:before="0" w:after="20" w:line="240" w:lineRule="auto"/>'.format(ns=_NS)
    ))

    # 4. Bullet run (two spaces after bullet)
    bullet_run = para.add_run('\u2022  ')
    bullet_run.font.name = FONT
    bullet_run.font.size = Pt(size_pt)
    bullet_run.bold = bold

    # 5. Text run
    text_run = para.add_run(text)
    text_run.font.name = FONT
    text_run.font.size = Pt(size_pt)
    text_run.bold = bold
    if color:
        text_run.font.color.rgb = color
    if highlight:
        rPr = text_run._r.get_or_add_rPr()
        hl = OxmlElement('w:highlight')
        hl.set(qn('w:val'), 'yellow')
        rPr.append(hl)

    # 6. Re-apply indent AFTER runs (in case adding runs reset it)
    _apply_bullet_indent(para)

    return para


import re as _re

_STOP_WORK_PREFIX = _re.compile(
    r"^(\U0001f6d1\s*)?STOP\s+WORK\s+(if\s*:\s*)?",
    _re.IGNORECASE,
)

_HOLD_POINT_PREFIX = _re.compile(
    r"^(\u26a0\ufe0f?\s*)?HOLD\s+POINT\s*(\u2014\s*)?(do\s+not\s+\w+\s+until\s*:\s*)?",
    _re.IGNORECASE,
)


def _strip_stop_work_label(text: str) -> str:
    """Remove leading '🛑 STOP WORK if:' from a bullet item."""
    cleaned = _STOP_WORK_PREFIX.sub("", text).strip()
    # Capitalise first letter
    return cleaned[0].upper() + cleaned[1:] if cleaned else text


def _strip_hold_point_label(text: str) -> str:
    """Remove leading '⚠️ HOLD POINT — do not X until:' from a bullet item."""
    cleaned = _HOLD_POINT_PREFIX.sub("", text).strip()
    return cleaned[0].upper() + cleaned[1:] if cleaned else text


def _hazard_cell(cell, task: TaskBlock, size_pt: int = 8) -> None:
    """Populate hazard column with bulleted hazard items."""
    _clear_cell_default_indent(cell)
    # Gather hazard items — split any compound items on comma/semicolon
    raw_items = task.hazards if task.hazards else [task.scope or ""]
    items = []
    for raw in raw_items:
        # Split on semicolons or commas followed by a capital letter (new hazard)
        parts = _re.split(r'[;]\s*|\n', raw)
        for part in parts:
            stripped = part.strip()
            if stripped:
                items.append(stripped)
    # Write each hazard as a bulleted paragraph
    for hi, haz in enumerate(items):
        _write_bullet_para(cell, haz, size_pt=size_pt, first=(hi == 0))


def _controls_cell(cell, task: TaskBlock, size_pt: int = 8) -> None:
    _clear_cell_default_indent(cell)
    first = [True]

    def _label(text, bold=False, color=None, highlight=False, rule=False):
        """Write a non-bullet label paragraph (Engineering:, Admin:, etc.)."""
        if first[0]:
            p = cell.paragraphs[0]
            first[0] = False
        else:
            p = cell.add_paragraph()
        if rule:
            _add_section_rule(p)
        _run(p, text, bold=bold, color=color, highlight=highlight, size_pt=size_pt)

    def _bullet(text, rule=False):
        """Write a bullet item using _write_bullet_para."""
        first[0] = False  # never use paragraphs[0] after first label
        _write_bullet_para(cell, text, size_pt=size_pt, rule=rule)

    # Engineering: header always first
    _label("Engineering:", bold=True)
    if task.controls:
        for item in task.controls:
            _bullet(item)
    else:
        _bullet("Refer to site-specific risk assessment")

    # Admin
    if task.admin:
        _label("Admin:", bold=True, rule=True)
        for item in task.admin:
            _bullet(item)

    # PPE
    if task.ppe:
        _label("PPE:", bold=True, rule=True)
        for item in task.ppe:
            _bullet(item)

    # Hold points
    if task.hold_points:
        _label(
            "\u26a0\ufe0f HOLD POINT \u2014 do not start until:",
            bold=True, highlight=True, rule=True,
        )
        for item in task.hold_points:
            _bullet(_strip_hold_point_label(item))

    # Stop work
    if task.stop_work:
        _label(
            "\U0001f6d1 STOP WORK if:",
            bold=True, color=RED, highlight=True, rule=True,
        )
        for item in task.stop_work:
            _bullet(_strip_stop_work_label(item))

def _responsibility_cell(cell, task: TaskBlock, size_pt: int = 8) -> None:
    _clear_cell_default_indent(cell)
    is_first = True
    for role, obligation in task.responsibility.items():
        text = role
        if obligation:
            text += " \u2014 %s" % obligation
        _write_bullet_para(cell, text, size_pt=size_pt, bold=False, first=is_first)
        # Make the role portion bold by modifying the text run we just created
        para = cell.paragraphs[0] if is_first else cell.paragraphs[-1]
        # The text run is the last run; replace it with bold role + normal obligation
        text_run = para.runs[-1]
        text_run.text = ""
        r_role = para.add_run(role)
        r_role.font.name = FONT
        r_role.font.size = Pt(size_pt)
        r_role.bold = True
        if obligation:
            r_obl = para.add_run(" \u2014 %s" % obligation)
            r_obl.font.name = FONT
            r_obl.font.size = Pt(size_pt)
        is_first = False

# ── Monitoring table ─────────────────────────────────────────────────────────────────

def _monitoring_table(doc, task: TaskBlock) -> None:
    if task.monitoring is None:
        return
    m = task.monitoring

    gap = doc.add_paragraph()
    _fix_spacing(gap)

    heading = doc.add_paragraph()
    _run(heading, "Critical Control Verification Schedule", bold=True, size_pt=10)

    table = doc.add_table(rows=2, cols=5)
    _format_table(table)
    for row in table.rows:
        for i, w in enumerate(_MON_W):
            row.cells[i].width = Cm(w)

    for i, h in enumerate(_MON_HEADERS):
        _header_cell(table.rows[0].cells[i], h)

    vals = [task.task, m.critical_control, m.who, m.frequency, m.evidence]
    for i, val in enumerate(vals):
        _run(table.rows[1].cells[i].paragraphs[0], val or "")

# ── Main render ──────────────────────────────────────────────────────────────────────────

def render_docx(task: TaskBlock) -> bytes:
    """Render TaskBlock as a Word .docx table. Returns bytes."""
    root = Path(__file__).parent.parent / "src"
    template = root / "RPD-MSW-002_Remedial_Works_Master_SWMS.docx"
    fallback = root / "SWMS-260306-V1.docx"
    if template.exists():
        doc = Document(str(template))
    elif fallback.exists():
        doc = Document(str(fallback))
    else:
        doc = Document()

    # Clear all existing content
    for para in doc.paragraphs[:]:
        para._element.getparent().remove(para._element)
    for tbl in doc.tables[:]:
        tbl._element.getparent().remove(tbl._element)

    # Page: A4 landscape, 1cm margins
    section = doc.sections[0]
    section.orientation  = WD_ORIENT.LANDSCAPE
    section.page_width   = Mm(297)
    section.page_height  = Mm(210)
    section.left_margin  = section.right_margin = Cm(1)
    section.top_margin   = section.bottom_margin = Cm(1)

    # Main SWMS table
    table = doc.add_table(rows=2, cols=7)
    _format_table(table)
    for row in table.rows:
        for i, w in enumerate(_COL_W):
            row.cells[i].width = Cm(w)

    # Header row
    for i, h in enumerate(_HEADERS):
        _header_cell(table.rows[0].cells[i], h)

    # Data row — white, risk cells coloured
    c = table.rows[1].cells

    # Col 0 — Task + scope
    _run(c[0].paragraphs[0], task.task, bold=True)
    if task.scope:
        _run(c[0].add_paragraph(), "[%s]" % task.scope, color=GREY)

    # Col 1 — Hazards (bulleted)
    _hazard_cell(c[1], task)

    # Col 2 — Risk Pre
    _risk_cell(c[2], task.risk_pre or "")

    # Col 3 — Controls
    _controls_cell(c[3], task)

    # Col 4 — Risk Post
    _risk_cell(c[4], task.risk_post or "")

    # Col 5 — Responsibility
    _responsibility_cell(c[5], task)

    # Col 6 — CCVS code
    p6 = c[6].paragraphs[0]
    p6.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(p6, validate_ccvs_code(task.ccvs_code or "N/A"), bold=True, size_pt=10)

    # Monitoring table
    _monitoring_table(doc, task)

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ── HRCW checkbox map ────────────────────────────────────────────────────────
# Maps hrcw_category keywords to (row, col) in Table 0 of SWMS-260306-V1.docx.
# Each HRCW checkbox occupies two merged columns; we write into the first.

_SZ = 9  # Font size for task table, monitoring table, requirements table

_HRCW_TICK_MAP = {
    "falling_2m":       (3, 1),
    "telecom_tower":    (3, 3),
    "demolition":       (3, 5),
    "asbestos":         (4, 1),
    "temp_support":     (4, 3),
    "confined_space":   (4, 5),
    "shaft_trench":     (5, 1),
    "explosives":       (5, 3),
    "pressurised_gas":  (5, 5),
    "chemical_fuel":    (6, 1),
    "electrical":       (6, 3),
    "contaminated_atmo":(6, 5),
    "tiltup_precast":   (7, 1),
    "traffic_corridor": (7, 3),
    "mobile_plant":     (7, 5),
    "extreme_temp":     (8, 1),
    "drowning":         (8, 3),
    "diving":           (8, 5),
}


# ── Builder functions for render_swms_document() ──────────────────────────────


def _tick_checkbox(cell) -> None:
    """Tick a checkbox cell, bold all runs, and yellow-highlight the label."""
    ticked = False
    for para in cell.paragraphs:
        runs = para.runs
        for i, run in enumerate(runs):
            # Single-run checkbox: [   ] or [ ... ]
            if "[" in run.text and "]" in run.text and "\u2713" not in run.text:
                import re as _re_cb
                run.text = _re_cb.sub(r'\[\s*\]', '[\u2713]', run.text)
                ticked = True
                break
            # Two-run: '[ ' + '  ]' — bracket split across runs
            if "[" in run.text and "]" not in run.text and i + 1 < len(runs):
                if "]" in runs[i + 1].text:
                    run.text = "[\u2713"
                    runs[i + 1].text = "]" + runs[i + 1].text.split("]", 1)[-1]
                    ticked = True
                    break
            # Multi-run: '[' then whitespace then ']'
            if run.text.strip() == "[" and i + 1 < len(runs):
                if runs[i + 1].text.strip() == "":
                    runs[i + 1].text = "\u2713"
                    ticked = True
                    break
        if ticked:
            # Bold all runs and yellow-highlight the entire cell text
            for run in para.runs:
                run.bold = True
                rpr = run._r.get_or_add_rPr()
                # Remove existing highlight if any
                for hl in rpr.findall(qn("w:highlight")):
                    rpr.remove(hl)
                hl = etree.SubElement(rpr, qn("w:highlight"))
                hl.set(qn("w:val"), "yellow")
            return


def _fill_cover_table(doc, tasks, project_meta, inference, jur, doc_date) -> None:
    """Populate Table 0 — cover page fields and HRCW checkboxes."""
    from datetime import date
    t0 = doc.tables[0]

    def _set_cover(row: int, col: int, value: str) -> None:
        cell = t0.cell(row, col)
        # Remove w:sdt content controls that prevent text replacement
        for sdt in cell._tc.findall(qn('w:sdt')):
            cell._tc.remove(sdt)
        for para in cell.paragraphs:
            para.clear()
        _run(cell.paragraphs[0], value)

    _raw_pcbu = (project_meta.get("pcbu_name")
                 or project_meta.get("pcbu")
                 or project_meta.get("principal_contractor", ""))
    pcbu = sanitise_text(_raw_pcbu)
    if not pcbu or (pcbu == pcbu.lower() and " " not in pcbu) or len(pcbu) < 4:
        pcbu = "[Insert PCBU here]"
    manager = (project_meta.get("manager_name")
               or project_meta.get("manager", ""))
    site_name = (project_meta.get("project_address")
                 or project_meta.get("site_name")
                 or project_meta.get("site_address", ""))
    pc = project_meta.get("principal_contractor", pcbu)
    supervisor = project_meta.get("supervisor", "")
    work_activity = project_meta.get("work_activity_summary", "")
    if not work_activity:
        work_activity = (project_meta.get("work_activity")
                         or project_meta.get("description")
                         or project_meta.get("project_name", ""))
        if site_name and site_name in work_activity:
            work_activity = work_activity.replace(site_name, "").strip(" ,at-")
    # Cap work activity at 8 lines; summarise with Claude if over
    if work_activity and work_activity.count("\n") >= 8:
        work_activity = _summarise_work_activity(work_activity)

    # Row 0: PCBU + Site
    _set_cover(0, 1, pcbu)
    _set_cover(0, 6, site_name)
    # Row 1: Manager + Date
    _set_cover(1, 1, manager)
    _set_cover(1, 6, doc_date)
    # Row 2: Work activity + PC
    _set_cover(2, 1, work_activity)
    _set_cover(2, 6, pc)
    # Row 9: Supervisor + Date received
    _set_cover(9, 2, supervisor)
    _set_cover(9, 5, doc_date)
    # Row 11: Manager reviewer + Date
    _set_cover(11, 2, manager)
    _set_cover(11, 5, doc_date)
    # Row 13: Reviewer signature + Date
    _set_cover(13, 2, manager)
    _set_cover(13, 5, doc_date)

    # HRCW ticks — rows 3-8
    hrcw_flags = inference.get("hrcw_flags", {})
    for key, (row, col) in _HRCW_TICK_MAP.items():
        if hrcw_flags.get(key):
            _tick_checkbox(t0.cell(row, col))

    # Also tick based on task data
    for task in tasks:
        if task.wah_applicable:
            _tick_checkbox(t0.cell(3, 1))  # falling_2m

    # Set Table 0 runs: rows 0-2 and 9+ at 10pt, rows 3-8 (HRCW) at 9pt
    for ri, row in enumerate(t0.rows):
        sz = Pt(9) if 3 <= ri <= 8 else Pt(10)
        for cell in row.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.name = FONT
                    run.font.size = sz


def _build_task_table(doc, tasks) -> None:
    """Populate Table 1 — one row per task."""
    t1 = doc.tables[1]
    _set_table_cell_margins(t1)

    # Remove the blank data row (row index 1), keep header (row 0)
    if len(t1.rows) > 1:
        tr = t1.rows[1]._tr
        tr.getparent().remove(tr)

    # Re-format Table 1 header row at 9pt
    for i, h in enumerate(_HEADERS):
        cell = t1.rows[0].cells[i]
        for para in cell.paragraphs:
            para.clear()
        _header_cell(cell, h, size_pt=_SZ)

    # Add one row per task
    for task in tasks:
        row = t1.add_row()
        c = row.cells
        for i, w in enumerate(_COL_W):
            c[i].width = Cm(w)

        # Col 0 — Task + scope
        _run(c[0].paragraphs[0], task.task, bold=True, size_pt=_SZ)
        if task.scope:
            _run(c[0].add_paragraph(), "[%s]" % task.scope, color=GREY, size_pt=_SZ)

        # Col 1 — Hazards (genuine hazard descriptions, bulleted)
        _hazard_cell(c[1], task, size_pt=_SZ)

        # Col 2 — Risk Pre (10pt bold)
        _risk_cell(c[2], task.risk_pre or "", size_pt=10)

        # Col 3 — Controls
        _controls_cell(c[3], task, size_pt=_SZ)

        # Col 4 — Risk Post (10pt bold)
        _risk_cell(c[4], task.risk_post or "", size_pt=10)

        # Col 5 — Responsibility
        _responsibility_cell(c[5], task, size_pt=_SZ)

        # Col 6 — CCVS code (validated)
        p6 = c[6].paragraphs[0]
        p6.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(p6, validate_ccvs_code(task.ccvs_code or "N/A"), bold=True, size_pt=_SZ)


def _format_risk_matrix(doc) -> None:
    """Apply font to Table 3 — risk matrix (content untouched)."""
    t3 = doc.tables[4]
    for row in t3.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.name = FONT
                    run.font.size = Pt(_SZ)


def _fill_legislation_table(doc, inference, jur, jurisdiction) -> None:
    """Populate Table 4 — legislation references."""
    t4 = doc.tables[5]

    # Set all existing runs to Aptos 9pt (content untouched)
    for row in t4.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.name = FONT
                    run.font.size = Pt(_SZ)

    # Jurisdiction-aware legislation
    _base_parts = jur["base_legislation_string"].split(" \u2014 ")
    _BASE_LEGISLATION = [p.strip() for p in _base_parts if p.strip()]

    reg_notes = inference.get("regulatory_notes", [])
    jur_notes = inference.get("jurisdiction_notes", [])
    # Deduplicate regulatory notes against base legislation
    _cleaned_notes = []
    _base_lower = [b.lower() for b in _BASE_LEGISLATION]
    for n in reg_notes + jur_notes:
        if n.lower() in _base_lower:
            continue
        if n in _cleaned_notes:
            continue
        cleaned = n.strip()
        if jurisdiction == "AU":
            cleaned = (cleaned
                       .replace("Model WHS Act 2011", "WHS Act 2011 (NSW)")
                       .replace("Model WHS Regulations 2017", "WHS Regulation 2017 (NSW)")
                       .replace("Safe Work Australia Codes of Practice", "SafeWork NSW Codes of Practice"))
        if cleaned and cleaned.lower() not in _base_lower and cleaned not in _cleaned_notes:
            _cleaned_notes.append(cleaned)
    all_legislation = _BASE_LEGISLATION + _cleaned_notes
    cell = t4.cell(0, 1)
    for para in cell.paragraphs:
        para.clear()
    # Single paragraph with bold em-dash separators
    p = cell.paragraphs[0]
    for i, note in enumerate(all_legislation):
        if i > 0:
            _run(p, " \u2014 ", bold=True, size_pt=_SZ)
        _run(p, note, size_pt=_SZ)


def _fill_requirements_table(doc, tasks, inference, project_meta) -> None:
    """Populate Table 5 — PPE, permits, qualifications, plant, maintenance, hazardous substances, WAH."""
    t5 = doc.tables[6]
    _set_table_cell_margins(t5)

    # Re-format Table 5 existing text at 9pt (both columns, all rows)
    for row in t5.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.name = FONT
                    run.font.size = Pt(_SZ)

    def _fill_req_cell(row_idx: int, items: list[str]) -> None:
        """Populate col 1 of Table 5 — single paragraph, bold em-dash separated."""
        cell = t5.cell(row_idx, 1)
        for pi in range(len(cell.paragraphs) - 1, 0, -1):
            cell.paragraphs[pi]._element.getparent().remove(cell.paragraphs[pi]._element)
        cell.paragraphs[0].clear()
        if not items:
            _run(cell.paragraphs[0], "\u2014", size_pt=_SZ)
            _strip_para_indent(cell.paragraphs[0])
            return
        p = cell.paragraphs[0]
        for i, item in enumerate(items):
            if i > 0:
                _run(p, " \u2014 ", bold=True, size_pt=_SZ)
            _run(p, item, size_pt=_SZ)
        _strip_para_indent(p)

    # Row 0: PPE — always include baseline, then add inference PPE
    from vocab.swms_vocabulary import enforce_vocabulary as _enforce_vocab
    _job_text = " ".join(t.task.lower() + " " + t.scope.lower() for t in tasks)
    _CHEM_KW = ("epoxy", "resin", "hardener", "solvent", "chemical", "acid", "alkali",
                "caustic", "adhesive", "primer", "paint", "coating", "membrane",
                "sealant", "grout", "mortar", "waterproof")
    _has_chemicals = any(kw in _job_text for kw in _CHEM_KW)
    _glove_type = ("chemical-resistant gloves (nitrile or task-appropriate)"
                   if _has_chemicals else "cut-resistant gloves")
    _BASELINE_PPE = [
        "steel-capped footwear",
        "hi-viz shirt or vest",
        "eye protection",
        "hearing protection (>85dB)",
        _glove_type,
    ]
    raw_ppe = inference.get("ppe", [])
    enforced_ppe = [_enforce_vocab(item) for item in raw_ppe]
    _PPE_NORM = {
        "steel-capped footwear": "footwear", "steel-capped safety boots": "footwear",
        "safety boots": "footwear", "steel cap boots": "footwear",
        "steel-capped boots": "footwear", "safety footwear": "footwear",
        "hi-viz shirt or vest": "hiviz", "hi-viz vest or shirt": "hiviz",
        "high-visibility vest": "hiviz", "high-visibility vest or shirt": "hiviz",
        "hi-vis vest": "hiviz", "hi-vis shirt": "hiviz", "hi-vis vest or shirt": "hiviz",
        "eye protection": "eye", "safety glasses": "eye", "safety goggles": "eye",
        "hearing protection": "hearing", "hearing protection (>85db)": "hearing",
        "ear plugs": "hearing", "ear muffs": "hearing",
    }
    def _ppe_key(item):
        base = item.lower().split("\u2014")[0].strip()
        return _PPE_NORM.get(base, base)
    seen_keys = set()
    final_ppe = []
    for item in _BASELINE_PPE + enforced_ppe:
        key = _ppe_key(item)
        if key not in seen_keys:
            seen_keys.add(key)
            final_ppe.append(item)
    _fill_req_cell(0, final_ppe)
    # Row 1: Permits / certificates / approvals
    _fill_req_cell(1, inference.get("permits", []))
    # Row 2: Site-specific training
    _fill_req_cell(2, inference.get("qualifications", []))
    # Row 3: Certifications / HRW licences
    _fill_req_cell(3, inference.get("certifications", []))
    # Row 5 first (need maintenance items to derive plant list)
    _MAINTENANCE_LOOKUP = {
        "ewp": "EWP \u2014 pre-start checklist completed \u2014 boom, basket, controls, tyres, outriggers checked \u2014 log book current",
        "elevated work platform": "EWP \u2014 pre-start checklist completed \u2014 boom, basket, controls inspected",
        "mobile crane": "Mobile crane \u2014 pre-start checklist \u2014 outriggers, boom, load chart, slew ring \u2014 engineer ground bearing certificate sighted",
        "crane": "Crane \u2014 pre-start checklist \u2014 outriggers, load chart, slew ring inspected",
        "franna": "Franna crane \u2014 pre-start checklist \u2014 outriggers, load chart, slew ring inspected",
        "angle grinder": "Angle grinder \u2014 check guard intact and disc undamaged before each use \u2014 RCD test tag current (AS/NZS 3012 3-monthly)",
        "grinder": "Grinder \u2014 guard intact, disc undamaged, RCD test tag current (AS/NZS 3012 3-monthly)",
        "hepa vacuum": "HEPA vacuum \u2014 check filter condition before each shift",
        "vacuum": "Vacuum \u2014 check filter condition before use",
        "mixing containers": "Mixing containers \u2014 clean and dry before use",
        "scaffold": "Scaffold \u2014 daily pre-use inspection by competent person \u2014 tag current",
        "ladder": "Ladder \u2014 AS/NZS 1892 compliant \u2014 inspect feet, rungs, locks before each use",
        "scissor lift": "Scissor lift \u2014 pre-start checklist completed \u2014 platform, guardrails, controls checked",
        "boom lift": "Boom lift \u2014 pre-start checklist completed \u2014 boom, basket, controls, outriggers checked",
        "forklift": "Forklift \u2014 pre-start checklist \u2014 mast, forks, brakes, lights, seatbelt checked",
        "concrete saw": "Concrete saw \u2014 guard intact, blade undamaged, water supply connected",
        "jackhammer": "Jackhammer \u2014 inspect chisel retention, check hose connections before each use",
    }
    _task_text = " ".join(t.task.lower() + " " + t.scope.lower() for t in tasks)
    _plant_text = " ".join(p.lower() for p in inference.get("plant", []))
    maint_items = list(project_meta.get("maintenance_checks", []))
    if not maint_items:
        _search_text = _task_text + " " + _plant_text
        _seen_maint_names = set()
        for kw, entry in _MAINTENANCE_LOOKUP.items():
            if kw in _search_text:
                equip_name = entry.split("\u2014")[0].strip().lower()
                if equip_name not in _seen_maint_names:
                    maint_items.append(entry)
                    _seen_maint_names.add(equip_name)
        if any(k in _task_text for k in ("epoxy", "resin", "coating")) and not any("Mixing" in m for m in maint_items):
            maint_items.append("Mixing containers \u2014 clean and dry before use")
    _fill_req_cell(5, maint_items)

    # Row 4: Plant and equipment
    plant_items = list(inference.get("plant", []))
    for item in project_meta.get("plant_equipment", project_meta.get("plant", [])):
        if item not in plant_items:
            plant_items.append(item)
    for mitem in maint_items:
        plant_name = mitem.split("\u2014")[0].strip()
        if plant_name and plant_name.lower() not in [p.lower() for p in plant_items]:
            plant_items.append(plant_name)
    _PLANT_KEYWORDS = {
        "grinder": "Angle grinder", "angle grinder": "Angle grinder",
        "ewp": "EWP (elevated work platform)", "scissor lift": "Scissor lift",
        "vacuum": "HEPA vacuum", "hepa vacuum": "HEPA vacuum",
        "saw": "Power saw", "jackhammer": "Jackhammer",
        "drill": "Power drill", "mixer": "Mixing equipment",
    }
    _task_text_lower = _task_text
    for kw, pname in _PLANT_KEYWORDS.items():
        if kw in _task_text_lower and pname.lower() not in [p.lower() for p in plant_items]:
            plant_items.append(pname)
    if not plant_items:
        plant_items = ["As per task requirements \u2014 see controls column"]
    _fill_req_cell(4, plant_items)

    # Row 6: Hazardous substances
    hrcw_flags = inference.get("hrcw_flags", {})
    haz_sub_items = list(project_meta.get("hazardous_substances", []))
    if not haz_sub_items:
        _has_silica = any("silica" in n.lower() for n in inference.get("regulatory_notes", []))
        _has_epoxy_sub = any(k in _task_text for k in ("epoxy", "resin"))
        _has_primer = any(k in _task_text for k in ("primer", "solvent"))
        _has_tiltup = hrcw_flags.get("tiltup_precast", False)
        _has_crane_ewp = any(k in _plant_text for k in ("crane", "ewp", "boom", "forklift"))
        if _has_silica:
            haz_sub_items.append(
                "Respirable crystalline silica (RCS) \u2014 SDS on site "
                "\u2014 WES 0.05 mg/m\u00b3 TWA \u2014 P2 minimum, half-face RPE for prolonged exposure"
            )
        if _has_epoxy_sub:
            haz_sub_items.append(
                "Epoxy resin (Part A) \u2014 SDS on site \u2014 skin/eye sensitiser "
                "\u2014 chemical-resistant gloves, eye protection mandatory"
            )
            haz_sub_items.append(
                "Epoxy hardener (Part B) \u2014 SDS on site \u2014 corrosive "
                "\u2014 chemical resistant gloves, eye protection"
            )
        if _has_primer:
            haz_sub_items.append(
                "Epoxy primer \u2014 SDS on site \u2014 flammable liquid "
                "\u2014 store per AS 1940, ventilate during use"
            )
        if _has_tiltup:
            haz_sub_items.append(
                "Concrete release agent \u2014 SDS on site \u2014 skin/eye irritant "
                "\u2014 nitrile gloves and eye protection required"
            )
        if _has_crane_ewp:
            haz_sub_items.append(
                "Hydraulic fluid \u2014 SDS on site \u2014 skin sensitiser "
                "\u2014 gloves required"
            )
    if not haz_sub_items:
        haz_sub_items = [
            "No hazardous substances identified for this scope \u2014 "
            "confirm with site supervisor before work commences"
        ]
    _fill_req_cell(6, haz_sub_items)

    # Row 7: WAH risk assessment — ALWAYS populated (mandatory text)
    _wah_cell = t5.cell(7, 1)
    for pi in range(len(_wah_cell.paragraphs) - 1, 0, -1):
        _wah_cell.paragraphs[pi]._element.getparent().remove(
            _wah_cell.paragraphs[pi]._element
        )
    _wah_cell.paragraphs[0].clear()

    _wah_texts = [
        (True, "Fall prevention hierarchy applied: eliminate > isolate > minimise. "
               "Guardrails preferred. Fall restraint before fall arrest. "
               "Rescue plan documented for all harness work. "
               "Working at Heights licence/training verified before elevated work commences."),
        (False, "A-frame ladders may be used for short-duration tasks where a "
                "site-specific Working at Heights Risk Assessment (WaH RA) confirms "
                "ladder use is reasonably practicable; ladder must be AS/NZS 1892 "
                "compliant, stable, fully opened and used without overreaching."),
        (False, "Working at Heights Risk Assessment (if >2m): "
                "Height of task: _______ duration of task: _______ "
                "ground stable and level: Yes / No, "
                "heavy exertion required: Yes / No, "
                "overreaching required: Yes / No, "
                "scaffold reasonably practicable: Yes / No, "
                "EWP reasonably practicable: Yes / No, "
                "A-frame ladder appropriate control: Yes / No "
                "Assessed by: ________________ Date: ________ "
                "This creates documentary evidence."),
    ]

    for i, (is_bold, text) in enumerate(_wah_texts):
        p = _wah_cell.paragraphs[0] if i == 0 else _wah_cell.add_paragraph()
        _run(p, text, bold=is_bold, size_pt=_SZ)
        _strip_para_indent(p)


def _build_ccvs_table(doc, tasks) -> None:
    """Populate Table 7 — CCVS monitoring rows."""
    t2 = doc.tables[2]
    _set_table_cell_margins(t2)

    # Re-format Table 2 header row at 9pt
    for i, h in enumerate(_MON_HEADERS):
        cell = t2.rows[0].cells[i]
        for para in cell.paragraphs:
            para.clear()
        _header_cell(cell, h, size_pt=_SZ)

    # Remove blank data row (row 1), keep header
    if len(t2.rows) > 1:
        tr = t2.rows[1]._tr
        tr.getparent().remove(tr)

    # Add monitoring rows — only tasks with a real CCVS code and monitoring data
    for task in tasks:
        if task.monitoring is None:
            continue
        if validate_ccvs_code(task.ccvs_code or "N/A") == "N/A":
            continue
        m = task.monitoring
        row = t2.add_row()
        vals = [task.task, m.critical_control, m.who, m.frequency, m.evidence]
        for i, w in enumerate(_MON_W):
            row.cells[i].width = Cm(w)
        for i, val in enumerate(vals):
            _run(row.cells[i].paragraphs[0], val or "", size_pt=_SZ)


def _fill_signoff_table(doc) -> None:
    """Prevent sign-off table (Table 6) rows from splitting across pages."""
    if len(doc.tables) > 7:
        for _row in doc.tables[7].rows:
            _trPr = _row._tr.find(qn('w:trPr'))
            if _trPr is None:
                _trPr = etree.SubElement(_row._tr, qn('w:trPr'))
            _cs = _trPr.find(qn('w:cantSplit'))
            if _cs is None:
                _cs = etree.SubElement(_trPr, qn('w:cantSplit'))
            _cs.set(qn('w:val'), '1')


def _build_footer(doc, project_meta, jur, jurisdiction, doc_date) -> None:
    """Build document footer with SWMS ID slug and jurisdiction reference."""
    import re as _re
    from datetime import date
    _address = (project_meta.get("project_address")
                or project_meta.get("site_name")
                or project_meta.get("site_address", ""))
    if _address:
        _slug_parts = _address.split(",")[0].strip()
        _slug = _re.sub(r'[^a-zA-Z0-9\s]', '', _slug_parts)
        _slug = _re.sub(r'\s+', '-', _slug.strip())
        _suburb_match = _re.search(r',\s*([A-Za-z]+)', _address)
        if _suburb_match:
            _slug += '-' + _suburb_match.group(1)
    else:
        _slug = project_meta.get("project_name", "UNKNOWN")
    _slug = _re.sub(r'[\\/:*?"<>|]', "-", _slug)
    footer_date = project_meta.get("date", "")
    if not footer_date:
        footer_date = date.today().strftime("%d%m%Y")
    else:
        footer_date = footer_date.replace("/", "")
    _pcbu = (project_meta.get("pcbu_name") or "").strip()
    if not _pcbu or len(_pcbu) < 4:
        _pcbu = "Safe Method"
    footer_text = f"SWMS-{_slug}-{footer_date}-V01 | {_pcbu}"

    section = doc.sections[0]
    footer = section.footer
    footer.is_linked_to_previous = False
    if footer.paragraphs:
        fp = footer.paragraphs[0]
        fp.clear()
    else:
        fp = footer.add_paragraph()
    fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    _run(fp, footer_text, size_pt=_SZ)

    # Resolve footer tokens in all sections
    _FOOTER_TOKENS = {
        "{doc_ref}":  project_meta.get("doc_ref", f"SWMS-{_slug}"),
        "{revision}": project_meta.get("revision", "V01"),
        "{project}":  project_meta.get("project_name", ""),
        "{date}":     project_meta.get("issue_date", doc_date),
    }
    for _sec in doc.sections:
        for _fp in _sec.footer.paragraphs:
            for _fr in _fp.runs:
                for _tok, _val in _FOOTER_TOKENS.items():
                    if _tok in _fr.text:
                        _fr.text = _fr.text.replace(_tok, _val)


# ── Main SWMS document renderer ──────────────────────────────────────────────


def render_swms_document(
    tasks: list[TaskBlock],
    project_meta: dict,
    inference: dict,
    jurisdiction: str = "AU",
) -> bytes:
    """
    Multi-task SWMS renderer.  Populates the SWMS-260306-V1.docx template
    in-place using the 9-table structure:

        Table 0  cover page        — project_meta + HRCW ticks
        Table 1  task table        — header row kept, task rows added
        Table 2  CCVS monitoring   — header row kept, data rows added
        Table 3  amendments mid    — untouched
        Table 4  risk matrix       — untouched
        Table 5  legislation       — col 1 row 0
        Table 6  PPE / requirements— col 1 all rows
        Table 7  worker signoff    — untouched
        Table 8  amendments end    — untouched

    Args:
        tasks:        list of TaskBlock objects (one per task row)
        project_meta: dict with keys like pcbu, site_name, manager,
                      supervisor, principal_contractor, work_activity, date
        inference:    dict from infer_to_dict() — keys: hrcw, hrcw_category,
                      ppe, certifications, permits, qualifications,
                      notifications, regulatory_notes, etc.

    Returns:
        bytes — the rendered .docx file content.
    """
    from datetime import date
    from core.jurisdictions import get_jurisdiction
    jur = get_jurisdiction(jurisdiction)

    template_path = Path(__file__).parent.parent / "src" / "SWMS-260306-V1.docx"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    doc = Document(str(template_path))

    if len(doc.tables) != 9:
        raise ValueError(
            f"Template has {len(doc.tables)} tables, expected 9. "
            "Wrong template file — render_swms_document requires SWMS-260306-V1.docx"
        )

    # ── Body paragraph 0: Description (title-only, max 100 chars) ───────
    _p0_text = (project_meta.get("title") or "").strip()
    if not _p0_text:
        # Fallback: first sentence of description, capped
        _fallback = (project_meta.get("work_activity_summary")
                     or project_meta.get("work_activity")
                     or project_meta.get("description")
                     or project_meta.get("project_name", ""))
        _p0_address = (project_meta.get("project_address")
                       or project_meta.get("site_address", ""))
        if _p0_address and _p0_address in _fallback:
            _fallback = _fallback.replace(_p0_address, "").strip(" ,at-")
        _p0_text = _fallback.split(". ")[0].split(".\n")[0].rstrip(".") if _fallback else ""
    # Hard cap 100 chars, truncate at last word boundary
    if len(_p0_text) > 100:
        _p0_text = _p0_text[:100].rsplit(" ", 1)[0]
    if _p0_text and doc.paragraphs:
        p0 = doc.paragraphs[0]
        if "[Insert description here]" in p0.text:
            p0.clear()
            _run(p0, f"\u25a0 Description: {_p0_text}", bold=True, size_pt=16)
        p0.paragraph_format.space_after = Pt(0)
        p0.paragraph_format.space_before = Pt(0)
        p0.paragraph_format.keep_with_next = True

    # Remove any page breaks between P0 and Table 0
    for para in doc.paragraphs:
        if para._element.getnext() is not None and para._element.getnext().tag.endswith('}tbl'):
            pPr = para._element.find(qn('w:pPr'))
            if pPr is not None:
                for pb in pPr.findall(qn('w:pageBreakBefore')):
                    pPr.remove(pb)
            break

    # Reduce top margin so cover table stays on page 1
    if doc.sections:
        doc.sections[0].top_margin = Cm(1.0)

    doc_date = project_meta.get("date", date.today().strftime(jur["date_format"]))

    # ── Populate tables via builder functions ─────────────────────────────
    _fill_cover_table(doc, tasks, project_meta, inference, jur, doc_date)
    _build_task_table(doc, tasks)
    _format_risk_matrix(doc)
    _fill_legislation_table(doc, inference, jur, jurisdiction)
    _fill_requirements_table(doc, tasks, inference, project_meta)
    _build_ccvs_table(doc, tasks)
    _fill_signoff_table(doc)
    _build_footer(doc, project_meta, jur, jurisdiction, doc_date)

    # ── Post-render validation ────────────────────────────────────────
    warnings = validate_output(doc)
    if warnings:
        import logging
        for w in warnings:
            logging.warning(f"RENDER VALIDATION: {w}")

    # ── Save and return ─────────────────────────────────────────────────
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ── Output validation ────────────────────────────────────────────────────────

_KNOWN_PLACEHOLDER_TOKENS = [
    'UNKNOWN', '[Insert', 'mcxico', 'your-company',
    'PCBU_NAME', 'INSERT_', '{{', '}}',
]

def validate_output(doc) -> list[str]:
    """Check rendered document for unresolved placeholders and malformed codes."""
    errors = []
    all_text_blocks = []
    for para in doc.paragraphs:
        all_text_blocks.append(para.text)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                all_text_blocks.append(cell.text)
    full_text = ' '.join(all_text_blocks)

    for token in _KNOWN_PLACEHOLDER_TOKENS:
        if token in full_text:
            errors.append(f"Unresolved placeholder found: '{token}'")

    # Check for malformed CCVS codes (missing hyphen)
    bad_codes = _re_ccvs.findall(
        r'\b(' + '|'.join(_VALID_CCVS_STREAMS) + r')[A-Z]\d\b', full_text
    )
    for code in bad_codes:
        errors.append(f"Malformed CCVS code (missing hyphen): '{code}'")

    # Check for duplicate PPE tokens
    if 'steel-capped steel-capped' in full_text:
        errors.append("Duplicate PPE token: 'steel-capped steel-capped'")

    return errors

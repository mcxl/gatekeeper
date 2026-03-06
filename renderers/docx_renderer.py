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
from docx.oxml import parse_xml
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
    run = para.add_run(text)
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

def _header_cell(cell, text: str) -> None:
    _shade(cell, BLUE)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(p, text, bold=True)

def _risk_cell(cell, text: str) -> None:
    s = text.strip()
    if s.startswith("High"):     bg, fg = RED_BG, WHITE
    elif s.startswith("Medium"): bg, fg = YLW_BG, BLACK
    else:                        bg, fg = GRN_BG, BLACK
    _shade(cell, bg)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(p, text, bold=True, color=fg, size_pt=10)

def _controls_cell(cell, task: TaskBlock) -> None:
    first = [True]

    def _p(text, bold=False, color=None, highlight=False, rule=False):
        if first[0]:
            p = cell.paragraphs[0]
            first[0] = False
        else:
            p = cell.add_paragraph()
        if rule:
            _add_section_rule(p)
        _run(p, text, bold=bold, color=color, highlight=highlight)

    for item in task.controls:
        _p(item)

    if task.admin:
        _p("Admin:", bold=True, rule=bool(task.controls))
        for item in task.admin:
            _p(item)

    if task.ppe:
        _p("PPE:", bold=True, rule=bool(task.controls or task.admin))
        for item in task.ppe:
            _p(item)

    if task.hold_points:
        _p(
            "\u26a0\ufe0f HOLD POINT \u2014 do not start until:",
            bold=True, highlight=True,
            rule=bool(task.controls or task.admin or task.ppe),
        )
        for item in task.hold_points:
            _p(item, highlight=True)

    if task.stop_work:
        _p(
            "\U0001f6d1 STOP WORK if:",
            bold=True, color=RED,
            rule=bool(task.controls or task.admin or task.ppe or task.hold_points),
        )
        for item in task.stop_work:
            _p(item, color=RED)

def _responsibility_cell(cell, task: TaskBlock) -> None:
    first = True
    for role, obligation in task.responsibility.items():
        p = cell.paragraphs[0] if first else cell.add_paragraph()
        first = False
        _run(p, role, bold=True)
        if obligation:
            _run(p, " \u2014 %s" % obligation)

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

    # Col 1 — Hazard
    _run(c[1].paragraphs[0], task.scope or "")

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
    _run(p6, task.ccvs_code or "N/A", bold=True, size_pt=10)

    # Monitoring table
    _monitoring_table(doc, task)

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()

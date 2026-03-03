#!/usr/bin/env python3
"""
renderers/docx_renderer.py — TaskBlock → .docx bytes

Builds a single-row SWMS Word table (header + data row).
A4 landscape, 1cm margins, Aptos 8pt throughout.

Reuses helpers from src/docx_style_standard.py — no rewrites.
"""

import os
import sys
from io import BytesIO

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Mm, Pt, RGBColor
from lxml import etree

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.schema import TaskBlock
from src.docx_style_standard import (
    FONT_NAME,
    apply_document_font,
    add_risk_cell,
    format_header_cell,
    set_cell_margins,
    set_cell_shading,
)

# ============================================================
# CONSTANTS
# ============================================================

FONT_SIZE = Pt(8)
RED = RGBColor(0xC0, 0x00, 0x00)
BLACK = RGBColor(0x00, 0x00, 0x00)
SCOPE_GREY = RGBColor(0x44, 0x44, 0x44)
AMBER_BG = "FFE699"

# A4 landscape (297mm) — 1cm margins each side → 277mm usable
_USABLE_CM = (297 - 20) / 10  # 27.7cm

# Column proportions — must sum to 100
_COL_PCT = [10, 15, 8, 35, 8, 14, 10]
_COL_WIDTHS_CM = [_USABLE_CM * p / 100 for p in _COL_PCT]

_HEADERS = [
    "Task", "Hazard", "Risk\n(Pre)", "Controls",
    "Risk\n(Post)", "Responsibility", "CCVS\nCode",
]


# ============================================================
# LOW-LEVEL HELPERS
# ============================================================

def _add_run(
    para,
    text: str,
    bold: bool = False,
    color: RGBColor = None,
    highlight: bool = False,
) -> None:
    run = para.add_run(text)
    run.font.name = FONT_NAME
    run.font.size = FONT_SIZE
    run.bold = bold
    if color:
        run.font.color.rgb = color
    if highlight:
        rpr = run._r.get_or_add_rPr()
        hl = etree.SubElement(rpr, qn("w:highlight"))
        hl.set(qn("w:val"), "yellow")


def _add_top_rule(para) -> None:
    """Add a top paragraph border as a visual section separator."""
    ppr = para._p.get_or_add_pPr()
    pbdr = parse_xml(
        f'<w:pBdr {nsdecls("w")}>'
        f'  <w:top w:val="single" w:sz="4" w:space="1" w:color="BFBFBF"/>'
        f"</w:pBdr>"
    )
    ppr.append(pbdr)


# ============================================================
# CELL BUILDERS
# ============================================================

def _build_controls_cell(cell, task: TaskBlock) -> None:
    """
    Populate the controls cell with ordered sections:
      controls → (rule) admin → (rule) PPE → (rule) hold_points → (rule) stop_work
    HOLD POINT items: amber highlight.
    STOP WORK items: red text.
    """
    _first = [True]

    def _para(text: str, bold: bool = False,
               color: RGBColor = None, highlight: bool = False,
               rule: bool = False) -> None:
        if _first[0]:
            p = cell.paragraphs[0]
            _first[0] = False
        else:
            p = cell.add_paragraph()
        if rule:
            _add_top_rule(p)
        _add_run(p, text, bold=bold, color=color, highlight=highlight)

    for item in task.controls:
        _para(item)

    if task.admin:
        _para("Admin:", bold=True, rule=bool(task.controls))
        for item in task.admin:
            _para(item)

    if task.ppe:
        _para("PPE:", bold=True, rule=bool(task.controls or task.admin))
        for item in task.ppe:
            _para(item)

    if task.hold_points:
        _para(
            "HOLD POINT \u2014 do not start until:",
            bold=True, highlight=True,
            rule=bool(task.controls or task.admin or task.ppe),
        )
        for item in task.hold_points:
            _para(item, highlight=True)

    if task.stop_work:
        _para(
            "STOP WORK if:",
            bold=True, color=RED,
            rule=bool(task.controls or task.admin or task.ppe or task.hold_points),
        )
        for item in task.stop_work:
            _para(item, color=RED)


def _build_responsibility_cell(cell, task: TaskBlock) -> None:
    """ROLE \u2014 obligation, one line per role."""
    first = True
    for role, obligation in task.responsibility.items():
        if first:
            p = cell.paragraphs[0]
            first = False
        else:
            p = cell.add_paragraph()
        _add_run(p, role, bold=True)
        if obligation:
            _add_run(p, f" \u2014 {obligation}")


# ============================================================
# RENDER
# ============================================================

def render_docx(task: TaskBlock) -> bytes:
    """Render TaskBlock as a Word .docx table. Returns bytes."""
    doc = Document()
    apply_document_font(doc)

    # A4 landscape, 1cm margins
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = Mm(297)
    section.page_height = Mm(210)
    section.left_margin = Cm(1)
    section.right_margin = Cm(1)
    section.top_margin = Cm(1)
    section.bottom_margin = Cm(1)

    table = doc.add_table(rows=2, cols=7)
    table.style = "Table Grid"

    # Column widths
    for row in table.rows:
        for i, w in enumerate(_COL_WIDTHS_CM):
            row.cells[i].width = Cm(w)

    # Header row
    for i, hdr_text in enumerate(_HEADERS):
        format_header_cell(table.rows[0].cells[i], hdr_text)

    # Data row
    dr = table.rows[1]
    if not task.approved:
        for cell in dr.cells:
            set_cell_shading(cell, AMBER_BG)

    cells = dr.cells

    # Col 0 — Task + scope
    _add_run(cells[0].paragraphs[0], task.task, bold=True)
    if task.scope:
        p_scope = cells[0].add_paragraph()
        _add_run(p_scope, f"[{task.scope}]", color=SCOPE_GREY)

    # Col 1 — Hazard (scope as hazard context — no separate hazard field in TaskBlock)
    _add_run(cells[1].paragraphs[0], task.scope or "")

    # Col 2 — Risk Pre
    add_risk_cell(cells[2], task.risk_pre or "")

    # Col 3 — Controls
    _build_controls_cell(cells[3], task)

    # Col 4 — Risk Post
    add_risk_cell(cells[4], task.risk_post or "")

    # Col 5 — Responsibility
    _build_responsibility_cell(cells[5], task)

    # Col 6 — CCVS Code (centred, bold, 10pt)
    p6 = cells[6].paragraphs[0]
    p6.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run6 = p6.add_run(task.ccvs_code or "N/A")
    run6.bold = True
    run6.font.name = FONT_NAME
    run6.font.size = Pt(10)

    set_cell_margins(table)

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()

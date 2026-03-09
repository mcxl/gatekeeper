#!/usr/bin/env python3
"""
renderers/ra_renderer.py — Risk Assessment document renderer.

Generates a standalone .docx Risk Assessment with:
  - Cover / header page
  - Project description
  - Assessment team table
  - Legislation and standards
  - 5x5 risk rating matrix (colour-coded)
  - Hazard register table
  - Review and sign-off section

A4 portrait, Aptos throughout, 1.5cm margins.
"""

import os
import sys
from datetime import date
from io import BytesIO

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt, RGBColor, Inches
from lxml import etree

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Constants ────────────────────────────────────────────────────────────────

FONT = "Aptos"
BLACK = RGBColor(0x00, 0x00, 0x00)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREY = RGBColor(0x44, 0x44, 0x44)

# Risk level colours
LOW_BG = "00FF00"
MED_BG = "FFFF00"
HIGH_BG = "FF6600"
EXTREME_BG = "FF0000"
BLUE_BG = "DBE5F1"

_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

_BORDER_TBL = (
    '<w:tblBorders {ns}>'
    '<w:top    w:val="single" w:sz="4" w:space="0" w:color="808080"/>'
    '<w:left   w:val="single" w:sz="4" w:space="0" w:color="808080"/>'
    '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="808080"/>'
    '<w:right  w:val="single" w:sz="4" w:space="0" w:color="808080"/>'
    '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="808080"/>'
    '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="808080"/>'
    '</w:tblBorders>'
).format(ns=_NS)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _shade(cell, hex_color: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    for e in tcPr.findall(qn("w:shd")):
        tcPr.remove(e)
    tcPr.append(parse_xml(
        '<w:shd {ns} w:val="clear" w:color="auto" w:fill="{c}"/>'.format(ns=_NS, c=hex_color)
    ))


def _run(para, text: str, bold=False, color=None, size_pt: int = 10, italic=False) -> None:
    run = para.add_run(text)
    run.font.name = FONT
    run.font.size = Pt(size_pt)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = color


def _format_table(table) -> None:
    tbl = table._tbl
    tblPr = tbl.find(qn("w:tblPr"))
    if tblPr is None:
        tblPr = parse_xml('<w:tblPr {ns}/>'.format(ns=_NS))
        tbl.insert(0, tblPr)
    for tag in ("w:tblBorders", "w:tblLayout"):
        for el in tblPr.findall(qn(tag)):
            tblPr.remove(el)
    tblPr.append(parse_xml(_BORDER_TBL))
    tblPr.append(parse_xml('<w:tblLayout {ns} w:type="fixed"/>'.format(ns=_NS)))


def _header_cell(cell, text: str, size_pt: int = 9) -> None:
    _shade(cell, BLUE_BG)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(p, text, bold=True, size_pt=size_pt)


def _risk_color(level: str) -> str:
    level = level.lower()
    if level == "extreme":
        return EXTREME_BG
    elif level == "high":
        return HIGH_BG
    elif level == "medium":
        return MED_BG
    else:
        return LOW_BG


def _risk_text_color(level: str) -> RGBColor:
    level = level.lower()
    if level in ("extreme", "high"):
        return WHITE
    return BLACK


def _matrix_level(score: int) -> str:
    if score >= 17:
        return "Extreme"
    elif score >= 10:
        return "High"
    elif score >= 5:
        return "Medium"
    else:
        return "Low"


def _add_heading(doc, text: str, size_pt: int = 14, space_before: int = 12) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(4)
    _run(p, text, bold=True, size_pt=size_pt)


# ── Main render ──────────────────────────────────────────────────────────────

def render_ra_document(
    hazards: list[dict],
    project_meta: dict,
    inference: dict,
    jurisdiction: str = "AU",
    ca_province: str = "",
) -> bytes:
    """
    Render a Risk Assessment as a Word .docx document.

    Args:
        hazards:       list of hazard dicts (from infer_to_dict_ra)
        project_meta:  dict with project_name, site_address, principal_contractor, etc.
        inference:     dict from infer_to_dict()
        jurisdiction:  jurisdiction code (AU, NZ, UK, US, CA)
        ca_province:   optional CA province code (ON, BC, AB, QC)

    Returns:
        bytes — the rendered .docx file content.
    """
    from core.jurisdictions import get_jurisdiction

    jur = get_jurisdiction(jurisdiction, ca_province=ca_province)
    doc = Document()

    # Page: A4 portrait, 1.5cm margins
    section = doc.sections[0]
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.left_margin = Cm(1.5)
    section.right_margin = Cm(1.5)
    section.top_margin = Cm(1.5)
    section.bottom_margin = Cm(1.5)

    # ── Cover / Header ───────────────────────────────────────────────────
    proj_name = project_meta.get("project_name", "Untitled Project")
    site_address = project_meta.get("site_address", "")
    pc = project_meta.get("principal_contractor", "")
    doc_date = project_meta.get("date", date.today().strftime(jur["date_format"]))
    version = project_meta.get("version", "1.0")

    # Title
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(title_p, "RISK ASSESSMENT", bold=True, size_pt=22)

    subtitle_p = doc.add_paragraph()
    subtitle_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(subtitle_p, proj_name, bold=True, size_pt=16)

    # Cover table
    cover_table = doc.add_table(rows=6, cols=2)
    _format_table(cover_table)
    cover_data = [
        ("Company / PCBU", pc),
        ("Project Name", proj_name),
        ("Site Address", site_address),
        ("Assessment Date", doc_date),
        ("Prepared By", project_meta.get("manager", "")),
        ("Document Number", f"RA-{proj_name[:30]}-{doc_date.replace('/', '')}-V{version.replace('.', '').zfill(2)}"),
    ]
    for i, (label, value) in enumerate(cover_data):
        _shade(cover_table.cell(i, 0), BLUE_BG)
        _run(cover_table.cell(i, 0).paragraphs[0], label, bold=True, size_pt=10)
        _run(cover_table.cell(i, 1).paragraphs[0], value, size_pt=10)
        cover_table.cell(i, 0).width = Cm(5)
        cover_table.cell(i, 1).width = Cm(12)

    # ── Section 1: Project Description ───────────────────────────────────
    _add_heading(doc, "1. Project Description")
    description = project_meta.get("description", project_meta.get("work_activity", proj_name))
    desc_p = doc.add_paragraph()
    _run(desc_p, description, size_pt=10)

    # ── Section 2: Assessment Team ───────────────────────────────────────
    _add_heading(doc, "2. Assessment Team")
    team_table = doc.add_table(rows=4, cols=4)
    _format_table(team_table)
    team_headers = ["Name", "Role", "Signature", "Date"]
    for i, h in enumerate(team_headers):
        _header_cell(team_table.rows[0].cells[i], h)
    # Pre-fill first row with manager if available
    manager = project_meta.get("manager", "")
    if manager:
        _run(team_table.cell(1, 0).paragraphs[0], manager, size_pt=9)
        _run(team_table.cell(1, 1).paragraphs[0], "Assessor", size_pt=9)

    # ── Section 3: Legislation and Standards ─────────────────────────────
    _add_heading(doc, "3. Applicable Legislation and Standards")
    leg_parts = jur["base_legislation_string"].split(" \u2014 ")
    jur_notes = inference.get("jurisdiction_notes", [])
    reg_notes = inference.get("regulatory_notes", [])
    all_leg = leg_parts + [n for n in jur_notes + reg_notes
                           if n.strip() not in leg_parts]
    for item in all_leg:
        item = item.strip()
        if not item:
            continue
        bp = doc.add_paragraph()
        bp.paragraph_format.space_before = Pt(1)
        bp.paragraph_format.space_after = Pt(1)
        _run(bp, "\u2022  " + item, size_pt=9)

    # ── Section 4: Risk Rating Matrix ────────────────────────────────────
    _add_heading(doc, "4. Risk Rating Matrix")

    LIKELIHOOD = ["Rare", "Unlikely", "Possible", "Likely", "Almost Certain"]
    CONSEQUENCE = ["Insignificant", "Minor", "Moderate", "Major", "Catastrophic"]

    # 6 rows (header + 5 likelihood), 6 cols (header + 5 consequence)
    matrix = doc.add_table(rows=7, cols=6)
    _format_table(matrix)

    # Top-left corner: empty
    _shade(matrix.cell(0, 0), BLUE_BG)

    # Header row: consequences
    _shade(matrix.cell(0, 0), BLUE_BG)
    _run(matrix.cell(0, 0).paragraphs[0], "", size_pt=8)
    # Consequence header spanning row 0
    for ci, c in enumerate(CONSEQUENCE):
        cell = matrix.cell(0, ci + 1)
        _shade(cell, BLUE_BG)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(p, f"{c}\n({ci + 1})", bold=True, size_pt=7)

    # Sub-header row for "Consequence →"
    _shade(matrix.cell(1, 0), BLUE_BG)
    p = matrix.cell(1, 0).paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(p, "Likelihood \u2193", bold=True, size_pt=8)
    for ci in range(5):
        cell = matrix.cell(1, ci + 1)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Likelihood rows
    for li, l in enumerate(LIKELIHOOD):
        row_idx = li + 2
        cell0 = matrix.cell(row_idx, 0)
        _shade(cell0, BLUE_BG)
        p0 = cell0.paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(p0, f"{l}\n({li + 1})", bold=True, size_pt=7)

        for ci in range(5):
            score = (li + 1) * (ci + 1)
            level = _matrix_level(score)
            cell = matrix.cell(row_idx, ci + 1)
            _shade(cell, _risk_color(level))
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _run(p, str(score), bold=True, color=_risk_text_color(level), size_pt=9)

    # ── Section 5: Hazard Register ───────────────────────────────────────
    _add_heading(doc, "5. Hazard Register")

    # Switch to landscape for the wide table
    new_section = doc.add_section(2)  # continuous section break
    new_section.orientation = WD_ORIENT.LANDSCAPE
    new_section.page_width = Mm(297)
    new_section.page_height = Mm(210)
    new_section.left_margin = Cm(1)
    new_section.right_margin = Cm(1)
    new_section.top_margin = Cm(1)
    new_section.bottom_margin = Cm(1)

    # Hazard register table
    hz_headers = [
        "No.", "Hazard", "Who is\nat Risk",
        "L", "C", "L\u00d7C", "Risk\nLevel",
        "Control Measures",
        "Res.\nRisk", "Resp."
    ]
    hz_widths_cm = [1.2, 4.0, 2.5, 1.0, 1.0, 1.0, 1.8, 11.0, 1.5, 1.7]

    hz_table = doc.add_table(rows=1 + len(hazards), cols=10)
    _format_table(hz_table)

    # Header row
    for i, h in enumerate(hz_headers):
        cell = hz_table.rows[0].cells[i]
        _header_cell(cell, h, size_pt=8)
        cell.width = Cm(hz_widths_cm[i])

    # Data rows
    for idx, haz in enumerate(hazards):
        row = hz_table.rows[idx + 1]
        for ci in range(10):
            row.cells[ci].width = Cm(hz_widths_cm[ci])

        # No.
        _run(row.cells[0].paragraphs[0], str(idx + 1), size_pt=8)
        row.cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Hazard
        _run(row.cells[1].paragraphs[0], haz.get("hazard", ""), size_pt=8)

        # Who at risk
        _run(row.cells[2].paragraphs[0], haz.get("who_at_risk", "Workers"), size_pt=8)

        # Likelihood
        _run(row.cells[3].paragraphs[0], str(haz.get("likelihood", "")), size_pt=8)
        row.cells[3].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Consequence
        _run(row.cells[4].paragraphs[0], str(haz.get("consequence", "")), size_pt=8)
        row.cells[4].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Risk rating
        rating = haz.get("risk_rating", 0)
        level = haz.get("risk_level", "Low")
        _shade(row.cells[5], _risk_color(level))
        p5 = row.cells[5].paragraphs[0]
        p5.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(p5, str(rating), bold=True, color=_risk_text_color(level), size_pt=9)

        # Risk level
        _shade(row.cells[6], _risk_color(level))
        p6 = row.cells[6].paragraphs[0]
        p6.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(p6, level, bold=True, color=_risk_text_color(level), size_pt=8)

        # Control measures
        controls = haz.get("controls", {})
        ctrl_cell = row.cells[7]
        first = True
        for cat, label in [("engineering", "Engineering:"), ("admin", "Admin:"), ("ppe", "PPE:")]:
            items = controls.get(cat, [])
            if not items:
                continue
            p = ctrl_cell.paragraphs[0] if first else ctrl_cell.add_paragraph()
            first = False
            _run(p, label + " ", bold=True, size_pt=8)
            _run(p, " \u2014 ".join(items), size_pt=8)

        # Residual risk
        res_risk = haz.get("residual_risk", 0)
        res_level = haz.get("residual_level", "Low")
        _shade(row.cells[8], _risk_color(res_level))
        p8 = row.cells[8].paragraphs[0]
        p8.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(p8, f"{res_risk}\n({res_level[0]})", bold=True, color=_risk_text_color(res_level), size_pt=8)

        # Responsible
        _run(row.cells[9].paragraphs[0], haz.get("responsible", "Supervisor"), size_pt=8)

    # ── Section 6: Review and Sign Off ───────────────────────────────────
    # Switch back to portrait
    final_section = doc.add_section(2)
    final_section.orientation = WD_ORIENT.PORTRAIT
    final_section.page_width = Mm(210)
    final_section.page_height = Mm(297)
    final_section.left_margin = Cm(1.5)
    final_section.right_margin = Cm(1.5)
    final_section.top_margin = Cm(1.5)
    final_section.bottom_margin = Cm(1.5)

    _add_heading(doc, "6. Review and Sign Off")

    review_p = doc.add_paragraph()
    _run(review_p, "This Risk Assessment must be reviewed:", bold=True, size_pt=10)

    triggers = [
        "Before work commences",
        "After any incident, near miss, or change in conditions",
        "When new hazards are identified",
        "When work methods or equipment change",
        "At a minimum every 12 months",
    ]
    for t in triggers:
        tp = doc.add_paragraph()
        tp.paragraph_format.space_before = Pt(1)
        tp.paragraph_format.space_after = Pt(1)
        _run(tp, "\u2022  " + t, size_pt=9)

    # Sign-off table
    doc.add_paragraph()  # spacer
    signoff = doc.add_table(rows=4, cols=3)
    _format_table(signoff)
    signoff_headers = ["Prepared By", "Reviewed By", "Approved By"]
    for i, h in enumerate(signoff_headers):
        _header_cell(signoff.rows[0].cells[i], h)

    signoff_rows = ["Name:", "Signature:", "Date:"]
    for ri, label in enumerate(signoff_rows):
        for ci in range(3):
            _run(signoff.cell(ri + 1, ci).paragraphs[0], label, size_pt=9, italic=True, color=GREY)

    # ── Footer ───────────────────────────────────────────────────────────
    import re as _re
    safe_name = _re.sub(r'[\\/:*?"<>|]', "-", proj_name)[:40]
    footer_date = doc_date.replace("/", "").replace("-", "")
    _JUR_FOOTER = {
        "AU": "WHS Act 2011", "NZ": "HSWA 2015", "UK": "CDM 2015",
        "US": "OSHA 29 CFR 1926", "CA": "Canada Labour Code Part II",
    }
    jur_ref = _JUR_FOOTER.get(jurisdiction, "")
    footer_text = f"RA-{safe_name}-{footer_date}-V01"
    if jur_ref:
        footer_text += f" | {jur_ref}"

    for sec in doc.sections:
        footer = sec.footer
        footer.is_linked_to_previous = False
        if footer.paragraphs:
            fp = footer.paragraphs[0]
            fp.clear()
        else:
            fp = footer.add_paragraph()
        fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
        _run(fp, footer_text, size_pt=9)

    # ── Save and return ──────────────────────────────────────────────────
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()

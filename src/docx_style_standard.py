"""AuditCo Risk Register Document Style Standard.

Reusable font, colour, and formatting constants for all Word document
generation across Gatekeeper projects.  Import this module to ensure
consistent branding and WHS-compliant colour coding.

Usage:
    from src.docx_style_standard import (
        apply_document_font,
        RISK_BG, RISK_FONT, HEADER_BG, HEADER_FONT, BLACK,
        set_cell_shading, set_row_shading, format_header_cell,
        add_risk_cell, add_body_cell, set_col_widths, set_cell_margins,
    )
"""

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml


# ── Document Font ──────────────────────────────────────────────────
FONT_NAME = "Arial"
FONT_SIZE_BODY = Pt(9)
FONT_SIZE_CELL = Pt(8)

# ── Text Colours ───────────────────────────────────────────────────
BLACK = RGBColor(0x00, 0x00, 0x00)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

# ── Risk Rating Cell Backgrounds ───────────────────────────────────
RISK_BG = {
    "Critical": "FF0000",
    "High":     "FF0000",
    "Medium":   "FFFF00",
    "Low":      "00FF00",
}

# ── Risk Rating Font Colours (contrast against background) ─────────
RISK_FONT = {
    "Critical": WHITE,   # white on red
    "High":     WHITE,   # white on red
    "Medium":   BLACK,   # black on yellow
    "Low":      BLACK,   # black on green
}

# ── Table Header Row ──────────────────────────────────────────────
HEADER_BG = "DBE5F1"
HEADER_FONT = BLACK

# ── Alternate Row Shading ─────────────────────────────────────────
ALT_ROW_BG = "F2F2F2"


# ── Helpers ────────────────────────────────────────────────────────

def apply_document_font(doc: Document) -> None:
    """Set Arial as the font for Normal, Heading, and List styles."""
    for style_name in [
        "Normal", "Heading 1", "Heading 2", "Heading 3",
        "List Bullet", "List Number",
    ]:
        try:
            style = doc.styles[style_name]
            style.font.name = FONT_NAME
            # Set the east-asian / complex-script font as well
            rpr = style.element.get_or_add_rPr()
            rfonts = rpr.find(qn("w:rFonts"))
            if rfonts is None:
                rfonts = parse_xml(
                    f'<w:rFonts {nsdecls("w")} '
                    f'w:ascii="{FONT_NAME}" w:hAnsi="{FONT_NAME}" '
                    f'w:cs="{FONT_NAME}" w:eastAsia="{FONT_NAME}"/>'
                )
                rpr.insert(0, rfonts)
            else:
                rfonts.set(qn("w:ascii"), FONT_NAME)
                rfonts.set(qn("w:hAnsi"), FONT_NAME)
                rfonts.set(qn("w:cs"), FONT_NAME)
                rfonts.set(qn("w:eastAsia"), FONT_NAME)
        except KeyError:
            pass  # style not present in this document

    # Ensure the default document font is set
    style = doc.styles["Normal"]
    style.font.name = FONT_NAME
    style.font.size = FONT_SIZE_BODY


def risk_level(rating_str: str) -> str:
    """Extract the risk level word from a rating string like 'Critical (5)'."""
    for level in ("Critical", "High", "Medium", "Low"):
        if level in rating_str:
            return level
    return "Low"


def set_cell_shading(cell, hex_color: str) -> None:
    """Apply background shading to a table cell."""
    shading = parse_xml(
        f'<w:shd {nsdecls("w")} w:fill="{hex_color}" w:val="clear"/>'
    )
    cell._tc.get_or_add_tcPr().append(shading)


def set_row_shading(row, hex_color: str) -> None:
    """Apply background shading to all cells in a row."""
    for cell in row.cells:
        set_cell_shading(cell, hex_color)


def format_header_cell(cell, text: str) -> None:
    """Format a header cell with standard header background and font."""
    set_cell_shading(cell, HEADER_BG)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.bold = True
    run.font.name = FONT_NAME
    run.font.size = FONT_SIZE_CELL
    run.font.color.rgb = HEADER_FONT


def add_risk_cell(cell, text: str) -> None:
    """Format a risk rating cell with colour-coded background."""
    level = risk_level(text)
    set_cell_shading(cell, RISK_BG.get(level, RISK_BG["Low"]))
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.bold = True
    run.font.name = FONT_NAME
    run.font.size = FONT_SIZE_CELL
    run.font.color.rgb = RISK_FONT.get(level, BLACK)


def add_body_cell(cell, text: str, bold: bool = False, size: int = 8) -> None:
    """Add text to a body cell with Arial font."""
    p = cell.paragraphs[0]
    run = p.add_run(text)
    run.bold = bold
    run.font.name = FONT_NAME
    run.font.size = Pt(size)
    run.font.color.rgb = BLACK


def set_col_widths(table, widths: list) -> None:
    """Set column widths in cm."""
    for row in table.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)


def set_cell_margins(table, top=40, bottom=40, left=60, right=60) -> None:
    """Set cell margins for the whole table (in twentieths of a point)."""
    for row in table.rows:
        for cell in row.cells:
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            tcMar = parse_xml(
                f'<w:tcMar {nsdecls("w")}>'
                f'  <w:top w:w="{top}" w:type="dxa"/>'
                f'  <w:bottom w:w="{bottom}" w:type="dxa"/>'
                f'  <w:start w:w="{left}" w:type="dxa"/>'
                f'  <w:end w:w="{right}" w:type="dxa"/>'
                f"</w:tcMar>"
            )
            tcPr.append(tcMar)

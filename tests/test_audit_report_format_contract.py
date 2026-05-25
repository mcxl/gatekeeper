"""SSA Audit Report — Format Contract Regression Test.

This test PINS every constant in ``pims/services/ssa_format_constants.py``
to the exact value the format contract specifies. Any change to a constant
breaks this test until both the constant AND the contract document
(``docs/SSA_FORMAT_CONTRACT.md``) AND the changelog entry are updated.

This is layer 4 of the format lockdown:
- L1: Settings file (pims/services/ssa_format_constants.py)
- L2: Rules document (docs/SSA_FORMAT_CONTRACT.md)
- L3: Claude skill (~/.claude/skills/ssa-audit-format/SKILL.md)
- L4: This test

To CORRECTLY change a contract rule:
1. Operator approves the change.
2. Update the rule in ``docs/SSA_FORMAT_CONTRACT.md`` + add a changelog
   entry with date + rationale.
3. Update the constant in ``pims/services/ssa_format_constants.py``.
4. Update the corresponding assertion in THIS file.
5. All four changes in a SINGLE commit.

To INCORRECTLY change a contract rule (i.e. silently): you'll trip this
test and the build fails. That's the point.

----------------------------------------------------------------------
Contract version: 2026-05-25 (initial lock)
----------------------------------------------------------------------
"""
from __future__ import annotations

import re

from pims.services import ssa_format_constants as fmt


# ============================================================================
# R1 — Font: Aptos everywhere
# ============================================================================

def test_R1_body_font_name():
    assert fmt.BODY_FONT_NAME == "Aptos"


def test_R1_body_font_size_pt():
    assert fmt.BODY_FONT_PT == 10.0


# ============================================================================
# R2 — Client display name map
# ============================================================================

def test_R2_rpd_display_name():
    assert fmt.CLIENT_DISPLAY_NAMES["RPD"] == "Robertson's Remedial and Painting"


def test_R2_default_display_name():
    assert fmt.DEFAULT_CLIENT_DISPLAY_NAME == "Robertson's Remedial and Painting"


# ============================================================================
# R3 — Running header (page 2+)
# ============================================================================

def test_R3_header_table_width_cm():
    assert fmt.HEADER_TABLE_WIDTH_CM == 16.0


def test_R3_header_text_col_cm():
    assert fmt.HEADER_TEXT_COL_CM == 13.0


def test_R3_header_logo_col_cm():
    assert fmt.HEADER_LOGO_COL_CM == 3.0


def test_R3_text_plus_logo_columns_equal_table_width():
    """Sanity: column widths must add up to table width."""
    assert (
        fmt.HEADER_TEXT_COL_CM + fmt.HEADER_LOGO_COL_CM
        == fmt.HEADER_TABLE_WIDTH_CM
    )


def test_R3_header_logo_width_cm():
    assert fmt.HEADER_LOGO_WIDTH_CM == 2.5


def test_R3_header_text_font_pt():
    assert fmt.HEADER_TEXT_FONT_PT == 10


def test_R3_header_text_color_rgb():
    assert fmt.HEADER_TEXT_COLOR_RGB == (0x40, 0x40, 0x40)


def test_R3_header_title_suffix():
    assert fmt.HEADER_TITLE_SUFFIX == " – Site Safety Audit Report"


def test_R3_header_table_width_twips_matches_cm():
    """16 cm in twips (1 cm = 567 twips) = 9072."""
    assert fmt.HEADER_TABLE_WIDTH_TWIPS == 9072


def test_R3_logo_asset_relative_path():
    assert fmt.LOGO_ASSET_RELATIVE_PATH == "pims/assets/AuditCo.png"


# ============================================================================
# R4 — Body section footer position
# ============================================================================

def test_R4_body_bottom_margin_cm():
    assert fmt.BODY_BOTTOM_MARGIN_CM == 2.0


def test_R4_footer_distance_cm():
    assert fmt.FOOTER_DISTANCE_CM == 0.75


def test_R4_gap_above_footer_is_about_1_25_cm():
    """Sanity: bottom margin - footer distance should give the visible
    gap between body content and footer text."""
    gap = fmt.BODY_BOTTOM_MARGIN_CM - fmt.FOOTER_DISTANCE_CM
    assert gap == 1.25


# ============================================================================
# R5 — Table borders policy
# ============================================================================

def test_R5_border_color_light_grey():
    assert fmt.BORDER_COLOR_LIGHT_GREY == "BFBFBF"


def test_R5_border_size_half_pt():
    """4 eighths of a point = 0.5 pt."""
    assert fmt.BORDER_SIZE_HALF_PT == "4"


# ============================================================================
# R6 — Observations Register column widths
# ============================================================================

def test_R6_register_col_widths_cm_exact():
    assert fmt.REGISTER_COL_WIDTHS_CM == (1.0, 1.75, 1.75, 2.5, 3.0, 3.5, 3.0)


def test_R6_register_col_widths_total_165_cm():
    """A4 printable area ~16.5 cm — exactly at the limit."""
    assert sum(fmt.REGISTER_COL_WIDTHS_CM) == 16.5


def test_R6_register_headers_exact():
    assert fmt.REGISTER_HEADERS == (
        "#", "Status", "CCVS", "Observation", "Finding",
        "Recommendation", "Photo",
    )


def test_R6_register_header_count_matches_widths_count():
    assert len(fmt.REGISTER_HEADERS) == len(fmt.REGISTER_COL_WIDTHS_CM)


def test_R6_register_header_fill():
    assert fmt.REGISTER_HEADER_FILL_HEX == "1F3864"  # deep navy


def test_R6_register_header_fg():
    assert fmt.REGISTER_HEADER_FG_HEX == "FFFFFF"


def test_R6_register_alt_fill():
    assert fmt.REGISTER_ALT_FILL_HEX == "F2F2F2"


def test_R6_register_photo_width_cm():
    assert fmt.REGISTER_PHOTO_WIDTH_CM == 2.2


# ============================================================================
# R7 — "Observations Register" section heading style
# ============================================================================

def test_R7_register_heading_text():
    assert fmt.REGISTER_HEADING_TEXT == "Observations Register"


def test_R7_register_heading_font_pt():
    assert fmt.REGISTER_HEADING_FONT_PT == 16


def test_R7_register_heading_bold():
    assert fmt.REGISTER_HEADING_BOLD is True


def test_R7_register_heading_color_matches_table_header_fill():
    """The heading color is the same deep navy as the table's header row
    fill — they're visually anchored together."""
    r, g, b = fmt.REGISTER_HEADING_COLOR_RGB
    assert (r, g, b) == (0x1F, 0x38, 0x64)
    assert f"{r:02X}{g:02X}{b:02X}" == fmt.REGISTER_HEADER_FILL_HEX


def test_R7_register_heading_space_before_pt():
    assert fmt.REGISTER_HEADING_SPACE_BEFORE_PT == 18


def test_R7_register_heading_space_after_pt():
    assert fmt.REGISTER_HEADING_SPACE_AFTER_PT == 12


# ============================================================================
# R8 — Email draft (.eml)
# ============================================================================

def test_R8_email_recipients_rpd_has_both():
    assert "matt@rpd.net.au" in fmt.EMAIL_RECIPIENTS_RPD
    assert "nick@rpd.net.au" in fmt.EMAIL_RECIPIENTS_RPD


def test_R8_email_recipients_uses_display_names():
    assert "Matthew McCarthy" in fmt.EMAIL_RECIPIENTS_RPD
    assert "Nick Vuckovic" in fmt.EMAIL_RECIPIENTS_RPD


def test_R8_email_recipients_comma_separated():
    """RFC 5322 uses comma, not semicolon."""
    assert ", " in fmt.EMAIL_RECIPIENTS_RPD
    assert ";" not in fmt.EMAIL_RECIPIENTS_RPD


def test_R8_email_greeting_target():
    assert fmt.EMAIL_GREETING_TARGET == "Matt and Nick"


def test_R8_email_x_unsent_header():
    """'1' = Outlook 2016+ 'open as editable draft' hint."""
    assert fmt.EMAIL_X_UNSENT_HEADER == "1"


def test_R8_email_attachment_ext_is_pdf():
    assert fmt.EMAIL_ATTACHMENT_EXT == ".pdf"


def test_R8_summary_keeps_only_ncr_line():
    assert fmt.EMAIL_SUMMARY_KEEP_LINES_STARTING_WITH == (
        "• Non-conformances (NCR):",
    )


def test_R8_summary_drops_observations_conditional_compliant():
    assert set(fmt.EMAIL_SUMMARY_DROP_LINES_STARTING_WITH) == {
        "• Observations recorded:",
        "• Conditional:",
        "• Compliant:",
    }


# ============================================================================
# R9 — Output file naming
# ============================================================================

def test_R9_folder_regex_matches_canonical_folder():
    rx = re.compile(fmt.FOLDER_NAME_REGEX)
    m = rx.match("2026-05-22-RPD-03")
    assert m is not None
    assert m.group(1) == "2026-05-22"
    assert m.group(2) == "RPD"
    assert m.group(3) == "03"


def test_R9_folder_regex_supports_sdg():
    rx = re.compile(fmt.FOLDER_NAME_REGEX)
    m = rx.match("2026-04-11-SDG-12")
    assert m is not None
    assert m.group(2) == "SDG"


def test_R9_folder_regex_rejects_noncanonical():
    rx = re.compile(fmt.FOLDER_NAME_REGEX)
    for bad in (
        "2026-05-22-RPD",        # no NN
        "2026-05-22-RPD-3",      # NN not zero-padded
        "2026-5-22-RPD-03",      # date not zero-padded
        "site-2026-05-22-RPD-03",  # prefix
        "2026-05-22-XYZ-03",     # unknown client
    ):
        assert rx.match(bad) is None, f"should reject {bad!r}"


def test_R9_docx_name_template():
    name = fmt.REPORT_DOCX_NAME_TEMPLATE.format(date="2026-05-22", nn="03")
    assert name == "RPD_SSA_Audit_Report_2026-05-22-03.docx"


def test_R9_pdf_name_template():
    name = fmt.REPORT_PDF_NAME_TEMPLATE.format(date="2026-05-22", nn="03")
    assert name == "RPD_SSA_Audit_Report_2026-05-22-03.pdf"


def test_R9_zip_name_template():
    name = fmt.REPORT_ZIP_NAME_TEMPLATE.format(date="2026-05-22", nn="03")
    assert name == "RPD_SSA_Audit_Reports_2026-05-22-03.zip"


def test_R9_eml_name_template():
    name = fmt.EMAIL_EML_NAME_TEMPLATE.format(
        stamp="260522", site_slug="53-Killeaton-Street-St-Ives",
    )
    assert name == "Email_Draft_260522_53-Killeaton-Street-St-Ives.eml"


def test_R9_docx_and_pdf_basenames_match():
    """The .pdf is a sibling of the .docx with the same basename — only
    the extension differs."""
    docx = fmt.REPORT_DOCX_NAME_TEMPLATE.format(date="2026-05-22", nn="03")
    pdf = fmt.REPORT_PDF_NAME_TEMPLATE.format(date="2026-05-22", nn="03")
    assert docx.rsplit(".", 1)[0] == pdf.rsplit(".", 1)[0]


# ============================================================================
# Cross-rule integration checks
# ============================================================================

def test_constants_module_imports_from_contract_path():
    """Sanity: the contract document referenced by the skill should exist
    at the path the skill claims."""
    from pathlib import Path
    contract_path = (
        Path(__file__).resolve().parents[1] / "docs" / "SSA_FORMAT_CONTRACT.md"
    )
    assert contract_path.exists(), f"contract missing at {contract_path}"


def test_logo_asset_present_at_relative_path():
    """The logo path declared in constants must point at a real PNG."""
    from pathlib import Path
    logo = (
        Path(__file__).resolve().parents[1] / fmt.LOGO_ASSET_RELATIVE_PATH
    )
    assert logo.exists(), f"logo missing at {logo}"
    assert logo.suffix.lower() == ".png"

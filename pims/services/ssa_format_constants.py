"""SSA Audit Report — Format Constants (single source of truth).

Every magic number, font name, color, spacing value, and string template
that determines the visual appearance of the rendered audit report lives
in this module. Other modules MUST import from here rather than
hardcoding values.

This is the dashboard. Change a number here -> change the format.
Touch a magic value anywhere else -> it falls out of sync with the
operator-locked specification.

----------------------------------------------------------------------
**ANY CHANGE TO THIS FILE REQUIRES READING ``docs/SSA_FORMAT_CONTRACT.md``
FIRST AND GETTING OPERATOR APPROVAL.** The constants below encode
decisions made by Alan Richardson during the
2026-05-25 format lockdown session. Silent drift = formatting regression.
----------------------------------------------------------------------

See also:
- ``docs/SSA_FORMAT_CONTRACT.md`` — plain-English rules + rationale
- ``~/.claude/skills/ssa-audit-format/SKILL.md`` — Claude session guard
- ``tests/fixtures/golden_audit_report.docx`` — regression baseline
"""
from __future__ import annotations

# =============================================================================
# R1. Font — Aptos everywhere
# =============================================================================
BODY_FONT_NAME = "Aptos"
BODY_FONT_PT = 10.0


# =============================================================================
# R2. Client display name map
#   Folder code (RPD/SDG/...) -> human-readable name shown in the running
#   header and elsewhere.
# =============================================================================
CLIENT_DISPLAY_NAMES: dict[str, str] = {
    "RPD": "Robertson's Remedial and Painting",
}
DEFAULT_CLIENT_DISPLAY_NAME = "Robertson's Remedial and Painting"


# =============================================================================
# R3. Running header (page 2+) — branded 2-cell borderless table
# =============================================================================
HEADER_TABLE_WIDTH_CM = 16.0
HEADER_TEXT_COL_CM = 13.0
HEADER_LOGO_COL_CM = 3.0
HEADER_LOGO_WIDTH_CM = 2.5
HEADER_TEXT_FONT_PT = 10
HEADER_TEXT_COLOR_RGB = (0x40, 0x40, 0x40)  # dark grey
HEADER_TITLE_SUFFIX = " – Site Safety Audit Report"  # appended after client name
# 16 cm in twips (1/20 of a point, dxa unit). 1 cm = 567 twips.
HEADER_TABLE_WIDTH_TWIPS = 9072


# =============================================================================
# R4. Body section footer position
# =============================================================================
BODY_BOTTOM_MARGIN_CM = 2.0
FOOTER_DISTANCE_CM = 0.75


# =============================================================================
# R5. Table borders policy
#   Default: every body-level table renders with invisible borders.
#   Exception: the Observations Register gets solid light-grey borders.
# =============================================================================
BORDER_COLOR_LIGHT_GREY = "BFBFBF"
BORDER_SIZE_HALF_PT = "4"  # eighths of a point; 4 = 0.5pt


# =============================================================================
# R6. Observations Register — column widths (cm)
#   Order: #, Status, CCVS, Observation, Finding, Recommendation, Photo
#   Total: 16.5 cm (A4 printable area ~16.5 cm)
# =============================================================================
REGISTER_COL_WIDTHS_CM = (1.0, 1.75, 1.75, 2.5, 3.0, 3.5, 3.0)
REGISTER_HEADERS = ("#", "Status", "CCVS", "Observation", "Finding",
                    "Recommendation", "Photo")
REGISTER_PHOTO_WIDTH_CM = 2.2

# Header row of the register table
REGISTER_HEADER_FILL_HEX = "1F3864"  # deep navy
REGISTER_HEADER_FG_HEX = "FFFFFF"
# Alternating row fill (zebra striping)
REGISTER_ALT_FILL_HEX = "F2F2F2"


# =============================================================================
# R7. "Observations Register" section heading style
# =============================================================================
REGISTER_HEADING_TEXT = "Observations Register"
REGISTER_HEADING_FONT_PT = 16
REGISTER_HEADING_BOLD = True
REGISTER_HEADING_COLOR_RGB = (0x1F, 0x38, 0x64)  # deep navy, matches header fill
REGISTER_HEADING_SPACE_BEFORE_PT = 18
REGISTER_HEADING_SPACE_AFTER_PT = 12


# =============================================================================
# R8. Email draft (.eml)
# =============================================================================
EMAIL_RECIPIENTS_RPD = (
    "Matthew McCarthy <matt@rpd.net.au>, "
    "Nick Vuckovic <nick@rpd.net.au>"
)
EMAIL_GREETING_TARGET = "Matt and Nick"
EMAIL_X_UNSENT_HEADER = "1"  # Outlook 2016+ "open as draft" hint
EMAIL_ATTACHMENT_EXT = ".pdf"
# Summary section content policy: NCR-only (operator: noise reduction)
EMAIL_SUMMARY_KEEP_LINES_STARTING_WITH = ("• Non-conformances (NCR):",)
EMAIL_SUMMARY_DROP_LINES_STARTING_WITH = (
    "• Observations recorded:",
    "• Conditional:",
    "• Compliant:",
)


# =============================================================================
# R9. Output file naming
# =============================================================================
# Folder name pattern: YYYY-MM-DD-<CLIENT>-NN
FOLDER_NAME_REGEX = r"^(\d{4}-\d{2}-\d{2})-(RPD|SDG)-(\d{2})$"
# Output file templates (use .format(date=..., nn=...))
REPORT_DOCX_NAME_TEMPLATE = "RPD_SSA_Audit_Report_{date}-{nn}.docx"
REPORT_PDF_NAME_TEMPLATE = "RPD_SSA_Audit_Report_{date}-{nn}.pdf"
REPORT_ZIP_NAME_TEMPLATE = "RPD_SSA_Audit_Reports_{date}-{nn}.zip"
EMAIL_EML_NAME_TEMPLATE = "Email_Draft_{stamp}_{site_slug}.eml"


# =============================================================================
# Asset paths (resolved relative to gatekeeper repo root)
# =============================================================================
LOGO_ASSET_RELATIVE_PATH = "pims/assets/AuditCo.png"

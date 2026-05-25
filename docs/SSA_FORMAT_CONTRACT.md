# SSA Audit Report — Format Contract

**Status:** LOCKED as of **2026-05-25**
**Owner:** Alan Richardson (`alan.richardson@mcxi.com.au`)
**Implementation:** `pims/services/ssa_format_constants.py`
**Regression test:** `tests/test_audit_report_format_contract.py` (golden file at `tests/fixtures/golden_audit_report.docx`)
**Claude session guard:** `~/.claude/skills/ssa-audit-format/SKILL.md`

---

## Purpose

This document is the **single human-readable source of truth** for how the SSA audit report .docx, sibling .pdf, and email .eml must look. Every visual decision below was made deliberately by the operator after one or more rounds of review against actual rendered output.

**The rules below are LOCKED.** Any code change that affects the visual output of an audit report MUST:

1. Be approved by the operator (Alan).
2. Update the corresponding rule in this document with a dated entry in the changelog at the bottom.
3. Update `pims/services/ssa_format_constants.py` in the same commit.
4. Regenerate `tests/fixtures/golden_audit_report.docx` in the same commit.
5. Pass the contract regression test.

Silent drift = formatting regression. The whole point of this contract is to prevent the next session (Claude or human) from quietly breaking the look you spent hours getting right.

---

## The rules

### R1 — Font: Aptos everywhere

Every glyph in the rendered docx must source as **Aptos**. Recipient-side substitution (no Office 365) is acceptable, but the source must contain no leftover Calibri / Arial / Times.

Enforcement: four layers.
- `_BODY_FONT = "Aptos"` drives explicit run-level rFonts.
- `_apply_body_typography` walks every body run.
- `_enforce_aptos_everywhere` walks every run including cover.
- `_patch_theme_and_styles_aptos` post-build patches `theme1.xml` and `styles.xml`.

Constants: `BODY_FONT_NAME`, `BODY_FONT_PT`.

### R2 — Client display name map

The folder code (3 letters: `RPD`, `SDG`, …) expands to a human-readable name shown in the running header and elsewhere.

Current map:
- `RPD` → `Robertson's Remedial and Painting`

New clients added by appending to `CLIENT_DISPLAY_NAMES` in the constants module.

Constants: `CLIENT_DISPLAY_NAMES`, `DEFAULT_CLIENT_DISPLAY_NAME`.

### R3 — Running header (page 2+)

A branded two-cell borderless table at the top of every page after the cover.

- Layout: 2 columns × 1 row, fixed table layout, total width 16 cm.
- Left cell (13 cm): client display name + " – Site Safety Audit Report"
- Right cell (3 cm): AuditCo logo, 2.5 cm wide
- Text: Aptos 10pt, dark grey (`#404040`)
- Borders: invisible on all six edges
- Suppressed on cover page (section 0 first page)
- All body sections (section 1+) have `different_first_page_header_footer = False` so every body page gets the header. First-page header explicitly populated to prevent inheriting cover's first-page design (the orange anchored shapes).

Constants: `HEADER_TABLE_WIDTH_CM`, `HEADER_TEXT_COL_CM`, `HEADER_LOGO_COL_CM`, `HEADER_LOGO_WIDTH_CM`, `HEADER_TEXT_FONT_PT`, `HEADER_TEXT_COLOR_RGB`, `HEADER_TITLE_SUFFIX`, `HEADER_TABLE_WIDTH_TWIPS`, `LOGO_ASSET_RELATIVE_PATH`.

### R4 — Body section footer position

Body section page margins:
- Bottom margin: **2.0 cm** (body content ends 2 cm from page bottom)
- Footer distance: **0.75 cm** (footer text sits 0.75 cm from page bottom)
- Net effect: ~1.25 cm vertical gap between last body line and footer text

Cover section (section 0) is untouched — its margins are template-driven.

Constants: `BODY_BOTTOM_MARGIN_CM`, `FOOTER_DISTANCE_CM`.

### R5 — Table borders policy

**Default:** every body-level table renders with INVISIBLE borders. `val="nil"` on all six edges (sides + insideH + insideV). Per-cell `tcBorders` overrides are stripped.

**One exception:** the Observations Register table gets solid 0.5pt light-grey borders (`#BFBFBF`, `single`, `sz=4` half-points).

Border detection: heading-anchored. The first table immediately after a paragraph whose text starts with "observations register" (case-insensitive) is the register. Fallback to the last body-level table if the heading isn't found.

Constants: `BORDER_COLOR_LIGHT_GREY`, `BORDER_SIZE_HALF_PT`.

### R6 — Observations Register column widths (cm)

| # | Status | CCVS | Observation | Finding | Recommendation | Photo |
|--:|--:|--:|--:|--:|--:|--:|
| 1.00 | 1.75 | 1.75 | 2.50 | 3.00 | 3.50 | 3.00 |

Total: **16.5 cm** (A4 printable area ~16.5 cm — exactly at the limit).

Header row repeats across page breaks. Zebra striping in alt rows (`#F2F2F2`).

Constants: `REGISTER_COL_WIDTHS_CM`, `REGISTER_HEADERS`, `REGISTER_HEADER_FILL_HEX`, `REGISTER_HEADER_FG_HEX`, `REGISTER_ALT_FILL_HEX`, `REGISTER_PHOTO_WIDTH_CM`.

### R7 — "Observations Register" section heading

The bold title above the Observations Register table:
- Text: `Observations Register`
- Font: Aptos, 16pt, **bold**
- Color: deep navy `#1F3864` (matches the table's header row fill)
- Space before: 18pt
- Space after: 12pt
- Alignment: left

Constants: `REGISTER_HEADING_TEXT`, `REGISTER_HEADING_FONT_PT`, `REGISTER_HEADING_BOLD`, `REGISTER_HEADING_COLOR_RGB`, `REGISTER_HEADING_SPACE_BEFORE_PT`, `REGISTER_HEADING_SPACE_AFTER_PT`.

### R8 — Email draft (.eml)

Output format: **.eml** (RFC822) — not .msg. Python stdlib only; no Outlook COM dependency.

Headers:
- To: `Matthew McCarthy <matt@rpd.net.au>, Nick Vuckovic <nick@rpd.net.au>` (comma-separated per RFC 5322; fixed for all RPD jobs)
- Subject: `Site Safety Audit Report — <site address> — <YYYY-MM-DD>`
- X-Unsent: `1` (Outlook 2016+ convention — opens .eml as editable draft instead of received message)

Body:
- Greeting: `Hi Matt and Nick,`
- Intro paragraph (auto-generated)
- Summary of findings: **NCR line ONLY**. Drop Observations / Conditional / Compliant lines (operator: noise reduction).
- Conditional paragraph (NCR present vs absent)
- Attachment line: references the **.pdf** (recipients prefer PDF over docx)
- Signature block (Alan Richardson / AuditCo / phone / web / email)

Constants: `EMAIL_RECIPIENTS_RPD`, `EMAIL_GREETING_TARGET`, `EMAIL_X_UNSENT_HEADER`, `EMAIL_ATTACHMENT_EXT`, `EMAIL_SUMMARY_KEEP_LINES_STARTING_WITH`, `EMAIL_SUMMARY_DROP_LINES_STARTING_WITH`, `EMAIL_EML_NAME_TEMPLATE`.

### R9 — Output file naming

Folder name canonical form: `YYYY-MM-DD-<CLIENT>-NN`
(e.g. `2026-05-22-RPD-03` → audit date `2026-05-22`, client `RPD`, sub-id `03`)

Output files written next to the input xlsx:
- `RPD_SSA_Audit_Report_<YYYY-MM-DD>-<NN>.docx`
- `RPD_SSA_Audit_Report_<YYYY-MM-DD>-<NN>.pdf` (rendered via `docx2pdf` → Word COM)
- `Email_Draft_<YYMMDD>_<site-slug>.eml`

Multi-site xlsx → zip: `RPD_SSA_Audit_Reports_<YYYY-MM-DD>-<NN>.zip`

Non-canonical folder names fall back to xlsx audit_date and NN=01 with a stderr warning.

Constants: `FOLDER_NAME_REGEX`, `REPORT_DOCX_NAME_TEMPLATE`, `REPORT_PDF_NAME_TEMPLATE`, `REPORT_ZIP_NAME_TEMPLATE`, `EMAIL_EML_NAME_TEMPLATE`.

---

## Change procedure (don't skip)

When the operator approves a rule change:

1. **Update this document.** Edit the affected rule. Note the change in the changelog at the bottom with the date, the operator's name, the old value, the new value, and the reason.

2. **Update `pims/services/ssa_format_constants.py`** in the same commit.

3. **Regenerate the golden file:**
   ```bash
   cd C:/Users/AlanRichardson/gatekeeper
   py -m tests.regen_golden_audit_report
   ```
   Commit the new `tests/fixtures/golden_audit_report.docx`.

4. **Run the contract test:**
   ```bash
   py -m pytest tests/test_audit_report_format_contract.py
   ```
   Must pass before merge.

5. **Commit with a clear message** like `pims/audit: R6 register widths — operator-approved 2026-06-01`.

---

## Changelog

### 2026-05-25 — Initial lock
First version of the format contract. All rules R1–R9 set per operator's review session against folders `2026-05-20-RPD-02`, `2026-05-22-RPD-01`, `2026-05-22-RPD-02`, `2026-05-22-RPD-03`.

Key decisions made during this session:
- Aptos chosen as body font (was Calibri); enforced at 4 layers (run + body + theme + styles) per operator's "hard rule" directive.
- Cover-page running header suppressed via `different_first_page_header_footer = True` on section 0.
- Running header on body pages: text left, logo right, in a 2-cell borderless fixed-layout table (16 cm total). Two earlier attempts had cells stacking vertically; the fix was to set widths at BOTH column AND cell level AND force `<w:tblLayout w:type="fixed"/>` AND set `<w:tblW>` explicitly.
- Cover bleed onto page 2 was caused by body section's `titlePg=True` inheriting cover's first-page header. Fix: set `different_first_page_header_footer = False` on section 1+ AND explicitly populate `first_page_header`.
- Table borders defaulted to invisible (operator: "Unprofessional pdf - all gridlines showing"). Observations Register re-applies light-grey for readability.
- Observations Register column widths set to operator spec: `(1.0, 1.75, 1.75, 2.5, 3.0, 3.5, 3.0)` cm = 16.5 cm total.
- Observations Register section heading restyled to Aptos 16pt bold, deep navy, with 18pt space before / 12pt space after.
- Body footer position dropped to 0.75 cm from page edge with 2.0 cm bottom margin → ~1.25 cm gap above footer text.
- Email writer switched from .msg (Outlook COM) to .eml (RFC822 stdlib) after `CO_E_SERVER_EXEC_FAILURE` on operator's machine. `X-Unsent: 1` makes Outlook open as editable draft.
- Email Summary trimmed to NCR-only line; Attachment line references .pdf not .docx (recipients prefer PDF).
- Output filename convention changed from `RPD_SSA_AuditReport_<date>.docx` (single date, no NN) to `RPD_SSA_Audit_Report_<YYYY-MM-DD>-<NN>.docx` (full ISO date + sub-id from folder name).
- Sibling .pdf added via `docx2pdf` (Word COM under the hood).

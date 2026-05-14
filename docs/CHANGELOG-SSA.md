# CHANGELOG — SSA pipeline

Scoped changelog for the Site Safety Audit pipeline and its quality
guards. Newest at top.

## 2026-05-15

### Added

- **Full drift checker.** Two new checks beyond the minimal v1 CSV
  header check:
  - Every `PH_*` placeholder constant in `ssa_pipeline.py` must appear
    as literal text in the SSA report template `.docx` (concatenated
    `<w:t>` text across all `word/*.xml` parts, so tokens split across
    formatting boundaries are still caught).
  - Every `STAGING_HEADERS` entry must have a corresponding
    `_STAGING_COL_WIDTHS` key. Subset semantics, not equality —
    `_STAGING_COL_WIDTHS` legitimately carries forward-defined
    gap-4/5/6 columns (phase, activity_ref, hrcw, swms_required, etc.)
    that aren't yet in `STAGING_HEADERS`.

### Changed

- **Placeholder tokens centralised.** `build_ssa_report_docx` no longer
  carries inline `{{SITE_ADDRESS}}` / `{{NARRATIVE_SUMMARY}}` /
  `{{AUDIT_DATE}}` / `{{PREPARED_BY}}` strings in its `body_replacements`
  and `footer_replacements` dicts. They're now module-level
  `PH_*` constants plus an `SSA_REPORT_PLACEHOLDERS` tuple, which the
  drift checker walks. Pure refactor — no behaviour change.

## 2026-05-14

### Added

- **Deterministic post-pass** on `build_ssa_report_docx` output. Two
  runs over the same inputs now produce byte-identical docx files.
  Lifted from rpd-ssa-builder. See `pims/services/ssa_quality/determinism.py`.
- **OOXML schema validation** on every report docx via Microsoft's
  OpenXmlValidator (wrapped in a small .NET CLI reused from
  rpd-ssa-builder's cache at `%LOCALAPPDATA%\rpd-ssa-validator\`).
  Errors surface on the diagnostics dict and as log warnings; the
  build does not abort on findings. Soft-skips when dotnet is
  unreachable.
- **Headless LibreOffice render smoke test** after each successful
  full or from-state build (CLI-main level — does not run during
  build_ssa_report_docx unit tests). Catches "python-docx accepts
  it but LibreOffice / Word won't render it" defects that the
  schema validator may miss. Soft-skips when soffice is not installed.
- **`--check` preflight CLI flag** on `run_ssa_pipeline.py`. Verifies
  folder name pattern, Evidence_Master.csv presence and shape,
  images in folder root, template readability, and environment
  tool availability (LibreOffice, dotnet, ANTHROPIC_API_KEY).
  Hard failures return exit 1; informational warnings don't block.
- **Drift checker** at `tools/check_ssa_drift.py` for paired
  constants across SSA modules. v1 covers the one drift case
  introduced when preflight duplicated `_REQUIRED_HEADER` as
  `_EXPECTED_CSV_HEADERS`.
- **Byte-hash regression test** in `tests/test_ssa_determinism.py`
  pins the SHA-256 contract for a fixture build so future
  formatting drift on the docx output is caught by CI.

### Fixed

- **`<w:tblBorders>` schema-order bug** in `_apply_all_cell_borders`
  (`pims/services/ssa_pipeline.py:1089`). The function was emitting
  `<w:tblBorders>` at the end of `<w:tblPr>` via plain `.append()`;
  the OOXML schema places `tblBorders` at position 11, before
  `<w:tblLook>` (position 15) which every template table already
  carries. Tripped four `Sch_UnexpectedElementContentExpectingComplex`
  errors per built docx. Word's recovery prompt tolerates this;
  OpenXmlValidator does not. Now inserts before the first child
  whose tag falls in the positions-after-tblBorders set.

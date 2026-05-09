---
description: Generate RPD/SSA audit report .docx (or .zip) from a Site Visit Report xlsx
argument-hint: <xlsx-path> [--prepared-by "Name"] [--enrich-findings | --no-enrich-findings] [--out <dir>]
---

Run the audit report generator on the xlsx the user supplied as `$ARGUMENTS`.

Steps:
1. Resolve the xlsx path. If `$ARGUMENTS` is empty, ask which file. If the path is bare (no directory), assume it lives in `pims/`.
2. From the repo root (`C:\Users\AlanRichardson\gatekeeper`), run:
   ```
   python pims/scripts/generate_audit_report.py <xlsx-path> [flags]
   ```
   Pass through any flags the user included verbatim (`--prepared-by`, `--enrich-findings`, `--no-enrich-findings`, `--out`).
3. Report the output filename and size from the script's `WROTE …` line.

Notes:
- `--enrich-findings` toggles the wording-enrichment staging stage (overrides `PIMS_ENRICH_FINDINGS` env var). Default behavior is whatever the env var says.
- All corrective actions are auto-normalised to "It is recommended …" by the renderer (see `_normalise_corrective_text`); no flag needed.
- Output lands next to the xlsx unless `--out` is given.

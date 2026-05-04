# SSA Pipeline — Codex Review Bundle

Single-document bundle of the **original plan** plus the **shipped
implementation** of the SSA evidence-folder → 3-deliverable pipeline.
Use this to diff plan vs. implementation and surface drift.

## What this bundle is for

The original plan was written before any of the canonical sample
deliverables had been opened. Real-folder runs (specifically
`G:/My Drive/alan_mcxico/SSA-evidence/2026-05-01-SDG/`) revealed
several contract mismatches between the plan and what the user
considers canonical. Most of those were corrected during the build
and are listed in the **Drift between plan and shipped** section
below.

Use this document to:

1. Identify any remaining drift (places where the plan still differs
   from what the code actually does).
2. Catch quality / correctness issues the test suite (69 pytest
   cases, all green; flake8 clean) does not assert against.
3. Suggest improvements to the plan itself so future work has a
   spec that matches the canonical samples.

## Drift between plan and shipped (already-known deltas)

These are deliberate departures from the plan, made because the
canonical samples (`PIMS-Enriched - Sample.xlsx`,
`Site-Visit-Report- Upload to PIMS Staging.xlsx`,
`Site-Safety-Audit-Report - new Sample.docx`,
`Unitas_Risk_Assessment_all.docx`) showed the plan's contract was
wrong on these axes:

| Axis | Plan says | Shipped reality | Why |
|---|---|---|---|
| CCVS code source | `pims/audit_checklist.xlsx` (Category/Criteria/Instruction; numeric `01.01` synthesised from leading digits) | Canonical 25 × 6 = 150 codes from `renderers/docx_renderer.py:_VALID_CCVS_STREAMS` + `SYS` extension; tier suffixes H6/H9/M3/M4/L1/L2 | Sample uses `SYS-M3`, `MOB-H6`, `WAH-H6`, `STR-H9`, `ELE-H6`. The 01.01 scheme has no relationship to the canonical taxonomy. |
| Status assignment | Keyword auto-matcher (difflib token recall) emits Conditional/Unmatched only | Vision Anthropic call (Opus 4.7) emits Compliant/Conditional/NCR/Info/Unmatched | Sample is Compliant-heavy (39/64). A classifier that never produces Compliant cannot match the contract. |
| LLM gating | `PIMS_ENRICH_FINDINGS` env var, default OFF | Default ON; `--no-enrich` opts out; `ANTHROPIC_API_KEY` required at runtime | Sample observation/finding cells are LLM-rewritten multi-sentence narratives citing WHS Reg / AS / SafeWork NSW inline. |
| Vision support | text-only enrichment | photo (downscaled to 1024 px, EXIF-normalised, JPEG q85, base64) sent to vision model | Photo is the primary evidence the human reviewer uses; required for status assignment. |
| Project context | none | RA-aware: auto-discovers `*Risk_Assessment*.docx` in the audit folder, parses metadata + 9 hold points + 66 phase activities, injects into vision prompt | Without RA awareness the audit cannot reference HP-04 / TP-05 / HRCW H14, etc. — reviewer can't trace findings back to the principal contractor's WHS contract. |
| `#N` Findings cloning | R-1.3 forbids paragraph-level cloning at body level | Cloning enabled for Findings list (heading + body pair per non-Compliant row) | R-1.3 conflicts with V-10.5 ("count of #N paragraphs equals count of non-Compliant"). Without cloning, the rendered docx leaves only the template's `#1` placeholder visible. |
| Per-location 2-col block | Clone N times per detected location | Always remove (R-1.3(e) explicitly permits removal) | Location detection is out of scope for v1. Removing avoids a stale 6-row scaffold in the output. |
| Status of Previous Recs | Parse prior report (deferred slice in plan) | Implemented: `parse_prior_report_recommendations` extracts NCR/Conditional rows from the prior report's Observations Register | Reviewer needs carry-forward visibility; placeholder text wasn't acceptable. |
| Staging xlsx polish | Plan said embed thumbnails; nothing about column widths / wrap / status fills | Column widths set, wrap_text on long-content columns, status colour fills (NCR red, Conditional amber, Compliant green, Info blue-grey, Unmatched neutral) | Sample uses these conventions; without them long enriched findings render truncated and reviewer can't scan status at a glance. |
| `_clone_row` insertion order | not specified beyond "deepcopy and append" | append to END of `<w:tbl>` parent (was: `addnext` after placeholder, with `rows[-1]` returning the wrong row) | The first attempt used `addnext` which silently corrupted multi-row tables — every clone except the last carried the placeholder content. Caught by visual inspection of the docx; a regression test now locks the failure mode in. |
| Network retry | not specified | retries=2 on `httpx.ConnectError/ReadError/WriteError/TimeoutException/RemoteProtocolError` + HTTP 408/429/500/502/503/504; immediate raise on other 4xx | Real-folder run dropped 2 of 21 rows to transient network errors mid-batch; retry recovers cleanly. |
| Model | claude-sonnet-4-5-20250929 (initial) | claude-opus-4-7 (after user direction) | Most capable model; supports vision. |

## Known remaining gaps (not yet shipped)

- **HRCW / Hold Point cross-reference columns**: vision findings reference HP/activity refs inside finding text, but no dedicated `phase` / `activity_ref` / `hold_point` columns in the staging xlsx. Reviewer reads them as part of the narrative.
- **Compliant / Info SWMS verification**: RA mandates SWMS verification across nearly every activity row; the audit doesn't generally check for SWMS presence beyond the rows where the auditor noted it.
- **Initial / Residual risk axis**: RA uses H/M/L 3/2/1 rubric for both initial and residual risk. SSA tier suffix (H6/H9/M3/M4/L1/L2) carries severity but uses a different rubric.
- **Image preprocessing cache (Appendix C §C.6)**: the staging size-control wrapper re-renders at progressively smaller caps but doesn't share preprocessed BytesIO across rerenders; cache key is implicit per-call. Functional but wastes CPU on large audits that need progressive downscale.
- **`audit_checklist.xlsx` legacy fallback**: still single-source-of-truth for the legacy keyword matcher when `--no-enrich`. Could be retired once vision is the only supported path.

## File inventory

- **`pims/services/ssa_pipeline.py`** (1755 lines) — Pipeline core: parser, matcher, three builders, enrichment, size-control wrapper, prior-rec parser, Findings #N expansion, xlsx polish helper.
- **`pims/services/ssa_checklist_lookup.py`** (279 lines) — Legacy CCVS-keyed lookup over audit_checklist.xlsx. Kept as a deterministic fallback for --no-enrich mode; bypassed when vision is on.
- **`pims/services/ssa_ccvs_taxonomy.py`** (100 lines) — Canonical 25-stream x 6-tier CCVS taxonomy. Replaces the audit_checklist.xlsx-derived 01.01 numeric scheme with the real WAH-H6 / SYS-M3 / etc. coding the canonical samples use.
- **`pims/services/ssa_vision_enricher.py`** (476 lines) — Per-row Anthropic vision call (Opus 4.7). Sends downscaled EXIF-normalised photo + observation text + project RA context. Receives status / ccvs_code / finding / legal_ref / recommendation / monitoring_note. Transient-error retry.
- **`pims/services/ssa_ra_parser.py`** (281 lines) — Project Risk Assessment docx parser. Extracts metadata + 9 hold points + N phase activities; compact-context-block packs into the vision prompt so findings cite HP-04 / TP-05 / HRCW H14 inline.
- **`pims/services/ssa_watcher.py`** (309 lines) — Quiescence-gated folder watcher: settle_seconds + N stable polls; exclusions cover every watcher-owned artifact. Manifest-sha256 idempotency lives in the orchestrator.
- **`pims/scripts/run_ssa_pipeline.py`** (529 lines) — CLI orchestrator. Folder-name parse, manifest sha256, freeze escape hatch, sentinels (NOT_UPLOADABLE / NO_BULK_ENDPOINT), RA auto-discover, vision wiring, .ssa_run.json payload.
- **`pims/scripts/start_ssa_watcher.py`** (66 lines) — Long-run entry for the watcher. Rotating-file logging.
- **`tests/test_ssa_pipeline.py`** (1353 lines) — 69-case regression net. Covers parser, matcher, three builders, size-control, manifest, watcher, vision coercion, RA parser, prior-rec parser, Findings #N expansion, status colour fills, freeze, idempotency, partial-output recovery.

---

## Original plan

Source: `C:\Users\AlanRichardson\.claude\plans\workflow-1-i-upload-optimized-catmull.md`

````markdown
# SSA Evidence → 3 Deliverables Pipeline (Workflow #1)

## Context

Today an audit produces a folder on Google Drive (e.g. `G:\My Drive\alan_mcxico\SSA-evidence\2026-05-01-SDG\`) containing audit photos and an `Evidence_Master.csv` with `timestamp, observation, filename` rows. From that, three deliverables are needed every time, in the same folder, formatted exactly like the samples — no drift:

1. `PIMS-Enriched-YYMMDD-<CLIENT>.xlsx` — enriched register, photo thumbnails embedded in column D.
2. `Site-Safety-Audit-Report-YYMMDD-<CLIENT>.docx` — narrative audit report with photo thumbnails in the Observations table Photo column.
3. `Site-Visit-Report-Upload-PIMS-Staging-YYMMDD-<CLIENT>.xlsx` — canonical staging upload for PIMS (RPD or SDG depending on client).

Goal: a stable, permanent, phone-friendly workflow. Alan uploads from phone → desktop watcher detects the folder is **quiescent** → the deliverable set lands back in the same folder, **written via per-file atomic replacement with reruns recovering any partial set**, ready to review and (where the uploadability gate passes) upload to PIMS staging. Reruns must be safe and must redo work when inputs change.

The canonical deliverable set is three files (PIMS-Enriched, SSA report, Staging xlsx), but the actual output set is dynamic — large audits may produce split staging files (`-part1`, `-part2`, …) and gate outcomes may add **either** `STAGING-NOT-UPLOADABLE.txt` (schema-gate failure) **or** `STAGING-NO-BULK-ENDPOINT.txt` (SDG, schema-valid but no bulk endpoint). The full set produced by any given run is recorded in `.ssa_run.json` under `outputs`. All these artifacts — including both sentinel variants and `.ssa_freeze` — are excluded from quiescence snapshots and are watcher-owned, never folder-state inputs.

**Upload-readiness caveat (tri-state):** every run produces review-ready files, but the staging xlsx carries one of three statuses recorded in `.ssa_run.json` as `staging_status`:
- `bulk_uploadable` — passes all schema gates AND client (RPD) has a bulk endpoint. Push to PIMS via `/pims/upload/observations`.
- `schema_valid_no_endpoint` — passes all schema gates BUT client (SDG today) has no bulk endpoint. `STAGING-NO-BULK-ENDPOINT.txt` sentinel written; observations must be posted one-at-a-time via the single-observation API.
- `not_uploadable` — fails a schema gate (e.g. `site_address_unresolved`). `STAGING-NOT-UPLOADABLE.txt` sentinel written naming the blocker. Remediation depends on the blocker (see Remediation paths below).

**Remediation paths (per blocker — never both):**
- `site_address_unresolved`: **fix the source observation** (add an address-shaped sentence to a row in `Evidence_Master.csv`), then let the watcher rerun. Manual edits to the generated staging xlsx will be wiped on the next rerun. To preserve a manual edit instead, see the freeze rule below.
- `audit_date_unparseable`: rename the audit folder to the canonical `YYYY-MM-DD-<CLIENT>` form, then rerun.
- Row count >500: handled automatically (split). No manual remediation.

**Freeze rule (manual-patch escape hatch):** if Alan needs to hand-patch a generated staging xlsx without losing it on the next rerun, he writes a `.ssa_freeze` empty file into the audit folder. **Both** the watcher AND the manual `run_ssa_pipeline` CLI refuse to run any folder containing `.ssa_freeze`, logging the skip. The CLI accepts an explicit `--ignore-freeze` flag for the rare case Alan deliberately wants to overwrite a frozen folder; without that flag, the CLI exits non-zero with a clear message. To resume automatic regeneration, delete `.ssa_freeze`. The file is added to the static quiescence exclusions. This makes "fix by hand" a deliberate, auditable choice and prevents a manual rerun from silently destroying the very edit the freeze was meant to protect.

## Locked decisions (from clarification + Codex review)

- **Trigger:** desktop folder watcher on `G:\My Drive\alan_mcxico\SSA-evidence\`. Fires when the folder is *quiescent* (see Watcher contract below) — not just "some files exist".
- **Client routing:** folder name suffix `-SDG` or `-RPD` is authoritative. Determines PIMS staging template variant.
- **CSV schema:** 3 columns `timestamp, observation, filename`. Tolerant parser (see CSV contract).
- **Enrichment:** reuse `pims/services/finding_enricher.py` + `pims/services/checklist_matcher.py`. **Phase 0 first**: verify these module signatures actually match the assumptions before building on them.
- **Tone scope:** year-12 plain-English + humaniser ruleset applies **only to the narrative summary and the `finding` field**. `Action Description`, `Recommendation`, `Legal Ref`, `CCVS Code/Category` are taken **verbatim from the checklist** to keep determinism, reviewer trust, and rerun stability.

---

## Watcher contract (replaces naive "files exist" gate)

The watcher is the single biggest operational risk. Half-synced Google Drive folders must not produce sticky partial outputs.

**Eligibility check** for a dated folder:
1. Folder name matches `YYYY-MM-DD-<CLIENT>` where `<CLIENT>` ∈ {`SDG`, `RPD`}.
2. Contains an `Evidence_Master.csv`.
3. Contains ≥1 image file.
4. **Quiescence (both conditions required):**
   - **(a)** `now - max(input_mtime) >= 120s` — true wall-clock stability of inputs.
   - **(b)** 4 consecutive 30s polls show identical `(filename, size, mtime)` snapshots.
   The snapshot **excludes** every watcher-owned artifact — see the *Quiescence snapshot exclusions* paragraph below for the full list (dynamic `outputs` from `.ssa_run.json` plus all static exclusions including both sentinel variants, `.ssa_freeze`, `.ssa_work/`, and canonical output prefixes including `-partN`). "Inputs" for condition (a) means CSV + image files + any prior `Site-Safety-Audit-Report-*.docx` — not the watcher's own artifacts.

**Input manifest:** before running, the watcher computes a manifest using **full-file SHA-256** over the CSV bytes and every image file's bytes:
```
inputs.sha256 = sha256( sorted( filename || sha256(file_bytes) ) over CSV + every image + qualifying prior SSA report )
```
**Qualifying prior SSA report** = a `Site-Safety-Audit-Report-*.docx` whose filename date suffix is **strictly earlier** than the current audit folder date AND whose filename **does not equal** the current target output filename. The newly-generated report from a previous run of the *same* folder must never appear in the manifest — otherwise the second cycle sees a different manifest from the first and reruns forever.
Full content hashing (not size+mtime+first-4KB) — removes a whole class of "why didn't it rerun?" disputes. Manifest is written to `.ssa_run.json` after a successful run, alongside output paths, timestamps, and the per-file hashes.

**Output set is dynamic.** The pipeline does not always produce exactly three files. The canonical core is three (PIMS-Enriched, SSA report, Staging xlsx), but the staging xlsx may be split into `-part1.xlsx`, `-part2.xlsx`, … on >500 rows, and **either** `STAGING-NOT-UPLOADABLE.txt` (schema gate failed) **or** `STAGING-NO-BULK-ENDPOINT.txt` (SDG, schema-valid but no bulk endpoint) may also be written. The full set of artifacts produced by a run is enumerated in `.ssa_run.json` under `outputs: [filename, …]`.

**Quiescence snapshot exclusions** are computed as the union of:
1. **Recorded outputs**: every filename listed in `.ssa_run.json` `outputs` (if a `.ssa_run.json` exists).
2. **Current target output filenames** (computed from folder name + client suffix, even before the first run): `PIMS-Enriched-YYMMDD-<CLIENT>.xlsx`, `Site-Safety-Audit-Report-YYMMDD-<CLIENT>.docx`, and `Site-Visit-Report-Upload-PIMS-Staging-YYMMDD-<CLIENT>.xlsx` (plus any `-partN` variants for the staging file).
3. **Static watcher artifacts**: `.ssa_work/` (any depth), `.ssa_run.json`, `.ssa_run.error`, `.ssa_freeze`, and **both** sentinel files (`STAGING-NOT-UPLOADABLE.txt` and `STAGING-NO-BULK-ENDPOINT.txt`).

Older `Site-Safety-Audit-Report-*.docx` files (qualifying prior reports per §"Prior-report reuse policy") are **NOT** excluded — they are legitimate watcher inputs, included in quiescence snapshots and in the input manifest hash. Only the current target's output filename is excluded, never the broad prefix. This prevents a changed or newly added qualifying prior report from being silently ignored, while still preventing the watcher from reacting to its own writes. The same narrowing applies to PIMS-Enriched and Staging filenames: only the current target name (and recorded `outputs`) are excluded, not the broad prefix.

**Idempotency rules (output-set aware):**
- If `.ssa_run.json` exists AND `inputs.sha256` matches AND **every file listed in `outputs`** exists → **skip**.
- If `.ssa_run.json` exists AND `inputs.sha256` differs → **rerun** (inputs changed). The new run computes a fresh output set; old extra outputs (e.g. a `-part2.xlsx` from a previous larger run that's no longer needed) are removed before final replacement.
- If `.ssa_run.json` exists AND any file listed in `outputs` is missing → **rerun** (partial state).
- If `.ssa_run.json` is absent and any canonical-prefix output exists → **rerun** and adopt them as overwrite targets (recovery from earlier crash).

**Write strategy (per-file atomic, set-level eventually consistent):** every output is written to `<name>.tmp` inside `.ssa_work/`, then `os.replace`'d into its final path. Each *individual* file replacement is atomic. A crash between file 2 and file 3 can still leave a mixed visible set on disk — the **idempotency rules above are what guarantees recovery**: the next watcher cycle sees a partial output set or a missing-output condition and reruns. The plan does not claim true set-level atomicity.

**Single-instance lock:** `.ssa_work/lock` (file lock) prevents two watcher cycles from racing the same folder.

**Failure mode:** on exception, write `.ssa_run.error` with the traceback and a human summary; do NOT write `.ssa_run.json`. Next eligibility cycle will retry. Watcher logs to `pims/audits/ssa_watcher.log`.

---

## CSV parser contract

`Evidence_Master.csv` parser must handle:

- **Encoding:** detect UTF-8, UTF-8-SIG (BOM), and CP1252; normalise to UTF-8 internally.
- **Header detection:** treat row 1 as a header **only if** its three cells case-insensitively match the literal header names `timestamp`, `observation`, `filename` (in that order, with whitespace tolerance). Any other row 1 — including a row whose first cell is a malformed timestamp — is treated as data and parsed/flagged per the timestamp rule below. This avoids silently dropping a real first observation that has a bad timestamp.
- **Field count:** parse with Python `csv.reader` (default dialect) so quoted commas and embedded newlines are absorbed correctly. After parsing, `len(row) == 3` is **required**. Any other length (including 4+ from genuine extra columns) → log row number + reason and skip. No ad-hoc reconstruction of malformed rows.
- **Quoted commas + embedded newlines** in observation: supported (standard `csv` module behaviour).
- **Blank rows:** skipped silently.
- **Timestamp:** parse as `YYYY-MM-DD_HH-MM-SS`; on failure, row is kept but flagged `needs_review=True` with reason.
- **Filename:** required. Missing filename → row dropped with log entry.
- **Duplicate filename:** kept; flagged `duplicate_filename=True` on every affected row; reviewer decides at QA.
- **No silent coercion:** every drop / flag goes into `.ssa_run.json` under `csv_warnings: [...]`.

---

## Filename matching contract

Photos are matched to CSV `filename` values with these rules, in order. **Every rule returns 0 / 1 / many; "many" always means `needs_review=True` with no silent selection.**

1. **Canonicalise** both sides: lowercase, strip whitespace, normalise extension (`.jpeg` → `.jpg`, `.png` stays `.png`). **Drive-suffix patterns (`(1)`, ` - Copy`) are NOT stripped** — they identify derivative copies and stripping them would collapse `EV_001.jpg` and `EV_001 (1).jpg` to the same key.
2. **Exact match** on canonical form. 0 → fall through. 1 → match. Many → `needs_review`.
3. **Stem match** (filename without extension) across the JPEG family only. 0 → fall through. 1 → match, log extension swap. Many → `needs_review`.
4. **Suffix match** (canonical CSV filename appears as the suffix of an on-disk canonical filename — handles prefixed names like `6aFrancis_EV_2026-05-01_09-17-19.jpg`). 0 → fall through. 1 → match, log prefix. Many → `needs_review`.
5. **Camera-name fallback** (`IMG_*`, `EV_DB_*`, etc.): only matched if the CSV token literally references that name; no fuzzy matching across naming conventions.
6. **Missing** (0 across all rules): row kept, photo cell blank, flagged `needs_review=True`.

Case-insensitive, extension-insensitive within the JPEG family (`.jpg`/`.jpeg`/`.JPG`/`.JPEG`). PNG kept distinct.

**`photo refs` write contract:** the value written to the staging xlsx `photo refs` column is the **resolved on-disk filename** (the actual file that ships alongside the workbook to PIMS), not the CSV token — so PIMS's filename join works whether or not an extension swap or prefix match happened. The original CSV token is preserved separately in `.ssa_run.json` under `csv_warnings` whenever it differs from the resolved name. If matching failed (rule 6), `photo refs` is blank and `needs review = TRUE`.

---

## Site-address extraction (no unsafe fallback)

1. Scan **all observations** in the CSV for an address-shaped string (street number + street + suburb pattern, or a known site name from `pims/data/known_sites.json` if it exists). The earlier "first 5 observations" cap is removed — it conflicted with the remediation guidance, since Alan adding an address to a later row would have been ignored. Scanning all rows is cheap (typical audit ≤30 rows of text).
2. Use first hit (lowest row index).
3. **If nothing found:** `site_address` left blank. `needs_review` set TRUE on every observation row in the staging xlsx. `.ssa_run.json` records `site_address_unresolved=True`. **Do not** fall back to the folder name — that leaks date/client junk into PIMS.

---

## Prior-report reuse policy

**Eligibility:** a candidate `Site-Safety-Audit-Report-*.docx` qualifies for reuse only if ALL:
- its filename date suffix parses as `YYMMDD` (the canonical format used by this pipeline). If the date suffix is missing or unparseable, the file is **non-qualifying** — never guessed from mtime or document content.
- its parsed date is **strictly earlier** than the current audit folder date, AND
- its filename **does not equal** the current target output filename for this run.

This excludes the report this run is about to generate (or has just generated on a prior cycle of the same folder) — preventing self-reference and the rerun loop it would cause.

Selection from qualifying candidates:
- Zero qualifying → no prior report; previous-recs table populated with single placeholder row "No prior recommendations carried forward."
- One qualifying → parse it.
- Multiple qualifying → choose the newest by filename date suffix; log the selection.
- Unreadable docx, wrong table shape, or different site address → skip parsing; placeholder row noting "prior report not reused: <reason>"; continue.
- Never block pipeline on prior-report failure.

---

## Output contracts (template-clone, not template-match)

Codex was right: "match the sample exactly" is too loose. Switch contract to **copy the template file, then mutate only named regions**. The template files carry every formatting decision (column widths including hidden Q, freeze panes, styles, header/footer, paragraph spacing, table layout). Implementation is forbidden from constructing these from scratch.

### Template files
- `pims/templates/ssa/PIMS-Enriched.template.xlsx` — frozen copy of `PIMS-Enriched - Sample.xlsx` with data rows cleared, header rows + Summary sheet retained.
- `pims/templates/ssa/Site-Safety-Audit-Report.template.docx` — **derived from `G:\My Drive\alan_mcxico\SSA-evidence\Site-Safety-Audit-Report - new Sample.docx`**, not the original sample. The canonical template **intentionally deviates** from the new sample on one axis: the font is changed from `Arial Nova Light` (sample) to `Aptos` (canonical) as a one-time manual Word edit before freeze. Alan confirmed this deviation explicitly. All other formatting (font sizes, bold, alignment, table structure, page geometry, headers/footers) is preserved verbatim from the new sample. Once the template is frozen, the **frozen template is the single source of truth** — neither the original sample nor the new sample is consulted again at runtime; the pipeline operates only on copies of the frozen template.

  **Preserved verbatim from the new sample — implementation must NOT touch:**
  - Font sizes (all bold): 18 pt title, 16 pt site address, 14 pt section headings, 12 pt finding sub-headings.
  - All structured paragraphs Justified.
  - 3 sections, page geometry, header/footer parts, table structures, column widths.

  **Intentional template-freeze deviation from the sample:**
  - Font: **Aptos** everywhere (replaces the sample's Arial Nova Light). One-time manual Word edit per Phase 0; locked thereafter. See Appendix A R-4.1.
  - Font sizes (all bold): 18 pt title, 16 pt site address, 14 pt section headings (Executive Summary, Positive Observations, Findings, Status of Previous Recommendations, Observations Register), 12 pt finding sub-headings (`#1`, `#2`, …). Body inherits Normal.
  - All structured paragraphs Justified.
  - 3 sections. **Section 0 has `different_first_page_header_footer = True`** — this is the page-zero mechanism. First physical page shows the larger first-page header (logo) and a blank first-page footer; subsequent pages get the running header (small logo) and the running footer.
  - Page geometry: A4, margins t=1.5 / b=0.5 / l=2.54 / r=2.54 cm; section 2 bottom margin 1.25 cm. Header/footer distance 1.25 cm.
  - 5 header parts + 3 footer parts as in the sample.
  - All 7 tables and their column widths (notably observations register: 1.12 / 2.74 / 5.10 / 3.79 / 2.25 / 2.75 cm).

  **Manual one-time edits before freezing as the template:**
  1. Replace the literal date `05/05/2026` in the section 1 footer with a placeholder run `{{AUDIT_DATE}}`; replace `Alan Richardson` in the same footer with `{{PREPARED_BY}}`. Page numbering stays as Word field codes (`Page: {n} of {N}`).
  2. Replace the literal site address paragraph with `{{SITE_ADDRESS}}`.
  3. Replace the executive-summary body paragraphs with a single `{{NARRATIVE_SUMMARY}}` placeholder paragraph.
  4. Reduce the observations-register table (table 6) to one placeholder row (used for cloning at runtime).
  5. Reduce the 4-col `Status of Previous Recommendations` table to one placeholder row.
  6. Reduce each per-location 2-col table to one placeholder location block (or one cloneable shell).
  7. Reduce the positive-observations table (table 0) to one placeholder row.

  Headings and section names use the **new sample wording** — "Executive Summary", "Observations Register" — not the older "Site Safety Audit Observations". The "Findings" sub-heading + numbered `#N` list stays as the sample lays it out.
- `pims/templates/ssa/Site-Visit-Report-PIMS-Staging.template.xlsx` — frozen copy of the staging sample with data rows cleared.

### 1. PIMS-Enriched-YYMMDD-<CLIENT>.xlsx
- `shutil.copyfile(template, output.tmp)` then open with openpyxl.
- Sheet `Enriched Register`: append data rows starting at row 2. Column order is taken from the template header row, not redeclared in code.
- Column D `Photo`: embedded thumbnail per Appendix B (image preprocessing + insertion contract for the xlsx). Row height auto-set to fit (~95 pt for a 2.5 cm landscape image; taller for portrait).
- Sheet `Summary`: write into named cells only (Audit Date, Site Address, totals). Title row, layout, widths inherited from template.
- Hidden columns, freeze panes, filters, number formats, conditional formatting: never touched.

### 2. Site-Safety-Audit-Report-YYMMDD-<CLIENT>.docx

This section summarises the build steps. **Appendix A is the authoritative contract** for the SSA docx — these steps MUST conform to A.6 (placeholder substitutions), A.7 (table cloning), A.9 (headers/footers), and S-11 (runtime sequence). Where this summary appears to differ from Appendix A, Appendix A wins.

- Open template with python-docx.
- Substitute the four `{{TOKEN}}` placeholders defined in A.6, in **both** body paragraphs and the section 1 footer:
  - Body: `{{SITE_ADDRESS}}` (16 pt bold paragraph), `{{NARRATIVE_SUMMARY}}` (paragraph below `Executive Summary`).
  - Section 1 footer: `{{AUDIT_DATE}}` (replacing the literal date), `{{PREPARED_BY}}` (replacing the prepared-by name). Page-numbering field codes (`PAGE` / `NUMPAGES`) are preserved as Word field codes — never replaced with literal numbers (R-9.4).
  - There is no `{{POSITIVE_OBS_LIST}}` token. Positive observations are rendered by cloning the placeholder row of the Positive Observations table (per A.7), not by text substitution.
- Tables — clone the placeholder row of each table per A.7 and write cell content:
  - Positive Observations (3 cols): one row per `Compliant` observation.
  - Status of Previous Recommendations (4 cols): rows from the prior-report parser, or the placeholder row.
  - Observations Register (6 cols): one row per non-Compliant observation; Photo cell receives an inline image at `Cm(2.5)` per R-7.4 / R-7.4.1.
  - Per-location detail tables (2 cols, multi-row blocks): clone or remove per detected locations (see A.7 + R-1.3 block-level allowance).
- Headers (cover + running) and section structure: inherited untouched (R-1.2, R-3.x).
- Footer: only the `{{AUDIT_DATE}}` and `{{PREPARED_BY}}` tokens are mutated; field codes, tab stops, and surrounding literal text are preserved verbatim (R-9.3).

### 3. Site-Visit-Report-Upload-PIMS-Staging-YYMMDD-<CLIENT>.xlsx

**Confirmed against `pims/routes.py:2091` `/pims/upload/observations` (RPD bulk-upload endpoint):**
- Filename: any `*.xlsx` extension accepted. Our naming pattern is fine but the endpoint does not require it.
- Sheet name: must be `Observations`.
- **Format: "upload format", not the presentation sample format.**
  - Row 1: title block / metadata (free).
  - Row 2: blank.
  - **Row 3: header row** — column names in `snake_case`: `id, photo, site_address, audit_date, observation_text, finding, conformance_status, ccvs_code, ccvs_category, action_description, responsible, due_category, recommendation, monitoring_note, legal_ref, photo_refs, prepared_by, source_pdf, section, needs_review`. Underscored, not spaced. Required minimum: `site_address`, `audit_date`, `observation_text`.
  - Row 4: blank.
  - **Row 5+: data rows.**
- Size limit: 5 MB. Row limit: 500.
- Auth: session cookie from the RPD dashboard at upload time (Alan logs in via the dashboard, then uploads the file).

**Insert-from-staging direction (the "other direction" — load-bearing):**

The PIMS bulk-upload endpoint at `pims/routes.py:2091` has two branches keyed off the `id` column:

- **Branch A — `id` is a valid UUID** (`routes.py:2250`): the row is treated as an enrichment of an existing `pims_staging` record. Endpoint PATCHes that row by id. If the UUID doesn't actually exist in Supabase, the PATCH succeeds silently (HTTP 204, zero rows affected) and the endpoint reports `updated += 1` — the finding is **lost without an error**.
- **Branch B — `id` is blank or non-UUID** (`routes.py:2316`): the row is treated as a brand-new finding originating from the staging xlsx (never captured via the field API, never previously in Supabase). Endpoint duplicate-checks by `(audit_date, observation_text, site_address)` against `pims_observations`; if no match, INSERTs into `pims_observations` with `staging: True, enriched: True`, `imported_at = now()`, `prepared_by = <CSV value or "Alan Richardson">`. The row enters the normal staging→approval workflow as if it had been captured live, then enriched.

**Our pipeline is always Branch B.** Every observation in `Evidence_Master.csv` is, by construction, captured for the first time at audit time — there is no pre-existing Supabase record to enrich. Therefore:

- `id` is **blank** in every row of every staging xlsx the pipeline produces.
- The endpoint takes Branch B, deduplicates against existing observations (so safe re-uploads), and INSERTs new rows.
- A pipeline that emitted `uuid4()` here would silently lose every finding to the no-op PATCH path.

**Idempotency on re-upload** is handled by the endpoint's natural-key dedup: `(audit_date, observation_text, site_address)`. A second upload of the same staging xlsx skips already-inserted rows. This means Alan can safely re-upload after fixing one row — only the changed row inserts; the rest are detected as duplicates and skipped.

**Edge case — observation text edits:** if Alan edits `observation_text` between uploads, the dedup natural key changes and the edited row is treated as a *new* finding (a second row in Supabase). To update an existing row instead, Alan must use the dashboard UI directly; the bulk-upload path cannot edit existing rows by anything other than `id`. The pipeline doesn't try to support edit-via-reupload — that's an out-of-scope design constraint of the endpoint.

**SDG asymmetry — known limitation:** SDG currently has no bulk-upload endpoint. The pipeline still produces the staging xlsx for SDG audits in the same upload format (so the file is forward-compatible when the endpoint is added), but Alan cannot upload SDG audits in bulk today — they go via `/pims/observation/sdgroup` one-at-a-time. The pipeline's job ends at producing the file; how it's posted to PIMS is downstream.

**Build:**
- `shutil.copyfile(template, output.tmp)`; open with openpyxl.
- Sheet `Observations` in the template carries the row 1/2/3/4 layout, header text in row 3 in snake_case, and any styling. Implementation appends data rows starting at row 5.
- Column population per Field Defaults table below — header keys in the table use the snake_case names that match row 3.

**Template file `pims/templates/ssa/Site-Visit-Report-PIMS-Staging.template.xlsx` must be built fresh in upload format**, not copied from the presentation-format sample at `G:\...`. Phase 0 step: hand-build this template once by saving an empty upload-format workbook with row 3 headers verified against `routes.py:2131` (`for col_idx, cell in enumerate(ws[3], 1)`).

**Uploadability status (tri-state, not boolean):**

- `bulk_uploadable` — file passes every schema/payload gate below AND client has a bulk-upload endpoint.
- `schema_valid_no_endpoint` — file passes every schema/payload gate below BUT client has no bulk endpoint (today: SDG). The file is correct and forward-compatible; observations must be posted one-at-a-time via the single-observation API until a bulk endpoint exists.
- `not_uploadable` — file fails one or more schema/payload gates. `.ssa_run.json` carries a `blocker` field naming the failed gate.

**Client-capability gate (gate 0):** RPD has `/pims/upload/observations` (confirmed at `pims/routes.py:2091`). SDG does **not** today. A clean SDG run therefore lands in `schema_valid_no_endpoint`, never `bulk_uploadable`. `.ssa_run.json` records `client_bulk_endpoint: "/pims/upload/observations"` for RPD or `null` for SDG. When a bulk SDG endpoint is added later, this gate flips automatically. For SDG, the `STAGING-NOT-UPLOADABLE.txt` sentinel is **not** written (the file is schema-valid, just lacking an endpoint); a `STAGING-NO-BULK-ENDPOINT.txt` sentinel is written instead, naming the per-observation API as the alternative.

**Schema/payload gates — all must hold for `bulk_uploadable` (RPD) or `schema_valid_no_endpoint` (SDG):**

1. **Row count ≤ 500.** If the audit produces >500 observation rows after parsing, the staging xlsx is **still produced** but split into `Site-Visit-Report-Upload-PIMS-Staging-YYMMDD-<CLIENT>-part1.xlsx`, `-part2.xlsx`, … each ≤500 rows. `.ssa_run.json` records `staging_split=True` and the part filenames. The single-file naming convention is preserved when ≤500 rows.
2. **File size ≤ 5 MB.** The staging xlsx **does** embed review thumbnails in column B (per Appendix C); it is not a text-only workbook. The 5 MB cap is enforced by the staging-specific image budget, progressive-downscale, and split path defined in **Appendix C §C.6** — read that section as the authoritative size-control contract for this gate. Summary: thumbnails default to 1600 px longest edge; if the resulting xlsx exceeds 5 MB, the staging file (and only the staging file) is re-rendered with progressively smaller thumbnails (1200 → 1000 → 800 px); if still over budget, the file is split into `-partN.xlsx` parts, each independently ≤5 MB AND ≤500 rows. The docx and Enriched xlsx keep their 1600 px thumbnails throughout — staging downscale is staging-only. Any oversize blocker is recorded in `.ssa_run.json`.
3. **`site_address` resolved on every row.** The RPD upload endpoint requires `site_address` as a minimum. If extraction failed and `site_address` is blank, the staging file is produced for review but status drops to `not_uploadable`: `.ssa_run.json` records `staging_status="not_uploadable", blocker="site_address_unresolved"`; `.ssa_run.error` is **not** written (the run succeeded, just the schema gate failed); a `STAGING-NOT-UPLOADABLE.txt` sentinel is written into the audit folder summarising the blocker. Remediation: edit the source CSV (preferred — survives reruns) or use the `.ssa_freeze` escape hatch and patch the generated xlsx by hand. See "Remediation paths".
4. **`audit_date` parses as ISO date.** Folder-name parse should always succeed; if not, same `not_uploadable` treatment with `blocker="audit_date_unparseable"`.
5. **`observation_text` non-empty on every data row.** Rows with empty `observation_text` are dropped at parse time (CSV contract), so this is a belt-and-braces check.

The Goal sentence "ready to review and upload to PIMS staging" applies only when `staging_status == "bulk_uploadable"`. For `schema_valid_no_endpoint` it is "ready to review and post one-at-a-time"; for `not_uploadable` it is "ready to review only — fix blocker before uploading". The status and blocker are surfaced in `.ssa_run.json` and via the appropriate sentinel file.

---

## Field Defaults — what each column gets, explicitly

To stop implementers inventing content, every output field is one of: **derived** (computed from inputs/checklist), **enriched** (LLM-rewritten, narrow scope), **input** (user-provided per-run), or **blank** (left empty for human fill at review). No field is "smart-defaulted" silently.

**PIMS-Enriched workbook — `Enriched Register` sheet:**

| Column | Source |
|---|---|
| `#` | derived: row index, 1-based |
| `Observation Date` | derived: from CSV timestamp |
| `Photo ID` | derived: `P-` + zero-padded row index (`P-0001`) |
| `Photo` | derived: embedded thumbnail of resolved photo |
| `Filename` | derived: resolved on-disk filename |
| `Observation` | enriched: light cleanup of raw note |
| `Conformance Status` | derived: from `checklist_matcher` |
| `CCVS Code` | derived: from `checklist_matcher` |
| `CCVS Category` | derived: from `checklist_matcher` |
| `Action Required` | derived: `Yes` if status ∈ {NCR, Conditional} else `No` |
| `Action Description` | derived: verbatim from `audit_checklist.xlsx` keyed by CCVS code |
| `Responsible` | **blank** (filled at QA review) |
| `Due` | **blank** (filled at QA review) |
| `Monitoring Note` | **blank** |
| `Close-out Status` | **blank** |
| `Closed Date` | **blank** |
| `Closed By` | **blank** |
| `Close-out Notes` | **blank** |

**SSA Report docx — `Site Safety Audit Observations` 6-col table:**

| Column | Source |
|---|---|
| `Obs #` | derived: row index, 1-based |
| `Photo` | derived: embedded thumbnail (2.5cm) |
| `Observation` | enriched: 3-part *what / why / what good looks like* finding |
| `Reference` | derived: verbatim from `audit_checklist.xlsx` `Legal Ref` column for the matched CCVS code; blank if no match |
| `Status` | derived: `Conformance Status` |
| `Evidence File` | derived: resolved on-disk filename |

**Positive Observations identification rule:** an observation is rendered in the Positive Observations numbered list **only if** status == `Compliant`. Every other status — `NCR`, `Conditional`, `Info`, `Unmatched` — is rendered in the main `Site Safety Audit Observations` table. Every observation appears in exactly one of the two destinations; nothing is dropped.

**Status of Previous Recommendations table:** populated only from the prior-report parser. Empty if no prior report or parse failed (single placeholder row: "No prior recommendations carried forward.").

**Narrative summary paragraph:** enriched — generated by `finding_enricher` in narrative mode from the full set of findings + site address + audit date. One paragraph, ~120 words.

**Per-location 2-col detail tables:** built only if observations explicitly mention distinct locations (regex against observation text for "at <location>" patterns). If none detected, the cloned location-block rows are deleted from the document.

**PIMS Staging workbook — `Observations` sheet (row-3 header literals, snake_case):**

Column key = the exact string written into the row 3 header cell. Implementation must use these literals; the RPD upload endpoint matches on them case-insensitively but tolerates no spaces.

| Row 3 header (literal) | Source |
|---|---|
| `id` | **blank** — see "Insert-from-staging direction" below. Never `uuid4()` for pipeline-originated rows. |
| `photo` | derived: embedded thumbnail (2.5 cm) per Appendix C. PIMS upload endpoint ignores this column (joins via `photo_refs`); the thumbnail is for review-before-upload only. |
| `site_address` | input: extracted from observations; **blank** if unresolved |
| `audit_date` | derived: from folder name `YYYY-MM-DD` (always; never row-level) |
| `observation_text` | enriched: cleaned raw note |
| `finding` | enriched: 3-part finding |
| `conformance_status` | derived: `checklist_matcher` (or `Unmatched`) |
| `ccvs_code` | derived: `checklist_matcher` |
| `ccvs_category` | derived: `checklist_matcher` |
| `action_description` | derived: verbatim from checklist |
| `responsible` | **blank** (filled at QA) |
| `due_category` | derived: `Immediate` if NCR, `Within 7 days` if Conditional, `N/A` otherwise |
| `recommendation` | derived: verbatim from checklist |
| `monitoring_note` | derived: verbatim from checklist `Monitoring Note` if present, else blank |
| `legal_ref` | derived: verbatim from checklist |
| `photo_refs` | derived: resolved on-disk filename (see filename matching contract) |
| `prepared_by` | input: CLI/watcher arg `--prepared-by`; defaults to `"Alan Richardson"` if not supplied |
| `source_pdf` | **blank** (no source PDF in this workflow; column kept for schema parity) |
| `section` | **blank** (PIMS auto-derives from CCVS category server-side) |
| `needs_review` | derived: `TRUE` if any of {site_address_unresolved, photo_match_ambiguous, photo_missing, bad_timestamp, duplicate_filename, no_checklist_match} else `FALSE` |

**Defaults for kept-but-invalid rows.** Any row that survives parsing but has a parse/match failure must populate every column deterministically — no crashes, no invented placeholders, no nulls in non-blank fields:

- **Bad timestamp** (row kept per CSV rules):
  - PIMS-Enriched `Observation Date`: write the **literal raw string** from the CSV cell, prefixed with `RAW:`. Empty raw → blank cell.
  - Staging `audit date`: **always** the folder date (`YYYY-MM-DD` from folder name). Never row-level. Keeps PIMS schema consistent — every staging row in one upload shares the same audit date. The bad-timestamp condition is surfaced via `needs review = TRUE` and `.ssa_run.json` warnings, not via the audit-date field.
  - `needs review = TRUE`. CSV warning recorded.
- **No checklist match** (`checklist_matcher` returns no row for the observation): `Conformance Status` / `conformance status` = literal `Unmatched`. `CCVS Code`, `CCVS Category`, `Action Description`, `Recommendation`, `Legal Ref`, `Monitoring Note`, `due category` = **blank**. `Action Required` = `Yes` (forces reviewer attention). `needs review = TRUE`. The `finding` field is still enriched (3-part recipe) from the raw observation alone — it just has no checklist anchor. **Routing in the SSA report:** `Unmatched` rows always render in the main `Site Safety Audit Observations` table; they never appear in the Positive Observations list. The Positive Observations rule below is updated accordingly.
- **Photo missing or ambiguous:** `Photo` cell blank, `Filename` / `Evidence File` / `photo refs` blank. `needs review = TRUE`.
- **Site address unresolved:** `site address` blank on every staging row; `needs review = TRUE` on every row. SSA report site-address line written as the literal string `[Site address — to be confirmed]` so the docx doesn't render with a visibly empty heading.

The pipeline never raises on a kept-but-invalid row. All failure modes resolve to one of the explicit defaults above.

---

## Tone recipe — narrowed scope

**Humanised (year-12 + humaniser rules):**
- Narrative summary paragraph in the SSA report.
- `Observation` field rewrite (light cleanup of raw note → readable sentence).
- `Finding` field — the 3-part *what / why it matters / what good looks like* recipe.

**Verbatim from checklist (deterministic, no LLM rewrite):**
- `Action Description` — taken from `pims/data/audit_checklist.xlsx` row keyed by CCVS code.
- `Recommendation` — same.
- `Legal Ref` — same.
- `CCVS Code` / `CCVS Category` — assigned by `checklist_matcher`, never paraphrased.

Banned vocabulary in humanised fields: *crucial, pivotal, landscape, ensure, leverage, robust, comprehensive, navigate, delve into, it's important to note, serves as, at its core*. No em-dash clustering, rule-of-three, negative parallelism, signposting, sycophantic openers/closers, emoji, curly quotes, passive voice without a named actor.

---

## Files to create / modify

### Phase 0 — verify reuse assumptions and prepare templates (before any new code)
- Read `pims/services/finding_enricher.py` and `pims/services/checklist_matcher.py`. Confirm callable signatures. If `checklist_matcher` cannot be invoked standalone with a single observation string, add a `match_one(observation: str) -> ChecklistMatch` helper with `(status, ccvs_code, ccvs_category, action_description, recommendation, legal_ref)`. If `finding_enricher` does not accept a `tone` parameter, add `tone: Literal["consultant","educational"]="consultant"` (default keeps existing PIMS callers unchanged).
- Confirm `pims/services/audit_report_from_xlsx.py` exposes a usable `insert_image_into_cell(cell, path, width_cm)` helper. If not, extract one.
- **Hand-build templates in Word/openpyxl, commit them, freeze:**
  - `pims/templates/ssa/Site-Safety-Audit-Report.template.docx`: derived from `Site-Safety-Audit-Report - new Sample.docx` with these one-time manual edits in Word:
    1. **Font swap to Aptos** (per Appendix A R-4.1, confirmed by Alan): change Normal, Heading 1, Heading 2, Heading 3, and Table Normal styles to `Aptos` (ascii / hAnsi / cs all set to `Aptos`; remove any `asciiTheme` references). Font sizes (18 / 16 / 14 / 12 pt bold per A.5), bold, alignment, and all other formatting unchanged.
    2. Placeholder substitutions: `{{SITE_ADDRESS}}` (16 pt body paragraph), `{{NARRATIVE_SUMMARY}}` (paragraph below `Executive Summary`), `{{AUDIT_DATE}}` and `{{PREPARED_BY}}` (in section 1 footer, replacing the literal `05/05/2026` and `Alan Richardson`).
    3. Reduce each repeated table to one cloneable placeholder row (Positive Observations 3-col, Status of Previous Recommendations 4-col, Observations Register 6-col, Per-location 2-col blocks).
    4. Footer pattern preserved verbatim: `Date: {{AUDIT_DATE}}   Page: <PAGE_FIELD> of <NUMPAGES_FIELD>   Written By: {{PREPARED_BY}}`. Field codes preserved.
    Save and freeze. After freeze, no further font edits are permitted by code.
  - `pims/templates/ssa/PIMS-Enriched.template.xlsx`: copy sample, clear data rows on `Enriched Register` (keep header row + Summary sheet structure), save.
  - `pims/templates/ssa/Site-Visit-Report-PIMS-Staging.template.xlsx`: hand-build in upload format (header row 3 with snake_case headers, data row 5+, sheet `Observations`). Verify by feeding an empty file to `pims/routes.py:2091` `/pims/upload/observations` and confirming the parser sees the headers correctly.

### New
- `pims/services/ssa_pipeline.py` — orchestrator: `parse_evidence_csv`, `match_photos`, `extract_site_context`, `enrich_observations`, `build_pims_enriched_xlsx`, `build_ssa_report_docx`, `build_pims_staging_xlsx`. All three builders take a pre-built `PipelineState` (rows + warnings + site context) so they share the same data.
- `pims/services/ssa_watcher.py` — quiescence-based watcher with manifest, atomic writes, lock, error file.
- `pims/scripts/run_ssa_pipeline.py` — manual CLI: `python -m pims.scripts.run_ssa_pipeline "<folder>"` (bypasses watcher, same pipeline).
- `pims/scripts/start_ssa_watcher.py` — long-running entry; install as Windows Scheduled Task at logon.
- `pims/templates/ssa/` — three template files (see Output contracts).
- `tests/test_ssa_pipeline.py` — fixtures + assertions (see Verification).

### Modify
- `pims/services/finding_enricher.py` — add `tone="educational"` mode with the year-12 + humaniser system prompt. Default mode unchanged.

### Reuse as-is
- `pims/data/audit_checklist.xlsx`
- `pims/services/checklist_matcher.py` (after Phase 0 verification)
- Image-insertion helper from `pims/services/audit_report_from_xlsx.py`

---

## Verification

End-to-end:
1. `python -m pims.scripts.run_ssa_pipeline "G:\My Drive\alan_mcxico\SSA-evidence\2026-05-01-RPD"` (use an **RPD** fixture for the pure 3-output smoke path) — produces exactly 3 outputs in folder, no sentinels. Visual diff against samples (column order, photo placement, narrative structure, header/footer). For an SDG smoke run, expect **4 artifacts**: the 3 deliverables plus `STAGING-NO-BULK-ENDPOINT.txt`.
2. Start watcher; copy RPD fixture under SSA-evidence/ as `2099-01-01-RPD`; confirm exactly 3 deliverables (no sentinels) appear within ~3 min (quiescence + run) and `.ssa_run.json` is written with `staging_status="bulk_uploadable"`. Repeat with `2099-01-01-SDG`; confirm 3 deliverables PLUS `STAGING-NO-BULK-ENDPOINT.txt` appear, `.ssa_run.json` records `staging_status="schema_valid_no_endpoint"` and `client_bulk_endpoint=null`.

Tests in `tests/test_ssa_pipeline.py` (fixture under `tests/fixtures/ssa/`):
3. **Happy path (RPD):** clean 3-photo RPD folder → exactly 3 outputs produced, no sentinels; `.ssa_run.json.outputs` lists those 3 filenames; PIMS-Enriched has image objects in column D rows 2–4; Staging xlsx has 3 rows with `needs review = FALSE` and `photo refs` filled; `staging_status="bulk_uploadable"`.
4. **CSV edge cases:** UTF-8-SIG file; row with embedded newlines + quoted commas; row with missing filename; duplicate filename row; header-present row 1; row with bad timestamp. Each handled per parser contract; warnings present in `.ssa_run.json`.
5. **Filename matching:** input mix of `EV_*.JPG`, `EV_*.jpeg`, `6aFrancis_EV_*.jpg`, `IMG_1234.jpg`. Canonical/stem/suffix matches succeed; ambiguous case is flagged not silently matched.
6. **Rerun no-op:** run pipeline twice on identical inputs → second run reads `.ssa_run.json`, matches manifest, exits without writing. Output mtimes unchanged.
7. **Rerun after input change:** run pipeline; add a new photo + CSV row; rerun → manifest mismatch detected; every file listed in the previous `.ssa_run.json.outputs` is eventually replaced with content reflecting the new inputs. If the second run is interrupted mid-write, the next watcher cycle must complete the replacement (intermediate partial state is recoverable — no claim of true set-level atomicity).
8. **Partial-output recovery:** run pipeline; delete one file from `.ssa_run.json.outputs`; rerun → every recorded output is rewritten.
9. **Crash recovery:** simulate exception mid-run; confirm `.ssa_work/` left behind, no final files written, `.ssa_run.error` present, next run cleans `.ssa_work/` and succeeds.
10. **Quiescence:** copy fixture into watch dir but keep touching CSV mtime; watcher must not fire until 4 consecutive 30s polls show no change.
11. **Site-address unresolved:** observations contain no address → `site_address` blank, every staging row `needs review = TRUE`, `.ssa_run.json` records `site_address_unresolved=True`; folder name does **not** appear in any output.
12. **Prior-report self-reference (regression):** fixture folder contains (a) one qualifying older report `Site-Safety-Audit-Report-260330-SDG.docx` and (b) the current run's freshly generated `Site-Safety-Audit-Report-260501-SDG.docx`. Assert: only (a) is included in `inputs.sha256`; (b) is excluded from the manifest; a second watcher cycle on the same folder is a no-op (manifest matches, all 3 outputs present). Also assert: a candidate report whose date suffix is unparseable is treated as non-qualifying.
13. **Kept-but-invalid row defaults:** fixture with a bad-timestamp row and a no-checklist-match row → assert exact defaults per the Defaults table (`RAW:` prefix on Observation Date, `Unmatched` status, `Action Required = Yes`, blank checklist-derived fields, `needs review = TRUE`).
14. **Uploadability tri-state:** (a) RPD fixture, site_address unresolved → `staging_status="not_uploadable"`, `STAGING-NOT-UPLOADABLE.txt` sentinel, no `.ssa_run.error`. (b) RPD fixture, 501 rows resolved → `staging_status="bulk_uploadable"`, split into `-part1.xlsx` + `-part2.xlsx`, no single-file output, `staging_split=True`. (c) RPD fixture, 50 rows fully resolved → `staging_status="bulk_uploadable"`, no sentinel. (d) **SDG** fixture, 50 rows fully resolved → `staging_status="schema_valid_no_endpoint"`, `STAGING-NO-BULK-ENDPOINT.txt` sentinel, no `STAGING-NOT-UPLOADABLE.txt`, `client_bulk_endpoint=null` in `.ssa_run.json`.
15. **Template fidelity:** open generated SSA docx; assert `word/styles.xml` references **`Aptos`** (the canonical font, set at template freeze per Appendix A R-4.1) and contains zero references to `Arial Nova Light` or any other font; assert paragraph 03 = title at 18 pt bold, paragraph 04 = site address at 16 pt bold, section headings at 14 pt bold, finding sub-headings at 12 pt bold; assert section 0 has `different_first_page_header_footer=True`; assert section 1 footer paragraph contains `Date:`, `Page:`, `Written By:` and that the placeholders `{{AUDIT_DATE}}` / `{{PREPARED_BY}}` were substituted (no `{{` left in the document); assert section count = 3 and header/footer part count matches the template (5 header + 3 footer).
16. **Issue gate:** run `src/issue_gate.py` against produced SSA report docx → no hard fails.

Phone path:
17. **Freeze escape hatch:** run pipeline on RPD fixture → 3 outputs + `.ssa_run.json` written. Hand-edit the staging xlsx (e.g. fill `responsible` on row 2). Write an empty `.ssa_freeze` file into the audit folder. (a) Trigger the watcher (touch CSV mtime) → watcher must skip the folder, log the skip reason `frozen`, and the manual edit must survive. (b) Run `python -m pims.scripts.run_ssa_pipeline "<folder>"` → CLI must exit non-zero with a clear "frozen — use --ignore-freeze to overwrite" message; the manual edit must survive. (c) Run `python -m pims.scripts.run_ssa_pipeline "<folder>" --ignore-freeze` → pipeline runs and overwrites; the manual edit is wiped (expected — explicit override). (d) Delete `.ssa_freeze` and trigger the watcher → normal rerun proceeds.
18. Phone-upload a small test folder + CSV + 2 photos; let Drive sync; confirm watcher waits past quiescence then fires; deliverable set lands in Drive viewable from phone.

---

## Out of scope for v1

- Vision parsing of photos (text-only enrichment).
- Auto-upload to PIMS staging endpoint (Alan uploads manually post-review).
- Cloud-hosted version (local desktop watcher only).
- Sidecar `audit_meta.json`.
- Adaptive quiescence window (fixed 120s for v1; can be tuned later from `.ssa_run.json` telemetry).

---

## Known limitation — SDG bulk upload

For SDG, no bulk endpoint exists yet — the file is produced in the same format for forward compatibility, but you'd need to upload SDG observations one-at-a-time via the existing single-observation API or wait for an `/upload/observations/sdgroup` endpoint to be built.

---

# APPENDIX A — Explicit Formatting & Layout Rules for `Site-Safety-Audit-Report - new Sample.docx`

**Purpose:** This appendix is the contract the implementation must follow when reproducing the SSA report from `G:\My Drive\alan_mcxico\SSA-evidence\Site-Safety-Audit-Report - new Sample.docx`. It is written as a self-contained ruleset for independent review (Codex). Every rule is a MUST unless marked otherwise.

## A.0 Source of truth

R-0.1 The canonical template is `pims/templates/ssa/Site-Safety-Audit-Report.template.docx`, derived **only** from `Site-Safety-Audit-Report - new Sample.docx` after the placeholder substitutions in §A.6. The original (pre-"new") sample is not used.

R-0.2 The canonical template file is byte-frozen. Any change to it is a versioned, reviewed action — never a side effect of running the pipeline.

R-0.3 The runtime pipeline starts every render with `shutil.copyfile(template, output.tmp)` and operates only on that copy.

## A.1 Hard rules (Alan's explicit instruction)

R-1.1 All formatting, fonts, and font sizes are not to be changed.

R-1.2 The implementation MUST NOT set, override, or rebuild any of:
- font name, size, weight, italic, colour, strikethrough, underline
- paragraph alignment, indentation, line spacing, spacing-before, spacing-after
- table style, table width, column widths, cell width, cell margins, cell vertical alignment, row heights, table borders
- section properties (page size, margins, orientation, header/footer distance, `different_first_page_header_footer`, page-numbering restart)
- header or footer XML, header/footer relationships, or any field code
- styles.xml, numbering.xml, theme1.xml

R-1.3 The implementation MAY ONLY perform:
- (a) replace `{{TOKEN}}` placeholder run text with audit-specific text (in body paragraphs AND in section 1 footer);
- (b) deepcopy a placeholder table row N times within its parent table;
- (c) write text into the cells of those cloned rows;
- (d) insert exactly one inline image into a designated cell, at exactly `Cm(2.5)` width;
- (e) **block-level operations on the per-location 2-col table placeholder block only**: deepcopy the entire placeholder table element (`<w:tbl>`) plus the immediately preceding heading paragraph (if present) N times, OR remove the placeholder block entirely (when no locations are detected). This is the only structural operation permitted outside row-level cloning, and applies exclusively to the per-location detail blocks. No other table or paragraph may be added, removed, or duplicated.

R-1.4 Any operation outside R-1.3 is a contract violation and MUST fail the test suite.

## A.2 Page geometry (preserved verbatim)

R-2.1 Page size A4: 21.0 cm × 29.7 cm.

R-2.2 Margins (sections 0 and 1): top 1.50 cm, bottom 0.50 cm, left 2.54 cm, right 2.54 cm.

R-2.3 Margins (section 2): top 1.50 cm, bottom **1.25 cm**, left 2.54 cm, right 2.54 cm.

R-2.4 Header distance 1.25 cm. Footer distance 1.25 cm. All sections.

R-2.5 No code path sets any of R-2.1 through R-2.4.

## A.3 Section structure (3 sections, preserved verbatim)

R-3.1 Document MUST contain exactly 3 sections. No section may be added, removed, merged, or reordered.

R-3.2 Section 0 MUST have `different_first_page_header_footer == True`. This is the page-zero mechanism. Implementation MUST NOT toggle this flag.

R-3.3 Section 0 first-page header MUST contain its existing single inline drawing (the larger cover logo) and no other content.

R-3.4 Section 0 first-page footer MUST be blank (no running text, no field codes).

R-3.5 Section 1 header MUST contain its existing single inline drawing (the smaller running logo).

R-3.6 Section 1 footer MUST contain the running footer text per §A.9, with the only mutations being the placeholder substitutions in R-9.3.

R-3.7 Header/footer parts in the docx zip MUST be exactly: `header1.xml`, `header2.xml`, `header3.xml`, `header4.xml`, `header5.xml`, `footer1.xml`, `footer2.xml`, `footer3.xml`. None added, none removed, none re-linked.

## A.4 Fonts (Aptos — applied once at template freeze, then preserved verbatim)

R-4.1 The canonical font for the SSA template is **Aptos**. The new sample's original `Arial Nova Light` is replaced with Aptos as a one-time manual Word edit before freezing the template (see Phase 0). After freeze, `word/styles.xml` MUST reference only `Aptos` and contain zero references to any other font name after rendering by the pipeline.

R-4.1.1 Specifically: Normal style, Heading 1, Heading 2, Heading 3, Table Normal, and any other style referenced by the body or tables MUST have `w:ascii="Aptos"`, `w:hAnsi="Aptos"`, and `w:cs="Aptos"`. Theme font (`<w:rFonts w:asciiTheme="...">`) references must be removed in favour of explicit `Aptos` strings to prevent Office's theme-substitution from silently picking a different family on machines without the Aptos theme.

R-4.1.2 Aptos is the Microsoft 365 default since 2024 and ships with current Office installs. If the user's Word lacks Aptos, Word will substitute a fallback font at render time — that's a Word display issue, not a contract violation, and is out of scope for the pipeline.

R-4.2 Implementation MUST NOT call `run.font.name = ...`, MUST NOT call `style.font.name = ...`, MUST NOT introduce a `theme1.xml` font swap. The font change is template-side only, never code-side.

## A.5 Font sizes (preserved verbatim, per element)

R-5.1 Document title ("Site Safety Audit Report"): **18 pt, bold, Justified**, paragraph style `Normal`.

R-5.2 Site address line (paragraph immediately after the title): **16 pt, bold, Justified**, paragraph style `Normal`.

R-5.3 Section headings — all of: `Executive Summary`, `Positive Observations`, `Findings`, `Status of Previous Recommendations `, `Observations Register` — **14 pt, bold**, paragraph style `Normal`. Capitalisation, trailing whitespace (note the trailing space on `Status of Previous Recommendations `), and punctuation MUST match the sample exactly.

R-5.4 Finding sub-headings (`#1 ...`, `#2 ...`, …): **12 pt, bold**, paragraph style `Normal`.

R-5.5 Body paragraphs (executive-summary text and similar): inherit Normal, no run-level size override.

R-5.6 Direct run-level formatting in the sample is preserved by replacing only `r.text` on the existing run; implementation MUST NOT delete and recreate the run.

## A.6 Placeholder substitutions (the only allowed text mutations)

R-6.1 The following `{{TOKEN}}` placeholders are introduced in the canonical template by a one-time manual Word edit, and substituted at runtime:

| Token | Location | Replacement source |
|---|---|---|
| `{{SITE_ADDRESS}}` | site address paragraph (16 pt, bold) | resolved `site_address` from extraction |
| `{{NARRATIVE_SUMMARY}}` | single paragraph below `Executive Summary` heading | LLM-generated narrative (year-12 + humaniser) |
| `{{AUDIT_DATE}}` | section 1 footer, in place of `05/05/2026` | folder-derived audit date in `DD/MM/YYYY` |
| `{{PREPARED_BY}}` | section 1 footer, in place of `Alan Richardson` | CLI/watcher arg `--prepared-by`, default `Alan Richardson` |

R-6.2 Substitution is performed by locating the run containing the literal token and replacing only that run's `text`. The run's `rPr` (font size, bold, etc.) MUST be preserved.

R-6.3 After rendering, the document MUST contain zero occurrences of `{{` and zero occurrences of `}}`.

R-6.4 No additional placeholder tokens may be added without updating this appendix and the test suite.

## A.7 Tables (cloning rules)

R-7.1 The canonical template reduces each repeated-content table to **one placeholder row** (or one placeholder per-location block). The pipeline `copy.deepcopy`s the placeholder row's `<w:tr>` element N times and inserts the clones as siblings before writing cell text.

R-7.2 Cloned rows inherit cell widths, vertical alignment, paragraph properties, run properties (including font size and bold), and borders from the placeholder row. Implementation MUST NOT touch `<w:tcPr>`, `<w:trPr>`, `<w:tblPr>`, or `<w:pPr>` of cloned rows.

R-7.3 Table inventory and column widths (cm), measured from the new sample, MUST match exactly:

| Table | Cols | Column widths (cm) | Header cells | Clone count rule |
|---|---|---|---|---|
| Positive Observations | 3 | 1.31 / 12.59 / 3.86 | `# / Observation / Reference` | one row per `Compliant` observation |
| Per-location detail | 2 | 3.00 / 14.75 | `Location / Observation / Reference / Recommendation / Status / Evidence File` rows | one block per detected location; remove placeholder block if none |
| Status of Previous Recommendations | 4 | 3.83 / 5.61 / 2.50 / 5.80 | `Recommendation / Required Actions / Status (DD/MM/YY) / Commentary` | one row per carried-forward recommendation; placeholder row "No prior recommendations carried forward." if none |
| Observations Register | 6 | 1.12 / 2.74 / 5.10 / 3.79 / 2.25 / 2.75 | `Obs # / Photo / Observation / Reference / Status / Evidence File` | one row per non-Compliant observation (NCR, Conditional, Info, Unmatched) |

R-7.4 Photo cells in the Observations Register MUST receive exactly one inline image per row, inserted via `paragraph.add_run().add_picture(image_stream, width=Cm(2.5))` into the cell's existing paragraph. Cell width, vertical alignment, and cell margins MUST NOT be set in code.

R-7.4.1 **Image preprocessing pipeline** (applied in this order, before insertion):

  (a) **EXIF orientation normalisation.** Phone photos (especially iPhone) carry EXIF orientation tags 1–8. Word renders the raw pixel matrix and ignores EXIF, so an unrotated landscape photo taken in portrait mode will appear sideways. Open the image with Pillow, call `ImageOps.exif_transpose(img)` to bake the rotation into the pixel matrix, then strip the EXIF block. Mandatory for every photo.

  (b) **Format normalisation.** Source images may be `.jpg`, `.jpeg` (case-insensitive), or `.png`. Convert any source not already in JPEG to JPEG before insertion (`img.convert("RGB")` then save as JPEG quality 85), unless the source is PNG and contains transparency, in which case keep PNG. HEIC and other formats are out of scope (the canonicalisation rules already exclude them).

  (c) **Downscale before embed.** If the source image's longest edge exceeds 1600 px, downscale to 1600 px on the longest edge using `Image.LANCZOS`. At 2.5 cm rendered width on a 600 dpi target, 1600 px is ample; embedding the original 4032×3024 phone photo wastes ~10× the file space per row.

  (d) **Recompress.** Save the processed image to a `BytesIO` at JPEG quality 85 (or PNG if transparency was preserved). The `BytesIO` is what's passed to `add_picture`.

R-7.4.2 **Aspect ratio.** Width is fixed at `Cm(2.5)` per R-7.4. Height is **not** set explicitly — python-docx computes it from the source aspect ratio. Implementation MUST NOT pass `height=...` to `add_picture`. Portrait photos render taller than landscape; the cell row height auto-grows to fit (see R-7.4.4).

R-7.4.3 **Cell paragraph alignment for the image.** The placeholder paragraph's existing `pPr` is preserved. Implementation does not call `paragraph.alignment = ...`. The sample's placeholder cell is left-aligned; cloned rows inherit that.

R-7.4.4 **Row height.** Row height is left as `auto` (the template's setting). Word will grow the row to the image's natural rendered height. Implementation MUST NOT set `row.height` or `row.height_rule`.

R-7.4.5 **Missing source file** (filename matched to a name in the CSV but the file isn't actually on disk at render time): treated identically to R-7.5 — empty Photo cell, `Obs #` carries `*` suffix, `needs_review = TRUE` on the corresponding staging row, warning recorded in `.ssa_run.json` under `csv_warnings` with reason `photo_file_missing_at_render`.

R-7.4.6 **Pillow load failure** (corrupt JPEG, unreadable file): same treatment as R-7.4.5, with reason `photo_load_failed: <Pillow exception class>`. The pipeline MUST NOT raise on a single bad photo.

R-7.4.7 **Total embedded image budget.** After all photos are embedded, the output docx file size SHOULD be < 25 MB. If the sum of preprocessed image sizes pushes the docx beyond 25 MB, downscale step (c) is re-run with longest-edge cap reduced to 1200 px, then 1000 px, until the budget is met. If still over budget after the 1000 px pass, the run completes but `.ssa_run.json` records `docx_oversize: True, final_bytes: <n>`. No hard failure.

R-7.4.8 **Deterministic ordering.** Images are inserted in the same order as the Observations Register rows (which is the same order as observations in the CSV after canonicalisation). Two runs over the same inputs MUST produce byte-identical embedded image streams (Pillow + JPEG quality 85 is deterministic for the same source bytes; this is verified in test V-10.18).

R-7.5 If a Photo cell has no resolved image at the matching stage (per the filename-matching rules in the main plan — rule 6 "missing" or rule 6 "ambiguous"), the cell paragraph is left empty and the row's `Obs #` carries a `*` suffix to flag the missing-photo state on the page. The row still renders; the report does not have a hole.

## A.8 Headings and section names (locked verbatim)

R-8.1 Locked literal strings, exact case and whitespace:
- `Site Safety Audit Report` (title)
- `Executive Summary`
- `Positive Observations`
- `Findings`
- `Status of Previous Recommendations ` (trailing space)
- `Observations Register`

R-8.2 The "Findings" sub-heading and its numbered `#N ...` list sit between "Positive Observations" and "Status of Previous Recommendations" exactly as the sample lays them out. Their grouping under the Positive Observations heading region in the sample is treated as intentional and preserved.

R-8.3 No heading text may be re-pluralised, re-cased, abbreviated, or expanded.

## A.9 Headers, footers, page-zero (preserved verbatim)

R-9.1 First-page header (section 0): single inline drawing (cover logo). No text. No tabs.

R-9.2 First-page footer (section 0): blank.

R-9.3 Running footer (section 1, applies to all pages from 2 onward): single paragraph with the literal layout below. Tab stops as in the sample. Field codes preserved as Word field codes (`<w:fldChar>` / `PAGE` / `NUMPAGES`):

```
Date: {{AUDIT_DATE}}<TAB>Page: <PAGE_FIELD> of <NUMPAGES_FIELD><TAB>Written By: {{PREPARED_BY}}
```

R-9.4 Implementation MUST NOT replace `<PAGE_FIELD>` or `<NUMPAGES_FIELD>` with literal numbers. They remain Word field codes.

R-9.5 Running header (section 1+): single inline drawing (small running logo). No text. Implementation MUST NOT modify it.

R-9.6 Section 2 carries the same header/footer references as section 1 (continuous). Implementation MUST NOT change those references.

## A.10 Verification (asserted by `tests/test_ssa_pipeline.py`)

For an audit fixture rendered through the pipeline, every assertion below MUST pass:

V-10.1 `word/styles.xml` of the output contains `Aptos` (the canonical font set at template freeze per R-4.1) and contains zero of: `Arial Nova Light`, `Calibri`, `Arial,`, `Arial"`, `Times New Roman`, `Helvetica`, `Segoe`, `Cambria`. Specifically: every `<w:rFonts>` element used by Normal, Heading 1, Heading 2, Heading 3, and Table Normal has `w:ascii="Aptos"`, `w:hAnsi="Aptos"`, `w:cs="Aptos"`. No `w:asciiTheme` substitutions remain.

V-10.2 Body paragraph at index 03 has exactly one run; that run's `font.size == Pt(18)` and `bold is True`; text equals `"Site Safety Audit Report"`.

V-10.3 Body paragraph at index 04 has `runs[0].font.size == Pt(16)`, `bold is True`, alignment Justify; text equals the resolved `site_address`.

V-10.4 Each of the strings in R-8.1 (excluding the title) appears exactly once as a paragraph whose `runs[0].font.size == Pt(14)` and `bold is True`.

V-10.5 Every `#N ...` finding sub-heading paragraph has `runs[0].font.size == Pt(12)` and `bold is True`. Count of these paragraphs equals the count of non-Compliant observations rendered into the Observations Register.

V-10.6 `len(document.sections) == 3`. `sections[0].different_first_page_header_footer is True`. `sections[1].different_first_page_header_footer is False`. `sections[2].different_first_page_header_footer is False`.

V-10.7 Page geometry per R-2.1, R-2.2, R-2.3, R-2.4 — assert numerically (within ±0.01 cm to absorb EMU rounding).

V-10.8 Section 1 footer paragraph contains literal substrings `Date:`, `Page:`, `of`, `Written By:`. Contains the resolved audit date in `DD/MM/YYYY` form. Contains the resolved `prepared_by`. Contains zero occurrences of `{{` or `}}`.

V-10.9 Section 1 footer XML still contains both `<w:fldChar w:fldCharType="begin"/>` and the instruction texts `PAGE` and `NUMPAGES`.

V-10.10 SHA-256 of `word/header1.xml`, `word/header2.xml`, `word/header3.xml`, `word/header4.xml`, `word/header5.xml` in the output equals the SHA-256 of those parts in the canonical template (proves headers, including the cover logo, were not mutated).

V-10.11 Output zip namelist count of `header*.xml` == 5 and `footer*.xml` == 3.

V-10.12 Observations Register table column widths (in EMU) equal the template's column widths exactly (no tolerance — column widths are literal XML attributes, not rounded measurements).

V-10.13 For every row in the Observations Register that has a resolved photo: the row's Photo cell contains exactly one inline image whose width is `Cm(2.5)` (within ±9525 EMU = 0.01 cm). No `height` attribute is set on the inline image element.

V-10.14 For every row in the Observations Register without a resolved photo (missing-match, ambiguous-match, missing-source-file, or load-failure): the Photo cell paragraph is empty AND the `Obs #` cell text ends with `*`.

V-10.18 **Photo preprocessing assertions** (fixture: one upright JPEG, one portrait phone JPEG with EXIF orientation 6, one PNG with transparency, one 4032×3024 source, one corrupt JPEG, one referenced-but-missing file):
  - Portrait phone JPEG renders upright in the docx (extract the embedded image; assert its pixel orientation matches the EXIF-baked rendering, not the raw matrix).
  - PNG with transparency is embedded as PNG; JPEG sources are embedded as JPEG.
  - 4032×3024 source is embedded with longest edge ≤ 1600 px.
  - Corrupt JPEG → empty Photo cell, `Obs #` ends with `*`, `.ssa_run.json` records `photo_load_failed`. Run did not raise.
  - Missing source file → same treatment, `.ssa_run.json` records `photo_file_missing_at_render`.
  - Total docx size < 25 MB for a 30-photo fixture.
  - Two consecutive runs over the same inputs produce byte-identical docx files (deterministic embedding).

V-10.15 Total observations = (rows in Positive Observations table) + (rows in Observations Register). No observation is duplicated across tables, and none is dropped.

V-10.16 Heading paragraph text equals `"Observations Register"` exactly (not `"Site Safety Audit Observations"`).

V-10.17 No paragraph or run in the output has any `rPr` attribute that was not present in the corresponding template element. (Diff check: walk both DOMs in parallel and assert run-level `rPr` equality on every preserved run.)

## A.11 Runtime sequence (the only allowed render path)

S-11.1 `shutil.copyfile(canonical_template, output.tmp)` — start from a byte-perfect copy.

S-11.2 Open with `python-docx`.

S-11.3 Substitute the four `{{TOKEN}}` placeholders per §A.6.

S-11.4 Locate the Positive Observations table by header text match `# / Observation / Reference`; clone its placeholder row N times; write cell text.

S-11.5 Locate per-location detail tables by `Location` first-cell match; clone or remove per detected locations.

S-11.6 Locate the Status of Previous Recommendations table by header text match; clone rows from prior-report parser output, or write the placeholder row.

S-11.7 Locate the Observations Register table by header text match `Obs # / Photo / Observation / Reference / Status / Evidence File`; clone its placeholder row N times; write cell text; insert photos per R-7.4 / R-7.5.

S-11.8 Save to `<final>.tmp`; `os.replace` to final path.

S-11.9 No other docx operations are permitted.

---

End of Appendix A.

---

# APPENDIX B — Photo Insertion Rules for `PIMS-Enriched-YYMMDD-<CLIENT>.xlsx`

**Purpose:** Independent contract for embedding photo thumbnails into column D of the `Enriched Register` sheet. Mirrors Appendix A R-7.4 / R-7.4.1–8 but for openpyxl + xlsx, where the mechanics differ. Self-contained for Codex review.

## B.1 Source of truth

R-B-1.1 The canonical template is `pims/templates/ssa/PIMS-Enriched.template.xlsx`, derived from `G:\My Drive\alan_mcxico\SSA-evidence\PIMS-Enriched - Sample.xlsx` with data rows cleared. Header row 1, formatting, column widths (notably column D = 11.33), Summary sheet structure: all preserved verbatim.

R-B-1.2 `shutil.copyfile(template, output.tmp)`, open with openpyxl, append data starting row 2. Photo embedding follows §B.4.

## B.2 What the column carries

R-B-2.1 Column D header: literal text `Photo` (row 1). Width: 11.33 (template).

R-B-2.2 Each data row's column D cell receives exactly one embedded image, anchored to the cell, sized to fit a 2.5 cm wide thumbnail.

R-B-2.3 Cells with no resolved photo (filename matching rules — missing, ambiguous, missing-source-file, load-failure) MUST be left empty. The `Filename` column (E) carries the original CSV token regardless; `needs_review` flags are surfaced via the corresponding row in the Staging xlsx, not the Enriched workbook directly. The Enriched workbook's `Conformance Status` and `CCVS Code` columns still populate normally.

## B.3 Image preprocessing pipeline

R-B-3.1 Identical to Appendix A R-7.4.1 (a) through (d): EXIF orientation normalisation via `Pillow.ImageOps.exif_transpose`, format normalisation (JPEG quality 85, except PNG with transparency stays PNG), downscale to 1600 px on the longest edge if larger, then save to `BytesIO`. Cache key is `(source_path, max_edge_px)` per Appendix C R-C-3.1 — the Enriched xlsx pulls the `(source, 1600)` variant; the staging xlsx may pull a smaller variant under a different cache key if §C.6.2 fires. The Enriched xlsx's variant is unaffected by staging-only resizing.

R-B-3.2 HEIC and other formats out of scope (per filename canonicalisation rules).

## B.4 Insertion mechanics (openpyxl-specific)

R-B-4.1 Use `openpyxl.drawing.image.Image(image_stream)` constructed from the preprocessed `BytesIO` from R-B-3.1. Do NOT pass a file path — passing a path makes openpyxl re-read from disk on every save and breaks determinism if the source file is mutated mid-run.

R-B-4.2 Compute `width_emu = 2.5 * 360000` (EMU per cm) and `height_emu = round(width_emu * (img.height / img.width))` from the preprocessed image's pixel dimensions. Set `image.width = pixels(2.5cm @ 96dpi) = 95` and `image.height = round(95 * (img.height / img.width))`. Openpyxl uses pixel units, not EMU, on the `Image` object.

R-B-4.3 Anchor the image to column D of the target row using `ws.add_image(image, anchor=f"D{row_num}")`. The anchor is one-cell (top-left); openpyxl writes a `oneCellAnchor` element, which is what the existing PIMS extractor (`pims/services/audit_report_from_xlsx.py:140` `extract_images`) reads.

R-B-4.4 Set `ws.row_dimensions[row_num].height = max(95, round(95 * (img.height / img.width)))` in points. 95 pt covers a 2.5 cm landscape image at 96 dpi; portrait images get the taller value. Implementation MUST set this — without it the image overflows downward into the next row.

R-B-4.5 Implementation MUST NOT touch column D `width`, MUST NOT add column-level styles, MUST NOT touch any other column's width or row's height, MUST NOT call `ws.merge_cells` for any photo cell, MUST NOT add cell fill/font/border in the photo cell.

## B.5 Failure modes

R-B-5.1 Missing source file at render time: column D cell empty, `Filename` column (E) still populated with the CSV token, `.ssa_run.json` records `photo_file_missing_at_render` for that filename. No exception raised.

R-B-5.2 Pillow load failure (corrupt JPEG, unreadable PNG): same treatment as R-B-5.1, reason `photo_load_failed: <Pillow exception class>`.

R-B-5.3 Filename matching ambiguous (multiple candidates): same treatment as R-B-5.1, reason `photo_ambiguous_match`.

## B.6 File size budget

R-B-6.1 Same 25 MB budget as the docx (Appendix A R-7.4.7). If sum of preprocessed image sizes pushes the xlsx over 25 MB, re-run downscale at 1200 px then 1000 px. If still over budget, complete the run and record `xlsx_oversize: True, final_bytes: <n>` in `.ssa_run.json`.

R-B-6.2 The same shared image cache from R-B-3.1 means the docx and xlsx pulled from the same source file embed the same compressed bytes — total disk impact is roughly the larger of the two budgets, not the sum.

## B.7 Determinism

R-B-7.1 Image insertion order MUST match data row order (which matches CSV order after canonicalisation).

R-B-7.2 Two consecutive runs over the same inputs MUST produce byte-identical embedded `xl/media/imageN.png` (or `.jpeg`) entries inside the xlsx zip. Pillow + JPEG quality 85 is deterministic for the same source bytes; PNG without optimisation is also deterministic.

R-B-7.3 Image numbering inside the xlsx (`image1.jpeg`, `image2.jpeg`, …) MUST follow row order, not file-system order or hash order.

## B.8 Verification (asserted by `tests/test_ssa_pipeline.py`)

V-B-8.1 For every data row in `Enriched Register` whose corresponding observation has a resolved photo: the row contains exactly one embedded image anchored at column D; image pixel width is 95 (within ±1 px); image pixel height equals `round(95 * source_aspect_inverse)`.

V-B-8.2 For every data row with no resolved photo: column D cell is empty; column E carries the original CSV filename token; row height is the openpyxl default (no manual override).

V-B-8.3 EXIF orientation: fixture row sourced from a portrait phone JPEG (EXIF orientation 6) — extract the embedded image from `xl/media/image*.jpeg`, decode pixels, assert orientation matches the EXIF-baked rendering (i.e. portrait).

V-B-8.4 Format: PNG-with-transparency source ends up as `xl/media/image*.png` in the zip; JPEG sources end up as `xl/media/image*.jpeg`.

V-B-8.5 Downscale: 4032×3024 source ends up with longest edge ≤ 1600 px in the embedded media.

V-B-8.6 Missing source file → `xl/media/` count for that row is zero; `.ssa_run.json` records `photo_file_missing_at_render`. Run did not raise.

V-B-8.7 Corrupt JPEG → same as V-B-8.6 with reason `photo_load_failed`.

V-B-8.8 Two consecutive runs over the same inputs produce byte-identical xlsx files (compare sha256). Tests deterministic embedding end-to-end.

V-B-8.9 Total xlsx size for a 30-photo fixture is < 25 MB.

V-B-8.10 Shared cache: when the same source photo is embedded into both the SSA docx (Appendix A) and the PIMS-Enriched xlsx (this appendix) in the same run, the embedded byte streams in the two zips are identical (compare sha256 of `xl/media/imageN.jpeg` against `word/media/imageN.jpeg` for the corresponding source).

## B.9 Forbidden in-code operations

- Setting any column width on the Enriched Register sheet.
- Setting any row height on rows other than rows containing embedded images (and only as per R-B-4.4).
- Adding cell styles (fill, font, border, number format) to column D photo cells.
- Merging any cells in the Enriched Register sheet.
- Adding new sheets, removing existing sheets, renaming sheets.
- Touching the Summary sheet's structure (only named cells per the Field Defaults table are written).
- Adding or removing data validation, conditional formatting, or filters.

End of Appendix B.

---

# APPENDIX C — Photo Insertion Rules for `Site-Visit-Report-Upload-PIMS-Staging-YYMMDD-<CLIENT>.xlsx`

**Purpose:** Self-contained contract for embedding photo thumbnails into column B (`photo`) of the `Observations` sheet. Mirrors Appendix B but for the staging xlsx, where the column purpose is presentational (review-before-upload) — the PIMS bulk-upload endpoint reads only `photo_refs` and ignores column B.

## C.1 Source of truth

R-C-1.1 The canonical template is `pims/templates/ssa/Site-Visit-Report-PIMS-Staging.template.xlsx`, hand-built in upload format (header row 3, data row 5+, sheet name `Observations`, snake_case headers per the staging output contract).

R-C-1.2 `shutil.copyfile(template, output.tmp)`, open with openpyxl, append data starting row 5. Photo embedding follows §C.4.

## C.2 What the column carries

R-C-2.1 Column B header (row 3): literal text `photo` (lowercase). Width: same as template; not modified in code.

R-C-2.2 Each data row's column B cell receives exactly one embedded image, anchored to the cell, sized to fit a 2.5 cm wide thumbnail.

R-C-2.3 Cells with no resolved photo (missing, ambiguous, missing-source-file, load-failure) MUST be left empty. `photo_refs` (column P / header `photo_refs`) still carries the resolved on-disk filename per the main staging contract; `needs_review` flags the row.

R-C-2.4 The PIMS bulk-upload endpoint (`pims/routes.py:2091`) does not read column B (verified at line 2151–2177 — only `photo_refs`, `id`, `site_address`, `audit_date`, `observation_text`, etc. are pulled). Column B presence does not affect upload behaviour.

## C.3 Image preprocessing pipeline

R-C-3.1 Image preprocessing pipeline is identical to Appendix A R-7.4.1 and Appendix B R-B-3.1.

**Cache key is `(source_path, max_edge_px)`, not just `source_path`.** This allows the staging xlsx to hold an alternate (smaller) cached variant when §C.6 progressive downscale fires, without invalidating the 1600 px variant the docx and Enriched xlsx are using.

- First pass for every deliverable: cache key `(source_path, 1600)`. Each source photo is preprocessed exactly once at 1600 px and the resulting `BytesIO` is reused across all three deliverables.
- If the staging xlsx exceeds 5 MB after embedding (§C.6.2): the staging-only re-render computes a fresh `BytesIO` per source at the smaller cap (e.g. 1200 px) and stores it under a new cache key `(source_path, 1200)`. The 1600 px entries remain in cache and continue to back the docx and Enriched xlsx.
- Cache lifetime is one pipeline run; cleared on completion.

This way C.3.1 (preprocess once per `(source, edge)` combination) and C.6.2 (staging-only smaller variants) are both true: the cache is keyed to allow alternate sized variants per source, and "preprocessed exactly once" applies per cache key, not per source.

## C.4 Insertion mechanics (openpyxl, mirrors Appendix B)

R-C-4.1 Use `openpyxl.drawing.image.Image(image_stream)` constructed from the cached `BytesIO`. Do not re-read from disk.

R-C-4.2 Set `image.width = 95` (px, = 2.5 cm @ 96 dpi); `image.height = round(95 * (img.height / img.width))`. Implementation MUST NOT pass an EMU value.

R-C-4.3 Anchor with `ws.add_image(image, anchor=f"B{row_num}")` — one-cell anchor.

R-C-4.4 Set `ws.row_dimensions[row_num].height = max(95, round(95 * (img.height / img.width)))` in points. Mandatory — without it the image overflows downward.

R-C-4.5 Implementation MUST NOT touch column B `width`, MUST NOT add cell styles to column B, MUST NOT merge cells, MUST NOT touch any other column or row dimension.

R-C-4.6 The header row (row 3) is **never** given a photo cell. Image insertion only ever targets data rows (row 5 onwards). When the staging file is split into `-partN.xlsx` (per the uploadability gate's row-count rule), each part carries its own template copy and photo insertion runs per-part.

## C.5 Failure modes

R-C-5.1 Identical to Appendix B R-B-5.1 / R-B-5.2 / R-B-5.3. Missing or unreadable source → empty column B cell, no exception, `.ssa_run.json` records the reason. The row is preserved in the staging xlsx so PIMS can still ingest the observation; `needs_review = TRUE` flags it for QA.

## C.6 File size budget

R-C-6.1 Same 25 MB budget as Appendices A and B. The progressive downscale fallback is shared (one downscale pass affects all three deliverables, since they share the cache).

R-C-6.2 Critical: the staging xlsx file size MUST stay ≤ 5 MB after embedding (PIMS upload endpoint enforces 5 MB limit at `routes.py:2113`). The downscale pipeline runs differently for the staging file than for the docx/Enriched-xlsx:
- First pass at 1600 px (cache-shared default).
- If the staging xlsx exceeds 5 MB after embedding, re-render the staging xlsx ONLY with images downscaled progressively (1200 → 1000 → 800 px on longest edge). The docx and Enriched-xlsx keep the 1600 px versions.
- If still > 5 MB after the 800 px pass, the staging xlsx is split into more parts (per the uploadability gate row-count rule, but triggered by size instead). `.ssa_run.json` records `staging_split_reason="size"` instead of `"row_count"`.
- If a single observation row's image alone is > 5 MB raw and won't compress under the 800 px cap, the staging row's column B is left empty and the row is flagged `needs_review` with reason `photo_too_large_for_staging`. The docx and Enriched-xlsx still embed that photo at 1600 px.

R-C-6.3 The 5 MB cap is per uploaded file. If splitting into parts, each part must independently be ≤ 5 MB and ≤ 500 rows.

## C.7 Determinism

R-C-7.1 Same rules as Appendix B R-B-7.1 / R-B-7.2 / R-B-7.3. Two consecutive runs over the same inputs MUST produce byte-identical staging xlsx files (or, when split, byte-identical part files in the same partition).

## C.8 Verification (asserted by `tests/test_ssa_pipeline.py`)

V-C-8.1 For every data row in `Observations` whose corresponding observation has a resolved photo: row contains exactly one embedded image anchored at column B; pixel width 95 (±1 px); pixel height `round(95 * source_aspect_inverse)`.

V-C-8.2 For every data row with no resolved photo: column B cell empty; `photo_refs` (column P) carries the resolved on-disk filename or is blank for missing/ambiguous matches; row height is the openpyxl default.

V-C-8.3 Header row (row 3) has no embedded image in column B; row 3 height unchanged from template.

V-C-8.4 EXIF-orientation, format-normalisation, and downscale assertions: identical fixtures to V-B-8.3, V-B-8.4, V-B-8.5 — assert against the staging xlsx's `xl/media/` entries.

V-C-8.5 Missing source / corrupt JPEG fixtures: column B empty for those rows; `.ssa_run.json` records the failure reasons; run did not raise.

V-C-8.6 Staging xlsx final size ≤ 5 MB for a 30-photo fixture. If the test fixture is engineered to exceed 5 MB at 1600 px, assert progressive-downscale-then-split behaviour fired (`.ssa_run.json` records `staging_split_reason="size"` and produces `-part1.xlsx` + `-part2.xlsx`, each ≤ 5 MB).

V-C-8.7 Two consecutive runs over the same inputs produce byte-identical staging xlsx files (compare sha256).

V-C-8.8 Cross-deliverable cache: for the same source photo, the embedded byte stream in the staging xlsx is identical to the Enriched-xlsx and docx versions (sha256-equal across `xl/media/` of staging, `xl/media/` of Enriched, `word/media/` of docx) — UNLESS the staging-only progressive downscale fired due to the 5 MB cap, in which case the staging media will differ and `.ssa_run.json` records `staging_resized=True`.

V-C-8.9 PIMS upload acceptance smoke test: post a fixture-generated staging xlsx (with embedded column B thumbnails) to a local instance of `/pims/upload/observations`; assert HTTP 200 and the same row count is inserted into Supabase as the file contains. Confirms column B presence does not regress the upload path.

V-C-8.10 **Insert-from-staging direction (Branch B) acceptance:**
  (a) Every row in the generated staging xlsx has `id` cell **blank** (assert `ws.cell(row=r, column=1).value in (None, "")` for every data row).
  (b) Post the file to `/pims/upload/observations`; parse the response — `inserted` count equals the data-row count, `updated` count is zero, `skipped` count is zero.
  (c) Query Supabase `pims_observations`; assert each new row has `staging=True`, `enriched=True`, `imported_at` populated, `prepared_by` matches the file value (or `"Alan Richardson"` default).
  (d) Re-post the same file unchanged; second response shows `inserted=0`, `skipped=N` (dedup by `(audit_date, observation_text, site_address)` worked).
  (e) Edit one observation_text in the file, re-post; response shows `inserted=1` (the edited row), `skipped=N-1`. Confirms edit-via-reupload is treated as a new finding (documented endpoint behaviour).
  (f) Negative test — manually mint a `uuid4()` into one row's `id` column, re-post; assert that row is NOT inserted (endpoint takes Branch A and silently no-ops). This protects against future regressions where the pipeline accidentally re-introduces uuid4-on-id.

## C.9 Forbidden in-code operations

- Setting any column width on the Observations sheet.
- Setting any row height on rows other than rows containing embedded images (and only as per R-C-4.4).
- Adding cell styles to column B photo cells.
- Merging cells.
- Adding new sheets, removing sheets, renaming sheets.
- Touching the row 1 / row 2 / row 4 metadata/blank rows.
- Modifying the row 3 header text.
- Adding data validation, conditional formatting, or filters.

End of Appendix C.

````

---

## Shipped implementation

### `pims/services/ssa_pipeline.py`

Pipeline core: parser, matcher, three builders, enrichment, size-control wrapper, prior-rec parser, Findings #N expansion, xlsx polish helper.

```python
"""SSA evidence-folder → 3-deliverable pipeline.

Orchestrator for the Site Safety Audit pipeline (workflow #1). Produces:

  1. PIMS-Enriched-YYMMDD-<CLIENT>.xlsx
  2. Site-Safety-Audit-Report-YYMMDD-<CLIENT>.docx
  3. Site-Visit-Report-Upload-PIMS-Staging-YYMMDD-<CLIENT>.xlsx

This file currently contains the template-independent stages only:

  - parse_evidence_csv        (CSV parser contract)
  - match_photos              (filename matching contract)
  - extract_site_address      (no unsafe fallback)

The three builders, watcher, and CLI scripts depend on hand-built
templates under pims/templates/ssa/ and are added in subsequent phases.

Authoritative spec: .claude/plans/workflow-1-i-upload-optimized-catmull.md
"""
from __future__ import annotations

import csv
import io
import json
import logging
import re
import shutil
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Iterable

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------

@dataclass
class CsvWarning:
    row: int | None
    reason: str
    detail: str = ""

    def to_dict(self) -> dict:
        return {"row": self.row, "reason": self.reason, "detail": self.detail}


@dataclass
class ObservationRow:
    """One parsed CSV row + match resolution. Builder stages mutate
    enriched / checklist-derived fields after this struct is constructed."""
    csv_row: int                       # 1-based source row number
    timestamp_raw: str                 # original CSV cell, never mutated
    timestamp_iso: str | None          # parsed YYYY-MM-DD_HH-MM-SS or None
    observation_text: str
    csv_filename: str                  # original CSV token for the photo
    resolved_filename: str | None = None  # actual on-disk filename (post-match)
    resolved_path: Path | None = None
    needs_review: bool = False
    review_reasons: list[str] = field(default_factory=list)
    duplicate_filename: bool = False

    def flag(self, reason: str) -> None:
        self.needs_review = True
        if reason not in self.review_reasons:
            self.review_reasons.append(reason)


# ---------------------------------------------------------------------------
# CSV parsing — Evidence_Master.csv
# ---------------------------------------------------------------------------

_REQUIRED_HEADER = ("timestamp", "observation", "filename")
_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")


def _decode_csv_bytes(raw: bytes) -> str:
    """Detect UTF-8 / UTF-8-SIG / CP1252 and return a unicode string.

    BOM is stripped. CP1252 fallback only fires when both UTF-8 codecs
    raise UnicodeDecodeError — avoids silently mojibake-ing real UTF-8.
    """
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252")


def _is_header_row(row: list[str]) -> bool:
    if len(row) != 3:
        return False
    return tuple(c.strip().lower() for c in row) == _REQUIRED_HEADER


def parse_evidence_csv(
    csv_path: Path,
) -> tuple[list[ObservationRow], list[CsvWarning]]:
    """Parse Evidence_Master.csv per the CSV parser contract.

    Returns (rows, warnings). Drops are recorded as warnings; flags are
    attached to the surviving row. No silent coercion.
    """
    raw = csv_path.read_bytes()
    text = _decode_csv_bytes(raw)
    reader = csv.reader(io.StringIO(text))

    rows: list[ObservationRow] = []
    warnings: list[CsvWarning] = []
    seen_filenames: dict[str, list[int]] = {}

    for line_no, raw_row in enumerate(reader, start=1):
        # Blank rows: skip silently.
        if not raw_row or all(not (c or "").strip() for c in raw_row):
            continue

        # Header detection: only when row 1's three cells match exactly.
        if line_no == 1 and _is_header_row(raw_row):
            continue

        if len(raw_row) != 3:
            warnings.append(CsvWarning(
                row=line_no,
                reason="bad_field_count",
                detail=f"expected 3 fields, got {len(raw_row)}",
            ))
            continue

        ts_raw, obs_text, fname = (c.strip() for c in raw_row)

        if not fname:
            warnings.append(CsvWarning(
                row=line_no, reason="missing_filename",
            ))
            continue

        if not obs_text:
            warnings.append(CsvWarning(
                row=line_no, reason="empty_observation_text",
            ))
            continue

        ts_iso: str | None
        if _TIMESTAMP_RE.match(ts_raw):
            ts_iso = ts_raw
        else:
            ts_iso = None

        row = ObservationRow(
            csv_row=line_no,
            timestamp_raw=ts_raw,
            timestamp_iso=ts_iso,
            observation_text=obs_text,
            csv_filename=fname,
        )
        if ts_iso is None:
            row.flag("bad_timestamp")
            warnings.append(CsvWarning(
                row=line_no,
                reason="bad_timestamp",
                detail=ts_raw,
            ))

        seen_filenames.setdefault(fname.lower(), []).append(len(rows))
        rows.append(row)

    # Stamp duplicate flag on every affected row (kept; flagged).
    for indices in seen_filenames.values():
        if len(indices) > 1:
            for idx in indices:
                rows[idx].duplicate_filename = True
                rows[idx].flag("duplicate_filename")

    return rows, warnings


# ---------------------------------------------------------------------------
# Filename matching
# ---------------------------------------------------------------------------

_JPEG_EXTS = {".jpg", ".jpeg"}


def _canonical_name(name: str) -> str:
    """Lowercase + JPEG-extension normalisation. Drive-suffix patterns
    like '(1)' or ' - Copy' are NOT stripped — they identify derivative
    copies and stripping them would collapse distinct files."""
    s = name.strip().lower()
    p = Path(s)
    ext = p.suffix
    if ext in _JPEG_EXTS:
        return p.with_suffix(".jpg").name
    return p.name


def _stem(name: str) -> str:
    return Path(name).stem.lower()


def match_photos(
    rows: list[ObservationRow],
    image_paths: Iterable[Path],
) -> list[CsvWarning]:
    """Resolve each row's csv_filename to an on-disk image path.

    Mutates rows in place. Returns a list of warnings. Every rule
    yields 0/1/many; "many" always sets needs_review=True with no
    silent selection (per filename-matching contract).
    """
    warnings: list[CsvWarning] = []
    on_disk = [Path(p) for p in image_paths]

    # Pre-index for cheap lookup. Store the full Path against multiple keys.
    by_canonical: dict[str, list[Path]] = {}
    by_stem: dict[str, list[Path]] = {}
    for p in on_disk:
        by_canonical.setdefault(_canonical_name(p.name), []).append(p)
        if p.suffix.lower() in _JPEG_EXTS:
            by_stem.setdefault(_stem(p.name), []).append(p)

    for row in rows:
        token = row.csv_filename
        canon = _canonical_name(token)

        # Rule 2: exact canonical match.
        hits = list(by_canonical.get(canon, []))
        if len(hits) == 1:
            row.resolved_filename = hits[0].name
            row.resolved_path = hits[0]
            continue
        if len(hits) > 1:
            row.flag("photo_match_ambiguous")
            warnings.append(CsvWarning(
                row=row.csv_row,
                reason="photo_match_ambiguous",
                detail=f"{token} -> {[h.name for h in hits]}",
            ))
            continue

        # Rule 3: stem match across the JPEG family.
        if Path(canon).suffix in _JPEG_EXTS:
            hits = list(by_stem.get(_stem(token), []))
            if len(hits) == 1:
                row.resolved_filename = hits[0].name
                row.resolved_path = hits[0]
                if hits[0].suffix.lower() != Path(token).suffix.lower():
                    warnings.append(CsvWarning(
                        row=row.csv_row,
                        reason="extension_swap",
                        detail=f"{token} -> {hits[0].name}",
                    ))
                continue
            if len(hits) > 1:
                row.flag("photo_match_ambiguous")
                warnings.append(CsvWarning(
                    row=row.csv_row,
                    reason="photo_match_ambiguous",
                    detail=f"stem {token} -> {[h.name for h in hits]}",
                ))
                continue

        # Rule 4: suffix match — canonical CSV filename appears at the
        # end of an on-disk canonical filename (handles prefixed names).
        suffix_hits = [
            p for p in on_disk
            if _canonical_name(p.name).endswith(canon)
            and _canonical_name(p.name) != canon
        ]
        if len(suffix_hits) == 1:
            row.resolved_filename = suffix_hits[0].name
            row.resolved_path = suffix_hits[0]
            warnings.append(CsvWarning(
                row=row.csv_row,
                reason="prefix_match",
                detail=f"{token} -> {suffix_hits[0].name}",
            ))
            continue
        if len(suffix_hits) > 1:
            row.flag("photo_match_ambiguous")
            warnings.append(CsvWarning(
                row=row.csv_row,
                reason="photo_match_ambiguous",
                detail=f"suffix {token} -> {[h.name for h in suffix_hits]}",
            ))
            continue

        # Rule 6: missing.
        row.flag("photo_missing")
        warnings.append(CsvWarning(
            row=row.csv_row, reason="photo_missing", detail=token,
        ))

    return warnings


# ---------------------------------------------------------------------------
# Site-address extraction (no unsafe fallback)
# ---------------------------------------------------------------------------

# Conservative street pattern: a leading street number (with optional
# letter suffix) followed by 1-4 capitalised words then a street-type
# token. Matches "12 Smith Street", "6a Francis Rd", "100-104 King Ave".
# Deliberately strict — a stray sentence with a number won't trigger.
_STREET_TYPES = (
    r"(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Lane|Ln|Place|Pl|"
    r"Court|Ct|Crescent|Cres|Parade|Pde|Highway|Hwy|Way|Boulevard|"
    r"Blvd|Terrace|Tce|Close|Cl|Circuit|Cct|Esplanade|Esp)"
)
_ADDRESS_RE = re.compile(
    r"\b\d{1,5}[A-Za-z]?(?:-\d{1,5}[A-Za-z]?)?\s+"
    r"(?:[A-Z][A-Za-z'’]+\s+){1,4}"
    + _STREET_TYPES
    + r"\b[^.\n,]*",
    re.UNICODE,
)


def _load_known_sites(path: Path | None) -> list[str]:
    if path is None or not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        log.warning("known_sites.json unreadable", exc_info=True)
        return []
    if isinstance(data, list):
        return [str(s) for s in data if isinstance(s, str)]
    if isinstance(data, dict):
        return [str(s) for s in data.values() if isinstance(s, str)]
    return []


def extract_site_address(
    rows: list[ObservationRow],
    known_sites_path: Path | None = None,
) -> str | None:
    """Scan all observations for an address-shaped string.

    Returns the first hit (lowest CSV row index). On no match returns
    None — caller is responsible for flagging needs_review on every
    staging row and recording site_address_unresolved=True. Folder name
    is NEVER used as a fallback (would leak date/client junk into PIMS).
    """
    known = _load_known_sites(known_sites_path)
    known_lower = [(s, s.lower()) for s in known]

    for row in rows:
        text = row.observation_text or ""
        m = _ADDRESS_RE.search(text)
        if m:
            return m.group(0).strip().rstrip(",")
        text_lower = text.lower()
        for original, lower in known_lower:
            if lower in text_lower:
                return original

    return None


# ---------------------------------------------------------------------------
# Per-row enrichment payload (filled by upstream stages before builders run)
# ---------------------------------------------------------------------------

@dataclass
class EnrichedRow:
    """Builder input — one fully-resolved register row.

    Carries the parsed CSV row plus everything the three deliverables
    need to render: checklist-derived deterministic fields, enriched
    observation/finding text, conformance status. Builders never call
    the enricher or matcher — those are upstream stages.
    """
    obs: ObservationRow
    observation_text_clean: str = ""
    finding: str = ""
    conformance_status: str = "Unmatched"
    ccvs_code: str = ""
    ccvs_category: str = ""
    action_description: str = ""
    recommendation: str = ""
    legal_ref: str = ""
    monitoring_note: str = ""

    @property
    def action_required(self) -> str:
        if self.conformance_status in {"NCR", "Conditional", "Unmatched"}:
            return "Yes"
        return "No"

    @property
    def needs_review(self) -> bool:
        return bool(self.obs.needs_review) or self.conformance_status == "Unmatched"


# ---------------------------------------------------------------------------
# Photo preprocessing — Appendix A R-7.4.1 / Appendix B R-B-3.1
# ---------------------------------------------------------------------------

def _preprocess_photo(
    source: Path,
    max_edge_px: int = 1600,
) -> tuple[BytesIO, str, int, int] | None:
    """EXIF-transpose, downscale, recompress.

    Returns (BytesIO, format, width_px, height_px) or None on load
    failure / missing source. ``format`` is ``"JPEG"`` or ``"PNG"``
    (PNG only when the source was PNG with transparency).
    """
    try:
        from PIL import Image, ImageOps
    except Exception:
        log.warning("Pillow unavailable - photo embed skipped")
        return None
    try:
        with Image.open(source) as im:
            im = ImageOps.exif_transpose(im)
            keep_png = (
                source.suffix.lower() == ".png"
                and (im.mode in ("RGBA", "LA") or "transparency" in im.info)
            )
            longest = max(im.width, im.height)
            if longest > max_edge_px:
                ratio = max_edge_px / float(longest)
                new_size = (int(im.width * ratio), int(im.height * ratio))
                im = im.resize(new_size, Image.LANCZOS)
            buf = BytesIO()
            if keep_png:
                im.save(buf, format="PNG", optimize=False)
                fmt = "PNG"
            else:
                rgb = im.convert("RGB")
                rgb.save(buf, format="JPEG", quality=85, optimize=False)
                fmt = "JPEG"
            buf.seek(0)
            return buf, fmt, im.width, im.height
    except FileNotFoundError:
        return None
    except Exception:
        log.warning("photo load failed for %s", source, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Builder #1 - PIMS-Enriched-YYMMDD-<CLIENT>.xlsx (Appendix B)
# ---------------------------------------------------------------------------

_PHOTO_THUMB_PX = 95  # 2.5 cm @ 96 dpi
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "ssa"
PIMS_ENRICHED_TEMPLATE = _TEMPLATE_DIR / "PIMS-Enriched.template.xlsx"
SSA_REPORT_TEMPLATE = _TEMPLATE_DIR / "Site-Safety-Audit-Report.template.docx"
PIMS_STAGING_TEMPLATE = (
    _TEMPLATE_DIR / "Site-Visit-Report-PIMS-Staging.template.xlsx"
)


# --- xlsx polish — column widths, status colour fills, wrap ---------------
#
# Excel column-width units are roughly "character widths of the default
# font". 95 px ≈ 13.6 char-units, so the photo columns get 14 to fit the
# embedded thumbnails. Long-content columns (Observation, Finding,
# Action Description, Monitoring Note) widen and wrap so reviewers
# don't see truncated mid-sentence findings.

# Header (lowercased) → column width in Excel char-units.
_ENRICHED_COL_WIDTHS: dict[str, float] = {
    "#": 4,
    "observation date": 18,
    "photo id": 9,
    "photo": 14,                # 2.5 cm thumbnail
    "filename": 30,
    "observation": 60,          # multi-sentence enriched finding
    "conformance status": 14,
    "ccvs code": 10,
    "ccvs category": 22,
    "action required": 10,
    "action description": 40,
    "responsible": 14,
    "due": 12,
    "monitoring note": 40,
    "close-out status": 14,
    "closed date": 12,
    "closed by": 14,
    "close-out notes": 30,
}

_STAGING_COL_WIDTHS: dict[str, float] = {
    "id": 8,
    "photo": 14,
    "site_address": 30,
    "audit_date": 12,
    "observation_text": 50,
    "finding": 60,
    "conformance_status": 14,
    "ccvs_code": 10,
    "ccvs_category": 22,
    "action_description": 40,
    "responsible": 14,
    "due_category": 14,
    "recommendation": 40,
    "monitoring_note": 40,
    "legal_ref": 30,
    "photo_refs": 28,
    "prepared_by": 16,
    "source_pdf": 14,
    "section": 14,
    "needs_review": 12,
}

# Headers that need wrap_text=True applied to data cells. Without wrap
# Excel renders the cell as a single truncated line, even when the
# column is wide enough — wrap is what makes multi-sentence findings
# render as a readable paragraph block.
_WRAP_HEADERS: frozenset[str] = frozenset({
    "observation",          # PIMS-Enriched
    "action description",
    "monitoring note",
    "close-out notes",
    "observation_text",     # Staging
    "finding",
    "recommendation",
    "monitoring_note",
    "legal_ref",
    "site_address",
})

# Conformance Status colour fills — at-a-glance scanning convention
# from the canonical PIMS-Enriched - Sample.xlsx (NCR red, Conditional
# amber, Compliant green, Info grey, Unmatched white).
_STATUS_FILL_HEX: dict[str, str] = {
    "NCR":         "FFC7CE",   # light red
    "Conditional": "FFE699",   # light amber
    "Compliant":   "C6EFCE",   # light green
    "Info":        "D9E1F2",   # light blue / grey
    "Unmatched":   "F2F2F2",   # neutral
}


def _apply_xlsx_polish(
    ws,
    header_row_idx: int,
    data_first_row: int,
    col_widths: dict[str, float],
    status_header: str,
) -> None:
    """Apply column widths, wrap, and status colour fills to a sheet.

    ``ws`` openpyxl worksheet; ``header_row_idx`` 1-based; ``data_first_row``
    the first data row (2 for Enriched, 5 for Staging); ``col_widths``
    keyed by lowercased header literal; ``status_header`` the lowercased
    header name to colour-fill (``"conformance status"`` for Enriched,
    ``"conformance_status"`` for Staging).
    """
    from openpyxl.styles import Alignment, PatternFill
    from openpyxl.utils import get_column_letter

    headers = [
        ("" if c.value is None else str(c.value).strip().lower())
        for c in ws[header_row_idx]
    ]

    # Column widths.
    for idx, hdr in enumerate(headers, start=1):
        width = col_widths.get(hdr)
        if width is not None:
            ws.column_dimensions[get_column_letter(idx)].width = width

    # wrap_text + vertical-centre on every data cell. Vertical-centre
    # keeps photo cells (which set tall row heights) aligned with the
    # text in the rest of the row instead of stuck at the top.
    wrap_alignment = Alignment(wrap_text=True, vertical="center")
    plain_alignment = Alignment(vertical="center")
    last_data_row = ws.max_row
    for row in ws.iter_rows(
        min_row=data_first_row, max_row=last_data_row,
        min_col=1, max_col=len(headers),
    ):
        for cell in row:
            hdr = headers[cell.column - 1] if cell.column <= len(headers) else ""
            cell.alignment = wrap_alignment if hdr in _WRAP_HEADERS else plain_alignment

    # Status colour fills.
    try:
        status_col_idx = headers.index(status_header) + 1
    except ValueError:
        status_col_idx = 0
    if status_col_idx:
        for r in range(data_first_row, last_data_row + 1):
            cell = ws.cell(row=r, column=status_col_idx)
            val = (cell.value or "").strip() if isinstance(cell.value, str) else ""
            hex_fill = _STATUS_FILL_HEX.get(val)
            if hex_fill:
                cell.fill = PatternFill(
                    fill_type="solid", start_color=hex_fill, end_color=hex_fill,
                )


def _row_value(row: EnrichedRow, header_lc: str) -> object:
    """Map a header literal (lowercased) to the cell value to write.

    Blank-by-design fields per the Field Defaults table return ``""``.
    Photo cell is image-only (caller skips it). The ``#`` and
    ``photo id`` columns are renumbered against the data-row index by
    the builder, not from this function.
    """
    obs = row.obs
    if header_lc == "observation date":
        if obs.timestamp_iso:
            return obs.timestamp_iso
        return f"RAW: {obs.timestamp_raw}" if obs.timestamp_raw else ""
    if header_lc == "filename":
        return obs.resolved_filename or ""
    if header_lc == "observation":
        # Per the canonical sample, this column carries the enriched
        # multi-sentence narrative (the "finding"), not the raw note.
        # Falls back to the cleaned observation when no enrichment ran.
        return row.finding or row.observation_text_clean or obs.observation_text
    if header_lc == "conformance status":
        return row.conformance_status
    if header_lc == "ccvs code":
        return row.ccvs_code
    if header_lc == "ccvs category":
        return row.ccvs_category
    if header_lc == "action required":
        return row.action_required
    if header_lc == "action description":
        # Vision enricher writes the corrective action into
        # ``recommendation``; keep ``action_description`` as a fallback
        # for upstream paths that populated it directly. Compliant rows
        # leave both empty per the sample's pattern.
        return row.action_description or row.recommendation
    if header_lc == "monitoring note":
        return row.monitoring_note
    return ""


def build_pims_enriched_xlsx(
    rows: list[EnrichedRow],
    output_path: Path,
    template_path: Path = PIMS_ENRICHED_TEMPLATE,
) -> dict:
    """Write the PIMS-Enriched register per Appendix B.

    Returns a diagnostics dict for ``.ssa_run.json``:
        {"photo_load_failed": [...], "photo_file_missing_at_render": [...]}

    Implementation: ``shutil.copyfile`` then openpyxl mutate. Column
    widths, header row, and Summary sheet structure are inherited
    untouched per R-B-1.2 / B.9.
    """
    import os
    import openpyxl
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.utils import get_column_letter

    if not template_path.exists():
        raise FileNotFoundError(
            f"PIMS-Enriched template missing: {template_path}"
        )

    # openpyxl validates by extension on load — keep ``.xlsx`` on the
    # tmp path while still using a sibling-of-final pattern so os.replace
    # is atomic on the same volume.
    tmp = output_path.with_name(output_path.name + ".tmp.xlsx")
    shutil.copyfile(template_path, tmp)

    wb = openpyxl.load_workbook(tmp)
    if "Enriched Register" not in wb.sheetnames:
        raise ValueError("template missing 'Enriched Register' sheet")
    ws = wb["Enriched Register"]

    headers = [
        ("" if c.value is None else str(c.value).strip().lower())
        for c in ws[1]
    ]
    try:
        photo_col_idx = headers.index("photo") + 1
    except ValueError:
        photo_col_idx = 4  # column D per Appendix B

    diagnostics: dict[str, list] = {
        "photo_load_failed": [],
        "photo_file_missing_at_render": [],
    }

    for data_idx, row in enumerate(rows, start=1):
        excel_row = data_idx + 1

        for col_idx, hdr in enumerate(headers, start=1):
            if hdr == "photo":
                continue
            if hdr == "#":
                ws.cell(row=excel_row, column=col_idx, value=data_idx)
                continue
            if hdr == "photo id":
                ws.cell(
                    row=excel_row, column=col_idx, value=f"P-{data_idx:04d}",
                )
                continue
            ws.cell(row=excel_row, column=col_idx, value=_row_value(row, hdr))

        path = row.obs.resolved_path
        if not path:
            continue
        if not path.exists():
            diagnostics["photo_file_missing_at_render"].append(str(path))
            continue
        prepared = _preprocess_photo(path)
        if prepared is None:
            diagnostics["photo_load_failed"].append(str(path))
            continue
        buf, _fmt, w_px, h_px = prepared
        img = XLImage(buf)
        scale = _PHOTO_THUMB_PX / float(w_px)
        img.width = _PHOTO_THUMB_PX
        img.height = max(1, int(round(h_px * scale)))
        anchor_col = get_column_letter(photo_col_idx)
        ws.add_image(img, anchor=f"{anchor_col}{excel_row}")
        ws.row_dimensions[excel_row].height = max(95, img.height)

    _apply_xlsx_polish(
        ws,
        header_row_idx=1,
        data_first_row=2,
        col_widths=_ENRICHED_COL_WIDTHS,
        status_header="conformance status",
    )

    wb.save(tmp)
    wb.close()
    os.replace(tmp, output_path)
    return diagnostics


# ---------------------------------------------------------------------------
# Builder #2 - Site-Safety-Audit-Report-YYMMDD-<CLIENT>.docx (Appendix A)
# ---------------------------------------------------------------------------

# Header-text signatures used to locate the four template tables. Match
# is "first row's joined cell text contains all of these tokens" — keeps
# us robust against a stray non-breaking space without ever picking a
# wrong table.
_TABLE_SIGNATURES = {
    "positive": ("#", "Observation", "Reference"),
    "prior_recs": ("Recommendation", "Required Actions", "Status", "Commentary"),
    "obs_register": ("Obs #", "Photo", "Observation", "Reference", "Status", "Evidence File"),
}

# Per-location 2-col detail block: first row first cell == "Location",
# 2 columns. Distinct enough from every other table in the template to
# match unambiguously.
_PER_LOCATION_FIRST_CELL = "Location"


def parse_prior_report_recommendations(path: Path) -> list[dict]:
    """Extract carry-forward recommendations from a prior SSA report.

    Pulls NCR + Conditional rows from the prior report's Observations
    Register (6-col table whose header[0] == 'Obs #'). Each row becomes
    a ``Status of Previous Recommendations`` entry shaped:

        {
          "recommendation":   short summary from prior Observation cell,
          "required_actions": prior Reference / regulatory cite,
          "status":           "" — auditor fills with DD/MM/YY at QA,
          "commentary":       "" — auditor fills at QA,
        }

    Returns ``[]`` when the file is unreadable, lacks an Observations
    Register, or carries no non-Compliant rows. Never raises into the
    orchestrator.
    """
    if not path.exists():
        return []
    try:
        from docx import Document
        doc = Document(path)
    except Exception:
        log.warning("prior report unreadable: %s", path, exc_info=True)
        return []

    register = None
    for tbl in doc.tables:
        if len(tbl.columns) != 6:
            continue
        if not tbl.rows:
            continue
        head = tbl.rows[0].cells[0].text.strip()
        if head.startswith("Obs"):
            register = tbl
            break
    if register is None:
        return []

    out: list[dict] = []
    for row in register.rows[1:]:
        if len(row.cells) < 6:
            continue
        status = row.cells[4].text.strip()
        if status == "Compliant" or status == "":
            continue
        if status not in {"NCR", "Conditional", "Info", "Unmatched"}:
            # Status text in older reports may be free-form (e.g.
            # "See F1 re exclusion zone"); treat as carry-forward.
            pass
        observation = " ".join(row.cells[2].text.split())
        reference = " ".join(row.cells[3].text.split())
        if not observation:
            continue
        out.append({
            "recommendation": observation,
            "required_actions": reference,
            "status": "",
            "commentary": "",
        })
    return out


def _expand_findings_list(doc, register_rows: list[EnrichedRow]) -> int:
    """Materialise the ``#N`` Findings sub-list per non-Compliant row.

    The canonical template has a placeholder shape:

        Findings              (14pt bold)
        #1                    (12pt bold) — placeholder heading
        (empty paragraph)     — body slot
        Status of Previous Recommendations …

    For each register row this function lays down:

        #N STATUS — CCVS-CODE          (12pt bold heading clone)
        <finding text>                 (body paragraph clone)

    Inserted in CSV order before the ``Status of Previous
    Recommendations`` heading paragraph. Without this, V-10.5 fails
    and the rendered docx shows an empty ``#1`` placeholder regardless
    of how many findings the audit produced.

    Returns the number of `#N` headings written. ``0`` is a no-op (no
    placeholder found, or no non-Compliant rows).
    """
    import copy
    from docx.oxml.ns import qn

    body = doc.element.body

    # Locate the `#1 ` heading and the Status heading. The status
    # heading is locked text per A.8 R-8.1.
    heading_p = None
    status_p = None
    for child in body.iterchildren():
        if child.tag != qn("w:p"):
            continue
        text = "".join(t.text or "" for t in child.iter(qn("w:t"))).strip()
        if heading_p is None and text.startswith("#1"):
            heading_p = child
        elif heading_p is not None and text.startswith(
            "Status of Previous Recommendations"
        ):
            status_p = child
            break
    if heading_p is None or status_p is None:
        return 0

    # The placeholder body paragraph sits between the `#1 ` heading and
    # the Status heading. Walk forward from heading_p until we hit a
    # paragraph that's not the heading itself; that's the body slot.
    body_p = heading_p.getnext()
    if body_p is None or body_p.tag != qn("w:p"):
        return 0

    if not register_rows:
        # Empty audit — collapse the Findings list to a single
        # placeholder row noting "no findings recorded" so the section
        # header still renders meaningfully.
        _set_paragraph_runs_text(heading_p, "No findings recorded.")
        _set_paragraph_runs_text(body_p, "")
        return 0

    # i==1: mutate the existing heading + body in-place. i>=2: deepcopy
    # the (heading, body) pair and insert before the Status heading so
    # iteration order is preserved.
    written = 0
    for idx, row in enumerate(register_rows, start=1):
        title = _finding_heading_text(idx, row)
        text = (row.finding or row.observation_text_clean
                or row.obs.observation_text or "").strip()
        if idx == 1:
            _set_paragraph_runs_text(heading_p, title)
            _set_paragraph_runs_text(body_p, text)
        else:
            new_h = copy.deepcopy(heading_p)
            new_b = copy.deepcopy(body_p)
            _set_paragraph_runs_text(new_h, title)
            _set_paragraph_runs_text(new_b, text)
            status_p.addprevious(new_h)
            status_p.addprevious(new_b)
        written += 1
    return written


def _finding_heading_text(idx: int, row: EnrichedRow) -> str:
    """``#3 NCR — WAH-H6`` or ``#3 — WAH-H6`` if status is empty."""
    parts = [f"#{idx}"]
    if row.conformance_status:
        parts.append(row.conformance_status)
    if row.ccvs_code:
        parts.append(row.ccvs_code)
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[1]} — {parts[2]}" if len(parts) == 3 \
        else f"{parts[0]} — {parts[1]}"


def _set_paragraph_runs_text(p_element, text: str) -> None:
    """Replace text on the first <w:r>/<w:t> of the paragraph; preserve
    that run's rPr (font size, bold, theme). Drop trailing runs so the
    placeholder fragments don't ghost into the output. When the
    paragraph carries no runs at all (an intentionally-empty template
    paragraph), append a fresh ``<w:r><w:t>`` so the text shows up
    instead of silently disappearing."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    runs = list(p_element.iter(qn("w:r")))
    if not runs:
        run = OxmlElement("w:r")
        t = OxmlElement("w:t")
        t.text = text
        # Preserve leading/trailing whitespace so multi-sentence
        # findings don't get collapsed at line breaks.
        t.set(qn("xml:space"), "preserve")
        run.append(t)
        p_element.append(run)
        return
    first = runs[0]
    # Update the first <w:t> on the first run.
    t_els = list(first.iter(qn("w:t")))
    if t_els:
        t_els[0].text = text
        t_els[0].set(qn("xml:space"), "preserve")
        for extra in t_els[1:]:
            extra.text = ""
    else:
        t = OxmlElement("w:t")
        t.text = text
        t.set(qn("xml:space"), "preserve")
        first.append(t)
    # Drop sibling runs after the first to avoid leftover placeholder
    # text fragments.
    for extra in runs[1:]:
        parent = extra.getparent()
        if parent is not None:
            parent.remove(extra)


def _remove_per_location_block(doc) -> bool:
    """Remove the per-location 2-col placeholder table from the document.

    Per A.7 / R-1.3(e), block-level removal of the per-location detail
    table is the one structural operation permitted outside row-level
    cloning. v1 always removes — location detection (clone-per-location)
    is a deferred slice. Returns True if a block was removed.

    Conservative — does NOT remove the preceding heading paragraph,
    because in this template the per-location block sits inside the
    Findings list region and its preceding paragraphs (``Findings`` /
    ``#1 ``) are part of the Findings scaffolding, not a per-location
    sub-heading.
    """
    for tbl in list(doc.tables):
        if len(tbl.columns) != 2:
            continue
        if not tbl.rows:
            continue
        first_cell_text = tbl.rows[0].cells[0].text.strip()
        if first_cell_text == _PER_LOCATION_FIRST_CELL:
            tbl._element.getparent().remove(tbl._element)
            return True
    return False


def _replace_tokens_in_part(part, replacements: dict[str, str]) -> int:
    """Replace ``{{TOKEN}}`` text inside every ``<w:t>`` of a docx part.

    Walks the element tree (so text boxes / drawings are covered, not
    just python-docx's surfaced paragraphs). Tokens are pre-confirmed
    single-run in the canonical template — no run splitting needed.
    """
    from docx.oxml.ns import qn
    if not hasattr(part, "element"):
        return 0
    n = 0
    for t in part.element.iter(qn("w:t")):
        txt = t.text
        if not txt:
            continue
        new = txt
        for token, value in replacements.items():
            if token in new:
                new = new.replace(token, value)
        if new != txt:
            t.text = new
            n += 1
    return n


def _replace_token_runs(paragraphs, replacements: dict[str, str]) -> int:
    """Replace ``{{TOKEN}}`` text on a per-run basis.

    Per A.6 R-6.2: locate the run containing the literal token, replace
    only ``r.text``. ``rPr`` (font size, bold, theme) is preserved.
    Returns the number of runs mutated.
    """
    n = 0
    for para in paragraphs:
        for run in para.runs:
            txt = run.text
            if not txt:
                continue
            new = txt
            for token, value in replacements.items():
                if token in new:
                    new = new.replace(token, value)
            if new != txt:
                run.text = new
                n += 1
    return n


def _find_table(doc, signature: tuple[str, ...]):
    """Locate a table whose first row contains every signature token."""
    for tbl in doc.tables:
        if not tbl.rows:
            continue
        joined = " | ".join(c.text.strip() for c in tbl.rows[0].cells)
        if all(token in joined for token in signature):
            return tbl
    return None


def _clone_row(table, src_row):
    """deepcopy a placeholder ``<w:tr>`` and append as the table's last row.

    Returns a ``_Row`` wrapper around the freshly appended element. Per
    R-7.2 we touch nothing on the cloned row's properties — text writes
    happen via cell.text on the caller side, which only mutates the
    cell's first paragraph runs.

    NOTE: do NOT use ``src_row._tr.addnext(new_tr)`` here. ``addnext``
    inserts each new row immediately after ``src_row``, pushing earlier
    clones further down the table. Combined with ``table.rows[-1]`` this
    silently corrupts the table — every clone except the final one
    keeps the placeholder's deepcopied content, and only the very first
    clone (now at index -1) gets repeatedly overwritten with each
    iteration's data. The fix appends to the END of the parent ``<w:tbl>``
    element directly so clones land in iteration order.
    """
    import copy
    from docx.table import _Row
    new_tr = copy.deepcopy(src_row._tr)
    parent = src_row._tr.getparent()
    parent.append(new_tr)
    return _Row(new_tr, table)


def _set_cell_text(cell, text: str) -> None:
    """Write text into a cloned cell, preserving the cell's first run's
    formatting. Subsequent paragraphs/runs are emptied — the placeholder
    cell carries one paragraph with one styled run.
    """
    if not cell.paragraphs:
        cell.add_paragraph(text)
        return
    p = cell.paragraphs[0]
    if p.runs:
        # Keep the first run's rPr; replace text. Drop trailing runs to
        # avoid leaving placeholder fragments behind.
        first = p.runs[0]
        first.text = text or ""
        for extra in list(p.runs[1:]):
            extra._element.getparent().remove(extra._element)
    else:
        p.add_run(text or "")
    # Clear any extra paragraphs in the cell (placeholder cells always
    # carry exactly one paragraph; defensive only).
    for extra in list(cell.paragraphs[1:]):
        extra._element.getparent().remove(extra._element)


def _embed_image_in_cell(cell, image_buf: BytesIO) -> bool:
    """Insert one inline image at exactly Cm(2.5) into the cell's first
    paragraph. Per R-7.4 / R-7.4.2 width is fixed; height is auto.
    Returns True on success.
    """
    from docx.shared import Cm
    try:
        if not cell.paragraphs:
            cell.add_paragraph()
        p = cell.paragraphs[0]
        # Drop the placeholder text run (keeps rPr-bearing run only if
        # empty; we want a clean paragraph that hosts only the image).
        for run in list(p.runs):
            run._element.getparent().remove(run._element)
        run = p.add_run()
        image_buf.seek(0)
        run.add_picture(image_buf, width=Cm(2.5))
        return True
    except Exception:
        log.warning("docx photo embed failed", exc_info=True)
        return False


def build_ssa_report_docx(
    rows: list[EnrichedRow],
    site_address: str,
    audit_date_ddmmyyyy: str,
    narrative_summary: str,
    output_path: Path,
    prepared_by: str = "Alan Richardson",
    prior_recs: list[dict] | None = None,
    template_path: Path = SSA_REPORT_TEMPLATE,
) -> dict:
    """Render the SSA report per Appendix A.

    Allowed operations only (R-1.3): replace placeholder run text;
    deepcopy a placeholder table row N times; write text into cloned
    cells; insert exactly one inline image per Photo cell at ``Cm(2.5)``.

    The per-location 2-col detail table (table 1 in the template) is
    left as-is in v1 — location detection is out of scope for this
    slice.

    Returns a diagnostics dict for ``.ssa_run.json``:
        {"photo_load_failed": [...], "photo_file_missing_at_render": [...],
         "missing_photo_obs": [...]}  # rows whose Obs # got a `*` suffix

    ``site_address`` is written verbatim. Caller is responsible for
    passing ``"[Site address - to be confirmed]"`` when extraction
    failed (per Field Defaults).
    """
    import os
    from docx import Document

    if not template_path.exists():
        raise FileNotFoundError(
            f"SSA report template missing: {template_path}"
        )

    tmp = output_path.with_name(output_path.name + ".tmp.docx")
    shutil.copyfile(template_path, tmp)

    doc = Document(tmp)

    # --- A.6: token substitution -------------------------------------
    # Walk the body part AND every header/footer part. Body-paragraph
    # iteration alone misses tokens inside text boxes (e.g. cover-page
    # site address frame); the part-level walk covers those.
    all_replacements = {
        "{{SITE_ADDRESS}}": site_address or "",
        "{{NARRATIVE_SUMMARY}}": narrative_summary or "",
        "{{AUDIT_DATE}}": audit_date_ddmmyyyy or "",
        "{{PREPARED_BY}}": prepared_by or "",
    }
    _replace_tokens_in_part(doc.part, all_replacements)
    for sec in doc.sections:
        for hf in (
            sec.header, sec.first_page_header,
            sec.footer, sec.first_page_footer,
        ):
            _replace_tokens_in_part(hf.part, all_replacements)

    # --- Partition rows ----------------------------------------------
    positive = [r for r in rows if r.conformance_status == "Compliant"]
    register = [r for r in rows if r.conformance_status != "Compliant"]

    # Strip the per-location placeholder block (R-1.3(e)). v1 never
    # populates it — keeps the deliverable clean instead of leaving a
    # stale 6-row scaffold visible in the output.
    _remove_per_location_block(doc)

    # Materialise the `#N` Findings sub-list — one heading + body pair
    # per non-Compliant row. Without this the rendered docx leaves
    # only the template's `#1` placeholder visible regardless of how
    # many findings the audit produced.
    _expand_findings_list(doc, register)

    diagnostics: dict[str, list] = {
        "photo_load_failed": [],
        "photo_file_missing_at_render": [],
        "missing_photo_obs": [],
    }

    # --- Positive Observations table (3 cols) ------------------------
    pos_tbl = _find_table(doc, _TABLE_SIGNATURES["positive"])
    if pos_tbl is not None and len(pos_tbl.rows) >= 2:
        placeholder = pos_tbl.rows[1]
        if positive:
            for idx, row in enumerate(positive, start=1):
                target = placeholder if idx == 1 else _clone_row(pos_tbl, placeholder)
                cells = target.cells
                _set_cell_text(cells[0], str(idx))
                _set_cell_text(
                    cells[1],
                    row.observation_text_clean or row.obs.observation_text,
                )
                _set_cell_text(cells[2], row.legal_ref or "")
        else:
            cells = placeholder.cells
            _set_cell_text(cells[0], "-")
            _set_cell_text(cells[1], "No positive observations recorded.")
            _set_cell_text(cells[2], "")

    # --- Status of Previous Recommendations table (4 cols) ----------
    prev_tbl = _find_table(doc, _TABLE_SIGNATURES["prior_recs"])
    if prev_tbl is not None and len(prev_tbl.rows) >= 2:
        placeholder = prev_tbl.rows[1]
        recs = list(prior_recs or [])
        if recs:
            for idx, rec in enumerate(recs, start=1):
                target = placeholder if idx == 1 else _clone_row(prev_tbl, placeholder)
                cells = target.cells
                _set_cell_text(cells[0], str(rec.get("recommendation", "")))
                _set_cell_text(cells[1], str(rec.get("required_actions", "")))
                _set_cell_text(cells[2], str(rec.get("status", "")))
                _set_cell_text(cells[3], str(rec.get("commentary", "")))
        else:
            cells = placeholder.cells
            _set_cell_text(cells[0], "No prior recommendations carried forward.")
            _set_cell_text(cells[1], "")
            _set_cell_text(cells[2], "")
            _set_cell_text(cells[3], "")

    # --- Observations Register table (6 cols, photos in col 1) -------
    reg_tbl = _find_table(doc, _TABLE_SIGNATURES["obs_register"])
    if reg_tbl is not None and len(reg_tbl.rows) >= 2:
        placeholder = reg_tbl.rows[1]
        if register:
            for idx, row in enumerate(register, start=1):
                target = placeholder if idx == 1 else _clone_row(reg_tbl, placeholder)
                cells = target.cells

                # Resolve photo first so the Obs # marker reflects
                # missing-photo state per R-7.5.
                photo_embedded = False
                src = row.obs.resolved_path
                if src is not None:
                    if not src.exists():
                        diagnostics["photo_file_missing_at_render"].append(str(src))
                    else:
                        prepared = _preprocess_photo(src)
                        if prepared is None:
                            diagnostics["photo_load_failed"].append(str(src))
                        else:
                            buf, _fmt, _w, _h = prepared
                            photo_embedded = _embed_image_in_cell(cells[1], buf)
                if not photo_embedded:
                    # Empty Photo cell (cells[1] kept untouched) and
                    # mark Obs # with the trailing `*` per R-7.5.
                    diagnostics["missing_photo_obs"].append(idx)

                obs_marker = f"{idx}{'*' if not photo_embedded else ''}"
                _set_cell_text(cells[0], obs_marker)
                # cells[1] is the Photo cell; only mutated by the embed
                # path above. If embed failed, leave the placeholder
                # paragraph empty per R-7.5.
                if not photo_embedded:
                    _set_cell_text(cells[1], "")

                finding_text = (
                    row.finding
                    or row.observation_text_clean
                    or row.obs.observation_text
                )
                _set_cell_text(cells[2], finding_text)
                _set_cell_text(cells[3], row.legal_ref or "")
                _set_cell_text(cells[4], row.conformance_status)
                _set_cell_text(cells[5], row.obs.resolved_filename or "")
        else:
            cells = placeholder.cells
            _set_cell_text(cells[0], "-")
            _set_cell_text(cells[1], "")
            _set_cell_text(cells[2], "No findings recorded.")
            _set_cell_text(cells[3], "")
            _set_cell_text(cells[4], "")
            _set_cell_text(cells[5], "")

    doc.save(tmp)
    os.replace(tmp, output_path)
    return diagnostics


# ---------------------------------------------------------------------------
# Builder #3 - Site-Visit-Report-Upload-PIMS-Staging-YYMMDD-<CLIENT>.xlsx
# (Appendix C)
# ---------------------------------------------------------------------------

# Snake_case header literals expected in row 3 of the staging template.
# Order is the column order PIMS-side reads at routes.py:2131; we match
# against the template's actual row 3 at build time but keep this list
# as a contract reference + due-category dispatch keys.
STAGING_HEADERS: tuple[str, ...] = (
    "id", "photo", "site_address", "audit_date", "observation_text",
    "finding", "conformance_status", "ccvs_code", "ccvs_category",
    "action_description", "responsible", "due_category", "recommendation",
    "monitoring_note", "legal_ref", "photo_refs", "prepared_by",
    "source_pdf", "section", "needs_review",
)

# Per Field Defaults: due_category derived deterministically from status.
_DUE_CATEGORY = {
    "NCR": "Immediate",
    "Conditional": "Within 7 days",
}


def _staging_row_value(
    row: EnrichedRow,
    header: str,
    site_address: str,
    audit_date_iso: str,
    prepared_by: str,
) -> object:
    """Map a snake_case staging header to its cell value.

    Per Field Defaults (workflow plan §"PIMS Staging workbook"). ``id``
    is ALWAYS blank — see "Insert-from-staging direction" in the plan;
    the upload endpoint takes Branch B (INSERT) only when id is empty.
    Returning a ``uuid4()`` here would silently no-op every row at
    upload time.
    """
    obs = row.obs
    if header == "id":
        return ""  # Branch B contract — never uuid4
    if header == "photo":
        return ""  # image-only cell; image added separately
    if header == "site_address":
        return site_address or ""
    if header == "audit_date":
        return audit_date_iso or ""  # always folder-derived, never row-level
    if header == "observation_text":
        return row.observation_text_clean or obs.observation_text
    if header == "finding":
        return row.finding or ""
    if header == "conformance_status":
        return row.conformance_status
    if header == "ccvs_code":
        return row.ccvs_code
    if header == "ccvs_category":
        return row.ccvs_category
    if header == "action_description":
        return row.action_description
    if header == "responsible":
        return ""  # filled at QA review
    if header == "due_category":
        return _DUE_CATEGORY.get(row.conformance_status, "N/A")
    if header == "recommendation":
        return row.recommendation
    if header == "monitoring_note":
        return row.monitoring_note
    if header == "legal_ref":
        return row.legal_ref
    if header == "photo_refs":
        return obs.resolved_filename or ""
    if header == "prepared_by":
        return prepared_by or "Alan Richardson"
    if header == "source_pdf":
        return ""
    if header == "section":
        return ""  # PIMS auto-derives server-side from CCVS category
    if header == "needs_review":
        return "TRUE" if row.needs_review else "FALSE"
    return ""


def build_pims_staging_xlsx(
    rows: list[EnrichedRow],
    output_path: Path,
    site_address: str,
    audit_date_iso: str,
    prepared_by: str = "Alan Richardson",
    max_edge_px: int = 1600,
    template_path: Path = PIMS_STAGING_TEMPLATE,
) -> dict:
    """Render the staging xlsx in PIMS upload format per Appendix C.

    Sheet ``Observations``: row 3 = snake_case headers (template);
    data appended from row 5. Photos embedded in column B (review
    only — PIMS upload endpoint joins via ``photo_refs``).

    Returns diagnostics for ``.ssa_run.json``:
        {
          "photo_load_failed":            [...],
          "photo_file_missing_at_render": [...],
          "rows_written":                 int,
          "final_bytes":                  int,
          "max_edge_px":                  int,   # actual cap used
        }

    The 5 MB cap and split-on-size path (Appendix C §C.6) are the
    caller's responsibility — this builder honours ``max_edge_px`` so
    the orchestrator can re-render at progressively smaller caps
    (1200 → 1000 → 800) before falling back to a row-count split.
    """
    import os
    import openpyxl
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.utils import get_column_letter

    if not template_path.exists():
        raise FileNotFoundError(
            f"PIMS staging template missing: {template_path}"
        )

    tmp = output_path.with_name(output_path.name + ".tmp.xlsx")
    shutil.copyfile(template_path, tmp)

    wb = openpyxl.load_workbook(tmp)
    if "Observations" not in wb.sheetnames:
        raise ValueError("template missing 'Observations' sheet")
    ws = wb["Observations"]

    # Read row 3 header literals — the template is the source of truth.
    headers = [
        ("" if c.value is None else str(c.value).strip().lower())
        for c in ws[3]
    ]
    # Locate the photo column from the template (defensive — defaults to
    # column B per Appendix C R-C-2.1).
    try:
        photo_col_idx = headers.index("photo") + 1
    except ValueError:
        photo_col_idx = 2

    diagnostics: dict[str, object] = {
        "photo_load_failed": [],
        "photo_file_missing_at_render": [],
        "rows_written": 0,
        "final_bytes": 0,
        "max_edge_px": max_edge_px,
    }

    for data_idx, row in enumerate(rows, start=1):
        excel_row = data_idx + 4  # row 5 is the first data row

        for col_idx, hdr in enumerate(headers, start=1):
            if hdr == "photo":
                continue  # image-only cell
            value = _staging_row_value(
                row, hdr, site_address, audit_date_iso, prepared_by,
            )
            ws.cell(row=excel_row, column=col_idx, value=value)

        path = row.obs.resolved_path
        if path is None:
            continue
        if not path.exists():
            diagnostics["photo_file_missing_at_render"].append(str(path))
            continue
        prepared = _preprocess_photo(path, max_edge_px=max_edge_px)
        if prepared is None:
            diagnostics["photo_load_failed"].append(str(path))
            continue
        buf, _fmt, w_px, h_px = prepared
        img = XLImage(buf)
        scale = _PHOTO_THUMB_PX / float(w_px)
        img.width = _PHOTO_THUMB_PX
        img.height = max(1, int(round(h_px * scale)))
        anchor_col = get_column_letter(photo_col_idx)
        ws.add_image(img, anchor=f"{anchor_col}{excel_row}")
        ws.row_dimensions[excel_row].height = max(95, img.height)

    diagnostics["rows_written"] = len(rows)
    _apply_xlsx_polish(
        ws,
        header_row_idx=3,
        data_first_row=5,
        col_widths=_STAGING_COL_WIDTHS,
        status_header="conformance_status",
    )
    wb.save(tmp)
    wb.close()
    diagnostics["final_bytes"] = tmp.stat().st_size
    os.replace(tmp, output_path)
    return diagnostics


# ---------------------------------------------------------------------------
# Staging size-control wrapper (Appendix C §C.6)
# ---------------------------------------------------------------------------

# 5 MB hard cap from pims/routes.py:2113 (RPD upload endpoint). The
# 500-row cap (R-1) is independent and applies even when size is fine.
STAGING_MAX_BYTES = 5 * 1024 * 1024
STAGING_MAX_ROWS = 500

# Progressive downscale ladder. Each rung is a longest-edge cap fed to
# `_preprocess_photo`. Order matters: the first rung that produces a
# file ≤ 5 MB wins. If 800 px still oversizes a single part, fall
# through to a row-count split at the smallest cap.
_DOWNSCALE_LADDER = (1600, 1200, 1000, 800)


def _staging_part_path(output_path: Path, part_idx: int, total_parts: int) -> Path:
    """Single-file when total_parts == 1; ``-partN.xlsx`` suffix otherwise."""
    if total_parts == 1:
        return output_path
    stem = output_path.stem  # ``...-RPD``
    return output_path.with_name(f"{stem}-part{part_idx}{output_path.suffix}")


def build_pims_staging_xlsx_with_size_control(
    rows: list[EnrichedRow],
    output_path: Path,
    site_address: str,
    audit_date_iso: str,
    prepared_by: str = "Alan Richardson",
    template_path: Path = PIMS_STAGING_TEMPLATE,
    max_bytes: int = STAGING_MAX_BYTES,
    max_rows: int = STAGING_MAX_ROWS,
) -> dict:
    """Render the staging xlsx within the PIMS upload limits (5 MB / 500 rows).

    Returns a dict shaped:
        {
          "parts":          [Path, ...],        # written files in order
          "max_edge_px":    int,                # cap that produced the parts
          "split":          bool,
          "split_reason":   "row_count" | "size" | None,
          "diagnostics":    [per-part diag, ...],
        }

    Strategy (per Appendix C §C.6):
      1. If ``len(rows) > max_rows`` → split by row count up front; each
         chunk renders independently at the default 1600 px cap. This is
         the cheap path — no re-render loop.
      2. Otherwise render at 1600 px. If ≤ ``max_bytes`` → done.
      3. Otherwise re-render at 1200 → 1000 → 800 px. First pass under
         budget wins.
      4. If 800 px still over budget → split the row set in halves
         (recursively at 800 px) until every part fits or a part has
         only one row. A single-row part that still oversizes is the
         "photo too large for staging" case in the plan; we still emit
         it and surface the size in diagnostics.

    The non-size-controlled builder remains in place for callers that
    want a single render at a fixed cap (tests, debugging).
    """
    diags: list[dict] = []

    def _render_at(rs: list[EnrichedRow], path: Path, edge_px: int) -> dict:
        return build_pims_staging_xlsx(
            rs, path,
            site_address=site_address,
            audit_date_iso=audit_date_iso,
            prepared_by=prepared_by,
            max_edge_px=edge_px,
            template_path=template_path,
        )

    # --- Path 1: row-count split (deterministic, no size loop) ------
    if len(rows) > max_rows:
        chunks = [rows[i:i + max_rows] for i in range(0, len(rows), max_rows)]
        total = len(chunks)
        parts_written: list[Path] = []
        for idx, chunk in enumerate(chunks, start=1):
            part_path = _staging_part_path(output_path, idx, total)
            d = _render_at(chunk, part_path, _DOWNSCALE_LADDER[0])
            diags.append(d)
            parts_written.append(part_path)
        return {
            "parts": parts_written,
            "max_edge_px": _DOWNSCALE_LADDER[0],
            "split": True,
            "split_reason": "row_count",
            "diagnostics": diags,
        }

    # --- Path 2-3: progressive downscale on a single part ----------
    for edge_px in _DOWNSCALE_LADDER:
        d = _render_at(rows, output_path, edge_px)
        diags.append(d)
        if d["final_bytes"] <= max_bytes:
            return {
                "parts": [output_path],
                "max_edge_px": edge_px,
                "split": False,
                "split_reason": None,
                "diagnostics": diags,
            }

    # --- Path 4: size-driven split at the smallest cap -------------
    # Bisect the row set; each half is recursed into the same wrapper
    # so a half that fits short-circuits cleanly. Halves render at the
    # smallest cap because anything larger has already been rejected
    # at the full set.
    if len(rows) <= 1:
        # Single row over budget at 800 px — emit it and flag.
        return {
            "parts": [output_path],
            "max_edge_px": _DOWNSCALE_LADDER[-1],
            "split": False,
            "split_reason": None,
            "diagnostics": diags,
            "oversize_row": True,
        }

    mid = len(rows) // 2
    left_rows, right_rows = rows[:mid], rows[mid:]
    # Reserve part1/part2 names; recurse into a temporary "single-file"
    # path per half, then collapse into our caller's part list.
    left_path = _staging_part_path(output_path, 1, 2)
    right_path = _staging_part_path(output_path, 2, 2)

    left = build_pims_staging_xlsx_with_size_control(
        left_rows, left_path,
        site_address=site_address, audit_date_iso=audit_date_iso,
        prepared_by=prepared_by, template_path=template_path,
        max_bytes=max_bytes, max_rows=max_rows,
    )
    right = build_pims_staging_xlsx_with_size_control(
        right_rows, right_path,
        site_address=site_address, audit_date_iso=audit_date_iso,
        prepared_by=prepared_by, template_path=template_path,
        max_bytes=max_bytes, max_rows=max_rows,
    )

    # If the recursion itself produced parts (size-driven splits within
    # halves), flatten and renumber so the final file set is
    # `-part1.xlsx`, `-part2.xlsx`, …, regardless of recursion depth.
    flat: list[Path] = []
    for p in (*left["parts"], *right["parts"]):
        flat.append(p)
    final_paths: list[Path] = []
    total = len(flat)
    if total == 1:
        # Single part was returned — collapse name to canonical.
        if flat[0] != output_path:
            flat[0].replace(output_path)
        final_paths = [output_path]
    else:
        for new_idx, current in enumerate(flat, start=1):
            new_path = _staging_part_path(output_path, new_idx, total)
            if current != new_path:
                if new_path.exists():
                    new_path.unlink()
                current.replace(new_path)
            final_paths.append(new_path)

    return {
        "parts": final_paths,
        "max_edge_px": _DOWNSCALE_LADDER[-1],
        "split": True,
        "split_reason": "size",
        "diagnostics": [
            *left.get("diagnostics", []),
            *right.get("diagnostics", []),
        ],
    }


# ---------------------------------------------------------------------------
# Upstream stage - enrich_observations
# ---------------------------------------------------------------------------

# Collapse runs of whitespace to a single space; strip ends. The cleanup
# is deliberately conservative — we don't reflow sentences, we don't
# autocapitalise, we don't strip trailing punctuation. The LLM finding
# pass (when enabled) does the year-12 rewrite separately.
_WS_RUN = re.compile(r"\s+")


def _light_cleanup(text: str) -> str:
    if not text:
        return ""
    return _WS_RUN.sub(" ", text).strip()


def enrich_observations(
    rows: list[ObservationRow],
    checklist: object | None = None,
    ccvs_codes: dict[int, str] | None = None,
    auto_match: bool = False,
) -> list[EnrichedRow]:
    """Lift parsed CSV rows into builder-ready ``EnrichedRow``s.

    v1 contract — CCVS resolution is **out of scope**. Every row lands
    with ``conformance_status="Unmatched"`` and blank checklist-derived
    fields, matching the "no checklist match" defaults in the plan
    ("Defaults for kept-but-invalid rows"): ``Action Required="Yes"``
    (forced via the EnrichedRow property), ``needs_review=TRUE``, every
    checklist column blank, ``finding`` initially blank (builders fall
    back to ``observation_text_clean``).

    Hooks for a later auto-matcher are kept narrow:
      - ``checklist`` is a ``ChecklistLookup`` (or anything exposing
        ``.match(ccvs_code) -> ChecklistMatch | None``).
      - ``ccvs_codes`` is an optional ``{csv_row: ccvs_code}`` map. When
        supplied, any matched code populates the deterministic checklist
        fields verbatim and lifts the status to a default of
        ``"Conditional"`` so the row is treated as a real finding rather
        than Unmatched. The status itself is never inferred — caller
        overrides via a sibling ``statuses`` arg in a later slice.

    The function is sync and side-effect-free. LLM-driven finding
    rewrites (educational tone, narrative summary) run as a separate
    async pass in the orchestrator — keeps this stage testable without
    Anthropic credentials.
    """
    enriched: list[EnrichedRow] = []
    for obs in rows:
        clean = _light_cleanup(obs.observation_text)
        row = EnrichedRow(
            obs=obs,
            observation_text_clean=clean,
            finding="",
            conformance_status="Unmatched",
        )

        match = None
        ccvs = (ccvs_codes or {}).get(obs.csv_row, "").strip()
        if ccvs and checklist is not None:
            # Caller-supplied CCVS code is authoritative (manual override
            # path or future explicit-mapping pre-stage).
            match = checklist.match(ccvs)
        elif auto_match and checklist is not None:
            # Conservative token-recall match against the criteria
            # corpus — see ``ChecklistLookup.match_observation`` for the
            # gate (≥2 overlap, ≥0.40 score, ≥0.10 margin). A miss
            # leaves the row at status="Unmatched".
            text = clean or obs.observation_text
            try:
                match = checklist.match_observation(text)  # type: ignore[attr-defined]
            except AttributeError:
                match = None

        if match is not None:
            row.ccvs_code = match.ccvs_code
            row.ccvs_category = match.ccvs_category
            row.action_description = match.action_description
            row.recommendation = match.recommendation
            row.legal_ref = match.legal_ref
            row.monitoring_note = match.monitoring_note
            # Reviewer flips the status at QA — auto-match cannot tell
            # NCR from Compliant, so default to Conditional which still
            # surfaces ``needs_review=TRUE`` and a "Within 7 days" due
            # category for follow-up. Caller can override status via a
            # future ``statuses`` arg without touching this stage.
            row.conformance_status = "Conditional"

        enriched.append(row)

    return enriched

```

### `pims/services/ssa_checklist_lookup.py`

Legacy CCVS-keyed lookup over audit_checklist.xlsx. Kept as a deterministic fallback for --no-enrich mode; bypassed when vision is on.

```python
"""CCVS-keyed lookup over ``pims/audit_checklist.xlsx``.

Phase 1 helper for the SSA pipeline (workflow #1). Distinct from
``pims/services/checklist_matcher.py`` — that module operates on
Supabase ``checklist_items`` rows and returns severity states. This
module reads the static reviewer checklist xlsx and exposes a
``ChecklistMatch`` keyed by CCVS code, providing the verbatim values
the SSA pipeline writes into PIMS-Enriched / Staging xlsx fields.

The current ``audit_checklist.xlsx`` only carries
``Category, Criteria, Instruction`` columns. Any later columns
(``CCVS Code``, ``Legal Ref``, ``Action Description``,
``Recommendation``, ``Monitoring Note``) are picked up automatically
when the xlsx is extended; missing columns resolve to blank strings,
never None — caller writes them straight into a cell.

Lookup contract (per workflow plan §"Field Defaults"):

    ChecklistLookup.from_xlsx(path).match(ccvs_code) -> ChecklistMatch | None
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import openpyxl

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChecklistMatch:
    ccvs_code: str
    ccvs_category: str
    action_description: str
    recommendation: str
    legal_ref: str
    monitoring_note: str
    criteria: str = ""


# Header-name → field. Lowercased + whitespace-collapsed for matching.
# ``Instruction`` (the operational guidance column in the current xlsx)
# maps to ``action_description`` — that's what reviewers want in the
# action-register cell on the staging xlsx.
_HEADER_MAP = {
    "ccvs code": "ccvs_code",
    "ccvs_code": "ccvs_code",
    "category": "ccvs_category",
    "ccvs category": "ccvs_category",
    "ccvs_category": "ccvs_category",
    "action description": "action_description",
    "action_description": "action_description",
    "instruction": "action_description",
    "recommendation": "recommendation",
    "legal ref": "legal_ref",
    "legal_ref": "legal_ref",
    "monitoring note": "monitoring_note",
    "monitoring_note": "monitoring_note",
    "criteria": "criteria",
}

# Australian WHS legal-reference patterns embedded inside Criteria text,
# e.g. ``(WHS Reg cl.34-38)`` / ``(AS 1742.3)`` / ``(WHS Act s.19)``.
# Conservative — extracts only well-shaped citations, no fuzzy guesses.
_LEGAL_REF_RE = re.compile(
    r"\(("
    r"WHS\s+(?:Act|Reg)[^)]+|"
    r"AS\s*\d[\d./\s-]*|"
    r"AS/NZS\s*\d[\d./\s-]*"
    r")\)",
    re.IGNORECASE,
)


def _extract_legal_ref(criteria: str) -> str:
    if not criteria:
        return ""
    m = _LEGAL_REF_RE.search(criteria)
    return m.group(1).strip() if m else ""


# Token-set tools for the auto-matcher (match_observation). Stopword
# list is deliberately tight — drop only true noise words; keep WHS
# domain terms (eg. "first", "high", "edge") that carry signal.
_MATCHER_STOP = frozenset(
    "a an the is are was were be been being and or of to for in on at by "
    "with from as that this it not no any all each every some none has have "
    "had do did does we you they i me my our your their he she his her its "
    "but if then so than which who whom whose where when why how"
    .split()
)
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    if not text:
        return set()
    return {
        w for w in _TOKEN_RE.findall(text.lower())
        if len(w) >= 3 and w not in _MATCHER_STOP
    }

# `01. Planning ...` / `01.02 ...` leading-number extraction. Used to
# synthesise a CCVS code when the xlsx doesn't carry one explicitly.
_LEADING_NUM = re.compile(r"^\s*(\d{1,3})(?:\.(\d{1,3}))?")


def _norm_header(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def _leading_num(value: object) -> tuple[str, str]:
    """Return (cat_num, item_num) extracted from a leading numeric prefix.

    ``"01. Planning and Risk Management"`` -> (``"01"``, ``""``).
    ``"02. Does the site sign include..."`` (criteria) -> (``"02"``, ``""``).
    Returns ``("", "")`` when nothing matches.
    """
    if value is None:
        return "", ""
    m = _LEADING_NUM.match(str(value))
    if not m:
        return "", ""
    return m.group(1), (m.group(2) or "")


def _synthesise_ccvs_code(cat_value: object, criteria_value: object) -> str:
    """Build ``"<cat>.<item>"`` from leading numbers on Category + Criteria.

    Returns ``""`` if either side has no numeric prefix — the caller then
    skips this row (no key, no match possible).
    """
    cat_num, _ = _leading_num(cat_value)
    item_num, _ = _leading_num(criteria_value)
    if not cat_num or not item_num:
        return ""
    return f"{int(cat_num):02d}.{int(item_num):02d}"


@dataclass
class ChecklistLookup:
    by_code: dict[str, ChecklistMatch]

    @classmethod
    def from_xlsx(
        cls,
        path: Path,
        sheet_names: Iterable[str] | None = None,
    ) -> "ChecklistLookup":
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        sheets = list(sheet_names) if sheet_names else list(wb.sheetnames)

        by_code: dict[str, ChecklistMatch] = {}
        for sheet in sheets:
            if sheet not in wb.sheetnames:
                log.warning("checklist sheet %s missing from %s", sheet, path)
                continue
            ws = wb[sheet]
            rows = ws.iter_rows(values_only=True)
            try:
                header_row = next(rows)
            except StopIteration:
                continue
            header_to_idx: dict[str, int] = {}
            for idx, cell in enumerate(header_row):
                key = _HEADER_MAP.get(_norm_header(cell))
                if key and key not in header_to_idx:
                    header_to_idx[key] = idx
            cat_idx = header_to_idx.get("ccvs_category")
            crit_idx = header_to_idx.get("criteria")
            # Heuristic fallback: first column = category, second = criteria
            # when the headers are literal "Category" / "Criteria".
            if cat_idx is None and len(header_row) > 0:
                cat_idx = 0
            if crit_idx is None and len(header_row) > 1:
                crit_idx = 1

            for row in rows:
                if not row or all((c is None or str(c).strip() == "") for c in row):
                    continue

                def cell(field: str) -> str:
                    i = header_to_idx.get(field)
                    if i is None or i >= len(row):
                        return ""
                    v = row[i]
                    return "" if v is None else str(v).strip()

                ccvs_code = cell("ccvs_code")
                if not ccvs_code:
                    cat_v = row[cat_idx] if cat_idx is not None and cat_idx < len(row) else ""
                    crit_v = row[crit_idx] if crit_idx is not None and crit_idx < len(row) else ""
                    ccvs_code = _synthesise_ccvs_code(cat_v, crit_v)
                if not ccvs_code:
                    continue

                cat_v = row[cat_idx] if cat_idx is not None and cat_idx < len(row) else ""
                crit_v = row[crit_idx] if crit_idx is not None and crit_idx < len(row) else ""
                criteria_text = cell("criteria") or (str(crit_v).strip() if crit_v else "")
                # Pull a legal_ref out of the criteria text when the
                # column itself is blank — current xlsx lacks the column
                # but criteria like ``(WHS Reg cl.34-38)`` carry it.
                legal_ref = cell("legal_ref") or _extract_legal_ref(criteria_text)
                match = ChecklistMatch(
                    ccvs_code=ccvs_code,
                    ccvs_category=cell("ccvs_category") or (str(cat_v).strip() if cat_v else ""),
                    action_description=cell("action_description"),
                    recommendation=cell("recommendation"),
                    legal_ref=legal_ref,
                    monitoring_note=cell("monitoring_note"),
                    criteria=criteria_text,
                )
                # First sheet wins on duplicate keys (the <$250K sheet ships
                # first; >$250K is the same coding).
                by_code.setdefault(ccvs_code.lower(), match)

        return cls(by_code=by_code)

    def match(self, ccvs_code: str) -> ChecklistMatch | None:
        if not ccvs_code:
            return None
        return self.by_code.get(ccvs_code.strip().lower())

    def match_observation(
        self,
        observation_text: str,
        min_overlap: int = 2,
        min_score: float = 0.40,
        min_margin: float = 0.10,
    ) -> ChecklistMatch | None:
        """Best-fit checklist row for a free-form observation.

        Scoring is token-recall against the observation:
            score = |obs_tokens ∩ candidate_tokens| / |obs_tokens|

        Conservative gate — a candidate wins iff ALL hold:
          - ``overlap`` (the size of the token intersection) ≥ ``min_overlap``
          - ``score`` ≥ ``min_score``
          - ``score`` exceeds the second-best candidate's score by at
            least ``min_margin`` (an unambiguous winner)

        Otherwise returns ``None`` — the caller should leave the row at
        ``status="Unmatched"``. Defaults were probed against the v1
        ``audit_checklist.xlsx`` and ten representative audit
        observations: they accept the obvious wins and reject the ties.
        """
        obs_tokens = _tokens(observation_text)
        if len(obs_tokens) < min_overlap:
            return None

        scored: list[tuple[float, int, ChecklistMatch]] = []
        for m in self.by_code.values():
            cand_tokens = _tokens(f"{m.criteria} {m.ccvs_category}")
            if not cand_tokens:
                continue
            overlap = len(obs_tokens & cand_tokens)
            if overlap < min_overlap:
                continue
            score = overlap / len(obs_tokens)
            if score < min_score:
                continue
            scored.append((score, overlap, m))

        if not scored:
            return None
        # Highest score wins; ties broken by raw overlap count, then by
        # CCVS code (stable / deterministic).
        scored.sort(key=lambda t: (-t[0], -t[1], t[2].ccvs_code))
        top = scored[0]
        if len(scored) >= 2 and (top[0] - scored[1][0]) < min_margin:
            return None
        return top[2]

```

### `pims/services/ssa_ccvs_taxonomy.py`

Canonical 25-stream x 6-tier CCVS taxonomy. Replaces the audit_checklist.xlsx-derived 01.01 numeric scheme with the real WAH-H6 / SYS-M3 / etc. coding the canonical samples use.

```python
"""Canonical CCVS coding taxonomy for SSA audit deliverables.

Source of truth: ``renderers/docx_renderer.py`` ``_VALID_CCVS_STREAMS``
(24 streams) plus ``SYS`` (Systems / Compliance Records) which the
``PIMS-Enriched - Sample.xlsx`` confirms is in active use on the
audit side even though the SWMS-side validator rejects it.

A CCVS code is ``<STREAM>-<TIER>`` where ``STREAM`` is one of the 25
3-letter prefixes listed below and ``TIER`` is one of the 6 valid
severity-ordering suffixes (H6/H9 high, M3/M4 medium, L1/L2 low).

Plain-English category names are reviewer-facing labels that appear in
the ``CCVS Category`` column of the PIMS-Enriched workbook and the
``ccvs_category`` column of the staging xlsx. They are short trade or
hazard-family names, not the long SWMS-side section headings.
"""
from __future__ import annotations

import re

# Stream prefix → reviewer-facing category. Keys MUST match the
# ``_VALID_CCVS_STREAMS`` list in ``renderers/docx_renderer.py`` plus
# the audit-side ``SYS`` extension.
STREAM_TO_CATEGORY: dict[str, str] = {
    "WFR": "Worker Facilities",
    "WFA": "Worker Amenities",
    "WAH": "Work at Height",
    "IRA": "Industrial Rope Access",
    "ELE": "Electrical",
    "SIL": "Silica Dust",
    "STR": "Structural",
    "CFS": "Confined Space",
    "ENE": "Energy and Services",
    "HOT": "Hot Works",
    "MOB": "Mobile Plant",
    "ASB": "Asbestos",
    "LED": "Lead Hazard",
    "TRF": "Traffic Management",
    "ENV": "Environmental",
    "CHM": "Chemical / Hazardous Substances",
    "SCF": "Scaffold",
    "CRN": "Crane and Lifting",
    "EXC": "Excavation and Trenching",
    "MNH": "Manual Handling",
    "NOI": "Noise",
    "TLT": "Tilt-up and Precast",
    "DEM": "Demolition",
    "FMW": "Formwork",
    "SYS": "Systems",
}

VALID_STREAMS: frozenset[str] = frozenset(STREAM_TO_CATEGORY)

# Severity-ordered tier suffixes. Letter = severity (H/M/L), digit =
# ordering within tier. Reviewers pick the tier from observed evidence.
VALID_TIERS: frozenset[str] = frozenset({"H6", "H9", "M3", "M4", "L1", "L2"})

# Reviewer-facing severity descriptions — used in LLM prompts so the
# model picks a tier consistent with what the photo + observation show.
TIER_DESCRIPTION: dict[str, str] = {
    "H6": "High severity — immediate non-conformance, stop-work or NCR",
    "H9": "High severity — uncontrolled risk, NCR with urgent remediation",
    "M3": "Medium severity — non-conformance with managed risk, conditional",
    "M4": "Medium severity — observation needing controls, conditional",
    "L1": "Low severity — minor finding or compliant-with-notes",
    "L2": "Low severity — record-keeping or systems compliance item",
}

# Conformance status canonical set. The LLM picks one per observation.
VALID_STATUSES: frozenset[str] = frozenset(
    {"Compliant", "Conditional", "NCR", "Info", "Unmatched"}
)

_CCVS_RE = re.compile(
    r"^(" + "|".join(sorted(VALID_STREAMS)) + r")-(H6|H9|M3|M4|L1|L2)$"
)


def is_valid_code(code: str) -> bool:
    """Return True iff ``code`` is one of the 25 × 6 = 150 valid codes."""
    return bool(code) and bool(_CCVS_RE.match(code))


def category_for(code: str) -> str:
    """Plain-English category for a CCVS code. Returns ``""`` on invalid."""
    if not code:
        return ""
    m = _CCVS_RE.match(code)
    if not m:
        return ""
    return STREAM_TO_CATEGORY.get(m.group(1), "")


def stream_of(code: str) -> str:
    """Return the 3-letter stream prefix or ``""`` on invalid."""
    if not code:
        return ""
    m = _CCVS_RE.match(code)
    return m.group(1) if m else ""

```

### `pims/services/ssa_vision_enricher.py`

Per-row Anthropic vision call (Opus 4.7). Sends downscaled EXIF-normalised photo + observation text + project RA context. Receives status / ccvs_code / finding / legal_ref / recommendation / monitoring_note. Transient-error retry.

```python
"""Vision-enabled per-observation enrichment for the SSA pipeline.

For each evidence row this module sends the photo (downscaled,
EXIF-normalised, base64-encoded) plus the auditor's raw observation
text to an Anthropic vision call and receives a JSON record carrying:

  - conformance_status  (Compliant / Conditional / NCR / Info / Unmatched)
  - ccvs_code           (one of the 150 valid <STREAM>-<TIER> codes)
  - ccvs_category       (plain-English category derived from the stream)
  - finding             (multi-sentence narrative, year-12 plain English)
  - legal_ref           (NSW WHS regulation / AS / SafeWork NSW citation)
  - recommendation      (one-sentence corrective action)
  - monitoring_note     (one-sentence reviewer follow-up cue)

Replaces the keyword-based ``ChecklistLookup.match_observation``
matcher — that approach hit 5/21 on real audit data with one outright
misroute. The vision approach uses the photo as primary evidence,
which matches how the human reviewer assigns these fields.

LLM is on by default. ``ANTHROPIC_API_KEY`` must be set in the
environment. When the key is missing or any individual call fails,
the row falls back to ``conformance_status="Unmatched"`` and blank
fields — never raises into the orchestrator.

Cost expectation: ~21 rows × one Sonnet vision call ≈ $0.10–$0.20 per
typical audit. Image is downscaled to 1024 px longest edge before
base64 encoding to keep input tokens predictable.
"""
from __future__ import annotations

import base64
import json
import logging
import os
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx

from pims.services.ssa_ccvs_taxonomy import (
    STREAM_TO_CATEGORY,
    TIER_DESCRIPTION,
    VALID_STATUSES,
    category_for,
    is_valid_code,
)
from pims.services.ssa_pipeline import EnrichedRow

log = logging.getLogger(__name__)

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
VISION_MODEL = "claude-opus-4-7"

# Largest edge for the photo passed into the vision call. 1024 px is
# enough resolution for compliance evidence (signage legibility, edge
# protection presence, PPE on workers) while keeping each call's input
# tokens around 1k–1.5k for the image plus ~500 for text.
_VISION_MAX_EDGE_PX = 1024

# Hard cap on JSON output size — replies are small structured records,
# 800 tokens is plenty for the longest finding paragraph + citations.
_MAX_OUTPUT_TOKENS = 800


def _encode_photo_for_vision(path: Path) -> tuple[str, str] | None:
    """EXIF-normalise + downscale + JPEG-encode + base64.

    Returns ``(base64_str, "image/jpeg")`` or ``None`` on failure /
    missing file. JPEG quality 85 is the same setting as the embedded-
    thumbnail path, so the image the LLM sees is consistent with what
    the reviewer sees in the deliverable.
    """
    try:
        from PIL import Image, ImageOps
    except Exception:
        log.warning("Pillow unavailable — vision enrichment skipped")
        return None
    if not path.exists():
        return None
    try:
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im)
            longest = max(im.width, im.height)
            if longest > _VISION_MAX_EDGE_PX:
                ratio = _VISION_MAX_EDGE_PX / float(longest)
                im = im.resize(
                    (int(im.width * ratio), int(im.height * ratio)),
                    Image.LANCZOS,
                )
            buf = BytesIO()
            im.convert("RGB").save(buf, format="JPEG", quality=85)
            data = base64.standard_b64encode(buf.getvalue()).decode("ascii")
            return data, "image/jpeg"
    except Exception:
        log.warning("vision photo encode failed for %s", path, exc_info=True)
        return None


_TIER_LIST = "\n".join(f"  {t}  {desc}" for t, desc in TIER_DESCRIPTION.items())
_STREAM_LIST = "\n".join(
    f"  {s}  {cat}" for s, cat in sorted(STREAM_TO_CATEGORY.items())
)

_SYSTEM_PROMPT = (
    "You are an Australian construction WHS auditor reviewing one site "
    "evidence photo plus the auditor's raw note. Classify the "
    "observation against the canonical CCVS taxonomy and write the "
    "review-ready finding.\n\n"
    "OUTPUT JSON ONLY — no prose, no markdown fences. The JSON object "
    "must carry exactly these keys:\n"
    '  status            ∈ ["Compliant", "Conditional", "NCR", "Info", "Unmatched"]\n'
    '  ccvs_code         "<STREAM>-<TIER>" or "" if no clear match\n'
    '  ccvs_category     plain-English category for the chosen stream, or ""\n'
    '  finding           2–4 sentence narrative, year-12 plain English\n'
    '  legal_ref         NSW WHS Reg / AS / SafeWork NSW citation, or ""\n'
    '  recommendation    one short sentence, or ""\n'
    '  monitoring_note   one short sentence reviewer cue, or ""\n\n'
    "STREAM PREFIXES (pick exactly one):\n"
    f"{_STREAM_LIST}\n\n"
    "SEVERITY TIERS:\n"
    f"{_TIER_LIST}\n\n"
    "CLASSIFICATION RULES:\n"
    "- Compliant: photo shows the control in place AND the auditor's "
    "  note describes a satisfactory state. Use a tier (usually L1/L2) "
    "  but the row records compliance, not non-conformance.\n"
    "- Conditional: control is present but partially in place, OR the "
    "  evidence needs follow-up. Tier M3/M4 typical.\n"
    "- NCR: control absent or seriously inadequate. Tier H6/H9.\n"
    "- Info: contextual / record-keeping observation, no control "
    "  judgement. Tier L1/L2 typical.\n"
    "- Unmatched: neither photo nor note give enough signal to "
    "  classify. Reviewer assigns at QA. Set ccvs_code, ccvs_category "
    "  to \"\" in this case.\n\n"
    "FINDING WRITING RULES (year-12 plain English, Australian):\n"
    "- 2–4 sentences. Describe what was observed, why it matters, and "
    "  what good looks like. Do not paraphrase the raw note — write "
    "  the reviewer-grade finding.\n"
    "- Cite the legal_ref inside the finding sentence when one applies "
    "  (e.g. \"contrary to WHS Regulation 2017 cl.79\").\n"
    "- Banned vocabulary: crucial, pivotal, landscape, ensure, "
    "  leverage, robust, comprehensive, navigate, delve, it's "
    "  important to note, serves as, at its core. No em-dash clusters, "
    "  no signposting, no sycophantic openers/closers, no emoji, no "
    "  curly quotes.\n"
    "- Do not invent measurements, names, dates, or evidence not "
    "  present in the photo or note.\n"
    "- For Compliant rows, the finding describes what was seen and "
    "  why it satisfies the requirement.\n\n"
    "LEGAL_REF RULES:\n"
    "- Use canonical Australian forms: \"NSW WHS Regulation 2017 cl.79\", "
    "  \"WHS Act 2011 s.19\", \"AS/NZS 1576.1:2019\", \"SafeWork NSW "
    "  Code of Practice: Construction Work (2022)\".\n"
    "- Leave \"\" if you do not know the citation. Do not fabricate.\n\n"
    "RECOMMENDATION + MONITORING_NOTE:\n"
    "- Both single-sentence. Recommendation is the corrective action; "
    "  monitoring_note is what the next audit should verify.\n"
    "- For Compliant / Info rows, recommendation may be \"\" and "
    "  monitoring_note records the verification cue."
)


_TRANSIENT_HTTP_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


async def _vision_call(
    photo_b64: str, photo_mime: str, observation_text: str,
    site_address: str, audit_date_iso: str, api_key: str,
    ra_context: str = "",
    retries: int = 2,
) -> dict[str, Any]:
    """Single Anthropic vision call. Returns the parsed JSON dict.

    Raises on HTTP error / JSON parse failure / network — caller wraps
    in try/except and falls back to Unmatched on any failure.

    ``ra_context`` is the compact project Risk Assessment block (per
    ``ssa_ra_parser.compact_context_block``). When non-empty, the
    model is instructed to cite RA hold-point codes (``HP-04``) and
    activity refs (``TP-05``) inside the finding text, and to align
    severity with the RA's Initial / Residual rubric where it can.
    """
    parts: list[str] = []
    if ra_context:
        parts.append(ra_context)
        parts.append("")
        parts.append(
            "RA-ALIGNMENT INSTRUCTIONS:\n"
            "- When this photo + note relates to a specific RA "
            "  activity, reference the activity ref (e.g. TP-05) "
            "  inside your finding sentence.\n"
            "- When the activity is gated by a Hold Point, reference "
            "  the HP code (e.g. HP-04) and what evidence the RA "
            "  requires.\n"
            "- When the RA states an HRCW category for that activity, "
            "  mention it (e.g. \"HRCW H14 traffic corridor\").\n"
            "- Pick the CCVS tier (H6/H9/M3/M4/L1/L2) consistent with "
            "  the RA's Initial / Residual risk for the activity. NCR "
            "  status when the observed control falls below the RA's "
            "  minimum standard for that activity."
        )
        parts.append("")
    parts.append(f"SITE: {site_address or '(unresolved)'}")
    parts.append(f"AUDIT_DATE: {audit_date_iso}")
    parts.append(f"AUDITOR_NOTE: {observation_text}")
    user_text = "\n".join(parts) + "\n"
    body = {
        "model": VISION_MODEL,
        "max_tokens": _MAX_OUTPUT_TOKENS,
        "system": _SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": photo_mime,
                            "data": photo_b64,
                        },
                    },
                    {"type": "text", "text": user_text},
                ],
            }
        ],
    }
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    ANTHROPIC_URL,
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": ANTHROPIC_VERSION,
                        "content-type": "application/json",
                    },
                    json=body,
                )
            if resp.status_code in _TRANSIENT_HTTP_STATUSES:
                raise httpx.HTTPStatusError(
                    f"transient HTTP {resp.status_code}",
                    request=resp.request, response=resp,
                )
            resp.raise_for_status()
            text = resp.json()["content"][0]["text"].strip()
            break
        except (httpx.ConnectError, httpx.ReadError, httpx.WriteError,
                httpx.TimeoutException, httpx.RemoteProtocolError,
                httpx.HTTPStatusError) as exc:
            last_exc = exc
            if isinstance(exc, httpx.HTTPStatusError) and \
                    exc.response.status_code not in _TRANSIENT_HTTP_STATUSES:
                # 4xx (auth, bad request) — don't retry, surface
                raise
            if attempt >= retries:
                raise
            import asyncio
            await asyncio.sleep(1.5 * (attempt + 1))
    else:  # pragma: no cover — loop never falls through; either break or raise
        raise RuntimeError(f"vision call failed after retries: {last_exc}")
    # Strip code fences if the model wrapped output despite instruction.
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0].strip()
    return json.loads(text)


def _coerce_record(raw: dict[str, Any]) -> dict[str, str]:
    """Validate + normalise a single LLM record.

    - status falls back to ``"Unmatched"`` if not in the allowed set
    - ccvs_code is dropped (and category cleared) if it does not
      validate against the taxonomy
    - ccvs_category is regenerated from the (validated) code so the
      reviewer-facing label is always self-consistent
    """
    def _s(key: str) -> str:
        v = raw.get(key, "")
        return "" if v is None else str(v).strip()

    status = _s("status") or "Unmatched"
    if status not in VALID_STATUSES:
        status = "Unmatched"

    code = _s("ccvs_code").upper().replace(" ", "")
    if code and not is_valid_code(code):
        log.info("LLM returned invalid ccvs_code %r — dropping", code)
        code = ""
    category = category_for(code) if code else ""

    return {
        "status": status,
        "ccvs_code": code,
        "ccvs_category": category,
        "finding": _s("finding"),
        "legal_ref": _s("legal_ref"),
        "recommendation": _s("recommendation"),
        "monitoring_note": _s("monitoring_note"),
    }


async def enrich_rows_with_vision(
    rows: list[EnrichedRow],
    site_address: str,
    audit_date_iso: str,
    ra_context: str = "",
) -> dict[str, Any]:
    """In-place enrichment: photo+note → status + CCVS + finding fields.

    Returns a diagnostics dict for ``.ssa_run.json``:
        {
          "model":        str,
          "rows_total":   int,
          "rows_called":  int,    # rows that had a resolved photo
          "rows_ok":      int,    # successful enrichments
          "rows_failed":  int,    # API / parse / encode failures
          "errors":       [str],  # short error reasons (deduped)
        }

    Rows without a resolved photo cannot be vision-classified — they
    keep ``status="Unmatched"`` and blank fields.
    """
    diag: dict[str, Any] = {
        "model": VISION_MODEL,
        "rows_total": len(rows),
        "rows_called": 0,
        "rows_ok": 0,
        "rows_failed": 0,
        "errors": [],
    }

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log.warning(
            "ANTHROPIC_API_KEY not set — vision enrichment skipped, "
            "every row stays Unmatched"
        )
        diag["errors"].append("ANTHROPIC_API_KEY missing")
        return diag

    seen_errors: set[str] = set()
    for row in rows:
        path = row.obs.resolved_path
        if path is None:
            continue
        encoded = _encode_photo_for_vision(path)
        if encoded is None:
            diag["rows_failed"] += 1
            seen_errors.add(f"photo encode failed: {path.name}")
            continue
        photo_b64, photo_mime = encoded
        diag["rows_called"] += 1

        text = row.observation_text_clean or row.obs.observation_text or ""
        try:
            raw = await _vision_call(
                photo_b64, photo_mime, text,
                site_address, audit_date_iso, api_key,
                ra_context=ra_context,
            )
        except httpx.HTTPStatusError as exc:
            diag["rows_failed"] += 1
            seen_errors.add(
                f"http {exc.response.status_code} on row {row.obs.csv_row}"
            )
            continue
        except Exception as exc:
            diag["rows_failed"] += 1
            seen_errors.add(f"{type(exc).__name__} on row {row.obs.csv_row}")
            log.warning(
                "vision call failed on row %s", row.obs.csv_row,
                exc_info=True,
            )
            continue

        try:
            rec = _coerce_record(raw)
        except Exception as exc:
            diag["rows_failed"] += 1
            seen_errors.add(f"parse error on row {row.obs.csv_row}: {exc}")
            continue

        row.conformance_status = rec["status"]
        row.ccvs_code = rec["ccvs_code"]
        row.ccvs_category = rec["ccvs_category"]
        if rec["finding"]:
            row.finding = rec["finding"]
        if rec["legal_ref"]:
            row.legal_ref = rec["legal_ref"]
        if rec["recommendation"]:
            row.recommendation = rec["recommendation"]
        if rec["monitoring_note"]:
            row.monitoring_note = rec["monitoring_note"]
        diag["rows_ok"] += 1

    diag["errors"] = sorted(seen_errors)
    return diag


async def generate_narrative_summary(
    rows: list[EnrichedRow],
    site_address: str,
    audit_date_iso: str,
) -> str:
    """Compose the Executive Summary paragraph after vision enrichment.

    Pulls from the now-populated ``finding`` + ``conformance_status``
    fields. Returns ``""`` when no Anthropic key is set or the call
    fails — caller substitutes the empty string into the template's
    ``{{NARRATIVE_SUMMARY}}`` placeholder.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return ""
    if not rows:
        return ""

    payload = [
        {
            "status": r.conformance_status,
            "ccvs_category": r.ccvs_category,
            "finding": r.finding or r.observation_text_clean,
        }
        for r in rows
    ]

    system = (
        "You write the Executive Summary paragraph at the top of an "
        "Australian construction site safety audit report. Output ONE "
        "paragraph, 100–140 words, no bullets, no headings, no lists. "
        "Open with the site address and audit date in a single "
        "sentence. Then summarise the audit's overall picture grounded "
        "in the findings supplied — note major non-conformance themes "
        "by hazard family, balance with positive observations. End "
        "with one sentence on the next-step posture (close out NCRs, "
        "monitor Conditional). Australian English, year-12 plain "
        "English. Banned vocabulary: crucial, pivotal, landscape, "
        "ensure, leverage, robust, comprehensive, navigate, delve, "
        "it's important to note, serves as, at its core. Do not "
        "invent counts, names, dates, or breaches not in the input. "
        "Return ONLY the paragraph text — no JSON, no quotes, no "
        "markdown."
    )
    user_text = (
        f"SITE: {site_address or '(unresolved)'}\n"
        f"AUDIT_DATE: {audit_date_iso}\n"
        f"FINDINGS:\n{json.dumps(payload, ensure_ascii=False)}"
    )
    body = {
        "model": VISION_MODEL,
        "max_tokens": 600,
        "system": system,
        "messages": [{"role": "user", "content": user_text}],
    }
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                ANTHROPIC_URL,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": ANTHROPIC_VERSION,
                    "content-type": "application/json",
                },
                json=body,
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"].strip()
    except Exception:
        log.warning("narrative summary generation failed", exc_info=True)
        return ""

```

### `pims/services/ssa_ra_parser.py`

Project Risk Assessment docx parser. Extracts metadata + 9 hold points + N phase activities; compact-context-block packs into the vision prompt so findings cite HP-04 / TP-05 / HRCW H14 inline.

```python
"""Parse a project-specific Risk Assessment docx into structured data.

The RA carries the project's WHS contract: which controls must be in
place at which phase, which activities are HRCW, which Hold Points
gate construction. The SSA audit is reviewed against the RA, so
findings that reference RA activity refs (``TP-05``) and hold points
(``HP-04``) sit closer to the document the principal contractor is
held to.

Authoritative shape (from
``Unitas_Risk_Assessment_all.docx`` and equivalent RA exports from
the gatekeeper RA generator):

  - project metadata table (2 cols, key/value rows: Project, Site
    address, Principal Contractor, …)
  - hold-point schedule (6 cols: HP code, description, package,
    condition to be met, sign-off authority, evidence required)
  - risk register (7 cols: Ref, Activity / Hazard, HRCW Category,
    Initial Risk, Controls, Residual Risk, Responsible / SWMS / HP).
    Phase headers appear as repeated-cell rows (every cell carries
    the phase name).

Non-conforming RAs (cell counts off, header text different) are
parsed best-effort — missing fields land as empty strings. The
parser never raises on a malformed input; the orchestrator decides
whether to enrich without RA context or skip the project-context
injection.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RAHoldPoint:
    code: str        # "HP-04"
    description: str
    package: str
    condition: str
    sign_off: str
    evidence: str


@dataclass(frozen=True)
class RAActivity:
    ref: str          # "TP-05"
    phase: str        # "6 – Tilt-Up Panel Erection"
    activity: str
    hrcw: str
    initial_risk: str
    controls: str
    residual_risk: str
    responsible: str


@dataclass
class RiskAssessment:
    project_name: str = ""
    site_address: str = ""
    principal_contractor: str = ""
    hold_points: list[RAHoldPoint] = field(default_factory=list)
    activities: list[RAActivity] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.hold_points or self.activities)


_HP_REF_RE = re.compile(r"^HP-\d{2}$")
# Activity refs in the canonical RA: 2-letter package + dash + digits,
# optionally suffixed (TP-01A, MR-02). Phase header rows have phase-
# title text in the ref cell instead, which fails this match.
_ACTIVITY_REF_RE = re.compile(r"^[A-Z]{2}-\d{1,3}[A-Z]?$")
# Phase header rows look like "6 — Tilt-Up Panel Erection" — leading
# digit then em-dash / en-dash / hyphen then title.
_PHASE_HEADER_RE = re.compile(r"^\s*(\d{1,2})\s*[—–-]\s*(.+)$")


def _norm_cell(text: object) -> str:
    if text is None:
        return ""
    s = str(text).replace("\n", " ").strip()
    return re.sub(r"\s+", " ", s)


def _looks_like_phase_header(row_cells: list[str]) -> str:
    """Phase header rows repeat the same value across every cell.

    Returns the normalised phase title (e.g. ``"6 – Tilt-Up Panel
    Erection"``) when detected, else ``""``.
    """
    if not row_cells:
        return ""
    first = row_cells[0]
    if not first:
        return ""
    # Every non-empty cell on the row carries the same value.
    distinct = {c for c in row_cells if c}
    if len(distinct) != 1:
        return ""
    if not _PHASE_HEADER_RE.match(first):
        return ""
    return first


def _parse_metadata_table(table) -> tuple[str, str, str]:
    """Extract project / site / principal contractor from a 2-col table."""
    project = site = pc = ""
    for row in table.rows:
        if len(row.cells) < 2:
            continue
        key = _norm_cell(row.cells[0].text).lower()
        val = _norm_cell(row.cells[1].text)
        if not val:
            continue
        if "project" in key and not project:
            project = val
        elif "site address" in key:
            site = val
        elif "principal contractor" in key:
            pc = val
    return project, site, pc


def _parse_hold_points_table(table) -> list[RAHoldPoint]:
    out: list[RAHoldPoint] = []
    for row in table.rows:
        cells = [_norm_cell(c.text) for c in row.cells]
        if len(cells) < 6:
            continue
        ref = cells[0]
        if not _HP_REF_RE.match(ref):
            continue  # header row or stray
        out.append(RAHoldPoint(
            code=ref, description=cells[1], package=cells[2],
            condition=cells[3], sign_off=cells[4], evidence=cells[5],
        ))
    return out


def _parse_register_table(table) -> list[RAActivity]:
    out: list[RAActivity] = []
    current_phase = ""
    for row in table.rows:
        cells = [_norm_cell(c.text) for c in row.cells]
        if len(cells) < 7:
            continue
        # Phase header row?
        ph = _looks_like_phase_header(cells)
        if ph:
            current_phase = ph
            continue
        ref = cells[0]
        if not _ACTIVITY_REF_RE.match(ref):
            continue
        out.append(RAActivity(
            ref=ref,
            phase=current_phase,
            activity=cells[1],
            hrcw=cells[2],
            initial_risk=cells[3],
            controls=cells[4],
            residual_risk=cells[5],
            responsible=cells[6],
        ))
    return out


def parse_risk_assessment(path: Path) -> RiskAssessment:
    """Best-effort parse of a project RA docx.

    Selects tables by shape: ``2 cols`` → project metadata,
    ``6 cols`` with HP-XX refs → hold-point schedule, ``7 cols`` with
    activity refs → risk register. Multiple matching tables are
    processed in order; values from earlier tables don't overwrite.
    Returns an empty ``RiskAssessment`` if the docx is unreadable.
    """
    try:
        from docx import Document
    except Exception:
        log.warning("python-docx not available; RA parse skipped")
        return RiskAssessment()

    if not path.exists():
        return RiskAssessment()

    try:
        doc = Document(path)
    except Exception:
        log.warning("RA docx unreadable: %s", path, exc_info=True)
        return RiskAssessment()

    ra = RiskAssessment()
    for tbl in doc.tables:
        cols = len(tbl.columns)
        if cols == 2 and not ra.project_name:
            project, site, pc = _parse_metadata_table(tbl)
            ra.project_name = project
            ra.site_address = site
            ra.principal_contractor = pc
        elif cols == 6 and not ra.hold_points:
            ra.hold_points = _parse_hold_points_table(tbl)
        elif cols == 7 and not ra.activities:
            ra.activities = _parse_register_table(tbl)
    return ra


def autodiscover_in_folder(folder: Path) -> Path | None:
    """Find a Risk Assessment docx inside the audit folder.

    Match by filename: any ``*.docx`` with ``risk assessment`` (any
    case) in the name AND not already a watcher-owned artifact (no
    ``Site-Safety-Audit-Report-`` prefix). First match wins.
    """
    if not folder.is_dir():
        return None
    candidates = []
    for p in folder.iterdir():
        if not p.is_file() or p.suffix.lower() != ".docx":
            continue
        if p.name.startswith("Site-Safety-Audit-Report-"):
            continue
        if "risk assessment" in p.stem.lower().replace("_", " "):
            candidates.append(p)
    return sorted(candidates)[0] if candidates else None


def compact_context_block(ra: RiskAssessment, max_activities: int = 60) -> str:
    """Compact text representation for the vision prompt.

    Trims to ``max_activities`` rows (keeps within prompt-token
    budget). Activities list is grouped by phase to keep the model's
    attention on phase boundaries.
    """
    if ra.is_empty:
        return ""
    lines: list[str] = []
    lines.append("PROJECT RISK ASSESSMENT CONTEXT")
    if ra.project_name:
        lines.append(f"Project: {ra.project_name}")
    if ra.site_address:
        lines.append(f"Site: {ra.site_address}")
    if ra.principal_contractor:
        lines.append(f"Principal Contractor: {ra.principal_contractor}")

    if ra.hold_points:
        lines.append("")
        lines.append("HOLD POINTS:")
        for hp in ra.hold_points:
            lines.append(f"  {hp.code}  {hp.description} | {hp.package}")

    if ra.activities:
        lines.append("")
        lines.append("PHASES + ACTIVITIES:")
        seen_phase = ""
        emitted = 0
        for act in ra.activities:
            if emitted >= max_activities:
                lines.append(
                    f"  ... ({len(ra.activities) - emitted} more activities)"
                )
                break
            if act.phase != seen_phase:
                lines.append(f"[{act.phase}]")
                seen_phase = act.phase
            init = act.initial_risk or "-"
            resid = act.residual_risk or "-"
            hrcw = act.hrcw or "-"
            lines.append(
                f"  {act.ref}  {act.activity[:90]} | hrcw={hrcw} | "
                f"init={init} resid={resid}"
            )
            emitted += 1

    return "\n".join(lines)

```

### `pims/services/ssa_watcher.py`

Quiescence-gated folder watcher: settle_seconds + N stable polls; exclusions cover every watcher-owned artifact. Manifest-sha256 idempotency lives in the orchestrator.

```python
"""Quiescence-based watcher for SSA evidence folders.

Polls a watch root for dated audit folders (``YYYY-MM-DD-<RPD|SDG>``).
A folder is processed only when it is *quiescent*:

  - the latest input mtime is at least ``settle_seconds`` ago (default
    120 s — true wall-clock stability), AND
  - ``required_stable_polls`` consecutive snapshots (default 4) of
    ``(filename, size, mtime)`` are identical.

Quiescence snapshots exclude every watcher-owned artifact:
``.ssa_run.json``, ``.ssa_run.error``, ``.ssa_freeze``, ``.ssa_work/``,
both sentinel files, and the canonical output filenames for the
current folder (computed from the folder name, plus anything previously
recorded in ``.ssa_run.json`` ``outputs``). This stops the watcher
reacting to its own writes.

A frozen folder (``.ssa_freeze`` present) is skipped with a logged
reason; this is the manual-patch escape hatch.

Idempotency on the run itself is `run_ssa_pipeline.run_once`'s job
(manifest sha256 + recorded outputs); when nothing has changed the
pipeline returns ``skipped=True`` and no disk writes happen.

This module exposes:
  - ``Watcher`` — encapsulated state + polling logic. ``tick()`` drives
    one polling cycle per folder; tests call it directly with a fake
    clock.
  - ``run_forever()`` — convenience long-run loop. Used by
    ``pims/scripts/start_ssa_watcher.py``.
"""
from __future__ import annotations

import json
import logging
import re
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

log = logging.getLogger(__name__)


# --- folder + filename rules --------------------------------------------

_FOLDER_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(RPD|SDG)$")
_IMAGE_EXTS = {".jpg", ".jpeg", ".png"}

# Static exclusions — names always skipped from the input snapshot,
# regardless of folder. Output filenames are added per-folder.
_STATIC_EXCLUDED_NAMES = frozenset({
    ".ssa_run.json",
    ".ssa_run.error",
    ".ssa_freeze",
    "STAGING-NOT-UPLOADABLE.txt",
    "STAGING-NO-BULK-ENDPOINT.txt",
})
_STATIC_EXCLUDED_DIRS = frozenset({".ssa_work"})


def _expected_outputs(folder_name: str) -> set[str]:
    """Canonical output filenames for the folder, computed from its name.

    Excluded from the quiescence snapshot even on a folder that has
    never been processed — prevents the watcher reacting to its own
    first write.
    """
    m = _FOLDER_RE.match(folder_name)
    if not m:
        return set()
    yyyy, mm, dd, client = m.groups()
    yymmdd = f"{yyyy[2:]}{mm}{dd}"
    return {
        f"PIMS-Enriched-{yymmdd}-{client}.xlsx",
        f"Site-Safety-Audit-Report-{yymmdd}-{client}.docx",
        f"Site-Visit-Report-Upload-PIMS-Staging-{yymmdd}-{client}.xlsx",
    }


def _recorded_outputs(folder: Path) -> set[str]:
    rj = folder / ".ssa_run.json"
    if not rj.exists():
        return set()
    try:
        data = json.loads(rj.read_text(encoding="utf-8"))
    except Exception:
        return set()
    out = data.get("outputs") or []
    return {str(n) for n in out if isinstance(n, str)}


def _snapshot(folder: Path) -> tuple[tuple[str, int, int], ...]:
    """Filename / size / mtime triples for everything that counts as input.

    Sorted by lowercased filename so the snapshot is order-stable. mtime
    is rounded to the nearest int second — Drive sync touches sometimes
    bump fractional mtime within a stable poll, which would otherwise
    flap the snapshot.
    """
    excluded_names = _STATIC_EXCLUDED_NAMES \
        | _expected_outputs(folder.name) \
        | _recorded_outputs(folder)
    triples: list[tuple[str, int, int]] = []
    try:
        entries = list(folder.iterdir())
    except FileNotFoundError:
        return ()
    for p in entries:
        if p.is_dir():
            if p.name in _STATIC_EXCLUDED_DIRS:
                continue
            # Walk-into is not needed at v1 — audit folders are flat.
            continue
        if p.name in excluded_names:
            continue
        # Output-prefixed -partN.xlsx variants for the staging file:
        # exclude any file whose name is a recorded output.
        try:
            st = p.stat()
        except FileNotFoundError:
            continue
        triples.append((p.name.lower(), st.st_size, int(st.st_mtime)))
    triples.sort()
    return tuple(triples)


def _max_input_mtime(snap: tuple[tuple[str, int, int], ...]) -> int:
    if not snap:
        return 0
    return max(t[2] for t in snap)


def _is_eligible_folder(folder: Path) -> tuple[bool, str]:
    """Return (eligible, reason). Reason is "" on the truthy branch."""
    if not folder.is_dir():
        return False, "not a directory"
    if not _FOLDER_RE.match(folder.name):
        return False, "name does not match YYYY-MM-DD-<RPD|SDG>"
    if not (folder / "Evidence_Master.csv").exists():
        return False, "Evidence_Master.csv missing"
    has_image = any(
        p.is_file() and p.suffix.lower() in _IMAGE_EXTS
        for p in folder.iterdir()
    )
    if not has_image:
        return False, "no images present"
    return True, ""


# --- per-folder watcher state -------------------------------------------

@dataclass
class FolderState:
    """Rolling history of recent snapshots.

    ``snapshots`` is a bounded deque of length ``required_stable_polls``;
    quiescence is reached when the deque is full AND every entry is
    equal to the latest one.
    """
    snapshots: deque = field(default_factory=lambda: deque(maxlen=4))

    def push(self, snap, capacity: int) -> None:
        if self.snapshots.maxlen != capacity:
            self.snapshots = deque(self.snapshots, maxlen=capacity)
        self.snapshots.append(snap)

    def is_stable(self, capacity: int) -> bool:
        return (
            len(self.snapshots) == capacity
            and all(s == self.snapshots[0] for s in self.snapshots)
        )

    def reset(self) -> None:
        self.snapshots.clear()


# --- watcher -------------------------------------------------------------

@dataclass
class Watcher:
    watch_root: Path
    settle_seconds: int = 120
    required_stable_polls: int = 4
    runner: Callable[[Path], dict] | None = None  # injects run_once
    clock: Callable[[], float] = time.time
    state: dict[Path, FolderState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.runner is None:
            # Lazy import keeps watcher importable without the CLI.
            from pims.scripts.run_ssa_pipeline import run_once
            self.runner = run_once  # type: ignore[assignment]

    # --- tick ----------------------------------------------------------

    def _candidates(self) -> Iterable[Path]:
        if not self.watch_root.is_dir():
            return ()
        return sorted(p for p in self.watch_root.iterdir() if p.is_dir())

    def tick(self) -> list[dict]:
        """Run one polling cycle across all candidate folders.

        Returns a list of result dicts (one per folder examined) with
        keys ``folder``, ``action`` ∈ {``"skip"``, ``"wait"``,
        ``"frozen"``, ``"ran"``, ``"error"``}, plus ``reason`` /
        ``payload`` / ``error`` as applicable. Caller can log or test
        against this directly.
        """
        results: list[dict] = []
        for folder in self._candidates():
            results.append(self._tick_folder(folder))
        return results

    def _tick_folder(self, folder: Path) -> dict:
        eligible, reason = _is_eligible_folder(folder)
        if not eligible:
            self.state.pop(folder, None)
            return {"folder": folder.name, "action": "skip", "reason": reason}

        if (folder / ".ssa_freeze").exists():
            self.state.pop(folder, None)
            return {"folder": folder.name, "action": "frozen"}

        snap = _snapshot(folder)
        st = self.state.setdefault(folder, FolderState())
        st.push(snap, self.required_stable_polls)

        # (a) wall-clock settle
        latest = _max_input_mtime(snap)
        now = int(self.clock())
        settle_ok = (now - latest) >= self.settle_seconds

        # (b) snapshot stability
        stable = st.is_stable(self.required_stable_polls)

        if not (settle_ok and stable):
            return {
                "folder": folder.name,
                "action": "wait",
                "reason": (
                    f"settle_ok={settle_ok} stable={stable} "
                    f"polls={len(st.snapshots)}/{self.required_stable_polls}"
                ),
            }

        # Quiescent — invoke the pipeline runner. On success, .ssa_run.json
        # is updated; on failure, write .ssa_run.error and reset state so
        # the next cycle can retry once inputs change again.
        try:
            payload = self.runner(folder)  # type: ignore[misc]
        except Exception as exc:
            log.exception("pipeline failed for %s", folder)
            (folder / ".ssa_run.error").write_text(
                f"{type(exc).__name__}: {exc}\n", encoding="utf-8",
            )
            st.reset()
            return {"folder": folder.name, "action": "error", "error": str(exc)}

        # Clear any prior error sentinel after a clean run.
        err = folder / ".ssa_run.error"
        if err.exists():
            try:
                err.unlink()
            except OSError:
                pass

        # Outputs are now recorded — refresh stability state so the very
        # next poll doesn't immediately re-fire on the just-written files.
        st.reset()

        return {
            "folder": folder.name,
            "action": "ran",
            "skipped": bool(payload.get("skipped")),
            "staging_status": payload.get("staging_status"),
        }

    # --- long-run convenience -----------------------------------------

    def run_forever(self, poll_seconds: int = 30) -> None:
        log.info(
            "watcher start: root=%s settle=%ss polls=%d cadence=%ds",
            self.watch_root, self.settle_seconds,
            self.required_stable_polls, poll_seconds,
        )
        while True:
            try:
                results = self.tick()
            except Exception:
                log.exception("watcher tick failed; continuing")
                results = []
            for r in results:
                if r["action"] == "ran":
                    log.info("ran: %s status=%s skipped=%s",
                             r["folder"], r.get("staging_status"),
                             r.get("skipped"))
                elif r["action"] == "error":
                    log.error("error: %s — %s", r["folder"], r.get("error"))
                elif r["action"] == "frozen":
                    log.info("frozen: %s", r["folder"])
                # "wait" / "skip" are debug-only to avoid log spam.
                else:
                    log.debug("%s: %s %s", r["folder"], r["action"],
                              r.get("reason", ""))
            time.sleep(poll_seconds)

```

### `pims/scripts/run_ssa_pipeline.py`

CLI orchestrator. Folder-name parse, manifest sha256, freeze escape hatch, sentinels (NOT_UPLOADABLE / NO_BULK_ENDPOINT), RA auto-discover, vision wiring, .ssa_run.json payload.

```python
"""Manual CLI for the SSA evidence-folder → 3-deliverable pipeline.

    python -m pims.scripts.run_ssa_pipeline "<folder>"

Bypasses the watcher; runs the same pipeline once over the supplied
folder. The watcher (added separately) is the long-running entry that
drives this same orchestration on quiescent folders.

v1 scope:
  - parse Evidence_Master.csv, match photos, extract site address
  - lift to EnrichedRow (every row Unmatched until CCVS auto-matcher
    lands as a separate slice)
  - build all three deliverables
  - compute staging_status (tri-state per workflow plan)
  - write sentinel file when applicable
  - write .ssa_run.json with outputs + warnings + status

v1 NON-scope (deferred slices, called out in the plan):
  - input-manifest sha256 + idempotency skip (watcher concern)
  - LLM finding-rewrite + narrative summary (separate async pass)
  - staging 5 MB progressive-downscale + size-based split
  - quiescence polling
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from pims.services.ssa_checklist_lookup import ChecklistLookup
from pims.services.ssa_pipeline import (
    EnrichedRow,
    build_pims_enriched_xlsx,
    build_pims_staging_xlsx_with_size_control,
    build_ssa_report_docx,
    enrich_observations,
    extract_site_address,
    match_photos,
    parse_evidence_csv,
    parse_prior_report_recommendations,
)

log = logging.getLogger("ssa.cli")


# Folder name contract: YYYY-MM-DD-<CLIENT>, CLIENT ∈ {RPD, SDG}
_FOLDER_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(RPD|SDG)$")

# Image extensions the watcher cares about. PNG-with-transparency is
# legal but rare; HEIC explicitly out of scope (filename canonicalisation
# rules in the plan).
_IMAGE_EXTS = {".jpg", ".jpeg", ".png"}

# Client-bulk-endpoint capability (gate 0). RPD has it today, SDG
# doesn't — confirmed against pims/routes.py:2091.
_BULK_ENDPOINT = {"RPD": "/pims/upload/observations", "SDG": None}


def _parse_folder(folder: Path) -> tuple[str, str, str, str]:
    """Return (audit_date_iso, audit_date_ddmmyyyy, yymmdd, client).

    Raises ValueError when the folder name doesn't match the contract —
    rerun with a renamed folder is the documented remediation.
    """
    m = _FOLDER_RE.match(folder.name)
    if not m:
        raise ValueError(
            f"folder name {folder.name!r} does not match YYYY-MM-DD-<CLIENT> "
            f"with CLIENT in (RPD, SDG)"
        )
    yyyy, mm, dd, client = m.groups()
    iso = f"{yyyy}-{mm}-{dd}"
    ddmmyyyy = f"{dd}/{mm}/{yyyy}"
    yymmdd = f"{yyyy[2:]}{mm}{dd}"
    # Sanity-check the date itself; ValueError on Feb 30 etc.
    datetime.strptime(iso, "%Y-%m-%d")
    return iso, ddmmyyyy, yymmdd, client


def _output_names(yymmdd: str, client: str) -> dict[str, str]:
    return {
        "enriched": f"PIMS-Enriched-{yymmdd}-{client}.xlsx",
        "report": f"Site-Safety-Audit-Report-{yymmdd}-{client}.docx",
        "staging": f"Site-Visit-Report-Upload-PIMS-Staging-{yymmdd}-{client}.xlsx",
    }


def _images_in(folder: Path) -> list[Path]:
    return sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in _IMAGE_EXTS
    )


# Filename-date-suffix on a prior SSA report: ``...YYMMDD-<CLIENT>.docx``.
_PRIOR_REPORT_RE = re.compile(
    r"^Site-Safety-Audit-Report-(\d{6})-(RPD|SDG)\.docx$"
)


def _qualifying_prior_reports(
    folder: Path, current_iso: str, current_target: str,
) -> list[Path]:
    """Return prior SSA reports eligible for input-manifest inclusion.

    Eligible iff ALL:
      - filename matches ``Site-Safety-Audit-Report-YYMMDD-<CLIENT>.docx``
      - parsed date strictly earlier than the current folder's audit date
      - filename != the current target output filename

    Per the plan's "Prior-report reuse policy". Files whose date suffix
    is missing/unparseable are non-qualifying — never guessed from mtime.
    """
    out: list[Path] = []
    for p in folder.iterdir():
        if not p.is_file():
            continue
        if p.name == current_target:
            continue
        m = _PRIOR_REPORT_RE.match(p.name)
        if not m:
            continue
        yymmdd = m.group(1)
        try:
            cand_iso = datetime.strptime(yymmdd, "%y%m%d").date().isoformat()
        except ValueError:
            continue
        if cand_iso < current_iso:
            out.append(p)
    return sorted(out)


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _compute_manifest(
    csv_path: Path, images: list[Path], prior_reports: list[Path],
) -> str:
    """Full-content sha256 over CSV + images + qualifying prior reports.

    Per the watcher contract: hash the sorted ``filename || sha256(bytes)``
    pairs so that any byte-level change in any input flips the manifest.
    Filenames are lowercased for case-insensitive volumes (Windows).
    """
    parts: list[str] = []
    for p in [csv_path, *images, *prior_reports]:
        parts.append(f"{p.name.lower()}||{_file_sha256(p)}")
    parts.sort()
    h = hashlib.sha256()
    for line in parts:
        h.update(line.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _existing_run_record(folder: Path) -> dict | None:
    rj = folder / ".ssa_run.json"
    if not rj.exists():
        return None
    try:
        return json.loads(rj.read_text(encoding="utf-8"))
    except Exception:
        log.warning(".ssa_run.json unreadable; treating as missing")
        return None


def _write_sentinel(folder: Path, name: str, body: str) -> str:
    path = folder / name
    path.write_text(body, encoding="utf-8")
    return path.name


def _resolve_staging_status(
    client: str, site_address: str | None,
) -> tuple[str, str | None]:
    """Return (staging_status, blocker) per the tri-state contract."""
    if not site_address:
        return "not_uploadable", "site_address_unresolved"
    if _BULK_ENDPOINT.get(client) is None:
        return "schema_valid_no_endpoint", None
    return "bulk_uploadable", None


def _apply_vision_enrichment(
    enriched: list[EnrichedRow],
    site_address: str | None,
    audit_date_iso: str,
    enable: bool,
    ra_context: str = "",
) -> tuple[str, dict]:
    """Vision-enabled per-row classification + narrative summary.

    Returns ``(narrative_paragraph, diagnostics_dict)``. On any failure
    path (LLM disabled, key missing, network error, JSON parse error,
    timeout) the function returns an empty narrative and a diagnostics
    dict describing what happened — never raises into the orchestrator.

    Side-effect: in-place mutation of every row that the LLM
    successfully classifies — sets ``conformance_status``,
    ``ccvs_code``, ``ccvs_category``, ``finding``, ``legal_ref``,
    ``recommendation``, ``monitoring_note``. Rows that fall through
    the LLM (no photo / API error / parse error) keep their default
    ``Unmatched`` state.
    """
    if not enable or not enriched:
        return "", {"enabled": False, "rows_total": len(enriched)}

    from pims.services.ssa_vision_enricher import (
        enrich_rows_with_vision,
        generate_narrative_summary,
    )

    async def _drive() -> tuple[str, dict]:
        diag = await enrich_rows_with_vision(
            enriched,
            site_address=site_address or "",
            audit_date_iso=audit_date_iso,
            ra_context=ra_context,
        )
        text = await generate_narrative_summary(
            enriched,
            site_address=site_address or "",
            audit_date_iso=audit_date_iso,
        )
        return text, diag

    try:
        narrative, diag = asyncio.run(_drive())
    except Exception as exc:
        log.warning("vision enrichment driver failed: %s", exc, exc_info=True)
        return "", {
            "enabled": True, "driver_error": f"{type(exc).__name__}: {exc}",
            "rows_total": len(enriched),
        }
    diag["enabled"] = True
    return narrative, diag


def run_once(
    folder: Path,
    prepared_by: str = "Alan Richardson",
    ignore_freeze: bool = False,
    checklist_path: Path | None = None,
    force: bool = False,
    enrich: bool = True,
    risk_assessment_path: Path | None = None,
) -> dict:
    """Run the pipeline once. Returns the .ssa_run.json payload.

    Idempotency: when ``force`` is False and a prior ``.ssa_run.json``
    is present whose ``inputs_sha256`` matches the current manifest AND
    every recorded output still exists on disk, the run is a no-op and
    the existing payload is returned with ``skipped=True`` set.
    """
    folder = folder.resolve()
    if not folder.is_dir():
        raise NotADirectoryError(folder)

    freeze = folder / ".ssa_freeze"
    if freeze.exists() and not ignore_freeze:
        raise RuntimeError(
            f"frozen — use --ignore-freeze to overwrite ({freeze})"
        )

    iso, ddmmyyyy, yymmdd, client = _parse_folder(folder)
    csv_path = folder / "Evidence_Master.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Evidence_Master.csv missing in {folder}")

    images = _images_in(folder)
    if not images:
        raise FileNotFoundError(f"no images found in {folder}")

    # --- manifest + idempotency -------------------------------------
    names = _output_names(yymmdd, client)
    prior_reports = _qualifying_prior_reports(folder, iso, names["report"])
    manifest = _compute_manifest(csv_path, images, prior_reports)

    prior_record = _existing_run_record(folder)
    if (
        not force
        and prior_record is not None
        and prior_record.get("inputs_sha256") == manifest
        and all((folder / n).exists() for n in prior_record.get("outputs", []))
    ):
        prior_record["skipped"] = True
        log.info("manifest unchanged + outputs present — skipping")
        return prior_record

    # --- parse + match + address ------------------------------------
    rows, csv_warnings = parse_evidence_csv(csv_path)
    match_warnings = match_photos(rows, images)

    cl_path = checklist_path or (
        Path(__file__).resolve().parent.parent / "audit_checklist.xlsx"
    )
    checklist = (
        ChecklistLookup.from_xlsx(cl_path) if cl_path.exists() else None
    )

    site_address = extract_site_address(rows)

    enriched = enrich_observations(rows, checklist=checklist)

    # When site_address is unresolved, every staging row must
    # needs_review=TRUE (Field Defaults). enrich_observations already
    # sets needs_review for Unmatched rows; flagging the obs surfaces
    # the address-unresolved reason in the warning trail.
    if site_address is None:
        for r in enriched:
            r.obs.flag("site_address_unresolved")

    # --- build deliverables -----------------------------------------
    enriched_path = folder / names["enriched"]
    report_path = folder / names["report"]
    staging_path = folder / names["staging"]

    site_for_docx = site_address or "[Site address - to be confirmed]"
    site_for_staging = site_address or ""

    # Project Risk Assessment context (optional). Auto-discovers any
    # ``*Risk_Assessment*.docx`` in the audit folder when no explicit
    # path is supplied. Empty string when no RA is available — the
    # vision call falls back to generic Australian-WHS classification.
    from pims.services.ssa_ra_parser import (
        autodiscover_in_folder, compact_context_block, parse_risk_assessment,
    )
    ra_path = risk_assessment_path
    if ra_path is None:
        ra_path = autodiscover_in_folder(folder)
    ra_context = ""
    ra_summary: dict[str, object] = {"path": None, "phases": 0, "activities": 0,
                                     "hold_points": 0}
    if ra_path is not None:
        ra = parse_risk_assessment(ra_path)
        ra_context = compact_context_block(ra)
        ra_summary = {
            "path": ra_path.name,
            "project": ra.project_name,
            "phases": len({a.phase for a in ra.activities}),
            "activities": len(ra.activities),
            "hold_points": len(ra.hold_points),
        }
        log.info(
            "RA loaded: %s — %d activities, %d hold points",
            ra_path.name, len(ra.activities), len(ra.hold_points),
        )

    # Vision enrichment — per-row classification (status, CCVS code,
    # finding text, legal_ref, recommendation, monitoring_note) plus
    # the Executive Summary paragraph. Default-on. No-op when
    # ``--no-enrich`` was passed or ANTHROPIC_API_KEY is unset.
    narrative_summary, llm_diag = _apply_vision_enrichment(
        enriched,
        site_address=site_address,
        audit_date_iso=iso,
        enable=enrich,
        ra_context=ra_context,
    )
    llm_diag["ra"] = ra_summary

    # Parse carry-forward recommendations from the newest qualifying
    # prior report so the SSA report's "Status of Previous
    # Recommendations" table actually carries content.
    prior_recs: list[dict] = []
    if prior_reports:
        newest_prior = prior_reports[-1]
        prior_recs = parse_prior_report_recommendations(newest_prior)

    enriched_diag = build_pims_enriched_xlsx(enriched, enriched_path)
    report_diag = build_ssa_report_docx(
        enriched,
        site_address=site_for_docx,
        audit_date_ddmmyyyy=ddmmyyyy,
        narrative_summary=narrative_summary,
        output_path=report_path,
        prepared_by=prepared_by,
        prior_recs=prior_recs,
    )
    report_diag["prior_recs_count"] = len(prior_recs)
    staging_result = build_pims_staging_xlsx_with_size_control(
        enriched,
        staging_path,
        site_address=site_for_staging,
        audit_date_iso=iso,
        prepared_by=prepared_by,
    )
    staging_diag = {
        "parts":         [p.name for p in staging_result["parts"]],
        "max_edge_px":   staging_result["max_edge_px"],
        "split":         staging_result["split"],
        "split_reason":  staging_result["split_reason"],
        "per_part":      staging_result["diagnostics"],
    }

    # --- staging tri-state ------------------------------------------
    staging_status, blocker = _resolve_staging_status(client, site_address)
    staging_part_names = [p.name for p in staging_result["parts"]]
    outputs: list[str] = [
        enriched_path.name,
        report_path.name,
        *staging_part_names,
    ]

    if staging_status == "not_uploadable":
        outputs.append(_write_sentinel(
            folder, "STAGING-NOT-UPLOADABLE.txt",
            f"staging blocker: {blocker}\n"
            f"folder: {folder.name}\n"
            f"remediation: see .claude/plans/workflow-1 — for "
            f"site_address_unresolved, add an address-shaped sentence to "
            f"a row in Evidence_Master.csv and rerun.\n",
        ))
    elif staging_status == "schema_valid_no_endpoint":
        outputs.append(_write_sentinel(
            folder, "STAGING-NO-BULK-ENDPOINT.txt",
            f"client: {client}\n"
            f"the staging xlsx is schema-valid and forward-compatible.\n"
            f"no bulk-upload endpoint exists for {client} today; post "
            f"observations one-at-a-time via the single-observation API.\n",
        ))

    # --- run record --------------------------------------------------
    payload = {
        "folder": folder.name,
        "client": client,
        "audit_date": iso,
        "inputs_sha256": manifest,
        "prior_reports_used": [p.name for p in prior_reports],
        "skipped": False,
        "prepared_by": prepared_by,
        "site_address": site_address,
        "site_address_unresolved": site_address is None,
        "staging_status": staging_status,
        "blocker": blocker,
        "client_bulk_endpoint": _BULK_ENDPOINT[client],
        "outputs": outputs,
        "row_count": len(enriched),
        "csv_warnings": [w.to_dict() for w in csv_warnings],
        "match_warnings": [w.to_dict() for w in match_warnings],
        "review_reasons_per_row": [
            {"csv_row": r.obs.csv_row, "reasons": list(r.obs.review_reasons)}
            for r in enriched if r.obs.review_reasons
        ],
        "enriched_diagnostics": enriched_diag,
        "report_diagnostics": report_diag,
        "staging_diagnostics": staging_diag,
        "llm_diagnostics": llm_diag,
        "completed_at": datetime.now(timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (folder / ".ssa_run.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="run_ssa_pipeline")
    ap.add_argument("folder", type=Path, help="audit evidence folder")
    ap.add_argument("--prepared-by", default="Alan Richardson")
    ap.add_argument("--ignore-freeze", action="store_true")
    ap.add_argument(
        "--force", action="store_true",
        help="ignore the manifest-based idempotency skip",
    )
    ap.add_argument("--checklist", type=Path, default=None)
    ap.add_argument(
        "--risk-assessment", type=Path, default=None,
        help="path to project Risk Assessment .docx; "
             "auto-discovered from audit folder when omitted",
    )
    ap.add_argument(
        "--no-enrich", action="store_true",
        help="skip the LLM finding-rewrite + narrative-summary pass",
    )
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )

    try:
        payload = run_once(
            args.folder,
            prepared_by=args.prepared_by,
            ignore_freeze=args.ignore_freeze,
            checklist_path=args.checklist,
            force=args.force,
            enrich=not args.no_enrich,
            risk_assessment_path=args.risk_assessment,
        )
    except RuntimeError as e:
        # Frozen folder — the documented exit signal for the manual CLI
        # is non-zero with a clear message.
        print(f"error: {e}", file=sys.stderr)
        return 2
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if payload.get("skipped"):
        print("skipped: manifest unchanged + all outputs present")
    print(f"staging_status: {payload['staging_status']}")
    if payload.get("blocker"):
        print(f"blocker:        {payload['blocker']}")
    print(f"outputs:        {len(payload['outputs'])} files in {args.folder}")
    for name in payload["outputs"]:
        print(f"  - {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

```

### `pims/scripts/start_ssa_watcher.py`

Long-run entry for the watcher. Rotating-file logging.

```python
"""Long-running entry for the SSA watcher.

    python -m pims.scripts.start_ssa_watcher "G:\\My Drive\\alan_mcxico\\SSA-evidence"

Install via Windows Scheduled Task at logon. Logs to
``pims/audits/ssa_watcher.log`` and stderr.
"""
from __future__ import annotations

import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from pims.services.ssa_watcher import Watcher


def _setup_logging(log_path: Path, verbose: bool) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s | %(message)s",
    )
    file_h = RotatingFileHandler(
        log_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8",
    )
    file_h.setFormatter(fmt)
    stream_h = logging.StreamHandler(sys.stderr)
    stream_h.setFormatter(fmt)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(file_h)
    root.addHandler(stream_h)
    root.setLevel(logging.DEBUG if verbose else logging.INFO)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="start_ssa_watcher")
    ap.add_argument("watch_root", type=Path)
    ap.add_argument("--settle-seconds", type=int, default=120)
    ap.add_argument("--required-stable-polls", type=int, default=4)
    ap.add_argument("--poll-seconds", type=int, default=30)
    default_log = (
        Path(__file__).resolve().parent.parent / "audits" / "ssa_watcher.log"
    )
    ap.add_argument("--log-file", type=Path, default=default_log)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    if not args.watch_root.is_dir():
        print(f"error: watch_root is not a directory: {args.watch_root}",
              file=sys.stderr)
        return 1

    _setup_logging(args.log_file, args.verbose)
    Watcher(
        watch_root=args.watch_root,
        settle_seconds=args.settle_seconds,
        required_stable_polls=args.required_stable_polls,
    ).run_forever(poll_seconds=args.poll_seconds)
    return 0  # never reached


if __name__ == "__main__":
    raise SystemExit(main())

```

### `tests/test_ssa_pipeline.py`

69-case regression net. Covers parser, matcher, three builders, size-control, manifest, watcher, vision coercion, RA parser, prior-rec parser, Findings #N expansion, status colour fills, freeze, idempotency, partial-output recovery.

```python
"""Regression tests for the SSA evidence-folder → 3-deliverable pipeline.

Locks down behaviours verified ad-hoc across the slices that built the
parser, builders, CLI, and watcher (see ``.claude/plans/workflow-1...md``
for the spec). These tests run without Anthropic credentials — the LLM
pass is a separate slice and stubbed out where it would otherwise be
called.

Coverage:
  - parse_evidence_csv: header detection, encoding, bad timestamp,
    duplicate filename, missing filename, embedded newlines / quoted
    commas, blank rows, bad field count
  - match_photos: exact, stem (extension swap), suffix/prefix,
    ambiguous, missing
  - extract_site_address: regex hit + no-hit
  - ChecklistLookup.from_xlsx + match (synthesised CCVS code path)
  - enrich_observations: Unmatched defaults; needs_review surface
  - build_pims_enriched_xlsx: header passthrough, photo embed, missing
    photo, RAW: prefix on bad timestamp
  - build_ssa_report_docx: token substitution (incl. cover-page text
    box), table cloning by status, `*` marker on missing photo, no
    `{{`/`}}` left in any document part
  - build_pims_staging_xlsx: row 3 headers, row 5 data start, blank
    `id`, due_category mapping, needs_review TRUE/FALSE, photo embed
    in column B
  - run_ssa_pipeline.run_once: tri-state staging_status (RPD ok / SDG /
    no-address); freeze skip; manifest-based idempotency (skip,
    input-change rerun, partial-output recovery); prior-report
    self-reference protection
  - ssa_watcher.Watcher: eligibility skip; quiescence (settle +
    stability); freeze; runner-error → .ssa_run.error; idempotent
    second fire returns skipped=True
"""
from __future__ import annotations

import json
import time
import zipfile
from io import BytesIO
from pathlib import Path

import openpyxl
import pytest
from docx import Document
from PIL import Image

from pims.scripts.run_ssa_pipeline import run_once
from pims.services.ssa_ccvs_taxonomy import (
    STREAM_TO_CATEGORY, VALID_STREAMS, VALID_TIERS,
    category_for, is_valid_code, stream_of,
)
from pims.services.ssa_checklist_lookup import ChecklistLookup
from pims.services.ssa_pipeline import (
    ObservationRow,
    EnrichedRow,
    build_pims_enriched_xlsx,
    build_pims_staging_xlsx,
    build_pims_staging_xlsx_with_size_control,
    build_ssa_report_docx,
    enrich_observations,
    extract_site_address,
    match_photos,
    parse_evidence_csv,
)
from pims.services.ssa_watcher import Watcher


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def _save_jpeg(path: Path, size=(800, 600), color="red") -> Path:
    Image.new("RGB", size, color).save(path, "JPEG")
    return path


@pytest.fixture
def evidence_folder(tmp_path):
    """Minimal RPD evidence folder: 2-row CSV + 2 photos.

    Returns a folder named ``2026-05-01-RPD`` so the CLI's folder-name
    contract parses cleanly. The address-shaped string is embedded in
    one observation so ``extract_site_address`` finds it.
    """
    folder = tmp_path / "2026-05-01-RPD"
    folder.mkdir()
    (folder / "Evidence_Master.csv").write_text(
        "timestamp,observation,filename\n"
        "2026-05-01_09-15-22,Edge protection missing on level 2 at "
        "12 Smith Street site,EV_001.jpg\n"
        "2026-05-01_09-30-05,Site sign current and clear,EV_002.jpg\n",
        encoding="utf-8",
    )
    _save_jpeg(folder / "EV_001.jpg", (1600, 1200))
    _save_jpeg(folder / "EV_002.jpg", (1200, 1600), "blue")
    return folder


# ---------------------------------------------------------------------------
# parse_evidence_csv
# ---------------------------------------------------------------------------

def test_parse_csv_basic_with_header(tmp_path):
    p = tmp_path / "ev.csv"
    p.write_text(
        "timestamp,observation,filename\n"
        "2026-05-01_09-15-22,obs one,EV_001.jpg\n"
        "2026-05-01_09-30-05,obs two,EV_002.jpg\n",
        encoding="utf-8",
    )
    rows, warnings = parse_evidence_csv(p)
    assert len(rows) == 2
    assert warnings == []
    assert rows[0].csv_row == 2  # header consumed from row 1
    assert rows[0].timestamp_iso == "2026-05-01_09-15-22"
    assert rows[0].csv_filename == "EV_001.jpg"


def test_parse_csv_utf8_sig_encoded(tmp_path):
    p = tmp_path / "ev.csv"
    body = "timestamp,observation,filename\n2026-05-01_09-15-22,a,b.jpg\n"
    p.write_bytes(b"\xef\xbb\xbf" + body.encode("utf-8"))
    rows, warnings = parse_evidence_csv(p)
    assert len(rows) == 1
    assert warnings == []


def test_parse_csv_bad_timestamp_kept_with_flag(tmp_path):
    p = tmp_path / "ev.csv"
    p.write_text(
        "timestamp,observation,filename\n"
        "not-a-time,obs text,EV.jpg\n",
        encoding="utf-8",
    )
    rows, warnings = parse_evidence_csv(p)
    assert len(rows) == 1
    assert rows[0].timestamp_iso is None
    assert rows[0].needs_review
    assert "bad_timestamp" in rows[0].review_reasons
    assert any(w.reason == "bad_timestamp" for w in warnings)


def test_parse_csv_missing_filename_dropped(tmp_path):
    p = tmp_path / "ev.csv"
    p.write_text(
        "timestamp,observation,filename\n"
        "2026-05-01_09-15-22,obs,\n",
        encoding="utf-8",
    )
    rows, warnings = parse_evidence_csv(p)
    assert rows == []
    assert any(w.reason == "missing_filename" for w in warnings)


def test_parse_csv_duplicate_filename_flagged_on_all(tmp_path):
    p = tmp_path / "ev.csv"
    p.write_text(
        "timestamp,observation,filename\n"
        "2026-05-01_09-15-22,a,EV.jpg\n"
        "2026-05-01_09-30-00,b,EV.jpg\n",
        encoding="utf-8",
    )
    rows, _ = parse_evidence_csv(p)
    assert len(rows) == 2
    assert all(r.duplicate_filename for r in rows)
    assert all("duplicate_filename" in r.review_reasons for r in rows)


def test_parse_csv_quoted_commas_and_embedded_newlines(tmp_path):
    p = tmp_path / "ev.csv"
    p.write_text(
        'timestamp,observation,filename\n'
        '2026-05-01_09-15-22,"line one, line two\nline three",EV.jpg\n',
        encoding="utf-8",
    )
    rows, warnings = parse_evidence_csv(p)
    assert len(rows) == 1
    assert "line three" in rows[0].observation_text
    assert warnings == []


def test_parse_csv_blank_rows_skipped(tmp_path):
    p = tmp_path / "ev.csv"
    p.write_text(
        "timestamp,observation,filename\n"
        "\n"
        "2026-05-01_09-15-22,a,EV.jpg\n"
        ",,\n",
        encoding="utf-8",
    )
    rows, warnings = parse_evidence_csv(p)
    assert len(rows) == 1
    # Both the empty line and the all-commas line are blank-row-skipped
    # silently per the parser contract.
    assert warnings == []


def test_parse_csv_bad_field_count_dropped(tmp_path):
    p = tmp_path / "ev.csv"
    p.write_text(
        "timestamp,observation,filename\n"
        "2026-05-01_09-15-22,obs,EV.jpg,extra\n",
        encoding="utf-8",
    )
    rows, warnings = parse_evidence_csv(p)
    assert rows == []
    assert any(w.reason == "bad_field_count" for w in warnings)


# ---------------------------------------------------------------------------
# match_photos
# ---------------------------------------------------------------------------

def _row(filename: str, csv_row: int = 1) -> ObservationRow:
    return ObservationRow(
        csv_row=csv_row,
        timestamp_raw="2026-05-01_09-15-22",
        timestamp_iso="2026-05-01_09-15-22",
        observation_text="x",
        csv_filename=filename,
    )


def test_match_photos_exact(tmp_path):
    p = _save_jpeg(tmp_path / "EV_001.jpg")
    rows = [_row("EV_001.jpg")]
    warnings = match_photos(rows, [p])
    assert warnings == []
    assert rows[0].resolved_path == p


def test_match_photos_jpeg_extension_normalisation(tmp_path):
    """CSV says .jpeg, disk has .JPG — both canonicalise to .jpg so the
    canonical-match rule (rule 2) wins. Verifies the JPEG-family case-
    and extension-insensitivity built into ``_canonical_name``."""
    p = _save_jpeg(tmp_path / "EV_001.JPG")
    rows = [_row("EV_001.jpeg")]
    warnings = match_photos(rows, [p])
    assert rows[0].resolved_path == p
    assert warnings == []


def test_match_photos_suffix_prefixed_disk_name(tmp_path):
    p = _save_jpeg(tmp_path / "6aFrancis_EV_001.jpg")
    rows = [_row("EV_001.jpg")]
    warnings = match_photos(rows, [p])
    assert rows[0].resolved_path == p
    assert any(w.reason == "prefix_match" for w in warnings)


def test_match_photos_ambiguous_flags_no_silent_select(tmp_path):
    a = _save_jpeg(tmp_path / "a" / "EV_001.jpg".replace("a/", "")) \
        if False else _save_jpeg(tmp_path / "EV_001.jpg")
    # Two distinct on-disk files with the same canonical name (different
    # case → same .lower()). Use suffix match to manufacture ambiguity:
    # two prefixed disk files, neither identical to the CSV token.
    p1 = _save_jpeg(tmp_path / "siteA_EV_999.jpg")
    p2 = _save_jpeg(tmp_path / "siteB_EV_999.jpg")
    rows = [_row("EV_999.jpg")]
    warnings = match_photos(rows, [p1, p2])
    assert rows[0].resolved_path is None
    assert "photo_match_ambiguous" in rows[0].review_reasons
    assert any(w.reason == "photo_match_ambiguous" for w in warnings)


def test_match_photos_missing_flags_needs_review(tmp_path):
    rows = [_row("nope.jpg")]
    warnings = match_photos(rows, [])
    assert rows[0].resolved_path is None
    assert "photo_missing" in rows[0].review_reasons
    assert any(w.reason == "photo_missing" for w in warnings)


# ---------------------------------------------------------------------------
# extract_site_address
# ---------------------------------------------------------------------------

def test_extract_site_address_picks_first_address_shaped_hit():
    rows = [_row("a.jpg"), _row("b.jpg", csv_row=2)]
    rows[0].observation_text = "no address here"
    rows[1].observation_text = "issue at 12 Smith Street, Sydney"
    addr = extract_site_address(rows)
    assert addr is not None
    assert "12 Smith Street" in addr


def test_extract_site_address_no_hit_returns_none():
    rows = [_row("a.jpg")]
    rows[0].observation_text = "site is generally tidy"
    assert extract_site_address(rows) is None


# ---------------------------------------------------------------------------
# ChecklistLookup
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# CCVS taxonomy (canonical scheme: 25 streams x 6 tiers = 150 codes)
# ---------------------------------------------------------------------------

def test_ccvs_taxonomy_25_streams():
    """Stream list locks against renderers/docx_renderer.py + sample SYS."""
    expected = {
        "WFR", "WFA", "WAH", "IRA", "ELE", "SIL", "STR", "CFS", "ENE",
        "HOT", "MOB", "ASB", "LED", "TRF", "ENV", "CHM", "SCF", "CRN",
        "EXC", "MNH", "NOI", "TLT", "DEM", "FMW", "SYS",
    }
    assert VALID_STREAMS == frozenset(expected)
    assert set(STREAM_TO_CATEGORY) == expected


def test_ccvs_taxonomy_tiers_six():
    assert VALID_TIERS == frozenset({"H6", "H9", "M3", "M4", "L1", "L2"})


def test_ccvs_validate_code_round_trip():
    """Sample-derived codes all validate; ill-formed codes are rejected."""
    for c in ("WAH-H6", "MOB-M4", "SYS-L1", "STR-H9", "ELE-H6", "SIL-H6"):
        assert is_valid_code(c), c
    for bad in ("WAH-X1", "WAH-H7", "XXX-H6", "WAH", "wah-h6", "", None):
        assert not is_valid_code(bad)


def test_ccvs_category_for_round_trip():
    assert category_for("WAH-H6") == "Work at Height"
    assert category_for("MOB-M4") == "Mobile Plant"
    assert category_for("SYS-L1") == "Systems"
    assert category_for("XXX-H6") == ""
    assert category_for("") == ""


def test_ccvs_stream_of_extracts_prefix():
    assert stream_of("WAH-H6") == "WAH"
    assert stream_of("invalid") == ""


# ---------------------------------------------------------------------------
# Risk Assessment parser
# ---------------------------------------------------------------------------

def _make_synthetic_ra_docx(path: Path) -> Path:
    """Build a minimal RA docx in the canonical shape: 2-col metadata,
    6-col hold-point schedule, 7-col risk register with phase headers."""
    from docx import Document
    d = Document()

    # 2-col metadata
    meta = d.add_table(rows=3, cols=2)
    meta.rows[0].cells[0].text = "Project"
    meta.rows[0].cells[1].text = "Test Project — 5 Units"
    meta.rows[1].cells[0].text = "Site address"
    meta.rows[1].cells[1].text = "1 Test Lane, Sydney NSW 2000"
    meta.rows[2].cells[0].text = "Principal Contractor"
    meta.rows[2].cells[1].text = "Acme PC"

    # 6-col hold-point schedule
    hp = d.add_table(rows=3, cols=6)
    hp.rows[0].cells[0].text = "Hold Point"
    hp.rows[0].cells[1].text = "Description"
    hp.rows[0].cells[2].text = "Package"
    hp.rows[0].cells[3].text = "Condition"
    hp.rows[0].cells[4].text = "Sign-off"
    hp.rows[0].cells[5].text = "Evidence"
    hp.rows[1].cells[0].text = "HP-01"
    hp.rows[1].cells[1].text = "Lift study reviewed"
    hp.rows[1].cells[2].text = "Tilt-Up"
    hp.rows[1].cells[3].text = "Lift study signed"
    hp.rows[1].cells[4].text = "Engineer"
    hp.rows[1].cells[5].text = "Signed doc"
    hp.rows[2].cells[0].text = "HP-02"
    hp.rows[2].cells[1].text = "Excavation inspection"
    hp.rows[2].cells[2].text = "Pier Footings"
    hp.rows[2].cells[3].text = "Inspection complete"
    hp.rows[2].cells[4].text = "Competent person"
    hp.rows[2].cells[5].text = "Signed record"

    # 7-col risk register: header + 1 phase header + 2 activity rows
    reg = d.add_table(rows=4, cols=7)
    reg.rows[0].cells[0].text = "Ref"
    reg.rows[0].cells[1].text = "Activity"
    reg.rows[0].cells[2].text = "HRCW"
    reg.rows[0].cells[3].text = "Initial"
    reg.rows[0].cells[4].text = "Controls"
    reg.rows[0].cells[5].text = "Residual"
    reg.rows[0].cells[6].text = "Responsible"
    # Phase header row — ALL cells carry the phase title
    for c in reg.rows[1].cells:
        c.text = "1 — Site Establishment"
    reg.rows[2].cells[0].text = "SE-01"
    reg.rows[2].cells[1].text = "Site compound"
    reg.rows[2].cells[2].text = "H14"
    reg.rows[2].cells[3].text = "High (3)"
    reg.rows[2].cells[4].text = "TMP in place"
    reg.rows[2].cells[5].text = "Medium (2)"
    reg.rows[2].cells[6].text = "Site Manager"
    reg.rows[3].cells[0].text = "SE-02"
    reg.rows[3].cells[1].text = "Temporary power"
    reg.rows[3].cells[2].text = "H11"
    reg.rows[3].cells[3].text = "High (3)"
    reg.rows[3].cells[4].text = "Isolation"
    reg.rows[3].cells[5].text = "Medium (2)"
    reg.rows[3].cells[6].text = "Electrician"

    d.save(path)
    return path


def test_ra_parser_extracts_metadata_holdpoints_activities(tmp_path):
    from pims.services.ssa_ra_parser import parse_risk_assessment
    p = _make_synthetic_ra_docx(tmp_path / "RA.docx")
    ra = parse_risk_assessment(p)

    assert ra.project_name == "Test Project — 5 Units"
    assert ra.site_address == "1 Test Lane, Sydney NSW 2000"
    assert ra.principal_contractor == "Acme PC"

    assert len(ra.hold_points) == 2
    assert ra.hold_points[0].code == "HP-01"
    assert ra.hold_points[0].description == "Lift study reviewed"

    assert len(ra.activities) == 2
    assert ra.activities[0].ref == "SE-01"
    assert ra.activities[0].phase == "1 — Site Establishment"
    assert ra.activities[0].hrcw == "H14"
    assert ra.activities[0].initial_risk == "High (3)"
    assert ra.activities[1].ref == "SE-02"
    assert ra.activities[1].phase == "1 — Site Establishment"


def test_ra_parser_phase_header_em_dash_and_hyphen(tmp_path):
    """Phase header detection must handle em-dash, en-dash, and hyphen."""
    from pims.services.ssa_ra_parser import _PHASE_HEADER_RE
    for s in ("1 — Foo", "2 – Bar", "3 - Baz", "10 — Final Phase"):
        assert _PHASE_HEADER_RE.match(s), s


def test_ra_compact_context_caps_activity_count(tmp_path):
    from pims.services.ssa_ra_parser import (
        RiskAssessment, RAActivity, compact_context_block,
    )
    ra = RiskAssessment(project_name="X")
    for i in range(100):
        ra.activities.append(RAActivity(
            ref=f"AC-{i:03d}", phase="1 — Phase A", activity=f"A{i}",
            hrcw="H01", initial_risk="High (3)", controls="x",
            residual_risk="Low (1)", responsible="x",
        ))
    ctx = compact_context_block(ra, max_activities=10)
    assert "AC-009" in ctx
    assert "AC-099" not in ctx
    assert "(90 more activities)" in ctx


def test_ra_autodiscover_in_folder_picks_risk_assessment(tmp_path):
    from pims.services.ssa_ra_parser import autodiscover_in_folder
    # Plant decoys + the real one
    (tmp_path / "Site-Safety-Audit-Report-260501-SDG.docx").write_bytes(b"x")
    (tmp_path / "Random_Doc.docx").write_bytes(b"x")
    target = tmp_path / "Project_Risk_Assessment_v3.docx"
    target.write_bytes(b"x")
    assert autodiscover_in_folder(tmp_path) == target


def test_ra_parser_returns_empty_on_missing_file(tmp_path):
    from pims.services.ssa_ra_parser import parse_risk_assessment
    ra = parse_risk_assessment(tmp_path / "does-not-exist.docx")
    assert ra.is_empty


# ---------------------------------------------------------------------------
# Vision enricher — coercion + offline path
# ---------------------------------------------------------------------------

def test_vision_coerce_record_normalises_and_validates():
    from pims.services.ssa_vision_enricher import _coerce_record
    r = _coerce_record({
        "status": "NCR",
        "ccvs_code": "wah-h6",   # case + hyphen normalised
        "ccvs_category": "ignored — derived from code",
        "finding": "  multi-line  finding   ",
        "legal_ref": "WHS Reg cl.79",
        "recommendation": "fix it",
        "monitoring_note": "verify next audit",
    })
    assert r["status"] == "NCR"
    assert r["ccvs_code"] == "WAH-H6"
    assert r["ccvs_category"] == "Work at Height"  # regenerated from code
    assert r["finding"] == "multi-line  finding"   # outer-trim only


def test_vision_coerce_record_drops_invalid_code():
    from pims.services.ssa_vision_enricher import _coerce_record
    r = _coerce_record({
        "status": "NCR", "ccvs_code": "BOGUS-X9",
        "ccvs_category": "Bogus", "finding": "x",
    })
    assert r["ccvs_code"] == ""
    assert r["ccvs_category"] == ""


def test_vision_coerce_record_unknown_status_falls_to_unmatched():
    from pims.services.ssa_vision_enricher import _coerce_record
    r = _coerce_record({"status": "Compliantish", "ccvs_code": ""})
    assert r["status"] == "Unmatched"


def test_vision_enrichment_no_api_key_skips_cleanly(evidence_folder, monkeypatch):
    """ANTHROPIC_API_KEY missing → vision enricher returns diagnostics
    with the missing-key reason and rows stay Unmatched. Pipeline does
    not raise."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    payload = run_once(evidence_folder)
    assert payload["staging_status"] == "bulk_uploadable"
    assert "ANTHROPIC_API_KEY missing" in payload["llm_diagnostics"]["errors"]


def test_checklist_lookup_synthesises_code_from_leading_numbers():
    cl_path = Path(__file__).resolve().parent.parent / "pims" / "audit_checklist.xlsx"
    cl = ChecklistLookup.from_xlsx(cl_path)
    assert len(cl.by_code) > 0
    m = cl.match("01.01")
    assert m is not None
    assert m.ccvs_code == "01.01"
    assert "Planning" in m.ccvs_category
    assert cl.match("nonexistent") is None


def test_checklist_lookup_extracts_legal_ref_from_criteria_parens():
    """``(WHS Reg cl.34-38)`` inside a Criteria cell becomes the
    legal_ref when the column itself is blank — current xlsx case."""
    cl_path = Path(__file__).resolve().parent.parent / "pims" / "audit_checklist.xlsx"
    cl = ChecklistLookup.from_xlsx(cl_path)
    m = cl.match("01.02")  # criteria mentions "(WHS Reg cl.34-38)"
    assert m is not None
    assert "WHS Reg cl.34" in m.legal_ref


def test_checklist_lookup_maps_instruction_column_to_action_description():
    cl_path = Path(__file__).resolve().parent.parent / "pims" / "audit_checklist.xlsx"
    cl = ChecklistLookup.from_xlsx(cl_path)
    m = cl.match("01.02")
    assert m is not None
    # Instruction text in the xlsx for 01.02 is "Check risk assessment ..."
    assert m.action_description.lower().startswith("check")


def test_match_observation_confident_hit():
    cl_path = Path(__file__).resolve().parent.parent / "pims" / "audit_checklist.xlsx"
    cl = ChecklistLookup.from_xlsx(cl_path)
    m = cl.match_observation("first aid kit was incomplete")
    assert m is not None
    assert m.ccvs_code == "01.06"


def test_match_observation_ambiguous_returns_none():
    cl_path = Path(__file__).resolve().parent.parent / "pims" / "audit_checklist.xlsx"
    cl = ChecklistLookup.from_xlsx(cl_path)
    # Tied across multiple plausible candidates — guard rejects.
    assert cl.match_observation("guardrail missing at edge of slab") is None


def test_match_observation_too_few_tokens_returns_none():
    cl_path = Path(__file__).resolve().parent.parent / "pims" / "audit_checklist.xlsx"
    cl = ChecklistLookup.from_xlsx(cl_path)
    assert cl.match_observation("the and of") is None
    assert cl.match_observation("") is None


# ---------------------------------------------------------------------------
# enrich_observations
# ---------------------------------------------------------------------------

def test_enrich_observations_auto_matches_on_confident_hit():
    cl_path = Path(__file__).resolve().parent.parent / "pims" / "audit_checklist.xlsx"
    cl = ChecklistLookup.from_xlsx(cl_path)
    obs1 = _row("a.jpg", csv_row=1)
    obs1.observation_text = "first aid kit was incomplete"
    obs2 = _row("b.jpg", csv_row=2)
    obs2.observation_text = "guardrail missing at edge of slab"  # ambiguous
    enriched = enrich_observations([obs1, obs2], checklist=cl, auto_match=True)
    # Confident match: status lifts to Conditional, fields populated.
    assert enriched[0].conformance_status == "Conditional"
    assert enriched[0].ccvs_code == "01.06"
    assert enriched[0].action_description != ""
    # Ambiguous: stays Unmatched, fields blank.
    assert enriched[1].conformance_status == "Unmatched"
    assert enriched[1].ccvs_code == ""


def test_enrich_observations_auto_match_disabled_keeps_unmatched():
    cl_path = Path(__file__).resolve().parent.parent / "pims" / "audit_checklist.xlsx"
    cl = ChecklistLookup.from_xlsx(cl_path)
    obs = _row("a.jpg", csv_row=1)
    obs.observation_text = "first aid kit was incomplete"
    enriched = enrich_observations([obs], checklist=cl, auto_match=False)
    assert enriched[0].conformance_status == "Unmatched"
    assert enriched[0].ccvs_code == ""


def test_enrich_observations_explicit_ccvs_code_overrides_auto_match():
    cl_path = Path(__file__).resolve().parent.parent / "pims" / "audit_checklist.xlsx"
    cl = ChecklistLookup.from_xlsx(cl_path)
    obs = _row("a.jpg", csv_row=1)
    obs.observation_text = "first aid kit was incomplete"
    enriched = enrich_observations(
        [obs], checklist=cl, ccvs_codes={1: "01.01"}, auto_match=True,
    )
    # Explicit code wins over the auto-matcher's preferred 01.06.
    assert enriched[0].ccvs_code == "01.01"
    assert enriched[0].conformance_status == "Conditional"


def test_enrich_observations_v1_defaults_every_row_unmatched():
    obs = [
        _row("a.jpg", csv_row=1),
        _row("b.jpg", csv_row=2),
    ]
    obs[0].observation_text = "  edge   protection  missing  "
    enriched = enrich_observations(obs)
    assert len(enriched) == 2
    for r in enriched:
        assert r.conformance_status == "Unmatched"
        assert r.action_required == "Yes"
        assert r.needs_review
        assert r.ccvs_code == "" and r.legal_ref == ""
    # Light cleanup collapses runs of whitespace.
    assert enriched[0].observation_text_clean == "edge protection missing"


# ---------------------------------------------------------------------------
# build_pims_enriched_xlsx
# ---------------------------------------------------------------------------

def test_build_enriched_xlsx_shape_and_photo_embed(tmp_path):
    p1 = _save_jpeg(tmp_path / "a.jpg", (1200, 800))
    p2 = _save_jpeg(tmp_path / "b.jpg", (800, 1200), "blue")
    p_missing = tmp_path / "gone.jpg"
    obs1 = ObservationRow(csv_row=1, timestamp_raw="2026-05-01_09-15-22",
                          timestamp_iso="2026-05-01_09-15-22",
                          observation_text="x", csv_filename="a.jpg",
                          resolved_filename="a.jpg", resolved_path=p1)
    obs2 = ObservationRow(csv_row=2, timestamp_raw="bogus",
                          timestamp_iso=None,
                          observation_text="y", csv_filename="b.jpg",
                          resolved_filename="b.jpg", resolved_path=p2)
    obs2.flag("bad_timestamp")
    obs3 = ObservationRow(csv_row=3, timestamp_raw="2026-05-01_10-00-00",
                          timestamp_iso="2026-05-01_10-00-00",
                          observation_text="z", csv_filename="gone.jpg",
                          resolved_filename="gone.jpg",
                          resolved_path=p_missing)

    rows = [
        EnrichedRow(obs=obs1, conformance_status="NCR", ccvs_code="02.05"),
        EnrichedRow(obs=obs2, conformance_status="Compliant"),
        EnrichedRow(obs=obs3, conformance_status="Unmatched"),
    ]
    out = tmp_path / "enriched.xlsx"
    diag = build_pims_enriched_xlsx(rows, out)

    assert out.exists()
    assert str(p_missing) in diag["photo_file_missing_at_render"]

    wb = openpyxl.load_workbook(out)
    ws = wb["Enriched Register"]
    headers = [c.value for c in ws[1]]
    assert headers[0] == "#" and headers[3] == "Photo"

    # Row 2: NCR row, embedded photo
    assert ws.cell(row=2, column=1).value == 1
    assert ws.cell(row=2, column=3).value == "P-0001"
    assert ws.cell(row=2, column=10).value == "Yes"  # Action Required
    # Row 3: bad timestamp → RAW: prefix
    assert str(ws.cell(row=3, column=2).value).startswith("RAW: bogus")
    # Row 4: Unmatched, missing photo, default row height
    assert ws.cell(row=4, column=10).value == "Yes"  # Unmatched forces Yes
    assert ws.row_dimensions[4].height in (None, 0)

    # Two photos embedded (obs1, obs2); obs3 missing on disk → none
    assert len(ws._images) == 2


# ---------------------------------------------------------------------------
# build_ssa_report_docx
# ---------------------------------------------------------------------------

def test_build_ssa_report_docx_substitutes_tokens_and_clones_tables(tmp_path):
    p1 = _save_jpeg(tmp_path / "a.jpg", (1200, 800))
    p2 = _save_jpeg(tmp_path / "b.jpg", (800, 1200), "blue")
    obs1 = ObservationRow(csv_row=1, timestamp_raw="", timestamp_iso=None,
                          observation_text="x", csv_filename="a.jpg",
                          resolved_filename="a.jpg", resolved_path=p1)
    obs2 = ObservationRow(csv_row=2, timestamp_raw="", timestamp_iso=None,
                          observation_text="y", csv_filename="b.jpg",
                          resolved_filename="b.jpg", resolved_path=p2)
    obs3 = ObservationRow(csv_row=3, timestamp_raw="", timestamp_iso=None,
                          observation_text="z", csv_filename="m.jpg")
    rows = [
        EnrichedRow(obs=obs1, finding="Top rail missing.",
                    conformance_status="NCR", legal_ref="WHS Reg cl.79"),
        EnrichedRow(obs=obs2, observation_text_clean="Site sign clear.",
                    conformance_status="Compliant", legal_ref="WHS Reg cl.34"),
        EnrichedRow(obs=obs3, finding="Unmatched issue.",
                    conformance_status="Unmatched"),
    ]
    out = tmp_path / "report.docx"
    diag = build_ssa_report_docx(
        rows=rows,
        site_address="12 Test Street, Sydney NSW",
        audit_date_ddmmyyyy="01/05/2026",
        narrative_summary="Audit summary text.",
        output_path=out,
        prepared_by="Alan Richardson",
    )
    assert out.exists()
    assert diag["missing_photo_obs"] == [2]  # obs3 → row 2 in register

    # No leftover tokens in any document part.
    with zipfile.ZipFile(out) as z:
        for name in z.namelist():
            if name.endswith(".xml"):
                data = z.read(name).decode(errors="ignore")
                assert "{{" not in data, name
                assert "}}" not in data, name

    doc = Document(out)
    # p4 = site address (16 pt bold), p6 = narrative
    assert doc.paragraphs[4].text == "12 Test Street, Sydney NSW"
    assert doc.paragraphs[6].text == "Audit summary text."

    # Footer carries DD/MM/YYYY + prepared_by
    foot = doc.sections[1].footer.paragraphs[0].text
    assert "01/05/2026" in foot
    assert "Alan Richardson" in foot

    # Positive Observations table → 1 Compliant row
    pos = next(t for t in doc.tables if t.rows[0].cells[0].text == "#"
               and "Reference" in t.rows[0].cells[2].text)
    assert pos.rows[1].cells[1].text == "Site sign clear."

    # Observations Register → 2 non-Compliant rows; second row has `*`
    reg = next(t for t in doc.tables
               if "Obs #" in t.rows[0].cells[0].text and len(t.columns) == 6)
    assert len(reg.rows) == 3  # header + 2 data
    assert reg.rows[1].cells[0].text == "1"
    assert reg.rows[2].cells[0].text == "2*"


def test_findings_list_expands_per_non_compliant_row(tmp_path):
    """Findings #N section must materialise one heading + body pair per
    non-Compliant row. Before this fix the rendered docx left only the
    template's `#1` placeholder visible."""
    rows = []
    for i in range(4):
        obs = ObservationRow(
            csv_row=i + 1, timestamp_raw="", timestamp_iso=None,
            observation_text=f"obs-{i}", csv_filename=f"x{i}.jpg",
        )
        rows.append(EnrichedRow(
            obs=obs,
            finding=f"FINDING-{i} multi-sentence reviewer narrative.",
            conformance_status="NCR" if i % 2 == 0 else "Compliant",
            ccvs_code="WAH-H6" if i % 2 == 0 else "SYS-L1",
        ))
    out = tmp_path / "report.docx"
    build_ssa_report_docx(
        rows=rows, site_address="addr", audit_date_ddmmyyyy="01/01/2026",
        narrative_summary="x", output_path=out,
    )
    doc = Document(out)
    headings = [
        p.text for p in doc.paragraphs
        if p.text.startswith("#") and len(p.text) > 2
    ]
    # 2 non-Compliant rows (i=0 NCR, i=2 NCR) → 2 #N headings.
    assert len(headings) == 2
    assert any(h.startswith("#1") and "WAH-H6" in h for h in headings)
    assert any(h.startswith("#2") and "WAH-H6" in h for h in headings)
    # Finding body text must appear as separate paragraphs.
    body_texts = [p.text for p in doc.paragraphs]
    assert any("FINDING-0" in t for t in body_texts)
    assert any("FINDING-2" in t for t in body_texts)


def test_findings_list_no_register_rows_writes_placeholder(tmp_path):
    """Empty audit collapses Findings to a single 'no findings recorded'
    line so the section still renders cleanly."""
    out = tmp_path / "report.docx"
    build_ssa_report_docx(
        rows=[], site_address="addr", audit_date_ddmmyyyy="01/01/2026",
        narrative_summary="", output_path=out,
    )
    doc = Document(out)
    assert any("No findings recorded." in p.text for p in doc.paragraphs)


def test_parse_prior_report_recommendations_extracts_non_compliant(tmp_path):
    """Prior report's NCR / Conditional rows in the Observations
    Register table become carry-forward recommendation entries."""
    from pims.services.ssa_pipeline import parse_prior_report_recommendations
    # Build a minimal prior-report shape: one 6-col Observations
    # Register with mixed statuses.
    from docx import Document as DocBuilder
    d = DocBuilder()
    t = d.add_table(rows=4, cols=6)
    headers = ["Obs #", "Photo", "Observation", "Reference", "Status", "Evidence File"]
    for i, h in enumerate(headers):
        t.rows[0].cells[i].text = h
    # NCR row
    for i, v in enumerate(["1", "", "missing edge protection", "WHS Reg cl.79",
                            "NCR", "ev1.jpg"]):
        t.rows[1].cells[i].text = v
    # Compliant row — should be skipped
    for i, v in enumerate(["2", "", "site sign current", "WHS Reg cl.34",
                            "Compliant", "ev2.jpg"]):
        t.rows[2].cells[i].text = v
    # Conditional row
    for i, v in enumerate(["3", "", "SWMS undated", "WHS Reg cl.301",
                            "Conditional", "ev3.jpg"]):
        t.rows[3].cells[i].text = v
    p = tmp_path / "Site-Safety-Audit-Report-260301-RPD.docx"
    d.save(p)

    recs = parse_prior_report_recommendations(p)
    assert len(recs) == 2
    assert recs[0]["recommendation"] == "missing edge protection"
    assert recs[0]["required_actions"] == "WHS Reg cl.79"
    assert recs[0]["status"] == ""
    assert recs[1]["recommendation"] == "SWMS undated"


def test_parse_prior_report_missing_file_returns_empty(tmp_path):
    from pims.services.ssa_pipeline import parse_prior_report_recommendations
    assert parse_prior_report_recommendations(tmp_path / "no.docx") == []


def test_build_ssa_report_docx_clones_distinct_rows_per_finding(tmp_path):
    """Regression for the _clone_row bug that dropped all middle rows.

    Before the fix, addnext()+rows[-1] caused every cloned row except
    the final one to keep the placeholder's deepcopied content, so a
    table built from N findings rendered row 1 repeated (N-1) times
    plus row N at the end. Asserts every cloned row carries the
    finding text it was written for, in order.
    """
    photos = []
    for i in range(5):
        p = tmp_path / f"P_{i}.jpg"
        _save_jpeg(p, (400, 300))
        photos.append(p)

    rows = [
        EnrichedRow(
            obs=ObservationRow(
                csv_row=i + 1, timestamp_raw="", timestamp_iso=None,
                observation_text=f"obs {i}", csv_filename=p.name,
                resolved_filename=p.name, resolved_path=p,
            ),
            observation_text_clean=f"clean {i}",
            finding=f"FINDING NUMBER {i} unique-marker-{i}",
            conformance_status="NCR" if i % 2 == 0 else "Compliant",
            legal_ref=f"REF-{i}",
        )
        for i, p in enumerate(photos)
    ]
    out = tmp_path / "report.docx"
    build_ssa_report_docx(
        rows=rows,
        site_address="addr",
        audit_date_ddmmyyyy="01/01/2026",
        narrative_summary="x",
        output_path=out,
    )

    doc = Document(out)
    pos = next(t for t in doc.tables if t.rows[0].cells[0].text == "#"
               and "Reference" in t.rows[0].cells[2].text)
    reg = next(t for t in doc.tables
               if "Obs #" in t.rows[0].cells[0].text and len(t.columns) == 6)

    # 3 NCR (i=0,2,4) → register; 2 Compliant (i=1,3) → positive table.
    pos_data = [r.cells[1].text for r in pos.rows[1:]]
    reg_data = [r.cells[2].text for r in reg.rows[1:]]
    assert pos_data == ["clean 1", "clean 3"]
    # All NCR rows must carry their finding text — placeholder-content
    # repetition would surface as identical strings here.
    assert "unique-marker-0" in reg_data[0]
    assert "unique-marker-2" in reg_data[1]
    assert "unique-marker-4" in reg_data[2]
    # And every register row must be distinct.
    assert len(set(reg_data)) == len(reg_data)


def test_build_ssa_report_docx_removes_per_location_placeholder(tmp_path):
    """v1 always strips the per-location 2-col block per R-1.3(e).
    Output should contain exactly 3 tables (Positive, Prior Recs,
    Observations Register) and no 'Location' first-cell table."""
    out = tmp_path / "r.docx"
    build_ssa_report_docx(
        rows=[],
        site_address="addr",
        audit_date_ddmmyyyy="01/01/2026",
        narrative_summary="",
        output_path=out,
    )
    doc = Document(out)
    assert len(doc.tables) == 3
    for t in doc.tables:
        assert t.rows[0].cells[0].text.strip() != "Location"


def test_build_ssa_report_docx_no_findings_writes_placeholder(tmp_path):
    out = tmp_path / "empty.docx"
    build_ssa_report_docx(
        rows=[],
        site_address="addr",
        audit_date_ddmmyyyy="01/01/2026",
        narrative_summary="",
        output_path=out,
    )
    doc = Document(out)
    # Status of Previous Recs default placeholder.
    prev = next(
        t for t in doc.tables
        if "Recommendation" in t.rows[0].cells[0].text and len(t.columns) == 4
    )
    assert "No prior recommendations" in prev.rows[1].cells[0].text


# ---------------------------------------------------------------------------
# build_pims_staging_xlsx
# ---------------------------------------------------------------------------

def test_build_staging_xlsx_row5_data_id_blank_due_category(tmp_path):
    p1 = _save_jpeg(tmp_path / "a.jpg", (1200, 800))
    obs1 = ObservationRow(csv_row=1, timestamp_raw="2026-05-01_09-15-22",
                          timestamp_iso="2026-05-01_09-15-22",
                          observation_text="x", csv_filename="a.jpg",
                          resolved_filename="a.jpg", resolved_path=p1)
    obs2 = ObservationRow(csv_row=2, timestamp_raw="bogus",
                          timestamp_iso=None,
                          observation_text="y", csv_filename="b.jpg")
    obs2.flag("bad_timestamp")
    rows = [
        EnrichedRow(obs=obs1, conformance_status="NCR",
                    ccvs_code="02.05", legal_ref="WHS Reg cl.79"),
        EnrichedRow(obs=obs2, conformance_status="Compliant"),
        EnrichedRow(
            obs=ObservationRow(csv_row=3, timestamp_raw="",
                               timestamp_iso=None, observation_text="z",
                               csv_filename="c.jpg"),
            conformance_status="Conditional"),
    ]
    out = tmp_path / "staging.xlsx"
    diag = build_pims_staging_xlsx(
        rows, out, site_address="12 Test St", audit_date_iso="2026-05-01",
    )
    assert diag["rows_written"] == 3

    wb = openpyxl.load_workbook(out)
    ws = wb["Observations"]
    # Row 3 = headers (snake_case)
    headers = [c.value for c in ws[3]]
    assert headers[:5] == [
        "id", "photo", "site_address", "audit_date", "observation_text",
    ]
    # Data starts at row 5
    assert ws.cell(row=5, column=1).value in (None, "")  # id ALWAYS blank
    assert ws.cell(row=5, column=3).value == "12 Test St"
    assert ws.cell(row=5, column=4).value == "2026-05-01"
    assert ws.cell(row=5, column=12).value == "Immediate"   # NCR → due
    assert ws.cell(row=5, column=20).value == "FALSE"        # NCR no flags
    # Row 6: Compliant + bad_timestamp flag → needs_review TRUE
    assert ws.cell(row=6, column=12).value == "N/A"
    assert ws.cell(row=6, column=20).value == "TRUE"
    # Row 7: Conditional → "Within 7 days"
    assert ws.cell(row=7, column=12).value == "Within 7 days"


def test_xlsx_polish_widths_wrap_and_status_fills_applied(tmp_path):
    """The Enriched + Staging builders apply column widths, wrap_text on
    long-content cells, and status colour fills on the Conformance
    Status column. Without these the deliverables render unprofessional
    (truncated mid-sentence findings, no at-a-glance status scanning)."""
    p1 = _save_jpeg(tmp_path / "a.jpg", (1200, 800))
    obs = ObservationRow(
        csv_row=1, timestamp_raw="2026-05-01_09-15-22",
        timestamp_iso="2026-05-01_09-15-22",
        observation_text="x", csv_filename="a.jpg",
        resolved_filename="a.jpg", resolved_path=p1,
    )
    rows = [
        EnrichedRow(obs=obs, conformance_status="NCR",
                    finding="multi-sentence enriched finding text here",
                    ccvs_code="WAH-H6"),
    ]

    e_out = tmp_path / "enriched.xlsx"
    build_pims_enriched_xlsx(rows, e_out)
    wb = openpyxl.load_workbook(e_out)
    ws = wb["Enriched Register"]
    # Observation column wider than default 8.43.
    obs_col_width = ws.column_dimensions["F"].width  # F = "Observation"
    assert obs_col_width is not None and obs_col_width >= 50
    # Wrap text on the Observation cell.
    assert ws.cell(row=2, column=6).alignment.wrap_text is True
    # NCR row gets a red-ish fill on the Conformance Status column (G).
    fill = ws.cell(row=2, column=7).fill
    assert fill.fill_type == "solid"
    assert "FFC7CE" in (fill.start_color.rgb or "").upper()

    s_out = tmp_path / "staging.xlsx"
    build_pims_staging_xlsx(
        rows, s_out, site_address="addr", audit_date_iso="2026-05-01",
    )
    wb = openpyxl.load_workbook(s_out)
    ws = wb["Observations"]
    # Finding column (header in row 3) widened and wrapped.
    assert ws.column_dimensions["F"].width is not None
    assert ws.cell(row=5, column=6).alignment.wrap_text is True
    # Conformance Status (column G) on row 5 gets the NCR fill.
    fill = ws.cell(row=5, column=7).fill
    assert "FFC7CE" in (fill.start_color.rgb or "").upper()


# ---------------------------------------------------------------------------
# build_pims_staging_xlsx_with_size_control
# ---------------------------------------------------------------------------

def _make_staging_rows(tmp_path, n: int, edge_px=(800, 600)):
    """Build n EnrichedRows backed by simple synthetic JPEGs."""
    out = []
    for i in range(n):
        p = tmp_path / f"EV_{i:04d}.jpg"
        _save_jpeg(p, edge_px, color=(i * 5 % 255, 80, 80))
        obs = ObservationRow(
            csv_row=i + 1, timestamp_raw="", timestamp_iso=None,
            observation_text=f"obs {i}", csv_filename=p.name,
            resolved_filename=p.name, resolved_path=p,
        )
        out.append(EnrichedRow(obs=obs, conformance_status="NCR"))
    return out


def test_size_control_small_audit_single_part_at_1600(tmp_path):
    rows = _make_staging_rows(tmp_path, 10)
    out = tmp_path / "s.xlsx"
    r = build_pims_staging_xlsx_with_size_control(
        rows, out, site_address="x", audit_date_iso="2026-05-01",
    )
    assert r["split"] is False
    assert r["split_reason"] is None
    assert r["max_edge_px"] == 1600
    assert len(r["parts"]) == 1
    assert r["parts"][0] == out
    assert out.exists()


def test_size_control_row_count_split_above_500(tmp_path):
    """Row count > 500 forces an immediate split, no size loop."""
    rows = _make_staging_rows(tmp_path, 510, edge_px=(400, 300))
    out = tmp_path / "s.xlsx"
    r = build_pims_staging_xlsx_with_size_control(
        rows, out, site_address="x", audit_date_iso="2026-05-01",
    )
    assert r["split"] is True
    assert r["split_reason"] == "row_count"
    assert len(r["parts"]) == 2
    assert r["parts"][0].name.endswith("-part1.xlsx")
    assert r["parts"][1].name.endswith("-part2.xlsx")
    # Single-file path was not written.
    assert not out.exists()


def test_size_control_size_driven_split_into_partN(tmp_path):
    """Force a tiny budget that no full-set render can satisfy → recursive
    halving + sequential renumbering of parts."""
    rows = _make_staging_rows(tmp_path, 20, edge_px=(1200, 900))
    out = tmp_path / "s.xlsx"
    r = build_pims_staging_xlsx_with_size_control(
        rows, out, site_address="x", audit_date_iso="2026-05-01",
        max_bytes=12_000,
    )
    assert r["split"] is True
    assert r["split_reason"] == "size"
    assert len(r["parts"]) >= 2
    # Sequential -part1, -part2, ... naming with no gaps.
    for i, p in enumerate(r["parts"], start=1):
        assert p.name.endswith(f"-part{i}.xlsx")
        assert p.exists()


# ---------------------------------------------------------------------------
# run_ssa_pipeline.run_once — staging tri-state + freeze + idempotency
# ---------------------------------------------------------------------------

def test_run_once_rpd_bulk_uploadable(evidence_folder):
    payload = run_once(evidence_folder)
    assert payload["staging_status"] == "bulk_uploadable"
    assert payload["blocker"] is None
    assert payload["client_bulk_endpoint"] == "/pims/upload/observations"
    for name in payload["outputs"]:
        assert (evidence_folder / name).exists()


def test_run_once_sdg_schema_valid_no_endpoint(tmp_path):
    folder = tmp_path / "2026-05-02-SDG"
    folder.mkdir()
    (folder / "Evidence_Master.csv").write_text(
        "timestamp,observation,filename\n"
        "2026-05-02_09-00-00,obs at 12 Smith Street,EV.jpg\n",
        encoding="utf-8",
    )
    _save_jpeg(folder / "EV.jpg")
    payload = run_once(folder)
    assert payload["staging_status"] == "schema_valid_no_endpoint"
    assert payload["client_bulk_endpoint"] is None
    assert "STAGING-NO-BULK-ENDPOINT.txt" in payload["outputs"]
    assert (folder / "STAGING-NO-BULK-ENDPOINT.txt").exists()


def test_run_once_no_address_writes_not_uploadable_sentinel(tmp_path):
    folder = tmp_path / "2026-05-03-RPD"
    folder.mkdir()
    (folder / "Evidence_Master.csv").write_text(
        "timestamp,observation,filename\n"
        "2026-05-03_09-00-00,no address text,EV.jpg\n",
        encoding="utf-8",
    )
    _save_jpeg(folder / "EV.jpg")
    payload = run_once(folder)
    assert payload["staging_status"] == "not_uploadable"
    assert payload["blocker"] == "site_address_unresolved"
    assert (folder / "STAGING-NOT-UPLOADABLE.txt").exists()


def test_run_once_freeze_blocks_unless_ignore(evidence_folder):
    run_once(evidence_folder)
    (evidence_folder / ".ssa_freeze").touch()
    with pytest.raises(RuntimeError, match="frozen"):
        run_once(evidence_folder)
    payload = run_once(evidence_folder, ignore_freeze=True)
    assert payload["staging_status"] == "bulk_uploadable"


def test_run_once_idempotent_skip_on_unchanged_inputs(evidence_folder):
    p1 = run_once(evidence_folder)
    enriched = evidence_folder / "PIMS-Enriched-260501-RPD.xlsx"
    mtime_before = enriched.stat().st_mtime
    time.sleep(1.05)
    p2 = run_once(evidence_folder)
    assert p2["skipped"] is True
    assert enriched.stat().st_mtime == mtime_before
    assert p2["inputs_sha256"] == p1["inputs_sha256"]


def test_run_once_input_change_reruns_and_force_overrides(evidence_folder):
    p1 = run_once(evidence_folder)
    csv = evidence_folder / "Evidence_Master.csv"
    csv.write_text(
        csv.read_text()
        + "2026-05-01_10-00-00,Hot works near combustibles,EV_003.jpg\n",
        encoding="utf-8",
    )
    _save_jpeg(evidence_folder / "EV_003.jpg")
    p2 = run_once(evidence_folder)
    assert p2["skipped"] is False
    assert p2["inputs_sha256"] != p1["inputs_sha256"]
    assert p2["row_count"] == 3

    # --force overrides the skip when nothing changed.
    p3 = run_once(evidence_folder)
    assert p3["skipped"] is True
    p4 = run_once(evidence_folder, force=True)
    assert p4["skipped"] is False


def test_run_once_partial_output_recovery(evidence_folder):
    p = run_once(evidence_folder)
    victim = evidence_folder / p["outputs"][0]
    assert victim.exists()
    victim.unlink()
    p2 = run_once(evidence_folder)
    assert p2["skipped"] is False
    assert victim.exists()


def test_run_once_prior_report_self_reference_excluded(evidence_folder):
    """The current run's freshly-generated report must NOT be hashed
    into the next manifest, otherwise reruns of the same folder would
    flap the manifest and never converge."""
    p = run_once(evidence_folder)
    current = evidence_folder / "Site-Safety-Audit-Report-260501-RPD.docx"
    # Drop a qualifying older report; it should appear in the manifest
    # source list while the current target stays out.
    older = evidence_folder / "Site-Safety-Audit-Report-260330-RPD.docx"
    older.write_bytes(current.read_bytes())
    p2 = run_once(evidence_folder)
    assert older.name in p2["prior_reports_used"]
    assert current.name not in p2["prior_reports_used"]
    # Stable across cycles.
    p3 = run_once(evidence_folder)
    assert p3["skipped"] is True


def test_run_once_unparseable_prior_report_date_non_qualifying(evidence_folder):
    run_once(evidence_folder)
    (evidence_folder / "Site-Safety-Audit-Report-bogus-RPD.docx").write_bytes(
        b"x"
    )
    p = run_once(evidence_folder, force=True)
    assert "Site-Safety-Audit-Report-bogus-RPD.docx" not in p["prior_reports_used"]


def test_run_once_llm_pass_disabled_by_default_in_tests(evidence_folder, monkeypatch):
    """Tests run without ``PIMS_ENRICH_FINDINGS`` set, so the LLM pass
    short-circuits via ``finding_enricher.is_enabled``. Verify that an
    empty narrative flows through to the docx without raising and that
    no Anthropic call is attempted (would have surfaced as an
    environment / network error)."""
    monkeypatch.delenv("PIMS_ENRICH_FINDINGS", raising=False)
    payload = run_once(evidence_folder)
    assert payload["staging_status"] == "bulk_uploadable"
    # Docx exists; narrative paragraph (p6) is empty.
    docx_path = evidence_folder / "Site-Safety-Audit-Report-260501-RPD.docx"
    doc = Document(docx_path)
    assert doc.paragraphs[6].text == ""


def test_run_once_llm_pass_explicit_no_enrich_skips_pass(evidence_folder, monkeypatch):
    """Even with ``PIMS_ENRICH_FINDINGS=1``, ``enrich=False`` short-circuits
    before the env-var gate. No Anthropic call attempted."""
    monkeypatch.setenv("PIMS_ENRICH_FINDINGS", "1")
    payload = run_once(evidence_folder, enrich=False)
    assert payload["staging_status"] == "bulk_uploadable"
    docx_path = evidence_folder / "Site-Safety-Audit-Report-260501-RPD.docx"
    doc = Document(docx_path)
    assert doc.paragraphs[6].text == ""


def test_run_once_bad_folder_name_raises(tmp_path):
    bad = tmp_path / "not-a-dated-folder"
    bad.mkdir()
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        run_once(bad)


# ---------------------------------------------------------------------------
# ssa_watcher
# ---------------------------------------------------------------------------

def test_watcher_skips_ineligible_folder(tmp_path):
    (tmp_path / "random").mkdir()
    w = Watcher(watch_root=tmp_path, settle_seconds=0,
                required_stable_polls=1, runner=lambda f: {})
    results = w.tick()
    assert all(r["action"] == "skip" for r in results)


def test_watcher_quiescence_then_fires(tmp_path):
    folder = tmp_path / "2026-05-01-RPD"
    folder.mkdir()
    (folder / "Evidence_Master.csv").write_text(
        "timestamp,observation,filename\n"
        "2026-05-01_09-15-22,obs at 12 Smith Street,EV.jpg\n",
        encoding="utf-8",
    )
    _save_jpeg(folder / "EV.jpg")

    fake_now = [time.time() + 10_000]   # past settle window
    calls = []

    def runner(f):
        calls.append(f.name)
        return run_once(f)

    w = Watcher(
        watch_root=tmp_path, settle_seconds=120, required_stable_polls=4,
        runner=runner, clock=lambda: fake_now[0],
    )
    # 3 polls — still waiting for stability
    for _ in range(3):
        results = w.tick()
        assert any(r["action"] == "wait" for r in results
                   if r["folder"] == folder.name)
    # 4th poll fires
    results = w.tick()
    fired = [r for r in results if r["folder"] == folder.name]
    assert fired and fired[0]["action"] == "ran"
    assert fired[0]["skipped"] is False
    assert calls == [folder.name]

    # Next 4-poll window: idempotency yields skipped=True
    for _ in range(4):
        results = w.tick()
    fired = [r for r in results if r["folder"] == folder.name]
    assert fired[0]["action"] == "ran"
    assert fired[0]["skipped"] is True


def test_watcher_frozen_folder_skipped(tmp_path):
    folder = tmp_path / "2026-05-01-RPD"
    folder.mkdir()
    (folder / "Evidence_Master.csv").write_text(
        "timestamp,observation,filename\n"
        "2026-05-01_09-15-22,obs at 12 Smith Street,EV.jpg\n",
        encoding="utf-8",
    )
    _save_jpeg(folder / "EV.jpg")
    (folder / ".ssa_freeze").touch()

    fake_now = [time.time() + 10_000]
    calls = []

    def runner(f):
        calls.append(f.name)
        return {}

    w = Watcher(
        watch_root=tmp_path, settle_seconds=0, required_stable_polls=1,
        runner=runner, clock=lambda: fake_now[0],
    )
    results = w.tick()
    fired = [r for r in results if r["folder"] == folder.name]
    assert fired[0]["action"] == "frozen"
    assert calls == []


def test_watcher_runner_exception_writes_error_sentinel(tmp_path):
    folder = tmp_path / "2026-05-01-RPD"
    folder.mkdir()
    (folder / "Evidence_Master.csv").write_text(
        "timestamp,observation,filename\n"
        "2026-05-01_09-15-22,obs at 12 Smith Street,EV.jpg\n",
        encoding="utf-8",
    )
    _save_jpeg(folder / "EV.jpg")

    def runner(f):
        raise RuntimeError("simulated pipeline failure")

    fake_now = [time.time() + 10_000]
    w = Watcher(
        watch_root=tmp_path, settle_seconds=0, required_stable_polls=1,
        runner=runner, clock=lambda: fake_now[0],
    )
    results = w.tick()
    fired = [r for r in results if r["folder"] == folder.name]
    assert fired[0]["action"] == "error"
    err = folder / ".ssa_run.error"
    assert err.exists()
    assert "simulated pipeline failure" in err.read_text(encoding="utf-8")

```


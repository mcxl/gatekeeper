# SSA Pipeline — Codex Review Bundle

Single-document bundle of the **original plan** plus the **shipped
implementation** of the SSA evidence-folder → 3-deliverable pipeline.
Use this to diff plan vs. implementation and surface drift.

## What this bundle is for

The original plan was written before any of the canonical sample
deliverables had been opened. Real-folder runs against
`G:/My Drive/alan_mcxico/SSA-evidence/2026-05-01-SDG/` (with
`Unitas_Risk_Assessment_all.docx`, prior `260330-SDG.docx`, 21
photos, and the three canonical sample files in the parent folder)
revealed many contract mismatches between the plan and what Alan
considers canonical. The shipped pipeline has been progressively
re-aligned with the samples through a sequence of bug-fix and
delta-closure commits.

Use this document to:

1. Identify any remaining drift (places where the plan still differs
   from what the code actually does, or where the code still
   differs from the canonical samples).
2. Catch quality / correctness issues the test suite (99 pytest
   cases, all green; flake8 clean) does not assert against.
3. Suggest improvements to the plan itself so future work has a
   spec that matches the canonical samples.

## Drift between plan and shipped (current state)

| Axis | Plan / template said | Shipped reality | Why |
|---|---|---|---|
| CCVS code source | `pims/audit_checklist.xlsx` (Category / Criteria / Instruction; numeric `01.01` synthesised from leading digits) | Canonical 25 × 6 = 150 codes — 24 streams from `renderers/docx_renderer.py:_VALID_CCVS_STREAMS` plus `SYS` extension; suffixes H6 / H9 / M3 / M4 / L1 / L2 | Samples use `SYS-M3`, `MOB-H6`, `WAH-H6`, `STR-H9`, `ELE-H6`. The numeric scheme has no relationship to the canonical taxonomy. |
| Status assignment | Keyword auto-matcher (difflib token recall) emits Conditional / Unmatched only | Vision Anthropic call (Opus 4.7) emits Compliant / Conditional / NCR / Info / Unmatched | Sample is Compliant-heavy (39 / 64). A classifier that never produces Compliant cannot match the contract. |
| LLM gating | `PIMS_ENRICH_FINDINGS` env var, default OFF | Default ON; `--no-enrich` opts out; `ANTHROPIC_API_KEY` required at runtime | Sample observation / finding cells are LLM-rewritten multi-sentence narratives citing WHS Reg / AS / SafeWork NSW inline. |
| Vision support | text-only enrichment | Photo downscaled to 1024 px, EXIF-normalised, JPEG q85, base64-encoded; sent to vision model alongside the auditor's note | Photo is the primary evidence the human reviewer uses; required for accurate status assignment. |
| Project context | none | RA-aware: auto-discovers `*Risk_Assessment*.docx` in the audit folder, parses 9 hold points + 66 phase activities + project metadata, injects into the vision prompt | Without RA awareness the audit cannot reference `HP-04`, `TP-05`, `HRCW H14`, etc. — reviewer can't trace findings back to the principal contractor's WHS contract. |
| `#N` Findings layout | R-1.3 forbids paragraph-level cloning at body level | Cloning enabled for Findings list. Each finding renders as a `(#N <descriptive title>` heading + a 2-col 6-row detail table. Per-finding detail labels: `Location / Observation / Regulatory Basis / Hierarchy of Control / Recommendation / Timeframe`. The literal cell label `Required Action` from the template is rewritten to `Recommendation` at render time. | R-1.3 conflicts with V-10.5 ("count of #N paragraphs equals count of non-Compliant"). The canonical sample shows each finding rendering as a 6-row detail table with these specific labels. |
| Per-location 2-col block | Clone N times per detected location | Used as the per-finding detail block (per the canonical sample) — cloned once per non-Compliant row | The template's `Location / Observation / Regulatory Basis / Hierarchy of Control / Required Action / Timeframe` block is the per-finding detail card, not a per-location scaffold. |
| Status of Previous Recs | Parse prior report (deferred slice in plan) | `parse_prior_report_recommendations` extracts NCR / Conditional rows from the prior report's Observations Register; carry-forward dict written into the table. Header reads `Status (DD/MM/YY)` with the prior audit date substituted. | Reviewer needs carry-forward visibility; placeholder text wasn't acceptable. |
| Site address line | `{{SITE_ADDRESS}}` | Project name (from RA) prepended → `Unitas Business Park 4-6 Mile End Rd Rouse Hill NSW 2155` | Sample p4 carries the venue prefix. |
| Executive Summary | one paragraph (`{{NARRATIVE_SUMMARY}}`) | Two paragraphs — fixed scope intro ("This report presents the findings of a site safety audit conducted on `<long date>`...") plus dynamic LLM-generated narrative. Split via `_split_narrative_paragraph` after token substitution. | Sample carries both. |
| Per-finding detail table column language | Plan didn't specify | LLM produces tier-prefixed control language (`Engineering: <control>`), urgency-prefixed Recommendation (`Within 7 days – mount extinguishers on compliant brackets with location signage`, ≤15 words, paired-verb `establish and maintain` pattern for persistent controls), multi-instrument legal_ref (`WHS Act 2011 (NSW) s.19; WHS Reg r.291; SafeWork NSW COP: …`), Timeframe one of `Immediate / Within 7 days / Next audit / Ongoing / N/A` | Sample uses these conventions consistently. |
| Findings `#N` heading | Plan didn't specify | Descriptive title from the LLM (`#1 Steel Erection Exclusion Zone`); space-before of 240 twentieths-of-a-point (≈12 pt) on every `#N` heading so each finding visually breathes from the previous detail table | Sample uses descriptive titles, not `STATUS – CCVS-CODE`. |
| Positive Observations table | column widths inherited from template | column widths `1.5 / 7 / 9.5 cm`, bold header row, header repeats across page breaks (`<w:tblHeader/>`) | User direction. |
| Status of Previous Recs table | column widths inherited from template | column widths `6.5 / 4 / 2.5 / 4.75 cm` | User direction. |
| Observations Register table | header didn't repeat across pages | `<w:tblHeader/>` set on first row | User direction. |
| Staging xlsx polish | Plan said embed thumbnails; nothing about column widths / wrap / status fills | Column widths set, wrap_text on long-content columns, status colour fills (NCR red `FFC7CE`, Conditional amber `FFE699`, Compliant green `C6EFCE`, Info blue-grey `D9E1F2`, Unmatched neutral `F2F2F2`) | Sample uses these conventions; without them long enriched findings render truncated. |
| Enriched xlsx Summary sheet | Plan said write into named cells only | `_populate_enriched_summary_sheet` builds the canonical dashboard: title row + Audit Date / Site / Principal Contractor + Conformance Status counts + percentages + CCVS Category breakdown (Total / NCR / Conditional / Open Actions) + Open Actions list (#, Status, CCVS Code, Action Description, Responsible="PC", Due) | Sample carries this whole dashboard; mine had been rendering an empty Summary sheet. |
| Enriched Register field defaults | Plan said leave Responsible / Due / Close-out blank | Responsible="PC" on every row; Due = Immediate (NCR) / Next audit (Conditional / Unmatched) / N/A (Compliant / Info); Close-out Status="N/A" for Compliant / Info, blank for non-Compliant | Sample fills these deterministically. |
| `_clone_row` insertion order | not specified beyond "deepcopy and append" | append to END of `<w:tbl>` parent. The first attempt used `addnext` after placeholder + `rows[-1]` which silently corrupted every multi-row table (every clone except the last carried the placeholder content) | Caught by visual inspection of the docx; a regression test now locks the failure mode in. |
| Network retry | not specified | retries=2 on `httpx.ConnectError / ReadError / WriteError / TimeoutException / RemoteProtocolError` + HTTP 408 / 429 / 500 / 502 / 503 / 504; immediate raise on other 4xx (auth / billing) | Real-folder run dropped 2 of 21 rows to transient network errors mid-batch; retry recovers cleanly. |
| API error reporting | not specified | HTTP error tag now includes the API's own `error.type` + `error.message` so billing / auth issues surface as e.g. `"http 400 invalid_request_error: Your credit balance is too low"` instead of generic "bad request" | Surfaced when a credit-exhaustion failure was misread as a code defect. |
| Humaniser ruleset | Plan listed banned vocab + em-dash / signposting / sycophantic / emoji / curly-quote / passive-without-named-actor bans | All plan-listed bans are in both system prompts. Plus three additions caught in user review: rule-of-three constructions (with the actual phrases user highlighted as bad — `"available, accessible, and clearly identified"`, `"obscured, kicked, or removed"`); negative parallelism (`"not just X, but Y"`); legalistic connectors (`"contrary to"`, `"in breach of"`, `"in violation of"`, `"non-compliant with"`, `"pursuant to"`) — replaced by plain-English regulation framing (`"WHS Reg X requires Y; the site does not meet that standard"`) | Self-inflicted humaniser violations the original prompt taught the LLM to produce; user caught each on review. |
| Recommendation verb selection | not specified | Paired-verb pattern `"establish and maintain"` for persistent controls (exclusion zones, barriers, edge protection, traffic controls); single-shot `install / mount / fit` for fixtures; `complete / sign` for records; `verify / audit / check` for monitoring; `stop / stand down` for halt-work | User caught `"demarcate"` as too narrow — captures setup but not maintenance obligation. |
| Model | initial: `claude-sonnet-4-5-20250929` | `claude-opus-4-7` per user direction | Most capable model; supports vision. |
| Folder name | strict `YYYY-MM-DD-<RPD or SDG>` | also accepts optional `-NN` sub-id (`2026-05-01-SDG-01`) for split-day visits; sub-id propagates into all output filenames | Multiple visits to the same site on the same day need distinct deliverable names. |
| Runtime preflight | nothing | `PreflightError` raised before row processing when `enrich=True` and `ANTHROPIC_API_KEY` is missing; CLI rc=3 | Operators hit "silent semantic degradation" twice; loud failure prevents both. |
| Findings index table | not in plan | 3-column `# | Finding | Recommendation` table inserted directly under the Findings heading; numbered 1..N matching the per-finding detail blocks; bold header, all-cell borders, header repeats | Reviewer ask 2026-05-06: visible navigation aid. |
| Significance ordering | not in plan | `_significance_score` ranks: HP breach > SWMS gap > plant/public (MOB/CRN/TRF H6/H9) > permit-class (HOT/ASB/CFS/DEM/ELE H6/H9) > generic; secondary axes break ties on status then CCVS tier | Reviewer ask: critical-safety findings appear at the top of the Findings index + detail blocks. |
| Multi-issue row splitting | not in plan | `(1) ... (2) ... (3) ...` composite notes split into separate atomic ObservationRows BEFORE photo-match metadata is consumed; each shares the source photo + timestamp | Auditors record several distinct issues against one photo with leading numerals. |
| Similar-finding merge | not in plan | `merge_similar_findings` consolidates non-Compliant rows that share status + stream + (title equality OR recommendation Jaccard ≥0.5 OR ≥4 content-token overlap OR anchor-phrase like {establish, zone}). Anchor merge crosses streams — an exclusion zone above a steel lift (WAH-H6) and the telehandler beneath it (MOB-H9) are physically the same intervention. Plural-stem trim (`zone` / `zones` collapse) | Reviewer call 2026-05-06: the merge criterion is the recommended action / control intent, not the descriptive title. |
| Manual `--merge` directive | not in plan | Operator can pass `--merge "1,3"` (or `"1,3;5,7,8"`) to consolidate findings by displayed index when the auto-merge can't infer the intent from text alone | Escape hatch for cases the heuristic doesn't catch. |
| Per-finding detail table layout | not in plan | Each finding renders as `#N <title>` heading + 6-row 2-col detail table: `Location | Observation | Regulatory Basis | Hierarchy of Control | Recommendation | Timeframe`. Template label `Required Action` rewritten to `Recommendation` at render time. Tier-prefixed Hierarchy (`Engineering: ...`), urgency-prefixed Recommendation (`Within 7 days – ...`, ≤15 words). | Canonical sample shape; "Recommendation" is the reviewer-facing label. |
| Status of Previous Recs schema | plan: `Recommendation | Required Actions | Status (DD/MM/YY) | Commentary` | New schema: `Date | Recommendations | Status as of <DD-MMM-YYYY> | Comments`. Column widths 2.5 / 6.25 / 2.5 / 6.25 cm. Bold header, header-repeats, all-cell borders. Date format DD-MMM-YYYY (4-digit year). | Reviewer direction 2026-05-06 — table now chains forward audit-by-audit. |
| Prior-recs population | plan: parse prior report into `prior_recs` (deferred) | `populate_prior_recs_table.py` enforces the 10 locked rules: allowed statuses Completed/Partial/Not completed/Not assessed only, "Retired" banned, dates DD-MMM-YYYY, F-refs in every Comments cell, default `Not assessed` when no current-cycle evidence, keep all carry-forwards + append all current-cycle, sort by significance + date. Output as Word tracked changes (author=Claude). | Reviewer direction 2026-05-06. |
| Cover/footer date formats | not in plan | Cover page: `1st May 2026` (ordinal long form). Running footer: `1-may-26` (short, lowercase month, 2-digit year). Same `{{AUDIT_DATE}}` placeholder; substitution branches per part. | Reviewer direction. |
| Table styling consistency | not in plan | Every multi-column table in the report (Findings index, Positive Observations, Status of Previous Recs, Observations Register) uses bold header + header-repeat + all-cell single-line borders. Per-finding detail tables get all-cell borders + bold left-column labels. | Reviewer direction 2026-05-06. |
| RA-code labelling | not in plan | Every TP-NN / HP-NN / HRCW H-NN reference in finding text / recommendation / hierarchy / monitoring / narrative is wrapped: `SDG Project Risk Assessment code: <CODE>`. First occurrence in each block expands the shorthand: `TP-07 (Tilt-Up Panel Erection activity 07)`. Adjacent codes collapse to `... codes: TP-05, HP-06`. Idempotent. | Reviewer ask 2026-05-06 — make every project-RA reference traceable. |
| Plain-English finding titles | not in plan | Vision prompt requires an active-voice sentence ≤12 words, no noun-phrase titles like "EWP Exclusion Zone". Good: "Temporary brace removal proceeded without engineer sign-off". | Reviewer direction. |
| Executive Summary cap | not in plan | Hard-truncated at 20 visual lines (~280 words); LLM prompt also targets ≤140 words. | Reviewer direction. |
| Humaniser hardening | plan banned vocab + em-dash | Banned vocabulary list, banned constructions: em-dash clusters, rule-of-three (with concrete sample phrases the user flagged: `"available, accessible, and clearly identified"`, `"obscured, kicked, or removed"`), negative parallelism, signposting, sycophantic openers/closers, emoji, curly quotes, passive voice without a named actor, legalistic connectors (`"contrary to"`, `"in breach of"`, `"in violation of"`, etc.). Recommendation verb selection: `establish and maintain` for persistent controls, `install/mount/fit` for fixtures, `complete/sign` for records, `verify/audit/check` for monitoring, `stop/stand down` for halt-work. | Reviewer caught self-inflicted humaniser violations on review iterations. |
| Three-phase review workflow | not in plan | Operator-driven review gate: `--enrich-only` writes enriched.xlsx + state JSON and exits → operator reviews/edits → `--from-state` rebuilds docx + staging from edits → operator reviews docx → `--from-report` flows docx edits BACK to enriched + staging xlsx. State JSON persists EnrichedRow rows + xlsx-snapshot fingerprint + `finding_render_order` for phase-3 pairing. | Reviewer ask: human review gate at every export boundary. |
| Image preprocessing cache | not in plan | `_PHOTO_CACHE` keyed by `(source_path, max_edge_px)` so size-control rerenders (1600 → 1200 → 1000 → 800 px) reuse preprocessed bytes. Cache delta reported in size-control diagnostics. | Real-folder runs hit the rerender ladder; cache avoids redundant CPU. |
| Network retry | not in plan | retries=2 on transient HTTP/network errors (ConnectError, ReadError, WriteError, TimeoutException, RemoteProtocolError, HTTP 408/429/500/502/503/504). 4xx other than these (auth, billing, bad request) raise immediately. | Real-folder run dropped 2 of 21 rows to transient errors mid-batch. |
| Forgiving JSON parser | not in plan | `_parse_json_object` strips code fences, then if `json.loads` fails, walks brace depth (respecting strings + escapes) to extract the first balanced `{...}` substring — handles LLM outputs that wrap JSON in prose despite "JSON ONLY" instruction. | Real-folder run had 5/21 rows landing as JSONDecodeError after schema expansion. |
| Legacy fallback retirement | plan default-on legacy matcher | Default vision path skips the audit_checklist.xlsx load entirely. Legacy keyword fallback only fires when operator explicitly passes `--no-enrich AND --checklist <path>`. | Real data: legacy matcher hit 5/21 with one outright misroute; vision is the canonical classifier. |

## Known remaining gaps (not yet shipped)

These are open items between the shipped output and the canonical
samples / the reviewer's stated requirements.

- **Positive Observations row IDs**: shipped — uses `P1 / P2 / P3`
  numbering with `"PIMS Obs N | <reg ref>"` cross-references. Open:
  no further drift here.
- **Observations Register scope**: shipped — register now carries
  every observation (Compliant + non-Compliant) with status
  cross-refs (`"Non-compliant — See F1"`, `"Partially complete —
  See F2"`, `"Compliant"`, `"Noted"`, `"Review at QA"`). Open: no
  further drift.
- **HRCW / Hold Point staging columns**: shipped — `phase`,
  `activity_ref`, `hold_point`, `hrcw` columns added to the staging
  template; vision enricher populates from RA context. Open: no
  further drift.
- **SWMS verification**: shipped — `swms_required` (TRUE/FALSE) and
  `swms_present` (yes/no/unknown) columns + LLM coercion. Open: no
  further drift.
- **Initial / Residual risk axis**: shipped — `initial_risk` /
  `residual_risk` columns with H/M/L canonicalisation; LLM
  forbidden from inventing rating from photo alone. Open: no
  further drift.
- **Image preprocessing cache**: shipped — `_PHOTO_CACHE` keyed
  by `(source_path, max_edge_px)` reuses bytes across size-control
  rerenders; diagnostics report hit/miss delta.
- **Legacy `audit_checklist.xlsx` fallback retirement**: shipped —
  default vision path skips the legacy load entirely; only fires
  on explicit `--no-enrich --checklist <path>`. Could be retired
  fully once vision is locked as the only supported path.

Genuinely open items:

- **Three-phase round-trip merge fidelity**: phase 3 (`--from-report`)
  pairs detail tables to EnrichedRows by `finding_render_order`
  position. If the operator deletes / reorders detail tables in
  Word, the pairing breaks silently. Could be hardened by tagging
  each rendered detail table with an invisible `csv_idx` bookmark
  and reading it back during phase 3.
- **Phase-2 false-positive overrides**: the enriched xlsx
  fingerprint snapshot reduces false positives but a couple of
  rendered-fallback values (Action Description, Due) still register
  as edits because the rendered cell value differs from the
  underlying attribute. Harmless; cosmetic only.
- **Auto-merge calibration**: the {establish, zone} anchor + 4-token
  strong-overlap rule was tuned against one real-folder corpus
  (Unitas, 23 rows). Could over-merge or under-merge on materially
  different audit content; needs a fixture corpus to validate.
- **Vision JSON output schema**: 18 fields requested per row pushes
  the LLM toward occasional prose-wrapped JSON. The forgiving parser
  catches most cases; very rarely a row still fails. A "rewrite to
  strict JSON" retry call would close this.

## File inventory

- **`pims/services/ssa_pipeline.py`** (3457 lines) — Pipeline core: parser, matcher, three builders, enrichment, size-control wrapper, prior-rec parser, Findings #N expansion + index table, xlsx polish, RA-code labelling, significance ordering, anchor/Jaccard merge, manual --merge directives.
- **`pims/services/ssa_checklist_lookup.py`** (279 lines) — Legacy CCVS-keyed lookup over audit_checklist.xlsx. Kept as a deterministic fallback for --no-enrich mode; bypassed when vision is on (default).
- **`pims/services/ssa_ccvs_taxonomy.py`** (100 lines) — Canonical 25-stream x 6-tier CCVS taxonomy. Replaces the audit_checklist.xlsx-derived 01.01 numeric scheme with the real WAH-H6 / SYS-M3 / etc. coding the canonical samples use.
- **`pims/services/ssa_vision_enricher.py`** (730 lines) — Per-row Anthropic vision call (Opus 4.7). Sends downscaled EXIF-normalised photo + observation text + project RA context. Receives status / ccvs_code / finding_title / location / finding / hierarchy_of_control / recommendation / timeframe / phase / activity_ref / hold_point / hrcw / swms_required / swms_present / initial_risk / residual_risk / legal_ref / monitoring_note. Transient-error retry; forgiving JSON parser.
- **`pims/services/ssa_ra_parser.py`** (281 lines) — Project Risk Assessment docx parser. Extracts metadata + 9 hold points + N phase activities; compact-context-block packs into the vision prompt so findings cite HP-04 / TP-05 / HRCW H14 inline.
- **`pims/services/ssa_watcher.py`** (312 lines) — Quiescence-gated folder watcher: settle_seconds + N stable polls; exclusions cover every watcher-owned artifact. Manifest-sha256 idempotency lives in the orchestrator.
- **`pims/scripts/run_ssa_pipeline.py`** (1413 lines) — CLI orchestrator. Folder-name parse (with -NN sub-id), manifest sha256, preflight, freeze escape hatch, sentinels, RA auto-discover, vision wiring, three-phase review workflow (--enrich-only / --from-state / --from-report), --merge directives, .ssa_run.json + .ssa_state.json payloads.
- **`pims/scripts/start_ssa_watcher.py`** (66 lines) — Long-run entry for the watcher. Rotating-file logging.
- **`pims/scripts/populate_prior_recs_table.py`** (628 lines) — Operator-driven post-render edit: populates the Status of Previous Recommendations table with prior carry-forward + current-cycle rows under the 10 locked rules (allowed status set, DD-MMM-YYYY date format, F<n> refs, significance + date sort). Tracked-changes output (author=Claude).
- **`tests/test_ssa_pipeline.py`** (2429 lines) — 99-case regression net. Covers parser, matcher, three builders, size-control + cache, manifest, watcher, vision coercion, RA parser, prior-rec parser, Findings #N expansion + index table, status colour fills, freeze, idempotency, partial-output recovery, anchor/Jaccard/strong-overlap merge, manual --merge directives, three-phase round-trip (--enrich-only / --from-state / --from-report).

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

Pipeline core: parser, matcher, three builders, enrichment, size-control wrapper, prior-rec parser, Findings #N expansion + index table, xlsx polish, RA-code labelling, significance ordering, anchor/Jaccard merge, manual --merge directives.

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
    # Vision-derived per-finding block fields (template's 2-col detail
    # table). ``location`` is a short reviewer-facing place anchor
    # (e.g. "Mile End Road frontage", "Tilt-up panel zone, north
    # elevation"). ``hierarchy_of_control`` names the WHS hierarchy
    # tier the recommendation lands in: Elimination / Substitution /
    # Isolation / Engineering / Administrative / PPE.
    location: str = ""
    hierarchy_of_control: str = ""
    finding_title: str = ""        # 3-6 word descriptive title for #N heading
    timeframe: str = ""            # LLM override for the per-finding Timeframe cell
    # RA cross-reference fields populated by the vision enricher when
    # the project Risk Assessment is loaded. Empty strings when no RA
    # was supplied or the LLM couldn't anchor the row.
    phase: str = ""           # e.g. "6 — Tilt-Up Panel Erection"
    activity_ref: str = ""    # e.g. "TP-05"
    hold_point: str = ""      # e.g. "HP-06"
    hrcw: str = ""            # RA's HRCW codes, e.g. "H14, H15"
    swms_required: bool = False   # gap-5: explicit SWMS verification flag
    swms_present: str = ""        # one of: "yes" / "no" / "unknown" / ""
    initial_risk: str = ""        # gap-6: H/M/L per RA scheme
    residual_risk: str = ""       # gap-6: H/M/L
    # Item 12: when several photos provide evidence for the same
    # consolidated finding, the canonical row carries each contributing
    # csv_idx here for cross-referencing.
    evidence_csv_indices: list[int] = field(default_factory=list)

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

# Image preprocessing cache — Appendix C §C.6 + gap-7. Keyed by
# (source_abs_path_str, max_edge_px). Each entry stores a snapshot of
# the encoded image bytes plus pixel dimensions so callers receive a
# fresh BytesIO cursor on every cache hit (BytesIO is mutable; sharing
# the same instance would let one caller's read() consume bytes for
# the next).
#
# Cache lifetime is the running process — for a single CLI run the
# orchestrator initialises and the watcher likewise. _PHOTO_CACHE_HITS
# / MISSES counters expose how many rerenders the cache saved; the
# size-control wrapper records both into the run diagnostics so we
# can verify on real folders that the cache actually fires.
_PHOTO_CACHE: dict[tuple[str, int], tuple[bytes, str, int, int]] = {}
_PHOTO_CACHE_HITS = 0
_PHOTO_CACHE_MISSES = 0


def _photo_cache_clear() -> None:
    """Drop every cached entry; reset hit/miss counters."""
    global _PHOTO_CACHE_HITS, _PHOTO_CACHE_MISSES
    _PHOTO_CACHE.clear()
    _PHOTO_CACHE_HITS = 0
    _PHOTO_CACHE_MISSES = 0


def _photo_cache_stats() -> dict[str, int]:
    return {
        "hits": _PHOTO_CACHE_HITS,
        "misses": _PHOTO_CACHE_MISSES,
        "entries": len(_PHOTO_CACHE),
    }


def _cache_delta(snapshot: dict[str, int]) -> dict[str, int]:
    """Diff the photo cache against ``snapshot`` so the size-control
    wrapper reports just the hits / misses it drove."""
    now = _photo_cache_stats()
    return {
        "hits":   now["hits"] - snapshot.get("hits", 0),
        "misses": now["misses"] - snapshot.get("misses", 0),
    }


def _preprocess_photo(
    source: Path,
    max_edge_px: int = 1600,
) -> tuple[BytesIO, str, int, int] | None:
    """EXIF-transpose, downscale, recompress.

    Returns (BytesIO, format, width_px, height_px) or None on load
    failure / missing source. ``format`` is ``"JPEG"`` or ``"PNG"``
    (PNG only when the source was PNG with transparency).

    Result is cached by ``(source_path, max_edge_px)`` so the staging
    size-control wrapper can re-render at progressively smaller caps
    without paying the EXIF / downscale / JPEG-encode cost on every
    pass. Cache hits return a fresh ``BytesIO`` cursor over the
    stored bytes.
    """
    global _PHOTO_CACHE_HITS, _PHOTO_CACHE_MISSES
    try:
        cache_key = (str(source.resolve()), int(max_edge_px))
    except Exception:
        cache_key = (str(source), int(max_edge_px))
    cached = _PHOTO_CACHE.get(cache_key)
    if cached is not None:
        _PHOTO_CACHE_HITS += 1
        data, fmt, w, h = cached
        return BytesIO(data), fmt, w, h
    _PHOTO_CACHE_MISSES += 1
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
            data = buf.getvalue()
            _PHOTO_CACHE[cache_key] = (data, fmt, im.width, im.height)
            return BytesIO(data), fmt, im.width, im.height
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
    # gap-4 columns (RA cross-reference)
    "phase": 22,
    "activity_ref": 12,
    "hold_point": 12,
    "hrcw": 14,
    # gap-5 columns (SWMS verification)
    "swms_required": 14,
    "swms_present": 14,
    # gap-6 columns (initial/residual risk axis)
    "initial_risk": 12,
    "residual_risk": 12,
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
    if header_lc == "responsible":
        # Sample defaults to "PC" (Principal Contractor) on every row.
        # Reviewer overrides at QA when a specific subcontractor owns
        # the action.
        return "PC"
    if header_lc == "due":
        # Sample maps status → due slot:
        #   Compliant / Info → N/A
        #   NCR              → Immediate
        #   Conditional      → Next audit
        #   Unmatched        → Next audit (forces review attention)
        if row.conformance_status == "NCR":
            return "Immediate"
        if row.conformance_status in {"Conditional", "Unmatched"}:
            return "Next audit"
        return "N/A"
    if header_lc == "monitoring note":
        return row.monitoring_note
    if header_lc == "close-out status":
        # Compliant / Info rows close-out to N/A immediately; non-
        # Compliant rows leave it blank for QA / close-out tracking.
        if row.conformance_status in {"Compliant", "Info"}:
            return "N/A"
        return ""
    return ""


def _populate_enriched_summary_sheet(
    wb,
    rows: list[EnrichedRow],
    project_name: str,
    site_address: str,
    principal_contractor: str,
    audit_date_ddmmyyyy: str,
) -> None:
    """Write the Summary sheet of PIMS-Enriched per the canonical
    sample. Layout mirrors ``PIMS-Enriched - Sample.xlsx`` Summary:

      r1: title "PIMS Audit Summary — <project>"
      r2-r4: Audit Date / Site / Principal Contractor
      r6: header   "Conformance Status | Count | %"
      r7-r10: Compliant / Conditional / NCR / Info row
      r12: Total
      r14: header  "CCVS Category | Total | NCR | Conditional | Open Actions"
      r15+: per-category breakdown
      r21: heading "Open Actions"
      r22: header  "# | Status | CCVS Code | Action Description | Responsible | Due"
      r23+: one row per non-Compliant / non-Info finding

    No-op when the Summary sheet is missing or empty.
    """
    if "Summary" not in wb.sheetnames:
        return
    ws = wb["Summary"]
    # Wipe any prior data so reruns don't leave stale rows.
    if ws.max_row > 0:
        ws.delete_rows(1, ws.max_row)

    title = (
        f"PIMS Audit Summary — {project_name}"
        if project_name else "PIMS Audit Summary"
    )
    ws.cell(row=1, column=1, value=title)
    ws.cell(row=2, column=1, value="Audit Date")
    ws.cell(row=2, column=2, value=audit_date_ddmmyyyy or "")
    ws.cell(row=3, column=1, value="Site")
    ws.cell(row=3, column=2, value=site_address or "")
    ws.cell(row=4, column=1, value="Principal Contractor")
    ws.cell(row=4, column=2, value=principal_contractor or "")

    # Status conformance count + percentage.
    statuses = ["Compliant", "Conditional", "NCR", "Info", "Unmatched"]
    counts: dict[str, int] = {s: 0 for s in statuses}
    for r in rows:
        s = r.conformance_status
        if s in counts:
            counts[s] += 1
        else:
            counts[s] = counts.get(s, 0) + 1
    total = sum(counts.values())

    ws.cell(row=6, column=1, value="Conformance Status")
    ws.cell(row=6, column=2, value="Count")
    ws.cell(row=6, column=3, value="%")
    for i, s in enumerate(statuses, start=7):
        c = counts.get(s, 0)
        ws.cell(row=i, column=1, value=s)
        ws.cell(row=i, column=2, value=c)
        pct = (c / total * 100) if total else 0
        ws.cell(row=i, column=3, value=f"{pct:.1f}%")
    ws.cell(row=12, column=1, value="Total")
    ws.cell(row=12, column=2, value=total)

    # CCVS category breakdown.
    by_cat: dict[str, dict[str, int]] = {}
    for r in rows:
        cat = r.ccvs_category or "(Unmatched)"
        agg = by_cat.setdefault(
            cat, {"total": 0, "NCR": 0, "Conditional": 0, "Open": 0},
        )
        agg["total"] += 1
        s = r.conformance_status
        if s == "NCR":
            agg["NCR"] += 1
            agg["Open"] += 1
        elif s == "Conditional":
            agg["Conditional"] += 1
            agg["Open"] += 1

    ws.cell(row=14, column=1, value="CCVS Category")
    ws.cell(row=14, column=2, value="Total Observations")
    ws.cell(row=14, column=3, value="NCR")
    ws.cell(row=14, column=4, value="Conditional")
    ws.cell(row=14, column=5, value="Open Actions")
    cat_row = 15
    for cat in sorted(by_cat):
        agg = by_cat[cat]
        ws.cell(row=cat_row, column=1, value=cat)
        ws.cell(row=cat_row, column=2, value=agg["total"])
        ws.cell(row=cat_row, column=3, value=agg["NCR"])
        ws.cell(row=cat_row, column=4, value=agg["Conditional"])
        ws.cell(row=cat_row, column=5, value=agg["Open"])
        cat_row += 1

    # Open Actions list — every NCR / Conditional / Unmatched row
    # appears with the action register fields. Compliant / Info rows
    # are skipped (no action expected).
    actions_start = cat_row + 2
    ws.cell(row=actions_start, column=1, value="Open Actions")
    hdr_row = actions_start + 1
    ws.cell(row=hdr_row, column=1, value="#")
    ws.cell(row=hdr_row, column=2, value="Status")
    ws.cell(row=hdr_row, column=3, value="CCVS Code")
    ws.cell(row=hdr_row, column=4, value="Action Description")
    ws.cell(row=hdr_row, column=5, value="Responsible")
    ws.cell(row=hdr_row, column=6, value="Due")
    next_row = hdr_row + 1
    for idx, r in enumerate(rows, start=1):
        if r.conformance_status not in {"NCR", "Conditional", "Unmatched"}:
            continue
        ws.cell(row=next_row, column=1, value=idx)
        ws.cell(row=next_row, column=2, value=r.conformance_status)
        ws.cell(row=next_row, column=3, value=r.ccvs_code)
        ws.cell(row=next_row, column=4,
                value=r.recommendation or r.action_description or "")
        ws.cell(row=next_row, column=5, value="PC")
        due = "Immediate" if r.conformance_status == "NCR" else "Next audit"
        ws.cell(row=next_row, column=6, value=due)
        next_row += 1

    # Modest column widths so the Summary sheet reads well on open.
    from openpyxl.utils import get_column_letter
    for i, w in enumerate([24, 20, 12, 60, 16, 14], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def build_pims_enriched_xlsx(
    rows: list[EnrichedRow],
    output_path: Path,
    template_path: Path = PIMS_ENRICHED_TEMPLATE,
    project_name: str = "",
    site_address: str = "",
    principal_contractor: str = "",
    audit_date_ddmmyyyy: str = "",
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

    # Populate the Summary sheet — the canonical sample carries a
    # full audit-summary dashboard (status counts + CCVS breakdown +
    # Open Actions list); without this the Summary sheet renders as
    # an empty page.
    _populate_enriched_summary_sheet(
        wb, rows,
        project_name=project_name,
        site_address=site_address,
        principal_contractor=principal_contractor,
        audit_date_ddmmyyyy=audit_date_ddmmyyyy,
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
    # Layout per 2026-05-06 reviewer direction: 4 cols
    # Date | Recommendations | Status (DD-Mon-YY) | Comments
    "prior_recs": ("Date", "Recommendations", "Status", "Comments"),
    "obs_register": ("Obs #", "Photo", "Observation", "Reference", "Status", "Evidence File"),
}

# Per-table column widths in centimetres (from user direction). The
# helper below converts cm → twips (Word's table-cell width unit) and
# writes <w:tcW w:w=... w:type="dxa"/> on every cell in every row of
# the table so the column widths are deterministic across all clones.
_TABLE_COL_WIDTHS_CM: dict[str, tuple[float, ...]] = {
    "positive":     (1.5, 7.0, 9.5),
    # 2026-05-06: Date / Rec / Status / Comments at 2.5 / 6.25 / 2.5 / 6.25 cm
    "prior_recs":   (2.5, 6.25, 2.5, 6.25),
}

# Tables whose first row should:
#   - be bold (header styling)
#   - repeat across page breaks (Word's tblHeader flag)
# Every table in the SSA report carries a bold first row, repeats
# its header on page break, and renders all-cell single-line borders
# (Word's "All" preset). Consistency is the locked styling per the
# 2026-05-06 reviewer direction.
_TABLE_HEADER_BOLD: frozenset[str] = frozenset({
    "positive", "prior_recs", "obs_register",
})
_TABLE_HEADER_REPEAT: frozenset[str] = frozenset({
    "positive", "obs_register", "prior_recs",
})
_TABLE_ALL_BORDERS: frozenset[str] = frozenset({
    "positive", "prior_recs", "obs_register",
})


def _cm_to_twips(cm: float) -> int:
    """1 cm = 567 twips (Word table width unit, 'dxa')."""
    return int(round(cm * 567))


def _apply_all_cell_borders(tbl) -> None:
    """Apply Word's "All" border preset — single-line ½-pt borders on
    every cell edge inside and outside the table. Sets ``<w:tblBorders>``
    on the table-level properties so every row inherits the boundary
    style; per-cell ``<w:tcBorders>`` overrides are left alone.
    """
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    tbl_el = tbl._tbl
    tblPr = tbl_el.find(qn("w:tblPr"))
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        tbl_el.insert(0, tblPr)
    # Drop any pre-existing border block — easier than reconciling.
    existing = tblPr.find(qn("w:tblBorders"))
    if existing is not None:
        tblPr.remove(existing)
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement(f"w:{edge}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), "4")        # ½ pt
        b.set(qn("w:space"), "0")
        b.set(qn("w:color"), "auto")
        borders.append(b)
    tblPr.append(borders)


def _apply_table_format(
    tbl,
    col_widths_cm: tuple[float, ...] | None,
    bold_header: bool,
    repeat_header: bool,
    all_borders: bool = False,
) -> None:
    """Set deterministic column widths, optional bold first row, and
    optional header-repeat-across-pages on a python-docx Table.

    Column widths are written on every row's cell so that cloned rows
    inherit the same widths. ``bold_header`` walks the first row's
    runs and sets ``bold=True``. ``repeat_header`` adds the
    ``<w:tblHeader/>`` element to the first row's ``<w:trPr>`` so
    Word repeats the header on each new page.
    """
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    if col_widths_cm:
        twip_widths = [_cm_to_twips(w) for w in col_widths_cm]
        # Update <w:gridCol> entries on the table's <w:tblGrid> first
        # — Word reads these to size the columns initially.
        grid = tbl._tbl.find(qn("w:tblGrid"))
        if grid is not None:
            grid_cols = grid.findall(qn("w:gridCol"))
            for i, gc in enumerate(grid_cols):
                if i < len(twip_widths):
                    gc.set(qn("w:w"), str(twip_widths[i]))
        # Then write per-cell widths on every row.
        for row in tbl.rows:
            for i, cell in enumerate(row.cells):
                if i >= len(twip_widths):
                    break
                tcPr = cell._tc.get_or_add_tcPr()
                tcW = tcPr.find(qn("w:tcW"))
                if tcW is None:
                    tcW = OxmlElement("w:tcW")
                    tcPr.append(tcW)
                tcW.set(qn("w:w"), str(twip_widths[i]))
                tcW.set(qn("w:type"), "dxa")

    if not tbl.rows:
        return
    header_row = tbl.rows[0]

    if bold_header:
        for cell in header_row.cells:
            for p in cell.paragraphs:
                if p.runs:
                    for r in p.runs:
                        r.bold = True
                else:
                    # Empty paragraph — append a bold run so any
                    # existing header text on a clean cell still
                    # renders bold (defensive; templates carry text).
                    pass

    if repeat_header:
        trPr = header_row._tr.find(qn("w:trPr"))
        if trPr is None:
            trPr = OxmlElement("w:trPr")
            header_row._tr.insert(0, trPr)
        if trPr.find(qn("w:tblHeader")) is None:
            trPr.append(OxmlElement("w:tblHeader"))

    if all_borders:
        _apply_all_cell_borders(tbl)

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
          "date":           prior audit date as "DD-Mon-YY"
                            (parsed from the prior report's filename)
          "recommendation": short summary from prior Observation cell,
          "status":         "" — auditor fills based on what they
                            observe in the current audit,
          "commentary":     "" — auditor fills at QA,
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

    # Pull the prior audit date from the filename so the table's
    # Date column carries "DD-Mon-YY" per the 2026-05-06 layout.
    prior_date = ""
    m = re.search(r"-(\d{6})-(?:RPD|SDG)(?:-\d{2})?\.docx$", path.name)
    if m:
        try:
            from datetime import datetime
            d = datetime.strptime(m.group(1), "%y%m%d")
            prior_date = (
                f"{d.day}-{d.strftime('%b')}-{d.strftime('%y')}"
            )
        except Exception:
            prior_date = ""

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
        if not observation:
            continue
        out.append({
            "date": prior_date,
            "recommendation": observation,
            "status": "",
            "commentary": "",
        })
    return out


def _build_findings_index_table(doc, register_rows: list[EnrichedRow]) -> int:
    """Insert a 2-col index table directly below the "Findings"
    heading paragraph (item 15 of the gap-closure brief).

    Columns: Finding | Recommendation
    One row per detail block, in the same significance order as the
    detail blocks themselves. Uses python-docx's built-in
    ``Table Grid`` style so the table matches the surrounding tables
    visually.

    Returns the count of finding rows written (header excluded);
    ``0`` is a no-op (no Findings heading or no findings).
    """
    from docx.oxml.ns import qn
    body = doc.element.body
    findings_p = None
    for child in body.iterchildren():
        if child.tag != qn("w:p"):
            continue
        text = "".join(t.text or "" for t in child.iter(qn("w:t"))).strip()
        if text == "Findings":
            findings_p = child
            break
    if findings_p is None or not register_rows:
        return 0

    # Build the index table programmatically. python-docx's table
    # API requires inserting through ``Document.add_table`` then
    # moving the element; we do it via XML manipulation so the table
    # lands exactly after the "Findings" heading paragraph.
    from docx.oxml import OxmlElement
    tbl = OxmlElement("w:tbl")

    # tblPr — borders + Table Grid style for visual parity with the
    # surrounding tables.
    tblPr = OxmlElement("w:tblPr")
    tblStyle = OxmlElement("w:tblStyle")
    tblStyle.set(qn("w:val"), "TableGrid")
    tblPr.append(tblStyle)
    tblW = OxmlElement("w:tblW")
    tblW.set(qn("w:w"), "0")
    tblW.set(qn("w:type"), "auto")
    tblPr.append(tblW)
    tbl_borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement(f"w:{edge}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), "4")
        b.set(qn("w:color"), "auto")
        tbl_borders.append(b)
    tblPr.append(tbl_borders)
    tbl.append(tblPr)

    # tblGrid — three columns: # | Finding | Recommendation. The
    # left "#" column is narrow (~1 cm) and matches the numbering on
    # the per-finding detail blocks below the index, so reviewers
    # can navigate from the index row to the detail block by number.
    tbl_grid = OxmlElement("w:tblGrid")
    for w_twips in (567, 5050, 4380):  # ~1.0 cm + ~8.9 cm + ~7.7 cm
        gc = OxmlElement("w:gridCol")
        gc.set(qn("w:w"), str(w_twips))
        tbl_grid.append(gc)
    tbl.append(tbl_grid)

    def _make_cell(text: str, bold: bool = False, width_twips: int = 0):
        tc = OxmlElement("w:tc")
        tcPr = OxmlElement("w:tcPr")
        tcW = OxmlElement("w:tcW")
        tcW.set(qn("w:w"), str(width_twips))
        tcW.set(qn("w:type"), "dxa")
        tcPr.append(tcW)
        tc.append(tcPr)
        p = OxmlElement("w:p")
        if bold:
            pPr = OxmlElement("w:pPr")
            p.append(pPr)
        r = OxmlElement("w:r")
        if bold:
            rPr = OxmlElement("w:rPr")
            b = OxmlElement("w:b")
            rPr.append(b)
            r.append(rPr)
        t = OxmlElement("w:t")
        t.text = text
        t.set(qn("xml:space"), "preserve")
        r.append(t)
        p.append(r)
        tc.append(p)
        return tc

    # Header row.
    header_tr = OxmlElement("w:tr")
    trPr = OxmlElement("w:trPr")
    tbl_header = OxmlElement("w:tblHeader")
    trPr.append(tbl_header)
    header_tr.append(trPr)
    header_tr.append(_make_cell("#", bold=True, width_twips=567))
    header_tr.append(_make_cell("Finding", bold=True, width_twips=5050))
    header_tr.append(_make_cell("Recommendation", bold=True, width_twips=4380))
    tbl.append(header_tr)

    # Data rows — one per finding in register order. The "#" cell
    # numbers each row to match the per-finding detail blocks below
    # (so reviewers can navigate from index to detail by number).
    # The Finding column carries the descriptive title; Recommendation
    # carries the short directive sentence (already tier-prefixed by
    # the vision enricher).
    written = 0
    for idx, row in enumerate(register_rows, start=1):
        title = row.finding_title or row.ccvs_category or "Finding"
        rec = (row.recommendation or row.action_description or "").strip()
        tr = OxmlElement("w:tr")
        tr.append(_make_cell(str(idx), width_twips=567))
        tr.append(_make_cell(title, width_twips=5050))
        tr.append(_make_cell(rec, width_twips=4380))
        tbl.append(tr)
        written += 1

    findings_p.addnext(tbl)
    return written


def _expand_findings_list(doc, register_rows: list[EnrichedRow]) -> int:
    """Materialise the ``Findings`` section per non-Compliant row.

    The canonical template lays each finding out as a heading + a
    6-row 2-col detail table (per the screenshot the user shared):

        #N                        (12pt bold heading)
        +---------------------+----------------+
        | Location            | <site/area>    |
        | Observation         | <finding text> |
        | Regulatory Basis    | <legal_ref>    |
        | Hierarchy of Control| <hierarchy>    |
        | Required Action     | <recommend>    |
        | Timeframe           | <due timeframe>|
        +---------------------+----------------+

    Per R-1.3(e) block-level cloning of (heading + 2-col table) is
    permitted. For idx==1 we mutate the existing pair in-place; for
    idx>=2 we deepcopy and insert before the Status heading so
    iteration order is preserved.

    Returns the number of finding blocks written.
    """
    import copy
    from docx.oxml.ns import qn

    body = doc.element.body

    # Locate the placeholder #1 heading + the 2-col detail table that
    # follows it + the Status of Previous Recommendations heading.
    heading_p = None
    detail_tbl = None
    status_p = None
    for child in body.iterchildren():
        tag = child.tag
        if tag == qn("w:p"):
            text = "".join(t.text or "" for t in child.iter(qn("w:t"))).strip()
            if heading_p is None and text.startswith("#1"):
                heading_p = child
            elif heading_p is not None and text.startswith(
                "Status of Previous Recommendations"
            ):
                status_p = child
                break
        elif tag == qn("w:tbl") and heading_p is not None and detail_tbl is None:
            # The first <w:tbl> after the #1 heading is the per-finding
            # detail block. Confirm by checking it's 2-col and the first
            # row's first cell carries the literal ``Location``.
            first_row = next(child.iter(qn("w:tr")), None)
            if first_row is not None:
                cells = list(first_row.iter(qn("w:tc")))
                if len(cells) == 2:
                    label_text = "".join(
                        t.text or "" for t in cells[0].iter(qn("w:t"))
                    ).strip()
                    if label_text.startswith("Location"):
                        detail_tbl = child
    if heading_p is None or status_p is None or detail_tbl is None:
        return 0

    if not register_rows:
        _set_paragraph_runs_text(heading_p, "No findings recorded.")
        # Wipe the detail table's right-column cells.
        for row in detail_tbl.iter(qn("w:tr")):
            cells = list(row.iter(qn("w:tc")))
            if len(cells) >= 2:
                _set_cell_text_oxml(cells[1], "")
        return 0

    from docx.table import Table

    def _format_detail_tbl(tbl_el):
        """Apply consistent styling to a per-finding detail table —
        all-cell borders, bold left-column labels."""
        tbl = Table(tbl_el, doc)
        _apply_all_cell_borders(tbl)
        # Bold the left-column label cells (Location / Observation /
        # Regulatory Basis / Hierarchy of Control / Recommendation /
        # Timeframe). Right-column values stay normal weight.
        for r in tbl.rows:
            if not r.cells:
                continue
            for p in r.cells[0].paragraphs:
                for run in p.runs:
                    run.bold = True

    written = 0
    for idx, row in enumerate(register_rows, start=1):
        title = _finding_heading_text(idx, row)
        if idx == 1:
            _set_paragraph_runs_text(heading_p, title)
            _set_paragraph_space_before(heading_p, twentieths_of_a_point=240)
            _populate_finding_detail_table(detail_tbl, row)
            _format_detail_tbl(detail_tbl)
        else:
            new_h = copy.deepcopy(heading_p)
            new_t = copy.deepcopy(detail_tbl)
            _set_paragraph_runs_text(new_h, title)
            _set_paragraph_space_before(new_h, twentieths_of_a_point=240)
            _populate_finding_detail_table(new_t, row)
            _format_detail_tbl(new_t)
            status_p.addprevious(new_h)
            status_p.addprevious(new_t)
        written += 1
    return written


def _set_paragraph_space_before(p_element, twentieths_of_a_point: int) -> None:
    """Add ``<w:spacing w:before="N"/>`` so each cloned ``#N`` heading
    breathes from the previous finding's table. ``N`` is in
    twentieths of a point — 240 ≈ 12 pt of leading whitespace."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    pPr = p_element.find(qn("w:pPr"))
    if pPr is None:
        pPr = OxmlElement("w:pPr")
        p_element.insert(0, pPr)
    spacing = pPr.find(qn("w:spacing"))
    if spacing is None:
        spacing = OxmlElement("w:spacing")
        pPr.append(spacing)
    spacing.set(qn("w:before"), str(twentieths_of_a_point))


# Row-label → EnrichedRow attribute resolver. Header (left-cell) text
# is matched case-insensitively against the canonical labels.
_FINDING_DETAIL_LABEL_TO_VALUE = {
    "location": lambda r: r.location or "",
    "observation": lambda r: (
        r.finding or r.observation_text_clean or r.obs.observation_text or ""
    ),
    "regulatory basis": lambda r: r.legal_ref or "",
    "hierarchy of control": lambda r: r.hierarchy_of_control or "",
    # Template label was "Required Action"; canonical reviewer wording
    # is "Recommendation". Keep both as match keys so the resolver
    # works whether the template was relabelled in-place or not.
    "required action": lambda r: (r.recommendation or r.action_description or ""),
    "recommendation": lambda r: (r.recommendation or r.action_description or ""),
    "timeframe": lambda r: _timeframe_for(r),
}

# Label rewrites applied to the LEFT cell at render time. Lets the
# template ship with the legacy "Required Action" wording while the
# rendered deliverable reads with the canonical "Recommendation".
_FINDING_DETAIL_LABEL_REWRITES: dict[str, str] = {
    "Required Action": "Recommendation",
}


def _timeframe_for(row: EnrichedRow) -> str:
    """Plain-English timeframe label for the per-finding detail table.

    LLM-supplied ``row.timeframe`` wins when set (lets the model say
    ``Ongoing`` for monitoring items, ``Next audit`` for record-keeping
    follow-ups). Falls back to a status-derived default for rows the
    LLM didn't classify.
    """
    if row.timeframe:
        return row.timeframe
    if row.conformance_status == "NCR":
        return "Immediate"
    if row.conformance_status == "Conditional":
        return "Within 7 days"
    if row.conformance_status == "Info":
        return "Monitor"
    return "N/A"


def _populate_finding_detail_table(tbl_element, row: EnrichedRow) -> None:
    """Walk the cloned 2-col table, write each label's value into
    that row's right cell. Left cells (the labels) inherit the
    template wording; ``_FINDING_DETAIL_LABEL_REWRITES`` rewrites a
    handful of legacy labels at render time (e.g. ``Required Action``
    → ``Recommendation``) without touching the frozen template."""
    from docx.oxml.ns import qn
    for tr in tbl_element.iter(qn("w:tr")):
        cells = list(tr.iter(qn("w:tc")))
        if len(cells) < 2:
            continue
        label_raw = "".join(
            t.text or "" for t in cells[0].iter(qn("w:t"))
        ).strip()
        # Rewrite the label cell first so the rendered deliverable
        # carries the reviewer-facing wording.
        new_label = _FINDING_DETAIL_LABEL_REWRITES.get(label_raw)
        if new_label and new_label != label_raw:
            _set_cell_text_oxml(cells[0], new_label)
        # Resolver lookup is case-insensitive against the ORIGINAL
        # template label so existing templates keep matching even
        # after the relabel.
        resolver = _FINDING_DETAIL_LABEL_TO_VALUE.get(label_raw.lower())
        if resolver is None:
            continue
        _set_cell_text_oxml(cells[1], resolver(row))


def _set_cell_text_oxml(tc_element, text: str) -> None:
    """Replace the cell's text content while preserving the first
    paragraph's pPr/rPr (so the cloned cell inherits the template's
    font, alignment, indent). Drops trailing paragraphs and runs to
    avoid placeholder ghosts."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    paragraphs = list(tc_element.iter(qn("w:p")))
    if not paragraphs:
        # No paragraph — Word will reject the cell. Append one with
        # the text. python-docx auto-fixes on save but we do it here
        # to keep the XML well-formed in flight.
        p = OxmlElement("w:p")
        r = OxmlElement("w:r")
        t = OxmlElement("w:t")
        t.text = text
        t.set(qn("xml:space"), "preserve")
        r.append(t)
        p.append(r)
        tc_element.append(p)
        return
    first_p = paragraphs[0]
    _set_paragraph_runs_text(first_p, text)
    # Remove sibling paragraphs after the first to avoid stale lines.
    for extra in paragraphs[1:]:
        parent = extra.getparent()
        if parent is not None:
            parent.remove(extra)


# --- RA code labelling (items 9 + 14) ------------------------------------
#
# Reviewer requirement: every reference to an RA code (TP-07, HP-04,
# H14, etc.) inside finding text / recommendations / hierarchy / staging
# narrative should carry the explicit prefix
#   "SDG Project Risk Assessment code: <CODE>"
# and the first occurrence inside any one block of text expands the
# shorthand once (e.g. "TP-07 (Tilt-up panel activity 07)") so the
# downstream reader doesn't need to flip back to the RA to decode it.
#
# RA-derived expansions come from the parsed RiskAssessment object;
# HRCW codes use a static map (the RA's HRCW column carries them as
# free-text descriptions, not a structured table).

# RA reference patterns. Activity refs: 2-letter package + 2-3 digits +
# optional letter suffix (TP-01A, MR-02). HP codes: HP-01 .. HP-99.
# HRCW codes: H01..H99 (not preceded by a hyphen, so we don't match
# CCVS tier suffix like "WAH-H6").
_RA_ACTIVITY_RE = re.compile(r"\b([A-Z]{2}-\d{1,3}[A-Z]?)\b")
_RA_HP_RE = re.compile(r"\b(HP-\d{2})\b")
_RA_HRCW_RE = re.compile(r"(?<![-A-Za-z0-9])(H\d{1,2})\b")

# Static HRCW expansions — H-codes from NSW WHS Reg 2017 cl.291 plus
# the project-RA's H01-H15 set used in Unitas_Risk_Assessment_all.docx.
_HRCW_EXPANSIONS: dict[str, str] = {
    "H01": "fall risk",
    "H02": "telecommunication tower work",
    "H03": "demolition",
    "H04": "asbestos disturbance",
    "H05": "structural alteration",
    "H06": "confined space",
    "H07": "trench / shaft >1.5 m",
    "H08": "tunnels",
    "H09": "explosives",
    "H10": "pressurised gas distribution",
    "H11": "energised electrical installations",
    "H12": "contaminated atmospheres",
    "H13": "tilt-up or precast concrete",
    "H14": "traffic corridor",
    "H15": "powered mobile plant",
    "H16": "extreme temperatures",
    "H17": "drowning hazards",
    "H18": "diving work",
}


def _ra_code_expansion(code: str, ra) -> str:
    """Plain-English expansion of an RA code, used on first occurrence.

    ``ra`` is a ``RiskAssessment`` (or None when no RA was loaded).
    Returns the parenthesised expansion text WITHOUT the surrounding
    parens (caller wraps); empty string when no expansion is known.
    """
    code = code.upper()
    if code.startswith("HP-"):
        if ra is not None:
            for hp in getattr(ra, "hold_points", []) or []:
                if hp.code == code:
                    return f"Hold Point {code[3:]}: {hp.description}"
        return f"Hold Point {code[3:]}"
    if "-" in code and code[:2].isalpha():
        # Activity ref like TP-07. Look up in the RA's activities list
        # and use the phase title + activity number for the expansion.
        if ra is not None:
            for act in getattr(ra, "activities", []) or []:
                if act.ref == code:
                    phase_title = act.phase
                    # Strip the leading "N — " from "6 — Tilt-Up Panel
                    # Erection" so the parens read cleanly.
                    for sep in (" — ", " – ", " - "):
                        if sep in phase_title:
                            phase_title = phase_title.split(sep, 1)[1]
                            break
                    suffix = code.split("-", 1)[1]
                    return f"{phase_title.strip()} activity {suffix}"
        return ""
    if code in _HRCW_EXPANSIONS:
        return f"HRCW {_HRCW_EXPANSIONS[code]}"
    return ""


_RA_LABEL_PREFIX = "SDG Project Risk Assessment code"


def apply_ra_code_labels(text: str, ra=None) -> str:
    """Wrap RA codes in the canonical reviewer-facing prefix.

    First occurrence of each distinct code in ``text`` becomes:
        SDG Project Risk Assessment code: TP-07 (Tilt-up Panel
        Erection activity 07)
    Subsequent occurrences (if any in the same block) become:
        SDG Project Risk Assessment code: TP-07
    Codes already wrapped in the prefix are left alone (idempotent
    on re-runs / chained labelling). Multiple consecutive codes that
    cluster in one phrase collapse into a single
    "SDG Project Risk Assessment codes: A, B, C" prefix on first hit.
    """
    if not text:
        return text
    if _RA_LABEL_PREFIX in text:
        return text  # already labelled

    # Collect every code occurrence with span and category.
    matches: list[tuple[int, int, str, str]] = []  # (start, end, code, kind)
    for m in _RA_HP_RE.finditer(text):
        matches.append((m.start(), m.end(), m.group(1), "hp"))
    for m in _RA_ACTIVITY_RE.finditer(text):
        code = m.group(1)
        if code.startswith("HP-"):
            continue  # already covered by _RA_HP_RE
        matches.append((m.start(), m.end(), code, "activity"))
    for m in _RA_HRCW_RE.finditer(text):
        matches.append((m.start(), m.end(), m.group(1), "hrcw"))
    if not matches:
        return text

    matches.sort(key=lambda t: t[0])

    # Cluster matches that sit within a small gap (e.g. "HP-04 / TP-05"
    # or "TP-05 (HRCW H14)") into one labelled phrase. Threshold: 6
    # characters between match end and next match start (covers
    # ", ", " / ", " (HRCW ", " and ").
    clusters: list[list[tuple[int, int, str, str]]] = []
    for tup in matches:
        if not clusters:
            clusters.append([tup])
            continue
        prev_end = clusters[-1][-1][1]
        if tup[0] - prev_end <= 6:
            clusters[-1].append(tup)
        else:
            clusters.append([tup])

    seen: set[str] = set()
    out_parts: list[str] = []
    cursor = 0
    for cluster in clusters:
        c_start = cluster[0][0]
        c_end = cluster[-1][1]
        out_parts.append(text[cursor:c_start])
        codes = [c for _s, _e, c, _k in cluster]
        # First-use expansions for any unseen codes in this cluster.
        expansions: list[str] = []
        for code in codes:
            if code in seen:
                continue
            seen.add(code)
            exp = _ra_code_expansion(code, ra)
            if exp:
                expansions.append(f"{code} ({exp})")
            else:
                expansions.append(code)
        # Any later codes in the cluster that were already seen still
        # need to appear — we emit them as bare codes alongside the
        # expansions, in original order.
        rendered_codes: list[str] = []
        seen_in_cluster: set[str] = set()
        for code in codes:
            if code in seen_in_cluster:
                continue
            seen_in_cluster.add(code)
            # Find the matching expansion (if we just emitted one).
            for ex in expansions:
                if ex.startswith(code):
                    rendered_codes.append(ex)
                    break
            else:
                rendered_codes.append(code)
        prefix_word = (
            _RA_LABEL_PREFIX
            if len(rendered_codes) == 1
            else _RA_LABEL_PREFIX + "s"
        )
        out_parts.append(f"{prefix_word}: {', '.join(rendered_codes)}")
        cursor = c_end
    out_parts.append(text[cursor:])
    return "".join(out_parts)


def cap_executive_summary(text: str, max_lines: int = 20) -> str:
    """Hard-cap the Executive Summary to ``max_lines`` lines.

    "Lines" is interpreted as visual lines on the rendered page. We
    approximate by counting ~14 words per line on A4 with the SSA
    template's body width and capping the input at
    ``max_lines * 14`` words. The text is truncated at the last
    sentence boundary that fits, and an ellipsis is NOT added — the
    LLM prompt already targets ≤140 words; this is a defensive
    safety net for when the model overshoots.
    """
    if not text:
        return text
    words_per_line = 14
    word_cap = max_lines * words_per_line
    words = text.split()
    if len(words) <= word_cap:
        return text
    truncated = " ".join(words[:word_cap])
    # Trim back to the last sentence end so we don't end mid-thought.
    for marker in (". ", "? ", "! "):
        cut = truncated.rfind(marker)
        if cut > word_cap // 2:
            return truncated[:cut + 1]
    return truncated


def apply_manual_merges(
    indexed_rows: list[tuple[int, EnrichedRow]],
    merge_groups: list[list[int]],
) -> list[tuple[int, EnrichedRow]]:
    """Apply operator-supplied merge directives by displayed-finding
    number (1-based, matching the index-table numbering reviewers see
    in the rendered docx).

    ``merge_groups`` is a list of groups; each group is a list of
    1-based indices into ``indexed_rows`` after significance sort.
    Within a group, the lowest index becomes the canonical row;
    other rows are merged into it (their titles / recommendations /
    findings are concatenated and their csv indices are folded into
    ``evidence_csv_indices``). Other rows are then dropped from the
    list.

    Indices outside the range or duplicated across groups are
    silently ignored — operator typos shouldn't crash the pipeline.
    """
    if not merge_groups or not indexed_rows:
        return indexed_rows
    drop: set[int] = set()
    for group in merge_groups:
        if len(group) < 2:
            continue
        valid = [
            i for i in group
            if 1 <= i <= len(indexed_rows) and (i - 1) not in drop
        ]
        if len(valid) < 2:
            continue
        valid.sort()
        canonical_idx = valid[0] - 1  # 0-based
        canonical = indexed_rows[canonical_idx][1]
        merged_titles = [canonical.finding_title]
        merged_recs = [canonical.recommendation] if canonical.recommendation else []
        merged_findings = [canonical.finding] if canonical.finding else []
        evidence_indices: list[int] = list(
            canonical.evidence_csv_indices
            or [indexed_rows[canonical_idx][0]]
        )
        for other_pos in valid[1:]:
            other_pair = indexed_rows[other_pos - 1]
            other_csv_idx, other_row = other_pair
            if other_row.finding_title and other_row.finding_title not in merged_titles:
                merged_titles.append(other_row.finding_title)
            if other_row.recommendation and other_row.recommendation not in merged_recs:
                merged_recs.append(other_row.recommendation)
            if other_row.finding and other_row.finding not in merged_findings:
                merged_findings.append(other_row.finding)
            if other_csv_idx not in evidence_indices:
                evidence_indices.append(other_csv_idx)
            for fold_idx in (other_row.evidence_csv_indices or []):
                if fold_idx not in evidence_indices:
                    evidence_indices.append(fold_idx)
            drop.add(other_pos - 1)
        # Compose the merged values back onto the canonical row.
        canonical.finding_title = "; ".join(t for t in merged_titles if t)
        canonical.recommendation = " | ".join(r for r in merged_recs if r)
        canonical.finding = "\n\n".join(f for f in merged_findings if f)
        canonical.evidence_csv_indices = evidence_indices
        # Surface the consolidation in monitoring_note so the reviewer
        # sees which evidence rows were folded in.
        extra = "Consolidated finding — Evidence: " + ", ".join(
            f"PIMS Obs {i}" for i in evidence_indices
        )
        if canonical.monitoring_note:
            if "Consolidated finding" not in canonical.monitoring_note:
                canonical.monitoring_note = (
                    f"{canonical.monitoring_note} | {extra}"
                )
        else:
            canonical.monitoring_note = extra
    return [pair for i, pair in enumerate(indexed_rows) if i not in drop]


def parse_merge_argument(arg: str) -> list[list[int]]:
    """Parse an operator merge directive into groups of 1-based indices.

    Format: ``"1,3"`` for one group; ``"1,3;5,7,8"`` for multiple.
    Whitespace tolerant. Invalid tokens are dropped silently.
    """
    if not arg:
        return []
    out: list[list[int]] = []
    for chunk in arg.split(";"):
        group: list[int] = []
        for tok in chunk.split(","):
            tok = tok.strip()
            if tok.isdigit():
                group.append(int(tok))
        if group:
            out.append(group)
    return out


# Tokens dropped before measuring recommendation similarity. The
# urgency prefix carries no signal about the actual control intent;
# function words and generic glue words also dilute the Jaccard score.
_RECOMMENDATION_STOPWORDS: frozenset[str] = frozenset({
    "immediate", "ongoing", "the", "a", "an", "of", "for", "and", "or",
    "to", "with", "in", "on", "at", "is", "be", "are", "was", "by",
    "from", "as", "this", "that", "any", "all", "until", "before",
    "after", "while", "when", "while", "site", "manager", "site-manager",
    "within", "days", "day", "next", "audit",
})


def _stem_plural(token: str) -> str:
    """Trim trailing ``s`` on tokens longer than 4 characters so
    plural forms collapse to their singular for similarity scoring
    (``zones`` → ``zone``, ``spotters`` → ``spotter``,
    ``signatures`` → ``signature``). Conservative — leaves short
    tokens (``gas``, ``has``) and ``-ss`` words (``access``) alone.
    """
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _recommendation_tokens(text: str) -> set[str]:
    """Return content-word tokens of a Recommendation cell.

    Strips the leading urgency phrase ("Immediate – ", "Within 7 days
    – ") because that timing prefix carries no information about the
    physical control the recommendation is asking for. Lowercases,
    drops stopwords, drops short tokens, and stems trailing plural
    ``s`` so ``zone`` / ``zones`` and ``spotter`` / ``spotters``
    collapse for matching.
    """
    if not text:
        return set()
    s = text.lower()
    # Strip an "Immediate – ", "within 7 days – ", "next audit – " etc.
    # urgency prefix.
    for sep in (" – ", " - ", " — "):
        if sep in s:
            head, _, rest = s.partition(sep)
            head_words = head.split()
            if head_words and head_words[0] in {
                "immediate", "within", "next", "ongoing", "audit",
            }:
                s = rest
                break
    tokens = re.findall(r"[a-z][a-z0-9-]+", s)
    return {
        _stem_plural(t) for t in tokens
        if len(t) >= 3 and t not in _RECOMMENDATION_STOPWORDS
    }


_RECOMMENDATION_JACCARD_THRESHOLD = 0.5
_RECOMMENDATION_OVERLAP_MIN = 3

# Absolute content-token overlap that triggers a merge regardless of
# Jaccard. Catches cases where the recommendations share a strong
# common subject (e.g. ``daily``, ``register``, ``time-out``,
# ``entries``) but the Jaccard score is diluted by length. Empirically
# tuned against real-folder content — 4 tokens is meaningful.
_RECOMMENDATION_STRONG_OVERLAP = 4

# Anchor-phrase merge — when BOTH recommendations contain every token
# in an anchor set, treat them as the same physical control intent
# even when the surrounding wording diverges. Reviewer call:
# "we are only merging because very similar and results in
# establishing a work zone" — the canonical control is the
# work/exclusion zone, regardless of whether the recommendation
# emphasises the spotter, the suspended-load aspect, or the stop-
# work directive.
_MERGE_ANCHORS: tuple[frozenset[str], ...] = (
    # exclusion-zone control intent — present whether the
    # recommendation says "establish exclusion zone", "stop until
    # exclusion zone in place", or "maintain exclusion zone".
    frozenset({"exclusion", "zone"}),
    # generic "establish [work] zone" — catches recommendations that
    # mention a work zone without the canonical "exclusion" word.
    frozenset({"establish", "zone"}),
    # barricaded boundary (stem match for "barricade", "barricaded",
    # "barricades")
    frozenset({"establish", "barricad"}),
    # energy isolation
    frozenset({"isolate", "energy"}),
)


def _has_anchor_match(a: str, b: str) -> bool:
    """Return True iff some anchor set is fully present in BOTH
    recommendation strings (post-tokenise, with stem-style prefix
    matching for tokens that end in a partial stem)."""
    ta = _recommendation_tokens(a)
    tb = _recommendation_tokens(b)
    if not ta or not tb:
        return False
    for anchor in _MERGE_ANCHORS:
        ok_a = all(_anchor_present(stem, ta) for stem in anchor)
        ok_b = all(_anchor_present(stem, tb) for stem in anchor)
        if ok_a and ok_b:
            return True
    return False


def _anchor_present(stem: str, tokens: set[str]) -> bool:
    """Token-set membership with prefix-stem matching.

    ``barricad`` matches ``barricaded`` / ``barricade`` / ``barricades``
    by checking that any token in the set starts with the stem.
    """
    for tok in tokens:
        if tok == stem or tok.startswith(stem):
            return True
    return False


def _recommendation_jaccard(a: str, b: str) -> float:
    """Jaccard similarity between two recommendation strings on the
    content-token set. Returns 0.0 when either side is empty."""
    ta = _recommendation_tokens(a)
    tb = _recommendation_tokens(b)
    if not ta or not tb:
        return 0.0
    inter = ta & tb
    if len(inter) < _RECOMMENDATION_OVERLAP_MIN:
        return 0.0
    union = ta | tb
    return len(inter) / len(union) if union else 0.0


def _recommendation_strong_overlap(a: str, b: str) -> bool:
    """Absolute-overlap merge trigger: when the two recommendations
    share at least ``_RECOMMENDATION_STRONG_OVERLAP`` distinct content
    tokens, treat as the same control intent regardless of Jaccard
    score (which can be diluted when one side carries extra qualifying
    text)."""
    ta = _recommendation_tokens(a)
    tb = _recommendation_tokens(b)
    if not ta or not tb:
        return False
    return len(ta & tb) >= _RECOMMENDATION_STRONG_OVERLAP


def merge_similar_findings(
    indexed_rows: list[tuple[int, EnrichedRow]],
) -> list[tuple[int, EnrichedRow]]:
    """Consolidate materially similar non-Compliant findings.

    Two rows are "similar" when they share BOTH:
      - conformance_status (NCR / Conditional / Info)
      - ccvs_code stream prefix (e.g. both MOB-*, both WAH-*)
    AND at least one of:
      - identical finding_title (case-insensitive)
      - recommendation Jaccard ≥ 0.5 with ≥3 content tokens overlap.
        Reviewer-driven: when two findings prescribe the same physical
        control ("establish and maintain an exclusion zone with a
        spotter" vs "establish and maintain an exclusion zone beneath
        suspended steel"), they are operationally one finding even if
        the descriptive titles differ.

    The first row in significance order becomes the canonical row;
    subsequent similar rows have their evidence references appended
    to the canonical row's ``monitoring_note`` ("Evidence also: <fn>")
    and their photo csv_idx folded into ``evidence_csv_indices``.
    Compliant rows are NOT merged — Positive Observations needs each
    one to render in the table separately.
    """
    if not indexed_rows:
        return indexed_rows

    canonical: list[tuple[int, EnrichedRow]] = []
    for csv_idx, row in indexed_rows:
        if row.conformance_status == "Compliant":
            canonical.append((csv_idx, row))
            continue
        stream = row.ccvs_code.split("-", 1)[0] if "-" in row.ccvs_code else row.ccvs_code
        match_pos = -1
        for pos, (_idx, c_row) in enumerate(canonical):
            if c_row.conformance_status != row.conformance_status:
                continue
            c_stream = (
                c_row.ccvs_code.split("-", 1)[0]
                if "-" in c_row.ccvs_code else c_row.ccvs_code
            )
            same_stream = c_stream == stream
            # Title equality OR recommendation similarity — both
            # require the same stream because the same descriptive
            # phrase shouldn't auto-cross stream boundaries.
            same_title = same_stream and (
                row.finding_title and c_row.finding_title
                and row.finding_title.strip().lower()
                == c_row.finding_title.strip().lower()
            )
            similar_rec = same_stream and (
                _recommendation_jaccard(row.recommendation, c_row.recommendation)
                >= _RECOMMENDATION_JACCARD_THRESHOLD
                or _recommendation_strong_overlap(
                    row.recommendation, c_row.recommendation,
                )
            )
            # Anchor-phrase merge: when both recommendations carry one
            # of the canonical control-intent anchors (establish ...
            # zone, isolate energy, etc.), treat them as the same
            # finding REGARDLESS of CCVS stream. Reviewer's call:
            # an exclusion-zone control above a steel lift (WAH-H6)
            # and the telehandler beneath it (MOB-H9) are physically
            # the same intervention even though the streams differ.
            anchor_match = _has_anchor_match(
                row.recommendation, c_row.recommendation,
            )
            if same_title or similar_rec or anchor_match:
                match_pos = pos
                break
        if match_pos < 0:
            row.evidence_csv_indices = [csv_idx]
            canonical.append((csv_idx, row))
        else:
            _t_idx, target_row = canonical[match_pos]
            target_row.evidence_csv_indices = list(
                target_row.evidence_csv_indices or []
            ) + [csv_idx]
            extra = f"Evidence also: PIMS Obs {csv_idx}"
            if target_row.monitoring_note:
                if extra not in target_row.monitoring_note:
                    target_row.monitoring_note = (
                        f"{target_row.monitoring_note} | {extra}"
                    )
            else:
                target_row.monitoring_note = extra
    return canonical


def apply_ra_labels_to_rows(
    rows: list[EnrichedRow], ra=None,
) -> None:
    """Apply ``apply_ra_code_labels`` in-place to every text field of
    every EnrichedRow. Idempotent — pre-labelled text is left alone.
    Called once by the orchestrator after vision enrichment so all
    three builders (enriched xlsx / docx / staging xlsx) see the
    labelled output consistently."""
    for row in rows:
        row.finding = apply_ra_code_labels(row.finding, ra=ra)
        row.observation_text_clean = apply_ra_code_labels(
            row.observation_text_clean, ra=ra,
        )
        row.recommendation = apply_ra_code_labels(row.recommendation, ra=ra)
        row.hierarchy_of_control = apply_ra_code_labels(
            row.hierarchy_of_control, ra=ra,
        )
        row.monitoring_note = apply_ra_code_labels(
            row.monitoring_note, ra=ra,
        )


def _significance_score(row: EnrichedRow) -> tuple[int, int, int]:
    """Significance ranking key — smaller tuple sorts first.

    Highest priority themes (from item 10 of the gap-closure brief):
      - hold-point breaches            (HP-XX referenced in finding/
                                        recommendation/hold_point field)
      - HRCW activity not on a SWMS    (swms_required AND swms_present
                                        in {"no", "unknown", ""})
      - uncontrolled plant / public
        interface                      (CCVS streams MOB / CRN / TRF
                                        with H6/H9 tier)
      - critical authorisation /
        permit breaches                (HOT-H6/H9, ELE-H6/H9, ASB-*,
                                        CFS-*, DEM-*)

    Secondary axes (used to break ties):
      - status severity rank: NCR > Conditional > Info > Compliant > Unmatched
      - tier severity:        H9 > H6 > M3 > M4 > L1 > L2 > ""
    """
    finding_blob = " ".join((
        row.finding or "",
        row.recommendation or "",
        row.hold_point or "",
        row.activity_ref or "",
    )).upper()
    has_hp = "HP-" in finding_blob

    swms_gap = bool(
        row.swms_required and row.swms_present in ("", "no", "unknown")
    )

    # Plant / public interface ↔ MOB, CRN, TRF streams at H6/H9.
    plant_public = False
    if row.ccvs_code:
        stream = row.ccvs_code.split("-", 1)[0]
        tier = row.ccvs_code.split("-", 1)[-1] if "-" in row.ccvs_code else ""
        if stream in {"MOB", "CRN", "TRF"} and tier in {"H6", "H9"}:
            plant_public = True

    # Critical authorisation / permit streams.
    permit_breach = False
    if row.ccvs_code:
        stream = row.ccvs_code.split("-", 1)[0]
        tier = row.ccvs_code.split("-", 1)[-1] if "-" in row.ccvs_code else ""
        if stream in {"HOT", "ASB", "CFS", "DEM"} and tier in {"H6", "H9"}:
            permit_breach = True
        if stream == "ELE" and tier in {"H6", "H9"}:
            permit_breach = True

    # Primary key: high-priority theme rank (0 = highest).
    if has_hp:
        primary = 0
    elif swms_gap and row.conformance_status in {"NCR", "Conditional"}:
        primary = 1
    elif plant_public:
        primary = 2
    elif permit_breach:
        primary = 3
    else:
        primary = 4

    status_rank = {
        "NCR": 0, "Conditional": 1, "Info": 2, "Unmatched": 3, "Compliant": 4,
    }.get(row.conformance_status, 5)

    tier_rank = {
        "H9": 0, "H6": 1, "M3": 2, "M4": 3, "L1": 4, "L2": 5, "": 6,
    }
    tier_key = tier_rank.get(row.ccvs_code.split("-", 1)[-1] if "-" in row.ccvs_code else "", 6)

    return (primary, status_rank, tier_key)


def sort_register_by_significance(
    rows: list[tuple[int, EnrichedRow]],
) -> list[tuple[int, EnrichedRow]]:
    """Sort the register-bound rows by significance score, leaving
    csv_idx attached so cross-references still resolve."""
    return sorted(rows, key=lambda pair: _significance_score(pair[1]))


def _register_status_text(conformance_status: str, finding_ref: str) -> str:
    """Status cell text for the Observations Register row.

    Aligned with the canonical sample wording:
      - Compliant            → "Compliant"
      - Info                 → "Noted"
      - NCR + Findings ref   → "Non-compliant — See F<N>"
      - NCR alone            → "NCR"
      - Conditional + ref    → "Partially complete — See F<N>"
      - Conditional alone    → "Conditional"
      - Unmatched            → "Review at QA"
    """
    if conformance_status == "Compliant":
        return "Compliant"
    if conformance_status == "Info":
        return "Noted"
    if conformance_status == "NCR":
        return f"Non-compliant — See {finding_ref}" if finding_ref else "NCR"
    if conformance_status == "Conditional":
        return f"Partially complete — See {finding_ref}" if finding_ref else "Conditional"
    if conformance_status == "Unmatched":
        return "Review at QA"
    return conformance_status or ""


def _to_long_date(ddmmyyyy: str) -> str:
    """``01/05/2026`` → ``1 May 2026``. Returns ``""`` on parse failure.

    Avoids platform-specific strftime tokens (``%-d`` POSIX vs ``%#d``
    Windows) by composing the day integer manually.
    """
    if not ddmmyyyy:
        return ""
    try:
        from datetime import datetime
        dt = datetime.strptime(ddmmyyyy, "%d/%m/%Y")
        return f"{dt.day} {dt.strftime('%B %Y')}"
    except Exception:
        return ""


def _ordinal_suffix(day: int) -> str:
    """1 → ``st``, 2 → ``nd``, 3 → ``rd``, 4-20 → ``th``, etc."""
    if 10 <= day % 100 <= 20:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


def _to_ordinal_date(ddmmyyyy: str) -> str:
    """``01/05/2026`` → ``1st May 2026``. Reviewer-facing cover-page form.

    Returns ``""`` on parse failure.
    """
    if not ddmmyyyy:
        return ""
    try:
        from datetime import datetime
        dt = datetime.strptime(ddmmyyyy, "%d/%m/%Y")
        return f"{dt.day}{_ordinal_suffix(dt.day)} {dt.strftime('%B %Y')}"
    except Exception:
        return ""


def _to_short_date(ddmmyyyy: str) -> str:
    """``01/05/2026`` → ``1-may-26``. Reviewer-facing footer form.

    Returns ``""`` on parse failure. Day is unpadded; month is lowercase
    abbreviated; year is 2-digit.
    """
    if not ddmmyyyy:
        return ""
    try:
        from datetime import datetime
        dt = datetime.strptime(ddmmyyyy, "%d/%m/%Y")
        mon = dt.strftime("%b").lower()
        yy = dt.strftime("%y")
        return f"{dt.day}-{mon}-{yy}"
    except Exception:
        return ""


def _split_narrative_paragraph(doc, narrative_combined: str) -> None:
    """Two-paragraph Executive Summary per the canonical sample.

    Searches the body for the paragraph that ended up carrying the
    combined narrative (scope intro + ``\\n\\n`` + audit summary)
    after token substitution, splits on the literal ``\\n\\n``, mutates
    the existing paragraph to hold only the first part, and inserts a
    deepcopy after it carrying the second part. Both paragraphs
    inherit the template's Normal style and any ``rPr`` on the
    placeholder run.

    No-op when the narrative carries no ``\\n\\n`` separator (single
    paragraph or LLM disabled).
    """
    import copy
    from docx.oxml.ns import qn
    if "\n\n" not in narrative_combined:
        return
    parts = narrative_combined.split("\n\n", 1)
    intro, follow = parts[0].strip(), parts[1].strip()
    if not (intro and follow):
        return

    body = doc.element.body
    target_p = None
    for child in body.iterchildren():
        if child.tag != qn("w:p"):
            continue
        text = "".join(t.text or "" for t in child.iter(qn("w:t")))
        # The whole combined narrative landed in one paragraph during
        # substitution — find it by checking it equals or starts with
        # the intro text.
        if text.strip().startswith(intro[:60]):
            target_p = child
            break
    if target_p is None:
        return

    _set_paragraph_runs_text(target_p, intro)
    new_p = copy.deepcopy(target_p)
    _set_paragraph_runs_text(new_p, follow)
    target_p.addnext(new_p)


def _finding_heading_text(idx: int, row: EnrichedRow) -> str:
    """``#3 EWP Exclusion Zone`` per the canonical sample.

    Uses the LLM-provided 3-6 word descriptive ``finding_title`` when
    available. Falls back to ``ccvs_category`` (e.g. ``#3 Mobile
    Plant``) and finally to ``CCVS code + status`` for rows the LLM
    didn't get to.
    """
    if row.finding_title:
        return f"#{idx} {row.finding_title}"
    if row.ccvs_category:
        return f"#{idx} {row.ccvs_category}"
    if row.ccvs_code:
        return f"#{idx} {row.ccvs_code}"
    return f"#{idx}"


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
    project_name: str = "",
    prior_audit_date_ddmmyy: str = "",
    risk_assessment=None,
    merge_groups: list[list[int]] | None = None,
    render_order_out: list[int] | None = None,
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
    from docx.oxml.ns import qn

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
    #
    # Site address prepends the project name when supplied so the
    # cover line reads "Unitas Business Park 4-6 Mile End Rd ..." per
    # the canonical sample's p4 paragraph.
    full_site = (
        f"{project_name} {site_address}".strip()
        if project_name and site_address else (site_address or project_name or "")
    )
    # Two-paragraph Executive Summary per the canonical sample:
    # paragraph 1 is the standard scope intro, paragraph 2 is the
    # audit-specific narrative the LLM produced. We compose both into
    # the {{NARRATIVE_SUMMARY}} placeholder text and split into two
    # paragraphs at the cloning step below.
    audit_date_long = _to_long_date(audit_date_ddmmyyyy)
    scope_intro = (
        f"This report presents the findings of a site safety audit "
        f"conducted on {audit_date_long}. The focus is to confirm the "
        f"principal contractor's WHS controls are in place at the time "
        f"of inspection, identify any non-conformances against the "
        f"project Risk Assessment, and record positive observations for "
        f"continued monitoring."
    ) if audit_date_long else ""
    # Item 16: hard-cap the LLM-generated narrative at 20 lines before
    # composing with the scope intro. Defensive — the prompt already
    # targets <=140 words but the cap prevents pathological overshoots.
    capped_narrative = cap_executive_summary(narrative_summary or "")
    combined_narrative = (
        f"{scope_intro}\n\n{capped_narrative}".strip()
        if scope_intro else capped_narrative
    )
    # Two date formats are wired into the deliverable per reviewer
    # direction:
    #   - cover-page text box (in document.xml body): ``1st May 2026``
    #   - running footer (footer*.xml):              ``1-may-26``
    # Both share the same {{AUDIT_DATE}} placeholder; the substitution
    # branch picks the right form per part.
    audit_date_ordinal = _to_ordinal_date(audit_date_ddmmyyyy)
    audit_date_short = _to_short_date(audit_date_ddmmyyyy)
    body_replacements = {
        "{{SITE_ADDRESS}}": full_site,
        "{{NARRATIVE_SUMMARY}}": combined_narrative,
        "{{AUDIT_DATE}}": audit_date_ordinal or audit_date_ddmmyyyy or "",
        "{{PREPARED_BY}}": prepared_by or "",
    }
    footer_replacements = {
        "{{SITE_ADDRESS}}": full_site,
        "{{NARRATIVE_SUMMARY}}": combined_narrative,
        "{{AUDIT_DATE}}": audit_date_short or audit_date_ddmmyyyy or "",
        "{{PREPARED_BY}}": prepared_by or "",
    }
    _replace_tokens_in_part(doc.part, body_replacements)
    # Split the combined narrative into the canonical two-paragraph
    # Executive Summary. No-op when scope_intro was empty.
    _split_narrative_paragraph(doc, combined_narrative)
    for sec in doc.sections:
        for hf in (
            sec.header, sec.first_page_header,
            sec.footer, sec.first_page_footer,
        ):
            _replace_tokens_in_part(hf.part, footer_replacements)

    # --- Partition rows ----------------------------------------------
    # Track each row's CSV-order index so the Positive Observations
    # table can render "PIMS Obs N | <reg ref>" cross-references back
    # to the Enriched register row numbers (canonical sample shape).
    indexed = list(enumerate(rows, start=1))
    positive = [(i, r) for i, r in indexed if r.conformance_status == "Compliant"]
    raw_register = [(i, r) for i, r in indexed if r.conformance_status != "Compliant"]
    # Item 12: merge materially similar findings before significance
    # ordering — keeps the canonical row's csv_idx so cross-refs in
    # the Observations Register still resolve.
    merged_register = merge_similar_findings(raw_register)
    # Item 10: order findings by significance so the most important
    # appears as #1 and at the top of the Findings index table.
    register = sort_register_by_significance(merged_register)
    # Operator override (--merge "1,3"): apply manual merge directives
    # AFTER significance sort so the indices line up with what the
    # reviewer sees in the rendered docx index table.
    if merge_groups:
        register = apply_manual_merges(register, merge_groups)

    # Item 9 + 14: RA labelling has already been applied by the
    # orchestrator on every row's text fields (see
    # ``apply_ra_labels_to_rows``) so all three builders see the
    # same labelled output.

    # Capture the rendered finding order so phase-3 (--from-report)
    # can pair operator edits in detail tables back to the correct
    # EnrichedRow. The order matches the per-finding detail blocks
    # expanded immediately below.
    if render_order_out is not None:
        render_order_out.clear()
        for csv_idx, _row in register:
            render_order_out.append(csv_idx)

    # Item 15: insert the Findings index table directly below the
    # "Findings" heading paragraph BEFORE the per-finding detail
    # blocks are expanded so the index sits above every detail
    # section in the rendered docx.
    _build_findings_index_table(doc, [r for _i, r in register])

    # Materialise the Findings section: clone the (#N heading + 2-col
    # detail table) block per non-Compliant row. Per the canonical
    # template each finding renders as a 6-row table (Location /
    # Observation / Regulatory Basis / Hierarchy of Control /
    # Required Action / Timeframe). R-1.3(e) explicitly permits this
    # block-level operation on the per-finding detail table.
    _expand_findings_list(doc, [r for _i, r in register])

    diagnostics: dict[str, list] = {
        "photo_load_failed": [],
        "photo_file_missing_at_render": [],
        "missing_photo_obs": [],
    }

    # --- Positive Observations table (3 cols) ------------------------
    pos_tbl = _find_table(doc, _TABLE_SIGNATURES["positive"])
    if pos_tbl is not None and len(pos_tbl.rows) >= 2:
        _apply_table_format(
            pos_tbl,
            col_widths_cm=_TABLE_COL_WIDTHS_CM["positive"],
            bold_header="positive" in _TABLE_HEADER_BOLD,
            repeat_header="positive" in _TABLE_HEADER_REPEAT,
            all_borders="positive" in _TABLE_ALL_BORDERS,
        )
        placeholder = pos_tbl.rows[1]
        if positive:
            for pos_idx, (csv_idx, row) in enumerate(positive, start=1):
                target = placeholder if pos_idx == 1 else _clone_row(pos_tbl, placeholder)
                cells = target.cells
                # Per the canonical sample, Positive Observations use
                # ``P1 / P2 / P3`` numbering (distinct from the
                # Observations Register's ``1 / 2 / 3``) so reviewers
                # can cite a positive without ambiguity.
                _set_cell_text(cells[0], f"P{pos_idx}")
                _set_cell_text(
                    cells[1],
                    row.observation_text_clean or row.obs.observation_text,
                )
                # Reference column carries the cross-ref to the Enriched
                # register row plus the regulatory citation:
                # ``PIMS Obs 4 | NSW WHS Regulation 2017 cl.43``.
                ref_text = f"PIMS Obs {csv_idx}"
                if row.legal_ref:
                    ref_text = f"{ref_text} | {row.legal_ref}"
                _set_cell_text(cells[2], ref_text)
        else:
            cells = placeholder.cells
            _set_cell_text(cells[0], "-")
            _set_cell_text(cells[1], "No positive observations recorded.")
            _set_cell_text(cells[2], "")

    # --- Status of Previous Recommendations table (4 cols) ----------
    # 2026-05-06 layout: Date | Recommendations | Status (DD-Mon-YY) |
    # Comments. Column widths 2.5 / 6.25 / 2.5 / 6.25 cm. All-cell
    # single-line borders. Header row repeats across page breaks.
    prev_tbl = _find_table(doc, _TABLE_SIGNATURES["prior_recs"])
    if prev_tbl is not None and len(prev_tbl.rows) >= 2:
        _apply_table_format(
            prev_tbl,
            col_widths_cm=_TABLE_COL_WIDTHS_CM["prior_recs"],
            bold_header="prior_recs" in _TABLE_HEADER_BOLD,
            repeat_header="prior_recs" in _TABLE_HEADER_REPEAT,
            all_borders="prior_recs" in _TABLE_ALL_BORDERS,
        )
        # Substitute the CURRENT audit date into the header cell —
        # template carries "Status (DD-Mon-YY)" placeholder; rendered
        # form uses the short footer-style date ("Status (1-may-26)").
        # Reviewer direction: the column header tracks "as-of" the
        # current audit date so the table chains forward.
        audit_short = _to_short_date(audit_date_ddmmyyyy)
        if audit_short:
            hdr_cell = prev_tbl.rows[0].cells[2]
            for p_el in hdr_cell._tc.iter(qn("w:p")):
                t_text = "".join(
                    t.text or "" for t in p_el.iter(qn("w:t"))
                )
                if "DD-Mon-YY" in t_text:
                    new_text = t_text.replace("DD-Mon-YY", audit_short)
                    _set_paragraph_runs_text(p_el, new_text)
                    break
                if "DD/MM/YY" in t_text:  # legacy template fallback
                    new_text = t_text.replace(
                        "DD/MM/YY",
                        prior_audit_date_ddmmyy or audit_short,
                    )
                    _set_paragraph_runs_text(p_el, new_text)
                    break
        placeholder = prev_tbl.rows[1]
        recs = list(prior_recs or [])
        if recs:
            for idx, rec in enumerate(recs, start=1):
                target = placeholder if idx == 1 else _clone_row(prev_tbl, placeholder)
                cells = target.cells
                # 2026-05-06 column layout:
                # Date | Recommendations | Status (as of <audit>) | Comments
                _set_cell_text(cells[0], str(rec.get("date", "")))
                _set_cell_text(cells[1], str(rec.get("recommendation", "")))
                _set_cell_text(cells[2], str(rec.get("status", "")))
                _set_cell_text(cells[3], str(rec.get("commentary", "")))
        else:
            cells = placeholder.cells
            _set_cell_text(cells[0], "")
            _set_cell_text(cells[1], "No prior recommendations carried forward.")
            _set_cell_text(cells[2], "")
            _set_cell_text(cells[3], "")

    # --- Observations Register table (6 cols, photos in col 1) -------
    # Per the canonical sample, the Observations Register is the
    # MASTER list — every observation appears (Compliant + non-
    # Compliant) so the audit trail is complete. Non-Compliant rows
    # carry a status pointer back to their Findings entry
    # ("See F1 re exclusion zone"); Compliant / Info rows carry the
    # canonical status word.
    reg_tbl = _find_table(doc, _TABLE_SIGNATURES["obs_register"])
    if reg_tbl is not None and len(reg_tbl.rows) >= 2:
        _apply_table_format(
            reg_tbl,
            col_widths_cm=None,  # use template's existing widths
            bold_header="obs_register" in _TABLE_HEADER_BOLD,
            repeat_header="obs_register" in _TABLE_HEADER_REPEAT,
            all_borders="obs_register" in _TABLE_ALL_BORDERS,
        )
        # Map each non-Compliant row's csv_idx → finding number (F1, F2 …)
        # so we can cite the Findings entry from the register's status
        # cell. Findings render in the same order as `register`.
        finding_ref_for: dict[int, str] = {}
        for f_idx, (csv_idx, _row) in enumerate(register, start=1):
            finding_ref_for[csv_idx] = f"F{f_idx}"

        placeholder = reg_tbl.rows[1]
        all_rows = indexed
        if all_rows:
            for n, (csv_idx, row) in enumerate(all_rows, start=1):
                target = placeholder if n == 1 else _clone_row(reg_tbl, placeholder)
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
                    diagnostics["missing_photo_obs"].append(n)

                obs_marker = f"{n}{'*' if not photo_embedded else ''}"
                _set_cell_text(cells[0], obs_marker)
                if not photo_embedded:
                    _set_cell_text(cells[1], "")

                # Observation column: short cleaned summary, not the
                # full multi-sentence finding. The detail block at
                # the top of the report carries the long form.
                summary = (
                    row.observation_text_clean
                    or row.obs.observation_text
                    or ""
                )
                _set_cell_text(cells[2], summary)
                _set_cell_text(cells[3], row.legal_ref or "")
                # Status column carries cross-reference text per the
                # canonical sample shape.
                _set_cell_text(cells[4], _register_status_text(
                    row.conformance_status,
                    finding_ref_for.get(csv_idx, ""),
                ))
                _set_cell_text(cells[5], row.obs.resolved_filename or "")
        else:
            cells = placeholder.cells
            _set_cell_text(cells[0], "-")
            _set_cell_text(cells[1], "")
            _set_cell_text(cells[2], "No observations recorded.")
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
    # --- gap-4 fields (RA cross-references) ----
    if header == "phase":
        return row.phase
    if header == "activity_ref":
        return row.activity_ref
    if header == "hold_point":
        return row.hold_point
    if header == "hrcw":
        return row.hrcw
    # --- gap-5 fields (SWMS verification) ----
    if header == "swms_required":
        return "TRUE" if row.swms_required else "FALSE"
    if header == "swms_present":
        return row.swms_present
    # --- gap-6 fields (initial/residual risk axis) ----
    if header == "initial_risk":
        return row.initial_risk
    if header == "residual_risk":
        return row.residual_risk
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
    # Snapshot cache stats at entry so the wrapper's diagnostics
    # report the hits / misses it actually drove (rather than the
    # whole-process running totals).
    cache_at_entry = _photo_cache_stats()

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
            "cache": _cache_delta(cache_at_entry),
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
                "cache": _cache_delta(cache_at_entry),
            }

    # --- Path 4: size-driven split at the smallest cap -------------
    # _cache_delta is defined locally below the top-level builder and
    # bound here at call time — see helper at module level.
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
        "cache": _cache_delta(cache_at_entry),
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


# Composite-note splitter — auditors sometimes record several
# distinct issues against a single photo with leading numerals like
# "(1) Pre-start NOT completed (2) Worker observed without VOC".
# Each numbered fragment is its own atomic finding for the report
# (item 11 of the gap-closure brief). The pattern requires at least
# two leading-numeral markers; a single "(1)" prefix is a one-issue
# annotation and is left alone.
_COMPOSITE_MARKER_RE = re.compile(r"\(\d+\)\s*")


def _split_composite_notes(text: str) -> list[str]:
    """Split a composite "(1)... (2)..." note into atomic fragments.

    Returns a list with the original text when the input doesn't carry
    at least two markers, or one cleaned fragment per marker when it
    does. Marker prefixes are stripped from each fragment so the
    downstream finding text reads as a complete sentence.
    """
    if not text:
        return [text]
    markers = list(_COMPOSITE_MARKER_RE.finditer(text))
    if len(markers) < 2:
        return [text]
    out: list[str] = []
    for i, m in enumerate(markers):
        start = m.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        fragment = text[start:end].strip().rstrip(".,;").strip()
        if fragment:
            out.append(fragment)
    return out or [text]


def split_multi_issue_observations(
    rows: list[ObservationRow],
) -> list[ObservationRow]:
    """Expand any composite "(1)... (2)..." rows into atomic
    ObservationRows.

    Each split row keeps the original CSV row index, timestamp, photo
    filename and resolved path, so the downstream pipeline still
    matches one photo per fragment (every atomic finding cites the
    same evidence). The synthesised rows carry a ``part`` suffix in
    ``review_reasons`` for traceability.
    """
    out: list[ObservationRow] = []
    for obs in rows:
        fragments = _split_composite_notes(obs.observation_text or "")
        if len(fragments) < 2:
            out.append(obs)
            continue
        for idx, frag in enumerate(fragments, start=1):
            clone = ObservationRow(
                csv_row=obs.csv_row,
                timestamp_raw=obs.timestamp_raw,
                timestamp_iso=obs.timestamp_iso,
                observation_text=frag,
                csv_filename=obs.csv_filename,
                resolved_filename=obs.resolved_filename,
                resolved_path=obs.resolved_path,
                needs_review=obs.needs_review,
                review_reasons=list(obs.review_reasons) + [f"split_part_{idx}"],
                duplicate_filename=obs.duplicate_filename,
            )
            out.append(clone)
    return out


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

Legacy CCVS-keyed lookup over audit_checklist.xlsx. Kept as a deterministic fallback for --no-enrich mode; bypassed when vision is on (default).

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

Per-row Anthropic vision call (Opus 4.7). Sends downscaled EXIF-normalised photo + observation text + project RA context. Receives status / ccvs_code / finding_title / location / finding / hierarchy_of_control / recommendation / timeframe / phase / activity_ref / hold_point / hrcw / swms_required / swms_present / initial_risk / residual_risk / legal_ref / monitoring_note. Transient-error retry; forgiving JSON parser.

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
    '  status               ∈ ["Compliant", "Conditional", "NCR", "Info", "Unmatched"]\n'
    '  ccvs_code            "<STREAM>-<TIER>" or "" if no clear match\n'
    '  ccvs_category        plain-English category for the chosen stream, or ""\n'
    '  finding_title        SHORT plain-English sentence (max 12 words) '
    'describing what the finding actually is. PREFER active-voice '
    'sentences over noun phrases. Good examples: '
    '"Temporary brace removal proceeded without engineer sign-off", '
    '"Fire extinguishers stored on the ground rather than wall-mounted", '
    '"Telehandler operated without a current pre-start". '
    'Bad examples (do NOT use noun-phrase titles like): '
    '"EWP Exclusion Zone", "Pre-Start Logbook Gap", '
    '"SWMS Sign-On Date Missing". Used as the #N heading and as the '
    'Findings index table label.\n'
    '  location             site/area anchor with concrete reference, e.g. '
    '"Unit 1 shell", "Tilt-up panel zone, north elevation", "Site office area"\n'
    '  finding              2–4 sentence narrative, year-12 plain English\n'
    '  hierarchy_of_control "<Tier>: <specific control>" — Tier is one of '
    'Elimination / Substitution / Isolation / Engineering / Administrative / PPE; '
    'specific control is the actual physical or procedural step, e.g. '
    '"Engineering: Re-establish physical barriers at unit entry openings"\n'
    '  required_action      SHORT directive sentence, max 15 words, '
    'starting with "<Urgency> – " where Urgency is one of '
    'Immediate / Within 7 days / Next audit / Ongoing.\n'
    '\n'
    '    VERB SELECTION — pick the verb that captures BOTH the '
    'initial action AND any ongoing obligation. Australian WHS '
    'reviewer language prefers paired verbs for controls that must '
    'persist (exclusion zones, barriers, edge protection, signage, '
    'permits in force):\n'
    '      - "establish and maintain" — for exclusion zones, '
    'barriers, edge protection, traffic controls, permits, '
    'monitoring regimes (anything that has to be set up AND held '
    'in place across the work). Use this in preference to '
    '"demarcate", "set up", "implement" alone.\n'
    '      - "install" / "mount" / "fit" — for one-shot physical '
    'fixtures (extinguisher brackets, signage, cable trays).\n'
    '      - "complete" / "sign" — for record-keeping (logbook '
    'entries, pre-starts, SWMS sign-on).\n'
    '      - "verify" / "audit" / "check" — for monitoring or '
    'verification actions.\n'
    '      - "stop" / "stand down" — when the corrective action '
    'is to halt work until a control is in place.\n'
    '\n'
    '    EXAMPLES (good):\n'
    '      "Immediate – establish and maintain an exclusion zone '
    'beneath suspended steel works"\n'
    '      "Within 7 days – mount extinguishers on compliant brackets '
    'with location signage"\n'
    '      "Immediate – stop telehandler use until pre-start and VOC '
    'are completed"\n'
    '      "Ongoing – maintain daily register with time-in / time-out '
    'entries"\n'
    '\n'
    '    Do NOT name specific personnel, hold points, or activity '
    'refs in this field — those belong in the finding text. Keep to '
    'a directive verb phrase that fits a single line in a table cell.\n'
    '  timeframe            one of: Immediate / Within 7 days / Next audit / '
    'Ongoing / N/A — matches the urgency in required_action\n'
    '  legal_ref            multi-instrument citation separated by "; " — '
    'e.g. "WHS Act 2011 (NSW) s.19; WHS Reg r.291; SafeWork NSW Code of Practice: '
    'Managing the Risk of Falls", or ""\n'
    '  recommendation       one short sentence (paraphrase of required_action), or ""\n'
    '  monitoring_note      one short sentence reviewer cue, or ""\n'
    '  phase                "<phase number> — <phase name>" copied from the RA when the activity matches a phase, e.g. "6 — Tilt-Up Panel Erection"; "" if no RA / no clear match\n'
    '  activity_ref         RA activity ref the observation maps to, e.g. "TP-05"; "" if none\n'
    '  hold_point           RA Hold Point code if the activity is gated by one, e.g. "HP-06"; "" otherwise\n'
    '  hrcw                 RA HRCW codes for the activity, comma-separated, e.g. "H14, H15"; "" if RA does not classify\n'
    '  swms_required        true ONLY when the RA / WHS Reg requires a SWMS for this activity (HRCW work, scaffold, demolition, asbestos, height >2m, etc.). Otherwise false.\n'
    '  swms_present         "yes" if a SWMS sign-on / sighted on site evidence is in the photo or note; "no" if SWMS required but absent / undated; "unknown" if not visible; "" when swms_required is false\n'
    '  initial_risk         RA Initial Risk word for the matching activity ("High" / "Medium" / "Low") if the RA carries it for this activity; "" otherwise. Do not invent a rating from the photo alone.\n'
    '  residual_risk        RA Residual Risk word for the matching activity if the RA carries it; "" otherwise. Do not invent.\n\n'
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
    "- Reference the relevant regulation in plain English. Good: "
    "  \"WHS Regulation 2017 cl.79 requires edge protection at this "
    "  height; the site does not meet that standard.\" or \"This "
    "  falls below the WHS Regulation 2017 cl.79 minimum.\" Bad: "
    "  \"contrary to WHS Regulation 2017 cl.79\", \"in breach of\", "
    "  \"in violation of\", \"non-compliant with\". The bad forms read "
    "  as legal template phrasing; the good forms describe what the "
    "  rule says and how the observation falls short.\n"
    "- Banned vocabulary: crucial, pivotal, landscape, ensure, "
    "  leverage, robust, comprehensive, navigate, delve, it's "
    "  important to note, serves as, at its core.\n"
    "- Banned constructions:\n"
    "  * No em-dash clusters.\n"
    "  * No rule-of-three lists. Examples that are FORBIDDEN: "
    "    \"available, accessible, and clearly identified\", "
    "    \"obscured, kicked, or removed\", "
    "    \"fast, cheap, and reliable\". When citing what a rule "
    "    requires, name ONE primary requirement and let the rule "
    "    speak for itself, e.g. \"AS 2444 requires extinguishers "
    "    to be mounted at marked locations\" — not \"AS 2444 "
    "    requires extinguishers to be available, accessible, and "
    "    clearly identified\".\n"
    "  * No negative parallelism (\"not just X, but Y\", \"not only "
    "    X but also Y\").\n"
    "  * No signposting (\"firstly\", \"in conclusion\", \"to "
    "    summarise\").\n"
    "  * No sycophantic openers or closers (\"great question\", "
    "    \"I hope this helps\").\n"
    "  * No emoji, no curly quotes.\n"
    "  * No passive voice without a named actor — write \"the "
    "    auditor observed X\" or \"X was observed by the SD Group "
    "    site manager\", not bare \"X was observed\".\n"
    "  * No legalistic connectors — never write \"contrary to\", "
    "    \"in breach of\", \"in violation of\", \"non-compliant "
    "    with\", \"pursuant to\". Reference regulations by stating "
    "    what the rule requires and how the observation falls short.\n"
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


def _parse_json_object(text: str) -> dict[str, Any]:
    """Forgiving JSON-object parse for LLM output.

    Step 1: strip code fences if present.
    Step 2: try ``json.loads`` directly.
    Step 3: on failure, locate the first ``{`` and walk forward
    counting brace depth (respecting strings and escapes) until the
    matching ``}``; parse that substring. Handles cases where the
    model wraps the JSON in prose like ``"Here is the result: { ... }"``
    despite the explicit "JSON ONLY" instruction.

    Raises ``json.JSONDecodeError`` (passed through) when no valid
    JSON object can be extracted — caller wraps in try/except and
    falls back to Unmatched.
    """
    s = text.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1]
        if s.startswith("json"):
            s = s[4:]
        s = s.rsplit("```", 1)[0].strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    # Walk to find a balanced { ... } substring. Respect strings so
    # braces inside string literals don't fool the depth counter.
    start = s.find("{")
    if start < 0:
        raise json.JSONDecodeError("no { found in LLM output", s, 0)
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(s[start:i + 1])
    raise json.JSONDecodeError("unbalanced { in LLM output", s, start)


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
    return _parse_json_object(text)


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

    # Hierarchy of Control — accept "<Tier>: <control>" or bare tier;
    # validate the tier prefix against the canonical WHS hierarchy.
    # Anything else collapses to "" so the template cell stays blank
    # rather than carrying a fabricated label.
    hoc_raw = _s("hierarchy_of_control").strip()
    hoc = ""
    if hoc_raw:
        head = hoc_raw.split(":", 1)[0].strip().title()
        if head == "Ppe":
            head = "PPE"
        if head in {"Elimination", "Substitution", "Isolation",
                    "Engineering", "Administrative", "PPE"}:
            hoc = hoc_raw  # preserve the "Tier: control" full string

    # gap-5: SWMS verification — coerce truthy values to bool, gate
    # swms_present to the canonical {yes,no,unknown,""} set so the
    # staging xlsx column never carries a fabricated label.
    swms_required = raw.get("swms_required")
    if isinstance(swms_required, str):
        swms_required = swms_required.strip().lower() in {"true", "yes", "1"}
    else:
        swms_required = bool(swms_required)
    swms_present = _s("swms_present").lower()
    if swms_present not in {"yes", "no", "unknown", ""}:
        swms_present = "unknown"
    if not swms_required:
        # Unset swms_present when the row doesn't need a SWMS — keeps
        # the staging cell clean and prevents accidental yes/no carry.
        swms_present = ""

    # gap-6: initial/residual risk — accept only the canonical H/M/L
    # vocabulary. RA carries "High (3)" / "Medium (2)" / "Low (1)";
    # the LLM may return either form, so collapse to the bare word.
    def _risk(key: str) -> str:
        v = _s(key).strip().split(" ", 1)[0].title()
        return v if v in {"High", "Medium", "Low"} else ""

    return {
        "status": status,
        "ccvs_code": code,
        "ccvs_category": category,
        "finding_title": _s("finding_title"),
        "location": _s("location"),
        "finding": _s("finding"),
        "hierarchy_of_control": hoc,
        "required_action": _s("required_action"),
        "timeframe": _s("timeframe"),
        "legal_ref": _s("legal_ref"),
        "recommendation": _s("recommendation"),
        "monitoring_note": _s("monitoring_note"),
        "phase": _s("phase"),
        "activity_ref": _s("activity_ref"),
        "hold_point": _s("hold_point"),
        "hrcw": _s("hrcw"),
        "swms_required": swms_required,
        "swms_present": swms_present,
        "initial_risk": _risk("initial_risk"),
        "residual_risk": _risk("residual_risk"),
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
            # Surface the API's own error message body so billing /
            # auth / model-not-found issues don't read as "bad request"
            # to the orchestrator.
            try:
                api_err = exc.response.json().get("error", {})
                api_msg = api_err.get("message", "")[:160]
                api_type = api_err.get("type", "")
            except Exception:
                api_msg = ""
                api_type = ""
            tag = f"http {exc.response.status_code}"
            if api_type:
                tag = f"{tag} {api_type}"
            if api_msg:
                tag = f"{tag}: {api_msg}"
            seen_errors.add(tag)
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
        if rec["finding_title"]:
            row.finding_title = rec["finding_title"]
        if rec["location"]:
            row.location = rec["location"]
        if rec["finding"]:
            row.finding = rec["finding"]
        if rec["hierarchy_of_control"]:
            row.hierarchy_of_control = rec["hierarchy_of_control"]
        if rec["legal_ref"]:
            row.legal_ref = rec["legal_ref"]
        # Required-action and timeframe overlap with recommendation /
        # due_category. Prefer the LLM's tier-prefixed strings — they
        # render cleanly in the per-finding detail table — but fall
        # back to recommendation when required_action is blank.
        if rec["required_action"]:
            row.recommendation = rec["required_action"]
        elif rec["recommendation"]:
            row.recommendation = rec["recommendation"]
        if rec["monitoring_note"]:
            row.monitoring_note = rec["monitoring_note"]
        # timeframe — LLM's pick (Immediate / Within 7 days / Next
        # audit / Ongoing / N/A) overrides the status-derived default
        # so the docx Timeframe cell reflects the model's judgement
        # for context-specific items (e.g. "Ongoing" maintenance vs
        # one-shot "Immediate").
        tf = rec["timeframe"].strip()
        if tf in {"Immediate", "Within 7 days", "Next audit",
                  "Ongoing", "N/A"}:
            row.timeframe = tf
        # gap-4: RA cross-reference fields.
        if rec["phase"]:
            row.phase = rec["phase"]
        if rec["activity_ref"]:
            row.activity_ref = rec["activity_ref"]
        if rec["hold_point"]:
            row.hold_point = rec["hold_point"]
        if rec["hrcw"]:
            row.hrcw = rec["hrcw"]
        # gap-5: SWMS verification.
        row.swms_required = rec["swms_required"]
        if rec["swms_present"]:
            row.swms_present = rec["swms_present"]
        # gap-6: Initial / Residual risk axis (RA H/M/L).
        if rec["initial_risk"]:
            row.initial_risk = rec["initial_risk"]
        if rec["residual_risk"]:
            row.residual_risk = rec["residual_risk"]
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
        "paragraph, MAXIMUM 140 words and 12 lines on an A4 page "
        "(prefer 100 words). Provide site condition + the most "
        "significant gaps only — do NOT enumerate every finding; the "
        "Findings section below the summary already lists them all. "
        "No bullets, no headings, no lists. "
        "Open with the site address and audit date in a single "
        "sentence. Then summarise the audit's overall picture grounded "
        "in the findings supplied — note major non-conformance themes "
        "by hazard family, balance with positive observations. End "
        "with one sentence on the next-step posture (close out NCRs, "
        "monitor Conditional). Australian English, year-12 plain "
        "English. Banned vocabulary: crucial, pivotal, landscape, "
        "ensure, leverage, robust, comprehensive, navigate, delve, "
        "it's important to note, serves as, at its core. Banned "
        "constructions: no em-dash clusters, no rule-of-three lists, "
        "no negative parallelism (\"not just X, but Y\"), no "
        "signposting (\"firstly\", \"in conclusion\"), no "
        "sycophantic openers/closers, no emoji, no curly quotes, no "
        "passive voice without a named actor, no legalistic "
        "connectors (\"contrary to\", \"in breach of\", \"in "
        "violation of\", \"non-compliant with\", \"pursuant to\"). "
        "Do not invent counts, names, dates, or breaches not in the "
        "input. Return ONLY the paragraph text — no JSON, no quotes, "
        "no markdown."
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

_FOLDER_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})-(RPD|SDG)(?:-(\d{2}))?$"
)
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
    yyyy, mm, dd, client, sub_id = m.groups()
    yymmdd = f"{yyyy[2:]}{mm}{dd}"
    suffix = f"-{client}-{sub_id}" if sub_id else f"-{client}"
    return {
        f"PIMS-Enriched-{yymmdd}{suffix}.xlsx",
        f"Site-Safety-Audit-Report-{yymmdd}{suffix}.docx",
        f"Site-Visit-Report-Upload-PIMS-Staging-{yymmdd}{suffix}.xlsx",
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

CLI orchestrator. Folder-name parse (with -NN sub-id), manifest sha256, preflight, freeze escape hatch, sentinels, RA auto-discover, vision wiring, three-phase review workflow (--enrich-only / --from-state / --from-report), --merge directives, .ssa_run.json + .ssa_state.json payloads.

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
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from pims.services.ssa_checklist_lookup import ChecklistLookup
from pims.services.ssa_pipeline import (
    EnrichedRow,
    apply_ra_labels_to_rows,
    build_pims_enriched_xlsx,
    build_pims_staging_xlsx_with_size_control,
    build_ssa_report_docx,
    enrich_observations,
    extract_site_address,
    match_photos,
    parse_evidence_csv,
    parse_merge_argument,
    parse_prior_report_recommendations,
    split_multi_issue_observations,
)

log = logging.getLogger("ssa.cli")


# Folder name contract: YYYY-MM-DD-<CLIENT>[-NN], CLIENT ∈ {RPD, SDG},
# optional "-NN" sub-id distinguishes multiple visits to the same site
# on the same day (e.g. morning + afternoon walk, or sub-area split).
# When present, the sub-id is propagated to the output filenames so
# multiple runs against the same day's folders don't collide.
_FOLDER_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})-(RPD|SDG)(?:-(\d{2}))?$"
)

# Image extensions the watcher cares about. PNG-with-transparency is
# legal but rare; HEIC explicitly out of scope (filename canonicalisation
# rules in the plan).
_IMAGE_EXTS = {".jpg", ".jpeg", ".png"}

# Client-bulk-endpoint capability (gate 0). RPD has it today, SDG
# doesn't — confirmed against pims/routes.py:2091.
_BULK_ENDPOINT = {"RPD": "/pims/upload/observations", "SDG": None}


def _parse_folder(folder: Path) -> tuple[str, str, str, str, str]:
    """Return (audit_date_iso, audit_date_ddmmyyyy, yymmdd, client, sub_id).

    ``sub_id`` is the trailing ``-NN`` digit pair (e.g. ``"01"``) when
    the folder name carries one, or ``""`` when it doesn't. The sub-id
    is propagated to output filenames so multiple visits on the same
    day (``2026-05-01-SDG-01``, ``...-SDG-02``) don't overwrite each
    other.

    Raises ValueError when the folder name doesn't match the contract.
    """
    m = _FOLDER_RE.match(folder.name)
    if not m:
        raise ValueError(
            f"folder name {folder.name!r} does not match "
            f"YYYY-MM-DD-<CLIENT>[-NN] with CLIENT in (RPD, SDG)"
        )
    yyyy, mm, dd, client, sub_id = m.groups()
    sub_id = sub_id or ""
    iso = f"{yyyy}-{mm}-{dd}"
    ddmmyyyy = f"{dd}/{mm}/{yyyy}"
    yymmdd = f"{yyyy[2:]}{mm}{dd}"
    # Sanity-check the date itself; ValueError on Feb 30 etc.
    datetime.strptime(iso, "%Y-%m-%d")
    return iso, ddmmyyyy, yymmdd, client, sub_id


def _output_names(yymmdd: str, client: str, sub_id: str = "") -> dict[str, str]:
    suffix = f"-{client}-{sub_id}" if sub_id else f"-{client}"
    return {
        "enriched": f"PIMS-Enriched-{yymmdd}{suffix}.xlsx",
        "report": f"Site-Safety-Audit-Report-{yymmdd}{suffix}.docx",
        "staging": f"Site-Visit-Report-Upload-PIMS-Staging-{yymmdd}{suffix}.xlsx",
    }


def _images_in(folder: Path) -> list[Path]:
    return sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in _IMAGE_EXTS
    )


# Filename-date-suffix on a prior SSA report:
# ``Site-Safety-Audit-Report-YYMMDD-<CLIENT>[-NN].docx``.
_PRIOR_REPORT_RE = re.compile(
    r"^Site-Safety-Audit-Report-(\d{6})-(RPD|SDG)(?:-\d{2})?\.docx$"
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


class PreflightError(RuntimeError):
    """Raised when a required runtime precondition is missing.

    Distinct from generic ``RuntimeError`` so the CLI can surface the
    failure with a clean exit code and human-readable message before
    any rows are processed (rather than silently producing
    semantically-degraded output).
    """


def _preflight(enrich: bool) -> None:
    """Fail loud BEFORE any row processing when required runtime
    preconditions are missing.

    Currently checks:
      - When ``enrich`` is True, ``ANTHROPIC_API_KEY`` must be set in
        the environment. Without it the vision enricher silently
        leaves every row at ``status="Unmatched"``, and operators
        have hit this twice — once mistaking the result for a code
        bug, once for a billing problem. A loud preflight failure
        prevents both.

    Caller can short-circuit with ``--no-enrich`` when they
    deliberately want the offline path.
    """
    if enrich and not os.environ.get("ANTHROPIC_API_KEY"):
        raise PreflightError(
            "ANTHROPIC_API_KEY is not set in the environment. "
            "Either set the key (load .env, run with the key exported, "
            "or invoke from a shell that already has it) or pass "
            "--no-enrich to run the deterministic offline path "
            "(every row will land Unmatched)."
        )


def _serialise_rows(rows: list[EnrichedRow]) -> list[dict]:
    """Convert EnrichedRow + nested ObservationRow into JSON-safe dicts.

    Used by the two-phase workflow so phase 1 (enrich-only) can
    persist the full row state and phase 2 (from-state) can rebuild
    EnrichedRow objects after the operator has edited the enriched
    xlsx.
    """
    out: list[dict] = []
    for r in rows:
        obs = r.obs
        out.append({
            "obs": {
                "csv_row": obs.csv_row,
                "timestamp_raw": obs.timestamp_raw,
                "timestamp_iso": obs.timestamp_iso,
                "observation_text": obs.observation_text,
                "csv_filename": obs.csv_filename,
                "resolved_filename": obs.resolved_filename,
                "resolved_path": (
                    str(obs.resolved_path) if obs.resolved_path else None
                ),
                "needs_review": obs.needs_review,
                "review_reasons": list(obs.review_reasons),
                "duplicate_filename": obs.duplicate_filename,
            },
            "observation_text_clean": r.observation_text_clean,
            "finding": r.finding,
            "conformance_status": r.conformance_status,
            "ccvs_code": r.ccvs_code,
            "ccvs_category": r.ccvs_category,
            "action_description": r.action_description,
            "recommendation": r.recommendation,
            "legal_ref": r.legal_ref,
            "monitoring_note": r.monitoring_note,
            "location": r.location,
            "hierarchy_of_control": r.hierarchy_of_control,
            "finding_title": r.finding_title,
            "timeframe": r.timeframe,
            "phase": r.phase,
            "activity_ref": r.activity_ref,
            "hold_point": r.hold_point,
            "hrcw": r.hrcw,
            "swms_required": r.swms_required,
            "swms_present": r.swms_present,
            "initial_risk": r.initial_risk,
            "residual_risk": r.residual_risk,
            "evidence_csv_indices": list(r.evidence_csv_indices or []),
        })
    return out


def _deserialise_rows(payload: list[dict]) -> list[EnrichedRow]:
    """Inverse of ``_serialise_rows``. Returns EnrichedRow objects with
    nested ObservationRow rebuilt; ``resolved_path`` is restored as a
    Path when present."""
    from pims.services.ssa_pipeline import EnrichedRow, ObservationRow
    out: list[EnrichedRow] = []
    for d in payload:
        o = d["obs"]
        obs = ObservationRow(
            csv_row=o["csv_row"],
            timestamp_raw=o["timestamp_raw"],
            timestamp_iso=o["timestamp_iso"],
            observation_text=o["observation_text"],
            csv_filename=o["csv_filename"],
            resolved_filename=o.get("resolved_filename"),
            resolved_path=Path(o["resolved_path"]) if o.get("resolved_path") else None,
            needs_review=o.get("needs_review", False),
            review_reasons=list(o.get("review_reasons") or []),
            duplicate_filename=o.get("duplicate_filename", False),
        )
        out.append(EnrichedRow(
            obs=obs,
            observation_text_clean=d.get("observation_text_clean", ""),
            finding=d.get("finding", ""),
            conformance_status=d.get("conformance_status", "Unmatched"),
            ccvs_code=d.get("ccvs_code", ""),
            ccvs_category=d.get("ccvs_category", ""),
            action_description=d.get("action_description", ""),
            recommendation=d.get("recommendation", ""),
            legal_ref=d.get("legal_ref", ""),
            monitoring_note=d.get("monitoring_note", ""),
            location=d.get("location", ""),
            hierarchy_of_control=d.get("hierarchy_of_control", ""),
            finding_title=d.get("finding_title", ""),
            timeframe=d.get("timeframe", ""),
            phase=d.get("phase", ""),
            activity_ref=d.get("activity_ref", ""),
            hold_point=d.get("hold_point", ""),
            hrcw=d.get("hrcw", ""),
            swms_required=bool(d.get("swms_required", False)),
            swms_present=d.get("swms_present", ""),
            initial_risk=d.get("initial_risk", ""),
            residual_risk=d.get("residual_risk", ""),
            evidence_csv_indices=list(d.get("evidence_csv_indices") or []),
        ))
    return out


# Columns in the Enriched Register sheet that the operator is
# expected to edit during a phase-1 review pass. When phase 2 reads
# the (potentially edited) xlsx it overrides the corresponding fields
# on the EnrichedRow loaded from the JSON state.
_ENRICHED_EDITABLE_COLUMNS: dict[str, str] = {
    "observation": "finding",                 # the enriched narrative
    "conformance status": "conformance_status",
    "ccvs code": "ccvs_code",
    "ccvs category": "ccvs_category",
    "action description": "action_description",
    "monitoring note": "monitoring_note",
    "responsible": None,                       # blank-by-default cell
    "due": None,                               # blank-by-default cell
}


def _snapshot_enriched_xlsx(xlsx_path: Path) -> dict[str, dict[str, str]]:
    """Hash every editable cell of every data row keyed by Filename.

    Used by phase 1 to record what was written so phase 2 can tell
    operator edits apart from rendered-fallback values that didn't
    actually change. Returns ``{filename: {header_lc: cell_value}}``.
    """
    if not xlsx_path.exists():
        return {}
    import openpyxl
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    if "Enriched Register" not in wb.sheetnames:
        return {}
    ws = wb["Enriched Register"]
    headers = [
        ("" if c.value is None else str(c.value).strip().lower())
        for c in ws[1]
    ]
    try:
        filename_col = headers.index("filename") + 1
    except ValueError:
        return {}
    out: dict[str, dict[str, str]] = {}
    for excel_row in range(2, ws.max_row + 1):
        fn_cell = ws.cell(row=excel_row, column=filename_col).value
        fn = str(fn_cell).strip() if fn_cell else ""
        if not fn:
            continue
        snap: dict[str, str] = {}
        for col_idx, hdr in enumerate(headers, start=1):
            if hdr not in _ENRICHED_EDITABLE_COLUMNS:
                continue
            v = ws.cell(row=excel_row, column=col_idx).value
            snap[hdr] = "" if v is None else str(v).strip()
        out[fn] = snap
    return out


# Per-finding detail-table label → EnrichedRow attribute. Used by
# phase 3 (--from-report) to read operator edits out of the docx
# detail tables and write them back onto EnrichedRows.
_DETAIL_LABEL_TO_ATTR: dict[str, str] = {
    "location": "location",
    "observation": "finding",
    "regulatory basis": "legal_ref",
    "hierarchy of control": "hierarchy_of_control",
    "recommendation": "recommendation",
    "required action": "recommendation",   # legacy templates
    "timeframe": "timeframe",
}


def _extract_detail_table_edits(
    docx_path: Path,
) -> list[dict[str, str]]:
    """Walk the rendered audit report docx and return one dict per
    per-finding detail table (in document order). Each dict maps
    EnrichedRow attribute → cell text. Returns ``[]`` when no detail
    tables are found.
    """
    if not docx_path.exists():
        return []
    from docx import Document
    doc = Document(docx_path)
    out: list[dict[str, str]] = []
    for tbl in doc.tables:
        if len(tbl.columns) != 2 or not tbl.rows:
            continue
        if tbl.rows[0].cells[0].text.strip() != "Location":
            continue
        edit: dict[str, str] = {}
        for row in tbl.rows:
            if len(row.cells) < 2:
                continue
            label = row.cells[0].text.strip().lower()
            attr = _DETAIL_LABEL_TO_ATTR.get(label)
            if attr is None:
                continue
            edit[attr] = row.cells[1].text.strip()
        if edit:
            out.append(edit)
    return out


def _merge_edits_from_audit_report(
    rows: list[EnrichedRow], docx_path: Path,
    finding_render_order: list[int] | None,
) -> dict:
    """Phase 3: read operator edits from the audit report docx's
    per-finding detail tables and apply them back to the matching
    EnrichedRows.

    ``finding_render_order`` is the list of csv-row indices the
    detail tables were rendered FOR (in display order). Phase 2
    stamps it onto the state JSON so phase 3 can pair detail-table
    edits back to the correct EnrichedRow even after merge / sort.

    Returns a diagnostics dict shaped:
        {
          "applied":          bool,
          "tables_seen":      int,
          "tables_paired":    int,
          "field_overrides":  int,
          "unpaired":         int,    # detail tables we couldn't map
        }
    """
    if not docx_path.exists():
        return {"applied": False, "reason": "audit report missing"}
    edits = _extract_detail_table_edits(docx_path)
    if not edits:
        return {"applied": False, "reason": "no detail tables found"}

    # Build csv_idx → EnrichedRow lookup. evidence_csv_indices on a
    # consolidated row include all csv indices folded into it; the
    # canonical row's primary csv_idx is the first entry in that
    # list, which matches what phase 2 emitted.
    by_idx: dict[int, EnrichedRow] = {}
    for r in rows:
        if not r.evidence_csv_indices:
            r.evidence_csv_indices = [r.obs.csv_row]
        by_idx[r.evidence_csv_indices[0]] = r
        # Allow lookup by any folded csv_idx so the operator can
        # also use the un-merged number if they're cross-referencing
        # the original CSV.
        for fold_idx in r.evidence_csv_indices[1:]:
            by_idx.setdefault(fold_idx, r)

    overrides = 0
    paired = 0
    unpaired = 0
    for table_pos, edit in enumerate(edits):
        target = None
        if finding_render_order and table_pos < len(finding_render_order):
            target = by_idx.get(finding_render_order[table_pos])
        if target is None:
            unpaired += 1
            continue
        paired += 1
        for attr, new_val in edit.items():
            old_val = getattr(target, attr, "") or ""
            if (new_val or "") == old_val:
                continue
            setattr(target, attr, new_val or "")
            overrides += 1
    return {
        "applied": True,
        "tables_seen": len(edits),
        "tables_paired": paired,
        "field_overrides": overrides,
        "unpaired": unpaired,
    }


def _merge_edits_from_enriched_xlsx(
    rows: list[EnrichedRow], xlsx_path: Path,
    snapshot: dict[str, dict[str, str]] | None = None,
) -> dict:
    """Read the enriched xlsx and overwrite editable fields on each
    EnrichedRow with the operator's edits.

    Pairing key: the ``Filename`` column (resolved on-disk filename)
    matches each xlsx data row to exactly one EnrichedRow. When the
    filename is ambiguous (post-split composite notes share a
    photo) only the FIRST matching row's editable fields are
    overwritten — the operator should re-split manually if they
    need to differentiate.

    Returns a diagnostics dict counting overrides applied.
    """
    if not xlsx_path.exists():
        return {"applied": False, "reason": "enriched xlsx missing"}
    import openpyxl
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    if "Enriched Register" not in wb.sheetnames:
        return {"applied": False, "reason": "Enriched Register sheet missing"}
    ws = wb["Enriched Register"]
    headers = [
        ("" if c.value is None else str(c.value).strip().lower())
        for c in ws[1]
    ]
    try:
        filename_col = headers.index("filename") + 1
    except ValueError:
        return {"applied": False, "reason": "filename column missing"}

    # Index EnrichedRows by resolved_filename for one-shot lookup.
    by_fn: dict[str, EnrichedRow] = {}
    for r in rows:
        fn = (r.obs.resolved_filename or "").strip()
        if fn and fn not in by_fn:
            by_fn[fn] = r

    overrides = 0
    rows_seen = 0
    for excel_row in range(2, ws.max_row + 1):
        fn_cell = ws.cell(row=excel_row, column=filename_col).value
        fn = str(fn_cell).strip() if fn_cell else ""
        if not fn or fn not in by_fn:
            continue
        rows_seen += 1
        target = by_fn[fn]
        baseline = (snapshot or {}).get(fn, {})
        for col_idx, hdr in enumerate(headers, start=1):
            if hdr not in _ENRICHED_EDITABLE_COLUMNS:
                continue
            attr = _ENRICHED_EDITABLE_COLUMNS[hdr]
            if attr is None:
                continue
            new_val = ws.cell(row=excel_row, column=col_idx).value
            new_val = "" if new_val is None else str(new_val).strip()
            # When phase 1 recorded a baseline, only treat the cell as
            # edited if the current value differs from what was
            # written. Without a baseline (legacy state files) fall
            # back to the bare attribute comparison.
            if baseline:
                if new_val == baseline.get(hdr, ""):
                    continue
            else:
                old_val = getattr(target, attr, "")
                if new_val == (old_val or ""):
                    continue
            setattr(target, attr, new_val)
            overrides += 1
    return {
        "applied": True,
        "rows_matched": rows_seen,
        "field_overrides": overrides,
    }


def run_once(
    folder: Path,
    prepared_by: str = "Alan Richardson",
    ignore_freeze: bool = False,
    checklist_path: Path | None = None,
    force: bool = False,
    enrich: bool = True,
    risk_assessment_path: Path | None = None,
    merge_groups: list[list[int]] | None = None,
    stop_after: str | None = None,
    from_state: bool = False,
    from_report: bool = False,
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

    # Runtime preflight — must happen before any row processing so a
    # missing API key (or other config gap) fails loud rather than
    # producing a structurally-valid but semantically-degraded run.
    _preflight(enrich=enrich)

    freeze = folder / ".ssa_freeze"
    if freeze.exists() and not ignore_freeze:
        raise RuntimeError(
            f"frozen — use --ignore-freeze to overwrite ({freeze})"
        )

    iso, ddmmyyyy, yymmdd, client, sub_id = _parse_folder(folder)
    csv_path = folder / "Evidence_Master.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Evidence_Master.csv missing in {folder}")

    images = _images_in(folder)
    if not images:
        raise FileNotFoundError(f"no images found in {folder}")

    # --- manifest + idempotency -------------------------------------
    names = _output_names(yymmdd, client, sub_id)
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

    # Phase-3 short-circuit: when ``from_report`` is True, skip
    # parse / match / enrichment / vision and rebuild EnrichedRows
    # from the .ssa_state.json sidecar, then apply operator edits
    # from the audit-report docx's per-finding detail tables BACK
    # onto the rows. Re-renders the enriched + staging xlsx files
    # only — leaves the operator-edited docx alone.
    state_path = folder / ".ssa_state.json"
    if from_report:
        if not state_path.exists():
            raise FileNotFoundError(
                f"--from-report requested but .ssa_state.json missing in "
                f"{folder}. Run the pipeline (or phase 1 then phase 2) "
                f"to produce the state sidecar first."
            )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        enriched = _deserialise_rows(state["rows"])
        site_address = state.get("site_address")
        ra_project_name = state.get("ra_project_name", "")
        principal_contractor = state.get("principal_contractor", "")
        finding_render_order = list(state.get("finding_render_order") or [])
        report_path = folder / names["report"]
        enriched_path = folder / names["enriched"]
        staging_path = folder / names["staging"]
        merge_diag = _merge_edits_from_audit_report(
            enriched, report_path, finding_render_order,
        )
        # Rebuild the enriched xlsx + staging from the now-updated rows.
        enriched_diag = build_pims_enriched_xlsx(
            enriched, enriched_path,
            project_name=ra_project_name,
            site_address=site_address or "",
            principal_contractor=principal_contractor,
            audit_date_ddmmyyyy=ddmmyyyy,
        )
        site_for_staging = site_address or ""
        staging_result = build_pims_staging_xlsx_with_size_control(
            enriched, staging_path,
            site_address=site_for_staging,
            audit_date_iso=iso,
            prepared_by=prepared_by,
        )
        staging_diag = {
            "parts":        [p.name for p in staging_result["parts"]],
            "max_edge_px":  staging_result["max_edge_px"],
            "split":        staging_result["split"],
            "split_reason": staging_result["split_reason"],
            "per_part":     staging_result["diagnostics"],
        }
        # Refresh state JSON with the operator-edited rows.
        state["rows"] = _serialise_rows(enriched)
        state_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        staging_status, blocker = _resolve_staging_status(
            client, site_address,
        )
        outputs = [enriched_path.name, *[p.name for p in staging_result["parts"]]]
        if staging_status == "not_uploadable":
            outputs.append(_write_sentinel(
                folder, "STAGING-NOT-UPLOADABLE.txt",
                f"staging blocker: {blocker}\nfolder: {folder.name}\n",
            ))
        elif staging_status == "schema_valid_no_endpoint":
            outputs.append(_write_sentinel(
                folder, "STAGING-NO-BULK-ENDPOINT.txt",
                f"client: {client}\n",
            ))
        payload = {
            "folder": folder.name,
            "client": client,
            "audit_date": iso,
            "phase": "from-report",
            "from_report": True,
            "merge_diag": merge_diag,
            "staging_status": staging_status,
            "blocker": blocker,
            "client_bulk_endpoint": _BULK_ENDPOINT[client],
            "outputs": outputs,
            "row_count": len(enriched),
            "enriched_diagnostics": enriched_diag,
            "staging_diagnostics": staging_diag,
            "completed_at": datetime.now(timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        (folder / ".ssa_run.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return payload

    # Two-phase workflow short-circuit: when ``from_state`` is True,
    # skip parse → match → enrichment → vision and rebuild EnrichedRows
    # from the .ssa_state.json sidecar dropped by phase 1. The
    # operator's edits to the enriched xlsx are picked up via
    # _merge_edits_from_enriched_xlsx so phase 2 sees the human's
    # final values without re-running the LLM.
    state_path = folder / ".ssa_state.json"
    if from_state:
        if not state_path.exists():
            raise FileNotFoundError(
                f"--from-state requested but .ssa_state.json missing in "
                f"{folder}. Run phase 1 first with --enrich-only."
            )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        enriched = _deserialise_rows(state["rows"])
        site_address = state.get("site_address")
        narrative_summary = state.get("narrative_summary", "")
        ra_project_name = state.get("ra_project_name", "")
        principal_contractor = state.get("principal_contractor", "")
        ra_summary = state.get("ra_summary", {})
        llm_diag = state.get("llm_diagnostics", {"enabled": False})
        csv_warnings = []
        match_warnings = []
        prior_reports = []
        # Honour the freshly-set sub_id / output names already computed.
        names_for_phase2 = names
        # Pull operator edits from the enriched xlsx (if present).
        enriched_xlsx_path = folder / names_for_phase2["enriched"]
        merge_diag = _merge_edits_from_enriched_xlsx(
            enriched, enriched_xlsx_path,
            snapshot=state.get("enriched_xlsx_snapshot"),
        )
        # Re-resolve prior-recs from the prior report (cheap).
        prior_recs = []
        prior_audit_date_ddmmyy = ""
        # Find newest qualifying prior report for this folder.
        for p in folder.iterdir():
            if not p.is_file() or p.suffix.lower() != ".docx":
                continue
            mm = re.search(
                r"-(\d{6})-(?:RPD|SDG)(?:-\d{2})?\.docx$", p.name,
            )
            if not mm:
                continue
            try:
                cand_iso = datetime.strptime(mm.group(1), "%y%m%d").date().isoformat()
            except ValueError:
                continue
            if cand_iso < iso and p.name != names_for_phase2["report"]:
                prior_reports.append(p)
        if prior_reports:
            newest_prior = sorted(prior_reports)[-1]
            prior_recs = parse_prior_report_recommendations(newest_prior)
            mm = re.search(
                r"-(\d{6})-(?:RPD|SDG)(?:-\d{2})?\.docx$", newest_prior.name,
            )
            if mm:
                yymmdd = mm.group(1)
                prior_audit_date_ddmmyy = (
                    f"{yymmdd[4:6]}/{yymmdd[2:4]}/{yymmdd[0:2]}"
                )
        # Recompute paths for the from_state branch and skip the
        # rest of the parse/enrich block by jumping straight to the
        # build step. We do this by setting a flag and falling through.
        enriched_path = folder / names_for_phase2["enriched"]
        report_path = folder / names_for_phase2["report"]
        staging_path = folder / names_for_phase2["staging"]
        site_for_docx = site_address or "[Site address - to be confirmed]"
        site_for_staging = site_address or ""
        # Build only the report + staging (skip enriched xlsx so the
        # operator's edits stay intact).
        report_diag = build_ssa_report_docx(
            enriched,
            site_address=site_for_docx,
            audit_date_ddmmyyyy=ddmmyyyy,
            narrative_summary=narrative_summary,
            output_path=report_path,
            prepared_by=prepared_by,
            prior_recs=prior_recs,
            project_name=ra_project_name,
            prior_audit_date_ddmmyy=prior_audit_date_ddmmyy,
            risk_assessment=None,
            merge_groups=merge_groups,
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
        staging_status, blocker = _resolve_staging_status(client, site_address)
        outputs: list[str] = [
            enriched_path.name, report_path.name,
            *[p.name for p in staging_result["parts"]],
        ]
        if staging_status == "not_uploadable":
            outputs.append(_write_sentinel(
                folder, "STAGING-NOT-UPLOADABLE.txt",
                f"staging blocker: {blocker}\nfolder: {folder.name}\n",
            ))
        elif staging_status == "schema_valid_no_endpoint":
            outputs.append(_write_sentinel(
                folder, "STAGING-NO-BULK-ENDPOINT.txt",
                f"client: {client}\n",
            ))
        payload = {
            "folder": folder.name,
            "client": client,
            "audit_date": iso,
            "inputs_sha256": manifest,
            "prior_reports_used": [p.name for p in prior_reports],
            "skipped": False,
            "from_state": True,
            "merge_diag": merge_diag,
            "staging_status": staging_status,
            "blocker": blocker,
            "client_bulk_endpoint": _BULK_ENDPOINT[client],
            "outputs": outputs,
            "row_count": len(enriched),
            "csv_warnings": [],
            "match_warnings": [],
            "review_reasons_per_row": [],
            "enriched_diagnostics": {
                "phase2_skipped": "operator-edited xlsx kept intact",
            },
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

    # --- parse + match + address ------------------------------------
    rows, csv_warnings = parse_evidence_csv(csv_path)
    match_warnings = match_photos(rows, images)

    # Item 11: split composite "(1) X (2) Y" notes into atomic
    # observations BEFORE photo-match metadata is consumed downstream.
    # Each split shares the same csv_row, photo and timestamp; only
    # the observation_text differs.
    rows = split_multi_issue_observations(rows)

    # Gap-8: Vision is the canonical classifier. The legacy keyword
    # matcher in ChecklistLookup.match_observation produced 5/21 hits
    # with one outright misroute on real audit data — it's only kept
    # for the offline (--no-enrich) path AND only when the operator
    # explicitly passes --checklist. The default (vision) path skips
    # the xlsx load entirely so a missing audit_checklist.xlsx never
    # silently degrades the run.
    checklist = None
    if not enrich and checklist_path is not None:
        if checklist_path.exists():
            checklist = ChecklistLookup.from_xlsx(checklist_path)
        else:
            log.warning(
                "--checklist %s does not exist; offline run continues "
                "with no keyword fallback", checklist_path,
            )

    site_address = extract_site_address(rows)

    # When vision is on, enrich_observations builds shells only — the
    # vision pass downstream does the real classification. When vision
    # is off and a checklist was loaded, enable the keyword auto-match
    # path so the run produces something better than all-Unmatched.
    enriched = enrich_observations(
        rows,
        checklist=checklist,
        auto_match=(checklist is not None and not enrich),
    )

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
    ra_project_name = ""
    ra_obj = None
    ra_summary: dict[str, object] = {"path": None, "phases": 0, "activities": 0,
                                     "hold_points": 0}
    if ra_path is not None:
        ra = parse_risk_assessment(ra_path)
        ra_obj = ra
        ra_context = compact_context_block(ra)
        # Strip the "— N Industrial Warehouse Units" suffix that some
        # RA project names carry; the cover line wants just the venue.
        if ra.project_name:
            for sep in (" — ", " – ", " - "):
                if sep in ra.project_name:
                    ra_project_name = ra.project_name.split(sep, 1)[0].strip()
                    break
            else:
                ra_project_name = ra.project_name.strip()
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

    # Items 9 + 14: apply "SDG Project Risk Assessment code: <CODE>"
    # labelling with first-use shorthand expansion to every row's
    # text fields. Runs once after vision enrichment so the
    # downstream enriched xlsx / docx / staging xlsx all carry the
    # same labelled output.
    apply_ra_labels_to_rows(enriched, ra=ra_obj)
    # Item 9: label RA codes inside the executive summary too.
    from pims.services.ssa_pipeline import apply_ra_code_labels
    if narrative_summary:
        narrative_summary = apply_ra_code_labels(narrative_summary, ra=ra_obj)

    # Parse carry-forward recommendations from the newest qualifying
    # prior report so the SSA report's "Status of Previous
    # Recommendations" table actually carries content.
    prior_recs: list[dict] = []
    prior_audit_date_ddmmyy = ""
    if prior_reports:
        newest_prior = prior_reports[-1]
        prior_recs = parse_prior_report_recommendations(newest_prior)
        # Extract YYMMDD date from filename, format as DD/MM/YY for the
        # canonical "Status (DD/MM/YY)" header in the prior-recs table.
        m = re.search(
            r"-(\d{6})-(?:RPD|SDG)(?:-\d{2})?\.docx$", newest_prior.name,
        )
        if m:
            yymmdd = m.group(1)
            prior_audit_date_ddmmyy = (
                f"{yymmdd[4:6]}/{yymmdd[2:4]}/{yymmdd[0:2]}"
            )

    # Pull principal contractor + project metadata from the parsed RA
    # so the Enriched workbook's Summary sheet matches the canonical
    # sample's title block / metadata rows.
    principal_contractor = ""
    if ra_path is not None:
        # Re-parse for the metadata only (compact_context_block already
        # consumed the parsed object once). Cheap; one xlsx-style read.
        try:
            ra_meta = parse_risk_assessment(ra_path)
            principal_contractor = ra_meta.principal_contractor
        except Exception:
            log.warning("RA principal-contractor lookup failed", exc_info=True)

    enriched_diag = build_pims_enriched_xlsx(
        enriched, enriched_path,
        project_name=ra_project_name,
        site_address=site_address or "",
        principal_contractor=principal_contractor,
        audit_date_ddmmyyyy=ddmmyyyy,
    )

    # render_order is filled by build_ssa_report_docx to map detail
    # table position → csv_idx. Phase-3 (--from-report) pairs docx
    # edits back to EnrichedRows using this list.
    finding_render_order: list[int] = []

    # Persist the full row state for the two-phase workflow. Phase 2
    # (--from-state) reads this back, optionally merges operator
    # edits from the enriched xlsx, then renders the report + staging.
    # Snapshot the enriched xlsx's editable cells AS WRITTEN so
    # phase 2 can distinguish operator edits from rendered-fallback
    # values that look different from the source attribute (e.g. the
    # Action Description cell shows ``recommendation`` when
    # ``action_description`` is empty).
    enriched_snapshot = _snapshot_enriched_xlsx(enriched_path)

    state_payload = {
        "folder": folder.name,
        "client": client,
        "audit_date": iso,
        "audit_date_ddmmyyyy": ddmmyyyy,
        "site_address": site_address,
        "ra_project_name": ra_project_name,
        "principal_contractor": principal_contractor,
        "ra_summary": ra_summary,
        "narrative_summary": narrative_summary,
        "llm_diagnostics": llm_diag,
        "rows": _serialise_rows(enriched),
        "enriched_xlsx_snapshot": enriched_snapshot,
        "finding_render_order": list(finding_render_order),
    }
    state_path.write_text(
        json.dumps(state_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Phase-1 short-circuit: when ``stop_after="enrich"`` the pipeline
    # writes the enriched xlsx + state JSON and exits BEFORE the report
    # / staging are produced. The operator reviews + edits the xlsx,
    # then runs phase 2 with --from-state.
    if stop_after == "enrich":
        sentinel_outputs = [enriched_path.name, ".ssa_state.json"]
        ph1_payload = {
            "folder": folder.name,
            "client": client,
            "audit_date": iso,
            "phase": "enrich-only",
            "outputs": sentinel_outputs,
            "row_count": len(enriched),
            "llm_diagnostics": llm_diag,
            "site_address": site_address,
            "site_address_unresolved": site_address is None,
            "ra": ra_summary,
            "completed_at": datetime.now(timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "next_step": (
                "review and edit the Enriched Register sheet in "
                f"{enriched_path.name}, then re-run with "
                "--from-state to produce the report + staging files"
            ),
        }
        (folder / ".ssa_run.json").write_text(
            json.dumps(ph1_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return ph1_payload
    report_diag = build_ssa_report_docx(
        enriched,
        site_address=site_for_docx,
        audit_date_ddmmyyyy=ddmmyyyy,
        narrative_summary=narrative_summary,
        output_path=report_path,
        prepared_by=prepared_by,
        prior_recs=prior_recs,
        project_name=ra_project_name,
        prior_audit_date_ddmmyy=prior_audit_date_ddmmyy,
        risk_assessment=ra_obj,
        merge_groups=merge_groups,
        render_order_out=finding_render_order,
    )
    report_diag["prior_recs_count"] = len(prior_recs)

    # Update the state JSON with the freshly-captured
    # finding_render_order so phase-3 (--from-report) can pair docx
    # detail-table edits back to the correct EnrichedRow.
    if state_path.exists():
        try:
            existing_state = json.loads(
                state_path.read_text(encoding="utf-8"),
            )
            existing_state["finding_render_order"] = list(
                finding_render_order,
            )
            existing_state["rows"] = _serialise_rows(enriched)
            state_path.write_text(
                json.dumps(existing_state, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            log.warning("failed to refresh state JSON", exc_info=True)

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
    ap.add_argument(
        "--enrich-only", action="store_true",
        help=(
            "phase 1 of the two-phase workflow — write the enriched "
            "xlsx + .ssa_state.json sidecar and EXIT before the "
            "report and staging files are produced. Use this when "
            "you want to review / edit the LLM's findings in Excel "
            "before they get baked into the docx + staging xlsx. "
            "Re-run with --from-state to complete the run."
        ),
    )
    ap.add_argument(
        "--from-state", action="store_true",
        help=(
            "phase 2 of the two-phase workflow — skip parse / match "
            "/ vision and rebuild EnrichedRows from the .ssa_state."
            "json sidecar, merging the operator's edits from the "
            "Enriched Register sheet. Produces the report + staging "
            "files; leaves the (already operator-edited) enriched "
            "xlsx untouched."
        ),
    )
    ap.add_argument(
        "--from-report", action="store_true",
        help=(
            "phase 3 of the workflow — read operator edits from the "
            "audit report docx (per-finding detail tables) and flow "
            "them BACK to the enriched + staging xlsx. Updates the "
            "Location / Observation / Regulatory Basis / Hierarchy "
            "of Control / Recommendation / Timeframe fields. Leaves "
            "the operator-edited docx alone (it's the source of "
            "truth)."
        ),
    )
    ap.add_argument(
        "--merge", default="",
        help=(
            "merge directives by displayed finding number, e.g. "
            "\"1,3\" merges findings #1 and #3 into one consolidated "
            "entry; \"1,3;5,7\" applies two merges. Indices are "
            "1-based and refer to the post-significance order shown "
            "in the docx Findings index table."
        ),
    )
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )

    try:
        phase_flags = (args.enrich_only, args.from_state, args.from_report)
        if sum(bool(f) for f in phase_flags) > 1:
            print(
                "error: --enrich-only / --from-state / --from-report "
                "are mutually exclusive (they select one phase of the "
                "review workflow).",
                file=sys.stderr,
            )
            return 1
        payload = run_once(
            args.folder,
            prepared_by=args.prepared_by,
            ignore_freeze=args.ignore_freeze,
            checklist_path=args.checklist,
            force=args.force,
            enrich=not args.no_enrich,
            risk_assessment_path=args.risk_assessment,
            merge_groups=parse_merge_argument(args.merge),
            stop_after="enrich" if args.enrich_only else None,
            from_state=args.from_state,
            from_report=args.from_report,
        )
    except PreflightError as e:
        # Preflight blocked the run before any rows processed; rc=3
        # distinguishes a config gap from a frozen folder (rc=2) and
        # an input/argument error (rc=1).
        print(f"preflight: {e}", file=sys.stderr)
        return 3
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
    if payload.get("phase") == "enrich-only":
        print("phase 1 (enrich-only) complete")
        print(f"row_count: {payload.get('row_count')}")
        print(f"next step: {payload.get('next_step', '')}")
        print(f"outputs ({len(payload['outputs'])} files):")
        for name in payload["outputs"]:
            print(f"  - {name}")
        return 0
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

### `pims/scripts/populate_prior_recs_table.py`

Operator-driven post-render edit: populates the Status of Previous Recommendations table with prior carry-forward + current-cycle rows under the 10 locked rules (allowed status set, DD-MMM-YYYY date format, F<n> refs, significance + date sort). Tracked-changes output (author=Claude).

```python
"""Status of Previous Recommendations table population (tracked changes).

Per the 2026-05-06 reviewer rules:

  1. Allowed statuses are exactly:
       Completed / Partial / Not completed / Not assessed
  2. "Retired" is banned.
  3. Date format is DD-MMM-YYYY (e.g. ``01-May-2026``) — 4-digit year.
  4. Every Comments cell carries a finding reference ``F<n>``.
  5. Default status when no current-cycle evidence is linked:
     ``Not assessed`` (NOT ``Partial``).
  6. Keep all carry-forward recommendations from the prior report.
  7. Append new current-cycle recommendations from current findings.
  8. New appended rows use the current audit date + F<n> refs.
  9. Sort: significance first (critical-safety first), then by date.
 10. Header date must be 4-digit year: "Status as of 01-May-2026".

Columns:
  Date | Recommendations | Status as of <current date> | Comments

Run:
    python -m pims.scripts.populate_prior_recs_table \
        "G:/.../Site-Safety-Audit-Report-260501-SDG-01.docx" \
        --prior      "G:/.../Site-Safety-Audit-Report-260330-SDG-01.docx" \
        --audit-date 01-May-2026

When ``--prior`` is omitted the newest qualifying sibling SSA
report (date suffix strictly earlier than the current report's) is
auto-discovered.

Every change is applied as a Word tracked change with author
``Claude`` so the operator can review and accept in Word before
issuing the report.
"""
from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

AUTHOR = "Claude"
TRACKED_DATE = (
    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
)

# Locked status vocabulary (rule 1). Anything else collapses to
# "Not assessed" (rule 5) so a stray label can't sneak through.
ALLOWED_STATUSES = ("Completed", "Partial", "Not completed", "Not assessed")
BANNED_STATUSES = ("Retired",)
DEFAULT_STATUS = "Not assessed"

_PRIOR_REPORT_RE = re.compile(
    r"^Site-Safety-Audit-Report-(\d{6})-(?:RPD|SDG)(?:-\d{2})?\.docx$"
)


# ---------------------------------------------------------------------------
# Date helpers — DD-MMM-YYYY canonical form per rule 3
# ---------------------------------------------------------------------------

def to_long_dash_date(value: str) -> str:
    """Normalise a date string to ``DD-MMM-YYYY`` (e.g. ``01-May-2026``).

    Accepts:
      * ``DD/MM/YYYY``  (e.g. ``"01/05/2026"``)
      * ``DD-MMM-YY`` / ``DD-MMM-YYYY`` (case-insensitive month)
      * ``YYMMDD`` 6-digit prior-report suffix (e.g. ``"260330"``)
      * ``YYYY-MM-DD``

    Returns ``""`` on parse failure.
    """
    if not value:
        return ""
    s = str(value).strip()
    fmts = (
        "%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y", "%d-%b-%y",
        "%Y-%m-%d", "%y%m%d",
    )
    for fmt in fmts:
        try:
            d = datetime.strptime(s, fmt)
            return f"{d.day:02d}-{d.strftime('%b')}-{d.strftime('%Y')}"
        except ValueError:
            continue
    return ""


def date_from_prior_filename(filename: str) -> str:
    """Pull the prior audit date out of the filename and return
    ``DD-MMM-YYYY``."""
    m = _PRIOR_REPORT_RE.match(filename)
    if not m:
        return ""
    return to_long_dash_date(m.group(1))


# ---------------------------------------------------------------------------
# OXML helpers — tracked-changes
# ---------------------------------------------------------------------------

def _next_revision_id(state: dict[str, int]) -> str:
    state["n"] = state.get("n", 100) + 1
    return str(state["n"])


def _make_ins_run(text: str, rev: str, font_name: str = "Aptos") -> OxmlElement:
    ins = OxmlElement("w:ins")
    ins.set(qn("w:id"), rev)
    ins.set(qn("w:author"), AUTHOR)
    ins.set(qn("w:date"), TRACKED_DATE)
    r = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    rFonts = OxmlElement("w:rFonts")
    rFonts.set(qn("w:ascii"), font_name)
    rFonts.set(qn("w:hAnsi"), font_name)
    rFonts.set(qn("w:cs"), font_name)
    rPr.append(rFonts)
    r.append(rPr)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    ins.append(r)
    return ins


def _make_inserted_paragraph(text: str, rev: str) -> OxmlElement:
    p = OxmlElement("w:p")
    p.append(_make_ins_run(text, rev))
    return p


def _make_inserted_cell(text: str, rev: str, width_twips: int) -> OxmlElement:
    """Cell with one or more paragraphs (multi-line via ``\\n`` split)
    each wrapped in <w:ins> so Word renders the cell as inserted."""
    tc = OxmlElement("w:tc")
    tcPr = OxmlElement("w:tcPr")
    tcW = OxmlElement("w:tcW")
    tcW.set(qn("w:w"), str(width_twips))
    tcW.set(qn("w:type"), "dxa")
    tcPr.append(tcW)
    tc.append(tcPr)
    if text:
        for line in text.split("\n"):
            tc.append(_make_inserted_paragraph(line, rev))
    else:
        tc.append(OxmlElement("w:p"))
    return tc


def _mark_row_as_inserted(tr_element: OxmlElement, rev: str) -> None:
    trPr = tr_element.find(qn("w:trPr"))
    if trPr is None:
        trPr = OxmlElement("w:trPr")
        tr_element.insert(0, trPr)
    if trPr.find(qn("w:ins")) is None:
        ins = OxmlElement("w:ins")
        ins.set(qn("w:id"), rev)
        ins.set(qn("w:author"), AUTHOR)
        ins.set(qn("w:date"), TRACKED_DATE)
        trPr.append(ins)


def _mark_row_as_deleted(tr_element: OxmlElement, rev: str) -> None:
    trPr = tr_element.find(qn("w:trPr"))
    if trPr is None:
        trPr = OxmlElement("w:trPr")
        tr_element.insert(0, trPr)
    if trPr.find(qn("w:del")) is None:
        d = OxmlElement("w:del")
        d.set(qn("w:id"), rev)
        d.set(qn("w:author"), AUTHOR)
        d.set(qn("w:date"), TRACKED_DATE)
        trPr.append(d)
    for tc in tr_element.iter(qn("w:tc")):
        _wrap_runs_in_del(tc, rev)


def _wrap_runs_in_del(tc_element: OxmlElement, rev: str) -> None:
    for r in list(tc_element.iter(qn("w:r"))):
        parent = r.getparent()
        if parent is not None and parent.tag == qn("w:del"):
            continue
        del_el = OxmlElement("w:del")
        del_el.set(qn("w:id"), rev)
        del_el.set(qn("w:author"), AUTHOR)
        del_el.set(qn("w:date"), TRACKED_DATE)
        for t in list(r.iter(qn("w:t"))):
            new_t = OxmlElement("w:delText")
            new_t.set(qn("xml:space"), "preserve")
            new_t.text = t.text
            t.getparent().replace(t, new_t)
        r.addprevious(del_el)
        del_el.append(r)


def _replace_header_cell_text(
    tc_element: OxmlElement, new_text: str, rev_state: dict[str, int],
) -> None:
    rev_del = _next_revision_id(rev_state)
    _wrap_runs_in_del(tc_element, rev_del)
    rev_ins = _next_revision_id(rev_state)
    paragraphs = list(tc_element.iter(qn("w:p")))
    if paragraphs:
        paragraphs[0].append(_make_ins_run(new_text, rev_ins))


# ---------------------------------------------------------------------------
# Detail-table reading
# ---------------------------------------------------------------------------

def _detail_table_field(detail_tbl, label: str) -> str:
    for row in detail_tbl.rows:
        if len(row.cells) < 2:
            continue
        cell_label = row.cells[0].text.strip().lower()
        if cell_label == label.lower():
            return row.cells[1].text.strip()
    return ""


def _short_summary(observation_text: str, max_words: int = 14) -> str:
    if not observation_text:
        return ""
    s = observation_text.strip()
    for marker in (". ", "; "):
        cut = s.find(marker)
        if 0 < cut < 200:
            s = s[:cut + 1]
            break
    words = s.split()
    if len(words) > max_words:
        s = " ".join(words[:max_words]) + "…"
    return s.rstrip(".")


def _find_detail_tables_and_titles(doc):
    """Walk body XML; pair each ``#N <title>`` heading with the
    immediately following 2-col ``Location...`` detail table."""
    pairs = []
    body = doc.element.body
    last_heading = ""
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            txt = "".join(t.text or "" for t in child.iter(qn("w:t"))).strip()
            if txt.startswith("#"):
                parts = txt.split(" ", 1)
                last_heading = parts[1].strip() if len(parts) > 1 else ""
        elif child.tag == qn("w:tbl"):
            first_row = next(child.iter(qn("w:tr")), None)
            if first_row is None:
                continue
            cells = list(first_row.iter(qn("w:tc")))
            if len(cells) != 2:
                continue
            label = "".join(
                t.text or "" for t in cells[0].iter(qn("w:t"))
            ).strip()
            if label.startswith("Location"):
                from docx.table import Table
                pairs.append((last_heading, Table(child, doc)))
                last_heading = ""
    return pairs


# ---------------------------------------------------------------------------
# Significance scoring (rule 9)
# ---------------------------------------------------------------------------

# Critical-safety keywords that bump a row to the top of the sort.
# Mirrors the priority tiers in pims.services.ssa_pipeline._significance_score
# but works from finding text alone (we don't have an EnrichedRow here).
_CRITICAL_KEYWORDS = (
    "hold point", "exclusion zone", "engineer authorisation",
    "engineer sign-off", "permit", "fall", "harness", "asbestos",
    "confined space", "energy isolation", "energised electrical",
    "suspended steel", "crane", "tilt-up", "brace removal",
)

_HIGH_KEYWORDS = (
    "swms", "voc", "pre-start", "spotter", "edge protection",
    "traffic", "high-vis", "ppe", "first aid",
)


def _significance_for_text(blob: str) -> int:
    """Return 0=critical, 1=high, 2=other. Smaller sorts first."""
    s = (blob or "").lower()
    for kw in _CRITICAL_KEYWORDS:
        if kw in s:
            return 0
    for kw in _HIGH_KEYWORDS:
        if kw in s:
            return 1
    return 2


# ---------------------------------------------------------------------------
# Status normalisation (rules 1, 2, 5)
# ---------------------------------------------------------------------------

def normalise_status(value: str) -> str:
    """Coerce any input to one of the four allowed statuses.

    "Retired" (banned per rule 2) and any other label collapse to
    ``Not assessed`` (rule 5 default).
    """
    if not value:
        return DEFAULT_STATUS
    s = value.strip()
    # Case-insensitive equality check.
    for allowed in ALLOWED_STATUSES:
        if s.lower() == allowed.lower():
            return allowed
    return DEFAULT_STATUS


# ---------------------------------------------------------------------------
# Row records — uniform representation for sorting + rendering
# ---------------------------------------------------------------------------

class Row:
    """A single prior-recs table row prior to render."""

    __slots__ = (
        "date_str", "date_sort", "recommendation", "status",
        "comment", "significance",
    )

    def __init__(
        self, date_str: str, date_sort: str, recommendation: str,
        status: str, comment: str, significance: int,
    ):
        self.date_str = date_str
        self.date_sort = date_sort  # ISO YYYY-MM-DD for sort key
        self.recommendation = recommendation
        self.status = normalise_status(status)
        self.comment = self._enforce_finding_ref(comment)
        self.significance = significance

    @staticmethod
    def _enforce_finding_ref(comment: str) -> str:
        """Rule 4 — every Comments cell must include at least one
        ``F<n>`` reference. When missing, the caller has already
        appended ``See prior F?.`` / ``See F?.`` so this is a defence
        against accidental empty refs (returns the comment unchanged
        when an F-ref is present)."""
        if not comment:
            return ""
        if re.search(r"\bF\d+\b", comment):
            return comment
        return comment.rstrip(".") + " (finding reference missing)"


def _iso_from_long(d: str) -> str:
    """``01-May-2026`` → ``2026-05-01`` for stable sort. Empty when
    parse fails."""
    try:
        return datetime.strptime(d, "%d-%b-%Y").strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return ""


def build_rows(
    prior_doc, prior_date: str,
    current_doc, current_audit_date: str,
) -> list[Row]:
    """Combine prior carry-forwards with current-cycle findings into
    one Row list (rules 6 + 7)."""
    rows: list[Row] = []
    iso_prior = _iso_from_long(prior_date)
    iso_curr = _iso_from_long(current_audit_date)

    # Group A — prior carry-forwards (rule 6).
    for n, (title, dtbl) in enumerate(_find_detail_tables_and_titles(prior_doc),
                                       start=1):
        rec_text = _detail_table_field(dtbl, "Recommendation") \
            or _detail_table_field(dtbl, "Required Action")
        observation_text = _detail_table_field(dtbl, "Observation")
        label = f"F{n} – {title}".rstrip(" –")
        rec_cell = "\n".join([label] + ([rec_text] if rec_text else []))
        comment = (
            f"{_short_summary(observation_text)} See prior F{n}."
            if observation_text else f"See prior F{n}."
        )
        sig = _significance_for_text(f"{title} {rec_text}")
        rows.append(Row(
            date_str=prior_date,
            date_sort=iso_prior,
            recommendation=rec_cell,
            status=DEFAULT_STATUS,    # rule 5 — auditor reviews
            comment=comment,
            significance=sig,
        ))

    # Group B — current-cycle findings (rules 7 + 8).
    for n, (title, dtbl) in enumerate(
        _find_detail_tables_and_titles(current_doc), start=1,
    ):
        rec_text = _detail_table_field(dtbl, "Recommendation") \
            or _detail_table_field(dtbl, "Required Action")
        observation_text = _detail_table_field(dtbl, "Observation")
        label = f"F{n} – {title}".rstrip(" –")
        rec_cell = "\n".join([label] + ([rec_text] if rec_text else []))
        comment = (
            f"{_short_summary(observation_text)} See F{n}."
            if observation_text else f"See F{n}."
        )
        sig = _significance_for_text(f"{title} {rec_text}")
        rows.append(Row(
            date_str=current_audit_date,
            date_sort=iso_curr,
            recommendation=rec_cell,
            status=DEFAULT_STATUS,
            comment=comment,
            significance=sig,
        ))

    # Sort (rule 9): significance first, then date oldest-to-newest.
    rows.sort(key=lambda r: (r.significance, r.date_sort))
    return rows


# ---------------------------------------------------------------------------
# Table rewrite
# ---------------------------------------------------------------------------

def populate_prior_recs(
    docx_in: Path, docx_out: Path, audit_date: str, prior_docx: Path,
) -> dict:
    if not prior_docx.exists():
        raise FileNotFoundError(f"prior report not found: {prior_docx}")
    audit_long = to_long_dash_date(audit_date)
    if not audit_long:
        raise ValueError(
            f"audit-date {audit_date!r} couldn't be parsed; "
            f"use DD-MMM-YYYY or DD/MM/YYYY"
        )
    prior_long = date_from_prior_filename(prior_docx.name)
    if not prior_long:
        raise ValueError(
            f"prior date couldn't be inferred from filename "
            f"{prior_docx.name!r}"
        )

    doc = Document(docx_in)
    prior_doc = Document(prior_docx)

    # Locate the prior-recs table in the CURRENT report.
    prior_tbl = None
    for t in doc.tables:
        if len(t.columns) != 4 or not t.rows:
            continue
        h0 = t.rows[0].cells[0].text.strip()
        h1 = t.rows[0].cells[1].text.strip()
        if (
            (h0 == "Date" and h1 == "Recommendations")
            or ("Recommendation" in h0 and "Required Actions" in h1)
        ):
            prior_tbl = t
            break
    if prior_tbl is None:
        raise RuntimeError("Status of Previous Recommendations table not found")

    rev_state: dict[str, int] = {}

    # --- Header rewrite: "Status as of <DD-MMM-YYYY>" (rule 10)
    status_cell = next(
        (c for c in prior_tbl.rows[0].cells
         if "Status" in c.text and "(" in c.text or c.text.strip().startswith("Status")),
        None,
    )
    # Some layouts have a clean "Status" header (no parens) — accept that.
    if status_cell is None:
        status_cell = (
            prior_tbl.rows[0].cells[2]
            if len(prior_tbl.rows[0].cells) >= 3 else None
        )
    if status_cell is not None:
        _replace_header_cell_text(
            status_cell._tc,
            f"Status as of {audit_long}",
            rev_state,
        )

    # --- Build the combined row list (rules 6 + 7 + 9)
    rows = build_rows(prior_doc, prior_long, doc, audit_long)

    # --- Mark every existing data row as deleted (preserves header
    # row untouched) and insert the new rows BEFORE the first data row.
    grid = prior_tbl._tbl.find(qn("w:tblGrid"))
    col_widths = [int(g.get(qn("w:w"))) for g in grid.findall(qn("w:gridCol"))]
    if not col_widths:
        col_widths = [1417, 3543, 1417, 3543]  # 2.5/6.25/2.5/6.25 cm

    existing_data_rows = list(prior_tbl.rows)[1:]
    insert_anchor = (
        existing_data_rows[0]._tr if existing_data_rows
        else None
    )

    for n, row in enumerate(rows, start=1):
        rev = _next_revision_id(rev_state)
        tr = OxmlElement("w:tr")
        _mark_row_as_inserted(tr, rev)
        cells_text = [
            row.date_str,
            row.recommendation,
            row.status,
            row.comment,
        ]
        for i, text in enumerate(cells_text):
            w = col_widths[i] if i < len(col_widths) else 2000
            tr.append(_make_inserted_cell(text, rev, w))
        if insert_anchor is not None:
            insert_anchor.addprevious(tr)
        else:
            prior_tbl._tbl.append(tr)

    # Mark the original placeholder rows as deleted.
    for tr in existing_data_rows:
        rev = _next_revision_id(rev_state)
        _mark_row_as_deleted(tr._tr, rev)

    docx_out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(docx_out)
    return {
        "rows_inserted": len(rows),
        "carry_forward_count": sum(
            1 for r in rows if r.date_str == prior_long
        ),
        "current_cycle_count": sum(
            1 for r in rows if r.date_str == audit_long
        ),
        "audit_date": audit_long,
        "prior_date": prior_long,
        "prior_source": str(prior_docx),
        "output": str(docx_out),
    }


# ---------------------------------------------------------------------------
# Auto-discover + CLI
# ---------------------------------------------------------------------------

def _autodiscover_prior(docx_in: Path) -> Path | None:
    m = _PRIOR_REPORT_RE.match(docx_in.name)
    if not m:
        return None
    current_yymmdd = m.group(1)
    folder = docx_in.parent
    candidates = []
    for p in folder.iterdir():
        if not p.is_file() or p.suffix.lower() != ".docx":
            continue
        if p.name == docx_in.name:
            continue
        cm = _PRIOR_REPORT_RE.match(p.name)
        if not cm:
            continue
        if cm.group(1) < current_yymmdd:
            candidates.append((cm.group(1), p))
    if not candidates:
        return None
    candidates.sort()
    return candidates[-1][1]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="populate_prior_recs_table")
    ap.add_argument("docx_in", type=Path)
    ap.add_argument(
        "--prior", type=Path, default=None,
        help="path to the PRIOR audit report (auto-discovered when omitted)",
    )
    ap.add_argument(
        "--output", type=Path, default=None,
        help="output path; defaults to <input>-tracked.docx",
    )
    ap.add_argument(
        "--audit-date", required=True,
        help="Current audit date — DD-MMM-YYYY (e.g. 01-May-2026) "
             "or DD/MM/YYYY",
    )
    args = ap.parse_args(argv)

    if not args.docx_in.exists():
        print(f"error: {args.docx_in} not found")
        return 1

    prior = args.prior or _autodiscover_prior(args.docx_in)
    if prior is None:
        print(
            "error: no prior report supplied and none auto-discovered. "
            "Pass --prior <path> with the PRIOR audit report."
        )
        return 1
    if not prior.exists():
        print(f"error: prior report not found: {prior}")
        return 1

    out = args.output or args.docx_in.with_name(
        args.docx_in.stem + "-tracked" + args.docx_in.suffix,
    )
    try:
        diag = populate_prior_recs(args.docx_in, out, args.audit_date, prior)
    except (FileNotFoundError, RuntimeError, ValueError) as e:
        print(f"error: {e}")
        return 1

    print("rows inserted:        ", diag["rows_inserted"])
    print("  carry-forward:      ", diag["carry_forward_count"])
    print("  current cycle:      ", diag["current_cycle_count"])
    print("audit date (header):  ", diag["audit_date"])
    print("prior audit date:     ", diag["prior_date"])
    print("prior source:         ", diag["prior_source"])
    print("output:               ", diag["output"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

```

### `tests/test_ssa_pipeline.py`

99-case regression net. Covers parser, matcher, three builders, size-control + cache, manifest, watcher, vision coercion, RA parser, prior-rec parser, Findings #N expansion + index table, status colour fills, freeze, idempotency, partial-output recovery, anchor/Jaccard/strong-overlap merge, manual --merge directives, three-phase round-trip (--enrich-only / --from-state / --from-report).

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


@pytest.fixture(autouse=True)
def _stub_anthropic_key(monkeypatch):
    """Most tests don't exercise the live vision path — they either
    pass ``enrich=False`` to run_once or stub the runner. The new
    runtime preflight requires ``ANTHROPIC_API_KEY`` to be set when
    ``enrich`` is True (default), so we stub a placeholder key here
    by default. Tests that specifically exercise the missing-key
    branch delete this with their own monkeypatch."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")
    yield


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


def test_vision_enrichment_no_api_key_preflight_fails_loud(
    evidence_folder, monkeypatch,
):
    """``ANTHROPIC_API_KEY`` missing + ``enrich=True`` (default) →
    ``PreflightError`` raised before any row processing. This is the
    new gap-1 contract: silent semantically-degraded output is
    forbidden; the operator must either supply the key or pass
    ``enrich=False``."""
    from pims.scripts.run_ssa_pipeline import PreflightError
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(PreflightError, match="ANTHROPIC_API_KEY"):
        run_once(evidence_folder)


def test_vision_enrichment_no_api_key_with_no_enrich_runs(
    evidence_folder, monkeypatch,
):
    """Operator can opt out of the preflight by passing ``enrich=False``;
    the deterministic offline path still produces all 3 deliverables
    (every row Unmatched as documented)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    payload = run_once(evidence_folder, enrich=False)
    assert payload["staging_status"] == "bulk_uploadable"
    assert payload["llm_diagnostics"]["enabled"] is False


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
    # obs3 has no resolved_path → no photo embedded. Register now
    # carries ALL 3 rows (gap-3) so obs3 lands at register row 3.
    assert diag["missing_photo_obs"] == [3]

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
    # Two-paragraph Executive Summary: p6 = scope intro (with long-
    # format date "1 May 2026"), p7 = the audit-specific narrative we
    # passed in. Both inherit Normal style.
    assert "site safety audit conducted on 1 May 2026" in doc.paragraphs[6].text
    assert doc.paragraphs[7].text == "Audit summary text."

    # Footer carries the short-form audit date + prepared_by per
    # reviewer direction (Date: 1-may-26, lowercase month, 2-digit year).
    foot = doc.sections[1].footer.paragraphs[0].text
    assert "1-may-26" in foot
    assert "Alan Richardson" in foot

    # Positive Observations table → 1 Compliant row.
    # Per gap-2: row IDs are P1/P2/P3, Reference is "PIMS Obs N | <ref>".
    pos = next(t for t in doc.tables if t.rows[0].cells[0].text == "#"
               and "Reference" in t.rows[0].cells[2].text)
    assert pos.rows[1].cells[0].text == "P1"
    assert pos.rows[1].cells[1].text == "Site sign clear."
    assert pos.rows[1].cells[2].text == "PIMS Obs 2 | WHS Reg cl.34"

    # Observations Register now carries ALL observations (gap-3): 3
    # data rows (1 NCR, 1 Compliant, 1 Unmatched). Status column uses
    # the canonical cross-reference wording.
    reg = next(t for t in doc.tables
               if "Obs #" in t.rows[0].cells[0].text and len(t.columns) == 6)
    assert len(reg.rows) == 4  # header + 3 data
    # NCR row → "Non-compliant — See F1"
    assert "Non-compliant" in reg.rows[1].cells[4].text
    assert "F1" in reg.rows[1].cells[4].text
    # Compliant row → "Compliant"
    assert reg.rows[2].cells[4].text == "Compliant"
    # Unmatched row (no resolved photo) gets `*` marker on Obs #
    assert reg.rows[3].cells[0].text.endswith("*")
    assert reg.rows[3].cells[4].text == "Review at QA"


def test_positive_observations_use_p_numbering_and_pims_obs_xref(tmp_path):
    """Gap-2: Positive Observations rows numbered P1/P2/P3...
    Reference column carries 'PIMS Obs N | <reg ref>'."""
    photos = [_save_jpeg(tmp_path / f"p{i}.jpg", (400, 300)) for i in range(4)]
    rows = []
    for i, p in enumerate(photos):
        obs = ObservationRow(
            csv_row=i + 1, timestamp_raw="", timestamp_iso=None,
            observation_text=f"obs-{i}", csv_filename=p.name,
            resolved_filename=p.name, resolved_path=p,
        )
        rows.append(EnrichedRow(
            obs=obs,
            observation_text_clean=f"clean obs {i}",
            conformance_status="Compliant" if i in (1, 3) else "NCR",
            legal_ref=f"NSW WHS Reg cl.{40 + i}",
        ))
    out = tmp_path / "r.docx"
    build_ssa_report_docx(
        rows=rows, site_address="addr", audit_date_ddmmyyyy="01/05/2026",
        narrative_summary="x", output_path=out,
    )
    doc = Document(out)
    pos = next(t for t in doc.tables if t.rows[0].cells[0].text == "#"
               and "Reference" in t.rows[0].cells[2].text)
    pos_rows = pos.rows[1:]
    assert [r.cells[0].text for r in pos_rows] == ["P1", "P2"]
    # Compliant rows are obs idx 2 and 4 (1-based).
    assert pos_rows[0].cells[2].text == "PIMS Obs 2 | NSW WHS Reg cl.41"
    assert pos_rows[1].cells[2].text == "PIMS Obs 4 | NSW WHS Reg cl.43"


def test_staging_xlsx_writes_ra_columns_swms_and_risk(tmp_path):
    """Gap-4/5/6: staging xlsx carries phase / activity_ref /
    hold_point / hrcw / swms_required / swms_present / initial_risk
    / residual_risk columns and writes the EnrichedRow values."""
    p = _save_jpeg(tmp_path / "a.jpg", (800, 600))
    obs = ObservationRow(
        csv_row=1, timestamp_raw="2026-05-01_09-00-00",
        timestamp_iso="2026-05-01_09-00-00",
        observation_text="x", csv_filename="a.jpg",
        resolved_filename="a.jpg", resolved_path=p,
    )
    rows = [
        EnrichedRow(
            obs=obs, conformance_status="NCR", ccvs_code="WAH-H6",
            phase="6 — Tilt-Up Panel Erection", activity_ref="TP-05",
            hold_point="HP-06", hrcw="H14, H15",
            swms_required=True, swms_present="no",
            initial_risk="High", residual_risk="Medium",
        ),
    ]
    out = tmp_path / "staging.xlsx"
    build_pims_staging_xlsx(
        rows, out, site_address="addr", audit_date_iso="2026-05-01",
    )
    wb = openpyxl.load_workbook(out)
    ws = wb["Observations"]
    headers = [c.value for c in ws[3]]
    # Schema columns are present in row 3.
    for h in ("phase", "activity_ref", "hold_point", "hrcw",
              "swms_required", "swms_present",
              "initial_risk", "residual_risk"):
        assert h in headers, f"missing column: {h}"
    # Helper to look up the data cell by column name.
    col = {h: i + 1 for i, h in enumerate(headers)}
    assert ws.cell(row=5, column=col["phase"]).value == "6 — Tilt-Up Panel Erection"
    assert ws.cell(row=5, column=col["activity_ref"]).value == "TP-05"
    assert ws.cell(row=5, column=col["hold_point"]).value == "HP-06"
    assert ws.cell(row=5, column=col["hrcw"]).value == "H14, H15"
    assert ws.cell(row=5, column=col["swms_required"]).value == "TRUE"
    assert ws.cell(row=5, column=col["swms_present"]).value == "no"
    assert ws.cell(row=5, column=col["initial_risk"]).value == "High"
    assert ws.cell(row=5, column=col["residual_risk"]).value == "Medium"


def test_vision_parse_json_object_handles_prose_and_fences():
    """LLM occasionally wraps output in prose or markdown despite the
    JSON-ONLY instruction. The forgiving parser strips code fences
    AND locates a balanced { ... } substring inside surrounding text."""
    from pims.services.ssa_vision_enricher import _parse_json_object
    # Plain JSON
    assert _parse_json_object('{"status":"NCR"}') == {"status": "NCR"}
    # Code-fenced
    assert _parse_json_object('```json\n{"a":1}\n```') == {"a": 1}
    # Prose-wrapped (the failure mode that broke 5/21 rows on real data)
    assert _parse_json_object(
        'Here is the result: {"status":"NCR","ccvs_code":"WAH-H6"} done.'
    ) == {"status": "NCR", "ccvs_code": "WAH-H6"}
    # Braces inside string literals don't fool the depth walker.
    assert _parse_json_object('{"finding":"site has {bad} stuff"}') \
        == {"finding": "site has {bad} stuff"}


def test_vision_coerce_record_swms_and_risk_normalisation():
    """Gap-5/6: vision coercion gates SWMS + risk fields to canonical
    enums; bogus values collapse to safe defaults instead of being
    written verbatim."""
    from pims.services.ssa_vision_enricher import _coerce_record
    r = _coerce_record({
        "status": "NCR", "ccvs_code": "WAH-H6",
        "swms_required": "true",
        "swms_present": "Yes",
        "initial_risk": "High (3)",
        "residual_risk": "Medium (2)",
    })
    assert r["swms_required"] is True
    assert r["swms_present"] == "yes"
    assert r["initial_risk"] == "High"
    assert r["residual_risk"] == "Medium"

    # When swms_required is false, swms_present is forced to "" so a
    # stale "yes" doesn't leak into the staging cell.
    r2 = _coerce_record({
        "status": "Compliant", "ccvs_code": "SYS-L1",
        "swms_required": False, "swms_present": "yes",
    })
    assert r2["swms_required"] is False
    assert r2["swms_present"] == ""

    # Bogus risk word collapses to "" rather than being copied through.
    r3 = _coerce_record({
        "status": "NCR", "ccvs_code": "WAH-H6",
        "initial_risk": "Definitely-something",
    })
    assert r3["initial_risk"] == ""


def test_observations_register_includes_all_with_finding_xref(tmp_path):
    """Gap-3: Observations Register carries every observation
    (Compliant + non-Compliant); status column cross-references the
    Findings entry for non-Compliant rows."""
    photos = [_save_jpeg(tmp_path / f"p{i}.jpg", (400, 300)) for i in range(4)]
    rows = []
    statuses = ["NCR", "Compliant", "Conditional", "Info"]
    for i, (p, s) in enumerate(zip(photos, statuses)):
        obs = ObservationRow(
            csv_row=i + 1, timestamp_raw="", timestamp_iso=None,
            observation_text=f"raw obs {i}", csv_filename=p.name,
            resolved_filename=p.name, resolved_path=p,
        )
        rows.append(EnrichedRow(
            obs=obs,
            observation_text_clean=f"clean obs {i}",
            conformance_status=s,
            ccvs_code="WAH-H6" if s == "NCR" else "SYS-L1",
        ))
    out = tmp_path / "r.docx"
    build_ssa_report_docx(
        rows=rows, site_address="addr", audit_date_ddmmyyyy="01/05/2026",
        narrative_summary="x", output_path=out,
    )
    doc = Document(out)
    reg = next(t for t in doc.tables
               if "Obs #" in t.rows[0].cells[0].text and len(t.columns) == 6)
    # Every observation row appears.
    assert len(reg.rows) == 5  # 1 header + 4 data
    statuses_rendered = [r.cells[4].text for r in reg.rows[1:]]
    # Row order = CSV order (1-based: NCR / Compliant / Conditional / Info).
    assert "Non-compliant" in statuses_rendered[0]
    assert "F1" in statuses_rendered[0]   # links back to first finding
    assert statuses_rendered[1] == "Compliant"
    assert "Partially complete" in statuses_rendered[2]
    assert "F2" in statuses_rendered[2]   # second non-Compliant finding
    assert statuses_rendered[3] == "Noted"  # canonical wording for Info


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
    # Finding body text now lives in the cloned 2-col detail table's
    # Observation row, not in a body paragraph. Verify it landed there.
    detail_obs = []
    for t in doc.tables:
        if len(t.columns) == 2 and t.rows[0].cells[0].text.strip() == "Location":
            obs_row = next(
                (r for r in t.rows if r.cells[0].text.strip() == "Observation"),
                None,
            )
            if obs_row is not None:
                detail_obs.append(obs_row.cells[1].text)
    assert any("FINDING-0" in t for t in detail_obs)
    assert any("FINDING-2" in t for t in detail_obs)


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
    # 2026-05-06 schema: Date column is parsed from the prior
    # report's filename ("260301" → "1-Mar-26"). The Reference
    # column from the prior register is no longer carried — the
    # rendered table doesn't have a "Required Actions" column.
    assert recs[0]["date"] == "1-Mar-26"
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

    # 2 Compliant (i=1,3) → Positive Observations table.
    pos_data = [r.cells[1].text for r in pos.rows[1:]]
    assert pos_data == ["clean 1", "clean 3"]
    # Per gap-3, the Observations Register is the master list — all
    # 5 rows (Compliant + non-Compliant) appear, each with the
    # cleaned-summary in the Observation column. Distinctness is the
    # original anti-clone-bug guard; finding text lives in the
    # per-finding detail tables, not in the register.
    reg_data = [r.cells[2].text for r in reg.rows[1:]]
    assert reg_data == [f"clean {i}" for i in range(5)]
    detail_tables = [
        t for t in doc.tables
        if len(t.columns) == 2 and t.rows[0].cells[0].text.strip() == "Location"
    ]
    # 3 NCR rows → 3 cloned per-finding detail tables, each carrying
    # the long finding narrative.
    assert len(detail_tables) == 3
    detail_obs = []
    for t in detail_tables:
        obs_row = next(
            (r for r in t.rows if r.cells[0].text.strip() == "Observation"),
            None,
        )
        if obs_row is not None:
            detail_obs.append(obs_row.cells[1].text)
    assert any("unique-marker-0" in t for t in detail_obs)
    assert any("unique-marker-2" in t for t in detail_obs)
    assert any("unique-marker-4" in t for t in detail_obs)


def test_build_ssa_report_docx_findings_block_per_non_compliant(tmp_path):
    """Each non-Compliant finding renders as a (#N heading + 6-row
    2-col detail table) block per the canonical template. The
    detail table's right column carries Location / Observation /
    Regulatory Basis / Hierarchy of Control / Required Action /
    Timeframe values."""
    photos = [_save_jpeg(tmp_path / f"p{i}.jpg", (400, 300)) for i in range(3)]
    rows = []
    for i, p in enumerate(photos):
        obs = ObservationRow(
            csv_row=i + 1, timestamp_raw="", timestamp_iso=None,
            observation_text=f"obs-{i}", csv_filename=p.name,
            resolved_filename=p.name, resolved_path=p,
        )
        rows.append(EnrichedRow(
            obs=obs,
            finding=f"FINDING-{i} narrative.",
            conformance_status="NCR",
            ccvs_code="WAH-H6",
            legal_ref=f"WHS Reg cl.{79 + i}",
            recommendation=f"do action {i}",
            location=f"area-{i}",
            hierarchy_of_control="Engineering" if i == 0 else "Administrative",
        ))
    out = tmp_path / "r.docx"
    build_ssa_report_docx(
        rows=rows, site_address="addr", audit_date_ddmmyyyy="01/01/2026",
        narrative_summary="", output_path=out,
    )
    doc = Document(out)
    # 3 NCR rows → 3 cloned per-finding detail tables, plus Positive
    # Observations + Prior Recs + Observations Register = 6 tables.
    detail_tables = [
        t for t in doc.tables
        if len(t.columns) == 2
        and t.rows[0].cells[0].text.strip() == "Location"
    ]
    assert len(detail_tables) == 3
    # Each detail table carries the right field values for its row.
    for i, t in enumerate(detail_tables):
        # 2-col, 6 rows: Location, Observation, Regulatory Basis,
        # Hierarchy of Control, Required Action, Timeframe.
        labels = [r.cells[0].text.strip() for r in t.rows]
        # "Required Action" template label is rewritten to
        # "Recommendation" at render time per the canonical wording.
        assert labels == [
            "Location", "Observation", "Regulatory Basis",
            "Hierarchy of Control", "Recommendation", "Timeframe",
        ]
        values = [r.cells[1].text.strip() for r in t.rows]
        assert values[0] == f"area-{i}"
        assert f"FINDING-{i}" in values[1]
        assert values[2] == f"WHS Reg cl.{79 + i}"
        assert values[3] in {"Engineering", "Administrative"}
        assert values[4] == f"do action {i}"
        assert values[5] == "Immediate"  # NCR → Immediate


def test_build_ssa_report_docx_no_findings_collapses_detail_table(tmp_path):
    """Empty audit collapses the Findings detail table's right-column
    cells to blank and writes the placeholder heading."""
    out = tmp_path / "r.docx"
    build_ssa_report_docx(
        rows=[], site_address="addr", audit_date_ddmmyyyy="01/01/2026",
        narrative_summary="", output_path=out,
    )
    doc = Document(out)
    assert any("No findings recorded." in p.text for p in doc.paragraphs)


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
    # 2026-05-06 layout: Date | Recommendations | Status (...) | Comments
    prev = next(
        t for t in doc.tables
        if t.rows[0].cells[0].text.strip() == "Date" and len(t.columns) == 4
    )
    # Empty-recs placeholder text lives in the Recommendations cell
    # (column index 1) per the new layout.
    assert "No prior recommendations" in prev.rows[1].cells[1].text


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


def test_size_control_image_cache_avoids_rerun_preprocess(tmp_path):
    """Gap-7: progressive-downscale rerenders must reuse the
    preprocessed bytes for the SAME (source, max_edge_px) pair
    instead of running EXIF-transpose / downscale / JPEG-encode
    again. Cache hits / misses are exposed on the wrapper's diag."""
    from pims.services import ssa_pipeline as sp
    sp._photo_cache_clear()
    rows = _make_staging_rows(tmp_path, 5, edge_px=(800, 600))
    out = tmp_path / "s.xlsx"

    # Force a single-pass at 1600px (no rerender); the cache miss
    # count must equal the number of rows since each photo was
    # processed exactly once.
    r = build_pims_staging_xlsx_with_size_control(
        rows, out, site_address="x", audit_date_iso="2026-05-01",
    )
    cache = r["cache"]
    assert cache["misses"] == 5
    assert cache["hits"] == 0

    # Rerunning the same wrapper now should be ENTIRELY cache hits
    # because every (source, 1600) pair is already cached.
    r2 = build_pims_staging_xlsx_with_size_control(
        rows, out, site_address="x", audit_date_iso="2026-05-01",
    )
    cache2 = r2["cache"]
    assert cache2["hits"] == 5
    assert cache2["misses"] == 0


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


def test_run_once_llm_pass_no_enrich_produces_scope_intro_only(
    evidence_folder, monkeypatch,
):
    """``enrich=False`` skips the LLM cleanly (no preflight trip,
    no Anthropic call). The deterministic scope-intro paragraph still
    renders; the dynamic narrative is empty."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")
    payload = run_once(evidence_folder, enrich=False)
    assert payload["staging_status"] == "bulk_uploadable"
    docx_path = evidence_folder / "Site-Safety-Audit-Report-260501-RPD.docx"
    doc = Document(docx_path)
    assert "site safety audit conducted on" in doc.paragraphs[6].text
    assert payload["llm_diagnostics"]["enabled"] is False


def test_run_once_explicit_no_enrich_skips_pass(evidence_folder, monkeypatch):
    """``enrich=False`` short-circuits before the API call regardless
    of API key presence."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")
    payload = run_once(evidence_folder, enrich=False)
    assert payload["staging_status"] == "bulk_uploadable"
    assert payload["llm_diagnostics"]["enabled"] is False


# ---------------------------------------------------------------------------
# Items 9-16 — gap-closure refinements
# ---------------------------------------------------------------------------

def test_audit_date_helpers_format_correctly():
    """Reviewer-facing date formats: ordinal cover form and short
    footer form. Helpers handle ordinal suffixes (st/nd/rd/th) for
    teens and round numbers."""
    from pims.services.ssa_pipeline import _to_ordinal_date, _to_short_date
    assert _to_ordinal_date("01/05/2026") == "1st May 2026"
    assert _to_ordinal_date("02/05/2026") == "2nd May 2026"
    assert _to_ordinal_date("03/05/2026") == "3rd May 2026"
    assert _to_ordinal_date("04/05/2026") == "4th May 2026"
    assert _to_ordinal_date("11/05/2026") == "11th May 2026"  # teens always th
    assert _to_ordinal_date("21/05/2026") == "21st May 2026"
    assert _to_ordinal_date("") == ""
    assert _to_ordinal_date("garbage") == ""

    assert _to_short_date("01/05/2026") == "1-may-26"
    assert _to_short_date("15/12/2026") == "15-dec-26"
    assert _to_short_date("") == ""


def test_audit_report_docx_uses_ordinal_cover_and_short_footer(tmp_path):
    """Cover-page text box gets ``1st May 2026`` (reviewer-facing
    ordinal form); running footer gets ``1-may-26`` (short form)."""
    out = tmp_path / "r.docx"
    build_ssa_report_docx(
        rows=[],
        site_address="addr", audit_date_ddmmyyyy="01/05/2026",
        narrative_summary="x", output_path=out,
    )
    import zipfile
    with zipfile.ZipFile(out) as z:
        body = z.read("word/document.xml").decode()
        footer = z.read("word/footer1.xml").decode()
    # Cover: ordinal form
    assert "1st May 2026" in body
    assert "01/05/2026" not in body
    # Footer: short form (lowercase month, 2-digit year)
    assert "1-may-26" in footer
    assert "01/05/2026" not in footer


def test_split_multi_issue_observations_atomises_numbered_notes():
    """Item 11: composite "(1) X (2) Y (3) Z" notes split into three
    atomic ObservationRows; single "(1)" prefix left alone; rows
    without numbered markers pass through unchanged."""
    from pims.services.ssa_pipeline import split_multi_issue_observations
    a = ObservationRow(
        csv_row=1, timestamp_raw="", timestamp_iso=None,
        observation_text="(1) Pre-start NOT completed (2) VOC missing (3) SWMS undated",
        csv_filename="a.jpg",
    )
    b = ObservationRow(
        csv_row=2, timestamp_raw="", timestamp_iso=None,
        observation_text="(1) only one issue",  # single-marker, untouched
        csv_filename="b.jpg",
    )
    c = ObservationRow(
        csv_row=3, timestamp_raw="", timestamp_iso=None,
        observation_text="plain note no markers",
        csv_filename="c.jpg",
    )
    out = split_multi_issue_observations([a, b, c])
    # 3 atomic from a + 1 b + 1 c = 5
    assert len(out) == 5
    fragments = [r.observation_text for r in out[:3]]
    assert "Pre-start NOT completed" in fragments[0]
    assert "VOC missing" in fragments[1]
    assert "SWMS undated" in fragments[2]
    # Photo / timestamp / csv_row preserved.
    assert all(r.csv_row == 1 for r in out[:3])
    assert all(r.csv_filename == "a.jpg" for r in out[:3])
    # Single-marker row unchanged.
    assert out[3].observation_text == "(1) only one issue"
    assert out[4].observation_text == "plain note no markers"


def test_apply_ra_code_labels_first_use_expansion(tmp_path):
    """Items 9 + 14: first occurrence of an RA code in a block of
    text becomes "SDG Project Risk Assessment code: TP-07 (Tilt-up
    panel activity 07)"; subsequent occurrences in the same block
    drop the expansion. Multiple codes in a single phrase collapse
    into "SDG Project Risk Assessment codes: A, B"."""
    from pims.services.ssa_pipeline import apply_ra_code_labels
    from pims.services.ssa_ra_parser import RiskAssessment, RAActivity, RAHoldPoint
    ra = RiskAssessment(
        project_name="Test",
        hold_points=[
            RAHoldPoint(
                code="HP-04",
                description="Heavy plant / ground setup release",
                package="Tilt-Up", condition="x", sign_off="x", evidence="x",
            ),
        ],
        activities=[
            RAActivity(
                ref="TP-05", phase="6 — Tilt-Up Panel Erection",
                activity="Temporary brace install", hrcw="H13",
                initial_risk="High (3)", controls="x",
                residual_risk="Medium (2)", responsible="x",
            ),
        ],
    )
    text = (
        "Brace removal proceeded outside HP-04. Activity TP-05 "
        "covers the brace step; HRCW H14 traffic also applies. "
        "Subsequent TP-05 reference."
    )
    out = apply_ra_code_labels(text, ra=ra)
    # First HP-04 use carries the prefix + parenthesised expansion.
    assert "SDG Project Risk Assessment code: HP-04" in out
    assert "Heavy plant / ground setup release" in out
    # First TP-05 use carries the activity-phase expansion (preserves
    # the RA's casing of "Tilt-Up Panel Erection").
    assert "Tilt-Up Panel Erection activity 05" in out
    # H14 (HRCW) gets the static expansion.
    assert "HRCW traffic corridor" in out
    # Second TP-05 occurrence: bare code, no second expansion.
    assert out.count("Tilt-Up Panel Erection activity 05") == 1
    # Idempotent: re-applying produces the same output.
    assert apply_ra_code_labels(out, ra=ra) == out


def test_apply_ra_code_labels_clusters_codes_into_codes_prefix():
    """When two codes appear adjacent (e.g. "TP-05 / HP-04"), the
    label collapses to "SDG Project Risk Assessment codes: ...". """
    from pims.services.ssa_pipeline import apply_ra_code_labels
    out = apply_ra_code_labels("review HP-06 / TP-07 for compliance")
    assert "SDG Project Risk Assessment codes:" in out


def test_significance_score_orders_hp_then_swms_then_plant_then_permit():
    """Item 10: significance ordering — HP breaches first, then
    SWMS gaps, then plant/public, then permit-class breaches, then
    everything else."""
    from pims.services.ssa_pipeline import _significance_score
    # HP breach (highest priority)
    hp_row = EnrichedRow(
        obs=ObservationRow(csv_row=1, timestamp_raw="", timestamp_iso=None,
                           observation_text="x", csv_filename="x"),
        finding="see HP-06 violation",
        conformance_status="NCR", ccvs_code="TLT-H9",
    )
    # SWMS-required-but-absent (priority 1)
    swms_row = EnrichedRow(
        obs=ObservationRow(csv_row=2, timestamp_raw="", timestamp_iso=None,
                           observation_text="x", csv_filename="x"),
        finding="no swms",
        conformance_status="NCR", ccvs_code="WAH-H6",
        swms_required=True, swms_present="no",
    )
    # Plant/public (priority 2)
    mob_row = EnrichedRow(
        obs=ObservationRow(csv_row=3, timestamp_raw="", timestamp_iso=None,
                           observation_text="x", csv_filename="x"),
        finding="kubota under boom",
        conformance_status="NCR", ccvs_code="MOB-H9",
    )
    # Permit-class (priority 3)
    hot_row = EnrichedRow(
        obs=ObservationRow(csv_row=4, timestamp_raw="", timestamp_iso=None,
                           observation_text="x", csv_filename="x"),
        finding="hot work no permit",
        conformance_status="NCR", ccvs_code="HOT-H6",
    )
    # Generic NCR (priority 4)
    generic_row = EnrichedRow(
        obs=ObservationRow(csv_row=5, timestamp_raw="", timestamp_iso=None,
                           observation_text="x", csv_filename="x"),
        finding="other",
        conformance_status="Conditional", ccvs_code="SYS-M3",
    )
    rows = [(i, r) for i, r in enumerate(
        [generic_row, hot_row, mob_row, swms_row, hp_row], start=1
    )]
    rows.sort(key=lambda pair: _significance_score(pair[1]))
    order = [r.ccvs_code for _i, r in rows]
    assert order == ["TLT-H9", "WAH-H6", "MOB-H9", "HOT-H6", "SYS-M3"]


def test_parse_merge_argument_handles_groups_and_whitespace():
    from pims.services.ssa_pipeline import parse_merge_argument
    assert parse_merge_argument("") == []
    assert parse_merge_argument("1,3") == [[1, 3]]
    assert parse_merge_argument("1, 3 ; 5, 7, 8") == [[1, 3], [5, 7, 8]]
    # Invalid tokens dropped silently.
    assert parse_merge_argument("1,abc,3;x,y") == [[1, 3]]


def test_apply_manual_merges_consolidates_displayed_indices():
    """Operator-supplied merge directive consolidates findings by
    displayed index (1-based, post-significance order). The lowest
    index in each group is the canonical row; others have their
    titles / recommendations / findings folded in and their csv_idx
    appended to evidence_csv_indices."""
    from pims.services.ssa_pipeline import apply_manual_merges
    rows = [
        (10, EnrichedRow(
            obs=ObservationRow(
                csv_row=10, timestamp_raw="", timestamp_iso=None,
                observation_text="x", csv_filename="x"),
            finding_title="Telehandler near steel without exclusion",
            finding="long finding A", recommendation="Action A",
            conformance_status="NCR", ccvs_code="MOB-H9",
        )),
        (11, EnrichedRow(
            obs=ObservationRow(
                csv_row=11, timestamp_raw="", timestamp_iso=None,
                observation_text="x", csv_filename="x"),
            finding_title="Brace removal sign-off",
            finding="long finding B", recommendation="Action B",
            conformance_status="NCR", ccvs_code="TLT-H9",
        )),
        (12, EnrichedRow(
            obs=ObservationRow(
                csv_row=12, timestamp_raw="", timestamp_iso=None,
                observation_text="x", csv_filename="x"),
            finding_title="Pre-start logbook missing",
            finding="long finding C", recommendation="Action C",
            conformance_status="NCR", ccvs_code="MOB-H9",
        )),
    ]
    out = apply_manual_merges(rows, [[1, 3]])
    # 3 inputs, group [1,3] → 2 outputs (indices 1+3 collapse into
    # canonical at displayed position 1, position 2 untouched).
    assert len(out) == 2
    canonical = out[0][1]
    # Title concatenation preserves both originals.
    assert "Telehandler near steel" in canonical.finding_title
    assert "Pre-start logbook missing" in canonical.finding_title
    # Recommendation and finding fields concatenated with separators.
    assert "Action A" in canonical.recommendation
    assert "Action C" in canonical.recommendation
    assert "long finding A" in canonical.finding
    assert "long finding C" in canonical.finding
    # Evidence csv indices folded.
    assert 10 in canonical.evidence_csv_indices
    assert 12 in canonical.evidence_csv_indices
    # monitoring_note documents the consolidation.
    assert "Consolidated finding" in canonical.monitoring_note
    assert "PIMS Obs 10" in canonical.monitoring_note
    assert "PIMS Obs 12" in canonical.monitoring_note
    # Position 2 (Brace removal) untouched.
    assert out[1][1].finding_title == "Brace removal sign-off"


def test_merge_similar_findings_anchor_phrase_establish_zone():
    """Anchor-phrase merge: two recommendations that both prescribe
    "establish ... zone" merge even when overall Jaccard is below
    the 0.5 threshold AND even when the CCVS streams differ
    (e.g. WAH-H6 + MOB-H9). Reviewer's call: an exclusion zone
    above a steel lift and the telehandler beneath it are physically
    the same intervention even though the streams differ."""
    from pims.services.ssa_pipeline import merge_similar_findings
    a = EnrichedRow(
        obs=ObservationRow(
            csv_row=10, timestamp_raw="", timestamp_iso=None,
            observation_text="x", csv_filename="x"),
        finding_title="Telehandler near steel without exclusion zone",
        recommendation=(
            "Immediate – stop lifts and establish and maintain "
            "exclusion zone with spotter"
        ),
        conformance_status="NCR", ccvs_code="MOB-H9",
    )
    # Different stream (WAH not MOB) but the SAME control intent —
    # establish/maintain an exclusion zone. Anchor-phrase merge
    # crosses the stream boundary because the physical control is
    # the same intervention.
    b = EnrichedRow(
        obs=ObservationRow(
            csv_row=11, timestamp_raw="", timestamp_iso=None,
            observation_text="x", csv_filename="x"),
        finding_title="Workers under suspended steel — no zone",
        recommendation=(
            "Immediate – establish and maintain an exclusion zone "
            "beneath suspended steel works"
        ),
        conformance_status="NCR", ccvs_code="WAH-H6",
    )
    out = merge_similar_findings([(10, a), (11, b)])
    assert len(out) == 1
    canonical = out[0][1]
    assert canonical.evidence_csv_indices == [10, 11]
    assert "Evidence also: PIMS Obs 11" in canonical.monitoring_note


def test_merge_similar_findings_strong_overlap_collapses_register_pair():
    """Two SYS-class register findings with low Jaccard but ≥4
    shared content tokens (daily, register, time-out, entries) merge
    via the absolute-overlap rule. Without it the two daily-register
    duplicates render as separate findings even though the reviewer
    sees them as one."""
    from pims.services.ssa_pipeline import merge_similar_findings
    a = EnrichedRow(
        obs=ObservationRow(
            csv_row=10, timestamp_raw="", timestamp_iso=None,
            observation_text="x", csv_filename="x"),
        finding_title="Daily register missing time-out entries",
        recommendation=(
            "Within 7 days – complete time-out entries daily and "
            "review register at shift end"
        ),
        conformance_status="Conditional", ccvs_code="SYS-M3",
    )
    b = EnrichedRow(
        obs=ObservationRow(
            csv_row=11, timestamp_raw="", timestamp_iso=None,
            observation_text="x", csv_filename="x"),
        finding_title="Daily register entries missing time-out signatures",
        recommendation=(
            "Within 7 days – maintain daily register with time-in and "
            "time-out entries completed"
        ),
        conformance_status="Conditional", ccvs_code="SYS-M3",
    )
    out = merge_similar_findings([(10, a), (11, b)])
    assert len(out) == 1
    assert out[0][1].evidence_csv_indices == [10, 11]


def test_merge_similar_findings_anchor_only_fires_when_intent_overlaps():
    """Anchor merge does NOT fire when one recommendation prescribes
    "establish exclusion zone" and the other prescribes "complete
    pre-start logbook" — different physical control intents."""
    from pims.services.ssa_pipeline import merge_similar_findings
    a = EnrichedRow(
        obs=ObservationRow(
            csv_row=10, timestamp_raw="", timestamp_iso=None,
            observation_text="x", csv_filename="x"),
        finding_title="Telehandler near steel without exclusion zone",
        recommendation="Immediate – establish exclusion zone with spotter",
        conformance_status="NCR", ccvs_code="MOB-H9",
    )
    b = EnrichedRow(
        obs=ObservationRow(
            csv_row=11, timestamp_raw="", timestamp_iso=None,
            observation_text="x", csv_filename="x"),
        finding_title="Pre-start logbook missing for telehandler",
        recommendation=(
            "Immediate – stop telehandler use until pre-start logbook "
            "entry is completed and signed"
        ),
        conformance_status="NCR", ccvs_code="MOB-H9",
    )
    out = merge_similar_findings([(10, a), (11, b)])
    assert len(out) == 2  # NOT merged


def test_merge_similar_findings_collapses_on_recommendation_intent():
    """Two NCRs with different titles but the same physical control
    intent ("establish and maintain an exclusion zone") merge.
    Mirrors the reviewer call: 'we are only merging because very
    similar and results in establishing a work zone'."""
    from pims.services.ssa_pipeline import merge_similar_findings
    a = EnrichedRow(
        obs=ObservationRow(
            csv_row=10, timestamp_raw="", timestamp_iso=None,
            observation_text="x", csv_filename="x"),
        finding_title="Telehandler near steel without exclusion zone",
        recommendation="Immediate – establish and maintain an exclusion zone with spotter beneath the steel erection",
        conformance_status="NCR", ccvs_code="MOB-H9",
    )
    b = EnrichedRow(
        obs=ObservationRow(
            csv_row=11, timestamp_raw="", timestamp_iso=None,
            observation_text="x", csv_filename="x"),
        finding_title="Worker beneath suspended steel — no exclusion zone",
        recommendation="Immediate – establish and maintain an exclusion zone beneath suspended steel works",
        conformance_status="NCR", ccvs_code="MOB-H9",
    )
    c = EnrichedRow(  # different intent — should NOT merge
        obs=ObservationRow(
            csv_row=12, timestamp_raw="", timestamp_iso=None,
            observation_text="x", csv_filename="x"),
        finding_title="Pre-start logbook missing for telehandler",
        recommendation="Immediate – stop telehandler use until pre-start is completed and signed",
        conformance_status="NCR", ccvs_code="MOB-H9",
    )
    out = merge_similar_findings([(10, a), (11, b), (12, c)])
    # 3 input → 2 canonical (a and b merged into a; c standalone).
    assert len(out) == 2
    canonical = out[0][1]
    assert canonical.evidence_csv_indices == [10, 11]
    assert "Evidence also: PIMS Obs 11" in canonical.monitoring_note
    # c's title preserved as a separate canonical row.
    assert "Pre-start logbook missing" in out[1][1].finding_title


def test_apply_manual_merges_silent_on_invalid_indices():
    """Out-of-range / single-index groups are silently dropped — an
    operator typo should never crash the pipeline."""
    from pims.services.ssa_pipeline import apply_manual_merges
    rows = [
        (1, EnrichedRow(obs=ObservationRow(
            csv_row=1, timestamp_raw="", timestamp_iso=None,
            observation_text="x", csv_filename="x"))),
    ]
    # group of 1: no-op. Out-of-range: ignored.
    out = apply_manual_merges(rows, [[1], [1, 99], [50, 100]])
    assert out == rows


def test_merge_similar_findings_consolidates_evidence():
    """Item 12: rows with the same status + stream + finding_title
    collapse into one canonical row; subsequent rows fold their
    csv_idx into the canonical row's evidence_csv_indices and
    monitoring_note."""
    from pims.services.ssa_pipeline import merge_similar_findings
    base = lambda i, title: EnrichedRow(  # noqa: E731
        obs=ObservationRow(csv_row=i, timestamp_raw="", timestamp_iso=None,
                           observation_text="x", csv_filename="x"),
        finding_title=title,
        conformance_status="NCR",
        ccvs_code="MOB-H9",
    )
    rows = [
        (1, base(1, "Pre-start logbook gap")),
        (2, base(2, "Pre-start logbook gap")),  # duplicate
        (3, base(3, "Different issue")),
    ]
    merged = merge_similar_findings(rows)
    # 2 canonical rows (Pre-start + Different issue).
    assert len(merged) == 2
    canonical = merged[0][1]
    assert canonical.evidence_csv_indices == [1, 2]
    assert "Evidence also: PIMS Obs 2" in canonical.monitoring_note


def test_executive_summary_capped_at_20_lines_word_budget():
    """Item 16: cap_executive_summary truncates anything longer than
    ~280 words (20 lines × 14 words/line)."""
    from pims.services.ssa_pipeline import cap_executive_summary
    long_text = (
        "Sentence one is quite ordinary. Sentence two adds context. "
        * 50  # ~700 words total
    )
    out = cap_executive_summary(long_text, max_lines=20)
    assert len(out.split()) <= 20 * 14
    # Short text passes through unchanged.
    short = "A brief summary of the audit."
    assert cap_executive_summary(short) == short


def test_findings_index_table_inserted_below_findings_heading(tmp_path):
    """Item 15: the Findings index table (2 cols: Finding,
    Recommendation) is inserted directly under the Findings heading
    paragraph, with one row per detail block in significance order."""
    photos = [_save_jpeg(tmp_path / f"p{i}.jpg", (400, 300)) for i in range(3)]
    rows = []
    titles = [
        "Brace removal proceeded without engineer sign-off",
        "Pre-start logbook missing for telehandler",
        "Site sign in good order",
    ]
    statuses = ["NCR", "NCR", "Compliant"]
    codes = ["TLT-H9", "MOB-H9", "SYS-L1"]
    for i, p in enumerate(photos):
        obs = ObservationRow(
            csv_row=i + 1, timestamp_raw="", timestamp_iso=None,
            observation_text=f"obs {i}", csv_filename=p.name,
            resolved_filename=p.name, resolved_path=p,
        )
        rows.append(EnrichedRow(
            obs=obs, finding_title=titles[i],
            conformance_status=statuses[i], ccvs_code=codes[i],
            recommendation=f"recom {i}",
        ))
    out = tmp_path / "r.docx"
    build_ssa_report_docx(
        rows=rows, site_address="addr", audit_date_ddmmyyyy="01/05/2026",
        narrative_summary="x", output_path=out,
    )
    doc = Document(out)
    # Index table shape — find the 2-col table whose header is
    # exactly ("Finding", "Recommendation") and lives BEFORE every
    # per-finding detail table.
    idx_tbl = None
    for t in doc.tables:
        if (
            len(t.columns) == 3
            and [c.text.strip() for c in t.rows[0].cells] == ["#", "Finding", "Recommendation"]
        ):
            idx_tbl = t
            break
    assert idx_tbl is not None
    # 2 NCR rows → 2 data rows (header + 2)
    assert len(idx_tbl.rows) == 3
    # # column carries 1-based row numbers matching the per-finding
    # detail blocks below the index. Order is set by
    # _significance_score: MOB-H9 lands in the plant/public-interface
    # priority tier (rank 2), TLT-H9 with no HP ref / no SWMS gap /
    # no plant stream lands in generic-NCR rank 4.
    assert idx_tbl.rows[1].cells[0].text == "1"
    assert idx_tbl.rows[1].cells[1].text.startswith("Pre-start")
    assert idx_tbl.rows[1].cells[2].text == "recom 1"
    assert idx_tbl.rows[2].cells[0].text == "2"
    assert idx_tbl.rows[2].cells[1].text.startswith("Brace removal")
    assert idx_tbl.rows[2].cells[2].text == "recom 0"


def test_ra_label_applied_to_findings_in_real_render(tmp_path):
    """Item 9: a finding text containing TP-07 is rendered with the
    explicit "SDG Project Risk Assessment code:" prefix in the
    per-finding detail table's Observation cell."""
    p = _save_jpeg(tmp_path / "p.jpg", (400, 300))
    obs = ObservationRow(
        csv_row=1, timestamp_raw="", timestamp_iso=None,
        observation_text="x", csv_filename=p.name,
        resolved_filename=p.name, resolved_path=p,
    )
    row = EnrichedRow(
        obs=obs, finding_title="Brace removal without sign-off",
        finding="Brace removal proceeded without engineer sign-off; HP-06 not closed.",
        conformance_status="NCR", ccvs_code="TLT-H9",
        recommendation="Immediate – stop brace removal until sign-off.",
    )
    # Apply the labelling pre-render (mirrors orchestrator behaviour).
    from pims.services.ssa_pipeline import apply_ra_labels_to_rows
    apply_ra_labels_to_rows([row])
    out = tmp_path / "r.docx"
    build_ssa_report_docx(
        rows=[row], site_address="addr", audit_date_ddmmyyyy="01/05/2026",
        narrative_summary="x", output_path=out,
    )
    doc = Document(out)
    detail_tables = [
        t for t in doc.tables
        if len(t.columns) == 2 and t.rows[0].cells[0].text.strip() == "Location"
    ]
    obs_row = next(
        r for r in detail_tables[0].rows
        if r.cells[0].text.strip() == "Observation"
    )
    assert "SDG Project Risk Assessment code: HP-06" in obs_row.cells[1].text


def test_run_once_two_phase_workflow_round_trip(evidence_folder, monkeypatch):
    """Two-phase workflow: --enrich-only writes xlsx + state JSON
    and exits; --from-state reads state, applies operator edits to
    the Conformance Status / CCVS columns, and produces the report
    + staging without re-running the LLM."""
    # Stub the vision pass so the test doesn't need an API key but
    # exercises the persistence-and-reload path. The stub leaves
    # rows at their default Unmatched state but writes a token
    # narrative so the docx render has something to show.
    def fake_apply(enriched, **kw):
        # Mark first row as NCR so the operator-edit override has a
        # detectable change.
        if enriched:
            enriched[0].finding = "ORIGINAL FINDING TEXT"
            enriched[0].conformance_status = "Unmatched"
            enriched[0].ccvs_code = ""
        return ("Stub narrative for two-phase test.", {
            "enabled": True, "rows_total": len(enriched),
            "rows_called": len(enriched), "rows_ok": len(enriched),
            "rows_failed": 0, "errors": [],
            "ra": {"path": None},
        })

    from pims.scripts import run_ssa_pipeline as mod
    monkeypatch.setattr(mod, "_apply_vision_enrichment", fake_apply)

    # Phase 1: --enrich-only
    payload1 = mod.run_once(evidence_folder, stop_after="enrich")
    assert payload1["phase"] == "enrich-only"
    assert (evidence_folder / ".ssa_state.json").exists()
    enriched_xlsx = evidence_folder / "PIMS-Enriched-260501-RPD.xlsx"
    assert enriched_xlsx.exists()
    # Report + staging not yet written.
    assert not (evidence_folder / "Site-Safety-Audit-Report-260501-RPD.docx").exists()

    # Operator edits the Conformance Status of row 1 from "Unmatched"
    # to "NCR" and the CCVS code to "WAH-H6".
    import openpyxl
    wb = openpyxl.load_workbook(enriched_xlsx)
    ws = wb["Enriched Register"]
    headers = [str(c.value).strip().lower() if c.value else "" for c in ws[1]]
    status_col = headers.index("conformance status") + 1
    code_col = headers.index("ccvs code") + 1
    obs_col = headers.index("observation") + 1
    ws.cell(row=2, column=status_col, value="NCR")
    ws.cell(row=2, column=code_col, value="WAH-H6")
    ws.cell(row=2, column=obs_col, value="OPERATOR-EDITED FINDING")
    wb.save(enriched_xlsx)

    # Phase 2: --from-state
    payload2 = mod.run_once(evidence_folder, force=True, from_state=True)
    assert payload2["from_state"] is True
    assert payload2["staging_status"] == "bulk_uploadable"
    # Operator edits propagated to docx + staging.
    sx = evidence_folder / "Site-Visit-Report-Upload-PIMS-Staging-260501-RPD.xlsx"
    assert sx.exists()
    wb2 = openpyxl.load_workbook(sx)
    ws2 = wb2["Observations"]
    headers2 = [str(c.value).strip() if c.value else "" for c in ws2[3]]
    finding_col = headers2.index("finding") + 1
    status_col2 = headers2.index("conformance_status") + 1
    code_col2 = headers2.index("ccvs_code") + 1
    # The staging xlsx writes from EnrichedRow.finding, which gets
    # overwritten when the operator edits the Observation column in
    # the enriched xlsx during phase 1.
    finding_text = ws2.cell(row=5, column=finding_col).value
    assert finding_text == "OPERATOR-EDITED FINDING"
    assert ws2.cell(row=5, column=status_col2).value == "NCR"
    assert ws2.cell(row=5, column=code_col2).value == "WAH-H6"
    # Phase-2 diagnostics show the merge fired.
    assert payload2["merge_diag"]["applied"] is True
    assert payload2["merge_diag"]["field_overrides"] >= 3  # status + ccvs + finding


def test_run_once_from_report_round_trip(evidence_folder, monkeypatch):
    """Phase 3: operator edits the docx → flow back to enriched +
    staging xlsx. Round trip:
      1. Single-shot pipeline produces all 3 deliverables + state JSON.
      2. Operator edits the Recommendation cell in the docx for finding #1.
      3. --from-report rebuilds enriched + staging from state, applies
         the docx edit, and the new staging xlsx carries the edit."""
    def fake_apply(enriched, **kw):
        # First row becomes a non-Compliant finding so it lands in
        # the docx Findings section with a detail table.
        if enriched:
            enriched[0].finding = "Original finding text."
            enriched[0].finding_title = "Test finding title"
            enriched[0].conformance_status = "NCR"
            enriched[0].ccvs_code = "WAH-H6"
            enriched[0].ccvs_category = "Work at Height"
            enriched[0].location = "Original location"
            enriched[0].recommendation = "Immediate – original action"
            enriched[0].legal_ref = "WHS Reg cl.79"
            enriched[0].hierarchy_of_control = "Engineering: original control"
        return ("Stub narrative.", {
            "enabled": True, "rows_total": len(enriched),
            "rows_called": len(enriched), "rows_ok": len(enriched),
            "rows_failed": 0, "errors": [], "ra": {"path": None},
        })
    from pims.scripts import run_ssa_pipeline as mod
    monkeypatch.setattr(mod, "_apply_vision_enrichment", fake_apply)

    payload1 = mod.run_once(evidence_folder)
    assert payload1["staging_status"] == "bulk_uploadable"
    state = json.loads(
        (evidence_folder / ".ssa_state.json").read_text(encoding="utf-8"),
    )
    assert state.get("finding_render_order"), \
        "finding_render_order must be persisted for phase-3 pairing"

    # Operator edits the docx — find the first per-finding detail
    # table and overwrite the Recommendation cell.
    docx_path = evidence_folder / "Site-Safety-Audit-Report-260501-RPD.docx"
    from docx import Document as DocxDocument
    doc = DocxDocument(docx_path)
    detail = next(
        t for t in doc.tables
        if len(t.columns) == 2
        and t.rows[0].cells[0].text.strip() == "Location"
    )
    rec_row = next(
        r for r in detail.rows
        if r.cells[0].text.strip() == "Recommendation"
    )
    rec_row.cells[1].text = "Immediate – OPERATOR-EDITED ACTION"
    doc.save(docx_path)

    # Phase 3
    payload3 = mod.run_once(evidence_folder, force=True, from_report=True)
    assert payload3["from_report"] is True
    assert payload3["merge_diag"]["applied"] is True
    assert payload3["merge_diag"]["field_overrides"] >= 1
    # Edit propagated to the staging xlsx.
    sx = evidence_folder / "Site-Visit-Report-Upload-PIMS-Staging-260501-RPD.xlsx"
    wb = openpyxl.load_workbook(sx)
    ws = wb["Observations"]
    headers = [str(c.value).strip() if c.value else "" for c in ws[3]]
    rec_col = headers.index("recommendation") + 1
    # Find the row whose ccvs_code is WAH-H6 (the seeded NCR).
    code_col = headers.index("ccvs_code") + 1
    edited_row = None
    for r in range(5, ws.max_row + 1):
        if ws.cell(row=r, column=code_col).value == "WAH-H6":
            edited_row = r
            break
    assert edited_row is not None
    rec_cell = ws.cell(row=edited_row, column=rec_col).value or ""
    assert "OPERATOR-EDITED ACTION" in rec_cell


def test_run_once_two_phase_from_state_without_phase_one_raises(
    evidence_folder,
):
    """Phase 2 requires phase 1 to have run — bare --from-state on a
    folder without .ssa_state.json fails loud."""
    state = evidence_folder / ".ssa_state.json"
    if state.exists():
        state.unlink()
    with pytest.raises(FileNotFoundError, match="ssa_state.json"):
        run_once(evidence_folder, from_state=True)


def test_run_once_default_path_does_not_load_legacy_checklist(
    evidence_folder, monkeypatch,
):
    """Gap-8: default (vision) path skips the audit_checklist.xlsx
    load — vision is the canonical classifier and the legacy keyword
    fallback hit 5/21 with a misroute on real data. We stub
    ChecklistLookup.from_xlsx to fail loud so the test breaks if
    anything ever calls it on the default path."""
    from pims.services import ssa_checklist_lookup
    calls: list[str] = []

    def boom(path):  # pragma: no cover — fail loud
        calls.append(str(path))
        raise AssertionError(f"legacy checklist loaded on default path: {path}")

    monkeypatch.setattr(
        ssa_checklist_lookup.ChecklistLookup, "from_xlsx", staticmethod(boom),
    )
    # Stub the LLM driver so we don't need an API key in this test.
    monkeypatch.setattr(
        "pims.scripts.run_ssa_pipeline._apply_vision_enrichment",
        lambda *a, **kw: ("stub narrative", {"enabled": True, "rows_total": 0}),
    )
    payload = run_once(evidence_folder)  # default enrich=True
    assert payload["staging_status"] == "bulk_uploadable"
    assert calls == []


def test_run_once_no_enrich_with_explicit_checklist_loads_legacy(
    evidence_folder, tmp_path, monkeypatch,
):
    """Gap-8: legacy fallback only fires when the operator explicitly
    passes --no-enrich AND --checklist. Without --checklist the
    offline path runs with everything Unmatched (acceptable: the
    operator opted out of vision)."""
    cl_path = (
        Path(__file__).resolve().parent.parent
        / "pims" / "audit_checklist.xlsx"
    )
    assert cl_path.exists()
    payload = run_once(
        evidence_folder, enrich=False, checklist_path=cl_path,
    )
    assert payload["staging_status"] == "bulk_uploadable"
    # We don't assert specific matches — the keyword matcher is
    # noisy by design — only that the run completed and the
    # checklist hook ran (no PreflightError, no missing-file).


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


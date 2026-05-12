# Audit Report Renderer — Correct Template + Plan (v3)

**Date:** 2026-05-13
**Author:** Claude Code (Opus 4.7, 1M)
**Status:** Definitive. Supersedes the §4.8 plan in
`docs/plans/AUDIT_REPORT_REFERENCE_EVALUATION.md`. The §4.8 plan
adopted the wrong template; this plan corrects that.
**Awaiting:** operator approval before any code change.

---

## 1. The discovery

The audit-report renderer has been pointing at the wrong template
binary the whole time.

**Correct (canonical) template:**
- `C:\Users\AlanRichardson\gatekeeper\pims\RPD_SSA_template-inserted.docx`
- 9.4 MB, 457 paragraphs, 326 tables, 74 images.
- Structure matches the references exactly: `Executive Summary`,
  `Site Safety Inspection` headings only. **No** Part A/B/C/D. No
  Auditor Sign-off. Hierarchical category banners
  (`Planning and risk management | 17 / 17 (100%)`). Per-criterion
  checklist tables already structured for status badge +
  observation + photo embeds.
- Indexed by `pims/services/template_index.py` (a one-time indexer
  built explicitly for this template — see its line-1 docstring).

**Wrong template the audit-report renderer is using:**
- `C:\Users\AlanRichardson\gatekeeper\pims\audit_report_template.docx`
- 4.4 MB, 188 paragraphs, 103 tables. Simpler, degraded "shipped"
  template. Referenced from
  `pims/audit_report_docx.py:44 TEMPLATE_PATH`.

**Stale reference:**
- `pims/services/site_visit_report.py:47` references
  `RPD_SSA_template.docx` (without `-inserted`). That file
  **does not exist** on disk. The Site Visit Report renderer's
  template path is broken — likely a latent bug separate from the
  audit-report issue.

## 2. Evidence the references came from the canonical template

Compared structurally with the Cremorne reference
(`pims/7_Hampden_Rd_Cremorne.docx`):

| Marker | Cremorne reference | RPD_SSA_template-inserted | audit_report_template (wrong) |
|---|---|---|---|
| `Executive Summary` heading | yes | yes | yes |
| `Site Safety Inspection` heading | yes | yes | no |
| Hierarchical category banners | yes | yes | no |
| Per-criterion checklist tables | yes (272 tables) | yes (326 tables) | no (103 tables) |
| `Part A/B/C/D` headings | **no** | **no** | no (renderer emits them) |
| Auditor Sign-off block | no | no | no (renderer emits it) |

The reference's structure is **only achievable** from the
RPD_SSA_template-inserted.docx baseline. The simpler audit-report
template lacks the category banners and per-criterion tables that
the references carry verbatim.

## 3. Why this wasn't caught earlier

A factual list, no excuses:

1. The repo carries **two parallel template paths** that drifted
   apart:
   - audit-report flow → `audit_report_template.docx` (simple/old)
   - site-visit-report flow → `RPD_SSA_template-inserted.docx`
     (rich/canonical) via `template_index.py`
2. **No `TEMPLATE_REGISTRY.md`** in `docs/` enumerating which
   template each renderer consumes. Templates are invisible unless
   you grep `*.docx` AND `TEMPLATE_PATH` constants AND check the
   service modules.
3. **Reference docx files have no sidecar metadata** declaring
   their producing template / commit. `pims/7_Hampden_Rd_Cremorne.docx`
   and `pims/56-58_Fraters_Ave_Sans_Souci.docx` sit untracked in
   git, no `.meta.json`.
4. **The audit-report renderer's `_append_site`** function emits
   Part A/B/C/D + a body Site Safety Inspection section. This made
   sense for the simple shipped template (which has no such
   sections). It produces duplicate content when paired with the
   canonical template (which already has the sections built in).
   Nothing in code enforces "renderer ⇄ template" pairing.
5. **The session's prior diagnoses** (`791e167` regression, then
   "adopt feat/audit-report-visual-polish") closed real defects
   (CONTRACTOR_CONFIG, cover placeholders, score precision, typo
   strip, photo filter) but missed the structural template mismatch
   because both diagnoses chased the renderer codebase without
   broadening the search to "what other templates exist?".
6. `pims/services/template_index.py:1` says verbatim "One-time
   index of RPD_SSA_template-inserted.docx" — that line is the
   smoking gun, sitting unused by the audit-report path for the
   entire session.

## 4. Current state (post-`df80599`)

What's correct on `main` and stays:

- `CONTRACTOR_CONFIG` RPD entry (`Matthew McCarthy`, no `Matt M`
  prefix).
- `title_display_name` key for trade-name title rendering.
- `report_issue_date` plumbing — route → `SiteData` → renderer.
  Six route-level test cases cover the matrix.
- `_format_audit_date` helper.
- Integer percent in `_score_totals`.
- Fingerprint contract test (reference-file pin) +
  baseline snapshots.
- Anthropic SDK migration, site resolver, CCVS fallback,
  approve-time guard, SDGroup PDF promote — all unaffected.

What's wrong on `main` and must change:

- `pims/audit_report_docx.py:44 TEMPLATE_PATH` points at the wrong
  template binary.
- `_append_site` emits Part A/B/C/D + body Site Safety Inspection
  + Auditor Sign-off content that the canonical template already
  carries. With the canonical template, the renderer must
  **populate existing structure**, not append new sections.
- `pims/scripts/clean_audit_report_template.py` cleans the wrong
  template binary. Either retire it or repoint at the canonical
  one (probably retire — the canonical template doesn't need
  cleaning).
- Tests `tests/test_audit_report_template_clean.py` and
  `tests/test_audit_report_body_section.py` are anchored on the
  wrong template; rewrite or retire.
- Tests asserting Part A/B/C/D structure
  (`tests/test_audit_report_docx_smoke.py` — the ten previously
  skipped Phase D/E/F/G tests + the fixture-driven smoke test)
  need rewriting to assert the canonical template's structure.

## 5. Plan — Path B refactor (index-and-fill)

Pattern to copy: `pims/services/site_visit_report.py` already
uses `template_index.py` to index a template and inject data into
existing cells. Mirror that approach for the audit report.

### Step 1 — Repoint the template

- `pims/audit_report_docx.py:44`
  `TEMPLATE_PATH = PIMS_DIR / "RPD_SSA_template-inserted.docx"`
- Verify the path exists and is the only template the audit-report
  flow consumes.

### Step 2 — Inventory what the canonical template carries

Pre-existing in the template binary:

- Cover (page 1): AuditCo title-page text frames, all the
  `[Insert …]` placeholders (`[Insert Site Address]`,
  `[Insert Executive Summary]`, `[Insert Current Date]`,
  `[Insert Site Conducted]`, `[Insert Prepared by]`,
  `[Insert Date of inspection]`, `[Insert Score]`,
  `[Insert Flagged]`, `[Insert Category Score]`).
- Cover/header bar: `Robertson's Remedial and Painting – Site
  Safety Audit Report`.
- Body `Site Safety Inspection` heading + KPI table.
- Section banners for the 9 sections enumerated in
  `template_index.py::SECTIONS_ORDERED`.
- Per-criterion 1×2 tables (criterion text | status badge) with
  default `Compliant` shading.
- Per-criterion 2×N observation tables sitting underneath, with
  photo slots in row 1.

### Step 3 — Rewrite `_append_site` to fill, not emit

Current `_append_site` (lines ~1218 onward in the adopted renderer)
emits:

- `Part A — Open Actions Register` heading + bordered actions table.
- `Part B — Site Visit Summary` heading + metadata table + exec
  summary duplicate.
- `Part C — Site Safety Inspection Checklist` heading + summary
  banner + grouped checklist with embedded photos.
- `Part D — Auditor Sign-off` heading + disclaimer + signature
  table.

None of that should run against the canonical template. New
behaviour:

1. Build the `TemplateIndex` once via `template_index.get_index()`.
2. For each `LineItem` produced by the index:
   - If observation(s) match this line item (via the same
     `ccvs_code` / `ccvs_category` rules `pims/services/
     checklist_matcher.py` already implements):
     - Shade the status cell per the matched observation's
       conformance status using `STATUS_PALETTE`.
     - Populate the observation cell with finding text.
     - Embed each matched observation's photo in the corresponding
       photo slot in row 1 of the 2×N observation table.
   - If no observations match:
     - Section in `COMPLIANT_DEFAULT_SECTIONS` → leave default
       Compliant shading.
     - Section in `NA_SECTIONS` → set N/A shading; blank narrative.
3. Increment a single global `photo_counter` across the whole
   document (per Codex resolved decision 1; matches the reference).
4. Do NOT emit Part A/B/C/D. Do NOT call `_part_d_signoff`.
5. Cover placeholders (`[Insert Site Address]` etc.) populate via
   the existing `_populate_cover` walk — no change needed there
   beyond removing assumptions baked in for the wrong template.

### Step 4 — Reuse the existing matcher

`pims/services/checklist_matcher.py` already implements
observation → checklist-line-item matching for the Site Visit
Report path. Reuse the same matcher for the audit report. Don't
re-implement.

### Step 5 — Retire / repoint the wrong-template scaffolding

- `pims/scripts/clean_audit_report_template.py` — retire (the
  canonical template is operator-curated and doesn't need a
  programmatic cleaner). Move it to `pims/scripts/_archive/` or
  delete outright. If retained, repoint at the canonical template
  AND audit its rules so it doesn't strip canonical content.
- `pims/audit_report_template.docx` — retire from the audit-report
  flow. Keep it in the repo as a historical artefact under
  `pims/_archive/` or delete.
- `tests/test_audit_report_template_clean.py` — retire (cleaner
  retired) or rewrite for the canonical template.
- `tests/test_audit_report_body_section.py` — retire or rewrite.
- `tests/test_audit_report_docx_smoke.py` — rewrite the ten
  Phase D/E/F/G tests + the smoke test to assert canonical
  template structure (Executive Summary / Site Safety Inspection /
  per-criterion structured blocks, NOT Part A/B/C/D).

### Step 6 — Refresh the fingerprint contract

The existing `tests/test_audit_report_contract.py` snapshot
baselines are correct (they came from the reference docx files,
which were produced by the canonical template). What changes:

- The render-against-fixture extension (Codex finding 1, still
  out of scope at the moment) becomes feasible once the renderer
  uses the canonical template — fixture render + fingerprint
  assertion can actually match the references' shape.

### Step 7 — Regenerate v6 + side-by-side vs Cremorne

Same recipe as v5 — POST to `/pims/audit-report/rpd`, save to
`G:\My Drive\alan_mcxico\SSA-evidence\2026-05-12-RPD-01\Audit_Report_96-98_Hampden_Rd_Russel_Lea_v6.docx`,
fingerprint vs `pims/7_Hampden_Rd_Cremorne.docx`. Specific
assertions:

- `Part A/B/C/D`: 0 occurrences (was 4 / 3 / 2 / 2 in v5).
- `12 / 13 (92.31%)` 2-decimal residue: 0 (was 2 in v5; template
  residue gone once we switch templates).
- Table count ≈ 272 (matches reference; was 205 in v5).
- Image count: ≈ Cremorne's 8–9 (was 27 in v5; canonical template
  has 74 images but only renders the right subset).

### Step 8 — Decision record

`docs/decisions/2026-05-13-audit-report-canonical-template-switch.md`
recording the template mismatch as the actual root cause and
documenting the renderer-emit → renderer-fill pivot.

## 6. Risks

1. **`template_index.py` was built for the Site Visit Report
   path.** It might assume things specific to SVR (e.g., a
   `checklist_matcher` state model that doesn't align with the
   audit-report's NCR/Conditional/Info statuses). May need
   parametric extension. Mitigation: read it thoroughly before
   wiring it into the audit-report renderer.
2. **`site_visit_report.py:47` already references a
   nonexistent file** (`RPD_SSA_template.docx`). If the SVR path
   is broken in production, fixing it is a separate
   responsibility — but in scope to flag, not to fix here.
3. **The canonical template has 74 images** vs 8–9 in the
   references. Some of those are template artwork (logos, header
   strips); some may be example photos the template carried. The
   cleaner pattern (if we keep one) needs to know which are
   structural and which are removable. Mitigation: inspect the
   template's image list before assuming.
4. **`_populate_cover` was written for the wrong template's
   placeholders.** The canonical template may have additional
   placeholders the current renderer doesn't know about (e.g.
   `[Insert Category Score]` already shows up in
   `_build_cover_replacements`, but there may be more). Test by
   rendering against fixture input and grepping the output for
   `[Insert ` survivors.
5. **Test re-writes are substantial.** Ten Phase D/E/F/G tests
   assert Part D structure that won't exist. The cover test
   asserts the wrong template's behaviour. Allow ~30 min for test
   rewrites alone.
6. **No timeline pressure has been stated, but this is a
   not-small refactor.** Estimated 2–3 hours of focused work,
   plus 10 minutes of operator side-by-side sign-off on v6.

## 7. Process guardrails (must land in the same commit as the fix)

These were filed in `AUDIT_REPORT_REFERENCE_EVALUATION.md` §6 but
not implemented. Add now:

1. **`docs/TEMPLATE_REGISTRY.md`** — one line per template:
   path, purpose, consuming renderer module, last commit that
   produced any reference artefacts from it.
2. **Sidecar `.meta.json` for each reference docx**:
   - `pims/7_Hampden_Rd_Cremorne.docx.meta.json`
   - `pims/56-58_Fraters_Ave_Sans_Souci.docx.meta.json`
   Fields: `producing_template`, `producing_commit` (best-known),
   `produced_date`, `produced_by`, `notes`.
3. **In-renderer contract docstring** at the top of
   `pims/audit_report_docx.py` declaring the template it
   consumes and pointing at the registry. Same for
   `site_visit_report.py` once its broken path is fixed.
4. **A two-line CI check** that asserts:
   - Every `TEMPLATE_PATH` constant resolves to an existing file.
   - Every renderer module's declared template appears in
     `TEMPLATE_REGISTRY.md`.

## 8. Scope boundaries

In scope for the next commit:
- Steps 1–6 of §5.
- §7 process guardrails (registry + sidecars + docstring + CI
  check).

Out of scope:
- Fixing `pims/services/site_visit_report.py:47` (broken
  `RPD_SSA_template.docx` reference). Separate ticket.
- Render-against-fixture extension of the fingerprint contract
  test. Already out of scope per Codex finding 1.
- Long-lived-branch alarm (G1 from the existing process-guardrail
  list).

## 9. Acknowledgement

The §4.8 plan adopted the feature branch wholesale, on the
assumption that branch's renderer produced the references. The
structural mismatch (no Part A/B/C/D in references, but Part
A/B/C/D in v5) was the signal that the assumption was wrong. I
attributed that mismatch to operator hand-editing rather than
template mismatch. The correct interpretation was the opposite:
the references are render-pristine output from a renderer that
uses the canonical template; the feature branch's renderer was
NOT that renderer.

The corrections this plan applies do not invalidate the §4.8
work — `CONTRACTOR_CONFIG`, `report_issue_date`, score precision,
the typo strip, and the cover placeholder walk are all still
right. What changes is the template the renderer consumes and the
body emission strategy.

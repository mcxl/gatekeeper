# Audit Report — Reference Evaluation, Defect Catalog, Implementation Plan, Process Guardrails

**Date:** 2026-05-12
**Author:** Claude Code (Opus 4.7, 1M)
**Reference inputs evaluated (both confirm the contract):**
- `G:\My Drive\alan_mcxico\SSA-evidence\2026-05-12-RPD-01\7_Hampden_Rd_Cremorne.pdf` (30 pages)
- `G:\My Drive\alan_mcxico\SSA-evidence\2026-05-12-RPD-01\56-58_Fraters_Ave_Sans_Souci.pdf` (29 pages)
**Current production output evaluated:**
- `G:\My Drive\alan_mcxico\SSA-evidence\2026-05-12-RPD-01\Audit_Report_96-98_Hampden_Rd_Russel_Lea_v4.docx`
- v4 screenshots in `G:\My Drive\alan_mcxico\SSA-evidence\2026-05-12-RPD-01\screenshots\`
**Per-PDF page renders for cross-reference:**
- `G:\My Drive\alan_mcxico\SSA-evidence\2026-05-12-RPD-01\7_Hampden_Rd_Cremorne_pages\`
- `G:\My Drive\alan_mcxico\SSA-evidence\2026-05-12-RPD-01\56-58_Fraters_Ave_Sans_Souci_pages\`
**Status:** definitive; §5 resolved by Codex review (2026-05-12),
§4 updated to fold in the resolutions. Awaiting operator "go".
Supersedes
- `C:\Users\AlanRichardson\gatekeeper\docs\plans\AUDIT_REPORT_RENDERER_DIAGNOSIS.md`
- `C:\Users\AlanRichardson\gatekeeper\docs\plans\AUDIT_REPORT_COVER_GAP_DIAGNOSIS.md`
- `C:\Users\AlanRichardson\gatekeeper\docs\plans\AUDIT_REPORT_FULL_GAP_AND_PLAN.md`

## 1. The contract (what the references prove)

Both reference PDFs follow the **same** structure. The Fraters PDF
renders cleanly (no font-substitution glitches); the Cremorne PDF
shows the same content with occasional missing-glyph boxes where
specific font ligatures lack embedded glyphs in the PDF (cosmetic,
not a content defect).

### 1.1 Page 1 — Title page (AuditCo branded cover)

Background: dark navy. Decorative orange circle motif + large
checkmark icon top-right. Small grey circles as accents.

Top-left:
- AuditCo logo (orange circle with white checkmark + orange "AuditCo" wordmark)
- Underline + date strip beneath the logo (e.g. `03 May 2026`)

Centre, large white sans-serif:
- `Site Safety Audit` (one line)
- `<Site Address>` (the audited site, e.g. `7 Hampden Rd Cremorne` or `56-58 Fraters Ave Sans Souci`; can wrap to two lines for long addresses)
- `Audit Report` (smaller, third line)

Lower-left, small white text:
- `Prepared by`
- `Alan Richardson, AuditCo`
- (blank line)
- `Prepared For`
- `Matthew McCarthy`
- `Robertson's Remedial and Painting Pty Ltd`
- `10/ 56 Buffalo Road, GLADESVILLE 2111`

Bottom-left, rotated vertical:
- `auditco.com`

### 1.2 Page 2 — Executive Summary

Top-right corner: small AuditCo logo (white-on-orange checkmark + orange wordmark).
Top: framed header bar `Robertson's Remedial and Painting – Site Safety Audit Report`.

Body (left-aligned, white background):
- `<Site address>` (e.g. `7 Hampden Rd Cremorne`)
- (blank line)
- `Executive Summary` (bold heading, slightly larger)
- One paragraph: `A site safety audit was conducted at <site address> on <date>. <auditor's narrative — context for the audit and any high-level commentary>`
- (blank line)
- 0..N "finding-summary" bullets — one per NCR/Conditional finding, written in plain-language consultant tone (NOT the raw observation text — a polished summary line per flagged item)
- (blank line)
- `Score` (bold)
- `<numerator> / <denominator> (<integer-percent>%)` value (e.g. `45 / 47 (96%)`)
- (blank line)
- `Flagged Items` (bold)
- `<count>` value (e.g. `2`)
- (blank line)
- `Findings` (bold heading)
- One block per NCR/Conditional, exactly two paragraphs each:
  - `NCR #<N>. <CCVS Category> – <CCVS Subcategory or sub-tag> – <observation_text_enriched or polished finding text>`
  - `Required action: <action_description / recommendation / specific instruction>`

Footer (all pages from p2 onwards): `Date: <date>  Page: <N> of <total>  Written By: Alan Richardson`.

### 1.3 Page 3 onwards — Site Safety Inspection

Section heading: `Site Safety Inspection` (bold, slightly larger).

KPI summary table (6-column, single row):
- `Score | <numerator>/<denominator> (<integer-percent>%) | Flagged observations | <count> | Open actions | <count>`
- Light-grey shaded header row.

Metadata rows (each 2-cell label/value):
- `Site conducted | <site address>`
- `Prepared by | <auditor name>` (e.g. `Alan Richardson` — no "AuditCo" suffix here)
- `Date of inspection | <date>` (formatted `<D> <Month-abbreviated-3-letter> <YYYY>`, e.g. `29 Apr 2026`)

Spacer.

**Section-score banner row** (2-cell):
- `Site Inspection | <overall score>` (light-grey shading)

**Category banner row** (2-cell, light-grey shading):
- `<Category name> (project value >$250K)` (the parenthetical applies only when tier-gated) `| <category numerator>/<category denominator> (<integer-percent>%)`

**Per-criterion blocks** — repeat for each checklist row in the category:

Block layout:
- Two-cell row: criterion text (left, bold) | status badge (right, colour-shaded):
  - Compliant → green (#1E8449 or similar emerald)
  - NCR → red (#C0392B or similar)
  - Conditional → amber/orange
- Below the badge row, for each MATCHED observation against this criterion:
  - `#<N>. <Status>` (bold, e.g. `#1. NCR` or `#3. Compliant`). This is the **block-scoped** counter — i.e. it counts matched observations within a single criterion block, starting at #1 each block. (Distinct from the global `Photo <N>` counter in §1.3 photo strip, which never resets — see §5 item 1.)
  - `Observation: <observation_text>` (raw observer note)
  - `Finding: <observation_text_enriched>` (polished consultant write-up)
  - `CCVS Code: <code>` (e.g. `WAH-H6`)
  - `CCVS Category: <category – sub>` (e.g. `Working at Height – Scaffold`)
  - For NCR/Conditional only: `Required action: <action_description>`
  - For all: `Due Category: <due_category>` (e.g. `Immediate`, `N/A`)
- Photo strip at the bottom of the block:
  - Each matched observation that has a `photo_url` gets one inline image (~3.5 cm wide).
  - Photos are placed left-to-right in observation order.
  - Each photo carries a small italic caption `Photo <N>` where `<N>` is the running counter across the **whole report** (Photo 1, 2, 3, … through to the end).
- A thin horizontal rule separates each criterion block from the next.

**Unmatched criteria** (checklist row with no observation):
- Two-cell row: criterion text | `Compliant` badge (green).
- No `#N. <Status>` block beneath, no photos.
- Implies the criterion is verified compliant by absence of any flagged observation.

### 1.4 No "Part A" / "Part B" / "Part C" / "Part D" / "Auditor Sign-off"

The references contain none of these section labels. Body sections
are simply: Executive Summary → Findings → Site Safety Inspection.
No Auditor Sign-off block.

### 1.5 Footer (all pages)

`Date: <DD Month YYYY>  Page: <N> of <total>  Written By: Alan Richardson`

Filled, no `[Insert …]` placeholders, no junk prefix.

## 2. Defect catalog (current production v4 vs the references)

D-codes prefixed `T` are title-page defects, `B` body, `S` Site
Safety Inspection, `F` footer, `X` cross-cutting.

| Code | Where | Defect | Severity |
|---|---|---|---|
| T1 | Title page | Date strip `[Insert Current Date]` placeholder unfilled | Major |
| T2 | Title page | Site address line shows literal `[Site Address]` (different placeholder name than `[Insert Site Address]` that the renderer knows; the title-page text-frame uses `[Site Address]`) | Major |
| T3 | Title page | `Prepared For` block has stray `Matt M` prefix → reads `Matt M Matthew McCarthy` instead of `Matthew McCarthy` | Major |
| T4 | Title page | Title shows `Site Safet Audit` (missing `y`) — a typo in the template's text-frame string (NOT a font-substitution issue — the docx itself has the typo) | Major |
| T5 | Title page | Renderer cannot walk `<w:txbxContent>` / `<a:t>` (DrawingML text frame) content; consequence is that T1, T2, T4 cannot be fixed via current `_populate_cover` | Architectural |
| B1 | Body page 2+ | `Robertson's Remedial and Painting – Site Safety Audit Report` header bar — present and correct | OK |
| B2 | Body page 2 | Site address heading — present and correct | OK |
| B3 | Body page 2 | Executive Summary heading + opener — present, correct format | OK |
| B4 | Body page 2 | Finding-summary bullets on cover — present | OK (post-`f6a7c01`) |
| B5 | Body page 2 | Score / Flagged Items blocks — present and correct | OK |
| B6 | Body page 2 | Findings section: NCR #N. paragraph + Required action paragraph per NCR | OK |
| S1 | Site Safety Inspection | KPI summary table labels — Flagged observations / Open actions match | OK (post-`f6a7c01`) |
| S2 | Site Safety Inspection | Metadata rows — Site conducted / Prepared by / Date of inspection | OK |
| S3 | Site Safety Inspection | `Site Inspection` section-score banner row — present and correctly populated with overall score (post-`f6a7c01`) | OK |
| S4 | Site Safety Inspection | Category banner row (`<Category name> | <category score>`) — **missing** | Major |
| S5 | Site Safety Inspection | Per-criterion block uses 2x2 mini-table with `Category | Result` header + `<criterion>` / `<status>`-shaded cell. Reference uses a 2-cell row (criterion left, badge right) with no header row | Major |
| S6 | Site Safety Inspection | Block contents missing the `#N. <Status>` header line per matched observation | Major |
| S7 | Site Safety Inspection | Block contents missing the `Observation: <text>` / `Finding: <text>` / `CCVS Code: <code>` / `CCVS Category: <category>` / `Due Category: <due>` structured lines | Major |
| S8 | Site Safety Inspection | Photos filtered to NCR/Conditional only (commit `11b8047`) — reference shows photos on Compliant rows too (Photos 3, 4, 5, 6 in Cremorne are all Compliant rows) | Major (regression — D9 fix was wrong against the reference) |
| S9 | Site Safety Inspection | Photo caption numbering: reference uses running `Photo <N>` counter; v4 uses the same pattern but the count differs because filtering is wrong | Minor (corrects when S8 is fixed) |
| S10 | Site Safety Inspection | Status badge styling: reference uses big colour-shaded right cell with white bold label (`Compliant` green, `NCR` red); v4 uses smaller shaded variant | Minor (cosmetic) |
| S11 | Site Safety Inspection | Hierarchical indent — reference shows Site Inspection → Category → Criterion → Per-observation block. v4 emits criterion blocks flatly | Major |
| F1 | Footer | `<date>` displays with stray leading `22` (e.g. `22Date: 12 May 2026`) | Major |
| F2 | Footer | `Page: <N> of <total>` missing the total page count (just `Page: 2 of`) | Major |
| F3 | Footer | Footer text spans header AND footer — the `Robertson's Remedial and Painting – Site Safety Audit Report` framed bar is the header on every page from p2; v4 has it; reference has it | OK |
| X1 | Cross-cutting | Trailing `Contact Us` AuditCo template page appears at the END of the body (template-resident content not stripped by cleaner) | Minor (cosmetic; reference may or may not include this — both Cremorne and Fraters reach 29–30 pages, mine reaches similar; check operator preference) |
| X2 | Cross-cutting | Photo source is the high-res Supabase originals (verified — 4032×3024 JPEGs); the embedded photos display correctly but at a different resolution than the reference (which embedded the photos as portrait 370×493 — operator's iPhone screen-captured/resized before upload? Or the reference renderer used a smaller thumbnail box). Cosmetic only — content is correct | Minor |

## 3. Why this happened — five-factor root cause

1. **Unmerged feature branch.** `feat/audit-report-visual-polish`
   (commits `9a69239` Phase H1, `e953c45` Phase H2, `4a0e651`
   Phase H pre-3) holds the renderer + template combination that
   produced these references. It was never merged to `main`. Three
   weeks elapsed (24 Apr → 12 May) without a merge or PR.
2. **A destructive chore commit on main.** Commit `791e167`
   (2026-05-03, "Slice 3 field-flow + photo embed") made 179 lines
   of undocumented "audit_report_docx.py adjustments" AND deleted
   `pims/audit_report_template.docx` as "unused". The commit
   message did not list what the adjustments were. The template was
   the post-Phase-H1-clean state; deleting it was a regression.
3. **Half-restoration without renderer revert.** Commit `64303ca`
   (2026-05-09) restored the binary but from the pre-Phase-H1 state
   (i.e. an older version), and did NOT revert the renderer
   changes from `791e167`. The renderer drifted further from the
   template; the template drifted further from the references.
4. **The reference docx files weren't tied to a commit.** Both
   `pims/7_Hampden_Rd_Cremorne.docx` and
   `pims/56-58_Fraters_Ave_Sans_Souci.docx` sit in the repo
   untracked. They are evidence files, not source. Nothing in CI
   guards the renderer against their contract.
5. **Iterative patching by me.** Once asked to fix the output, I
   should have:
   - run `git branch -a` to find unmerged work touching the same
     files;
   - dumped the references with full python-docx walk including
     DrawingML text frames before designing fixes;
   - written a structural fingerprint test against the references
     BEFORE writing any renderer change.
   Instead I made nine forward-progress commits patching on top of
   `main` and only realised the cover lived in text frames after
   the operator surfaced the screenshots.

## 4. Implementation plan — single coordinated commit

### 4.1 Bring the feature branch's renderer + template to main

```sh
git fetch origin feat/audit-report-visual-polish
git checkout -b chore/adopt-audit-report-visual-polish
git checkout origin/feat/audit-report-visual-polish -- \
    pims/audit_report_docx.py \
    pims/audit_report_template.docx \
    pims/scripts/clean_audit_report_template.py \
    tests/test_audit_report_template_clean.py \
    tests/test_audit_report_body_section.py
```

### 4.2 Reconcile the data layer

`pims/routes.py` must match the feature-branch `SiteData` signature.
Specifically:

- Remove the D9 photo-filter that restricts to NCR/Conditional.
  Pre-fetch photos for **all** observations — the feature-branch
  renderer decides per-row whether to embed (and the reference
  shows photos on Compliant rows).
- Keep the data-layer wins from this session unchanged:
  - Anthropic SDK migration (commit `d39859c`).
  - Site resolver on every write path (commit `c3a81d9`).
  - CCVS deterministic fallback + dashboard chip (`d4205bc`,
    `b2e4b7f`).
  - Approve-time enrichment guard + idempotent approve
    (`668b168`).
  - SDGroup backend PDF promote (`4d9835b`).
- Adjust `SiteData(...)` construction in `routes.py` to match the
  feature-branch dataclass field set (only field present on the
  feature-branch `SiteData` should be passed).

### 4.3 Lock the contract with a fingerprint test

New: `tests/test_audit_report_contract.py`

For each of the two reference docx files
(`pims/7_Hampden_Rd_Cremorne.docx`,
`pims/56-58_Fraters_Ave_Sans_Souci.docx`):

- Extract a structural fingerprint:
  - Every non-empty paragraph text (cover body — paragraphs only,
    not text frames).
  - Every text-frame `<a:t>` value (cover title page).
  - Every table shape (`rows × cols`) and every non-empty cell's
    stripped text, in order.
  - Every section header/footer text.
  - Count of embedded images.
- Persist the fingerprints as JSON snapshots in
  `tests/fixtures/audit_report_contracts/`.
- The test loads the snapshot, renders the audit report against
  fixture data designed to produce the SAME outputs (same flagged
  count, same scores), and asserts the fingerprint matches.
- Fixture data lives in `tests/fixtures/audit_report_inputs/`
  (synthetic — does not depend on production Supabase).

This test fails any future change that regresses the contract.

### 4.4 Title-page renderer audit (text-frame walker)

Confirm Phase H2's `_populate_cover` in the feature branch already
walks `<w:txbxContent>` / `<a:t>`. If yes, the title-page defects
T1–T4 close automatically when the placeholders match the
template:

- Replace `[Site Address]` (the text-frame placeholder name) with
  the audited site address.
- Replace `[Insert Current Date]` with the **report issue date**
  (see 4.4a). Format `<DD Month YYYY>` to match reference.
- The `Site Safet Audit` typo is fixed by the cleaner script's
  text-frame pass: replace the literal token in any
  `<a:t>` or `<w:t>` inside a text-frame. Add an entry to
  `EXACT_PARAGRAPH_MATCHES` (or its text-frame equivalent in the
  feature-branch cleaner) for `Site Safet Audit → Site Safety
  Audit`.
- The `Matt M` prefix on the Prepared-For block is replaced by
  the `CONTRACTOR_CONFIG` lookup added in 4.4b — the stray prefix
  goes away by construction, not by typo-strip in the cleaner.

### 4.4a Report issue date (resolved decision 4)

- Add `report_issue_date: Optional[date]` to `AuditReportRequest`
  in `pims/routes.py`. Route resolves to `date.today()` (Australia/
  Sydney) if the request omits it. Result is a single deterministic
  date value passed to the renderer.
- `SiteData` gains `report_issue_date: date` (NOT `str`) so the
  renderer never reformats / parses. The renderer formats it once
  for display: `DD Month YYYY` on the title page AND in the
  page-2+ footer (same string in both surfaces).
- Renderer must NOT call `date.today()`. Stable input → stable
  fingerprint → contract test reproducible.

### 4.4b CONTRACTOR_CONFIG (resolved decision 3)

In `pims/audit_report_docx.py` (matches Phase H2's existing
constant pattern):

```python
# Keyed by canonical sites.client_name.
CONTRACTOR_CONFIG: dict[str, dict[str, str]] = {
    "Robertson's Remedial and Painting Pty Ltd": {
        "prepared_for_name":    "Matthew McCarthy",
        "prepared_for_company": "Robertson's Remedial and Painting Pty Ltd",
        "prepared_for_address": "10/ 56 Buffalo Road, GLADESVILLE 2111",
    },
}
```

Title-page text-frame replacements for the Prepared-For block read
from this dict via `sites[0].client`. If `client_name` is missing
or unknown, fall back to leaving the placeholder paragraphs empty
(NOT a hard fail — let the operator see the gap and decide).

`Matt M` text-frame fragment is overwritten by the
`prepared_for_name` value above, so the stray prefix is removed by
the same write path that fills the legitimate contact lines. No
separate cleaner rule needed.

### 4.5 Footer

`Date: <DD Month YYYY>  Page: <N> of <total>  Written By: Alan Richardson`

The feature branch's renderer should already produce this. Two
required behaviours:

1. `<DD Month YYYY>` = the report issue date from 4.4a (same date
   used on the title page).
2. `Page: <N> of <total>` uses Word `PAGE` and `NUMPAGES` field
   codes, not literal text — the feature branch's
   `_replace_inline_placeholder` is field-safe (preserves
   `<w:fldChar>` / `<w:instrText>` runs) so this works.

### 4.5a Photo counter (resolved decision 1)

Single global counter scoped to the **whole report**. Never resets
per-block or per-site. For multi-site reports, counter continues
from the first site through to the last. Implementation: a single
`list[int]` initialised once in `build_audit_report_docx`,
threaded into each `_append_site` and each `_checklist_row_block`
call. The feature branch's renderer already follows this pattern
(shared `photo_counter[0]` mutable list); no change needed if
adopted wholesale.

### 4.5b Trailing AuditCo `Contact Us` page (resolved decision 2)

**Preserved in v5.** It is part of the reference contract. The
cleaner script's `EXACT_PARAGRAPH_MATCHES` list must NOT include
any of the Contact Us page strings (`Connect with us online via
these contact details`, `Auditors located across 20+ locations
Australia-wide`, the phone-number block, etc.). If a future commit
intentionally removes the Contact Us page, that's a contract
change with its own ADR + fingerprint snapshot update.

### 4.6 Validation

- Regenerate Hampden Rd Russel Lea as v5 against the deployed
  feature-branch renderer.
- Side-by-side comparison: every defect in §2 either flips to OK
  or has a documented exception with operator sign-off.
- Save v5 next to v4 in
  `G:\My Drive\alan_mcxico\SSA-evidence\2026-05-12-RPD-01\`.

### 4.7 Single commit boundary

One commit containing:
- The three feature-branch source files (renderer, template,
  cleaner).
- The `routes.py` reconcile.
- The contract test + snapshot fixtures.
- An ADR in
  `docs/decisions/2026-05-12-adopt-audit-report-visual-polish.md`
  documenting the merge-forward and why.

### 4.8 Execution handoff (authoritative)

This is the implementation contract. When the operator says "go",
execute exactly these steps, in this order, in one coordinated
commit.

**Implementation plan:**

1. **Adopt the feature-branch renderer and template onto `main`.**
   Source branch: `feat/audit-report-visual-polish`. Bring forward
   verbatim:
   - `pims/audit_report_docx.py`
   - `pims/audit_report_template.docx`
   - `pims/scripts/clean_audit_report_template.py`
   - `tests/test_audit_report_template_clean.py`
   - `tests/test_audit_report_body_section.py`

2. **Reconcile the live route to the adopted renderer shape.**
   - Update `pims/routes.py` to match the adopted `SiteData` fields
     exactly.
   - Keep current `main` data-layer wins intact (Anthropic SDK
     migration, site resolver, CCVS fallback, approve guard,
     SDGroup PDF promote).
   - Prefetch photos for ALL observations (not NCR/Conditional only
     — revert D9 filter).
   - Pass the report issue date explicitly at the route boundary
     (new `report_issue_date` field on `AuditReportRequest`).
   - Do NOT call `date.today()` inside the renderer.

3. **Implement the resolved output decisions in the same commit.**
   - Keep the trailing AuditCo `Contact Us` page.
   - Use one global `Photo N` counter across the whole report.
   - Use block-scoped `#N. <Status>` numbering per criterion block.
   - Use `CONTRACTOR_CONFIG` keyed by `sites.client_name` for the
     `Prepared For` block. RPD entry renders exactly:
     - `Matthew McCarthy`
     - `Robertson's Remedial and Painting Pty Ltd`
     - `10/ 56 Buffalo Road, GLADESVILLE 2111`
   - Stray `Matt M` prefix overwritten by construction (text-frame
     write), not by cleaner typo-strip.
   - Title-page date = report issue / sign-off date, not inspection
     date.
   - Ignore the Cremorne PDF glyph artefact.

4. **Lock the contract with a fingerprint regression test.**
   - Add `tests/test_audit_report_contract.py`.
   - References:
     - `pims/7_Hampden_Rd_Cremorne.docx`
     - `pims/56-58_Fraters_Ave_Sans_Souci.docx`
   - Snapshot fixtures under:
     - `tests/fixtures/audit_report_contracts/`
     - `tests/fixtures/audit_report_inputs/`
   - Assert structure, text-frame content, tables, headers/footers,
     and embedded-image counts.

5. **Verify title-page text-frame paths and footer paths.**
   - Renderer walks `<w:txbxContent>` / `<a:t>` (DrawingML).
   - Title-page placeholders populate correctly.
   - Footer date + `PAGE` / `NUMPAGES` field codes render correctly.
   - Footer date uses the explicit report issue date.

6. **Regenerate the report as v5 and validate against the references.**
   - Generate v5 to
     `G:\My Drive\alan_mcxico\SSA-evidence\2026-05-12-RPD-01\Audit_Report_96-98_Hampden_Rd_Russel_Lea_v5.docx`.
   - Side-by-side vs Cremorne + Fraters.
   - Every catalogued defect (§2) either fixed or explicitly
     documented with operator sign-off.

7. **Record the adoption decision.**
   - Add `docs/decisions/2026-05-12-adopt-audit-report-visual-polish.md`.
   - Document what was adopted, what was preserved from `main`, and
     why.

8. **One coordinated commit covering:**
   - Renderer
   - Template
   - Cleaner
   - Route reconcile
   - Contract tests + fixtures
   - Decision record
   - Regeneration / proof artefacts as appropriate

**Operator `/goal` prompt (paste verbatim to start execution):**

```text
/goal Bring the `feat/audit-report-visual-polish` audit-report renderer/template contract onto `main`, reconcile `pims/routes.py`, add a fingerprint contract test against the two in-repo reference DOCX files, and regenerate the report as v5.

Context:
- Repo: `C:\Users\AlanRichardson\gatekeeper`
- Canonical reference: this plan
- Canonical source branch: `feat/audit-report-visual-polish`
- Scope: one coordinated commit
- Keep current `main` data-layer wins intact
- Keep the trailing AuditCo contact page
- Use one global `Photo N` counter across the report
- Use block-scoped `#N. <Status>` numbering per criterion block
- Pass report issue date explicitly at the route boundary; never call `date.today()` inside the renderer
- Use `CONTRACTOR_CONFIG` keyed by `sites.client_name` for Prepared For
- For RPD, render exactly:
  - `Matthew McCarthy`
  - `Robertson's Remedial and Painting Pty Ltd`
  - `10/ 56 Buffalo Road, GLADESVILLE 2111`
- Ignore the Cremorne PDF glyph artefact

Plan:
1. Adopt the feature-branch renderer/template/cleaner/tests onto `main`.
2. Reconcile `pims/routes.py` to the adopted renderer shape and preserve current `main` behaviour.
3. Implement the resolved output decisions in the same commit.
4. Add fingerprint contract tests and fixtures pinned to:
   - `pims/7_Hampden_Rd_Cremorne.docx`
   - `pims/56-58_Fraters_Ave_Sans_Souci.docx`
5. Verify title-page text-frame replacement, footer rendering, and deterministic date handling.
6. Regenerate the report as v5 and validate it against the references.
7. Add a decision record documenting the adoption.

Rules:
1. Output a numbered plan first.
2. Execute autonomously unless genuinely blocked.
3. After each step, self-verify with tests, output inspection, or artifact review.
4. If something fails, debug and fix it before moving on.
5. No placeholders, no TODOs, no stubs.
6. Keep a concise progress log: done, in flight, decisions, blockers.
7. Before stopping, re-check every success criterion.

Success criteria:
1. `pims/audit_report_docx.py`, `pims/audit_report_template.docx`, and related helpers on `main` match the reference contract and resolved decisions.
2. `pims/routes.py` matches the adopted renderer shape without regressing current data-layer behaviour.
3. Fingerprint contract tests and fixtures exist and pass.
4. Final output runs without errors.
5. Final proof includes pytest output, artifact path, and any useful screenshots/diffs.

Final deliverable:
- Confirmation each criterion is satisfied
- Files changed
- How to run / test / regenerate
- Proof
- Decisions made
- Known limitations / follow-ups
```

## 5. Resolved decisions (Codex review, 2026-05-12)

The five questions originally posed in this section have been
resolved. These are the contracts §4 will ship against.

1. **Photo-caption numbering scope** (S9). **One counter across the
   whole report.** Never reset per-block or per-site. For multi-site
   reports the counter remains continuous from the first site to
   the last. In-repo references confirm: Cremorne carries
   `Photo 1` – `Photo 8`; Fraters carries `Photo 1` – `Photo 9`.
   (Earlier draft of this doc said Cremorne went to `Photo 6` —
   that was a partial-page observation; the full document goes to 8.)

2. **`Contact Us` template tail page** (X1). **Keep it in v5.** It
   is part of the reference artefacts and stripping would knowingly
   diverge from the current contract. Any future removal is a
   separate deliberate contract change with its own commit + ADR.

3. **Title page "Prepared For" block source of truth.** **Not
   template-hardcoded and no new DB table.** Renderer-side client
   config keyed by `sites.client_name`. For this commit, add one
   entry for the RPD client_name (the canonical
   `"Robertson's Remedial and Painting Pty Ltd"`) with payload:

   ```
   Matthew McCarthy
   Robertson's Remedial and Painting Pty Ltd
   10/ 56 Buffalo Road, GLADESVILLE 2111
   ```

   The stray `Matt M` prefix (currently bleeding from a template
   text-frame fragment) must be removed in the same pass. Config
   lives next to the renderer as a Python dict for now (e.g.
   `CONTRACTOR_CONFIG = { … }` in `pims/audit_report_docx.py` —
   matches the convention Phase H2 already introduced for that
   constant on `feat/audit-report-visual-polish`).

4. **Title-page date label.** **Report issue / sign-off date, not
   the inspection date.** Use the *same* date on the title page
   and in the page-2+ footer. Pass it explicitly at the route
   boundary (new `report_issue_date` field on
   `AuditReportRequest`, default `date.today()` resolved by the
   route, not by the renderer). The renderer takes a deterministic
   date and renders it identically in both surfaces. This keeps the
   fingerprint contract test stable — no implicit `date.today()`
   buried in the renderer.

5. **Glyph rendering glitch in Cremorne PDF only.** **Ignore.**
   One-off PDF / font-embedding noise, not a DOCX content defect.
   Standardise on one DOCX-to-PDF toolchain for future exports
   (decide outside this commit) and do not spend time reverse-
   debugging the Cremorne PDF.

## 6. Process guardrails — never lose this work again

Below is a concrete, low-effort set of checks I will apply (and
recommend you require) to prevent this exact pattern of loss.

### G1. Long-lived branches are flagged

Add a CI job (GitHub Actions, or a manual weekly check) that lists
any branch with:
- No PR open,
- Last commit older than 14 days,
- Diverged from `main`.

Either the branch is merged, or rebased, or explicitly archived
with a tag (e.g. `archive/<branch-name>`). No branch should hold
production-critical work in suspension.

For this repo today: `feat/audit-report-visual-polish` would have
been flagged ~3 weeks ago. Run the check now and again every
Friday.

### G2. Reference outputs are pinned to a commit

Every "evidence" docx/pdf that defines the contract for a renderer
must have a sidecar metadata file pointing at the producing
commit:

```
pims/7_Hampden_Rd_Cremorne.docx
pims/7_Hampden_Rd_Cremorne.docx.meta.json
```

The `.meta.json` records: the producing commit SHA, the renderer
version, the date, and the operator who blessed it. Anyone reading
the evidence can immediately find the producing code.

### G3. Renderer-contract tests gate every renderer commit

The contract test in §4.3 must run in CI on every PR that touches
`pims/audit_report_docx.py`, `pims/audit_report_template.docx`,
or any of the upstream data-shape modules. PR cannot merge with a
red fingerprint.

If a contract change is intentional, the test snapshot is updated
in the same PR with explicit operator sign-off in the PR
description.

### G4. No "unused" deletions of binary assets without evidence

The commit message of `791e167` claimed
`audit_report_template.docx` was "unused" and deleted it. CI
should reject any commit that:
- Deletes a binary asset under `pims/` or `frontend/`, AND
- The commit message does not contain a grep-evidence block
  showing zero callers.

Manual policy: a reviewer requires either (a) a grep result
showing zero references, or (b) an existence test for the asset
in the test suite that passes after the deletion.

### G5. Chore commits with >50 lines of diff to a load-bearing
       file get a structured message

For any commit whose subject starts with `chore:` and that
modifies a file flagged as "load-bearing" (renderer, route,
template), the commit body must enumerate the changes — not a
catch-all "adjustments". A simple CI lint check on the commit
message is feasible.

For this repo: add `pims/audit_report_docx.py`,
`pims/audit_report_template.docx`, `pims/routes.py`, and
`frontend/pims_dashboard_rpd.html` to a `LOAD_BEARING.txt` list.

### G6. Renderer dependencies named in code

`pims/audit_report_docx.py` should declare at the top of the file:

```python
# This renderer's output is contracted against:
#   tests/fixtures/audit_report_contracts/cremorne.json
#   tests/fixtures/audit_report_contracts/fraters.json
# Reference docx files (do not delete):
#   pims/7_Hampden_Rd_Cremorne.docx
#   pims/56-58_Fraters_Ave_Sans_Souci.docx
# Any change to this file requires:
#   1. Passing tests/test_audit_report_contract.py
#   2. Operator sign-off on a regenerated docx (kept as evidence)
```

Cheap, durable, lives next to the code.

### G7. A `make audit-report` smoke target

Add a Makefile or `scripts/smoke_audit_report.sh` that:
- Boots the FastAPI app locally,
- Calls `/pims/audit-report/rpd` with a known site_id,
- Saves the result as `tmp/audit_smoke.docx`,
- Compares to the contract fingerprint.

Run on every PR that touches the renderer or routes. Five-minute
job. Cheap insurance.

## 7. What I'd like to do next

All §5 decisions are resolved (Codex review, 2026-05-12). Awaiting
operator "go" to execute §4 in one coordinated commit. Estimated 90
minutes of focused work, followed by 5 minutes of operator visual
sign-off on v5.

Process guardrails (§6) can land separately as their own commits
after v5 is signed off — they don't gate the renderer fix.

## 8. What I will NOT do

- Keep iterating on the current main renderer / template binary.
  Every patch reveals another mismatch I missed because the docx
  format hides content in places my dumps don't inspect (DrawingML
  text frames, section first-page headers, etc.).
- Hand-roll a new renderer from scratch when the feature branch
  already has the right code.
- Promise byte-perfect output without first running the contract
  test against the references.

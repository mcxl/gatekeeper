# Audit Report Cover Gap — Diagnosis + Solution

**Date:** 2026-05-12
**Author:** Claude Code (Opus 4.7, 1M)
**Status:** Diagnosis + solution. Fix lands in the same session as
this doc. Supersedes the cover-gap section of
`C:\Users\AlanRichardson\gatekeeper\docs\plans\AUDIT_REPORT_RENDERER_DIAGNOSIS.md`.

## 0. The gap

After Option B's nine commits, `Audit_Report_96-98_Hampden_Rd_Russel_Lea_v3.docx`
matches `pims/7_Hampden_Rd_Cremorne.docx` on body structure but still
diverges on the cover. Operator response: "Rubbish".

Byte-level cover comparison below.

## 1. Cover paragraph diff (REF → NEW)

| Paragraph idx (REF) | REF text | NEW v3 status |
|---|---|---|
| p4 | `Robertson's Remedial and Painting – Site Safety Audit Report` | ✅ present |
| p5 | `7 Hampden Rd Cremorne` (site address) | ✅ present |
| p7 | `Executive Summary` (heading) | ✅ present |
| p8 | exec summary opener `"A site safety audit was conducted at … on … . …"` | ✅ present |
| **p9** | **`Project risk assessment doesn't include any hazard with Work at Heights…`** (first finding-summary bullet on cover) | ❌ MISSING |
| **p10** | **`Ladder left unsecured on scaffold…`** (second finding-summary bullet on cover) | ❌ MISSING |
| p12 | `Score` | ✅ present (as p9 in NEW) |
| p13 | `45 / 47 (96%)` | ✅ present |
| **p14** | **`Flagged Items`** (explicit cover heading) | ❌ MISSING |
| **p15** | **`2`** (count under the heading) | ❌ MISSING |
| p16 | `Findings` | ✅ present (but at p188 in NEW, far down the body) |
| p17 | `NCR #1. Working at Height – Scaffold – …` | ✅ present at p189 |

## 2. Cover table diff (REF → NEW)

| Table idx | REF | NEW v3 | Status |
|---|---|---|---|
| t0 (1x6 KPI) | `Score \| 45 / 47 (96%) \| Flagged observations \| 2 \| Open actions \| 2` | `Score \| 19 / 34 (56%) \| Flagged items \| 15 \| Actions \| 13` | ❌ template labels wrong (D5 partial) |
| t1–t6 | metadata rows | metadata rows | ✅ match |
| **t7** (1x2) | `Site Inspection \| 45 / 47 (96%)` | `Flagged items \| 15 flagged` | ❌ wrong template label + wrong value mapping |
| t8+ | hierarchical checklist | flatter checklist | ⚠ different layout (acceptable for this pass; deeper refactor only if needed) |

## 3. Root cause

### 3.1 Missing cover bullets (gap items p9, p10, p14, p15)

Cause: **commit `830a071`** (this session) extended the template
cleaner with `EXACT_PARAGRAPH_MATCHES` and stripped these literal
paragraph strings from the template binary:

- `[Insert line items from Open Actions Register linked to the site address]`
- `[Insert Summary of Findings from the Flagged Items in dot points]`

I removed them assuming they were duplicates of the body's
Findings / Open Actions content. They were not. The renderer's
`_populate_cover` function at
`C:\Users\AlanRichardson\gatekeeper\pims\audit_report_docx.py:612–646`
has full logic to populate these placeholders with cover-level
finding bullets. The render-time warnings on every test run
(`Cover placeholder '[Insert line items from Open Actions Register' not found`)
are the symptom — the renderer is looking for them and not finding
them because the cleaner deleted them.

`Flagged Items` heading + count paragraphs were either part of
those placeholder regions in the original template, or live as
separate paragraphs the cleaner also caught via the "exact match"
strip list (it strips `"Flagged Items"` heuristically — let me
verify in the cleaner source). Need to keep "Flagged Items" as a
template heading.

### 3.2 KPI table labels (t0)

Cause: the deployed `pims/audit_report_template.docx` carries the
labels `Flagged items` and `Actions`. The reference docx (and per
the operator's intent) uses `Flagged observations` and `Open
actions`. My commit `1b5cb0f` added tolerant lookup in the
renderer so the VALUE cells get populated regardless of which
label the template uses, but the LABELS themselves are
template-resident text and aren't rewritten by the renderer.

### 3.3 Table 7 layout

Cause: the deployed template has table 7 as
`Flagged items | <flagged-count> flagged`. The reference has it as
`Site Inspection | <score>`. Template-binary mismatch — the
deployed template predates a label change made on the unmerged
`feat/audit-report-visual-polish` branch.

### 3.4 Site Safety Inspection table structure

REF uses hierarchical: category banner → criteria-level
score-table → 2x6 observation matrix. NEW uses flatter: category
heading → 2x2 criteria table → 2x6 observation matrix. **Deferred**
— not in scope for this pass; the visible body still reads
correctly, and rebuilding the hierarchical checklist render is a
larger renderer refactor that belongs in a separate session.

## 4. Solution (single coordinated commit)

Four atomic changes, all on top of HEAD:

### 4.1 Restore two cover placeholders to the template binary

Write a small fixup script that inserts the two placeholder
paragraphs back into `pims/audit_report_template.docx` at their
original cover positions (after `[Insert Site Address]` and
before/after the `Score` block). The renderer's existing
`_populate_cover` will then fill them with the cover bullet lines.

Specifically restore:

- `[Insert line items from Open Actions Register linked to the site address]`
  — placed after the Open Actions section heading on the cover.
- `[Insert Summary of Findings from the Flagged Items in dot points]`
  — placed after the Findings section heading on the cover.

The original template additionally had a `[Insert Flagged]`
placeholder under a `Flagged Items` heading. Restore both.

### 4.2 Update KPI table labels in the template binary

Rewrite cells in `pims/audit_report_template.docx`:

- t0 cell `(0, 2)`: `Flagged items` → `Flagged observations`
- t0 cell `(0, 4)`: `Actions` → `Open actions`
- t7 cell `(0, 0)`: `Flagged items` → `Site Inspection`

### 4.3 Update renderer mapping for the renamed t7 label

In `_populate_cover` `label_values_label_pair`, add the mapping
`"Site Inspection": totals["score_text"]` so the renamed t7 cell
gets the full score string (`"45 / 47 (96%)"`) rather than a
flagged-count fragment.

### 4.4 Update the cleaner's `EXACT_PARAGRAPH_MATCHES`

Remove these two entries (added in `830a071`) so future re-runs
of the cleaner don't re-delete the placeholders we just restored:

- `[Insert line items from Open Actions Register linked to the site address]`
- `[Insert Summary of Findings from the Flagged Items in dot points]`

Keep the other entries (`Part A`, `Part B`, `Part C`, `Part D`,
`Open Actions Register`, `Findings`, `RPD - Site Safety Inspections`,
`Example format below`) since those are the renderer-emitted
headings we don't want duplicated.

## 5. Verification (post-commit)

Regenerate
`G:\My Drive\alan_mcxico\SSA-evidence\2026-05-12-RPD-01\Audit_Report_96-98_Hampden_Rd_Russel_Lea_v4.docx`
and assert the cover paragraphs now match REF positionally:

- p9 contains a bullet from the open-actions register OR the
  findings summary.
- p10 contains another bullet.
- `Flagged Items` heading + count appear before `Findings`.
- t0 cells read `Score | … | Flagged observations | … | Open actions | …`.
- t7 reads `Site Inspection | <score>`.

## 6. Out of scope (for this pass)

- Hierarchical Site Safety Inspection table structure (§3.4). Defer
  until after the cover lands clean.
- Multi-site cover layout. Single-site is the active path.

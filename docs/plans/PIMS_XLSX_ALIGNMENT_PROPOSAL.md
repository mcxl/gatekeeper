# PIMS audit-checklist xlsx ↔ canonical-template alignment proposal

**Date:** 2026-05-13
**Author:** Claude Code (Opus 4.7, 1M) — Alan's session
**Status:** Proposal. Operator decision required.
**Trigger:** Stage B live render against 96-98 Hampden Rd surfaced a
50% obs-match rate against the canonical template. Code-side
improvements (ccvs-prefix family map + threshold tuning) close part of
the gap; the rest is upstream data-shape misalignment that only
operator-curated work can fix.

---

## 1. The gap

Three artefacts shape the audit report:

| Artefact | Owner | Shape |
|---|---|---|
| `pims/audit_checklist.xlsx` | Operator-curated | Two sheets (>$250K / <$250K). Columns: **Category, Criteria, Instruction**. 86 rows in HIGH sheet, 86 in LOW. |
| `pims/RPD_SSA_template-inserted.docx` | Operator-curated (separate authoring path) | 86 criteria across 9 sections. Each criterion has a header table (status badge cell) + obs table (narrative + photo cells). |
| `pims_observations` table | Operator-captured in PIMS app | Columns include `ccvs_code` (e.g. `WAH-H6`), `ccvs_category` (e.g. `"Working at Height"`), `observation_text_enriched`. |

**The three don't reference each other by stable key.** The renderer
bridges them by:

1. observation → LineItem via `_match_obs_to_line_item` (Stage B+).
2. xlsx → LineItem via best-effort section-family + criterion-text
   match (loud-logged but not blocking).

Stage B live render on 34 real observations from 96-98 Hampden Rd
showed **17 unmatched (50%)**. The post-Stage-B+ ccvs-prefix matcher
should lift this materially for `WAH/SIL/CHM/ENE/PPE`-prefixed obs, but
the underlying structural mismatches remain.

## 2. Inventory of structural mismatches

Comparison of section-families across artefacts (count = criteria per
section/category):

| Concept | Template | xlsx HIGH | xlsx LOW | obs.ccvs_category examples |
|---|---|---|---|---|
| Planning & risk mgmt | 17 (HIGH) + 13 (LOW) | 30 (one combined section) | 30 (one combined section) | `Systems`, `Systems – SWMS, …` |
| Worker competency & PPE | 5 | 5 | 5 | `Systems` (sometimes) |
| General work at height | 14 | 11 | 11 | `Working at Height` |
| Hazardous substances & silica | 11 | 11 | 11 | `Silica Dust`, `Hazardous Chemicals` |
| Rope access | 13 | 13 | 13 | (none seen in this audit) |
| Plant & equipment safety | 6 | 6 | 6 | `Systems` (sometimes) |
| Demolition & temporary works | 4 | 4 | 4 | (none seen) |
| Energy & services | 3 | 3 | 3 | `Energy` |
| (xlsx-only) Scaffolding | — | 14 | 14 | (no obs use this name) |

### 2a. Planning tier split (template ≠ xlsx)

- Template carries **two** Planning sections (>$250K = 17 items;
  <$250K = 13 items), selected per site by `project_value`.
- xlsx carries **one** combined Planning section per sheet (30 items
  in each tier sheet).
- The 30-row xlsx Planning ≠ 17 + 13 template Planning — the operator
  curated them independently with different rollups.

### 2b. Orphan xlsx Scaffolding section (xlsx-only, 14 items)

- The xlsx carries a `Scaffolding` category in both sheets.
- The canonical template has **no Scaffolding section**. Conceptually,
  scaffolding items live across "General work at height" and "Plant
  and equipment safety" in the template.
- 14 observations tagged with Scaffolding-related criteria can never
  bridge from xlsx to template, regardless of matcher improvements.

### 2c. xlsx criterion wording diverges from template item_text

xlsx Criteria are interrogative ("01. Does the site sign include
required warnings, …?") while template item_text is declarative ("For
projects > $250,000 in contract value site sign includes the required
warnings, …"). Same intent, different wording. Stage B+ matches via
section-family + difflib at 0.25, which catches most — but unaligned
rows (23 of 86 currently per the live render warnings) miss.

### 2d. Observations' `ccvs_category` strings don't match either
template section names or xlsx category names

Examples from real data:

| obs.ccvs_category | Template section | xlsx category |
|---|---|---|
| `Working at Height` | `General work at height` | `04. General Work at Height` |
| `Systems` (and variants) | (no equivalent) | (none — across multiple) |
| `Silica Dust` | `Hazardous substances and silica control` | `08. Hazardous Substances and Silica Control` |
| `Hazardous Chemicals` | same as above | same as above |
| `Energy` | `Energy and services` | `10. Energy and Services` |

The `_section_family()` normaliser handles "01. " prefixes and tier
suffixes but cannot reconcile "Working at Height" ↔ "General work at
height" or "Silica Dust" ↔ "Hazardous substances and silica control".

### 2e. The `Systems` ccvs category has no template home

In production observations: ~10 of 34 carry `ccvs_category` starting
with `Systems` (sometimes `Systems – SWMS, toolbox talks, permits,
inspections`, sometimes just `Systems`). The narratives describe
items conceptually belonging to Planning, Worker competency,
Hazardous substances, or Plant equipment — but the operator-supplied
category is monolithically "Systems". The template has no Systems
section. Stage B+ falls back to global difflib for these; most still
miss because narrative ↔ item_text token overlap is too low.

## 3. Three remediation paths

### Path A — xlsx-driven canonicalisation

Bring the xlsx into structural alignment with the template:

1. Split each xlsx sheet's `01. Planning and Risk Management (…)`
   row block into the same 17/13 split the template uses, with
   matching criterion wording.
2. Remove the xlsx `05. Scaffolding` section. Redistribute its 14
   rows into `04. General Work at Height` and `07. Plant and
   Equipment Safety` in line with the template.
3. Add two new columns to each sheet:
   - `ccvs_code` — canonical short code per criterion (e.g.
     `WAH-001`, `SIL-007`).
   - `template_section` — the canonical section name from the
     template (matches `template_index.SECTIONS_ORDERED`).
4. Renumber criteria within each section to match template order.

Result: the renderer can do strict ccvs-code-key joins instead of
fuzzy text matching. Match quality goes from ~75% to near 100% for
xlsx-bridged paths.

**Effort:** ~2–3 hours of operator-curated xlsx editing. One-time.

### Path B — template-driven canonicalisation

Re-author the template to mirror the xlsx structure:

1. Merge the template's two Planning sections back into one
   "Planning and risk management" section of 30 items.
2. Add a Scaffolding section of 14 items between GWH and Hazardous
   substances.
3. Adjust GWH from 14 → 11 items, Hazardous from 11 → match.
4. Re-run `template_index.py` indexing; verify section count = 9.

Result: 1:1 alignment with the xlsx. Renderer can use positional
matching within sections.

**Effort:** ~3–4 hours of operator-curated docx editing + a
template re-export step. Risks: breaks reference docs (Cremorne /
Fraters) until they're regenerated from the new template.

### Path C — observation-side canonicalisation

Constrain operator observation entry in the PIMS app:

1. Replace the free-form `ccvs_category` text input with a
   dropdown sourced from `template_index.SECTIONS_ORDERED` (9
   options).
2. Replace `ccvs_code` free-form input with a per-section dropdown
   sourced from xlsx criterion ccvs_codes (added per Path A).
3. Validate at submission: `ccvs_category` ∈ template sections;
   `ccvs_code` ∈ xlsx codes for that category.

Result: at submission time the obs is already keyed to a template
section + xlsx criterion. The renderer becomes a strict lookup.

**Effort:** ~half-day of PIMS frontend + backend work. Requires
Paths A or B done first (since the dropdown source must exist).

## 4. Recommendation

**Combination: Path A (xlsx canonicalisation) + Path C (constrained
observation entry).**

Reasoning:
- Path A is the smallest, most contained operator-curated edit.
  Single artefact, no docx reflow risk, no reference-file
  regeneration.
- Path A + ccvs_code column unblocks the renderer to do strict
  lookups instead of fuzzy text matching. Stage B+ matcher becomes
  legacy/fallback for pre-Path-A obs.
- Path C closes the loop so new observations are already canonical
  at write time. Without Path C, the gap reappears every time an
  operator types in `ccvs_category` freehand.
- Path B (template canonicalisation) is the highest-risk move.
  Defer unless Path A reveals that the template's structure is
  genuinely wrong for the domain (no evidence of that today).

## 5. Suggested phasing

1. **Path A.1 — xlsx ccvs_code column.** Operator adds `ccvs_code`
   to each row of the >$250K and <$250K sheets. No row count
   changes. Stage B+ matcher can be augmented to do strict
   `ccvs_code` join when both sides carry it. **~1 hour.**
   
2. **Path A.2 — Planning split + Scaffolding redistribution.**
   Restructure xlsx Planning into HIGH (17) + LOW (13) to mirror
   template; redistribute Scaffolding rows. **~1.5 hours.**

3. **Path C — PIMS app dropdown enforcement.** Frontend dropdown +
   backend validation for `ccvs_category` and `ccvs_code`.
   **~half-day.**

4. **Reference regeneration.** Re-render Cremorne + Fraters
   references against the new artefact set to verify the alignment
   produces reference-quality output. **~30 min.**

Each phase is independent and operator-callable. Stage B+ renders
continue to work throughout (warnings get quieter as phases land).

## 6. Out of scope of this proposal

- Path B (template canonicalisation) — only consider if Path A
  reveals a structural defect in the template.
- Historical observation re-tagging — existing obs stay as-is; the
  Stage B+ fuzzy matcher continues to handle them. Path C only
  affects future entries.
- Adding new template criteria — separate decision per WHS
  compliance scope.

## 7. Open questions for operator

1. Does the operator have authority to edit `audit_checklist.xlsx`,
   or is it sourced from an external regulatory template?
2. Are the reference docs (`pims/7_Hampden_Rd_Cremorne.docx`,
   `pims/56-58_Fraters_Ave_Sans_Souci.docx`) considered ground
   truth, or were they themselves produced from a now-different
   template version?
3. Is there an existing canonical mapping of `ccvs_code` values to
   criteria, or are the codes ad-hoc per audit?

## 8. Code-side complement

Once Path A.1 lands (xlsx carries `ccvs_code`), the Stage B+ matcher
should be extended:

```python
def _match_obs_to_line_item(obs, items, ...):
    # New Tier 0: strict ccvs_code lookup via xlsx → LineItem mapping
    # (only when xlsx carries the column).
    if obs.get("ccvs_code") and xlsx_carries_ccvs:
        target_row = xlsx_index.get(obs["ccvs_code"])
        if target_row:
            li = criteria_to_line_item.get(_normalize_criteria(target_row.criteria))
            if li:
                return li
    # Existing Tier 1/2/3 fallback below…
```

This is a ~20-LOC addition once the data shape supports it. Today it
would be dead code.

# Codex Review — Audit Report Renderer Stage B Plan (v2)

**Date:** 2026-05-13
**Branch:** `main` @ `7b785c4`
**Author:** Claude Code (Opus 4.7, 1M) — Alan's session
**Status:** v2 — incorporates Codex v1 findings (two P1s, two P2s, one P3).
**Reviewer ask:** validate the revised plan; flag missed risks before
implementation.

This document is self-contained. You don't need session history.

---

## 0. TL;DR

The audit-report renderer was pointing at the wrong template binary
for the entire session. Stage A (commit `7b785c4`, deployed) repointed
it at the canonical template `pims/RPD_SSA_template-inserted.docx` and
stripped the body-emission code from `_append_site`. Cover now
populates cleanly; body is empty (template default).

**Stage B (this plan)** rewires `_append_site` to **fill the canonical
template's pre-existing structure** instead of emitting new sections —
mirroring the Site Visit Report path's index-and-fill pattern.

**Changes from v1 (Codex findings folded in):**
- **[P1]** Keying switched from `item_idx` (section-local, collides) to
  `header_table_idx` (globally unique). §4 + §5 updated.
- **[P1]** Multi-site rendering strategy added (§4a). v1 silently kept
  the existing single-doc-loop, which would overwrite site 1's
  checklist when filling for site 2. New strategy: render one Document
  per site, zip at the route (matches reference shape — each reference
  is single-site).
- **[P2]** Planning-tier applicability handled explicitly (§4b). The
  canonical template carries both >$250K and <$250K planning sections;
  v1 left both in `COMPLIANT_DEFAULT_SECTIONS` so the inactive tier
  would render as "compliant" — wrong. Stage B marks the inactive tier
  as N/A.
- **[P2]** Bridge problem resolved via **Option C** (§4c): reuse the
  existing `match_observation(obs, list[ChecklistRow])` at
  `pims/audit_report_docx.py:505`. Drops the synthetic-ID adapter
  (Option A) and the second-matcher proposal (Option B).
- **[P3]** Render recipe inlined in B5 (§5).

---

## 1. Background — what's happened so far

### 1.1 Project context

`gatekeeper/pims` is the PIMS audit-report subsystem. Operators inspect
construction sites, capture observations in Supabase
(`pims_observations`), and a FastAPI route `/pims/audit-report/rpd`
renders a Word document grouping observations against a checklist.

The "checklist" exists in two places:
- `pims/audit_checklist.xlsx` — operator-curated, has two sheets
  (`>$250K_inspection_checklist`, `<$250K_inspection_checklist`) with
  columns
  `Category, Criteria, Instruction, ccvs_code, ccvs_category,
  observation_text_enriched`.
- `pims/RPD_SSA_template-inserted.docx` — the Word template carrying
  category banners, per-criterion 1×2 header tables (criterion text |
  status badge), and per-criterion 2×N observation tables underneath
  (narrative row + photo row).

Reference outputs (operator-approved):
- `pims/7_Hampden_Rd_Cremorne.docx`
- `pims/56-58_Fraters_Ave_Sans_Souci.docx`

Both references are single-site.

### 1.2 The wrong-template incident

v3/v4/v5 of a regeneration sequence for "96-98 Hampden Rd Russel Lea"
failed to match the references on cover layout AND body structure. We
iterated five times before the operator asked "why are you not going
back to `RPD_SSA_template-inserted.docx`?" — at which point we
discovered the audit-report renderer had been wired to a different,
degraded template (`pims/audit_report_template.docx`) the entire time.

Structural comparison confirmed the references came from the canonical
template, not the degraded one:

| Marker | Cremorne ref | Canonical | Degraded |
|---|---|---|---|
| `Executive Summary` heading | yes | yes | yes |
| `Site Safety Inspection` heading | yes | yes | no |
| Hierarchical category banners | yes | yes | no |
| Per-criterion checklist tables | 272 | 326 | 103 |
| `Part A/B/C/D` headings | **no** | **no** | no (renderer emitted them) |
| Auditor Sign-off block | **no** | **no** | no (renderer emitted it) |

The renderer's `_append_site` was emitting Part A/B/C/D + a synthesized
Site Safety Inspection body that **duplicated** structure the canonical
template already carried. The references showed no Part A/B/C/D because
they came from a renderer wired to the canonical template — which we
now believe was an earlier prototype not present on `main`.

Root-cause diagnosis lives at
`docs/plans/AUDIT_REPORT_CORRECT_TEMPLATE_DIAGNOSIS_AND_PLAN.md` (v3).

### 1.3 Why this wasn't caught

1. Two parallel template paths drifted apart silently:
   - audit-report flow → `audit_report_template.docx` (degraded)
   - site-visit-report flow → `RPD_SSA_template-inserted.docx`
     (canonical), via `pims/services/template_index.py`
2. No `docs/TEMPLATE_REGISTRY.md` enumerating which template each
   renderer consumes.
3. No `.meta.json` sidecars on the reference docx files declaring their
   producing template / commit.
4. Prior session diagnoses (CONTRACTOR_CONFIG fix, cover-placeholder
   walk, score-precision fix, "Site Safet"/"Matt M" typo strip, photo
   filter revert) closed real defects but chased the renderer codebase
   without broadening the search to "what other templates exist?".
5. The smoking-gun line —
   `pims/services/template_index.py:1` *"One-time index of
   RPD_SSA_template-inserted.docx"* — sat unused by the audit-report
   path for the entire session.

### 1.4 Stage A — what just shipped (commit `7b785c4`)

`pims/audit_report_docx.py`:
- `TEMPLATE_PATH` switched to `RPD_SSA_template-inserted.docx`.
- `_append_site` stripped of Part A/B/C/D emission. Now only emits a
  page break + address heading for non-first sites in multi-site
  reports. **Body is empty** — canonical template's default Compliant
  shading on every criterion shows through.
- `_populate_cover` unchanged (still walks DrawingML text frames to
  replace `[Insert …]` placeholders).

Tests: 39 passed, 18 skipped (Phase D/E/F/G assertions of Part A/B/C/D
structure that no longer exists; all marked with
`reason="Stage A 2026-05-13: ... Stage B will rewrite"`). Ruff clean.
Codex independently reran the same test subset and confirmed 39
passed / 18 skipped.

Local v6 verification render (stub data):
- Output opens cleanly, 6.96 MB.
- `96-98 Hampden` address appears 4× (cover title + cover table +
  page-2 header).
- Zero `[Insert …]` placeholder leftovers.
- Zero `Matt M` fragments.
- `Site Safet` typo: **2× present** — canonical template carries the
  same title-page typo the degraded one had; the old cleaner was wired
  to the wrong template. **Deferred to Stage C** (text-frame walker
  pass over canonical template).
- Table count: 326 (v6) vs 272 (Cremorne). +54 expected because Stage A
  leaves every criterion at template-default Compliant; Stage B will
  fill cells, not delete them, so v7 will still be 326. Cremorne's 272
  was produced from a template variant or via cell-merge that's not
  worth replicating — content correctness wins over table-count parity.

---

## 2. The Stage B objective

Make `_append_site` populate the canonical template's pre-existing
structure based on observations, instead of emitting new sections.

Behaviour requirements:

1. Build the `TemplateIndex` once per site via
   `pims.services.template_index.get_index()` (already implemented;
   indexes line items + cover cells + status palette).
2. For each `LineItem` in the index:
   - **If observation(s) match this line item:**
     - Shade the status cell per the matched observations' worst
       conformance status (NCR > Conditional > Compliant > Info).
     - Populate the narrative cell with finding text.
     - Embed each matched observation's photo in the corresponding
       photo slot in row 1 of the 2×N observation table.
   - **If no observations match:**
     - LineItem's section in `COMPLIANT_DEFAULT_SECTIONS` → leave
       default Compliant shading.
     - LineItem's section in `NA_SECTIONS` → paint N/A shading; blank
       narrative.
     - LineItem in the **inactive planning tier** (per §4b) → paint
       N/A shading regardless of section membership.
3. Increment a single global `photo_counter` across the whole document.
4. Do **not** emit Part A/B/C/D. Do **not** call `_part_d_signoff`.
5. Cover placeholders populate via existing `_populate_cover` — already
   working post-Stage A.
6. Score / Flagged-items KPI cells on the cover populate via
   `index.cover_cells`.

---

## 3. The contract surfaces involved

```
pims/services/template_index.py
  get_index() -> TemplateIndex
    .items: list[LineItem]
      LineItem.section / section_idx (1-based, global) / item_idx (1-based, section-local)
      LineItem.header_table_idx  ← 1×2 table (criterion text | status badge) — GLOBALLY UNIQUE
      LineItem.obs_table_idx     ← 2×N table (narrative row + photo row) — GLOBALLY UNIQUE
      LineItem.item_text         ← criterion text from header cell
      LineItem.default_obs_text  ← obs_table[0][0] text
      LineItem.photo_cells: list[(row, col)] in obs_table
    .palette: dict[status -> (bg_hex, font_hex)]   # derived from live template
    .na_fill: str                                  # hex
    .cover_cells: dict[label -> CoverCell(table_idx, label_row, label_col, value_row, value_col)]

  Module-level constants:
    SECTIONS_ORDERED          # 9 sections, 2 of which are planning tiers
    PLANNING_HIGH             # ">$250K" planning section name
    PLANNING_LOW              # "<$250K" planning section name
    PLANNING_TIERS            # {PLANNING_HIGH, PLANNING_LOW}
    COMPLIANT_DEFAULT_SECTIONS # 5 sections (incl. both planning tiers — §4b adjusts at runtime)
    NA_SECTIONS               # 4 sections

pims/audit_report_docx.py (existing, reused in Stage B):
  ChecklistRow(category, criteria, instruction, ccvs_category, ccvs_code, observation_text_enriched)
  load_checklist(project_value, xlsx_path) -> list[ChecklistRow]
    # Selects sheet by project_value vs VALUE_THRESHOLD (=250000)
  match_observation(obs: dict, checklist: list[ChecklistRow], ratio_threshold=0.75)
    -> (ChecklistRow | None, float)
    # Primary: ccvs_code equality. Fallback: difflib 0.75 on
    # "category+criteria" vs "ccvs_category+observation_text_enriched".

  build_audit_report_docx(sites: list[SiteData], checklist_xlsx_path: Path) -> BytesIO
    SiteData: address, project_value, client, prepared_by, inspection_datetime,
              summary_text, observations: list[dict], open_actions: list[dict],
              open_action_photo_bytes_by_obs_id: dict[obs_id -> bytes],
              report_issue_date.
```

---

## 4. Resolved design decisions (Codex v1 findings folded in)

### 4a. Multi-site rendering — [P1 resolution]

Current `build_audit_report_docx` opens **one** `Document` and loops
over sites mutating it in place
(`pims/audit_report_docx.py:1359-1366`). Under the canonical template
that fills pre-existing tables (mutates `doc.tables[header_table_idx]`
in place), site 2 would overwrite site 1's checklist cells.

**Two viable strategies:**

**Strategy 1 — Per-site Document + zip at the route layer.** Mirrors
how `pims/services/audit_report_from_xlsx.build(...)` already returns
`.zip` for multi-site, single `.docx` for single-site. Aligns with the
references (both are single-site docs). Body cloning at the oxml level
is non-trivial in python-docx; this strategy avoids the cloning
entirely.

**Strategy 2 — Clone the body block per additional site within one
Document.** Requires deep-copying every body XML element between
`Site Safety Inspection` (and re-indexing the per-site tables). python-
docx has no native API for this; would need direct oxml manipulation
and would also require re-running `template_index.get_index()` against
each cloned region (or rewriting the index API to support offsets).

**Recommendation: Strategy 1.** Concretely:

- Change `build_audit_report_docx(sites, ...)` to assert `len(sites) ==
  1` and return a single-site `BytesIO`. Multi-site callers must zip
  externally. (Today's only multi-site caller is
  `audit_report_from_xlsx.build` and it already wraps in zip; the route
  `/pims/audit-report/rpd` may also need adjustment — see §6 Open
  Q-MS1.)
- Net effect: each site renders against a fresh template Document.
  Sites are independent; no cross-site contamination.

**Trade-off declared:** the route currently produces one combined docx
for multi-site `site_ids` (current production behaviour for ≥2 sites).
This contract change has to be flagged in the commit message and the
route's response handling has to switch to zip-on-multi.

### 4b. Planning-tier applicability — [P2 resolution]

Canonical template carries **both** planning sections
(`Planning and risk management (project value >$250K)` and
`(project value <$250K)`). For any given site, only one tier applies
(selected by `load_checklist()` via `VALUE_THRESHOLD = 250_000`).

`COMPLIANT_DEFAULT_SECTIONS` in `template_index.py:42` includes both
tiers. Without intervention, the inactive tier reads as "compliant" —
which is wrong (the auditor never inspected against it).

**Resolution:** compute per site at fill time:

```python
def _inactive_planning_section(project_value: float) -> str:
    if project_value >= 250_000:
        return PLANNING_LOW   # the <$250K section is inactive
    return PLANNING_HIGH      # the >$250K section is inactive
```

For every `LineItem` whose `.section == inactive_planning_section`:
paint N/A shading on the header table's status cell. (Narrative cell
left at template default; we are not adding text to the N/A obs
table.)

This overrides `COMPLIANT_DEFAULT_SECTIONS` membership for the
inactive tier per site. Active tier behaves normally (matched obs →
their status; unmatched → Compliant default per `COMPLIANT_DEFAULT_SECTIONS`).

### 4c. Bridge — Option C [P2 resolution]

`pims/audit_report_docx.py:505` already exposes
`match_observation(obs: dict, checklist: list[ChecklistRow])` for the
audit-report flow. Reusing it removes both v1 options:

1. Build `checklist: list[ChecklistRow]` via `load_checklist(site.project_value, xlsx_path)`.
2. Build `criteria_to_line_item: dict[str (normalized criteria), LineItem]`
   by walking the index's items and `.item_text`. (Equality on
   normalized criteria text; difflib fallback for near-misses.)
3. For each observation, call `match_observation(obs, checklist)`. If a
   `ChecklistRow` is returned, look it up in `criteria_to_line_item`
   via `row.criteria` to land on a `LineItem`.
4. Aggregate per `line_item.header_table_idx` (the unique key — see
   §4d):
   `matched_by_key: dict[int, list[obs]]`.

Single matching algorithm; no synthetic IDs; no second matcher.

**One residual gap:** `match_observation` returns `ChecklistRow`; we
need to map that back to `LineItem`. The bridge is `row.criteria ↔
line_item.item_text`. Both come from operator-curated sources (xlsx
column "Criteria" vs template header text). If they drift, the lookup
fails. Stage B will log a warning and treat that observation as
unmatched (will surface unmapped xlsx rows in the log; operator can
correct upstream).

### 4d. Stable LineItem key — [P1 resolution]

v1 keyed matches by `LineItem.item_idx`, which is **section-local and
resets each section** (`template_index.py:146`). Two LineItems in
different sections can share `item_idx` → collisions.

**Fix:** key by `LineItem.header_table_idx` (globally unique;
guaranteed by `template_index.py`'s docx table-position semantics).
This is what B1/B3 will use everywhere.

---

## 5. Proposed slice plan (revised)

### B1 — Native bridge + matcher wrapper
- New helpers in `pims/audit_report_docx.py`:
  - `_normalize_criteria(s: str) -> str` (collapse whitespace, lowercase).
  - `_build_criteria_to_line_item(items: list[LineItem]) -> dict[str, LineItem]`
    (case-insensitive equality with difflib 0.75 fallback when there
    are no exact hits).
  - `_match_observations_to_line_items(items: list[LineItem],
    checklist: list[ChecklistRow], observations: list[dict],
    inactive_planning_section: str) -> tuple[dict[int, list[dict]],
    list[dict]]`
    - Returns `(matched_by_header_table_idx, unmatched_observations)`.
    - Internals: for each obs → `match_observation(obs, checklist)` →
      bridge `ChecklistRow.criteria` to `LineItem` via the criteria
      map → aggregate by `line_item.header_table_idx`.
    - Observations matching a row whose criteria lives in the
      **inactive** planning section: still log and aggregate (they
      indicate operator confusion about which tier applies and should
      be surfaced in the unmatched log) — but `_fill_line_item` will
      still paint N/A on that section, so the obs won't render. (Open
      Q-B1: surface these as unmatched instead? — see §6.)
- Pure functions, no I/O. Unit-testable.
- ~70 lines.
- One file changed.

### B2 — Fill primitive (`_fill_line_item`)
- New function in `pims/audit_report_docx.py`.
- Signature:
  `_fill_line_item(doc, line_item: LineItem, palette: dict, na_fill: str, observations: list[dict], photo_counter_state: list[int], open_action_photo_bytes_by_obs_id: dict[str, bytes], force_na: bool = False) -> None`
- Behaviour:
  - If `force_na=True` (inactive planning tier or unmatched in
    `NA_SECTIONS`): set status cell text="N/A", shade `na_fill`,
    blank narrative. Return.
  - Compute worst-status from observations (NCR > Conditional >
    Compliant > Info; Info doesn't lift state).
  - Mutate `doc.tables[line_item.header_table_idx]` status cell
    (row 0, col 1): set text = status label, shade `palette[status][0]`,
    set font color `palette[status][1]`.
  - Mutate `doc.tables[line_item.obs_table_idx]` narrative cell
    (row 0, col 0) — **assumption pinned by B2-test**: concatenate
    each matched observation's narrative text with blank-line
    separators (per Codex answer Q2; no new rows).
  - For each observation with a photo, in order: embed into the next
    available `line_item.photo_cells` slot. First slot wins. If all
    slots are full and more photos remain, log a warning and drop
    extras (per Codex answer Q3).
  - Increment `photo_counter_state[0]` per embedded photo.
- ~80 lines.
- One file changed.

### B3 — `_append_site` rewrite + single-site contract
- Replace Stage A stub:
  1. Assert `len(sites) == 1` at the top of `build_audit_report_docx`
     (or accept the list but iterate by re-opening the template per
     site — Strategy 1 from §4a; the simpler form is a single-site
     contract).
  2. Get template index via `get_index()`.
  3. Load xlsx via `load_checklist(site.project_value, xlsx_path)`.
  4. Determine inactive planning tier via `_inactive_planning_section(site.project_value)`.
  5. Run B1 → `matched_by_header_table_idx`, `unmatched_observations`.
  6. Initialize `photo_counter_state = [0]`.
  7. For each `LineItem`:
     - `line_item.section == inactive_planning_section` → call B2 with `force_na=True`.
     - else `matched = matched_by_header_table_idx.get(line_item.header_table_idx, [])`:
       - matched non-empty → call B2 with observations.
       - matched empty + section in `NA_SECTIONS` → call B2 with `force_na=True`.
       - matched empty + section in `COMPLIANT_DEFAULT_SECTIONS` → no-op
         (template default Compliant shading).
  8. Populate cover KPI cells (Score, Flagged items, Actions) via
     `index.cover_cells`.
  9. Log `unmatched_observations` (don't block render).
- ~50 lines net.
- One file changed (route layer adjustment may add a second — see §6 Q-MS1).

### B4 — Test rewrite
- Un-skip the 18 Stage-A-skipped tests in
  `tests/test_audit_report_docx_smoke.py` (17) +
  `tests/test_audit_report_cover.py` (1).
- New small unit-test file `tests/test_audit_report_fill.py`:
  - B1: `_match_observations_to_line_items` with synthetic LineItems +
    ChecklistRows + observations; assert correct aggregation by
    `header_table_idx`, correct unmatched routing, correct inactive-
    tier handling.
  - B2-pin test: assert obs_table row 0 col 0 IS the narrative cell on
    the canonical template (Codex answer Q1 — lock the assumption).
- Rewrite assertions in the un-skipped suite:
  - `test_phase_g_*` (Part D structure): **delete** — Part D doesn't
    exist in canonical template.
  - `test_phase_f_*` (Part C banner + grouping): **rewrite** as
    "section banner table at expected position exists with category
    name + score" against canonical structure.
  - `test_phase_e_*` (metadata table + exec summary): **rewrite** as
    "cover Site Conducted / Date of Inspection / Prepared By cells
    populated", and "Executive Summary text frame populated".
  - `test_phase_d_*` (status palette + finding cells + open-actions
    photo embeds): **rewrite** as "criterion N's status cell shaded
    color C", "narrative cell contains observation text", "photo
    embedded in obs_table row 1 col 0".
  - `test_single_site_cover_has_no_bracketed_placeholders`: **rewrite**
    against canonical template's cell coordinates (`index.cover_cells`).
- New multi-site test:
  `tests/test_audit_report_multi_site_zip.py` (if §6 Q-MS1 resolves
  to "route returns zip for multi-site"): verifies route returns zip
  with N independent docx blobs.
- ~3 files changed (smoke, cover, new unit-test file) + optionally a
  4th (multi-site route test).

### B5 — v7 verification render (recipe inlined)

Local stub render (mirrors Stage A's verification, parameter-tweaked):

```python
# /tmp/render_v7.py
import sys
sys.path.insert(0, r"C:\Users\AlanRichardson\gatekeeper")
from pims.audit_report_docx import SiteData, build_audit_report_docx, PIMS_DIR

site = SiteData(
    address="96-98 Hampden Rd, Russell Lea NSW",
    project_value=250_000,
    client="Robertson's Remedial and Painting Pty Ltd",
    prepared_by="Alan Richardson",
    inspection_datetime="13 May 2026 09:00 AEST",
    summary_text="Stage B verification render.",
    observations=[
        {"conformance_status": "Compliant", "ccvs_code": "WAH-H6",
         "observation_text_enriched": "Stub compliant observation."},
        {"conformance_status": "NCR", "ccvs_code": "WAH-H6",
         "observation_text_enriched": "Stub NCR observation."},
    ],
    open_actions=[],
    report_issue_date="2026-05-13",
)
buf = build_audit_report_docx([site], checklist_xlsx_path=PIMS_DIR / "audit_checklist.xlsx")
buf.seek(0)
(PIMS_DIR / "RPD_SSA_v7_StageB_96-98_Hampden.docx").write_bytes(buf.read())
```

Run: `.venv-test/Scripts/python.exe /tmp/render_v7.py`.

Diff vs `pims/7_Hampden_Rd_Cremorne.docx`:
- `Part A/B/C/D` occurrences: 0 (Stage A already cleared; B should not
  regress).
- `Site Safet` typo: still 2 (Stage C).
- Status-cell shading: stub data has 1 Compliant + 1 NCR; visual check
  that the WAH-H6 criterion's status cell now shows the **worst**
  status of the two observations (NCR red) and that the narrative
  cell shows both observations concatenated.
- Inactive planning tier: project_value=250_000 selects HIGH tier;
  LOW tier's planning section should be visibly N/A-shaded throughout.
- Cover KPI cells: Score / Flagged items / Actions populated with
  numeric values (not bracketed placeholders).

Commit + push when satisfied.

### B6 (Stage C, NOT this commit) — out of scope
- `Site Safet` text-frame cleanup pass.
- `docs/TEMPLATE_REGISTRY.md` + `.meta.json` sidecars + in-renderer
  docstring + CI check.
- Retire `pims/scripts/clean_audit_report_template.py`,
  `pims/audit_report_template.docx`,
  `tests/test_audit_report_template_clean.py`,
  `tests/test_audit_report_body_section.py`.

---

## 6. Suggested commit cadence

| Commit | Slices | Files (est) | Test state after |
|---|---|---|---|
| `Stage B1+B2+B3 — index-and-fill + single-site contract` | B1, B2, B3 (+ route adjustment if Q-MS1 picks zip-on-multi) | 1–2 | 39 still pass, 18 still skipped (rewritten next commit) |
| `Stage B4 — rewrite skipped tests against canonical structure` | B4 | 3–4 | ~55 pass, 0 skip |
| `Stage B5 — v7 verification render` | B5 | 0 (docx artefact, gitignored) | n/a |

Stops at logical checkpoints; no commit lands with broken tests.

---

## 7. Open questions for Codex (v2)

**Q-MS1. Multi-site route behaviour.** If we make
`build_audit_report_docx` single-site (§4a Strategy 1), the route
`/pims/audit-report/rpd` for ≥2 `site_ids` must change behaviour:
either iterate + zip (matches `audit_report_from_xlsx.build` semantics)
or return one docx per site as separate response (worse UX). Pick
zip-on-multi? Confirm scope to land in Stage B B3 or defer to a
separate ticket.

**Q-B1. Inactive-tier observations.** An operator could file an
observation against `ccvs_code` that maps via xlsx to a Criteria in the
inactive planning tier (e.g., site value 250k+ but obs tagged with a
<$250K-only criterion). Three options:
(a) treat as unmatched (logged, not rendered),
(b) render under the active tier's "miscellaneous" — no such cell
exists in template,
(c) drop silently.
Recommend (a). Confirm.

**Q-B2. Photo-counter scope.** A single global counter across all
photos in the document (per plan §5 Step 3). For the single-site
contract this is unambiguous. For multi-site-via-zip, each site's
counter restarts at 1. Confirm.

**Q-B3. Bridge drift surfacing.** If `criteria_to_line_item` fails to
resolve a `ChecklistRow` returned by `match_observation` (xlsx Criteria
text drifted from template item_text), the observation is silently
dropped. Should we instead **fail loud at startup** by verifying the
xlsx Criteria column ⊆ template item_text set when
`build_audit_report_docx` is invoked? Costs one extra pass; benefit is
early detection of operator-induced drift.

**Q-B4. Cover-cells text-frame vs table dedup.** Cover labels in
`COVER_LABELS` (`Score`, `Flagged items`, `Actions`, `Site conducted`,
`Prepared by`, `Date of inspection`, `Site Inspection`) live in the
indexed cover **tables**. `_populate_cover` also walks DrawingML
**text frames** for `[Insert …]` placeholders. If the same label
appears as both a table cell and a text-frame placeholder, we'd
populate twice (potentially with diverging values). Plan B3 step 8
populates via `index.cover_cells`. Should we **remove** the
corresponding `[Insert …]` placeholder walks for those labels to avoid
the dedup hazard, or rely on both writing identical values?

---

## 8. Risks

1. **Per-site Document re-open cost.** Multi-site renders open the
   canonical template (9.4 MB, 326 tables) once per site. For typical
   audit batches (1–5 sites) the cost is acceptable (~200–500ms each).
   Above 20 sites would warrant caching, but no current customer use
   case requires it.
2. **`template_index.py` LRU cache.** `get_index()` is
   `@lru_cache(maxsize=1)`. Per-site loop calls return the same
   indexed structure — fine because we're indexing the **template**
   (immutable), not the rendered document. But Stage B B3 must
   carefully **not** rely on cached `doc` references; each per-site
   render must open its own `Document(template_path)` and use the
   cached index's `header_table_idx` / `obs_table_idx` against the
   fresh doc's `doc.tables[i]`. Since table positions are deterministic
   from the template binary, indices are stable across reopens.
3. **`_populate_cover` text-frame walker.** Survived Stage A and works
   for cover placeholders, but post-Stage B the cover KPI cells will
   be populated via tables (not text frames). Risk of double-writing
   addressed in Q-B4 above.
4. **Test rewrites are substantial.** 18 tests need rewriting; some
   delete cleanly (Part D), others need cell-coordinate-aware
   assertions on the canonical template. Estimated 30–45 min of test
   work alone.
5. **Stub-driven v7 won't catch all production-time failures.** A live
   render against `96-98 Hampden Rd Russel Lea` real observations (via
   Railway + session cookie) is the real proof. Stage B5 should also
   trigger a Railway live render, not just stub — flag as part of the
   B5 step for operator action.

---

## 9. References

- `docs/plans/AUDIT_REPORT_CORRECT_TEMPLATE_DIAGNOSIS_AND_PLAN.md` —
  root-cause diagnosis + the v3 plan this Stage B implements.
- `docs/plans/AUDIT_REPORT_REFERENCE_EVALUATION.md` — superseded
  predecessor plan (the §4.8 plan was wrong about which template
  produced the references).
- `docs/plans/CODEX_QA_HANDOVER_audit_report_adoption.md` — Codex's
  prior QA pass against the now-superseded adoption work.
- `pims/services/template_index.py` — the indexer Stage B will use.
- `pims/audit_report_docx.py:505` — `match_observation` (the matcher
  Stage B will reuse, per Option C).
- `pims/services/checklist_matcher.py` — the SVR-flow matcher (NOT
  used in Stage B per Option C).
- `pims/7_Hampden_Rd_Cremorne.docx`,
  `pims/56-58_Fraters_Ave_Sans_Souci.docx` — reference outputs.
- `pims/RPD_SSA_template-inserted.docx` — canonical template.
- Stage A commit: `7b785c4`.

---

## 10. Specific review asks (in priority order)

1. **§4a (multi-site Strategy 1 + route impact)** — Strategy 1 vs body
   cloning. Q-MS1 scope confirmation.
2. **§4b (planning-tier N/A handling)** — semantics correct? Any case
   where the inactive tier should NOT be N/A (e.g., template variant
   that hides the inactive tier already)?
3. **§4c (Option C bridge)** — agree on `match_observation` reuse?
4. **§4d (header_table_idx keying)** — agree, or a better unique key?
5. **§5 slice boundaries** — is B1+B2+B3 still right for one commit
   now that single-site contract is in B3?
6. **§7 Q-B1 through Q-B4** — open questions.
7. **§8 risks** — missing failure modes?

---

## 11. Codex v1 findings — disposition

| Finding | Severity | Disposition | Where addressed |
|---|---|---|---|
| `item_idx` key collides across sections | P1 | Fixed — use `header_table_idx` | §4d + §5 (B1–B3) |
| Multi-site overwrites under in-place fill | P1 | Fixed — per-site Document + zip | §4a, §6 Q-MS1, §B3 |
| Inactive planning tier rendered as compliant | P2 | Fixed — explicit `_inactive_planning_section` → N/A | §4b, §B3 step 4 + 7 |
| Bridge problem framed too narrowly | P2 | Fixed — Option C reuses `match_observation` | §4c |
| Render recipe out-of-band | P3 | Fixed — recipe inlined | §B5 |
| Q1 narrative cell coords | answer | Accepted with B2-test pin | §B2 + §B4 |
| Q2 multi-obs narrative | answer | Concatenate, blank-line sep, no new rows | §B2 |
| Q3 photo overflow | answer | First-slot wins, log overflow | §B2 |
| Q4 N/A semantics | answer | "Always paint N/A" stays for `NA_SECTIONS`; new tier-aware override | §4b |
| Q5 bridge | answer | Option C | §4c |
| Q7 stage scope | answer | `Site Safet` → Stage C; multi-site + tier → Stage B | §B6 |

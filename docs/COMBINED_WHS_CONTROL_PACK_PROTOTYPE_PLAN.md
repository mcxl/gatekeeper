# Combined WHS Control Pack — Prototype Plan

## Status: Planning complete — ready for implementation decision

---

## 1. Prototype Goal

### What the prototype proves

That Safe Method can generate a credible project-level WHS control pack from uploaded scope documents, producing output that a consultant would recognise as a useful first draft for review and refinement — not a finished document, but a structured starting point that saves hours of manual assembly.

### What success looks like

1. A consultant uploads a scope of works for the Withers Road benchmark case
2. The system extracts project context with field-level confidence
3. The consultant confirms/edits extracted fields and trade packages
4. The system generates a single combined .docx containing all 8 sections
5. The output matches the Withers Road benchmark document structure
6. HRCW register shows correct YES/CONDITIONAL/NO for all 17 categories
7. SWMS matrix maps trade packages to HRCW references
8. Hold points are project-specific with conditions and authorisation
9. Risk register is grouped by trade/activity in construction sequence
10. Open items are clearly listed for reviewer attention

If a consultant says "this saves me a day of work and I can review and issue it with my amendments" — the prototype succeeds.

---

## 2. Locked Product Decisions

| Decision | Locked value |
|----------|-------------|
| Product path | Prototype/spec-confirm first |
| Primary user | Consultant |
| Primary input | Uploaded scope/specification documents |
| First output shape | One combined reviewable .docx |
| Relationship to existing products | Standalone SWMS and standalone RA remain separate |
| Trade package identification | Extract + user confirm |
| Risk register depth | One-line summary controls (benchmark style) |
| Review workflow | Two-step: confirm extraction → review output |

---

## 3. Version 1 Scope — Included

### Extraction
- Upload one or more scope/specification documents (PDF, DOCX, TXT)
- Extract project fields using existing `/intake/extract` pipeline (reuse, not rebuild)
- Extract candidate trade packages from scope text
- Assign field-level confidence (high/medium/low/absent)

### User Confirmation Step
- Display extracted fields with confidence badges
- Allow user to edit project fields, confirm/add/remove trade packages
- Flag missing required fields before generation
- Confirm jurisdiction

### Generation
- Run classification (`classify_ra_scope` or new `classify_control_pack_scope`)
- Run inference (`infer_to_dict_ra` extended or new function)
- Build HRCW register (reuse `_build_ra_hrcw_register`)
- Build SWMS matrix from confirmed trade packages + HRCW mapping
- Build hold points from civil/building modifiers (reuse RA hold-point logic)
- Build risk register from hazard list with phase/trade grouping (reuse `_build_hazard_list` + `group_ra_hazards_by_phase`)

### Rendering
- New `render_control_pack()` function producing a single .docx
- 8 sections per the specification
- Dedicated template (portrait, landscape for risk register)
- Footer with document reference and page numbering

### Review Metadata
- Open items list generated from missing/conditional data
- Review status starts at `draft`
- Reviewer name captured at download/issue

---

## 4. Version 1 Exclusions

| Excluded | Reason |
|----------|--------|
| Individual trade-package SWMS generation | Separate product — too complex for V1 |
| Full task-level SWMS detail in risk register | Benchmark uses summary controls, not task steps |
| SDK/API packaging | Premature — product shape not yet validated |
| Multi-user collaboration / assignment workflow | V1 is single-consultant use |
| Template customisation / branding | V1 uses one standard template |
| PDF rendering of control pack | DOCX first; PDF via Gotenberg can be added later |
| Automated trade package identification without user confirmation | Too risky for accuracy — user must confirm |
| Integration with standalone SWMS generation from control pack output | Future feature — pack identifies what SWMSs are needed, doesn't generate them |

---

## 5. Prototype Architecture Impact

### Backend

| Component | Change | Effort |
|-----------|--------|--------|
| `core/inference_matrix.py` | Minor — reuse existing classifiers and hazard builders. May need `classify_control_pack_scope()` wrapper or reuse `classify_ra_scope()` directly | Small |
| `core/control_pack.py` (new) | New module: `build_swms_matrix()` from trade packages + HRCW, `build_control_pack()` orchestrating all sections | Medium |
| `api/main.py` or `api/control_pack_routes.py` (new) | New endpoints: `POST /control-pack/extract`, `POST /control-pack/generate`, `POST /control-pack/render` | Medium |
| `renderers/control_pack_renderer.py` (new) | New renderer: 8-section .docx from scratch or dedicated template | Large |

### Data Structures

| Structure | Status |
|-----------|--------|
| HRCW register | Exists — `_build_ra_hrcw_register()` |
| Hazard list with confidence | Exists — `_build_hazard_list()` |
| Phase grouping | Exists — `group_ra_hazards_by_phase()` |
| Hold points | Exists — RA supplementary sections logic |
| Classification | Exists — `classify_ra_scope()` / `classify_swms_scope()` |
| SWMS matrix | **New** — needs `build_swms_matrix(trade_packages, hrcw_register)` |
| Review metadata | **New** — needs open-items generation from confidence/conditional data |

### Frontend

| Component | Change |
|-----------|--------|
| `frontend/app.html` or new page | New tab or dedicated page for control pack mode |
| Extraction review form | Reuse Mode 04 intake form pattern with trade-package editor |
| Generation status panel | Reuse Mode 04 streaming status pattern |
| Review/download flow | New — shows open items, captures reviewer name |

### Template

| Item | Notes |
|------|-------|
| New .docx template | 8-section structure, portrait + landscape |
| Black-and-white with blue accents | Match current RA/SWMS style |
| HRCW register table | 7 columns |
| SWMS matrix table | 6 columns |
| Hold point table | 6 columns |
| Risk register table | 7 columns, grouped with phase headers |

---

## 6. Prototype Workflow

### Step 1: Upload
User navigates to `/control-pack` (or new tab in app).
Uploads one or more scope/specification documents.
System shows extraction spinner.

### Step 2: Extraction
Backend extracts project fields using Claude (reuse `/intake/extract` prompt adapted for project-level context).
Returns: fields, confidence, sources, candidate trade packages.

### Step 3: Confirm Extracted Context
User reviews extracted fields with confidence badges.
User confirms/edits: project name, site, PCBU, client, jurisdiction.
User confirms/adds/removes candidate trade packages.
User sees missing-field warnings.
User clicks "Generate Control Pack".

### Step 4: Generation
Backend runs:
1. Classification
2. Inference (HRCW flags, hazard families)
3. HRCW register (17 categories, YES/CONDITIONAL/NO)
4. SWMS matrix (from confirmed trade packages + HRCW)
5. Hold points (from classification modifiers + hazard families)
6. Risk register (from hazard list, grouped by trade/activity)
7. Review metadata (open items from missing/conditional data)

Status panel shows progress.

### Step 5: Review Combined Pack
User sees:
- Summary: X trade packages, Y HRCW triggered, Z hold points, W open items
- Open items list (items requiring confirmation before issue)
- Option to enter reviewer name
- Download as .docx

### Step 6: Download / Issue
User downloads .docx.
Document is marked `draft` until reviewer explicitly changes status.
Open items are printed in the document for the reviewer's attention.

---

## 7. Benchmark and Test Plan

### Benchmark Cases

| Case | Input | Expected outcome |
|------|-------|-----------------|
| **Withers Road** (primary) | LinkedIn-level description or uploaded scope | 17 HRCW assessed, 8+ trade packages, 6 hold points, 25+ risk entries, matches benchmark doc structure |
| **Data centre retrofit** (secondary) | Uploaded specification | Correct retrofit classification, fit-out trade packages, no over-called civil HRCW |
| **Facade remedial** (secondary) | Uploaded scope of works | Scaffold as access, occupied-building controls, WAH trade package identified |

### Validation Before Prototype Success

1. Withers Road case produces a .docx that a consultant recognises as structurally correct
2. HRCW register matches benchmark 15/17 or better
3. SWMS matrix identifies at least 6 of the benchmark's 10 trade packages
4. Hold points match benchmark 5/6 or better
5. Risk register has entries grouped by trade/activity, not a flat list
6. Open items list is non-empty for sparse input (honesty check)
7. No fabricated field values — all missing fields use placeholders

### Regression Coverage

- Add `tests/test_control_pack.py` with:
  - Classification assertions for Withers Road
  - HRCW register assertions (reuse from `test_ra_reference_jobs.py`)
  - SWMS matrix entry count assertions
  - Hold point assertions
  - Risk register grouping assertions
  - Renderer produces non-empty .docx bytes

---

## 8. Key Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Trade package extraction is inaccurate** | SWMS matrix is wrong — consultant loses trust | Extract + user confirm (locked decision). Never auto-generate matrix without confirmation. |
| **Renderer complexity** | 8-section .docx is the largest renderer yet | Build incrementally: cover page first, then HRCW table, then each section. Test each section independently. |
| **Scope description quality** | Sparse input produces thin output | Open items list catches this. Conditional HRCW handles uncertainty. Placeholder fields for missing data. |
| **Template design delays** | Can't test renderer without a template | Build renderer from scratch (like RA renderer) for prototype. Migrate to template later if needed. |
| **Feature creep** | V1 tries to do too much | Exclusion list is locked. No trade SWMS generation, no PDF, no collaboration. |
| **Benchmark case is only one project type** | Civil infrastructure coverage strong, other types untested | Add data centre and facade cases as secondary benchmarks after primary validation. |

---

## 9. Recommended Implementation Sequence

### Phase A: Data layer (no frontend)

| Step | What | Builds on |
|------|------|-----------|
| A1 | `build_swms_matrix(trade_packages, hrcw_register)` function | Existing HRCW register |
| A2 | `build_control_pack(description, project_meta, trade_packages)` orchestrator | Existing classify + infer + hazard + hold-point logic |
| A3 | Withers Road data-layer test: generate control pack data, assert structure | A1 + A2 |

### Phase B: Renderer

| Step | What | Builds on |
|------|------|-----------|
| B1 | `render_control_pack()` — cover page + scope summary | RA renderer patterns |
| B2 | HRCW register table (7-column) | A1 data |
| B3 | SWMS matrix table (6-column) | A1 data |
| B4 | Hold point schedule table (6-column) | A2 data |
| B5 | Risk register table (7-column, grouped) | A2 data |
| B6 | Footer, review section, document control | Standard |
| B7 | Withers Road render test: generate .docx, verify structure | B1-B6 |

### Phase C: Backend endpoints

| Step | What | Builds on |
|------|------|-----------|
| C1 | `POST /control-pack/generate` — accepts fields + trade packages, returns .docx | A2 + B1-B6 |
| C2 | `POST /control-pack/extract` — reuse intake extract with control-pack prompt | Existing /intake/extract |
| C3 | Integration test: extract → generate → verify .docx | C1 + C2 |

### Phase D: Frontend

| Step | What | Builds on |
|------|------|-----------|
| D1 | Control pack page or tab — upload + extraction | Mode 04 patterns |
| D2 | Trade package confirmation UI | D1 extraction output |
| D3 | Generation status + download | Mode 04 patterns |
| D4 | Open items display + reviewer name capture | Review metadata |

### Phase E: Benchmark validation

| Step | What | Builds on |
|------|------|-----------|
| E1 | Withers Road end-to-end: upload description → generate → compare to benchmark | All phases |
| E2 | Secondary benchmarks: data centre, facade | E1 patterns |
| E3 | Regression test suite: `test_control_pack.py` | A3 + B7 assertions |

**Estimated total**: 8-12 working days for a competent developer familiar with the codebase. Phase A is the smallest and proves the data layer. Phase B is the largest single effort.

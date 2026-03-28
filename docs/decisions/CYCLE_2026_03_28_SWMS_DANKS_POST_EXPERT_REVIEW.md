# Refinement Decision Log
## Per-Cycle LBV Decision Record

---

### 1. Cycle Summary

- **Date:** 2026-03-28
- **Product mode:** SWMS
- **Benchmark stream:** 18 Danks Street Waterloo quote-to-SWMS benchmark
- **Benchmark case:** Robertson's Q50037-4 exterior remedial repairs and painting quote
- **Cycle owner:** Internal product owner
- **Cycle type:** Post-expert-review refinement (first cycle after escalation to consultant review)

### 2. Starting State

- **Current status:** ESCALATED — returned from consultant review
- **Current weakest point:** Anti-slop solved. Remaining gaps: demolition prerequisites leaking, task 1.7 waterproofing wording drift, blank cover fields, ?? artifacts, no interface controls from quote
- **Reason this cycle was run:** Expert review identified content-quality and issue-gating defects that the deterministic layer can address

### 3. Evaluation Inputs

- **Generated output reviewed:** SWMS_18_Danks_St_Benchmark_Latest.docx (12 tasks, rendered .docx)
- **Reference / benchmark used:** Robertson's quote Q50037-4 (page 2–4: scope, exclusions, conditions)
- **Internal checks run:** Quote-to-SWMS field alignment, prerequisite relevance, artifact scan, cover field completeness, interface control coverage
- **Expert review used:** Yes — Aussie WHS consultant review findings as input
- **Reviewer / review source:** Expert review findings + internal diagnostic

### 4. Main Findings

- **Primary finding:** Demolition-specific prerequisites (licensed demolition supervisor, pre-demolition engineering assessment, SafeWork demolition notification, WHS Reg s.292) present in prerequisites table despite this being a remedial painting job — not supported by source quote.
- **Secondary findings:**
  - Task 1.7 titled "Apply sealants and waterproofing" — source says recaulking / silane clear sealer, not waterproofing
  - Cover table R4 col1 (Person responsible for ensuring compliance) blank — should show placeholder
  - `??` artifact text leaking into stop-work triggers in rendered .docx
  - No interface controls from quote conditions (resident clearing, neighbour access, vegetation, parking, pre-commencement inspection)
  - Finish systems (painted masonry, fibre cement, timber doors, timber beams) not fully separated — agent-level, deferred
- **Where trust dropped:** Prerequisites table credibility (demolition content on a painting job). Blank responsible-person field.
- **What remained strong:** Anti-slop (verified clean). Task-to-quote coverage (10/12 direct match). HRCW flags correct. Task sequence logical.

### 5. Finding Classification

- **Reusable rule(s):**
  1. Demolition prerequisite stripping — applies to all non-demolition SWMS
  2. Waterproofing wording fix — applies when scope has sealant/silane keywords but task says waterproofing
  3. `??` artifact stripping in sanitise_text() — applies to all renderer output
  4. Interface controls injection for occupied residential strata — applies to all occupied-building SWMS
- **Case-specific fix(es):** None
- **Product decision(s):** None — all fixes are reusable rules
- **Deferred item(s):** Finish system separation (agent-level task decomposition), Agent 3 JSON reliability, fibre cement → asbestos association

### 6. Refinement Applied

- **Main refinement targets:** 4 deterministic post-processing and renderer fixes
- **Files/functions changed:**
  1. `renderers/docx_renderer.py` — `sanitise_text()`: strips `??` artifact prefixes
  2. `renderers/docx_renderer.py` — `_fill_prerequisites_table()`: strips demolition-specific qualifications, permits, and legislation when job is not demolition
  3. `renderers/docx_renderer.py` — `_fill_cover_table()`: applies `resolve_field()` to supervisor/responsible-person field so blank → `[To be confirmed]`
  4. `core/orchestrator.py` — `_fix_unsupported_waterproofing()`: replaces "waterproofing" with "sealer application" in task names when scope mentions sealant/silane
  5. `core/orchestrator.py` — `_inject_interface_controls()`: injects 5 quote-derived interface controls (resident clearing, neighbour access, vegetation, parking, pre-commencement inspection) into site-setup tasks for occupied residential jobs
  6. `tests/test_post_expert_review.py` — 10 new tests covering all 4 fixes
- **What changed in plain English:**
  - Demolition boilerplate no longer appears in non-demolition SWMS
  - Sealant/silane tasks no longer drift to "waterproofing" wording
  - Blank critical cover fields show `[To be confirmed]` instead of empty
  - `??` text artifacts stripped before they reach the document
  - Occupied residential SWMS now includes interface controls from the quote conditions
- **What was intentionally not changed:** Agent prompts, task decomposition, finish system separation, anti-slop logic

### 7. Re-Evaluation Result

- **Internal result:** IMPROVEMENTS VERIFIED — all 4 fixes tested (292 tests passing, 10 new)
- **Expert re-review used:** No — awaiting next consultant review cycle
- **What materially improved:** Prerequisite credibility, task wording fidelity, blank field coverage, artifact removal, interface control coverage
- **What is still weak:** Finish system separation (agent-level), Agent 3 JSON reliability, fibre cement → asbestos in task 8 hazards

### 8. End-of-Cycle Decision

- **Decision:** HOLD FOR REGENERATION — the fixes are in the deterministic layer. The SWMS needs to be regenerated against the same benchmark case to verify the fixes render correctly in a fresh output, then re-reviewed.
- **Why this decision was made:** The 4 fixes address the top expert-review findings that the deterministic layer can solve. Finish system separation is agent-level and cannot be fixed without decomposer changes — that is a separate product decision.
- **Next refinement target:** Regenerate benchmark SWMS → verify demolition stripped, waterproofing wording fixed, blank fields filled, artifacts gone, interface controls present → then decide whether to run another content-quality cycle or escalate for second consultant review.

### 9. Governance Note

- **Does this change affect product boundaries?** No
- **Does this introduce a reusable quality rule?** Yes — 4 reusable rules (demolition stripping, waterproofing fix, artifact stripping, interface controls)
- **Does regression protection need updating?** Yes — 10 new tests added in test_post_expert_review.py

### 10. One-Line Outcome

Post-expert-review refinement: demolition prerequisites stripped, waterproofing wording fixed, blank fields gated, artifacts stripped, interface controls injected. 292 tests passing. Decision: hold for regeneration and re-verification.

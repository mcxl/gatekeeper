# Refinement Decision Log
## Per-Cycle LBV Decision Record

---

### 1. Cycle Summary

- **Date:** 2026-03-28
- **Product mode:** SWMS
- **Benchmark stream:** 18 Danks Street Waterloo quote-to-SWMS benchmark
- **Benchmark case:** Robertson's Q50037-4 exterior remedial repairs and painting quote
- **Cycle owner:** Internal product owner

### 2. Starting State

- **Current status:** ACTIVE
- **Current weakest point:** Three-layer anti-slop verified; remaining gaps are agent content quality and task-to-quote alignment
- **Reason this cycle was run:** Unattended validation and final-readiness assessment

### 3. Evaluation Inputs

- **Generated output reviewed:** Regenerated SWMS (12 tasks, rendered to .docx)
- **Reference / benchmark used:** Robertson's quote Q50037-4
- **Internal checks run:** Anti-slop verification, task-to-quote alignment scoring, renderer crash identification
- **Expert review used:** No
- **Reviewer / review source:** Internal diagnostic

### 4. Main Findings

- **Primary finding:** Anti-slop remains clean (no asbestos HRCW, no road boilerplate, no dedicated asbestos task). Task-to-quote alignment is materially adequate (10/12 direct match, 2 partial).
- **Secondary findings:** Renderer crashed on surrogate characters from agent output — fixed with utf-8 encode/decode in sanitise_text(). Agent 3 had multiple JSON parsing failures ("Extra data") — pre-existing pipeline reliability issue. Task 8 still mentions asbestos in fibre cement painting hazards — agent-level, known, deferred.
- **Where trust dropped:** Agent 3 reliability (multiple failures per generation). Fibre cement → asbestos association in task 8 hazards.
- **What remained strong:** Anti-slop architecture (3 layers), task-to-quote coverage, task sequence (site setup → access → repairs → painting → defects → demob), HRCW alignment.

### 5. Finding Classification

- **Reusable rule(s):** Surrogate character stripping in sanitise_text() — applies to all renderer output
- **Case-specific fix(es):** None
- **Product decision(s):** The next step for this stream is external Aussie WHS consultant review, not another internal refinement
- **Deferred item(s):** Agent 3 JSON reliability, fibre cement → asbestos association, building-age gating

### 6. Refinement Applied

- **Main refinement target:** Renderer surrogate character crash
- **Files/functions changed:** `renderers/docx_renderer.py` — sanitise_text() strips surrogates
- **What changed in plain English:** Agent-generated text containing emoji surrogates no longer crashes the renderer
- **What was intentionally not changed:** Agent prompts, task-to-quote mapping, fibre cement association

### 7. Re-Evaluation Result

- **Internal result:** ESCALATE_TO_EXPERT_REVIEW — the output is strong enough for consultant review
- **Expert re-review used:** No — prepared for handoff
- **What materially improved:** Renderer no longer crashes on agent-generated surrogates
- **What is still weak:** Agent 3 JSON reliability, fibre cement → asbestos mention in task 8 hazards

### 8. End-of-Cycle Decision

- **Decision:** Escalate to expert review
- **Why this decision was made:** Internal refinement has reached diminishing returns. The anti-slop architecture is verified. The task-to-quote alignment is adequate for draft quality. The remaining weaknesses are agent-level content quality that benefits more from consultant feedback than from more inference rules.
- **Next refinement target:** Consultant review findings → classify as reusable rules or case-specific fixes

### 9. Governance Note

- **Does this change affect product boundaries?** No
- **Does this introduce a reusable quality rule?** Yes — surrogate stripping in sanitise_text()
- **Does regression protection need updating?** No

### 10. One-Line Outcome

18 Danks Street SWMS passes internal gates and is ready for external consultant review. Surrogate crash fixed. Anti-slop verified. Task-to-quote alignment adequate. Decision: escalate to expert review.

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
- **Current weakest point:** Verify two-layer anti-slop fix and assess task-to-quote alignment
- **Reason this cycle was run:** Prior cycles added inference negation + agent exclusion instruction. This cycle regenerated to verify combined effect.

### 3. Evaluation Inputs

- **Generated output reviewed:** Regenerated SWMS (12 tasks) with both anti-slop layers active
- **Reference / benchmark used:** Robertson's quote Q50037-4
- **Internal checks run:** Asbestos/demolition/road content scan; HRCW flag check; task-to-quote alignment
- **Expert review used:** No
- **Reviewer / review source:** Internal diagnostic

### 4. Main Findings

- **Primary finding:** Dedicated asbestos survey task is gone (anti-slop working at agent layer). Road/traffic boilerplate is gone. BUT asbestos HRCW flag still ticked — because `infer_requirements()` HRCW flag computation used `k in expanded` without calling `_is_negated()`. The negation fix had been applied to matrix matching and hazard list building, but not to HRCW flag computation.
- **Secondary findings:** Task 8 "Paint fibre cement board" still mentions asbestos in hazards — this is from the agent, which sees "fibre cement" and associates it with asbestos risk. This is a judgment call (fibre cement ≠ asbestos cement, but the association is common in the industry).
- **Where trust dropped:** HRCW asbestos checkbox still ticked despite T&Cs explicitly excluding asbestos — a reviewer would notice this immediately.
- **What remained strong:** Task set is materially better (12 tasks covering quoted scope items). Site setup is now first. No road/traffic contamination. No dedicated asbestos task.

### 5. Finding Classification

- **Reusable rule(s):** Negation/exclusion detection must be applied to ALL inference outputs — matrix matching, hazard list building, AND HRCW flag computation. These are three independent code paths that all need the same awareness.
- **Case-specific fix(es):** None — this is a systemic gap.
- **Product decision(s):** None
- **Deferred item(s):** Agent-level fibre cement → asbestos association in painting tasks — this is an industry knowledge issue, not a negation issue. Fibre cement boards in buildings built after 2003 should not trigger asbestos concerns. Building age should gate this.

### 6. Refinement Applied

- **Main refinement target:** HRCW flag negation
- **Files/functions changed:** `core/inference_matrix.py` — added `_hrcw_check()` helper in `infer_requirements()` that calls `_is_negated(k, original_text)` before confirming a flag. Applied to all 11 HRCW flag checks.
- **What changed in plain English:** All HRCW checkbox decisions now respect exclusion/variation context. A keyword like "asbestos" appearing in "latent condition... deemed variation" text no longer ticks the HRCW checkbox.
- **What was intentionally not changed:** Agent-level fibre cement association (deferred — needs building-age awareness). Task sequence refinement (still agent-dependent).

### 7. Re-Evaluation Result

- **Internal result:** REVIEW_INTERNAL — three-layer anti-slop is now complete (inference + HRCW flags + agent). Asbestos HRCW correctly suppressed. Task set materially aligned to quote.
- **Expert re-review used:** No
- **What materially improved:** Asbestos HRCW flag now correctly suppressed for Danks Street. Three independent anti-slop layers all active and verified.
- **What is still weak:** Agent may still mention asbestos risk in fibre cement painting tasks (industry association, not scope-derived). Task sequence could be tighter. Building-age gating not implemented.

### 8. End-of-Cycle Decision

- **Decision:** Continue and refine — but the remaining weaknesses are agent-level content quality and building-age awareness, not inference/HRCW logic. The anti-slop fix is structurally complete.
- **Why this decision was made:** The three-layer anti-slop architecture is now verified and working. The HRCW flags, inference matrix, and agent scope context all respect exclusion/variation context. The next improvement would be either: (a) agent prompt refinement for fibre cement ≠ asbestos in post-2003 buildings, or (b) task-to-quote alignment tightening.
- **Next refinement target:** Assess whether the Danks Street stream is approaching its stop rule, or whether one more cycle on task-to-quote alignment is justified.

### 9. Governance Note

- **Does this change affect product boundaries?** No
- **Does this introduce a reusable quality rule?** Yes — negation/exclusion must be applied to ALL three inference output paths (matrix matching, hazard list, HRCW flags)
- **Does regression protection need updating?** No — existing tests pass. The HRCW negation is covered by the _is_negated tests.

### 10. One-Line Outcome

HRCW flag detection now respects exclusion/variation negation — three-layer anti-slop complete. Asbestos flag correctly suppressed for Danks Street. Decision: continue and refine (evaluate stop-rule readiness next).

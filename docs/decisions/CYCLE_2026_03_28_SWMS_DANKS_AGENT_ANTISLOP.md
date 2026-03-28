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
- **Current weakest point:** Task sequence and task-to-quote alignment after inference-layer anti-slop fix
- **Reason this cycle was run:** Prior cycle added exclusion-context negation to the inference engine. This cycle regenerated the SWMS to verify whether the agent-level output improved.

### 3. Evaluation Inputs

- **Generated output reviewed:** Regenerated SWMS from quote scope description (12 tasks)
- **Reference / benchmark used:** Robertson's quote Q50037-4
- **Internal checks run:** Task list vs quote scope comparison; asbestos/demolition content scan
- **Expert review used:** No
- **Reviewer / review source:** Internal diagnostic

### 4. Main Findings

- **Primary finding:** The inference-layer negation fix works (asbestos HRCW suppressed in inference). However, the decomposer agent still generated task 1.3 "Survey and record pre-existing conditions and latent hazards" with ASB-H6 CCVS and asbestos content — because the agent reads the raw description text independently of the inference engine.
- **Secondary findings:** Task sequence improved (site setup is now task 1, access is task 2). Core repair/painting tasks align well to the quote scope. 11 of 12 tasks are legitimate.
- **Where trust dropped:** The asbestos survey task (1.3) is still the trust-killer — a consultant seeing an asbestos task in a painting/repairs SWMS where asbestos is explicitly excluded would question the document.
- **What remained strong:** Repair tasks (spalling, crack stitching, brickwork), painting tasks, access setup/demob, green wall removal all match the quote.

### 5. Finding Classification

- **Reusable rule(s):** Exclusion-context items must be communicated to the decomposer agent, not just the inference engine. The inference and agent layers are independent — fixing one doesn't fix the other.
- **Case-specific fix(es):** None beyond the reusable rule.
- **Product decision(s):** None
- **Deferred item(s):** Task sequence fine-tuning (crack stitching before spalling or vice versa — both are defensible). Product-name specificity in controls (Fosroc, Dulux references).

### 6. Refinement Applied

- **Main refinement target:** Agent-level anti-slop via excluded-item detection
- **Files/functions changed:** `core/orchestrator.py` — added `_detect_excluded_items()`, wired into both `generate_swms()` and `generate_swms_stream()` scope_context
- **What changed in plain English:** When the description contains hazmat keywords (asbestos, lead paint, toxic material) in exclusion/variation context, the orchestrator adds an explicit instruction to the decomposer's scope context: "DO NOT generate tasks for: asbestos removal or survey, lead paint removal or testing — these are latent conditions, not contracted scope."
- **What was intentionally not changed:** Raw description text (still includes the T&C sentence for honesty), inference matrix negation (already working), task sequence order

### 7. Re-Evaluation Result

- **Internal result:** REVIEW_INTERNAL — the two-layer anti-slop fix (inference negation + agent exclusion instruction) should now prevent both HRCW triggering and task generation for excluded items. Full regeneration needed to confirm.
- **Expert re-review used:** No
- **What materially improved:** Decomposer now receives explicit "DO NOT generate" instruction for excluded hazmat items alongside scope context.
- **What is still weak:** Not yet regenerated and confirmed end-to-end with both fixes active. Next cycle should regenerate and verify zero asbestos content.

### 8. End-of-Cycle Decision

- **Decision:** Continue and refine
- **Why this decision was made:** Two layers of anti-slop are now in place (inference negation + agent exclusion instruction). The next cycle should regenerate and confirm the combined effect. If asbestos content is eliminated, the stream can focus on task-to-quote alignment quality.
- **Next refinement target:** Regenerate and confirm zero asbestos/hazmat slop. Then assess overall task-to-quote alignment.

### 9. Governance Note

- **Does this change affect product boundaries?** No
- **Does this introduce a reusable quality rule?** Yes — excluded-item detection must reach both inference AND agent layers
- **Does regression protection need updating?** No — existing tests pass; full end-to-end requires live regeneration

### 10. One-Line Outcome

Added agent-level exclusion instruction for hazmat items in variation/latent-condition context. Two-layer anti-slop now in place (inference + agent). Decision: continue and refine (regenerate and verify next cycle).

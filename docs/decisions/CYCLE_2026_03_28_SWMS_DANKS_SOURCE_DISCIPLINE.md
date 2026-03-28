# Refinement Decision Log
## Per-Cycle LBV Decision Record

---

### 1. Cycle Summary

- **Date:** 2026-03-28
- **Product mode:** SWMS
- **Benchmark stream:** 18 Danks Street Waterloo quote-to-SWMS benchmark
- **Benchmark case:** Robertson's Q50037-4 exterior remedial repairs and painting quote
- **Cycle owner:** Internal product owner
- **Cycle type:** Source-discipline refinement (post-Aussie-WHS-review)

### 2. Starting State

- **Current status:** ACTIVE — content-quality fixes applied, Aussie WHS review returned additional findings
- **Current weakest point:** Residual unsupported invention (active hazmat workflows, utility isolation, structural engineer approvals, council consent), one generic monitoring row, some merged repair scopes
- **Reason this cycle was run:** Aussie WHS review identified that the prior content-quality cycle was necessary but insufficient. Specific findings: latent hazmat treated too actively, unsupported controls surviving, monitoring still too WAH-centred in places, document-trust gaps.

### 3. Evaluation Inputs

- **Generated output reviewed:** Regenerated SWMS (12 tasks, 0 failures, logically ordered)
- **Reference / benchmark used:** Robertson's quote Q50037-4 (pages 2-4: scope, exclusions, conditions)
- **Internal checks run:** 6-priority automated verification (P1-P6)
- **Expert review used:** Yes — Aussie WHS review findings as control point
- **Reviewer / review source:** Aussie WHS consultant review findings

### 4. Main Findings

- **Primary finding:** Two new stripping functions eliminated the remaining unsupported invention:
  1. Active hazmat workflows stripped — latent-condition pathway preserved but active survey/assessor controls removed
  2. Unsupported controls stripped — utility isolation, shoring plans, council consent, structural engineer approvals removed from non-applicable tasks

- **Secondary findings:**
  - The agent did not regenerate the invented "Survey and identify latent hazardous materials" task on this run — the `_strip_active_hazmat` function is a safety net for when it does
  - Generic responsibilities: 0/12 (was 1/12 last cycle)
  - Generic WAH-only monitoring: 1/12 (task 1.5 "Point and reinstate brickwork" — fixed with broader dust keyword matching)
  - Quote coverage: 12/12 (100%)
  - Task separation: 12 distinct tasks covering all quote scope items
  - Repair scopes still partially merged by the decomposer (crack stitching + spalling in 1.10, brickwork reconstruction + repointing in 1.5) — this is agent-level and acceptable given both are masonry repair tasks

- **Where trust dropped:** Minor — task 1.8 "Paint fibre cement eaves, soffits and timber elements" still lumps fibre cement with some timber. But fibre cement is now a distinct task from masonry/render painting, which is the key separation.
- **What remained strong:** All prior fixes (reliability 12/12, sequence, anti-slop, interface controls, demolition stripping, responsibility improvement, monitoring crosswalk).

### 5. Finding Classification

- **Reusable rule(s):**
  1. `_strip_unsupported_controls()` — strips utility isolation, shoring plans, council consent, structural engineer approvals from remedial painting scope. Applies to all remedial/painting SWMS.
  2. `_strip_active_hazmat()` — converts active hazmat survey tasks to latent-condition stop-work; strips active hazmat controls from other tasks. Applies to all SWMS where hazmat is a latent condition, not contracted scope.
- **Case-specific fix(es):** None
- **Product decision(s):** Repair scope merging (crack stitching + spalling, reconstruction + repointing) is acceptable decomposer behaviour — not worth forcing separation.
- **Deferred item(s):** Fibre cement + timber lumping in task 1.8 (minor, agent-level).

### 6. Refinement Applied

- **Main refinement targets:** 2 new stripping functions + 1 monitoring keyword fix
- **Files/functions changed:**
  1. `core/orchestrator.py` — added `_strip_unsupported_controls()`: strips utility isolation, shoring plans, council consent, structural engineer approvals
  2. `core/orchestrator.py` — added `_strip_active_hazmat()`: converts active hazmat survey tasks to latent-condition pathway, strips active hazmat controls from other tasks
  3. `core/orchestrator.py` — `_improve_monitoring()`: added "mortar", "brickwork re" as dust-monitoring keywords
  4. `core/orchestrator.py` — `_normalise_task()`: hooks both new functions
  5. `tests/test_content_quality.py` — 7 new tests (4 unsupported controls + 3 active hazmat)
- **What changed in plain English:**
  - No more utility isolation certificates, structural shoring plans, or council consent requirements in a remedial painting SWMS
  - If the agent invents an active hazmat survey task, it gets converted to a latent-condition stop-work note
  - Active hazmat survey controls are stripped from all tasks — the latent-condition pathway (stop work if encountered) is preserved
  - Brickwork/mortar tasks now get dust-specific monitoring instead of generic WAH
- **What was intentionally not changed:** Agent prompts, decomposer granularity, anti-slop logic, renderer logic, existing reliability/sequence/interface controls

### 7. Re-Evaluation Result

- **Internal result:** SOURCE DISCIPLINE MATERIALLY TIGHTENED
  - Active hazmat content: 0 instances
  - Unsupported controls: 0 instances
  - Generic responsibilities: 0/12
  - Generic monitoring: 0/12 (after mortar keyword fix)
  - Quote coverage: 12/12 (100%)
  - Task completion: 12/12
  - Sequence: logically ordered
  - All prior fixes: no regression
- **Expert re-review used:** Expert review findings as input, not re-reviewed
- **What materially improved:** Source discipline — the output no longer invents controls the quote doesn't support
- **What is still weak:** Minor — repair scope merging (acceptable), fibre cement + timber lumping in one task (minor)

### 8. End-of-Cycle Decision

- **Decision:** APPROACHING BENCHMARK QUALITY — hold for re-review or one more precision pass
- **Why this decision was made:** The six priority findings from the Aussie WHS review are now materially addressed:
  1. Active hazmat: stripped
  2. Unsupported controls: stripped
  3. Repair scope separation: improved (12 tasks, some acceptable merging)
  4. CCVS/monitoring crosswalk: hazard-specific (11/12, last one fixed)
  5. Responsibilities: all task-specific
  6. Document trust: placeholders gated, no artifacts

  The remaining issues are minor agent-level content choices (repair merging, fibre cement + timber lumping) that do not materially harm the draft quality. A consultant would likely accept this as a competent working draft requiring site-specific completion, not a document with structural defects.
- **Next refinement target:** Either (a) submit for re-review to confirm benchmark quality, or (b) one final precision pass on repair scope separation if the decomposer can be nudged without destabilising.

### 9. Governance Note

- **Does this change affect product boundaries?** No
- **Does this introduce a reusable quality rule?** Yes — 2 reusable rules (unsupported control stripping, active hazmat stripping)
- **Does regression protection need updating?** Yes — 7 new tests in test_content_quality.py. Total: 330 tests passing.

### 10. One-Line Outcome

Source-discipline refinement: unsupported controls stripped, active hazmat converted to latent-condition pathway, monitoring fully hazard-specific, 100% quote coverage, 0 generic responsibilities. 330 tests. Decision: approaching benchmark quality.

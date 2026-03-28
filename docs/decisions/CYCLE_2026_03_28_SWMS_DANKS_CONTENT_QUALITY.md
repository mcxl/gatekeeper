# Refinement Decision Log
## Per-Cycle LBV Decision Record

---

### 1. Cycle Summary

- **Date:** 2026-03-28
- **Product mode:** SWMS
- **Benchmark stream:** 18 Danks Street Waterloo quote-to-SWMS benchmark
- **Benchmark case:** Robertson's Q50037-4 exterior remedial repairs and painting quote
- **Cycle owner:** Internal product owner
- **Cycle type:** Content-quality refinement (first cycle on stable base)

### 2. Starting State

- **Current status:** ACTIVE — ready for content-quality cycle (reliability and sequence resolved)
- **Current weakest point:** Unsupported invention in agent controls, generic SUP/WKR responsibility boilerplate, WAH-only CCVS monitoring, insufficient finish-system separation
- **Reason this cycle was run:** Output is now complete (12/12 tasks) and logically ordered. Content-quality assessment can proceed on a stable base.

### 3. Evaluation Inputs

- **Generated output reviewed:** Regenerated SWMS (12 tasks, 0 failures, logically ordered)
- **Reference / benchmark used:** Robertson's quote Q50037-4 (pages 2-4)
- **Internal checks run:** Demolition content scan, responsibility genericity count, monitoring specificity audit, quote coverage, finish-system separation
- **Expert review used:** Aussie WHS review findings as input (via adjudication analysis)
- **Reviewer / review source:** Internal diagnostic informed by expert review findings

### 4. Main Findings

- **Primary finding:** Three deterministic post-processing fixes materially improved content quality:
  1. Demolition content stripped from all non-demolition tasks (was present in scaffold dismantle, green wall removal, and other tasks)
  2. Responsibility assignments replaced from generic boilerplate to task-specific text (11/12 tasks now have specific responsibilities)
  3. CCVS monitoring crosswalk improved from WAH-only to hazard-specific (dust, chemical, exclusion zone, scaffold patterns)

- **Secondary findings:**
  - Finish-system separation dramatically improved by the agent (likely aided by the more complete task list from reliability fixes): 6 distinct finish tasks now present
  - Quote scope coverage reached 100% (11/11 checked items)
  - One remaining generic responsibility (task 1.3 "Survey and identify latent hazardous materials") — this is a niche task type not in the pattern library
  - Task 1.7 named "Apply sealants and sealer application coatings" — slightly redundant wording but functionally correct
  - Task sequence has minor imperfections (repairs split across tasks 1.4 and 1.6, painting at 1.5 between them) but is materially logical

- **Where trust dropped:** Minor: task 1.3 "Survey and identify latent hazardous materials" is partially invented — the quote mentions "pre-existing toxic materials" as a latent condition/variation, not as a task to perform. This is a reasonable WHS inclusion but not quote-derived.
- **What remained strong:** Anti-slop (no regression). Reliability (12/12). Sequence (setup first, demob last, repairs before coating). All prior deterministic fixes still operational.

### 5. Finding Classification

- **Reusable rule(s):**
  1. `_strip_demolition_content()` — strips demolition phrases from controls/admin of non-demolition tasks. Applies to all SWMS.
  2. `_improve_responsibility()` — replaces generic SUP/WKR boilerplate with task-type-specific text. Applies to all SWMS.
  3. `_improve_monitoring()` — replaces WAH-only monitoring with hazard-specific critical controls (dust, chemical, scaffold, exclusion, removal). Applies to all SWMS.
- **Case-specific fix(es):** None
- **Product decision(s):** None needed this cycle
- **Deferred item(s):** Task 1.3 "hazardous materials survey" invention (minor — reasonable WHS content), minor task sequencing imperfections

### 6. Refinement Applied

- **Main refinement targets:** 3 content-quality post-processing functions
- **Files/functions changed:**
  1. `core/orchestrator.py` — added `_strip_demolition_content()`: strips demolition-specific controls/admin from non-demolition tasks
  2. `core/orchestrator.py` — added `_improve_responsibility()`: replaces generic SUP/WKR boilerplate with task-type-specific responsibility text (9 task-type patterns)
  3. `core/orchestrator.py` — added `_improve_monitoring()`: replaces WAH-only monitoring with hazard-specific critical controls (6 hazard patterns: setup, scaffold, dust, chemical, wah, removal)
  4. `core/orchestrator.py` — `_normalise_task()`: hooks all three new functions
  5. `tests/test_content_quality.py` — 13 new tests covering all 3 functions
- **What changed in plain English:**
  - Scaffold dismantling no longer claims you need a demolition licence
  - Each task now has specific supervisor and worker responsibilities instead of "[task name] per SWMS"
  - The monitoring table now checks for dust extraction on grinding tasks, SDS on chemical tasks, exclusion zones on setup tasks — not just harness checks on everything
- **What was intentionally not changed:** Agent prompts, decomposer granularity, anti-slop logic, renderer logic

### 7. Re-Evaluation Result

- **Internal result:** CONTENT QUALITY MATERIALLY IMPROVED
  - Demolition content: 0 instances (was multiple)
  - Generic responsibility: 1/12 (was 12/12)
  - WAH-only monitoring: 0/12 (was 12/12)
  - Quote scope coverage: 100% (was 93%)
  - Finish systems: 6 distinct tasks (was 2 lumped tasks)
  - Task completion: 12/12
  - Task sequence: logically ordered
- **Expert re-review used:** No — preparing for handoff
- **What materially improved:** Responsibility specificity, monitoring hazard alignment, demolition content removal, finish-system separation
- **What is still weak:** Minor — task 1.3 invention, slight sequence imperfections, one remaining generic responsibility

### 8. End-of-Cycle Decision

- **Decision:** READY FOR AUSSIE WHS REVIEW
- **Why this decision was made:** The output now addresses all four content-quality findings from the adjudication:
  1. Unsupported invention: demolition content stripped, remaining invention is minor and reasonable
  2. Responsibility boilerplate: replaced in 11/12 tasks
  3. CCVS monitoring: fully crosswalked to hazard profiles
  4. Finish-system separation: 6 distinct finish tasks
  The output is complete (12/12), logically ordered, and content-quality is at the level where consultant feedback would be more productive than further internal tuning.
- **Next refinement target:** Consultant review findings → classify as reusable rules vs agent-prompt changes

### 9. Governance Note

- **Does this change affect product boundaries?** No
- **Does this introduce a reusable quality rule?** Yes — 3 reusable rules (demolition stripping, responsibility improvement, monitoring crosswalk)
- **Does regression protection need updating?** Yes — 13 new tests in test_content_quality.py. Total: 323 tests passing.

### 10. One-Line Outcome

Content-quality cycle: demolition content stripped, responsibilities task-specific (11/12), monitoring hazard-aligned (0 WAH-only), finish systems separated (6 tasks), 100% quote coverage. 323 tests. Decision: ready for Aussie WHS review.

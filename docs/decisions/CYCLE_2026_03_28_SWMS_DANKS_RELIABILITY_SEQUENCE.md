# Refinement Decision Log
## Per-Cycle LBV Decision Record

---

### 1. Cycle Summary

- **Date:** 2026-03-28
- **Product mode:** SWMS
- **Benchmark stream:** 18 Danks Street Waterloo quote-to-SWMS benchmark
- **Benchmark case:** Robertson's Q50037-4 exterior remedial repairs and painting quote
- **Cycle owner:** Internal product owner
- **Cycle type:** Reliability and sequence hardening

### 2. Starting State

- **Current status:** ACTIVE — internal refinement (revised from premature READY_FOR_SECOND_CONSULTANT_REVIEW)
- **Current weakest point:** Agent 3 JSON reliability (41% task loss) and arbitrary task sequence ordering
- **Reason this cycle was run:** Adjudication found the prior verification cycle was too narrow. Output was missing 5 of 12 tasks and had illogical task order. Content-quality judgment cannot be stable on incomplete, unordered output.

### 3. Evaluation Inputs

- **Generated output reviewed:** Regenerated SWMS (12 tasks, 0 failures, logically ordered)
- **Reference / benchmark used:** Robertson's quote Q50037-4
- **Internal checks run:** Task completion rate, quote scope coverage, sequence logic verification
- **Expert review used:** Adjudication analysis informed by Aussie WHS review findings
- **Reviewer / review source:** Internal adjudication + automated verification

### 4. Main Findings

- **Primary finding:** Agent 3 reliability fixed — 0% failure rate (was 41%). Robust JSON extraction (`extract_json`) handles trailing commentary that caused "Extra data" parse failures. Retry logic (1 retry per task) provides additional safety net.

- **Secondary findings:**
  - Task sequence ordering now follows logical site workflow: setup → access → removals → repairs → sealant → coatings → reinstatement → QA → demob
  - Quote scope coverage: 14/15 items (93%) — only "concrete spalling" as a named task is missing (likely folded into crack stitching/masonry repair)
  - 12/12 tasks present — complete output for the first time in this stream
  - Timber beam treatment now present as a distinct task
  - Paint fibre cement now appears alongside masonry/render painting
  - Paint timber doors/frames is a separate task

- **Where trust dropped:** The agent decomposer still lumps some finish systems (masonry + fibre cement in one task). "Concrete spalling" is absorbed into adjacent repair tasks rather than standing alone.
- **What remained strong:** Anti-slop verified (no regression). All prior deterministic fixes still operational. Interface controls present. No demolition prerequisites. No waterproofing wording drift. No `??` artifacts. No blank critical fields.

### 5. Finding Classification

- **Reusable rule(s):**
  1. `extract_json()` — robust JSON extraction handling trailing commentary, leading text, markdown fences. Applies to all 4 agents.
  2. `_reorder_tasks()` — deterministic site-workflow ordering by phase. Applies to all SWMS output.
  3. Retry logic (1 retry) in `_process_single_task` — applies to all streaming SWMS generation.
- **Case-specific fix(es):** None
- **Product decision(s):** None — but finish-system granularity remains a potential decomposer prompt decision
- **Deferred item(s):** Finish-system separation (masonry vs fibre cement), concrete spalling as named task, agent content invention assessment, responsibility column quality, CCVS monitoring crosswalk completeness

### 6. Refinement Applied

- **Main refinement targets:** Agent 3 reliability + task sequence ordering
- **Files/functions changed:**
  1. `core/utils.py` — added `extract_json()`: robust JSON extraction with `JSONDecoder.raw_decode` fallback
  2. `agents/control_writer.py` — replaced `json.loads()` with `extract_json()`
  3. `agents/assembler.py` — replaced `json.loads()` with `extract_json()`
  4. `agents/decomposer.py` — replaced `json.loads()` with `extract_json()`
  5. `agents/risk_assessor.py` — replaced `json.loads()` with `extract_json()`
  6. `core/orchestrator.py` — added retry logic (1 retry) in `_process_single_task()`
  7. `core/orchestrator.py` — added `_reorder_tasks()` and `_task_phase_score()` for deterministic site-workflow ordering
  8. `core/orchestrator.py` — `done` event now includes reordered `tasks` list
  9. `tests/test_reliability_sequence.py` — 18 new tests (7 extract_json + 11 sequence ordering)
- **What changed in plain English:**
  - Agent JSON parse failures no longer lose tasks — trailing commentary is handled gracefully
  - Failed tasks get one automatic retry before being dropped
  - All SWMS tasks are now sorted into a logical site workflow (setup → scaffold → removals → repairs → coatings → reinstatement → QA → demob)
  - Task step numbers (1.1, 1.2, ...) are renumbered after reordering
- **What was intentionally not changed:** Agent prompts, task decomposition granularity, anti-slop logic, renderer logic

### 7. Re-Evaluation Result

- **Internal result:** RELIABILITY AND SEQUENCE STABILISED
  - Task completion: 12/12 (100%) — was 7/12 (58%)
  - Quote scope coverage: 14/15 (93%) — was 8/15 (53%)
  - Sequence: logically ordered — was arbitrary
  - Setup first: YES
  - Demob last: YES
  - Repairs before painting: YES
- **Expert re-review used:** No — preparing for content-quality assessment
- **What materially improved:** Output completeness, task sequence, reliability
- **What is still weak:** Finish-system granularity (masonry + fibre cement lumped), agent content invention not yet assessed, responsibility/monitoring boilerplate, CCVS crosswalk

### 8. End-of-Cycle Decision

- **Decision:** READY FOR CONTENT-QUALITY CYCLE
- **Why this decision was made:** The upstream blockers (reliability, sequence) are now resolved. For the first time in this stream, the output is complete (12/12 tasks), logically ordered, and stable enough for meaningful content-quality assessment. The remaining gaps (invention, boilerplate, monitoring crosswalk, finish granularity) are content-quality issues, not infrastructure issues.
- **Next refinement target:** Content-quality cycle — assess against the Aussie WHS review findings: unsupported invention, weak responsibility assignment, generic CCVS monitoring, finish-system granularity. Classify each as deterministic-fixable or agent-prompt-level.

### 9. Governance Note

- **Does this change affect product boundaries?** No
- **Does this introduce a reusable quality rule?** Yes — `extract_json` (all agents), `_reorder_tasks` (all SWMS), retry logic (all streaming)
- **Does regression protection need updating?** Yes — 18 new tests in test_reliability_sequence.py. Total: 310 tests passing.

### 10. One-Line Outcome

Agent 3 reliability fixed (0% failures, was 41%). Task sequence now follows logical site workflow. Output complete (12/12 tasks, 93% quote coverage). 310 tests passing. Decision: ready for content-quality cycle.

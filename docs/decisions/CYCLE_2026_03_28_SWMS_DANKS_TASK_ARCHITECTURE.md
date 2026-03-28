# Refinement Decision Log
## Per-Cycle LBV Decision Record

---

### 1. Cycle Summary

- **Date:** 2026-03-28
- **Product mode:** SWMS
- **Benchmark stream:** 18 Danks Street Waterloo quote-to-SWMS benchmark
- **Benchmark case:** Robertson's Q50037-4 exterior remedial repairs and painting quote
- **Cycle owner:** Internal product owner
- **Cycle type:** Task-architecture refinement (source-led sequence and CCVS precision)

### 2. Starting State

- **Current status:** BENCHMARK_CANDIDATE — strong working draft, not yet benchmark quality
- **Current weakest point:** Paint tasks appearing before repair tasks in sequence; green wall reinstatement not consistently after coatings; demolition text still leaking in scaffold dismantle; one generic monitoring row for reinstatement
- **Reason this cycle was run:** Aussie WHS review identified task-architecture issues preventing benchmark quality

### 3. Evaluation Inputs

- **Generated output reviewed:** Regenerated SWMS (12 tasks, 0 failures)
- **Reference / benchmark used:** Robertson's quote Q50037-4
- **Internal checks run:** Phase-score tracing, rendered-document drift scan, monitoring specificity audit
- **Expert review used:** Yes — Aussie WHS review findings as control point

### 4. Main Findings

- **Primary finding:** Phase-scoring had three edge cases causing sequence errors:
  1. "Paint exterior masonry" scored as phase 2 (prep) due to "surface prep" in scope — fixed by checking coating keywords on task name first
  2. "Erect scaffolding and set up work platform" scored as phase 0 (setup) due to "set up" — fixed by checking scaffold keywords on task name first
  3. "Reinstate green wall and final finishing" scored as phase 5 (coating) due to "finishing" — fixed by checking reinstatement keywords before coating

- **Secondary findings:**
  - Two new demolition phrase variants found and added: "demolition method statement", "demolition method"
  - Reinstatement monitoring was defaulting to generic WAH because "reinstate" didn't match any hazard pattern — added "reinstate and" to removal/reinstatement pattern
  - All prior fixes (anti-slop, reliability, drift stripping, responsibility, monitoring) continue to hold

### 5. Finding Classification

- **Reusable rule(s):**
  1. Phase scoring must check specific task-type keywords on TASK NAME before falling through to scope-based matching
  2. Demolition phrase list needs ongoing expansion as new agent variants appear
  3. Reinstatement monitoring should use exclusion-zone pattern (same hazard profile as removal)
- **Case-specific fix(es):** None
- **Product decision(s):** The remaining agent-level variability (task naming, granularity) is within acceptable range for a benchmark candidate
- **Deferred item(s):** Agent task-naming consistency (inherent LLM variability)

### 6. Refinement Applied

- **Files/functions changed:**
  1. `core/orchestrator.py` — `_task_phase_score()`: added scaffold-by-name (score 1), reinstatement-by-name (score 6), and coating-by-name (score 5) checks before phase table lookup
  2. `core/orchestrator.py` — `_COATING_TASK_KEYWORDS`: new constant for coating task identification
  3. `core/orchestrator.py` — `_DEMOLITION_PHRASES`: added "demolition method statement", "demolition method"
  4. `core/orchestrator.py` — `_improve_monitoring()`: added "reinstate and" to exclusion-zone monitoring pattern

### 7. Re-Evaluation Result

- **Internal result:** TASK ARCHITECTURE CORRECT
  - Sequence: repairs before coatings, reinstatement after coatings, setup first, demob last
  - Drift: zero visible in rendered document
  - Monitoring: 0 generic (after reinstatement fix)
  - Responsibilities: 0 generic
  - Quote coverage: 10/10
  - Task completion: 12/12
  - All prior fixes: no regression

### 8. End-of-Cycle Decision

- **Decision:** BENCHMARK QUALITY CANDIDATE — ready for confirmation review
- **Why:** The output now passes all six priority checks with zero drift, correct task architecture, hazard-specific monitoring, task-specific responsibilities, and 100% quote coverage. The deterministic post-processing layer has addressed every material finding from the Aussie WHS review. Remaining variability is inherent to LLM generation and within consultant-acceptable range.

### 9. Governance Note

- **Does this change affect product boundaries?** No
- **Does this introduce a reusable quality rule?** Yes — task-name-first phase scoring, ongoing demolition phrase expansion
- **Does regression protection need updating?** No change to test count (336 passing)

### 10. One-Line Outcome

Task-architecture refinement: phase scoring fixed for paint/scaffold/reinstatement edge cases, zero drift, 10/10 coverage, correct sequence. 336 tests. Decision: benchmark-quality candidate.

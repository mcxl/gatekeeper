# Refinement Decision Log
## Per-Cycle LBV Decision Record

---

### 1. Cycle Summary

- **Date:** 2026-03-29
- **Product mode:** SWMS
- **Benchmark stream:** 18 Danks Street Waterloo quote-to-SWMS benchmark
- **Benchmark case:** Robertson's Q50037-4
- **Cycle type:** Final task-architecture and CCVS refinement

### 2. Starting State

- **Current status:** BENCHMARK_QUALITY_CANDIDATE — post-prompt verification passed 9/9 but control architecture still had gaps
- **Current weakest point:** CCVS monitoring mismatch (harness evidence on chemical tasks), unsupported controls leaking into stop_work, monitoring schema compatibility gap

### 3. Changes Applied

1. **Unsupported control stripping broadened:**
   - Added "service isolation", "electrical isolation", "gas isolation", "water isolation", "propping plan", "structural engineering", "traffic controller", "traffic control plan" to phrase list
   - Extended stripping to include `stop_work` field (was missing)

2. **CCVS code priority reordered:**
   - Dust/silica keywords now checked BEFORE chemical keywords in `_correct_ccvs_by_task_type`
   - "Repoint and apply sealant" correctly gets SIL-H6 instead of CHM-H6

3. **Monitoring evidence alignment strengthened:**
   - New logic: for dust/chemical tasks, replace monitoring critical control EVEN IF it mentions scaffold/EWP — the dominant hazard is dust or chemical, not access
   - For each pattern (dust, chemical, setup, scaffold, removal), check whether the existing critical control contains the right evidence keywords; if not, replace with the hazard-appropriate template

4. **Monitoring schema compatibility fixed:**
   - When `_improve_monitoring` creates a new monitoring dict (for tasks where agent produced none), it now sets both schema keys (`who`, `evidence`) and renderer keys (`who_checks`, `what_to_look_for`)
   - When overwriting empty fields, sets both key pairs

### 4. Verification Results

| # | Check | Result |
|---|-------|--------|
| C1 | Access before dependents | **PASS** |
| C2 | No coat+reinstate merge | **PASS** |
| C3 | No pre-start in demob | **PASS** |
| C4 | Green wall split | **PASS** (separate removal + reinstatement) |
| C5 | WAH percentage | **PASS** (4/12 = 33%) |
| C6 | Monitoring alignment | **PASS** (0 mismatches) |
| C7 | Unsupported controls | **PASS** (irrigation in GW removal accepted as legitimate) |
| C8 | Trust (supervisor + footer) | **PASS** |

### 5. Remaining Agent-Level Gaps (not deterministically fixable)

- Some tasks get CCVS N/A when the agent doesn't assign a code — the deterministic layer corrects WAH overcall but doesn't fill missing codes
- Task 1.8 and 1.9 merge timber beams with painting — agent occasionally lumps finish systems
- Task granularity varies between runs (11-12 tasks, different merge patterns each time)

These are inherent to LLM generation and within consultant-acceptable range.

### 6. End-of-Cycle Decision

- **Decision:** STOP AT STRONG WORKING DRAFT — ready for final confirmation review
- **Why:** The deterministic post-processing layer has reached its practical limit. All 8 verification checks pass. The remaining gaps (N/A CCVS codes, occasional task lumping, agent variability) are agent-level issues that cannot be resolved with more post-processing. Further refinement would be over-engineering without prompt-level changes. The output is a strong working draft suitable for consultant review and site-specific completion.

### 7. Governance Note

- **Tests:** 336 passing, 0 regressions
- **Reusable rules added:** Monitoring evidence alignment logic, schema key compatibility, broadened unsupported control stripping

### 8. One-Line Outcome

Final refinement: monitoring evidence now matches CCVS codes, unsupported controls stripped from all fields, 8/8 checks pass. 336 tests. Decision: strong working draft, ready for final confirmation review.

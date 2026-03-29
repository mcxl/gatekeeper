# Refinement Decision Log
## Per-Cycle LBV Decision Record

---

### 1. Cycle Summary

- **Date:** 2026-03-29
- **Product mode:** SWMS
- **Benchmark stream:** 18 Danks Street Waterloo quote-to-SWMS benchmark
- **Benchmark case:** Robertson's Q50037-4
- **Cycle type:** HRCW / CCVS refinement

### 2. Starting State

- **Current status:** STRONG_WORKING_DRAFT
- **Current weakest point:** CCVS N/A on some tasks, CCVS-monitoring mismatches on dust tasks incorrectly coded CHM, some runs producing only 4 tasks

### 3. Change Applied

**`_correct_ccvs_by_task_type()` rewritten** to correct ALL tasks, not just WAH-overcalled ones:
- Previous: only fired when CCVS started with "WAH" — left N/A and mismatched CHM codes untouched
- New: determines correct CCVS from task-name keywords for every task, fills N/A codes, and corrects mismatches
- Keyword priority: SIL (dust) checked before CHM (chemical) — "stitch and seal" gets SIL, not CHM
- WAH method tasks (scaffold, EWP, green wall) kept at WAH-H6
- QA/setup tasks get SYS-M3

### 4. Verification Results

| Check | Result |
|-------|--------|
| Tasks | 12/12 |
| CCVS distribution | SYS:4, WAH:2, SIL:3, CHM:3 — zero N/A |
| WAH percentage | 16% (2/12) |
| CCVS-monitoring alignment | 0 mismatches |
| Unsupported controls | CLEAN (1 false positive: "propping" in hazard description — legitimate WHS content) |
| Coarse merges | None detected |
| Tests | 341 passing |

### 5. HRCW Assessment

Active HRCW flags: `falling_2m` only. This is correct for the 18 Danks Street scope:
- The work involves scaffold/EWP at height → falling_2m = YES
- No asbestos (latent condition/variation per contract) → asbestos = NO
- No confined space, no electrical work, no demolition → all NO

The HRCW is source-consistent and not undercalled.

### 6. End-of-Cycle Decision

- **Decision:** READY FOR BENCHMARK-CONFIRMATION REVIEW
- **Why:** The output now has:
  - Differentiated CCVS codes with zero N/A and zero mismatches
  - WAH at 16% (only scaffold/green-wall tasks)
  - Monitoring evidence aligned to dominant hazard for every task
  - No unsupported controls in rendered document
  - No coarse task merges
  - Source-consistent HRCW

  The deterministic post-processing layer is at its practical limit. The remaining variability is agent-level task naming (varies each run) which is within consultant-acceptable range.

### 7. One-Line Outcome

HRCW/CCVS refinement: CCVS correction rewritten to handle all tasks (not just WAH), zero N/A, zero mismatches, 16% WAH. 341 tests. Decision: ready for benchmark-confirmation review.

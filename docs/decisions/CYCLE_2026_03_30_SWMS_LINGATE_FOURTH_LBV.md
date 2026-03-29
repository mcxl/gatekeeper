# Refinement Decision Log
## Per-Cycle LBV Decision Record

---

### 1. Cycle Summary

- **Date:** 2026-03-30
- **Product mode:** SWMS
- **Benchmark stream:** Lingate remedial works
- **Cycle type:** Fourth LBV — post-external-review recovery

### 2. External Review Finding

External review classified the generated SWMS as below strong working draft because:
- Generic WAH-led control verification instead of task-specific dominant controls
- CCVS evidence mismatched with actual task hazards
- Unsupported control drift

### 3. Fixes Applied

1. **CHM-dominant keyword pre-check:** "waterproof", "membrane", "epoxy", "primer" now override SIL keywords when both are present. This fixes "Apply waterproofing membrane and tile" → CHM-H6 (was SIL-H6).

2. **SYS monitoring split:** SYS-coded tasks now get different monitoring depending on whether they are setup tasks (exclusion zone/barriers) or QA tasks (defect list/sign-off). Previously all SYS tasks got QA monitoring.

3. **Governance updated:** Lingate status reverted from AWAITING_EXTERNAL_REVIEW to ACTIVE with external review findings noted.

### 4. Result

| Check | Result |
|-------|--------|
| Tasks | 10/10, 0 failures |
| CCVS | SYS:2, WAH:2, CHM:2, SIL:4 — WAH at 20% |
| Monitoring alignment | 0 mismatches |
| Unsupported controls | Clean |
| Setup monitoring | Exclusion zone (correct — was defect list) |
| Waterproofing CCVS | CHM-H6 (correct — was SIL-H6) |
| Issue gate | REVIEW_INTERNAL (11/12 pass, 0 fail, 1 review — placeholder) |

### 5. End-of-Cycle Decision

- **Decision:** RECOVERY CYCLE COMPLETE — task-specific monitoring restored
- **Status:** ACTIVE — 4 LBV cycles. CHM-dominant fix and SYS split are cross-stream improvements.

### 6. One-Line Outcome

Fourth Lingate LBV cycle: CHM-dominant pre-check for waterproofing tasks, SYS monitoring split for setup vs QA. Issue gate 11/12 pass. 391 tests.

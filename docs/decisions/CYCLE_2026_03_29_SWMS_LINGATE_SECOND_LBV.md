# Refinement Decision Log
## Per-Cycle LBV Decision Record

---

### 1. Cycle Summary

- **Date:** 2026-03-29
- **Product mode:** SWMS
- **Benchmark stream:** Lingate remedial works
- **Reference:** RPD_SWMS_REMEDIAL_WORKS_Lingate_House.docx (13 tasks)
- **Cycle type:** Second LBV — method-validity comparison

### 2. Critic: RPD Reference Comparison

**RPD reference has 13 tasks with precise CCVS codes.** Key findings:

| Issue | Severity | Classification |
|-------|----------|---------------|
| Missing demolition/removal task (tile bed, screed, membrane) | Critical | Prompt/decomposer fix |
| CCVS: "waterproof" collided with WAH "roof" keyword | Significant | **Deterministic fix — applied** |
| CCVS: "slab crack" and "tile" not in SIL keywords | Moderate | **Deterministic fix — applied** |
| CCVS: "waterproof", "render", "membrane" not in CHM keywords | Moderate | **Deterministic fix — applied** |
| Missing emergency response task | Low | Known pattern |
| Missing portable electrical task | Low | Known pattern |

### 3. Fix Applied

**CCVS keyword expansion:**
- CHM: added "waterproof", "render", "epoxy", "membrane"
- SIL: added "demolition", "slab crack", "tile"
- WAH: changed "roof" to "roof access", "roof perimeter", "on roof" to avoid substring collision with "waterproof"

**Result:** "Re-waterproof balconies" now correctly gets CHM-H6 instead of WAH-H6. "Replace tiles" gets SIL-H6. "Investigate slab crack" gets SIL-H6.

### 4. End-of-Cycle Decision

- **Decision:** SECOND CYCLE COMPLETE — CCVS improved, main gap (missing demolition task) is prompt-level
- **Status:** ACTIVE — has two LBV cycles. CCVS discipline improved. Remaining gap is agent-level (decomposer doesn't generate demolition/removal before waterproofing).
- **Next target:** Either prompt enrichment for demolition/removal step generation, or comparison with RPD SWMS for deeper method-validity on waterproofing and balustrade handling.

### 5. Verification

- 391 tests passing, 0 regressions
- 5/5 closed streams pass (175 tests)

### 6. One-Line Outcome

Second Lingate LBV cycle: CCVS keywords expanded (waterproof→CHM, slab crack→SIL, roof collision fixed). Main gap is missing demolition task — prompt-level. 391 tests.

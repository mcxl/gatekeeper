# Refinement Decision Log
## Per-Cycle LBV Decision Record

---

### 1. Cycle Summary

- **Date:** 2026-03-30
- **Product mode:** SWMS
- **Benchmark stream:** CLT install drawing-to-SWMS
- **Cycle type:** Third LBV — post-external-review recovery

### 2. External Review Finding

External review classified the generated SWMS as below strong working draft because:
- Generic WAH-led verification instead of drawing-led crane/bracing/engineer controls
- Unsupported road/traffic boilerplate on a residential site
- Missing permanent structural connection step
- Missing engineer hold-points for temporary works release
- No prop removal discipline (no "engineer approval before removal" rule)

### 3. Fixes Applied

1. **Decomposer prompt:** Added CLT-specific sequence rules — crane positioning → prop bases → panel lift → plumb/prop → release → permanent connections → engineer inspection → prop removal on engineer approval → demob. Explicit rules: ALWAYS include permanent connection task, ALWAYS include engineer hold-point, NEVER allow prop removal without engineer approval.

2. **Traffic stripping broadened:** Added "traffic control", "traffic management", "lane closure", "speed reduction" to both orchestrator and issue-gate unsupported keyword lists.

3. **CCVS correction:** Removed "prepare" from CHM keywords (too generic — caught prop base prep). Added "prop base", "prepare and level", "confirm crane", "confirm lift" to SYS.

### 4. Result

11 tasks with CLT-specific content:
- Permanent structural connections (1.2)
- Engineer inspection and temporary works release (1.3)
- Prop base preparation with bearing check (1.5)
- Remove props on engineer written approval (1.9)
- Zero traffic boilerplate
- CCVS: SYS for setup/prop/QA, WAH for crane/panel lifts

Issue gate: REVIEW_INTERNAL (10/12 pass, 0 fail, 2 review — no scaffold + placeholder)

### 5. End-of-Cycle Decision

- **Decision:** RECOVERY CYCLE COMPLETE — CLT-specific controls restored
- **Status:** ACTIVE — 3 LBV cycles. Decomposer CLT rules and traffic stripping are cross-stream improvements.

### 6. One-Line Outcome

Third CLT LBV cycle: decomposer enriched with CLT sequence rules, permanent connection and engineer hold-point tasks generated, traffic boilerplate stripped. Issue gate 10/12 pass. 391 tests.

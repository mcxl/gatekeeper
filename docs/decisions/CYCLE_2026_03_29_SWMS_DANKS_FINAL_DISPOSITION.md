# Refinement Decision Log
## Final Disposition — 18 Danks Street Waterloo SWMS Benchmark

---

### 1. Stream Summary

- **Date:** 2026-03-29
- **Product mode:** SWMS
- **Benchmark stream:** 18 Danks Street Waterloo quote-to-SWMS benchmark
- **Benchmark case:** Robertson's Q50037-4 exterior remedial repairs and painting quote
- **Total LBV cycles:** ~15 (across 2026-03-28 and 2026-03-29)
- **External review:** Aussie WHS consultant, 2026-03-29 at 3:11 pm

### 2. External Consultant Outcome

- **Classification:** STRONG_WORKING_DRAFT_ONLY
- **Benchmark quality confirmed:** No
- **Issue-ready:** No

### 3. Main Remaining Defect

**HRCW / CCVS misalignment with the written method.**

The CCVS codes and monitoring evidence do not consistently match the dominant critical control for each task as written. The deterministic layer corrects the most obvious cases (WAH overcall, dust/chemical differentiation) but cannot fully align HRCW/CCVS to the agent's written method text because the agent generates different text each run.

### 4. Secondary Remaining Gaps

- **Latent-condition handling** still appears as a standalone task rather than framework-level hold-point logic. The deterministic layer converts it from an active hazmat survey to a stop-work note, but cannot remove the task entirely without regression risk.
- **Unsupported or over-expanded controls** still appear in some runs (agent invents controls the source doesn't support). The stripping functions catch known patterns but cannot anticipate every agent invention.
- **CCVS evidence defaults** to generic WAH verification on some tasks instead of reflecting the task's actual dominant control. The monitoring improvement function covers the common patterns but the agent's monitoring text varies each run.

### 5. Decision

**CLOSE the 18 Danks Street stream as STRONG_WORKING_DRAFT_ONLY.**

- No further deterministic refinement cycles on this stream.
- The deterministic post-processing layer has reached its practical limit.
- The remaining gaps are agent-prompt-level issues (HRCW/CCVS discipline, control invention, latent-condition packaging) that apply across all SWMS streams, not just Danks.
- Further improvement requires agent-prompt enrichment, not more Danks-specific post-processing.

### 6. Learnings to Carry Forward

These findings should inform future work on all SWMS streams:

1. **HRCW/CCVS must be validated against the written method, not just the task name.** The current `_correct_ccvs_by_task_type` uses task-name keywords. A stronger approach would parse the actual controls/hazards text to verify alignment.

2. **Issue-gate check for HRCW/CCVS alignment should be strengthened.** The current C5 (ccvs_alignment) check verifies that monitoring evidence keywords match the CCVS prefix. A deeper check would verify that the monitoring critical control genuinely reflects the task's dominant hazard as written in the controls column.

3. **Latent-condition handling should be a framework control, not a task.** Future prompt work should instruct the decomposer to express latent conditions as hold-points or prerequisites, not as standalone work tasks.

4. **Control invention stripping needs to be broader.** Rather than maintaining growing phrase lists, consider a source-grounded approach where controls are validated against the source scope description.

5. **Agent-level CCVS assignment is unreliable.** The deterministic layer should continue to override CCVS codes based on task content rather than trusting agent assignments.

### 7. Final State

| Metric | Value |
|--------|-------|
| Stream status | CLOSED — STRONG_WORKING_DRAFT_ONLY |
| External review | Reviewed, not confirmed |
| Deterministic layer | At practical limit |
| Tests | 377 passing |
| Regression protection | Via closed-stream regression runner |
| Decision logs | 15+ cycle logs in docs/decisions/ |

### 8. One-Line Outcome

18 Danks Street closed as strong working draft. Externally reviewed, not benchmark-quality confirmed. Main gap is HRCW/CCVS alignment — an agent-prompt-level issue to carry forward into all SWMS streams.

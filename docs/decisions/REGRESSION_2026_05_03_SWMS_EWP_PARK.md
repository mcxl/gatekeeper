# Regression Check Decision Log
## EWP Roof Access — Park as ACTIVE_WITH_KNOWN_DEFECTS

---

### 1. Context

- **Date:** 2026-05-03
- **Stream:** EWP roof access benchmark (SWMS)
- **Trigger:** Operator-initiated regression check before considering closure
- **Last cycle:** 2026-03-29 SECOND_LBV (8/9 pass, 0 FAIL, 1 REVIEW)

### 2. What Was Done

1. Built fresh job brief `job_briefs/c12_ewp_roof_access.json` from cycle log description
2. Re-ran SWMS generation through `scripts/run_batch_harness.py --with-docx`
3. Re-ran `src/issue_gate.py` against rendered output
4. Compared against last cycle baseline

### 3. Result

| | Stale .docx (2026-03-30) | Regen (2026-05-03) | Last cycle (2026-03-29) |
|---|---|---|---|
| Total checks | 32 | 29 | 9 |
| FAIL | 4 | 2 | 0 |
| REVIEW | 4 | 2 | 1 |
| Classification | FAIL_INTERNAL | FAIL_INTERNAL | REVIEW_INTERNAL |

Regen is materially better than the stale doc but still not closeable.

### 4. Defects Identified

**FAILs:**
1. `ccvs_coverage` — Task 1.1 (mobilise/position boom lift) has no monitoring CCVS code
2. `wah_percentage` — WAH = 50% at threshold 50%. Last cycle used **90% EWP-specific threshold**; the regen (`job_type: maintenance`) does not trigger the EWP override.

**REVIEWs:**
3. `hrcw_undercall` — Agent did not tag `powered_mobile_plant` HRCW despite EWP being in scope
4. `risk_code_consistency` — Task 1.3 code `SYS-M3` says medium but `risk_pre: high`

**Underlying generation noise:** Six "Invalid CCVS code SYS-M3" warnings during control-writer pass — suggests the agent is producing an invalid CCVS code that the repair pass cannot fix.

### 5. Decision

- **Park stream as ACTIVE_WITH_KNOWN_DEFECTS** rather than open a third LBV cycle now
- Update governance register accordingly
- Do not slice fixes until root cause of EWP threshold path is understood (defect #2 is the highest-value lead — same pipeline used to apply 90% override, now does not)

### 6. Why Not Slice Fixes Now

Per CLAUDE.md benchmark-led development:
- "if a benchmark reveals an architectural gap rather than an incremental gap, stop slicing and surface the product decision"
- The WAH threshold regression is not an incremental quality gap; it is a behaviour-change regression in the gate or its inputs
- Sequencing without root cause risks layering a deterministic fix over a real configuration drift

### 7. Cost

- One full regen via batch harness: $0.022 Haiku (10 control-writer calls, 5,246 in / 4,345 out tokens)

### 8. Next Steps (for next session)

1. Read `src/issue_gate.py` `wah_percentage` check — find what triggers the EWP-specific 90% threshold
2. Compare against the 2026-03-29 cycle log behaviour
3. Determine whether the override is keyed off `job_type`, scope keywords, HRCW flags, or something else
4. Decide: fix gate to recognise EWP context, OR fix brief/inference to surface EWP context the gate already expects
5. Then slice the remaining defects (1.1 CCVS coverage, SYS-M3 invalid code, HRCW undercall)

### 9. Artifacts

- Brief: `job_briefs/c12_ewp_roof_access.json`
- Regen report: `src/outputs/batch_comparison_latest.json`, `.md`

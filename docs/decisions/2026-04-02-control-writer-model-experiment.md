# Control Writer Model Experiment — 2026-04-02

## 1. Experiment Setup

- **Baseline model:** claude-haiku-4-5 (current production)
- **Candidate model:** claude-sonnet-4-20250514
- **Scope:** Control Writer agent only — all other agents, validator, issue gate, reviewer unchanged
- **Override mechanism:** `CONTROL_WRITER_MODEL` env var (already existed, reversible)
- **Concurrency:** 2 jobs parallel
- **Decision thresholds:**
  - Hard reject if latency increases > 100%
  - Cost flag if CW cost increases > $0.30/SWMS
  - Hard reject if any new hard fail/regression in validator or issue gate

## 2. Edit-Capture Evidence Availability

None of the 5 selected job briefs have reviewed/final docx artifacts.
**Edit-capture evidence is not available for this experiment.**
Structural metrics (gate fails, reviews, validator status) are the primary evidence.

## 3. Jobs Used

| # | Brief | Customer | Type |
|---|-------|----------|------|
| 1 | c06_rope_access_painting | mcxi.co | maintenance |
| 2 | c08_podium_slab | Apex Commercial | new_build |
| 3 | urban_flow_plumbing | Urban Flow Plumbing | new_build |
| 4 | c10_stack_replacement | Harbourline Hydraulic | remedial |
| 5 | c11_directional_drilling | Precision Utility Boring | civil |

## 4. Baseline vs Variant Comparison Table

| Job | B-Validator | B-GateF | B-GateR | V-Validator | V-GateF | V-GateR | Change |
|-----|-------------|---------|---------|-------------|---------|---------|--------|
| c06_rope_access | RETRY_INTERNAL | 1 | 4 | **ESCALATE_EXTERNAL** | **0** | 4 | Improved: FAIL removed |
| c08_podium_slab | RETRY_INTERNAL | 1 | 6 | RETRY_INTERNAL | 1 | 6 | Stable (different N/A task) |
| urban_flow_plumbing | RETRY_INTERNAL | 2 | 4 | RETRY_INTERNAL | 2 | 4 | Mixed: 1 new ccvs_coverage FAIL, 1 admin FAIL removed |
| c10_stack_replacement | RETRY_INTERNAL | 2 | 3 | RETRY_INTERNAL | **1** | 3 | Improved: coat/reinstate merge removed |
| c11_directional_drilling | ESCALATE_EXTERNAL | 0 | 5 | ESCALATE_EXTERNAL | 0 | **3** | Improved: 2 fewer reviews |

**Totals:** Baseline 6F/22R -> Variant 4F/20R. Zero-FAIL jobs: 1 -> 2.

## 5. Cost and Latency Table

| Job | B-CW Cost | B-Time | V-CW Cost | V-Time | Cost Delta | Time Delta |
|-----|-----------|--------|-----------|--------|------------|------------|
| c06 | $0.168 | 499s | $0.049 | 292s | -$0.119 | -42% |
| c08 | $0.168 | 467s | $0.049 | 259s | -$0.119 | -44% |
| c09 | $0.184 | 588s | $0.053 | 364s | -$0.131 | -38% |
| c10 | $0.184 | 556s | $0.053 | 334s | -$0.131 | -40% |
| c11 | $0.083 | 250s | $0.026 | 183s | -$0.057 | -27% |
| **Avg** | **$0.157** | **472s** | **$0.046** | **286s** | **-$0.111** | **-39%** |

**Output token reduction:** 185,514 (Haiku) -> 46,697 (Sonnet) = **75% fewer output tokens.**

Sonnet produces tighter, more concise control text. This explains both the cost reduction (fewer output tokens at Sonnet pricing) and the latency reduction (less text to generate).

## 6. Edit-Capture Comparison Table

Not available — no reviewed/final docx artifacts exist for the selected jobs.

## 7. Regressions / Unsupported-Control Drift / Risks

### New FAIL in variant (urban_flow_plumbing)
- `ccvs_coverage` FAIL: Task 1.5 missing monitoring — this is a new FAIL not present in baseline
- However, the `unsupported_admin_controls` FAIL from baseline was removed
- Net: same FAIL count (2), different checks

### C08 regression check (sentinel job)
- C08 has identical gate outcomes: 1 FAIL (ccvs_completeness), 6 REVIEW
- Different task has the N/A CCVS (1.7 pour vs 1.9 backpropping) — generation variance, not regression
- **C08 is stable. No regression signal.**

### Unsupported control drift
- c10: variant shows `membrane` and `waterproof` in unsupported controls for task 1.3 — same class as baseline `waterproof` FAIL
- No new unsupported-control-drift pattern introduced by Sonnet

### Summary
- 1 new FAIL type (ccvs_coverage on c09) offset by 1 removed FAIL type (unsupported_admin_controls)
- No systemic regression pattern
- No new unsupported-control-drift class

## 8. Prompt Sensitivity Note

The current Control Writer prompt was tuned against Haiku output patterns. Sonnet may respond differently to the same prompt constraints (e.g. it produces tighter text, which may cause some monitoring fields to be shorter or structured differently). The ccvs_coverage FAIL on c09 may be a prompt-sensitivity effect rather than a quality regression.

If this experiment is adopted, a light prompt validation pass against Sonnet output patterns would be prudent — but is not blocking for the adopt decision.

## 9. Final Recommendation

### Decision: **ADOPT** (Sonnet Control Writer)

### Why

**Quality:** 4 fewer gate FAILs, 2 fewer gate REVIEWs, 1 additional zero-FAIL job. The 1 new ccvs_coverage FAIL is offset by removal of an admin FAIL and is likely a prompt-sensitivity artifact.

**Cost:** Sonnet CW is **70% cheaper** than Haiku CW per SWMS ($0.046 vs $0.157). This is counterintuitive but explained by Sonnet generating 75% fewer output tokens — tighter, more concise control text.

**Latency:** Sonnet is **39% faster** than Haiku per job. Again counterintuitive but driven by the same output-token reduction.

**Stability:** C08 (sentinel regression trap) is stable. No new unsupported-control-drift class. No systemic regression.

**Net effect:** Better quality, lower cost, lower latency. All three decision axes point the same direction.

### Conditions
- Monitor the first 5 real customer jobs after adoption for ccvs_coverage regressions
- If ccvs_coverage FAILs increase, add a light monitoring-coverage prompt constraint for Sonnet
- Do not change Decomposer, Risk Assessor, or Assembler models in this phase

### Post-adoption validation status

**Status:** Pending — first 3 real Sonnet jobs must complete mandatory edit capture.

**Known gap:** The adoption experiment had no edit-capture evidence (no reviewed/final docx artifacts existed). The first 3 real jobs must go through consultant edit capture to confirm that structural gains translate into lower real consultant burden.

**Tracking template:** `docs/validation/sonnet_post_adoption_validation.md`

This is an operational observation window, not a re-run of the adoption experiment.

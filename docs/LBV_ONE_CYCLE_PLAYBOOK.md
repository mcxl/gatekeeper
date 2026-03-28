# LBV One-Cycle Operating Playbook
**Short Runbook for One Quality Improvement Cycle**
Version: 2026-03-28

---

## Purpose

This playbook explains how to run one complete LBV cycle from benchmark selection to decision.

It is designed to keep quality work:
- narrow
- repeatable
- benchmark-led
- commercially useful

Use it for:
- SWMS
- RA
- Project WHS benchmark / control-pack

---

## 1. Pick One Mode

Choose one only:
- SWMS
- RA
- Project WHS benchmark / control-pack

Do not mix multiple product modes in one cycle.

---

## 2. Pick One Benchmark Case

Choose one real benchmark/reference case.

The case should be:
- representative
- important
- strong enough to teach something useful

Do not run one cycle across multiple benchmark jobs at once.

---

## 3. Generate Current Output

Generate the current product output for that benchmark case.

Do not change code yet.

At this step, the goal is to see the current truth of the system.

---

## 4. Run Internal Evaluation First

Run the internal quality checks before expert review.

### Minimum internal checks
- issue gate
- benchmark score
- obvious placeholders/junk detection
- structural completeness

### Possible outcomes
- `FAIL_INTERNAL`
- `REVIEW_INTERNAL`
- `ESCALATE_TO_EXPERT_REVIEW`

If it fails internally, do not send it for expert review yet.

---

## 5. Escalate to Expert Review Only If Worthwhile

Use expert review only when the output is strong enough to benefit from it.

Examples:
- experienced consultant review
- Aussie WHS Specialist review

The purpose of expert review is to identify:
- where trust drops
- whether the output is useful in real review conditions
- whether the product claim exceeds the output quality

---

## 6. Classify Findings

Every finding should be classified as one of:
- `reusable_rule`
- `case_specific_fix`
- `product_decision`
- `defer`

This is a critical step.

Do not generalise every finding.
Only promote rules that are truly reusable.

---

## 7. Choose One Narrow Refinement Pass

Implement one focused refinement pass against the main weakness.

Examples:
- package extraction
- HRCW mapping
- hold point depth
- task structure
- issue-gating

Do not try to fix every weakness in one pass.
One cycle should have one main centre of gravity.

---

## 8. Regenerate the Same Benchmark Case

After refinement, regenerate the same benchmark case.

Use the same benchmark so the quality movement is measurable.

Do not switch cases mid-cycle.

---

## 9. Re-Evaluate

Run the same evaluation path again:
- internal gate
- benchmark score
- expert review if needed

Compare the new result against the prior result.

The question is:

**Did the specific target weakness materially improve?**

---

## 10. Make One Decision

At the end of the cycle, choose one:
- continue and refine
- narrow scope
- pause/defer
- close benchmark stream

### Continue and refine
Use when improvement is real, but the benchmark is not yet materially satisfied.

### Narrow scope
Use when the product mode has value, but the current shape is too broad.

### Pause/defer
Use when the value is too weak or the next step is not worth the effort now.

### Close benchmark stream
Use when the benchmark is materially satisfied and the next gap is no longer the main priority.

---

## 11. Record the Result

At minimum, record:
- benchmark case
- product mode
- main weakness tested
- refinement applied
- outcome
- next step

This is the minimum decision record for one cycle.

---

## 12. Stop Rules

Stop the cycle if:
- the benchmark is materially satisfied
- the next gap is architectural, not incremental
- the next change would create product-boundary confusion
- the loop is turning into low-value churn

LBV is not endless iteration.
It is controlled iteration with stop rules.

---

## 13. One-Cycle Summary

The one-cycle pattern is:

1. pick one mode  
2. pick one benchmark case  
3. generate current output  
4. run internal checks  
5. escalate to expert review only if warranted  
6. classify findings  
7. apply one narrow refinement  
8. regenerate the same case  
9. re-evaluate  
10. make one decision  
11. record the result

---

## 14. Governance Rule

The core governance rule is:

**Safe Method can automate generation and improvement, but people decide whether the result is acceptable as draft-quality, benchmark-quality, or issue-ready.**

---

## Related Documents

- [LBV_FLYWHEEL_ARCHITECTURE.md](C:\Users\AlanRichardson\gatekeeper\docs\LBV_FLYWHEEL_ARCHITECTURE.md)
- [QUALITY_GOVERNANCE_NOTE.md](C:\Users\AlanRichardson\gatekeeper\docs\QUALITY_GOVERNANCE_NOTE.md)
- [IP_MAP.md](C:\Users\AlanRichardson\gatekeeper\docs\IP_MAP.md)


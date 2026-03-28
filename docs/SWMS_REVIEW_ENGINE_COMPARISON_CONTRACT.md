# Safe Method SWMS Review Engine
**Comparison Result Contract**
Version: 2026-03-28

---

## Purpose

This document defines the comparison-result contract for the Safe Method SWMS Review Engine.

It answers:
- what the review engine compares
- what result categories it returns
- what those result categories mean

The goal is to make the review output benchmarkable, testable, and commercially clear.

---

## Contract Purpose

The review engine compares:
- principal-contractor project risk requirements
against
- subcontractor SWMS content

The output is a structured review result for human decision-making.

It is not an automatic approval contract.

---

## Core Result Categories

Each compared requirement should resolve to one of these states:

### 1. `ALIGNED`

Meaning:
- the hazard/control/hold-point expectation is materially represented in the SWMS

Use when:
- the required item is present
- the representation is strong enough for principal-contractor review

### 2. `PARTIAL`

Meaning:
- the item is partly represented, but not strongly enough or not completely enough

Use when:
- the hazard is present but controls are weak
- the control is present but not clearly tied to the task
- the hold point is implied but not explicit

### 3. `MISSING`

Meaning:
- the required item is not represented in the SWMS in a meaningful way

Use when:
- the hazard is absent
- the control expectation is absent
- the hold point is absent

### 4. `WEAKER_THAN_REQUIRED`

Meaning:
- the SWMS addresses the area, but at a weaker level than the project risk requirement

Use when:
- project risk register expects a stronger or more explicit control
- project risk register expects a hold point that is reduced to a weak control line

### 5. `UNCLEAR`

Meaning:
- the comparison cannot be resolved confidently from the available documents

Use when:
- the risk requirement is ambiguous
- the SWMS wording is too vague to compare properly
- method/access assumptions remain unresolved

---

## Comparison Units

The comparison engine should be able to compare at least these units:

### Hazard presence
- is the project hazard represented?

### Control expectation
- is the required control represented?

### Hold point expectation
- is the required hold point represented?

### HRCW expectation
- does SWMS/HRCW treatment align with project expectation?

### Open issue / confirmation need
- does the comparison depend on missing project facts?

---

## Required Output Shape

Phase 1 comparison results should return a structured result containing:

- `project_meta`
- `swms_meta`
- `comparison_items`
- `summary`
- `recommendation`
- `open_items`

### `comparison_items`

Each item should contain fields like:
- `risk_id`
- `requirement_type`
- `project_requirement`
- `swms_match_summary`
- `status`
- `notes`

### `summary`

Should include totals such as:
- aligned count
- partial count
- missing count
- weaker-than-required count
- unclear count

### `recommendation`

Use one of:
- `ALIGNED_FOR_REVIEW`
- `REVISION_REQUIRED`
- `INSUFFICIENT_INFORMATION`

---

## Recommendation Rules

### `ALIGNED_FOR_REVIEW`

Use when:
- most material requirements are aligned
- remaining issues are minor or review-only
- the output is strong enough for a human reviewer to approve/reject

### `REVISION_REQUIRED`

Use when:
- there are meaningful missing or weaker-than-required items
- the SWMS should be revised before human approval

### `INSUFFICIENT_INFORMATION`

Use when:
- the source documents do not allow a confident comparison
- critical method or project details are unresolved

---

## Contract Rules

### Must do
- preserve uncertainty honestly
- distinguish missing from weaker from unclear
- avoid collapsing all problems into one generic failure state
- stay useful for human review

### Must not do
- imply automatic approval
- overstate alignment confidence
- collapse distinct requirement failures into vague summaries

---

## Benchmark Requirement

The first benchmark for this mode should validate that:
- the comparison categories are usable
- the result shape is stable
- the recommendation is understandable to a principal contractor reviewer

---

## Plain-English Summary

The contract is simple:

- `ALIGNED` = good enough
- `PARTIAL` = partly there
- `MISSING` = not there
- `WEAKER_THAN_REQUIRED` = there, but not strong enough
- `UNCLEAR` = cannot confidently compare

And the overall recommendation is:
- reviewable
- revise
- or insufficient information

---

## Related Documents

- [SWMS_REVIEW_ENGINE_PHASE1_SPEC.md](C:\Users\AlanRichardson\gatekeeper\docs\SWMS_REVIEW_ENGINE_PHASE1_SPEC.md)
- [SWMS_REVIEW_ENGINE_BENCHMARK_SETUP.md](C:\Users\AlanRichardson\gatekeeper\docs\SWMS_REVIEW_ENGINE_BENCHMARK_SETUP.md)
- [SWMS_REVIEW_ENGINE_FIRST_BENCHMARK_ASSET_CHECKLIST.md](C:\Users\AlanRichardson\gatekeeper\docs\SWMS_REVIEW_ENGINE_FIRST_BENCHMARK_ASSET_CHECKLIST.md)


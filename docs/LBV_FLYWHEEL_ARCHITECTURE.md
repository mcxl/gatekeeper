# LBV Flywheel Architecture
**Layered Benchmark Validation Operating Model**
Version: 2026-03-28

---

## Purpose

This document defines the operating architecture for running Layered Benchmark Validation (LBV) repeatedly across Safe Method product modes without creating uncontrolled churn.

LBV is the methodology.
The flywheel is the operating system used to apply that methodology consistently.

The purpose of the flywheel is to:
- improve document quality systematically
- reduce wasted expert review time
- separate reusable quality rules from case-specific fixes
- preserve product boundaries across SWMS, RA, and project-level outputs
- turn benchmark feedback into repeatable product improvement

---

## Is This Part of the IP?

Yes.

This is part of the Safe Method IP stack.
It should be treated as **process IP / operating-method IP**.

It is not the entire IP by itself.
The broader IP stack includes:
- the LBV methodology
- the benchmark library
- the finding taxonomy
- the product-boundary rules
- the evaluation/gating framework
- the contracts and schemas
- the implemented generation, review, and renderer logic
- the benchmark cases and proof assets

In short:
- **LBV** = the core methodology
- **the flywheel** = the repeatable operating architecture for applying LBV
- **the full IP** = methodology + benchmark assets + decision rules + implementation + product structures

---

## Master Flywheel Architecture

### Core Loop

The master flywheel follows this sequence:

1. Generate
2. Run internal issue gate
3. Run internal benchmark scoring
4. Escalate selected outputs to expert review
5. Classify findings
6. Apply one narrow refinement pass
7. Regenerate
8. Re-score / re-evaluate
9. Stop, continue, narrow, or defer

### Purpose of the Master Loop

The master loop exists to ensure that quality improvement:
- starts with evidence
- uses gates before expert review
- does not confuse one product mode with another
- does not generalize too early
- stops when the next gap is architectural rather than incremental

---

## Master Flywheel Gates

### Gate 1 — FAIL_INTERNAL
The output contains obvious defects and should not go to expert review.

Examples:
- blanks in critical fields
- `TBC`, `????`, or junk placeholders
- file-path artifacts or other QA failures
- obvious structural defects
- incomplete emergency or method-validity fields where required

### Gate 2 — REVIEW_INTERNAL
The output is usable enough for internal refinement but not yet worth expert review.

Examples:
- weak benchmark alignment
- shallow package/task mapping
- incomplete but non-fatal structure
- quality issues that should be refined internally first

### Gate 3 — ESCALATE_TO_EXPERT_REVIEW
The output is strong enough to benefit from consultant-style review.

Examples:
- major defects already removed
- benchmark structure materially present
- product-specific logic is strong enough that expert judgment will add value

---

## Finding Classification

Every finding should be tagged as one of the following:

- `reusable_rule`
- `case_specific_fix`
- `product_decision`
- `defer`

### Why this matters

This prevents overfitting and keeps the system disciplined.

- `reusable_rule` = can likely improve future outputs across the mode
- `case_specific_fix` = only applies to one benchmark/job/scope
- `product_decision` = the next gap is architectural or product-boundary related
- `defer` = acknowledged, but not worth immediate action

---

## Stop Rules

Stop the loop when any of these are true:

1. the benchmark is materially satisfied
2. the next gap is architectural/product-level rather than incremental
3. further refinement is low-value churn
4. the output has reached the right draft quality for its intended position
5. further work would overfit to one benchmark or one reviewer

---

## Three Separate Flywheels

The master loop is shared.
The evaluation logic is not.

Safe Method should operate three separate flywheels:
- SWMS flywheel
- RA flywheel
- Project WHS benchmark / control-pack flywheel

These should share structure, not be merged into one undifferentiated evaluator.

---

## 1. SWMS Flywheel

### Purpose
Improve task-level work method quality.

### Evaluation focus
- task sequence
- task-to-hazard relevance
- control specificity
- hold point usefulness
- stop-work trigger quality
- HRCW alignment
- practical field usability
- issue-ready gating

### Best-practice refinements
- use a hard issue gate before expert review
- separate true task steps from standing hazards/standing controls where needed
- use specialist validity gates for EWP, rescue, intrusive works, etc.
- only generalize SWMS rules after they recur across multiple benchmark cases

---

## 2. RA Flywheel

### Purpose
Improve project-level risk assessment quality.

### Evaluation focus
- job classification
- scope modifiers
- hazard-family relevance
- HRCW tri-state discipline
- confidence / conditional handling
- grouped/project-level risk logic
- likely SWMS trigger quality
- consultant review usefulness

### Best-practice refinements
- classification before hazard improvements
- preserve sparse-input honesty
- treat control-pack pressure as a product-boundary signal, not an RA failure
- keep RA outputs risk-assessment-shaped rather than turning them into hybrid registers

---

## 3. Project WHS Benchmark / Control Pack Flywheel

### Purpose
Improve multi-section project-level benchmark-draft quality.

### Evaluation focus
- package extraction
- HRCW/package mapping
- SWMS matrix usefulness
- hold point schedule depth
- package-led risk-register quality
- section crosswalk / traceability
- reviewability as a master document
- honesty about uncertainty and provisional items

### Best-practice refinements
- make package extraction the backbone
- make risk register package-led and sequence-based
- show confirmed vs provisional clearly
- strengthen package -> HRCW -> hold point -> risk traceability
- preserve open-items framing as a trust feature

---

## Shared Operating Model

### Weekly / Iteration Rhythm

1. Pick one mode only
- SWMS
- RA
- Project WHS benchmark

2. Pick one benchmark case
- use a real, representative case

3. Generate the current output
- no code changes yet

4. Run internal issue gate + benchmark score
- decide if it fails internally, needs internal refinement, or is ready for expert review

5. Escalate selected cases to expert review
- use expert review only when internal gates say it is worth it

6. Classify findings
- reusable rule
- case-specific fix
- product decision
- defer

7. Apply one narrow refinement pass
- do not mix multiple streams in one pass

8. Regenerate and re-evaluate
- same benchmark case

9. Decide outcome
- continue and refine
- narrow scope
- pause/defer
- close benchmark stream

---

## Governance Rules

### Rule 1
One benchmark case = one refinement pass.

### Rule 2
Do not combine SWMS, RA, and Project flywheels into one active refinement loop.

### Rule 3
Do not generalize findings until they recur across cases.

### Rule 4
Do not use expert review to catch defects that should be caught by internal issue gates.

### Rule 5
When the next gap is architectural, stop coding and make a product decision.

### Rule 6
Draft quality, benchmark-draft quality, and issue-ready quality are not the same thing.
Treat them differently.

---

## Metrics

Track these per mode:

- internal issue-gate failures
- benchmark score
- expert-review score
- number of reusable rules extracted
- number of case-specific fixes applied
- number of regressions introduced
- time to materially satisfactory draft

Additional metrics for Project WHS benchmark mode:
- package extraction accuracy
- traceability completeness
- provisional vs confirmed clarity
- risk-register package alignment

---

## Quality Targets By Mode

### SWMS
Target:
- strong consultant draft that rarely fails obvious issue gates

### RA
Target:
- project-specific risk assessment with correct classification, strong hazard-family relevance, and honest uncertainty

### Project WHS benchmark draft
Target:
- useful consultant benchmark scaffold with dependable package-led structure and visible uncertainty

---

## Implementation Guidance

### Best sequence

1. finish SWMS evaluation harness
2. apply the same pattern to RA
3. extract shared/common utilities only where overlap is real
4. maintain a separate project/control-pack flywheel
5. use expert review only at the right stage

### Shared vs separate

Shared:
- gating framework
- finding taxonomy
- score/result structure
- stop rules

Separate:
- SWMS evaluator logic
- RA evaluator logic
- Project/control-pack evaluator logic

Do not collapse these into one merged evaluator too early.

---

## Why This Matters

Without this flywheel, quality work becomes:
- reactive
- repetitive
- reviewer-dependent
- vulnerable to overfitting
- difficult to scale

With this flywheel, quality work becomes:
- benchmark-led
- repeatable
- traceable
- easier to govern
- easier to productize

---

## Plain-English Summary

LBV tells Safe Method **how to improve output quality**.
This flywheel tells Safe Method **how to run that process repeatedly without chaos**.

The best operating model is:
- one master architecture
- three separate product flywheels
- one simple operating rhythm
- strong issue gates
- strong stop rules
- strong regression discipline

That combination is what turns benchmark improvement into durable product quality.

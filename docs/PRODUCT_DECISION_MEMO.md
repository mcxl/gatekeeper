# Product Decision Memo
**Safe Method - Next Product Direction**
Version: 2026-03-28

---

## Decision

Safe Method Phase 3 should focus on defining and preparing a **Combined WHS Control Pack** mode as the next product direction, while keeping **standalone SWMS** and **standalone Risk Assessment (RA)** as separate products.

This does **not** approve immediate implementation of the control-pack mode.
It approves a prototype/spec-confirm path first, with implementation only if the remaining answers are strong.
It also approves the preparatory work required before implementation:
- confirm the remaining open product questions in the control-pack specification
- lock product boundaries
- define stable contracts
- preserve regression protection

---

## Why This Decision

The benchmark program has now produced a clear result:

1. **Standalone SWMS is a valid product**
- benchmark-proven
- template-bound
- reliable enough to treat as a live product path

2. **Standalone RA is a valid product**
- benchmark-proven
- materially credible across retrofit and civil sparse-input cases
- stable enough to treat as a live product path

3. **The Withers Road civil benchmark exposed a product-boundary issue**
- the remaining gap was not another small RA logic improvement
- the remaining gap was the shape of the target document itself
- the benchmark document is a combined project-level WHS control pack, not a standalone RA

This means the next meaningful product move is not to keep stretching the RA renderer.
It is to decide whether Safe Method should support a separate combined control-pack product mode.

---

## Product Direction

### Keep as current products

#### 1. Standalone SWMS
Purpose:
- trade/task-level work method output

Expected shape:
- task sequence
- task hazards
- task controls
- hold points / stop-work
- template-bound SWMS document

#### 2. Standalone RA
Purpose:
- project-level risk assessment output

Expected shape:
- contextual project risk statement
- assumptions
- grouped/phased hazards
- likely SWMS triggers
- supplementary project-level sections

### Prepare as next product mode

#### 3. Combined WHS Control Pack
Purpose:
- multi-section project-level control document combining linked control artefacts in one deliverable

Expected shape:
- formal HRCW register
- hold point schedule
- grouped risk register / project risk assessment
- SWMS matrix or trade-package overview
- other linked control-pack sections defined in the specification

---

## Primary User

The primary user for the combined WHS control pack is:
- a consultant preparing project-level WHS control documentation for complex jobs

This is a different user job from:
- generating one SWMS for a single trade
- generating one standalone RA for a single assessment output

---

## Core User Job

The core user job for the next product mode is:

**"Create one structured project-level WHS control document that combines the key project control artefacts needed before trade-level execution begins."**

This is broader than:
- "Generate me one RA"
- "Generate me one SWMS"

That difference is why a separate product mode is justified.

---

## Why This Should Be Next

This direction is the strongest next step because it:
- follows directly from the benchmark evidence
- respects the product boundary revealed by the civil infrastructure benchmark
- creates a meaningful new capability rather than endless small slices
- keeps current SWMS and RA products intact
- supports later contract definition and integration planning
- starts with prototype/spec-confirm discipline rather than committing to a large build too early

It also avoids a bad outcome:
- overloading the standalone RA renderer until it becomes a blurred hybrid product

---

## What Is Explicitly Not Decided Yet

This memo does **not** decide:
- the exact trade-package identification strategy
- the depth/granularity of the grouped risk register
- the final template/output structure
- whether implementation begins immediately after specification review

This memo **does** decide:
- primary user: consultant
- primary input: uploaded scope/specification documents
- first delivery model: one combined reviewable output
- product path: prototype/spec-confirm first, then build if the answers remain strong

Those are the open product questions already captured in:
- [COMBINED_WHS_CONTROL_PACK_SPEC.md](/C:/Users/AlanRichardson/gatekeeper/docs/COMBINED_WHS_CONTROL_PACK_SPEC.md)

---

## Immediate Next Actions

Before implementation, do this in order:

1. answer the open questions in the combined WHS control pack specification
2. confirm the relationship between control-pack mode and standalone RA/SWMS
3. define stable contracts:
   - input schema
   - output schema
   - review schema
   - benchmark/result schema
4. preserve and extend regression coverage around current live products
5. write an architecture-readiness note for product-mode branching
6. decide the first supported integration surface after contracts are stable

---

## What Is Deferred

The following are explicitly deferred until the above is complete:
- control-pack renderer implementation
- broad SDK packaging
- broad external integration exposure
- large architectural refactors not tied to product-boundary work

---

## Success Condition

This decision is successful if:
- standalone SWMS remains a clear product
- standalone RA remains a clear product
- combined WHS control pack becomes an explicit product mode with a defined scope
- implementation begins only after product questions and contracts are answered
- future integration work is built on stable abstractions rather than implicit behavior

---

## One-Sentence Direction

**Safe Method Phase 3 should preserve standalone SWMS and standalone RA as separate products, and prototype a consultant-facing Combined WHS Control Pack from uploaded scope/specification documents as one combined reviewable output before any broad integration or SDK packaging work begins.**

# Safe Method SWMS Review Engine
**Benchmark Stream Setup Note**
Version: 2026-03-28

---

## Purpose

This note sets up the SWMS Review Engine as a governed benchmark stream inside the Safe Method quality system.

It ensures this mode enters the same operating structure as:
- SWMS
- RA
- Project WHS benchmark / control pack

---

## Benchmark Stream Definition

### Product mode

SWMS Review Engine

### Stream name

Principal-contractor risk register to subcontractor SWMS alignment benchmark

### Stream type

New product-mode benchmark stream

### Status

HOLD - awaiting first benchmark assets

---

## Product Purpose

Review a subcontractor SWMS against principal-contractor project risk requirements and produce a structured gap report for human approval.

This stream is benchmarked as:
- review-and-gap engine
- approval-support workflow

It is **not** benchmarked as:
- automatic SWMS approval
- autonomous compliance sign-off

---

## First Benchmark Goal

Prove that Safe Method can:
1. ingest a project risk register
2. ingest a subcontractor SWMS
3. compare the two in a project-specific way
4. identify:
   - aligned items
   - partial items
   - missing hazards
   - weaker or missing controls
   - HRCW mismatches
5. produce a useful plain-English gap report for a principal contractor reviewer

---

## First Benchmark Inputs Required

To activate the stream, the following benchmark assets are needed:

### 1. Principal-contractor project risk register

Preferred first format:
- `.xlsx`

### 2. Subcontractor SWMS

Preferred first format:
- `.docx`

### 3. Human benchmark expectation

A short expected-review note or benchmark comparison statement describing:
- what gaps should be found
- what alignment should be found
- what a principal contractor reviewer would expect to see

---

## Initial Weakest Point

Before benchmark assets exist, the initial weakest point is:

**benchmark asset readiness and review-contract definition**

Meaning:
- do we have the right project risk register example?
- do we have the right SWMS example?
- do we have a clear comparison result contract?

---

## First Benchmark Success Criteria

The first stream milestone is reached when Safe Method can produce a gap report that:
- is clearly tied to project risk requirements
- distinguishes aligned vs missing vs weaker items
- preserves uncertainty honestly
- is useful enough for principal-contractor review
- does not overclaim automatic approval

---

## Benchmark Failure Signals

The benchmark should be considered weak if:
- project risk items are not normalised clearly
- SWMS parsing is too unstable to compare reliably
- the comparison only produces generic compliance noise
- the gap report does not help a reviewer make a decision
- the engine overclaims alignment certainty

---

## Product-Boundary Rules

This stream must not be confused with:

### Standalone SWMS generation
This stream is review/comparison, not task generation.

### Standalone RA generation
This stream is not project-level RA drafting.

### Project WHS benchmark / control pack
This stream compares subcontractor SWMS to project risk requirements.
It is not the same as generating a project-level benchmark pack.

---

## Recommended Next Steps

1. Choose one benchmark project risk register
2. Choose one benchmark subcontractor SWMS
3. Define the comparison result contract
4. Add this stream to the governance register
5. Start the first benchmark cycle

---

## Governance Recommendation

Until benchmark assets exist, the stream should remain:

`HOLD - awaiting first benchmark assets`

It should become ACTIVE only when:
- benchmark inputs are selected
- comparison expectations are defined
- the first benchmark cycle can actually run

---

## Related Documents

- [SWMS_REVIEW_ENGINE_CONCEPT.md](C:\Users\AlanRichardson\gatekeeper\docs\SWMS_REVIEW_ENGINE_CONCEPT.md)
- [SWMS_REVIEW_ENGINE_PHASE1_SPEC.md](C:\Users\AlanRichardson\gatekeeper\docs\SWMS_REVIEW_ENGINE_PHASE1_SPEC.md)
- [BENCHMARK_GOVERNANCE_REGISTER.md](C:\Users\AlanRichardson\gatekeeper\docs\BENCHMARK_GOVERNANCE_REGISTER.md)
- [QUALITY_GOVERNANCE_NOTE.md](C:\Users\AlanRichardson\gatekeeper\docs\QUALITY_GOVERNANCE_NOTE.md)


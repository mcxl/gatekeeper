# Safe Method SWMS Review Engine
**Product Concept Note**
Version: 2026-03-28

---

## Purpose

This note defines a new Safe Method product direction:

**review subcontractor SWMS against principal-contractor project risk requirements**

This is positioned as a review-and-gap engine, not an autonomous final approver.

---

## Product Concept

Safe Method ingests:
- a principal contractor project risk register
- a subcontractor SWMS

Then it:
- normalises the project risk requirements
- parses the subcontractor SWMS
- compares hazards, controls, hold points, and HRCW expectations
- identifies alignment and gaps
- produces a review result
- supports revise-and-resubmit until human approval

---

## Best Positioning

Safe Method should be positioned as:
- a SWMS review engine
- a gap-detection engine
- an approval-support workflow

It should **not** be positioned as:
- fully autonomous SWMS approval
- automatic sign-off
- replacement for principal contractor judgment

---

## Primary Users

### Principal contractor
- WHS manager
- project manager
- site manager

### Subcontractor
- SWMS preparer
- project engineer
- supervisor

---

## Core Workflow

1. Principal contractor uploads/imports project risk register
2. Safe Method normalises it into a structured project risk schema
3. Subcontractor uploads SWMS
4. Safe Method parses the SWMS
5. Safe Method compares SWMS against project risk requirements
6. Safe Method produces one of:
   - aligned enough for review
   - partially aligned
   - gaps found / revision required
7. Principal contractor and subcontractor receive the review result
8. Subcontractor revises and resubmits if needed
9. Principal contractor makes the final approval decision

---

## Why This Fits Safe Method

This direction matches Safe Method's strengths:
- benchmark comparison
- control crosswalk logic
- gap detection
- review workflow
- quality governance

It is a better near-term fit than trying to sell full autonomous issue-ready generation.

---

## What Safe Method Must Be Good At

### Required capabilities
- risk register intake
- SWMS parsing
- hazard/control/hold-point matching
- HRCW expectation matching
- alignment/gap reporting
- version-aware resubmission workflow

### Hard problems
- same hazard described differently
- equivalent but not identical controls
- poor-quality subcontractor SWMS formatting
- project-specific method variation
- approval thresholds

Because of this, final approval should remain human-led.

---

## Best First Version

The narrowest useful version is:
- XLSX project risk register in
- SWMS in
- gap report out
- human approval decision outside the engine

This is the shortest credible path.

---

## Product Promise

Recommended product promise:

**Safe Method reviews subcontractor SWMS against principal-contractor project risk requirements and identifies alignment, gaps, and revision needs before approval.**

---

## Commercial Value

This product direction can save time by:
- reducing manual SWMS review effort
- improving consistency of review
- making project-specific expectations visible
- creating an audit trail for revision and approval

It can also improve trust because it is review-led rather than overclaiming autonomous sign-off.

---

## Risks

Main risks:
- poor source data quality from project risk registers
- messy subcontractor SWMS formats
- over-rigid matching logic
- false confidence if positioned as automatic approval

Mitigation:
- keep human approval in the loop
- keep uncertainty visible
- use benchmarked comparison logic
- roll out in a narrow first version

---

## Recommended Next Step

Write a Phase 1 implementation spec for:
- project risk register intake
- SWMS parsing
- comparison engine
- structured gap report

---

## Related Documents

- [PRODUCT_DECISION_MEMO.md](C:\Users\AlanRichardson\gatekeeper\docs\PRODUCT_DECISION_MEMO.md)
- [LBV_FLYWHEEL_ARCHITECTURE.md](C:\Users\AlanRichardson\gatekeeper\docs\LBV_FLYWHEEL_ARCHITECTURE.md)
- [QUALITY_GOVERNANCE_NOTE.md](C:\Users\AlanRichardson\gatekeeper\docs\QUALITY_GOVERNANCE_NOTE.md)


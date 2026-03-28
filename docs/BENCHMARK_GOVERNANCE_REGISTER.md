# Benchmark Governance Register
**Active Benchmark Streams and Control Status**
Version: 2026-03-28

---

## Purpose

This register provides a short governance view of active benchmark streams.

It is designed to show, in one place:
- what benchmark streams are active
- who owns them
- what state they are in
- what the current weakest point is
- what the next refinement target is
- what the close-out rule is

Use this as the working control sheet for LBV benchmark management.

---

## Status Meanings

- `ACTIVE` = benchmark stream is still being refined
- `HOLD` = paused pending decision, capacity, or dependency
- `CLOSED` = benchmark stream is materially satisfied or intentionally stopped

---

## Register

| Benchmark Stream | Product Mode | Owner | Status | Current Weakest Point | Next Refinement Target | Close-Out Rule |
|---|---|---|---|---|---|---|
| Facade remedial benchmark | SWMS | Internal product owner | CLOSED | Previously task/control quality and consultant trust | Maintain by regression only | Keep closed unless regression or new specialist gap appears |
| EWP roof access benchmark | SWMS | Internal product owner | ACTIVE | Issue-ready gating, rescue/recovery completeness, method-validity evidence | Add stronger issue gate and rescue/method-validity checks | Close when draft is materially strong and obvious issue-ready blockers are automatically caught |
| Lingate remedial works benchmark | SWMS | Internal product owner | ACTIVE | Issue gating, pre-refurbishment validation, scope-to-task completeness | Add intrusive-work validation and tighten task structure/coverage | Close when draft is materially strong and consultant-trust gaps are bounded and visible |
| Principal-contractor risk register to subcontractor SWMS alignment benchmark | SWMS Review Engine | Internal product owner | HOLD | Benchmark asset readiness and review-contract definition | Select first project risk register, first subcontractor SWMS, and define comparison result contract | Move to ACTIVE only when first benchmark assets and comparison expectations are ready |
| Data centre fit-out benchmark | RA | Internal product owner | CLOSED | Previously classification/HRCW/control quality | Maintain by regression only | Keep closed unless regression or product-boundary shift appears |
| Withers Road civil benchmark | RA | Internal product owner | CLOSED | Previously civil classification and HRCW/package relevance | Maintain by regression only | Keep closed unless regression or new civil benchmark gap appears |
| Withers Road project WHS benchmark draft | Project WHS benchmark / control pack | Internal product owner | CLOSED | Materially satisfied as benchmark-quality draft | Maintain by regression only | Closed 2026-03-28 — reopen only if expert review or new civil benchmark exposes material gaps |

---

## Operating Rules

### 1. One owner per benchmark stream

Every benchmark stream should have one clear owner responsible for:
- deciding whether the stream continues
- directing refinement
- recording the next step

### 2. One main weakness at a time

Each active stream should have one main centre of gravity.

Do not run one benchmark stream against multiple unrelated weaknesses at once.

### 3. Close streams deliberately

A stream should not stay open by default.

It should be:
- actively refined
- intentionally held
- or explicitly closed

### 4. Closed does not mean forgotten

Closed benchmark streams should still be protected through:
- regression tests
- benchmark reruns where needed
- issue-gating maintenance

---

## Review Rhythm

Review this register whenever:
- a benchmark cycle finishes
- a new benchmark stream starts
- a stream changes from active to hold
- a stream is closed

---

## Related Documents

- [LBV_ONE_CYCLE_PLAYBOOK.md](C:\Users\AlanRichardson\gatekeeper\docs\LBV_ONE_CYCLE_PLAYBOOK.md)
- [LBV_FLYWHEEL_ARCHITECTURE.md](C:\Users\AlanRichardson\gatekeeper\docs\LBV_FLYWHEEL_ARCHITECTURE.md)
- [QUALITY_GOVERNANCE_NOTE.md](C:\Users\AlanRichardson\gatekeeper\docs\QUALITY_GOVERNANCE_NOTE.md)
- [IP_MAP.md](C:\Users\AlanRichardson\gatekeeper\docs\IP_MAP.md)

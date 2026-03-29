# Benchmark Governance Register
**Active Benchmark Streams and Control Status**
Version: 2026-03-29

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
| 18 Danks Street quote-to-SWMS benchmark | SWMS | Internal product owner | CLOSED — STRONG_WORKING_DRAFT_ONLY | Externally reviewed 2026-03-29. Not benchmark-quality confirmed. Main gap: HRCW/CCVS misalignment with written method. Secondary: latent-condition packaging, unsupported controls, generic WAH monitoring defaults. Deterministic layer at practical limit. | No further deterministic refinement. Carry learnings into HRCW/CCVS issue-gate improvement and agent-prompt work on future streams. | Closed as strong working draft. Benchmark-quality requires agent-prompt-level HRCW/CCVS improvements that apply across all SWMS streams, not Danks-specific fixes. |
| Facade remedial benchmark | SWMS | Internal product owner | CLOSED | Previously task/control quality and consultant trust | Maintain by regression only | Keep closed unless regression or new specialist gap appears |
| EWP roof access benchmark | SWMS | Internal product owner | ACTIVE | Agent-level EWP method knowledge (transfer scenarios, wind OEM limits) — product investment decision | Agent prompt enrichment for EWP-specific content, or deeper method-validity comparison | Two LBV cycles complete (2026-03-29). Transfer controls verified against SD Group reference. Remaining gap is agent-level. Close when issue gate passes consistently. |
| Lingate remedial works benchmark | SWMS | Internal product owner | ACTIVE | External review returned below strong working draft. Generic WAH-led verification instead of task-specific. Unsupported control drift. | Fix CCVS/monitoring task-specificity and unsupported controls. | Four LBV cycles (2026-03-29/30). Waterproofing CCVS priority fix + SYS setup/QA monitoring split applied. |
| CLT install drawing-to-SWMS benchmark | SWMS | Internal product owner | ACTIVE | External review returned below strong working draft. Generic WAH-led verification instead of drawing-led crane/bracing/engineer controls. | Fix CCVS/monitoring for CLT, add permanent connection task, strengthen engineer hold-points. | Three LBV cycles (2026-03-30). Decomposer prompt enriched with CLT sequence rules. Traffic stripping broadened. |
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

## Automation Status (2026-03-29)

| Tool | Location | Coverage | Status |
|------|----------|----------|--------|
| Issue-gate checker | `src/issue_gate.py` | 9 deterministic checks, stage-aware, configurable WAH threshold | Built, 29 tests |
| Regression runner | `src/regression_runner.py` | 5 closed streams, 175 tests | Built, 7 tests |
| CI pipeline | `.github/workflows/ci.yml` | Lint + full pytest on push to main | Active |
| Reference jobs | `tests/run_reference_jobs.py` | 8 SWMS inference jobs | Active |

**Total test suite:** 377 tests passing

---

## Related Documents

- [LBV_ONE_CYCLE_PLAYBOOK.md](C:\Users\AlanRichardson\gatekeeper\docs\LBV_ONE_CYCLE_PLAYBOOK.md)
- [LBV_FLYWHEEL_ARCHITECTURE.md](C:\Users\AlanRichardson\gatekeeper\docs\LBV_FLYWHEEL_ARCHITECTURE.md)
- [QUALITY_GOVERNANCE_NOTE.md](C:\Users\AlanRichardson\gatekeeper\docs\QUALITY_GOVERNANCE_NOTE.md)
- [IP_MAP.md](C:\Users\AlanRichardson\gatekeeper\docs\IP_MAP.md)

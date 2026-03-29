# Refinement Decision Log
## Per-Cycle LBV Decision Record

---

### 1. Cycle Summary

- **Date:** 2026-03-29
- **Product mode:** SWMS
- **Benchmark stream:** CLT install drawing-to-SWMS
- **Benchmark case:** Vincent Rd House — 36 CLT wall panels, 23 push-pull props (F5/F3), Stora Enso bracing plan
- **Cycle type:** Second LBV — method-fidelity verification + road boilerplate stripping

### 2. What Writer Produced

11 tasks, 0 agent failures. Logical CLT erection sequence:
1. Establish site and secure laydown
2. Verify panel delivery and check stored panels
3. Confirm crane lift plan and exclusion zones
4. Install temporary push-pull props and base packing
5. Lift and position first CLT wall panel with mobile crane
6. Plumb panel and connect to bracing props
7. Release crane and repeat for remaining 35 panels
8. Verify final panel plumb and prop tension
9. Establish temporary bracing sign and security
10. Hold for structural engineer inspection and release
11. Demobilise crane and remove temporary plant

### 3. Critic Findings

**Improved from cycle 1:** Task sequence now correct, no "rop" false match, drawing-specific content present (F5/F3, timber packing, exclusion zones).

**New finding:** Road/traffic boilerplate re-appeared in task 1.1 (road opening permit, traffic management plan, AS 1742.3). The agent generates these controls despite the description saying "no traffic management required". Different root cause from cycle 1 — the inference matrix and agents independently inject road controls.

**Also:** "Structural engineer" was flagged as unsupported by issue gate, but it IS source-supported for CLT work (description references engineer drawing). Removed from unsupported keyword list.

### 4. Fixes Applied

1. **Orchestrator `_UNSUPPORTED_CONTROL_PHRASES`:** Added "road opening permit", "traffic management plan", "as 1742" to strip road boilerplate from non-road jobs
2. **Orchestrator:** Removed "structural engineer" from unsupported list — legitimate in construction contexts (CLT, concrete, demolition)
3. **Issue-gate `_UNSUPPORTED_KEYWORDS`:** Same changes mirrored — added road terms, removed structural engineer

### 5. End-of-Cycle Decision

- **Decision:** SECOND CYCLE COMPLETE — CLT task architecture correct, road boilerplate stripping strengthened
- **Status:** ACTIVE — 2 cycles. Task sequence and method content are good. Remaining: drawing-specific detail depth (prop numbering, F3/F5 type selection) requires richer input or drawing-extraction capability — product-level gap.

### 6. Verification

- 391 tests passing, 0 regressions
- 5/5 closed streams pass (175 tests)

### 7. One-Line Outcome

Second CLT LBV cycle: task sequence correct, road boilerplate stripping strengthened (road opening permit, traffic management plan, AS 1742), structural engineer removed from unsupported list. 391 tests.

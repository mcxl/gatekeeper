# Multi-Agent Close-Out Checklist
**End-One-Cycle Checklist for Safe Method**
Version: 2026-03-28

---

## Purpose

Use this checklist at the end of a multi-agent benchmark cycle.

It is designed to make sure the cycle ends cleanly, with:
- one clear decision
- the right records updated
- the next step made explicit
- no loose benchmark state

This keeps the system governable and prevents unfinished loops.

---

## Close-Out Checklist

### 1. Confirm Cycle Outcome

- [ ] One end-of-cycle decision has been made:
  - continue and refine
  - narrow scope
  - pause/defer
  - close benchmark stream
- [ ] The decision matches the actual benchmark result
- [ ] The cycle did not quietly drift into multiple unrelated outcomes

### 2. Confirm Weakness Status

- [ ] The original weakest point was addressed, tested, or deliberately deferred
- [ ] If the weakest point changed, the new weakest point is clearly named
- [ ] If the benchmark is materially satisfied, that is stated explicitly

### 3. Confirm Verification

- [ ] Regeneration / tests / checks were run where needed
- [ ] Any regressions found are recorded
- [ ] If a regression exists, the cycle is not falsely treated as complete

### 4. Confirm Documentation Updates

- [ ] Refinement decision log updated if a full cycle was completed
- [ ] Benchmark governance register updated if:
  - weakest point changed
  - status changed
  - stream moved to HOLD or CLOSED
- [ ] Benchmark close-out template completed if the stream was closed

### 5. Confirm Next Step

- [ ] The next step is explicit:
  - another internal refinement cycle
  - external expert review
  - hold / defer
  - close-out / regression only
- [ ] If external review is next, the handoff materials are prepared
- [ ] If no next step is required, that is stated clearly

### 6. Confirm Product-Boundary Safety

- [ ] The cycle did not create product-boundary confusion
- [ ] SWMS, RA, and Project/control-pack roles stayed separate
- [ ] No unrelated benchmark stream was silently affected

### 7. Final Close-Out Check

- [ ] One stream
- [ ] One decision
- [ ] One recorded next step
- [ ] No open loop without owner

---

## Quick Close-Out Rule

**If you cannot clearly state the cycle decision, the new weakest point, and the next step, the cycle is not closed yet.**

---

## Related Documents

- [MULTI_AGENT_OPERATING_SYSTEM.md](C:\Users\AlanRichardson\gatekeeper\docs\MULTI_AGENT_OPERATING_SYSTEM.md)
- [MULTI_AGENT_WORKFLOW_DIAGRAM.md](C:\Users\AlanRichardson\gatekeeper\docs\MULTI_AGENT_WORKFLOW_DIAGRAM.md)
- [MULTI_AGENT_LAUNCH_CHECKLIST.md](C:\Users\AlanRichardson\gatekeeper\docs\MULTI_AGENT_LAUNCH_CHECKLIST.md)
- [REFINEMENT_DECISION_LOG_TEMPLATE.md](C:\Users\AlanRichardson\gatekeeper\docs\REFINEMENT_DECISION_LOG_TEMPLATE.md)
- [BENCHMARK_CLOSE_OUT_TEMPLATE.md](C:\Users\AlanRichardson\gatekeeper\docs\BENCHMARK_CLOSE_OUT_TEMPLATE.md)


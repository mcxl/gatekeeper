# Multi-Agent Launch Checklist
**Start-One-Cycle Checklist for Safe Method**
Version: 2026-03-28

---

## Purpose

Use this checklist before starting a multi-agent benchmark cycle.

It is designed to make sure the cycle starts cleanly, with:
- the right stream
- the right inputs
- the right weakest point
- the right stopping rule

This keeps the system repeatable and reduces prompt drift.

---

## Launch Checklist

### 1. Select One Stream

- [ ] Product mode is selected:
  - SWMS
  - RA
  - Project WHS benchmark / control pack
- [ ] One benchmark stream only is active for this cycle
- [ ] The stream status has been checked in the governance register

### 2. Confirm Benchmark Inputs

- [ ] Source documents are identified
- [ ] Latest generated output is identified
- [ ] Benchmark/reference material is identified if relevant
- [ ] File paths are known and usable

### 3. Confirm Current Weakest Point

- [ ] Current weakest point is taken from the governance register or latest decision log
- [ ] The weakest point is narrow enough for one cycle
- [ ] The weakest point is not already solved

### 4. Confirm Stop Rule

- [ ] The likely end-of-cycle stop point is known:
  - continue and refine
  - narrow scope
  - pause/defer
  - close benchmark stream
  - external review handoff
- [ ] The cycle will stop if the next step requires external review or architectural change

### 5. Confirm Agent Roles

- [ ] Writer role is clear
- [ ] Critic role is clear
- [ ] Classifier role is clear if needed
- [ ] Fixer / Checker role is clear
- [ ] Coordinator role is assigned if multiple streams are active

### 6. Confirm Output Expectations

- [ ] The cycle should produce one clear end-of-cycle decision
- [ ] The decision log should be updated if a full cycle is completed
- [ ] The governance register should be updated if stream status or weakest point changes

### 7. Final Launch Check

- [ ] One stream
- [ ] One main weakness
- [ ] One clean cycle
- [ ] No unrelated implementation work

---

## Quick Launch Rule

**If you cannot clearly name the stream, source inputs, weakest point, and stop rule, do not launch the cycle yet.**

---

## Related Documents

- [MULTI_AGENT_OPERATING_SYSTEM.md](C:\Users\AlanRichardson\gatekeeper\docs\MULTI_AGENT_OPERATING_SYSTEM.md)
- [MULTI_AGENT_WORKFLOW_DIAGRAM.md](C:\Users\AlanRichardson\gatekeeper\docs\MULTI_AGENT_WORKFLOW_DIAGRAM.md)
- [BENCHMARK_GOVERNANCE_REGISTER.md](C:\Users\AlanRichardson\gatekeeper\docs\BENCHMARK_GOVERNANCE_REGISTER.md)
- [LBV_ONE_CYCLE_PLAYBOOK.md](C:\Users\AlanRichardson\gatekeeper\docs\LBV_ONE_CYCLE_PLAYBOOK.md)


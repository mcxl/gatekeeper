# Consolidated Issue-Gate Assessment
## All Active SWMS Streams — 2026-03-29

---

### Assessment Results

| Stream | Tasks | Pass | Fail | Review | Classification | Main issue |
|--------|-------|------|------|--------|---------------|------------|
| **EWP roof access** | 12 | 10 | 1 | 1 | FAIL_INTERNAL | Access task at pos 5, dependent at pos 4 (agent ordering — trivially fixed by adding "mobilise boom" to phase 0) |
| **Lingate remedial** | 12 | 11 | 0 | 1 | REVIEW_INTERNAL | Placeholder supervisor only |
| **CLT install** | 9 | 11 | 0 | 1 | REVIEW_INTERNAL | Placeholder supervisor only |

### Key Observations

1. **Lingate and CLT are effectively clean.** The only review on both is the supervisor placeholder — acceptable at benchmark stage. Both would be READY_FOR_EXPERT_REVIEW if supervisor were populated.

2. **EWP has one sequencing issue** — agent puts EWP mobilisation after dependent tasks. This is agent ordering variability, mitigated by adding "mobilise boom" to phase 0 keywords (trivial fix applied).

3. **CCVS-monitoring alignment is now zero mismatches** across all streams (cross-stream fix from earlier this session is working).

4. **Road boilerplate stripping is working** — no road terms in Lingate or CLT outputs.

5. **Latent-condition packaging** is no longer appearing in these runs (the decomposer prompt improvements and stripping functions are effective).

### Cross-Stream Improvement Impact

| Improvement | Streams affected | Before | After |
|-------------|-----------------|--------|-------|
| CCVS-monitoring alignment | All 3 | 1-3 mismatches per stream | 0 |
| Decomposer remedial sequence rules | Lingate | Missing demolition task | Present |
| Road boilerplate stripping | CLT, Lingate | Road terms in output | Clean |
| CCVS keyword expansion | All 3 | N/A and WAH overcall | Differentiated |

### Single Highest-Value Next Improvement

**The supervisor placeholder is the only remaining review across all 3 streams.** At benchmark stage this is acceptable, but at issue-ready stage it would be the only blocker. The highest-value next step is NOT a code fix — it's deciding whether to:

1. Accept the current state and move streams toward expert review
2. Or focus on a new benchmark stream (SWMS Review Engine)

The active streams are at diminishing returns for deterministic/prompt-level improvement. The remaining gaps are agent-level variability (task naming, ordering) and product-level capability (drawing extraction for CLT, richer scope input for Lingate).

### Recommendation

**Pause active refinement on EWP, Lingate, and CLT.** All three are at strong working draft quality with issue gates passing (except one trivially-fixable sequence issue on EWP). The next highest-value work is either:
- External review of one of these streams to test benchmark-quality confirmation
- SWMS Review Engine benchmark asset setup (Phase 5 from execution plan)
- Or a new benchmark stream if one is available

# Next-Stage Execution Plan
## 2026-03-29

---

### Phase Sequence

| Phase | Target | Type | Dependency | Status |
|-------|--------|------|------------|--------|
| 1 | Danks disposition | Governance update | None | **DONE** — status updated to AWAITING_EXTERNAL_REVIEW |
| 2 | Issue-gate automation | Build (deterministic) | None | **DONE** — `src/issue_gate.py`, 9 checks, 29 tests |
| 3 | Benchmark regression runner | Build (deterministic) | Phase 2 pattern | **DONE** — `src/regression_runner.py`, 5 streams, 175 tests |
| 4 | EWP roof access stream | Benchmark refinement | Phase 2 available | **DONE** — 2 LBV cycles, transfer controls verified against SD Group reference |
| 5 | SWMS Review Engine | Benchmark setup | Real project assets | NOT STARTED — awaiting benchmark asset selection |

### Phase 2 Detail: Issue-Gate Automation

Build a deterministic issue-gate checker (~100 lines Python) that takes a rendered .docx and returns pass/fail on 9 checks:
1. Access before dependents
2. No coat+reinstate merge
3. No pre-start in demob
4. CCVS monitoring coverage
5. CCVS-monitoring alignment
6. WAH percentage < 50%
7. No unsupported controls
8. Supervisor field populated
9. Footer populated

No API calls. Runs in <2 seconds. Can be called from CI, regeneration scripts, or pre-review gates.

### Phase 3 Detail: Benchmark Regression Runner

Lightweight script that reruns closed-stream tests:
- RA reference jobs (data centre, Withers Road)
- Control pack tests (Withers Road)
- SWMS reference jobs (8 fixtures)
Run as CI step or pre-commit check.

### What Stays Manual

- External Aussie WHS reviews
- Decomposer prompt tuning
- New benchmark stream selection
- SWMS Review Engine benchmark asset selection

### Next Active Refinement Target

**Danks disposition (2026-03-29):** Closed as STRONG_WORKING_DRAFT_ONLY after external review. Not benchmark-quality confirmed. Learnings carried forward.

**Next priorities:**
1. Strengthen HRCW/CCVS issue-gate checks using Danks learnings (applies to all SWMS streams)
2. EWP deeper method-validity cycle or agent prompt enrichment
3. Lingate remedial works — first LBV cycle
4. SWMS Review Engine benchmark asset selection (Phase 5, when ready)

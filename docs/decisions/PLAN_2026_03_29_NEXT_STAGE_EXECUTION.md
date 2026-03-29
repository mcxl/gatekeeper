# Next-Stage Execution Plan
## 2026-03-29

---

### Phase Sequence

| Phase | Target | Type | Dependency |
|-------|--------|------|------------|
| 1 | Danks disposition | Governance update | None |
| 2 | Issue-gate automation | Build (deterministic) | None |
| 3 | Benchmark regression runner | Build (deterministic) | Phase 2 pattern |
| 4 | EWP roof access stream | Benchmark refinement | Phase 2 available |
| 5 | SWMS Review Engine | Benchmark setup | Real project assets |

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

EWP roof access benchmark — after Phase 2 is built.

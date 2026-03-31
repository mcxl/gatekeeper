# Five-Job Pilot Plan

## Objective

Prove that Safe Method generates SWMS documents across different job types at STRONG_WORKING_DRAFT quality or above, using the current pipeline, without manual rewrite.

The pilot bridges benchmark development and trusted commercial use.

---

## What the pilot proves

### Commercially
- The pipeline produces usable SWMS drafts across real project types
- A consultant can complete the draft to issue-ready quality with minor effort
- The product saves meaningful time vs writing from scratch

### Technically
- Deterministic post-processing generalises across job types
- Decomposer prompt rules produce credible sequences for different trades
- The issue gate catches structural defects reliably on new scopes
- The self-learning layer captures useful findings from new job types
- The known generation-quality limit (monitoring copy-paste) is bounded

---

## Candidate Jobs

| # | Job | Job Type | Source | Reference SWMS | Expected Weak Points |
|---|-----|----------|--------|----------------|---------------------|
| 1 | Remedial facade painting — commercial, scaffold access, occupied | remedial | Quote or scope brief | Yes (Danks learnings) | Control credibility, monitoring copy-paste, CHM/SIL alignment |
| 2 | Internal fit-out — office refurb, ceiling, partitions, services | fit_out | Quote or scope brief | No | Job-type detection, HRCW undercall on services, trade merging |
| 3 | Strip-out demolition — existing fitout, asbestos survey referenced | demolition | Quote or scope brief | No | Asbestos latent packaging, demolition sequence, HRCW overcall |
| 4 | Roof maintenance — EWP/scissor lift to roof plant for HVAC | maintenance | Scope brief | Partial (EWP learnings) | Transfer method, rescue plan, WAH dominance |
| 5 | Structural erection — CLT or steel, crane-led, temporary works | new_build | Drawing + scope brief | Partial (CLT learnings) | Crane exclusion, temp works sequence, engineer holds |

### Selection rationale
- Covers 5 of 6 supported job_types
- Mix of high-confidence (remedial, EWP) and stretch (fit_out, demolition)
- At least one job has asbestos/latent conditions
- At least one job has crane/lift and temporary works

---

## Workflow Per Job

```
1. Obtain or write a realistic scope brief (100-300 words)
2. Run generate_swms() with job_type and scope_context
3. Run run_validator_loop() — record status, fails, reviews
4. If ESCALATE_EXTERNAL: run run_parallel_review()
5. Append all findings to findings_log.jsonl
6. Run detect_patterns(min_occurrences=2) — record candidates
7. Classify each finding using defect taxonomy
8. If externally reviewable: render docx, run issue gate
9. Update pilot tracking table
```

---

## Metrics

| Metric | How measured |
|--------|-------------|
| Validator status | run_validator_loop() |
| Validator fail count | len(failing_checks) |
| Reviewer status | run_parallel_review() |
| Reviewer hard fail count | len(hard_fails) |
| Reviewer review item count | len(review_items) |
| Issue gate on docx | run_issue_gate() |
| Findings captured | count per job |
| Pattern candidates | detect_patterns() after each job |
| External review verdict | If submitted |
| Operator time | Minutes from scope to render |

---

## Success Criteria

### Pass (all must be met)
1. Validator PASS_INTERNAL on at least 4 of 5 jobs
2. Reviewer hard fails < 3 on at least 4 of 5 jobs
3. At least 2 jobs judged externally reviewable without structural rewrite
4. No new systemic defect requiring pipeline architecture change

### Stretch (desirable)
- Validator PASS_INTERNAL on 5/5
- At least 1 external review returns STRONG_WORKING_DRAFT or above
- Pattern detector surfaces at least 1 actionable cross-job candidate
- Operator time under 15 minutes per job

### Fail (any one triggers)
- Validator PASS_INTERNAL on fewer than 3 of 5
- Any job produces a dangerous-if-followed sequence
- A new defect class requires pipeline rewrite
- Operator time exceeds 60 minutes per job on average

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Monitoring copy-paste on new job types | High | Medium | Known limit — consultant completion expected |
| fit_out or demolition HRCW miscall | Medium | Medium | Job-type rule packs exist for demolition; fit_out may need new rules |
| No decomposer trade-specific sequence for new type | Medium | Medium | Generic sequence applies; record gap if found |
| Agent 2 validation failures on retry | Medium | Low | Known Haiku variance — retry logic handles this |
| Asbestos handling fails on demolition job | Low | High | Well-tested stripping logic; specific bug if it fails |
| External reviewer returns BELOW on all jobs | Medium | High | Pivot to consultant-assisted workflow if this happens |

---

## Pilot timeline

1. Job 1 (remedial) — high confidence, validates workflow
2. Job 2 (fit_out) — stretch test, likely exposes gaps
3. Job 3 (demolition) — tests asbestos/latent logic
4. Job 4 (maintenance) — lightweight, tests simple path
5. Job 5 (new_build) — most complex, validates CLT/crane

Run sequentially. Fix deterministic bugs between jobs. Do not accumulate.

---

## Pilot Tracking Table

| Job | Type | Validator | V Fails | Reviewer | R HF | R Items | Gate FAIL | Gate REV | External | Notes |
|-----|------|-----------|---------|----------|------|---------|-----------|----------|----------|-------|
| 1 | remedial | RETRY_INTERNAL | 2 | BELOW_WORKING_DRAFT | 2 | 69 | — | — | Not submitted | Rerun: hold point SYS-M3 fix applied. Sequence issues remain (scaffold late, expose after repair). |
| 2 | fit_out | RETRY_INTERNAL | 2 | BELOW_WORKING_DRAFT | 6 | 59 | — | — | Not submitted | Demolition N/A CCVS + disconnection cert drift. C24 caught monitoring copy-paste. 12 pattern candidates. |
| 3 | demolition | — | — | — | — | — | — | — | — | — |
| 4 | maintenance | — | — | — | — | — | — | — | — | — |
| 5 | new_build | — | — | — | — | — | — | — | — | — |

---

## After the pilot

If pass: define consultant-assisted workflow, begin production-readiness planning.
If fail: record what failed, classify the defect, address before retrying.

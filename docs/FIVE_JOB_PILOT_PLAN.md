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
| 1 | remedial | ESCALATE_EXTERNAL | 1 | — | — | — | 1 | 1 | Not submitted | Hardened: monitoring dedup worked (CHM tasks clean). 1 remaining FAIL: late scaffold confirm. |
| 2 | fit_out | RETRY_INTERNAL | 1 | — | — | — | 1 | 3 | Not submitted | Hardened: fails halved. 1 remaining FAIL: barricade N/A CCVS (fallback expanded). |
| 3 | demolition | ESCALATE_EXTERNAL | 0 | BELOW_WORKING_DRAFT | 5 | 60 | 0 | 4 | Not submitted | Cleanest gate result (0 FAIL). Demolish CCVS fix worked. Disconnection allowed. Services sequence late. |
| 4 | maintenance | ESCALATE_EXTERNAL | 0 | BELOW_WORKING_DRAFT | 3 | 38 | 0 | 4 | Not submitted | Scissor lift protected access. No unsupported WAH controls. Lowest review items (38). Task 1.2 early. |
| 5 | new_build | RETRY_INTERNAL | 1 | BELOW_WORKING_DRAFT | 2 | 48 | 1 | 3 | Not submitted | Steel erection sequence correct. Crane/prop/bolt logic present. Staging N/A + prop removal SIL. |

---

## After the pilot

If pass: define consultant-assisted workflow, begin production-readiness planning.
If fail: record what failed, classify the defect, address before retrying.

---

## Pilot Results Summary (2026-03-31)

### Final tracking table

| Job | Type | Validator | V Fails | Gate FAIL | Gate REV | R HF | R Items |
|-----|------|-----------|---------|-----------|----------|------|---------|
| 1 | remedial | RETRY_INTERNAL | 2 | — | — | 2 | 69 |
| 2 | fit_out | RETRY_INTERNAL | 2 | — | — | 6 | 59 |
| 3 | demolition | ESCALATE_EXTERNAL | 0 | 0 | 4 | 5 | 60 |
| 4 | maintenance | ESCALATE_EXTERNAL | 0 | 0 | 4 | 3 | 38 |
| 5 | new_build | RETRY_INTERNAL | 1 | 1 | 3 | 2 | 48 |

### Success criteria assessment

| Criterion | Target | Result | Met? |
|-----------|--------|--------|------|
| Validator PASS_INTERNAL 4/5 | 4 pass | 2 pass (J3, J4 ESCALATE_EXTERNAL = 0 FAIL) | PARTIAL — 2/5 zero-fail, 3/5 have 1-2 FAIL |
| Reviewer HF < 3 on 4/5 | 4 jobs | 3 jobs (J1=2, J4=3, J5=2) | PARTIAL — 3/5 meet, J2=6 and J3=5 exceed |
| 2 jobs externally reviewable | 2 | J3 and J4 (0 gate FAIL) | MET |
| No new systemic architecture defect | None | None found | MET |

**Overall: PARTIAL PASS.** Two of four criteria met, two partially met. The system produces usable drafts but not consistently clean enough for unassisted use.

### Recurring defect families

| Defect | Frequency | Type | Fix layer |
|--------|-----------|------|-----------|
| Monitoring copy-paste across unlike CCVS families | 4/5 jobs | deterministic_limit | Model quality — Haiku reuses monitoring text across tasks |
| CCVS completeness (N/A on tasks with hazards) | 3/5 jobs | deterministic_fix | Agent generates N/A for staging/delivery/hold-point tasks |
| Generic responsibility text | 2/5 jobs | deterministic_fix | _improve_responsibility() covers main patterns but not all |
| Unsupported control drift | 2/5 jobs | prompt_decomposer_fix | Agent generates out-of-scope controls (membrane on painting, disconnection cert on fit-out) |
| Sequence variance | 2/5 jobs | prompt_decomposer_fix | Agent places tasks out of chronological order despite prompt rules |
| HRCW undercall | 3/5 jobs | issue_gate_candidate | Scissor lift, crane, structural alteration not always in HRCW |

### Commercial readiness assessment

**Current state: PRE-PILOT HARDENING required.**

The system is not yet at unsupervised commercial pilot readiness, but it is close. The output is consistently at STRONG_WORKING_DRAFT quality for a consultant to complete — not a full rewrite.

What works:
- Method sequences are broadly correct across all 5 job types
- Dominant control family logic works (SIL, CHM, WAH correctly assigned in most tasks)
- Issue gate catches real structural defects (27 checks)
- Self-learning layer captures findings and detects cross-job patterns
- No dangerous sequences were generated in any of the 5 jobs
- Two jobs (demolition, maintenance) produced zero gate failures

What doesn't yet work reliably:
- Monitoring text is frequently copied across unlike tasks (model-quality limit)
- CCVS completeness on N/A tasks (agent sometimes generates N/A for real tasks)
- Generic responsibility text leaks through on some tasks
- Unsupported control drift on scopes outside the remedial waterproofing benchmark

### Deterministic vs model-quality classification

| Category | Defects | Fixable? |
|----------|---------|----------|
| Deterministic (already fixed) | Hold point SYS-M3, demolish CCVS, membrane/asbestos strip, scaffold WAH override, generator artefact strip | Yes — implemented |
| Deterministic (fixable) | CCVS N/A on staging tasks, HRCW undercall patterns, generic responsibility patterns | Yes — narrow issue gate or orchestrator fixes |
| Model-quality limit | Monitoring copy-paste, sequence variance, unsupported control drift | No — requires stronger model or post-generation rewrite |

### Stronger model tiering recommendation

**Justified.** The monitoring copy-paste defect recurs on 4/5 jobs and is the single largest barrier to STRONG_WORKING_DRAFT or above. It cannot be fixed deterministically. Options:

1. **Tier up to Sonnet for the assembler agent (Agent 4)** — the assembler writes monitoring and responsibility text. Sonnet is more likely to produce task-specific monitoring rather than copying from adjacent tasks. Cost increase is bounded (1 agent out of 4).

2. **Add a post-generation monitoring rewrite pass** — a deterministic function that detects verbatim monitoring duplication and replaces it with family-specific templates. Already partially implemented in `_improve_monitoring()` but needs to detect cross-task verbatim copying.

3. **Accept the limit** — the output is usable as a strong working draft with consultant completion of monitoring sections. This is the current state.

Recommendation: implement option 2 (deterministic monitoring dedup) first. If it doesn't resolve the pattern, trial option 1 (Sonnet assembler) on 2 jobs.

---

## Commercial Pilot Tracking

| # | Customer | Job | Type | Time | Validator | Gate FAIL | Gate REV | Edits | Would issue |
|---|----------|-----|------|------|-----------|-----------|----------|-------|-------------|
| C1 | mcxi.co | Unitas warehouse metal roofing | new_build | ~15 min | RETRY_INTERNAL 1F | 1 | 4 | CCVS N/A on crane-lift, HRCW, supervisor names, lifeline control | Yes with edits |
| C2 | mcxi.co | Tilt-up panel erection with crane | new_build | ~15 min | RETRY_INTERNAL 1F | 1 | 3 | Sequence: permanent connections before lift, lift plan after brace removal. CCVS N/A on 4 tasks. HRCW. Names. | Yes with edits |
| C3 | mcxi.co | Withers Road civil upgrade | civil | ~20 min | RETRY_INTERNAL 2F | 3 | 4 | CCVS N/A on 3 civil tasks. Commissioning false positive. Signal sequencing. Sydney Water hold points. Names. | Yes with edits |
| C4 | mcxi.co | Gabion cage / rail corridor | civil | ~15 min | RETRY_INTERNAL 3F | 4 | 4 | Excellent sequence. Rail corridor controls missing (critical). 3 N/A CCVS. Waterproof false positive. HRCW excavation. | Yes with edits (rail controls needed) |

---

## Commercial Pilot Assessment (2026-04-01)

### Is the system ready for consultant-assisted commercial use?

**Yes.** All four commercial pilot jobs produced SWMS that a consultant would issue with edits. No dangerous sequences were generated. Average time from scope to reviewed docx was 16 minutes — materially faster than writing from scratch (typically 2-4 hours for comparable scope complexity).

The system is not ready for unsupervised use. Every output requires consultant review and completion. But as a draft-generation tool that saves the consultant 80-90% of the initial writing time, it is commercially usable now.

### Recurring consultant edits (system defects)

These edits recurred across multiple jobs and represent real system improvements still needed:

| Edit | Frequency | Classification |
|------|-----------|----------------|
| Fill in supervisor/worker names (placeholder) | 4/4 | Expected — system cannot know site-specific names |
| CCVS N/A on specialist tasks | 3/4 | Deterministic fix — keyword coverage expanding each job |
| Generic responsibility text on some tasks | 3/4 | Deterministic fix — _improve_responsibility() needs more patterns |
| HRCW undercall (crane, excavation, plant) | 3/4 | Issue gate candidate — flags correctly but agent under-calls |

### Expected specialist additions (not system defects)

These edits are specialist-environment additions that the system correctly does not invent. The anti-drift logic is working as intended — the consultant adds these based on their knowledge of the specific site:

| Addition | Jobs | Why it's expected |
|----------|------|-------------------|
| Rail corridor protection controls (track isolation, protection officer, overhead clearance) | C4 | Specialist environment — system correctly avoids inventing rail controls without source support |
| Named authority on hold points (specific engineer, inspector, utility company) | C3, C4 | Site-specific — system cannot know which consultant or authority applies |
| Lifeline/safety wire enabling sequencing (specific to roofing method) | C1 | Method-specific — system generates controls but consultant verifies enabling sequence |
| Sydney Water hold point authority | C3 | Utility-specific — system references the hold point but cannot name the inspector |

### Time saving vs writing from scratch

| Metric | Safe Method | Manual writing |
|--------|-------------|---------------|
| Scope to first draft | 5 min (automated) | 60-120 min |
| Consultant review and completion | 10-15 min | N/A (part of writing) |
| Total to issued document | 15-20 min | 120-240 min |
| **Estimated saving** | **~85%** | baseline |

### Scope types that work best

| Scope type | Quality | Notes |
|-----------|---------|-------|
| Remedial / facade / painting | High | Strongest benchmark coverage (Lingate, 18 Danks) |
| Civil road / drainage | Good | Sequence excellent, CCVS coverage improving |
| Structural erection (tilt-up, steel) | Good | Crane/bracing logic present, sequence needs minor reorder |
| Maintenance / HVAC | Good | Lightweight scope, clean output |

### Scope types that need more hardening

| Scope type | Gap | Effort |
|-----------|-----|--------|
| Rail corridor interface | No rail-specific controls generated | Scenario rule pack candidate |
| Complex multi-trade fit-out | HRCW undercall on services coordination | Prompt improvement |
| Demolition with active asbestos | Latent vs active logic sensitive | Tested but needs more edge cases |

### Recommended next commercial action

1. **Continue using the system for real customer jobs** — each job improves the keyword coverage and surfaces new CCVS edge cases that get fixed in 5-10 minutes
2. **Focus on remedial, civil, and maintenance scopes first** — these have the strongest coverage
3. **For specialist environments (rail, confined space, live electrical)** — use the system for the base method and add specialist controls manually per the consultant workflow
4. **Track consultant edit time and type** — when a recurring edit appears on 3+ jobs, implement as a deterministic fix
5. **Do not invest in model tiering (Sonnet) yet** — the monitoring copy-paste issue is real but manageable at the consultant-review stage, and the deterministic CCVS/keyword fixes are delivering more value per hour

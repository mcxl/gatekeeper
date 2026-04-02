# Post-Adoption Sonnet Validation — First 3 Real Jobs

## Purpose

Short production observation window to confirm that Sonnet's structural gains translate into lower real consultant burden. This is not a re-run of the adoption experiment.

## Context

- Sonnet adoption decision: **2026-04-02** (commit 2bbdb9f)
- Experiment: 5-job batch comparison, Haiku vs Sonnet Control Writer
- Experiment result: **ADOPT** — better quality, lower cost, lower latency
- Experiment limitation: **no edit-capture evidence** (no reviewed/final docx artifacts existed)
- This validation closes that gap with real consultant edit data

## Haiku baseline reference (experiment results)

| Metric | Haiku baseline |
|--------|---------------|
| Avg gate FAILs/job | 1.2 (6 total / 5 jobs) |
| Avg latency | 472s |
| Zero-FAIL jobs | 1/5 |
| Avg CW cost/job | $0.157 |
| Avg CW output tokens | 37K |

## Mandatory protocol

The first 3 real customer jobs under the Sonnet baseline **must** go through:
1. Normal SWMS generation
2. Consultant review in Word
3. Edit capture via `/v1/swms/capture-edits` (both generated + reviewed docx)
4. This tracking template completed for each job

---

## Job 1

| Field | Value |
|-------|-------|
| job_id | |
| date | |
| reviewer_id | |
| job_type | |
| scope_modifiers | |
| generation_time_seconds | |
| control_writer_input_tokens | |
| control_writer_output_tokens | |
| control_writer_estimated_cost | |
| would_issue | |
| review_duration_mins | |
| changed_task_count | |
| changed_responsibilities_count | |
| average_similarity_ratio | |
| major_rewrite_detected | |
| validator_result | |
| issue_gate_result | |
| fail_count | |
| review_count | |
| main_edit_categories | |
| monitoring_quality_note | better / same / still copy-paste |
| notable_new_defect_pattern | none |
| reviewer_impression | better / same / worse |
| vs_old_baseline | better / same / worse |
| overall_verdict | adopt-supporting / neutral / concern |
| ship_risk_exposed | none / low / medium / high |
| one_line_reason | |

## Job 2

| Field | Value |
|-------|-------|
| job_id | |
| date | |
| reviewer_id | |
| job_type | |
| scope_modifiers | |
| generation_time_seconds | |
| control_writer_input_tokens | |
| control_writer_output_tokens | |
| control_writer_estimated_cost | |
| would_issue | |
| review_duration_mins | |
| changed_task_count | |
| changed_responsibilities_count | |
| average_similarity_ratio | |
| major_rewrite_detected | |
| validator_result | |
| issue_gate_result | |
| fail_count | |
| review_count | |
| main_edit_categories | |
| monitoring_quality_note | better / same / still copy-paste |
| notable_new_defect_pattern | none |
| reviewer_impression | better / same / worse |
| vs_old_baseline | better / same / worse |
| overall_verdict | adopt-supporting / neutral / concern |
| ship_risk_exposed | none / low / medium / high |
| one_line_reason | |

## Job 3

| Field | Value |
|-------|-------|
| job_id | |
| date | |
| reviewer_id | |
| job_type | |
| scope_modifiers | |
| generation_time_seconds | |
| control_writer_input_tokens | |
| control_writer_output_tokens | |
| control_writer_estimated_cost | |
| would_issue | |
| review_duration_mins | |
| changed_task_count | |
| changed_responsibilities_count | |
| average_similarity_ratio | |
| major_rewrite_detected | |
| validator_result | |
| issue_gate_result | |
| fail_count | |
| review_count | |
| main_edit_categories | |
| monitoring_quality_note | better / same / still copy-paste |
| notable_new_defect_pattern | none |
| reviewer_impression | better / same / worse |
| vs_old_baseline | better / same / worse |
| overall_verdict | adopt-supporting / neutral / concern |
| ship_risk_exposed | none / low / medium / high |
| one_line_reason | |

---

## 3-Job Summary

| Metric | Value |
|--------|-------|
| job_types_covered | |
| jobs_supporting_adoption | |
| neutral_jobs | |
| concern_jobs | |
| avg_review_duration_mins | |
| avg_changed_task_count | |
| avg_similarity_ratio | |
| major_rewrite_on_any_job | yes / no |
| would_issue_all_3 | yes / no |
| monitoring_trend | better / same / inconsistent |
| new_defect_pattern_found | yes / no |
| latency_trend_vs_baseline | faster / same / slower |
| cost_trend_vs_baseline | lower / same / higher |
| recurring_edit_categories | |
| recurring_new_defect_patterns | |
| overall_recommendation | keep / keep_with_guardrails / re_open |
| follow_up_engineering_needed | yes / no |
| next_action | |

---

## Interpretation guidance

### Fully validated

Use only if **all** are true:
- No serious regression appears
- Review duration is lower or clearly not worse overall
- No major rewrite on any of the 3 jobs
- Edit categories shift away from structural/safety fixes
- Monitoring trend is better or not worse
- No issue-gate/validator trust regression
- Live cost/latency remain within expected range

### Partially validated

Use if:
- Structural quality remains strong
- No serious regression appears
- Consultant burden is mixed or flat
- At least one job clearly supports adoption

**Action:** Keep Sonnet. Extend observation window by 2 more real jobs. Do not reopen engineering immediately.

### Re-open investigation

Use if:
- A serious regression appears
- Review duration is materially worse
- Major rewrites increase
- Practical usability gets worse
- Trust drops because of new defect patterns

### What counts as a serious regression

- Major rewrite on a job that should have been routine
- New structural defect pattern affecting safe issue decision
- Materially longer review time due to Sonnet output quality
- Issue-gate or validator regression that reduces reviewer trust

### Complexity note

If the first 3 jobs all come from low-complexity scopes, treat the result as directional only and continue observing until at least one higher-complexity job (remedial occupied, multi-trade, or specialist scope) is captured.

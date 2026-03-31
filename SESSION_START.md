# Safe Method — Session Bootstrap
# Read this first. Begin work immediately after.
# Do not re-read other docs unless a specific gap requires it.

---

## OPERATING MODE
- Headless checkpoint-to-checkpoint
- Claude Code owns the terminal — run all commands directly, never present them for manual execution

## TERMINAL OWNERSHIP
- Execute all commands directly — never output a command for the operator to run manually
- No bash blocks presented for copy-paste
- No "run this in your terminal"
- No "you may need to execute"
- If a command needs to run, run it
- The only exception is an explicit operator override or a genuine unrecoverable blocker

---

## Platform identity
Product: Safe Method / Gatekeeper
Repo: C:\Users\AlanRichardson\gatekeeper
Railway deployment: active
Stack: FastAPI + Python

## Exact file paths — use these, do not explore
Issue gate:          src/issue_gate.py
Validator:           core/validator_runner.py
Orchestrator:        core/orchestrator.py
Reviewer agent:      core/reviewer_agent.py
Job-type rules:      core/job_type_rules.py
Decomposer prompt:   agents/decomposer.py
Control writer:      agents/control_writer.py
Shared prompts:      prompts/system.py, prompts/swms.py
Governance register: docs/BENCHMARK_GOVERNANCE_REGISTER.md
Reviewer rubric:     docs/reviewer_rubric.md
Generation rubric:   docs/SWMS_GENERATION_RUBRIC.md
Regression runner:   src/regression_runner.py
Findings store:      core/findings_store.py
Pattern detector:    core/pattern_detector.py
Rule promoter:       core/rule_promoter.py
Findings log:        src/data/findings_log.jsonl
Rule candidates:     src/data/rule_candidates.jsonl
Promotion log:       src/data/promotion_log.jsonl

## Current test count
[UPDATE THIS AFTER EVERY SESSION]
Passing: 516

## Issue gate check count
[UPDATE THIS AFTER EVERY SESSION]
Checks: 21

## Pipeline summary — one line each
Decomposer:       task architecture + job_type detection
Risk assessor:    hazards, HRCW, CCVS codes
Control writer:   dominant-hazard-first + _get_dominant_family() constraint injected per task
Assembler:        final SWMS assembly
Validator:        issue gate (20 checks) + PASS_INTERNAL / RETRY_INTERNAL / ESCALATE_EXTERNAL
Reviewer agent:   parallel Critic — 4 agents concurrent — recalibrated credibility floor active
Findings store:   captures all validator + reviewer findings to findings_log.jsonl
Pattern detector: surfaces rule candidates on demand from findings store
Rule promoter:    human-approved proposals — no source mutation in v1

## Stream statuses — update after every session
[UPDATE THESE AFTER EVERY SESSION]
Lingate remedial:           ACTIVE — V12 (monitoring copy-paste resolved, scaffold WAH override, 2 HF gen-variance, recommend external resubmission)
CLT install:                AWAITING_EXTERNAL_REVIEW
EWP roof access:            ACTIVE
18 Danks Street:            CLOSED — STRONG_WORKING_DRAFT_ONLY
Facade remedial:            CLOSED
SWMS Review Engine:         HOLD
Data centre RA:             CLOSED
Withers Road RA:            CLOSED
Withers Road control pack:  CLOSED

## Operating rules — always apply

NEVER
- Write to docs/BENCHMARK_GOVERNANCE_REGISTER.md
- Parse docs/reviewer_rubric.md at runtime
- Create a second Anthropic API client stack
- Push to GitHub unless explicitly instructed
- Touch closed-stream regression protection
- Block document output — validator and reviewer are advisory
- Stop for minor questions resolvable from this file
- Present bash commands for manual execution

ALWAYS
- Run pytest before every commit
- Use exact file paths listed above
- Use job_type values: new_build | fit_out | remedial | demolition | maintenance | civil
- Detect CLT and EWP from task text — not from job_type
- Commit after each phase with a non-interactive message
- End every session by updating this file
- Report the exact next prompt to paste

## Build / No-Build Filter

Before starting any new feature, phase, or subsystem, ask:

**Does this get Safe Method to trusted pilot use faster, or does it mainly make the system more elaborate?**

Build now only if most of these are true:
- real user benefit
- recurring proven problem
- narrow safe fix
- helps the five-job pilot
- customer/reviewer would notice
- low permanent complexity
- moves toward proof, trust, or revenue

Scoring:
- 6-7 = build now
- 4-5 = maybe, only if cheap and bounded
- 0-3 = defer

Default bias until the five-job pilot is complete:
- prefer benchmark closure over new architecture
- prefer narrow deterministic fixes over new subsystems
- prefer pilot workflow improvements over platform abstractions
- prefer proof over elegance
- prefer customer-visible gains over internal sophistication

## Terminology — use exactly
- job_type not "job family"
- values: new_build | fit_out | remedial | demolition | maintenance | civil
- CLT and crane detected from task text — not from job_type
- src/issue_gate.py not core/issue_gate.py
- docs/BENCHMARK_GOVERNANCE_REGISTER.md not governance/
- Reviewer agent = Critic specialisation — not replacement for 4-agent pipeline

## Defect taxonomy — classify all findings using these terms only
deterministic_fix | issue_gate_candidate | prompt_decomposer_fix |
case_specific_fix | expert_review_only | product_investment_gap |
deterministic_limit_reached

## Status model — use these terms only
CLOSED | ACTIVE | AWAITING_EXTERNAL_REVIEW |
CLOSED — STRONG_WORKING_DRAFT_ONLY |
BENCHMARK_QUALITY_CONFIRMED |
BENCHMARK_QUALITY_WITH_CAVEATS

## Validator outcomes — use these terms only
PASS_INTERNAL | RETRY_INTERNAL | ESCALATE_EXTERNAL

## Reviewer outcomes — use these terms only
BENCHMARK_QUALITY_CONFIRMED | BENCHMARK_QUALITY_WITH_CAVEATS |
STRONG_WORKING_DRAFT | BELOW_WORKING_DRAFT

## Recommended actions — use these terms only
PASS_TO_CLIENT | TARGETED_REWORK | FULL_REWORK

## What to do at the end of every session
1. Update test count in this file
2. Update issue gate check count in this file
3. Update stream statuses in this file
4. Update CLAUDE.md if any new assets were added
5. Report the exact next prompt to paste


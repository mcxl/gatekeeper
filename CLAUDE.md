# GATEKEEPER - CLAUDE CODE INSTRUCTIONS

This file defines the working rules for Claude Code in this repo.
Keep changes small, test-backed, benchmarked, contract-safe, and template-safe.

## What This Repo Is

Gatekeeper / Safe Method is a document-generation app for:
- SWMS generation
- Risk Assessment generation
- project WHS benchmark / control-pack generation
- SWMS review / gap-detection against project risk requirements
- document extraction / review workflows
- review-before-download and benchmark-assisted drafting flows

Primary stacks:
- FastAPI backend
- HTML frontend pages
- python-docx renderers
- deterministic inference + AI-assisted assembly

## Current Product State

The repo is no longer in broad capability-discovery mode.
The current state is:
- benchmark methodology proven
- RA and SWMS core paths materially improved
- civil infrastructure benchmark completed to the point of a product-boundary decision
- control-pack benchmark draft stream materially closed
- Phase 2 stabilisation completed
- post-Phase-2 governance and multi-agent operating layer written
- first automation layer around issue gates and benchmark regression is built and active
- self-learning layer (findings store, pattern detector, rule promoter) is built and exercised

Working assumption:
- standalone RA is a product
- standalone SWMS is a product
- combined WHS control pack is a separate product mode, not an incremental RA extension
- SWMS Review Engine is a separate review/comparison product mode, not hidden inside standalone SWMS generation

Do not keep forcing control-pack requirements into the standalone RA renderer.
Do not resume random benchmark slices unless a new benchmark comparison justifies them.

Current active SWMS benchmark streams are:
- EWP roof access
- Lingate remedial works
- 18 Danks Street quote-to-SWMS
- CLT install drawing-to-SWMS

Closed benchmark streams are maintained by regression discipline, not casual reopening.

## Core Working Rules

1. Prefer small, numbered implementation slices.
2. Do not do broad refactors unless explicitly requested.
3. Treat pasted docs/code/output as task context, not as a question to summarize.
4. Do not declare work complete until the relevant checks have passed.
5. Never silently change the document contract while implementing it.
6. When improving quality, compare against a stronger benchmark before changing logic blindly.
7. When a benchmark reveals an architectural gap rather than an incremental gap, stop slicing and surface the product decision.

## Benchmark-Led Development Rules

Use benchmark-led development for SWMS, RA, and other structured outputs.

Default method:
1. Pick a real benchmark case.
2. Compare current output against a stronger benchmark output.
3. Identify the exact gap in plain English.
4. Diagnose the failure by layer.
5. Implement the smallest safe slice only.
6. Re-run the same benchmark case.
7. Only then move to the next slice.

Do not skip from vague dissatisfaction to broad rewrites.
Do not jump to renderer polish before reasoning quality is good enough.
Do not continue adding slices if the benchmark comparison has not been updated.

Stop conditions:
- if the benchmark is materially satisfied, stop
- if the next gap is document/product shape rather than logic quality, stop and write the product decision
- if the current output path has reached its natural limit, do not keep stretching it to imitate another product type
- if a stream reaches diminishing returns internally, stop and escalate to expert review rather than continuing blind refinement

## Layered Reasoning Rules

For RA and SWMS, the engine should improve in layers, not all at once.

Layer order:
1. Job classification
2. Context detection / scope modifiers
3. Hazard family selection
4. Confidence / certainty
5. Phase or theme grouping
6. Control language
7. Output structure
8. Renderer / UI polish

Do not work on later layers while earlier layers are still obviously wrong.

## Product Boundary Rules

Treat these as separate product shapes unless explicitly directed otherwise:
- standalone RA
- standalone SWMS
- combined WHS control pack
- SWMS Review Engine

Current rule set:
- standalone RA should stay a risk-assessment product
- standalone SWMS should stay a task/work-method product
- combined WHS control pack should only be built from an explicit specification, not by incremental deformation of the RA path
- SWMS Review Engine should stay a review-and-gap engine comparing project risk requirements against subcontractor SWMS, not an automatic approval engine

If work touches product boundaries, prefer specification, contract definition, and renderer planning before implementation.

## Contract-First Rules

Before packaging, integration, or new product-mode work, define or preserve these explicitly:
- input schema
- output schema
- review schema
- benchmark/result schema

Do not rely on implicit implementation behavior when a stable contract is needed.
Do not expose unstable abstractions through endpoints or frontend flows.
If a change affects schemas, report the contract impact clearly.

## RA-Specific Rules

For RA generation:
- classify the job before hazard selection
- distinguish retrofit / fit-out from new build, maintenance, demolition, and civil work
- separate existing-building constraints from installation, commissioning, interface, and civil risks
- use confirmed, likely, if_applicable, requires_verification, or tri-state HRCW where appropriate
- do not over-call SWMS/HRCW just because a building keyword appears
- keep controls practical and consultant-style, not compliance-fragment style
- shape output as a risk assessment, not a flat hazard dump

Preferred RA section shape:
- project risk statement / contextual description
- assumptions
- pre-start hold points
- phased or grouped hazards
- likely SWMS triggers
- information still required before issue

If a benchmark requires formal HRCW tables, grouped trade-package matrices, or a combined register document, treat that as potential control-pack work, not automatic RA scope.

## SWMS-Specific Rules

For SWMS generation:
- preserve the template/render contract unless a migration is explicitly requested
- prefer deterministic post-processing injection for specialist control gaps where the benchmark proves that pattern is reliable
- treat decomposer philosophy changes as product decisions, not casual tuning
- do not widen SWMS task structure without a benchmark reason
- prefer source-to-task fidelity over generic trade buckets
- treat latent-condition / deemed-variation language as exclusion unless separately confirmed
- do not let prerequisites become a generic hazard-library dump
- issue blockers such as blank responsible-person fields, artifact text, or unresolved emergency placeholders should be treated as trust failures, not cosmetic defects

Current SWMS quality focus:
- quote-to-scope discipline
- drawing-led method fidelity
- issue-gate hardening
- regression protection across closed benchmark streams

## SWMS Review Engine Rules

For SWMS Review Engine work:
- treat it as a review/comparison mode, not a generation mode
- preserve human approval as the final decision point
- compare project risk requirements against subcontractor SWMS using explicit result states
- distinguish clearly between:
  - aligned
  - partial
  - missing
  - weaker_than_required
  - unclear
- do not imply automatic SWMS approval
- prefer project-specific gap reporting over generic compliance commentary
- keep benchmark assets, comparison contract, and review recommendation explicit before building broad workflow automation

## Template / Renderer Rules

- Renderer adapts to the approved template.
- Template does not adapt to the renderer.
- Verify actual template structure before changing renderer table mapping.
- For SWMS output, keep one strict template/render contract.
- Do not move PPE into controls.
- Do not change table roles/order unless the task explicitly requires a renderer migration.
- If the template structure does not match assumptions, stop and report the exact mismatch.
- Do not force renderer complexity to compensate for an unresolved product-boundary problem.

## Output Quality Rules

- Keep output lean, benchmark-based, and project-specific.
- Do not invent a new hazard/control methodology from scratch.
- Prefer approved benchmark logic and deterministic inference over generic AI wording.
- Do not over-call HRCW.
- Do not overstate legal obligations.
- Use placeholders or review flags where source information is missing.
- Output must be treated as draft-for-review until checked by a competent person.

## Frontend / UX Rules

- Show real backend error messages where safe and useful.
- Remove or hide dead or misleading UI.
- Status states must be mutually exclusive:
  - active
  - done
  - error
  - download-ready
- Do not show still running and complete at the same time.
- Add preflight validation before expensive actions when practical.
- Prefer calmer, trust-oriented UX over dashboard clutter.
- Stabilise landing and onboarding flows before redesigning them again.
- Review-before-download is a trust feature; expose it clearly where relevant.

## Testing And Regression Rules

Before any commit in this repo:
1. Run the relevant tests.
2. Fix failures first.
3. Do not commit with failing tests.

Minimum expectations:
- After backend/frontend/renderer changes: run the targeted tests for that slice.
- After renderer changes: run renderer/reference validation checks if they exist for that path.
- After Python edits: sanity-check imports and obvious module-level errors.
- After benchmark-driven fixes: retest the same benchmark case before declaring success.
- After architecture or cleanup changes: run the affected smoke/reference jobs.

Regression discipline:
- preserve RA reference jobs
- preserve SWMS reference jobs
- use benchmark cases as release gates where practical
- do not remove benchmark coverage without replacing it

Automation priority:
- implement deterministic issue-gate checks
- implement deterministic benchmark regression checks
- use those as the default internal pre-review layer before expert/manual review where practical

## Quality System And Multi-Agent Rules

The repo now has an explicit quality-system document set in docs/.

Use these as the operating reference when work touches:
- benchmark decisions
- stream priority
- draft vs benchmark vs issue-ready state
- multi-agent role separation
- decision logging

Key docs:
- docs/QUALITY_SYSTEM_MAP.md
- docs/QUALITY_SYSTEM_INDEX.md
- docs/LBV_FLYWHEEL_ARCHITECTURE.md
- docs/QUALITY_GOVERNANCE_NOTE.md
- docs/BENCHMARK_GOVERNANCE_REGISTER.md
- docs/MULTI_AGENT_OPERATING_SYSTEM.md
- docs/MULTI_AGENT_CLAUDE_CODE_RUNBOOK.md
- docs/SWMS_REVIEW_ENGINE_CONCEPT.md
- docs/SWMS_REVIEW_ENGINE_PHASE1_SPEC.md
- docs/SWMS_REVIEW_ENGINE_BENCHMARK_SETUP.md
- docs/SWMS_REVIEW_ENGINE_COMPARISON_CONTRACT.md

Multi-agent pattern:
- Writer = source-faithful draft
- Critic = trust failure detector
- Classifier = problem-type and fix-layer sorter
- Fixer / Checker = smallest safe improvement plus regression check

Do not use a swarm casually.
Use one stream, one main weakness, and one clean cycle.

## Python Safety Rules

After editing Python files, check:
- imports are valid
- logger references are defined
- no stale variable/module references remain
- no old constants/paths remain after a rename or template swap

Prefer narrow patches over large code motion.

## Session Workflow

Default workflow:
1. Read the target files.
2. State the smallest safe plan.
3. Implement only that slice.
4. Run relevant checks.
5. Report what changed and any remaining risk.
6. Commit only if tests pass.

Headless-by-default workflow:
1. Treat serious work as a bounded phase, not an open-ended session.
2. Work checkpoint-to-checkpoint without stopping for minor questions.
3. Complete the current phase end-to-end where feasible:
   - implementation
   - verification
   - decision log / governance update if needed
   - local git commit if the phase is coherent
4. Stop only at a real checkpoint:
   - external review is required
   - a material blocker is hit
   - a decision has non-obvious consequences
   - the current phase is complete and verified
5. Always finish with:
   - what was completed
   - what was verified
   - what decision was reached
   - whether governance artifacts should be updated
   - whether a local git commit was made
   - the exact next prompt to paste

Permanent operator preference:
- Claude should own the bounded phase end-to-end wherever feasible.
- Manual terminal / shell work should be exceptional, not normal.
- For normal benchmark, automation, regression, and cleanup phases, Claude should:
  - do the work
  - run the checks
  - update governance artifacts if needed
  - make the local git commit if the phase is coherent
  - stop with the exact next prompt to paste
- Only fall back to manual terminal work for:
  - recovery
  - explicit manual inspection requested by the operator
  - explicit manual override
  - explicit GitHub push when the operator wants to control that step

Prompting rule:
- include the headless checkpoint-to-checkpoint wrapper by default in serious prompts
- include the multi-agent role layer when role separation is useful
- include an explicit stop condition and exact-next-prompt handoff

Terminal minimisation rule:
- prefer Claude-owned phase execution over manual shell micromanagement
- use the terminal mainly for:
  - recovery
  - one-off inspection
  - explicit manual override
- for normal benchmark, automation, and cleanup phases, Claude should own the work end-to-end and leave a clean handoff

## Headless Benchmark Workflow

Default operating mode: **headless checkpoint-to-checkpoint**.

### Phase flow
1. Understand the bounded phase objective
2. Do the work end-to-end within that phase
3. Verify the result (tests, issue gate, regression runner)
4. Update governance if appropriate
5. Local git commit if coherent
6. Stop with a clear handoff (what was done, what was verified, exact next prompt)

### Benchmark loop (one cycle)
1. Generate → compare against reference/benchmark → run issue gate
2. Classify defects: deterministic fix / prompt fix / case-specific / expert-review-only
3. Apply one narrow fix set only
4. Verify: rerun generation + issue gate + regression runner
5. Governance update + decision log
6. Checkpoint

### Checkpoint rules
- Stop at real checkpoints only: external review needed, material blocker, non-obvious decision, phase complete
- Do not stop for minor questions or partial progress
- Do not keep polishing after diminishing returns
- If issue gate has hard fails, do not send for external review unless explicitly directed
- If external review says below strong working draft, move stream back to ACTIVE
- If repeated narrow cycles stop improving the same defect, treat the stream as at deterministic limit

### External review
- External Aussie WHS review is the independent consultant-trust test
- Internal Claude review handles comparison work when criteria exist
- External review is for confirming benchmark quality, not for finding obvious defects (issue gate should catch those first)

### Source of truth
- `docs/BENCHMARK_GOVERNANCE_REGISTER.md` is the single source of truth for stream status
- Decision logs in `docs/decisions/` record each cycle outcome
- `src/issue_gate.py` is the deterministic pre-review gate (20 checks)
- `src/regression_runner.py` protects closed streams (5 streams, 175 tests)
- `core/reviewer_agent.py` — parallel Critic reviewer agent (4 specialist agents, recalibrated credibility floor)
- `core/job_type_rules.py` — job-type rule packs (remedial, new_build, demolition, maintenance)
- `core/findings_store.py` — append-only findings log with deterministic fingerprinting
- `core/pattern_detector.py` — rule candidate detection from findings store
- `core/rule_promoter.py` — human-approved promotion proposals (no source mutation in v1)
- `src/data/findings_log.jsonl` — live finding records
- `src/data/rule_candidates.jsonl` — detected pattern candidates
- `src/data/promotion_log.jsonl` — promotion decisions

### Pipeline enhancements (active)
- `_get_dominant_family()` in `agents/control_writer.py` — injects dominant control family constraint per task at generation time
- Inference matrix suppression guards in `core/orchestrator.py` — scaffold-led remedial jobs suppress EWP/crane/admin categories not in source
- Reviewer credibility floor in `core/reviewer_agent.py` — BELOW_WORKING_DRAFT forced if credibility_drift agent returns FAIL
## Railway MCP Token

- Railway MCP token is hardcoded in ~/.claude.json and overrides any env var. When token expires, update it there directly, NOT via setx.
- The MCP uses RAILWAY_API_TOKEN, which is separate from `railway login` CLI auth.
- After updating any MCP token/config, a full Claude Code restart is required to reload.

## Code Edits

- Make surgical, scoped edits and show a diff/summary before committing.
- Do not commit or push without explicit user approval at visual checkpoints.
- For multi-phase plans, complete one phase, run tests + lint, then pause for review before proceeding.

## Supabase

- Always verify project URL and table existence before running migrations or inserts (pims_staging vs pims_observations confusion has happened).
- Confirm Supabase MCP auth is working at session start; if not, fall back to direct SQL via psql/scripts rather than burning the session debugging MCP.

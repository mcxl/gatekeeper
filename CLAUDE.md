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
- first automation layer around issue gates and benchmark regression is now the main outstanding system task

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

Benchmark workflow:
1. Compare current output to benchmark output.
2. Identify top 1-3 gaps only.
3. Pick the next slice.
4. Implement that slice only.

# Session summary — 2026-03-30

## What was completed

- Phases A-G of validator upgrade: 20 issue gate checks, job-type rule packs, reviewer rubric, prompt non-negotiables, parallel reviewer agent
- Reviewer agent recalibration: credibility floor enforced
- Inference matrix suppression guards: scaffold-led remedial
- Dominant control family injection: _get_dominant_family() per task in control writer
- HRCW boolean contradiction fix: _normalise_task()
- Membrane false positive fix: _check_unsupported_controls_json() — job-scope-aware detection
- Demob CCVS correction: _correct_ccvs_by_task_type() — demob/reinstatement tasks to SYS-M3
- Self-learning layer: findings_store, pattern_detector, rule_promoter — all committed and tested
- First live flywheel run: local Python with dotenv, 231 findings captured, 4 pattern candidates detected, 1 promotion approved
- Lingate V5, V6, and V7 generated and validated

## Current test count

504 passing

## Lingate stream status

ACTIVE — deterministic limit reached (V7: 0 hard fails, 54 review items)

Fixes applied across V5-V7:
- Membrane false positive: RESOLVED
- HRCW boolean contradiction: RESOLVED (0 contradictions, was 7)
- Demob CCVS WAH-H6 → SYS-M3: RESOLVED
- ccvs_coverage gap: RESOLVED

Remaining V7 review items are architecture/sequencing — prompt-quality issues:
- Isolate/barricade task sequencing relative to scaffold
- Inspection/QA task ordering
- Hold point specificity (named consultant approval authority)
- Framework vs work-package CCVS duplication

## Architecture decisions made

1. Improvement 5 standalone (dominant control family injection) chosen over Improvement 2 (decomposer schema extension). Keyword lookup at generation time is sufficient. Improvement 2 deferred indefinitely.

2. Improvement 1 (pre-generation brief agent) deferred. Decomposer prompt already contains job-type rules. Brief agent adds API cost for deterministic data.

3. Improvement 3 (retry with error feedback) deferred. Retry loop does not re-call agents (confirmed at line 296 core/validator_runner.py). Fix upstream at generation time.

4. Improvement 4 (reference SWMS ingestion) deferred. Risk of template contamination outweighs benefit. Reference used for validation not generation.

5. Rule promoter v1: no source mutation. Approval generates PromotionProposal only. Proposal is the next Claude Code implementation prompt. Source mutation deferred to v2 after stability proven.

6. Patch stub quality gap recorded as product_investment_gap in findings store. auto_generatable=False candidates currently produce comment-style templates rather than implementation-ready patch stubs.

## What is not ready yet

- Procore integration: reviewer calibration still maturing
- Full production deployment: needs durable storage, tenant-safe audit logs, versioned outputs
- 5-job blind pilot: not yet run — required before claiming production validation

## Next session focus

Implement decomposer prompt sequencing improvements:
- Isolate/barricade tasks BEFORE scaffold erection
- Inspection/QA tasks AFTER all construction tasks
- Demob/reinstatement AFTER occupant space reinstatement
- Named consultant hold points must specify approval authority

Then regenerate Lingate V8 and compare against V7 baseline.
Do not resubmit externally until V8 reviewed internally.

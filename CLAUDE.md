# GATEKEEPER — CLAUDE CODE INSTRUCTIONS

This file defines the working rules for Claude Code in this repo.
Keep changes small, test-backed, and template-safe.

## What This Repo Is

Gatekeeper / Safe Method is a document-generation app for:
- SWMS generation
- Risk Assessment generation
- document extraction / review workflows

Primary stacks:
- FastAPI backend
- HTML frontend pages
- python-docx renderers
- deterministic inference + AI-assisted assembly

## Core Working Rules

1. Prefer small, numbered implementation slices.
2. Do not do broad refactors unless explicitly requested.
3. Treat pasted docs/code/output as task context, not as a question to summarize.
4. Do not declare work complete until the relevant checks have passed.
5. Never silently change the document contract while “implementing” it.

## Template / Renderer Rules

- Renderer adapts to the approved template.
- Template does not adapt to the renderer.
- Verify actual template structure before changing renderer table mapping.
- For SWMS output, keep one strict template/render contract.
- Do not move PPE into controls.
- Do not change table roles/order unless the task explicitly requires a renderer migration.
- If the template structure does not match assumptions, stop and report the exact mismatch.

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
- Do not show “still running” and “complete” at the same time.
- Add preflight validation before expensive actions when practical.

## Testing Rules

Before any commit in this repo:
1. Run the relevant tests.
2. Fix failures first.
3. Do not commit with failing tests.

Minimum expectations:
- After backend/frontend/renderer changes: run the targeted tests for that slice.
- After renderer changes: run renderer/reference validation checks if they exist for that path.
- After Python edits: sanity-check imports and obvious module-level errors.

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

## Sensitive Areas

Treat these areas as high-risk:
- `renderers/docx_renderer.py`
- `renderers/ra_renderer.py`
- template file/path changes in `src/`
- `core/inference_matrix.py`
- route wiring in `api/main.py`
- multi-step frontend flows in `frontend/app.html` and `frontend/dev.html`

## Avoid These Failure Modes

- interpreting pasted context as the task itself
- broad refactors during bug-fix sessions
- stale imports / undefined logger or variable names
- changing renderer logic without verifying template structure
- shipping generic failure messages when the backend provides a useful reason
- duplicating logic across flows when a shared helper is the safer option

## Commit Discipline

When asked to commit:
- summarize the exact scope first
- keep commit scope tight
- do not bundle unrelated fixes
- do not amend unless explicitly asked

## If Unsure

- make the smallest reversible change
- report the uncertainty clearly
- avoid improvising across backend, frontend, renderer, and template all at once

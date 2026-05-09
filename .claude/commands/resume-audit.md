# Resume SSA Audit

Resume an SSA audit folder from the last green phase recorded in
`.ssa_state.json`. This is the operator-facing wrapper around
`python -m pims.scripts.run_ssa_pipeline --resume <folder>`.

## Inputs

- **Required:** absolute path to the audit folder (under
  `G:\My Drive\alan_mcxico\SSA-evidence\`).
- If no folder is provided, do **not** guess. Glob the SSA-evidence
  root for sub-folders that contain `.ssa_state.json` sorted by mtime
  desc, list the 3 most recent, and ask the operator to pick one.

## Process

1. **Verify** the folder exists and contains `.ssa_state.json`. If
   missing, tell the operator to start the audit with
   `python -m pims.scripts.run_ssa_pipeline <folder> --enrich-only`
   instead of resuming.
2. **Read** the sidecar and report the `run_status` block:
   - last_completed_phase
   - last_attempted_phase
   - last_run_at
   - last_exit_code (call out non-zero explicitly)
   - last_error (if present)
   - next_suggested_phase
3. **Decide** what `--resume` will do:
   - non-zero `last_exit_code` → re-run `last_attempted_phase`
   - else → run `next_suggested_phase`
   - terminal (no `next_suggested_phase` after a green
     `from-report` / `full-run`) → audit complete; nothing to do.
4. **State** the chosen phase to the operator and what files it will
   produce (enriched xlsx for `enrich-only`; report.docx + staging
   xlsx for `from-state`; refreshed enriched + staging for
   `from-report`).
5. **Wait for explicit "go"** before running anything (per the
   checkpoint rule). Do not auto-execute.
6. **Run** `python -m pims.scripts.run_ssa_pipeline <folder> --resume`
   on approval. Surface stdout/stderr verbatim.
7. **Re-read** `.ssa_state.json` after the run and show the updated
   `run_status` so the operator sees what changed.

## Rules

- Never invoke `--resume` automatically — always pause for "go".
- Never delete or modify files in the audit folder outside what the
  pipeline writes.
- Never push or commit anything as part of resuming an audit.
- If the operator's edits to the enriched xlsx or report docx are
  unsaved (e.g. file lock visible), tell them to close the file before
  resuming — the pipeline reads those files mid-phase.
- If `last_exit_code != 0` and the previous error suggests an input
  problem (missing CSV, malformed photo, RA docx absent), surface the
  error and suggest a fix rather than blindly re-running the same
  failing phase.

## Out of scope

- Multi-folder batch resume (operator picks one folder at a time).
- Auto-discovery of which folder to resume — explicit folder only.
- Modifying the resume phase choice (use the underlying CLI flags
  directly if you need to override).

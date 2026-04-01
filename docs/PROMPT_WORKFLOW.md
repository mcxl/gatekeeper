# Prompt Workflow

Local developer tool for generating paste-ready Claude Code session prompts.

## File locations

| What | Where |
|------|-------|
| Templates | `prompts/session_templates/*.md` |
| Partials | `prompts/partials/_*.md` |
| Job briefs | `job_briefs/*.json` |
| Generator | `scripts/make_prompt.py` |

## Placeholder syntax

- `{{field}}` — replaced with the matching field from the job brief JSON
- `{{>partial_name}}` — replaced with the content of `prompts/partials/_partial_name.md`

Partials are resolved first, then field placeholders.

## Array rendering

- `scope_modifiers` → comma-separated inline
- `quick_scan_focus` → bulleted list (one per line)
- `batch_jobs` → bulleted list (one per line)
- Other arrays → comma-separated

## Usage

```bash
# List available templates and briefs
python scripts/make_prompt.py --list

# Dry run — check which fields are present/missing
python scripts/make_prompt.py -t next_pilot_job -b job_briefs/urban_flow_plumbing.json --dry-run

# Generate full prompt to stdout
python scripts/make_prompt.py -t next_pilot_job -b job_briefs/urban_flow_plumbing.json

# Pipe to clipboard (Git Bash on Windows)
python scripts/make_prompt.py -t next_pilot_job -b job_briefs/urban_flow_plumbing.json | clip
```

## What --list shows

- All templates by name
- All partials by name
- All briefs with customer, job type, and run count

## What --dry-run shows

- Each placeholder in the template
- Whether the brief has a matching field
- A preview of the value
- Whether the render would succeed or fail

## Brief metadata

After a successful (non-dry-run) generation:
- `last_used` is updated to the current UTC timestamp
- `jobs_run` is incremented by 1

## Adding a new job

1. Create `job_briefs/your_job.json` with required fields
2. Run `--dry-run` to verify all fields present
3. Run full generation and paste into Claude Code

---

## Batch Comparison Harness

Developer tool for running multiple job briefs through the pipeline and producing a structured comparison report.

### Usage

```bash
# Run all briefs
python scripts/run_batch_harness.py --all

# Run specific briefs
python scripts/run_batch_harness.py job_briefs/c01_unitas_roofing.json job_briefs/c08_podium_slab.json

# Dry run — list jobs without running
python scripts/run_batch_harness.py --all --dry-run
```

### Output

Reports are written to:
- `src/outputs/batch_comparison_latest.json` — machine-readable
- `src/outputs/batch_comparison_latest.md` — human-readable table

### What the report contains

Per job: brief ID, customer, job type, task count, validator status, gate FAIL/REVIEW counts, notable flags, elapsed time.

Summary: validator status breakdown, total gate FAIL/REVIEW counts, zero-FAIL job count, averages, most-FAILs job.

### When to use

- Before/after model or prompt changes — compare gate results
- Regression check across all pilot jobs
- Quick health check of the current pipeline

---

## JSON Fixtures for Deterministic Testing

Pipeline output fixtures in `tests/fixtures/pipeline_outputs/` enable fast issue-gate and CCVS-correction testing without LLM calls.

### Where fixtures live

- `tests/fixtures/pipeline_outputs/*.json` — saved task lists from pilot jobs
- Each fixture has `label`, `job_type`, and `tasks` array

### When to use fixture-based tests

- Testing issue gate check logic (C1-C33)
- Testing `_correct_ccvs_by_task_type()` keyword coverage
- Testing `_task_phase_score()` sequence logic
- Testing unsupported-controls scope-awareness
- Any deterministic logic that operates on task dicts

### Parallel test execution

pytest-xdist is installed for parallel execution:

```bash
# Normal sequential run
pytest

# Parallel with auto-detected workers
pytest -n auto

# Parallel with specific worker count
pytest -n 4
```

All tests are compatible with both sequential and parallel execution.

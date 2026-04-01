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

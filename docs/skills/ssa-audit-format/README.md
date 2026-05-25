# SSA Audit Format Skill (master copy)

This is the **repo-versioned master copy** of the Claude skill that enforces
the SSA Audit Report format contract. The active Claude skill must live at:

```
~/.claude/skills/ssa-audit-format/SKILL.md
```

This directory is the canonical source. Any change to the skill goes here
first, then gets copied to the global location.

## Installation (one-time, per workstation)

PowerShell:
```powershell
# From gatekeeper repo root:
New-Item -ItemType Directory -Force "$HOME/.claude/skills/ssa-audit-format" | Out-Null
Copy-Item -Force docs/skills/ssa-audit-format/SKILL.md "$HOME/.claude/skills/ssa-audit-format/SKILL.md"
```

Bash / Git Bash:
```bash
mkdir -p ~/.claude/skills/ssa-audit-format
cp docs/skills/ssa-audit-format/SKILL.md ~/.claude/skills/ssa-audit-format/SKILL.md
```

## Verification

After installing, the skill should appear in Claude Code's available skills
list as `ssa-audit-format`. Start a new Claude Code session and check.

## When to update

When you edit `SKILL.md` here (e.g. to add a new client to the rules), also
re-run the install command above so your local `~/.claude/skills/` copy
matches.

## Why two copies

- **Repo copy** (`docs/skills/ssa-audit-format/SKILL.md`): version-controlled,
  reviewable, survives machine swaps and backups.
- **Global copy** (`~/.claude/skills/ssa-audit-format/SKILL.md`): what Claude
  Code actually loads at session start.

The global location is fixed by Claude Code's skill-discovery mechanism;
the repo location is our convention for keeping it versioned.

## Cross-reference

- The skill enforces `docs/SSA_FORMAT_CONTRACT.md` (the rules).
- The rules cite constants in `pims/services/ssa_format_constants.py`.
- The constants are pinned by `tests/test_audit_report_format_contract.py`.
- The test is run by the `ssa-format-contract` pre-commit hook in `.pre-commit-config.yaml`.

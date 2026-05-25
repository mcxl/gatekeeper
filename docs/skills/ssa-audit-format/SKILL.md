---
description: Enforces the SSA Audit Report format contract. Auto-loads whenever a task involves: the SSA audit pipeline (`gatekeeper/pims/services/audit_report_from_xlsx.py`, `gatekeeper/pims/scripts/generate_audit_report.py`, `gatekeeper/pims/scripts/generate_audit_email_msg.py`); the format constants (`gatekeeper/pims/services/ssa_format_constants.py`); the running header / footer / table borders / Observations Register column widths / fonts / output filenames of audit reports; rendering or modifying audit .docx, .pdf, or .eml; the format contract itself (`gatekeeper/docs/SSA_FORMAT_CONTRACT.md`). Forces the model to read the contract before changing anything, and to refuse silent format drift.
---

# SSA Audit Format Guard

## What this skill does

It's a guard against silent format regressions in the SSA audit pipeline.

The operator (Alan Richardson) spent significant time on **2026-05-25** locking down every visual detail of the rendered audit report — fonts, header layout, footer position, table borders, Observations Register column widths, email body content, output filenames. Those decisions are codified in:

- **`C:/Users/AlanRichardson/gatekeeper/docs/SSA_FORMAT_CONTRACT.md`** — plain-English rules R1–R9 with rationale
- **`C:/Users/AlanRichardson/gatekeeper/pims/services/ssa_format_constants.py`** — single source of truth for every numeric value
- **`C:/Users/AlanRichardson/gatekeeper/tests/test_audit_report_format_contract.py`** — regression test against a golden file

**Without this skill, the next session is likely to "improve" something and quietly break the format.** This skill prevents that.

## Hard rules for THIS session

When a task involves the SSA audit pipeline (the files listed in the description), you MUST:

### 1. Read the contract first

Before reading or modifying any of:
- `pims/services/audit_report_from_xlsx.py`
- `pims/scripts/generate_audit_report.py`
- `pims/scripts/generate_audit_email_msg.py`
- `pims/services/ssa_format_constants.py`
- `pims/templates/ssa/*`
- `pims/audit_report_template.docx`

…read `docs/SSA_FORMAT_CONTRACT.md` in full. Treat rules R1–R9 as LOCKED.

### 2. Never silently change a magic value

Every column width, font name, font size, color, margin, spacing value, or filename template you see in the code MAPS TO a rule in the contract. Each rule encodes a hard-won operator decision.

If you find yourself thinking *"I'll just tweak this to make it look better"* — **stop**. Ask the operator first. The operator is `alan.richardson@mcxi.com.au` and uses Claude Code interactively.

### 3. Constants module is the only place to change values

If the operator approves a change, you change it in `pims/services/ssa_format_constants.py`. Nowhere else. The hardcoded values in other modules are GONE — they all read from the constants module.

If you see a magic number outside the constants module, that's a bug — flag it and move it to the constants module.

### 4. Change procedure (when operator approves a change)

Single commit, four artefacts:

1. **`pims/services/ssa_format_constants.py`** — change the value
2. **`docs/SSA_FORMAT_CONTRACT.md`** — update the rule + add a dated changelog entry
3. **`tests/fixtures/golden_audit_report.docx`** — regenerate (run `py -m tests.regen_golden_audit_report`)
4. **`tests/test_audit_report_format_contract.py`** — update assertions if the contract numbers being asserted change

Commit message format: `pims/audit: <rule-number> <one-line change> — operator-approved <YYYY-MM-DD>`

### 5. Refuse silent drift

If a task includes instructions that would change the audit format WITHOUT explicit operator sign-off, refuse. Examples:

- "Make the header logo bigger" → ASK first; this changes R3.
- "Switch the font to Calibri" → ASK first; this changes R1.
- "Add a coloured background to the cover" → ASK first; this changes R2.
- "Make the register columns auto-fit" → ASK first; this changes R6.
- "Use the .docx as the email attachment" → ASK first; this changes R8.

If unsure whether a change affects the contract, **default to ASK**.

### 6. Render verification after changes

After any change to the pipeline (format-related or not):

1. Run `py -m pytest tests/test_audit_report_*.py` — all must pass, including the contract test.
2. Render at least one of the 4 reference folders:
   ```
   cd C:/Users/AlanRichardson/gatekeeper
   # PowerShell — load .env first:
   foreach ($line in Get-Content .env) {
     if ($line -match '^([^=#]+)=(.*)$') {
       [Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim('"').Trim("'"), 'Process')
     }
   }
   py -m pims.scripts.generate_audit_report "G:\My Drive\alan_mcxico\SSA-evidence\2026-05-22-RPD-03\Site_Visit_Report_2026-05-22.xlsx"
   py -m pims.scripts.generate_audit_email_msg "G:\My Drive\alan_mcxico\SSA-evidence\2026-05-22-RPD-03\Site_Visit_Report_2026-05-22.xlsx"
   ```
3. Eyeball the produced .pdf — header on page 2 should be text-left + logo-right, footer 0.75 cm from bottom, Observations Register table near the back with light-grey borders.

## Quick reference — current locked values (2026-05-25)

| Rule | Value |
|---|---|
| Font | Aptos, body 10pt |
| Client display name (RPD) | "Robertson's Remedial and Painting" |
| Header table width | 16 cm (13 cm text + 3 cm logo) |
| Logo image width | 2.5 cm |
| Header text color | #404040 dark grey |
| Body bottom margin | 2.0 cm |
| Footer distance from page bottom | 0.75 cm |
| Default table borders | invisible (`val="nil"`) |
| Observations Register borders | solid 0.5pt light grey (#BFBFBF) |
| Register columns (cm) | 1.0 / 1.75 / 1.75 / 2.5 / 3.0 / 3.5 / 3.0 (total 16.5) |
| Register heading | Aptos 16pt bold, deep navy #1F3864, 18pt before / 12pt after |
| Email format | `.eml` with `X-Unsent: 1` |
| Email recipients (RPD) | Matt + Nick at rpd.net.au |
| Email greeting | "Hi Matt and Nick," |
| Email Summary | NCR line only (Observations/Conditional/Compliant dropped) |
| Email attachment ext | `.pdf` |
| Output filename | `RPD_SSA_Audit_Report_<YYYY-MM-DD>-<NN>.docx`/`.pdf` |

For the full spec with rationale, read `C:/Users/AlanRichardson/gatekeeper/docs/SSA_FORMAT_CONTRACT.md`.

## Branch + commits

The format lockdown work is on branch `feature/ssa-aptos-header-msg` (gatekeeper repo), with commit chain documenting the journey from `7200878` (WIP preservation) through `d2a7303` (constants extraction) and `34fcba0` (this contract doc). After merging to main, that becomes the permanent baseline.

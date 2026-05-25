# How to Run an SSA Audit (operator playbook)

End-to-end procedure for producing the three audit deliverables (docx,
pdf, eml) from an evidence folder.

**Format is locked.** This doc explains the *invocation* only. For what
the deliverables look like and why, see `docs/SSA_FORMAT_CONTRACT.md`.

---

## Quick reference (the 3 commands)

```powershell
cd C:\Users\AlanRichardson\gatekeeper

# One-time per shell session: load the API key
foreach ($line in Get-Content .env) {
  if ($line -match '^([^=#]+)=(.*)$') {
    [Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim('"').Trim("'"), 'Process')
  }
}

# Render docx + pdf (Sonnet calls: ~$0.15 per folder, ~30s)
py -m pims.scripts.generate_audit_report "G:\My Drive\alan_mcxico\SSA-evidence\<FOLDER>\Site_Visit_Report_<DATE>.xlsx"

# Render .eml draft
py -m pims.scripts.generate_audit_email_msg "G:\My Drive\alan_mcxico\SSA-evidence\<FOLDER>\Site_Visit_Report_<DATE>.xlsx"
```

---

## Setting up an evidence folder

1. **Create the folder** under `G:\My Drive\alan_mcxico\SSA-evidence\`
   with the canonical name: `YYYY-MM-DD-<CLIENT>-NN`
   - Example: `2026-05-22-RPD-03`
   - `YYYY-MM-DD` = audit date
   - `<CLIENT>` = `RPD` (or `SDG` etc. once mapped in `ssa_format_constants.py`)
   - `NN` = zero-padded sub-id for that date (`01`, `02`, …)
   - **Non-canonical folder names work but degrade**: NN defaults to `01`
     and a warning prints to stderr.

2. **Drop these into the folder**:
   - `Site_Visit_Report_<DATE>.xlsx` — the audit data (PIMS export
     format). The xlsx filename's date doesn't have to match the
     folder's date; the folder name wins for output naming.
   - `<FOLDER>-photos/` — sibling folder of jpgs referenced by
     `photo_refs` in the xlsx. Auto-discovered. The folder name must
     end in `-photos`.

3. **Optional**:
   - Previous audit `.docx` in the same folder triggers
     carry-forward parsing for the Status of Previous Recommendations
     table (handled by `populate_prior_recs_table.py`, see below).

---

## Step 1 — Render docx + pdf

```powershell
cd C:\Users\AlanRichardson\gatekeeper
# (load .env once per shell session — see Quick reference above)
py -m pims.scripts.generate_audit_report "G:\My Drive\alan_mcxico\SSA-evidence\2026-05-22-RPD-03\Site_Visit_Report_2026-05-22.xlsx"
```

What happens:
- Three Sonnet API calls (planning tier probe → main mapping → exec
  summary). About 10–15 seconds. ~$0.15 worth of API spend.
- Word opens in the background, renders the docx to pdf via COM, closes.
  Don't have the same docx open in Word during this step — you'll get
  `PermissionError`. Close it first.

Output:
- `RPD_SSA_Audit_Report_<DATE>-<NN>.docx` (locked filename per R9)
- `RPD_SSA_Audit_Report_<DATE>-<NN>.pdf` (sibling, same basename)

Flags:
- `--no-pdf` — skip the PDF render if Word is busy/unavailable
- `--prepared-by "Name"` — override default Alan Richardson on cover
- `--no-enrich-findings` — skip wording enrichment

---

## Step 2 — Render the email draft

```powershell
py -m pims.scripts.generate_audit_email_msg "G:\My Drive\alan_mcxico\SSA-evidence\2026-05-22-RPD-03\Site_Visit_Report_2026-05-22.xlsx"
```

Output:
- `Email_Draft_<YYMMDD>_<site-slug>.eml`

Double-clicking the .eml opens it in Outlook as an **editable draft**
(thanks to the `X-Unsent: 1` header). To: is pre-filled with Matt +
Nick at rpd.net.au. Body greeting: "Hi Matt and Nick,". Attachment
line references the sibling .pdf.

Flags:
- `--legacy-txt` — also emit the old `.txt` format alongside the .eml

---

## Step 3 — Issue the report

1. Open the `.pdf` in Acrobat — eyeball the cover, page 2 header, and
   Observations Register near the back. Confirm Aptos font throughout.
2. Open the `.eml` in Outlook — confirm To/Subject/Body, then attach
   the `.pdf` if Outlook didn't auto-attach (it doesn't; that's
   manual).
3. Hit Send.

---

## Doing all folders at once (batch)

```powershell
cd C:\Users\AlanRichardson\gatekeeper
foreach ($line in Get-Content .env) {
  if ($line -match '^([^=#]+)=(.*)$') {
    [Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim('"').Trim("'"), 'Process')
  }
}
$folders = @('2026-05-22-RPD-01','2026-05-22-RPD-02','2026-05-22-RPD-03')
foreach ($f in $folders) {
  Write-Host "=== $f ==="
  $xlsx = Get-ChildItem "G:\My Drive\alan_mcxico\SSA-evidence\$f\Site_Visit_Report_*.xlsx" | Select-Object -First 1
  py -m pims.scripts.generate_audit_report $xlsx.FullName
  py -m pims.scripts.generate_audit_email_msg $xlsx.FullName
}
```

About 30–45 seconds per folder. Close any open audit docx in Word
before starting or one folder will fail mid-batch with `PermissionError`.

---

## Troubleshooting

### `ANTHROPIC_API_KEY not set in environment`
You forgot the `.env` loader incantation at the top of the session. Run
it again (see Quick reference). The script tries to load `.env` itself
but the loader silently does nothing if your shell already has the
variable set to empty or whitespace — easier to just preload it via
PowerShell.

### `PermissionError: [Errno 13] Permission denied: ...RPD_SSA_Audit_Report_...docx`
The docx is open in Word. Close it and re-run.

### `Outlook COM failed: CO_E_SERVER_EXEC_FAILURE`
You wouldn't see this with the current `.eml` writer — that error was
from the old `.msg` (Outlook COM) writer which was retired. If you see
this, you're somehow running the old code path. Check you're on `main`
at commit `9a42f07` or later.

### PDF render produces a 0-byte file or hangs
Word COM is fragile. Three things to try in order:
1. Close all Word windows.
2. Re-run with `--no-pdf` to confirm the docx renders, then run a
   separate `docx2pdf` command manually.
3. Reboot Word's COM server: `taskkill /f /im winword.exe` then retry.

### Folder name not matching `YYYY-MM-DD-<CLIENT>-NN`
Pipeline still runs but uses fallback: NN=01 and audit_date from the
xlsx. You'll see a stderr warning. Rename the folder to canonical form
for clean output.

### Cover page or header looks wrong
You hit a real format regression — should be impossible if the contract
test is passing (51 pins). Open `docs/SSA_FORMAT_CONTRACT.md` and
verify against the locked rules, then check `git log` for any commits
touching `pims/services/ssa_format_constants.py` since
`2026-05-25`.

---

## After the audit — Status of Previous Recommendations

For audits where a prior audit's `.docx` exists in the same folder:

```powershell
py -m pims.scripts.populate_prior_recs_table "<docx path>" --audit-date <DD-MMM-YYYY>
```

Produces a `<docx>-tracked.docx` with the prior recs table populated
under tracked changes by "Claude". Open in Word, review the Review
tab, fill the Status column. Not covered by the format lockdown (this
is a separate, older script).

---

## The format contract — DO NOT EDIT WITHOUT READING

The visual appearance of every deliverable above is governed by:

- **Rules document**: `docs/SSA_FORMAT_CONTRACT.md` (R1–R9, locked
  2026-05-25)
- **Constants module**: `pims/services/ssa_format_constants.py` (every
  number, font, color, filename template)
- **Claude skill**: `~/.claude/skills/ssa-audit-format/SKILL.md`
  (master copy at `docs/skills/ssa-audit-format/SKILL.md`) — auto-loads
  in Claude Code sessions and refuses silent format changes
- **Regression test**: `tests/test_audit_report_format_contract.py`
  (51 pinned constants; runs on every commit via pre-commit hook)

**To change a format rule**: update all four artefacts in one commit.
The change procedure is documented in the contract itself.

If a future you (or a future Claude session) is tempted to "improve"
the format — stop. Re-read the contract. Confirm the rule change is
intentional. Then follow the change procedure.

---

## Cross-reference

- `pims/scripts/generate_audit_report.py` — docx + pdf builder CLI
- `pims/scripts/generate_audit_email_msg.py` — .eml builder CLI
- `pims/services/audit_report_from_xlsx.py` — the docx-building engine
- `pims/services/ssa_format_constants.py` — locked format values
- `docs/SSA_FORMAT_CONTRACT.md` — plain-English format rules + changelog
- `docs/skills/ssa-audit-format/SKILL.md` — Claude session guard
- `tests/test_audit_report_format_contract.py` — 51-pin regression test
- `.pre-commit-config.yaml` — runs the contract test on every commit

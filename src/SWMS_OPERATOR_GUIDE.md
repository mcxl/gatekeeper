# SWMS OPERATOR GUIDE — v16.3
# Consolidated from: FINAL_MANIFEST.md + CLAUDE_PROJECT_GUIDE.md

**System:** SWMS Generator — Australian Construction, Any Industry
**Version:** v16.3
**Updated:** 20/02/2026
**Owner:** Robertson's Remedial and Painting Pty Ltd

---

## WHAT THIS SYSTEM IS

A frozen-engine Word document generator for Safe Work Method Statements.

**"Frozen"** means the formatting, cell mapping, and table logic are locked in
validated Python functions. Only three user-data sections change per job —
PROJECT, TASKS, REQUIREMENTS. The engine cannot be broken by AI rewriting
structural code, because AI is only permitted to edit the data sections.

**Two output tables per document:**
- **Consolidated** — short, verb-driven, one line per task. Must pass the
  defensibility standard in SWMS_CONSOLIDATED_RULES.md. Worker reads the full
  picture in under 30 seconds.
- **Detail** — complete risk assessment with full hazard text, hierarchy-structured
  controls, colored risk cells, and short codes.

**Short codes** (e.g. `WAH-H6`, `ASB-H9`) auto-generated from audit string and
pre-score. H-tier suffix bold black. No colour needed — bold weight is sufficient.

---

## FILE MANIFEST

### Core files (required for generation):

| File | Purpose | Edit? |
|---|---|---|
| `SWMS_BASE_GENERAL.py` | General engine v16.3 — any job type, auto-injects SYS + EMR | ✏️ Sections 1, 2, 3 only |
| `swms_bulletize.py` | Bullet post-processor — converts consolidated table col 3 to ▪ bullets, preserves CCVS bold+yellow | ❌ Never edit |
| `SWMS_Template.docx` | Word template — 10 tables, validated 19/02/2026 | ❌ Never |

### Reference files (read before generating):

| File | Purpose | Edit? |
|---|---|---|
| `SWMS_GENERATOR_MASTER_v16.0.md` | Compliance rules, code system, technical spec | ❌ Read only |
| `SWMS_METHODOLOGY.md` | Nine-step decision logic — why the system works this way | ❌ Read only |
| `SWMS_TASK_LIBRARY.md` | Pre-written task dicts for all 15 codes — select per job | ❌ Read only |
| `SWMS_CONSOLIDATED_RULES.md` | Consolidated table defensibility standard — read before writing any control_summary ★ v16.2 | ❌ Read only |
| `TEMPLATE_RULES.md` | Frozen cell map, preservation rules, HRCW map | ❌ Read only |
| `USER_INPUT_REQUEST_GENERAL.md` | General intake form — any job type | ✏️ Fill in per job |
| `SWMS_METHODOLOGY.md` | Nine-step decision logic v16.3 — ENV surface prep rule added | ❌ Read only |
| `SWMS_TASK_LIBRARY.md` | Pre-written task dicts — ENV-5 and ENV-6 added v16.3 | ❌ Read only |
| `PROJECT_INSTRUCTIONS.md` | Claude Project Instructions — paste into Project Instructions field | ❌ Reference |
| `FINAL_MANIFEST.md` | This file — master index | ❌ Reference |

### Output files (generated per job):

| File | Contents |
|---|---|
| `SWMS_[WorkType]_[Date]_Standard.docx` | Standard version — controls in place language |
| `SWMS_[WorkType]_[Date]_CCVS.docx` | CCVS version — hold point language for H-tier tasks |

---

## SYSTEM ARCHITECTURE

```
USER INPUT (USER_INPUT_REQUEST.md)
         │
         ▼
CLAUDE reads SWMS_GENERATOR_MASTER_v16.0.md + SWMS_METHODOLOGY.md
         │
         ▼
CLAUDE reads SWMS_CONSOLIDATED_RULES.md ★ NEW v16.2
  ↳ Apply defensibility standard to all control_summary fields
  ↳ Run acceptance test before generating
         │
         ▼
CLAUDE edits SWMS_BASE_GENERAL.py — Sections 1, 2, 3 only
  ✏️ Section 1: PROJECT dict (company, site, personnel, HRCW)
  ✏️ Section 2: TASKS list
       controls        → full hierarchical text → Detail table (tables[3])
       control_summary → short defensible text  → Consolidated table (tables[2])
  ✏️ Section 3: PPE, Permits, Quals, Plant, Substances, Legislation
         │
         ▼
python3 SWMS_BASE_GENERAL.py
  ⛔ Frozen engine runs:
     _populate_header()             → Table 0
     _populate_consolidated_table() → Table 2 (control_summary fields)
     _populate_detail_table()       → Table 3 (controls fields)
     _populate_requirements()       → Tables 1, 6, 7
     _add_audit_metadata()          → Hidden paragraph
         │
         ▼
OUTPUT: Standard.docx + CCVS.docx
```

---

## CONSOLIDATED TABLE STANDARD (v16.2)

The consolidated table (`tables[2]`) is governed by `SWMS_CONSOLIDATED_RULES.md`.
The following rules apply to every job. Full detail is in that file.

**Three mandatory elements for every H-tier task:**
1. Verification action — what gets checked, confirmed, sighted, or recorded
2. Isolation control — exclusion/drop zone with fall-line rule applied
3. Stop-work trigger — what condition halts work

**Fall-line rule:** Never write a fixed distance alone.
Always: "min [X]m — extend to full fall-line/drop zone as required"

**EMR-H9 mandatory:** Call 000 + rescue steps (access method specific) +
suspension intolerance protocol + first aider/kit + muster point.

**SYS-L1 mandatory:** Always include change management rule:
"Method or site change: STOP, update SWMS, re-brief, re-sign before recommencing."

**Acceptance test (run before generating):**
☐ Every H6/H9 row: verification + isolation + stop-work trigger
☐ Fall-line rule applied — no bare fixed distance
☐ EMR-H9: rescue steps specific to access method on this job
☐ SYS row: change management rule present

---

## OPERATING PROCEDURE — EVERY JOB

### Step 1: Collect details
Fill in `USER_INPUT_REQUEST_GENERAL.md` — all ★ mandatory fields.
Confirm access method, lead, asbestos, and silica status before starting.

### Step 2: Choose platform

**Option A — Claude (cloud, no setup):**
1. Open SWMS Generator Project
2. Start new conversation — attach `SWMS_Template.docx`
3. Paste completed `USER_INPUT_REQUEST_GENERAL.md`
4. Claude reads system files, applies consolidated rules, edits and runs script
5. Download Standard.docx and CCVS.docx

**Option B — Replit (cloud, persistent):**
1. Open Replit project — files already uploaded
2. Paste intake form
3. Replit AI edits Sections 1, 2, 3 only
4. Click Run — download outputs from file panel
5. See `REPLIT_AI_FOR_SWMS_GENERATION.md` for full setup

**Option C — Local Python (advanced):**
1. Edit Sections 1, 2, 3 manually in SWMS_BASE_GENERAL.py
2. Set `TEMPLATE = r"C:\path\to\SWMS_Template.docx"`
3. Run: `python3 SWMS_BASE_GENERAL.py`
4. Outputs in same folder as script

### Step 3: Review outputs
Check both .docx files:
- Header: PBCU single line, site address, HRCW boxes ticked correctly
- Consolidated: short/defensible, fall-line rule applied, stop-work triggers present
- Detail: full controls, hierarchy labels, colored risk cells, no truncation warnings
- Requirements: PPE, permits, qualifications all populated

### Step 4: Sign and issue
Supervisor and reviewer signatures in Table 0 Rows 9 and 13.
Issue correct version to PC (Standard or CCVS as required).

**Target time: under 10 minutes per SWMS.**

---

## FROZEN ENGINE — WHAT IS LOCKED

These elements are frozen in `SWMS_BASE_GENERAL.py` and must never be modified:

| Element | Why frozen |
|---|---|
| All `_` prefixed functions | Validated formatting logic |
| `HRCW_MAP` dict | Validated cell coordinates |
| `RISK_SCORES` dict | Validated colour and label values |
| All cell index numbers | Validated against template |
| `_generate_short_code()` | Short code format consistency |
| `_write_short_code_cell()` | Bold-black H-tier formatting |
| `_set_header_repeat()` | Header repeat XML logic |
| `_inject_risk_cell()` | Risk cell colour/text logic |
| `_add_audit_metadata()` | Hidden audit trail |
| Table index numbers (tables[0]–tables[9]) | Validated against 10-table template |
| `if __name__ == "__main__":` runner block | Output path logic |

---

## WHAT IS EDITABLE (per job)

| Section | Key | Notes |
|---|---|---|
| Section 1 | `pbcu_line` | Single string, no `\n` |
| Section 1 | `site` | Address only |
| Section 1 | `pc` | Principal contractor name |
| Section 1 | `date` | DD/MM/YYYY |
| Section 1 | `manager`, `supervisor`, `reviewer` | Personnel names |
| Section 1 | `activity` | Max ~200 chars |
| Section 1 | `emergency_contact`, `assembly_point` | Used in EMR task |
| Section 1 | `hrcw` | Boolean dict — valid keys only |
| Section 1 | `output_standard`, `output_ccvs` | Filenames without .docx |
| Section 1 | `title_prefix` | 14pt bold heading |
| Section 2 | `controls` | Full hierarchical text — Detail table |
| Section 2 | `control_summary` | Short defensible text — Consolidated table |
| Section 2 | `hazard_summary` | One-line hazard summary — Consolidated table |
| Section 3 | All six content strings | PPE, Permits, Quals, Plant, Substances, Legislation |
| Runner | `TEMPLATE` path | Platform-specific path only |

---

## VERSION CONTROL

### Current version: v16.3 (20/02/2026)

| Version | Date | Key Change |
|---|---|---|
| v16.3 | 20/02/2026 | Bold label tokens in detail table (Admin: Engineering: PPE: STOP WORK: etc). CCVS HOLD POINTS auto-prepended + bold+yellow in consolidated table. swms_bulletize.py introduced (▪ bullets, CCVS formatting preserved). ENV-5 and ENV-6 added to task library. Painting surface prep locked: STD-4-2-ENV always. SWMS_METHODOLOGY.md v16.3. PROJECT_INSTRUCTIONS.md v16.3. |
| v16.2 | 20/02/2026 | SWMS_CONSOLIDATED_RULES.md added. Consolidated table defensibility standard formalised. Fall-line rule. Minimum defensible set per risk class. Wording templates for all 15 codes + EMR. Change management rule mandatory in SYS row. Acceptance test before generation. PROJECT_INSTRUCTIONS.md updated. |
| v16.1 | Feb 2026 | SWMS_METHODOLOGY.md added. SYS locked (REC removed). Negative CCVS rule. Spray Step 7. Change management 6 triggers. Step 9 data layer. |
| v16.0 | Feb 2026 | 15-code system, Consolidated+Detail tables, summary keys, bold-black H-tier. |
| v15.5 | Feb 2026 | Frozen engine architecture, Replit ready, SWMS_BASE.py introduced. |
| v15.2 | Feb 2026 | Table 1 PPE fix — both Table 1 and Table 6 populated. |
| v15.1 | Feb 2026 | Cell mapping fix — Col 5 vs Col 6, PBCU single line. |
| v3.8  | Feb 2026 | CCVS integrated, A14/A15/A16/A17 added. |

### Update procedure:
1. Never overwrite a validated `SWMS_BASE_GENERAL.py` without saving previous version
2. Test against `SWMS_Template.docx` before issuing any SWMS
3. Version bump requires re-validating all table indices against template
4. Update this manifest and relevant reference files when rules change
5. Delete old version from Project Knowledge before uploading new version

---

## 15-CODE RISK SYSTEM

| Code | Full Name | Tier | Stop Work? |
|---|---|---|---|
| WFR | Work at Heights — Fall Restraint | H | No |
| WFA | Work at Heights — Fall Arrest | H | No |
| WAH | Work at Heights — Collective & Access | H | No |
| IRA | Industrial Rope Access | H | ✅ Yes (two-rope compromise) |
| ELE | Electrical | H | ✅ Yes |
| SIL | Silica & Dust | H | No |
| STR | Structural | H | ✅ Yes |
| CFS | Confined Space | H | ✅ Yes (atmospheric failure) |
| ENE | Energised Equipment & Stored Energy | H | ✅ Yes |
| HOT | Hot Works | H | No |
| MOB | Mobile Plant | H | No |
| ASB | Asbestos | H | ✅ Yes (unexpected disturbance) |
| LED | Lead | H | No |
| TRF | Traffic & Public Interface | M typical | No |
| ENV | Environmental & Chemical | M or H | No |

2 special codes (auto-injected — never add to TASKS list):

| Code | Role | Tier |
|---|---|---|
| SYS | Site induction, daily sign-in, governance — always Task 1 | L |
| EMR | Emergency response — always final task | H9 locked |

---

## CCVS TRIGGER SUMMARY

```
IF   Pre-Control Risk ≥ 6
AND  Consequence = 3 (Major)
AND  Category in locked critical list (13 codes)
THEN CCVS language — hold point format in Detail table

Locked critical list:
WFR  WFA  WAH  IRA  ELE  SIL  STR  CFS  ENE  HOT  MOB  ASB  LED

NEGATIVE RULE: Pre = 6 + Consequence = 2 → does NOT trigger CCVS
TRF and ENV → do NOT trigger CCVS (consequence typically = 2)
EMR → never CCVS — always standard emergency language
```

---

## SHORT CODE FORMAT

```
[CATEGORY]-[TIER][PRE_SCORE]

Tier:  H = pre 6 or 9  |  M = pre 3 or 4  |  L = pre 1 or 2

Examples:
  WAH-H6   Work at Heights, High, pre 6    → suffix BOLD black
  IRA-H6   Rope Access, High, pre 6        → suffix BOLD black
  ASB-H9   Asbestos, High, pre 9           → suffix BOLD black
  SIL-H6   Silica, High, pre 6             → suffix BOLD black
  ENV-M4   Environmental, Medium, pre 4    → all normal weight
  TRF-M4   Traffic, Medium, pre 4          → all normal weight
  SYS-L1   Governance, Low, pre 1          → all normal weight
  EMR-H9   Emergency, High, pre 9          → suffix BOLD black

Short codes appear in Col 6 of both Consolidated and Detail tables.
Full audit codes (e.g. CCVS-6-3-WAH) are hidden in audit metadata only.
```

---

## BACKUP PROCEDURE

Recommended folder structure:

```
SWMS-System/
├── engine/
│   └── SWMS_BASE_GENERAL.py            ← general engine — use for all new jobs
├── docs/
│   ├── SWMS_GENERATOR_MASTER_v16.0.md
│   ├── SWMS_METHODOLOGY.md
│   ├── SWMS_TASK_LIBRARY.md
│   ├── SWMS_CONSOLIDATED_RULES.md      ← ★ new v16.2
│   ├── TEMPLATE_RULES.md
│   ├── USER_INPUT_REQUEST_GENERAL.md
│   ├── FINAL_MANIFEST.md
│   └── CLAUDE_PROJECT_GUIDE.md
├── template/
│   └── SWMS_Template.docx              ← never modify
└── jobs/
    ├── [JobRef]_[Site]_[Date]/
    │   ├── [JobRef]_SWMS.py
    │   ├── [JobRef]_Standard.docx
    │   └── [JobRef]_CCVS.docx
    └── [NextJob]/
```

Back up job script before every new job that modifies the data sections.

---

## QUICK START GUIDE — NEW JOB

```
1. Fill in USER_INPUT_REQUEST_GENERAL.md (5 min)
2. Open SWMS Generator Project — start new conversation
3. Attach SWMS_Template.docx to message
4. Paste completed intake form
5. Claude reads system files + consolidated rules
6. Claude edits Sections 1, 2, 3 — runs acceptance test — generates
7. Download Standard.docx and CCVS.docx
8. Open in Word — check header, consolidated table, detail table
9. Print or PDF — sign — issue to PC
Target: under 10 minutes
```

---

## CONTACTS & OWNERSHIP

```
System owner:  [Your Company Name]
               [Address]
               Phone: [Phone]  |  ABN: [ABN]

Developed:     February 2026
Platform:      Python 3 + python-docx + Claude AI
```


---

## SETUP AND USAGE

## PART 1 — ONE-TIME SETUP

### Step 1 — Create the Project

1. Open claude.ai in your browser
2. Click **Projects** in the left sidebar
3. Click **New Project**
4. Name it: `SWMS Generator v16`
5. Click **Create Project**

---

### Step 2 — Upload Files to Project Knowledge

Inside the Project, find the **Knowledge** section (usually on the right side
or accessible via a button at the top of the project).

Upload ALL of the following files in this order:

| # | File | Purpose |
|---|---|---|
| 1 | `SWMS_BASE_GENERAL.py` | General engine — auto-injects SYS and EMR |
| 2 | `SWMS_GENERATOR_MASTER_v16.0.md` | Rules, code system, technical spec |
| 3 | `SWMS_METHODOLOGY.md` | Nine-step decision logic |
| 4 | `SWMS_TASK_LIBRARY.md` | Pre-written task dicts for all 15 codes |
| 5 | `TEMPLATE_RULES.md` | Frozen cell map and table preservation rules |
| 6 | `USER_INPUT_REQUEST_GENERAL.md` | Intake form template |
| 7 | `FINAL_MANIFEST.md` | Master index and version control |
| 8 | `CLAUDE_PROJECT_GUIDE.md` | This file |

**SWMS_Template.docx** — upload this to Knowledge as well. Claude reads it
as reference. You will also need to attach it fresh each generation session
because the Python engine opens it as a live file at runtime.

**Do not upload:**
- Old version files (v15.x, v3.x)
- Generated output documents (Standard.docx, CCVS.docx)
- Job-specific scripts (RPD_SWMS_Painting_v16.py)

---

### Step 3 — Paste Project Instructions

Click the **Project Instructions** section (sometimes called Custom
Instructions or System Prompt for the Project).

Paste the entire contents of `PROJECT_INSTRUCTIONS.md` into this field.

Save.

That text now loads automatically in every conversation inside this Project.
You never have to explain the system again.

---

## PART 2 — USING THE PROJECT FOR EVERY NEW JOB

### Standard workflow — new SWMS

**What you do:**

1. Open the SWMS Generator v16 Project
2. Start a new conversation
3. Attach `SWMS_Template.docx` to the message (required every session —
   the engine opens it as a live file)
4. Paste your completed `USER_INPUT_REQUEST_GENERAL.md` intake form
5. Send

**What Claude does:**

1. Reads the system files from Project Knowledge
2. Selects tasks from SWMS_TASK_LIBRARY.md based on your scope
3. Populates Sections 1, 2, and 3 of SWMS_BASE_GENERAL.py
4. Runs the engine — SYS and EMR auto-injected
5. Generates Standard.docx and CCVS.docx
6. Returns download links

**Total time per job once system is running: 5–10 minutes.**

---

### Filling in the intake form

Open `USER_INPUT_REQUEST_GENERAL.md`. Fill in:

- Section A — Project details (PBCU, site, PC, dates, names)
- Section B — Work description (plain language)
- Section C — Access method (tick boxes)
- Section D — Scope items (tick all activities)
- Section E — HRCW flags (tick what applies)
- Section F — Site conditions (answer each question)
- Section G — Requirements content (PPE, permits, quals, plant, substances)
- Section H — Output selection (Standard, CCVS, or both)
- Section I — Additional notes

Paste the completed form directly into the chat. No need to attach as a file.

---

### If something looks wrong in the output

Tell Claude specifically what is wrong. Examples:

- "Task 3 should be CCVS not Standard — the pre score is 6 and consequence is 3"
- "The site address is wrong — it should be [correct address]"
- "Add a task for confined space entry between tasks 4 and 5"
- "The EWP task needs the CCVS hold points for anchor verification added"

Claude will regenerate only the affected section, not the entire document.

---

### If you need to add a new task type not in the library

Tell Claude:

"I need a task for [description of work]. The dominant hazard is [hazard].
The access method is [method]. Apply the six-trigger check and suggest the
correct code, pre score, and whether CCVS applies."

Claude will generate a new task dict using METHODOLOGY Step 3 (six-trigger
check) and add it to the job. If it is a recurring task type, ask Claude to
add it to SWMS_TASK_LIBRARY.md — then re-upload the updated library to
Project Knowledge.

---

## PART 3 — KEEPING THE SYSTEM CURRENT

### When rules change

1. Edit the relevant file locally
2. Bump the version number in document control
3. Delete the old file from Project Knowledge
4. Upload the new file
5. Update FINAL_MANIFEST.md with the change summary
6. Re-upload FINAL_MANIFEST.md

Always delete before uploading. Project Knowledge can hold multiple versions
of the same filename — Claude may read either. One version at a time, always.

### When you add new tasks to the library

1. Open SWMS_TASK_LIBRARY.md locally
2. Add the new task dict under the correct code section
3. Re-upload to Project Knowledge (delete old version first)
4. No engine changes required

### When you want to change the document format

This is the most involved change. See TEMPLATE_RULES.md for the cell map.
Any format change requires:
1. Modify SWMS_Template.docx
2. Re-validate cell mapping in TEMPLATE_RULES.md
3. Update engine functions in SWMS_BASE_GENERAL.py if columns change
4. Test against the new template before issuing documents
5. Version bump on engine and TEMPLATE_RULES.md

---

## PART 4 — FILE INVENTORY

### What lives in Project Knowledge (permanent)

These files are always available in every conversation without uploading:

```
SWMS_BASE_GENERAL.py
SWMS_GENERATOR_MASTER_v16.0.md
SWMS_METHODOLOGY.md
SWMS_TASK_LIBRARY.md
TEMPLATE_RULES.md
USER_INPUT_REQUEST_GENERAL.md
FINAL_MANIFEST.md
CLAUDE_PROJECT_GUIDE.md
SWMS_Template.docx
```

### What you attach per session (runtime files)

These are attached fresh each generation session:

```
SWMS_Template.docx    ← engine opens this as a live file at runtime
```

### What lives on your local computer

Your source of truth. Mirror of everything in Project Knowledge plus outputs:

```
SWMS-System/
├── engine/
│   └── SWMS_BASE_GENERAL.py
├── docs/
│   ├── SWMS_GENERATOR_MASTER_v16.0.md
│   ├── SWMS_METHODOLOGY.md
│   ├── SWMS_TASK_LIBRARY.md
│   ├── TEMPLATE_RULES.md
│   ├── USER_INPUT_REQUEST_GENERAL.md
│   ├── FINAL_MANIFEST.md
│   └── CLAUDE_PROJECT_GUIDE.md
├── template/
│   └── SWMS_Template.docx
└── jobs/
    ├── RPD_Painting_BreakfastPoint_Feb2026/
    │   ├── RPD_SWMS_Painting_v16.py
    │   ├── [job]_Standard.docx
    │   └── [job]_CCVS.docx
    └── [NextJob]/
```

---

## PART 5 — TROUBLESHOOTING

**Claude says it cannot find the template or a file**
→ The file is in Project Knowledge but Claude cannot open .docx files as
  code at runtime. Attach SWMS_Template.docx directly to the chat message.

**Generated document has wrong content in a cell**
→ Tell Claude exactly which table, row, and column is wrong and what it
  should say. Claude will fix and regenerate.

**CCVS hold points not highlighted yellow**
→ The _set_cell_text_9pt_ccvs function is frozen and validated. If highlight
  is missing, check the control text contains the exact string
  "CCVS HOLD POINTS" — the function splits on that exact phrase.

**Task numbered incorrectly**
→ Do not number tasks in Section 2 of the engine. The _inject_tasks()
  function numbers them automatically after SYS injection. If numbers are
  wrong, check whether SYS or EMR were accidentally included in TASKS list.

**Engine produces an error**
→ Paste the full error message to Claude. Do not attempt to fix the frozen
  engine functions — tell Claude the error and it will diagnose and fix.

**Output files not downloading**
→ Claude generates files in /mnt/user-data/outputs/. If the download link
  does not work, ask Claude to re-present the files.

---

## PART 6 — QUICK REFERENCE

**Nine-step checklist (METHODOLOGY summary):**
1. Tasks in order of occurrence, code = dominant risk driver
2. Four site conditions confirmed (access, ground, public, environment)
3. Six-trigger check for every task
4. Controls follow hierarchy — at least one above PPE
5. v16 codes applied — SYS not REC, IRA not WAH for rope access
6. CCVS: pre ≥ 6 AND consequence = 3 AND critical category
7. Spray assessed — wind, exclusion zone, stop decision before trigger
8. Six change management triggers identified and briefed
9. SYS Task 1 auto, EMR final task auto, records captured

**CCVS locked critical list (13 codes):**
WFR WFA WAH IRA ELE SIL STR CFS ENE HOT MOB ASB LED
TRF and ENV do NOT trigger CCVS.
EMR never uses CCVS language.

**Audit string format:**
`[STD|CCVS]-[pre]-[consequence]-[CODE]`
Examples: `CCVS-6-3-WAH` | `STD-4-2-TRF` | `STD-9-3-EMR`

**Risk score valid values:**
1, 2, 3, 4, 6, 9 — no other values are valid

---

*End of CLAUDE_PROJECT_GUIDE.md*
*Read this once. Pin it. Never need to re-explain the system.*


---

*End of SWMS_OPERATOR_GUIDE.md*
*Version: v16.3*
*Consolidated: FINAL_MANIFEST.md + CLAUDE_PROJECT_GUIDE.md*

# CLAUDE.md — Gatekeeper Project
## Robertson's Remedial and Painting Pty Ltd
## WHS Governance Architecture + SWMS Generation System

---

## What Gatekeeper Is

Gatekeeper is the WHS governance architecture for Robertson's Remedial
and Painting Pty Ltd (RPD). It automates compliance document generation,
risk classification, audit scoring, and safety management workflows for
Australian construction sites.

The primary output system is SWMS generation — Safe Work Method
Statements for high-risk construction work under WHS Regulation 2017
(NSW).

All code is Python. All document outputs are .docx or .xlsx. All scripts
live in src/.

---

## Folder Structure

```
gatekeeper/
├── CLAUDE.md                        ← you are here
├── src/                             ← all Python scripts
│   ├── SWMS_BASE_GENERAL.py         ← SWMS engine v16.4 (PRIMARY ENGINE)
│   ├── SWMS_TASK_LIBRARY.md         ← pre-written task dicts (15 codes)
│   ├── SWMS_GENERATOR_MASTER_v16_0.md  ← generation rules and code system
│   ├── SWMS_METHODOLOGY.md          ← nine-step decision logic v16.3
│   ├── SWMS_OPERATOR_GUIDE.md       ← setup, usage, version history
│   ├── swms_bulletize.py            ← post-processor: semicolons → bullets
│   ├── swms_ppe_validator.py        ← QA gate: PPE terminology checker
│   ├── swms_generator.py            ← RPD Master SWMS task definitions
│   ├── build_all_swms.py            ← batch runner for all Master SWMS docs
│   ├── swms_base_generator.py       ← base generator (legacy)
│   ├── audit_classification.py      ← risk scoring for site inspections
│   ├── data_analysis.py             ← trend identification and risk analysis
│   ├── mental_checkpoints.py        ← mental checkpoint class (core)
│   ├── docx_style_standard.py       ← shared font/colour/formatting constants
│   ├── risk_register_to_docx.py     ← risk register → Word export
│   ├── risk_register_to_xlsx.py     ← risk register → Excel export
│   └── rr_double_bay.py             ← Double Bay project risk register
├── docs/                            ← reference documentation
├── tests/                           ← test files
└── outputs/                         ← generated documents land here
```

---

## SWMS Generation System — Rules You Must Follow

### Engine

- Primary engine: `src/SWMS_BASE_GENERAL.py` — v16.4
- Never rewrite frozen functions — fix bugs only by targeted edits
- Frozen functions: `_inject_tasks()`, `_generate_short_code()`,
  `_populate_consolidated_table()`, `_populate_detail_table()`,
  `generate_swms()` and all others listed in the engine header
- SYS and EMR tasks are auto-injected — never add them to TASKS list
- Do not number tasks in TASKS list — engine numbers after injection

### Generation Workflow (always follow this order)

1. Write job `.py` file with PROJECT, TASKS, REQUIREMENTS sections
2. Run engine: `python src/SWMS_BASE_GENERAL.py` (or job file directly)
3. Run bulletizer on Standard output
4. Run bulletizer on CCVS output
5. Run PPE validator on Standard Bullets
6. Run PPE validator on CCVS Bullets
7. Report pass/fail — do not deliver documents if validator fails

### PPE Standard — LOCKED — Never Deviate

| Wrong | Correct |
|-------|---------|
| safety boots | steel-capped footwear |
| safety footwear | steel-capped footwear |
| hi-vis / hi-viz / high-vis / high-viz | hi-vis vest or shirt |
| gloves (bare) | cut-resistant gloves |

Exceptions for gloves: chemical-resistant, insulated, leather,
waterproof, nitrile, disposable, welding, heat-resistant gloves
are all acceptable with their descriptor.

The PPE normaliser in the engine catches these automatically.
The validator confirms after generation. Both must pass.

### Code System v16.0

15 working codes:
WFR WFA WAH IRA ELE SIL STR CFS ENE HOT MOB ASB LED TRF ENV

2 auto-injected (never add manually):
SYS — always Task 1
EMR — always final task

### CCVS Trigger — All Three Must Be Met

1. Pre-control risk score ≥ 6
2. Consequence = 3 (fatality or permanent disability)
3. Code is in the locked critical list:
   WFR WFA WAH IRA ELE SIL STR CFS ENE HOT MOB ASB LED

TRF and ENV never trigger CCVS.
EMR always uses standard language — never CCVS.

### Audit String Format

`[STD|CCVS]-[pre]-[consequence]-[CODE]`

Valid pre scores: 1, 2, 3, 4, 6, 9

### Character Limit

Control text fields: 1,400 characters maximum.
Trim from Admin section first — preserve Engineering and STOP WORK.

### Content Authority Hierarchy

1. Hansen Yuncken (HY) procedures — PRIMARY — never contradict
2. SafeWork NSW Codes of Practice and WHS Regulation
3. RPD internal standards and task libraries

---

## Coding Standards

- Python 3.x throughout
- python-docx for all Word document generation
- openpyxl for Excel outputs
- No external API calls from generation scripts
- File naming: descriptive, underscores, no spaces
- Outputs always go to outputs/ — never overwrite src files
- All new scripts must import from docx_style_standard.py for
  consistent font/colour formatting

---

## Git Workflow

After any file changes — always commit and push:

```
git add .
git commit -m "brief description of what changed"
git push
```

If asked to make changes to .md documentation files or Python scripts,
always commit after saving. Never leave changes uncommitted.

Branch: main
Remote: origin

---

## RPD Project Context

**Company:** Robertson's Remedial and Painting Pty Ltd
**Director:** Leslie Robertson
**Works Manager:** Jim Georgiadis
**Supervisor:** Nick Vuckovic
**Location:** Sydney, NSW, Australia
**Typical work:** Remedial, waterproofing, painting, cladding,
  demolition on occupied residential and commercial strata buildings
**Regulatory framework:** WHS Act 2011 (NSW), WHS Regulation 2017 (NSW),
  SafeWork NSW Codes of Practice

---

## What Claude Code Should Do by Default

- Always read relevant src files before making changes
- Always follow the PPE standard — no exceptions
- Always run the full generation workflow (engine → bulletizer → validator)
- Always commit and push after file changes unless told otherwise
- Never rewrite frozen engine functions
- Never add SYS or EMR to TASKS lists
- When generating a new SWMS job: create the job .py file in src/,
  run it, bulletize both outputs, validate both outputs, report results
- When updating .md files: read current version first, make targeted
  edits only, preserve all existing content not being changed
- When unsure about a rule: check SWMS_GENERATOR_MASTER_v16_0.md first

---

*Last updated: 27/02/2026*
*System: Gatekeeper v1.0 — SWMS Generator v16.4*
*Owner: Alan Richardson — Robertson's Remedial and Painting Pty Ltd*

---

## Gatekeeper Governance Architecture — Full Vision

Gatekeeper is being built as a complete WHS governance architecture.
Documents and registers are not standalone — they flow from a single
source of truth (the project risk register) through to issued documents.

### The Governance Flow

```
PROJECT RISK REGISTER
        ↓
  Identifies hazards, risk scores, control categories
        ↓
    REGISTERS (linked to risk register)
    • Hazardous Chemicals Register
    • Plant and Equipment Register
    • Subcontractor Register (future)
        ↓
  Risk register drives SWMS task selection
  High-risk items → CCVS tasks automatically
        ↓
    SWMS GENERATION
    Standard + CCVS versions
    Engine → Bulletizer → PPE Validator → Output
        ↓
    DRAFT REVIEW PORTAL (Phase 3)
    PM views PDF online → Comments → Approves
        ↓
    ISSUED DOCUMENT
    Signed, dated, version controlled
        ↓
    SITE MONITORING (Phase 4)
    Audits → Incidents → SWMS review triggered
```

### Build Phases

**Phase 1 — Foundation (complete)**
- CLAUDE.md governance document ✅
- SWMS engine v16.4 with PPE normaliser ✅
- PPE validator QA gate ✅
- Master SWMS alignment to RPD procedures (in progress)

**Phase 2 — Risk Register as Engine (next)**
- Standardise risk register format across all RPD projects
- Risk register outputs drive SWMS task selection automatically
- Hazardous chemicals register linked to risk register
- Plant and equipment register linked to risk register
- One risk register per project → auto-populates relevant SWMS tasks

**Phase 3 — Draft Review Portal**
- Generated PDFs auto-save to shared location
- PM accesses link on any device (phone or desktop)
- PM views draft SWMS, leaves comment, clicks Approve or Request Changes
- Alan receives notification
- Approved documents logged and version controlled
- Built in Python/Flask, hosted on Railway or Render (free tier)

**Phase 4 — Site Monitoring (future)**
- Site audits feed back into risk register
- Incidents trigger automatic SWMS review flag
- Trend analysis via data_analysis.py
- Reporting dashboard

### Register Standards (Phase 2 target format)

All registers output to both .docx and .xlsx:
- risk_register_to_docx.py
- risk_register_to_xlsx.py
- docx_style_standard.py (shared formatting — always use this)

Risk scoring uses same matrix as SWMS:
- Pre-control score: 1, 2, 3, 4, 6, 9
- Consequence: 1 (minor), 2 (moderate), 3 (major/fatality)
- Risk level: Low (green), Medium (yellow), High (red)

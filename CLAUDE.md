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
│   ├── swms_vocabulary.py           ← controlled vocabulary: canonical phrases
│   ├── vocab_tool.py                ← CLI: list/add/check/scan vocabulary
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

### P2 Respirator Rule — Non-Negotiable

The canonical term is **P2 respirator (minimum)**.

`(minimum)` is mandatory — it signals that P2 is the floor, not
the ceiling. Higher-grade RPE (P3, half-face, full-face, supplied
air) replaces P2 where task-specific risks demand it.

| Wrong | Correct |
|-------|---------|
| P2 mask | P2 respirator (minimum) |
| P2 dust mask | P2 respirator (minimum) |
| P2 face mask | P2 respirator (minimum) |
| dust mask | P2 respirator (minimum) |
| face mask | P2 respirator (minimum) |

**Enforcement chain:**
1. `swms_vocabulary.py` — `PPE_ITEMS["p2_respirator"]` = canonical
2. `format_swms.py` Rule 7 — auto-replaces all variants at
   generation time and logs each fix to console
3. `swms_ppe_validator.py` — confirms after generation

This rule applies to every SWMS document — Master, standalone,
and any future format. No exceptions.

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

### SWMS Formatting & Content Rules (Mandatory)

All rules below are LOCKED. Applied by `src/format_swms.py`
(post-processor) and `src/build_all_swms.py` (row builder).
Build will fail if format_swms.py is missing.

#### Font Standard

- Font: Aptos
- Size: 8pt (sz=16 half-points)
- No Calibri, Arial, or Aptos Narrow anywhere in task tables

#### Paragraph Settings (every paragraph in every task table cell)

- Alignment: Left
- Left indent: 0.4cm (227 DXA)
- Special: Hanging 0.4cm (227 DXA)
- Space before: 1pt (20 twips)
- Space after: 1pt (20 twips)
- Line spacing: Multiple 1.15
- XML: `<w:spacing w:before="20" w:after="20" w:line="276"
  w:lineRule="auto"/>` `<w:ind w:left="227" w:hanging="227"/>`

#### Em Dash Rule

- Bold the — character only (its own run)
- Text before and after stays normal weight
- Capital letter after every em dash
- No full stops between em dash items

#### Bold Labels (all task types)

- Engineering: — bold, no highlight
- Admin: — bold, no highlight
- PPE: — bold, no highlight
- Supervision: — bold, no highlight
- Hold points: — bold, no highlight

#### Special Highlights

- STOP WORK if: — bold + YELLOW highlight on LABEL ONLY;
  conditions after are normal weight, no highlight
- HOLD POINT: — bold + YELLOW highlight on ENTIRE LINE
  (includes em dash and "Do not commence until:")
- Emergency Response: — bold, white text (FFFFFF), RED highlight

#### Sub-labels (dynamic — not hardcoded)

- Any capitalised text ending with `:` at start of a run → bold
- Catches: Anchor verification:, Two-rope system:, Rescue readiness:,
  Exclusion zone:, Edge management:, Drop zone controls: etc.

#### Task Descriptions

- Text in [square brackets] → italic, dark grey (#444444)
- Not bold even if surrounding text is bold

#### Task Column Generation Rule (Mandatory)

Task name and scope MUST be written by `build_all_swms.py`
using the `make_col0_paras()` helper function only.
Never write raw paragraphs directly into Col 0.
The helper enforces bold/italic/indent/colour automatically.
`format_swms.py` catches and corrects any deviation as fallback.

- Task name paragraph: Bold, Aptos 8pt, indent left=0 hanging=0,
  space before=20 twips, space after=0
- Scope paragraph: Italic, Aptos 8pt, colour #444444,
  text wrapped in [square brackets], indent left=0 hanging=0,
  space before=0, space after=20 twips

#### Risk Cell Colours

- High: fill FF0000, text FFFFFF, bold
- Medium: fill FFFF00, text 000000, bold
- Low: fill 00FF00, text 000000, bold

#### CCVS Control Cell

- Cell fill: FFF2F2 (light pink)

#### Header Row

- Cell fill: DBE5F1 (light blue)

#### Table Borders

- Style: dotted, size 2, colour BFBFBF
- All sides including inside

#### Bullet Style (CCVS control blocks and hazard column)

- Character: o (Courier New font) — renders as open circle
- Left indent: 0.4cm (227 DXA)
- Hanging indent: 0.4cm (227 DXA)
- One item per bullet (except PPE and STOP WORK)

---

#### NON-CCVS STANDARD TASK — Control Cell Structure

Mandatory order:
1. Risk header: `PRE (Medium-4): Controls in place.` ← ONLY full stop
2. Engineering: [em dash chain — no full stops]
3. Admin: [em dash chain — no full stops]
4. PPE: [comma list — no em dashes, no full stop]
5. STOP WORK if: [yellow highlight on label] [em dash chain]

Reference example:

> **PRE (Medium-4): Controls in place.**
> **Engineering:** Temporary edge protection/fall prevention at exposed
> edges — Slot cutting applies silica controls (wet/HEPA + P2 +
> exclusion zone) — No dry cutting — Depth stops set on cutting
> equipment per engineering specification typically 25–35mm
> **Admin:** Engineering specification and drawings reviewed before
> commencement — Slot depths, bar sizes, spacing, grout product
> confirmed — SDS for all epoxy, grout, and primer products reviewed
> — Crack monitoring record completed before and after stitching —
> Structural engineer sign-off required before proceeding if crack
> width exceeds specification tolerance
> **PPE:** Steel-capped footwear, P2 respirator (minimum) during cutting
> operations, eye protection, hearing protection during
> cutting, nitrile gloves for epoxy and grout handling
> **STOP WORK if:** Crack width or depth exceeds engineering specification
> tolerance — Unexpected movement or displacement observed — Services
> detected in cutting path — Structural engineer advises hold —
> Product temperature outside application range

Rules:
- Full stop appears ONLY after the risk header
- Em dashes separate all control items in Engineering and Admin
- PPE uses commas only — never em dashes
- STOP WORK if: label is bold + yellow highlight; conditions after
  are normal weight, no highlight
- No full stops anywhere except the risk header line
- Each label starts a new paragraph
- Content wraps within the paragraph — no mid-chain line breaks

#### CCVS TASK — Control Cell Structure

Mandatory order:
1. Risk header: `STR (High-6) CCVS HOLD POINTS:` ← bold, no highlight
2. HOLD POINT line: `HOLD POINT — Do not commence until:` ← bold +
   full YELLOW highlight
3. Numbered list: 1. 2. 3. verification conditions ← normal weight
4. Engineering: bold label + bullet list (one item per bullet)
5. Admin: bold label + bullet list (one item per bullet)
6. PPE: bold label + single bullet, comma list
7. STOP WORK if: bold label + YELLOW highlight + single bullet
   em dash chain

#### CCVS vs Standard Key Differences

| Element | Standard (non-CCVS) | CCVS |
|---------|---------------------|------|
| Hold points | None | Numbered list at top |
| Engineering | Em dash chain inline | Bullet list one per bullet |
| Admin | Em dash chain inline | Bullet list one per bullet |
| PPE | Comma list single para | Single bullet comma list |
| STOP WORK | Em dash chain inline | Single bullet em dash chain |
| HOLD POINT | Not present | Full line yellow highlight |

#### Em Dash Chain Rules (all task types)

- No full stops between control items
- No new paragraphs mid-chain
- Em dash (—) is the ONLY separator between items
- Capital letter after every em dash
- Full stop only at risk header line
- PPE uses commas only — never em dashes

#### Task Name + Scope Format (Col 0 — every row)

- Task name: bold, black
- Scope text: italic, [square brackets], next paragraph, colour #444444
- Never bold scope text
- Never remove the square brackets
- Scope is the customisation point for site-specific works

#### Hazard Column Format (Col 2 — every row)

- Each hazard = separate bullet point
- Bullet: o Courier New open circle
- Left indent: 0.4cm (227 DXA), Hanging: 0.4cm (227 DXA)
- Short noun phrases — not full sentences
- Em dash allowed within item for qualification (bold the dash only)
- Full stop on last bullet only (optional)
- Applies to EVERY row without exception

#### SWMS Data Structure in swms_generator.py

**New tasks (vocabulary-based)** — use `new_task()`:
- `hazard_keys`: list of HAZARDS dict keys
- `engineering`: list of CONTROLS keys or raw strings
- `admin`: list of CONTROLS keys or raw strings
- `ppe_keys`: list of PPE_ITEMS keys
- `stop_work_keys`: list of STOP_WORK keys
- `new_task()` returns a build-compatible dict automatically

**Legacy tasks (raw dicts)** — being migrated to `new_task()`:

CCVS tasks store:
- `hold_points`: list of strings (numbered list items)
- `eng`: list of strings (one per bullet)
- `admin`: list of strings (one per bullet)
- `ppe`: single string (comma separated)
- `stop_work`: list of strings (joined with em dash, single bullet)

Non-CCVS tasks store:
- `control`: list of tuples (label, text) — em dash chain, pre-formatted
- PPE and STOP WORK embedded in control tuples

#### Scope Customisation Trigger

When user uploads a scope of works, specification, or drawing:
1. Read the uploaded document
2. Identify matching tasks in swms_generator.py
3. Update ONLY the [ ] scope text for matched tasks
4. Add [SITE SPECIFIC] prefix to updated scope
5. Do NOT change task name, hazards, controls, or risk ratings
6. Commit with message referencing the source document

### How New SWMS Are Generated (Mandatory Workflow)

When generating any new SWMS or adding new tasks:

1. ALWAYS use `new_task()` helper from `swms_generator.py`
   Never build task dicts manually with raw strings

2. ALWAYS use vocabulary keys for hazards, PPE, and STOP WORK
   Run: `python src/vocab_tool.py list hazards`
   to see available keys before writing a task

3. If a required phrase is not in vocabulary:
   a. Run: `python src/vocab_tool.py add hazard` (or control/ppe/stopwork)
   b. Define the canonical phrase
   c. Commit the vocabulary addition FIRST
   d. Then use the new key in the task definition

4. Engineering and Admin controls:
   Use vocabulary keys where a canonical phrase exists
   Raw strings are permitted for task-specific content
   but trigger a WARNING during build

5. After adding any new tasks run:
   `python src/vocab_tool.py scan`
   to check for unregistered phrases

6. This ensures every worker reading any RPD SWMS
   sees identical wording for identical hazards
   regardless of which document they are reading

#### Vocabulary Files

- `src/swms_vocabulary.py` — canonical dictionaries + resolver functions
- `src/vocab_tool.py` — CLI tool for listing, adding, checking vocabulary
- Resolver functions: `get_hazard()`, `get_control()`, `get_ppe()`,
  `get_stop_work()`, `build_engineering()`, `build_admin()`
- Invalid keys raise `ValueError` at build time — fail fast, not silent

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

*Last updated: 01/03/2026*
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

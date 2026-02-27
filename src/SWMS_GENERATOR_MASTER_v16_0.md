# SWMS GENERATOR — MASTER INSTRUCTIONS v16.0

**Expert WHS Consultant & Python Developer**
**Last Updated:** February 2026
**Version:** v16.3 — Merged: TEMPLATE_RULES + CONSOLIDATED_RULES. Bold labels. ENV surface prep rule.

---

## ⛔ PRIME DIRECTIVE — READ FIRST

**Claude must never rewrite frozen engine functions.**
**Claude must never paraphrase cell mapping rules.**
**Claude fills in data (PROJECT, TASKS, REQUIREMENTS) only.**
**All structural code is copied verbatim from SWMS_BASE.py.**

When a user provides `SWMS_BASE.py` + `SWMS_Template.docx` + this `.md`:
1. Read this `.md` for rules
2. Use `SWMS_BASE.py` as the code base — modify ✏️ sections only
3. Never regenerate the frozen engine from scratch

---

## VERSION HISTORY

### v16.0 — February 2026 (CURRENT)
**15-CODE SYSTEM + CONSOLIDATED/DETAIL TABLES + SUMMARY KEYS**

**What Changed:**
- ✅ New template: 10 tables (was 9). All table indices updated throughout.
- ✅ Table 2 = Consolidated summary table (new). Table 3 = Detail (was Table 2).
- ✅ Table 6 = Legislation (was Table 5). Table 7 = Requirements (was Table 6).
- ✅ 15-code risk system replaces 10-code system.
- ✅ WAH split → WFR (restraint) / WFA (arrest) / WAH (collective + ladders).
- ✅ IRA added — Industrial Rope Access (IRATA/ARAA).
- ✅ HPR renamed ENE — Energised Equipment & Stored Energy.
- ✅ HAZ split → ASB (asbestos) + LED (lead).
- ✅ PUB renamed TRF — Traffic & Public Interface.
- ✅ ENV added — Environmental & Chemical.
- ✅ Short codes auto-generated: WAH-H6, ASB-H9, TRF-M4, ENV-L2 etc.
- ✅ H6/H9 suffix: bold black (prefix black normal). No colour.
- ✅ `hazard_summary` and `control_summary` keys added — Option C imperative style.
- ✅ Fallback: if summary keys absent → first 200 chars of full text, no error.
- ✅ `_populate_consolidated_table()` frozen function added (tables[2]).
- ✅ `_populate_detail_table()` replaces `_populate_risk_table()` (tables[3]).
- ✅ `_generate_short_code()` and `_write_short_code_cell()` frozen utilities added.
- ✅ `_populate_header()` Row 9/11/13 date corrected to cells[5].
- ✅ `_populate_requirements()` updated — tables[6] legislation, tables[7] requirements.
- ✅ CCVS stop-work trigger list updated to 15-code system.

---

### v15.5 — February 2026
**FROZEN ENGINE ARCHITECTURE + REPLIT READY**
- ✅ `SWMS_BASE.py` introduced — frozen file replacing per-session generation
- ✅ Three ✏️ USER DATA sections clearly separated from frozen engine
- ✅ All engine functions prefixed `_` (private/frozen)
- ✅ Replit setup instructions, user input template, CCVS option selection

---

### v15.2 — February 2026
- ✅ Table 1 PPE fix — both Table 1 and Table 6 populated

### v15.1 — February 2026
- ✅ Col 5 vs Col 6 cell mapping fix, PBCU single line, ■ Site address only

### v3.8 — February 2026
- ✅ CCVS trigger, A14 lead protocol, A15 asbestos protocol, A16 WAH hierarchy, A17 audit metadata

---

# ═══════════════════════════════════════════════════════════════════════
# PART A: COMPLIANCE ENGINE
# ═══════════════════════════════════════════════════════════════════════

## A1. Legislative Alignment

All SWMS must comply with:
- Work Health and Safety Act 2011 (NSW)
- Work Health and Safety Regulation 2017 (NSW)
- Applicable NSW Codes of Practice
- Relevant Australian Standards
- SafeWork NSW guidance material

NSW-specific requirements take priority over generic Australian guidance.

---

## A2. HRCW Confirmation

Before generating, confirm work is **High Risk Construction Work** under WHS Reg 2017 Part 6.3 r291.

If NOT HRCW → recommend JSA, SOP, or Scope of Works with risk assessment instead.
**Never generate a SWMS for non-HRCW work.**

---

## A3. Mandatory SWMS Content (Reg 299)

Every SWMS must include all five elements:

| # | Element | Implementation |
|---|---|---|
| 1 | Identification of HRCW | Title + HRCW checkboxes |
| 2 | Specific hazards and risks | Hazard column |
| 3 | Control measures | Control column with hierarchy |
| 4 | How controls implemented | Responsibility column |
| 5 | How controls monitored/reviewed | Review section in template footer |

---

## A4. Risk Management (Reg 34–38)

### Hierarchy of Control (must follow this order):

| Priority | Level | Rule |
|---|---|---|
| 1 | **Elimination** | Always consider first |
| 2 | **Substitution** | Explain if not used |
| 3 | **Isolation** | Barriers, enclosures |
| 4 | **Engineering** | Mechanical, ventilation, guarding |
| 5 | **Administrative** | Procedures, training, signage |
| 6 | **PPE** | Last resort — never rely on PPE alone |

Every task must have at least one control above PPE. Specific PPE items required (never "appropriate PPE").

---

## A5. Hazardous Chemical Logic (WHS Reg Chapter 7)

Where hazardous chemicals present, include:
- Air monitoring requirements
- Exposure control plan (ventilation, PPE, duration limits)
- Decontamination procedures
- Waste disposal requirements
- SDS reference (specific product name)
- Emergency procedures (per SDS Section 4)

---

## A13. CCVS — Conditional Control-Verification Logic

### Trigger (ALL THREE conditions must be met):

```
IF   Pre-Control Risk ≥ 6
AND  Consequence Rating = 3 (Major — potential fatality/disability)
AND  HazardCategory ∈ CriticalRiskCategories (15-code list below)
THEN Apply CCVS language
```

Consequence = 3 is required. Pre-Risk = 6 with Consequence = 2 (Moderate × Likely = 6) does NOT trigger CCVS.

### Critical Risk Categories — locked list (CCVS eligible):

| Code | Category |
|---|---|
| WFR | Work at Heights — Fall Restraint |
| WFA | Work at Heights — Fall Arrest |
| WAH | Work at Heights — Collective & Access |
| IRA | Industrial Rope Access |
| ELE | Electrical |
| SIL | Silica & Dust |
| STR | Structural |
| CFS | Confined Space |
| ENE | Energised Equipment & Stored Energy |
| HOT | Hot Works |
| MOB | Mobile Plant |
| ASB | Asbestos |
| LED | Lead |

**TRF and ENV are NOT in the CCVS list.** Their consequence is typically
Moderate (2), not Major (3). This list is fixed — not extended by discretion.
If a new category is added to v16, update this list explicitly.

**Negative rule — non-negotiable:**
Pre = 6 with Consequence = 2 does NOT trigger CCVS regardless of likelihood.
A TRF or ENV task scoring pre = 6 at consequence = 2 uses standard controls.

**EMR exception:**
EMR-H9 always uses standard emergency language — never CCVS hold point language.
Emergency response must be executable immediately without verification steps.

### CCVS Language Requirements:

✅ Include timing trigger: `"Work must not commence until..."`
✅ Numbered hold points where multiple conditions
✅ Specify measurable verification action per hold point
✅ Avoid vague "ensure" or "check"
✅ Retention statement: `"Confirmation retained in site diary or digital system"`

### STOP WORK — catastrophic exposures only:

Explicit `"STOP WORK"` permitted only for:
1. **ELE** — energised electrical contact
2. **STR** — structural collapse
3. **ASB** — asbestos disturbance (unexpected)
4. **CFS** — confined space atmospheric failure
5. **ENE** — high-pressure injection or stored energy release
6. **IRA** — two-rope system compromise

All other exposures → `"Remove from exposure and rectify prior to recommencing."`

### Governance Bridge (insert once in Permits section):

> "Critical controls for high-risk work must be verified prior to commencement; where implemented, verification may be recorded via documented or digital system."

---

## A14. Mandatory Lead Paint Protocol

Trigger: ANY lead paint work (encapsulation, disturbance, surface prep).
**Apply regardless of risk score.**

Insert at START of control column:

```
LEAD PAINT PROTOCOL (Mandatory):
1. TEST – Confirm lead presence prior to disturbance (licensed assessor).
2. PLAN – Exclusion zone. PPE: coveralls, cut-resistant gloves, P2 minimum (P3 if high exposure).
3. PROTECT – 200μm plastic containment sheeting. Seal perimeter.
4. CONTAIN – NO dry sanding. Wet methods or Peel Away only. Surfaces damp.
5. CLEAN – HEPA vacuum only (no sweeping/blowing). Wet wipe daily.
6. DISPOSE – Double-bag, label "LEAD WASTE", licensed disposal.
Health monitoring if exposure >standard: blood lead baseline/periodic/exit, 30yr records, WHS Reg Part 7.2.
```

~450 chars — leaves ~950 chars for task-specific controls.

Audit code: `LED-H6` or `LED-H9` depending on pre score.

---

## A15. Mandatory Bonded Asbestos Painting Protocol

Trigger: Painting intact bonded (non-friable) asbestos surfaces.
**Apply regardless of risk score.**

Insert at START of control column:

```
BONDED ASBESTOS PAINTING PROTOCOL (WHS Reg r.445):
1. CONFIRM – Asbestos register sighted. Bonded (non-friable) confirmed.
2. ASSESS – If damaged/deteriorating → STOP. Licensed removalist required.
3. ENCAPSULATE – Apply encapsulant per SDS before any surface preparation.
4. NO DISTURBANCE – No sanding, grinding, cutting, or pressure washing of ACM.
5. PPE – P2 respirator minimum, coveralls, cut-resistant gloves during encapsulant application.
6. WASTE – Contaminated materials double-bagged, labelled "ASBESTOS WASTE", licensed disposal.
Notify SafeWork NSW if removal required: WHS Reg Part 8.6.
```

~480 chars — leaves ~920 chars for task-specific controls.

Audit code: `ASB-H9` (consequence = 3 always for asbestos).

---

## A16. Height Hierarchy Prefix Constants

Prepend to height tasks as appropriate. Constants defined in SWMS_BASE.py — reference by name.

| Constant | Use when | ~Chars |
|---|---|---|
| `WAH_HIERARCHY` | EWP, scaffold, ladder, mezzanine, platform | ~170 |
| `WFA_PREFIX` | Harness in arrest mode, SRL, leading edge work | ~175 |
| `WFR_PREFIX` | Static line, restraint lanyard — worker cannot reach edge | ~140 |
| `IRA_PREFIX` | Rope access — two-rope system, IRATA/ARAA crew | ~190 |

---

## A17. Audit Metadata (Hidden)

Every generated document has a hidden 1pt white paragraph at the end:

```
AUDIT: [code1] | [code2] | [code3] | ...
```

Full audit codes format: `[CCVS|STD]-[pre]-[consequence]-[category]`
Examples: `CCVS-6-3-WAH`, `STD-4-2-SIL`, `STD-9-3-WAH`

Short codes in document (Col 6) are auto-generated — never manually entered.

---

## A18. Emergency Response — Mandatory Final Task

Every SWMS must end with Emergency Response:

```python
{
    "task":     "N. Emergency Response\n(ALWAYS APPLICABLE — ALL WORKERS)",
    "hazard":   "Medical emergency. Fire. Suspended worker. Missing person.",
    "pre":      9,
    "controls": "...(site-specific emergency procedures)...",
    "post":     1,
    "resp":     "[Supervisor name]",
    "audit":    "STD-9-3-WAH",
    "hazard_summary":  "Medical emergency, fire, suspended worker, or missing person on site.",
    "control_summary": "Call 000, first aid on site, evacuate to assembly point, rescue suspended worker within 10 min.",
}
```

---

## A19. SWMS Version Selection

| Option | When to use |
|---|---|
| Standard only | Routine work, lower-risk PC, internal documentation |
| CCVS only | Tier 1 PC, government projects, FSC audit expected |
| Both (default) | Issue both — submit whichever the PC requires |

---

## A20. Replit Setup

```
1. replit.com → Create Repl → Python → Name: SWMS-Generator
2. Upload: SWMS_BASE.py + SWMS_Template.docx
3. Shell: pip install python-docx
4. In SWMS_BASE.py runner: TEMPLATE = "SWMS_Template.docx"
5. Run → download outputs from file panel
```

See `REPLIT_AI_FOR_SWMS_GENERATION.md` for full operating guide.

---

## A21. Standard User Input Template

```
COMPANY:
  PBCU company name:     ________________________________
  Street address:        ________________________________
  Suburb/State/Post:     ________________________________
  Phone:                 ________________________________
  ABN:                   ________________________________
  Principal Contractor:  ________________________________

PERSONNEL:
  Works Manager:         ________________________________
  Supervisor:            ________________________________
  Reviewer:              ________________________________

SITE:
  Site address:          ________________________________
  Date (DD/MM/YYYY):     ________________________________
  Assembly point:        ________________________________
  Emergency contact:     ________________________________

WORK:
  Activity description:  ________________________________
  Access method:         EWP / Ladder / Scaffold / IRA / Ground only
  Max working height:    ________________________________
  Lead paint:            Yes / No / Unknown
  Asbestos:              Yes (bonded) / Yes (friable — STOP) / No / Unknown
  Silica substrates:     Yes / No

HRCW (tick all that apply):
  [ ] falling_2m              [ ] telecom_tower         [ ] demolition
  [ ] disturb_asbestos        [ ] load_bearing          [ ] confined_space
  [ ] shaft_trench            [ ] explosives            [ ] pressurised_gas
  [ ] chemical_lines          [ ] near_powerlines       [ ] flammable_atmosphere
  [ ] tilt_up_precast         [ ] traffic_corridor      [ ] powered_mobile_plant
  [ ] artificial_temperature  [ ] water_drowning        [ ] diving

VERSION: Standard / CCVS / Both

OUTPUT NAME:
  WorkType:              ________________________________
  Date (DDMMYYYY):       ________________________________
```

---

## A22. CCVS Version Selection Prompt

```
Which SWMS version do you need?
  1 = STANDARD VERSION ONLY
  2 = CCVS VERSION ONLY
  3 = BOTH VERSIONS (recommended default)
```

---

# ═══════════════════════════════════════════════════════════════════════
# PART B: TECHNICAL ENGINE
# ═══════════════════════════════════════════════════════════════════════

## B1. Table Map — validated 19/02/2026

```
Index │ Table                    │ Rows │ Cols │ Action
──────┼──────────────────────────┼──────┼──────┼──────────────────────────────────
  0   │ Header                   │  15  │   7  │ POPULATE — specific cells only
  1   │ PPE Summary              │   1  │   2  │ POPULATE — Col 1 only
  2   │ Consolidated Summary     │  2+  │   7  │ POPULATE — add rows, hazard/ctrl summary
  3   │ Detail Risk Assessment   │  2+  │   7  │ POPULATE — add rows, full content
  4   │ SWMS Amendments          │   8  │   6  │ DO NOT TOUCH
  5   │ Risk Matrix              │  13  │   6  │ DO NOT TOUCH
  6   │ Legislation & Review     │   2  │   2  │ APPEND Row 0 only — NEVER Row 1
  7   │ Requirements             │   8  │   2  │ POPULATE rows 0,1,3,4,6 — PRESERVE 2,5,7
  8   │ Worker Sign-off          │  25  │   4  │ DO NOT TOUCH
  9   │ SWMS Amendments cont.    │  34  │   6  │ DO NOT TOUCH
```

---

## B2. Template Preservation Rules

```
tables[6] Row 0 (legislation) → APPEND project-specific text — NEVER overwrite
tables[6] Row 1 (review freq) → DO NOT TOUCH — ever
tables[7] Row 2 (training)    → PRESERVE — Construction Industry Induction Card text
tables[7] Row 5 (maintenance) → PRESERVE — Daily pre-start checks text
tables[7] Row 7 (WaH RA)      → PRESERVE — A-frame ladder guidance text
```

---

## B3. Document Title

```python
_set_paragraph_text_14pt(doc.paragraphs[0], f"{project['title_prefix']} [{version_label}]")
```

14pt Calibri Bold. Single paragraph. Always first element in body.

---

## B4. Cell Text Function

```python
_set_cell_text_9pt(cell, text)
```

9pt Calibri. Clears all existing content before writing. Never use `\n` in PBCU line.

---

## B5. Risk Cell Injection

```python
_inject_risk_cell(cell, score)
```

Valid scores: **1, 2, 3, 4, 6, 9** — any other value raises `ValueError`.

```
Score │ Label        │ Background │ Text colour
──────┼──────────────┼────────────┼────────────
  1   │ Low (1)      │ 00B050     │ White
  2   │ Low (2)      │ 00B050     │ White
  3   │ Medium (3)   │ FFFF00     │ BLACK
  4   │ Medium (4)   │ FFFF00     │ BLACK
  6   │ High (6)     │ FF0000     │ White
  9   │ High (9)     │ FF0000     │ White
```

Yellow cells use BLACK text — exception to the white rule.

---

## B6. HRCW Checkbox Map

```python
_tick_hrcw_boxes(table, hrcw_dict)
```

```
Row 3: falling_2m(c1)          telecom_tower(c3)        demolition(c5)
Row 4: disturb_asbestos(c1)    load_bearing(c3)         confined_space(c5)
Row 5: shaft_trench(c1)        explosives(c3)           pressurised_gas(c5)
Row 6: chemical_lines(c1)      near_powerlines(c3)      flammable_atmosphere(c5)
Row 7: tilt_up_precast(c1)     traffic_corridor(c3)     powered_mobile_plant(c5)
Row 8: artificial_temperature  water_drowning(c3)       diving(c5)
       (c1)
```

Replaces `[   ]` with `[✓]` in cell text. Key names are frozen — use exact strings.

---

## B7. Header Table Cell Map (FROZEN)

```
VALIDATED CELL MAP — do not alter (19/02/2026):
┌──────────────────────────────────────────────────────────────────┐
│ Row 0  │ cells[1] = PBCU (single line)    │ cells[6] = ■ Site   │
│ Row 1  │ cells[1] = ■ Works Manager       │ cells[6] = ■ Date   │
│ Row 2  │ cells[1] = ■ Description         │ cells[6] = ■ PC     │
│ Rows 3-8 = HRCW checkboxes (see B6)                             │
│ Row 9  │ cells[2] = ■ Supervisor          │ cells[5] = ■ Date   │
│ Row 11 │ cells[2] = ■ Project Manager     │ cells[5] = ■ Date   │
│ Row 13 │ cells[2] = ■ Project Manager     │ cells[5] = ■ Date   │
└──────────────────────────────────────────────────────────────────┘

RULES:
  B7-R1: cells[5] rows 0-2 = template label — NEVER write data here
  B7-R2: cells[6] rows 0-2 = data column for right-hand fields
  B7-R3: ■ Site = site address ONLY — no assembly point, no emergency contact
  B7-R4: PBCU = single continuous line — NO \n characters
  B7-R5: Emergency details → Emergency Response task ONLY
  B7-R6: Rows 9/11/13 date → cells[5] NOT cells[6]
```

---

## B8. Header Row Repeat

```python
_set_header_repeat(table)
```

Sets `tblHeader` XML on Row 0 so header repeats on every page.
**Must be called before populating any data rows** — applies to both tables[2] and tables[3].
Strips `tblHeader` from all data rows automatically.

---

## B9. Short Code System (v16.0)

### Auto-generation

```python
prefix, suffix = _generate_short_code(audit, pre)
# Returns: prefix = "WAH-", suffix = "H6"
```

Format: `[CATEGORY]-[TIER][PRE]`
- H = pre score 6 or 9
- M = pre score 3 or 4
- L = pre score 1 or 2

Examples: `WAH-H6`, `ASB-H9`, `WFA-H6`, `IRA-H9`, `TRF-M4`, `ENV-L2`

### Cell formatting

```python
_write_short_code_cell(cell, audit, pre)
```

```
Prefix (e.g. "WAH-"):  9pt Calibri, black, normal weight
Suffix M/L tier:       9pt Calibri, black, normal weight
Suffix H tier (H6/H9): 9pt Calibri, black, BOLD
```

No colour used. Bold weight is the only differentiator for high-risk codes.

---

## B10. Consolidated Table (tables[2])

```python
_populate_consolidated_table(doc, tasks)
```

One-line-per-task overview. Written in **Option C imperative style** — active voice, worker-ready.

### Column map:
```
Col 0: Task title only (first line before \n)
Col 1: hazard_summary if present → else first 200 chars of hazard
Col 2: Pre-control risk (colored cell)
Col 3: control_summary if present → else first 200 chars of controls
Col 4: Post-control risk (colored cell)
Col 5: Responsible person
Col 6: Short code (prefix normal, H6/H9 suffix bold)
```

### Summary key rules:
- `hazard_summary`: imperative one-liner, max 200 chars, active voice
  Example: `"Fall from EWP — tipover, contact with overhead, entrapment risk."`
- `control_summary`: imperative one-liner, max 200 chars, active voice
  Example: `"Inspect EWP, confirm WP licence, clip harness to basket anchor, post spotter, 3m zone."`
- Both keys are **optional** — engine falls back silently if absent
- Both keys go in SECTION 2 task dicts alongside `hazard` and `controls`

### 3-step process:
```python
# STEP 1 — MANDATORY FIRST
_set_header_repeat(con_table)
# STEP 2 — Add rows
for _ in range(len(tasks) - 1): con_table.add_row()
# STEP 3 — Populate using summary keys
```

---

## B11. Detail Table (tables[3])

```python
_populate_detail_table(doc, tasks)
```

Full risk assessment. Complete hazard and control text. Colored risk cells. Short code col 6.

### Column map:
```
Col 0: Full task text (task name + \n + description)
Col 1: Full hazard text
Col 2: Pre-control risk (colored cell)
Col 3: Full control text — MAX 1400 CHARS (auto-truncated with warning)
Col 4: Post-control risk (colored cell)
Col 5: Responsible person
Col 6: Short code (prefix normal, H6/H9 suffix bold)
```

### 3-step process (identical structure to Consolidated):
```python
# STEP 1 — MANDATORY FIRST
_set_header_repeat(det_table)
# STEP 2 — Add rows
for _ in range(len(tasks) - 1): det_table.add_row()
# STEP 3 — Populate using full text keys
```

**Control column limit: 1400 characters maximum. Auto-truncated at 1397 + "..." with console warning.**

---

## B12. Requirements Population (FROZEN)

```python
_populate_requirements(doc, ppe, permits, quals, plant, substances, leg_append)
```

```python
# Table 1 — PPE summary (B1-R1: ALWAYS write separately from Table 7)
_set_cell_text_9pt(doc.tables[1].rows[0].cells[1], "■ PPE:\n" + ppe)

# Table 6 — Legislation (APPEND — never overwrite)
leg_cell = doc.tables[6].rows[0].cells[1]
_set_cell_text_9pt(leg_cell, leg_cell.text.strip() + leg_append)
# Table 6 Row 1 — DO NOT TOUCH

# Table 7 — Requirements
req = doc.tables[7]
_set_cell_text_9pt(req.rows[0].cells[1], "■ PPE:\n" + ppe)
_set_cell_text_9pt(req.rows[1].cells[1], "■ Permits Required:\n" + permits)
# Row 2 — PRESERVE
_set_cell_text_9pt(req.rows[3].cells[1], "■ Qualifications:\n" + quals)
_set_cell_text_9pt(req.rows[4].cells[1], "■ Plant:\n" + plant)
# Row 5 — PRESERVE
_set_cell_text_9pt(req.rows[6].cells[1], "■ Substances:\n" + substances)
# Row 7 — PRESERVE
```

---

## B13. Task Dict Format

Every task in `TASKS_STANDARD` and `TASKS_CCVS` must have these keys:

```python
{
    # Required — Detail table
    "task":            str,   # Task name + \n + description. Col 0.
    "hazard":          str,   # Full hazard text. Col 1. No length limit.
    "pre":             int,   # Pre-control risk: 1, 2, 3, 4, 6, or 9 ONLY
    "controls":        str,   # Full control text. Col 3. MAX 1400 CHARS.
    "post":            int,   # Post-control risk: 1, 2, 3, 4, 6, or 9 ONLY
    "resp":            str,   # Responsible person. Col 5.
    "audit":           str,   # e.g. "CCVS-6-3-WAH" or "STD-4-2-TRF"

    # Optional — Consolidated table (fallback to first 200 chars if absent)
    "hazard_summary":  str,   # Imperative one-liner. Max 200 chars. Active voice.
    "control_summary": str,   # Imperative one-liner. Max 200 chars. Active voice.
}
```

---

## B14. PBCU Format Rule (B7-R4)

```python
# ✅ CORRECT — single continuous string, no \n
"pbcu_line": (
    "■ PBCU: Robertson's Remedial and Painting Pty Ltd "
    "10/56 Buffalo Road Gladesville NSW 2111 "
    "Phone: (02) 9181 3519 | ABN: 16 140 746 247"
)

# ❌ WRONG — \n will push content to new line in cell
"pbcu_line": "■ PBCU: Company Name\n10/56 Address\nPhone: ..."
```

---

## B15. How Claude Uses SWMS_BASE.py

When user provides `SWMS_BASE.py` + project details:

1. **Identify the three ✏️ sections** (PROJECT, TASKS, REQUIREMENTS)
2. **Populate SECTION 1** from user input
3. **Generate TASKS** using compliance rules (A4, A13, A14, A15, A16, A17, A18)
4. **Write `hazard_summary` and `control_summary`** for each task — Option C imperative style
5. **Populate SECTION 3** from job specifics
6. **Verify** against B16 checklist
7. **Run** — frozen engine handles all formatting

Claude must **never** modify:
- Any `_` prefixed function
- The `if __name__ == "__main__":` runner block
- The `HRCW_MAP` inside `_tick_hrcw_boxes()`
- The `RISK_SCORES` dict inside `_inject_risk_cell()`
- Any cell index numbers in `_populate_header()`
- The `_generate_short_code()` or `_write_short_code_cell()` functions

---

## B16. Pre-Generation Checklist

Before generating any SWMS, verify:

**Template Preservation:**
- [ ] tables[6] Row 0 (legislation) will be APPENDED TO — not overwritten
- [ ] tables[6] Row 1 (review frequency) will NOT be modified
- [ ] tables[7] Rows 2, 5, 7 will be PRESERVED

**Risk Assessment Tables:**
- [ ] `_set_header_repeat()` called BEFORE populating any data rows — both tables[2] and tables[3]
- [ ] Data rows do NOT have tblHeader property

**Header Cell Mapping:**
- [ ] PBCU written to cells[1] as single continuous line
- [ ] ■ Site written to cells[6] — address only
- [ ] No data written to cells[5] in rows 0-2
- [ ] Rows 9/11/13 date written to cells[5] not cells[6]

**PPE:**
- [ ] tables[1] rows[0] cells[1] populated (PPE summary)
- [ ] tables[7] rows[0] cells[1] populated (Requirements PPE)

**Tasks:**
- [ ] All control texts ≤ 1400 chars
- [ ] All risk scores are valid (1, 2, 3, 4, 6, or 9)
- [ ] Last task is Emergency Response (pre=9, post=1, audit STD-9-3-WAH)
- [ ] All height tasks have appropriate hierarchy prefix (WAH/WFA/WFR/IRA)
- [ ] `hazard_summary` and `control_summary` written for each task

**Asbestos/Lead:**
- [ ] If ANY asbestos → disturb_asbestos: True AND A15 protocol in controls
- [ ] If ANY lead → A14 protocol in controls

---

## B17. Replit vs Claude Path Switching

```python
# Claude:
TEMPLATE = "/mnt/user-data/uploads/SWMS_Template.docx"

# Replit:
TEMPLATE = "SWMS_Template.docx"

# Windows local:
TEMPLATE = r"C:\Users\YourName\Documents\SWMS_Template.docx"
```

Output directory defaults to same folder as `SWMS_BASE.py` — no path changes needed for outputs.

---

# ═══════════════════════════════════════════════════════════════════════
# PART C: QUICK REFERENCE
# ═══════════════════════════════════════════════════════════════════════

## C1. Risk Matrix

| | Unlikely (1) | Possible (2) | Almost Certain (3) |
|---|---|---|---|
| **Major (3)** | Medium (3) | High (6) | High (9) |
| **Moderate (2)** | Low (2) | Medium (4) | High (6) |
| **Minor (1)** | Low (1) | Low (2) | Medium (3) |

CCVS applies only at High (6 or 9) AND Consequence = 3.

---

## C2. Short Code Quick Reference

| Work Type | Audit Code | Short Code |
|---|---|---|
| Fall from height — CCVS | CCVS-6-3-WAH | **WAH-H6** |
| Fall from height — high | CCVS-9-3-WAH | **WAH-H9** |
| Fall arrest harness | CCVS-6-3-WFA | **WFA-H6** |
| Fall restraint | STD-3-2-WFR | WFR-M3 |
| Rope access | CCVS-9-3-IRA | **IRA-H9** |
| EWP — collective | CCVS-6-3-WAH | **WAH-H6** |
| Asbestos | CCVS-9-3-ASB | **ASB-H9** |
| Lead paint | CCVS-6-3-LED | **LED-H6** |
| Electrical | CCVS-9-3-ELE | **ELE-H9** |
| Silica/dust | STD-4-2-SIL | SIL-M4 |
| Energised equipment | CCVS-9-3-ENE | **ENE-H9** |
| Hot works | STD-6-3-HOT | **HOT-H6** |
| Mobile plant | CCVS-6-3-MOB | **MOB-H6** |
| Traffic/public | STD-4-2-TRF | TRF-M4 |
| Environmental/chemical | STD-4-2-ENV | ENV-M4 |
| Clean up | STD-2-1-ENV | ENV-L2 |
| Site setup | STD-4-2-TRF | TRF-M4 |
| Emergency Response | STD-9-3-WAH | **WAH-H9** |

**Bold = H tier → suffix bold black in document**

---

## C3. Common HRCW Combinations

| Work | HRCW keys to set True |
|---|---|
| EWP painting | `falling_2m`, `powered_mobile_plant` |
| Scaffold painting | `falling_2m` |
| Rope access | `falling_2m` |
| Bonded asbestos painting | `disturb_asbestos`, `falling_2m` (if heights) |
| Lead encapsulation at heights | `falling_2m`, `disturb_asbestos` (if ACM also) |
| Spray in enclosed area | `flammable_atmosphere` |
| Near HVAC/refrigerant | `chemical_lines` |
| Near live electrical | `near_powerlines` |
| Near traffic | `traffic_corridor` |
| Near water | `water_drowning` |

---

## C4. 15-Code Category Definitions

| Code | Full Name | Covers |
|---|---|---|
| WFR | Work at Heights — Fall Restraint | Static lines, restraint lanyards, inertia reels in restraint mode. Worker cannot reach fall edge. |
| WFA | Work at Heights — Fall Arrest | Harness + lanyard in arrest mode, SRL. Worker can reach fall edge. Arrest forces, clearance distances, suspension trauma rescue plan. |
| WAH | Work at Heights — Collective & Access | EWP, scaffold, elevated platforms, mezzanines, roof barriers, ladders (AS/NZS 1892). |
| IRA | Industrial Rope Access | IRATA/ARAA two-rope systems, anchor engineering sign-off, no-solo rule, mandatory rescue plan. |
| ELE | Electrical | Live conductors, switchboards, energised services, powerlines, AS/NZS 3000. |
| SIL | Silica & Dust | Concrete/masonry cutting and grinding, dry sanding, respirable crystalline silica. |
| STR | Structural | Collapse, tilt-up, precast, excavation, shoring, temporary works. |
| CFS | Confined Space | Tanks, pits, trenches, restricted egress, atmospheric hazard — WHS Reg Part 4.3. |
| ENE | Energised Equipment & Stored Energy | Pneumatic tools, hydraulic equipment, pressurised gas cylinders, airless spray injection, stored mechanical energy, nail guns. |
| HOT | Hot Works | Welding, cutting, grinding sparks, open flame, ignition sources near combustibles. |
| MOB | Mobile Plant | Crane, forklift, concrete pump, excavator, bobcat, telehandler. |
| ASB | Asbestos | All ACM work — friable and bonded, encapsulation, removal, WHS Reg Part 8.6. |
| LED | Lead | Lead paint — encapsulation, removal, health monitoring, WHS Reg Part 7.2. |
| TRF | Traffic & Public Interface | Live traffic, pedestrian zones, road work, public interface. |
| ENV | Environmental & Chemical | Spill risk, contaminated land, hazmat storage, solvent waste, EPA obligations. |

---

## C5. Files Summary

| File | Purpose | Edit? |
|---|---|---|
| `SWMS_BASE.py` | Frozen engine + editable data | ✏️ Sections 1, 2, 3 only |
| `SWMS_Template.docx` | Word template — validated 19/02/2026 | ❌ Never |
| `SWMS_GENERATOR_MASTER_v16.0.md` | Rules + instructions | ❌ Read only |
| `SWMS_METHODOLOGY.md` | Nine-step decision logic + reasoning | ❌ Read only |
| Template rules | Now in Section D of this file | — |
| `USER_INPUT_REQUEST.md` | Job intake form | ✏️ Copy per job |
| `REPLIT_AI_FOR_SWMS_GENERATION.md` | Replit operating guide | ❌ Reference |
| `SWMS_OPERATOR_GUIDE.md` | Setup, usage, version history, file inventory | ❌ Reference |


---

## D — TEMPLATE RULES (merged from TEMPLATE_RULES.md)

## PART 1 — TEMPLATE OVERVIEW

```
Body element order (28 elements total):
[ 0] TABLE 0  — Header (15r × 7c)
[ 1] PARA     — "■ Description:" (informational — do not touch)
[ 2] PARA     — ""
[ 3] TABLE 1  — PPE Summary (1r × 2c)
[ 4] PARA     — ""
[ 5] PARA     — "Consolidated" (section label)
[ 6] TABLE 2  — Consolidated Summary (2r × 7c) ← NEW v16.0
[ 7] PARA     — ""
[ 8] PARA     — ""
[ 9] PARA     — "Detail" (section label)
[10] TABLE 3  — Detail Risk Assessment (2r × 7c)
[11] PARA     — ""
[12] PARA     — ""
[13] TABLE 4  — SWMS Amendments (8r × 6c) — DO NOT TOUCH
[14] PARA     — ""
[15] TABLE 5  — Risk Matrix (13r × 6c) — DO NOT TOUCH
[16] PARA     — "Under WHS Act s18..." (informational)
[17] TABLE 6  — Legislation & Review (2r × 2c)
[18] PARA     — ""
[19] TABLE 7  — Requirements (8r × 2c)
[20] PARA     — ""
[21] PARA     — ""
[22] TABLE 8  — Worker Sign-off (25r × 4c) — DO NOT TOUCH
[23] PARA     — ""
[24] PARA     — ""
[25] TABLE 9  — SWMS Amendments cont. (34r × 6c) — DO NOT TOUCH
[26] PARA     — ""
[27] sectPr
```

---

## PART 2 — TABLE INDEX MASTER LIST

| Index | Name | Rows | Cols | Action |
|---|---|---|---|---|
| tables[0] | Header | 15 | 7 | POPULATE — specific cells only (see Part 3) |
| tables[1] | PPE Summary | 1 | 2 | POPULATE — cells[1] only |
| tables[2] | Consolidated Summary | 2+ | 7 | POPULATE — add rows, write summaries |
| tables[3] | Detail Risk Assessment | 2+ | 7 | POPULATE — add rows, full content |
| tables[4] | SWMS Amendments | 8 | 6 | ⛔ DO NOT TOUCH |
| tables[5] | Risk Matrix | 13 | 6 | ⛔ DO NOT TOUCH |
| tables[6] | Legislation & Review | 2 | 2 | APPEND Row 0 only — never Row 1 |
| tables[7] | Requirements | 8 | 2 | POPULATE rows 0,1,3,4,6 — PRESERVE 2,5,7 |
| tables[8] | Worker Sign-off | 25 | 4 | ⛔ DO NOT TOUCH |
| tables[9] | SWMS Amendments cont. | 34 | 6 | ⛔ DO NOT TOUCH |

---

## PART 3 — TABLE 0: HEADER (15r × 7c)

### Column roles (rows 0–2):

```
Col 0 = Template label (left)      — NEVER write data here
Col 1 = Data (spans cols 1–4)      — PBCU / Works Manager / Description
Col 5 = Template label (right)     — NEVER write data here (B7-R1)
Col 6 = Data (right side)          — Site / Date / PC (B7-R2)
```

### Row map:

```
Row  0: cells[1] = PBCU line (single string, no \n)  |  cells[6] = ■ Site (address only)
Row  1: cells[1] = ■ Works Manager                   |  cells[6] = ■ Date
Row  2: cells[1] = ■ Description                     |  cells[6] = ■ PC
Row  3: HRCW — falling_2m(c1)    telecom_tower(c3)   demolition(c5)
Row  4: HRCW — disturb_asb(c1)   load_bearing(c3)    confined_space(c5)
Row  5: HRCW — shaft_trench(c1)  explosives(c3)      pressurised_gas(c5)
Row  6: HRCW — chemical_lines(c1) near_powerlines(c3) flammable_atm(c5)
Row  7: HRCW — tilt_up(c1)       traffic_corridor(c3) powered_mobile(c5)
Row  8: HRCW — artificial_temp(c1) water_drowning(c3) diving(c5)
Row  9: cells[2] = ■ Supervisor                      |  cells[5] = ■ Date  ← cells[5] NOT [6]
Row 10: DO NOT TOUCH (toolbox meetings text)
Row 11: cells[2] = ■ Project Manager                 |  cells[5] = ■ Date  ← cells[5] NOT [6]
Row 12: DO NOT TOUCH (control measures text)
Row 13: cells[2] = ■ Project Manager (reviewer)      |  cells[5] = ■ Date  ← cells[5] NOT [6]
Row 14: DO NOT TOUCH (SWMS retention notice)
```

### Critical rules:

| Rule | Detail |
|---|---|
| B7-R1 | cells[5] in rows 0–2 = template label column — NEVER write data here |
| B7-R2 | cells[6] in rows 0–2 = data column for right-hand fields |
| B7-R3 | ■ Site = site address ONLY — no assembly point, no emergency contact |
| B7-R4 | PBCU = single continuous string — NO `\n` characters permitted |
| B7-R5 | Emergency details go in Emergency Response task controls ONLY |
| B7-R6 | Rows 9/11/13 date → cells[5] NOT cells[6] (merged cell behaviour) |

---

## PART 4 — TABLE 1: PPE SUMMARY (1r × 2c)

```
Row 0: cells[0] = "PPE required:" (template label — preserve)
       cells[1] = ■ PPE: [content]  ← ALWAYS write here
```

Rule B1-R1: Table 1 PPE must be written independently of Table 7 Row 0.
Both must receive identical PPE content — they serve different layout purposes.

---

## PART 5 — TABLE 2: CONSOLIDATED SUMMARY (2+ rows × 7c)

### Column map:

```
Col 0: Task title only (first line before \n) — width 3116 dxa
Col 1: hazard_summary (or first 200 chars of hazard if absent) — width 2693 dxa
Col 2: Pre-control risk — colored cell (_inject_risk_cell) — width 1134 dxa
Col 3: control_summary (or first 200 chars of controls if absent) — width 4536 dxa
Col 4: Post-control risk — colored cell (_inject_risk_cell) — width 1276 dxa
Col 5: Responsible person — width 1701 dxa
Col 6: Short code — split run formatting — width 936 dxa
```

### Row 0 (template header — preserve):

```
Task | Hazard | Risk (Pre) | Control | Risk (Post) | Responsibility | Code
```

### Rule B10-R1: Header repeat mandatory before any data rows.

```python
_set_header_repeat(con_table)  # STEP 1 — always first
```

### Short code formatting in Col 6:

```
Prefix (e.g. "WAH-"):  9pt Calibri, black, normal
Suffix M/L (e.g. "M4"): 9pt Calibri, black, normal
Suffix H (e.g. "H6"):   9pt Calibri, black, BOLD
```

No background colour on cell. Bold weight only differentiates high-risk codes.

---

## PART 6 — TABLE 3: DETAIL RISK ASSESSMENT (2+ rows × 7c)

### Column map:

```
Col 0: Full task text (name + \n + description) — width 2486 dxa
Col 1: Full hazard text — width 2084 dxa
Col 2: Pre-control risk — colored cell — width 1256 dxa
Col 3: Full control text (MAX 1400 chars) — width 5653 dxa
Col 4: Post-control risk — colored cell — width 1276 dxa
Col 5: Responsible person — width 1701 dxa
Col 6: Short code — split run formatting — width 936 dxa
```

### Row 0 (template header — preserve):

```
Task | Hazard | Risk (Pre) | Control | Risk (Post) | Responsibility | Code
```

### Rule B11-R1: Header repeat mandatory before any data rows.

```python
_set_header_repeat(det_table)  # STEP 1 — always first
```

### Control column limit:

1400 characters maximum. Auto-truncated at 1397 + "..." with console warning.
If controls consistently exceed 1400 chars — split into two tasks.

### Risk cell colours:

```
Score  Label         Background  Text
  1    Low (1)       00B050      White
  2    Low (2)       00B050      White
  3    Medium (3)    FFFF00      BLACK  ← exception
  4    Medium (4)    FFFF00      BLACK  ← exception
  6    High (6)      FF0000      White
  9    High (9)      FF0000      White
```

---

## PART 7 — TABLE 4: SWMS AMENDMENTS (8r × 6c)

⛔ **DO NOT TOUCH** — template content only.
Contains amendment tracking structure for post-issue changes.

---

## PART 8 — TABLE 5: RISK MATRIX (13r × 6c)

⛔ **DO NOT TOUCH** — reference only.
Contains the 3×3 likelihood × consequence matrix used for scoring guidance.

---

## PART 9 — TABLE 6: LEGISLATION & REVIEW (2r × 2c)

```
Row 0: cells[0] = "Relevant legislation:" (template label — preserve)
       cells[1] = existing legislation text + LEGISLATION_APPEND  ← APPEND ONLY
Row 1: DO NOT TOUCH — review frequency text
```

### Rule B2-R1: APPEND — never overwrite.

```python
leg_cell = doc.tables[6].rows[0].cells[1]
_set_cell_text_9pt(leg_cell, leg_cell.text.strip() + leg_append)
```

Existing template text begins: `"WHS Act 2011 (NSW), WHS Regulation 2017 (NSW)..."`
`LEGISLATION_APPEND` adds job-specific standards after the existing text.

---

## PART 10 — TABLE 7: REQUIREMENTS (8r × 2c)

### Row map:

```
Row 0: cells[1] = ■ PPE: [content]                ← POPULATE
Row 1: cells[1] = ■ Permits Required: [content]   ← POPULATE
Row 2: Construction Industry Induction Card...     ← ⛔ PRESERVE
Row 3: cells[1] = ■ Qualifications: [content]     ← POPULATE
Row 4: cells[1] = ■ Plant: [content]              ← POPULATE
Row 5: Daily pre-start checks...                   ← ⛔ PRESERVE
Row 6: cells[1] = ■ Substances: [content]         ← POPULATE
Row 7: A-frame ladders may be used...              ← ⛔ PRESERVE
```

### Preserved rows — exact template content:

| Row | Content (preserve exactly) |
|---|---|
| 2 | Construction Industry Induction Card and Safe Work Method Statement |
| 5 | Daily pre-start checks recorded and maintenance as per manufacturer specification |
| 7 | A-frame ladders may be used for short-duration painting tasks where EWP is not reasonably practicable — site-specific Working at Heights Risk Assessment (WaH RA) required |

---

## PART 11 — TABLES 8 AND 9

⛔ **DO NOT TOUCH** — worker sign-off and amendments continuation.

---

## PART 12 — HRCW CHECKBOX MAP

Validated against SWMS_Template.docx 19/02/2026.
Replace `[   ]` with `[✓]` using `_tick_hrcw_boxes()`.

### Complete map:

```
Key                        Row  Col  Template text (abbreviated)
─────────────────────────  ───  ───  ──────────────────────────────────────
falling_2m                  3    1   [   ] Risk of a person falling more than 2m
telecom_tower               3    3   [   ] Work on a telecommunication tower
demolition                  3    5   [   ] Demolition of load-bearing structure
disturb_asbestos            4    1   [   ] Likely to involve disturbing asbestos
load_bearing                4    3   [   ] Temporary load-bearing support
confined_space              4    5   [   ] Work in or near a confined space
shaft_trench                5    1   [   ] Work in or near a shaft or trench
explosives                  5    3   [   ] Use of explosives
pressurised_gas             5    5   [   ] Work on or near pressurised gas mains
chemical_lines              6    1   [   ] Work on or near chemical, fuel or refrigerant lines
near_powerlines             6    3   [   ] Work on or near energised electrical installations
flammable_atmosphere        6    5   [   ] Work in an area that may have a contaminated or flammable atmosphere
tilt_up_precast             7    1   [   ] Tilt-up or precast concrete elements
traffic_corridor            7    3   [   ] Work on, in or adjacent to a road or railway
powered_mobile_plant        7    5   [   ] Work in an area with movement of powered mobile plant
artificial_temperature      8    1   [   ] Work in areas with artificial extremes of temperature
water_drowning              8    3   [   ] Work in or near water or other liquid
diving                      8    5   [   ] Diving work
```

### Common combinations by work type:

| Work Type | Keys to set True |
|---|---|
| EWP painting | `falling_2m`, `powered_mobile_plant` |
| Scaffold painting | `falling_2m` |
| Ladder only | `falling_2m` |
| Rope access (IRA) | `falling_2m` |
| Bonded asbestos painting | `disturb_asbestos`, `falling_2m` (if heights) |
| Lead encapsulation at height | `falling_2m` |
| Spray in enclosed area | `flammable_atmosphere` |
| Near refrigerant/fuel lines | `chemical_lines` |
| Near live electrical | `near_powerlines` |
| Near traffic | `traffic_corridor` |
| Near water/dam | `water_drowning` |
| Tilt-up construction | `tilt_up_precast`, `falling_2m` |
| Confined space work | `confined_space` |

---

## PART 13 — QUICK RULES SUMMARY

| Rule | Description |
|---|---|
| B1-R1 | Table 1 AND Table 7 Row 0 both receive identical PPE content |
| B2-R1 | Table 6 Row 0 — APPEND only, never overwrite |
| B2-R2 | Table 6 Row 1 — DO NOT TOUCH |
| B3-R1 | Title paragraph[0] — 14pt Calibri Bold |
| B4-R1 | All cell text — 9pt Calibri via `_set_cell_text_9pt()` |
| B5-R1 | Risk scores: 1, 2, 3, 4, 6, 9 only — others raise ValueError |
| B5-R2 | Yellow (FFFF00) cells use BLACK text — all others white |
| B6-R1 | HRCW keys must exactly match HRCW_MAP — no custom keys |
| B7-R1 | cells[5] rows 0–2 = label column — never write data |
| B7-R2 | cells[6] rows 0–2 = data column (right side) |
| B7-R3 | ■ Site = address only — no assembly point or emergency contact |
| B7-R4 | PBCU = single string, no `\n` |
| B7-R5 | Emergency details in Emergency Response task controls only |
| B7-R6 | Rows 9/11/13 date → cells[5] not cells[6] |
| B8-R1 | `_set_header_repeat()` before any data rows — tables[2] and tables[3] |
| B9-R1 | Short codes auto-generated — never manually entered in task dict |
| B9-R2 | H tier suffix (H6/H9): bold black — prefix always normal weight |
| B10-R1 | Consolidated: use summary keys if present — fallback 200 chars |
| B11-R1 | Detail: full text — controls MAX 1400 chars |
| B12-R1 | tables[7] rows 2, 5, 7 — PRESERVE always |

---

*Template rules validated: 19/02/2026*
*Template: SWMS_Template.docx (10 tables)*
*Engine: SWMS_BASE.py v16.0*


---

## E — CONSOLIDATED TABLE DEFENSIBILITY STANDARD (merged from SWMS_CONSOLIDATED_RULES.md)

## Purpose

This document defines the writing standard for the **Consolidated Summary table**
(`tables[2]`) in all SWMS documents produced by this system.

The Detail table (`tables[3]`) continues to carry full hierarchical control text.
This document governs only the `control_summary` and `hazard_summary` fields
in each task dict — the values that populate the Consolidated table.

**Core principle:** Consolidated ≠ vague.
A short row is only acceptable if it tells a worker what to do AND tells an
auditor what was verified. Generic summaries without verification anchors are
not acceptable at any risk tier.

---

## 1. The Three Non-Negotiable Elements (All H-Tier Tasks)

Every `control_summary` for an H-tier task (pre score 6 or 9) must contain:

| Element | What it means | Example |
|---|---|---|
| **Verification action** | What gets checked, confirmed, sighted, or recorded | "pre-start recorded (no defects); HRL licence sighted" |
| **Isolation control** | Exclusion zone, drop zone, or physical separation — described functionally | "exclusion zone min 3m extended to full fall-line" |
| **Stop-work trigger** | What condition breaks the method and halts work | "stop-work for unsafe ground/weather, defect, or barrier/spotter loss" |

If any of these three elements is absent from an H-tier control_summary, the
field must be rewritten before the script is run.

---

## 2. The Fall-Line Rule (Exclusion Zones)

**Never write a fixed distance alone.**

Always write:

> "exclusion zone min [X]m — extend to full fall-line/drop zone as required"

For jobs where the exact fall-line cannot be determined before site setup,
add the note:

> "fall-line distance to be confirmed on site before EWP positioning / work commences"

**Rationale:** A fixed 3m zone is indefensible for multi-storey work where
the actual drop zone may extend 10–15m from the base of the structure.
The fall-line rule ensures the zone is functionally correct, not nominally correct.

---

## 3. Minimum Defensible Set by Risk Class

### A — H-Tier Tasks (pre 6 or 9)

Maximum two short lines. Every element below must be present:

- Pre-start / inspection: "completed and recorded / no defects"
- Competency: "verified / sighted" (licence or qualification as applicable)
- Critical setup condition: "confirmed within manufacturer / engineer / spec limits"
- Isolation: exclusion or drop zone described with fall-line rule
- Supervision: "spotter assigned / confirmed as required"
- Stop-work triggers: 3–6 key conditions in one phrase

### B — M-Tier Tasks (pre 3 or 4)

One line. Must include at minimum:

- One isolation or administrative control
- One clear stop-work trigger where a credible breach condition exists

### C — L-Tier Tasks (pre 1 or 2) — SYS / REC

Short phrase. Must include:

- Confirmation of governance action completed
- Record retention anchor
- Change management rule (see Section 5)

### D — EMR-H9 (always final task, always locked)

Maximum three bullets or one compact paragraph. Must include all four:

1. "Call 000 immediately; supervisor directs responders (site address available)"
2. Specific rescue steps for the access method used on this job (EWP, IRA, scaffold — match the method)
3. Suspension intolerance / medical response protocol relevant to the access method
4. "First aider / kit confirmed on site; muster point confirmed at daily toolbox"

---

## 4. Control Wording Templates (Use These — Do Not Paraphrase)

These templates are the validated minimum defensible sets for each code.
Use them verbatim as the starting point. Edit only to insert job-specific
values (distances, licence types, access method details).

---

### WAH-H6 — EWP / Scaffold / Ladder Access

```
Pre-start recorded (no defects); [licence type] sighted; set-up on firm level
hardstand within manufacturer limits; harness clipped to basket anchor (gate closed);
exclusion zone min [X]m (extend to full fall-line — confirm on site before EWP
positioning) with barriers/signs; spotter as required; stop-work for unsafe
ground/weather, defect, or barrier/spotter loss.
```

---

### IRA-H6 — Industrial Rope Access

```
Anchors verified (engineered/approved); two-rope system buddy-checked; edge/rope
protection in place; drop zone to fall-line barricaded; rescue kit + trained rescue
capability on site; comms confirmed; stop-work for weather, anchor uncertainty,
equipment defect, or zone breach.
```

---

### SIL-H6 — Silica / Dust (Dominant Hazard)

```
Wet/extraction controls operating; P2/P3 worn as required; containment/exclusion
in place; housekeeping to prevent migration; RCD/tagging verified for powered tools;
stop-work if suppression/containment fails.
```

---

### ENV-M4 or ENV-H6 — Chemical / Environmental

```
SDS reviewed; ventilation/controls applied; correct PPE; safe storage/decanting;
spill kit on site; stop-work for uncontrolled spill/exposure.
```

For surface preparation (paint only — no masonry, no silica):

```
SDS reviewed; [tool control e.g. rated tip, trigger lock]; [containment e.g.
drop sheets]; tools lanyard-secured; debris/wash-off to waste (not stormwater);
stop-work if debris or wash-off cannot be contained.
```

---

### STR-H6 — Structural Works

```
Engineer/PC approval confirmed; temporary support as required; controlled sequence;
drop zone barricaded; stop-work if instability/cracking/movement observed.
```

---

### TRF-M4 — Traffic / Public Interface

```
Barriers/signage; controlled pedestrian route; [plant/boom] confirmed within site
boundary before operation; stop-work if zone breached or road/footpath occupancy
required without approval; TPMP implemented if required; spotter/marshal for
interface periods and deliveries.
```

For occupied residential or public premises — add:

```
Residents/public notified before commencement; work hours coordinated with building
management; site secured end of each shift; emergency egress maintained at all times.
```

---

### SYS-L1 / REC-L1 — Site Governance

```
Site induction completed day one (recorded); daily toolbox/pre-start conducted and
recorded; SWMS brief + sign-on before work each day — no signature, no start;
records retained.
```

Always append the change management rule (see Section 5).

---

### EMR-H9 — Emergency Response (EWP Access)

```
Call 000 immediately; supervisor directs responders (site address available).
EWP rescue: trained person uses ground override controls (location briefed daily)
to lower basket; if inoperable — isolate area, maintain comms, await FRNSW.
Treat suspension intolerance: keep upright, monitor ABC, call 000 if unresponsive.
First aider/kit confirmed on site; muster point confirmed at daily toolbox.
```

---

### EMR-H9 — Emergency Response (Rope Access)

```
Call 000 immediately; supervisor directs responders (site address available).
IRA rescue: trained rescue operator initiates lower or raise per rescue plan —
plan briefed and rehearsed before work starts each day. Rescue kit confirmed on
site. Treat suspension intolerance: keep upright, monitor ABC, call 000 if
unresponsive. First aider/kit confirmed on site; muster point confirmed at daily
toolbox.
```

---

## 5. Change Management Rule (Mandatory — Include in SYS Row)

Every SWMS produced under this system must include the following rule,
embedded in the SYS-L1 control_summary:

> "Method or site change: STOP, update SWMS, re-brief all workers, re-sign
> before recommencing."

This rule satisfies the WHS Regulation 2017 r.299 requirement that a SWMS
be reviewed and updated when conditions change.

---

## 6. Style Rules

| Rule | Apply |
|---|---|
| Use verbs | recorded / verified / confirmed / established / assigned / sighted / stop-work |
| Avoid filler | Never use "ensure", "appropriate", "as required" unless the phrase is meaningless without it |
| Length — H6/H9 | One line preferred; two short lines maximum |
| Length — M/L | One short phrase |
| Length — EMR | Three bullets or one compact paragraph; never more |
| Commas not bullets | Write control_summary as a comma-separated run-on — no bullet points inside the string |

---

## 7. Consolidated Table Acceptance Test

Before issuing a SWMS, verify the consolidated table passes all four checks:

| Check | Pass condition |
|---|---|
| ✅ H-tier minimum defensible set | Every H6/H9 row has verification + isolation + stop-work trigger |
| ✅ Fall-line rule | No fixed distance without fall-line extension note |
| ✅ EMR-H9 rescue steps | Specific to access method used on this job |
| ✅ Change management | SYS row includes STOP / update / re-brief / re-sign rule |

If any check fails — rewrite the row. Do not proceed to generation.

---

## 8. Relationship to Other System Files

| File | Relationship |
|---|---|
| `SWMS_TASK_LIBRARY.md` | Provides `controls` (detail table) — this file governs `control_summary` (consolidated table) |
| `SWMS_GENERATOR_MASTER_v16.0.md` | Governs code selection, CCVS triggers, audit strings — this file governs consolidated wording only |
| `SWMS_METHODOLOGY.md` | Governs the nine-step decision logic — this file governs the output format of step 4 (control selection) |
| `SWMS_BASE_GENERAL.py` | `control_summary` key in each task dict populates `tables[2]` col 3 via `_populate_consolidated_table()` |

---

## 9. Version History

| Version | Date | Change |
|---|---|---|
| v1.0 | 20/02/2026 | Initial release — consolidated defensibility standard, fall-line rule, templates for all 15 codes + EMR, change management rule, acceptance test |

---

---


---

*End of SWMS_GENERATOR_MASTER_v16.0*
*Validated: 19/02/2026*
*Engine: SWMS_BASE.py v16.0*
*Template: SWMS_Template.docx (10 tables)*
*Methodology: SWMS_METHODOLOGY.md v16.1*

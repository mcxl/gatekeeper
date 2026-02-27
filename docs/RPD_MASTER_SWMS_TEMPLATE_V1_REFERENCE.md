# RPD_MASTER_SWMS_TEMPLATE_V1 — Reference Specification

**Document:** RPD_MASTER_SWMS_TEMPLATE_V1.docx
**Version:** V1 (February 2026 upload)
**Font:** Aptos 8pt throughout (101600 EMU)
**Page size:** A4 Landscape

---

## 1. Document Structure

| Table | Name | Rows × Cols | Purpose |
|-------|------|-------------|---------|
| 0 | Header | 15 × 7 | PCBU, site address, works manager, dates, HRCW checkboxes, compliance sign-off |
| 1 | Task Table | 21 × 7 tc (8 grid cols, Task col merged span=2) | 20 tasks — header + 20 data rows |
| 2 | Amendments (short) | 8 × 6 | Amendment log (in-document) |
| 3 | Risk Matrix | 13 × 6 | 3×3 risk matrix + hierarchy of controls |
| 4 | Legislation | 2 × 2 | WHS Act/Regulation references |
| 5 | Requirements | 8 × 2 | PPE, permits, training, qualifications, plant, maintenance, hazardous substances, WAH assessment |
| 6 | Worker Sign-off | 33 × 4 | Induction sign-off (Date, Name, Signature, Confirmation) |
| 7 | Amendments (extended) | 34 × 6 | Extended amendment log at end of document |

---

## 2. Content Authority Hierarchy — SWMS Generation

When generating or reviewing SWMS content (task sequencing, hold point conditions, control measures, engineering controls, admin procedures, stop work triggers), the following reference hierarchy applies in order of authority:

### Primary Reference: Hansen Yuncken (HY) Procedures and Standards

Hansen Yuncken documents are the **primary authority** for:

- **Activity sequencing** — the order in which tasks must be performed
- **Hold point conditions** — what must be verified before work commences (CCVS HOLD POINT triggers)
- **Engineering controls** — required physical controls and design specifications
- **Administrative controls** — permit requirements, inspection regimes, documentation
- **Stop work triggers** — conditions requiring immediate work cessation
- **Exclusion zones and clearance distances** — HY site-specific requirements
- **Plant and equipment requirements** — specifications, certifications, inspection frequencies

HY documents are located in:
- **Local (Gatekeeper):** `C:\Users\AlanRichardson\gatekeeper\reference-docs\principal-contractor-procedures`
- **Google Drive (backup):** `hansen-yuncken-procedures/` (folder ID: `1GRZJg0pjpaNn66fuSXpvtWJP0fb5q0PW`) and `hansen-yuncken-standards/` (folder ID: `1PDpTnvA6Hh_RF8LavkG914LrevO-D3bQ`)

**Status:** Files uploaded but not yet indexable by Drive API. Once accessible, cross-reference all SWMS control text against HY requirements and refine accordingly.

### Secondary Reference: SafeWork NSW Codes of Practice and WHS Regulation

Where HY documents are silent or do not cover a specific hazard:

- SafeWork NSW Codes of Practice (Managing the Risk of Falls, Excavation, Demolition, Confined Spaces, etc.)
- WHS Regulation 2017 (NSW) — Chapter 6 (Construction), Chapter 7 (Hazardous Chemicals), Chapter 4 Part 4.5 (HRWL)
- AS/NZS Standards referenced in HY or SafeWork NSW documents

### Tertiary Reference: RPD Internal Standards

Where neither HY nor SafeWork NSW specifically addresses a control:

- RPD Master SWMS task libraries (this document and the 8 master SWMS documents)
- RPD operational experience and site-specific knowledge
- Industry best practice

### Application Rule

When generating any SWMS — whether Master Mode (fixed task libraries) or General Mode (task selection per job):

1. **Check HY first** — does HY have a procedure or standard covering this activity? If yes, the SWMS must align with HY requirements. HY hold points become CCVS HOLD POINT conditions. HY sequencing governs task order.
2. **Fill gaps from SafeWork NSW** — where HY is silent, apply SafeWork NSW Codes of Practice and WHS Regulation.
3. **RPD standards fill remaining gaps** — where neither HY nor SafeWork NSW covers a specific control, apply RPD internal standards.
4. **Never contradict HY** — if an RPD master task text conflicts with an HY requirement, the HY requirement prevails. Flag the conflict to Alan for master text update.

---

## 3. Formatting Locks (Applied)

All 8 tables have the following locks:

| Lock | Status | Count |
|------|--------|-------|
| `tblLayout type="fixed"` | ✅ All 8 tables | 8 |
| `cantSplit` on all rows | ✅ All rows | 134 total (15+21+8+13+2+8+33+34) |
| `tcW type="dxa"` | ✅ All cells — exact widths | All data cells |
| `tblBorders` | ✅ Dotted `BFBFBF` sz=2 — top/left/bottom/right/insideH/insideV | All 8 tables |

### Header Row Repeat (`tblHeader`)

| Table | Rows with tblHeader | Notes |
|-------|---------------------|-------|
| 1 (Task) | Row 0 only | Header repeats on every page |
| 2 (Amendments short) | Rows 0–1 | Two-row header |
| 6 (Sign-off) | Row 0 only | |
| 7 (Amendments extended) | Rows 0–1 | Two-row header |

All other tables: no tblHeader flags.

---

## 4. Page Layout

| Property | Value |
|----------|-------|
| Top margin | 360045 EMU (~28.3pt) |
| Bottom margin | 254000 EMU (~20pt) |
| Left margin | 457200 EMU (36pt) |
| Right margin | 457200 EMU (36pt) |
| Header distance | 450215 EMU |
| Footer distance | 254000 EMU |
| Footer font | 7pt, spacing after=0, line=200 |

---

## 5. Table 0 — Header

15 rows × 7 columns. Key fields with placeholder text:

| Row | Col | Field | Placeholder |
|-----|-----|-------|------------|
| 0 | 1 | PCBU | Robertson's Remedial and Painting Pty Ltd (pre-filled) |
| 0 | 6 | Site | `[Insert Site Address Here]` |
| 1 | 1 | Works Manager | `[Insert Project Manager Here]` |
| 1 | 6 | Date SWMS provided to PC | `[Insert Date Here]` |
| 2 | 1 | Work activity description | `[Insert Description Here]` |
| 2 | 6 | Principal Contractor | Robertson's Remedial and Painting Pty Ltd (pre-filled) |
| 9 | 5–6 | Compliance date | `[Insert Date Here]` |
| 11 | 5–6 | Reviewer date | `[Insert Date Here]` |
| 13 | 5–6 | Review date | `[Insert Date Here]` |

### HRCW Checkboxes (Rows 3–8)

Pre-ticked in master template:
- `[✓] Risk of a person falling more than 2 metres` (Row 3)
- `[✓] Work in an area with movement of powered mobile plant` (Row 7)

All other boxes: `[   ]` — tick per job scope.

---

## 6. Table 1 — Task Table

### Structure

- 21 rows: 1 header + 20 task rows
- 7 tc elements per row (8 grid columns — Task column has `gridSpan=2`)
- Column widths (DXA): Task=2227+10 (gridSpan=2), Hazard=2458, Risk Pre=947, Control=6544, Risk Post=847, Responsibility=1451, Code=908
- Row height: `trHeight val=200` (auto-expand)

### Table Borders

All borders on Task Table (and all 8 tables): **dotted, `BFBFBF` grey, sz=2**. Applied at table level (`tblBorders`) — no cell-level overrides. Covers top, left, bottom, right, insideH, insideV.

### Header Row

- Background shading: `DBE5F1` (light blue)
- Font: **Aptos 8pt bold**
- `tblHeader` set — repeats on every page

### Task Register — All 20 Tasks

| Row | Task | Risk Pre | Risk Post | Code | Type |
|-----|------|----------|-----------|------|------|
| 1 | Site Induction, Daily Sign-In and SWMS Induction | Low (1) | Low (1) | SYS-L1 | STD |
| 2 | Emergency Response | High (9) | Low (1) | SYS-H9 | STD |
| 3 | Residents and Public Interface | Medium (3) | Low (1) | SYS-M3 | STD |
| 4 | High Access — Ladder Use (Short-Duration Only) | High (6) | Low (2) | WAH-H6 | CCVS |
| 5 | Scaffold — Erect, Use, and Dismantle | High (6) | Low (2) | WAH-H6 | CCVS |
| 6 | Industrial Rope Access — Rope Setup and Rigging (NSW) | High (6) | Low (2) | IRA-H6 | CCVS |
| 7 | Work-Positioning System — Fall Restraint | High (6) | Low (2) | WAH-H6 | CCVS |
| 8 | EWP Operation — Boom and Scissor Lift | High (6) | Low (2) | WAH-H6 | CCVS |
| 9 | Jackhammering, Cutting, Grinding and Core Drilling — Silica Dust | High (6) | Low (2) | SIL-H6 | CCVS |
| 10 | Manual Handling | Medium (3) | Low (1) | PRE-M3 | STD |
| 11 | Housekeeping and Waste Management | Low (2) | Low (1) | PRE-L2 | STD |
| 12 | Balcony Security (Occupied Residential Apartments) | Medium (3) | Low (2) | SYS-M3 | STD |
| 13 | Hazardous Chemicals — Paints, Solvents, and Coatings | Medium (4) | Low (2) | HAZ-M4 | STD |
| 14 | High-Pressure Water Cleaning | Medium (4) | Low (2) | PRE-M4 | STD |
| 15 | Surface Preparation — Non-Silica-Lead | Medium (4) | Low (2) | PRE-M4 | STD |
| 16 | Sealant Replacement and Recaulking | Medium (4) | Low (2) | PRE-M4 | STD |
| 17 | Exterior and Interior Painting — Brush and Roller Application | Medium (4) | Low (1) | PRE-M4 | STD |
| 18 | Lead Paint Assessment and 6-Step Encapsulation | High (6) | Low (2) | HAZ-H6 | CCVS |
| 19 | Painting — NON-FRIABLE (Bonded) Asbestos Cement Sheet (Painting Only) | High (6) | Low (2) | HAZ-H6 | CCVS |
| 20 | Hot and Dangerous Weather | Medium (3) | Low (2) | SYS-M3 | STD |

### Risk Cell Colours

| Score | Fill | Text Colour |
|-------|------|-------------|
| High (6), High (9) | `FF0000` red | **White (`FFFFFF`)** |
| Medium (3), Medium (4) | `FFFF00` yellow | **Black (`000000`)** |
| Low (1), Low (2) | `00FF00` green | **Black (`000000`)** |

Text colour must contrast with fill — white on red, black on yellow and green.

### Code Column Format

Code cell has **no background colour** (no shading). Code text is **black bold** for all tasks (STD and CCVS).

---

## 7. CCVS HOLD POINT Control Cell Format — LOCKED SPECIFICATION

### Paragraph Structure (CCVS Tasks)

CCVS tasks have multi-paragraph control cells with numbered/bulleted sub-items. Four paragraph types:

| Type | List? | Bold | Spacing | Font |
|------|-------|------|---------|------|
| Header line | No list | All bold | before=20, after=20, line=276 | Aptos 8pt (sz=16 half-pt) |
| Section label (Engineering/Admin/PPE/STOP WORK) | No list | Label bold, trailing space regular | before=20, after=20, line=276 | Aptos 8pt |
| Numbered item (HOLD POINTS) | numId varies, ilvl=0, format `1. 2. 3.` | Regular text | before=20, after=20, line=276 | Aptos 8pt |
| Bullet item (Eng/Admin/PPE/STOP WORK) | numId varies, ilvl=0, open circle `o` | Regular text | before=20, after=20, line=276 | Aptos 8pt |

**Note:** Template master rows may have `before=None after=None` on some paragraphs (inherited from style). New generated tasks always set `before=20 after=20` explicitly. Both render identically — the explicit form is preferred for consistency.

### CCVS Control Structure (mandatory order)

```
¶ {CODE} ({Level}-{Score}) CCVS HOLD POINTS:           [bold, no list]
¶ HOLD POINT — Do not commence until:                   [bold, no list]
  1. Condition 1                                         [numbered 1. 2. 3.]
  2. Condition 2                                         [numbered 1. 2. 3.]
  ...
¶ Engineering:                                           [bold label, no list]
  • Engineering control 1                                [bullet list]
  • ...
¶ Admin:                                                 [bold label, no list]
  • Admin control 1                                      [bullet list]
  • ...
¶ PPE:                                                   [bold label, no list]
  • PPE item 1                                           [bullet list]
¶ STOP WORK if:                                          [bold, no list]
  • Stop conditions                                      [bullet list]
```

### Numbering IDs Per CCVS Task

Each CCVS task uses its own set of numbering definition IDs (not a single shared ID):

| Row | Task | numIds used |
|-----|------|-------------|
| 4 | Ladder | 32, 33, 34 |
| 5 | Scaffold | 26, 27, 28, 29 |
| 6 | Rope Access | 19, 30 |
| 7 | Fall Restraint | 2, 18, 19, 20, 21 |
| 8 | EWP | 0, 6, 7, 8, 9 |
| 9 | Silica Dust | 1, 15, 16, 17 |
| 18 | Lead Paint | 10, 11, 12, 13, 14 |
| 19 | Asbestos Cement | 10, 43 |

### Paragraph Counts Per Control Cell

| Row | Total ¶ | Bulleted | Type |
|-----|---------|----------|------|
| 1 | 5 | 0 | STD |
| 2 | 8 | 5 | STD |
| 3 | 1 | 0 | STD |
| 4 | 15 | 9 | CCVS |
| 5 | 19 | 13 | CCVS |
| 6 | 18 | 14 | CCVS |
| 7 | 22 | 15 | CCVS |
| 8 | 20 | 17 | CCVS |
| 9 | 18 | 13 | CCVS |
| 10 | 5 | 0 | STD |
| 11 | 5 | 0 | STD |
| 12 | 5 | 4 | STD |
| 13 | 1 | 0 | STD |
| 14 | 5 | 0 | STD |
| 15 | 5 | 0 | STD |
| 16 | 1 | 0 | STD |
| 17 | 4 | 0 | STD |
| 18 | 11 | 6 | CCVS |
| 19 | 11 | 8 | CCVS |
| 20 | 1 | 0 | STD |

### Standard Task Control Format

Standard tasks use plain paragraphs (no bullet lists) with bold section labels:

```
¶ {CODE} ({Level}-{Score}): Controls in place.          [bold header]
¶ Engineering: {controls}                                [bold label + regular text]
¶ Admin: {controls}                                      [bold label + regular text]
¶ PPE: {items}                                           [bold label + regular text]
¶ STOP WORK if: {conditions}                             [bold label + regular text]
```

Some standard tasks have all sections in a single paragraph (Rows 3, 13, 16, 20). Others split into multiple paragraphs (Rows 1, 2, 10, 11, 12, 14, 15, 17). Row 2 (Emergency Response) is a special case with 5 bulleted items despite being STD type (no HOLD POINT).

---

## 8. Table 5 — Requirements

8 rows × 2 columns. Left column = label, right column = content.

| Row | Label | Content (pre-filled master) |
|-----|-------|---------------------------|
| 0 | PPE required | Steel capped footwear (AS/NZS 2210.3), High-vis vest or shirt (AS/NZS 4602), Eye protection (AS/NZS 1337.1), P2 respirator... |
| 1 | Permits, certificates, approvals | Scaffold licence, EWP licence, Working at Heights training, IRATA certification... |
| 2 | Training required | White Card, SWMS induction, SDS briefing, Working at Heights certification... |
| 3 | Qualifications | Trade certificate, scaffolding licence, EWP licence, IRATA certification... |
| 4 | Plant and equipment | Scaffold, EWP, pressure washer, airless spray unit, power tools... |
| 5 | Maintenance checks | OEM schedule, test-tag 3-monthly per AS/NZS 3012... |
| 6 | Hazardous substances | Chemical register maintained, SDS current, risk assessment per GHS/WHS Reg Chapter 7... |
| 7 | WAH Risk Assessment | Fall prevention hierarchy: eliminate > isolate > minimise... |

---

## 9. SafeWork NSW — High Risk Work Licences (HRWL)

High Risk Work Licences (HRWL) are mandatory under WHS Regulation Chapter 4 Part 4.5 for operating specific machinery or performing hazardous tasks. There are **29 classes** of high risk work. Licences are nationally recognised across all Australian states and territories. All licence classes below must be referenced correctly in SWMS control text, Table 5 (Requirements), and job SWMS site-specific additions. Use the exact class codes.

### Scaffolding (SB, SI, SA)

| Class | Name | Scope |
|-------|------|-------|
| **SB** | Basic Scaffolding | Modular/prefabricated scaffolds, cantilevered materials hoists, ropes/gin wheels, safety nets/static lines, bracket scaffolds |
| **SI** | Intermediate Scaffolding | All SB scope, plus cantilevered crane loading platforms, spurred scaffolds, barrow ramps/sloping platforms, mast climbers, tube and coupler scaffolds |
| **SA** | Advanced Scaffolding | All SI scope, plus hung scaffolds and suspended scaffolds |

**Hierarchy:** SA → SI → SB (higher class covers all lower classes)

### Dogging and Rigging (DG, RB, RI, RA)

| Class | Name | Scope |
|-------|------|-------|
| **DG** | Dogging | Slinging techniques (selection and inspection of lifting gear) and directing a crane/hoist operator in the movement of a load |
| **RB** | Basic Rigging | Movement of plant and equipment, steel erection, hoists (personnel and materials), safety nets, catch nets/platforms, perimeter safety screens, site fences/hoardings |
| **RI** | Intermediate Rigging | All RB scope, plus tilt-up/tilt-slab construction, demolition work, suspended scaffolds (rigging for swing stages) |
| **RA** | Advanced Rigging | All RI scope, plus gin poles, flying foxes, cable-way cranes, guyed derricks, shear legs |

**Hierarchy:** RA → RI → RB → DG (DG is prerequisite for all rigging classes)

### Crane and Hoist Operation

| Class | Name | Scope |
|-------|------|-------|
| **CV** | Vehicle Loading Crane | Capacity 10 metre-tonnes or more |
| **CN** | Non-slewing Mobile Crane | Capacity over 3 tonnes |
| **C2** | Slewing Mobile Crane (up to 20t) | Capacity up to 20 tonnes |
| **C6** | Slewing Mobile Crane (up to 60t) | Capacity up to 60 tonnes |
| **C1** | Slewing Mobile Crane (up to 100t) | Capacity up to 100 tonnes |
| **CO** | Slewing Mobile Crane (over 100t) | Capacity over 100 tonnes |
| **CT** | Tower Crane | All tower cranes |
| **CS** | Self-erecting Tower Crane | Self-erecting tower cranes |
| **CD** | Derrick Crane | All derrick cranes |
| **CP** | Portal Boom Crane | Portal boom cranes |
| **CB** | Bridge and Gantry Crane | Bridge and gantry cranes (cabin-controlled or more than 3 remote-controlled powered operations) |
| **WP** | Boom-type Elevating Work Platform | Boom length 11 metres or more |
| **HM** | Materials Hoist | Materials hoist with cantilever platform |
| **HP** | Personnel and Materials Hoist | Personnel and materials hoist |
| **PB** | Concrete Placing Boom | Knuckle-type articulated booms for placing concrete by pumping — vehicle and satellite mounted |

**Slewing crane hierarchy:** CO → C1 → C6 → C2 (each higher class encompasses CV, CN, RS, and all lower slewing classes)

### Forklift and Order Picker

| Class | Name | Scope |
|-------|------|-------|
| **LF** | Forklift Truck | All forklift trucks |
| **LO** | Order Picking Forklift Truck | Order picking forklift trucks |

### Reach Stacker

| Class | Name | Scope |
|-------|------|-------|
| **RS** | Reach Stacker | Empty container handlers and loaded container handlers |

### Pressure Equipment

| Class | Name | Scope |
|-------|------|-------|
| **BS** | Standard Boiler Operation | Standard boilers with straightforward operations |
| **BA** | Advanced Boiler Operation | All BS scope, plus fully automatic and unattended boilers, superheaters, feedwater heaters, economisers, dual firing |
| **TO** | Turbine Operation | Steam turbine operation |
| **ES** | Reciprocating Steam Engine | Reciprocating steam engine operation |

**Boiler hierarchy:** BA → BS (advanced covers standard)

### HRWL Summary — All 29 Classes

| Category | Classes | Count |
|----------|---------|-------|
| Scaffolding | SB, SI, SA | 3 |
| Dogging | DG | 1 |
| Rigging | RB, RI, RA | 3 |
| Slewing Mobile Crane | C2, C6, C1, CO | 4 |
| Other Crane | CT, CS, CD, CP, CB, CV, CN | 7 |
| Hoist / EWP / Boom | WP, HM, HP, PB | 4 |
| Forklift | LF, LO | 2 |
| Reach Stacker | RS | 1 |
| Pressure Equipment | BS, BA, TO, ES | 4 |
| **Total** | | **29** |

### HRWL Reference Rules

When referencing licences in SWMS control text or requirements:

- Always use the **class code** in parentheses after the licence name, e.g. "Scaffold licence (SB minimum)" or "EWP licence (WP)"
- Where a task requires a **minimum licence class**, state the minimum and note higher classes are acceptable, e.g. "Rigging licence (RB minimum — RI or RA also accepted)"
- Where **no HRWL exists** for a task but competency is required, reference the relevant unit of competency or training standard instead, e.g. "Working at Heights training (RIIWHS204E)" or "IRATA Level 1 minimum"
- The **WP class** (boom-type EWP, boom 11m+) is the only EWP class requiring a HRWL — scissor lifts and boom lifts under 11m require training but not a HRWL
- Licence expiry: **5 years** — renewal required before expiry to continue performing HRW

---

## 10. PPE Terminology — Standardised Terms

All PPE references in control text must use the following standardised terms:

| Old Term | Standardised Term |
|----------|-------------------|
| Safety glasses | **Eye protection** |
| Hearing protection | **Hearing protection (>85 dB)** |
| Gloves (generic) | **Cut-resistant gloves** |
| High-vis vest | **High-vis vest or shirt** |

Specific glove types (nitrile, leather, insulating, blast) remain unchanged — the "cut-resistant gloves" standard applies only where generic "gloves" is used.

**Scope:** PPE standardisation applies to **all rows** — both new generated tasks (52 tasks) and reused master template rows. The build script performs run-level text replacement on reused rows at generation time. Specific glove types (nitrile, leather, insulating, blast, anti-vibration, gauntlet) are preserved — only generic unqualified "gloves" is replaced.

---

## 11. Core Text Protection Rules — CRITICAL

### NEVER Modify

Under **no circumstances** modify text in these cells:

- **Task column** (TC0, gridSpan=2): Task name and description text
- **Hazard column** (TC1): Hazard descriptions
- **Control column** (TC3): All master control text including HOLD POINT conditions, section blocks, and STOP WORK triggers

Master text is the **locked source of truth**.

### Site-Specific Additions

- Append to end of control cell as new paragraphs
- Every addition prefixed `[SITE SPECIFIC]`
- Font: **Aptos 8pt**, colour `#C0504D`
- Bold on `[SITE SPECIFIC]` prefix, regular on content text
- Master text above remains untouched

### Job SWMS Rules

- **Keep all 20 tasks** in every job SWMS — no deletions, no renumbering
- Tasks not applicable to a specific job remain in the document
- Task numbering is fixed (master numbers 1–20)
- New tasks not in master: **flag to Alan and wait for instruction**
- If uncertain whether a change is site-specific or core text modification: **ask Alan first**

---

## 12. Known Anomalies

| Issue | Location | Description | Expected |
|-------|----------|-------------|----------|
| Risk Pre shows code text | Row 19, Risk Pre (TC2) | Displays "HAZ-H6" instead of risk score | Should show "High (6)" with `FF0000` fill |
| Empty Responsibility | Row 19, Responsibility (TC5) | Cell is blank | Should list responsible parties |

---

## 13. Differences from Previous Template Version

| Feature | Previous | Current V1 |
|---------|----------|------------|
| Font | Calibri 8pt | **Aptos 8pt** |
| CCVS bullet numId | Single shared numId=32 for all CCVS tasks | **Each CCVS task has its own set of numIds** (see Section 6) |
| CCVS HOLD POINT numbering | `(1) (2) (3)` | **`1. 2. 3.`** |
| HRCW pre-ticked | Falls >2m only | Falls >2m **+ Powered mobile plant** |
| Risk cell text colour | Not specified | **Contrasting: white on red, black on yellow/green** |
| Code column | Red shading on CCVS tasks | **No shading. Black bold text for all tasks** |
| PPE: safety glasses | "Safety glasses" | **"Eye protection"** |
| PPE: hearing protection | "Hearing protection" | **"Hearing protection (>85 dB)"** |
| PPE: gloves | "Gloves" | **"Cut-resistant gloves"** |
| PPE: high-vis vest | "High-vis vest" | **"High-vis vest or shirt"** |
| Row 19 Risk Pre | High (6) | **Shows "HAZ-H6" — anomaly** |
| Row 19 Responsibility | Populated | **Empty — anomaly** |
| Bottom margin | 400 DXA | **254000 EMU (~20pt)** |
| Task count | 20 | **20** (unchanged) |
| CCVS HOLD POINT tasks | Rows 4–9, 18–19 (8 tasks) | **Rows 4–9, 18–19 (8 tasks)** (unchanged) |

---

## 14. Job SWMS Build — Site-Specific Addition Format

When building a job SWMS from this template:

```
Font:       Aptos 8pt
Colour:     #C0504D
Bold:       [SITE SPECIFIC] prefix bold, content text regular
Spacing:    line=276
List:       No list (plain paragraphs appended after master content)
Position:   After last master paragraph in control cell
```

All 20 tasks remain. No deletions. No renumbering. Site additions in `#C0504D` Aptos 8pt with bold `[SITE SPECIFIC]` prefix.

---

## 15. Build Validation Checklist

When generating SWMS documents from this template, the build script must enforce:

| Check | Rule | Verified |
|-------|------|----------|
| Risk Pre/Post cell fill | High=`FF0000`, Medium=`FFFF00`, Low=`00FF00` | ✅ All 7 docs |
| Risk Pre/Post text colour | High=`FFFFFF` (white), Medium/Low=`000000` (black) | ✅ All 7 docs |
| Code cell shading | None — no fill on any task (STD or CCVS) | ✅ All 7 docs |
| Code cell text | Black bold (`w:b` present, no colour override) | ✅ All 7 docs |
| HOLD POINT numbering | `%1.` format → renders as `1. 2. 3.` | ✅ All 7 docs |
| Bullet format | Open circle `o` (Courier New) for Eng/Admin/PPE/STOP WORK | ✅ All 7 docs |
| Paragraph spacing | `line=276, before=20, after=20` on all control cell paragraphs | ✅ All new tasks |
| Font | Aptos 8pt (sz=16 half-pt) on all new task runs | ✅ All 7 docs |
| cantSplit | Present on every row in Task Table | ✅ All 7 docs |
| tblLayout fixed | Present on Task Table | ✅ All 7 docs |
| abstractNum 18 fix | `(%1)` → `%1.` in template numbering on load | ✅ All 7 docs |
| PPE: eye protection | No "safety glasses" in any task | ✅ All rows (new + reused) |
| PPE: hearing protection (>85 dB) | No unqualified "hearing protection" in any task | ✅ All rows (new + reused) |
| PPE: cut-resistant gloves | No generic "gloves" in any task | ✅ All rows (specific types preserved) |
| PPE: high-vis vest or shirt | No "high-vis vest" without "or shirt" in any task | ✅ All rows (new + reused) |

### Not Yet Applied (requires template V2 or Alan decision)

| Item | Status | Notes |
|------|--------|-------|
| Row 19 Risk Pre anomaly | ⏳ In template | Shows "HAZ-H6" instead of "High (6)" |
| Row 19 Responsibility anomaly | ⏳ In template | Cell is empty |

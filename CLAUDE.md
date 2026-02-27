# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Gatekeeper is a Zero-Trust Safety Framework for the construction industry. It addresses normalization of deviance through mandatory mental checkpoints, audit classification, and data-driven risk analysis. Built by AuditCo (mcxi.com.au).

The SWMS generation system is integrated into Gatekeeper as a core module, operating in two modes from a unified codebase.

## Commands

```bash
# Setup
python -m venv venv
source venv/Scripts/activate   # Windows/Git Bash
pip install -r requirements.txt

# Run tests
pytest tests/

# Run a single test
pytest tests/test_mental_checkpoints.py

# Run a specific test function
pytest tests/test_mental_checkpoints.py::test_function_name

# Build all 7 RPD Master SWMS documents
python src/build_all_swms.py

# Generate a job SWMS (General Mode)
python src/swms_base_general.py
```

## Content Authority Hierarchy

When generating or reviewing SWMS content (task sequencing, hold points, control measures, stop work triggers), follow this hierarchy strictly:

### 1. Primary: Hansen Yuncken (HY) Procedures and Standards
- Located in: `reference-docs/principal-contractor-procedures/`
- Also in: `reference-docs/hansen-yuncken-standards/` and `reference-docs/hansen-yuncken-procedures/`
- HY documents govern: activity sequencing, hold point conditions, engineering controls, admin procedures, stop work triggers, exclusion zones, plant requirements
- **Never contradict HY** — if RPD master text conflicts with HY, flag to Alan for master text update

### 2. Secondary: SafeWork NSW Codes of Practice and WHS Regulation
- Apply where HY is silent on a specific hazard
- Codes of Practice: Falls, Excavation, Demolition, Confined Spaces, etc.
- WHS Regulation 2017 (NSW) — Chapter 4 Part 4.5 (HRWL), Chapter 6 (Construction), Chapter 7 (Hazardous Chemicals)

### 3. Tertiary: RPD Internal Standards
- RPD Master SWMS task libraries and operational experience
- Apply where neither HY nor SafeWork NSW specifically addresses a control

## Architecture

### src/ — Core Modules

#### SWMS Generation (Unified Engine)
- **swms_generator.py** — Task definitions for RPD Master SWMS system. Contains 52 new task definitions across 7 work types. Uses python-docx. All PPE terms standardised (eye protection, hearing protection >85 dB, cut-resistant gloves, high-vis vest or shirt).
- **build_all_swms.py** — Master SWMS builder. Generates 7 master SWMS documents from RPD_MASTER_SWMS_TEMPLATE_V1.docx. Handles row reuse, new task insertion, CCVS formatting, risk cell colours, code cell styling, PPE standardisation on reused rows, numbering format fixes.
- **swms_base_general.py** — General purpose SWMS engine (v16). Intake-form driven, task selection from library. Auto-injects SYS (Task 1) and EMR (final task). Generates Standard and CCVS versions.
- **swms_bulletize.py** — Bullet formatting helper for SWMS document output.

#### Gatekeeper Core
- **mental_checkpoints.py** — `MentalCheckpoint` class: deliberate pause points that interrupt automatic work processes to force safety engagement and prevent complacency.
- **audit_classification.py** — `AuditClassification` class: quantitative risk scoring for site inspections with severity categorisation.
- **data_analysis.py** — Trend identification and proactive risk analysis using pandas/numpy.

### docs/ — System Documentation

#### SWMS Reference Specifications
- **RPD_MASTER_SWMS_TEMPLATE_V1_REFERENCE.md** — Authoritative formatting specification for the RPD template. Covers all 8 tables, formatting locks, CCVS structure, risk cell colours, code column format, PPE terminology, HRWL register (all 29 SafeWork NSW classes), content authority hierarchy, and build validation checklist.
- **RPD_Master_SWMS_Build_Plan.md** — Task assignments for all 7 master SWMS documents. Maps which template rows are reused vs new per document. Contains formatting rules and PPE standardisation log.

#### SWMS v16 General System
- **SWMS_GENERATOR_MASTER_v16_0.md** — Master instructions for general SWMS generation. Code system (15 codes + SYS/EMR), CCVS trigger rules, risk matrix.
- **SWMS_TASK_LIBRARY.md** — Library of pre-written task definitions for all 15 codes. Used by General Mode.
- **SWMS_METHODOLOGY.md** — Nine-step decision logic for task selection and CCVS determination.
- **SWMS_OPERATOR_GUIDE.md** — Guide for operators using the system.
- **USER_INPUT_REQUEST_GENERAL.md** — Intake form template for General Mode jobs.
- **PROJECT_INSTRUCTIONS.md** — Claude Project setup instructions.
- **SWMS_Template.docx** — General SWMS Word template (v16 engine).

#### Templates
- **RPD_MASTER_SWMS_TEMPLATE_V1.docx** — RPD master template. Aptos 8pt, A4 Landscape, 8 tables, 20 fixed tasks. Used by Master Mode.

### rpd-v8-upgrade/ — RPD V8 Consolidation

Contains the governance architecture for the 46→16 SWMS consolidation:
- RPD-GOV-001 (Architecture — 9-code system, CCVS)
- RPD-CCL-001 (Common Controls — 12 tasks)
- RPD-MSW-001 (Painting Master — 18 tasks)

### reference-docs/ — Principal Contractor Procedures

Hansen Yuncken procedures and standards. **Primary authority** for all SWMS content generation. See Content Authority Hierarchy above.

### tests/

Tests mirror the `src/` module names (e.g., `test_mental_checkpoints.py`).

## SWMS Generation Modes

### Master Mode (RPD repetitive work types)

Fixed task registers per work type. All tasks stay in every job SWMS — no deletions, no renumbering. Site-specific additions appended in #C0504D with [SITE SPECIFIC] prefix.

**8 Master SWMS documents:**

| Code | Document | Tasks |
|------|----------|-------|
| MSW-001 | Painting Master | 20 (template base) |
| MSW-002 | Remedial Works | 21 |
| MSW-003 | Spray Painting | 18 |
| MSW-004 | Groundworks | 17 |
| MSW-005 | Cladding Works | 19 |
| MSW-006 | EWP Standalone | 16 |
| MSW-007 | Swing Stage | 16 |
| MSW-008 | Abrasive Blasting | 20 |

**Job SWMS workflow:**
1. Select master for work type
2. Keep all tasks — no deletions
3. Append site-specific additions in #C0504D
4. Prefix additions with [SITE SPECIFIC]

### General Mode (v16 — any industry)

Intake-form driven. 15 working codes (WFR, WFA, WAH, IRA, ELE, SIL, STR, CFS, ENE, HOT, MOB, ASB, LED, TRF, ENV) plus auto-injected SYS and EMR.

**CCVS trigger:** Pre ≥ 6 AND Consequence = 3 AND code in critical list.
**Critical list:** WFR WFA WAH IRA ELE SIL STR CFS ENE HOT MOB ASB LED.
TRF and ENV do not trigger CCVS. EMR never uses CCVS language.

**Job SWMS workflow:**
1. Complete intake form (USER_INPUT_REQUEST_GENERAL.md)
2. Select tasks from SWMS_TASK_LIBRARY.md
3. Populate engine sections 1-3
4. Run engine — generates Standard and CCVS versions

### Code System Mapping (Master ↔ General)

| RPD Master Code | v16 General Code(s) |
|-----------------|---------------------|
| SYS | SYS (auto) |
| PRE | WFR, WFA, STR |
| WAH | WAH |
| IRA | IRA |
| ELE | ELE |
| SIL | SIL |
| HAZ | CFS, ASB, LED |
| MOB | MOB |
| ENV | ENV, TRF |

## Formatting Standards (Both Modes)

- **Font:** Aptos 8pt
- **Risk cells:** High = red fill (#FF0000) white text; Medium = yellow fill (#FFFF00) black text; Low = green fill (#00FF00) black text
- **Code column:** No background, black bold text
- **HOLD POINT numbering:** 1. 2. 3. (not (1) (2) (3))
- **Table borders:** Dotted, #BFBFBF grey, sz=2
- **PPE terms:** Eye protection, hearing protection (>85 dB), cut-resistant gloves (generic only), high-vis vest or shirt

## HRWL Quick Reference

29 SafeWork NSW classes. Always use class code in parentheses:
- Scaffolding: SB, SI, SA
- Dogging/Rigging: DG, RB, RI, RA
- Cranes: CV, CN, C2, C6, C1, CO, CT, CS, CD, CP, CB
- Hoists/EWP/Boom: WP, HM, HP, PB
- Forklift: LF, LO
- Reach Stacker: RS
- Pressure Equipment: BS, BA, TO, ES

Full details in RPD_MASTER_SWMS_TEMPLATE_V1_REFERENCE.md Section 9.

## Workflow

1. Create feature branch from main
2. Write tests first
3. Implement feature
4. Commit with descriptive message

## Boundaries

✅ Always:
- Follow Australian WHS Act 2011 and regulations
- Use FSC-compliant risk language
- Check HY procedures before writing control text
- Use standardised PPE terminology
- Write tests before implementing features
- Use exact HRWL class codes (e.g., "Scaffold licence (SB minimum)")

⚠️ Ask first:
- Changes to gate code classifications
- Modifying SWMS template structure
- Adding new tasks to master SWMS documents
- Changes to CCVS HOLD POINT conditions
- Anything that conflicts with HY procedures

🚫 Never:
- Commit API keys or credentials
- Delete failing tests
- Use non-metric units
- Delete tasks from master SWMS documents
- Modify master control text without Alan's approval
- Use "safety glasses" (use "eye protection")
- Use unqualified "hearing protection" (use "hearing protection (>85 dB)")
- Use generic "gloves" (use "cut-resistant gloves" or specify type)
- Contradict Hansen Yuncken procedures

## Known Gotchas

- Template Row 19 (Asbestos Cement) has Risk Pre showing "HAZ-H6" instead of "High (6)" — anomaly in source template
- Template Row 19 Responsibility cell is empty — anomaly in source template
- python-docx cell indexing is offset by gridSpan merges — Task column spans 2 grid columns, so TC0 via python-docx .cells[] may not match TC0 via XML xpath
- abstractNum 18 in template uses old (1) format — build script patches to %1. on load
- Reused template rows may have None for paragraph spacing before/after (inherited from style) — new tasks set before=20 after=20 explicitly. Both render identically.
- Generic "gloves" replacement must check for specific type prefixes (nitrile, leather, insulating, blast, anti-vibration, gauntlet) — only replace truly generic instances

## Dependencies

Core: pandas, numpy, python-docx (document generation), lxml (XML manipulation). Testing: pytest.

## Import Convention

Modules are imported from `src/` directly:
```python
from src.mental_checkpoints import MentalCheckpoint
from src.audit_classification import AuditClassification
from src.swms_generator import NEW_TASKS_LIBRARY
from src.build_all_swms import build_all
```

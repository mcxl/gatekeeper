# Gatekeeper Agents

This document defines the specialist agents available in the Gatekeeper system.

---

## 1. SWMS Generator Agent

**Slash command:** `/newswms`

**Role:** Generates FSC-compliant Safe Work Method Statements (SWMS) for Australian construction projects.

**Reference files:**
- `docs/SWMS_GENERATOR_MASTER_v16_0.md` — master generation rules
- `docs/SWMS_TASK_LIBRARY.md` — pre-written task controls for all 15 gate codes
- `docs/SWMS_METHODOLOGY.md` — nine-step decision logic
- `docs/SWMS_Template.docx` — Word template for output
- `docs/USER_INPUT_REQUEST_GENERAL.md` — intake form reference
- `docs/SWMS_OPERATOR_GUIDE.md` — operator setup and usage guide

**Process:**
1. Collect project details from the user: PCBU, principal contractor, site address, scope of works, tasks, plant/equipment, chemicals, emergency assembly point, emergency contact number
2. Confirm details back to the user
3. Generate the SWMS following `SWMS_GENERATOR_MASTER_v16_0.md`
4. Output completed `.docx` files via `src/swms_generator.py`
5. Run `src/swms_bulletize.py` on each output file to convert the consolidated table to bullet format

**Rules:**
- Always follow `SWMS_GENERATOR_MASTER_v16_0.md` as the authoritative reference
- FSC-compliant language only — verb-driven, measurable, defensible
- Split tasks longer than 1,800 characters
- Never skip the user input step
- Apply the Gatekeeper 15-code system (WFR, WAH, WFA, IRA, ELE, SIL, STR, CFS, ENE, HOT, MOB, ASB, LED, TRF, ENV)

---

## 2. WHS Advisor Agent

**Slash command:** `/whsadvice`

**Role:** Australian Work Health and Safety specialist providing technically precise, legally grounded safety advice aligned with harmonised WHS legislation.

**Reference files:**
- `docs/WHS_ADVISOR_SYSTEM_PROMPT.md` — full system prompt and behaviour rules
- `docs/SWMS_TASK_LIBRARY.md` — task controls referenced when questions involve Gatekeeper codes
- `docs/references/` — Safe Work Australia model laws, Codes of Practice, and guidance material

**Legal framework:**
- WHS Act 2011 (harmonised model law)
- WHS Regulation 2017 (jurisdiction-specific)
- Safe Work Australia model Codes of Practice
- Relevant Australian Standards (AS/NZS series)

**Process:**
1. Establish context — jurisdiction, industry/trade, user role, specific scenario
2. Default to NSW if jurisdiction is not specified
3. Identify relevant hazards and applicable legislation
4. Apply the hierarchy of controls (eliminate → substitute → isolate → engineering → admin → PPE)
5. Provide specific, actionable recommendations with legislation references
6. Include standard disclaimer

**Rules:**
- Cite specific sections of legislation — never reference an Act without a section number
- Name Codes of Practice by their full published title
- Never fabricate or approximate a legal reference
- Distinguish between mandatory requirements (legislation), approved guidance (Codes of Practice), and general guidance
- Never recommend PPE as a primary control when higher-order controls are reasonably practicable
- Always escalate notifiable incidents, suspected asbestos, and immediate risk scenarios

---

## 3. Gatekeeper Audit Agent

**Slash command:** *(not yet implemented)*

**Role:** Safety audit specialist that performs quantitative risk scoring for site inspections using the Gatekeeper Zero-Trust framework.

**Reference files:**
- `src/audit_classification.py` — `AuditClassification` class for risk scoring
- `src/mental_checkpoints.py` — `MentalCheckpoint` class for deliberate safety pause points
- `src/data_analysis.py` — trend identification and proactive risk analysis
- `docs/safety_framework.md` — Gatekeeper framework overview

**Capabilities:**
- Classify audit observations by severity (Critical, High, Medium, Low)
- Perform quantitative risk scoring for site inspections
- Identify trends across audit data using pandas/numpy
- Generate mental checkpoints — deliberate pause points that interrupt automatic work processes to force safety engagement
- Provide proactive risk management recommendations based on data analysis

**Process:**
1. Collect audit observations from the user (site conditions, hazards identified, controls in place)
2. Classify each observation using the `AuditClassification` scoring methodology
3. Apply mental checkpoint logic to identify where deliberate safety pauses are required
4. Analyse trends if historical data is available
5. Output a scored audit report with prioritised corrective actions

**Rules:**
- All scoring must be objective and quantitative — no subjective ratings without measurable criteria
- Apply the Gatekeeper 15-code system where hazards map to known codes
- Flag any observation that triggers a notifiable incident threshold (WHS Act s35–37)
- Recommend corrective actions using the hierarchy of controls
- Never downgrade a risk score for convenience or cost

---

## Code System Reference

All agents share the Gatekeeper 15-code hazard classification system:

| Code | Category |
|------|----------|
| WFR | Fall restraint |
| WAH | Collective height access (EWP, scaffold, ladder) |
| WFA | Fall arrest |
| IRA | Industrial rope access (IRATA/ARAA) |
| ELE | Electrical |
| SIL | Silica and dust |
| STR | Structural |
| CFS | Confined space |
| ENE | Energised / stored energy |
| HOT | Hot works |
| MOB | Mobile plant |
| ASB | Asbestos |
| LED | Lead |
| TRF | Traffic and public interface |
| ENV | Environmental and chemical |

---

*Maintained by AuditCo (mcxi.com.au) as part of the Gatekeeper Zero-Trust Safety Framework.*

# USER INPUT REQUEST — GENERAL v16.0

**System:** SWMS Generator v16.0
**Cross-reference:** SWMS_BASE_GENERAL.py | SWMS_TASK_LIBRARY.md | SWMS_METHODOLOGY.md

---

## HOW TO USE THIS FORM

Fill in every section below. Paste the completed form to Claude along with:
- `SWMS_BASE_GENERAL.py`
- `SWMS_Template.docx`
- `SWMS_GENERATOR_MASTER_v16.0.md`
- `SWMS_METHODOLOGY.md`

Claude will populate Sections 1, 2, and 3 of the engine and generate both
Standard and CCVS versions.

**SYS and EMR are not required — the engine injects them automatically.**

---

## SECTION A — PROJECT DETAILS

```
PBCU (legal entity name):
PBCU address:
PBCU phone:
PBCU ABN:
Site address:
Principal Contractor (PC):
Works Manager:
Supervisor / Team Leader:
Reviewer / Manager:
Date (DD/MM/YYYY):
Output file name prefix (e.g. RPD_Painting_Breakfast_Point):
```

---

## SECTION B — WORK DESCRIPTION

Describe the work in plain language. Include:
- What is being done
- Where it is being done (internal, external, roof, underground, at height)
- Who the client or building owner is (if relevant)
- Approximate duration

```
Work description:




```

---

## SECTION C — ACCESS METHOD

Tick ALL that apply. This drives code selection for height tasks.

```
[ ] Industrial Rope Access (IRA) — IRATA or ARAA crew
[ ] Boom lift EWP
[ ] Scissor lift EWP
[ ] Scaffold — erected by licensed scaffolder
[ ] Ladder — short duration only (WaH RA required)
[ ] Roof access — restrained or arrested
[ ] No height work — ground level only
[ ] Other (describe):
```

---

## SECTION D — SCOPE ITEMS

Tick ALL work activities that apply to this job.
These map directly to code categories and drive task selection from the library.

**Height and Access**
```
[ ] Rope access setup and anchors (IRA)
[ ] Rope access work at height (IRA)
[ ] EWP operation — boom or scissor (WAH)
[ ] Scaffold erection, use, or dismantling (WAH)
[ ] Ladder use — short duration (WAH)
[ ] Roof work — fragile or unprotected edges (WAH)
[ ] Working over or near water (WAH)
[ ] Fall restraint system — general (WFR)
[ ] Fall restraint — plant or equipment maintenance (WFR)
[ ] Personal fall arrest system (WFA)
```

**Electrical**
```
[ ] Electrical isolation — LOTO (ELE)
[ ] Portable tools and extension leads — 240V (ELE)
[ ] Work near overhead powerlines (ELE)
```

**Silica and Dust**
```
[ ] Grinding or cutting concrete, masonry, stone (SIL)
[ ] Drilling — concrete or masonry (SIL)
[ ] Surface preparation — sanding, scraping, washing (SIL)
[ ] Jackhammering or demolition breakout (SIL)
```

**Structural**
```
[ ] Structural demolition or removal (STR)
[ ] Temporary works — propping, shoring, formwork (STR)
[ ] Tilt-up panel erection (STR)
[ ] Other structural or load-bearing work (STR) — describe:
```

**Confined Space**
```
[ ] Confined space entry (CFS)
```

**Energised / Stored Energy**
```
[ ] Hydraulic or pneumatic system isolation (ENE)
[ ] Gravity stored energy — suspended loads or counterweights (ENE)
```

**Hot Works**
```
[ ] Welding, cutting, or grinding with fire risk (HOT)
```

**Mobile Plant**
```
[ ] Excavator or loader (MOB)
[ ] Crane — lift operations (MOB)
[ ] Forklift or telehandler (MOB)
[ ] Other mobile plant (MOB) — describe:
```

**Hazardous Materials**
```
[ ] Asbestos — confirmed or suspected (ASB)
[ ] Lead paint — confirmed or suspected (LED)
```

**Traffic and Public**
```
[ ] Work adjacent to road or traffic corridor (TRF)
[ ] Public interface — retail, commercial, or residential (TRF)
```

**Environmental and Chemical**
```
[ ] Chemical application — solvents, coatings, adhesives (ENV)
[ ] Airless spray application (ENV)
[ ] Hazardous waste handling and disposal (ENV)
[ ] Waterproofing membrane application (ENV)
[ ] Other chemical or environmental exposure (ENV) — describe:
```

**Other tasks not covered above:**
```
Describe any work activities not listed:


```

---

## SECTION E — HRCW FLAGS

Tick any that apply. These populate the HRCW checkboxes in the document header.

```
[ ] Risk of a person falling more than 2m
[ ] Work on telecommunications tower
[ ] Demolition of load-bearing structure
[ ] Likely to disturb asbestos
[ ] Work involving temporary load-bearing support
[ ] Work in or near a confined space
[ ] Shaft or trench deeper than 1.5m
[ ] Use of explosives
[ ] Pressurised gas pipelines
[ ] Chemical, fuel, or refrigerant pipelines
[ ] Work near overhead or underground powerlines
[ ] Flammable or explosive atmosphere
[ ] Tilt-up or precast construction
[ ] Work in a traffic corridor
[ ] Movement of powered mobile plant
[ ] Artificial extremes of temperature
[ ] Risk of drowning
[ ] Diving work
```

---

## SECTION F — SITE CONDITIONS

Answer each question. These confirm the controls are valid for the actual site.
(Reference: SWMS_METHODOLOGY Step 2)

```
1. Access method confirmed (rope access, EWP, scaffold, ladder, ground only)?


2. Maximum working height and any overhead obstructions or balcony interfaces?


3. Ground conditions — firm hardstand, slopes, or soft ground?
   EWP: confirmed hardstand available?
   IRA: engineered anchors — design document available?


4. Public and traffic interface:
   Adjacent road or traffic corridor? Y / N
   Can exclusion zone be fully maintained within site boundary? Y / N
   Residents or occupants in building during works? Y / N


5. Environmental conditions:
   Wind limits applicable (IRA or spray)? Y / N — limit:
   Spray application? Y / N — overspray controls:
   Heat stress risk? Y / N


6. Any known hazardous materials on site?
   Asbestos: Confirmed absent / Confirmed present / Unknown (assume present)
   Lead paint: Confirmed absent / Confirmed present / Unknown (assume present if pre-2000)
   Other:
```

---

## SECTION G — REQUIREMENTS CONTENT

Fill in what applies to this specific job. Placeholder text will be replaced.

**PPE (list all required):**
```
Standard: Hard hat, hi-vis, safety boots, safety glasses
Additional for this job:
```

**Permits required:**
```
PC site induction — ALL workers (always)
SWMS sign-on — ALL workers (always)
Daily toolbox talk (always)
Additional for this job (hot works permit, EWP permit, confined space permit, etc.):
```

**Qualifications required:**
```
White Card — ALL workers (always)
First Aid HLTAID011 — minimum 1 per site (always)
Additional for this job:
```

**Plant and equipment:**
```
List all plant and equipment used on this job:
```

**Hazardous substances:**
```
List all chemicals and substances (confirm SDS on site before use):
```

**Legislation to append:**
```
Standard legislation is already in the template.
Any additional standards or codes of practice for this job:
```

---

## SECTION H — CCVS SELECTION

```
Which output(s) do you need?
[ ] Standard version only
[ ] CCVS version only
[ ] Both Standard and CCVS (recommended — always generate both)
```

---

## SECTION I — ADDITIONAL NOTES

Any other information the generator needs — unusual site conditions,
specific client requirements, scope limitations, interface with other trades:

```




```

---

## QUICK REFERENCE — SIX TRIGGER CHECK

Use this during Section D to confirm you have not missed any hazard category.
Run through all six for every major work activity on this job.

| Trigger | Ask yourself | Code |
|---|---|---|
| **Gravity / Height** | Is any work done above 2m? How? Who rescues if something goes wrong? | IRA / WAH / WFR / WFA |
| **Energy** | Electrical tools? Live circuits nearby? Hydraulic or pressurised plant? Stored energy? | ELE / ENE |
| **Materials / Substances** | Concrete or masonry cut or drilled? Chemicals, solvents, coatings? Lead or asbestos? | SIL / ENV / LED / ASB |
| **Structure** | Load-bearing elements disturbed? Temporary support? Crane lift? Tilt-up? | STR / MOB |
| **Interfaces** | Adjacent to road? Public or occupants nearby? Other trades overhead or below? | TRF |
| **Environment** | Wind or overspray risk? Noise? Vibration? Heat? Working in rain? | ENV / HOT |

---

## EXAMPLE — COMPLETED SECTION D FOR A TYPICAL JOB TYPE

**High-rise façade — rope access painting:**
IRA setup, IRA work, surface prep (SIL), sealant (ENV), paint spray (ENV),
concrete spalling (SIL), repointing (SIL), traffic adjacent (TRF), 240V tools (ELE)

**Balcony waterproofing — EWP access:**
EWP operation (WAH), surface prep (SIL), membrane application (ENV),
drainage penetrations (SIL), 240V tools (ELE), residents present (TRF)

**Retail fitout — ground level:**
Partition framing (STR), electrical first fix (ELE), plasterboard (SIL),
adhesives (ENV), forklift deliveries (MOB), public open hours (TRF)

**Civil drainage — excavation:**
Excavator (MOB), confined space inspection (CFS), powerlines nearby (ELE),
concrete cutting (SIL), traffic management (TRF), crane for precast (STR)

**Facilities maintenance — HVAC:**
Electrical isolation (ELE), hydraulic isolation (ENE), roof access restrained (WFR),
asbestos in roof void — assumed (ASB), hot works (HOT), 240V tools (ELE)

---

*End of USER_INPUT_REQUEST_GENERAL.md*
*Complete all sections. SYS and EMR are auto-injected — do not add them.*

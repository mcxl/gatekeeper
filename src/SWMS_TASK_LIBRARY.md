# SWMS TASK LIBRARY v16.0

**System:** Robertson's Remedial and Painting Pty Ltd
**Version:** v16.0
**Created:** February 2026
**Cross-reference:** SWMS_BASE_GENERAL.py | SWMS_GENERATOR_MASTER_v16.0.md | SWMS_METHODOLOGY.md

---

## How to Use This Library

Each section below corresponds to one code in the v16 system. Each entry is a
complete task dict ready to copy into SWMS_BASE_GENERAL.py Section 2.

**Selection process for any new job:**
1. Run the six-trigger check (METHODOLOGY Step 3) for each work activity
2. Identify which codes are activated
3. Select the most appropriate task entry from the relevant code section
4. Edit task name, hazard text, and controls to match actual site conditions
5. Assign the correct audit string (STD or CCVS, consequence, category)
6. Do NOT add SYS or EMR — the engine injects them automatically

**Audit string format:** `[STD|CCVS]-[pre]-[consequence]-[CODE]`
Examples: `STD-4-2-TRF`, `CCVS-6-3-WAH`, `STD-9-3-EMR`

**CCVS applies where:** pre ≥ 6 AND consequence = 3 AND code is in the
locked critical list: WFR WFA WAH IRA ELE SIL STR CFS ENE HOT MOB ASB LED

**Task numbering:** Do not number tasks in the library entries. The engine
numbers them after SYS is prepended as Task 1.

---

## CODE: WFR — Work at Heights, Fall Restraint

Fall restraint prevents the worker reaching the fall edge. The anchor and
restraint system are sized so the worker physically cannot reach the hazard.
No arrest force involved. Lower consequence than WFA — restraint failure
does not result in a fall.

---

### WFR-1 — Restraint System — General Roof or Edge Work

```python
{
    "task": (
        "Fall Restraint — Roof or Edge Work\n"
        "Install and use restraint system to prevent workers reaching unprotected edges."
    ),
    "hazard": (
        "Worker reaching unprotected edge — fall from height. "
        "Restraint anchor failure. "
        "Incorrect restraint length — worker reaches edge. "
        "Slips on roof surface."
    ),
    "pre": 6,
    "controls": (
        "WFR (High — C=3): Controls in place.\n"
        "Engineering: Restraint anchor rated and inspected — design load confirmed. "
        "Restraint lanyard length set so worker cannot reach edge — measured and confirmed.\n"
        "Admin: Competent person installs and checks system before use. "
        "All workers briefed on restraint limits — no overreach, no disconnection.\n"
        "PPE: Harness AS/NZS 1891.1, restraint lanyard, helmet.\n"
        "Remove from exposure and rectify if restraint system or anchor is in doubt."
    ),
    "post": 2,
    "resp": "Supervisor",
    "audit": "STD-6-3-WFR",
    "hazard_summary": "Worker reaching unprotected edge — restraint anchor failure or incorrect length.",
    "control_summary": "Anchor rated and inspected, lanyard length confirmed cannot reach edge, system checked before use.",
},
```

**CCVS variant** — change audit to `CCVS-6-3-WFR` and replace controls with:
```
"WFR (High — C=3) CCVS HOLD POINTS:\n"
"Work must not commence until:\n"
"(1) Restraint anchor design confirmed — load rating on file.\n"
"(2) Lanyard length measured — worker confirmed cannot reach edge.\n"
"(3) Harness inspected — AS/NZS 1891.1 compliant, no damage.\n"
"(4) All workers briefed on restraint limits — no disconnection permitted.\n"
"Confirmation retained in site diary or digital system.\n"
"Remove from exposure and rectify if anchor or restraint system in doubt."
```

---

### WFR-2 — Restraint — Plant or Equipment Maintenance at Height

```python
{
    "task": (
        "Fall Restraint — Plant or Equipment Maintenance\n"
        "Maintenance or inspection tasks at height where restraint prevents reaching fall edge."
    ),
    "hazard": (
        "Worker reaching fall edge during maintenance. "
        "Anchor attachment point integrity. "
        "Restraint length incorrect for task reach requirements."
    ),
    "pre": 6,
    "controls": (
        "WFR (High — C=3): Controls in place.\n"
        "Engineering: Anchor point on plant confirmed rated for restraint use. "
        "Restraint length sized for task — not longer than distance to nearest fall edge.\n"
        "Admin: Pre-start inspection of harness and lanyard. "
        "Task-specific briefing — confirm restraint limits before commencing. "
        "Isolate plant before maintenance commences.\n"
        "PPE: Harness AS/NZS 1891.1, restraint lanyard, helmet, non-slip footwear.\n"
        "Remove from exposure and rectify if anchor integrity uncertain."
    ),
    "post": 2,
    "resp": "Supervisor",
    "audit": "STD-6-3-WFR",
    "hazard_summary": "Worker reaching fall edge during maintenance — incorrect restraint length.",
    "control_summary": "Anchor rated for restraint, length sized to task, pre-start inspection, plant isolated.",
},
```

---

## CODE: WFA — Work at Heights, Fall Arrest

Fall arrest allows movement to the work area but arrests a fall before the
worker strikes a lower level. Clearance distance calculation is critical —
the system must be sized so the worker stops before hitting the ground or
lower structure.

---

### WFA-1 — Personal Fall Arrest — General Height Work

```python
{
    "task": (
        "Personal Fall Arrest System — Height Work\n"
        "Use of harness and lanyard for fall arrest at height where collective "
        "protection is not practicable."
    ),
    "hazard": (
        "Fall from height — arrest system failure. "
        "Insufficient clearance distance — worker strikes lower level before arrest. "
        "Swing fall — pendulum impact against structure. "
        "Suspension intolerance after arrest."
    ),
    "pre": 6,
    "controls": (
        "WFA (High — C=3): Controls in place.\n"
        "Engineering: Anchor rated minimum 15kN. "
        "Clearance distance calculated — confirms arrest before lower level. "
        "Energy-absorbing lanyard used where fall distance permits.\n"
        "Admin: Harness AS/NZS 1891.1 inspected pre-use. "
        "Rescue plan in place — suspended worker recovered promptly. "
        "Worker briefed on swing-fall risk — position to minimise pendulum arc.\n"
        "PPE: Full body harness, energy-absorbing lanyard, helmet.\n"
        "Remove from exposure and rectify if anchor, clearance, or rescue plan in doubt."
    ),
    "post": 2,
    "resp": "Supervisor",
    "audit": "STD-6-3-WFA",
    "hazard_summary": "Fall from height — arrest failure, insufficient clearance, swing fall, suspension intolerance.",
    "control_summary": "15kN anchor, clearance calculated, rescue plan briefed, energy-absorbing lanyard, harness inspected.",
},
```

**CCVS variant** — change audit to `CCVS-6-3-WFA` and replace controls with:
```
"WFA (High — C=3) CCVS HOLD POINTS:\n"
"Work must not commence until:\n"
"(1) Anchor load rating confirmed — minimum 15kN, on engineering record.\n"
"(2) Clearance distance calculated and confirmed — worker arrested before lower level.\n"
"(3) Harness inspected — AS/NZS 1891.1, no damage, correct fit.\n"
"(4) Rescue plan briefed to all workers — rescue equipment accessible.\n"
"(5) Swing-fall risk assessed — work positioning confirmed.\n"
"Confirmation retained in site diary or digital system.\n"
"Remove from exposure and rectify if anchor, clearance, or rescue plan in doubt."
```

---

## CODE: WAH — Work at Heights, Collective & Access

EWP, scaffold, elevated platforms, and ladders. Collective protection where
practicable. Ladder only where collective access is not reasonably practicable
with site-specific WaH RA completed.

---

### WAH-1 — EWP — Boom or Scissor Lift

```python
{
    "task": (
        "EWP Operation — Boom or Scissor Lift\n"
        "Use elevated work platform for height access."
    ),
    "hazard": (
        "Fall from basket (>2m). "
        "Tip-over or instability on uneven or soft ground. "
        "Entrapment or crush against overhead structure. "
        "Dropped objects. "
        "Collision with pedestrians or plant."
    ),
    "pre": 6,
    "controls": (
        "WAH (High — C=3): Controls in place.\n"
        "Engineering: Daily pre-start inspection completed and recorded. "
        "Ground firm and level — hardstand only. "
        "Outriggers and stabilisers deployed per manufacturer.\n"
        "Admin: Competent operator — WP licence sighted where required. "
        "Spotter mandatory near structures and when manoeuvring. "
        "Exclusion zone established around EWP. "
        "HOLD POINT: If set-up or exclusion cannot be contained within site — "
        "STOP and implement approved traffic or pedestrian controls.\n"
        "PPE: Harness clipped to manufacturer anchor, helmet, hi-vis vest or shirt, steel-capped footwear.\n"
        "Remove from exposure and rectify if ground unstable or fault detected."
    ),
    "post": 2,
    "resp": "Supervisor / Operator",
    "audit": "STD-6-3-WAH",
    "hazard_summary": "Fall from basket, tip-over, entrapment — EWP on uneven ground or near overhead structure.",
    "control_summary": "Pre-start check, firm ground, WP licence, spotter, harness clipped, exclusion zone confirmed.",
},
```

**CCVS variant** — change audit to `CCVS-6-3-WAH` and replace controls with:
```
"WAH (High — C=3) CCVS HOLD POINTS:\n"
"Work must not commence until:\n"
"(1) Daily pre-start inspection completed — defects nil — recorded.\n"
"(2) Ground confirmed firm and level on hardstand — outriggers fully deployed.\n"
"(3) Competent operator — WP licence sighted and confirmed.\n"
"(4) Overhead clearances measured and confirmed safe.\n"
"(5) Harness inspected — lanyard clipped to manufacturer anchor point.\n"
"(6) Exclusion zone established — spotter confirmed on station.\n"
"Confirmation retained in site diary or digital system.\n"
"Remove from exposure and rectify if ground unstable or fault detected."
```

---

### WAH-2 — Scaffold — Erected and Used

```python
{
    "task": (
        "Scaffold — Erection, Use, and Dismantling\n"
        "Erect, use, modify, or dismantle scaffold for height access."
    ),
    "hazard": (
        "Fall from scaffold platform or through gaps. "
        "Scaffold collapse — overload or base failure. "
        "Falls during erection and dismantling. "
        "Dropped objects — tools and materials from platform. "
        "Contact with overhead powerlines."
    ),
    "pre": 6,
    "controls": (
        "WAH (High — C=3): Controls in place.\n"
        "Engineering: Scaffold designed, erected, and inspected by licensed scaffolder. "
        "Handover certificate issued before use. "
        "Platform fully planked — gaps ≤25mm. "
        "Guardrails top and mid-rail plus kickboard on all open sides.\n"
        "Admin: Do not modify scaffold without licensed scaffolder. "
        "Load limits posted and observed. "
        "Inspect scaffold before each shift. "
        "Exclusion zone below during erection and dismantling.\n"
        "PPE: Helmet, steel-capped footwear, harness during erection/dismantling.\n"
        "Remove from exposure and tag-out scaffold if defects found."
    ),
    "post": 2,
    "resp": "Supervisor / Licensed Scaffolder",
    "audit": "STD-6-3-WAH",
    "hazard_summary": "Fall from platform, scaffold collapse, dropped objects — erection, use, and dismantling.",
    "control_summary": "Licensed scaffolder, handover cert before use, fully planked, guardrails, no unauthorised modifications.",
},
```

---

### WAH-3 — Ladder Use — Short Duration

```python
{
    "task": (
        "Ladder Use — Short Duration Only\n"
        "A-frame or extension ladder where EWP or scaffold is not reasonably practicable."
    ),
    "hazard": (
        "Fall from height. "
        "Kick-out or instability. "
        "Overreaching. "
        "Dropped tools striking persons below."
    ),
    "pre": 6,
    "controls": (
        "WAH (High — C=3): Controls in place.\n"
        "Eliminate: Use EWP or scaffold first — ladder only where not practicable.\n"
        "Engineering: Industrial-rated ladder, correct angle (4:1 extension), "
        "non-slip feet, secured where possible.\n"
        "Admin: Site-specific WaH RA completed before use — confirms ladder is "
        "only practicable method. Three points of contact at all times. "
        "No top two rungs. No overreaching. Barricade area below.\n"
        "PPE: Non-slip footwear, helmet, tool lanyards.\n"
        "Remove from exposure and rectify if ladder is damaged or conditions unsafe."
    ),
    "post": 2,
    "resp": "Supervisor",
    "audit": "STD-6-3-WAH",
    "hazard_summary": "Fall from ladder — kick-out, overreaching, dropped tools onto persons below.",
    "control_summary": "EWP or scaffold first, WaH RA required, 4:1 angle, three points contact, barricade below.",
},
```

---

### WAH-4 — Roof Work — Fragile or Unprotected

```python
{
    "task": (
        "Roof Work — Fragile or Unprotected Roof\n"
        "Access, inspection, repair, or installation on roof with unprotected edges "
        "or fragile surfaces."
    ),
    "hazard": (
        "Fall through fragile roof material. "
        "Fall from unprotected edge. "
        "Slip on roof surface — pitch, moisture, debris. "
        "Dropped objects below."
    ),
    "pre": 6,
    "controls": (
        "WAH (High — C=3): Controls in place.\n"
        "Engineering: Install edge protection (guardrail system) before work. "
        "Use roof walkboards over fragile surfaces — do not step directly. "
        "Cover and mark fragile areas.\n"
        "Admin: Limit number of workers on roof to minimum required. "
        "Exclusion zone below for full potential fall area. "
        "Weather assessment — no work on wet or windy roof.\n"
        "PPE: Harness and lanyard, non-slip footwear, helmet.\n"
        "Remove from exposure and rectify if edge protection incomplete."
    ),
    "post": 2,
    "resp": "Supervisor",
    "audit": "STD-6-3-WAH",
    "hazard_summary": "Fall through fragile surface or from unprotected edge — slip on roof pitch.",
    "control_summary": "Edge protection before work, walkboards over fragile areas, exclusion zone below, no work in wet or wind.",
},
```

---

### WAH-5 — Working Over or Near Water

```python
{
    "task": (
        "Working Over or Near Water\n"
        "Height work above or adjacent to water — bridge, jetty, marine, or drainage."
    ),
    "hazard": (
        "Fall into water — drowning. "
        "Cold water shock. "
        "Strong current or tidal movement. "
        "Fall from height before entering water."
    ),
    "pre": 9,
    "controls": (
        "WAH (High — C=3): Controls in place.\n"
        "Engineering: Guardrails or edge protection on all working platforms. "
        "Safety net or catching platform where practicable.\n"
        "Admin: Life rings and throw lines deployed at water level. "
        "Rescue boat or water rescue plan confirmed before work starts. "
        "Workers in water must wear PFD — Type 1 or 2. "
        "No lone working over water.\n"
        "PPE: PFD (Type 1 or 2 as assessed), harness and lanyard, helmet.\n"
        "Remove from exposure and rectify if rescue plan or equipment is absent."
    ),
    "post": 2,
    "resp": "Supervisor",
    "audit": "STD-9-3-WAH",
    "hazard_summary": "Fall into water — drowning, cold water shock, current — over bridge, jetty, or marine structure.",
    "control_summary": "Edge protection, life rings deployed, rescue plan confirmed, PFD mandatory, no lone working.",
},
```

---

## CODE: IRA — Industrial Rope Access

Two-rope systems only. IRATA or ARAA certified crew. Team of minimum 3.
Rescue kit on site and rescue plan briefed before work starts.
IRA is not WAH — do not use WAH for rope access tasks.

---

### IRA-1 — Rope Access Setup and Anchors

```python
{
    "task": (
        "Industrial Rope Access — Setup and Anchors\n"
        "Install rope systems on engineered anchors, protect edges, establish drop zones."
    ),
    "hazard": (
        "Fall from height during rigging. "
        "Anchor failure or incorrect rigging. "
        "Rope damage over sharp edges. "
        "Dropped objects during setup."
    ),
    "pre": 6,
    "controls": (
        "IRA (High — C=3): Controls in place.\n"
        "Engineering: Engineered anchors only — design document on site. "
        "Two-rope system — working line and safety line on independent anchors. "
        "Edge and rope protection at all contact points.\n"
        "Admin: Team of minimum 3 including Lead Tech. "
        "Pre-start rigging checklist and buddy check completed and recorded. "
        "Drop zone fully barricaded before rigging. Tool lanyards on all hardware.\n"
        "PPE: Rope access harness, helmet with chin strap, cut-resistant gloves, eye protection.\n"
        "Remove from exposure and rectify if anchor integrity is in doubt."
    ),
    "post": 2,
    "resp": "Lead Tech",
    "audit": "STD-6-3-IRA",
    "hazard_summary": "Fall during rigging — anchor failure, rope over sharp edges, dropped objects.",
    "control_summary": "Engineered anchors, buddy check, two-rope on independent anchors, drop zone barricaded before rigging.",
},
```

---

### IRA-2 — Rope Access Work at Height

```python
{
    "task": (
        "Industrial Rope Access — Work at Height\n"
        "Rope access positioning for façade, structure, or infrastructure works."
    ),
    "hazard": (
        "Worker fall or suspension intolerance. "
        "Pendulum or swing impact against structure. "
        "Entrapment or crush. "
        "Dropped objects impacting persons below."
    ),
    "pre": 6,
    "controls": (
        "IRA (High — C=3): Controls in place.\n"
        "Engineering: Two-rope system maintained at all times — backup device on safety line. "
        "Work positioning to prevent uncontrolled swing.\n"
        "Admin: Drop zone covers full potential fall line. "
        "Ground spotter monitors barricades and public interface. "
        "Rescue kit on site — team of 3 enables assisted rescue. "
        "Rescue plan briefed before work starts each day. "
        "Suspended worker recovered within 10 minutes — call 000.\n"
        "PPE: Rope access harness, helmet, cut-resistant gloves, task-specific PPE.\n"
        "Remove from exposure and rectify if two-rope system is compromised."
    ),
    "post": 2,
    "resp": "Lead Tech",
    "audit": "STD-6-3-IRA",
    "hazard_summary": "Fall, suspension intolerance, swing impact, dropped objects onto persons below.",
    "control_summary": "Two-rope at all times, spotter on ground, rescue kit on site, recover within 10 min, drop zone full fall line.",
},
```

---

## CODE: ELE — Electrical

Isolation and lock-out/tag-out (LOTO) before any electrical work. Test-for-dead
before touching. No live work unless explicitly authorised and using licensed
electrician with appropriate controls.

---

### ELE-1 — Electrical Isolation — Maintenance or Construction

```python
{
    "task": (
        "Electrical Isolation — Maintenance or Construction\n"
        "Isolate electrical supply before commencing work on or near electrical equipment."
    ),
    "hazard": (
        "Electrocution or electric shock — contact with live conductors. "
        "Arc flash injury. "
        "Unintentional re-energisation during work."
    ),
    "pre": 6,
    "controls": (
        "ELE (High — C=3): Controls in place.\n"
        "Engineering: Isolate at switchboard — lock-out and tag-out (LOTO) applied. "
        "Test-for-dead using calibrated tester before touching any conductor.\n"
        "Admin: Only licensed electrician to perform electrical work. "
        "Permit to work issued where required. "
        "All workers in area briefed on isolation and LOTO status.\n"
        "STOP WORK: If isolation cannot be confirmed or LOTO is removed without "
        "authorisation — stop immediately and do not re-energise without full process.\n"
        "PPE: Insulated cut-resistant gloves, safety glasses, ELE-rated footwear."
    ),
    "post": 1,
    "resp": "Licensed Electrician / Supervisor",
    "audit": "STD-6-3-ELE",
    "hazard_summary": "Electrocution from live conductors — arc flash — unintentional re-energisation.",
    "control_summary": "LOTO at switchboard, test-for-dead before touching, licensed electrician only, permit where required.",
},
```

---

### ELE-2 — Portable Electrical Tools and Leads

```python
{
    "task": (
        "Portable Electrical Tools and Extension Leads\n"
        "Use of 240V portable tools, extension leads, and RCD protection on site."
    ),
    "hazard": (
        "Electric shock from damaged tools or leads. "
        "RCD failure — unprotected circuit. "
        "Leads in wet conditions or near water. "
        "Overloaded circuits — fire risk."
    ),
    "pre": 4,
    "controls": (
        "ELE (Medium — C=2): Controls in place.\n"
        "Engineering: All 240V tools and leads protected by RCD — tested before use. "
        "Use battery tools where practicable.\n"
        "Admin: All tools and leads tested and tagged AS/NZS 3760 — "
        "construction/hostile environment minimum 3-monthly. "
        "Visual inspection pre-use — no damaged plugs, cords, or housings. "
        "No daisy-chaining. Keep leads off ground. "
        "Isolate before clearing jams or changing attachments. "
        "Keep electrical equipment away from water — IP-rated where wet.\n"
        "PPE: Safety footwear, insulated gloves not normally required — "
        "control by isolation and inspection, not PPE."
    ),
    "post": 1,
    "resp": "Supervisor",
    "audit": "STD-4-2-ELE",
    "hazard_summary": "Electric shock from damaged tools or leads — RCD failure — leads in wet conditions.",
    "control_summary": "RCD on all 240V, tested and tagged AS/NZS 3760, battery tools where practicable, no damaged cords.",
},
```

---

### ELE-3 — Work Near Overhead Powerlines

```python
{
    "task": (
        "Work Near Overhead Powerlines\n"
        "Plant, equipment, or personnel working in proximity to overhead powerlines."
    ),
    "hazard": (
        "Electrocution — contact with powerline by plant or person. "
        "Electrical arcing — flashover without contact. "
        "Line brought down — secondary contact risk."
    ),
    "pre": 9,
    "controls": (
        "ELE (High — C=3): Controls in place.\n"
        "Engineering: Exclusion zone established per AS/NZS 4836 — "
        "minimum 3m for <66kV, greater for higher voltage. "
        "Physical barriers (goal posts) erected where plant must pass near lines.\n"
        "Admin: Contact network operator before commencing — confirm voltage, "
        "request de-energisation or cover where practicable. "
        "Spotter assigned to monitor clearance when plant operating near lines. "
        "All workers briefed on exclusion zone — no exceptions.\n"
        "STOP WORK: If plant or person contacts or comes within exclusion zone "
        "of powerline — stop all work, do not touch plant, call 000 and network operator.\n"
        "PPE: hi-vis vest or shirt, helmet, steel-capped footwear."
    ),
    "post": 2,
    "resp": "Supervisor",
    "audit": "STD-9-3-ELE",
    "hazard_summary": "Electrocution or flashover — plant or person contacting overhead powerlines.",
    "control_summary": "Contact network operator, exclusion zone per AS/NZS 4836, goal posts, spotter assigned.",
},
```

---

## CODE: SIL — Silica and Dust

Silica is a Class 1 carcinogen. No dry cutting, grinding, or drilling of
silica-containing materials. Wet methods or on-tool extraction mandatory.
P2 minimum — P3 where high exposure or extended duration.

---

### SIL-1 — Grinding or Cutting Concrete, Masonry, Stone

```python
{
    "task": (
        "Grinding or Cutting — Concrete, Masonry, or Stone\n"
        "Angle grinding, cutting, or abrading silica-containing materials."
    ),
    "hazard": (
        "Silica dust inhalation — silicosis, lung cancer. "
        "Flying debris and sparks. "
        "Noise and vibration. "
        "Wheel failure — projectile."
    ),
    "pre": 6,
    "controls": (
        "SIL (High — C=3): Controls in place.\n"
        "Eliminate: Avoid or minimise grinding — use alternative method where practicable.\n"
        "Engineering: On-tool extraction (HEPA vacuum) or wet suppression on grinder. "
        "Blade guard fitted and intact.\n"
        "Admin: P2 or P3 respirator — fit-tested where required. "
        "Eye and face protection. Hearing protection. "
        "Exclusion zone around grinder for debris. "
        "Inspect wheel before fitting — no cracks or damage.\n"
        "PPE: P2/P3 respirator, face shield, hearing protection, cut-resistant gloves.\n"
        "Remove from exposure and rectify if dust controls fail."
    ),
    "post": 2,
    "resp": "Supervisor",
    "audit": "STD-6-3-SIL",
    "hazard_summary": "Silica dust inhalation from grinding concrete or masonry — silicosis risk.",
    "control_summary": "On-tool extraction or wet suppression, P2/P3 respirator, face shield, exclusion zone.",
},
```

---

### SIL-2 — Drilling into Concrete or Masonry

```python
{
    "task": (
        "Drilling — Concrete or Masonry\n"
        "Core drilling, hammer drilling, or SDS drilling into concrete, brick, or stone."
    ),
    "hazard": (
        "Silica dust inhalation. "
        "Striking concealed services — electrical, hydraulic, gas. "
        "Hand-arm vibration. "
        "Dropped debris below (at height)."
    ),
    "pre": 6,
    "controls": (
        "SIL (High — C=3): Controls in place.\n"
        "Engineering: Wet drilling or HEPA vacuum shroud on drill. "
        "P2 or P3 RPE.\n"
        "Admin: Services scan before drilling — confirm no services in drill path. "
        "Depth stop set to prevent over-penetration. "
        "Vibration exposure managed — rotate tasks, maintain tooling.\n"
        "PPE: P2/P3 respirator, safety glasses, hearing protection, cut-resistant gloves.\n"
        "Remove from exposure and rectify if dust controls fail."
    ),
    "post": 2,
    "resp": "Supervisor",
    "audit": "STD-6-3-SIL",
    "hazard_summary": "Silica dust from drilling concrete — striking concealed services, hand-arm vibration.",
    "control_summary": "Wet drilling or HEPA shroud, services scan before drilling, P2/P3 RPE, vibration rotation.",
},
```

---

### SIL-3 — Surface Preparation — Sanding, Scraping, Pressure Washing

```python
{
    "task": (
        "Surface Preparation — Sanding, Scraping, or Pressure Washing\n"
        "Prepare substrate prior to coating, waterproofing, or repair."
    ),
    "hazard": (
        "Silica or lead dust inhalation from sanding or scraping. "
        "Flying debris. "
        "Chemical exposure from cleaners. "
        "High-pressure injection injury (pressure washer)."
    ),
    "pre": 6,
    "controls": (
        "SIL (High — C=3): Controls in place.\n"
        "Eliminate: Wet sanding where practicable — no dry grinding.\n"
        "Engineering: HEPA vacuum on sander. Dust extraction. "
        "Wet methods for washing. Pressure washer — rated tip, never point at person.\n"
        "Admin: Test for lead or assume present — lead-safe procedures apply. "
        "P2 or P3 RPE for sanding or scraping. "
        "Exclusion zone for debris. Review SDS for all cleaning products.\n"
        "PPE: P2/P3 respirator, eye protection, cut-resistant gloves, hearing protection.\n"
        "Remove from exposure and rectify if dust controls fail."
    ),
    "post": 2,
    "resp": "Supervisor",
    "audit": "STD-6-3-SIL",
    "hazard_summary": "Silica and lead dust from sanding — chemical exposure, pressure washer injection injury.",
    "control_summary": "Wet methods only, HEPA vac, assume lead present, P2/P3 RPE, never point pressure washer at person.",
},
```

---

### SIL-4 — Jackhammering or Demolition Breakout

```python
{
    "task": (
        "Jackhammering or Demolition Breakout\n"
        "Break out concrete, masonry, or render using mechanical means."
    ),
    "hazard": (
        "Silica dust from breakout. "
        "Flying debris. "
        "Noise and severe vibration — HAVS. "
        "Structural instability during breakout. "
        "Striking concealed services."
    ),
    "pre": 6,
    "controls": (
        "SIL (High — C=3): Controls in place.\n"
        "Engineering: Wet suppression or on-tool extraction. "
        "Hammer guards fitted. Debris containment and catch.\n"
        "Admin: P2 or P3 RPE. Eye and face protection. Hearing protection. "
        "Services scan and isolation before commencing. "
        "Structural assessment — confirm breakout extent with engineer or PC. "
        "Vibration rotation — limit individual exposure, maintain tooling.\n"
        "PPE: P2/P3 respirator, face shield, hearing protection, cut-resistant gloves, steel-capped footwear.\n"
        "Remove from exposure and rectify if dust or structural controls fail."
    ),
    "post": 2,
    "resp": "Supervisor",
    "audit": "STD-6-3-SIL",
    "hazard_summary": "Silica dust from breakout, flying debris, severe vibration — structural instability.",
    "control_summary": "Wet suppression or extraction, services scan, structural confirmed, P2/P3 RPE, vibration rotation.",
},
```

---

## CODE: STR — Structural

Involves load-bearing elements, temporary works, structural stability, or
elements whose failure would cause collapse. Engineer or PC approval required
before disturbing any load-bearing element.

---

### STR-1 — Structural Demolition or Removal

```python
{
    "task": (
        "Structural Demolition or Removal\n"
        "Remove or alter load-bearing or structural elements."
    ),
    "hazard": (
        "Structural collapse — premature failure of element. "
        "Falling materials. "
        "Adjacent structure destabilised. "
        "Silica dust from cutting or breaking."
    ),
    "pre": 6,
    "controls": (
        "STR (High — C=3): Controls in place.\n"
        "Engineering: Structural engineer or PC approval before commencing — "
        "written confirmation on file. "
        "Temporary propping or support confirmed in place before element removed. "
        "Demolition sequence confirmed.\n"
        "Admin: Exclusion zone below and around work area. "
        "Only nominated workers in structural zone. "
        "Debris removed progressively — do not overload floors or platforms.\n"
        "SIL: Wet cutting or on-tool extraction — P2/P3 RPE for all cutting.\n"
        "STOP WORK: Any unplanned cracking, movement, or noise from structure — "
        "evacuate immediately, do not re-enter without engineer assessment.\n"
        "PPE: Helmet, steel-capped footwear, P2/P3 RPE, eye and face protection."
    ),
    "post": 2,
    "resp": "Supervisor",
    "audit": "STD-6-3-STR",
    "hazard_summary": "Structural collapse — premature failure, falling materials, adjacent structure destabilised.",
    "control_summary": "Engineer approval and written confirmation, temporary support in place, exclusion zone, progressive removal.",
},
```

---

### STR-2 — Temporary Works — Propping, Shoring, Formwork

```python
{
    "task": (
        "Temporary Works — Propping, Shoring, or Formwork\n"
        "Install, use, modify, or remove temporary structural support systems."
    ),
    "hazard": (
        "Collapse of temporary works — failure of props, shores, or formwork. "
        "Premature removal of support. "
        "Overloading temporary structure. "
        "Struck by collapsing formwork or material."
    ),
    "pre": 6,
    "controls": (
        "STR (High — C=3): Controls in place.\n"
        "Engineering: Temporary works designed by engineer — drawings on site. "
        "Installation supervised by competent person per design. "
        "Formwork inspected before concrete pour.\n"
        "Admin: No modifications to temporary works without engineer approval. "
        "Do not remove props or shores until engineer confirmation. "
        "Load limits observed — no material stockpiling on temporary structures. "
        "Exclusion zone during high-risk operations.\n"
        "STOP WORK: Any sign of distress, deflection, or movement — evacuate and "
        "do not re-enter without engineer assessment.\n"
        "PPE: Helmet, steel-capped footwear, cut-resistant gloves."
    ),
    "post": 2,
    "resp": "Supervisor / Engineer",
    "audit": "STD-6-3-STR",
    "hazard_summary": "Collapse of temporary works — failure of props, formwork, or shores.",
    "control_summary": "Engineer design on site, installed per drawings, no modifications without approval, load limits observed.",
},
```

---

### STR-3 — Tilt-Up Panel Erection

```python
{
    "task": (
        "Tilt-Up Panel Erection\n"
        "Lift, position, and brace precast tilt-up concrete panels."
    ),
    "hazard": (
        "Panel collapse during lift or before permanent bracing secured. "
        "Panel swing — struck by moving panel. "
        "Crane failure or rigging failure. "
        "Brace anchor failure — panel falls."
    ),
    "pre": 9,
    "controls": (
        "STR (High — C=3): Controls in place.\n"
        "Engineering: Lift design by engineer — rigging, brace design, anchor layout. "
        "Brace anchors cast to design and tested before lift. "
        "Temporary bracing installed immediately on landing — before crane releases.\n"
        "Admin: Crane pre-start inspection. Rigger and dogman licensed. "
        "Exclusion zone = 1.5× panel height. "
        "No persons under suspended load at any time. "
        "Wind limit observed — lift only within engineered wind speed parameters.\n"
        "STOP WORK: Any brace failure, anchor movement, or crane fault — "
        "stop immediately, do not approach, call engineer.\n"
        "PPE: Helmet, hi-vis vest or shirt, steel-capped footwear, cut-resistant gloves."
    ),
    "post": 2,
    "resp": "Supervisor / Licensed Rigger",
    "audit": "STD-9-3-STR",
    "hazard_summary": "Panel collapse before bracing — rigging failure, brace anchor failure, panel swing.",
    "control_summary": "Engineer lift design, brace anchors tested, bracing before crane releases, exclusion zone 1.5× panel height.",
},
```

---

## CODE: CFS — Confined Space

No entry without a permit. Atmospheric testing before and during entry.
Standby person outside at all times. Emergency rescue plan and equipment
confirmed before any entry. If atmosphere fails — evacuate immediately.

---

### CFS-1 — Confined Space Entry — General

```python
{
    "task": (
        "Confined Space Entry\n"
        "Entry into a confined space for inspection, maintenance, or installation."
    ),
    "hazard": (
        "Oxygen deficiency or toxic atmosphere — asphyxiation. "
        "Flammable atmosphere — explosion or fire. "
        "Engulfment — loose material inflow. "
        "Entrapment — worker cannot self-rescue."
    ),
    "pre": 9,
    "controls": (
        "CFS (High — C=3): Controls in place.\n"
        "Engineering: Forced ventilation before and during entry. "
        "Atmospheric testing — O2, CO, H2S, LEL — immediately before entry and continuous.\n"
        "Admin: Confined space entry permit signed and in force. "
        "Standby person outside at all times — never leaves until entrant out. "
        "Emergency rescue plan and equipment confirmed before entry. "
        "Entry log maintained.\n"
        "STOP WORK: Atmospheric alarm — evacuate immediately. "
        "Do not re-enter until atmosphere re-tested and safe.\n"
        "PPE: Supplied-air or SCBA if atmosphere uncertain, harness with retrieval line, "
        "helmet, chemical-resistant clothing as required."
    ),
    "post": 1,
    "resp": "Confined Space Supervisor",
    "audit": "STD-9-3-CFS",
    "hazard_summary": "Oxygen deficiency or toxic atmosphere — asphyxiation, flammable gas, entrapment.",
    "control_summary": "Entry permit signed, atmospheric test before and continuous, standby person outside, rescue plan confirmed.",
},
```

---

## CODE: ENE — Energised Equipment and Stored Energy

Hydraulic, pneumatic, spring, gravity, and electrical stored energy all require
isolation and energy dissipation before work. LOTO must cover all energy forms —
not just electrical.

---

### ENE-1 — Hydraulic or Pneumatic System Isolation

```python
{
    "task": (
        "Hydraulic or Pneumatic System Isolation\n"
        "Isolate and de-energise hydraulic or pneumatic systems before maintenance."
    ),
    "hazard": (
        "High-pressure fluid injection injury. "
        "Uncontrolled movement of hydraulic components. "
        "Residual pressure after isolation — stored energy release."
    ),
    "pre": 6,
    "controls": (
        "ENE (High — C=3): Controls in place.\n"
        "Engineering: Isolate all energy sources — LOTO applied. "
        "Bleed pressure to zero — confirm on gauge before work. "
        "Block or pin components that could move under gravity.\n"
        "Admin: Only trained personnel perform isolation. "
        "Never disconnect hydraulic fitting under pressure — pressure confirmed zero. "
        "Keep face and body clear when bleeding pressure.\n"
        "STOP WORK: If pressure cannot be confirmed zero or LOTO is compromised — "
        "stop and do not re-energise without full process.\n"
        "PPE: Safety glasses, face shield, chemical-resistant gloves."
    ),
    "post": 1,
    "resp": "Supervisor / Technician",
    "audit": "STD-6-3-ENE",
    "hazard_summary": "High-pressure injection injury — uncontrolled movement — residual stored energy after isolation.",
    "control_summary": "LOTO applied, bleed to zero confirmed on gauge, gravity components blocked, trained personnel only.",
},
```

---

### ENE-2 — Gravity Stored Energy — Suspended Loads or Counterweights

```python
{
    "task": (
        "Gravity Stored Energy — Suspended Loads or Counterweights\n"
        "Work on or near suspended loads, elevated components, or counterweight systems."
    ),
    "hazard": (
        "Uncontrolled descent — crushing injury or fatality. "
        "Component drop — struck by falling load. "
        "Counterweight movement — unintended operation."
    ),
    "pre": 6,
    "controls": (
        "ENE (High — C=3): Controls in place.\n"
        "Engineering: Block, pin, or mechanically restrain elevated components "
        "before working below. Never rely on hydraulic or pneumatic support alone.\n"
        "Admin: Exclusion zone below suspended loads. "
        "No persons beneath elevated components during work. "
        "Isolate and LOTO control systems before commencing.\n"
        "STOP WORK: Any unintended movement of suspended component — evacuate area.\n"
        "PPE: Helmet, steel-capped footwear, cut-resistant gloves."
    ),
    "post": 1,
    "resp": "Supervisor / Technician",
    "audit": "STD-6-3-ENE",
    "hazard_summary": "Uncontrolled descent or component drop — crushing — counterweight movement.",
    "control_summary": "Mechanically block or pin before working below, exclusion zone, LOTO control systems, no persons beneath.",
},
```

---

## CODE: HOT — Hot Works

Fire watch during and 60 minutes after all hot works. Remove or wet
combustibles within 5m radius. Permit required. Extinguisher at hand.

---

### HOT-1 — Welding or Grinding — Fire Risk

```python
{
    "task": (
        "Hot Works — Welding, Cutting, or Grinding\n"
        "Any process producing heat, sparks, or open flame."
    ),
    "hazard": (
        "Fire from sparks landing on combustibles. "
        "Burns to operator — radiant heat, spatter. "
        "Fume inhalation — welding fume, coated metal fume. "
        "UV radiation — arc eye."
    ),
    "pre": 6,
    "controls": (
        "HOT (High — C=3): Controls in place.\n"
        "Engineering: Remove combustibles within 5m radius or wet and cover. "
        "Fire blanket to protect non-removable combustibles. "
        "Extinguisher at hot works location — confirmed serviceable.\n"
        "Admin: Hot works permit signed and in force. "
        "Fire watch during works and 60 minutes after completion. "
        "Welding fume extraction or P3 FFP3 respirator — no galvanised metal without "
        "specific fume controls.\n"
        "PPE: Welding helmet or face shield, leather gloves, leather apron, "
        "fire-resistant clothing, steel-capped footwear."
    ),
    "post": 2,
    "resp": "Supervisor",
    "audit": "STD-6-3-HOT",
    "hazard_summary": "Fire from sparks on combustibles — burns, welding fume, UV radiation from arc.",
    "control_summary": "Remove combustibles 5m, extinguisher at hand, permit signed, 60-min fire watch after completion.",
},
```

---

## CODE: MOB — Mobile Plant

Exclusion zones around all operating plant. Spotter when plant reversing or
operating near workers. No persons in the swing or travel path.

---

### MOB-1 — Excavator or Loader — Earthworks or Materials Handling

```python
{
    "task": (
        "Excavator or Loader — Earthworks or Materials Handling\n"
        "Operate excavator or loader for earthworks, demolition, or materials handling."
    ),
    "hazard": (
        "Struck by swinging bucket or counterweight. "
        "Rollover on unstable or sloping ground. "
        "Striking buried services. "
        "Pedestrian or worker in swing or travel path."
    ),
    "pre": 6,
    "controls": (
        "MOB (High — C=3): Controls in place.\n"
        "Engineering: Exclusion zone = full swing radius + 1m — barricaded. "
        "No persons inside exclusion zone while plant operating.\n"
        "Admin: Plant pre-start inspection completed and recorded. "
        "Services scan and dial-before-you-dig completed — services located. "
        "Spotter mandatory when reversing or near workers. "
        "Ground bearing capacity confirmed before positioning.\n"
        "PPE: Helmet, hi-vis vest or shirt, steel-capped footwear — all persons on site."
    ),
    "post": 2,
    "resp": "Supervisor / Operator",
    "audit": "STD-6-3-MOB",
    "hazard_summary": "Struck by swing or travel — rollover — striking buried services.",
    "control_summary": "Exclusion zone full swing radius, no persons inside, services located, spotter when reversing.",
},
```

---

### MOB-2 — Crane — Lift Operations

```python
{
    "task": (
        "Crane — Lift Operations\n"
        "Crane lifts for materials, plant, structural elements, or equipment."
    ),
    "hazard": (
        "Suspended load failure — rigging, hook, or sling failure. "
        "Load swing — struck by moving load. "
        "Crane overload — tip-over or structural failure. "
        "Persons under suspended load."
    ),
    "pre": 9,
    "controls": (
        "MOB (High — C=3): Controls in place.\n"
        "Engineering: Lift plan prepared for all critical or complex lifts. "
        "Crane pre-start inspection and logbook current. "
        "Rigging inspected — slings, shackles, hooks rated for load.\n"
        "Admin: Licensed rigger and dogman. "
        "Exclusion zone = lift radius plus buffer. "
        "No persons under suspended load at any time. "
        "Wind limit observed. "
        "Lift plan briefed to all persons involved before lift.\n"
        "PPE: Helmet, hi-vis vest or shirt, steel-capped footwear, cut-resistant gloves."
    ),
    "post": 2,
    "resp": "Supervisor / Licensed Rigger",
    "audit": "STD-9-3-MOB",
    "hazard_summary": "Suspended load failure — load swing — crane overload — persons under load.",
    "control_summary": "Lift plan, licensed rigger, rated rigging inspected, no persons under load, wind limit observed.",
},
```

---

### MOB-3 — Forklift or Telehandler

```python
{
    "task": (
        "Forklift or Telehandler — Materials Handling\n"
        "Fork lift or telehandler for loading, unloading, or materials placement."
    ),
    "hazard": (
        "Pedestrian struck by forklift. "
        "Load falling from forks. "
        "Tip-over — unstable or uneven ground. "
        "Overhead obstruction — load or mast contact."
    ),
    "pre": 6,
    "controls": (
        "MOB (High — C=3): Controls in place.\n"
        "Engineering: Segregate pedestrian and forklift travel paths — physical barrier. "
        "Load secured and stable before travel.\n"
        "Admin: Licensed operator. Pre-start inspection completed. "
        "Spotter mandatory near pedestrians or in congested areas. "
        "Speed limit enforced. Horn used at intersections. "
        "Load within rated capacity — load chart checked.\n"
        "PPE: Helmet, hi-vis vest or shirt, steel-capped footwear — all persons in forklift operating area."
    ),
    "post": 2,
    "resp": "Supervisor / Licensed Operator",
    "audit": "STD-6-3-MOB",
    "hazard_summary": "Pedestrian struck — load falling — tip-over on uneven ground.",
    "control_summary": "Segregated travel paths, licensed operator, spotter near pedestrians, load within rated capacity.",
},
```

---

## CODE: ASB — Asbestos

Assume present in any pre-2003 building unless proven absent by licensed
assessor. No disturbance without confirmation of status. Friable asbestos
requires licensed removalist — no exceptions.

---

### ASB-1 — Pre-Work Asbestos Assessment

```python
{
    "task": (
        "Pre-Work Asbestos Assessment\n"
        "Confirm asbestos status before any work that may disturb materials "
        "in pre-2003 construction."
    ),
    "hazard": (
        "Asbestos fibre inhalation — mesothelioma, lung cancer. "
        "Unintentional disturbance during other work activities. "
        "Friable asbestos — higher release potential."
    ),
    "pre": 9,
    "controls": (
        "ASB (High — C=3): Controls in place.\n"
        "Engineering: Do not disturb any suspect material until status confirmed.\n"
        "Admin: Asbestos register sighted — confirm location, type, condition. "
        "If register absent or material unlisted — assume present, treat as ACM. "
        "Licensed assessor to inspect and sample before work. "
        "Non-friable: licensed removalist if >10m². "
        "Friable: licensed Class A removalist — no exceptions.\n"
        "STOP WORK: Any unexpected fibrous material encountered — stop, isolate area, "
        "do not re-enter without licensed assessment.\n"
        "PPE: P2 minimum until status confirmed. P3 half-face or full-face where risk confirmed."
    ),
    "post": 1,
    "resp": "Supervisor / Licensed Assessor",
    "audit": "STD-9-3-ASB",
    "hazard_summary": "Asbestos fibre inhalation — unintentional disturbance in pre-2003 construction.",
    "control_summary": "Register sighted, assume present if unknown, licensed assessor before work, licensed removalist if confirmed.",
},
```

---

## CODE: LED — Lead

Lead paint assumed present in any pre-1970 building and possible in
pre-2000. Wet methods only. No dry sanding or scraping without confirmation
of absence. Biological monitoring for extended exposure.

---

### LED-1 — Lead Paint — Surface Preparation or Removal

```python
{
    "task": (
        "Lead Paint — Surface Preparation or Removal\n"
        "Sanding, scraping, or removing paint from surfaces where lead is present or assumed."
    ),
    "hazard": (
        "Lead dust inhalation — lead poisoning, neurological damage. "
        "Lead ingestion — hand-to-mouth contamination. "
        "Lead contamination of work area and workers' clothing."
    ),
    "pre": 6,
    "controls": (
        "LED (High — C=3): Controls in place.\n"
        "Engineering: Wet methods only — no dry sanding or scraping. "
        "HEPA vacuum for dust collection. "
        "Containment sheeting to prevent spread.\n"
        "Admin: Test for lead before work or assume present and apply lead-safe controls. "
        "Decontamination procedures — remove coveralls before leaving work area, "
        "wash hands and face before eating or drinking. "
        "Waste disposal per lead paint waste guidelines.\n"
        "PPE: P2 minimum, disposable coveralls, cut-resistant gloves, eye protection. "
        "P3 for extensive work or elevated airborne concentrations.\n"
        "Remove from exposure and rectify if dust controls fail."
    ),
    "post": 2,
    "resp": "Supervisor",
    "audit": "STD-6-3-LED",
    "hazard_summary": "Lead dust inhalation and ingestion — lead paint in pre-2000 construction.",
    "control_summary": "Wet methods only, HEPA vac, confirm or assume lead, decontamination before leaving area, P2 minimum.",
},
```

---

## CODE: TRF — Traffic and Public Interface

Exclusion zones must be confirmed maintainable before work starts. If zones
cannot be maintained — STOP and implement approved TPMP. hi-vis vest or shirt mandatory
for all workers near traffic or public access areas.

---

### TRF-1 — Work Adjacent to Road or Traffic Corridor

```python
{
    "task": (
        "Work Adjacent to Road or Traffic Corridor\n"
        "Site setup, deliveries, or work activities in proximity to live traffic."
    ),
    "hazard": (
        "Worker struck by vehicle. "
        "Public pedestrian entry into work zone. "
        "Delivery vehicle in conflict with traffic flow."
    ),
    "pre": 4,
    "controls": (
        "TRF (Medium — C=2): Controls in place.\n"
        "Engineering: Barricade and signage to create controlled work area. "
        "Pedestrian diversion maintained.\n"
        "Admin: Traffic management plan (TPMP) as required by PC or council. "
        "Traffic controller or spotter where required. "
        "Schedule deliveries off-peak where practicable. "
        "HOLD POINT: If exclusion zone cannot be maintained without encroaching on "
        "footpath or roadway — STOP and implement approved TPMP before continuing.\n"
        "PPE: hi-vis vest or shirt, steel-capped footwear, hard hat."
    ),
    "post": 1,
    "resp": "Supervisor",
    "audit": "STD-4-2-TRF",
    "hazard_summary": "Worker struck by vehicle — public entering work zone during site setup or deliveries.",
    "control_summary": "Barricade and signage, TPMP if required, schedule off-peak, spotter where needed.",
},
```

---

### TRF-2 — Public Interface — Retail, Commercial, or Residential

```python
{
    "task": (
        "Public Interface — Retail, Commercial, or Residential Premises\n"
        "Works in or adjacent to occupied or publicly accessible premises."
    ),
    "hazard": (
        "Public or occupant entry into work zone. "
        "Dropped objects or debris reaching public areas. "
        "Noise, dust, or fume impact on occupants. "
        "Slips and trips — tools, leads, debris in public areas."
    ),
    "pre": 4,
    "controls": (
        "TRF (Medium — C=2): Controls in place.\n"
        "Engineering: Hoarding, barriers, or screens to fully separate public from work zone. "
        "Overhead catch protection where drop risk to public areas.\n"
        "Admin: Coordinate work hours with building manager or PC. "
        "Noise, dust, and fume management — schedule high-impact work for agreed times. "
        "Work zone inspected and secured at end of each shift. "
        "Clear and maintain emergency egress at all times.\n"
        "PPE: hi-vis vest or shirt, steel-capped footwear, appropriate dust/fume controls."
    ),
    "post": 1,
    "resp": "Supervisor",
    "audit": "STD-4-2-TRF",
    "hazard_summary": "Public or occupant entry into work zone — dropped objects — noise and dust impact.",
    "control_summary": "Hoarding or barriers to separate public, overhead catch protection, coordinate hours, secure site each shift.",
},
```

---

## CODE: ENV — Environmental and Chemical

SDS reviewed before use. Adequate ventilation confirmed before application
of solvent-based products. Waste disposed per SDS Section 13.
Never pour chemicals to drain or stormwater.

---

### ENV-1 — Chemical Application — Solvents, Coatings, Adhesives

```python
{
    "task": (
        "Chemical Application — Solvents, Coatings, or Adhesives\n"
        "Application of solvent-based paints, primers, adhesives, or chemical coatings."
    ),
    "hazard": (
        "Solvent vapour inhalation. "
        "Skin and eye contact. "
        "Ignition of flammable vapours. "
        "Environmental contamination — spill to stormwater or drain."
    ),
    "pre": 4,
    "controls": (
        "ENV (Medium — C=2): Controls in place.\n"
        "Admin: SDS reviewed before use — controls confirmed. "
        "Ventilation confirmed adequate before application. "
        "Ignition sources eliminated before opening solvent-based products. "
        "Spill kit on site. No disposal to drain or stormwater.\n"
        "PPE: Respirator per SDS, chemical-resistant gloves, eye protection, coveralls.\n"
        "Remove from exposure and rectify if ventilation inadequate."
    ),
    "post": 1,
    "resp": "Supervisor",
    "audit": "STD-4-2-ENV",
    "hazard_summary": "Solvent vapour inhalation, skin contact, ignition risk, spill to stormwater.",
    "control_summary": "SDS reviewed, ventilation confirmed, ignition sources eliminated, spill kit on site.",
},
```

---

### ENV-2 — Airless Spray Application

```python
{
    "task": (
        "Airless Spray Application\n"
        "Apply paint, membrane, or coating by airless spray."
    ),
    "hazard": (
        "High-pressure injection injury — nozzle contact. "
        "Solvent vapour and overspray inhalation. "
        "Overspray onto public or adjacent property. "
        "Ignition of flammable spray mist."
    ),
    "pre": 6,
    "controls": (
        "ENV (High — C=3): Controls in place.\n"
        "Engineering: Maintain equipment in good order — pressure settings per manufacturer. "
        "Trigger lock engaged when not spraying.\n"
        "Admin: SDS reviewed — ventilation confirmed before spraying. "
        "Never point gun at any person. "
        "Emergency procedure for injection injury — urgent medical immediately. "
        "Wind direction assessed before spray — stop if overspray uncontrollable. "
        "Exclusion zone sized to actual drift footprint.\n"
        "PPE: Respirator per SDS, coveralls, eye protection, chemical-resistant gloves."
    ),
    "post": 2,
    "resp": "Supervisor",
    "audit": "STD-6-3-ENV",
    "hazard_summary": "High-pressure injection injury, solvent vapour, overspray onto public, ignition of spray mist.",
    "control_summary": "Trigger lock when idle, never point at person, wind assessed, SDS controls, injection emergency plan.",
},
```

---

### ENV-3 — Hazardous Waste Handling and Disposal

```python
{
    "task": (
        "Hazardous Waste Handling and Disposal\n"
        "Collect, contain, and dispose of chemical waste, contaminated materials, "
        "or hazardous substances."
    ),
    "hazard": (
        "Chemical exposure during waste handling. "
        "Environmental contamination — spill or incorrect disposal. "
        "Manual handling — heavy or awkward waste containers."
    ),
    "pre": 4,
    "controls": (
        "ENV (Medium — C=2): Controls in place.\n"
        "Admin: Identify waste type — confirm disposal method per SDS Section 13. "
        "Labelled and sealed containers. No mixing of incompatible wastes. "
        "No disposal to drain, ground, or stormwater. "
        "Licensed waste contractor for regulated waste.\n"
        "PPE: Chemical-resistant cut-resistant gloves, eye protection, appropriate respiratory protection."
    ),
    "post": 1,
    "resp": "Supervisor",
    "audit": "STD-4-2-ENV",
    "hazard_summary": "Chemical exposure handling waste — environmental contamination from incorrect disposal.",
    "control_summary": "SDS disposal method confirmed, labelled sealed containers, no drain disposal, licensed contractor if required.",
},
```

---

### ENV-4 — Waterproofing Membrane Application

```python
{
    "task": (
        "Waterproofing Membrane Application\n"
        "Apply liquid or sheet waterproofing membrane to balconies, roofs, or wet areas."
    ),
    "hazard": (
        "Solvent vapour inhalation in semi-enclosed spaces. "
        "Skin sensitisation from isocyanates or epoxy components. "
        "Ignition of flammable membrane products. "
        "Slip on wet or uncured membrane."
    ),
    "pre": 6,
    "controls": (
        "ENV (High — C=3): Controls in place.\n"
        "Engineering: Forced ventilation in semi-enclosed balcony or internal spaces. "
        "Continuous air monitoring if isocyanate-based product used.\n"
        "Admin: SDS reviewed — confirm if isocyanate, epoxy, or solvent-based. "
        "Medical fitness confirmed for isocyanate exposure. "
        "Ignition sources eliminated before application. "
        "No walking on uncured membrane — barricade until cured.\n"
        "PPE: Supplied-air respirator or half-face with appropriate cartridge (per SDS), "
        "chemical-resistant gloves, coveralls, eye protection."
    ),
    "post": 2,
    "resp": "Supervisor",
    "audit": "STD-6-3-ENV",
    "hazard_summary": "Solvent vapour in enclosed space, isocyanate sensitisation, ignition risk, slip on uncured membrane.",
    "control_summary": "Forced ventilation, SDS controls, isocyanate fitness check, ignition eliminated, barricade until cured.",
},
```

---

### ENV-5 — Surface Preparation — Painting (No Silica, No Lead)

**Rule: This task is always Medium (4) / STD-4-2-ENV in any painting SWMS.**

Surface preparation for painting — scraping, sanding, spot-filling, and cleaning
painted surfaces — does not involve silica-generating substrates (masonry, concrete,
stone) or confirmed lead paint. The dust hazard is from existing paint only.
Consequence is C=2 (moderate injury — respiratory irritation, eye injury) — not C=3.

CCVS does not apply. Pre = 4, Post = 2, audit = STD-4-2-ENV.

**Do not assign ENV-H6 or CCVS to this task.** If silica or lead is present
(masonry grinding, pre-2000 paint confirmed), use SIL-H6 or LED-H6 instead.

If a pressure washer is used on the same job, it is a separate task (see ENV-6).
Do not combine pressure washing controls into this task.

```python
{
    "task": (
        "Surface Preparation — Interior & Exterior\n"
        "Scrape, sand, spot-fill and clean surfaces prior to painting. "
        "No masonry cutting or grinding. No confirmed lead paint."
    ),
    "hazard": (
        "Dust inhalation from dry sanding painted surfaces. "
        "Flying debris and paint chips at face and eye level. "
        "Chemical exposure from cleaning agents and sugar soap. "
        "Electric shock from 240V tools in wet or damp conditions."
    ),
    "pre": 4,
    "controls": (
        "ENV (Medium — C=2): Controls in place.\n"
        "Engineering: Wet sanding or damp sponge preferred for all hand sanding. "
        "HEPA vacuum fitted to any powered sanders — not dry-swept. "
        "Drop sheets to contain debris. "
        "All 240V tools RCD-protected (test-tagged) — battery tools preferred in damp areas.\n"
        "Admin: SDS reviewed for all cleaning agents before use — on site and accessible. "
        "P2 respirator worn during dry or powered sanding. "
        "Eye protection and cut-resistant gloves during scraping and chemical application. "
        "Keep public and residents clear of prep area — barricades maintained. "
        "Debris and wash-off collected — not to stormwater.\n"
        "PPE: P2 respirator (powered or dry sanding), safety glasses, "
        "chemical-resistant gloves, hearing protection (powered tools).\n"
        "STOP WORK: RCD trips and cannot be reset; 240V tool used in wet conditions."
    ),
    "post": 2,
    "resp": "Supervisor / Worker",
    "audit": "STD-4-2-ENV",
    "hazard_summary": (
        "Dust inhalation from sanding — flying debris — "
        "chemical exposure from cleaning agents — "
        "electric shock from 240V in damp conditions."
    ),
    "control_summary": (
        "Wet sanding preferred; HEPA vac on powered sanders; "
        "P2 respirator for dry/powered sanding; "
        "SDS on site for all cleaning agents; "
        "RCD on all 240V tools (test-tagged), battery tools in damp areas; "
        "debris contained — not to stormwater; "
        "stop-work if RCD trips or 240V used in wet conditions."
    ),
},
```

---

### ENV-6 — High-Pressure Washing — Petrol-Driven Unit

**Rule: Petrol-driven unit > 1000 PSI = ENV-H6 / CCVS-6-3-ENV.**
**Standard 240V domestic unit = ENV-M4 / STD-4-2-ENV.**

The CCVS trigger is the combination of injection injury consequence (C=3) from
high-pressure petrol units and the additional fire/explosion/CO risks from
on-site refuelling and exhaust in enclosed areas.

```python
{
    "task": (
        "High-Pressure Washing — Petrol-Driven Unit\n"
        "Pre-painting pressure wash of exterior surfaces using petrol-driven unit. "
        "On-site refuelling. Outdoors or fully open areas only."
    ),
    "hazard": (
        "High-pressure injection injury >1000 PSI — skin penetration. "
        "Fire or explosion from petrol refuelling. "
        "Carbon monoxide from exhaust in enclosed or semi-enclosed areas. "
        "Slip from wet surfaces. "
        "Whip injury from hose failure or fitting separation."
    ),
    "pre": 6,
    "controls": (
        "ENV (High — C=3) CCVS HOLD POINTS:\n"
        "Work must not commence until:\n"
        "(1) Rated tip confirmed correct for surface and PSI — no damaged or missing tips.\n"
        "(2) Unit confirmed outdoors or in fully open area — never in enclosed or "
        "semi-enclosed space (CO accumulation risk).\n"
        "(3) Exclusion zone established — min 3m from jet line, extend to full "
        "debris/spray throw (confirm on site before commencing).\n"
        "Engineering: Two-hand grip on lance at all times. "
        "Trigger lock engaged when not spraying. "
        "Whip-checks on all hose connections.\n"
        "REFUELLING: Engine off and cool before refuelling. "
        "Approved container with controlled spout. "
        "Fuel stored in bunded area — minimum quantity on site. "
        "No smoking or ignition sources within 5m. "
        "Spill kit on site.\n"
        "Admin: SDS for fuel on site. "
        "Waste wash-off captured — not to stormwater or drain.\n"
        "PPE: Waterproof footwear, face shield, cut-resistant gloves, hearing protection.\n"
        "STOP WORK: CO symptoms (headache, dizziness) — shut down, evacuate, call 000. "
        "Exclusion zone cannot be maintained."
    ),
    "post": 2,
    "resp": "Supervisor / Worker",
    "audit": "CCVS-6-3-ENV",
    "hazard_summary": (
        "High-pressure injection injury — fire/explosion from refuelling — "
        "CO from exhaust — whip from hose failure."
    ),
    "control_summary": (
        "Rated tip confirmed; trigger lock functional; whip-checks on hoses/connections; "
        "unit outdoors only (CO risk); exclusion zone min 3m extend to full spray throw "
        "(confirm on site); refuelling — engine off and cool, approved container, "
        "no ignition within 5m, spill kit on site; "
        "stop-work for CO symptoms or uncontrolled exclusion zone."
    ),
},
```

---

## SPECIAL CODE: SYS — AUTO-INJECTED

**DO NOT add SYS-L1 to your task list.**
The engine injects it automatically as Task 1 for every SWMS.

SYS-L1 covers: PC site induction on first day, daily toolbox talk pre-commencement,
SWMS sign-on before work starts each day, emergency briefing daily.

Pre = 1 always. Post = 1 always. No CCVS.

---

## SPECIAL CODE: EMR — AUTO-INJECTED

**DO NOT add EMR-H9 to your task list.**
The engine injects it automatically as the final task for every SWMS.

EMR-H9 covers: Call 000, first aid kit on site, emergency contacts displayed,
evacuation and muster point, rescue plan briefed.

Pre = 9 always. Post = 1 always. Standard language — never CCVS.

---

## Quick Reference — Code Selection by Trigger

| If you see this on site... | Primary code | Typical tier |
|---|---|---|
| Any work above 2m — rope access | IRA | H6 |
| Any work above 2m — EWP, scaffold, ladder | WAH | H6 |
| Any work above 2m — restraint only | WFR | H6 |
| Any work above 2m — arrest system | WFA | H6 |
| Grinding, drilling, raking concrete/masonry | SIL | H6 |
| Chemical application, solvents, coatings | ENV | M4 or H6 |
| Structural removal or reconstruction | STR | H6 |
| Confined space entry | CFS | H9 |
| Electrical isolation or live work | ELE | H6 or H9 |
| Stored energy — hydraulic, pneumatic, gravity | ENE | H6 |
| Hot works — welding, grinding with fire risk | HOT | H6 |
| Crane, excavator, forklift, mobile plant | MOB | H6 or H9 |
| Asbestos — disturbed or suspected | ASB | H9 |
| Lead paint — disturbed or suspected | LED | H6 |
| Traffic or public interface | TRF | M4 |
| Site governance — induction, toolbox | SYS | L1 (auto) |
| Emergency response | EMR | H9 (auto) |

---

*End of SWMS_TASK_LIBRARY.md*
*Select tasks from this library. SYS and EMR are auto-injected — never add manually.*

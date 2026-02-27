# SWMS METHODOLOGY — UNDERPINNING LOGIC v16.2

**System:** Robertson's Remedial and Painting Pty Ltd
**Version:** v16.3
**Created:** February 2026
**Cross-reference:** SWMS_GENERATOR_MASTER_v16.0.md | SWMS_BASE_GENERAL.py | SWMS_TASK_LIBRARY.md | TEMPLATE_RULES.md

---

## Purpose

This document explains the reasoning behind every decision in the SWMS generation
system. The MASTER tells you what to do. This document tells you why.

It serves three audiences:

**Anyone generating a SWMS** — so they understand the logic behind code selection,
CCVS triggers, and control hierarchy, and can make correct calls when a situation
does not fit a standard template.

**Supervisors and Lead Techs** — so they understand why hold points are structured
the way they are and what verification actually means on site.

**Auditors and regulators** — so the system can be demonstrated as a genuine safety
management process, not a document production exercise.

This SWMS is built using a consistent decision logic so the method, codes, and
controls reflect actual site conditions and the highest-risk parts of the work.
The SWMS is reviewed and revalidated whenever conditions or methods change.

---

## Step 1 — Define the Work as Performed

The work is broken into task steps in the order it will occur on site. Each task
is assigned a v16 hazard code based on the dominant risk driver for that step.

**Primary code selection rule — where multiple hazards exist:**
Where a task involves multiple hazards, the primary code reflects the hazard that
drives the most critical controls and the highest consequence. The other hazards
are addressed within the control text but do not change the code.

Examples of how this works in practice:

- Brickwork repointing involves silica dust, noise, vibration, and electrical tools.
  The primary code is `SIL-H6` because silica inhalation drives the most critical
  controls and has the highest consequence. Electrical controls are addressed in
  the control text as a secondary block.

- Crack stitching involves silica from drilling, chemical exposure from grout,
  and dropped objects. Primary code is `SIL-H6` — not `ENV` or `STR` — because
  silica dust from drilling is the dominant risk driver.

- Paint application involves solvent vapours, overspray, airless injection injury,
  and electrical risk. Primary code is `ENV-H6` because chemical/environmental
  exposure drives the primary controls.

**Rule:** Never assign a code based on what the task is called. Assign it based on
what hazard, if uncontrolled, would cause the most serious harm.

---

## Step 2 — Confirm Site Conditions and Interfaces

Controls and codes are selected after confirming site conditions. If conditions
differ from those assumed in this SWMS, work stops and the SWMS is updated and
re-signed before recommencing.

**Site Conditions Confirmation — four checks before task generation begins:**

**Check 1 — Access method and height**
What is the confirmed access method for each task? IRA (rope access) or WAH
(collective access — EWP, scaffold, ladder)? What is the maximum working height?
Are there overhead obstructions, balcony interfaces, or confined reach zones?

This determines whether the task gets `IRA` or `WAH` as its primary code.
These are not interchangeable. IRA requires two-rope systems, IRATA/ARAA
competency, and a dedicated rescue capability. WAH requires pre-start inspection,
operator licence for EWP, and hierarchy compliance for ladders. Assigning the
wrong code means the wrong controls apply.

**Check 2 — Ground and structural conditions**
Is the ground firm and level for EWP? Are anchors engineered and on a current
design document? Are there structural defects, movement, or instability in the
façade or substrate? Are there services behind the surface being worked on?

**Check 3 — Public and traffic interface**
Is there an adjacent road or traffic corridor? Can exclusion zones be fully
maintained within the site boundary without encroaching on footpath or roadway?
Are there residents, building occupants, or other trades whose access patterns
change during the day?

**Check 4 — Environmental conditions**
What are the wind limits for rope access and spray? Is rain forecast? Are there
heat stress risks? Can overspray be controlled given the prevailing wind direction
and adjacent properties?

**These four checks are not optional.** They are the inputs that determine whether
the controls written in this SWMS are valid for the actual site. A SWMS written
without confirming these conditions is a document, not a risk assessment.

---

## Step 3 — Identify Hazard Triggers Using a Repeatable Check

For each task, hazards are identified by running through six standard trigger
categories. This ensures no hazard type is missed and that the primary code
selection is defensible.

**The six triggers — run through every one for every task:**

| Trigger | What to look for | Codes it activates |
|---|---|---|
| **Gravity / Height** | Falls, dropped objects, access equipment, rescue complexity, suspension intolerance | IRA, WFA, WFR, WAH |
| **Energy** | Electrical tools and leads, moving plant, stored energy in pressurised or hydraulic equipment, airless spray injection | ELE, ENE, MOB |
| **Materials / Substances** | Silica and dust, solvents and chemicals, sealants and grouts, coatings and primers, lead, asbestos | SIL, ENV, LED, ASB |
| **Structure** | Instability, removal of load-bearing material, reconstruction, spalling, temporary works, excavation | STR |
| **Interfaces** | Pedestrians, residents, traffic corridor, other trades, dropped object fall-lines to public areas | TRF |
| **Environment** | Wind and overspray, noise and vibration, heat, working in rain or wet conditions | ENV, HOT |

**How to use this check:**
Go through each trigger for the task you are assessing. If it activates, note
which code it maps to. The trigger that maps to the highest consequence drives
the primary code. All activated triggers must be addressed in the control text
even if they do not change the primary code.

**Why this matters:**
The original RPD SWMS contained codes `AIR-H6`, `REM-H6`, and `CHM-H6` — none
of which exist in the v16 system. Those codes were assigned based on task
description rather than trigger analysis. Running the six-trigger check for each
of those tasks immediately identifies silica (SIL) or environmental chemical
(ENV) as the correct primary code. The trigger check is the correction mechanism.

---

## Step 4 — Select Controls Using the Hierarchy of Controls

Controls are selected in strict priority order. Every task must have at least
one control above PPE. PPE is always last — never the primary control.

```
1. Eliminate      — change the method so the hazard does not exist
2. Substitute     — lower-risk plant, material, or process
3. Isolate        — exclusion zones, barriers, physical separation
4. Engineering    — guarding, extraction, edge/rope protection, RCDs, HEPA vac
5. Administrative — permits, sequencing, supervision, hold points, checklists
6. PPE            — task-specific, verified fit, last resort
```

Controls are chosen to be reasonably practicable under WHS Act s18 — based on
severity, likelihood, and the availability and suitability of controls at the
time the work is performed.

**Practical rule:** If the only controls listed for a high-consequence task are
administrative and PPE, the assessment is incomplete. Engineering controls must
be identified and either implemented or explicitly justified as not practicable.

---

## Step 5 — Apply v16 Code Rules and Translations

This SWMS applies the 15-code v16 system plus two special codes. The full list:

| Code | Full Name | Tier |
|---|---|---|
| WFR | Work at Heights — Fall Restraint | H |
| WFA | Work at Heights — Fall Arrest | H |
| WAH | Work at Heights — Collective & Access | H |
| IRA | Industrial Rope Access | H |
| ELE | Electrical | H |
| SIL | Silica & Dust | H |
| STR | Structural | H |
| CFS | Confined Space | H |
| ENE | Energised Equipment & Stored Energy | H |
| HOT | Hot Works | H |
| MOB | Mobile Plant | H |
| ASB | Asbestos | H |
| LED | Lead | H |
| TRF | Traffic & Public Interface | M typical |
| ENV | Environmental & Chemical | M or H |
| SYS | Site Systems & Induction *(special — locked. REC is not used.)* | L always |
| EMR | Emergency Response *(special)* | H9 always |

**Translation rules — these are fixed, not discretionary:**

`IRA` is used for rope access tasks — not `WAH`. The distinction matters because
IRA requires two-rope systems, IRATA/ARAA crew competency, and a dedicated
on-site rescue capability. WAH does not. Using WAH for a rope access task means
the wrong controls apply.

`WAH` is used for collective access and access equipment — EWP, scaffold, ladder.

`SIL` is used where silica or dust is the primary hazard driver — surface
preparation, grinding, drilling, raking, jackhammering.

`ENV` is used for chemical and environmental exposures — solvents, sealants,
coatings, overspray, chemical spill risk.

**ENV — painting surface preparation rule (locked):**
Surface preparation for painting (scrape, sand, spot-fill, clean painted surfaces)
is always `ENV-M4` / `STD-4-2-ENV` in any painting SWMS. Pre = 4, C = 2.
The dust hazard from sanding existing paint is C=2 — not C=3. CCVS does not apply.
If silica-generating substrates (masonry, concrete, stone) are present, use `SIL-H6`.
If lead paint is confirmed or suspected, use `LED-H6`.
Pressure washing is always a separate task — never combined with surface preparation.
Petrol-driven pressure washers (>1000 PSI) = `ENV-H6` / `CCVS-6-3-ENV` (injection
injury C=3 + fire/CO from refuelling). Standard 240V units = `ENV-M4` / `STD-4-2-ENV`.

`STR` is used for structural and reconstruction tasks — brickwork, spalling
repair, load-bearing elements.

`TRF` is used for traffic and public interface tasks.

`SYS` — not `REC` — is the code for all governance and records tasks including
site induction, daily sign-in, toolbox talk, and SWMS sign-on. SYS is used
because the task is about doing the process, not filing the paperwork. REC
implies passive record creation. SYS implies active governance. Pre score is
always 1. This is a locked decision — do not use REC.

`EMR` is mandatory and locked for Emergency Response. Pre is always 9.
Post is always 1. Always the final task. Always applicable to all workers.

---

## Step 6 — Verification and CCVS Hold Points

Controls are written with a verification standard based on risk level.

### CCVS Trigger Rule — three conditions, all must be met

```
IF   pre score ≥ 6  (H tier)
AND  consequence = 3  (Major — potential fatality or permanent disability)
AND  category is in the critical risk list
THEN apply CCVS hold point language
```

**Critical risk categories for CCVS — full locked list:**
WFR, WFA, WAH, IRA, ELE, SIL, STR, CFS, ENE, HOT, MOB, ASB, LED

This list is fixed. It is not extended by PCBU discretion. If a new category
is added to the v16 system, this list is updated explicitly in this document
and in the MASTER. Until then, only these 13 categories trigger CCVS.

TRF and ENV are not in the CCVS list. Their consequence rating is typically
2 (Moderate), not 3 (Major). If a specific TRF or ENV scenario genuinely
carries consequence = 3, the task should be re-coded to the primary hazard
that drives that consequence — the code change resolves the CCVS question.

### The negative rule — explicit and non-negotiable

**Pre = 6 with consequence = 2 does NOT trigger CCVS, regardless of likelihood.**

Example: A TRF task scores pre = 6 because likelihood is Almost Certain (3)
and consequence is Moderate (2). That gives 3 × 2 = 6. CCVS does not apply
because the consequence is 2, not 3. Standard controls apply.

Example: Surface preparation for painting (sanding, scraping, cleaning painted
surfaces) scores pre = 4, consequence = 2. CCVS does not apply. Code is
`STD-4-2-ENV`. This applies to every painting SWMS without exception.

This is not a judgment call. If consequence is not 3, CCVS language is
not used. No exceptions.

### CCVS language

For CCVS tasks:
> *"Work must not commence until…"*
Followed by numbered hold points. Each hold point is a specific, measurable
verification action. Close with:
> *"Confirmation retained in site diary or digital system."*

For non-CCVS tasks:
> *"Controls in place."*

### EMR exception

EMR is always `EMR-H9` and always uses standard emergency response language.
It does not use CCVS hold point language regardless of its pre score of 9.
Emergency response cannot have a pre-commencement hold point — it must be
executable immediately without verification steps. A hold point before an
emergency is a contradiction in terms. The pre score of 9 reflects the
consequence of an uncontrolled emergency, not a trigger for CCVS language.

### What CCVS hold points actually mean on site

A CCVS hold point is not a signature. It is a specific check with a specific
outcome. The supervisor physically confirms each item before work starts and
retains a record. Over time, hold point records become the evidence base that
your highest-risk controls are being verified consistently — not assumed to be
in place because a SWMS exists.

---

## Step 7 — Spray and Overspray Logic

Spray application introduces a distinct risk dimension that does not exist with
brush and roller — uncontrolled drift and public exposure. It is treated as a
separate decision step, not just an ENV control.

**Before spray commences:**
Wind direction and speed assessed. If overspray cannot be contained within the
controlled zone, spray does not start. This is a stop decision, not a PPE
decision — no respirator resolves overspray onto a public footpath or adjacent
property.

Exclusion zones for spray are sized to the actual drift footprint under current
wind conditions — not a fixed distance. Screens and shrouds used where drift
risk exists toward any public or residential interface.

SDS controls applied for all solvent-based products — vapour management,
ignition source elimination, and skin/eye protection confirmed before the
trigger is pulled.

**During spray:**
Wind direction monitored continuously. If conditions change and drift risk
increases — stop, reassess, resume only when controlled.

**Code implication:**
Spray application is `ENV-H6` when chemical/vapour exposure is the dominant
driver. If the work is at height via IRA or WAH, the height code takes primary
position and spray controls are addressed as a secondary block within that task.
The spray decision does not override the primary code — it adds to the controls.

---

## Step 8 — Change Management (Dynamic Risk)

This SWMS must be stopped, updated, briefed to all workers, and re-signed
before work recommences if any of the following change:

**Trigger 1 — Access method changes**
IRA switches to WAH or vice versa. Different EWP type or positioning required.
Ladder required where EWP was planned. This changes the primary code, the
controls, and potentially the CCVS hold points. A new or amended task row
is required.

**Trigger 2 — Exclusion or drop zones cannot be maintained or are breached**
Public or resident access patterns change. A footpath or road cannot be closed
as planned. Other trades enter the fall zone. The controls for TRF and dropped
objects are no longer valid as written — stop, reassess, update.

**Trigger 3 — Anchors or rigging points cannot be verified**
An anchor cannot be confirmed against the engineering design. A rigging point
shows signs of movement, damage, or deterioration. Edge conditions change
in a way that affects rope protection. This is an IRA-specific trigger that
cannot be deferred — if the anchor cannot be verified, no one goes over the edge.

**Trigger 4 — Weather creates unsafe conditions**
Wind exceeds rope access limits or makes overspray uncontrollable. Rain affects
ground conditions for EWP or introduces electrical risk. Heat stress conditions
develop. Weather is not a minor variation — it changes likelihood scores and
may change consequence scores for affected tasks.

**Trigger 5 — Discovery of new hazards**
Services identified behind surface being worked on. Structural defects found
that were not visible before commencing. Hazardous materials — asbestos,
lead — discovered or suspected during work. Each of these may add a new task
row, change an existing code, or require the SWMS to be suspended pending
further assessment.

**Trigger 6 — New trades or changed interfaces**
Other contractors arrive whose work pattern creates new interfaces — overhead
work above the exclusion zone, plant movement near the work area, changed
building access for residents or occupants.

**Stop-work rule:**
If site conditions do not match this SWMS, work stops immediately. The SWMS
is revised, briefed to all workers in person, and signed before work
recommences. A verbal update is not sufficient. The revision is documented
with a date and the names of workers re-briefed.

**Change management and the database:**
Each change trigger event should be recorded — what changed, which task rows
were affected, what the updated controls are, and who was re-briefed. This
record is the evidence that your system responds to dynamic risk, not just
planned risk.

---

## Step 9 — Systems, Records, and Emergency Response Are Always Applied

These two tasks appear in every SWMS regardless of job type, access method,
or scope. They are not optional and are not removed or modified for simpler jobs.

**SYS-L1 — Site Induction & Daily Sign-In (always first task)**

Covers: PC site induction completed by all workers on first day and recorded.
Daily toolbox talk conducted pre-commencement — covers tasks, hazards, controls,
weather, and site changes. All workers sign SWMS before commencing work each day.
No signature means no start. Emergency assembly point and contacts briefed daily.
SWMS reviewed and re-signed if any change trigger is activated.

Pre score is always 1. This is a governance task, not a physical hazard task.
Code is `SYS-L1`. Post score is always 1.

**EMR-H9 — Emergency Response (always last task, always applicable to all workers)**

Covers: General emergency — call 000, first aider and kit on site, emergency
contacts displayed, evacuation to muster point and headcount.
Rope access rescue — rescue kit on site, team of 3, rescue plan briefed,
suspended worker recovered within 10 minutes.
EWP emergency — ground controls accessible, trained person able to operate
emergency lowering.
Fire — evacuate, call 000, do not re-enter.
Chemical spill — spill kit on site, isolate area, dispose per SDS.

Pre score is always 9. Post score is always 1. Code is `EMR-H9`.
Standard language — no CCVS hold points.

SYS sign-on records and CCVS hold point verifications are the primary data
inputs to the safety management system — not compliance paperwork. They are
the evidence base that your highest-risk controls are being verified
consistently across every job. Without them, the system is a document
library. With them, it is a measurable safety record.

---

## Summary — The Nine Steps as a Checklist

Use this before generating any SWMS:

```
[ ] Step 1  Work broken into tasks in order of occurrence.
            Primary code assigned based on dominant risk driver — not task name.
            Multi-hazard tasks: code reflects highest-consequence hazard.

[ ] Step 2  Four site conditions confirmed:
            access method and height | ground and structural conditions |
            public and traffic interface | environmental conditions.

[ ] Step 3  Six-trigger hazard check run for each task:
            gravity/height | energy | materials/substances |
            structure | interfaces | environment.

[ ] Step 4  Controls follow hierarchy — at least one control above PPE per task.
            Engineering controls identified or justified as not practicable.

[ ] Step 5  v16 codes applied per translation rules.
            SYS not REC. IRA not WAH for rope access.
            EMR-H9 locked and present as final task.

[ ] Step 6  CCVS applied where pre ≥ 6 AND consequence = 3 AND critical category.
            Negative rule confirmed: consequence = 2 does not trigger CCVS.
            Full locked list: WFR WFA WAH IRA ELE SIL STR CFS ENE HOT MOB ASB LED.
            EMR uses standard language — not CCVS.

[ ] Step 7  Spray: wind assessed, exclusion zone sized to drift footprint,
            stop decision made before trigger pulled — not a PPE decision.

[ ] Step 8  Six change management triggers identified and briefed to site team.
            Workers know the triggers and the stop-work rule.

[ ] Step 9  SYS-L1 is Task 1. EMR-H9 is final task. Both present in every SWMS.
            SYS sign-on and CCVS hold point records captured — not just signatures.
```

---

## Document Control

| Field | Detail |
|---|---|
| Version | v16.2 |
| Date | February 2026 |
| Owner | Robertson's Remedial and Painting Pty Ltd |
| Cross-reference | SWMS_GENERATOR_MASTER_v16.0.md |
| Cross-reference | SWMS_BASE_GENERAL.py |
| Cross-reference | SWMS_TASK_LIBRARY.md |
| Cross-reference | USER_INPUT_REQUEST_GENERAL.md |
| Cross-reference | TEMPLATE_RULES.md |
| Cross-reference | FINAL_MANIFEST.md |
| Review trigger | Any change to the v16 code system, CCVS rules, or step structure |
| Changes v16.1 | SYS locked (REC removed). Negative CCVS rule explicit. Full locked CCVS category list. EMR exception explanation added. Spray/overspray promoted to Step 7. Change management expanded to 6 triggers. Step 9 data layer. Nine-step checklist. |
| Changes v16.2 | General system introduced. SWMS_BASE_GENERAL.py with auto-injected SYS and EMR. SWMS_TASK_LIBRARY.md covering all 15 codes. USER_INPUT_REQUEST_GENERAL.md for all job types. Cross-references updated. |
| Changes v16.3 | ENV painting surface prep rule locked: always STD-4-2-ENV in any painting SWMS — C=2, no CCVS. Pressure washing separated as standalone task. ENV-5 and ENV-6 added to SWMS_TASK_LIBRARY.md. Rule added to Step 5 translation rules and Step 6 negative rule examples. |

---

*End of SWMS_METHODOLOGY.md*
*This document explains the reasoning. The MASTER documents the rules.*
*When they conflict — update both.*

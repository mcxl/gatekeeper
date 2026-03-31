# SWMS Expert Review Specification

Human reference only. Not parsed at runtime.
Source reference for prompt updates, issue-gate checks, scenario rule packs, pilot assessment, and external reviewer briefing.

---

## 1. Core drafting mandate

Every SWMS produced by this system must read like a competent Australian WHS consultant prepared it for a specific project — not like a compliance template filled by software. The document is always draft-for-review until a competent person signs it off.

Key principles:
- Source-faithful: controls and method reflect the actual project scope, not generic trade templates
- Physically credible: every control describes an observable action a worker can perform on site
- Sequentially sound: the method can be followed top-to-bottom as a real work sequence
- Hazard-specific: controls lead with the dominant physical hazard for each task, not admin or PPE
- Prudent but not speculative: infer only what is physically obvious from the method

---

## 2. Fixed SWMS table structure

8 columns, fixed. No new columns. No column renames.

| Col | Name | Content |
|-----|------|---------|
| 1 | Step | Sequential number (1.1, 1.2, ...) |
| 2 | Task | VERB + OBJECT + CONTEXT, under 10 words |
| 3 | Hazard | Dominant hazard + supporting hazards |
| 4 | Risk (Pre) | Pre-control risk rating: High(N), Medium(N), Low(N) |
| 5 | Controls | Physical controls in hierarchy order (see Section 8) |
| 6 | Risk (Post) | Post-control residual risk rating |
| 7 | Responsibility | SUP and WKR task-specific responsibility text |
| 8 | CCVS Code | Three components in fixed order (see Section 3) |

---

## 3. Column 8 rules — CCVS + HP + SWT

Column 8 must always contain all three components in this exact order:

```
CCVS: [code]
HP: [hold point condition]
SWT: [stop work trigger]
```

CCVS first. HP second. SWT third. Never reversed. Never omitted unless genuinely not applicable.

**CCVS code** must match the task's dominant hazard family:
- SIL-H6: silica dust — grinding, cutting, drilling, tile removal, concrete breakout
- CHM-H6: chemical — membrane application, coatings, sealants, adhesives
- WAH-H6: work at height — scaffold, EWP, rope access, roof edge
- SYS-M3: system/management — site setup, QA, inspection, demob
- Other codes per `agents/control_writer.py` CCVS table

**HP** must name a real condition: "substrate inspected and approved before membrane" — not "hold point required."

**SWT** must be tied to the dominant task failure mode: "stop work if wet suppression fails" — not "stop work if unsafe." If no specific trigger exists: "SWT: None beyond general project stop-work rules."

---

## 4. Dominant control family rules

Each task has a dominant control family determined by its CCVS code. Controls in Column 5 must lead with that family.

| Family | Task types | Column 5 leads with | Column 8 CCVS |
|--------|-----------|---------------------|---------------|
| SIL | Demolition, removal, grinding, cutting, drilling | Wet suppression, dust extraction, debris containment, exclusion zone | SIL-H6 |
| CHM | Waterproofing, coatings, adhesives, sealants | SDS on point of use, ventilation, substrate condition, cure window | CHM-H6 |
| WAH | Scaffold, EWP, rope access, roof edge work | Edge protection, rescue readiness, anchor inspection, transfer method | WAH-H6 |
| LIFT | Crane, suspended loads | Lift plan, ground bearing, exclusion zone, load path | LIFT code |
| TEMP | Propping, bracing, structural alteration | Prop base condition, engineer sequence, no unauthorised movement | TEMP code |
| SYS | Inspection, QA, site setup, demob | Acceptance criteria, hold point authority, sign-off condition | SYS-M3 |

**Determination logic**: `_correct_ccvs_by_task_type()` in `core/orchestrator.py` and `_get_dominant_family()` in `agents/control_writer.py`.

**Override rules**:
- Removal/demolition tasks force SIL regardless of what they're removing (e.g. "Remove waterproofing membrane" is SIL, not CHM)
- Scaffold/EWP tasks force WAH even when task name contains "remove" or "demobilise"
- Demob/handover tasks force SYS-M3 unless combined with scaffold dismantling (which stays WAH)

---

## 5. Sequence and dependency rules

### Generic backbone
```
mobilisation → site establishment → preparatory works →
principal works → finishing → defects/make good → demobilisation
```

### Chronological method rule
Each task must occur before the next task can safely happen. Do not place investigative, protective, or preparatory tasks after demolition, repair, waterproofing, tiling, or reinstatement.

### Phase scoring (deterministic reorder)
Phase 0: site setup, isolate/barricade, protect-below
Phase 1: scaffold/EWP erection
Phase 2: removal, stripping, substrate exposure, investigation
Phase 3: structural repairs
Phase 4: waterproofing, membrane application
Phase 5: coatings, painting, finishes, screed, tiling
Phase 6: reinstatement
Phase 7: QA, defect check, final inspection
Phase 8: demobilisation

**Implementation**: `_task_phase_score()` and `_reorder_tasks()` in `core/orchestrator.py`.

### Remedial waterproofing backbone (mandatory)
1. Pre-start planning and site readiness
2. Access / scaffold setup
3. Isolate occupants and protect areas below
4. Remove fittings, fixtures, and failed finishes
5. Expose and prepare substrate
6. Consultant inspection / hold point
7. Substrate repairs
8. Primer / membrane application
9. Cure / test / QA release
10. Screed / tile / finishes
11. Reinstate balustrades, fittings, joinery
12. Final inspection, clean, demobilisation

### Sequence failure rules (issue gate C22)
FAIL if any of these appear after repair/membrane/tiling/reinstatement:
- Protection-below or occupant isolation
- Substrate exposure or investigation
- Hold-point or inspection (except final inspection)

**Implementation**: `_check_late_protection_or_exposure()` in `src/issue_gate.py`.

---

## 6. Pre-requisite vs live-step rules

### Framework controls (not standalone task rows)
- Generic toolbox talk
- Generic SWMS review
- Generic latent condition wording
- Generic emergency note

These belong in pre-start logic or stop-work triggers, not as standalone task rows.

### Prerequisite contradiction
Do not write "No hazardous substances identified" as a prerequisite when later tasks use chemicals, membranes, or SDS-controlled products.

**Implementation**: `_strip_generator_artefacts()` in `core/orchestrator.py`.

---

## 7. Hazard identification rules

- Dominant hazard must match the task's actual physical work — not default to fall-from-height
- HRCW boolean must be true when hrcw_category contains any cl.N class (cl.1 through cl.9)
- HRCW must match written method — do not over- or under-call
- Asbestos: treat as latent/contingency condition unless source explicitly confirms active removal scope
- CLT and EWP patterns detected from task text, not from job_type field

**Implementation**: `_normalise_task()` hrcw correction in `core/orchestrator.py`, `_strip_active_hazmat()` for asbestos.

---

## 8. Control credibility rules

### Control writing order (Column 5)
1. Precondition — what must be true before work starts
2. Active control — what must be maintained during work
3. Exclusion or no-go — what must never happen
4. Completion or transition — what confirms step is done

### Anti-bloat (reject these controls)
- Follow SWMS
- Use PPE as required
- Supervisor to monitor
- Ensure area is safe
- Implement controls as necessary
- Maintain situational awareness
- Comply with legislation

### Technically incorrect wording (strip deterministically)
- "Working at heights licence/training verified" — training is a prerequisite, not a live control
- "Anchor point rated to 6 kN" — not a meaningful specification
- "Load-test scaffold before use" — not standard Australian practice
- "P2 mask/respirator" on CHM tasks — P2 is particulate-only; use organic vapour respirator per SDS Section 8

**Implementation**: `_strip_generator_artefacts()` and `FILLER_CONTROL_PHRASES` in `src/issue_gate.py`.

---

## 9. Responsibility assignment rules

Column 7 must contain task-specific responsibility text for SUP and WKR roles — not generic "Supervise [task name]" / "Perform [task name] per SWMS."

Task-type-specific patterns:
- Scaffold erection: SUP verifies certification, supervises erection, signs off load checks
- Scaffold dismantling: SUP supervises dismantling sequence, verifies exclusion below (NOT erection language)
- Painting/coating: SUP verifies SDS, checks ventilation, signs hold points
- Demob: SUP supervises dismantling, verifies controls, manages site access

**Implementation**: `_improve_responsibility()` in `core/orchestrator.py`.

---

## 10. Hold point / stop-work rules

### Hold points
- Must name the approval authority and the condition
- Wrong: "Hold point — inspector to approve"
- Right: "Hold point — [named consultant] to inspect and sign off [specific condition] before [next task] commences"
- Maximum 2 per task

### Stop-work triggers
- Must be tied to the dominant task failure mode
- Wrong: "Stop work if unsafe"
- Right: "Stop work if wet suppression fails, debris escapes exclusion zone, or unexpected substrate condition is found"
- Maximum 3 per task

---

## 11. Anti-bloat / anti-drift / generator-artefact filters

### Anti-drift (do not invent controls not in scope)
- Council permits or EPA notifications
- Demolition supervisor unless named in source
- Utility isolation certificates unless in source
- NATA certificates unless in source
- Mobile crane unless method confirms crane use
- Asbestos clearance as active scope when source says latent only
- Biocide or decay treatment when not in source
- Rail corridor or work box unless in source
- EPA asbestos licence holder clearance (invalid NSW framing)

### Prudent inference (acceptable)
- Exclusion zone below facade work
- SDS on point of use for chemical products
- Weather stop for long sheets or coatings
- Stop work if unknown material encountered

**Implementation**: `_strip_unsupported_controls()`, `_UNSUPPORTED_CONTROL_PHRASES`, `UNSUPPORTED_ADMIN_KEYWORDS` in `src/issue_gate.py` and `core/orchestrator.py`.

---

## 12. Deterministic check candidates

Current issue gate checks (see `src/issue_gate.py`):

| # | Check | Type |
|---|-------|------|
| C1 | access_before_dependents | Sequence |
| C2 | no_coat_reinstate_merge | Structure |
| C3 | no_prestart_in_demob | Structure |
| C4 | ccvs_coverage | CCVS |
| C5 | ccvs_alignment | CCVS |
| C5b | ccvs_completeness | CCVS |
| C6 | wah_percentage | WAH dominance |
| C7 | unsupported_controls (JSON + docx) | Drift |
| C8 | responsibility_field | Credibility |
| C9 | footer_version | Document |
| C10 | latent_condition_packaging | Structure |
| C14 | dominant_control_family | Control family |
| C15 | hrcw_undercall | HRCW |
| C16 | unsupported_admin_controls | Drift |
| C17 | framework_control_misuse | Structure |
| C18 | wah_dominance_extended | WAH dominance |
| C19 | filler_controls | Credibility |
| C20 | job_type_mandatory_steps | Job-type |
| C21 | orphan_reinstatement | Sequence |
| C22 | late_protection_or_exposure | Sequence |
| C23 | sequence_rule_pack_violations | Scenario |

**Candidates for future checks** (from external review learnings):
- Monitoring copy-paste detection (same critical_control text across unlike tasks)
- P2/organic-vapour mismatch detection on CHM tasks
- Prerequisite contradiction detection
- Truncated responsibility field detection

---

## 13. Reviewer verdict thresholds

| Status | Criteria |
|--------|---------|
| BENCHMARK_QUALITY_CONFIRMED | Source-faithful task map, believable workflow, HRCW coherent, Column 8 CCVS verifies every task, HP/SWT present and relevant, no unsupported drift, only minor wording variability |
| BENCHMARK_QUALITY_WITH_CAVEATS | All of the above except one narrow named non-structural gap |
| STRONG_WORKING_DRAFT | Broad sequence correct, main hazards identified, no systematic unsupported controls, Column 8 not systematically wrong, usable after consultant completion |
| BELOW_STRONG_WORKING_DRAFT | Material unsupported drift, wrong control family across multiple tasks, wrong sequence affecting safety logic, HP/SWT missing or generic across multiple tasks |

**Coordinator floor rule**: If credibility-drift agent returns FAIL, overall status floored at BELOW_WORKING_DRAFT regardless of other agents.

**Implementation**: `run_parallel_review()` in `core/reviewer_agent.py`.

---

## 14. Known generation-quality limits

These are limitations of the current Haiku-based pipeline that cannot be fixed deterministically:

| Limit | Impact | Workaround |
|-------|--------|------------|
| Monitoring copy-paste across task rows | Monitoring critical_control text from one task appears verbatim on another | Consultant completion — review monitoring per task |
| Responsibility field copy-paste | SUP/WKR text occasionally repeats from adjacent tasks | `_improve_responsibility()` catches generic patterns but not all cross-task copies |
| Agent 2 hazard count variance | Risk assessor sometimes returns < 2 hazards, causing validation retry | Pipeline retry logic handles this |
| Dominant hazard text vs CCVS mismatch | Agent 2 states "fall from height" as dominant hazard but CCVS correctly set to CHM/SIL by post-processing | Cosmetic — CCVS is authoritative, hazard text is informational |

---

## 15. Scenario pack candidates

Reusable scenario-specific rule packs that could be implemented in `core/job_type_rules.py`:

| Scenario | Detection | Key rules |
|----------|-----------|-----------|
| Remedial waterproofing | job_type=remedial + "waterproof" or "membrane" in tasks | 12-step backbone, substrate hold point, occupied-site interface |
| Protected roof access (scissor lift) | "scissor lift" + "roof" + guardrail/gate context | Transfer method, exclusion zone, controlled transfer sequence |
| CLT/mass timber erection | "clt" or "mass timber" or "panel" + crane | Engineer sequence, prop discipline, permanent connection before release |
| EWP roof access | "ewp" + "roof" | Transfer method, rescue plan, wind limits |
| Occupied building interface | "occupied" in scope_modifiers | Occupant notification, barricade, noise/dust management |
| Asbestos latent condition | "asbestos" as latent/contingency | Stop-work trigger, no active removal unless source-confirmed |

---

## 16. Relationship to existing files

| Document | Role | Relationship to this spec |
|----------|------|--------------------------|
| `docs/SWMS_GENERATION_RUBRIC.md` | Master rubric header (stub) | This spec contains the substantive content that the rubric header references |
| `src/issue_gate.py` | Deterministic checks | Section 12 of this spec lists all checks; future checks derive from Sections 8, 11 |
| `core/job_type_rules.py` | Job-type rule packs | Section 15 of this spec lists scenario pack candidates |
| `agents/decomposer.py` | Decomposer prompt | Sections 5, 6 of this spec are the source reference for sequence rules |
| `agents/control_writer.py` | Control writer prompt | Sections 3, 4, 8, 10 of this spec are the source reference for control rules |
| `core/reviewer_agent.py` | Reviewer agent prompts | Section 13 of this spec defines the quality thresholds |
| `core/orchestrator.py` | Deterministic post-processing | Sections 4, 7, 8, 9, 11 of this spec describe what the post-processing enforces |
| `docs/FIVE_JOB_PILOT_PLAN.md` | Pilot plan | This spec provides the assessment criteria for pilot jobs |

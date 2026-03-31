# Consultant-Assisted Pilot Workflow

How to use Safe Method to generate, review, and issue a SWMS in consultant-assisted mode.

---

## 1. How a consultant uses Safe Method

Safe Method generates a SWMS draft from a project scope description. The consultant provides the scope, reviews the generated output, completes consultant-specific fields, and issues the final document.

The system handles:
- Task decomposition and sequencing
- Hazard identification and CCVS coding
- Control writing led by dominant hazard family
- Deterministic post-processing (artefact removal, CCVS correction, monitoring alignment)
- Automated quality checking (27 issue gate checks)

The consultant handles:
- Verifying the method makes sense for the actual site
- Completing fields that require site-specific knowledge
- Correcting any generation-quality artefacts that slip through
- Signing off as the competent person

---

## 2. What the consultant reviews before issue

Every generated SWMS must be reviewed by the consultant before issue. The system is draft-for-review — never issue-ready without human sign-off.

### Mandatory review points

| Area | What to check | Why |
|------|---------------|-----|
| **Method sequence** | Does the task order match how the work would actually be done on this site? | The system reorders deterministically but decomposer may occasionally place tasks out of logical order |
| **Monitoring sections** | Is each task's monitoring.critical_control specific to that task's dominant hazard? | Known generation limit: monitoring text sometimes copies across unlike tasks |
| **Responsibility fields** | Are SUP and WKR fields filled with real names or roles for this project? | System generates generic role text; consultant must insert actual names |
| **HRCW classification** | Does the HRCW flag match the actual task content and WHS Reg Schedule 3? | System corrects boolean from category but agent may under- or over-call |
| **Hold point authorities** | Is the named consultant/inspector correct for this project? | System generates placeholder or generic authority names |
| **Stop-work triggers** | Is each SWT tied to the real dominant failure mode for that task? | System generates SWT per CCVS family but may miss site-specific conditions |
| **CCVS code alignment** | Does each task's CCVS code match its dominant hazard family? | System corrects most mismatches but edge cases exist |
| **Scope faithfulness** | Do the controls reflect only what the scope requires — no drift? | System strips known drift but agent may generate plausible-sounding unsupported controls |

### Quick-scan checklist (under 5 minutes)

1. Read the task list top to bottom — does the sequence make physical sense?
2. Scan Column 8 (CCVS + HP + SWT) — do the codes match the task names?
3. Check monitoring rows — is the critical control different for each task type?
4. Check responsibility — are names filled in or still generic?
5. Check hold points — is the named authority correct for this project?

---

## 3. Known areas requiring consultant attention

### Monitoring sections
The system applies family-specific monitoring templates and deduplicates cross-family copy-paste. However, verbatim monitoring from one task may still appear on another task within the same CCVS family. The consultant should verify that each task's monitoring makes sense for that specific task.

**What to look for:** Same monitoring text on tasks that do different physical work (e.g. "dust extraction" on a coating task).

### Responsibility fields
The system replaces generic "Supervise [task name]" / "Perform [task name] per SWMS" with task-type-specific text. The consultant must insert actual supervisor and worker names and verify the roles match the project team.

### HRCW classification
The system corrects the hrcw boolean when the hrcw_category contains any class (cl.1 through cl.9). The consultant should verify that HRCW is not under-called on tasks that genuinely involve Schedule 3 high-risk work (e.g. crane operation, confined space, work near energised electrical).

### Hold point authorities
The system generates hold point text but may use generic authority references. The consultant must name the actual inspector, engineer, or consultant responsible for each hold point.

### Stop-work triggers
The system generates SWT per CCVS family template. The consultant should verify that each trigger addresses the actual dominant failure mode for that task on this site — not a generic "stop work if unsafe" placeholder.

---

## 4. What the system handles reliably

These areas generally do not need consultant correction:

| Feature | Reliability | Notes |
|---------|------------|-------|
| Task sequencing (phase scoring) | High | Deterministic reorder enforces logical sequence |
| CCVS code correction | High | `_correct_ccvs_by_task_type()` assigns correct family based on task name keywords |
| Generator artefact removal | High | Strips WAH licence boilerplate, 6 kN anchor claims, scaffold load-test, P2 on CHM tasks, prerequisite contradictions |
| Anti-drift filtering | High | Removes unsupported controls (council permits, EPA, NATA, disconnection certs on non-demolition) |
| Anti-bloat filtering | High | Removes filler controls ("follow SWMS", "use PPE as required", "ensure area is safe") |
| Dominant control family injection | High | Control writer receives per-task constraint to lead with correct hazard family |
| Asbestos latent-condition handling | High | Strips active asbestos presumption when source says latent only |
| Plain English enforcement | High | Approved verbs, forbidden words, sentence length limits |

---

## 5. Workflow steps

```
STEP 1 — SCOPE INPUT (2-5 min)
Write or paste a project scope description (100-300 words).
Include: location, building type, access method, work items,
trade coordination, asbestos status, principal contractor.
Select job_type: remedial | fit_out | demolition | maintenance | new_build | civil

STEP 2 — GENERATE (1-2 min, automated)
System runs 4-agent pipeline + deterministic post-processing.
Output: JSON task data + inference matrix.

STEP 3 — VALIDATOR CHECK (automated)
System runs 27 issue gate checks.
Review any FAIL or REVIEW items.
If FAIL: assess whether it's a real defect or a generation edge case.

STEP 4 — CONSULTANT REVIEW (10-20 min)
Use the quick-scan checklist above.
Focus on: monitoring, responsibility, HRCW, hold points, SWT.
Insert site-specific names and verify method credibility.

STEP 5 — RENDER TO DOCX (automated)
System renders to the Safe Method SWMS template.
Issue gate runs on the rendered docx as a final check.

STEP 6 — FINAL SIGN-OFF (2-5 min)
Consultant signs as competent person.
Record version and issue date.
Issue to site.
```

**Expected total time: 15-30 minutes per SWMS** including scope input and consultant review.

---

## 6. When to escalate to a WHS specialist

Escalate if any of the following apply:

- **Asbestos as active removal scope** — requires licensed assessor and removal plan, not just latent-condition handling
- **Confined space entry** — requires specific rescue plan and atmospheric testing beyond what the system generates
- **Live electrical work** — requires specific isolation procedures and verification
- **Crane lifts over occupied areas** — requires specific exclusion and lift planning beyond standard controls
- **Demolition of load-bearing structure** — requires structural engineer involvement and specific demolition method
- **Work near rail corridors or active traffic** — requires traffic management plans and specific authority coordination
- **Multi-trade interface with live services** — requires coordination plan beyond standard fit-out controls
- **Reviewer returns BELOW_WORKING_DRAFT on external review** — the draft needs specialist rework, not just completion

---

## 7. When NOT to use the standard workflow

Do not use Safe Method without deeper specialist review for:

- **Heritage buildings** — may have undocumented structural conditions or materials
- **Work involving radioactive materials or biological hazards** — outside the system's training domain
- **Marine or offshore construction** — different regulatory framework
- **Mining or tunnelling** — WHS (Mines) regulations apply, not general WHS
- **Work in contaminated ground** — requires environmental assessment beyond WHS scope
- **Projects requiring a principal contractor SWMS review engine** — use the SWMS Review Engine product mode instead

---

## 8. Pilot evidence to capture on each job

Record the following for every consultant-assisted pilot job:

| Field | What to record |
|-------|---------------|
| Job ID | Sequential identifier |
| Scope summary | One-line description of the work |
| Job type | remedial / fit_out / demolition / maintenance / new_build / civil |
| Time: scope input | Minutes to write or paste the scope |
| Time: consultant review | Minutes spent reviewing and editing the draft |
| Time: total | Scope input to issued document |
| Validator result | PASS_INTERNAL / RETRY_INTERNAL / ESCALATE_EXTERNAL |
| Validator fail count | Number of FAIL checks |
| Issue gate result (docx) | FAIL count and REVIEW count on rendered output |
| Main consultant edits | Brief list of what the consultant changed (monitoring, names, HRCW, sequence) |
| Would consultant issue? | Yes / Yes with minor edits / No — needs rewrite |
| External review needed? | Yes / No — and reason if yes |
| Defects found | Any defects not caught by the system |
| Classification | deterministic_fix / prompt_fix / model_limit / consultant_completion |

### Success threshold for the pilot

The consultant-assisted pilot succeeds if:
- Consultant would issue (with minor edits) on at least 4 of 5 jobs
- Average total time is under 30 minutes per SWMS
- No job requires a full rewrite
- No dangerous-if-followed sequences are generated

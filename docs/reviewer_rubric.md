# Aussie WHS Reviewer Rubric

Human-readable specification for SWMS benchmark review classification.
Runtime thresholds are mirrored as code constants in `core/reviewer_agent.py`.
**Do not parse this file programmatically.**

---

## Purpose

This rubric defines how a generated SWMS draft is classified after internal validation and/or external consultant review. It aligns with the defect taxonomy in `docs/HEADLESS_BENCHMARK_RUNBOOK.md` and the multi-agent roles in `docs/MULTI_AGENT_OPERATING_SYSTEM.md`.

---

## Classification Thresholds

### BENCHMARK_QUALITY_CONFIRMED
Source-faithful task map. HRCW coherent with actual task wording. CCVS verifies dominant controls for every live task. No visible unsupported drift. Believable work sequence. Only minor drafting polish remaining.

### BENCHMARK_QUALITY_WITH_CAVEATS
All of the above except one narrow non-structural gap remains. The gap must be named explicitly. Acceptable for consultant handoff with the caveat noted.

### STRONG_WORKING_DRAFT
Broad sequence correct. Main hazards identified. Some controls need tightening. Some CCVS cleanup needed. Usable after consultant completion.

### BELOW_STRONG_WORKING_DRAFT
Material unsupported drift. Wrong control family across multiple tasks. Or wrong sequence affecting safety logic. Needs substantive rewrite, not just completion.

---

## Single Defects That Stop Confirmation

Regardless of overall quality, these defects prevent BENCHMARK_QUALITY_CONFIRMED:
- Systematic CCVS / dominant-control mismatch across the document
- Uncontrolled structural stability implied (e.g. no temporary works framework for CLT)
- Uncertain live electrical exposure (e.g. no isolation/exclusion for overhead lines)
- False confidence in HRCW on high-risk work (e.g. HRCW says NO for work that clearly triggers Schedule 3)

---

## Three-Layer Rule Classification

### Layer 1 — Hard automation
Deterministic checks that can be run without human judgment. Implemented in `src/issue_gate.py` checks 1-20.

Examples: CCVS completeness, unsupported control keyword scan, WAH percentage, filler control detection, footer/version consistency.

### Layer 2 — Flag for review
Checks that identify a potential issue but require human confirmation. Implemented as REVIEW results in the issue gate.

Examples: HRCW undercall flag, WAH dominance extended, latent condition packaging, framework control misuse in borderline cases.

### Layer 3 — Human judgment only
Assessments that cannot be automated. Require consultant or operator review.

Examples: Whether the document "reads like a practitioner wrote it", whether controls are proportionate to actual site risk, whether the task sequence is believable for this specific site, whether the scope-to-task translation captures the intent.

---

## Dominant Control Family Reference Table

| Task type | Expected dominant family | WAH-only evidence = flag |
|-----------|------------------------|--------------------------|
| Demolition / removal / strip-out | SIL (dust/silica) | Yes |
| Crack repair / slab repair / substrate prep | SIL + STRUCT | Yes |
| Waterproofing / membrane / sealant | CHM (chemical) | Yes |
| Coating / painting | CHM | Yes |
| CLT erection / panel lift / temporary bracing | TEMP_WORKS | Yes |
| Crane setup | LIFT | Yes |
| EWP roof access | WAH | No (correct) |

---

## Job-Type Mandatory Steps

### Remedial
- Removal/demolition before waterproofing
- Substrate hold point before membrane or tile reinstatement
- Occupied-site interface as framework control
- Correct dominant control family in CCVS for demolition and chemistry tasks

### CLT and Crane Sub-Pattern
- Engineer-led erection sequence
- Crane lift setup and exclusion
- Temporary bracing/prop discipline
- Permanent connection before release logic

### EWP Roof Access
- Plant setup and inspection before use
- Transfer method named explicitly
- Rescue plan referenced

### Occupied Residential Remedial
- Occupied-site interface as standalone framework control
- Resident exclusion zone logic
- Emergency arrangements for occupied building

---

## Trust-Killer Checklist

Controls or patterns that immediately reduce consultant trust:
- Road/traffic boilerplate on a residential site with no road work
- Demolition licence requirements on a non-demolition job
- Active asbestos management on a latent-condition-only scope
- Council after-hours permits without source support
- Generic "ensure compliance with all relevant regulations"

---

## Filler Control Phrase Blacklist

These phrases add no value as standalone controls:
- follow swms
- use ppe as required
- supervisor to monitor
- complete permit before work
- take care when carrying out task
- ensure area is safe
- ensure compliance with all relevant regulations
- maintain situational awareness

---

## Unsupported Admin Keyword List

These admin/governance controls are flagged unless explicitly supported by the source:
- council permit / council approval
- epa notification
- demolition supervisor
- utility disconnection certificate
- nata certificate
- owners corporation / by-law / special resolution
- asbestos clearance

---

## Automation Boundary

### Automatable by rule (Layer 1)
- CCVS completeness and alignment
- Unsupported keyword scan
- Filler control detection
- WAH percentage
- Footer/version consistency
- Job-type mandatory step presence

### Flaggable — human confirms (Layer 2)
- HRCW undercall
- WAH dominance
- Framework control misuse
- Dominant control family mismatch (single instance)

### Human only (Layer 3)
- Practitioner credibility assessment
- Proportionality of controls to site risk
- Source-to-task translation quality
- Believability of work sequence for this specific site

---

## Note

This document is the human-readable specification. Runtime thresholds are mirrored as code constants in `core/reviewer_agent.py`. Do not parse this file programmatically.

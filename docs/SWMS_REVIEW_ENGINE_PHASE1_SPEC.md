# Safe Method SWMS Review Engine
**Phase 1 Implementation Specification**
Version: 2026-03-28

---

## Purpose

This spec defines the first implementation phase for the Safe Method SWMS Review Engine.

Phase 1 goal:

**ingest a principal-contractor project risk register and a subcontractor SWMS, then produce a structured gap report for human review**

---

## Phase 1 Scope

Included:
- project risk register intake
- SWMS intake
- normalisation of project risk requirements
- parsing of SWMS content
- structured comparison
- review report / gap report

Excluded:
- automatic approval
- Procore API integration
- notification automation
- workflow orchestration
- final approval state machine
- broad multi-format import support

---

## Primary Inputs

### 1. Project risk register

Phase 1 source:
- `.xlsx`

Expected contents:
- project risk items
- hazard descriptions
- required controls
- required hold points if present
- HRCW expectations if present

### 2. Subcontractor SWMS

Phase 1 source:
- `.docx`

Preferred initial support:
- Safe Method-generated SWMS
- then selected third-party SWMS formats later

---

## Phase 1 Output

One structured review result with:
- aligned items
- partially aligned items
- missing hazards
- weaker or missing controls
- missing or weaker hold points
- HRCW expectation mismatches
- open items / human review notes
- overall recommendation

Recommendation states:
- `ALIGNED_FOR_REVIEW`
- `REVISION_REQUIRED`
- `INSUFFICIENT_INFORMATION`

---

## Core Comparison Logic

### 1. Normalise project risk register

Convert source risk register into a stable internal schema such as:
- risk id
- hazard family
- project hazard description
- required controls
- required hold points
- HRCW relevance
- confidence / scope notes

### 2. Parse SWMS

Extract:
- task list
- hazards by task
- controls by task
- hold points / stop-work triggers
- HRCW selections

### 3. Compare

For each project risk item:
- is the hazard represented?
- are required controls represented?
- are hold points represented?
- is HRCW aligned?
- is the SWMS weaker than the project expectation?

### 4. Summarise

Produce:
- alignment summary
- gap list
- plain-English review note

---

## Required Internal Schema

Phase 1 should define or preserve these explicit contracts:

### Project risk register schema
- project metadata
- risk items
- hazard family
- control requirements
- hold point requirements
- HRCW expectations

### SWMS review schema
- task entries
- hazard mapping
- control mapping
- hold point mapping
- HRCW mapping

### Comparison result schema
- aligned
- partial
- missing
- weaker_than_required
- open_items
- recommendation

---

## Benchmarking Requirement

This product mode must be benchmark-led from the beginning.

At minimum, Phase 1 should have:
- one benchmark PC risk register
- one benchmark subcontractor SWMS
- one expected gap-report outcome

This should follow the existing Safe Method benchmark/governance pattern.

---

## Quality Rules

### Must do
- preserve human approval as final decision
- preserve visible uncertainty
- distinguish missing information from true misalignment
- prefer project-specific comparison over generic compliance language

### Must not do
- imply automatic approval
- silently invent project requirements
- overstate alignment certainty
- collapse distinct risk requirements into vague summaries

---

## Suggested Delivery Order

### Step 1
Create input schema for project risk register intake.

### Step 2
Create parsing/normalisation for Phase 1 `.xlsx` risk register.

### Step 3
Create SWMS review schema for comparison.

### Step 4
Create comparison engine.

### Step 5
Create structured gap-report output.

### Step 6
Create one benchmark test case and expected result.

---

## What Success Looks Like

Phase 1 is successful when:
- a project risk register can be ingested cleanly
- a SWMS can be parsed into a stable review shape
- the engine can identify aligned vs missing vs weaker items
- the result is useful to a principal contractor reviewer
- the output is honest about uncertainty

---

## What Still Remains After Phase 1

Deferred to later phases:
- Procore-native integration
- versioned review/resubmission workflow
- notifications
- user-facing approval dashboard
- configurable approval thresholds
- broader third-party SWMS compatibility

---

## Recommended Next Step

After this spec:
- decide whether this mode becomes an active benchmark stream
- choose one benchmark project risk register and one SWMS example
- implement the narrowest comparison engine first

---

## Related Documents

- [SWMS_REVIEW_ENGINE_CONCEPT.md](C:\Users\AlanRichardson\gatekeeper\docs\SWMS_REVIEW_ENGINE_CONCEPT.md)
- [PRODUCT_DECISION_MEMO.md](C:\Users\AlanRichardson\gatekeeper\docs\PRODUCT_DECISION_MEMO.md)
- [BENCHMARK_GOVERNANCE_REGISTER.md](C:\Users\AlanRichardson\gatekeeper\docs\BENCHMARK_GOVERNANCE_REGISTER.md)


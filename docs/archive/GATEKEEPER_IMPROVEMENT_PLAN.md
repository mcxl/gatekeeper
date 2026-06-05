# GATEKEEPER IMPROVEMENT PLAN
# Safe Method SWMS + Risk Assessment Platform
# Version: 2026-03-28 | Supersedes prior plan versions

---

## CURRENT TRUTH

Gatekeeper / Safe Method is no longer in early capability-discovery mode.
It now has:
- a benchmark-proven SWMS path
- a benchmark-proven standalone RA path
- a defined combined WHS control pack mode with a materially closed Withers Road benchmark stream
- a defined SWMS Review Engine mode with benchmark setup and comparison contract written
- a stabilised post-Phase-2 product baseline
- an explicit quality-system and multi-agent operating layer

The current product reality is:
- standalone SWMS is a live product path
- standalone RA is a live product path
- review-before-download is now part of the trust workflow
- the combined WHS control pack is a separate product mode, not an extension of the current RA renderer
- the SWMS Review Engine is a separate review/comparison mode and is not yet active until first benchmark assets are selected
- SDK / integration packaging is a future phase that depends on stable contracts, product boundaries, regression discipline, and quality automation

Guiding principles:
- reliability and document trust come before expansion
- benchmark-led improvement comes before broad rewrites
- one strict template/render contract per document type
- contract clarity comes before external packaging
- architectural gaps should trigger product decisions, not endless incremental slices

---

## WHAT IS NOW PROVEN

### Benchmark methodology
The layered benchmark method is now proven across multiple output types:
- RA benchmark - data centre retrofit
- SWMS benchmark - facade remedial works
- SWMS benchmark - EWP roof transfer specialist case
- RA benchmark - civil infrastructure / sparse input / Withers Road
- Project WHS benchmark / control pack - Withers Road

What this proves:
- scope classification materially improves output relevance
- confidence / conditional handling is correct for sparse input
- deterministic post-processing injection is a valid pattern for specialist control gaps
- benchmarks can reveal product-boundary problems, not just logic problems

### Stable foundations
The following are now stable enough to treat as the baseline:
- SWMS renderer contract (V10 template and table mapping)
- RA renderer structure
- inference matrix base categories plus retrofit and civil expansions
- reference job baseline and SWMS reference set
- post-Phase-2 code hygiene and review integration changes
- quality-system governance docs
- multi-agent operating docs and runbook

### Phase 2 close-out complete
Phase 2 work is complete:
- code hygiene completed
- Mode 04 -> review integration completed
- landing stabilisation completed
- combined WHS control pack specification written
- benchmark governance and decision-log structure written

---

## RELEASE GATE

A release is not clean unless these flows pass.

### Core release checklist

| Flow | Steps | Pass condition |
|------|-------|---------------|
| 1. Quick Start SWMS | Describe job -> generate -> review -> confirm -> download | Document downloads, task sequence correct, no contradictory status states |
| 2. Upload Document SWMS | Upload scope/source file -> extract -> review -> generate -> download | Extraction fields populate, generation completes, real errors shown on failure |
| 3. Upgrade SWMS | Upload existing SWMS -> analyse gaps -> generate -> download | Gaps identified, new SWMS generated |
| 4. API key auth | POST `/v1/generate/stream` with `X-API-Key` | SSE streams correctly, 200 OK |
| 5. SWMS sequencing | Generate tilt-up or equivalent complex job | Task ordering and major controls remain correct |
| 6. Standalone RA | Dashboard -> `/ra` -> generate -> render -> download | RA flow loads, hazards render, file downloads correctly |
| 7. Failure transparency | Trigger one known failure in extract/render/generate | User sees a meaningful message, not a mystery failure |
| 8. Review workflow | Generate through Mode 04 -> review -> download | User can review before downloading and flow remains coherent |

### Regression discipline

Benchmark/reference coverage is now part of the product discipline.

Required expectations:
- preserve RA reference jobs
- preserve SWMS reference jobs
- use benchmark cases as release gates where practical
- do not remove benchmark coverage without replacing it
- after architecture or cleanup changes, rerun affected smoke/reference jobs

---

## CURRENT PRODUCT BOUNDARIES

### 1. Standalone SWMS
Purpose:
- trade/task-level work method output

### 2. Standalone Risk Assessment
Purpose:
- project-level risk assessment output

### 3. Combined WHS Control Pack
Purpose:
- multi-section project-level control document combining linked control artefacts

Rule:
- this is a separate product mode, not a renderer extension hidden inside standalone RA

---

## PHASE 3 GOAL

Phase 3 moves Safe Method from stabilised benchmark-proven products into:
- deterministic quality automation
- product-boundary decisions
- contract definition
- integration readiness
- architecture shaping for future product modes

Phase 3 should be a deliberate transition from working behavior to explicit contracts, stable release discipline, and supportable packaging surfaces.

---

## PHASE 3 PRIORITIES

### Priority 1 - Deterministic quality automation
Build the first internal automation layer around:
- issue-gate checks
- benchmark regression checks

Expected outcome:
- obvious trust failures caught before consultant-style review
- closed benchmark streams protected from regression
- active benchmark streams evaluated more consistently

### Priority 2 - Stable contracts
Define and preserve explicitly:
- input schema
- output schema
- review schema
- benchmark/result schema

### Priority 3 - Regression and release discipline hardening
Expand practical release confidence by:
- preserving RA and SWMS reference jobs
- adding any remaining critical smoke coverage
- tightening benchmark-based release rules

### Priority 4 - Product decision on the control pack mode
Treat the combined WHS control pack as a separate product mode with a proven benchmark draft stream.

### Priority 5 - SWMS Review Engine benchmark activation
Before implementation, activate the first benchmark pair for the SWMS Review Engine:
- one principal-contractor project risk register
- one subcontractor SWMS
- one benchmark expectation note

Expected outcome:
- stream moves from HOLD to ACTIVE
- first comparison benchmark can run

### Priority 6 - Architecture readiness
Focus areas:
- classifier growth boundaries
- inference matrix scaling discipline
- post-processing injection structure
- renderer branching by product mode

### Priority 7 - Integration surface decision
Do not expose a broad SDK yet.
Choose the first supported integration surface deliberately.

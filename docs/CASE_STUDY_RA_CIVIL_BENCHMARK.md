# Case Study: RA Benchmark — Civil Infrastructure (Withers Road)

## Benchmark Case

**Prompt (Level 1 — sparse early-stage input)**: "Partial upgrade of Withers Road, North Kellyville NSW — approximately 400 metres of live lane road works, Sydney Water asset relocation, conversion from chip seal to 4 lanes, T-intersection with traffic lights, pedestrian walkways, and stormwater works"

**Benchmark document**: SD Group Withers Road WHS Control Document Rev01 — a project-level control pack containing HRCW register, SWMS matrix, hold point schedule, and risk register across 8 trade packages.

**Why this case**: Tests how the system handles sparse civil infrastructure input — a LinkedIn-level description with no detailed scope documents. The benchmark document represents what a competent person would produce with full project knowledge. The gap between Level 1 input and the benchmark measures the system's honesty about what it can and cannot infer.

## What Changed

| Slice | Change | Files |
|-------|--------|-------|
| **Civil matrix** | 9 new MATRIX entries for road corridor, trenching, utility relocation (water + gas), traffic signals, mobile plant, stormwater, pedestrian, pavement/silica | `inference_matrix.py` |
| **Civil classifiers** | `civil_infrastructure` job type + 7 scope modifiers (road_corridor, live_lanes, utility_relocation, stormwater, traffic_signals, pedestrian_interface, civil_infrastructure) in both RA and SWMS classifiers | `inference_matrix.py` |
| **Synonym/chain expansion** | road upgrade → road works, chip seal → pavement, t-intersection → intersection; road works chains to live lane + mobile plant + pavement + pedestrian | `inference_matrix.py` |
| **Civil hold points** | 6 project-specific hold points: traffic management acceptance, service proving, trench inspection, Sydney Water hold points, compaction testing, traffic signal commissioning | `ra_renderer.py` |
| **Conditional HRCW** | Tri-state HRCW register (YES/CONDITIONAL/NO) for all 17 Schedule 1 categories with conditional triggers per category | `inference_matrix.py`, `ra_renderer.py` |

## Before/After

| Dimension | Before | After |
|-----------|--------|-------|
| Classification | `upgrade`, no modifiers | `civil_infrastructure`, 7 modifiers |
| Hazard count | 4 generic | 15 civil-relevant |
| HRCW flags | 1 (traffic_corridor) | 3 YES + 7 CONDITIONAL |
| HRCW register | Binary (flag on/off) | YES / CONDITIONAL / NO with reasons |
| Hold points | 2 generic (induction, SWMS sign-off) | 8 (6 project-specific + 2 standard) |
| Benchmark HRCW match | 1/17 | 15/17 exact, 2/17 acceptable (CONDITIONAL vs YES for unstated gas/electrical) |

### HRCW Register Comparison

| Category | Benchmark | Safe Method | Assessment |
|----------|-----------|-------------|------------|
| H01 Falling >2m | YES (conditional) | CONDITIONAL | Correct — falls into trenches not confirmed |
| H04 Asbestos | CONDITIONAL | CONDITIONAL | Exact match |
| H05 Structural alterations | CONDITIONAL | CONDITIONAL | Exact match |
| H06 Confined space | CONDITIONAL | CONDITIONAL | Exact match |
| H07 Shaft/trench >1.5m | YES | YES | Exact match |
| H09 Pressurised gas | YES | CONDITIONAL | Acceptable — gas not stated in description |
| H11 Energised electrical | YES | CONDITIONAL | Acceptable — traffic signals stated, energised work implied |
| H12 Contaminated atmosphere | CONDITIONAL | CONDITIONAL | Exact match |
| H14 Traffic corridor | YES | YES | Exact match |
| H15 Powered mobile plant | YES | YES | Exact match |
| All NOs | NO | NO | All match |

## Remaining Deferred Items

| Item | Severity | Notes |
|------|----------|-------|
| H09 gas is CONDITIONAL not YES | Low | Gas mains not stated in Level 1 input — correct honesty; would upgrade to YES with richer input |
| H11 electrical is CONDITIONAL not YES | Low | Traffic signals stated but energised work not explicit — correct for Level 1 |
| Phase grouping wrong for civil | Low | All hazards in "Installation and fit-out" — civil needs trade-package phases, not building phases |
| No HRCW register table in rendered output | Medium | HRCW register exists as data but not as a formal rendered table |
| No SWMS matrix by trade package | Medium | Benchmark maps 10 SWMS packages — RA doesn't produce this |
| No risk register grouped by activity | Medium | Benchmark has 30 entries across 8 groups — RA has 15 flat hazards |
| Info-required wording still generic for civil | Low | Civil hazards get "confirm scope details" not specific civil questions |

## Key Lesson

**The standalone RA is the wrong product shape for project-level civil infrastructure.**

The Withers Road benchmark document is not a standalone risk assessment — it's a combined WHS control pack containing four linked deliverables: HRCW register, SWMS matrix, hold point schedule, and risk register. The standalone RA can produce the right hazards, the right HRCW assessment, and the right hold points, but it cannot produce the trade-package structure, the SWMS matrix, or the activity-grouped risk register that a civil infrastructure project requires.

This is not a deficiency in the RA pipeline. It is evidence that civil infrastructure projects need a **separate product mode** — the combined WHS control pack described in `docs/archive/GATEKEEPER_IMPROVEMENT_PLAN.md`.

The benchmark-led methodology successfully identified this boundary:
1. The first slice (matrix content) showed the content gap
2. The hold-point slice showed the logic gap
3. The conditional HRCW slice showed the assessment-discipline gap
4. Each slice brought the RA closer to the benchmark — but the remaining gaps are structural, not content

**The next step is not another RA slice. It is a product decision about whether and when to build the combined WHS control pack mode.**

## Evidence for Product Mode Decision

This benchmark provides concrete evidence for the combined control pack:

1. **The data is available** — classification, HRCW register, hazard families, hold points, and conditional flagging are all in the RA pipeline now
2. **The structure is missing** — the renderer produces a single-document RA, not a multi-section control pack
3. **The benchmark document exists** — SD Group Withers Road Rev01 is the target output shape
4. **The gap is architectural, not incremental** — no amount of RA slices will produce a SWMS matrix or trade-package risk register

Recommendation: park this as input to the combined control pack product specification. Do not attempt to force the standalone RA into a control-pack shape.

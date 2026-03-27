# Case Study: RA Benchmark — Data Centre Retrofit

## Benchmark Case

**Prompt**: "Installing a data centre into an existing industrial warehouse (concrete tilt-up construction) in NSW"

**Why this case**: It tests scope interpretation, not just hazard matching. The system must distinguish retrofit/fit-out work inside an existing building from new-build construction — a distinction that generic AI hazard generation consistently fails.

## Original Output Weaknesses

Before this work, the RA pipeline produced:

1. **False hazards from context**: "tilt-up" in the description triggered tilt-up erection, crane operations, rigging, and WAH — all wrong for a fit-out inside an existing tilt-up building
2. **No scope interpretation**: no distinction between new-build and retrofit
3. **SWMS-style controls**: engineering controls were regulatory citations ("WHS Reg 2017 s.164") not practical site actions
4. **Flat structure**: no phase grouping, no assumptions, no hold points, no SWMS triggers, no information-required section
5. **Over-assertion**: all hazards presented as definite regardless of whether the scope actually implied them
6. **Polluted legislation**: 55+ regulatory notes including irrelevant tilt-up, crane, and rigging standards
7. **Raw keyword names**: hazard labels like "Ups " and "Hvac" instead of professional titles

## Benchmark Characteristics

The benchmark consultant-style RA:

1. Treats the job as retrofit/fit-out, not new build
2. Separates risks into phases: existing building, installation, live services, interface
3. Only includes hazards genuinely triggered by the scope
4. Uses "if applicable / confirm on site" for uncertain items
5. Does not over-call HRCW just because the building is tilt-up
6. Produces assumptions, pre-start hold points, SWMS triggers, and information-still-required sections

## Implementation Summary

| Slice | What | Impact |
|-------|------|--------|
| **1** | Job-type classifier (fit_out/retrofit/new_build + building_context + scope_modifiers) | Stopped treating existing tilt-up as new-build scope |
| **2** | Confidence field (confirmed/likely/if_applicable/requires_verification) | Uncertain hazards no longer asserted as definite |
| **2.5** | Chain expansion suppression for context-only terms | Eliminated false WAH, rigging, crane from "tilt-up" context |
| **2.5B** | 8 new retrofit/fit-out matrix categories + data-centre chain expansion | Replaced generic baseline with relevant fit-out hazards |
| **2.6** | Chain-derived hazards cannot be "confirmed" | Energised electrical correctly downgraded to "likely" |
| **3** | Phase grouping (existing building / installation / live services / interface) | Consultant-readable structure |
| **4** | RA control language overrides for 9 hazard families | Practical site controls instead of compliance fragments |
| **5** | 4 new renderer sections (assumptions, hold points, SWMS triggers, info required) | Complete consultant-style RA structure |
| **Polish 1** | Filtered legislation + RA display names | Clean document, professional hazard titles |
| **Polish 2** | Specific info-required questions + contextual project description | Targeted unresolved-question phrasing |
| **Polish 3** | Duplicate SWMS trigger removed + WAH conditional qualifier | Clean section 8 |

## Before/After Summary

| Dimension | Before | After |
|-----------|--------|-------|
| Hazard count | 2 (false WAH + rigging) | 8 (all relevant to fit-out) |
| False positives | Tilt-up erection, crane, rigging, WAH | None |
| Hazard names | "Ups ", "Hvac" | "UPS / Battery Installation", "HVAC / Cooling Systems" |
| Controls | "WHS Reg 2017 s.164" | "Test-before-touch — verify de-energised before work" |
| Document sections | 6 (cover through review) | 10 (+ assumptions, hold points, SWMS triggers, info required) |
| Legislation items | 55+ (including irrelevant) | 25 (all fit-out relevant) |
| Confidence | All asserted as definite | Honest: confirmed/likely/if_applicable/requires_verification |
| Project description | Repeated project name | Contextual: "Fit-out within existing industrial warehouse" |

## Deferred Cosmetic Items

1. Section 3 mixes legislation references with practical notes — structural separation would help
2. Phase subheadings not yet rendered in hazard register table — data is grouped but table is flat
3. "Work at Height" SWMS trigger could be more specific about which elevated tasks apply
4. Hazard register table could show confidence badges alongside hazard names

None are material defects. All can be addressed in a later polish pass.

## Key Lesson

**Benchmark first, then implement in layers.**

The original RA pipeline was a thin wrapper on the SWMS inference matrix. Attempting to fix it without a reference example would have led to guesswork. Starting with a strong benchmark case made every problem concrete and every fix verifiable.

The slice-by-slice approach worked because:
- Each slice addressed one specific weakness
- Each slice was tested against the benchmark before the next
- No slice required backtracking on a previous one
- The final output matched the benchmark intent without a single broad rewrite

This method should be applied to every document type: define the benchmark, measure the gap, fix one layer at a time, retest.

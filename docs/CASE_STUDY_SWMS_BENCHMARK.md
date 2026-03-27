# Case Study: SWMS Benchmark — Facade Remedial Works

## Benchmark Case

**Prompt**: "External facade remedial works to a 12-storey occupied residential strata building in Sydney — scaffold access, concrete spalling repair, protective coating application, balcony waterproofing"

**Why this case**: Tests multi-trade task sequencing, scaffold access handling, occupied-building interface, WAH proportionality, and whether the system frames remedial work correctly rather than treating it as new-build construction.

## Original Output Weaknesses

Before this work, the SWMS pipeline had these defects for this case:

1. **Scaffold task failed generation**: Agent 3 (control writer) exceeded the 8-control hard limit for scaffold erection → ValueError → Agent 4 crashed on empty fallback → blank task in output. The most critical access task was missing.
2. **WAH inconsistent**: Some elevated facade tasks had WAH, others didn't — depended on which CCVS code the control writer happened to assign. No deterministic rule.
3. **No scope classification**: Agents received raw description text with no structured context about job type, building context, or occupancy. Good occupied-building content appeared by LLM luck, not by design.
4. **No occupied-building controls by design**: Hazards mentioned occupants but no structured notification, work-hours, or balcony barricade controls were injected.
5. **PPE double-prefix artefacts**: Output contained "steel-capped footwear— steel-capped" formatting bugs.

## Benchmark Characteristics

A consultant-quality SWMS for this case should:

1. Sequence tasks correctly: mobilise → scaffold → inspect → repair → coat → waterproof → inspect → dismantle → demobilise
2. Treat scaffold as access infrastructure with its own erect/dismantle tasks
3. Apply WAH to all tasks performed from scaffold, exclude ground-level tasks
4. Include occupied-building controls: resident notification, work-hours, balcony barricade
5. Generate specific controls per trade (silica dust for grinding, vapour controls for coating, cure times for waterproofing)
6. Not include irrelevant hazards (no excavation, no crane, no confined space)

## Implementation Summary

| Slice | What | Impact |
|-------|------|--------|
| **1** | Control limit raised 8→12 + Agent 3 failure fallback with valid schema | Scaffold task generates reliably |
| **2** | WAH propagation rule for scaffold-access tasks | Elevated tasks get WAH by design |
| **2.5** | Refined WAH to elevated-execution tasks only | Planning/perimeter/cleanup tasks excluded |
| **3** | SWMS scope classifier + context wired to all 3 agents | Agents know job is remedial/existing/occupied/strata |
| **4** | WAH gap closed for concrete removal/prep + scope to all agents | Surface prep tasks now WAH; risk assessor and control writer receive classification |
| **5** | PPE double-prefix fix + occupied-strata control injection | Clean PPE; notification/barricade controls injected structurally |

## Before/After Summary

| Dimension | Before | After |
|-----------|--------|-------|
| Task completeness | Scaffold task missing (failed generation) | All tasks generate reliably |
| WAH consistency | Agent-dependent (some runs 6/11, some 10/11) | Deterministic: all elevated tasks WAH by rule |
| Scope classification | None — raw description only | remedial / existing / occupied / strata + 10 modifiers |
| Occupied controls | Present as hazards, not as structured controls | Body corporate notification, work-hours, balcony barricade |
| PPE formatting | "steel-capped footwear— steel-capped" | Clean, deduplicated |
| Task sequencing | Correct when scaffold task present | Consistently correct |
| Control specificity | Already good (silica dust, vapour controls, cure times) | Maintained + occupied controls added |

## Deferred Cosmetic Items

1. Surface prep task occasionally gets SIL-M4 instead of WAH-H6 in some runs
2. No general weather hold for all scaffold tasks (only coating has wind/rain)
3. No confidence field on SWMS tasks (RA has this; SWMS does not yet)
4. No phase grouping on SWMS tasks (RA has this; SWMS tasks are flat)

None are material defects. All can be addressed in future work.

## Key Lesson

**Pipeline reliability before methodology.**

The RA benchmark started with false positives and missing sections — a methodology problem. The SWMS benchmark started with a hard pipeline failure — the scaffold task literally couldn't generate. Fixing the reliability defect (control limit + failure fallback) unlocked all subsequent quality improvements. If we had started with scope classification before fixing the pipeline, we would have been classifying an incomplete document.

The slice sequence that worked:
1. Fix the hard failure first (pipeline reliability)
2. Add deterministic design rules (WAH propagation)
3. Then add scope framing (classification to agents)
4. Then add context-aware controls (occupied-building injection)
5. Then fix cosmetic issues (PPE formatting)

This is the same benchmark-led methodology as the RA stream, adapted for a generative (agent-based) pipeline instead of a deterministic (matrix-based) one.

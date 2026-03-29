# Refinement Decision Log
## Per-Cycle LBV Decision Record

---

### 1. Cycle Summary

- **Date:** 2026-03-29
- **Product mode:** SWMS
- **Benchmark stream:** Lingate remedial works
- **Benchmark case:** Remedial works at Lingate House, 409-411 New South Head Road, Double Bay — balcony waterproofing, glass balustrade replacement, render patching, tile replacement, scaffold access
- **Cycle type:** First LBV — baseline establishment

### 2. What Writer Produced

11 tasks, 0 agent failures:
1. Establish site and erect scaffold
2. Remove existing balustrades and prepare surfaces
3. Investigate and repair Suite 7 slab crack
4. Re-waterproof balconies, terrace, and Suite 7 awning
5. Install replacement glass balustrades
6. Isolate services and check for latent hazards
7. Replace ground-floor tiles
8. Remove waste via chute to Kiora Lane truck
9. Treat exposed steel and render patch
10. Check and remediate defects
11. Dismantle scaffold and demobilise

Scope coverage: all quoted items represented (waterproofing, balustrades, slab crack, render, tiles, waste chute).

### 3. Issue-Gate Result

With `allowed_keywords=("waterproof", "membrane")`:

```
FAIL_INTERNAL (9/12 pass, 1 fail, 2 review)
  [OK] access_before_dependents
  [OK] no_coat_reinstate_merge
  [OK] no_prestart_in_demob
  [OK] ccvs_coverage — All 11 tasks monitored
  [OK] ccvs_alignment
  [OK] ccvs_completeness
  [OK] wah_percentage — 45%
  [OK] unsupported_controls (JSON)
  [REV] latent_condition_packaging — standalone latent task
  [FAIL] unsupported_controls (docx) — service isolation
  [REV] responsibility_field — placeholder at benchmark stage
  [OK] footer_version
```

### 4. Issue-Gate Improvements Made

1. **C3 refined:** Removed "resident" and "neighbour" from pre-start keywords — resident notification before scaffold removal is legitimate demob practice on occupied buildings.
2. **C7 made scope-aware:** Added `allowed_keywords` parameter so waterproofing terms aren't flagged on waterproofing jobs.
3. **C7 docx variant:** Also accepts `allowed_keywords`.

### 5. Critic Assessment

**Strengths:** Full scope coverage, logical sequence, occupied-building controls present.
**Main weakness:** Task 1.6 "Isolate services and check for latent hazards" packages two different concerns (service isolation + latent-condition check) into one task. Service isolation for waterproofing is legitimate; latent-condition checking should be a hold-point.
**Secondary:** Some tasks could be more finely split (waterproofing vs awning work merged).

### 6. End-of-Cycle Decision

- **Decision:** FIRST CYCLE COMPLETE — stream baseline established
- **Status:** ACTIVE — has first benchmark output and issue-gate baseline
- **Next target:** Tighten the latent-condition/service-isolation packaging. Compare against the existing RPD SWMS for method-validity gaps.

### 7. One-Line Outcome

First Lingate LBV cycle: 11 tasks, full scope coverage, issue gate 9/12 pass (1 fail on service isolation, 2 reviews). Issue gate refined for scope-aware keyword checking and demob resident notifications. 391 tests.

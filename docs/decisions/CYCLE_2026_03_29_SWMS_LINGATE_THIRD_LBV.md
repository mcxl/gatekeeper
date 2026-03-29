# Refinement Decision Log
## Per-Cycle LBV Decision Record

---

### 1. Cycle Summary

- **Date:** 2026-03-29
- **Product mode:** SWMS
- **Benchmark stream:** Lingate remedial works
- **Cycle type:** Third LBV — prompt enrichment for demolition/removal task generation

### 2. Change Applied

**Decomposer prompt enrichment:** Added two new trade-specific sequence rules to `agents/decomposer.py`:

1. **Remedial waterproofing / balcony / terrace:** site setup → scaffold → remove existing membrane, screed, and tile bed (silica-producing demolition task) → repair substrate → apply new waterproofing membrane → retile/finish → reinstate → demobilisation. Explicit instruction: "ALWAYS include a separate removal/demolition task before waterproofing application."

2. **Remedial painting / facade repairs:** site setup → scaffold → removals and preparation → structural repairs → sealant and coating application → finish coats → reinstatement → defects → demobilisation. "Keep repairs before coatings."

### 3. Result

The decomposer now generates **"Remove existing membranes, screed, and tile beds"** as a dedicated SIL-H6 task (position 3) before waterproofing application (position 6). This closes the critical gap identified in cycle 2.

**Sequence:** Setup → Scaffold → **Remove existing** → Investigate slab → Substrate repair → **Apply waterproofing** → Finishes → Tiling → Demob

**CCVS:** SIL for removal/repair tasks, CHM for application tasks, WAH at 16% (2/12).

### 4. Issue-Gate Result

```
FAIL_INTERNAL (9/12 pass, 1 fail, 2 review) [allowed: waterproof, membrane]
  [OK] access_before_dependents
  [OK] no_coat_reinstate_merge
  [OK] no_prestart_in_demob
  [OK] ccvs_coverage — All 12 tasks monitored
  [FAIL] ccvs_alignment — 3 tasks with monitoring/CCVS mismatch
  [OK] ccvs_completeness
  [OK] wah_percentage — 16%
  [OK] unsupported_controls (JSON)
  [REV] latent_condition_packaging
  [OK] unsupported_controls (docx)
  [REV] responsibility_field — placeholder
  [OK] footer_version
```

CCVS alignment fail is the existing monitoring-evidence pattern (agent sets monitoring text that doesn't match the corrected CCVS code). This is a known issue across all streams.

### 5. End-of-Cycle Decision

- **Decision:** THIRD CYCLE COMPLETE — critical demolition/removal gap closed by prompt enrichment
- **Status:** ACTIVE — 3 LBV cycles. Demolition task now generated. Remaining issues are monitoring-evidence alignment (existing pattern) and latent-condition packaging (known).
- **Reusability:** The prompt rules apply to ALL remedial waterproofing and painting SWMS jobs, not just Lingate.

### 6. Verification

- 391 tests passing, 0 regressions
- 5/5 closed streams pass (175 tests)
- Demolition task confirmed in generated output

### 7. One-Line Outcome

Third Lingate LBV cycle: decomposer prompt enriched with remedial waterproofing and painting sequence rules. Demolition/removal task now generated before waterproofing. Reusable across all remedial SWMS streams. 391 tests.

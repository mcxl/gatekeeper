# Refinement Decision Log
## Per-Cycle LBV Decision Record

---

### 1. Cycle Summary

- **Date:** 2026-03-28
- **Product mode:** Project WHS benchmark
- **Benchmark stream:** Withers Road project WHS benchmark draft
- **Benchmark case:** Withers Road Partial Upgrade (sparse civil input)
- **Cycle owner:** Internal product owner

### 2. Starting State

- **Current status:** ACTIVE
- **Current weakest point:** Risk-register depth, package-to-HRCW mapping, package → RR coverage gaps
- **Reason this cycle was run:** Several confirmed packages had only 1 risk entry; HRCW refs were incomplete for Service Location and Earthworks; benchmark seeding only fired for groups with zero entries

### 3. Evaluation Inputs

- **Generated output reviewed:** Withers Road control pack (current prototype state)
- **Reference / benchmark used:** SD Group Withers Road WHS Control Document Rev01
- **Internal checks run:** Package → RR group → entry count analysis; HRCW ref completeness check
- **Expert review used:** No
- **Reviewer / review source:** Internal diagnostic

### 4. Main Findings

- **Primary finding:** 5 confirmed packages had only 1 RR entry each because benchmark seeding only fired for groups with zero entries
- **Secondary findings:** Service Location missing H15 (mobile plant), Earthworks missing H07 (trench >1.5m)
- **Where trust dropped:** Thin risk register groups looked like the system didn't understand the package scope
- **What remained strong:** Package extraction (13 packages), HRCW register (3 YES + 7 CONDITIONAL), hold points (6), crosswalk linkage

### 5. Finding Classification

- **Reusable rule(s):** Benchmark seeding should fire when group has <2 entries, not just zero — thin groups need standard risks even when inference produced one entry
- **Case-specific fix(es):** Service Location H15, Earthworks H07, Stormwater confined-space entry, Kerb pedestrian management
- **Product decision(s):** None
- **Deferred item(s):** Provisional packages (Asbestos, Confined Space, Gas) have no RR entries — acceptable for conditional items from sparse input

### 6. Refinement Applied

- **Main refinement target:** Benchmark seeding threshold + HRCW mapping completeness
- **Files/functions changed:** `core/control_pack.py`
- **What changed in plain English:** Benchmark risks now seed into groups with fewer than 2 entries (was zero). Added H15 to Service Location, H07 to Earthworks. Added confined-space and pedestrian-management benchmark risks. Fixed duplicate-seeding bug for groups mapped by multiple package keywords.
- **What was intentionally not changed:** Standing hazards group (already 7 entries), provisional package risk coverage

### 7. Re-Evaluation Result

- **Internal result:** REVIEW_INTERNAL (materially improved but not yet at expert-review threshold)
- **Expert re-review used:** No
- **What materially improved:** Risk register depth from 19 to 25 entries. Every confirmed package now has 2+ entries. HRCW mapping complete for all packages.
- **What is still weak:** Controls in benchmark-seeded entries are standard text, not project-specific. Standing hazards group is still a catch-all.

### 8. End-of-Cycle Decision

- **Decision:** Continue and refine
- **Why this decision was made:** The risk register is now structurally adequate (25 entries, 11 groups, every package covered). But the next weakness is control language quality — benchmark-seeded controls are generic standard text, not project-specific. This is a content-quality gap, not a structural gap.
- **Next refinement target:** Control language specificity in benchmark-seeded risk entries — make them more project-specific for the Withers Road scope rather than generic standard text.

### 9. Governance Note

- **Does this change affect product boundaries?** No
- **Does this introduce a reusable quality rule?** Yes — benchmark seeding threshold should be <2 entries, not zero
- **Does regression protection need updating?** No — existing tests cover structural assertions; entry counts are within test ranges

### 10. One-Line Outcome

Withers Road control-pack risk register improved from 19 to 25 entries with benchmark seeding at <2 threshold. Every confirmed package now has 2+ risk entries. Decision: continue and refine (control language quality next).

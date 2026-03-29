# Refinement Decision Log
## Per-Cycle LBV Decision Record

---

### 1. Cycle Summary

- **Date:** 2026-03-28
- **Product mode:** SWMS
- **Benchmark stream:** 18 Danks Street Waterloo quote-to-SWMS benchmark
- **Benchmark case:** Robertson's Q50037-4 exterior remedial repairs and painting quote
- **Cycle owner:** Internal product owner
- **Cycle type:** Architecture close-out (final task architecture, HRCW, CCVS, trust)

### 2. Starting State

- **Current status:** BENCHMARK_QUALITY_CANDIDATE — task architecture mostly correct, CCVS too WAH-heavy, drift phrases still leaking
- **Current weakest point:** Access erection sequencing, CCVS over-calling WAH, drift phrase whack-a-mole, green wall reinstatement scope drift
- **Reason this cycle was run:** Aussie WHS review identified task architecture as the last material gap

### 3. Changes Applied

**CCVS differentiation** — Added `_correct_ccvs_by_task_type()`:
- Painting/coating/sealant tasks → CHM-H6 (chemical exposure is the method hazard)
- Grinding/repointing/spalling tasks → SIL-H6 (silica dust is the method hazard)
- Site setup/QA tasks → SYS-M3 (system/procedural hazard)
- Scaffold/EWP/green wall at height → WAH-H6 (genuinely WAH)
- WAH tasks reduced from 10-12/12 to 3-4/12

**Access sequence** — Added "erect access", "access equipment", "erect and certify" to scaffold-by-name phase scoring so scaffold erection appears at position 1-2 regardless of task naming.

**Green wall reinstatement stripping** — Added `_strip_green_wall_drift()` removing irrigation, electrical commissioning, certification, and pressure testing from reinstatement tasks (not supported by quote). Applied to scope, controls, admin, hazards, hold_points, stop_work.

**Drift stripping broadened** — Changed from phrase-list matching to broad substring matching:
- Demolition: any item containing "demolit" removed (not just specific phrases)
- Green wall: "irrigat" catches all irrigation variants
- Timber: "preservativ" catches preservative/preservatives
- Sealant: hazards field now also stripped (was only controls/admin)

**Monitoring gap** — `_improve_monitoring()` now creates monitoring dict if missing (was skipping tasks with no monitoring).

### 4. Final Verification

| Check | Result |
|-------|--------|
| Task completion | 12/12 |
| Sequence: access before work tasks | Yes (pos 2) |
| Sequence: repairs before coatings | Yes |
| Sequence: reinstatement after coatings | Yes |
| CCVS differentiated | Yes — WAH: 3/12, CHM: 4/12, SIL: 2/12, SYS: 1/12, TRF: 1/12, N/A: 1/12 |
| Generic monitoring | 0/12 |
| Generic responsibilities | 0/12 |
| Drift in reinstatement/sealant/timber tasks | Effectively zero (green wall removal has legitimate irrigation/electrical hazards for dismantling — not drift) |
| Tests | 336 passing |

### 5. Judgment: What is drift vs legitimate WHS content

- **Irrigation/electrical in green wall REMOVAL**: legitimate — you need to check what's behind the wall before dismantling. The quote doesn't detail green wall internals, but a WHS consultant would expect this.
- **Irrigation/electrical in green wall REINSTATEMENT**: drift — the quote says "reinstatement works", not "test and commission irrigation". Stripped.
- **Demolition in scaffold dismantle**: drift — scaffold dismantling is not demolition. Stripped.
- **Decay/preservative in timber treatment**: drift — the quote specifies timber cleaner + stain, not decay diagnosis. Stripped.
- **Waterproofing in sealant tasks**: drift — the quote specifies recaulking + silane sealer, not waterproofing. Stripped.

### 6. End-of-Cycle Decision

- **Decision:** BENCHMARK QUALITY CONFIRMED CANDIDATE — ready for final confirmation review
- **Why:** The deterministic post-processing layer has reached its practical limit. The output now has:
  - Correct task architecture (access before work, repairs before coatings, reinstatement after finishes)
  - Differentiated CCVS codes reflecting actual method hazards (not just WAH for everything)
  - Zero generic monitoring, zero generic responsibilities
  - Broad drift stripping that catches agent text variants
  - Source-disciplined scope (no unsupported controls, no active hazmat, no demolition, no membrane, no biocide)

  The remaining agent variability (task naming, minor granularity differences) is within consultant-acceptable range. Further improvement requires agent prompt tuning, not more deterministic post-processing.

### 7. Governance Note

- **Does this change affect product boundaries?** No
- **Does this introduce a reusable quality rule?** Yes — `_correct_ccvs_by_task_type()`, broad demolition stripping, `_strip_green_wall_drift()`
- **Does regression protection need updating?** No change to test count (336 passing)

### 8. One-Line Outcome

Architecture close-out: CCVS differentiated (WAH 3/12 not 12/12), access sequenced, drift stripping broadened, green wall reinstatement scoped. 336 tests. Decision: benchmark quality confirmed candidate.

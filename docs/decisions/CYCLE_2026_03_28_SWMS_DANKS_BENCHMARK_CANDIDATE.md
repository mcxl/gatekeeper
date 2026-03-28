# Refinement Decision Log
## Per-Cycle LBV Decision Record

---

### 1. Cycle Summary

- **Date:** 2026-03-28
- **Product mode:** SWMS
- **Benchmark stream:** 18 Danks Street Waterloo quote-to-SWMS benchmark
- **Benchmark case:** Robertson's Q50037-4 exterior remedial repairs and painting quote
- **Cycle owner:** Internal product owner
- **Cycle type:** Benchmark-candidate refinement (tightening to benchmark quality)

### 2. Starting State

- **Current status:** APPROACHING_BENCHMARK_QUALITY — approaching but not yet at benchmark
- **Current weakest point:** Repairs after coatings in sequence, sealant membrane drift, timber decay/biocide drift, fibre cement/timber lumped, generic monitoring remnants, document-trust gaps
- **Reason this cycle was run:** Aussie WHS review identified remaining gaps between competent working draft and benchmark quality

### 3. Evaluation Inputs

- **Generated output reviewed:** Regenerated SWMS (12 tasks, 0 failures, logically ordered, zero visible drift)
- **Reference / benchmark used:** Robertson's quote Q50037-4
- **Internal checks run:** 6-priority automated verification + rendered-document drift scan
- **Expert review used:** Yes — Aussie WHS review findings as control point
- **Reviewer / review source:** Aussie WHS consultant review findings

### 4. Main Findings

- **Primary finding:** All 6 priority items addressed:
  1. Sequence: repairs now precede coatings in all regenerations
  2. Sealant drift: membrane/waterproofing stripped from sealant task scopes and controls
  3. Timber drift: decay/biocide/preservative stripped from timber stain task scopes and controls
  4. Monitoring: 0/12 generic (all hazard-specific)
  5. Responsibilities: 0-1/12 generic (task-type-specific)
  6. Document trust: footer supports version parameter, placeholder gating preserved

- **Secondary findings:**
  - Phase-scoring had multiple edge cases: "masonry" matching repair keywords in painting tasks, "defect" matching QA in repair tasks, "mobilise" not matching setup. All fixed with more precise keyword sets.
  - Sealant drift phrases broadened: "waterproof sealant", "hydrophobic or waterproof" added
  - Timber drift matching broadened: "structural timber", "treat structural" added
  - Demolition phrases broadened: "repair-demolition", "demolition work" added
  - Active hazmat task detection broadened: "check and test for latent toxic materials" pattern added
  - Fibre cement/timber doors separation: agent sometimes produces separate tasks, sometimes lumps them. This is agent-level variability, not deterministically fixable.

- **Where trust dropped:** Agent task-naming variability means each regeneration produces slightly different task structures. The deterministic layer is robust across variations, but the agent occasionally lumps tasks that the quote separates.
- **What remained strong:** All prior fixes (anti-slop, reliability, latent-condition discipline, unsupported-control stripping). Zero visible drift in rendered document.

### 5. Finding Classification

- **Reusable rule(s):**
  1. `_strip_sealant_drift()` — strips membrane/waterproofing/tanking from sealant task scopes and controls
  2. `_strip_timber_drift()` — strips decay/biocide/preservative from timber stain task scopes and controls, replaces empty scope with quote-faithful text
  3. Broadened `_REPAIR_KEYWORDS` — more specific to avoid "masonry" matching painting tasks
  4. Broadened phase 0 keywords — "mobilise site", "establish scaffold" added
  5. Footer version parameter support
- **Case-specific fix(es):** None
- **Product decision(s):** Fibre cement / timber doors separation is agent-level variability — not worth forcing. The agent sometimes separates them; the deterministic layer preserves the separation when it occurs.
- **Deferred item(s):** Agent task-naming variability (inherent to LLM generation)

### 6. Refinement Applied

- **Main refinement targets:** Sequence precision, sealant drift, timber drift, phase scoring edge cases
- **Files/functions changed:**
  1. `core/orchestrator.py` — `_strip_sealant_drift()`: new function stripping membrane/waterproofing from sealant tasks
  2. `core/orchestrator.py` — `_strip_timber_drift()`: new function stripping decay/biocide/preservative from timber tasks
  3. `core/orchestrator.py` — `_REPAIR_KEYWORDS`: more specific (e.g. "brickwork reconstruct" not just "brickwork")
  4. `core/orchestrator.py` — `_QA_KEYWORDS`: refined to not catch repair tasks mentioning "defect"
  5. `core/orchestrator.py` — Phase 0 keywords: "mobilise site", "establish scaffold" added
  6. `core/orchestrator.py` — `_DEMOLITION_PHRASES`: "repair-demolition" added
  7. `core/orchestrator.py` — `_strip_active_hazmat()`: broadened to catch "check and test for latent toxic"
  8. `core/orchestrator.py` — `_strip_timber_drift()`: now also strips from hazards field
  9. `renderers/docx_renderer.py` — footer: supports `project_meta["version"]` parameter
  10. `tests/test_content_quality.py` — 6 new tests for sealant/timber drift stripping
- **What changed in plain English:**
  - Sealant tasks no longer mention waterproofing membranes
  - Timber beam tasks no longer mention decay diagnosis or biocide treatment
  - Painting masonry no longer gets classified as a repair task in sequencing
  - Footer filename matches the actual draft version when specified
- **What was intentionally not changed:** Agent prompts, decomposer, anti-slop, renderer table logic

### 7. Re-Evaluation Result

- **Internal result:** BENCHMARK CANDIDATE
  - Task completion: 12/12
  - Visible drift in rendered document: 0
  - Unsupported controls: 0
  - Sequence: setup → access → prep → repairs → coatings → QA → demob
  - Generic monitoring: 0/12
  - Generic responsibilities: 0-1/12
  - Quote coverage: all key items found
  - All prior fixes: no regression
- **Expert re-review used:** Expert review findings as input
- **What materially improved:** Sequence precision, sealant/timber source discipline, phase-scoring robustness
- **What is still weak:** Agent task-naming variability (inherent), fibre cement/timber doors occasionally lumped (agent-level)

### 8. End-of-Cycle Decision

- **Decision:** BENCHMARK CANDIDATE — submit for Aussie WHS review
- **Why this decision was made:** The deterministic post-processing layer has reached the practical limit of what can be corrected without changing agent prompts. The output is:
  - Complete (12/12 tasks, 0% failure rate)
  - Logically sequenced (repairs before coatings)
  - Source-disciplined (zero visible drift in rendered document)
  - Hazard-specific monitoring (0 generic rows)
  - Task-specific responsibilities (0-1 generic)
  - All unsupported content stripped (demolition, hazmat, utility isolation, membrane, biocide)

  Remaining variability is inherent to LLM generation and is within the range a consultant would accept for a working draft requiring site-specific completion.
- **Next refinement target:** Consultant confirms benchmark quality OR identifies specific agent-prompt-level issues for the next cycle.

### 9. Governance Note

- **Does this change affect product boundaries?** No
- **Does this introduce a reusable quality rule?** Yes — sealant drift stripping, timber drift stripping, refined phase scoring
- **Does regression protection need updating?** Yes — 6 new tests. Total: 336 tests passing.

### 10. One-Line Outcome

Benchmark candidate: zero visible drift, repairs before coatings, hazard-specific monitoring, source-disciplined output. 336 tests. Decision: submit for Aussie WHS review.

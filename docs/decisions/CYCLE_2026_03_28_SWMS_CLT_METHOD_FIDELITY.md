# Refinement Decision Log
## Per-Cycle LBV Decision Record

---

### 1. Cycle Summary

- **Date:** 2026-03-28
- **Product mode:** SWMS
- **Benchmark stream:** CLT install and temporary propping drawing-to-SWMS benchmark
- **Benchmark case:** Vincent Rd House — CLT wall panel installation with push-pull props (Stora Enso bracing plan, 23 props, 36 panels)
- **Cycle owner:** Internal product owner

### 2. Starting State

- **Current status:** ACTIVE
- **Current weakest point:** Method fidelity — SWMS does not match actual CLT erection sequence, temporary propping arrangement, or drawing-specific controls
- **Reason this cycle was run:** The SWMS contains road/traffic boilerplate, wrong task sequence, and lacks drawing-specific prop controls

### 3. Evaluation Inputs

- **Generated output reviewed:** SWMS-28032026-V1.docx (10 tasks, temporary support HRCW ticked)
- **Reference / benchmark used:** Stora Enso CLT bracing plan drawing (316-330 CLT bracing plan.jpeg) — 23 push-pull props (10x F5, 13x F3), 36 panels, special base conditions for props #6 and #10
- **Internal checks run:** Task sequence analysis, HRCW validation, boilerplate contamination scan, prop-control traceability check
- **Expert review used:** No
- **Reviewer / review source:** Internal diagnostic against drawing

### 4. Main Findings

- **Primary finding:** Road/traffic boilerplate (road opening permit, traffic management plan, traffic controller, AS 1742.3, Roads Act) present in a residential CLT SWMS. Root cause: the keyword "rop" in the road-opening matrix entry matched as a substring of "prop" in "temporary propping".
- **Secondary findings:**
  - Task sequence is wrong (site setup is task 1.7, should be first; prop base prep is 1.1 before panel erection at 1.9)
  - No drawing-specific controls (F3/F5 prop types, 23 numbered locations, timber bases for #6/#10)
  - No exclusion zone logic for unbraced/partially braced panels
  - No erection sequence aligned to panel numbering
  - HRCW "temporary support for alterations or repairs" — debatable for new-build but defensible
- **Where trust dropped:** Road/traffic boilerplate in a residential site SWMS is an immediate trust-killer. Task sequence disorder makes the document look unreviewed.
- **What remained strong:** Core task content (prop base prep, panel erection, prop install, plumb/stabilise) is directionally correct. Temporary support HRCW is defensible.

### 5. Finding Classification

- **Reusable rule(s):**
  1. Short abbreviation keywords (3 letters or fewer) should be avoided in the inference matrix — they cause false-positive substring matches
  2. Drawing-led SWMS requires the description to include drawing-specific details — the system cannot infer F3/F5 prop types or prop #6/#10 timber bases from a generic scope description
- **Case-specific fix(es):** Removed "rop" from road-opening keywords
- **Product decision(s):** Drawing-specific method controls require richer input description or a separate drawing-annotation extraction step — this is a product-level gap, not an incremental fix
- **Deferred item(s):**
  - Task sequence improvement (agent-dependent — decomposer ordering)
  - Drawing-specific prop controls (requires richer description input)
  - Exclusion zone logic (requires erection-sequence awareness)
  - Panel-numbering traceability (requires drawing extraction)

### 6. Refinement Applied

- **Main refinement target:** False road/traffic boilerplate from keyword substring match
- **Files/functions changed:** `core/inference_matrix.py` — removed "rop" from road-opening MATRIX entry keywords
- **What changed in plain English:** The 3-letter keyword "rop" (road opening permit abbreviation) no longer matches as a substring of "prop" in descriptions. Road/traffic permits, notes, and qualifications no longer appear in non-road SWMS outputs.
- **What was intentionally not changed:** Task sequence (agent-dependent), drawing-specific controls (requires input-quality improvement), HRCW selection (temporary support is defensible for CLT propping)

### 7. Re-Evaluation Result

- **Internal result:** REVIEW_INTERNAL — road boilerplate eliminated. Remaining weaknesses are input-quality and agent-ordering issues, not inference-layer defects.
- **Expert re-review used:** No
- **What materially improved:** Road/traffic contamination completely removed from CLT inference output
- **What is still weak:** Task sequence, drawing-specific controls, exclusion zone logic — all require either richer input or agent-level improvements

### 8. End-of-Cycle Decision

- **Decision:** Continue and refine — but the next improvement requires a **richer input description** that includes drawing-specific details (prop types, quantities, special base conditions), not another inference-layer fix
- **Why this decision was made:** The inference and post-processing layers are now clean for this scope. The remaining gaps are:
  1. Task sequence — decomposer agent ordering (needs prompt improvement or post-processing sort)
  2. Drawing-specific controls — the system needs the description to include "23 push-pull props, F3 and F5 types, special timber bases for props #6 and #10" to generate useful prop controls
  3. Exclusion zones — requires erection-sequence awareness
- **Next refinement target:** Regenerate with a drawing-informed description and evaluate whether task quality improves with richer input

### 9. Governance Note

- **Does this change affect product boundaries?** No
- **Does this introduce a reusable quality rule?** Yes — avoid 3-letter keyword abbreviations in the inference matrix
- **Does regression protection need updating?** No — existing tests pass; the removed keyword was causing false positives

### 10. One-Line Outcome

Removed false road/traffic boilerplate from CLT SWMS caused by "rop" substring match in "propping". Remaining method-fidelity gaps require richer drawing-led input, not inference fixes. Decision: continue and refine with drawing-informed description next cycle.

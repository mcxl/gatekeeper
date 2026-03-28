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
- **Current weakest point:** Control language quality in inference-derived risk register entries — regulatory citations led instead of practical actions
- **Reason this cycle was run:** Prior cycle improved structural coverage (25 entries, 11 groups). The remaining weakness was content quality: inference-derived controls read as legal references, not project controls.

### 3. Evaluation Inputs

- **Generated output reviewed:** Withers Road control pack (post RR-depth cycle)
- **Reference / benchmark used:** SD Group Withers Road WHS Control Document Rev01 control language style
- **Internal checks run:** Control text analysis — identified 8 inference-derived entries leading with regulatory citations
- **Expert review used:** No
- **Reviewer / review source:** Internal diagnostic

### 4. Main Findings

- **Primary finding:** Inference-derived controls led with "WHS Reg 2017...", "AS 1742.3...", "Sydney Water Act..." — the practical action was buried after the citation
- **Secondary findings:** Benchmark-seeded entries already had action-first language — the gap was only in inference-derived entries
- **Where trust dropped:** Controls that read as legal references rather than site actions look like compliance padding, not practical controls
- **What remained strong:** All structural elements (packages, HRCW, hold points, crosswalk, coverage)

### 5. Finding Classification

- **Reusable rule(s):** Control pack risk register controls should lead with the practical action. Regulatory citations belong as trailing references, not leading text.
- **Case-specific fix(es):** None — this applies to all inference-derived entries across project types
- **Product decision(s):** None
- **Deferred item(s):** Standing hazards group controls still have some generic regulatory-first text — acceptable for cross-cutting items

### 6. Refinement Applied

- **Main refinement target:** Control text post-processing in risk register builder
- **Files/functions changed:** `core/control_pack.py` — added `_clean_control_for_register()`
- **What changed in plain English:** When a control sentence starts with a regulation (WHS Reg, AS/NZS, Sydney Water Act, etc.), the regulation is moved to a trailing parenthetical reference and the practical action leads.
- **What was intentionally not changed:** Benchmark-seeded controls (already action-first), standing hazards group, inference matrix notes fields (would affect SWMS/RA)

### 7. Re-Evaluation Result

- **Internal result:** REVIEW_INTERNAL (improved but the standing-hazards group still has some regulatory-first text)
- **Expert re-review used:** No
- **What materially improved:** 8 inference-derived controls now lead with practical actions instead of regulatory citations
- **What is still weak:** Standing hazards group (7 entries) still uses mixed regulatory/action language — lower priority since these are cross-cutting

### 8. End-of-Cycle Decision

- **Decision:** Continue and refine — but the next cycle should target a different weakness. Control language is now materially adequate for the non-standing entries.
- **Why this decision was made:** The structural and content improvements from the last two cycles have brought the Withers Road benchmark draft to a point where the main remaining gaps are: (1) standing hazards language polish, and (2) overall document readability when rendered. These are diminishing-return improvements.
- **Next refinement target:** Consider whether the Withers Road project WHS benchmark stream is approaching its stop rule ("materially strong as a project WHS benchmark draft"). The next cycle should evaluate whether to continue refining or close the stream.

### 9. Governance Note

- **Does this change affect product boundaries?** No
- **Does this introduce a reusable quality rule?** Yes — control pack risk register controls should lead with practical actions, not regulatory citations
- **Does regression protection need updating?** No — test assertions cover structural properties, not exact control text

### 10. One-Line Outcome

Withers Road control-pack inference-derived controls now lead with practical actions, regulatory citations moved to trailing references. Decision: continue and refine, but evaluate stop-rule readiness next cycle.

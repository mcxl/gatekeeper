# Refinement Decision Log
## Per-Cycle LBV Decision Record

---

### 1. Cycle Summary

- **Date:** 2026-03-28
- **Product mode:** SWMS
- **Benchmark stream:** 18 Danks Street Waterloo quote-to-SWMS benchmark
- **Benchmark case:** Robertson's Q50037-4 exterior remedial repairs and painting quote
- **Cycle owner:** Internal product owner

### 2. Starting State

- **Current status:** NEW (first cycle for this benchmark stream)
- **Current weakest point:** Quote-to-scope discipline — system over-inferenced by generating asbestos/lead/hazmat content from exclusion/variation T&C clauses
- **Reason this cycle was run:** Generated SWMS contained a full "Survey and manage hazardous materials presence" task (1.9) with asbestos survey, lead paint testing, and SafeWork NSW notification — none of which are in the contracted scope

### 3. Evaluation Inputs

- **Generated output reviewed:** SWMS-28032026-V1.docx (12 tasks, asbestos HRCW ticked)
- **Reference / benchmark used:** Robertson's quote Q50037-4 (7-page PDF with scope, exclusions, and T&Cs)
- **Internal checks run:** Task-to-quote traceability analysis; HRCW flag validation against confirmed scope
- **Expert review used:** No
- **Reviewer / review source:** Internal diagnostic against quote source text

### 4. Main Findings

- **Primary finding:** Task 1.9 "Survey and manage hazardous materials presence" is entirely unsupported by the quote scope. The quote's T&Cs explicitly say asbestos/lead are latent conditions, excluded from scope, and treated as deemed variations with additional cost. The inference engine triggered on the word "asbestos" in the T&C text.
- **Secondary findings:** Asbestos HRCW flag ticked without scope justification. Task sequence wrong (spalling repair before site setup). Some controls reference asbestos handling procedures that are not part of this job.
- **Where trust dropped:** The presence of an entire asbestos-management task in a painting/repairs SWMS that explicitly excludes asbestos work would cause a consultant to question the entire document.
- **What remained strong:** Core painting and repair tasks are broadly correct. WAH HRCW is justified. Access/scaffold context is appropriate.

### 5. Finding Classification

- **Reusable rule(s):** Keywords appearing in exclusion, variation, latent-condition, or "subject to additional cost" clauses should be suppressed from inference — same as direct negation. This applies to all quote-to-SWMS generation, not just this case.
- **Case-specific fix(es):** Task sequence (spalling before site setup) — decomposer ordering issue specific to this case.
- **Product decision(s):** None
- **Deferred item(s):** Product-specific control language (Fosroc product names, Dulux spec references) — not addressed in this cycle. Task sequence fix — not addressed in this cycle (agent-dependent).

### 6. Refinement Applied

- **Main refinement target:** Exclusion/variation context negation in inference engine
- **Files/functions changed:** `core/inference_matrix.py` — added `_EXCLUSION_CONTEXT_PATTERNS` (13 patterns), extended `_is_negated()` to check 200-char context window around keyword for exclusion patterns
- **What changed in plain English:** When asbestos, lead, or any other keyword appears within 200 characters of phrases like "subject to additional cost", "deemed variation", "latent condition", "excluded from", or "pre-existing toxic", the keyword is suppressed from inference. The inference engine no longer generates asbestos tasks or ticks asbestos HRCW from exclusion/variation T&C text.
- **What was intentionally not changed:** Task sequence ordering (agent-dependent), product-specific control language, SWMS agent prompts

### 7. Re-Evaluation Result

- **Internal result:** REVIEW_INTERNAL — the anti-slop fix addresses the primary finding. The SWMS still needs regeneration and re-evaluation to confirm the full effect.
- **Expert re-review used:** No
- **What materially improved:** Asbestos/lead keywords in exclusion context are now negated. The inference engine will not generate asbestos tasks or HRCW from this quote's T&C text.
- **What is still weak:** Task sequence ordering; product-specific control language; full regeneration needed to confirm end-to-end improvement

### 8. End-of-Cycle Decision

- **Decision:** Continue and refine
- **Why this decision was made:** The anti-slop negation fix is a strong reusable rule that addresses the primary finding. But the SWMS has not been regenerated and re-evaluated yet. The next cycle should regenerate from the Danks Street quote scope (without T&Cs feeding into the inference) and evaluate the resulting task set against the quote scope of works.
- **Next refinement target:** Regenerate and evaluate the Danks Street SWMS with the negation fix in place. Check task sequence, task-to-quote alignment, and whether any other slop remains.

### 9. Governance Note

- **Does this change affect product boundaries?** No
- **Does this introduce a reusable quality rule?** Yes — exclusion/variation context negation is a reusable rule for all quote-to-SWMS generation
- **Does regression protection need updating?** Yes — 9 new negation tests added

### 10. One-Line Outcome

Anti-slop negation fix suppresses asbestos/lead/toxic keywords from exclusion/variation T&C context. Reusable rule added. Decision: continue and refine (regenerate and re-evaluate next cycle).

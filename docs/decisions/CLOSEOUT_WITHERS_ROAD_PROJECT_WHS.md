# Benchmark Close-Out
## Short Record for Closing a Benchmark Stream

---

### 1. Benchmark Identification

- **Date:** 2026-03-28
- **Product mode:** Project WHS benchmark
- **Benchmark stream:** Withers Road project WHS benchmark draft
- **Benchmark case(s):** Withers Road Partial Upgrade (sparse civil input)
- **Owner:** Internal product owner

### 2. Closure Decision

- **Close-out status:** CLOSED
- **Decision type:** Materially satisfied

### 3. Why This Stream Is Closing

- **Main reason:** The benchmark draft is now structurally and content-wise adequate for its intended position as a project WHS benchmark draft. All stop rules from the LBV Flywheel Architecture are satisfied.

- **What is now strong enough:**
  - Package extraction: 13 packages (10 confirmed, 3 provisional)
  - HRCW register: 3 YES + 7 CONDITIONAL + 7 NO with category-specific reasons
  - SWMS matrix: trade packages mapped to HRCW refs with confirmed/provisional status
  - Hold points: 6 structured entries (3 WHS-critical, 3 QA/authority) with conditions, authorisation, and evidence
  - Risk register: 25 entries across 11 groups with action-first controls
  - Package crosswalk: 13/13 packages linked to hold points
  - Open items: 8 items flagged for reviewer confirmation
  - Control language: practical actions lead, regulations as trailing references

- **What is still imperfect but acceptable:**
  - Standing hazards group (7 entries) uses cross-cutting language — acceptable for general hazards
  - Risk register has 12 provisional and 10 benchmark-seeded entries vs 3 confirmed — expected for sparse input
  - Some benchmark-seeded controls are standard text rather than fully project-specific — acceptable for a benchmark draft

- **What remains out of scope or deferred:**
  - Issue-ready output (requires human reviewer confirmation per Quality Governance Note)
  - Full benchmark-document parity with the SD Group Withers Road WHS Control Document Rev01 (30 risk entries, 10 SWMS packages) — the prototype output covers the core structure but is not a 1:1 replica
  - Non-civil benchmark cases (data centre, facade) have not been tested through the control pack path — separate streams if needed

### 4. Quality Position

- **Current quality state:** Benchmark-quality draft
- **Is it issue-ready?** No
- **If not issue-ready, why not:** Issue-ready requires project facts confirmed, open items resolved, evidence and approvals in place, and a responsible human issuer — per the Quality Governance Note. The output is a strong benchmark draft, not an issued document.

### 5. Evidence for Closure

- **Internal checks passed / acceptable:**
  - 125/125 tests pass (54 control-pack specific)
  - 8/8 SWMS reference jobs pass (regression protection)
  - Package extraction covers all benchmark trade packages
  - HRCW register matches benchmark 15/17 categories
  - Hold points match benchmark 6/6
  - Risk register covers all 10 confirmed packages with 2+ entries each

- **Expert review result summary:** Not yet escalated to expert review. Internal evaluation indicates benchmark-draft quality is adequate. Expert review should be triggered through the evaluation plan (docs/COMBINED_WHS_CONTROL_PACK_EVALUATION_PLAN.md) as a separate activity.

- **Latest key benchmark outcome:** 25 risk register entries, 11 groups, action-first control language, 3-tier status visibility (confirmed/provisional/benchmark), 8 open items, full package crosswalk.

### 6. Ongoing Protection

- **Regression protection required:**
  - `tests/test_control_pack.py` (23 tests)
  - `tests/test_control_pack_renderer.py` (20 tests)
  - `tests/test_control_pack_endpoint.py` (11 tests)

- **Benchmark rerun trigger:** Rerun the Withers Road control pack if changes are made to:
  - `core/control_pack.py`
  - `core/inference_matrix.py` (HRCW register or civil categories)
  - `renderers/control_pack_renderer.py`

- **Conditions that would reopen this stream:**
  - Expert/consultant review identifies material structural gaps not visible in internal evaluation
  - New civil benchmark case exposes a regression or gap in the civil package extraction logic
  - Product decision to change the control pack document shape or section structure

### 7. One-Line Close-Out Statement

Withers Road project WHS benchmark stream closed as materially satisfied for benchmark-quality draft output. Maintain by regression tests and reopen only if expert review or new civil benchmark exposes material gaps.

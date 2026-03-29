# Headless Benchmark Refinement Runbook

Standing operating procedure for Safe Method benchmark-led development.

---

## Purpose

This runbook defines how benchmark refinement cycles run in this repo. The goal is to systematically improve SWMS, RA, and control-pack output quality through narrow, verified, governance-tracked cycles — using internal AI-driven comparison where criteria exist and external consultant review as the independent trust check.

---

## Standard Headless Phase Flow

Every work phase follows the same pattern:

1. **Understand** the bounded phase objective (one stream, one weakness)
2. **Do the work** end-to-end within that phase
3. **Verify** the result:
   - Run relevant tests (`python -m pytest tests/ -q`)
   - Run the issue gate (`python src/issue_gate.py <docx> --json <json> --stage benchmark`)
   - Run the regression runner (`python src/regression_runner.py`)
4. **Update governance** if the stream status changed
5. **Local git commit** if the work is coherent
6. **Stop with a clear handoff:**
   - What was completed
   - What was verified
   - What decision was reached
   - Whether governance should be updated
   - Whether a commit was made
   - The exact next prompt to paste

### When to stop
- External review is required
- A material blocker is hit
- A decision has non-obvious consequences
- The current phase is complete and verified
- Diminishing returns reached

### When NOT to stop
- Minor questions that can be resolved by reasonable assumption
- Partial progress (keep going until the phase is complete)
- Cosmetic issues that don't affect the benchmark assessment

---

## Benchmark Loop (One Cycle)

```
Generate → Compare → Gate → Classify → One Narrow Fix → Verify → Governance → Checkpoint
```

### Step by step

1. **Generate:** Regenerate the SWMS output with the current pipeline
2. **Compare:** Compare against the reference/benchmark (existing SWMS, quote, or drawing)
3. **Gate:** Run the issue gate with appropriate stream settings:
   - `--wah-threshold 90` for EWP/crane-dominant streams
   - `allowed_keywords=("waterproof", "membrane")` for waterproofing streams
4. **Classify** each finding:
   - **Deterministic fix** — can be applied in orchestrator/renderer post-processing
   - **Prompt/decomposer fix** — requires agent prompt enrichment
   - **Issue-gate candidate** — should become a new automated check
   - **Case-specific fix** — applies only to this benchmark case
   - **Expert-review-only** — requires consultant judgment
   - **Product-investment gap** — requires new capability (e.g. drawing extraction)
5. **One narrow fix:** Apply only the single most impactful fix set
6. **Verify:** Regenerate + issue gate + regression runner
7. **Governance:** Update register and write decision log
8. **Checkpoint:** Report and provide next prompt

---

## Multi-Agent Pattern

Each benchmark cycle uses the Safe Method multi-agent pattern:

| Role | Job |
|------|-----|
| **Coordinator** | Confirms stream, enforces one weakness per cycle, routes work, stops at decision |
| **Writer** | Generates/regenerates the strongest source-faithful draft |
| **Critic** | Compares output against reference, identifies the single most important gap |
| **Classifier** | Classifies findings by fix type |
| **Fixer/Checker** | Applies narrowest safe fix, reruns verification, notes regressions |

### Rules
- One weakness per cycle
- Critic identifies, Classifier sorts, Fixer implements
- Fixer only implements what Classifier approved
- Checker verifies before committing

---

## Role of External Aussie WHS Review

External consultant review is the **independent trust check**. It is NOT the primary defect-finding mechanism.

### Before sending for external review
- Issue gate must have zero hard failures (REVIEW items are acceptable at benchmark stage)
- The output must represent the best the current pipeline can produce
- The decision to send must be explicit, not automatic

### After external review returns
- If **benchmark quality confirmed** → close stream
- If **below strong working draft** → move stream back to ACTIVE, classify findings, run recovery cycle
- If **strong working draft but not benchmark** → decide whether further deterministic refinement has value or the stream is at its limit

### Diminishing returns rule
If repeated narrow cycles stop improving the same defect, the stream is at the **deterministic layer's practical limit**. Further improvement requires either:
- Agent prompt enrichment (higher effort, broader impact)
- Product-level capability investment (e.g. drawing extraction)
- Acceptance of the current quality level

---

## Defect Taxonomy

| Type | Description | Fix layer |
|------|-------------|-----------|
| **Deterministic** | Can be fixed in orchestrator/renderer post-processing | `core/orchestrator.py` |
| **Prompt/decomposer** | Requires agent prompt enrichment | `agents/decomposer.py`, `agents/control_writer.py` |
| **Issue-gate candidate** | Should become an automated check | `src/issue_gate.py` |
| **Case-specific** | Only applies to one benchmark case | N/A — note and move on |
| **Expert-review-only** | Requires consultant judgment | External review |
| **Product-investment** | Requires new capability | Product decision |

---

## Governance Model

### Source of truth
- **`docs/BENCHMARK_GOVERNANCE_REGISTER.md`** — single source of truth for all stream statuses
- **`docs/decisions/`** — one log per cycle, named by date and stream

### Stream statuses
- `ACTIVE` — being refined
- `AWAITING_EXTERNAL_REVIEW` — sent for consultant review
- `HOLD` — paused pending decision or dependency
- `CLOSED` — materially satisfied or at deterministic limit

### Decision rules
- One owner per stream
- One main weakness at a time
- Close streams deliberately (not by default)
- Closed streams are regression-protected, not forgotten

---

## Automation Assets

| Tool | Location | Purpose |
|------|----------|---------|
| Issue-gate checker | `src/issue_gate.py` | 12 deterministic checks, stage-aware, scope-configurable |
| Regression runner | `src/regression_runner.py` | 5 closed streams, 175 tests |
| CI pipeline | `.github/workflows/ci.yml` | Lint + full pytest on push to main |
| Reference jobs | `tests/run_reference_jobs.py` | 8 SWMS inference reference jobs |

---

## Required Checkpoint Output

Every checkpoint must report:

1. What was completed
2. What was verified
3. What decision was reached
4. Whether governance should be updated
5. Whether a local git commit was made
6. The exact next prompt to paste for the next phase

This format ensures clean handoff between sessions and prevents context loss.

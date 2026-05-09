# SSA Claude Implementation Gate

## Purpose
This file packages the current SSA plan-quality assessment and a ready-to-run implementation handoff for Claude Code.

Source context:
- `C:\Users\AlanRichardson\gatekeeper\docs\SSA_CODEX_REVIEW_BUNDLE.md`
- Last verified run target: `G:\My Drive\alan_mcxico\SSA-evidence\2026-05-01-SDG`

---

## SSA Plan Quality Gate (Filled)

### 1) Contract Capture
- Canonical samples opened before coding: PASS (current state), FAIL historically (original plan timing).
- Real-folder run validated: PASS (`G:\My Drive\alan_mcxico\SSA-evidence\2026-05-01-SDG`).
- Drift log maintained: PASS (22 deltas).

### 2) Source-of-Truth Matrix

| Field/Behavior | Authoritative source | Fallback | Forbidden |
|---|---|---|---|
| CCVS taxonomy | `pims/services/ssa_ccvs_taxonomy.py` | none in default path | `audit_checklist.xlsx` numeric synthesis |
| Status model | vision enricher (`claude-opus-4-7`) | `--no-enrich` legacy matcher | Conditional/Unmatched-only default |
| RA context | `pims/services/ssa_ra_parser.py` over `*Risk_Assessment*.docx` | none | no-context prompt |
| DOCX layout | frozen template clone + bounded mutations | none | layout rebuild from scratch |
| Staging upload shape | upload-format template + route contract | split parts on limits | presentation sample schema |

### 3) Assumption Register

| Assumption | Impact | Status | Required Proof |
|---|---|---|---|
| Vision optional | High | FAIL historically | Preflight key/model check |
| Text-only statusing is sufficient | High | FAIL historically | Canonical sample parity check |
| Network is stable | High | FAIL historically | Retry/backoff tests |

### 4) Runtime Preflight Gate
- `ANTHROPIC_API_KEY` present: FAIL in latest forced run.
- Model/API smoke call: FAIL when key missing.
- Folder input validation: PASS.
- Template/token integrity checks: PASS.

### 5) Reliability Contract
- Retries for transient HTTP/network: PASS.
- Idempotent reruns via manifest: PASS.
- Partial output recovery: PASS.

### 6) Verification Map
- Automated tests: PASS (70 green at bundle snapshot).
- Visual checkpoints against canonical outputs: PARTIAL (remaining gaps listed below).

### 7) Remaining Gaps (must become tracked work)
1. Positive Observations IDs/cross-references (`P1/P2/P3`, `PIMS Obs N | <reg ref>`).
2. Observations Register should include all observations + finding-reference phrasing.
3. Dedicated staging columns for `phase`, `activity_ref`, `hold_point`.
4. SWMS verification breadth.
5. Initial/Residual risk axis alignment.
6. Image preprocessing cache reuse for staged rerenders.
7. Legacy checklist fallback retirement path.

---

## Claude Code Implementation Brief (Copy/Paste)

```markdown
Implement the SSA gap-closure slice in `C:\Users\AlanRichardson\gatekeeper` using this gate.

Branch:
- `codex/ssa-gap-closure-v1`

Scope:
- Close the 7 known gaps documented in:
  - `C:\Users\AlanRichardson\gatekeeper\docs\SSA_CODEX_REVIEW_BUNDLE.md`

Files to modify:
- `C:\Users\AlanRichardson\gatekeeper\pims\services\ssa_pipeline.py`
- `C:\Users\AlanRichardson\gatekeeper\pims\services\ssa_vision_enricher.py`
- `C:\Users\AlanRichardson\gatekeeper\pims\services\ssa_ra_parser.py`
- `C:\Users\AlanRichardson\gatekeeper\pims\services\ssa_checklist_lookup.py` (only if needed; prefer retirement path)
- `C:\Users\AlanRichardson\gatekeeper\tests\test_ssa_pipeline.py`
- Add focused new tests under `C:\Users\AlanRichardson\gatekeeper\tests\`

Non-negotiable requirements:
1. Add startup preflight: fail loud if enrichment is enabled but `ANTHROPIC_API_KEY` is missing.
2. Implement Positive Observations IDs as `P1`, `P2`, `P3` and reference format `PIMS Obs N | <reg ref>`.
3. Expand Observations Register to include compliant + non-compliant rows with sample-aligned status text and finding cross-references.
4. Add staging columns: `phase`, `activity_ref`, `hold_point` populated from RA context when available.
5. Add explicit SWMS verification signal/flag behavior and test assertions.
6. Add initial/residual risk fields or mapping layer as agreed by schema contract; do not silently invent semantics.
7. Add reusable image preprocessing cache for staging size-control rerenders.
8. Keep manifest/idempotency and split-file behavior intact.

Test requirements:
- Add regression tests for each of the 7 items.
- Preserve existing suite stability.
- Run:
  - `python -m pytest tests/test_ssa_pipeline.py -v`
  - `python -m pytest tests/ -q`
  - `flake8 .`

Acceptance criteria:
- 0 test regressions.
- New tests pass and prove each gap closure.
- Forced run on `G:\My Drive\alan_mcxico\SSA-evidence\2026-05-01-SDG` with key present produces expected enriched statuses and updated output structure.
- Update bundle output to reflect closed gaps and reduced drift.

Deliverables:
- Small, reviewable commits grouped by feature.
- Final summary listing changed files, tests added, and before/after behavior for each closed gap.
```

---

## Operator Notes
- If `ANTHROPIC_API_KEY` is absent, treat run output as structurally valid but semantically degraded (rows remain unmatched).
- Keep SDG staging outcome semantics unchanged unless endpoint capability changes (`schema_valid_no_endpoint` + sentinel).

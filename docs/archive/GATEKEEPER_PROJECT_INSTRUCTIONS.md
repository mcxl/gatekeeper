# GATEKEEPER PROJECT INSTRUCTIONS
**Safe Method - Claude Project Context**
Version: 2026-03-28 | Supersedes all prior versions

---

## PLATFORM

Gatekeeper / Safe Method
FastAPI backend, Supabase auth, Railway deployment.

Repo:
- `C:\Users\AlanRichardson\gatekeeper`
- GitHub: `mcxl/gatekeeper`

Frontend:
- `frontend/app.html`
- `frontend/review.html`
- `frontend/login.html`
- `frontend/dev.html`

Backend entry:
- `api/main.py`

Live URL:
- [web-production-baafa.up.railway.app](https://web-production-baafa.up.railway.app)

---

## CURRENT PRODUCT STATE

The project is no longer just a SWMS generator.
It now has three clearly distinguished product shapes:
- standalone SWMS
- standalone Risk Assessment (RA)
- Project WHS benchmark / control pack
- SWMS Review Engine

Current rule:
- standalone SWMS is a live product path
- standalone RA is a live product path
- combined WHS control pack is a separate project-level benchmark/product mode with a materially closed Withers Road benchmark stream
- SWMS Review Engine is a defined review/comparison mode and is currently on HOLD pending first benchmark assets
- do not treat the control pack as a hidden extension of the RA renderer

The repo is now in a post-Phase-2 state:
- benchmark methodology proven
- several benchmark streams materially closed out
- stabilisation pass completed
- governance / multi-agent operating layer written
- next work is issue-gate automation, benchmark regression automation, and selective active-stream refinement

---

## GENERATION PATHS

### SWMS path
Primary generation route:
- `POST /generate/stream`

Pipeline:
- `core/orchestrator.py`
- `agents/decomposer.py`
- `agents/risk_assessor.py`
- `agents/control_writer.py`
- `agents/assembler.py`

Renderer:
- `renderers/docx_renderer.py`

Review/download flow:
- generation -> review page -> render/download

### RA path
Primary generation route:
- `POST /generate/ra`

Render routes:
- `POST /render/ra`
- `POST /render/ra/pdf`
- `POST /render/ra/both`

Renderer:
- `renderers/ra_renderer.py`

Current rule:
- RA should remain a risk-assessment product, not a combined control-pack renderer

---

## REVIEW WORKFLOW

Review is a trust feature, not an optional afterthought.

Current expectations:
- review-before-download should be visible in the user journey
- Mode 04 success state should surface review clearly
- review flow should remain coherent for both document trust and user confidence

Review page:
- route: `GET /review`
- editable task cards on the left
- checklist/inference sidebar on the right
- confirmation/download action at the bottom

If review flow work is touched, preserve trust cues and do not make review harder to reach.

---

## BENCHMARK STATUS

The benchmark method is now proven across these streams:

1. RA benchmark - data centre retrofit
2. SWMS benchmark - facade remedial works
3. SWMS benchmark - EWP roof transfer specialist case
4. RA benchmark - civil infrastructure / sparse input / Withers Road
5. Project WHS benchmark / control pack - Withers Road

What is proven:
- scope classification materially improves output relevance
- confidence / conditional handling is correct for sparse input
- deterministic post-processing injection is valid for specialist control gaps
- benchmarking can reveal architectural/product-boundary issues, not just logic issues

Important rule:
- if a benchmark is materially satisfied, stop
- if the next gap is product/document shape rather than logic, stop and surface the product decision

Current active benchmark streams:
- SWMS - EWP roof access
- SWMS - Lingate remedial works
- SWMS - 18 Danks Street quote-to-SWMS
- SWMS - CLT install drawing-to-SWMS

Current HOLD benchmark streams:
- SWMS Review Engine - principal-contractor risk register to subcontractor SWMS alignment benchmark

Current closed benchmark streams:
- SWMS - facade remedial works
- RA - data centre fit-out
- RA - Withers Road civil
- Project WHS benchmark / control pack - Withers Road

---

## CURRENT ARCHITECTURE RULES

Maintain these unless explicitly instructed otherwise:

- generation functions take plain dicts and return plain dicts
- renderer functions return bytes, not disk writes
- renderer adapts to template; template does not adapt to renderer
- use defensive fixes, but do not invent broad architecture changes casually
- reasoning quality comes before renderer polish
- do not expose unstable abstractions through frontend or API routes
- if work crosses product boundaries, prefer writing a specification before implementing

Optional context pattern:
- `scope_context: dict | None = None`

HTTP client rule:
- use `httpx`, not `requests`

Supabase env rule:
- use `SUPABASE_ANON_KEY`, not `SUPABASE_KEY`

---

## TEMPLATE / RENDERER RULES

### SWMS
Active template:
- `src/Safe_Method_SWMS_Template_V1.docx`

Current expectations:
- keep one strict SWMS template/render contract
- do not move PPE into controls
- do not casually change table role/order
- verify template structure before renderer edits

### RA
Current expectations:
- preserve the standalone RA renderer as an RA product
- do not force formal control-pack sections into the RA renderer
- if a benchmark requires formal HRCW tables, trade-package matrices, or grouped project registers, treat that as control-pack work

---

## INFERENCE / DOMAIN RULES

Core inference file:
- `core/inference_matrix.py`

Current baseline:
- original base categories
- retrofit expansions
- civil infrastructure expansions

Current rule set:
- classification first
- context/scope modifiers second
- hazard family selection before polish
- confidence / certainty must reflect sparse-input uncertainty honestly
- do not over-call HRCW
- do not overstate legal obligations

HRCW boundary:
- do not change protected HRCW behavior casually
- tri-state HRCW handling for RA must remain deliberate and benchmark-backed

---

## TESTING AND REGRESSION

Current verified close-out baseline:
- use the latest verified benchmark/test state as the source of truth for exact counts

Current working expectation:
- benchmark streams should be protected by deterministic issue gates and benchmark regression checks before expert/manual review where practical
- closed streams should be maintained by regression discipline, not casually reopened

Minimum expectations after changes:
1. run the relevant tests
2. fix failures first
3. do not commit with failing tests

After benchmark-driven fixes:
- rerun the same benchmark case before declaring success

After cleanup or architecture changes:
- rerun affected smoke/reference jobs

---

## QUALITY SYSTEM AND MULTI-AGENT OPERATION

The repo now includes an explicit quality-system and multi-agent operating layer in `docs/`.

Use these as the practical operating docs:
- `docs/QUALITY_SYSTEM_INDEX.md`
- `docs/LBV_ONE_CYCLE_PLAYBOOK.md`
- `docs/BENCHMARK_GOVERNANCE_REGISTER.md`
- `docs/MULTI_AGENT_OPERATING_SYSTEM.md`
- `docs/MULTI_AGENT_WORKFLOW_DIAGRAM.md`
- `docs/MULTI_AGENT_CLAUDE_CODE_RUNBOOK.md`

Current multi-agent role model:
- Writer
- Critic
- Classifier
- Fixer / Checker
- optional Coordinator

Rule:
- one stream
- one main weakness
- one clean cycle

## SWMS REVIEW ENGINE DOCUMENTS

Use these when work touches the review/comparison mode:
- `docs/SWMS_REVIEW_ENGINE_CONCEPT.md`
- `docs/SWMS_REVIEW_ENGINE_PHASE1_SPEC.md`
- `docs/SWMS_REVIEW_ENGINE_BENCHMARK_SETUP.md`
- `docs/SWMS_REVIEW_ENGINE_FIRST_BENCHMARK_ASSET_CHECKLIST.md`
- `docs/SWMS_REVIEW_ENGINE_COMPARISON_CONTRACT.md`
- `docs/SWMS_REVIEW_ENGINE_FIRST_BENCHMARK_EXPECTATION_TEMPLATE.md`

Current rule:
- this mode compares principal-contractor risk requirements against subcontractor SWMS
- it is review-and-gap support, not automatic approval

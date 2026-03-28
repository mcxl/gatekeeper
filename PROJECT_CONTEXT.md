Platform: Gatekeeper SWMS Generator — branded as Safe Method

FastAPI backend, Supabase auth, Railway deployment.

Repo: C:\\Users\\AlanRichardson\\gatekeeper

Frontend: /frontend/app.html (single file, inline JS)

Live URL: https://web-production-baafa.up.railway.app/app

API: api/main.py registers all routers

Generation pipeline: POST /generate/auto → core/orchestrator.py → 4-agent pipeline

  agents/decomposer.py (Agent 1, Haiku)

  agents/risk\_assessor.py (Agent 2)

  agents/control\_writer.py (Agent 3, Haiku)

  agents/assembler.py (Agent 4)

Renderer: renderers/docx\_renderer.py → nine-table DOCX template

Inference: core/inference\_matrix.py (119 categories, \~4,900 lines)

Validation: core/validate.py + orchestrator.\_validate\_task\_block()

Vocabulary: vocab/swms\_vocabulary.py, vocab/standards\_registry.py



CURRENT PATCH STATUS (as of 2026-03-11):

All 9 files below are PATCHED — confirm deployed before any new work:

  core/document\_extractor.py   — truncate\_for\_scope() added

  core/swms\_analyser.py        — 17-field SCOPE\_EXTRACT\_PROMPT, max\_tokens 4000

  core/generate.py             — scope\_context param, \_build\_scope\_block()

  api/upload\_routes.py         — truncate\_for\_scope, scope\_context in response

  agents/decomposer.py         — scope\_context param, \_build\_scope\_context\_block()

  agents/control\_writer.py     — scope\_context param, \_build\_scope\_context\_block()

  core/orchestrator.py         — scope\_context threaded, functools.partial fix

  api/main.py                  — scope\_context extracted from body, passed to generate\_swms()

  frontend/app.html            — \_scopeContext variable, passed in generate() body



ARCHITECTURE RULES (maintain always):

\- Generation functions take plain dicts, return plain dicts — no FastAPI types inside engine

\- scope\_context: dict = None is the pattern for optional site-specific context

\- render\_swms() target shape: returns bytes (io.BytesIO), not writes to disk

  → make this change when next touching docx\_renderer.py for rendering audit



ROADMAP — PATH B (Safe Method SaaS, integrations as growth levers):



IMMEDIATE (current):

  1. Deploy 9-file scope\_context patch (Mode 03 quality fix)

  2. Verify with New\_South\_Head\_Road\_DOUBLE\_BAY\_Scope\_of\_work.pdf test upload

  3. Begin rendering audit — 14 issues identified, fix in docx\_renderer.py

     → When opening renderer: convert to io.BytesIO return at same time



SHORT TERM (next):

  4. Mode 04 — chat intake (api/intake\_routes.py, ChatIntake.jsx, CreateSWMS.jsx)

     Files already written — needs integration into app.html tab strip

  5. Rendering audit complete — all 14 issues resolved



MEDIUM TERM:

  6. SDK packaging — gatekeeper\_sdk/ with clean \_\_init\_\_.py

     (architecture already heading there via patch discipline)

  7. Platform conversations — Procore ANZ, Hammertech, Donesafe — opportunistic



KNOWN PRE-EXISTING ISSUES (do not fix in passing — schedule separately):

  A. CCVS code system mismatch: generate.py uses score-based (WAH-H6),

     control\_writer.py uses sub-codes (WAH-H1 to WAH-H8) — different systems

  B. Stream path CCVS suppression runs after yield — never reaches client

  C. Legacy POST /generate has no auth (Depends(get\_current\_user) missing)



GATEKEEPER STANDARD:

  - validate.py: wah\_applicable forced False when ccvs\_code !startswith WAH

  - Admin fog hard cap = 20

  - Data row fill = white (no amber)

  - Renderer template: RPD-MSW-002, dotted grey borders, risk cells Aptos 10pt bold

  - Emojis: ⚠️ HOLD POINT, 🛑 STOP WORK

  - Standard PPE: eye protection, hearing protection (>85dB), cut-resistant gloves, hi-vis

  - CCVS: 30 approved codes, hyphen separators (WAH-H6 not WAHH6)


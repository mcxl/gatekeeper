Platform: Gatekeeper SWMS Generator — branded as Safe Method

FastAPI backend, Supabase auth, Railway deployment.

Repo: C:\\Users\\AlanRichardson\\gatekeeper

Frontend: /frontend/app.html (single file, inline JS)

API: api/main.py registers all routers

Generation pipeline: POST /generate/auto → core/orchestrator.py → 4-agent pipeline

&nbsp; agents/decomposer.py (Agent 1, Haiku)

&nbsp; agents/risk\_assessor.py (Agent 2)

&nbsp; agents/control\_writer.py (Agent 3, Haiku)

&nbsp; agents/assembler.py (Agent 4)

Renderer: renderers/docx\_renderer.py → nine-table DOCX template

Inference: core/inference\_matrix.py (119 categories, ~4,900 lines)

Validation: core/validate.py + orchestrator.\_validate\_task\_block()

Vocabulary: vocab/swms\_vocabulary.py, vocab/standards\_registry.py



CURRENT PATCH STATUS (as of 2026-03-11):

All 9 files below are PATCHED — confirm deployed before any new work:

&nbsp; core/document\_extractor.py   — truncate\_for\_scope() added

&nbsp; core/swms\_analyser.py        — 17-field SCOPE\_EXTRACT\_PROMPT, max\_tokens 4000

&nbsp; core/generate.py             — scope\_context param, \_build\_scope\_block()

&nbsp; api/upload\_routes.py         — truncate\_for\_scope, scope\_context in response

&nbsp; agents/decomposer.py         — scope\_context param, \_build\_scope\_context\_block()

&nbsp; agents/control\_writer.py     — scope\_context param, \_build\_scope\_context\_block()

&nbsp; core/orchestrator.py         — scope\_context threaded, functools.partial fix

&nbsp; api/main.py                  — scope\_context extracted from body, passed to generate\_swms()

&nbsp; frontend/app.html            — \_scopeContext variable, passed in generate() body



ARCHITECTURE RULES (maintain always):

\- Generation functions take plain dicts, return plain dicts — no FastAPI types inside engine

\- scope\_context: dict = None is the pattern for optional site-specific context

\- render\_swms() target shape: returns bytes (io.BytesIO), not writes to disk

&nbsp; → make this change when next touching docx\_renderer.py for rendering audit



ROADMAP — PATH B (Safe Method SaaS, integrations as growth levers):



IMMEDIATE (current):

&nbsp; 1. Deploy 9-file scope\_context patch (Mode 03 quality fix)

&nbsp; 2. Verify with New\_South\_Head\_Road\_DOUBLE\_BAY\_Scope\_of\_work.pdf test upload

&nbsp; 3. Begin rendering audit — 14 issues identified, fix in docx\_renderer.py

&nbsp;    → When opening renderer: convert to io.BytesIO return at same time



SHORT TERM (next):

&nbsp; 4. Mode 04 — chat intake (api/intake\_routes.py, ChatIntake.jsx, CreateSWMS.jsx)

&nbsp;    Files already written — needs integration into app.html tab strip

&nbsp; 5. Rendering audit complete — all 14 issues resolved



MEDIUM TERM:

&nbsp; 6. SDK packaging — gatekeeper\_sdk/ with clean \_\_init\_\_.py

&nbsp;    (architecture already heading there via patch discipline)

&nbsp; 7. Platform conversations — Procore ANZ, Hammertech, Donesafe — opportunistic



KNOWN PRE-EXISTING ISSUES (do not fix in passing — schedule separately):

&nbsp; A. CCVS code system mismatch: generate.py uses score-based (WAH-H6),

&nbsp;    control\_writer.py uses sub-codes (WAH-H1 to WAH-H8) — different systems

&nbsp; B. Stream path CCVS suppression runs after yield — never reaches client

&nbsp; C. Legacy POST /generate has no auth (Depends(get\_current\_user) missing)



GATEKEEPER STANDARD:

&nbsp; - validate.py: wah\_applicable forced False when ccvs\_code !startswith WAH

&nbsp; - Admin fog hard cap = 20

&nbsp; - Data row fill = white (no amber)

&nbsp; - Renderer template: RPD-MSW-002, dotted grey borders, risk cells Aptos 10pt bold

&nbsp; - Emojis: ⚠️ HOLD POINT, 🛑 STOP WORK

&nbsp; - Standard PPE: eye protection, hearing protection (>85dB), cut-resistant gloves, hi-vis

&nbsp; - CCVS: 30 approved codes, hyphen separators (WAH-H6 not WAHH6)


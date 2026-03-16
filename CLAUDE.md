# GATEKEEPER — CLAUDE CODE INSTRUCTIONS
# CLAUDE.md — repo root (C:\Users\AlanRichardson\gatekeeper\CLAUDE.md)
# Claude Code reads this automatically at the start of every session.
# Version: 2026-03-16 | Safe Method SWMS Generator

---

## Project Structure
The main project is a SWMS (Safe Work Method Statement) generator app with a FastAPI backend (Python) and HTML frontend. Key files: `docx_renderer.py`, `generate()` streaming endpoint, Supabase integration. The app runs on port 8000 by default.

---

## Testing
Always run the full test suite after any code modification. There are 35+ tests in tests/test_renderer.py. Fix any broken imports or stale references before committing. Never attempt large refactors without user confirmation.

---

## Git Workflow
After completing a feature or fix, stage, commit with a descriptive message, and push unless told otherwise. Always verify files exist before attempting git add.

---

## Interaction Rules
When the user pastes code, file contents, or documentation, treat it as context for an upcoming task — do NOT interpret it as a question or respond with analysis unless explicitly asked. If unclear, ask what they'd like done with it.

---

## OPERATING PRINCIPLES
- Always produce complete, executable output. No partial patches. No placeholders.
- Never explain what you are about to build. Build it. Explanation after if asked.
- Never ask clarifying questions if the answer is inferable from context. Decide and state it.
- Always write the full file when changing a file — not a diff, not a snippet.
- If a change touches multiple files, deliver all files in the same response.
- Default to the existing pattern in the codebase. No new patterns without being asked.
- Always choose the most robust/defensive fix — never the minimal one.
- Never surface raw errors to users — always degrade gracefully.
- All HTTP calls use httpx (not requests).
- All async functions use async/await. No threading inside agents.
- Tests go in tests/. Fixtures go in tests/fixtures/.
- Run pytest tests/test_renderer.py -v after every renderer change. 35/35 is the baseline.

---

## CURRENT STATE (2026-03-15)

COMPLETE — Blocks 1-5 all deployed and live.

NEXT — Block 6: Scope extraction confidence + source attribution
Add _confidence and _source_text companion fields to SCOPE_EXTRACT_PROMPT.
Update Review screen to use real values instead of synthetic ones.

---

## REPO STRUCTURE

```
gatekeeper/
  api/
    main.py              ← FastAPI app, all route registration, /health endpoint
    intake_routes.py     ← Mode 04 endpoints (/intake/extract, /intake/generate)
    upload_routes.py     ← Mode 02/03 upload + scope_context endpoints
  agents/
    decomposer.py        ← Agent 1 (Haiku) — PATCH_01 applied
    risk_assessor.py     ← Agent 2 (Haiku) — PATCH_02 applied
    control_writer.py    ← Agent 3 (Haiku) — PATCH_03 applied
    assembler.py         ← Agent 4 (Haiku) — PATCH_04 applied
  core/
    orchestrator.py      ← routes simple/full, scope_context threaded
    generate.py          ← PATCH_05 applied
    inference_matrix.py  ← PROTECTED — DO NOT TOUCH without dedicated session
    schema.py            ← TaskBlock, MonitoringEntry, ValidationResult
    validate.py          ← 13-check validation suite
    auth.py              ← Supabase JWT via httpx, SUPABASE_ANON_KEY
    swms_analyser.py     ← scope extraction, ToC-aware SCOPE_EXTRACT_PROMPT
    document_extractor.py← pypdf primary + Claude Haiku vision fallback (3 pages)
    jurisdictions.py     ← jurisdiction base legislation
    audit.py             ← AuditLog SQLite
  renderers/
    docx_renderer.py     ← 35/35 clean — 12-issue audit complete
    pdf_renderer.py      ← Gotenberg primary + fallbacks
    ra_renderer.py       ← Risk Assessment renderer
  vocab/
    swms_vocabulary.py   ← PLAIN_ENGLISH_SUBSTITUTIONS, CONTROLS, check_vocabulary()
    standards_registry.py
  supabase/
    migrations/
      001_scope_library.sql ← scope_documents + scope_extractions tables
  tests/
    test_renderer.py     ← 35 tests — run after every renderer change
    fixtures/            ← 01_basic_painting.json through 06_multi_hrcw.json
  src/
    Safe_Method_SWMS_Template_V1.docx ← active 10-table template
  frontend/
    app.html             ← single-file frontend, inline JS
```

---

## ARCHITECTURE RULES — NEVER VIOLATE

1. Generation functions take plain dicts, return plain dicts. No FastAPI types inside engine.
2. scope_context: dict = None — pattern for optional site context in all agent functions.
3. render_swms_document() MUST return bytes. Not io.BytesIO. Not disk writes.
4. docx_to_pdf() takes bytes, returns bytes.
5. SUPABASE_ANON_KEY not SUPABASE_KEY.
6. Template guard: len(doc.tables) != 10 raises ValueError.
7. httpx not requests.
8. inference_matrix.py — DO NOT TOUCH without dedicated review session.
9. hrcw_flags dict keys — DO NOT RENAME.
10. wah_applicable — always derived from ccvs_code.startswith("WAH").

---

## PDF EXTRACTION

Text PDFs: pypdf (first 5 pages, no API call)
Scanned PDFs: Claude Haiku vision on first 3 pages (150 DPI, 2000 tokens)
  Page 1: title/cover — address, client, contractor
  Page 2: ToC/summary — HRCW indicators from section headings
  Page 3: first content — trade types, access methods
Target: under 20 seconds. Never use Claude API as primary PDF reader.

---

## SCOPE EXTRACTION — THREE DOCUMENT FORMATS

1. Engineer scope: author is consultant NOT contractor. Address in headers/tables.
2. Tender schedule: address in "Address:" labelled field. Author is consultant.
3. Quote/proposal: author IS the contractor. Address in "To:" field.
   Strata Plan number = occupied_building: true.
   Managing agents ≠ PCBU.

---

## PDF CONVERSION — GOTENBERG

Railway internal URL: http://gotenberg.railway.internal:3000
Env var: GOTENBERG_URL on web service
Fallback: LibreOffice → docx2pdf
Local dev: docker run --rm -p 3000:3000 gotenberg/gotenberg:8

---

## SCOPE DOCUMENT LIBRARY

Tables: scope_documents, scope_extractions (Supabase)
Migration: supabase/migrations/001_scope_library.sql
Auto-saves via BackgroundTasks on every extraction. Zero latency impact.

---

## TEMPLATE — 10 TABLES

T0: cover + HRCW | T1: tasks (8 cols) | T2: monitoring (5 cols)
T3-T7: sign-off/amendments — cantSplit all | T8: risk matrix font only
T9: pre-requisites — max 6 bullets per cell
Phase banners: rows starting "PHASE" — skipped by _count_data_rows

---

## CCVS CODES (30 approved)

WAH-H6, WAH-H9, IRA-H6, IRA-H9, ELE-M4, ELE-H6, SIL-H6, SIL-H9,
STR-H6, STR-H9, CFS-H9, ENE-M4, ENE-H6, HOT-M4, HOT-H6, MOB-M4, MOB-H6,
ASB-H6, ASB-H9, LED-H6, CHM-M3, CHM-H6, TRF-M4, TRF-H6,
SYS-L1, SYS-L2, SYS-M3, SYS-M4, SYS-H6, SYS-H9, N/A

Invalid sub-codes (WAH-H1 etc) mapped to approved parents at post-processing.
Monitoring row: only where ccvs_code != "N/A"

---

## KEY DATA SHAPES

TaskBlock: task, scope, hazards[], risk_pre, risk_post, hold_points[],
controls[], stop_work[], admin[], ppe[], responsibility{SUP,WKR},
ccvs_code, monitoring|None, wah_applicable, source, approved, version, db_id

scope_context: project_name, site_address, principal_contractor, project_manager,
supervisor, contract_type, trade_types[], work_areas[], special_conditions[],
hrcw_indicators[], height_work, confined_spaces, hazardous_materials,
occupied_building, scope_summary, key_activities[], jurisdiction

---

## STREAM ENDPOINT

POST /generate/stream — SSE
Body: {description, project_meta, force_full:true, jurisdiction, scope_context}
Auth: Authorization: Bearer ${getToken()} — manual, NOT via apiCall()
Events: route → task_count → task(×N) → done | error
Buffer on \n\n before JSON.parse()

---

## PLAIN ENGLISH

Substitutions: commence→start, utilise→use, prior to→before, inspect→check, rectify→fix
Fog hard cap: admin=20, stop_work=16, all others=14

---

## KNOWN ISSUES — DO NOT FIX IN PASSING

A. CCVS mismatch: generate.py vs control_writer.py — monitor
B. Stream CCVS suppression after yield → Block 8
C. Legacy POST /generate no auth → Block 8
D. No stream timeout → deferred

---

## GATEKEEPER STANDARD

wah_applicable forced False when ccvs_code !startswith WAH | Admin fog hard cap 20
Data row fill = white | Font: Aptos 9pt content, 10pt risk cells
Emojis: ⚠️ HOLD POINT, 🛑 STOP WORK
PPE baseline: eye protection, hearing protection (>85dB), cut-resistant gloves, hi-vis
Colours: Dark Blue #1F3864, Mid Blue #2E75B6, Light Blue #D6E4F0, Red #C00000

---

## ENVIRONMENT

| Issue             | Local                        | Railway                                |
|-------------------|------------------------------|----------------------------------------|
| PDF               | LibreOffice or docx2pdf      | Gotenberg (enchanting-freedom project) |
| GOTENBERG_URL     | http://localhost:3000 (opt.) | http://gotenberg.railway.internal:3000 |
| SUPABASE_ANON_KEY | .env                         | Railway env var                        |
| ANTHROPIC_API_KEY | .env                         | Railway env var                        |
| SSE streaming     | Works                        | X-Accel-Buffering: no                  |

GATEKEEPER — SAFE METHOD SWMS GENERATOR
MASTER PLAN
Version: 2026-03-13

═══════════════════════════════════════════════════════════════
HEADLESS EXECUTION — --dangerously-skip-permissions
═══════════════════════════════════════════════════════════════

Claude Code runs with full tool access — no approval prompts.
Efficiency comes from tight prompts. Mistakes happen silently.
Always run the verification command before pushing.

BASE INVOCATION (run from repo root):
  cd C:\Users\AlanRichardson\gatekeeper
  claude --dangerously-skip-permissions -p "PROMPT"

Or pipe from a prompt file (recommended for complex items):
  claude --dangerously-skip-permissions -p "$(cat prompts\commit1.txt)"

─────────────────────────────────────────────────────────────
SAFE TO RUN HEADLESS (low blast radius — single file or additive)

  COMMIT 1 — app.html only
  COMMIT 2 — app.html + 3 lines in main.py
  ITEM 6    — one new function, one file
  AUDIT STEPS 0,1,4,8,10 — targeted single changes

REVIEW BEFORE PUSH (multi-file or touches protected boundary)

  ITEM 4    — Mode 04 gap close (unknown scope until reality check)
  ITEM 5    — Rendering audit Steps 3,5,6,7 (HRCW + major rebuilds)
  AUDIT STEP 3 — HRCW rendering rewrite (protected boundary adjacent)

─────────────────────────────────────────────────────────────
PROMPT FILES — save in C:\Users\AlanRichardson\gatekeeper\prompts\

Create this folder. One .txt file per item. Paste prompt, save, invoke.
Keeps prompts auditable and reusable across sessions.

─────────────────────────────────────────────────────────────
COMMIT 1 — prompts\commit1.txt

Read CLAUDE.md first. Then:
Modify frontend/app.html only. No other files.
Replace the two-call sequence inside generate() — the GET /infer call
and the POST /generate/auto call — with a single POST /generate/stream
ReadableStream consumer. Requirements:
1. Stream POST body includes: description, project_meta, force_full: true,
   jurisdiction, scope_context: _scopeContext
2. Auth header: Authorization: Bearer ${getToken()} added manually to fetch()
3. Buffer stream chunks on \n\n before JSON parse — never parse raw chunks
4. Reset lastTasks = [] and lastInference = {} at top of generate()
5. Stream events map to UI steps:
   route → step-analyse done, showInference(event.inference)
   task_count → step-infer active
   task → push to lastTasks, update label
   done → step-infer+step-tasks done, call renderDocument()
   error → throw new Error(event.message)
6. Health check inside auth success block disables fmt-pdf, fmt-both,
   ifmt-pdf, ifmt-both when pdf_available is false
7. Nothing outside generate() is modified
8. renderDocument() and everything after it is unchanged

VERIFY AFTER:
  grep -n "generate/stream" frontend/app.html
  grep -n "generate/auto\|GET.*infer" frontend/app.html
  (second command must return no results)

─────────────────────────────────────────────────────────────
COMMIT 2 — prompts\commit2.txt

Read CLAUDE.md first. Then:
Two files only: api/main.py and frontend/app.html.
Changes:
1. api/main.py — add at module level after imports:
   import shutil
   _PDF_AVAILABLE = bool(shutil.which("soffice") or shutil.which("libreoffice"))
   Add pdf_available: _PDF_AVAILABLE to the /health endpoint JSON response.
   Add Cache-Control: public, max-age=60 header to /health response.
2. frontend/app.html — add hidden div after format selector row:
   <div id="pdf-unavailable-notice" style="display:none;font-size:12px;
   color:var(--text-muted);text-align:center;margin-top:6px;">
   PDF export requires LibreOffice — DOCX available</div>
3. frontend/app.html — inside auth success block after name autofill,
   add fetch('/health') call that disables fmt-pdf, fmt-both, ifmt-pdf,
   ifmt-both and falls back currentFormat to 'docx' when pdf_available=false.
   Show pdf-unavailable-notice div when unavailable.
No other files.

VERIFY AFTER:
  grep -n "pdf_available\|_PDF_AVAILABLE" api/main.py
  grep -n "pdf-unavailable-notice" frontend/app.html

─────────────────────────────────────────────────────────────
RENDERING AUDIT STEPS 0+1 — prompts\audit_step01.txt

Read CLAUDE.md and docs/GATEKEEPER_RENDERING_AUDIT_CHECKLIST.txt first. Then:
Complete Steps 0 and 1 only in renderers/docx_renderer.py.
Step 0: Update template_path constant from SWMS-260306-V1.docx to
        Safe_Method_SWMS_Template_V1.docx
Step 1: Change table count guard from != 9 to != 10 and update error message.
No other changes.

VERIFY AFTER:
  grep -n "Safe_Method_SWMS_Template\|SWMS-260306" renderers/docx_renderer.py
  grep -n "!= 10\|!= 9" renderers/docx_renderer.py

─────────────────────────────────────────────────────────────
RENDERING AUDIT STEP 3 — prompts\audit_step3.txt
⚠ REVIEW OUTPUT BEFORE PUSH — touches HRCW protected boundary

Read CLAUDE.md and docs/GATEKEEPER_RENDERING_AUDIT_CHECKLIST.txt first.
Read core/inference_matrix.py hrcw_flags output keys — do not change them.
Complete Step 3 only in renderers/docx_renderer.py:
- Remove _HRCW_TICK_MAP
- Add _HRCW_KEYWORD_MAP (exact keys as specified in checklist)
- Add _tick_hrcw_checkbox() function
- Replace HRCW tick block inside _fill_cover_table
Do not change core/inference_matrix.py, assembler.py, or any other file.

VERIFY AFTER (manual — open DOCX and check ticks):
  python -c "
  from renderers.docx_renderer import render_swms_document
  # run with hrcw_flags={'falling_2m':True,'asbestos':True}
  # open output and confirm ☑ next to fall and asbestos only
  "
  (Full test spec in checklist Step 3T)

─────────────────────────────────────────────────────────────
RENDERING AUDIT STEPS 4+5 — prompts\audit_step45.txt

Read CLAUDE.md and docs/GATEKEEPER_RENDERING_AUDIT_CHECKLIST.txt first.
Step 3T must be marked DONE before running this prompt.
Complete Steps 4 and 5 only in renderers/docx_renderer.py.
Step 4: Fix _fill_cover_table field mapping per checklist col/row replacements.
Step 5: Rebuild _build_task_table for 8-column structure. Add _hold_point_cell.
        CCVS code appends bold grey at bottom of col 7 — not in T2.
No other files.

VERIFY AFTER:
  grep -n "_COL_W_DXA\|_HEADERS" renderers/docx_renderer.py
  grep -n "_hold_point_cell\|ccvs_code" renderers/docx_renderer.py

─────────────────────────────────────────────────────────────
RENDERING AUDIT STEPS 6+7 — prompts\audit_step67.txt

Read CLAUDE.md and docs/GATEKEEPER_RENDERING_AUDIT_CHECKLIST.txt first.
Complete Steps 6 and 7 only in renderers/docx_renderer.py.
Step 6: Rename _build_ccvs_table → _build_monitoring_table. 5 columns only.
        Skip row only when CCVS code is N/A. Null monitoring = dash placeholders.
Step 7: Delete _fill_legislation_table and _fill_requirements_table.
        Add _fill_prerequisites_table targeting T9. Move all assembly logic
        verbatim — only cell destinations change. Max 6 items per cell.
        Concise format: hazmat name+SDS+one note, plant name+cert note,
        legislation primary acts only max 4 lines. No WAH RA form in T9.
No other files.

VERIFY AFTER:
  grep -n "_fill_prerequisites_table\|_fill_requirements\|_fill_legislation" renderers/docx_renderer.py
  grep -n "_build_monitoring_table\|_build_ccvs" renderers/docx_renderer.py

─────────────────────────────────────────────────────────────
RENDERING AUDIT STEPS 8+9+10 — prompts\audit_step8910.txt

Read CLAUDE.md and docs/GATEKEEPER_RENDERING_AUDIT_CHECKLIST.txt first.
Complete Steps 8, 9, and 10 in renderers/docx_renderer.py and api/main.py.
Step 8: Fix _fill_signoff_table index from tables[7] to tables[3].
Step 9: Update render_swms_document orchestration block — new call sequence
        and updated docstring per checklist.
Step 10: Change render_swms_document return from buf.getvalue() to buf (BytesIO).
         Update both callers in api/main.py to call buf.read() after receiving.

VERIFY AFTER:
  grep -n "buf.seek\|buf.read\|getvalue" renderers/docx_renderer.py api/main.py
  grep -n "tables\[3\]\|tables\[7\]" renderers/docx_renderer.py

─────────────────────────────────────────────────────────────
ITEM 6 — prompts\plain_english.txt

Read CLAUDE.md first. Then:
Add _plain_english_pass() to core/validate.py.
Function signature: def _plain_english_pass(tasks: list) -> list
Runs a find-replace on all text fields in each TaskBlock after assembly.
Word substitutions (case-insensitive, whole-word where practical):
  commence → start
  utilise → use
  prior to → before
  inspect → check
  rectify → fix
Apply to: task.task, task.scope, task.hazards (list), task.controls (list),
task.hold_points (list), task.stop_work (list)
Call _plain_english_pass() in core/orchestrator.py after assembler returns,
before renderer is called.
No other files.

VERIFY AFTER:
  grep -n "_plain_english_pass" core/validate.py core/orchestrator.py

─────────────────────────────────────────────────────────────
GENERAL VERIFY COMMAND (run after any headless session):

  git diff --stat
  (confirms which files were actually touched — catch unexpected changes)

  git diff
  (scan for anything surprising before committing)

═══════════════════════════════════════════════════════════════
PRODUCT GOAL
═══════════════════════════════════════════════════════════════

Reduce time-to-document. Produce a SWMS that passes a safety
officer review without correction. Every item on this plan
exists to make the product faster, more reliable, or more
credible — in that order.

═══════════════════════════════════════════════════════════════
IMMEDIATE — COMMITS 1 AND 2
Files: frontend/app.html + api/main.py
═══════════════════════════════════════════════════════════════

COMMIT 1 — Switch generate() to /generate/stream
File: frontend/app.html only. No backend changes.

Replace the two-call sequence (GET /infer → POST /generate/auto)
with a single POST /generate/stream ReadableStream consumer.

Stream POST body:
  {
    description:    payload.description,
    project_meta:   payload.project_meta,
    force_full:     true,
    jurisdiction:   currentJurisdiction,
    scope_context:  _scopeContext
  }

Auth header: Authorization: Bearer ${getToken()} — manual, not via apiCall().
Mid-stream token expiry is not a real risk given generation duration.

Buffer stream chunks on \n\n before JSON parse. Never parse raw chunks.

Reset at top of generate():
  lastTasks = [];
  lastInference = {};

Stream event to UI step mapping:
  POST sent         → step-analyse active
  "route"           → step-analyse done. lastInference = event.inference.
                      showInference(lastInference).
  "task_count"      → step-infer active. Label: "Generating N tasks..."
  "task"            → push event.task to lastTasks. Label: "Task X of N done"
  "done"            → step-infer done. step-tasks done. renderDocument().
  "error"           → throw new Error(event.message). Existing catch handles.

Everything from renderDocument() onwards is unchanged.
Intake format buttons ifmt-pdf and ifmt-both disabled alongside
fmt-pdf and fmt-both in health check block.

WHY FIRST: Eliminates preflight round-trip. Removes wait pain.
Better demo. Streaming pattern available for Mode 04.

Pre-submission checklist:
  [ ] Chunks buffered on \n\n before JSON parse
  [ ] lastTasks = [] and lastInference = {} reset at top of generate()
  [ ] scope_context: _scopeContext in stream POST body
  [ ] force_full: true in stream POST body
  [ ] Authorization: Bearer ${getToken()} in stream fetch headers
  [ ] Health check inside auth success block — not top level
  [ ] ifmt-pdf + ifmt-both disabled alongside fmt-pdf + fmt-both
  [ ] Nothing outside generate() modified in Commit 1
  [ ] renderDocument() and everything after it unchanged

───────────────────────────────────────────────────────────────

COMMIT 2 — PDF capability detection
Files: api/main.py (~3 lines), frontend/app.html (~20 lines)

api/main.py — module level after imports:
  import shutil
  _PDF_AVAILABLE = bool(shutil.which("soffice") or shutil.which("libreoffice"))

In /health endpoint:
  return JSONResponse(
      content={"status": "ok", "pdf_available": _PDF_AVAILABLE},
      headers={"Cache-Control": "public, max-age=60"},
  )

app.html — hidden notice element (add after format selector row):
  <div id="pdf-unavailable-notice"
       style="display:none;font-size:12px;color:var(--text-muted);
              text-align:center;margin-top:6px;">
    PDF export requires LibreOffice — DOCX available
  </div>

app.html — inside auth success block after name autofill:
  fetch('/health')
    .then(r => r.json())
    .then(data => {
      if (!data.pdf_available) {
        ['fmt-pdf','fmt-both','ifmt-pdf','ifmt-both'].forEach(id => {
          const btn = document.getElementById(id);
          if (btn) { btn.disabled = true; btn.title = 'PDF requires LibreOffice'; }
        });
        if (currentFormat === 'pdf' || currentFormat === 'both') {
          currentFormat = 'docx';
          const b = document.getElementById('fmt-docx');
          if (b) b.click();
        }
        const n = document.getElementById('pdf-unavailable-notice');
        if (n) n.style.display = 'block';
      }
    })
    .catch(() => {});

WHY SECOND: Prevents silent 500s on Replit. Keeps rendering audit
failures scoped to real renderer issues, not environment mismatches.

═══════════════════════════════════════════════════════════════
SHORT TERM — ITEMS 3 TO 6
═══════════════════════════════════════════════════════════════

ITEM 3 — Mode 04 reality check (one validation pass, no code)

Before writing any integration code, confirm end-to-end:
  1. selectTab('intake') shows panel and hides main form
  2. /intake/extract returns fields correctly on a real file upload
  3. Review form populates and allows editing
  4. /intake/generate returns a valid DOCX
  5. UX is acceptable relative to the improved main flow

Do not spend a session fixing something that is not broken.
The real remaining gap is unknown until this pass is done.

───────────────────────────────────────────────────────────────

ITEM 4 — Mode 04 gap close

Fix only what the reality check reveals. Nothing more.

───────────────────────────────────────────────────────────────

ITEM 5 — Rendering audit
File: renderers/docx_renderer.py only (+ src/ template placement)
See: GATEKEEPER_RENDERING_AUDIT_CHECKLIST.txt for full step-by-step.

Decisions confirmed this session:

  Template:        Safe_Method_SWMS_Template_V1.docx — 10 tables.
                   No structural changes to template file needed.

  HRCW:            Protected boundary. Inference unchanged.
                   Old template: discrete cell checkboxes at (row, col).
                   New template: all checkboxes inline in merged cell t0.cell(3,0).
                   Rendering only change — _tick_hrcw_checkbox() by keyword proximity.
                   Fallback: wah_applicable on any task also ticks falling_2m.

  Step table T1:   8 columns.
                   Col 7 = Hold Point / Stop-Work Trigger.
                   CCVS code appended bold grey at bottom of col 7 cell,
                   beneath stop-work triggers.
                   CCVS code does NOT appear as a column in T2.

  Monitoring T2:   Stays at 5 columns as designed in template.
                   No template file editing required.
                   Skip rule = N/A CCVS code only.
                   Null monitoring object = dash placeholders, not skip row.

  Prerequisites T9: Replaces two old tables (_fill_requirements_table
                   and _fill_legislation_table).
                   Max 6 bullets per cell. Concise format.
                   Hazmat: name + SDS reference + one control note only.
                   Plant: names only + one-word cert note.
                   Legislation: primary acts only, max 4 lines.
                   No WAH RA form in T9 — that belongs in controls column.

  BytesIO:         render_swms_document() returns io.BytesIO.
                   Both api/main.py callers updated to call buf.read().

───────────────────────────────────────────────────────────────

ITEM 6 — Plain English pass (schedule after rendering audit)
File: core/validate.py or agents/assembler.py (one function, one session)

The SWMS_Workflow_And_Standard.docx (WorkCover NSW) requires plain language.
Haiku agents produce formal language variants despite prompt instructions.
A post-generation find-replace pass closes this gap without touching the agents.

Word substitution list (from standard):
  commence  → start
  utilise   → use
  prior to  → before
  inspect   → check
  rectify   → fix

Function: _plain_english_pass(tasks: list[TaskBlock]) → list[TaskBlock]
Runs after assembler, before renderer. High return for effort.

Current state: Fog score cap (20) and vocab enforcement (swms_vocabulary.py)
provide partial plain English control. Word substitution is the missing layer.

For platform conversations (Item 8), a safety officer opening a sample SWMS
will spot formal language immediately. It is disqualifying.

═══════════════════════════════════════════════════════════════
MEDIUM TERM — ITEMS 7 AND 8
═══════════════════════════════════════════════════════════════

ITEM 7 — SDK packaging
gatekeeper_sdk/ with clean __init__.py.
Generation functions already take plain dicts, return plain dicts.
/generate/stream is the right external primitive.
Do after flow and renderer are solid.

ITEM 8 — Platform conversations
Procore ANZ, Hammertech, Donesafe — opportunistic.
Streaming progress + plain English output + clean T9 = credible demo.

═══════════════════════════════════════════════════════════════
FULL SEQUENCE
═══════════════════════════════════════════════════════════════

  1  Commit 1 — Streaming switch (app.html only)
  2  Commit 2 — PDF fallback (app.html + main.py)
  3  Mode 04 reality check — no code, one pass
  4  Mode 04 gap close — fix only what is missing
  5  Rendering audit — docx_renderer.py, one session
  6  Plain English pass — one function, one file
  7  SDK packaging
  8  Platform conversations

═══════════════════════════════════════════════════════════════
KNOWN PRE-EXISTING ISSUES (do not fix in passing)
═══════════════════════════════════════════════════════════════

A. CCVS mismatch: generate.py score-based (WAH-H6) vs
   control_writer.py sub-codes (WAH-H1 to WAH-H8). Schedule separately.
B. Stream CCVS suppression runs after yield — never reaches client.
C. Legacy POST /generate has no auth guard. Schedule separately.
D. No stream timeout. reader.cancel() on error is sufficient for now.

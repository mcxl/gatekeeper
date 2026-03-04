# Gatekeeper — Project Status
**Last updated:** 2026-03-04
**Owner:** Alan Richardson — Robertson's Remedial and Painting Pty Ltd
**System:** Gatekeeper v1.0 — SWMS Generator v16.4

---

## Core Engine — Complete and Working

| Component | File | Status |
|-----------|------|--------|
| Validation suite (12 checks) | `core/validate.py` | COMPLETE |
| Claude API generation | `core/generate.py` | COMPLETE |
| Library lookup + fallback | `core/library.py` | COMPLETE |
| Data schema (Pydantic) | `core/schema.py` | COMPLETE |
| Audit logging | `core/audit.py` | COMPLETE |
| CLI entry point | `main.py` | COMPLETE |
| DOCX renderer | `renderers/docx_renderer.py` | COMPLETE |
| Markdown renderer | `renderers/md_renderer.py` | COMPLETE |

### Validation checks (core/validate.py)
1. Schema — Pydantic construction
2. CCVS code integrity — codes must not appear in bullet text
3. Responsibility integrity — role names must not appear in controls/admin/ppe
4. WAH rule — wah_applicable tasks must have exact WAH sentence in controls[0]
5. One-control rule — warns on stacked controls (em dash or semicolon)
6. Word cap — hard 18 words, soft 12 words per bullet
7. Comma/semicolon — semicolons hard fail; 2+ commas warn
8. Verb-first — warns if first word not in approved verb list
9. Fog score — Gunning Fog hard cap 14 (controls/admin/hold_points), 16 (stop_work); PPE exempt
10. Vocabulary — warns on banned phrases
11. Section count — hold_points 2–10, controls 3–25, stop_work 2–10
12. Responsibility length — warns if obligation exceeds 10 words

---

## Database State

**File:** `db/gatekeeper.db`
**Total tasks:** 74 (as of 2026-03-04, run 2 complete)

### Library tasks (Tasks 1–37, version 1.0)
- Source: `src/SWMS_TASK_LIBRARY.md` → seeded via `db/seed.py`
- Approved: **37/37**
- Passing validation: **25/37**
- Needing remediation: **12/37** — all Check 9 (fog score)
- Remediation list: `db/remediation_needed.md`

### AI-generated tasks (Task 38+)
- Task 38: "Crack Stitching with Thor Helical Bars" — approved by Alan, 2026-03-04

### Reference-seeded tasks (version ref-1.0) — RUN 2 COMPLETE
- **36 draft tasks** saved (IDs 39–74, status=draft, approved=0)
- Source: `db/seed_from_references.py` processing 10 priority CoPs
- Failures logged: `db/reference_seed_failures.txt` (74 failures)

#### Run 2 per-PDF breakdown
| PDF | Extracted | Saved |
|-----|-----------|-------|
| Construction-work-COP.pdf | 16 | 10 |
| Managing-the-risk-of-falls-at-workplaces-COP.pdf | 11 | 3 |
| guide_to_managing_risks_of_industrial_rope_access_systems.pdf | 11 | 2 |
| Managing-electrical-risks-in-the-workplace-COP.pdf | 16 | 7 |
| model_cop_elevatingworkplatforms-december2025.pdf | 11 | 7 |
| guide-suspended-swing-stage-scaffolds.pdf | 15 | 0 |
| Excavation-work-COP.pdf | 9 | 2 |
| model-code-practice-managing-risk-falls-workplaces.pdf | 13 | 2 |
| model_code_of_practice-managing-risks-respirable-crystalline-silica.pdf | — | SKIP (filename fixed) |
| How-to-safely-remove-asbestos-COP.pdf | 13 | 3 |
| **TOTAL** | **115** | **36** |

#### Dominant failure patterns (run 2)
- **Check 9 (fog)** — "reasonably practicable", multi-syllable domain terms
  (asbestos, assessor, removalist, excavation, electrical) consistently fail
- **Check 4 (WAH sentence)** — swing stage and falls planning tasks
  (wah_applicable=True but WAH sentence safety net not injecting correctly)
- Swing stage COP: 0 saved — all tasks are WAH with Check 4 failure

---

## 12 Tasks Requiring Remediation

All fail Check 9 (fog). Edit bullets in `SWMS_TASK_LIBRARY.md` and reseed,
or update directly in the DB. Run `python main.py score <id>` to confirm.

| Task ID | Task Name | Fog Score |
|---------|-----------|-----------|
| 2 | Fall Restraint — Plant or Equipment Maintenance | 16.9 |
| 7 | Roof Work — Fragile or Unprotected Roof | 16.9 |
| 11 | Electrical Isolation — Maintenance or Construction | 18.2 |
| 18 | Structural Demolition or Removal | 28.2 |
| 19 | Temporary Works — Propping, Shoring, or Formwork | 23.2 |
| 21 | Confined Space Entry | 19.3 |
| 23 | Gravity Stored Energy — Suspended Loads or Counterweights | 16.0 |
| 28 | Pre-Work Asbestos Assessment | 16.9 |
| 29 | Lead Paint — Surface Preparation or Removal | 18.2 |
| 32 | Chemical Application — Solvents, Coatings, or Adhesives | 18.2 |
| 35 | Waterproofing Membrane Application | 18.2 / 22.7 |
| 37 | High-Pressure Washing — Petrol-Driven Unit | 18.2 |

Full details with offending bullets: `db/remediation_needed.md`

---

## Next Actions — Priority Order

### 1. Review and approve reference-seeded tasks
```bash
python main.py list --status draft
python main.py score <id>           # check each before approving
python main.py approve <id> --user Alan
```
Batch approve all that score clean. Reject any with content errors.
36 tasks to review (IDs 39–74).

### 2. Run silica CoP (filename now fixed)
Filename corrected in `db/seed_from_references.py`:
`model_code_of_practice-managing-risks-respirable-crystalline-silica.pdf`
```bash
python db/seed_from_references.py   # will now pick up silica CoP
```

### 3. Remediate the 12 failing library tasks
Edit offending bullets in `src/SWMS_TASK_LIBRARY.md` to reduce fog score.
Target: shorten sentences, split complex bullets, use 1-2 syllable words.
Then:
```bash
rm db/gatekeeper.db && python db/init_db.py && python db/seed.py
python main.py score <id>           # confirm each fixed task
```

### 4. Investigate WAH safety net failure
Swing stage guide (0/15 saved) and falls planning CoP both failing Check 4
despite WAH injection in `dict_to_taskblock()`. Likely a whitespace or
strip mismatch between `WAH_SENTENCE` constant and validate.py comparison.
Debug: `python main.py score 39` on a WAH draft task.

### 5. Process remaining reference PDFs
Run `db/seed_from_references.py` against the other 38 PDFs in `docs/references/`.
Prioritise: `Demolition-Work-CoP.pdf`, `Hazardous-manual-tasks-COP.pdf`,
`Managing Risks of Hazardous Chemicals in the Workplace CoP.pdf`

### 6. Build Phase 2 — Risk Register integration
Risk register outputs drive SWMS task selection automatically.
See `CLAUDE.md` → Governance Flow for full architecture.

---

## Key Commands Reference

```bash
# Generate a new SWMS task (library lookup → AI fallback → save draft)
python main.py generate "Task Name" --output both

# List tasks by status
python main.py list
python main.py list --status draft
python main.py list --status approved

# Score a task against the validator
python main.py score <id>

# Approve a draft task
python main.py approve <id> --user Alan

# Reseed the library from SWMS_TASK_LIBRARY.md
python main.py seed

# Seed from WHS reference PDFs (10 priority files)
python db/seed_from_references.py

# Re-run remediation report
python db/remediation_report.py

# Verify API key
python -c "from dotenv import load_dotenv; import os; load_dotenv(); k=os.getenv('ANTHROPIC_API_KEY',''); print('OK' if k.startswith('sk-ant') else 'MISSING')"
```

---

## Reference Documents

**48 WHS PDFs** in `docs/references/` — SafeWork NSW Codes of Practice,
ISO standards, and industry guides.

**Key governance docs in `src/`:**
- `SWMS_TASK_LIBRARY.md` — 37 pre-written task dicts (canonical source)
- `SWMS_GENERATOR_MASTER_v16_0.md` — generation rules and code system
- `SWMS_METHODOLOGY.md` — nine-step decision logic v16.3
- `SWMS_OPERATOR_GUIDE.md` — setup, usage, version history

---

*Gatekeeper v1.0 — SWMS Generator v16.4*
*Robertson's Remedial and Painting Pty Ltd — Sydney NSW*

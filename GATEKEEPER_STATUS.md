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
**Total tasks:** 190 (as of 2026-03-04, all seeding complete)

### Summary
| Category | Count | Version | Status |
|----------|-------|---------|--------|
| v1.0 library tasks | 38 | 1.0 | All approved, 37/37 passing validation |
| AI-generated tasks | 1 | — | Task 38 — Crack Stitching, approved |
| CoP-extracted tasks | 102 | ref-1.0 | All approved (runs 1–4) |
| Industry SWMS (.doc) | 44 | industry-1.0 | All approved (45 files, 132 extracted) |
| HY procedures | 6 | hy-1.0 | All approved (14 PDFs, 78 extracted) |
| **Total approved** | **190** | — | 0 draft |

### v1.0 Library tasks (IDs 1–37)
- Source: `src/SWMS_TASK_LIBRARY.md` → seeded via `db/seed.py`
- All 37 approved, **37/37 passing validation** (fog fixes applied directly to DB 2026-03-04)

### AI-generated tasks
- Task 38: "Crack Stitching with Thor Helical Bars" — approved by Alan, 2026-03-04

### ref-1.0 CoP-extracted tasks — RUN 3 IN PROGRESS

#### Run 2 results (complete)
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
| How-to-safely-remove-asbestos-COP.pdf | 13 | 3 |
| **Run 2 TOTAL** | **115** | **36** |

#### Run 3 results (job bs4cb1es7 — COMPLETE, 36/36 approved)
| PDF | Extracted | Saved | Note |
|-----|-----------|-------|------|
| model_code_of_practice-managing-risks-respirable-crystalline-silica.pdf | 13 | 1 | |
| Demolition-Work-CoP.pdf | 17 | 5 | |
| Formwork-CoP.pdf | 12 | 3 | |
| Hazardous-manual-tasks-COP.pdf | 6 | 2 | |
| Managing Risks of Hazardous Chemicals in the Workplace CoP.pdf | 0 | 0 | No task content in first 5 chunks |
| First-aid-in-the-workplace-COP.pdf | 5 | 2 | |
| How-to-manage-and-control-asbestos-in-the-workplace-COP.pdf | 8 | 1 | |
| Managing-the-risks-of-plant-in-the-workplace-CoP.pdf | 18 | 6 | |
| Moving-plant-on-construction-sites-CoP.pdf | 22 | 16 | High yield |
| scaffolding-industry-safety-standard.pdf | 14 | 0 | API credits exhausted mid-run |
| WHS-Safe Design of Structures-CoP.pdf | 0 | 0 | API credits exhausted |
| model-code-practice-managing-psychosocial-hazards-work.pdf | 0 | 0 | API credits exhausted |
| model_code_of_practice-how_to_manage_work_health_and_safety_risks-nov24.pdf | 0 | 0 | API credits exhausted |
| **Run 3 TOTAL** | **115** | **36** | |

#### Run 4 results (COMPLETE, 6/6 approved)
| PDF | Extracted | Saved | Note |
|-----|-----------|-------|------|
| scaffolding-industry-safety-standard.pdf | 23 | 6 | |
| WHS-Safe Design of Structures-CoP.pdf | 0 | 0 | No procedure content — policy/methodology doc |
| model-code-practice-managing-psychosocial-hazards-work.pdf | 0 | 0 | No procedure content — policy doc |
| model_code_of_practice-how_to_manage_work_health_and_safety_risks-nov24.pdf | 0 | 0 | No procedure content — methodology doc |
| **Run 4 TOTAL** | **23** | **6** | |

#### Dominant failure patterns (runs 2–3)
- **Check 9 (fog)** — "reasonably practicable", multi-syllable domain terms
  (asbestos, assessor, removalist, excavation, electrical) consistently fail
- **Check 4 (WAH sentence)** — swing stage and falls planning tasks
  (wah_applicable=True but WAH sentence safety net not injecting correctly)
- Swing stage COP: 0 saved — all tasks are WAH with Check 4 failure

---

## Automation Sequence — Complete

All seeding and web interface steps are done. The system is operational.

### Completed Steps
1. **v1.0 library seeded** — 38 tasks from `SWMS_TASK_LIBRARY.md` via `db/seed.py`
2. **CoP reference seeding** — 102 tasks from 48 WHS PDFs via `db/seed_from_references.py` (runs 1–4)
3. **Industry SWMS seeding** — 44 tasks from 45 `.doc` files via `db/seed_from_industry_swms.py`
4. **HY procedure seeding** — 6 tasks from 14 HY PDFs via `db/seed_from_hy.py`
5. **FastAPI web interface** — `api/main.py` + `api/templates/index.html` — tested and working

### Run the Web Interface
```bash
python -m uvicorn api.main:app --reload --port 8000
# Then open http://localhost:8000
```
190 approved tasks available for library lookup. AI fallback for any unknown task.

---

## Future Actions — Priority Order

### 1. Investigate WAH safety net failure
Swing stage guide (0/15 saved) and falls planning CoP both failing Check 4
despite WAH injection in `dict_to_taskblock()`. Likely a whitespace or
strip mismatch between `WAH_SENTENCE` constant and validate.py comparison.
Debug: `python main.py score <wah_task_id>` on any WAH draft task.

### 2. Process remaining Tier 2 reference PDFs
- Formwork fact sheets, roof fact sheets, precast CoP
- Run `db/seed_from_references.py` after updating PRIORITY_FILES

### 3. Process HY standards (12+ PDFs — additional standards)
`reference-docs/principal-contractor-procedures/hansen-yuncken-standards/`
- 10 HYer-Standard PDFs (WAH, asbestos, cranes, demolition, electrical, etc.)
- 10 QC-HYer-Standard PDFs (concrete, facade, flooring, glazing, roofing, etc.)

### 4. Build Phase 2 — Risk Register integration
Risk register outputs drive SWMS task selection automatically.
See `CLAUDE.md` → Governance Flow for full architecture.

---

## Key Commands Reference

```bash
# Start web interface
python -m uvicorn api.main:app --reload --port 8000

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

# Seed from WHS reference PDFs
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

**HY Procedures** in `reference-docs/principal-contractor-procedures/` —
PRIMARY content authority (Hansen Yuncken). 14 procedure PDFs + 12+ standards.

**Key governance docs in `src/`:**
- `SWMS_TASK_LIBRARY.md` — 37 pre-written task dicts (canonical source)
- `SWMS_GENERATOR_MASTER_v16_0.md` — generation rules and code system
- `SWMS_METHODOLOGY.md` — nine-step decision logic v16.3
- `SWMS_OPERATOR_GUIDE.md` — setup, usage, version history

---

*Gatekeeper v1.0 — SWMS Generator v16.4*
*Robertson's Remedial and Painting Pty Ltd — Sydney NSW*

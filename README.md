![CI](https://github.com/mcxl/gatekeeper/actions/workflows/ci.yml/badge.svg)

# Gatekeeper — WHS Governance Architecture

---

## Architecture Overview

Gatekeeper is a Python-based WHS governance system that generates, validates, and renders Safe Work Method Statements (SWMS) for Australian construction sites. A controlled vocabulary (`vocab/swms_vocabulary.py`) defines canonical hazard, control, and PPE phrases; a SQLite task library stores 37 pre-approved task templates seeded from `src/SWMS_TASK_LIBRARY.md`. When a task is requested, the library layer performs fuzzy matching against approved tasks — high-confidence matches return immediately, low-confidence matches return with a warning, and misses fall back to Claude API generation. Every generated task is validated against a 12-check readability and integrity guardrail suite before being returned; all attempts are logged to an audit trail. Validated tasks can be rendered to `.docx` (A4 landscape Word table) or `.md` (structured Markdown) via the renderer layer, and the entire pipeline is accessible through a single `main.py` CLI.

---

## CLI Commands

### Generate a task document

```bash
python main.py generate "Surface Preparation" --output both
python main.py generate "Working at Height" --output docx
python main.py generate "EWP Operation" --output md
```

Outputs land in `src/outputs/`. If a library match is found (fuzzy score ≥ 85) the approved task is returned directly. Score 60–84 returns the task with a low-confidence warning. Score < 60 calls the Claude API to generate a new task (requires `ANTHROPIC_API_KEY`).

### Approve an AI-generated task

```bash
python main.py approve 42 --user "Alan"
```

Sets `status='approved'`, `approved=1`, `approved_by='Alan'`, `approved_at=now()` for task ID 42. AI-generated tasks have `approved=False` by default and will show an amber background in `.docx` and a warning banner in `.md` until approved.

### List tasks

```bash
python main.py list
python main.py list --status approved
python main.py list --status draft
```

Prints a table of `id / status / source / version / task_name`.

### Score (validate) a task

```bash
python main.py score 5
```

Loads task ID 5 from the database and runs all 12 validation checks. Prints the full validation report including any errors, warnings, and Gunning Fog scores per bullet.

### Seed the database

```bash
python main.py seed
# or directly:
python db/seed.py
```

Parses `src/SWMS_TASK_LIBRARY.md` and loads all task templates into `db/gatekeeper.db`. Safe to re-run — duplicates are skipped. To reseed from scratch, delete `db/gatekeeper.db` and re-run `python db/init_db.py` then `python db/seed.py`.

---

## Database Setup

```bash
python db/init_db.py   # create gatekeeper.db and tables
python db/seed.py      # load 37 library tasks
```

---

## Approving AI-Generated Tasks

When `generate` falls back to the Claude API, the returned task has `approved=False`. This is visible in outputs:
- `.docx` — amber row background (`FFE699`)
- `.md` — warning blockquote at the end

Review the task content, then approve:

```bash
python main.py score <task_id>    # check validation result
python main.py approve <task_id> --user "Alan"
```

After approval, re-generating the same task name will return the approved version from the library.

---

## File Structure

```
gatekeeper/
├── main.py                        ← CLI entry point
├── requirements.txt
│
├── core/
│   ├── schema.py                  ← Pydantic v2 models (TaskBlock, ValidationResult, AuditEvent)
│   ├── validate.py                ← 12-check guardrail suite (score_task / validate_task)
│   ├── generate.py                ← Claude API generation with retry + audit logging
│   ├── audit.py                   ← AuditLog persistence (log_event, get_log)
│   └── library.py                 ← Fuzzy lookup, save_task, approve_task
│
├── renderers/
│   ├── docx_renderer.py           ← TaskBlock → .docx bytes (A4 landscape table)
│   └── md_renderer.py             ← TaskBlock → Markdown string
│
├── vocab/
│   └── swms_vocabulary.py         ← Controlled vocabulary (canonical phrases)
│
├── db/
│   ├── schema.sql                 ← SQLite table definitions
│   ├── init_db.py                 ← Create gatekeeper.db
│   ├── seed.py                    ← Load SWMS_TASK_LIBRARY.md into DB
│   └── seed_from_masters.py       ← Load *_Master.txt docs via Claude API
│
├── src/
│   ├── SWMS_TASK_LIBRARY.md       ← 37 task templates (primary library source)
│   ├── SWMS_BASE_GENERAL.py       ← SWMS engine v16.4
│   ├── build_all_swms.py          ← Batch SWMS document builder
│   ├── format_swms.py             ← Post-processor (P2 normalisation, formatting)
│   ├── docx_style_standard.py     ← Shared Word formatting helpers
│   └── outputs/                   ← Generated documents land here
│
├── tests/
│   ├── test_validate.py           ← 12 validation engine tests
│   └── test_renderers.py          ← 5 renderer tests
│
└── docs/
    └── references/                ← SafeWork NSW Codes of Practice, ISO standards
```

---

## Regulatory Framework

WHS Act 2011 (NSW) · WHS Regulation 2017 (NSW) · SafeWork NSW Codes of Practice
All SWMS content authority: Hansen Yuncken procedures → SafeWork NSW → RPD internal standards

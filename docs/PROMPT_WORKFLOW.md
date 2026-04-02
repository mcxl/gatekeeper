# Prompt Workflow

Local developer tool for generating paste-ready Claude Code session prompts.

## File locations

| What | Where |
|------|-------|
| Templates | `prompts/session_templates/*.md` |
| Partials | `prompts/partials/_*.md` |
| Job briefs | `job_briefs/*.json` |
| Generator | `scripts/make_prompt.py` |

## Placeholder syntax

- `{{field}}` — replaced with the matching field from the job brief JSON
- `{{>partial_name}}` — replaced with the content of `prompts/partials/_partial_name.md`

Partials are resolved first, then field placeholders.

## Array rendering

- `scope_modifiers` → comma-separated inline
- `quick_scan_focus` → bulleted list (one per line)
- `batch_jobs` → bulleted list (one per line)
- Other arrays → comma-separated

## Usage

```bash
# List available templates and briefs
python scripts/make_prompt.py --list

# Dry run — check which fields are present/missing
python scripts/make_prompt.py -t next_pilot_job -b job_briefs/urban_flow_plumbing.json --dry-run

# Generate full prompt to stdout
python scripts/make_prompt.py -t next_pilot_job -b job_briefs/urban_flow_plumbing.json

# Pipe to clipboard (Git Bash on Windows)
python scripts/make_prompt.py -t next_pilot_job -b job_briefs/urban_flow_plumbing.json | clip
```

## What --list shows

- All templates by name
- All partials by name
- All briefs with customer, job type, and run count

## What --dry-run shows

- Each placeholder in the template
- Whether the brief has a matching field
- A preview of the value
- Whether the render would succeed or fail

## Brief metadata

After a successful (non-dry-run) generation:
- `last_used` is updated to the current UTC timestamp
- `jobs_run` is incremented by 1

## Adding a new job

1. Create `job_briefs/your_job.json` with required fields
2. Run `--dry-run` to verify all fields present
3. Run full generation and paste into Claude Code

---

## Batch Comparison Harness

Developer tool for running multiple job briefs through the pipeline and producing a structured comparison report.

### Usage

```bash
# Run all briefs
python scripts/run_batch_harness.py --all

# Run specific briefs
python scripts/run_batch_harness.py job_briefs/c01_unitas_roofing.json job_briefs/c08_podium_slab.json

# Dry run — list jobs without running
python scripts/run_batch_harness.py --all --dry-run
```

### Output

Reports are written to:
- `src/outputs/batch_comparison_latest.json` — machine-readable
- `src/outputs/batch_comparison_latest.md` — human-readable table

### What the report contains

Per job: brief ID, customer, job type, task count, validator status, gate FAIL/REVIEW counts, notable flags, elapsed time.

Summary: validator status breakdown, total gate FAIL/REVIEW counts, zero-FAIL job count, averages, most-FAILs job.

### When to use

- Before/after model or prompt changes — compare gate results
- Regression check across all pilot jobs
- Quick health check of the current pipeline

---

## JSON Fixtures for Deterministic Testing

Pipeline output fixtures in `tests/fixtures/pipeline_outputs/` enable fast issue-gate and CCVS-correction testing without LLM calls.

### Where fixtures live

- `tests/fixtures/pipeline_outputs/*.json` — saved task lists from pilot jobs
- Each fixture has `label`, `job_type`, and `tasks` array

### When to use fixture-based tests

- Testing issue gate check logic (C1-C33)
- Testing `_correct_ccvs_by_task_type()` keyword coverage
- Testing `_task_phase_score()` sequence logic
- Testing unsupported-controls scope-awareness
- Any deterministic logic that operates on task dicts

### Parallel test execution

pytest-xdist is installed for parallel execution:

```bash
# Normal sequential run
pytest

# Parallel with auto-detected workers
pytest -n auto

# Parallel with specific worker count
pytest -n 4
```

All tests are compatible with both sequential and parallel execution.

---

## Consultant Edit Capture

Compares generated SWMS docx to the consultant-reviewed docx and stores structured edit signals.

### How it works

1. Consultant generates a SWMS via Safe Method
2. Consultant opens the docx in Microsoft Word and makes edits
3. Consultant uploads both the original and reviewed docx to `/v1/swms/capture-edits`
4. The system extracts task tables from both documents
5. Computes row-by-row edit delta (similarity ratio, changed tasks, changed responsibilities)
6. Stores only structured edit signals — **no raw document content is stored**

### What is stored in `src/data/consultant_edits.jsonl`

Each record contains:
- `job_id` — opaque internal identifier
- `captured_at` — ISO timestamp
- `review_duration_mins` — time spent reviewing
- `would_issue` — boolean
- `main_edit_categories` — normalized list
- `changed_task_count`, `total_task_count`
- `average_similarity_ratio`
- `changed_responsibilities_count`
- `major_rewrite_detected` — true if similarity < 0.7
- `generated_doc_fingerprint`, `reviewed_doc_fingerprint` — sha256

### What is NOT stored

- Raw docx content
- Full task/control text
- Customer or project names

### Concurrency

v1 uses a module-level `threading.Lock()` for atomic JSONL append within a single process. If multi-process write concurrency is needed later, upgrade to SQLite or file-locking.

---

## Intake Normalizer v1

Creates a reviewable job-brief draft from a single text-bearing intake source, with explicit uncertainty, while keeping the core Safe Method workflow unchanged.

### What it does

- Accepts pasted text, email body, DOCX, or machine-readable PDF
- Extracts raw text and source metadata
- Produces a normalized draft artifact with field-level `extracted / inferred / unresolved` status
- Generates review prompts for the consultant
- Does NOT start generation — consultant review is mandatory

### Supported inputs

| Source | How |
|--------|-----|
| Pasted scope text | `source_text` form field |
| Email body | `source_text` with `source_type=email_text` |
| DOCX file | `source_file` upload |
| Machine-readable PDF | `source_file` upload |

### Not supported in v1

- Scanned/image PDFs (returns `extraction_insufficient`)
- OCR rescue
- Multi-document merge
- Mailbox sync
- HRCW / CCVS / risk extraction
- Automatic generation after intake

### API endpoint

```
POST /v1/swms/intake

Form fields:
  source_text: str (optional — pasted text)
  source_file: UploadFile (optional — DOCX or PDF)
  source_type: str (default: pasted_text)
  source_label: str (optional filename/label)
  clarification_note: str (optional short note)

Returns: JSON intake artifact with job_brief_draft
```

### Limits

| Limit | Value |
|-------|-------|
| Max file size | 10 MB |
| Max PDF pages | 10 |
| Min useful text | 50 chars |
| Max text chars | 50,000 (truncated with warning) |

### Known PDF limitations

- Only machine-readable (text-layer) PDFs are supported
- Scanned/image PDFs will return `extraction_insufficient`
- If PDF text is weak, the user should paste the scope section manually

---

## Project Requirements Intake v1

Creates a reviewable project rule pack from a single text-bearing source, with explicit uncertainty, while keeping the core Safe Method workflow unchanged.

### What it does

- Accepts project requirements text, DOCX, or machine-readable PDF
- Extracts structured project rules: HRCW categories, site constraints, hold points, permits, PPE rules, induction rules, named authorities
- Produces a draft rule pack with field-level extracted/inferred/unresolved status
- Generates review prompts for the consultant/admin
- Does NOT activate any rules or approve/reject SWMS — human review is mandatory

### What it does NOT do

- Automatic SWMS approval decisions
- Full compliance/policy management
- Multi-document reconciliation
- OCR for scanned PDFs
- HRCW/CCVS/risk inference (those remain in the generation pipeline)

### API endpoint

```
POST /v1/project/requirements

Form fields:
  source_text: str (optional — pasted text)
  source_file: UploadFile (optional — DOCX or PDF)
  source_type: str (default: pasted_text)
  source_label: str (optional)
  clarification_note: str (optional)

Returns: JSON project rule pack artifact (status: draft)
```

### Downstream use

The project rule pack is designed to be used later by the SWMS Review Engine to compare subcontractor SWMS against principal contractor requirements. The pack must be reviewed and confirmed before use.

---

## Procore Webhook Spike — Phase 1

Bounded spike proving one Procore-triggered SWMS pre-screen review path.

### What it proves

1. Safe Method can receive a Procore submittal event
2. Identify and extract an uploaded SWMS PDF
3. Load a project-specific rule pack
4. Run a bounded pre-screen review
5. Return a structured reviewer-facing artifact
6. Repeat reliably with idempotency protection

### Chosen Procore surface

**Submittals** — the natural fit for subcontractor SWMS submission in Australian construction.

### What it does NOT do

- Autonomous approval
- Multi-surface support
- Resubmission comparison
- Amendment generation
- OCR for scanned PDFs
- Full Procore app productization

### Phase 1 status

- **Part A (recorded/simulated payloads):** Complete. Tests, fixtures, contract validation all working.
- **Part B (live Procore sandbox):** Not connected. Endpoint is ready; requires Procore sandbox credentials and webhook registration.

### API endpoint

```
POST /v1/procore/webhook

Receives raw JSON payload from Procore webhook.
Validates signature (if PROCORE_WEBHOOK_SECRET configured).
Processes submittal events only.
Returns structured review artifact.
```

### Status vocabulary (restricted)

- Ready for Human Review
- Return for Amendment
- Escalate

Never uses: Approved, Accepted, Compliant, Passed.

### Project rule packs

Stored at: `src/data/procore_rule_packs/project_{id}.json`
Must be created and reviewed before webhook processing works for a project.

### Phase 1B: Live sandbox connection

Phase 1B adds live Procore API connectivity for the Submittals surface.

#### Required environment variables

| Variable | Purpose |
|----------|---------|
| `PROCORE_WEBHOOK_SECRET` | HMAC-SHA256 secret for webhook signature validation |
| `PROCORE_ACCESS_TOKEN` | OAuth2 bearer token for API calls |
| `PROCORE_CLIENT_ID` | Procore app client ID (used to detect live config) |
| `PROCORE_CLIENT_SECRET` | Procore app client secret |
| `PROCORE_COMPANY_ID` | Procore company ID (sent as header) |
| `PROCORE_BASE_URL` | Base URL (default: `https://sandbox.procore.com`) |
| `PROCORE_API_URL` | API URL (default: `https://sandbox.procore.com/rest/v1.1`) |

#### How webhook registration works

1. Register the webhook URL (`{your-domain}/v1/procore/webhook`) in Procore App Management
2. Select the Submittals trigger: `submittals.submittal_logs.created`
3. Configure the webhook secret and set `PROCORE_WEBHOOK_SECRET`
4. Create a project rule pack at `src/data/procore_rule_packs/project_{id}.json`

#### Retrieval modes

| Mode | When used |
|------|-----------|
| `live_api` | `PROCORE_ACCESS_TOKEN` + `PROCORE_CLIENT_ID` configured, attachment URL present |
| `simulated` | `_simulated_swms_text` field in payload (testing) |
| `fixture` | `_fixture_pdf_text_path` field in payload (local dev) |

#### Return path

When in `live_api` mode, a formatted review comment is posted back to the Procore submittal log. The comment is advisory only and does not change submittal status.

#### What remains after Phase 1B

- Production OAuth2 token refresh (currently uses static token)
- Procore sandbox webhook registration (requires Procore developer account)
- Multi-project rule pack management UI
- Additional Procore surfaces beyond Submittals

### Phase 2: Review-first workflow

Phase 2 adds a structured principal-contractor review workflow layer on top of the webhook path.

#### What Phase 2 adds

- **Workflow states:** `reviewed_pending_human`, `returned_for_amendment_recommended`, `escalated_for_attention`
- **Prioritized amendments:** mandatory-first ordering, priority numbers, capped at 5
- **Project-specific mismatch separation:** clearly separated from generic structural findings
- **Version identifiers:** `document_fingerprint`, `reviewed_at`, `job_id` for later comparison
- **Explicit rule-pack-available flag:** clear when structural review only (no project pack)
- **Review version 2.0 artifact contract**

#### Workflow states (restricted)

| State | Meaning |
|-------|---------|
| `reviewed_pending_human` | Pre-screen complete, awaiting human reviewer decision |
| `returned_for_amendment_recommended` | System recommends return for subcontractor amendment |
| `escalated_for_attention` | Requires escalation to senior reviewer/safety team |

Never uses: approved, accepted, compliant, passed.

#### How project rule packs affect the review

- If a rule pack exists for the project, project-specific rules are checked and mismatches reported separately
- If no rule pack exists, structural review still runs but `project_rule_pack_available` is false
- Rule packs are stored at `src/data/procore_rule_packs/project_{id}.json`

#### Phase 2 refinements

- **Workflow state precedence:** LOW confidence -> escalated; high/hrcw_gap -> escalated; amendments -> returned; else -> reviewed_pending_human
- **Controlled basis vocabulary:** issue_gate_check, project_rule, structural_defect, hrcw_gap, reviewer_judgment
- **Deterministic amendment ordering:** severity -> basis reliability -> source order
- **Top-5 visible amendments:** `suppressed_issue_count` tracks hidden overflow
- **project_review_status:** AVAILABLE | PARTIAL | UNAVAILABLE
- **Stable identifiers:** review_run_id, document_hash, source_surface, source_item_id for Phase 3 comparison
- **LOW confidence escalation:** forces escalated_for_attention + strengthened disclaimer
- **Evidence rules:** evidence_ref populated for deterministic findings; null for judgment-only

#### What remains deferred

- **Resubmission comparison:** Phase 2 prepares the data shape (document_hash, review_run_id, source_item_id) but does not compare versions. Phase 3 would add version-to-version comparison.
- **Amendment template generation:** Not in scope
- **Autonomous approval:** Never in scope
- **Multi-surface support:** Submittals only

### Phase 3: Resubmission comparison

Phase 3 compares the current SWMS review against the previous reviewed version for the same Procore item.

#### What Phase 3 adds

- **Issue classification:** fixed_issues, still_open_issues, new_issues
- **Stable issue matching:** exact issue_key (Tier 1), fuzzy title+reason (Tier 2)
- **Conservative matching:** weak matches (<0.85) stay still_open, never auto-fixed
- **Macro similarity check:** bypasses granular comparison if document is >40% different
- **Rule pack version safety:** flags when rule pack changed between reviews
- **Scope reduction detection:** flags >15% task count drop
- **Regression detection:** has_regression when new mandatory/high issues appear
- **Comparison confidence:** HIGH / MEDIUM / LOW (LOW forces escalation)

#### How matching works

| Tier | Method | Threshold | Result |
|------|--------|-----------|--------|
| 1 | Exact issue_key | exact | still_open (exact match) |
| 2 | Fuzzy title+reason | >=0.85 | still_open (strong) |
| 2 | Fuzzy title+reason | >=0.50 | still_open (weak — conservative) |
| - | Unmatched previous | - | fixed |
| - | Unmatched current | - | new |

#### Key fields

- `comparison_confidence`: HIGH / MEDIUM / LOW
- `rule_pack_changed`: true if versions differ
- `scope_reduction_flag`: true if task count dropped >15%
- `document_similarity_warning`: true if macro similarity is poor
- `comparison_bypassed_as_net_new_review`: true if too different for granular comparison
- `has_regression`: true if new mandatory/high issues appeared
- `comparison_disclaimer`: always present, always advisory

---

## Rule Library Overlay v1

Lightweight normalization and annotation layer giving findings stable identifiers and consistent metadata for governance, traceability, and reporting.

### What it is

- A small static JSON taxonomy (`src/rule_library/rule_library.json`)
- A thin mapping/annotation layer (`src/rule_library/rule_library.py`)
- Additive metadata on existing findings — does not replace review logic

### What it is NOT

- Not a new decision engine
- Not a rule authoring system
- Not executable logic
- Not routing or escalation automation

### Rule ID prefixes

| Prefix | Meaning |
|--------|---------|
| `IG-xxx` | Issue gate deterministic check |
| `RV-xxx` | Reviewer judgment finding |
| `PR-xxx` | Project rule reference (future) |
| `CO-xxx` | Consultant-only (future) |

### Mapping precedence

1. `finding_key` exact match (issue gate checks)
2. Project rule `rule_id` (PR- prefix)
3. `rule_family` match (reviewer findings)
4. No match → `rule_id: null` (explicit)

### Canonical library vs project rule packs

The canonical library is separate from project-specific rule packs. Project rule packs may reference canonical `rule_id`s where applicable but are not merged into the canonical library.

### Deferred to v2

- Executable logic in the taxonomy
- Customer-editable rules
- Routing/escalation automation
- Scoring/weighting engine

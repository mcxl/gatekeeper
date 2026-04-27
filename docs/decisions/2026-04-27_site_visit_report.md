# Decision log — Site Visit Report pipeline (Phases 0–5)

Date: 2026-04-27
Branch: `feat/pims-site-visit-report`
Spec: [docs/pims_site_visit_report_spec.md](../pims_site_visit_report_spec.md)

This log captures the design choices made while building the Site Visit
Report pipeline. The spec is the contract; this log is the explanation
behind it.

---

## Phase 0 — branch hygiene + spec lock

- Cut from `main@b19b012` (PR #3 merge — Phase B–G WHS upgrade).
- The Phase H branch `feat/audit-report-visual-polish` stays on origin
  but is **not merged**; useful assets (token-walk + field-code-safe
  stitch) lift into Phase 4 explicitly.
- Spec landed as the single source of truth in commit `61e3852`. Every
  subsequent commit references it by name. Disagreement between code
  and spec is resolved in the same commit that introduces it.

---

## Phase 1 — `public.checklist_items` schema

- Drift guard verbatim from spec line 129; runs **before** any DDL so
  a pre-existing table with the wrong shape aborts the migration loudly
  rather than partially mutating into an inconsistent state.
- Post-condition assertion mirrors the drift guard; protects against a
  mid-migration crash leaving a half-built schema.
- `project_value_tier` is a CHECK-constrained enum (`'high'`, `'low'`)
  rather than a generic text. The xlsx ships two sheets keyed by tier,
  so the tier value is intrinsic to a row. CHECK enforces it cheaply
  without extra typing infrastructure.
- `item_no` is text (not int) so leading zeros and future `01a`-style
  sub-numbering survive — the spec invariant about no silent drops
  forced this when the seed pipeline encountered duplicates.
- UNIQUE `(project_value_tier, category_no, item_no)` is the natural
  key that the seed's ON CONFLICT clause keys on. One row per
  (tier, category, item).
- RLS enabled with **zero policies** — the FastAPI backend is the only
  consumer, service role bypasses RLS, anon and authenticated get
  nothing. Reference data, but RLS is on for defence-in-depth.

---

## Phase 2 — xlsx → checklist_items seed

- The seeder lives in `scripts/seed_checklist_items.py` and emits an
  idempotent migration file at
  `pims/migrations/2026-04-27_seed_checklist_items.sql`. Two-stage on
  purpose: parse + emit is reproducible, the SQL file is replayable
  via either `mcp__claude_ai_Supabase__execute_sql` or `psql`.
- ON CONFLICT (tier, category_no, item_no) DO UPDATE refreshes
  category_name / criteria / instruction. ccvs_category and ccvs_code
  are deliberately **not** in the SET list — when the xlsx grows those
  columns later, an editor's NULL for those fields shouldn't blow away
  manually populated values.
- xlsx data quirk: category 01 in both sheets has 30 rows (17 + 13)
  with restarting item numbers. Two real-world possibilities — block
  paste error in the source, or genuinely two sub-sections under the
  same category heading. The seeder side-steps the question with
  deterministic `_2` suffixing on second-and-later occurrences and a
  loud stderr warning per affected row. Spec already anticipated text
  item_no with sub-numbering ("future `01a` sub-numbering"), so `_2`
  is a fit.
- xlsx category 02 is genuinely missing from source — left as-is, not
  back-filled, not asserted away. Future cleanup noted in commit
  message and spec drift register.

---

## Phase 3 — matcher contract

- `cross_reference(items, observations) -> (results, unmatched)` is
  pure-function. No I/O, no Supabase, no httpx. Route layer fetches +
  hands in. Keeps the matcher trivially testable and the rendering
  pipeline composable for the local CLI (Phase 5).
- Worst-severity precedence with explicit rank dict
  (`compliant_unobserved=0 < compliant_verified=1 < conditional=2 <
  ncr=3`). Avoids ambiguity that an `if/elif` chain plus future state
  additions would introduce.
- Info observations match the item (so they don't go to unmatched) but
  do NOT lift state above `compliant_unobserved`. Tested in
  `test_info_only_match_stays_unobserved`. The verbatim spec language
  ("treated as informational only") needs this exact split.
- Match algorithm: `ccvs_code` equality primary, difflib ratio ≥ 0.75
  fallback. Lifted from the prior audit-report flow — the threshold
  has lived through PR #3 without complaint, no reason to retune now.
  Pinned in `test_threshold_constant_pinned` so a future tweak forces
  a spec edit.
- Determinism: fuzzy ties resolve to lowest `(category_no, item_no)`.
  The matcher must produce byte-identical output for the same inputs;
  ordering by item key is the cheapest deterministic tiebreaker.
- Every unmatched observation emits exactly **one** `log.warning(...)`
  per spec invariant #6. Tested at n=1 and n=many. The route logs
  these too via the matcher's logger.

---

## Phase 4 — renderer + route + frontend

### Module split: `pims/services/site_visit_report.py`

- New module rather than rewriting `pims/audit_report_docx.py` in
  place. The legacy module carries the Phase B–G WHS upgrade flow that
  ships under a different route (`/pims/audit-report/rpd`) and is
  still in production. Killing it in this branch was tempting (1025
  lines of dead code) but:
  1. The seed for the legacy path (`pims/audit_checklist.xlsx`) is
     also the source for the new path's `checklist_items` table, so
     deleting them together would be a coupling-loss risk.
  2. The legacy renderer uses a different template
     (`pims/audit_report_template.docx`) with Part A–D content the
     consultancy invested heavily in.
  3. The spec says "rewritten in place" but a parallel-paths
     transition through Phase 8 keeps the door open if a stakeholder
     asks for the legacy multi-site flow back.
- Phase 8 will revisit this — once the new flow is proven in
  production for ~1 week, legacy gets deleted. Captured here to make
  that future commit easy.

### Token replacement

- Two-pass walk lifted verbatim from
  `feat/audit-report-visual-polish`'s `_process_paragraph` /
  `_paragraph_field_runs`. The polish branch's investment in handling
  field-code runs (PAGE / NUMPAGES / DATE) correctly is exactly what
  this needs — naïve `paragraph.text = paragraph.text.replace(...)`
  would clobber the dynamic page-number fields that are baked into
  the template footer.
- Template inspection caught only **two** distinct tokens
  (`[Insert Site Address]` body, `[Insert Current Date]` footer) — far
  fewer than the spec's anticipatory list of seven. Spec was updated
  in the same Phase 4 commit (per spec-drift rule). The other facts
  the consultancy wanted on the cover (audit ref, tier, auditor) now
  render into the appended Site Visit Summary section instead.
- `detect_unknown_tokens()` returns the set of `[…]` placeholders left
  after substitution. The route logs these as warnings — invariant #6
  surfaced at the template-tooling layer.

### KPI block

- Six rows per spec, in spec order. Counts use **checklist items**
  (results), not raw observations, so multi-match doesn't double-count.
  This is the subtle invariant that separates a defensible WHS audit
  count from a misleading one.
- Compliance rate rounded to 1 dp with explicit `round(_, 1)` — Python
  default float repr produces 66.66666... which would be unreadable in
  a printed report.

### Cross-reference shading

- `compliant_verified` and `compliant_unobserved` deliberately share
  green (`00B050`/`FFFFFF`). Per invariant #4: the reader distinguishes
  them via the KPI block + the verbatim audit-defensibility footer,
  not via shading. This is a legal-defensibility choice — visually
  asserting "verified" for items that were never sighted would
  misrepresent the audit and undermine the report's evidentiary value.

### Audit-defensibility footer

- The verbatim string is a module-level constant
  `AUDIT_DEFENSIBILITY_FOOTER`. Tests assert it appears unchanged in
  every rendered report. Renaming the constant or editing the string
  triggers an obvious test failure rather than silent drift.

### Route shape

- `POST /pims/site-visit-report` accepts `site_id` (canonical UUID) +
  optional `audit_date_start` / `audit_date_end`. Tier resolved from
  `sites.project_value` at the $250K boundary — same logic the
  legacy flow used; no new boundary policy here.
- Observations fetched via the existing `_fetch_observations_for_site`
  helper (Codex P2 pagination work survives intact). The select-column
  list grew with the columns the appendix and auditor-label resolver
  read; pinned by the existing
  `tests/test_audit_report_routes.py::test_observation_select_columns_all_exist_in_schema`
  test.
- audit_ref resolved via a small JOIN to `pims_audits` keyed on
  observations' `audit_id`. The legacy flow had this same logic (PR #3
  P2 hotfix). Lifted into a helper rather than re-implemented.

### Frontend

- Per spec line 178: existing button reused, repointed. The label
  changed (Audit Report → Site Visit Report) and the modal switched
  from multi-select to single-select per invariant #1. Inline error
  banner kept — silent empty dropdowns were the original P1 bug
  surface.

---

## Phase 5 — local render CLI + this decision log

- `scripts/render_site_visit_report.py` pulls live PIMS data from
  Supabase via the same paginated fetch shape as the route, then
  renders to a local `.docx`. No FastAPI server needed; no Railway
  redeploy needed.
- The `--include-pending` flag is the pilot-unblocking switch: the
  pilot site `1208 Pacific Highway Pymble` has 13 observations all
  in `review_status='Pending'`, so the live route's Approved-only
  filter produces an empty cross-reference. The CLI lets QA see the
  rendered result against unapproved data while the approval flow
  catches up (Phase 6 candidate).
- This decision log captures every non-obvious call from Phases 0–5
  so a future engineer doesn't re-litigate them. Anything that's
  obvious from the code or git history is omitted; this is the
  *why*, not the *what*.

---

## Phase 6 — observation approval endpoints

- Three endpoints land in `pims/routes.py`:
  - `POST /pims/observation/{id}/approve` — single-row flip to
    `Approved`, stamps `approved_by` + `approved_at`.
  - `POST /pims/observation/{id}/reject` — single-row flip to
    `Rejected`, optional `reason` is stuffed into `monitoring_note`
    so the next reviewer sees it without us needing a new column.
    Rejected rows do NOT appear in the Site Visit Report (the route
    filters Approved-only).
  - `POST /pims/site/observations/approve-pending` — bulk filter by
    `(site_id, review_status='Pending')`, idempotent, returns the
    count. Lets a reviewer clear a backlog before generating a
    report.
- All three share `_set_observation_review_status()` for the actual
  PATCH so the audit trail stays consistent — single place that
  writes the (status, approved_by, approved_at) triple.
- `VALID_OBSERVATION_REVIEW_STATUSES` mirrors the Postgres CHECK
  constraint; the helper validates before it touches the database so
  a bad value gets a 422 from FastAPI rather than a 500 from
  Postgres.
- Tests pin: 401 on no-session, 422 on bad uuid + bad status, 404 on
  missing row, default approver "dashboard" when none supplied,
  rejection reason landing in monitoring_note with `[Rejected by X]`
  prefix, bulk-approve filter shape (`site_id=eq.X` AND
  `review_status=eq.Pending`), zero-result return path.
- The pilot site flip itself was **not** done in this commit. A
  bulk UPDATE of 13 real WHS observations to Approved stamped as
  "claude-phase-6" is the wrong audit-trail signature — that
  approver column is meant to identify the human who reviewed the
  finding. The endpoints are now in place; the actual approvals
  happen when someone authoritative runs them with their own
  identity.

---

## Phase 7 — deterministic issue gate

Per CLAUDE.md "automation priority: implement deterministic issue-gate
checks ... use those as the default internal pre-review layer before
expert/manual review". Phase 7 lands a fail-closed gate that catches
trust failures *before* the .docx leaves the route.

### Module: `pims/services/site_visit_report_gate.py`

- Pure-function `run_gate(ctx, results, unmatched, docx_bytes)` →
  `GateReport`. No I/O, no Supabase, no env reads. The route + the
  CLI both call it and react to the issues identically.
- Severity is binary — ERROR (the report has a known trust failure
  and must not ship) or WARNING (structural drift worth logging but
  not blocking). The route returns 500 on any ERROR; the CLI prints
  + exits 1 but still writes the file (developer needs to open it
  to diagnose).
- Check-id constants are part of the public contract — tests
  reference them by id so a future renaming is loud.

### Checks (run order is deterministic so issue lists diff cleanly):

1. **`unresolved_tokens`** (ERROR) — any `[Insert Foo Bar]` /
   `[Foo Bar]` placeholder still in the document. Token regex
   requires either an `Insert ` prefix or an embedded space, so the
   evidence-cell prefixes the renderer emits (`[NCR]`, `[Compliant]`)
   don't false-fire. Real template tokens always have a space.
2. **`audit_footer_present`** (ERROR) — spec invariant #5: the
   audit-defensibility footer text appears verbatim. Catches a
   future edit that paraphrases or truncates it.
3. **`compliance_rate_rendered`** (ERROR) — the compliance rate
   computed by `compute_kpis` actually appears in the document
   (formatted as `XX.X%`). Catches a renderer refactor that drops
   the row or formats it unrecognisably.
4. **`kpi_totals_internally_consistent`** (ERROR) — KPI total
   equals the sum of items in known states. Pure-function arithmetic
   sanity. Catches the case where a future fifth state slips in
   without `compute_kpis` being updated to count it.
5. **`every_result_rendered`** (ERROR) — spec invariant #6: every
   `category_no.item_no` from the matcher appears in the rendered
   cross-reference. Catches silent drops.
6. **`every_unmatched_rendered`** (ERROR / WARNING) — spec
   invariant #6: every unmatched observation's text appears in the
   appendix. WARNING (rather than ERROR) when an unmatched obs has
   no `observation_text` to anchor a check on (data quality issue,
   not a render issue).
7. **`unmatched_appendix_presence`** (ERROR / WARNING) — spec
   line 98: appendix renders IFF unmatched is non-empty. ERROR
   when unmatched is non-empty but the appendix header is missing
   (silent drop). WARNING when the header is present but unmatched
   is empty (drift).

### Wiring

- `pims/routes.py::generate_site_visit_report` — runs the gate
  after build(). Logs warnings, raises 500 with the full error
  list as the response detail. Sets `X-Issue-Gate-Warnings: <count>`
  on success so a frontend / load balancer can surface
  warning counts without parsing logs.
- `scripts/render_site_visit_report.py` — runs the gate after
  build(), prints all warnings and errors, exits 1 if any errors.
  Still writes the .docx — a developer needs the file to diagnose
  whatever the gate flagged.

### Tests

- 11 cases pinning each individual check's failure mode and the
  pass case. Plus an end-to-end matcher → renderer → gate
  integration that exercises the realistic flow with one matched
  observation and one unmatched orphan, asserting the gate passes.

---

## Open questions / Phase 8+ candidates
- **Legacy deprecation.** Once Phase 6 ships and the new flow has run
  for ~1 week, delete `pims/audit_report_docx.py`,
  `pims/audit_report_template.docx`, the
  `/pims/audit-report/rpd` route, the four legacy tests
  (`test_audit_report_reframe.py`, `test_audit_report_checklist.py`,
  `test_audit_report_docx_smoke.py`, the legacy bits of
  `test_audit_report_routes.py`). Captured here so the future commit
  is easy.
- **xlsx category 01 cleanup.** The 17 + 13 sub-block split is
  surviving in the data via `_2` suffixes. A separate xlsx-cleanup
  pass with the WHS team should resolve whether that's a single
  category with 30 items or two categories accidentally sharing a
  heading.
- **xlsx category 02 absent.** Source xlsx skips from 01 to 03.
  Confirm with WHS team whether 02 was intentional or a content gap.
- **Approval audit trail.** When a reviewer approves an observation,
  the `approved_by` and `approved_at` columns get populated. The
  Site Visit Report doesn't currently surface either. Worth adding to
  the cross-reference evidence cell once the approval flow lands.

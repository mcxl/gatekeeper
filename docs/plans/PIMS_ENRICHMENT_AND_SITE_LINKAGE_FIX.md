# PIMS Enrichment + Site Linkage — Master Fix Plan (v4)

**Date:** 2026-05-12
**Author:** Claude Code (Opus 4.7, 1M)
**Reviewer:** Codex
**Status:** Approved by Codex (v3 sign-off, DONE × 7) with three
tweaks folded in here; awaiting operator approval
**Supersedes:** v3 (same filename, earlier today)

## Changelog from v3 (responding to Codex v3 review)

- **Phase 3:** removed the `monitoring_note` provenance prefix.
  Prompt-hash and model id now logged to the backfill script log
  only, not written into a business-facing column.
- **Phase 5:** clarified that `APIStatusError.body` is structured;
  log it via safe serialisation (`json.dumps` for dict-like, `str`
  otherwise) then truncate, rather than implying string slicing.
- **Phase 7:** added a "Workflow impact — expected friction"
  subsection. The `pims_audits.site_name` fallback is load-bearing
  (field-capture `ObservationRequest` does not carry `site_address`)
  and `pims_audits.site_name` is derived from `audit_ref`, not
  guaranteed canonical. Operators should expect some legitimate
  approvals to pause until they fill `site_address` inline.

## Changelog from v2 (responding to Codex v2 review)

- **Phase 4 SQL** replaced with dry-run-then-update-by-id pattern.
  Removed broad `Russel Lea` ILIKE.
- **Phase 7** expanded to cover every live-write path:
  `/pims/upload/observations`, frontend PDF promote (replaced with a
  backend route), and a "site context required" gate on approve when
  `site_address` is blank.
- **Phase 6** changed to **poll-then-409**. `enrich_observation()` no
  longer runs inside `/staging/{id}/approve`. Idempotency rule added:
  duplicate approve returns existing observation (200), not 409.
- **Phase 5** rescoped: migrate the two PIMS raw callers to the
  installed Anthropic SDK using `APIStatusError`; no repo-wide raw-
  HTTP helper. Noted `precedent_classifier.py` is **sync** httpx.
- **Phase 5.5** expanded to also watch live data quality (orphan
  `site_id`, empty enrichment on approved rows). Slack/email plumbing
  moved to "out of scope — separate slice".
- **Phase 2** collapsed from 2a/2b/2c into a single phase with a
  decision table.
- **Targeted tests** added to every phase's exit criteria.
- Section 8 ("Asks of Codex") replaced with **Resolved decisions**
  reflecting Codex's answers.

## 0. Fastest path to restore this customer's report

If only the immediate customer impact matters and prevention work can
wait:

  **Phase 0 (done)** → **Phase 4** (back-link site_id by reviewed row
  IDs; report works immediately with empty enrichment) → **Phase 1**
  (diagnostic logging) → **Phase 2** (fix root cause) → **Phase 3**
  (backfill enrichment).

Phases 5–8 are prevention and can land over the following days.

## 1. Problem statement

Three connected failures surfaced while trying to generate reports
for site `96-98 Hampden Rd Russel Lea`:

1. **Site missing from menus.** Now inserted as
   `98896ff0-996b-44d6-b878-66c4f301226d`, `project_value=250000`,
   `active=true`,
   `client_name="Robertson's Remedial and Painting Pty Ltd"`.
2. **Enrichment never ran.** 34 staging observations submitted
   2026-05-11 21:46–22:45 UTC have `enriched=false` and empty
   enrichment fields. Railway logs show every
   `POST /v1/messages` returned **HTTP 400**. Anthropic's error body
   was not logged because `enrich_observation`
   (`pims/routes.py:238`) calls `resp.raise_for_status()` and only
   logs the status line.
3. **Site Visit Report 404.** All 34 approved observations have
   `pims_observations.site_id = NULL` because the canonical sites
   row did not exist when they were submitted. `/site-visit-report/xlsx`
   (`pims/routes.py:3130`) filters by `site_id IN (...)`.

Address inconsistency: 33 rows store *"96-98 Hampton Road, Russel
Lea"* (Hampton vs Hampden); 1 uses Hampden. New sites row uses
Hampden.

## 2. Root causes

| # | Cause | Confidence | Evidence |
|---|---|---|---|
| RC1 | **Leading hypothesis:** bare model alias `claude-haiku-4-5` in `pims/routes.py:262` and `pims/services/precedent_classifier.py:177` rejected by Anthropic API. Other working call sites use `claude-haiku-4-5-20251001`. Alternative hypotheses (oversized `system`, malformed payload, `anthropic-version` mismatch) plausible. | Hypothesis | Railway logs (status only); code grep |
| RC2 | `enrich_observation` swallows Anthropic's error body via bare `raise_for_status()`. | Confirmed | `pims/routes.py:297–299` |
| RC3 | `/staging/{id}/approve` does not check `enriched`. Failed background enrichment silently produces approved-empty rows. | Confirmed | `pims/routes.py:781`, copy at line 820 |
| RC4 | Multiple live-write paths bypass any address→site_id resolution: `approve_staging_rpd`, `/pims/upload/observations` (~`pims/routes.py:2333`), and the frontend PDF promote that calls Supabase directly (`frontend/pims_dashboard_rpd.html:3908`). Address typos compound the problem on text joins. | Confirmed | Codex review v2 |

## 3. Master plan — phased

Each phase = one coherent commit + checkpoint. Stop after each phase
for explicit operator "go".

### Phase 0 — Site row (DONE)

- [x] Insert `sites` row for `96-98 Hampden Rd Russel Lea`,
  id `98896ff0-996b-44d6-b878-66c4f301226d`.

### Phase 4 — Back-link `site_id` for affected observations (runs early)

**Goal:** make `/site-visit-report/xlsx` return rows for this site
immediately. No broad ILIKE — operator reviews exact row IDs before
write.

**Step 1 — Dry-run (read-only):**

```sql
SELECT id, site_address, observation_date, review_status
FROM pims_observations
WHERE site_id IS NULL
  AND site_address IN (
    '96-98 Hampton Road, Russel Lea',
    '96-98 Hampden Rd Russel Lea'
  )
ORDER BY observation_date;
```

Operator reviews the returned row IDs, copies the list, confirms it
matches the expected ~34 rows for this site (any unexpected entries
investigated before proceeding).

**Step 2 — Update by exact IDs only:**

```sql
UPDATE pims_observations
SET    site_id = '98896ff0-996b-44d6-b878-66c4f301226d',
       updated_at = now()
WHERE  id IN ( /* reviewed UUID list */ );
```

**Step 3 — Canonicalise address on those exact rows:**

```sql
UPDATE pims_observations
SET    site_address = '96-98 Hampden Rd Russel Lea'
WHERE  id IN ( /* same reviewed UUID list */ );

UPDATE pims_staging
SET    site_address = '96-98 Hampden Rd Russel Lea'
WHERE  id IN (
  SELECT staging_id FROM pims_observations
  WHERE id IN ( /* same reviewed UUID list */ )
);
```

(`pims_staging` has no `site_id` column — only the address is
normalised there. Pull the matching staging IDs via `staging_id` join
so we don't re-introduce a broad ILIKE.)

Verify:
- SQL: `SELECT site_id, COUNT(*) FROM pims_observations WHERE id IN
  (...) GROUP BY site_id;` → all rows show the canonical site_id.
- Generate Site Visit Report (.xlsx) for this site in the UI →
  returns a non-empty xlsx with ~34 rows (enrichment columns blank
  for now; Phase 3 fills them).

Exit criterion: report endpoint returns the file; no 404; row count
matches the reviewed ID list exactly.

### Phase 1 — Diagnose with certainty

**Goal:** capture Anthropic's actual 400 body so RC1 is confirmed
or falsified.

Changes:
- `pims/routes.py::enrich_observation`: catch
  `httpx.HTTPStatusError` separately; log `e.response.status_code`,
  `e.response.headers.get("anthropic-error-type", "")`,
  `e.response.text[:2000]` before re-raising.
- Same pattern in `pims/services/precedent_classifier.py` (note:
  sync httpx — adjust catch accordingly).

Trigger:
- Call `enrich_observation` directly from a one-off Python session
  against an existing affected staging row.

Verify:
- Read the new log line; record Anthropic's literal error string in
  the Phase 1 decision log.

Exit criterion: Anthropic's error message is in Railway logs.

### Phase 2 — Fix root cause (single phase, decision table)

**Goal:** one fix keyed off the actual Phase 1 error.

| Phase 1 error mentions | Fix |
|---|---|
| `model`, `invalid_model`, model id | New env var `PIMS_ENRICHMENT_MODEL`, default `claude-haiku-4-5-20251001`. Apply to `pims/routes.py:262` and `pims/services/precedent_classifier.py:177` (or a decoupled `PIMS_PRECEDENT_MODEL`). |
| `system`, `messages`, `max_tokens`, payload shape | Inspect the offending field. Likely candidates: oversized `ENRICHMENT_SYSTEM`, stray `cache_control` block, `max_tokens` outside model range. Fix in place. |
| `anthropic-version`, version header | Update header in both call sites to the current recommended value. Centralise via env var if changed in more than two places. |

Verify:
- Submit one fresh test observation via the live dashboard for the
  affected site.
- Within ~30s, `pims_staging.enriched=true` and
  `observation_text_enriched` populated.
- New test: `tests/test_enrichment_smoke.py` mocks the Anthropic
  response and asserts `enrich_observation` returns the expected
  parsed shape; protects against future regression.

Exit criterion: one fresh observation enriches end-to-end on
production.

### Phase 3 — Backfill the 34 affected rows

**Goal:** recover enrichment for already-approved observations.

**Hard constraint:** must **not** touch `site_id` or `site_address`
on either table (Phase 4 owns those columns).

New script: `scripts/backfill_pims_enrichment.py`

Behaviour:
1. Accepts `--site-id <uuid>` or `--ids id1,id2,...` and `--dry-run`.
2. Selects `pims_staging` rows where filter matches AND
   `enriched=false`.
3. Pins `PIMS_ENRICHMENT_MODEL` explicitly. Provenance
   (sha256 of `ENRICHMENT_SYSTEM`, model id, script version) is
   written to the **backfill script log only** — never into
   `monitoring_note` or any other business-facing column. The log
   line is sufficient to trace which row was enriched with which
   prompt/model snapshot if questions arise.
4. For each row:
   - Call live `enrich_observation(observation_text)`.
   - PATCH staging row with enrichment columns +
     `enriched=true, enriched_at=now()`.
   - PATCH matching `pims_observations` row by `staging_id` with
     the same enrichment columns. Do **not** touch `review_status`,
     `approved_by`, `approved_at`, `staging`, `site_id`, `site_address`.
5. On `--dry-run`, prints intended writes without executing.

Verify:
- Dry-run for the 34 affected rows. Spot-check one row's planned
  payload manually.
- Real run.
- Section 6 enrichment health SQL → 34 rows `enriched=true` in both
  tables.
- Regenerate audit report — confirm enrichment columns populate.
- New test: `tests/test_backfill_enrichment.py` runs the script
  against a fixture with mocked Anthropic; asserts only enrichment
  columns are written, and `site_id`/`site_address` untouched.

Exit criterion: all 34 rows enriched in both tables; report renders
with rich text.

### Phase 5 — Prevention 1: migrate PIMS Anthropic callers to the SDK

**Goal:** structured error bodies on every Anthropic failure via the
installed SDK, no hand-rolled `httpx` plumbing. Scope strictly to
the two PIMS call sites.

Changes:
- `pims/routes.py::enrich_observation` (async): use
  `anthropic.AsyncAnthropic().messages.create(...)`. Catch
  `anthropic.APIStatusError`; log `e.status_code`,
  `e.response.headers.get("anthropic-error-type", "")`, and a safely-
  serialised body before re-raising. `APIStatusError.body` is
  structured (dict-like) — serialise via `json.dumps(e.body,
  default=str)` if dict-like, fall back to `str(e.body)` otherwise,
  then truncate to ~2KB.
- `pims/services/precedent_classifier.py` (sync — confirmed at
  `precedent_classifier.py:168`): use
  `anthropic.Anthropic().messages.create(...)`. Same error handling.
- Both pull model id from `PIMS_ENRICHMENT_MODEL` /
  `PIMS_PRECEDENT_MODEL` (Phase 2).

Out of scope: all *other* Anthropic callers in the repo (e.g.
`pims/audit_report_docx.py`, `core/document_extractor.py`). They
already use the dated model id and have not produced this incident;
migrate later if a recurrence motivates it.

Verify:
- Force one Anthropic 400 (bogus model id) → log shows status,
  error-type, body in one line.
- Grep confirms no `raise_for_status()` against Anthropic in the
  two changed files.

Exit criterion: any future Anthropic 4xx from these two callers
leaves a useful log line in one read of Railway logs.

### Phase 5.5 — Observability: silent-failure detection

**Goal:** broken enrichment and orphan rows surface within 1 hour
without manual SQL. Covers **both** staging staleness *and* live
data quality.

Three queries surfaced as dashboard chips:

```sql
-- Stale un-enriched staging
SELECT COUNT(*) FROM pims_staging
WHERE enriched=false AND submitted_at < now() - interval '1 hour';

-- Live data quality: orphan site_id on approved rows
SELECT COUNT(*) FROM pims_observations
WHERE review_status='Approved' AND site_id IS NULL;

-- Live data quality: empty enrichment on approved rows
SELECT COUNT(*) FROM pims_observations
WHERE review_status='Approved'
  AND (observation_text_enriched IS NULL OR observation_text_enriched = '');
```

UI:
- Three header chips in the operator dashboard, each clickable to
  filter the relevant table to the offending rows.
- Tooltip shows the underlying query.

Out of scope for this phase (separate slice): Slack / email
alerting plumbing. Add only if the team already has the pipeline.

Verify:
- Force one enrichment failure (bogus key in a test env); chip
  appears within 1h.
- Insert a synthetic approved row with `site_id=NULL`; chip
  increments.

Exit criterion: each of the three counts is queryable from the
dashboard.

### Phase 6 — Prevention 2: approve-time enrichment guard (poll-then-409)

**Goal:** silent enrichment failure cannot become an approved-empty
row, without putting `enrich_observation()` inside the approve
endpoint.

Design:
- New env var `PIMS_APPROVE_ENRICHMENT_GUARD` (default `on`).
  Operator kill-switch.
- `POST /staging/{id}/approve` when guard is on:
  1. **Idempotency check first:** if an approved
     `pims_observations` row already exists for this `staging_id`,
     return that row with **200** (covers double-click and
     approve/retry races).
  2. If `staging.enriched == true`: promote as today.
  3. If `staging.enriched == false`:
     - Poll the staging row up to 3× over 5s (1s sleep). Catches
       background task finishing between submit and approve.
     - If still `enriched=false`: return **409 Conflict** with
       `detail = "Enrichment not yet complete. POST /staging/{id}/
       retry-enrichment then approve."`.
     - **Do not** call `enrich_observation` inside this endpoint.
- New endpoint `POST /staging/{id}/retry-enrichment` (auth same as
  approve): re-runs `enrich_observation`; patches staging row;
  returns the updated row. This is the *only* place approve-path
  callers trigger enrichment work.
- Guard off (`PIMS_APPROVE_ENRICHMENT_GUARD=off`): legacy behaviour
  (promote regardless). For outage windows only.

Bulk approval: dashboard's "approve all" iterates per row,
collecting a summary ("28 approved, 6 need retry"). Failed rows get
a one-click bulk retry that calls `/retry-enrichment` for each, then
re-issues approve.

Frontend (small slice):
- Status pill on staging rows: `enriched ✓` / `pending` / `failed ↻`.
- Show Anthropic error summary (from staging row's `monitoring_note`
  if populated) on hover.

Verify:
- Test 1 (happy path): submit → wait 30s → approve → fast, no extra
  latency.
- Test 2 (race): submit → approve within 2s → guard polls → approve
  succeeds once enrichment lands.
- Test 3 (true failure): bogus API key → submit → approve → 409 with
  clear message. Restore key. Retry → enriches. Approve → 200.
- Test 4 (idempotency): approve a row twice in quick succession →
  second call returns 200 with the same observation, not 409 or
  duplicate insert.
- New tests in `tests/test_approve_staging.py` covering tests 1–4 with
  mocked Supabase + Anthropic.

Exit criterion: simulated enrichment failure cannot result in an
approved row with empty enrichment fields; routine approvals do not
feel slower; duplicate-click is idempotent.

### Phase 7 — Prevention 3: site resolver on every live-write path (no DDL)

**Goal:** every backend path that can create a live observation row
runs through one address→site_id resolver. No live-write paths
bypass the resolver.

Changes:

1. **Helper:** `services/site_resolver.py`:
   ```
   def resolve_site_id(address_raw: str) -> Optional[str]: ...
   ```
   - Canonicalise: lowercase, collapse whitespace, strip trailing
     punctuation, apply alias dict (initial seed: `hampton →
     hampden`; expanded by Phase 8).
   - Query `public.sites` where `active=true`; match canonicalised
     `address_raw`.
   - Precedence: exact canonical match wins; otherwise return
     `None`. Do not guess.
   - Return `None` on no match or ambiguity.

2. **`pims/routes.py::approve_staging_rpd`:**
   - If `staging.site_address` is blank or null → return **409**
     `"Site address required before approve. Set it in the staging
     dashboard, then retry."` *unless* the joined
     `pims_audits.site_name` resolves unambiguously, in which case
     use that.
   - Call `resolve_site_id`; include `site_id` in `obs_row` if
     resolved.

3. **`pims/routes.py::upload_observations` (~line 2333):**
   - On direct inserts to `pims_observations`, call resolver and
     include `site_id` in the insert payload.

4. **Frontend PDF promote replacement (most invasive change):**
   - Today: `frontend/pims_dashboard_rpd.html:3908` calls Supabase
     directly with `update({staging: false})`, bypassing all backend
     logic.
   - Replace with a backend route `POST /pdf-observation/{id}/promote`
     that:
     - Pulls the row.
     - Calls `resolve_site_id`.
     - Applies the same idempotency check and (optionally) the same
       guard as Phase 6.
     - Performs the `staging=false` update server-side.
   - Frontend calls the new route instead of Supabase directly.

**Hard rule:** the new `POST /pdf-observation/{id}/promote` route is
the **only** supported promotion path. The old direct-Supabase
helper in the frontend must be removed in the same commit; a
grep-based exit check guards against accidental survival.

Verify:
- Unit tests `tests/test_site_resolver.py`:
  - exact match → site_id
  - Hampton/Hampden alias → site_id
  - two active sites match canonical → None
  - empty/None input → None
- Integration:
  - approve a fresh row → observation has `site_id`.
  - upload via `/pims/upload/observations` → row has `site_id`.
  - PDF promote via new route → row has `site_id`.
- Frontend grep: `grep -n "update.*staging.*false" frontend/` and
  `grep -n "from('pims_observations')" frontend/` return no
  remaining direct-Supabase mutation paths to `pims_observations`.

Exit criterion: 100% of new live rows for known sites have
`site_id` set, regardless of which path created them; the
direct-Supabase mutation path is gone from the frontend.

### Workflow impact — expected friction

The approve gate is a **deliberate workflow change**, not just a
data-integrity check. Operators should expect some legitimate
approvals to pause until the address is filled in. Two upstream
facts make this load-bearing:

1. **Field-capture submissions do not carry `site_address`.**
   `ObservationRequest` (`pims/routes.py:130`) has no field for it
   and `insert_staging` (`pims/routes.py:577`) does not populate
   one. So most staging rows arrive blank and rely on the
   `pims_audits.site_name` fallback.
2. **`pims_audits.site_name` is derived from `audit_ref`**
   (`pims/routes.py:528`), not guaranteed canonical. Audit refs
   containing nicknames, shorthand, or unusual formatting will not
   resolve via the alias table, and the gate will return 409.

Mitigations available today:
- The staging dashboard already supports inline `site_address`
  edits (`frontend/pims_dashboard_rpd.html:3681, 3834`). Operators
  fill in the canonical address, then retry approve.

Permanent fix (out of scope for this plan, recommended follow-up):
- Capture canonical `site_address` (or `site_id` directly) at field
  submission time. Extend `ObservationRequest` and the device app
  so the resolver is rarely needed at approve.

Until that follow-up lands, the gate trades a small amount of
operator friction for the guarantee that no orphan or wrong-site
row enters `pims_observations`. The operator team should be told
ahead of the rollout.

### Phase 8 — Prevention 4: reconciliation script

**Goal:** retroactively repair orphan rows and surface ambiguous
ones for human review.

`scripts/reconcile_observation_sites.py`:
- For every `pims_observations` row with `site_id IS NULL`:
  - Run the Phase 7 resolver.
  - Unambiguous match → UPDATE `site_id`.
  - No match → log.
  - Ambiguous → log for human review.
- Idempotent. Safe to run on a schedule.

Alias maintenance: explicit Python dict in `site_resolver.py`,
human-reviewed via PR. Not a DB table, not auto-learned. Revisit
with `pg_trgm` only if alias churn becomes painful.

Verify:
- Dry-run on production → reports N orphans, M resolvable, K
  ambiguous.
- Real run → orphans drop; ambiguous logged.

Exit criterion: zero non-ambiguous orphans for any active site.

## 4. Out of scope

- Migrating other Anthropic callers outside the two PIMS files
  (Phase 5 is intentionally narrow).
- General refactor of error handling across the PIMS codebase.
- Slack / email alerting plumbing (separate operational slice).
- Frontend rework beyond Phase 6 status pills + Phase 7 PDF route
  swap + Phase 5.5 staleness chips.
- Changes to the Field Capture Platform device app.
- `pg_trgm` / fuzzy matching infrastructure.
- Postgres triggers to maintain `site_id`.
- DDL on `pims_staging` (no `site_id` column added).

## 5. Risks and reversibility

| Phase | Risk | Reversibility |
|---|---|---|
| 4 | Wrong site_id linked to wrong rows | Dry-run lists exact IDs before write; reversible via `UPDATE … SET site_id=NULL WHERE id IN (...)` |
| 1 | None — pure logging | Trivial revert |
| 2 | Wrong target → enrichment still fails | Env-var change or single-file revert |
| 3 | Bad enrichment overwrites manually-corrected fields | Dry-run first; only target `enriched=false`; never touches `review_status`/`approved_at`/`site_id`/`site_address` |
| 5 | SDK migration regresses one of the two callers | Per-caller revert; smoke test before deploy |
| 5.5 | False-positive chip noise | Tune threshold; chips are non-blocking |
| 6 | Guard blocks legitimate approvals when Anthropic is down | `PIMS_APPROVE_ENRICHMENT_GUARD=off` kill-switch |
| 7 | Resolver links rows to wrong site | Conservative matching; ambiguity → None; PDF route swap is the largest change — feature-flag the route if needed |
| 8 | Mass UPDATE on observations | Dry-run; review counts; per-site commit cadence |

## 6. Verification SQL (canonical checks)

```sql
-- After Phase 4: site link health
SELECT site_id, COUNT(*) FROM pims_observations
WHERE id IN ( /* reviewed UUID list */ )
GROUP BY site_id;

-- After Phase 3: enrichment health
SELECT enriched, COUNT(*) FROM pims_staging
WHERE id IN (
  SELECT staging_id FROM pims_observations
  WHERE id IN ( /* reviewed UUID list */ )
)
GROUP BY enriched;

-- After Phase 8: global orphan count
SELECT COUNT(*) AS orphans FROM pims_observations
WHERE site_id IS NULL AND review_status = 'Approved';

-- Phase 5.5 chip queries (see Phase 5.5)
```

## 7. Commit cadence

One commit per phase, each with:
- A `docs/decisions/2026-05-12-pims-enrichment-recovery-phase-N.md`
  decision log entry (cause, change, verification result).
- Mention of this master plan filename in the commit body.
- Tests added/changed.

## 8. Resolved decisions (from Codex v2 review)

1. **Phase 1 logging:** use the installed Anthropic SDK
   `APIStatusError.body` for the migration in Phase 5; for Phase 1
   itself, the lightweight `httpx` log patch is fine to confirm the
   hypothesis without blocking on an SDK migration.
2. **Env var name:** `PIMS_ENRICHMENT_MODEL` is the right shape (no
   strong generic naming convention in this repo).
3. **Backfill prompt:** use live `enrich_observation`; pin
   `PIMS_ENRICHMENT_MODEL` and log the `ENRICHMENT_SYSTEM` sha256
   in the backfill script log only for provenance. Never written
   into `monitoring_note` or any business-facing column.
4. **Approve-time guard:** poll-then-409 only; no synchronous
   enrichment inside approve; idempotent on duplicate clicks.
5. **Resolver location:** app-side, not Postgres trigger — *provided*
   Phase 7 routes the PDF promote path through the backend. With the
   PDF path routed, app-side covers every write surface.
6. **Alias table:** Python dict in `site_resolver.py`. Move to DB
   only if churn becomes painful.

## 9. Test coverage required to ship

- `tests/test_site_resolver.py` — resolver behaviour matrix.
- `tests/test_approve_staging.py` — happy path, race, true failure,
  idempotency.
- `tests/test_backfill_enrichment.py` — script touches only
  enrichment columns; respects `--dry-run`.
- `tests/test_enrichment_smoke.py` — `enrich_observation` parses a
  mocked Anthropic response correctly.
- `tests/test_upload_observations.py` — `/pims/upload/observations`
  writes `site_id` via resolver.
- `tests/test_pdf_promote_route.py` — new backend route promotes via
  resolver + idempotency; frontend grep confirms direct Supabase
  update from the browser is gone.

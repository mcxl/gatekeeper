# Codex QA Handover — Audit Report Renderer Adoption

**Commits under review:** `0085ab7` (adoption) + `8d78858` (template typo strip).
**Branch:** `main`
**Repo:** `C:\Users\AlanRichardson\gatekeeper`
**Date pushed:** 2026-05-12
**Author of changes:** Claude Code (Opus 4.7, 1M)
**Reviewer:** Codex (first pass landed; corrections folded back into this doc and the related code).
**Test status:** audit-report subset green locally; ruff clean on every changed file; pre-push hook passes without `--no-verify`.

---

## 0a. Codex QA findings (this revision)

Recorded so future readers don't repeat the same misreadings:

1. **Fingerprint test scope.** `tests/test_audit_report_contract.py`
   is a reference-file pin, not a renderer regression test. It
   guards the references and the JSON snapshots; it does NOT
   render the audit report and assert the rendered output matches
   the snapshot. Render-then-compare is a follow-up.
2. **Wrong local-render script.** Earlier drafts pointed at
   `scripts/render_site_visit_report.py` — that script renders
   the Site Visit Report xlsx, not the audit report. Corrected:
   either use `pims/scripts/generate_audit_report.py` (xlsx-
   driven) or skip local render and go via §3.3.
3. **`report_issue_date` route test coverage incomplete.**
   At the time of this revision, route-level tests for missing
   value, empty string, JSON `null`, invalid string, and explicit
   valid value round-trip have been added in
   `tests/test_audit_report_routes.py` — see §3.1 below for the
   targeted pytest invocation that covers them.
4. **Photo-prefetch overstatement.** Earlier wording implied the
   route pre-fetches image bytes for every observation. The code
   only pre-fetches for `open_actions`. The §4.8 implementation
   plan asks for "all observations" prefetch; we narrowed it to
   open-actions because the adopted renderer only embeds
   open-action photos. The route comment and the §1.3 wording in
   this handover have been corrected to match the code.

## 0. What you're QA-ing

Operator authorised execution of the plan in
`C:\Users\AlanRichardson\gatekeeper\docs\plans\AUDIT_REPORT_REFERENCE_EVALUATION.md`
§4.8. The plan brings the renderer + template + cleaner from the
unmerged feature branch `feat/audit-report-visual-polish` (tip
`4a0e651`) onto `main`, plus a fingerprint contract test pinned to
the two canonical reference docx files.

Plan + decisions to cross-reference:
- Full evaluation + plan: `docs/plans/AUDIT_REPORT_REFERENCE_EVALUATION.md`
- ADR for this adoption: `docs/decisions/2026-05-12-adopt-audit-report-visual-polish.md`
- Five resolved decisions you previously provided: §5 of the
  evaluation doc.

## 1. What changed in commit `0085ab7`

Thirteen files, 4173 insertions, 503 deletions. Categorised:

### 1.1 Imported verbatim from `feat/audit-report-visual-polish`

- `pims/audit_report_docx.py` — full renderer rewrite (was 1212 lines on main, now 1350 lines)
- `pims/audit_report_template.docx` — template binary
- `pims/scripts/clean_audit_report_template.py` — template cleaner
- `tests/test_audit_report_template_clean.py` — feature-branch tests, new on main
- `tests/test_audit_report_body_section.py` — feature-branch tests, new on main

### 1.2 Patches applied on top of the feature-branch import

In `pims/audit_report_docx.py`:

1. **`CONTRACTOR_CONFIG` RPD entry corrected.** Feature branch had
   `"contact_name": "Matt M Matthew McCarthy"`. Changed to
   `"Matthew McCarthy"`. New key `"title_display_name":
   "Robertson's Remedial and Painting"` added so the cover title
   renders without the legal-entity suffix (matches the
   references' `Robertson's Remedial and Painting – Site Safety
   Audit Report` header bar). Two keys provided to cover both
   normalised forms: `"robertson's remedial and painting pty ltd"`
   (canonical, with suffix) AND `"robertson's remedial and
   painting"` (legacy alias, without suffix).
2. **`_format_audit_date` helper re-introduced.** Parses ISO date
   strings (`YYYY-MM-DD`, `YYYY-MM-DDTHH:MM:SS`, `YYYY-MM-DD
   HH:MM:SS`) and returns `D Month YYYY` (e.g. `12 May 2026`).
   Returns empty string on parse failure (callers fall back to raw
   value).
3. **`SiteData.report_issue_date` (new field, default `""`).**
   Threaded through `_build_cover_replacements` into the
   `[Insert Current Date]` token. Same value renders on the title
   page (text-frame placeholder) AND in the page-2+ footer.
4. **`_resolve_cover_title` uses `_contractor_title_name` lookup.**
   Reads `CONTRACTOR_CONFIG[normalised_client]["title_display_name"]`
   if present; falls back to the raw client string otherwise.
5. **`_score_totals` percent reverted to integer.** Was 2-decimal
   on the feature branch (`50.00%`); references use integer
   (`98%`, `96%`, `94%`).
6. **`[Insert Date of inspection]` formatted via `_format_audit_date`.**
   So the body metadata cell shows `12 May 2026` not the raw
   `2026-05-12 09:00`.

### 1.3 Route reconcile

In `pims/routes.py`:

1. `AuditReportRequest` gains optional `report_issue_date: Optional[str]`.
2. Photo prefetch: the D9 NCR/Conditional filter was removed, but
   the fetch was NOT widened to every observation. The route still
   pre-fetches image bytes for `open_actions` only — that is the
   only set the adopted renderer consumes. Observations themselves
   are loaded from Supabase as before. Comment in `pims/routes.py`
   was corrected to state this explicitly; the §4.8 implementation
   plan asks for "all observations" prefetch and the QA-correction
   note in the evaluation doc records the narrower behaviour as a
   deliberate choice for this commit.
3. `SiteData(...)` construction:
   - Removed `obs_photo_bytes_by_obs_id` keyword (field doesn't
     exist on the adopted SiteData).
   - Added `report_issue_date=body.report_issue_date or date.today().isoformat()`.

### 1.4 Test updates

- `tests/test_audit_report_contract.py` (new, 8 cases) —
  **reference-file fingerprint pin only.** It asserts the in-repo
  reference DOCX files match their JSON snapshots and that the
  references carry the required strings / no forbidden
  placeholders. It does NOT yet render the audit report against
  fixture inputs and compare the rendered output to the
  snapshots. The render-then-compare regression test is a
  follow-up; the current test does not protect against renderer or
  template regressions on its own.
- `tests/test_audit_report_cover.py` — monkeypatch the test
  `CONTRACTOR_CONFIG` entry for the `Acme Construction Pty Ltd`
  fixture client; assertions updated for the feature branch's
  `Prepared by, AuditCo` suffix and integer-percent score.
- `tests/test_audit_report_docx_smoke.py` — ten previously
  skipped Phase D/E/F/G tests UN-skipped (feature branch satisfies
  them). The single fixture-driven smoke test now asserts Part
  A/B headings present instead of Findings/Site Safety Inspection
  (which was the Option-B contract this commit supersedes).
- `tests/fixtures/audit_report_contracts/{cremorne,fraters}.fingerprint.json`
  — baseline snapshots committed.

### 1.5 Docs / ADR

- `docs/decisions/2026-05-12-adopt-audit-report-visual-polish.md` (new)
- `docs/plans/AUDIT_REPORT_REFERENCE_EVALUATION.md` (new, committed
  with this change)

## 2. What I want you to challenge

These are the areas I'm least confident about. Please pressure-test
each.

### 2.1 CONTRACTOR_CONFIG behaviour for unknown contractors

Today `_resolve_cover_title` falls back to the raw `client` string
when the contractor is not in `CONTRACTOR_CONFIG`. For RPD that's
fine. But for any new client added to the `sites` table without a
config entry:

- The title will include the legal entity suffix (`...Pty Ltd – Site Safety Audit Report`).
- The `Prepared For` text-frame block falls back to the raw client
  string (per the existing else-branch in
  `_build_cover_replacements`).

Is silent fallback acceptable, or should the route 422 when the
contractor is unknown? The feature branch's commit message
references "Phase H3" as the place this gets enforced; H3 doesn't
exist yet.

### 2.2 `report_issue_date` round-trip

The new field accepts EITHER an ISO date (`2026-05-12`) OR an
already-formatted human string (`12 May 2026`).
`_format_audit_date` returns empty string when parsing fails;
caller then uses the raw value. Edge cases I want you to verify:

- Pass `report_issue_date="invalid"` — does it gracefully fall
  through to the raw value, or does it 500?
- Pass `report_issue_date=""` (or missing) — does the route
  default it to `date.today().isoformat()` and the renderer format
  it to today's display form?
- Pass `report_issue_date=null` (JSON) — does Pydantic accept it
  and route handle?

### 2.3 Multi-site behaviour

The feature branch's `_resolve_cover_title` for multi-site picks
the first client. `_build_cover_replacements` uses `site = sites[0]`
for all cover values. Test fixture only covers single-site. Should
multi-site reports have per-site title pages or a single combined
title page? Reference docx files are single-site only — no
guidance.

### 2.4 Fingerprint test coverage

The new `tests/test_audit_report_contract.py` currently asserts
the **reference files themselves** match the fingerprint snapshots.
What it does NOT yet do:

- Render the audit report against a synthetic site fixture and
  assert the **rendered** output matches the snapshot.
- This means a regression in `_populate_cover` or template would
  pass the test if the reference file remained unchanged.

Is that an acceptable v1 of the contract test, or do you want me
to implement the render-then-match part before this commit ships?

### 2.5 The `pims/routes.py` patch is large

The route is 3500+ lines. The diff hunks I made are at lines
3149-3163 (`AuditReportRequest`) and 3438-3470 (the SiteData
construction). Please verify I didn't break adjacent code paths or
introduce a stale variable name.

### 2.6 Removed `tests/test_audit_report_docx_smoke.py` skip markers

Ten tests were skipped earlier with reason "Option B refactor
removed Part A/B/C/D structure". They're now un-skipped because
the feature branch IS Phase D/E/F/G compliant. They pass locally,
but please check none of them assert behaviour that conflicts with
the resolved decisions (e.g. asserting `[Insert Current Date]` is
filled with `date.today()` — which would conflict with the new
`report_issue_date` plumbing).

## 3. How to verify

### 3.1 Quick local run

```bash
cd C:\Users\AlanRichardson\gatekeeper

# Static checks
.venv-test/Scripts/ruff.exe check \
  pims/audit_report_docx.py \
  pims/routes.py \
  pims/scripts/clean_audit_report_template.py \
  tests/test_audit_report_contract.py \
  tests/test_audit_report_cover.py \
  tests/test_audit_report_docx_smoke.py

# Test suite — audit-report subset (run twice; first run writes
# fingerprint snapshots if missing, second is the real assertion)
.venv-test/Scripts/python.exe -m pytest \
  tests/test_audit_report_cover.py \
  tests/test_audit_report_docx_smoke.py \
  tests/test_audit_report_routes.py \
  tests/test_audit_report_template_clean.py \
  tests/test_audit_report_body_section.py \
  tests/test_audit_report_contract.py
```

Expected: All checks passed (lint), 57/57 passed (tests — includes
the six new `report_issue_date` route cases added per Codex QA
finding 3).

### 3.2 Render a local DOCX without Railway

There is **no `--site-id`-driven local script** for the
`/pims/audit-report/rpd` path. `scripts/render_site_visit_report.py`
renders the **Site Visit Report** (the xlsx export endpoint), not
the audit report — earlier drafts of this handover linked it by
mistake. Two options for local rendering:

- `pims/scripts/generate_audit_report.py path/to/Site_Visit_Report.xlsx`
  — generates an audit-report DOCX from a Site-Visit-Report-format
  xlsx (the SSA pipeline path). Operator may have a suitable xlsx
  on `G:\My Drive\alan_mcxico\SSA-evidence\…` already.
- Skip local render and use §3.3 production sanity instead — the
  fast path for this QA.

### 3.3 Production sanity (post-deploy)

```bash
# Login (cookie jar)
curl -sS -c /tmp/qa_cookies.txt -X POST \
  https://web-production-baafa.up.railway.app/pims-login/rpd \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "password=PIMS_RPD"

# Generate v5
curl -sS -b /tmp/qa_cookies.txt -X POST \
  https://web-production-baafa.up.railway.app/pims/audit-report/rpd \
  -H "Content-Type: application/json" \
  -d '{"site_ids":["98896ff0-996b-44d6-b878-66c4f301226d"],"prepared_by":"Alan Richardson","inspection_datetime":"2026-05-12","report_issue_date":"2026-05-12"}' \
  -o /tmp/qa_v5.docx \
  -w "http=%{http_code}\nbytes=%{size_download}\n"
```

Expected: HTTP 200, several MB.

### 3.4 Structural fingerprint of v5

```python
from docx import Document
d = Document(r"/tmp/qa_v5.docx")
print("paragraphs:", len(d.paragraphs))
print("tables:", len(d.tables))
print("images:", sum(1 for s in d.part.related_parts.values()
                    if hasattr(s, 'content_type')
                    and 'image' in (s.content_type or '')))

# Title page text-frame walk
ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}t"
seen = set()
for el in d.element.body.iter():
    if el.tag == ns:
        t = (el.text or "").strip()
        if t:
            seen.add(t)
print("title-page strings (sample):")
for s in sorted(seen)[:20]:
    print("  ", repr(s))

# Forbidden tokens
text = "\n".join(p.text for p in d.paragraphs)
for bad in ("[Site Address]", "[Insert Current Date]", "Site Safet Audit", "Matt M Matthew McCarthy"):
    assert bad not in text, f"REGRESSION: {bad!r} still present in v5"
print("forbidden-token check: PASS")
```

Expected: All four forbidden tokens absent. Title-page strings
include `Robertson's Remedial and Painting – Site Safety Audit
Report`, `96-98 Hampden Rd Russel Lea`, `12 May 2026`, `Matthew
McCarthy`, `10/ 56 Buffalo Road, GLADESVILLE 2111`. No `Matt M`
prefix anywhere.

### 3.5 Side-by-side vs Cremorne reference

```bash
ls -la C:\Users\AlanRichardson\gatekeeper\pims\7_Hampden_Rd_Cremorne.docx
ls -la /tmp/qa_v5.docx
```

Open both side-by-side in Word. Look for:

- Title-page layout: AuditCo logo, date strip, site address, large
  "Site Safety Audit" heading, "Audit Report" subtitle, Prepared
  by / Prepared For block.
- Page 2+: header bar `Robertson's Remedial and Painting – Site
  Safety Audit Report`, Executive Summary + bullets, Score,
  Flagged Items, Findings, Site Safety Inspection.
- Footer: `Date: 12 May 2026   Page: N of M   Written By: Alan
  Richardson`.

## 4. Files to read in this order

1. `C:\Users\AlanRichardson\gatekeeper\docs\plans\AUDIT_REPORT_REFERENCE_EVALUATION.md`
   — full background, defect catalog, resolved decisions, plan.
2. `C:\Users\AlanRichardson\gatekeeper\docs\decisions\2026-05-12-adopt-audit-report-visual-polish.md`
   — ADR for this change.
3. `git show 0085ab7 --stat` — overview of files changed.
4. `git show 0085ab7 -- pims/audit_report_docx.py | head -200` —
   inspect the patches on top of the feature-branch import,
   especially `CONTRACTOR_CONFIG` (line ~165) and
   `_resolve_cover_title` / `_contractor_title_name` (line ~715).
5. `git show 0085ab7 -- pims/routes.py` — the route reconcile.
6. `C:\Users\AlanRichardson\gatekeeper\tests\test_audit_report_contract.py`
   — the fingerprint test.

## 5. What I'd ship next (not in this commit)

Listed in `docs/plans/AUDIT_REPORT_REFERENCE_EVALUATION.md` §6,
but in priority order:

- (a) Extend the fingerprint test to render against a synthetic
  fixture input and assert against the snapshot. Otherwise the
  test only guards the reference file, not the renderer.
- (b) `make audit-report` smoke target — boots FastAPI, generates
  a known site's audit, compares to fingerprint.
- (c) CI guard: long-lived-branch alarm. `feat/audit-report-visual-polish`
  was unmerged for 3 weeks before causing this incident.
- (d) `.meta.json` sidecar for the in-repo reference docx files
  recording which commit produced them.
- (e) Block "unused-binary-delete" commits without grep-evidence.

## 6. Known limitations I will not chase without operator approval

- Cremorne PDF glyph-substitution boxes (`Site Sa?ety`, `Date o?
  inspection`) are PDF/font-embedding noise. Operator resolved
  decision 5: ignore.
- The Site Safety Inspection checklist photo embedding behaviour
  matches the feature branch exactly. If a Compliant row in the
  reference docx has a photo, the feature branch's renderer puts
  it there. Spot-check three Compliant rows in v5 to confirm they
  carry their photos (Photo 3, 4, 5, 6 in the Cremorne reference
  are on Compliant rows).
- "Prepared by" column in the metadata table reads `Alan Richardson,
  AuditCo` (feature-branch appends `", AuditCo"`). The references
  agree. If this is wrong, that's a contract change.

## 7. Sign-off prompt for operator after your QA

When Codex review concludes, the operator's sign-off prompt is:

> v5 docx generated, side-by-side with Cremorne reviewed. Approve or
> reject? If reject, name the section + page + defect — I'll patch.

---

Status: commit `0085ab7` pushed. Railway deploying. v5 regeneration
+ side-by-side will land in the next operator turn or via the
scheduled wakeup, whichever fires first.

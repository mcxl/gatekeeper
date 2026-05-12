# Audit Report Renderer — Regression Diagnosis

**Date:** 2026-05-12
**Author:** Claude Code (Opus 4.7, 1M)
**Reviewer:** Codex (review applied 2026-05-12; corrections in §9)
**Status:** Diagnosis v2 — Codex caught fundamental ancestry errors
in v1. Operator must answer the new blocker in §6 before any
revert is attempted.

## 0. Why this doc exists

You spent significant time perfecting the RPD Site Safety Audit
Report renderer through **Phases 0 → H pre-3** (Apr 2026) — 11
incremental commits, each with detailed messages, producing the
two reference docx files in `pims/`:

- `pims/56-58_Fraters_Ave_Sans_Souci.docx`
- `pims/7_Hampden_Rd_Cremorne.docx`

The audit report you just generated for **96-98 Hampden Rd Russel
Lea** does not match those references. This doc traces what
happened, what was recorded, what wasn't, and exactly what's broken.

## 1. What was recorded

Each phase has a single git commit with a substantive message that
defines its contract. Reading them in order is the design log:

| Commit | Phase | Contract |
|---|---|---|
| `6b666e6` | (kick-off) | Generate Audit Report feature for /rpd dashboard |
| `f419b43` | Phase 0 | Populate cover page placeholders from site metadata |
| `9022f88` | Phase B | Remove scaffold "Photo" table from populated cover |
| `eae704b` | Phase C | One checklist block per matched observation (don't drop duplicates) |
| `ffd914e` | Phase D | Body reorder + bold status colour-coding + photos on Open Actions |
| `0cca120` | Phase E | Part B metadata table + shared executive summary |
| `bd072d9` | Phase F | Part C summary banner + checklist grouped by Category |
| `4dfab34` | Phase G | Part D auditor sign-off block (incl. disclaimer + 5-row signature table) |
| `92bff97` | Phase H0 | Backfill `pims_audits.principal_contractor` (data only) |
| `9a69239` | Phase H1 | Clean `audit_report_template.docx` in-place (strip Fraters example content) |
| `e953c45` | Phase H2 | Token-level placeholder replacement across all containers (txbxContent, sdtContent, DrawingML) |
| `4a0e651` | Phase H pre-3 | Body section after cover; blank body header/footer to remove cover artwork |
| `07e863f` | Phase 5 | Local render CLI (`scripts/render_site_visit_report.py`) + Phase 0–5 decision log |

There are no `docs/decisions/` entries specifically for these phases
— the design intent lives in the commit messages and in
`docs/pims_site_visit_report_spec.md` (which is the Site Visit Report
xlsx spec, not the docx).

The reference docx files themselves were never committed to git
(they're untracked artifacts in `pims/`). They are the only
preserved snapshot of "what the contract output looks like".

## 2. What broke

Commit **`791e167` chore(pims): pre-existing tree changes (Slice 3
field-flow + photo embed)** (2026-05-03) is the regression source.

That commit's message bundled five things under "Slice 3":

1. Added `recommendation` to `STAGING_COPY_FIELDS` (legit, unrelated to renderer).
2. Pre-fetched photos for **all** observations, not just open actions.
3. "audit_report_docx.py adjustments" — **179-line diff** with no further detail.
4. Updated `audit_checklist.xlsx`.
5. **Deleted `pims/audit_report_template.docx` and `RPD_SSA_template.docx`** as "unused".

The deletion in #5 broke `/audit-report/rpd` outright. Commit
`64303ca` (2026-05-09) restored the template binary from
`791e167`'s parent (which is post-Phase-H pre-3, so the template is
fine). **It did not revert the 179-line renderer changes**.

The "Slice" naming is from a different feature stream (precedent
import) — the work in `791e167` was not part of the Phase 0-H
sequence and was not separately reviewed.

## 3. Concrete defects in the current renderer output

Side-by-side comparison of the just-generated 96-98 Hampden Rd
docx against the two references:

| # | Defect | REF (correct) | NEW (current) | Likely source |
|---|---|---|---|---|
| D1 | Title line: company suffix | `Robertson's Remedial and Painting – Site Safety Audit Report` | `Robertson's Remedial and Painting **Pty Ltd** – Site Safety Audit Report` | Cover title built from raw `sites.client_name` (which has "Pty Ltd") instead of a CONTRACTOR_CONFIG display name (Phase H2 introduced `CONTRACTOR_CONFIG` — likely not used by every title path) |
| D2 | Date format | `30 April 2026` | `2026-05-12 09:00` | `Part D` disclaimer (commit `4dfab34`) interpolates `inspection_datetime` literally — never passes through `_format_audit_date` (which exists in the renderer but is only wired into the cover's `[Insert Current Date]` token, added in `791e167`) |
| D3 | Template scaffold visible | absent | `Part A`, `Part B`, `Example format below` left in body | Either the deployed template binary is an older non-Phase-H1 state, OR the renderer's Phase H1 paragraph-prefix delete loop dropped a prefix in `791e167`'s adjustments |
| D4 | Score precision | `47 / 48 (98%)` | `19 / 34 (55.88%)` | `_score_totals` uses `:.2f` formatting; reference rendered integer percent — regressed in `791e167`'s adjustments |
| D5 | KPI table labels | `Score \| Flagged observations \| Open actions` | `Score \| Flagged items \| Actions` | Labels changed in `791e167`'s adjustments |
| D6 | Stray "Alan Richardson \| Complete" row | absent | row 0 of cover | New cover row added in `791e167` that doesn't belong on this template |
| D7 | Findings structure | `NCR #1. <Category> – <Sub-category> – <text>` + immediate `Required action: <action>` paragraph beneath | Flat bullet `• <text>` with no numbering, no Category, no inline action | `_render_findings` rewritten in `791e167` — Phase D/E format was abandoned |
| D8 | Open Actions Register placement | Inline (`Required action:` under each NCR) | Pulled out into a separate `Open Actions Register` block above the findings | `_render_open_actions` extracted in `791e167`, breaking the Phase D inline-action contract |
| D9 | Photo set | 8 (Fraters) / 9 (Cremorne) — NCR + Conditional only | 27 — every observation including Compliant breadcrumbs | `791e167` "pre-fetches photos for ALL observations" — intentional change to enable inline checklist photos, but the render path embedded them indiscriminately instead of filtering at render time |
| D10 | Table count | 273 / 272 | 209 | Lower table count = different structural layout in body (likely the Part B / Part C / per-finding table layout changed) |

All ten map back to **`791e167`'s "audit_report_docx.py adjustments"**.

## 4. What's recoverable (v2 — ancestry corrected)

**v1 of this doc claimed `791e167~1` was the Phase H pre-3 renderer
state. That was wrong.** `791e167~1` resolves to commit `960fdf4`
("docs(pims): add updated platform brief, setup guide and onboarding
workflow", 2026-05-02), which is **docs-only on `main`** and does
NOT contain Phases H1/H2/H pre-3 of the renderer work.

Phases H1, H2, and H pre-3 live on the feature branch
**`feat/audit-report-visual-polish`** and were never merged to
`main`:

```
git log --oneline --all --decorate=full | grep -E "e953c45|4a0e651|9a69239"
4a0e651 (refs/remotes/origin/feat/audit-report-visual-polish, refs/heads/feat/audit-report-visual-polish)
        fix(pims): new section after cover, blank header/footer on body pages (Phase H pre-3 hotfix)
e953c45 feat(pims): token-level cover placeholder replacement … CONTRACTOR_CONFIG (Phase H2)
9a69239 refactor(pims): clean audit_report_template.docx in-place, guard with tests (Phase H1)
```

There are therefore **two possible baselines** for restoration, and
they are materially different:

| Baseline | Commit | Date | Contains |
|---|---|---|---|
| **A. `main@960fdf4`** | `791e167~1` | 2026-05-02 | Phases 0 → G; **no** H1/H2/H pre-3 renderer changes |
| **B. `feat/audit-report-visual-polish@4a0e651`** | tip of feature branch | 2026-04-24 | Phases 0 → G plus H1 (template clean) + H2 (CONTRACTOR_CONFIG + field-safe placeholder walker) + H pre-3 (blank body header/footer) |

**The two reference docx files (`pims/56-58_Fraters_Ave_Sans_Souci.docx`,
`pims/7_Hampden_Rd_Cremorne.docx`) were almost certainly built from
checkout B**, not A — they show no cover artwork bleeding onto body
pages, indicating Phase H pre-3 ran. Verifying which checkout
produced them is the v2 §6 blocker.

What's *not* recorded:
- The intent of `791e167`'s renderer changes (the commit message
  says "adjustments" with no specifics).
- Why H1/H2/H pre-3 were never merged to main.
- Whether any of `791e167`'s 179 lines are net-positive (Codex
  identified `_format_audit_date` as keep, `_replace_inline_placeholder`
  as **NOT safe** — see §9).

What's *not* recorded:
- The intent of `791e167`'s renderer changes (the commit message
  says "adjustments" with no specifics).
- Whether any of those 179 lines are net-positive and worth
  keeping (e.g. the `_format_audit_date` helper *is* an improvement
  — it just wasn't wired into the Part D disclaimer).

## 5. Recovery plan (v2 — coordinated, baseline-explicit)

v1 proposed a one-file revert. Codex pointed out this would break
`pims/routes.py` lines 3442–3462, which now construct
`SiteData(..., obs_photo_bytes_by_obs_id=...)` — a field that does
not exist in the pre-`791e167` `SiteData` dataclass. The recovery
must be **coordinated across `pims/audit_report_docx.py` and
`pims/routes.py`**, not a single-file revert.

### Option A (revised) — Restore to feature-branch H pre-3 baseline

Restore `C:\Users\AlanRichardson\gatekeeper\pims\audit_report_docx.py`
to `feat/audit-report-visual-polish@4a0e651` (the actual Phase H
pre-3 state that produced the reference docx files), then
coordinated-adjust callers:

```sh
git checkout 4a0e651 -- pims/audit_report_docx.py
```

Then in `C:\Users\AlanRichardson\gatekeeper\pims\routes.py`
(lines 3442–3462), choose ONE of:

- **A.1** — Drop the `obs_photo_bytes_by_obs_id=` keyword from the
  `SiteData(...)` construction. Removes the inline-checklist-photo
  feature that `791e167` introduced. Matches the reference docx
  behaviour exactly.
- **A.2** — Keep the field. Add it to `SiteData` in the restored
  `audit_report_docx.py` as a no-op data carrier (rendered nowhere
  in the Phase H pre-3 path). Lets `791e167`'s data-prep logic stay
  in place for future re-introduction without coupling it to
  rendering today.

Cherry-pick forward from `791e167` only:
- `_format_audit_date` helper. Re-wire into the Part D disclaimer
  (`C:\Users\AlanRichardson\gatekeeper\pims\audit_report_docx.py:947`
  in current HEAD, line numbers shift after restore) so the draft-
  date interpolation is human-readable. This is the only `791e167`
  improvement Codex confirmed is net-positive.

**Do NOT cherry-pick `_replace_inline_placeholder`.** Codex flagged
it as unsafe: it does `p.text.replace(...)`, clears all runs, then
writes one new run. The template footer's `Date:` paragraph
co-locates the placeholder with `PAGE` / `NUMPAGES` field runs
(`<w:fldChar>` + `<w:instrText>`). The helper would wipe the dynamic
page numbering. Use the Phase H2 field-safe walker from
`e953c45::_populate_cover` if footer current-date replacement is
needed — that walker already handles field runs correctly.

### Option B (revised) — Contract test + targeted defect fixes

Same as v1 Option B: lock the reference docx as a contract via
`C:\Users\AlanRichardson\gatekeeper\tests\test_audit_report_contract.py`
(structural fingerprint match), then fix each of D1–D10 one by one
on HEAD without reverting.

This option is now more attractive than v1 suggested because Codex
confirmed several defects (D1, D2, D4, D5, D7, D8) **don't trace to
`791e167`** — they're pre-existing on main or were never on main at
all. See §9 for the corrected defect→cause map. Targeted fixes may
be cleaner than a branch-restore that resets all 179 lines plus
forces a routes.py adjustment.

- Cost: ~3-4 hours, but each fix is independently committable and
  reviewable.

### Recommendation update

**Option B is now recommended** (was Option A in v1). Reason: the
ancestry mismatch means Option A is no longer a clean "restore to a
known-good snapshot" — it's a branch import requiring caller
coordination. Targeted fixes against HEAD with a contract test
gate are both lower-risk and faster to ship per defect.

## 6. Open questions for the operator (v2)

**BLOCKER (new):**

0. **Which baseline are we restoring to?** This determines whether
   any "restore" makes sense at all.
   - **Baseline B (recommended):** `feat/audit-report-visual-polish@4a0e651`
     — contains the Phase H1/H2/H pre-3 work and is the most likely
     source of the two reference docx files. Has CONTRACTOR_CONFIG +
     field-safe placeholder walker + blank body header/footer.
   - **Baseline A (alternative):** `main@960fdf4` (= `791e167~1`)
     — Phases 0–G only. Less work to merge but also less complete.
   - **Or: skip restore entirely, go with Option B** (targeted fixes
     against HEAD).
   Answer with `B`, `A`, or `targeted`.

**Still useful (lower priority):**

2. **Inline checklist photos (D9 cause).** `791e167` pre-fetched
   photos for every observation so the checklist rows could carry
   thumbnails. The references don't have this. Do you want that
   feature, or roll back to "photos on Open Actions only"?
   - If kept → Option A.2 in §5 (keep `obs_photo_bytes_by_obs_id`
     as a no-op data carrier; render later).
   - If dropped → Option A.1 (remove the keyword from `routes.py`).
4. **Are there any *other* known references** besides the two
   `pims/*.docx` files? If yes, give the full path — I'll compare
   against all available references before locking the contract
   test in Option B.

**Now demoted (Codex confirmed not blocking):**

1. **(no longer blocking)** Is `recommendation` useful to the renderer?
   The current renderer does NOT consume `recommendation`. Decide
   later if/when you want it surfaced — does not affect the revert.
3. **(only relevant if Baseline B picked)** Phase H2 `CONTRACTOR_CONFIG`
   contractor display-name mapping. If Baseline B is picked, this
   ships with it and the cover will render without "Pty Ltd" when
   the contractor entry is configured. If Baseline A or targeted,
   the choice is between editing `sites.client_name` to drop "Pty Ltd"
   or introducing a one-line display-name override in the title path.

## 7. What to commit if Option A is approved

Single PR / commit:

- `git checkout 791e167~1 -- pims/audit_report_docx.py` to restore
  the pre-`791e167` renderer.
- Re-apply only:
  - `_format_audit_date` helper (re-wired into Part D disclaimer too,
    not just cover token).
  - `_replace_inline_placeholder` helper (kept as a utility).
  - The `SiteData.obs_photo_bytes_by_obs_id` field, only if O.1 is
    a "yes — keep inline checklist photos".
- `tests/test_audit_report_contract.py` (new) — load
  `pims/56-58_Fraters_Ave_Sans_Souci.docx`, extract structural
  fingerprint, compare to the renderer's output for the same site's
  data. Locks the contract against future drift.
- `docs/decisions/2026-05-12-audit-report-renderer-revert.md` —
  records the regression, the revert, and why selected helpers were
  re-introduced.

After this lands, Hampden Rd Russel Lea is regenerated and visually
diffed against Cremorne (same street name, similar shape — easiest
comparison).

## 8. Time budget for you, the operator

- 5 min: answer the four questions in §6.
- 5 min: review the post-revert Hampden Rd docx side-by-side with
  Cremorne, sign off.
- Zero further design work — the contract is in the references and
  the phase commit messages.

Total: ~10 min of your time. I do the revert + selective
re-introduction + contract test + regenerate. Then you eyeball one
output.

## 9. Codex review findings (applied 2026-05-12)

Codex reviewed v1 of this doc and caught material errors. All
verified locally before patching here:

### Defect→cause map corrected

| Defect | v1 claim | Codex correction | Verified |
|---|---|---|---|
| D1 (`Pty Ltd` in title) | regressed by `791e167` | `_resolve_cover_title` (`C:\Users\AlanRichardson\gatekeeper\pims\audit_report_docx.py:415`) is OUTSIDE the `791e167` diff. `CONTRACTOR_CONFIG` was already absent from `791e167~1`. **Pre-existing, not regressed.** | ✅ |
| D2 (raw ISO date) | regressed by `791e167` | `_part_d_signoff` interpolates raw `site.inspection_datetime` at `C:\Users\AlanRichardson\gatekeeper\pims\audit_report_docx.py:947`. `791e167` did NOT touch that function. **Pre-existing bug from Phase G commit `4dfab34`.** | ✅ |
| D4 (score 2-decimal) | regressed by `791e167` | `_score_totals` at `C:\Users\AlanRichardson\gatekeeper\pims\audit_report_docx.py:384` is unchanged by `791e167`. **Pre-existing.** | ✅ |
| D5 (KPI labels) | regressed by `791e167` | KPI labels at `C:\Users\AlanRichardson\gatekeeper\pims\audit_report_docx.py:631` are unchanged by `791e167`. **Pre-existing.** | ✅ |
| D7/D8 (Part A/B/C structure + Open Actions placement) | regressed by `791e167` | Part A/B/C structure at `C:\Users\AlanRichardson\gatekeeper\pims\audit_report_docx.py:1031` predates `791e167`. **Pre-existing — likely on `main` since Phase E/F/G never produced the references; references came from feature branch.** | ✅ |
| D3 (Part A/B/Example below visible) | template scaffold issue | Plausible. Needs template binary inspection to confirm whether the deployed `audit_report_template.docx` is the pre-H1 or post-H1 state. | ⚠️ open |
| D6 (stray `Alan Richardson \| Complete` row) | new in `791e167` | Not contradicted by Codex. Still attributed to `791e167`. | (unverified by Codex) |
| D9 (27 photos vs 8-9) | `791e167` pre-fetches all photos | Confirmed by Codex. | ✅ |
| D10 (table count 209 vs 273) | structural difference | Consistent with reference docx being from feature branch with H1/H2/H pre-3 (different table layout). | ✅ |

**Implication:** the majority of visible defects (D1, D2, D4, D5,
D7, D8) are **not regressions caused by `791e167`** — they're
either pre-existing main-branch behaviour or behaviour the
references got from the unmerged feature branch. This strengthens
the case for **Option B (targeted fixes)** over Option A (branch
restore).

### `_replace_inline_placeholder` is unsafe

The helper at
`C:\Users\AlanRichardson\gatekeeper\pims\audit_report_docx.py:486`
does `p.text.replace(...)`, clears all runs, and writes one new
run. The template's footer `Date:` paragraph co-locates the date
placeholder with `PAGE` / `NUMPAGES` field-code runs
(`<w:fldChar>` + `<w:instrText>`). Running this helper across the
footer wipes the dynamic page numbering.

**Use the Phase H2 field-safe walker from `e953c45::_populate_cover`
instead**, which already handles field runs correctly via its
two-pass guarded-stitch design.

### Live caller dependency

`C:\Users\AlanRichardson\gatekeeper\pims\routes.py:3442–3462`
constructs:

```python
obs_photo_bytes_by_obs_id: dict[str, bytes] = {}
…
sites_data.append(SiteData(
    …
    obs_photo_bytes_by_obs_id=obs_photo_bytes_by_obs_id,
))
```

The pre-`791e167` `SiteData` does NOT have the
`obs_photo_bytes_by_obs_id` field. A file-only revert of
`pims/audit_report_docx.py` breaks `/audit-report/rpd` at
construction time. Any revert must adjust `routes.py` in lockstep
(see §5 Option A.1 / A.2).

### Tests don't catch this

Codex ran:
- `C:\Users\AlanRichardson\gatekeeper\tests\test_audit_report_cover.py`
- `C:\Users\AlanRichardson\gatekeeper\tests\test_audit_report_docx_smoke.py`
- `C:\Users\AlanRichardson\gatekeeper\tests\test_audit_report_routes.py`

All passed on HEAD. The current test suite does **not** guard
against:
- the ancestry mismatch
- the footer-field damage risk in `_replace_inline_placeholder`
- the defect-to-source mismatches above

Adding the contract test in §5 Option B is doubly motivated.

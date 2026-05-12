# ADR — Adopt feat/audit-report-visual-polish onto main

**Date:** 2026-05-12
**Status:** Accepted
**Author:** Claude Code (Opus 4.7, 1M) acting on operator instruction
**Reviewer of contract:** Codex (2026-05-12)

## Context

The renderer that produced the canonical reference docx files
(`pims/7_Hampden_Rd_Cremorne.docx` and
`pims/56-58_Fraters_Ave_Sans_Souci.docx`, both modified 2026-05-04)
lived on the unmerged feature branch
`feat/audit-report-visual-polish` (tip `4a0e651`, Phase H pre-3
hotfix, dated 2026-04-24). That branch contains Phases H1, H2 and
H pre-3:

- `9a69239` — Phase H1, template cleaner
- `e953c45` — Phase H2, token-level cover XML walker + CONTRACTOR_CONFIG
- `4a0e651` — Phase H pre-3, body section break + blank body
  header/footer

None of those commits ever merged to `main`. In their absence
commit `791e167` (Slice 3 field-flow + photo embed, 2026-05-03) made
179 lines of undocumented edits to `pims/audit_report_docx.py` on
`main` and deleted the post-H1 template binary as "unused". Commit
`64303ca` later restored the template from the pre-H1 state,
leaving `main` with a half-built renderer + half-built template
that bore no relationship to the reference contract.

A nine-commit patch sequence on `main` this session
(`1b5cb0f` → `4e75753` → `830a071` → `11b8047` → `f6a7c01`)
attempted to fix defects piecemeal. v3/v4 outputs converged on the
body's prose structure but the cover page remained broken (text
frames in DrawingML went un-touched), the Site Safety Inspection
structure stayed flatter than the reference, and several other
gaps persisted. The reference contract proved too far from `main`'s
state to close incrementally.

Full pre-decision diagnosis:
`docs/plans/AUDIT_REPORT_REFERENCE_EVALUATION.md`.

## Decision

**Adopt the feature branch wholesale.** Bring the renderer, the
template, the cleaner, and the two test files forward to `main` in
one coordinated commit. Reconcile `pims/routes.py` to the adopted
`SiteData` signature.

Files imported from `feat/audit-report-visual-polish`:
- `pims/audit_report_docx.py`
- `pims/audit_report_template.docx`
- `pims/scripts/clean_audit_report_template.py`
- `tests/test_audit_report_template_clean.py`
- `tests/test_audit_report_body_section.py`

Files preserved on `main`:
- All data-layer changes from this session — Anthropic SDK
  migration (`d39859c`), site resolver (`c3a81d9`), CCVS
  fallback (`d4205bc`, `b2e4b7f`), approve-time enrichment guard
  (`668b168`), SDGroup PDF promote backend route
  (`4d9835b`).

The 9 patch commits (`1b5cb0f` → `f6a7c01`) get superseded for
the renderer/template, but the rest of the surface area they
touched stays intact (routes.py data-layer, cleaner scripts, etc.).

## Resolved sub-decisions (Codex, 2026-05-12)

Per `docs/plans/AUDIT_REPORT_REFERENCE_EVALUATION.md` §5:

1. **Photo counter** — single global counter across the whole
   report. Never resets per-block or per-site. Continuous from
   first site to last in multi-site renders. Feature branch's
   renderer already implements this via a shared
   `photo_counter[0]` list.
2. **Contact Us tail page** — preserved as part of the reference
   contract. Future removal is a separate deliberate change with
   its own ADR.
3. **Prepared For** — driven by `CONTRACTOR_CONFIG` keyed on
   `sites.client_name` (normalised). RPD entry fixed to:
   - `Matthew McCarthy` (the stray `Matt M` prefix from the
     feature branch's literal value is removed in this commit)
   - `Robertson's Remedial and Painting Pty Ltd`
   - `10/ 56 Buffalo Road, GLADESVILLE 2111`
   New `title_display_name` key added so `_resolve_cover_title`
   can render the trade name on the cover/header bar (matches
   reference: `Robertson's Remedial and Painting – Site Safety
   Audit Report`, without the legal suffix).
4. **Title-page date** — report issue / sign-off date. Passed
   explicitly at the route boundary via new
   `report_issue_date` field on `AuditReportRequest` and
   `SiteData`. Same value renders on the title page (text frame)
   AND in the page-2+ footer (`[Insert Current Date]` token).
   Renderer never calls `date.today()` — required for stable
   fingerprint contract test.
5. **Cremorne PDF glyph glitch** — ignored. PDF/font-embedding
   noise, not a DOCX content defect.

## Other patches applied on top of the feature branch

The feature branch's `_score_totals` formatted percent as 2-decimal
(`50.00%`). The references show integer percent (`98%`, `96%`,
`94%`). Changed back to integer — `int(round(100 * passed /
total))` — matching reference and the D4 fix from this session.

## What the fingerprint contract test pins

`tests/test_audit_report_contract.py` (new) anchors the contract
against the two reference docx files:

- Paragraph count, table count, table shapes (rows × cols list).
- Embedded image count.
- Required section headings (`Executive Summary`, `Findings`,
  `Site Safety Inspection`).
- Forbidden raw placeholder strings (`[Site Address]`,
  `[Insert Current Date]`, `Site Safet Audit`, `Matt M Matthew
  McCarthy`, etc.) — none may appear in the reference.

Snapshot fingerprints land in
`tests/fixtures/audit_report_contracts/{cremorne,fraters}.fingerprint.json`.
The fingerprint test currently asserts the reference *file* matches
the snapshot. A follow-up PR will extend the test to assert the
*rendered* output matches the same snapshot for a synthetic fixture
input.

## Consequences

- Any future change that drifts from the reference contract trips
  the fingerprint test in CI.
- Title page now populates correctly: `[Site Address]`,
  `[Insert Current Date]`, `Prepared For` block.
- `Site Safet Audit` template typo is overwritten by construction
  (text-frame walker replaces the literal token with the rendered
  title string).
- Body emits Part A/B/C/D headings + Part D Auditor Sign-off
  (matches the reference structure, NOT the simpler
  Findings/Site Safety Inspection prose I tried in Option B).
- Future operators see the references-rendered-as-canonical
  contract enforced by tests.

## Process guardrails introduced separately

See `docs/plans/AUDIT_REPORT_REFERENCE_EVALUATION.md` §6 for the
seven guardrails recommended to prevent this exact pattern of loss
recurring. Implementation of those guardrails (long-lived-branch
alarm, evidence-file `.meta.json` sidecars, contract-test gating,
no-unused-delete CI, structured commit messages for load-bearing
files, in-code contract declaration, `make audit-report` smoke
target) is OUT OF SCOPE for this commit. Each guardrail lands as
its own follow-up.

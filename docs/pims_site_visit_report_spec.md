# PIMS Site Visit Report — Specification

This is the single source of truth for the Site Visit Report pipeline. Every Phase 0–8 commit on `feat/pims-site-visit-report` references it. Disagreement between code and spec is resolved by updating one or the other in the **same commit** that introduces the disagreement — never silently.

---

## Locked invariants

1. **Single-site report only.** Multi-site aggregation is out of scope.
2. **Runtime checklist source is `public.checklist_items` in Supabase.** `pims/audit_checklist.xlsx` is a one-time seed input only; not read at runtime.
3. **Four states are authoritative**: `compliant_verified`, `compliant_unobserved`, `conditional`, `ncr`. No fifth state, no aliases.
4. **Verified and unobserved compliant share the same green shading** (bg `00B050` / fg `FFFFFF`). The verified/unobserved split surfaces only in the KPI block + the mandatory footer disclaimer.
5. **Audit-defensibility footer is mandatory** on the Site Visit Summary section, verbatim (see below).
6. **No silent drops.** Every matched observation reaches the rendered output. Every unmatched observation reaches the rendered output (appendix subsection) **and** a structured log line.
7. **Schema drift on `checklist_items` is blocking**, not warning. The migration's drift-guard SQL fails loudly.

---

## States and worst-severity precedence (Phase 3)

States, in increasing severity:

```
compliant_unobserved < compliant_verified < conditional < ncr
```

Per `ChecklistResult`, the state is decided by the worst-severity observation in `matched_observations`:

| Any matched observation status | Resulting `state` |
|---|---|
| at least one `NCR` | `ncr` |
| no `NCR`, at least one `Conditional` | `conditional` |
| no `NCR` / `Conditional`, at least one `Compliant` | `compliant_verified` |
| no matched observations | `compliant_unobserved` |

`Info` observations exist in PIMS data but **do not** drive checklist state — they pass through to the appendix or, if they happen to match a checklist item, do not change the item's state from `compliant_unobserved` (they are treated as informational only).

Per matcher contract: `cross_reference()` returns `(results, unmatched_observations)`. An observation that fails to match any checklist item lands in `unmatched_observations` AND emits exactly one `log.warning("unmatched observation %s …", obs_id)` line.

---

## Cover-page token map (Phase 4 — finalised after template inspection)

The new template `pims/RPD_SSA_template.docx` is opened once at the start of Phase 4. Tokens are catalogued from `<w:t>` and `<a:t>` content (body, headers, footers, textboxes, sdt content, DrawingML).

**Expected token set** (placeholder names confirmed at template-inspection time):

| Token | Value source |
|---|---|
| `[Site Address]` | `site.address` |
| `[Audit Date Range]` | `f"{start:%d %b %Y} – {end:%d %b %Y}"` |
| `[Auditor]` | `site.prepared_by + ", AuditCo"` |
| `[Project Value Tier]` | `site.project_value_tier` |
| `[Audit Reference]` | `site.audit_ref` |
| `[Report Version]` | `"v1.0"` (hardcoded for first iteration) |
| `[Current Date]` | `date.today().strftime("%d %B %Y")` |

Any unrecognised template token surfaces to the user before merge — Phase 4 does not silently ignore.

Token replacement uses a two-pass walk lifted from `feat/audit-report-visual-polish`'s `_process_paragraph` / `_paragraph_field_runs`:

- **Pass 1 (node-local):** for each stitchable `<w:t>`, apply replacements against its own text.
- **Pass 2 (guarded stitch):** concatenate stitchable `<w:t>` texts in document order; if joined string still contains a placeholder, replace and write back to first node, empty the rest. Field-code runs (PAGE/NUMPAGES/DATE) are excluded so dynamic fields survive.

DrawingML `<a:t>` is node-local only.

---

## Audit-defensibility footer (Phase 4 — verbatim)

Italic, Pt 9, present on the Site Visit Summary section directly under the KPI block:

> "Compliant (no issues observed)" indicates no exception was recorded against the checklist item during the site visit. It does not represent a verified physical inspection of that item. Verified compliance is reported separately in the Items Verified KPI.

This text is fixed. Tests assert it appears verbatim in every rendered report.

---

## KPI aggregation rules (Phase 4)

Six rows, in order, in the Site Visit Summary KPI table:

| Row | Definition |
|---|---|
| Total checklist items applicable | `len(results)` after tier filtering |
| Items verified (sighted) | count + % of `state in {compliant_verified, conditional, ncr}` |
| Items not sighted (assumed compliant) | count + % of `state == compliant_unobserved` |
| NCRs | count of `state == ncr` |
| Conditionals | count of `state == conditional` |
| Compliance rate | `(compliant_verified + compliant_unobserved) / total * 100` rounded to 1 dp |

Counts use checklist **items** (not raw observations) so multi-match doesn't double-count.

---

## Unmatched observation rendering (Phase 4)

The appendix section "Unmatched Observations" renders **only if** `unmatched_observations` is non-empty.

Columns: Date, Observation Text, CCVS Code, Photo Ref, Conformance Status.

Header: "These observations did not match any checklist item. They are included for completeness."

This rule is the audit-defensibility safeguard for invariant #6 — an observation that field-walked into PIMS cannot disappear from the report.

---

## Renderer cross-reference shading (Phase 4)

Section 2 cross-reference table. Cell-level shading by state:

| State | bg | fg |
|---|---|---|
| `ncr` | `C00000` | `FFFFFF` |
| `conditional` | `FFC000` | `000000` |
| `compliant_verified` | `00B050` | `FFFFFF` |
| `compliant_unobserved` | `00B050` | `FFFFFF` |

The verified/unobserved visual identity is intentional per invariant #4. The reader distinguishes them via the KPI block + the footer disclaimer.

Multi-match: when a checklist item has multiple matched observations, render one evidence row per matched observation under the item's category/criteria header. No summarisation, no "+N more" footnotes.

---

## Migration drift-guard (Phase 2)

Top of `pims/migrations/2026-04-27_checklist_items.sql`:

```sql
DO $$
DECLARE
    expected_columns text[] := ARRAY[
        'id', 'category_no', 'category_name', 'item_no',
        'criteria', 'instruction', 'ccvs_category', 'ccvs_code',
        'project_value_tier'
    ];
    col text;
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'checklist_items'
    ) THEN
        FOREACH col IN ARRAY expected_columns LOOP
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'checklist_items'
                  AND column_name = col
            ) THEN
                RAISE EXCEPTION
                    'checklist_items schema drift: column "%" missing', col;
            END IF;
        END LOOP;
    END IF;
END $$;
```

Schema drift fails loudly **before** any DDL or DML runs. If the live production table differs from this expectation, the migration is rejected and we resolve before merge.

---

## Branch hygiene

- Branch: `feat/pims-site-visit-report`, cut from `main` at `b19b012` (PR #3 merge).
- The Phase H branch `feat/audit-report-visual-polish` (H0–H2 + pre-3 hotfix) stays on origin but is **not merged**. Useful assets (token-walk + field-code-safe stitch + Phase H2 token-walk tests) are lifted into Phase 4 in this branch's history.
- Phase 0–8 commits land in execution order; each commit message references this spec by name.

---

## Files referenced

- This spec: `docs/pims_site_visit_report_spec.md`
- Migration: `pims/migrations/2026-04-27_checklist_items.sql`
- Matcher: `pims/services/checklist_matcher.py`
- Renderer: `pims/audit_report_docx.py` (rewritten in place)
- Route: `pims/routes.py` (`POST /pims/site-visit-report`)
- Frontend: `pims/pims_dashboard.html` (existing button reused, repointed)
- New template: `pims/RPD_SSA_template.docx`
- Reused helpers: `src/docx_style_standard.py`

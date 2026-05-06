"""Build the SSA pipeline Codex review bundle.

Concatenates the original plan plus every shipped implementation file
into ``docs/SSA_CODEX_REVIEW_BUNDLE.md``. Intended for handing to a
reviewer (Codex) who needs to diff plan against shipped reality.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "SSA_CODEX_REVIEW_BUNDLE.md"
PLAN_PATH = (
    Path.home() / ".claude" / "plans"
    / "workflow-1-i-upload-optimized-catmull.md"
)

FILES = [
    ("pims/services/ssa_pipeline.py",
     "Pipeline core: parser, matcher, three builders, enrichment, "
     "size-control wrapper, prior-rec parser, Findings #N expansion + "
     "index table, xlsx polish, RA-code labelling, significance "
     "ordering, anchor/Jaccard merge, manual --merge directives."),
    ("pims/services/ssa_checklist_lookup.py",
     "Legacy CCVS-keyed lookup over audit_checklist.xlsx. Kept as a "
     "deterministic fallback for --no-enrich mode; bypassed when "
     "vision is on (default)."),
    ("pims/services/ssa_ccvs_taxonomy.py",
     "Canonical 25-stream x 6-tier CCVS taxonomy. Replaces the "
     "audit_checklist.xlsx-derived 01.01 numeric scheme with the "
     "real WAH-H6 / SYS-M3 / etc. coding the canonical samples use."),
    ("pims/services/ssa_vision_enricher.py",
     "Per-row Anthropic vision call (Opus 4.7). Sends downscaled "
     "EXIF-normalised photo + observation text + project RA context. "
     "Receives status / ccvs_code / finding_title / location / "
     "finding / hierarchy_of_control / recommendation / timeframe / "
     "phase / activity_ref / hold_point / hrcw / swms_required / "
     "swms_present / initial_risk / residual_risk / legal_ref / "
     "monitoring_note. Transient-error retry; forgiving JSON parser."),
    ("pims/services/ssa_ra_parser.py",
     "Project Risk Assessment docx parser. Extracts metadata + 9 "
     "hold points + N phase activities; compact-context-block packs "
     "into the vision prompt so findings cite HP-04 / TP-05 / "
     "HRCW H14 inline."),
    ("pims/services/ssa_watcher.py",
     "Quiescence-gated folder watcher: settle_seconds + N stable "
     "polls; exclusions cover every watcher-owned artifact. "
     "Manifest-sha256 idempotency lives in the orchestrator."),
    ("pims/scripts/run_ssa_pipeline.py",
     "CLI orchestrator. Folder-name parse (with -NN sub-id), "
     "manifest sha256, preflight, freeze escape hatch, sentinels, "
     "RA auto-discover, vision wiring, three-phase review workflow "
     "(--enrich-only / --from-state / --from-report), --merge "
     "directives, .ssa_run.json + .ssa_state.json payloads."),
    ("pims/scripts/start_ssa_watcher.py",
     "Long-run entry for the watcher. Rotating-file logging."),
    ("pims/scripts/populate_prior_recs_table.py",
     "Operator-driven post-render edit: populates the Status of "
     "Previous Recommendations table with prior carry-forward + "
     "current-cycle rows under the 10 locked rules (allowed status "
     "set, DD-MMM-YYYY date format, F<n> refs, significance + date "
     "sort). Tracked-changes output (author=Claude)."),
    ("tests/test_ssa_pipeline.py",
     "99-case regression net. Covers parser, matcher, three "
     "builders, size-control + cache, manifest, watcher, vision "
     "coercion, RA parser, prior-rec parser, Findings #N expansion + "
     "index table, status colour fills, freeze, idempotency, "
     "partial-output recovery, anchor/Jaccard/strong-overlap merge, "
     "manual --merge directives, three-phase round-trip "
     "(--enrich-only / --from-state / --from-report)."),
]

INTRO = '''# SSA Pipeline — Codex Review Bundle

Single-document bundle of the **original plan** plus the **shipped
implementation** of the SSA evidence-folder → 3-deliverable pipeline.
Use this to diff plan vs. implementation and surface drift.

## What this bundle is for

The original plan was written before any of the canonical sample
deliverables had been opened. Real-folder runs against
`G:/My Drive/alan_mcxico/SSA-evidence/2026-05-01-SDG/` (with
`Unitas_Risk_Assessment_all.docx`, prior `260330-SDG.docx`, 21
photos, and the three canonical sample files in the parent folder)
revealed many contract mismatches between the plan and what Alan
considers canonical. The shipped pipeline has been progressively
re-aligned with the samples through a sequence of bug-fix and
delta-closure commits.

Use this document to:

1. Identify any remaining drift (places where the plan still differs
   from what the code actually does, or where the code still
   differs from the canonical samples).
2. Catch quality / correctness issues the test suite (99 pytest
   cases, all green; flake8 clean) does not assert against.
3. Suggest improvements to the plan itself so future work has a
   spec that matches the canonical samples.

## Drift between plan and shipped (current state)

| Axis | Plan / template said | Shipped reality | Why |
|---|---|---|---|
| CCVS code source | `pims/audit_checklist.xlsx` (Category / Criteria / Instruction; numeric `01.01` synthesised from leading digits) | Canonical 25 × 6 = 150 codes — 24 streams from `renderers/docx_renderer.py:_VALID_CCVS_STREAMS` plus `SYS` extension; suffixes H6 / H9 / M3 / M4 / L1 / L2 | Samples use `SYS-M3`, `MOB-H6`, `WAH-H6`, `STR-H9`, `ELE-H6`. The numeric scheme has no relationship to the canonical taxonomy. |
| Status assignment | Keyword auto-matcher (difflib token recall) emits Conditional / Unmatched only | Vision Anthropic call (Opus 4.7) emits Compliant / Conditional / NCR / Info / Unmatched | Sample is Compliant-heavy (39 / 64). A classifier that never produces Compliant cannot match the contract. |
| LLM gating | `PIMS_ENRICH_FINDINGS` env var, default OFF | Default ON; `--no-enrich` opts out; `ANTHROPIC_API_KEY` required at runtime | Sample observation / finding cells are LLM-rewritten multi-sentence narratives citing WHS Reg / AS / SafeWork NSW inline. |
| Vision support | text-only enrichment | Photo downscaled to 1024 px, EXIF-normalised, JPEG q85, base64-encoded; sent to vision model alongside the auditor's note | Photo is the primary evidence the human reviewer uses; required for accurate status assignment. |
| Project context | none | RA-aware: auto-discovers `*Risk_Assessment*.docx` in the audit folder, parses 9 hold points + 66 phase activities + project metadata, injects into the vision prompt | Without RA awareness the audit cannot reference `HP-04`, `TP-05`, `HRCW H14`, etc. — reviewer can't trace findings back to the principal contractor's WHS contract. |
| `#N` Findings layout | R-1.3 forbids paragraph-level cloning at body level | Cloning enabled for Findings list. Each finding renders as a `(#N <descriptive title>` heading + a 2-col 6-row detail table. Per-finding detail labels: `Location / Observation / Regulatory Basis / Hierarchy of Control / Recommendation / Timeframe`. The literal cell label `Required Action` from the template is rewritten to `Recommendation` at render time. | R-1.3 conflicts with V-10.5 ("count of #N paragraphs equals count of non-Compliant"). The canonical sample shows each finding rendering as a 6-row detail table with these specific labels. |
| Per-location 2-col block | Clone N times per detected location | Used as the per-finding detail block (per the canonical sample) — cloned once per non-Compliant row | The template's `Location / Observation / Regulatory Basis / Hierarchy of Control / Required Action / Timeframe` block is the per-finding detail card, not a per-location scaffold. |
| Status of Previous Recs | Parse prior report (deferred slice in plan) | `parse_prior_report_recommendations` extracts NCR / Conditional rows from the prior report's Observations Register; carry-forward dict written into the table. Header reads `Status (DD/MM/YY)` with the prior audit date substituted. | Reviewer needs carry-forward visibility; placeholder text wasn't acceptable. |
| Site address line | `{{SITE_ADDRESS}}` | Project name (from RA) prepended → `Unitas Business Park 4-6 Mile End Rd Rouse Hill NSW 2155` | Sample p4 carries the venue prefix. |
| Executive Summary | one paragraph (`{{NARRATIVE_SUMMARY}}`) | Two paragraphs — fixed scope intro ("This report presents the findings of a site safety audit conducted on `<long date>`...") plus dynamic LLM-generated narrative. Split via `_split_narrative_paragraph` after token substitution. | Sample carries both. |
| Per-finding detail table column language | Plan didn't specify | LLM produces tier-prefixed control language (`Engineering: <control>`), urgency-prefixed Recommendation (`Within 7 days – mount extinguishers on compliant brackets with location signage`, ≤15 words, paired-verb `establish and maintain` pattern for persistent controls), multi-instrument legal_ref (`WHS Act 2011 (NSW) s.19; WHS Reg r.291; SafeWork NSW COP: …`), Timeframe one of `Immediate / Within 7 days / Next audit / Ongoing / N/A` | Sample uses these conventions consistently. |
| Findings `#N` heading | Plan didn't specify | Descriptive title from the LLM (`#1 Steel Erection Exclusion Zone`); space-before of 240 twentieths-of-a-point (≈12 pt) on every `#N` heading so each finding visually breathes from the previous detail table | Sample uses descriptive titles, not `STATUS – CCVS-CODE`. |
| Positive Observations table | column widths inherited from template | column widths `1.5 / 7 / 9.5 cm`, bold header row, header repeats across page breaks (`<w:tblHeader/>`) | User direction. |
| Status of Previous Recs table | column widths inherited from template | column widths `6.5 / 4 / 2.5 / 4.75 cm` | User direction. |
| Observations Register table | header didn't repeat across pages | `<w:tblHeader/>` set on first row | User direction. |
| Staging xlsx polish | Plan said embed thumbnails; nothing about column widths / wrap / status fills | Column widths set, wrap_text on long-content columns, status colour fills (NCR red `FFC7CE`, Conditional amber `FFE699`, Compliant green `C6EFCE`, Info blue-grey `D9E1F2`, Unmatched neutral `F2F2F2`) | Sample uses these conventions; without them long enriched findings render truncated. |
| Enriched xlsx Summary sheet | Plan said write into named cells only | `_populate_enriched_summary_sheet` builds the canonical dashboard: title row + Audit Date / Site / Principal Contractor + Conformance Status counts + percentages + CCVS Category breakdown (Total / NCR / Conditional / Open Actions) + Open Actions list (#, Status, CCVS Code, Action Description, Responsible="PC", Due) | Sample carries this whole dashboard; mine had been rendering an empty Summary sheet. |
| Enriched Register field defaults | Plan said leave Responsible / Due / Close-out blank | Responsible="PC" on every row; Due = Immediate (NCR) / Next audit (Conditional / Unmatched) / N/A (Compliant / Info); Close-out Status="N/A" for Compliant / Info, blank for non-Compliant | Sample fills these deterministically. |
| `_clone_row` insertion order | not specified beyond "deepcopy and append" | append to END of `<w:tbl>` parent. The first attempt used `addnext` after placeholder + `rows[-1]` which silently corrupted every multi-row table (every clone except the last carried the placeholder content) | Caught by visual inspection of the docx; a regression test now locks the failure mode in. |
| Network retry | not specified | retries=2 on `httpx.ConnectError / ReadError / WriteError / TimeoutException / RemoteProtocolError` + HTTP 408 / 429 / 500 / 502 / 503 / 504; immediate raise on other 4xx (auth / billing) | Real-folder run dropped 2 of 21 rows to transient network errors mid-batch; retry recovers cleanly. |
| API error reporting | not specified | HTTP error tag now includes the API's own `error.type` + `error.message` so billing / auth issues surface as e.g. `"http 400 invalid_request_error: Your credit balance is too low"` instead of generic "bad request" | Surfaced when a credit-exhaustion failure was misread as a code defect. |
| Humaniser ruleset | Plan listed banned vocab + em-dash / signposting / sycophantic / emoji / curly-quote / passive-without-named-actor bans | All plan-listed bans are in both system prompts. Plus three additions caught in user review: rule-of-three constructions (with the actual phrases user highlighted as bad — `"available, accessible, and clearly identified"`, `"obscured, kicked, or removed"`); negative parallelism (`"not just X, but Y"`); legalistic connectors (`"contrary to"`, `"in breach of"`, `"in violation of"`, `"non-compliant with"`, `"pursuant to"`) — replaced by plain-English regulation framing (`"WHS Reg X requires Y; the site does not meet that standard"`) | Self-inflicted humaniser violations the original prompt taught the LLM to produce; user caught each on review. |
| Recommendation verb selection | not specified | Paired-verb pattern `"establish and maintain"` for persistent controls (exclusion zones, barriers, edge protection, traffic controls); single-shot `install / mount / fit` for fixtures; `complete / sign` for records; `verify / audit / check` for monitoring; `stop / stand down` for halt-work | User caught `"demarcate"` as too narrow — captures setup but not maintenance obligation. |
| Model | initial: `claude-sonnet-4-5-20250929` | `claude-opus-4-7` per user direction | Most capable model; supports vision. |
| Folder name | strict `YYYY-MM-DD-<RPD or SDG>` | also accepts optional `-NN` sub-id (`2026-05-01-SDG-01`) for split-day visits; sub-id propagates into all output filenames | Multiple visits to the same site on the same day need distinct deliverable names. |
| Runtime preflight | nothing | `PreflightError` raised before row processing when `enrich=True` and `ANTHROPIC_API_KEY` is missing; CLI rc=3 | Operators hit "silent semantic degradation" twice; loud failure prevents both. |
| Findings index table | not in plan | 3-column `# | Finding | Recommendation` table inserted directly under the Findings heading; numbered 1..N matching the per-finding detail blocks; bold header, all-cell borders, header repeats | Reviewer ask 2026-05-06: visible navigation aid. |
| Significance ordering | not in plan | `_significance_score` ranks: HP breach > SWMS gap > plant/public (MOB/CRN/TRF H6/H9) > permit-class (HOT/ASB/CFS/DEM/ELE H6/H9) > generic; secondary axes break ties on status then CCVS tier | Reviewer ask: critical-safety findings appear at the top of the Findings index + detail blocks. |
| Multi-issue row splitting | not in plan | `(1) ... (2) ... (3) ...` composite notes split into separate atomic ObservationRows BEFORE photo-match metadata is consumed; each shares the source photo + timestamp | Auditors record several distinct issues against one photo with leading numerals. |
| Similar-finding merge | not in plan | `merge_similar_findings` consolidates non-Compliant rows that share status + stream + (title equality OR recommendation Jaccard ≥0.5 OR ≥4 content-token overlap OR anchor-phrase like {establish, zone}). Anchor merge crosses streams — an exclusion zone above a steel lift (WAH-H6) and the telehandler beneath it (MOB-H9) are physically the same intervention. Plural-stem trim (`zone` / `zones` collapse) | Reviewer call 2026-05-06: the merge criterion is the recommended action / control intent, not the descriptive title. |
| Manual `--merge` directive | not in plan | Operator can pass `--merge "1,3"` (or `"1,3;5,7,8"`) to consolidate findings by displayed index when the auto-merge can't infer the intent from text alone | Escape hatch for cases the heuristic doesn't catch. |
| Per-finding detail table layout | not in plan | Each finding renders as `#N <title>` heading + 6-row 2-col detail table: `Location | Observation | Regulatory Basis | Hierarchy of Control | Recommendation | Timeframe`. Template label `Required Action` rewritten to `Recommendation` at render time. Tier-prefixed Hierarchy (`Engineering: ...`), urgency-prefixed Recommendation (`Within 7 days – ...`, ≤15 words). | Canonical sample shape; "Recommendation" is the reviewer-facing label. |
| Status of Previous Recs schema | plan: `Recommendation | Required Actions | Status (DD/MM/YY) | Commentary` | New schema: `Date | Recommendations | Status as of <DD-MMM-YYYY> | Comments`. Column widths 2.5 / 6.25 / 2.5 / 6.25 cm. Bold header, header-repeats, all-cell borders. Date format DD-MMM-YYYY (4-digit year). | Reviewer direction 2026-05-06 — table now chains forward audit-by-audit. |
| Prior-recs population | plan: parse prior report into `prior_recs` (deferred) | `populate_prior_recs_table.py` enforces the 10 locked rules: allowed statuses Completed/Partial/Not completed/Not assessed only, "Retired" banned, dates DD-MMM-YYYY, F-refs in every Comments cell, default `Not assessed` when no current-cycle evidence, keep all carry-forwards + append all current-cycle, sort by significance + date. Output as Word tracked changes (author=Claude). | Reviewer direction 2026-05-06. |
| Cover/footer date formats | not in plan | Cover page: `1st May 2026` (ordinal long form). Running footer: `1-may-26` (short, lowercase month, 2-digit year). Same `{{AUDIT_DATE}}` placeholder; substitution branches per part. | Reviewer direction. |
| Table styling consistency | not in plan | Every multi-column table in the report (Findings index, Positive Observations, Status of Previous Recs, Observations Register) uses bold header + header-repeat + all-cell single-line borders. Per-finding detail tables get all-cell borders + bold left-column labels. | Reviewer direction 2026-05-06. |
| RA-code labelling | not in plan | Every TP-NN / HP-NN / HRCW H-NN reference in finding text / recommendation / hierarchy / monitoring / narrative is wrapped: `SDG Project Risk Assessment code: <CODE>`. First occurrence in each block expands the shorthand: `TP-07 (Tilt-Up Panel Erection activity 07)`. Adjacent codes collapse to `... codes: TP-05, HP-06`. Idempotent. | Reviewer ask 2026-05-06 — make every project-RA reference traceable. |
| Plain-English finding titles | not in plan | Vision prompt requires an active-voice sentence ≤12 words, no noun-phrase titles like "EWP Exclusion Zone". Good: "Temporary brace removal proceeded without engineer sign-off". | Reviewer direction. |
| Executive Summary cap | not in plan | Hard-truncated at 20 visual lines (~280 words); LLM prompt also targets ≤140 words. | Reviewer direction. |
| Humaniser hardening | plan banned vocab + em-dash | Banned vocabulary list, banned constructions: em-dash clusters, rule-of-three (with concrete sample phrases the user flagged: `"available, accessible, and clearly identified"`, `"obscured, kicked, or removed"`), negative parallelism, signposting, sycophantic openers/closers, emoji, curly quotes, passive voice without a named actor, legalistic connectors (`"contrary to"`, `"in breach of"`, `"in violation of"`, etc.). Recommendation verb selection: `establish and maintain` for persistent controls, `install/mount/fit` for fixtures, `complete/sign` for records, `verify/audit/check` for monitoring, `stop/stand down` for halt-work. | Reviewer caught self-inflicted humaniser violations on review iterations. |
| Three-phase review workflow | not in plan | Operator-driven review gate: `--enrich-only` writes enriched.xlsx + state JSON and exits → operator reviews/edits → `--from-state` rebuilds docx + staging from edits → operator reviews docx → `--from-report` flows docx edits BACK to enriched + staging xlsx. State JSON persists EnrichedRow rows + xlsx-snapshot fingerprint + `finding_render_order` for phase-3 pairing. | Reviewer ask: human review gate at every export boundary. |
| Image preprocessing cache | not in plan | `_PHOTO_CACHE` keyed by `(source_path, max_edge_px)` so size-control rerenders (1600 → 1200 → 1000 → 800 px) reuse preprocessed bytes. Cache delta reported in size-control diagnostics. | Real-folder runs hit the rerender ladder; cache avoids redundant CPU. |
| Network retry | not in plan | retries=2 on transient HTTP/network errors (ConnectError, ReadError, WriteError, TimeoutException, RemoteProtocolError, HTTP 408/429/500/502/503/504). 4xx other than these (auth, billing, bad request) raise immediately. | Real-folder run dropped 2 of 21 rows to transient errors mid-batch. |
| Forgiving JSON parser | not in plan | `_parse_json_object` strips code fences, then if `json.loads` fails, walks brace depth (respecting strings + escapes) to extract the first balanced `{...}` substring — handles LLM outputs that wrap JSON in prose despite "JSON ONLY" instruction. | Real-folder run had 5/21 rows landing as JSONDecodeError after schema expansion. |
| Legacy fallback retirement | plan default-on legacy matcher | Default vision path skips the audit_checklist.xlsx load entirely. Legacy keyword fallback only fires when operator explicitly passes `--no-enrich AND --checklist <path>`. | Real data: legacy matcher hit 5/21 with one outright misroute; vision is the canonical classifier. |

## Known remaining gaps (not yet shipped)

These are open items between the shipped output and the canonical
samples / the reviewer's stated requirements.

- **Positive Observations row IDs**: shipped — uses `P1 / P2 / P3`
  numbering with `"PIMS Obs N | <reg ref>"` cross-references. Open:
  no further drift here.
- **Observations Register scope**: shipped — register now carries
  every observation (Compliant + non-Compliant) with status
  cross-refs (`"Non-compliant — See F1"`, `"Partially complete —
  See F2"`, `"Compliant"`, `"Noted"`, `"Review at QA"`). Open: no
  further drift.
- **HRCW / Hold Point staging columns**: shipped — `phase`,
  `activity_ref`, `hold_point`, `hrcw` columns added to the staging
  template; vision enricher populates from RA context. Open: no
  further drift.
- **SWMS verification**: shipped — `swms_required` (TRUE/FALSE) and
  `swms_present` (yes/no/unknown) columns + LLM coercion. Open: no
  further drift.
- **Initial / Residual risk axis**: shipped — `initial_risk` /
  `residual_risk` columns with H/M/L canonicalisation; LLM
  forbidden from inventing rating from photo alone. Open: no
  further drift.
- **Image preprocessing cache**: shipped — `_PHOTO_CACHE` keyed
  by `(source_path, max_edge_px)` reuses bytes across size-control
  rerenders; diagnostics report hit/miss delta.
- **Legacy `audit_checklist.xlsx` fallback retirement**: shipped —
  default vision path skips the legacy load entirely; only fires
  on explicit `--no-enrich --checklist <path>`. Could be retired
  fully once vision is locked as the only supported path.

Genuinely open items:

- **Three-phase round-trip merge fidelity**: phase 3 (`--from-report`)
  pairs detail tables to EnrichedRows by `finding_render_order`
  position. If the operator deletes / reorders detail tables in
  Word, the pairing breaks silently. Could be hardened by tagging
  each rendered detail table with an invisible `csv_idx` bookmark
  and reading it back during phase 3.
- **Phase-2 false-positive overrides**: the enriched xlsx
  fingerprint snapshot reduces false positives but a couple of
  rendered-fallback values (Action Description, Due) still register
  as edits because the rendered cell value differs from the
  underlying attribute. Harmless; cosmetic only.
- **Auto-merge calibration**: the {establish, zone} anchor + 4-token
  strong-overlap rule was tuned against one real-folder corpus
  (Unitas, 23 rows). Could over-merge or under-merge on materially
  different audit content; needs a fixture corpus to validate.
- **Vision JSON output schema**: 18 fields requested per row pushes
  the LLM toward occasional prose-wrapped JSON. The forgiving parser
  catches most cases; very rarely a row still fails. A "rewrite to
  strict JSON" retry call would close this.

## File inventory

'''


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        fh.write(INTRO)
        for rel, desc in FILES:
            p = ROOT / rel
            loc = p.read_text(encoding="utf-8").count("\n") + 1 if p.exists() else 0
            fh.write(f"- **`{rel}`** ({loc} lines) — {desc}\n")

        fh.write("\n---\n\n## Original plan\n\n")
        fh.write(f"Source: `{PLAN_PATH}`\n\n")
        if PLAN_PATH.exists():
            fh.write("````markdown\n")
            fh.write(PLAN_PATH.read_text(encoding="utf-8"))
            fh.write("\n````\n\n")
        else:
            fh.write("(plan file not found at the expected path)\n\n")

        fh.write("---\n\n## Shipped implementation\n\n")
        for rel, desc in FILES:
            p = ROOT / rel
            if not p.exists():
                fh.write(f"### `{rel}` — MISSING\n\n")
                continue
            ext = p.suffix.lstrip(".")
            fence = "python" if ext == "py" else ext
            fh.write(f"### `{rel}`\n\n{desc}\n\n```{fence}\n")
            fh.write(p.read_text(encoding="utf-8"))
            fh.write("\n```\n\n")

    print(f"wrote {OUT.relative_to(ROOT)}, {OUT.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()

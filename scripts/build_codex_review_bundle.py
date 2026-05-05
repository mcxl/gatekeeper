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
     "size-control wrapper, prior-rec parser, Findings #N expansion, "
     "xlsx polish helper."),
    ("pims/services/ssa_checklist_lookup.py",
     "Legacy CCVS-keyed lookup over audit_checklist.xlsx. Kept as a "
     "deterministic fallback for --no-enrich mode; bypassed when "
     "vision is on."),
    ("pims/services/ssa_ccvs_taxonomy.py",
     "Canonical 25-stream x 6-tier CCVS taxonomy. Replaces the "
     "audit_checklist.xlsx-derived 01.01 numeric scheme with the "
     "real WAH-H6 / SYS-M3 / etc. coding the canonical samples use."),
    ("pims/services/ssa_vision_enricher.py",
     "Per-row Anthropic vision call (Opus 4.7). Sends downscaled "
     "EXIF-normalised photo + observation text + project RA context. "
     "Receives status / ccvs_code / finding / legal_ref / "
     "recommendation / monitoring_note. Transient-error retry."),
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
     "CLI orchestrator. Folder-name parse, manifest sha256, freeze "
     "escape hatch, sentinels (NOT_UPLOADABLE / NO_BULK_ENDPOINT), "
     "RA auto-discover, vision wiring, .ssa_run.json payload."),
    ("pims/scripts/start_ssa_watcher.py",
     "Long-run entry for the watcher. Rotating-file logging."),
    ("tests/test_ssa_pipeline.py",
     "69-case regression net. Covers parser, matcher, three "
     "builders, size-control, manifest, watcher, vision coercion, "
     "RA parser, prior-rec parser, Findings #N expansion, status "
     "colour fills, freeze, idempotency, partial-output recovery."),
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
2. Catch quality / correctness issues the test suite (70 pytest
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

## Known remaining gaps (not yet shipped)

These are still drift items between the shipped output and the
canonical samples.

- **Positive Observations row IDs and cross-references**: sample uses
  `P1 / P2 / P3` numbering with `"PIMS Obs N | <reg ref>"` cross-
  references in the Reference column. Mine uses plain `1 / 2 / 3`
  with the `legal_ref` alone. Needs a row-id assigner + cross-ref
  builder that links Positive rows back to Enriched register row
  numbers.
- **Observations Register scope**: sample carries ALL observations
  (Compliant + non-Compliant) with free-form status text such as
  `"See F1 re exclusion zone"` / `"Non-compliant – See F2"` /
  `"Noted"` / `"Partially complete – monitor"` referencing the
  finding numbers from the Findings section. Mine carries only
  non-Compliant rows with the canonical status set. Needs the
  register to be the master observation list + a finding-cross-
  reference text generator.
- **HRCW / Hold Point cross-reference columns in staging xlsx**:
  vision findings reference HP / activity refs inside the finding
  text, but no dedicated `phase` / `activity_ref` / `hold_point`
  columns are added to the staging xlsx. Reviewer reads them as
  part of the narrative.
- **Compliant / Info SWMS verification**: RA mandates SWMS
  verification across nearly every activity row; the audit doesn't
  generally check for SWMS presence beyond the rows where the
  auditor noted it.
- **Initial / Residual risk axis**: RA uses H / M / L 3 / 2 / 1
  rubric for both initial and residual risk. SSA tier suffix
  (H6 / H9 / M3 / M4 / L1 / L2) carries severity but uses a
  different rubric.
- **Image preprocessing cache (Appendix C §C.6)**: the staging
  size-control wrapper re-renders at progressively smaller caps but
  doesn't share preprocessed `BytesIO` across rerenders; cache key
  is implicit per-call. Functional but wastes CPU on large audits
  that need progressive downscale.
- **`audit_checklist.xlsx` legacy fallback**: still single-source-
  of-truth for the legacy keyword matcher (`enrich_observations(...,
  auto_match=True)`). Default is now `auto_match=False` so vision
  is the only path the orchestrator uses. The xlsx-based path could
  be retired entirely once vision is confirmed as the canonical
  classifier.

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

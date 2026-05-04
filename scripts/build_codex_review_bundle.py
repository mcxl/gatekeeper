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
deliverables had been opened. Real-folder runs (specifically
`G:/My Drive/alan_mcxico/SSA-evidence/2026-05-01-SDG/`) revealed
several contract mismatches between the plan and what the user
considers canonical. Most of those were corrected during the build
and are listed in the **Drift between plan and shipped** section
below.

Use this document to:

1. Identify any remaining drift (places where the plan still differs
   from what the code actually does).
2. Catch quality / correctness issues the test suite (69 pytest
   cases, all green; flake8 clean) does not assert against.
3. Suggest improvements to the plan itself so future work has a
   spec that matches the canonical samples.

## Drift between plan and shipped (already-known deltas)

These are deliberate departures from the plan, made because the
canonical samples (`PIMS-Enriched - Sample.xlsx`,
`Site-Visit-Report- Upload to PIMS Staging.xlsx`,
`Site-Safety-Audit-Report - new Sample.docx`,
`Unitas_Risk_Assessment_all.docx`) showed the plan's contract was
wrong on these axes:

| Axis | Plan says | Shipped reality | Why |
|---|---|---|---|
| CCVS code source | `pims/audit_checklist.xlsx` (Category/Criteria/Instruction; numeric `01.01` synthesised from leading digits) | Canonical 25 × 6 = 150 codes from `renderers/docx_renderer.py:_VALID_CCVS_STREAMS` + `SYS` extension; tier suffixes H6/H9/M3/M4/L1/L2 | Sample uses `SYS-M3`, `MOB-H6`, `WAH-H6`, `STR-H9`, `ELE-H6`. The 01.01 scheme has no relationship to the canonical taxonomy. |
| Status assignment | Keyword auto-matcher (difflib token recall) emits Conditional/Unmatched only | Vision Anthropic call (Opus 4.7) emits Compliant/Conditional/NCR/Info/Unmatched | Sample is Compliant-heavy (39/64). A classifier that never produces Compliant cannot match the contract. |
| LLM gating | `PIMS_ENRICH_FINDINGS` env var, default OFF | Default ON; `--no-enrich` opts out; `ANTHROPIC_API_KEY` required at runtime | Sample observation/finding cells are LLM-rewritten multi-sentence narratives citing WHS Reg / AS / SafeWork NSW inline. |
| Vision support | text-only enrichment | photo (downscaled to 1024 px, EXIF-normalised, JPEG q85, base64) sent to vision model | Photo is the primary evidence the human reviewer uses; required for status assignment. |
| Project context | none | RA-aware: auto-discovers `*Risk_Assessment*.docx` in the audit folder, parses metadata + 9 hold points + 66 phase activities, injects into vision prompt | Without RA awareness the audit cannot reference HP-04 / TP-05 / HRCW H14, etc. — reviewer can't trace findings back to the principal contractor's WHS contract. |
| `#N` Findings cloning | R-1.3 forbids paragraph-level cloning at body level | Cloning enabled for Findings list (heading + body pair per non-Compliant row) | R-1.3 conflicts with V-10.5 ("count of #N paragraphs equals count of non-Compliant"). Without cloning, the rendered docx leaves only the template's `#1` placeholder visible. |
| Per-location 2-col block | Clone N times per detected location | Always remove (R-1.3(e) explicitly permits removal) | Location detection is out of scope for v1. Removing avoids a stale 6-row scaffold in the output. |
| Status of Previous Recs | Parse prior report (deferred slice in plan) | Implemented: `parse_prior_report_recommendations` extracts NCR/Conditional rows from the prior report's Observations Register | Reviewer needs carry-forward visibility; placeholder text wasn't acceptable. |
| Staging xlsx polish | Plan said embed thumbnails; nothing about column widths / wrap / status fills | Column widths set, wrap_text on long-content columns, status colour fills (NCR red, Conditional amber, Compliant green, Info blue-grey, Unmatched neutral) | Sample uses these conventions; without them long enriched findings render truncated and reviewer can't scan status at a glance. |
| `_clone_row` insertion order | not specified beyond "deepcopy and append" | append to END of `<w:tbl>` parent (was: `addnext` after placeholder, with `rows[-1]` returning the wrong row) | The first attempt used `addnext` which silently corrupted multi-row tables — every clone except the last carried the placeholder content. Caught by visual inspection of the docx; a regression test now locks the failure mode in. |
| Network retry | not specified | retries=2 on `httpx.ConnectError/ReadError/WriteError/TimeoutException/RemoteProtocolError` + HTTP 408/429/500/502/503/504; immediate raise on other 4xx | Real-folder run dropped 2 of 21 rows to transient network errors mid-batch; retry recovers cleanly. |
| Model | claude-sonnet-4-5-20250929 (initial) | claude-opus-4-7 (after user direction) | Most capable model; supports vision. |

## Known remaining gaps (not yet shipped)

- **HRCW / Hold Point cross-reference columns**: vision findings reference HP/activity refs inside finding text, but no dedicated `phase` / `activity_ref` / `hold_point` columns in the staging xlsx. Reviewer reads them as part of the narrative.
- **Compliant / Info SWMS verification**: RA mandates SWMS verification across nearly every activity row; the audit doesn't generally check for SWMS presence beyond the rows where the auditor noted it.
- **Initial / Residual risk axis**: RA uses H/M/L 3/2/1 rubric for both initial and residual risk. SSA tier suffix (H6/H9/M3/M4/L1/L2) carries severity but uses a different rubric.
- **Image preprocessing cache (Appendix C §C.6)**: the staging size-control wrapper re-renders at progressively smaller caps but doesn't share preprocessed BytesIO across rerenders; cache key is implicit per-call. Functional but wastes CPU on large audits that need progressive downscale.
- **`audit_checklist.xlsx` legacy fallback**: still single-source-of-truth for the legacy keyword matcher when `--no-enrich`. Could be retired once vision is the only supported path.

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

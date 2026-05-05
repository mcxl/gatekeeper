"""Manual CLI for the SSA evidence-folder → 3-deliverable pipeline.

    python -m pims.scripts.run_ssa_pipeline "<folder>"

Bypasses the watcher; runs the same pipeline once over the supplied
folder. The watcher (added separately) is the long-running entry that
drives this same orchestration on quiescent folders.

v1 scope:
  - parse Evidence_Master.csv, match photos, extract site address
  - lift to EnrichedRow (every row Unmatched until CCVS auto-matcher
    lands as a separate slice)
  - build all three deliverables
  - compute staging_status (tri-state per workflow plan)
  - write sentinel file when applicable
  - write .ssa_run.json with outputs + warnings + status

v1 NON-scope (deferred slices, called out in the plan):
  - input-manifest sha256 + idempotency skip (watcher concern)
  - LLM finding-rewrite + narrative summary (separate async pass)
  - staging 5 MB progressive-downscale + size-based split
  - quiescence polling
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from pims.services.ssa_checklist_lookup import ChecklistLookup
from pims.services.ssa_pipeline import (
    EnrichedRow,
    apply_ra_labels_to_rows,
    build_pims_enriched_xlsx,
    build_pims_staging_xlsx_with_size_control,
    build_ssa_report_docx,
    enrich_observations,
    extract_site_address,
    match_photos,
    parse_evidence_csv,
    parse_prior_report_recommendations,
    split_multi_issue_observations,
)

log = logging.getLogger("ssa.cli")


# Folder name contract: YYYY-MM-DD-<CLIENT>, CLIENT ∈ {RPD, SDG}
_FOLDER_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(RPD|SDG)$")

# Image extensions the watcher cares about. PNG-with-transparency is
# legal but rare; HEIC explicitly out of scope (filename canonicalisation
# rules in the plan).
_IMAGE_EXTS = {".jpg", ".jpeg", ".png"}

# Client-bulk-endpoint capability (gate 0). RPD has it today, SDG
# doesn't — confirmed against pims/routes.py:2091.
_BULK_ENDPOINT = {"RPD": "/pims/upload/observations", "SDG": None}


def _parse_folder(folder: Path) -> tuple[str, str, str, str]:
    """Return (audit_date_iso, audit_date_ddmmyyyy, yymmdd, client).

    Raises ValueError when the folder name doesn't match the contract —
    rerun with a renamed folder is the documented remediation.
    """
    m = _FOLDER_RE.match(folder.name)
    if not m:
        raise ValueError(
            f"folder name {folder.name!r} does not match YYYY-MM-DD-<CLIENT> "
            f"with CLIENT in (RPD, SDG)"
        )
    yyyy, mm, dd, client = m.groups()
    iso = f"{yyyy}-{mm}-{dd}"
    ddmmyyyy = f"{dd}/{mm}/{yyyy}"
    yymmdd = f"{yyyy[2:]}{mm}{dd}"
    # Sanity-check the date itself; ValueError on Feb 30 etc.
    datetime.strptime(iso, "%Y-%m-%d")
    return iso, ddmmyyyy, yymmdd, client


def _output_names(yymmdd: str, client: str) -> dict[str, str]:
    return {
        "enriched": f"PIMS-Enriched-{yymmdd}-{client}.xlsx",
        "report": f"Site-Safety-Audit-Report-{yymmdd}-{client}.docx",
        "staging": f"Site-Visit-Report-Upload-PIMS-Staging-{yymmdd}-{client}.xlsx",
    }


def _images_in(folder: Path) -> list[Path]:
    return sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in _IMAGE_EXTS
    )


# Filename-date-suffix on a prior SSA report: ``...YYMMDD-<CLIENT>.docx``.
_PRIOR_REPORT_RE = re.compile(
    r"^Site-Safety-Audit-Report-(\d{6})-(RPD|SDG)\.docx$"
)


def _qualifying_prior_reports(
    folder: Path, current_iso: str, current_target: str,
) -> list[Path]:
    """Return prior SSA reports eligible for input-manifest inclusion.

    Eligible iff ALL:
      - filename matches ``Site-Safety-Audit-Report-YYMMDD-<CLIENT>.docx``
      - parsed date strictly earlier than the current folder's audit date
      - filename != the current target output filename

    Per the plan's "Prior-report reuse policy". Files whose date suffix
    is missing/unparseable are non-qualifying — never guessed from mtime.
    """
    out: list[Path] = []
    for p in folder.iterdir():
        if not p.is_file():
            continue
        if p.name == current_target:
            continue
        m = _PRIOR_REPORT_RE.match(p.name)
        if not m:
            continue
        yymmdd = m.group(1)
        try:
            cand_iso = datetime.strptime(yymmdd, "%y%m%d").date().isoformat()
        except ValueError:
            continue
        if cand_iso < current_iso:
            out.append(p)
    return sorted(out)


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _compute_manifest(
    csv_path: Path, images: list[Path], prior_reports: list[Path],
) -> str:
    """Full-content sha256 over CSV + images + qualifying prior reports.

    Per the watcher contract: hash the sorted ``filename || sha256(bytes)``
    pairs so that any byte-level change in any input flips the manifest.
    Filenames are lowercased for case-insensitive volumes (Windows).
    """
    parts: list[str] = []
    for p in [csv_path, *images, *prior_reports]:
        parts.append(f"{p.name.lower()}||{_file_sha256(p)}")
    parts.sort()
    h = hashlib.sha256()
    for line in parts:
        h.update(line.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _existing_run_record(folder: Path) -> dict | None:
    rj = folder / ".ssa_run.json"
    if not rj.exists():
        return None
    try:
        return json.loads(rj.read_text(encoding="utf-8"))
    except Exception:
        log.warning(".ssa_run.json unreadable; treating as missing")
        return None


def _write_sentinel(folder: Path, name: str, body: str) -> str:
    path = folder / name
    path.write_text(body, encoding="utf-8")
    return path.name


def _resolve_staging_status(
    client: str, site_address: str | None,
) -> tuple[str, str | None]:
    """Return (staging_status, blocker) per the tri-state contract."""
    if not site_address:
        return "not_uploadable", "site_address_unresolved"
    if _BULK_ENDPOINT.get(client) is None:
        return "schema_valid_no_endpoint", None
    return "bulk_uploadable", None


def _apply_vision_enrichment(
    enriched: list[EnrichedRow],
    site_address: str | None,
    audit_date_iso: str,
    enable: bool,
    ra_context: str = "",
) -> tuple[str, dict]:
    """Vision-enabled per-row classification + narrative summary.

    Returns ``(narrative_paragraph, diagnostics_dict)``. On any failure
    path (LLM disabled, key missing, network error, JSON parse error,
    timeout) the function returns an empty narrative and a diagnostics
    dict describing what happened — never raises into the orchestrator.

    Side-effect: in-place mutation of every row that the LLM
    successfully classifies — sets ``conformance_status``,
    ``ccvs_code``, ``ccvs_category``, ``finding``, ``legal_ref``,
    ``recommendation``, ``monitoring_note``. Rows that fall through
    the LLM (no photo / API error / parse error) keep their default
    ``Unmatched`` state.
    """
    if not enable or not enriched:
        return "", {"enabled": False, "rows_total": len(enriched)}

    from pims.services.ssa_vision_enricher import (
        enrich_rows_with_vision,
        generate_narrative_summary,
    )

    async def _drive() -> tuple[str, dict]:
        diag = await enrich_rows_with_vision(
            enriched,
            site_address=site_address or "",
            audit_date_iso=audit_date_iso,
            ra_context=ra_context,
        )
        text = await generate_narrative_summary(
            enriched,
            site_address=site_address or "",
            audit_date_iso=audit_date_iso,
        )
        return text, diag

    try:
        narrative, diag = asyncio.run(_drive())
    except Exception as exc:
        log.warning("vision enrichment driver failed: %s", exc, exc_info=True)
        return "", {
            "enabled": True, "driver_error": f"{type(exc).__name__}: {exc}",
            "rows_total": len(enriched),
        }
    diag["enabled"] = True
    return narrative, diag


class PreflightError(RuntimeError):
    """Raised when a required runtime precondition is missing.

    Distinct from generic ``RuntimeError`` so the CLI can surface the
    failure with a clean exit code and human-readable message before
    any rows are processed (rather than silently producing
    semantically-degraded output).
    """


def _preflight(enrich: bool) -> None:
    """Fail loud BEFORE any row processing when required runtime
    preconditions are missing.

    Currently checks:
      - When ``enrich`` is True, ``ANTHROPIC_API_KEY`` must be set in
        the environment. Without it the vision enricher silently
        leaves every row at ``status="Unmatched"``, and operators
        have hit this twice — once mistaking the result for a code
        bug, once for a billing problem. A loud preflight failure
        prevents both.

    Caller can short-circuit with ``--no-enrich`` when they
    deliberately want the offline path.
    """
    if enrich and not os.environ.get("ANTHROPIC_API_KEY"):
        raise PreflightError(
            "ANTHROPIC_API_KEY is not set in the environment. "
            "Either set the key (load .env, run with the key exported, "
            "or invoke from a shell that already has it) or pass "
            "--no-enrich to run the deterministic offline path "
            "(every row will land Unmatched)."
        )


def run_once(
    folder: Path,
    prepared_by: str = "Alan Richardson",
    ignore_freeze: bool = False,
    checklist_path: Path | None = None,
    force: bool = False,
    enrich: bool = True,
    risk_assessment_path: Path | None = None,
) -> dict:
    """Run the pipeline once. Returns the .ssa_run.json payload.

    Idempotency: when ``force`` is False and a prior ``.ssa_run.json``
    is present whose ``inputs_sha256`` matches the current manifest AND
    every recorded output still exists on disk, the run is a no-op and
    the existing payload is returned with ``skipped=True`` set.
    """
    folder = folder.resolve()
    if not folder.is_dir():
        raise NotADirectoryError(folder)

    # Runtime preflight — must happen before any row processing so a
    # missing API key (or other config gap) fails loud rather than
    # producing a structurally-valid but semantically-degraded run.
    _preflight(enrich=enrich)

    freeze = folder / ".ssa_freeze"
    if freeze.exists() and not ignore_freeze:
        raise RuntimeError(
            f"frozen — use --ignore-freeze to overwrite ({freeze})"
        )

    iso, ddmmyyyy, yymmdd, client = _parse_folder(folder)
    csv_path = folder / "Evidence_Master.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Evidence_Master.csv missing in {folder}")

    images = _images_in(folder)
    if not images:
        raise FileNotFoundError(f"no images found in {folder}")

    # --- manifest + idempotency -------------------------------------
    names = _output_names(yymmdd, client)
    prior_reports = _qualifying_prior_reports(folder, iso, names["report"])
    manifest = _compute_manifest(csv_path, images, prior_reports)

    prior_record = _existing_run_record(folder)
    if (
        not force
        and prior_record is not None
        and prior_record.get("inputs_sha256") == manifest
        and all((folder / n).exists() for n in prior_record.get("outputs", []))
    ):
        prior_record["skipped"] = True
        log.info("manifest unchanged + outputs present — skipping")
        return prior_record

    # --- parse + match + address ------------------------------------
    rows, csv_warnings = parse_evidence_csv(csv_path)
    match_warnings = match_photos(rows, images)

    # Item 11: split composite "(1) X (2) Y" notes into atomic
    # observations BEFORE photo-match metadata is consumed downstream.
    # Each split shares the same csv_row, photo and timestamp; only
    # the observation_text differs.
    rows = split_multi_issue_observations(rows)

    # Gap-8: Vision is the canonical classifier. The legacy keyword
    # matcher in ChecklistLookup.match_observation produced 5/21 hits
    # with one outright misroute on real audit data — it's only kept
    # for the offline (--no-enrich) path AND only when the operator
    # explicitly passes --checklist. The default (vision) path skips
    # the xlsx load entirely so a missing audit_checklist.xlsx never
    # silently degrades the run.
    checklist = None
    if not enrich and checklist_path is not None:
        if checklist_path.exists():
            checklist = ChecklistLookup.from_xlsx(checklist_path)
        else:
            log.warning(
                "--checklist %s does not exist; offline run continues "
                "with no keyword fallback", checklist_path,
            )

    site_address = extract_site_address(rows)

    # When vision is on, enrich_observations builds shells only — the
    # vision pass downstream does the real classification. When vision
    # is off and a checklist was loaded, enable the keyword auto-match
    # path so the run produces something better than all-Unmatched.
    enriched = enrich_observations(
        rows,
        checklist=checklist,
        auto_match=(checklist is not None and not enrich),
    )

    # When site_address is unresolved, every staging row must
    # needs_review=TRUE (Field Defaults). enrich_observations already
    # sets needs_review for Unmatched rows; flagging the obs surfaces
    # the address-unresolved reason in the warning trail.
    if site_address is None:
        for r in enriched:
            r.obs.flag("site_address_unresolved")

    # --- build deliverables -----------------------------------------
    enriched_path = folder / names["enriched"]
    report_path = folder / names["report"]
    staging_path = folder / names["staging"]

    site_for_docx = site_address or "[Site address - to be confirmed]"
    site_for_staging = site_address or ""

    # Project Risk Assessment context (optional). Auto-discovers any
    # ``*Risk_Assessment*.docx`` in the audit folder when no explicit
    # path is supplied. Empty string when no RA is available — the
    # vision call falls back to generic Australian-WHS classification.
    from pims.services.ssa_ra_parser import (
        autodiscover_in_folder, compact_context_block, parse_risk_assessment,
    )
    ra_path = risk_assessment_path
    if ra_path is None:
        ra_path = autodiscover_in_folder(folder)
    ra_context = ""
    ra_project_name = ""
    ra_obj = None
    ra_summary: dict[str, object] = {"path": None, "phases": 0, "activities": 0,
                                     "hold_points": 0}
    if ra_path is not None:
        ra = parse_risk_assessment(ra_path)
        ra_obj = ra
        ra_context = compact_context_block(ra)
        # Strip the "— N Industrial Warehouse Units" suffix that some
        # RA project names carry; the cover line wants just the venue.
        if ra.project_name:
            for sep in (" — ", " – ", " - "):
                if sep in ra.project_name:
                    ra_project_name = ra.project_name.split(sep, 1)[0].strip()
                    break
            else:
                ra_project_name = ra.project_name.strip()
        ra_summary = {
            "path": ra_path.name,
            "project": ra.project_name,
            "phases": len({a.phase for a in ra.activities}),
            "activities": len(ra.activities),
            "hold_points": len(ra.hold_points),
        }
        log.info(
            "RA loaded: %s — %d activities, %d hold points",
            ra_path.name, len(ra.activities), len(ra.hold_points),
        )

    # Vision enrichment — per-row classification (status, CCVS code,
    # finding text, legal_ref, recommendation, monitoring_note) plus
    # the Executive Summary paragraph. Default-on. No-op when
    # ``--no-enrich`` was passed or ANTHROPIC_API_KEY is unset.
    narrative_summary, llm_diag = _apply_vision_enrichment(
        enriched,
        site_address=site_address,
        audit_date_iso=iso,
        enable=enrich,
        ra_context=ra_context,
    )
    llm_diag["ra"] = ra_summary

    # Items 9 + 14: apply "SDG Project Risk Assessment code: <CODE>"
    # labelling with first-use shorthand expansion to every row's
    # text fields. Runs once after vision enrichment so the
    # downstream enriched xlsx / docx / staging xlsx all carry the
    # same labelled output.
    apply_ra_labels_to_rows(enriched, ra=ra_obj)
    # Item 9: label RA codes inside the executive summary too.
    from pims.services.ssa_pipeline import apply_ra_code_labels
    if narrative_summary:
        narrative_summary = apply_ra_code_labels(narrative_summary, ra=ra_obj)

    # Parse carry-forward recommendations from the newest qualifying
    # prior report so the SSA report's "Status of Previous
    # Recommendations" table actually carries content.
    prior_recs: list[dict] = []
    prior_audit_date_ddmmyy = ""
    if prior_reports:
        newest_prior = prior_reports[-1]
        prior_recs = parse_prior_report_recommendations(newest_prior)
        # Extract YYMMDD date from filename, format as DD/MM/YY for the
        # canonical "Status (DD/MM/YY)" header in the prior-recs table.
        m = re.search(r"-(\d{6})-(?:RPD|SDG)\.docx$", newest_prior.name)
        if m:
            yymmdd = m.group(1)
            prior_audit_date_ddmmyy = (
                f"{yymmdd[4:6]}/{yymmdd[2:4]}/{yymmdd[0:2]}"
            )

    # Pull principal contractor + project metadata from the parsed RA
    # so the Enriched workbook's Summary sheet matches the canonical
    # sample's title block / metadata rows.
    principal_contractor = ""
    if ra_path is not None:
        # Re-parse for the metadata only (compact_context_block already
        # consumed the parsed object once). Cheap; one xlsx-style read.
        try:
            ra_meta = parse_risk_assessment(ra_path)
            principal_contractor = ra_meta.principal_contractor
        except Exception:
            log.warning("RA principal-contractor lookup failed", exc_info=True)

    enriched_diag = build_pims_enriched_xlsx(
        enriched, enriched_path,
        project_name=ra_project_name,
        site_address=site_address or "",
        principal_contractor=principal_contractor,
        audit_date_ddmmyyyy=ddmmyyyy,
    )
    report_diag = build_ssa_report_docx(
        enriched,
        site_address=site_for_docx,
        audit_date_ddmmyyyy=ddmmyyyy,
        narrative_summary=narrative_summary,
        output_path=report_path,
        prepared_by=prepared_by,
        prior_recs=prior_recs,
        project_name=ra_project_name,
        prior_audit_date_ddmmyy=prior_audit_date_ddmmyy,
        risk_assessment=ra_obj,
    )
    report_diag["prior_recs_count"] = len(prior_recs)
    staging_result = build_pims_staging_xlsx_with_size_control(
        enriched,
        staging_path,
        site_address=site_for_staging,
        audit_date_iso=iso,
        prepared_by=prepared_by,
    )
    staging_diag = {
        "parts":         [p.name for p in staging_result["parts"]],
        "max_edge_px":   staging_result["max_edge_px"],
        "split":         staging_result["split"],
        "split_reason":  staging_result["split_reason"],
        "per_part":      staging_result["diagnostics"],
    }

    # --- staging tri-state ------------------------------------------
    staging_status, blocker = _resolve_staging_status(client, site_address)
    staging_part_names = [p.name for p in staging_result["parts"]]
    outputs: list[str] = [
        enriched_path.name,
        report_path.name,
        *staging_part_names,
    ]

    if staging_status == "not_uploadable":
        outputs.append(_write_sentinel(
            folder, "STAGING-NOT-UPLOADABLE.txt",
            f"staging blocker: {blocker}\n"
            f"folder: {folder.name}\n"
            f"remediation: see .claude/plans/workflow-1 — for "
            f"site_address_unresolved, add an address-shaped sentence to "
            f"a row in Evidence_Master.csv and rerun.\n",
        ))
    elif staging_status == "schema_valid_no_endpoint":
        outputs.append(_write_sentinel(
            folder, "STAGING-NO-BULK-ENDPOINT.txt",
            f"client: {client}\n"
            f"the staging xlsx is schema-valid and forward-compatible.\n"
            f"no bulk-upload endpoint exists for {client} today; post "
            f"observations one-at-a-time via the single-observation API.\n",
        ))

    # --- run record --------------------------------------------------
    payload = {
        "folder": folder.name,
        "client": client,
        "audit_date": iso,
        "inputs_sha256": manifest,
        "prior_reports_used": [p.name for p in prior_reports],
        "skipped": False,
        "prepared_by": prepared_by,
        "site_address": site_address,
        "site_address_unresolved": site_address is None,
        "staging_status": staging_status,
        "blocker": blocker,
        "client_bulk_endpoint": _BULK_ENDPOINT[client],
        "outputs": outputs,
        "row_count": len(enriched),
        "csv_warnings": [w.to_dict() for w in csv_warnings],
        "match_warnings": [w.to_dict() for w in match_warnings],
        "review_reasons_per_row": [
            {"csv_row": r.obs.csv_row, "reasons": list(r.obs.review_reasons)}
            for r in enriched if r.obs.review_reasons
        ],
        "enriched_diagnostics": enriched_diag,
        "report_diagnostics": report_diag,
        "staging_diagnostics": staging_diag,
        "llm_diagnostics": llm_diag,
        "completed_at": datetime.now(timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (folder / ".ssa_run.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="run_ssa_pipeline")
    ap.add_argument("folder", type=Path, help="audit evidence folder")
    ap.add_argument("--prepared-by", default="Alan Richardson")
    ap.add_argument("--ignore-freeze", action="store_true")
    ap.add_argument(
        "--force", action="store_true",
        help="ignore the manifest-based idempotency skip",
    )
    ap.add_argument("--checklist", type=Path, default=None)
    ap.add_argument(
        "--risk-assessment", type=Path, default=None,
        help="path to project Risk Assessment .docx; "
             "auto-discovered from audit folder when omitted",
    )
    ap.add_argument(
        "--no-enrich", action="store_true",
        help="skip the LLM finding-rewrite + narrative-summary pass",
    )
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )

    try:
        payload = run_once(
            args.folder,
            prepared_by=args.prepared_by,
            ignore_freeze=args.ignore_freeze,
            checklist_path=args.checklist,
            force=args.force,
            enrich=not args.no_enrich,
            risk_assessment_path=args.risk_assessment,
        )
    except PreflightError as e:
        # Preflight blocked the run before any rows processed; rc=3
        # distinguishes a config gap from a frozen folder (rc=2) and
        # an input/argument error (rc=1).
        print(f"preflight: {e}", file=sys.stderr)
        return 3
    except RuntimeError as e:
        # Frozen folder — the documented exit signal for the manual CLI
        # is non-zero with a clear message.
        print(f"error: {e}", file=sys.stderr)
        return 2
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if payload.get("skipped"):
        print("skipped: manifest unchanged + all outputs present")
    print(f"staging_status: {payload['staging_status']}")
    if payload.get("blocker"):
        print(f"blocker:        {payload['blocker']}")
    print(f"outputs:        {len(payload['outputs'])} files in {args.folder}")
    for name in payload["outputs"]:
        print(f"  - {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

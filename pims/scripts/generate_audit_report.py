"""Generate an RPD SSA audit report .docx (or multi-site .zip) from a
Site_Visit_Report-format xlsx.

Usage:
    python pims/scripts/generate_audit_report.py path/to/Site_Visit_Report.xlsx
    python pims/scripts/generate_audit_report.py path/to/file.xlsx --prepared-by "Alan Richardson"
    python pims/scripts/generate_audit_report.py path/to/file.xlsx --out path/to/out_dir/

Output filename convention:
    RPD_SSA_Audit_Report_<YYYY-MM-DD>-<NN>.docx

where YYYY-MM-DD is the audit date and NN is the sub-id parsed from the
parent folder name (e.g. ``2026-05-22-RPD-03`` -> NN = ``03``).
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
from datetime import date
from pathlib import Path

# Allow running directly from the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Best-effort .env loader so ANTHROPIC_API_KEY is picked up automatically
# (matches the pattern used by the Railway PIMS app).
import os  # noqa: E402
_env_file = _REPO_ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _v = _line.split("=", 1)
        _k = _k.strip(); _v = _v.strip().strip('"').strip("'")
        if _k and _k not in os.environ:
            os.environ[_k] = _v

from pims.services import audit_report_from_xlsx  # noqa: E402


# Folder name canonical form: ``YYYY-MM-DD-<CLIENT>-NN`` where CLIENT is
# RPD or SDG. NN is the audit sub-id.
_FOLDER_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(RPD|SDG)-(\d{2})$")


def _parse_folder_id(folder_name: str) -> tuple[str | None, str | None, str | None]:
    """Return (audit_date, client_code, nn) if folder_name matches the
    canonical form ``YYYY-MM-DD-<CLIENT>-NN``, else (None, None, None)."""
    m = _FOLDER_RE.match(folder_name)
    if not m:
        return (None, None, None)
    return (m.group(1), m.group(2), m.group(3))


def _render_pdf_sibling(docx_path: Path) -> Path | None:
    """Render a .pdf next to the .docx using docx2pdf (Word COM under the
    hood on Windows). Returns the pdf path on success, None otherwise.

    Failures are intentionally non-fatal: the operator can still issue
    the .docx if Word is unavailable. A clear warning is written to
    stderr so the failure isn't silent.
    """
    pdf_path = docx_path.with_suffix(".pdf")
    try:
        from docx2pdf import convert as _docx_convert
    except ImportError:
        print("WARNING: docx2pdf not installed; skipping PDF export.",
              file=sys.stderr)
        return None
    try:
        _docx_convert(str(docx_path), str(pdf_path))
    except Exception as e:
        print(f"WARNING: PDF export failed ({e}); .docx still written.",
              file=sys.stderr)
        return None
    if not pdf_path.exists():
        print("WARNING: PDF export reported success but file is missing.",
              file=sys.stderr)
        return None
    return pdf_path


def _compose_output_name(
    xlsx_path: Path, ext: str, xlsx_audit_date: str | None
) -> str:
    """Build the output filename.

    Primary source for audit_date and NN is the parent folder name (canonical
    ``YYYY-MM-DD-<CLIENT>-NN``). Falls back to the xlsx audit_date and today's
    date if the folder name is non-canonical; NN defaults to ``01`` with a
    stderr warning.
    """
    parent = xlsx_path.parent.name
    audit_date, _client, nn = _parse_folder_id(parent)
    if audit_date is None:
        audit_date = (xlsx_audit_date or date.today().isoformat())
        nn = "01"
        print(
            f"WARNING: parent folder '{parent}' does not match "
            f"YYYY-MM-DD-<RPD|SDG>-NN; defaulting NN=01 and "
            f"audit_date={audit_date}",
            file=sys.stderr,
        )
    if ext == ".docx":
        return f"RPD_SSA_Audit_Report_{audit_date}-{nn}{ext}"
    # Multi-site zip case
    return f"RPD_SSA_Audit_Reports_{audit_date}-{nn}{ext}"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("xlsx_path", type=Path)
    p.add_argument("--prepared-by", default=None,
                   help="Override Prepared by on the cover.")
    p.add_argument("--out", type=Path, default=None,
                   help="Output directory (defaults to xlsx_path.parent).")
    p.add_argument("--no-pdf", action="store_true",
                   help="Skip the sibling .pdf render (Word COM via "
                        "docx2pdf). Useful when Word is busy/unavailable.")
    enrich = p.add_mutually_exclusive_group()
    enrich.add_argument("--enrich-findings", dest="enrich_findings",
                        action="store_true", default=None,
                        help="Enable wording-enrichment staging stage "
                             "(overrides PIMS_ENRICH_FINDINGS env var).")
    enrich.add_argument("--no-enrich-findings", dest="enrich_findings",
                        action="store_false",
                        help="Disable wording-enrichment staging stage.")
    args = p.parse_args()

    if not args.xlsx_path.exists():
        print(f"ERROR: file not found: {args.xlsx_path}", file=sys.stderr)
        return 2
    raw = args.xlsx_path.read_bytes()
    if len(raw) > 5 * 1024 * 1024:
        print(f"ERROR: xlsx exceeds 5 MB ({len(raw):,} bytes)", file=sys.stderr)
        return 2
    if not raw:
        print("ERROR: empty file", file=sys.stderr)
        return 2

    # Auto-discover the sibling photos folder (any directory ending in
    # "-photos" inside the xlsx's parent). Photos referenced by name in
    # photo_refs will be loaded from there.
    photos_dir = None
    for sib in args.xlsx_path.parent.iterdir():
        if sib.is_dir() and sib.name.lower().endswith("-photos"):
            photos_dir = sib
            break

    # Read audit_date from xlsx as a fallback for filename composition;
    # folder name is the primary source.
    xlsx_audit_date: str | None = None
    try:
        obs = audit_report_from_xlsx.parse_xlsx(raw, photos_dir=photos_dir)
        xlsx_audit_date = next(
            (o.audit_date for o in obs if getattr(o, "audit_date", None)), None
        )
    except Exception as e:
        print(f"WARNING: could not pre-parse xlsx for audit_date: {e}",
              file=sys.stderr)

    # Resolve client display name from the folder's client code (RPD/SDG).
    _, client_code, _ = _parse_folder_id(args.xlsx_path.parent.name)
    client_display_name = (
        audit_report_from_xlsx.CLIENT_DISPLAY_NAMES.get(
            client_code or "",
            audit_report_from_xlsx.DEFAULT_CLIENT_DISPLAY_NAME,
        )
    )

    ext, payload = asyncio.run(
        audit_report_from_xlsx.build(
            raw, args.prepared_by, enrich_findings=args.enrich_findings,
            photos_dir=photos_dir,
            client_display_name=client_display_name,
        )
    )
    out_dir = args.out or args.xlsx_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_name = _compose_output_name(args.xlsx_path, ext, xlsx_audit_date)
    out_path = out_dir / out_name
    out_path.write_bytes(payload)
    print(f"WROTE {out_path}  ({len(payload):,} bytes)")

    # Render a sibling PDF for single-site docx outputs. Multi-site zip
    # bundles are left as-is; operator can extract and convert manually
    # if needed.
    if ext == ".docx" and not args.no_pdf:
        pdf = _render_pdf_sibling(out_path)
        if pdf is not None:
            print(f"WROTE {pdf}  ({pdf.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

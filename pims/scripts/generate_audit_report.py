"""Generate an RPD SSA audit report .docx (or multi-site .zip) from a
Site_Visit_Report-format xlsx.

Usage:
    python pims/scripts/generate_audit_report.py path/to/Site_Visit_Report.xlsx
    python pims/scripts/generate_audit_report.py path/to/file.xlsx --prepared-by "Alan Richardson"
    python pims/scripts/generate_audit_report.py path/to/file.xlsx --out path/to/out_dir/
"""
from __future__ import annotations

import argparse
import asyncio
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


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("xlsx_path", type=Path)
    p.add_argument("--prepared-by", default=None,
                   help="Override Prepared by on the cover.")
    p.add_argument("--out", type=Path, default=None,
                   help="Output directory (defaults to xlsx_path.parent).")
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

    ext, payload = asyncio.run(
        audit_report_from_xlsx.build(
            raw, args.prepared_by, enrich_findings=args.enrich_findings,
            photos_dir=photos_dir,
        )
    )
    out_dir = args.out or args.xlsx_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = date.today().isoformat()
    out_name = (
        f"RPD_SSA_AuditReport_{stamp}{ext}"
        if ext == ".docx"
        else f"RPD_SSA_AuditReports_{stamp}{ext}"
    )
    out_path = out_dir / out_name
    out_path.write_bytes(payload)
    print(f"WROTE {out_path}  ({len(payload):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

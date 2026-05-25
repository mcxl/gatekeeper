"""Generate a plain-text email draft summarising an audit report.

Usage:
    python pims/scripts/generate_audit_email_draft.py path/to/Site_Visit_Report.xlsx

Writes Email_Draft_<YYMMDD>_<site-slug>.txt next to the xlsx.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pims.services.audit_report_from_xlsx import parse_xlsx  # noqa: E402


def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")[:60] or "site"


def build_email_body(obs: list, report_path: Path) -> tuple[str, str]:
    if not obs:
        raise ValueError("xlsx contained no observation rows")
    sites = sorted({o.site_address for o in obs if o.site_address})
    site = sites[0] if sites else "(site)"
    audit_date = next((o.audit_date for o in obs if o.audit_date), "")
    statuses = Counter((o.status or "").strip() for o in obs)
    ncr = statuses.get("NCR", 0)
    cond = statuses.get("Conditional", 0)
    compliant = statuses.get("Compliant", 0)
    total = sum(statuses.values())

    ncr_lines: list[str] = []
    for o in obs:
        if (o.status or "").strip() != "NCR":
            continue
        action = (o.action_description or o.recommendation or "").strip()
        finding = (o.finding or o.observation_text or "").strip()
        bullet = f"- {finding[:240]}"
        if action:
            bullet += f"\n  Action: {action[:240]}"
        ncr_lines.append(bullet)

    subject = f"Site Safety Audit Report — {site} — {audit_date}"

    lines = [
        "Hi [Client Name],",
        "",
        f"Please find attached the Site Safety Audit Report for {site}, "
        f"conducted on {audit_date}.",
        "",
        "Summary of findings:",
        f"  • Observations recorded: {total}",
        f"  • Non-conformances (NCR): {ncr}",
        f"  • Conditional: {cond}",
        f"  • Compliant: {compliant}",
        "",
    ]

    if ncr_lines:
        lines.append("Non-conformances requiring immediate attention:")
        lines.extend(ncr_lines)
        lines.append("")
        lines.append(
            "Please review the attached report for the full register of "
            "observations, photos, and recommended actions. Items flagged "
            "as NCR should be addressed before the next site visit."
        )
    else:
        lines.append(
            "No non-conformances were identified during this audit. "
            "Please review the attached report for the full observation "
            "register and any monitoring notes for the next visit."
        )

    lines += [
        "",
        f"Attachment: {report_path.name}",
        "",
        "Please reply if any of the recommendations need clarification, or "
        "if you would like to discuss the findings on a brief call.",
        "",
        "Kind regards,",
        "Alan Richardson",
        "AuditCo",
        "1300 706 491 • www.auditco.com • info@auditco.com",
    ]
    return subject, "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("xlsx_path", type=Path)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    if not args.xlsx_path.exists():
        print(f"ERROR: file not found: {args.xlsx_path}", file=sys.stderr)
        return 2

    obs = parse_xlsx(args.xlsx_path.read_bytes())
    sites = sorted({o.site_address for o in obs if o.site_address})
    site = sites[0] if sites else "site"
    audit_date = next((o.audit_date for o in obs if o.audit_date), "")
    stamp = (audit_date or "").replace("-", "")[2:]  # YYMMDD
    if not stamp:
        from datetime import date
        stamp = date.today().strftime("%y%m%d")

    report_path = args.xlsx_path.parent / f"RPD_SSA_AuditReport_{audit_date}.docx"
    subject, body = build_email_body(obs, report_path)

    out_dir = args.out or args.xlsx_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_name = f"Email_Draft_{stamp}_{_slug(site)}.txt"
    out_path = out_dir / out_name
    out_path.write_text(
        f"Subject: {subject}\n\n{body}\n", encoding="utf-8",
    )
    print(f"WROTE {out_path}  ({out_path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

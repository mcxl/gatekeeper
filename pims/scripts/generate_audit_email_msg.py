"""Generate an Outlook .msg email draft for an audit report.

Usage:
    py -m pims.scripts.generate_audit_email_msg <xlsx_path>

Writes ``Email_Draft_<YYMMDD>_<site-slug>.msg`` next to the xlsx.
Double-clicking the .msg opens it in Outlook as an editable draft with
To: pre-filled (Matt + Nick at RPD), Subject set, and body ready to
send.

Requires:
- Windows with Outlook installed (any version with COM)
- Outlook profile configured for the user
- Pre-flight launches Outlook if it isn't already running
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# Fixed To: line for the RPD client. Uses the "Display Name <email>"
# form so Outlook shows the friendly name when the operator opens the
# draft; resolution falls back to plain email if the GAL/contacts don't
# have a match.
RPD_TO_RECIPIENTS = (
    "Matthew McCarthy <matt@rpd.net.au>; "
    "Nick Vuckovic <nick@rpd.net.au>"
)
DEFAULT_GREETING_TARGET = "Matt and Nick"

_FOLDER_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(RPD|SDG)-(\d{2})$")


def _compose_subject_and_body(
    obs, report_path: Path, greeting_target: str = DEFAULT_GREETING_TARGET,
) -> tuple[str, str]:
    """Build (subject, body) from observations using the existing email
    template, then rewrite the placeholder greeting for the fixed RPD
    recipients."""
    from pims.scripts.generate_audit_email_draft import build_email_body
    subject, body = build_email_body(obs, report_path)
    body = body.replace("Hi [Client Name],", f"Hi {greeting_target},")
    return subject, body


def _resolve_report_name(xlsx_path: Path, audit_date: str) -> str:
    """Best-effort guess of the sibling docx name (matches
    generate_audit_report's new convention) so the body's 'Attachment: '
    line is correct."""
    m = _FOLDER_RE.match(xlsx_path.parent.name)
    if m:
        return f"RPD_SSA_Audit_Report_{m.group(1)}-{m.group(3)}.docx"
    return f"RPD_SSA_Audit_Report_{audit_date or 'unknown'}.docx"


def _ensure_outlook_running() -> None:
    """Pre-flight: start Outlook (minimized) if no outlook.exe process
    exists. Non-fatal — a hard COM failure later will surface a clearer
    error than this pre-flight ever could."""
    try:
        ps = (
            "$p = Get-Process outlook -ErrorAction SilentlyContinue; "
            "if (-not $p) { "
            "  Start-Process outlook -WindowStyle Minimized; "
            "  Start-Sleep -Seconds 4 "
            "} else { Write-Host 'outlook already running' }"
        )
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-Command", ps],
            check=True, capture_output=True, text=True,
        )
    except Exception as e:
        print(f"WARNING: outlook pre-flight failed: {e}", file=sys.stderr)


def _save_msg_via_outlook(
    out_path: Path,
    subject: str,
    body: str,
    to: str = RPD_TO_RECIPIENTS,
) -> None:
    """Write a .msg file via PowerShell + Outlook COM.

    Subject and body go via UTF-8 temp files so PowerShell escaping
    issues (apostrophes, em-dashes, bullets) can't corrupt them.
    """
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        subject_file = td_path / "subject.txt"
        body_file = td_path / "body.txt"
        subject_file.write_text(subject, encoding="utf-8-sig")
        body_file.write_text(body, encoding="utf-8-sig")

        # Single-quoted PS strings: literal, no expansion. Format paths as
        # PS-friendly (backslash-escape single quotes; on Windows the paths
        # have no single quotes anyway).
        def _ps_str(s: str) -> str:
            return "'" + str(s).replace("'", "''") + "'"

        ps_script = (
            "$ErrorActionPreference = 'Stop'\n"
            f"$subj = Get-Content -Raw -Encoding UTF8 {_ps_str(subject_file)}\n"
            f"$bod  = Get-Content -Raw -Encoding UTF8 {_ps_str(body_file)}\n"
            "$ol = New-Object -ComObject Outlook.Application\n"
            "$mail = $ol.CreateItem(0)\n"  # 0 = olMailItem
            f"$mail.To = {_ps_str(to)}\n"
            "$mail.Subject = $subj.TrimEnd(\"`r\",\"`n\")\n"
            "$mail.Body = $bod\n"
            f"$mail.SaveAs({_ps_str(out_path)}, 9)\n"  # 9 = olMSGUnicode
        )

        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-Command", ps_script],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Outlook COM failed (rc={result.returncode}):\n"
                f"STDOUT: {result.stdout}\n"
                f"STDERR: {result.stderr}"
            )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("xlsx_path", type=Path)
    p.add_argument("--out", type=Path, default=None,
                   help="Output directory (defaults to xlsx_path.parent).")
    p.add_argument("--legacy-txt", action="store_true",
                   help="Also emit the plain-text .txt format for the "
                        "legacy workflow (in addition to the .msg).")
    args = p.parse_args()

    if not args.xlsx_path.exists():
        print(f"ERROR: file not found: {args.xlsx_path}", file=sys.stderr)
        return 2

    from pims.services.audit_report_from_xlsx import parse_xlsx
    from pims.scripts.generate_audit_email_draft import _slug

    obs = parse_xlsx(args.xlsx_path.read_bytes())
    if not obs:
        print("ERROR: xlsx contained no observation rows", file=sys.stderr)
        return 2

    sites = sorted({o.site_address for o in obs if o.site_address})
    site = sites[0] if sites else "site"
    audit_date = next((o.audit_date for o in obs if o.audit_date), "")
    stamp = (audit_date or "").replace("-", "")[2:]  # YYMMDD
    if not stamp:
        stamp = date.today().strftime("%y%m%d")

    out_dir = args.out or args.xlsx_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    report_name = _resolve_report_name(args.xlsx_path, audit_date)
    report_path = out_dir / report_name

    subject, body = _compose_subject_and_body(obs, report_path)

    msg_name = f"Email_Draft_{stamp}_{_slug(site)}.msg"
    msg_path = out_dir / msg_name

    _ensure_outlook_running()
    _save_msg_via_outlook(msg_path, subject, body)
    print(f"WROTE {msg_path}")

    if args.legacy_txt:
        txt_name = f"Email_Draft_{stamp}_{_slug(site)}.txt"
        txt_path = out_dir / txt_name
        txt_path.write_text(
            f"Subject: {subject}\n\n{body}\n", encoding="utf-8",
        )
        print(f"WROTE {txt_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

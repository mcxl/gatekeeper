"""Generate an .eml email draft for an audit report.

Usage:
    py -m pims.scripts.generate_audit_email_msg <xlsx_path>

Writes ``Email_Draft_<YYMMDD>_<site-slug>.eml`` next to the xlsx.
Double-clicking the .eml opens it in the operator's default mail
client. The ``X-Unsent: 1`` header (an Outlook 2016+ convention)
makes Outlook open the file as an editable draft rather than as a
received message — To/Subject/Body are populated and the user can
hit Send directly.

Why .eml instead of .msg:
.msg requires Outlook COM, which can fail with CO_E_SERVER_EXEC_FAILURE
when Outlook isn't already running. .eml is a portable RFC822 file
that Python's stdlib can author with zero external dependencies.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from email.message import EmailMessage
from email.policy import SMTP as _SMTP_POLICY
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pims.services import ssa_format_constants as _fmt  # noqa: E402

# Re-exported for backward compatibility (other modules import these names
# from this script). Source of truth is ssa_format_constants.
RPD_TO_RECIPIENTS = _fmt.EMAIL_RECIPIENTS_RPD
DEFAULT_GREETING_TARGET = _fmt.EMAIL_GREETING_TARGET

_FOLDER_RE = re.compile(_fmt.FOLDER_NAME_REGEX)


def _simplify_summary_to_ncr_only(body: str) -> str:
    """Strip the Observations / Conditional / Compliant bullets from the
    Summary of findings block; keep only the Non-conformances (NCR) line.
    Per format contract R8."""
    drop_prefixes = _fmt.EMAIL_SUMMARY_DROP_LINES_STARTING_WITH
    lines = body.split("\n")
    out: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        if any(stripped.startswith(p) for p in drop_prefixes):
            continue
        out.append(line)
    return "\n".join(out)


def _compose_subject_and_body(
    obs, report_path: Path, greeting_target: str = DEFAULT_GREETING_TARGET,
) -> tuple[str, str]:
    """Build (subject, body) from observations using the existing email
    template, then:
    - rewrite the placeholder greeting for the fixed RPD recipients
    - strip the Summary section down to the NCR line only
    """
    from pims.scripts.generate_audit_email_draft import build_email_body
    subject, body = build_email_body(obs, report_path)
    body = body.replace("Hi [Client Name],", f"Hi {greeting_target},")
    body = _simplify_summary_to_ncr_only(body)
    return subject, body


def _resolve_report_name(xlsx_path: Path, audit_date: str) -> str:
    """Best-effort guess of the sibling PDF name (matches
    generate_audit_report's new convention) so the body's 'Attachment: '
    line is correct. Per format contract R8/R9."""
    m = _FOLDER_RE.match(xlsx_path.parent.name)
    if m:
        return _fmt.REPORT_PDF_NAME_TEMPLATE.format(
            date=m.group(1), nn=m.group(3),
        )
    # Non-canonical folder fallback: use audit_date or 'unknown'
    return f"RPD_SSA_Audit_Report_{audit_date or 'unknown'}.pdf"


def _build_eml_bytes(
    subject: str,
    body: str,
    to: str = RPD_TO_RECIPIENTS,
) -> bytes:
    """Build an RFC822 .eml message ready to be written to disk.

    The ``X-Unsent: 1`` header is an Outlook 2016+ convention that tells
    Outlook to open the file as an editable draft rather than as a
    received message. Mail clients that don't understand the header
    just ignore it.
    """
    msg = EmailMessage(policy=_SMTP_POLICY)
    msg["To"] = to
    msg["Subject"] = subject
    msg["X-Unsent"] = _fmt.EMAIL_X_UNSENT_HEADER
    msg.set_content(body, subtype="plain", charset="utf-8")
    return bytes(msg)


def _save_eml(
    out_path: Path,
    subject: str,
    body: str,
    to: str = RPD_TO_RECIPIENTS,
) -> None:
    """Write an .eml file at ``out_path`` with To/Subject/Body filled."""
    out_path.write_bytes(_build_eml_bytes(subject, body, to))


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

    eml_name = _fmt.EMAIL_EML_NAME_TEMPLATE.format(
        stamp=stamp, site_slug=_slug(site),
    )
    eml_path = out_dir / eml_name

    _save_eml(eml_path, subject, body)
    print(f"WROTE {eml_path}")

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

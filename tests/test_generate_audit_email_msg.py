"""Unit tests for the pure-Python helpers in
``pims/scripts/generate_audit_email_msg.py``.

The Outlook-COM bits (``_save_msg_via_outlook``, ``_ensure_outlook_running``)
require Windows + Outlook + a configured profile; their integration is
exercised manually during the per-folder render verification step,
not in CI.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pims.scripts.generate_audit_email_msg import (
    DEFAULT_GREETING_TARGET,
    RPD_TO_RECIPIENTS,
    _compose_subject_and_body,
    _resolve_report_name,
)


class _FakeObs:
    """Minimal stand-in for ParsedObs that build_email_body() reads."""
    def __init__(
        self,
        site_address="2-6 Buckingham Road Killara",
        audit_date="2026-05-22",
        status="Compliant",
        finding="",
        observation_text="",
        recommendation="",
        action_description="",
        ccvs_category="",
    ):
        self.site_address = site_address
        self.audit_date = audit_date
        self.status = status
        self.finding = finding
        self.observation_text = observation_text
        self.recommendation = recommendation
        self.action_description = action_description
        self.ccvs_category = ccvs_category


# ---------- recipient constants ----------

def test_rpd_to_recipients_contains_both_emails():
    assert "matt@rpd.net.au" in RPD_TO_RECIPIENTS
    assert "nick@rpd.net.au" in RPD_TO_RECIPIENTS


def test_rpd_to_recipients_includes_display_names():
    assert "Matthew McCarthy" in RPD_TO_RECIPIENTS
    assert "Nick Vuckovic" in RPD_TO_RECIPIENTS


def test_default_greeting_target():
    assert DEFAULT_GREETING_TARGET == "Matt and Nick"


# ---------- _resolve_report_name ----------

def test_resolve_report_name_canonical_folder(tmp_path):
    folder = tmp_path / "2026-05-22-RPD-03"
    folder.mkdir()
    xlsx = folder / "Site_Visit_Report_2026-05-22.xlsx"
    xlsx.write_bytes(b"x")
    name = _resolve_report_name(xlsx, "2026-05-22")
    assert name == "RPD_SSA_Audit_Report_2026-05-22-03.docx"


def test_resolve_report_name_noncanonical_falls_back(tmp_path):
    folder = tmp_path / "somewhere"
    folder.mkdir()
    xlsx = folder / "x.xlsx"
    xlsx.write_bytes(b"x")
    name = _resolve_report_name(xlsx, "2026-05-22")
    assert name == "RPD_SSA_Audit_Report_2026-05-22.docx"


def test_resolve_report_name_no_audit_date(tmp_path):
    folder = tmp_path / "somewhere"
    folder.mkdir()
    xlsx = folder / "x.xlsx"
    xlsx.write_bytes(b"x")
    name = _resolve_report_name(xlsx, "")
    assert "unknown" in name


# ---------- _compose_subject_and_body ----------

def test_compose_replaces_greeting_placeholder():
    obs = [_FakeObs()]
    report = Path("RPD_SSA_Audit_Report_2026-05-22-03.docx")
    subject, body = _compose_subject_and_body(obs, report)
    assert "Hi [Client Name]," not in body
    assert "Hi Matt and Nick," in body


def test_compose_preserves_subject_format():
    obs = [_FakeObs(site_address="53 Killeaton Street St Ives",
                    audit_date="2026-05-22")]
    report = Path("dummy.docx")
    subject, _body = _compose_subject_and_body(obs, report)
    assert subject.startswith("Site Safety Audit Report")
    assert "53 Killeaton Street St Ives" in subject
    assert "2026-05-22" in subject


def test_compose_includes_attachment_line():
    obs = [_FakeObs()]
    report = Path("RPD_SSA_Audit_Report_2026-05-22-03.docx")
    _subject, body = _compose_subject_and_body(obs, report)
    assert "Attachment: RPD_SSA_Audit_Report_2026-05-22-03.docx" in body


def test_compose_includes_signature_block():
    obs = [_FakeObs()]
    report = Path("x.docx")
    _subject, body = _compose_subject_and_body(obs, report)
    assert "Kind regards," in body
    assert "Alan Richardson" in body
    assert "AuditCo" in body


def test_compose_custom_greeting_target():
    obs = [_FakeObs()]
    report = Path("x.docx")
    _s, body = _compose_subject_and_body(
        obs, report, greeting_target="RPD team",
    )
    assert "Hi RPD team," in body
    assert "Hi Matt and Nick," not in body


# ---------- import safety ----------

def test_module_imports_on_non_windows_without_pywin32():
    """The Outlook-COM code path is only invoked at runtime (in main());
    plain imports must succeed on any platform."""
    import pims.scripts.generate_audit_email_msg as m
    assert m is not None


def test_save_msg_signature():
    """The save function exists and is callable (signature only)."""
    from pims.scripts.generate_audit_email_msg import _save_msg_via_outlook
    assert callable(_save_msg_via_outlook)

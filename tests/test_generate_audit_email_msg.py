"""Unit tests for the .eml writer in
``pims/scripts/generate_audit_email_msg.py``.
"""
from __future__ import annotations

import email
from pathlib import Path

import pytest

from pims.scripts.generate_audit_email_msg import (
    DEFAULT_GREETING_TARGET,
    RPD_TO_RECIPIENTS,
    _build_eml_bytes,
    _compose_subject_and_body,
    _resolve_report_name,
    _save_eml,
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


# ---------- .eml writer ----------

def test_build_eml_bytes_has_required_headers():
    raw = _build_eml_bytes("My Subject", "My Body").decode("utf-8")
    assert "To: " in raw
    assert "Subject: My Subject" in raw
    assert "X-Unsent: 1" in raw
    assert "My Body" in raw


def test_build_eml_bytes_to_field_contains_both_recipients():
    raw = _build_eml_bytes("S", "B").decode("utf-8")
    # Parse the message and read the To header
    msg = email.message_from_string(raw)
    to = msg["To"]
    assert "matt@rpd.net.au" in to
    assert "nick@rpd.net.au" in to
    assert "Matthew McCarthy" in to
    assert "Nick Vuckovic" in to


def test_build_eml_bytes_preserves_unicode_in_body():
    """Em-dash, bullet point, apostrophe must survive RFC822 encoding."""
    import email.policy
    body = "Hi —\n• one\n• two\n• it's working"
    raw = _build_eml_bytes("Test", body)
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    decoded_body = msg.get_content()
    assert "—" in decoded_body
    assert "•" in decoded_body
    assert "it's working" in decoded_body


def test_build_eml_bytes_x_unsent_for_outlook_editable_open():
    """Outlook treats X-Unsent: 1 as a hint to open as a draft, not a
    received message — without this, Send would be disabled in the
    opened window."""
    raw = _build_eml_bytes("S", "B").decode("utf-8")
    msg = email.message_from_string(raw)
    assert msg.get("X-Unsent") == "1"


def test_save_eml_writes_file(tmp_path):
    out = tmp_path / "Email_Draft_260522_test.eml"
    _save_eml(out, "Sub", "Body")
    assert out.exists()
    raw = out.read_bytes()
    assert b"X-Unsent: 1" in raw
    assert b"Sub" in raw


def test_save_eml_overwrites_existing(tmp_path):
    out = tmp_path / "x.eml"
    out.write_bytes(b"old content")
    _save_eml(out, "New Subject", "New Body")
    raw = out.read_bytes()
    assert b"old content" not in raw
    assert b"New Subject" in raw


def test_module_imports_cleanly():
    """Imports must succeed on any platform — no Outlook/COM dependency."""
    import pims.scripts.generate_audit_email_msg as m
    assert m is not None
    assert callable(m._save_eml)
    assert callable(m._build_eml_bytes)

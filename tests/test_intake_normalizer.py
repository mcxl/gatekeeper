"""
tests/test_intake_normalizer.py — Tests for the intake normalizer v1.
"""

import json
import os
import sys
from io import BytesIO
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.intake_extractor import (
    MAX_FILE_SIZE_BYTES,
    MAX_TEXT_CHARS,
    MIN_USEFUL_TEXT_CHARS,
    ExtractionResult,
    extract_from_docx,
    extract_from_pdf,
    extract_from_text,
)
from core.intake_normalizer import normalize_intake

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ── Extraction: pasted text ─────────────────────────────────────────────────

class TestPastedText:
    def test_clean_scope_text(self):
        text = (
            "Project: Remedial facade painting at 22 Pacific Highway, North Sydney NSW.\n"
            "Client: RPD Group\n"
            "Scope: Concrete crack repair, spalling patch to balcony soffits, "
            "full preparation and two-coat acrylic paint system to rendered facades."
        )
        r = extract_from_text(text)
        assert r.text_extraction_succeeded
        assert r.source_type == "pasted_text"
        assert "RPD Group" in r.raw_text
        assert len(r.source_fingerprint) == 64

    def test_email_body_text(self):
        text = (
            "From: john@example.com\n"
            "Subject: Re: SWMS for Withers Road upgrade\n\n"
            "Hi team, please prepare a SWMS for the road widening works at "
            "Withers Road North Kellyville for The Hills Shire Council. "
            "Works include pavement demolition, earthworks, drainage, and asphalt."
        )
        r = extract_from_text(text, source_type="email_text")
        assert r.text_extraction_succeeded
        assert r.source_type == "email_text"

    def test_too_short_text(self):
        r = extract_from_text("Short text")
        assert not r.text_extraction_succeeded
        assert any("extraction_insufficient" in w for w in r.warnings)

    def test_empty_text(self):
        r = extract_from_text("")
        assert not r.text_extraction_succeeded

    def test_truncation_warning(self):
        long_text = "x" * (MAX_TEXT_CHARS + 1000)
        r = extract_from_text(long_text)
        assert r.text_extraction_succeeded
        assert len(r.raw_text) == MAX_TEXT_CHARS
        assert any("text_truncated" in w for w in r.warnings)

    def test_fingerprint_stability(self):
        text = "Stable content for fingerprint test with enough characters to pass minimum."
        r1 = extract_from_text(text)
        r2 = extract_from_text(text)
        assert r1.source_fingerprint == r2.source_fingerprint


# ── Extraction: DOCX ────────────────────────────────────────────────────────

class TestDocxExtraction:
    def test_clean_docx(self):
        path = FIXTURES_DIR / "test_swms_minimal.docx"
        if not path.exists():
            pytest.skip("DOCX fixture not available")
        with open(path, "rb") as f:
            r = extract_from_docx(f.read(), source_label="test.docx")
        assert r.text_extraction_succeeded
        assert r.source_type == "docx_text"
        assert len(r.raw_text) > 0

    def test_invalid_docx(self):
        r = extract_from_docx(b"not a real docx file")
        assert not r.text_extraction_succeeded
        assert any("extraction_failed" in w for w in r.warnings)

    def test_oversized_file(self):
        big = b"x" * (MAX_FILE_SIZE_BYTES + 1)
        r = extract_from_docx(big)
        assert not r.text_extraction_succeeded
        assert any("file_too_large" in w for w in r.warnings)


# ── Extraction: PDF ─────────────────────────────────────────────────────────

class TestPdfExtraction:
    def _make_simple_pdf(self) -> bytes:
        """Create a minimal PDF with text for testing."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            buf = BytesIO()
            c = canvas.Canvas(buf, pagesize=A4)
            c.drawString(72, 700, "Project: Test scaffold erection at 100 George Street Sydney NSW 2000")
            c.drawString(72, 680, "Client: Test Construction Pty Ltd")
            c.drawString(72, 660, "Scope of works: Erect scaffold to building facade for remedial painting works.")
            c.save()
            return buf.getvalue()
        except ImportError:
            return b""

    def test_machine_readable_pdf(self):
        pdf_bytes = self._make_simple_pdf()
        if not pdf_bytes:
            pytest.skip("reportlab not available for PDF fixture creation")
        r = extract_from_pdf(pdf_bytes, source_label="test.pdf")
        assert r.text_extraction_succeeded
        assert r.source_type == "pdf_text"

    def test_invalid_pdf(self):
        r = extract_from_pdf(b"not a pdf")
        assert not r.text_extraction_succeeded
        assert any("extraction_failed" in w or "extraction_insufficient" in w
                    for w in r.warnings)

    def test_oversized_pdf(self):
        big = b"x" * (MAX_FILE_SIZE_BYTES + 1)
        r = extract_from_pdf(big)
        assert not r.text_extraction_succeeded
        assert any("file_too_large" in w for w in r.warnings)


# ── Normalization ───────────────────────────────────────────────────────────

class TestNormalization:
    def test_clean_text_produces_draft(self):
        text = (
            "Project: Remedial facade painting at 22 Pacific Highway, North Sydney NSW 2060\n"
            "Client: RPD Group\n"
            "Scope: Concrete crack repair and spalling patch to balcony soffits. "
            "Full preparation and two-coat acrylic paint system to rendered facades. "
            "Scaffold access. Occupied building with residents remaining in tenancy."
        )
        extraction = extract_from_text(text)
        result = normalize_intake(extraction)

        assert result["intake_version"] == "1.0"
        assert result["requires_consultant_review"] is True
        draft = result["job_brief_draft"]
        assert draft["job_type"]["value"] == "remedial"
        assert "occupied_building" in draft["scope_modifiers"]["value"]
        assert draft["scope_of_works"]["status"] == "extracted"

    def test_ambiguous_source_leaves_fields_unresolved(self):
        text = "Please prepare documentation for the upcoming project works."
        extraction = extract_from_text(text)
        result = normalize_intake(extraction)

        draft = result["job_brief_draft"]
        assert draft["customer"]["status"] == "unresolved"
        assert draft["job_type"]["status"] == "unresolved"
        assert len(result["unresolved_fields"]) > 0
        assert len(result["review_prompts"]) > 0

    def test_job_type_inferred_correctly(self):
        text = (
            "Scope of works: demolition of existing partitions, strip-out of ceiling grid, "
            "removal of floor coverings. Asbestos survey completed."
        )
        extraction = extract_from_text(text)
        result = normalize_intake(extraction)
        assert result["job_brief_draft"]["job_type"]["value"] == "demolition"
        assert result["job_brief_draft"]["job_type"]["status"] == "inferred"

    def test_civil_job_type_inferred(self):
        text = (
            "Road widening, kerb and gutter, drainage, earthworks, pavement "
            "reconstruction, traffic management required throughout."
        )
        extraction = extract_from_text(text)
        result = normalize_intake(extraction)
        assert result["job_brief_draft"]["job_type"]["value"] == "civil"

    def test_address_extracted(self):
        text = (
            "Site: 45 Clarence Street Sydney NSW 2000\n"
            "Works: Internal fit-out of office level 3."
        )
        extraction = extract_from_text(text)
        result = normalize_intake(extraction)
        assert result["job_brief_draft"]["address"]["value"] != ""
        assert "Clarence" in result["job_brief_draft"]["address"]["value"]

    def test_customer_extracted(self):
        text = (
            "Client: Apex Commercial Constructions\n"
            "Project: Podium slab formwork installation."
        )
        extraction = extract_from_text(text)
        result = normalize_intake(extraction)
        assert "Apex" in result["job_brief_draft"]["customer"]["value"]
        assert result["job_brief_draft"]["customer"]["status"] == "extracted"

    def test_review_prompts_present(self):
        text = "Install new roofing at warehouse site."
        extraction = extract_from_text(text)
        result = normalize_intake(extraction)
        assert len(result["review_prompts"]) > 0
        assert result["requires_consultant_review"] is True

    def test_extraction_warnings_passed_through(self):
        r = ExtractionResult(
            raw_text="Short",
            source_type="pasted_text",
            warnings=["extraction_insufficient: too short"],
        )
        result = normalize_intake(r)
        assert "extraction_insufficient: too short" in result["extraction_warnings"]

    def test_quick_scan_focus_inferred_for_known_type(self):
        text = (
            "Scope: remedial waterproofing and concrete repair to occupied "
            "residential building with scaffold access."
        )
        extraction = extract_from_text(text)
        result = normalize_intake(extraction)
        qsf = result["job_brief_draft"]["quick_scan_focus"]
        assert qsf["status"] == "inferred"
        assert len(qsf["value"]) > 0

    def test_clarification_note_appended(self):
        text = "Install roofing at warehouse."
        extraction = extract_from_text(text)
        result = normalize_intake(extraction, clarification_note="Job type is new build")
        assert "new build" in result["job_brief_draft"]["scope_of_works"]["value"].lower()

    def test_mandatory_review_always_true(self):
        text = (
            "Project: Perfect SWMS with all details clearly stated.\n"
            "Client: Known Company\n"
            "Address: 1 Perfect Street, Sydney NSW 2000\n"
            "Scope: New build warehouse erection with crane."
        )
        extraction = extract_from_text(text)
        result = normalize_intake(extraction)
        assert result["requires_consultant_review"] is True


# ── API endpoint ────────────────────────────────────────────────────────────

class TestIntakeEndpoint:
    def test_text_intake(self):
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)

        response = client.post(
            "/v1/swms/intake",
            data={
                "source_text": (
                    "Client: Test Corp\n"
                    "Project: Remedial painting at 10 George St Sydney NSW 2000\n"
                    "Scope: Concrete repair and two-coat paint system to facade."
                ),
                "source_type": "pasted_text",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["intake_version"] == "1.0"
        assert body["requires_consultant_review"] is True
        assert body["job_brief_draft"]["scope_of_works"]["status"] == "extracted"

    def test_empty_input_returns_400(self):
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)

        response = client.post("/v1/swms/intake", data={})
        assert response.status_code == 400

    def test_docx_file_intake(self):
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)

        path = FIXTURES_DIR / "test_swms_minimal.docx"
        if not path.exists():
            pytest.skip("DOCX fixture not available")

        with open(path, "rb") as f:
            response = client.post(
                "/v1/swms/intake",
                files={"source_file": ("test.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            )
        assert response.status_code == 200
        body = response.json()
        assert body["source_metadata"]["source_type"] == "docx_text"

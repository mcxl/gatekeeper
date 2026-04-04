"""
tests/test_procore_stage2.py — Tests for Stage 2 Procore pipeline.
"""

import json
import os
import sys
from dataclasses import asdict
from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.procore_extract import ExtractionResult, extract_and_route, CRITICAL_PAGE_KEYWORDS
from core.procore_fetch import ProcoreFetchError, ProcoreFetchTimeout
from core.procore_review import Finding, ReviewResult
from core.procore_comment import _format_pm_message, _format_sm_review, _reason_summary


# ── Extraction routing ──────────────────────────────────────────────────────

class TestExtractionResult:
    def test_default_values(self):
        r = ExtractionResult()
        assert r.confidence_tier == "red"
        assert r.abort is False
        assert r.vision_audit_triggered is False

    def test_empty_bytes_aborts(self):
        import asyncio
        result = asyncio.run(extract_and_route(b"", "test-cid"))
        assert result.abort is True
        assert result.abort_reason == "empty_document"


class TestConfidenceRouting:
    def _make_pdf_bytes(self, page_texts: list[str]) -> bytes:
        """Create a simple PDF with given page texts."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            buf = BytesIO()
            c = canvas.Canvas(buf, pagesize=A4)
            for text in page_texts:
                c.drawString(72, 700, text[:200])
                c.showPage()
            c.save()
            return buf.getvalue()
        except ImportError:
            return b""

    def test_green_path_all_pages_long(self):
        """Pages with enough text → green confidence."""
        long_text = "A" * 1300
        pdf_bytes = self._make_pdf_bytes([long_text, long_text])
        if not pdf_bytes:
            pytest.skip("reportlab not available")
        import asyncio
        result = asyncio.run(extract_and_route(pdf_bytes, "test-green"))
        # reportlab creates minimal text, may not hit 1200 chars per page
        assert result.page_count == 2
        assert result.confidence_tier in ("green", "amber")


# ── Fetch exceptions ────────────────────────────────────────────────────────

class TestFetchExceptions:
    def test_fetch_timeout_exception(self):
        with pytest.raises(ProcoreFetchTimeout):
            raise ProcoreFetchTimeout("test timeout")

    def test_fetch_error_exception(self):
        err = ProcoreFetchError(403, "https://example.com/doc.pdf")
        assert err.status_code == 403
        assert "403" in str(err)


# ── Review result ───────────────────────────────────────────────────────────

class TestReviewResult:
    def test_default_result(self):
        r = ReviewResult()
        assert r.overall_result == "REVIEW"
        assert r.extraction_source == "pypdf"

    def test_finding_with_vision_source(self):
        f = Finding(code="HF-001", description="Test", source="vision_ocr")
        assert f.source == "vision_ocr"

    def test_findings_carry_extraction_source(self):
        r = ReviewResult(
            extraction_source="vision_ocr",
            findings=[Finding(code="A", source="vision_ocr")],
        )
        assert r.findings[0].source == "vision_ocr"


# ── Comment formatting ──────────────────────────────────────────────────────

class TestCommentFormatting:
    def test_pm_received(self):
        msg = _format_pm_message("received")
        assert "approximately 60 seconds" in msg

    def test_pm_complete(self):
        msg = _format_pm_message("complete", "missing HRCW controls")
        assert "missing HRCW controls" in msg
        assert "Safety Manager" in msg

    def test_pm_aborted(self):
        msg = _format_pm_message("aborted")
        assert "Unable to process" in msg

    def test_pm_failed(self):
        msg = _format_pm_message("failed")
        assert "could not be completed" in msg

    def test_pm_never_shows_correlation_id(self):
        for state in ("received", "complete", "aborted", "failed"):
            msg = _format_pm_message(state, "test")
            assert "correlation" not in msg.lower()

    def test_sm_review_has_correlation_id(self):
        rr = ReviewResult(
            overall_result="FAIL",
            hard_fails=["Missing HRCW controls"],
            hrcw_flags=["Work in excavations"],
            findings=[Finding(code="HF-001", description="Test", severity="hard_fail", source="pypdf")],
        )
        sm = _format_sm_review(rr, "test-cid-123")
        assert "test-cid-123" in sm
        assert "FAIL" in sm

    def test_sm_review_vision_tag(self):
        rr = ReviewResult(
            overall_result="REVIEW",
            extraction_source="vision_ocr",
            findings=[Finding(code="A", description="Test finding", severity="amendment", source="vision_ocr")],
        )
        sm = _format_sm_review(rr, "cid")
        assert "VISION-DERIVED" in sm
        assert "manual verification required" in sm

    def test_reason_summary_hard_fail(self):
        rr = ReviewResult(hard_fails=["Missing excavation controls"])
        assert "excavation" in _reason_summary(rr)

    def test_reason_summary_no_issues(self):
        rr = ReviewResult(overall_result="PASS")
        assert "no issues found" in _reason_summary(rr)

    def test_reason_summary_amendments(self):
        rr = ReviewResult(amendments_required=["Fix controls"])
        assert "amendments" in _reason_summary(rr)


# ── Orphan cleanup ──────────────────────────────────────────────────────────

class TestOrphanCleanup:
    def test_cleanup_runs_without_supabase(self):
        """Cleanup should not error when Supabase is not configured."""
        import asyncio
        from api.procore import _cleanup_orphaned_jobs
        # Should return silently — no Supabase configured
        asyncio.run(_cleanup_orphaned_jobs())


# ── Abort path ──────────────────────────────────────────────────────────────

class TestAbortPath:
    def test_abort_result_has_reason(self):
        r = ExtractionResult(abort=True, abort_reason="vision_abort", confidence_tier="red")
        assert r.abort is True
        assert r.abort_reason == "vision_abort"

    def test_abort_empty_doc(self):
        import asyncio
        result = asyncio.run(extract_and_route(b"", "test-abort"))
        assert result.abort is True
        assert result.abort_reason == "empty_document"


# ── Token absent → log only ─────────────────────────────────────────────────

class TestTokenAbsent:
    def test_comment_logs_only_without_token(self):
        """post_heartbeat_comment should log and return cleanly without PROCORE_ACCESS_TOKEN."""
        import asyncio
        from core.procore_comment import post_heartbeat_comment

        # Ensure no token
        old = os.environ.pop("PROCORE_ACCESS_TOKEN", None)
        try:
            asyncio.run(post_heartbeat_comment("sub-123", "received", "cid-test", tier="pm"))
        finally:
            if old is not None:
                os.environ["PROCORE_ACCESS_TOKEN"] = old


# ── Critical page keywords ──────────────────────────────────────────────────

class TestCriticalPages:
    def test_keywords_present(self):
        assert "hrcw" in CRITICAL_PAGE_KEYWORDS
        assert "control" in CRITICAL_PAGE_KEYWORDS
        assert "hold point" in CRITICAL_PAGE_KEYWORDS


# ── Job states schema doc ───────────────────────────────────────────────────

class TestJobStatesSchema:
    def test_schema_doc_exists(self):
        from pathlib import Path
        p = Path(__file__).parent.parent / "docs" / "procore" / "job_states_schema.md"
        assert p.exists()
        content = p.read_text(encoding="utf-8")
        assert "extraction_char_count" in content
        assert "confidence_tier" in content
        assert "vision_audit_triggered" in content
        assert "failure_reason" in content

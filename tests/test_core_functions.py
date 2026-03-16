"""Tests for core functions: resolve_field, _summarise_work_activity,
truncate_for_prompt, extract_text dispatch, and get_current_user."""

import os
import sys
from datetime import date
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from renderers.docx_renderer import resolve_field, _summarise_work_activity
from core.document_extractor import extract_text, truncate_for_prompt
from core.auth import get_current_user


# ── TEST 1: resolve_field() ──────────────────────────────────────────────────


class TestResolveField:
    def test_empty_string_returns_placeholder(self):
        text, is_placeholder = resolve_field("", "pcbu_name")
        assert is_placeholder is True
        assert text == "[Insert PCBU here]"

    def test_none_returns_placeholder(self):
        text, is_placeholder = resolve_field(None, "pcbu_name")
        assert is_placeholder is True
        assert text == "[Insert PCBU here]"

    def test_valid_string_returns_value(self):
        text, is_placeholder = resolve_field("Robertson's Remedial", "pcbu_name")
        assert is_placeholder is False
        assert text == "Robertson's Remedial"

    def test_swms_date_empty_returns_today(self):
        text, is_placeholder = resolve_field("", "swms_date")
        assert is_placeholder is False
        assert text == date.today().strftime("%d/%m/%Y")

    def test_swms_date_none_returns_today(self):
        text, is_placeholder = resolve_field(None, "swms_date")
        assert is_placeholder is False
        assert text == date.today().strftime("%d/%m/%Y")

    def test_unknown_field_returns_generic_placeholder(self):
        text, is_placeholder = resolve_field("", "unknown_field")
        assert is_placeholder is True
        assert text == "[Insert here]"

    def test_whitespace_only_returns_placeholder(self):
        text, is_placeholder = resolve_field("   ", "pcbu_name")
        assert is_placeholder is True


# ── TEST 2: _summarise_work_activity() ───────────────────────────────────────


class TestSummariseWorkActivity:
    SHORT_TEXT = "Concrete grinding and surface preparation."

    LONG_TEXT = "\n".join(
        [f"Line {i}: This is a complete sentence about construction work." for i in range(1, 15)]
    )

    LONG_CHARS = "A" * 900 + ". Final sentence."

    def _mock_anthropic(self, return_text):
        """Create a mock anthropic module with messages.create returning return_text."""
        mock_module = MagicMock()
        mock_client = MagicMock()
        mock_module.Anthropic.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text=return_text)]
        mock_client.messages.create.return_value = mock_resp
        return mock_module

    def test_short_text_returned_unchanged(self):
        mock_mod = self._mock_anthropic(self.SHORT_TEXT)
        with patch.dict("sys.modules", {"anthropic": mock_mod}):
            result = _summarise_work_activity(self.SHORT_TEXT)
        assert result == self.SHORT_TEXT

    def test_long_text_truncated_to_8_lines(self):
        mock_mod = self._mock_anthropic(self.LONG_TEXT)
        with patch.dict("sys.modules", {"anthropic": mock_mod}):
            result = _summarise_work_activity(self.LONG_TEXT)
        assert len(result.split("\n")) <= 8

    def test_hard_cap_at_800_chars(self):
        mock_mod = self._mock_anthropic(self.LONG_CHARS)
        with patch.dict("sys.modules", {"anthropic": mock_mod}):
            result = _summarise_work_activity(self.LONG_CHARS)
        assert len(result) <= 800

    def test_truncation_ends_on_full_stop(self):
        over_limit = "Word " * 200 + "End sentence here."
        mock_mod = self._mock_anthropic(over_limit)
        with patch.dict("sys.modules", {"anthropic": mock_mod}):
            result = _summarise_work_activity(over_limit)
        assert len(result) <= 800
        assert result[-1] == "." or not result.endswith(" ")

    def test_api_failure_returns_original(self):
        mock_mod = MagicMock()
        mock_mod.Anthropic.side_effect = Exception("API down")
        with patch.dict("sys.modules", {"anthropic": mock_mod}):
            result = _summarise_work_activity(self.SHORT_TEXT)
        assert result == self.SHORT_TEXT


# ── TEST 3: truncate_for_prompt() ────────────────────────────────────────────


class TestTruncateForPrompt:
    def test_short_text_unchanged(self):
        text = "Short document content."
        assert truncate_for_prompt(text) == text

    def test_text_at_limit_unchanged(self):
        text = "x" * 8000
        assert truncate_for_prompt(text) == text

    def test_long_text_truncated(self):
        text = "A" * 20000
        result = truncate_for_prompt(text)
        assert len(result) < len(text)

    def test_truncated_contains_marker(self):
        text = "B" * 20000
        result = truncate_for_prompt(text)
        assert "[... document truncated" in result

    def test_custom_max_chars(self):
        text = "C" * 5000
        result = truncate_for_prompt(text, max_chars=2000)
        assert "[... document truncated" in result
        assert len(result) < len(text)

    def test_preserves_start_and_end(self):
        text = "START" + "x" * 20000 + "END"
        result = truncate_for_prompt(text)
        assert result.startswith("START")
        assert result.endswith("END")


# ── TEST 4: extract_text() dispatch ──────────────────────────────────────────


class TestExtractText:
    def test_txt_returns_decoded_text(self):
        content = "Hello, this is plain text."
        result = extract_text(content.encode("utf-8"), "document.txt")
        assert result == content

    def test_txt_handles_unicode(self):
        content = "Café résumé naïve"
        result = extract_text(content.encode("utf-8"), "notes.txt")
        assert result == content

    @patch("core.document_extractor.extract_text_from_pdf")
    def test_pdf_dispatches_correctly(self, mock_pdf):
        mock_pdf.return_value = "PDF content"
        result = extract_text(b"fake-pdf-bytes", "report.pdf")
        mock_pdf.assert_called_once_with(b"fake-pdf-bytes")
        assert result == "PDF content"

    @patch("core.document_extractor.extract_text_from_docx")
    def test_docx_dispatches_correctly(self, mock_docx):
        mock_docx.return_value = "DOCX content"
        result = extract_text(b"fake-docx-bytes", "report.docx")
        mock_docx.assert_called_once_with(b"fake-docx-bytes")
        assert result == "DOCX content"

    def test_unsupported_extension_raises(self):
        with pytest.raises(ValueError, match="Unsupported file type"):
            extract_text(b"data", "file.xyz")

    def test_unsupported_extension_message(self):
        with pytest.raises(ValueError, match=r"\.xyz"):
            extract_text(b"data", "file.xyz")


# ── TEST 5: get_current_user() ───────────────────────────────────────────────


class TestGetCurrentUser:
    @pytest.mark.anyio
    async def test_invalid_jwt_raises_401(self):
        """Garbage token raises 401."""
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid.token.here")
        with patch("core.auth.get_jwks", new_callable=AsyncMock) as mock_jwks:
            mock_jwks.return_value = {"keys": []}
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(creds)
            assert exc_info.value.status_code == 401

    @pytest.mark.anyio
    async def test_missing_sub_claim_raises_401(self):
        """Token that decodes but has no 'sub' claim raises 401."""
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake.token")
        with patch("core.auth.get_jwks", new_callable=AsyncMock) as mock_jwks:
            mock_jwks.return_value = {"keys": []}
            with patch("core.auth.jwt.decode") as mock_decode:
                mock_decode.return_value = {"email": "test@test.com"}
                with pytest.raises(HTTPException) as exc_info:
                    await get_current_user(creds)
                assert exc_info.value.status_code == 401
                assert "no sub claim" in exc_info.value.detail

    @pytest.mark.anyio
    async def test_expired_jwt_raises_401(self):
        """Expired token raises 401."""
        from jose import JWTError
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="expired.token")
        with patch("core.auth.get_jwks", new_callable=AsyncMock) as mock_jwks:
            mock_jwks.return_value = {"keys": []}
            with patch("core.auth.jwt.decode") as mock_decode:
                mock_decode.side_effect = JWTError("Signature has expired")
                with pytest.raises(HTTPException) as exc_info:
                    await get_current_user(creds)
                assert exc_info.value.status_code == 401

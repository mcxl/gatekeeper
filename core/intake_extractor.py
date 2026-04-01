"""
core/intake_extractor.py — Extract raw text from a single intake source.

Supports: pasted text, email text, DOCX, machine-readable PDF.
Does not infer job_type, scope_modifiers, HRCW, CCVS, or risk details.
Produces raw text + source metadata only.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO

# ── Limits ──────────────────────────────────────────────────────────────────

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_PDF_PAGES = 10
MIN_USEFUL_TEXT_CHARS = 50
MAX_TEXT_CHARS = 50_000  # truncate and warn above this


@dataclass
class ExtractionResult:
    raw_text: str = ""
    source_type: str = ""  # pasted_text | email_text | pdf_text | docx_text
    source_label: str = ""
    source_fingerprint: str = ""
    parser_mode: str = ""  # text | pdf_text | docx_text
    text_extraction_succeeded: bool = False
    ingested_at: str = ""
    warnings: list[str] = field(default_factory=list)


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_from_text(
    text: str,
    source_type: str = "pasted_text",
    source_label: str = "",
) -> ExtractionResult:
    """Extract from raw pasted text or email body."""
    result = ExtractionResult(
        source_type=source_type,
        source_label=source_label,
        parser_mode="text",
        ingested_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )

    text = text.strip()
    if len(text) < MIN_USEFUL_TEXT_CHARS:
        result.warnings.append(
            f"extraction_insufficient: text is only {len(text)} chars "
            f"(minimum {MIN_USEFUL_TEXT_CHARS})"
        )
        result.raw_text = text
        result.source_fingerprint = _fingerprint(text)
        return result

    if len(text) > MAX_TEXT_CHARS:
        result.warnings.append(
            f"text_truncated: {len(text)} chars exceeds {MAX_TEXT_CHARS} limit, truncated"
        )
        text = text[:MAX_TEXT_CHARS]

    result.raw_text = text
    result.source_fingerprint = _fingerprint(text)
    result.text_extraction_succeeded = True
    return result


def extract_from_docx(
    file_bytes: bytes,
    source_label: str = "",
) -> ExtractionResult:
    """Extract text from a DOCX file."""
    result = ExtractionResult(
        source_type="docx_text",
        source_label=source_label,
        parser_mode="docx_text",
        ingested_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        result.warnings.append(
            f"file_too_large: {len(file_bytes)} bytes exceeds {MAX_FILE_SIZE_BYTES} limit"
        )
        return result

    try:
        from core.document_extractor import extract_text_from_docx
        text = extract_text_from_docx(file_bytes)
    except (ValueError, Exception) as e:
        result.warnings.append(f"docx_extraction_failed: {e}")
        return result

    return _finalize_text(result, text)


def extract_from_pdf(
    file_bytes: bytes,
    source_label: str = "",
) -> ExtractionResult:
    """Extract text from a machine-readable PDF (first 10 pages max).

    Does not attempt OCR for scanned/image PDFs — returns extraction_insufficient.
    """
    result = ExtractionResult(
        source_type="pdf_text",
        source_label=source_label,
        parser_mode="pdf_text",
        ingested_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        result.warnings.append(
            f"file_too_large: {len(file_bytes)} bytes exceeds {MAX_FILE_SIZE_BYTES} limit"
        )
        return result

    try:
        import pdfplumber
        pdf = pdfplumber.open(BytesIO(file_bytes))
        pages = pdf.pages[:MAX_PDF_PAGES]
        if len(pdf.pages) > MAX_PDF_PAGES:
            result.warnings.append(
                f"pdf_truncated: {len(pdf.pages)} pages, only first {MAX_PDF_PAGES} extracted"
            )
        parts = []
        for page in pages:
            text = page.extract_text()
            if text:
                parts.append(text.strip())
        pdf.close()
        text = "\n".join(parts).strip()
    except Exception as e:
        result.warnings.append(f"pdf_extraction_failed: {e}")
        return result

    return _finalize_text(result, text)


def _finalize_text(result: ExtractionResult, text: str) -> ExtractionResult:
    """Apply text limits and finalize the result."""
    if len(text) < MIN_USEFUL_TEXT_CHARS:
        result.warnings.append(
            f"extraction_insufficient: extracted only {len(text)} chars "
            f"(minimum {MIN_USEFUL_TEXT_CHARS}). "
            "Paste the relevant scope section manually."
        )
        result.raw_text = text
        result.source_fingerprint = _fingerprint(text) if text else ""
        return result

    if len(text) > MAX_TEXT_CHARS:
        result.warnings.append(
            f"text_truncated: {len(text)} chars exceeds {MAX_TEXT_CHARS} limit, truncated"
        )
        text = text[:MAX_TEXT_CHARS]

    result.raw_text = text
    result.source_fingerprint = _fingerprint(text)
    result.text_extraction_succeeded = True
    return result

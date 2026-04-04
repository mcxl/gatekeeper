"""
core/procore_extract.py — PDF extraction and confidence routing for Procore review.

Green path: all pages >= 1200 chars, no critical flags → direct to Sonnet.
Amber path: any page < 1200 OR critical flag → Haiku vision audit first 2 pages.
Red path: vision says illegible → abort, manual review required.
"""

from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass, field
from io import BytesIO

log = logging.getLogger(__name__)

CRITICAL_PAGE_KEYWORDS = [
    "hrcw", "hazard", "control", "step",
    "activity", "review", "sign-off",
    "hold point", "stop work", "ppe",
    "permit", "licence",
]

GREEN_CHARS_PER_PAGE = 1200
AMBER_VISION_PAGES = 2
VISION_DPI = 150
VISION_MAX_TOKENS = 2000


@dataclass
class ExtractionResult:
    text: str = ""
    page_count: int = 0
    char_count: int = 0
    chars_per_page: float = 0.0
    confidence_tier: str = "red"
    vision_audit_triggered: bool = False
    vision_audit_result: str | None = None
    abort: bool = False
    abort_reason: str | None = None
    critical_pages_flagged: list[int] = field(default_factory=list)


async def extract_and_route(
    pdf_bytes: bytes,
    correlation_id: str,
) -> ExtractionResult:
    """Extract text from PDF and route by confidence tier."""
    result = ExtractionResult()

    if not pdf_bytes:
        result.abort = True
        result.abort_reason = "empty_document"
        return result

    # Step 1: pypdf extraction per page
    try:
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(pdf_bytes))
        page_texts: list[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            page_texts.append(text)
    except Exception as e:
        log.error("PDF extraction failed: %s correlation_id=%s", e, correlation_id)
        result.abort = True
        result.abort_reason = "extraction_error"
        return result

    result.page_count = len(page_texts)
    full_text = "\n".join(page_texts)
    result.text = full_text
    result.char_count = len(full_text)
    result.chars_per_page = result.char_count / max(result.page_count, 1)

    # Step 2: Critical-page scan
    critical_flagged: list[int] = []
    for i, pt in enumerate(page_texts):
        pt_lower = pt.lower()
        page_chars = len(pt)
        for kw in CRITICAL_PAGE_KEYWORDS:
            if kw in pt_lower and page_chars < 300:
                critical_flagged.append(i + 1)
                log.info(
                    "Critical page %d flagged — '%s' found, %d chars. correlation_id=%s",
                    i + 1, kw, page_chars, correlation_id,
                )
                break
    result.critical_pages_flagged = critical_flagged

    # Step 3: Confidence routing
    all_pages_green = all(len(pt) >= GREEN_CHARS_PER_PAGE for pt in page_texts)
    if all_pages_green and not critical_flagged:
        result.confidence_tier = "green"
        return result

    # Amber path: vision audit needed
    result.confidence_tier = "amber"
    result.vision_audit_triggered = True

    # Step 4: Haiku vision audit (amber only)
    try:
        vision_result = await _run_vision_audit(pdf_bytes, correlation_id)
        result.vision_audit_result = vision_result
        if vision_result == "illegible":
            result.confidence_tier = "red"
            result.abort = True
            result.abort_reason = "vision_abort"
    except Exception as e:
        log.warning("Vision audit failed: %s correlation_id=%s", e, correlation_id)
        # Vision failure → stay amber, continue with pypdf text
        result.vision_audit_result = None

    return result


async def _run_vision_audit(pdf_bytes: bytes, correlation_id: str) -> str:
    """Run Haiku vision audit on first 2 pages. Returns 'legible' or 'illegible'."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        log.warning("PyMuPDF not available for vision audit. correlation_id=%s", correlation_id)
        return "legible"  # cannot audit → assume legible

    import anthropic

    pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_count = min(len(pdf_doc), AMBER_VISION_PAGES)
    if page_count == 0:
        pdf_doc.close()
        return "legible"

    images = []
    for i in range(page_count):
        pix = pdf_doc[i].get_pixmap(dpi=VISION_DPI)
        img_bytes = pix.tobytes("png")
        images.append(base64.standard_b64encode(img_bytes).decode("utf-8"))
    pdf_doc.close()

    client = anthropic.Anthropic()
    content: list[dict] = []
    for img_b64 in images:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": img_b64},
        })
    content.append({
        "type": "text",
        "text": (
            "Are all safety controls and HRCW classifications in this document legible? "
            "Answer YES or NO only, then list any unreadable sections."
        ),
    })

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=VISION_MAX_TOKENS,
        messages=[{"role": "user", "content": content}],
    )

    answer = response.content[0].text.strip().upper()
    log.info("Vision audit result: %s correlation_id=%s", answer[:20], correlation_id)

    if answer.startswith("YES"):
        return "legible"
    return "illegible"

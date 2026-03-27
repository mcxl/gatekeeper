#!/usr/bin/env python3
"""
api/intake_routes.py
Mode 04: Intake form — upload scope doc or existing SWMS,
Claude extracts and returns structured form with per-field confidence.
User reviews/edits, then confirms to generate.

Endpoints:
  POST /intake/extract   — file upload → structured form + confidence
  POST /intake/generate  — confirmed form → SWMS generation
"""

import logging
import traceback
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from typing import List
from pathlib import Path

from slowapi import Limiter
from slowapi.util import get_remote_address

from core.auth import get_current_user
from core.document_extractor import (
    extract_text, extract_multiple, truncate_for_prompt,
    IMAGE_EXTENSIONS, DOC_EXTENSIONS, _get_client
)

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/intake", tags=["intake"])

MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_FILES = 10
ALLOWED_EXTENSIONS = DOC_EXTENSIONS | IMAGE_EXTENSIONS

_MAGIC_BYTES = {
    ".pdf": (b"%PDF",),
    ".docx": (b"PK",),
    ".doc": (b"\xd0\xcf\x11\xe0",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG",),
}

CONFIDENCE_HIGH   = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW    = "low"
CONFIDENCE_ABSENT = "absent"


INTAKE_EXTRACT_PROMPT = """You are a WHS Safety adviser reading an Australian
construction document — this may be a Scope of Works, Specification, Contractor
Quote, Methodology Statement, or an existing SWMS.

DOCUMENT TEXT:
{doc_text}

Extract all available information and return a JSON object with this exact structure.

For each field, provide the value AND a confidence level:
- "high"   = explicitly stated in the document
- "medium" = reasonably inferred from context
- "low"    = assumed from building type or industry practice
- "absent" = not found — leave value as empty string

{{
  "pcbu_name":            {{"value": "", "confidence": "absent", "source": ""}},
  "project_address":      {{"value": "", "confidence": "absent", "source": ""}},
  "manager_name":         {{"value": "", "confidence": "absent", "source": ""}},
  "principal_contractor": {{"value": "", "confidence": "absent", "source": ""}},
  "title":                {{"value": "", "confidence": "absent", "source": ""}},
  "work_activity_summary":{{"value": "", "confidence": "absent", "source": ""}},
  "description":          {{"value": "", "confidence": "absent", "source": ""}},
  "access_method":        {{"value": "", "confidence": "absent", "source": ""}},
  "building_type":        {{"value": "", "confidence": "absent", "source": ""}},
  "storeys":              {{"value": "", "confidence": "absent", "source": ""}},
  "occupancy":            {{"value": "", "confidence": "absent", "source": ""}},
  "hrcw_categories":      {{"value": [], "confidence": "absent", "source": ""}}
}}

For "source": quote the brief clause or phrase (under 10 words) from the document
that you extracted each value from. Leave empty if absent or inferred.

For "description": Comprehensive brief capturing ALL trade types and work activities,
every material and product named, access methods, location context, and HRCW
implications. For quote documents, read every line item as a scope activity.
Do NOT omit line items.

For quote documents: read dashed/bulleted line items under trade headings as
individual work activities — do not just capture the trade heading.

Return only valid JSON, no preamble, no markdown fences.
"""


def _validate_file(contents: bytes, filename: str):
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"'{filename}' — unsupported type. Upload PDF, DOCX, TXT, JPG, or PNG."
        )
    expected = _MAGIC_BYTES.get(ext)
    if expected and not any(contents[:8].startswith(sig) for sig in expected):
        raise HTTPException(
            status_code=400,
            detail="File content does not match declared file type"
        )


def _parse_json(raw: str) -> dict:
    """Parse JSON from Claude response — uses defensive parser from swms_analyser."""
    from core.swms_analyser import _parse_json_response
    return _parse_json_response(raw)


def _flatten_fields(extracted: dict) -> dict:
    """Convert {field: {value, confidence, source}} → flat dicts for response."""
    fields = {}
    confidence = {}
    sources = {}
    for key, data in extracted.items():
        if isinstance(data, dict):
            fields[key]     = data.get("value", "")
            confidence[key] = data.get("confidence", CONFIDENCE_ABSENT)
            sources[key]    = data.get("source", "")
        else:
            fields[key]     = data
            confidence[key] = CONFIDENCE_HIGH
            sources[key]    = ""
    return fields, confidence, sources


@router.post("/extract")
@limiter.limit("10/minute")
async def intake_extract(
    request: Request,
    files: List[UploadFile] = File(default=None),
    file: UploadFile = File(default=None),
    current_user: dict = Depends(get_current_user)
):
    """
    Mode 04: Upload scope doc or existing SWMS.
    Returns structured intake form fields with per-field confidence scores.
    Accepts 'files' (list) or 'file' (single) form field.
    """
    # Accept either 'files' or 'file' form field name
    if not files and file:
        files = [file]
    if not files:
        return JSONResponse(
            status_code=400,
            content={"detail": "No file uploaded. Please select a PDF, Word, or image file."}
        )
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_FILES} files.")

    file_tuples = []
    for file in files:
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"'{file.filename}' exceeds 10MB limit."
            )
        _validate_file(contents, file.filename)
        file_tuples.append((contents, file.filename))

    import time
    from core.swms_analyser import save_extraction

    total_file_size = sum(len(fb) for fb, _ in file_tuples)
    first_filename = file_tuples[0][1] if file_tuples else "unknown"

    try:
        t0 = time.monotonic()

        if len(file_tuples) == 1:
            raw_text = extract_text(file_tuples[0][0], file_tuples[0][1])
        else:
            raw_text = extract_multiple(file_tuples)

        truncated = truncate_for_prompt(raw_text)

        client = _get_client()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": INTAKE_EXTRACT_PROMPT.format(doc_text=truncated)
            }]
        )

        duration_ms = int((time.monotonic() - t0) * 1000)

        extracted = _parse_json(response.content[0].text)
        fields, confidence, sources = _flatten_fields(extracted)

        # Count missing required fields
        required = ["pcbu_name", "project_address", "description",
                    "work_activity_summary", "title"]
        missing = [f for f in required
                   if not fields.get(f) or confidence.get(f) == CONFIDENCE_ABSENT]

        # Save to scope library (non-blocking)
        user_id = current_user.get("sub") if current_user else None
        await save_extraction(
            filename=first_filename,
            file_size=total_file_size,
            extracted_fields=fields,
            duration_ms=duration_ms,
            user_id=user_id,
        )

        return JSONResponse({
            "mode": "04",
            "file_count": len(files),
            "char_count": len(raw_text),
            "fields": fields,
            "confidence": confidence,
            "sources": sources,
            "missing_required": missing,
            "absent_count": sum(
                1 for v in confidence.values() if v == CONFIDENCE_ABSENT
            ),
        })

    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"detail": str(e) or "Could not extract text from this file. Try a different format."}
        )
    except Exception:
        logger.error(f"intake-extract error:\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal error occurred. Please try again."}
        )

# POST /intake/generate was removed — it was dead code.
# The intake flow uses /generate/stream + /render/docx instead.

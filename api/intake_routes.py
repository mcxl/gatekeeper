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
import json
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
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
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


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
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Mode 04: Upload scope doc or existing SWMS.
    Returns structured intake form fields with per-field confidence scores.
    """
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

    try:
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

        extracted = _parse_json(response.content[0].text)
        fields, confidence, sources = _flatten_fields(extracted)

        # Count missing required fields
        required = ["pcbu_name", "project_address", "description",
                    "work_activity_summary", "title"]
        missing = [f for f in required
                   if not fields.get(f) or confidence.get(f) == CONFIDENCE_ABSENT]

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
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"intake-extract error:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred. Please try again."
        )


@router.post("/generate")
@limiter.limit("5/minute")
async def intake_generate(
    request: Request,
    body: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Mode 04: Take confirmed intake form fields and fire generation.
    Streams back the same SSE format as POST /generate/auto.
    """
    from core.generate import generate_swms

    fields = body.get("fields", {})
    jurisdiction = body.get("jurisdiction", "AU")

    description = fields.get("description", "").strip()
    if not description:
        raise HTTPException(status_code=422, detail="Description is required.")

    project_meta = {
        "pcbu_name":             fields.get("pcbu_name", ""),
        "project_address":       fields.get("project_address", ""),
        "manager_name":          fields.get("manager_name", ""),
        "principal_contractor":  fields.get("principal_contractor", ""),
        "title":                 fields.get("title", ""),
        "work_activity_summary": fields.get("work_activity_summary", ""),
        "supervisor":            fields.get("manager_name", ""),
    }

    scope_context = {
        "access_method":  fields.get("access_method", ""),
        "building_type":  fields.get("building_type", ""),
        "storeys":        fields.get("storeys", ""),
        "occupancy":      fields.get("occupancy", ""),
        "hrcw_categories": fields.get("hrcw_categories", []),
    } if any(fields.get(k) for k in [
        "access_method", "building_type", "storeys", "occupancy"
    ]) else None

    async def stream():
        import json as _json
        try:
            async for event in generate_swms(
                description=description,
                project_meta=project_meta,
                jurisdiction=jurisdiction,
                scope_context=scope_context,
            ):
                yield f"data: {_json.dumps(event)}\n\n"
        except Exception as e:
            logger.error(f"intake-generate stream error: {e}")
            yield f"data: {_json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

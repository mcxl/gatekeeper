#!/usr/bin/env python3
"""
api/upload_routes.py
Endpoints for Mode 02 (existing SWMS) and Mode 03 (scope of works).
Accepts files (PDF/DOCX/TXT) and images (JPG/PNG) including multiple files.
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
    extract_text, extract_multiple, truncate_for_prompt, truncate_for_scope,
    IMAGE_EXTENSIONS, DOC_EXTENSIONS
)
from core.swms_analyser import analyse_existing_swms, extract_scope_from_document

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/upload", tags=["upload"])

MAX_FILE_SIZE = 10 * 1024 * 1024   # 10MB per file
MAX_FILES = 10                      # max photos/files per upload
ALLOWED_EXTENSIONS = DOC_EXTENSIONS | IMAGE_EXTENSIONS

# Magic bytes for file type verification
_MAGIC_BYTES = {
    ".pdf": (b"%PDF",),
    ".docx": (b"PK",),
    ".doc": (b"\xd0\xcf\x11\xe0",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG",),
}


def validate_files(files: List[UploadFile]):
    for file in files:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"'{file.filename}' — unsupported type. "
                       f"Upload PDF, DOCX, TXT, JPG, or PNG."
            )
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_FILES} files per upload."
        )


def validate_magic_bytes(contents: bytes, filename: str):
    """Verify file content matches declared extension via magic bytes."""
    ext = Path(filename).suffix.lower()
    expected = _MAGIC_BYTES.get(ext)
    if expected is None:
        return  # .txt and other text files — no magic bytes to check
    if not any(contents[:8].startswith(sig) for sig in expected):
        raise HTTPException(
            status_code=400,
            detail="File content does not match declared file type"
        )


def build_job_data(result: dict) -> dict:
    """Extract job_data fields from analyser result."""
    return {
        "description": result.get("description", ""),
        "work_activity_summary": result.get("work_activity_summary", ""),
        "pcbu_name": result.get("pcbu_name", ""),
        "principal_contractor": result.get("principal_contractor", ""),
        "project_address": result.get("project_address", ""),
        "manager_name": result.get("manager_name", ""),
        "jurisdiction": result.get("jurisdiction", "AU"),
    }


@router.post("/analyse-swms")
@limiter.limit("10/minute")
async def analyse_swms(
    request: Request,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Mode 02: Upload existing SWMS (file or photos).
    Returns gap analysis + pre-filled job_data for Direct Fields form.
    """
    validate_files(files)

    file_tuples = []
    for file in files:
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"'{file.filename}' exceeds 10MB limit."
            )
        validate_magic_bytes(contents, file.filename)
        file_tuples.append((contents, file.filename))

    try:
        if len(file_tuples) == 1:
            raw_text = extract_text(file_tuples[0][0], file_tuples[0][1])
        else:
            raw_text = extract_multiple(file_tuples)

        truncated = truncate_for_prompt(raw_text)
        result = await analyse_existing_swms(truncated)

        return JSONResponse({
            "mode": "02",
            "file_count": len(files),
            "char_count": len(raw_text),
            "gaps": result.get("gaps", []),
            "existing_tasks": result.get("existing_tasks", []),
            "hrcw_categories": result.get("hrcw_categories", []),
            "job_data": build_job_data(result)
        })

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        logger.error(f"analyse-swms error:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.post("/extract-scope")
@limiter.limit("10/minute")
async def extract_scope(
    request: Request,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Mode 03: Upload Scope of Works / Specification (file or photos).
    Returns extracted job_data for Direct Fields form.
    """
    validate_files(files)

    file_tuples = []
    for file in files:
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"'{file.filename}' exceeds 10MB limit."
            )
        validate_magic_bytes(contents, file.filename)
        file_tuples.append((contents, file.filename))

    try:
        if len(file_tuples) == 1:
            raw_text = extract_text(file_tuples[0][0], file_tuples[0][1])
        else:
            raw_text = extract_multiple(file_tuples)

        truncated = truncate_for_scope(raw_text)
        result = await extract_scope_from_document(truncated)

        # Build scope_context from all extracted fields (beyond job_data)
        scope_context = {k: v for k, v in result.items()
                         if k not in ("hrcw_categories",) and v}

        return JSONResponse({
            "mode": "03",
            "file_count": len(files),
            "char_count": len(raw_text),
            "hrcw_categories": result.get("hrcw_categories", []),
            "job_data": build_job_data(result),
            "scope_context": scope_context
        })

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        logger.error(f"extract-scope error:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")

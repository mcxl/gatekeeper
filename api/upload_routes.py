#!/usr/bin/env python3
"""
api/upload_routes.py
Endpoints for Mode 02 (existing SWMS) and Mode 03 (scope of works).
Accepts files (PDF/DOCX/TXT) and images (JPG/PNG) including multiple files.
"""

import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List
from pathlib import Path

from core.auth import get_current_user
from core.document_extractor import (
    extract_text, extract_multiple, truncate_for_prompt,
    IMAGE_EXTENSIONS, DOC_EXTENSIONS
)
from core.swms_analyser import analyse_existing_swms, extract_scope_from_document

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/upload", tags=["upload"])

MAX_FILE_SIZE = 10 * 1024 * 1024   # 10MB per file
MAX_FILES = 10                      # max photos/files per upload
ALLOWED_EXTENSIONS = DOC_EXTENSIONS | IMAGE_EXTENSIONS


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
async def analyse_swms(
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
    except Exception as e:
        logger.error(f"analyse-swms error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-scope")
async def extract_scope(
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
        file_tuples.append((contents, file.filename))

    try:
        if len(file_tuples) == 1:
            raw_text = extract_text(file_tuples[0][0], file_tuples[0][1])
        else:
            raw_text = extract_multiple(file_tuples)

        truncated = truncate_for_prompt(raw_text)
        result = await extract_scope_from_document(truncated)

        return JSONResponse({
            "mode": "03",
            "file_count": len(files),
            "char_count": len(raw_text),
            "hrcw_categories": result.get("hrcw_categories", []),
            "job_data": build_job_data(result)
        })

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"extract-scope error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

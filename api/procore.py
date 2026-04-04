#!/usr/bin/env python3
"""
api/procore.py
Reception-layer Procore webhook endpoint (Phase 1A).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from core.job_state import record_state
from core.logging_config import log_event, set_correlation_id

logger = logging.getLogger(__name__)
router = APIRouter(tags=["procore"])


@router.post("/webhook")
async def procore_webhook(request: Request):
    correlation_id = str(uuid.uuid4())
    set_correlation_id(correlation_id)
    raw_body = await request.body()
    headers = {"X-Correlation-ID": correlation_id}

    secret = os.getenv("PROCORE_WEBHOOK_SECRET", "")
    signature_header = request.headers.get("procore-signature", "")

    if not secret:
        logger.warning("PROCORE_WEBHOOK_SECRET not configured — skipping HMAC verification")
    else:
        computed_signature = hmac.new(
            secret.encode("utf-8"), raw_body, hashlib.sha256
        ).hexdigest()
        log_event(
            event_type="procore_webhook_hmac",
            duration_ms=None,
            metadata={
                "correlation_id": correlation_id,
                "signature_header": signature_header,
                "computed_signature": computed_signature,
            },
        )

        normalized_signature = signature_header.strip()
        if normalized_signature.lower().startswith("sha256="):
            normalized_signature = normalized_signature.split("=", 1)[1]

        if not hmac.compare_digest(normalized_signature, computed_signature):
            logger.warning("HMAC mismatch — rejecting webhook")
            return JSONResponse(
                content={"detail": "Invalid webhook signature"},
                status_code=401,
                headers=headers,
            )

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Procore webhook JSON: %s", exc)
        return JSONResponse(
            content={"detail": "Invalid JSON payload"},
            status_code=400,
            headers=headers,
        )

    try:
        await record_state(
            correlation_id=correlation_id,
            job_type="procore_webhook",
            state="received",
            metadata={
                "submittal_id": payload.get("submittal_id"),
                "project_id": payload.get("project_id"),
                "event_type": payload.get("event_type"),
                "document_url": payload.get("document_url"),
            },
        )
    except Exception as exc:
        logger.error("job_states insert failed: %s — type: %s", exc, type(exc).__name__)
        import traceback

        logger.error(traceback.format_exc())

    return JSONResponse(
        content={"status": "accepted", "correlation_id": correlation_id},
        status_code=202,
        headers=headers,
    )

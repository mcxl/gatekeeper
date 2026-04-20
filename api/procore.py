#!/usr/bin/env python3
"""
api/procore.py — Stage 2 Procore webhook endpoint.

Synchronous BackgroundTask pipeline:
1. Orphan cleanup
2. Accept webhook, return 202
3. BackgroundTask: fetch → extract → review → comment
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
import uuid

import httpx
from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse

from core.job_state import record_state
from core.logging_config import log_event, set_correlation_id

logger = logging.getLogger(__name__)
router = APIRouter(tags=["procore"])

ORPHAN_THRESHOLD_SECONDS = 150
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")


# ── Orphan cleanup ──────────────────────────────────────────────────────────

async def _cleanup_orphaned_jobs() -> None:
    """Mark processing jobs older than 150s as failed_orphaned.

    Opportunistic: runs at the start of each new webhook request.
    """
    try:
        # Query Supabase for orphaned jobs
        supabase_url = os.getenv("SUPABASE_URL", "")
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not supabase_url or not service_key:
            return

        from datetime import datetime, timedelta, timezone
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=ORPHAN_THRESHOLD_SECONDS)).isoformat()

        headers = {
            "apikey": service_key,
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

        # Find orphans
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{supabase_url}/rest/v1/job_states"
                f"?state=eq.processing&created_at=lt.{cutoff}&select=correlation_id,created_at",
                headers=headers,
            )

        if response.status_code != 200:
            return

        orphans = response.json()
        for orphan in orphans:
            cid = orphan.get("correlation_id", "unknown")
            created = orphan.get("created_at", "")
            logger.warning("Orphan detected — correlation_id: %s, created: %s", cid, created)

            await record_state(
                correlation_id=cid,
                job_type="procore_webhook",
                state="failed_orphaned",
                metadata={"failure_reason": "platform_timeout"},
            )
    except Exception as e:
        logger.warning("Orphan cleanup failed: %s", e)


# ── Timeout ladder helpers ──────────────────────────────────────────────────

async def _slack_alert(message: str, correlation_id: str) -> None:
    """Send alert to Slack if webhook URL configured. Never raises."""
    if not SLACK_WEBHOOK_URL:
        logger.info("Slack alert (log-only): %s correlation_id=%s", message, correlation_id)
        return
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(SLACK_WEBHOOK_URL, json={"text": f"{message} (correlation_id: {correlation_id})"})
    except Exception as e:
        logger.warning("Slack alert failed: %s", e)


# ── Background pipeline ────────────────────────────────────────────────────

async def _process_webhook(payload: dict, correlation_id: str) -> None:
    """Main pipeline: fetch → extract → review → comment."""
    from core.procore_comment import post_heartbeat_comment, post_review_comment
    from core.procore_extract import extract_and_route
    from core.procore_fetch import ProcoreFetchError, ProcoreFetchTimeout, fetch_procore_pdf
    from core.procore_review import run_procore_review

    set_correlation_id(correlation_id)
    submittal_id = str(payload.get("submittal_id", ""))
    document_url = payload.get("document_url", "")
    t_start = time.monotonic()

    def _elapsed() -> float:
        return time.monotonic() - t_start

    # 1. SM heartbeat: received
    await post_heartbeat_comment(submittal_id, "received", correlation_id, tier="sm")

    # 2. PM heartbeat: received
    await post_heartbeat_comment(submittal_id, "received", correlation_id, tier="pm")

    # 3. Write job_state: processing
    await record_state(correlation_id, "procore_webhook", "processing",
                        {"submittal_id": submittal_id})

    # 4. Fetch PDF
    try:
        pdf_bytes = await fetch_procore_pdf(document_url, correlation_id)
    except (ProcoreFetchError, ProcoreFetchTimeout) as e:
        await record_state(correlation_id, "procore_webhook", "failed",
                            {"failure_reason": "fetch_error", "error": str(e)})
        await post_heartbeat_comment(submittal_id, "failed", correlation_id, tier="sm")
        await post_heartbeat_comment(submittal_id, "failed", correlation_id, tier="pm")
        return

    # Check 45s timeout ladder
    if _elapsed() > 45:
        await _slack_alert("Procore review exceeding 45s", correlation_id)

    # 5. Extract + route
    extraction = await extract_and_route(pdf_bytes, correlation_id)
    if extraction.abort:
        await record_state(correlation_id, "procore_webhook", "failed",
                            {"failure_reason": extraction.abort_reason or "vision_abort",
                             "confidence_tier": extraction.confidence_tier})
        await post_heartbeat_comment(submittal_id, "aborted", correlation_id, tier="sm")
        await post_heartbeat_comment(submittal_id, "aborted", correlation_id, tier="pm")
        return

    # 6. SM heartbeat: processing
    await post_heartbeat_comment(submittal_id, "processing", correlation_id, tier="sm")

    # 7. PM heartbeat: processing
    await post_heartbeat_comment(submittal_id, "processing", correlation_id, tier="pm")

    # Check 90s timeout ladder
    if _elapsed() > 90:
        await post_heartbeat_comment(
            submittal_id,
            f"Still processing — correlation_id: {correlation_id}",
            correlation_id, tier="sm",
        )

    # 8. Run review engine
    extraction_source = "vision_ocr" if extraction.confidence_tier == "amber" else "pypdf"
    review_result = await run_procore_review(
        extraction.text, correlation_id, extraction_source=extraction_source,
    )

    # Check 120s timeout ladder
    if _elapsed() > 120:
        await record_state(correlation_id, "procore_webhook", "timed_out_soft",
                            {"elapsed_seconds": round(_elapsed(), 1)})

    # 9. SM review comment (vision tags if amber)
    await post_review_comment(submittal_id, review_result, correlation_id)

    # 10. PM complete comment
    from core.procore_comment import _reason_summary
    reason = _reason_summary(review_result)
    await post_heartbeat_comment(submittal_id, "complete", correlation_id, tier="pm",
                                  reason_summary=reason)

    # 11. Write job_state: complete
    await record_state(correlation_id, "procore_webhook", "complete", {
        "submittal_id": submittal_id,
        "overall_result": review_result.overall_result,
        "confidence": review_result.confidence,
        "extraction_source": extraction_source,
        "extraction_char_count": extraction.char_count,
        "extraction_page_count": extraction.page_count,
        "chars_per_page": round(extraction.chars_per_page, 1),
        "confidence_tier": extraction.confidence_tier,
        "vision_audit_triggered": extraction.vision_audit_triggered,
        "vision_audit_result": extraction.vision_audit_result,
        "finding_count": len(review_result.findings),
        "hard_fail_count": len(review_result.hard_fails),
    })

    # Final 180s safety net
    if _elapsed() > 180:
        await record_state(correlation_id, "procore_webhook", "failed",
                            {"failure_reason": "platform_timeout", "elapsed": round(_elapsed(), 1)})
        await post_heartbeat_comment(submittal_id, "failed", correlation_id, tier="sm")
        await post_heartbeat_comment(submittal_id, "failed", correlation_id, tier="pm")


# ── Webhook endpoint ────────────────────────────────────────────────────────

@router.post("/webhook")
async def procore_webhook(request: Request, background_tasks: BackgroundTasks):
    correlation_id = str(uuid.uuid4())
    set_correlation_id(correlation_id)
    raw_body = await request.body()
    headers = {"X-Correlation-ID": correlation_id}

    # Orphan cleanup (opportunistic)
    await _cleanup_orphaned_jobs()

    # HMAC verification
    secret = os.getenv("PROCORE_WEBHOOK_SECRET", "")
    signature_header = request.headers.get("procore-signature", "")

    if not secret:
        logger.warning("PROCORE_WEBHOOK_SECRET not configured — skipping HMAC verification")
    else:
        computed = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        normalized = signature_header.strip()
        if normalized.lower().startswith("sha256="):
            normalized = normalized.split("=", 1)[1]
        if not hmac.compare_digest(normalized, computed):
            logger.warning("HMAC mismatch — rejecting webhook")
            return JSONResponse(content={"detail": "Invalid webhook signature"}, status_code=401, headers=headers)

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Procore webhook JSON: %s", exc)
        return JSONResponse(content={"detail": "Invalid JSON payload"}, status_code=400, headers=headers)

    # Write received state
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
        logger.error("job_states insert failed: %s", exc)

    log_event(
        event_type="procore_webhook_received",
        metadata={"correlation_id": correlation_id, "submittal_id": payload.get("submittal_id")},
    )

    # Launch background pipeline
    background_tasks.add_task(_process_webhook, payload, correlation_id)

    return JSONResponse(
        content={"status": "accepted", "correlation_id": correlation_id},
        status_code=202,
        headers=headers,
    )

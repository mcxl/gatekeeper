#!/usr/bin/env python3
"""
core/job_state.py - Supabase-backed append-only job state writer.
"""

from __future__ import annotations

import os

import httpx

from core.logging_config import log_event

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


def _supabase_headers() -> dict:
    return {
        "apikey": SUPABASE_SERVICE_KEY,
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


async def record_state(
    correlation_id: str,
    job_type: str,
    state: str,
    metadata: dict | None = None,
) -> None:
    """
    INSERT a job state row. Never raises - log and swallow on failure.
    Observability must never break the generation pipeline.
    """
    try:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY or not SUPABASE_SERVICE_KEY:
            log_event(
                event_type="job_state_write_failed",
                duration_ms=None,
                metadata={
                    "reason": "supabase_not_configured",
                    "correlation_id": correlation_id,
                    "job_type": job_type,
                    "state": state,
                },
            )
            return

        payload = {
            "correlation_id": correlation_id,
            "job_type": job_type,
            "state": state,
            "metadata": metadata or {},
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/job_states",
                headers=_supabase_headers(),
                json=payload,
            )

        if response.status_code >= 300:
            log_event(
                event_type="job_state_write_failed",
                duration_ms=None,
                metadata={
                    "reason": "supabase_insert_failed",
                    "status_code": response.status_code,
                    "correlation_id": correlation_id,
                    "job_type": job_type,
                    "state": state,
                    "response_text": response.text[:500],
                },
            )
            return
    except Exception as exc:
        log_event(
            event_type="job_state_write_failed",
            duration_ms=None,
            metadata={
                "reason": "exception",
                "error": str(exc),
                "correlation_id": correlation_id,
                "job_type": job_type,
                "state": state,
            },
        )
        return

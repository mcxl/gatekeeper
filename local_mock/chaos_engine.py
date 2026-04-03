"""
local_mock/chaos_engine.py — Fake Procore webhook endpoint for testing.

Three modes via query param ?mode=:
  normal  → 200, returns fake payload immediately
  timeout → sleeps 30 seconds then returns 200
  error   → returns 503 immediately

Fake data only — no real PII. No external calls.
Run with: uvicorn local_mock.chaos_engine:app --port 3001
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

app = FastAPI(title="Chaos Engine — Procore Mock", version="0.1")

_FAKE_PAYLOAD = {
    "event_type": "submittals.submittal_logs.created",
    "timestamp": "",
    "resource_name": "submittal_logs",
    "resource_id": 99999,
    "project_id": 10001,
    "company_id": 20001,
    "api_version": "v1.1",
    "metadata": {
        "source_app": "chaos_engine",
        "delivery_id": "",
    },
    "data": {
        "id": 99999,
        "title": "SWMS - Excavation Near Services - Test",
        "description": "Chaos engine test submittal",
        "specification_section": {
            "id": 1,
            "number": "01 35 00",
            "description": "Special Procedures",
        },
        "status": {"id": 1, "name": "Open"},
        "current_revision": {
            "id": 88888,
            "number": 1,
            "attachments": [
                {
                    "id": 77777,
                    "filename": "SWMS_Excavation_Test_v1.pdf",
                    "content_type": "application/pdf",
                    "url": "https://fake.procore.test/attachment/77777",
                }
            ],
        },
        "submitter": {
            "id": 333,
            "name": "Test Subcontracting Pty Ltd",
            "abn": "12 345 678 901",
        },
        "site_address": "123 Test Street, Sydney NSW 2000",
        "created_at": "",
    },
}


@app.get("/webhook")
@app.post("/webhook")
async def webhook_mock(mode: str = Query(default="normal")):
    """Mock Procore webhook endpoint."""
    if mode == "error":
        return JSONResponse(
            content={"error": "Service unavailable (chaos mode)"},
            status_code=503,
        )

    if mode == "timeout":
        await asyncio.sleep(30)

    # Build fresh payload with timestamps
    payload = dict(_FAKE_PAYLOAD)
    payload["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload["metadata"] = {
        "source_app": "chaos_engine",
        "delivery_id": f"chaos-{uuid.uuid4().hex[:8]}",
    }
    payload["data"] = dict(payload["data"])
    payload["data"]["created_at"] = payload["timestamp"]

    return JSONResponse(content=payload)


@app.get("/health")
async def health():
    return {"status": "chaos_engine_ok", "modes": ["normal", "timeout", "error"]}

"""
local_mock/chaos_engine.py — Fake Procore webhook endpoint for testing.

Five modes via query param ?mode=:
  normal  → 200, returns fake payload immediately
  timeout → sleeps 30 seconds then returns 200
  error   → returns 503 immediately
  empty   → 200, returns 0-byte PDF response
  race    → fires two webhook POSTs 3s apart (same submittal, different versions)

Fake data only — no real PII. No external calls.
Run with: uvicorn local_mock.chaos_engine:app --port 3001
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, Response

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

    if mode == "empty":
        return Response(
            content=b"",
            media_type="application/pdf",
            status_code=200,
        )

    if mode == "race":
        return await _handle_race_mode()

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


async def _handle_race_mode() -> JSONResponse:
    """Fire two webhook POSTs 3 seconds apart to test idempotency and version suicide."""
    target_url = "http://localhost:8000/v1/procore/webhook"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    submittal_id = "fake-submittal-001"

    def _build_race_payload(version_id: str, file_id: str, delivery_suffix: str) -> dict:
        return {
            "event_type": "submittals.submittal_logs.created",
            "timestamp": now,
            "resource_name": "submittal_logs",
            "resource_id": 99999,
            "project_id": 10001,
            "company_id": 20001,
            "api_version": "v1.1",
            "metadata": {
                "source_app": "chaos_engine",
                "delivery_id": f"race-{delivery_suffix}",
            },
            "data": {
                "id": submittal_id,
                "title": f"SWMS - Race Test - {version_id}",
                "version_id": version_id,
                "current_revision": {
                    "id": int(file_id.replace("fake-file-", "").replace("-", "")),
                    "number": 1,
                    "attachments": [{
                        "id": file_id,
                        "filename": f"SWMS_Race_{version_id}.pdf",
                        "content_type": "application/pdf",
                        "url": f"https://fake.procore.test/attachment/{file_id}",
                    }],
                },
                "submitter": {"id": 333, "name": "Test Subcontracting Pty Ltd"},
            },
            "_simulated_swms_text": f"Excavation SWMS {version_id} with shoring and BYDA.",
        }

    results = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        # First request
        p1 = _build_race_payload("v1", "fake-file-001", "v1")
        try:
            r1 = await client.post(target_url, json=p1)
            results.append({"version": "v1", "status": r1.status_code})
        except Exception as e:
            results.append({"version": "v1", "error": str(e)})

        # Wait 3 seconds
        await asyncio.sleep(3)

        # Second request
        p2 = _build_race_payload("v2", "fake-file-002", "v2")
        try:
            r2 = await client.post(target_url, json=p2)
            results.append({"version": "v2", "status": r2.status_code})
        except Exception as e:
            results.append({"version": "v2", "error": str(e)})

    return JSONResponse(content={
        "mode": "race",
        "submittal_id": submittal_id,
        "results": results,
    })


@app.get("/health")
async def health():
    return {"status": "chaos_engine_ok", "modes": ["normal", "timeout", "error", "empty", "race"]}

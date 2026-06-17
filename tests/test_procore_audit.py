"""Tests for metadata-only Procore audit wiring."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from core.procore.audit import build_procore_audit_record, record_procore_audit
from core.procore.webhook_handler import WebhookEvent, parse_event

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "procore"


def _load_fixture(name: str) -> dict:
    with open(FIXTURES_DIR / f"{name}.json", encoding="utf-8") as f:
        return json.load(f)


def _review_artifact() -> dict:
    return {
        "review_run_id": "review-123",
        "document_hash": "abc123hash",
        "rule_pack_version": "pack-v1",
        "rule_library_version": "lib-v2",
        "project_review_status": "ACTIVE",
        "status_recommendation": "Return for Amendment",
        "workflow_state": "returned_for_amendment_recommended",
        "review_confidence": "HIGH",
        "review_summary": "RAW_SWMS_TEXT must never be stored in audit",
        "required_amendments": [
            {
                "title": "RAW_COMMENT_BODY",
                "reason": "RAW_SWMS_TEXT reason",
                "severity": "mandatory",
            },
            {
                "title": "Advisory item",
                "reason": "Another raw prose field",
                "severity": "advisory",
            },
        ],
        "_all_amendments": [{"reason": "RAW_INTERNAL_AMENDMENT"}],
    }


def test_build_audit_record_is_metadata_only(monkeypatch):
    monkeypatch.setenv("PROCORE_AUDIT_RETENTION_DAYS", "90")
    event = parse_event(_load_fixture("submittal_created"))

    record = build_procore_audit_record(
        event=event,
        review_artifact=_review_artifact(),
        delivery_key="evt-abc123-def456",
        correlation_id="corr-1",
        retrieval_mode="live_api",
        writeback_enabled=True,
        comment_posted=False,
    )
    serialized = json.dumps(record, sort_keys=True)

    assert record["record_type"] == "review"
    assert record["company_id"] == 67890
    assert record["project_id"] == 12345
    assert record["document_hash"] == "abc123hash"
    assert record["finding_count"] == 2
    assert record["hard_fail_count"] == 1
    assert record["retention_days"] == 90
    assert record["writeback"] == {
        "enabled": True,
        "posted": False,
        "retrieval_mode": "live_api",
        "resource_surface": "submittals",
        "resource_id": 98765,
        "resource_status": "unverified",
    }
    for forbidden in (
        "RAW_SWMS_TEXT",
        "RAW_COMMENT_BODY",
        "RAW_INTERNAL_AMENDMENT",
        "Another raw prose field",
    ):
        assert forbidden not in serialized


def test_record_procore_audit_noops_without_supabase(monkeypatch):
    import core.procore.audit as audit

    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.setattr(audit, "_post_supabase_audit", lambda record: 42)

    assert record_procore_audit({"record_type": "review"}) is None


def test_record_procore_audit_posts_expected_rpc(monkeypatch):
    import core.procore.audit as audit

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role")
    calls = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return 42

    class Client:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers, json):
            calls.append((url, headers, json, self.timeout))
            return Response()

    monkeypatch.setattr(audit.httpx, "Client", Client)

    assert record_procore_audit({"record_type": "review"}) == 42
    assert calls == [(
        "https://example.supabase.co/rest/v1/rpc/record_procore_audit",
        {
            "apikey": "service-role",
            "Authorization": "Bearer service-role",
            "Content-Type": "application/json",
        },
        {"p_record": {"record_type": "review"}},
        10.0,
    )]


def test_record_procore_audit_falls_back_on_rpc_error(monkeypatch):
    import core.procore.audit as audit

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role")

    def fail(record):
        raise RuntimeError("rpc missing")

    monkeypatch.setattr(audit, "_post_supabase_audit", fail)

    assert record_procore_audit({"record_type": "review"}) is None


def test_pipeline_attempts_metadata_audit_after_review(monkeypatch):
    import core.job_state as js
    import core.procore.audit as audit
    from api.main import _process_procore_v1_webhook

    async def noop_record_state(*args, **kwargs):
        return None

    calls = []
    monkeypatch.setattr(js, "record_state", noop_record_state)
    monkeypatch.setattr(
        audit,
        "record_review_audit",
        lambda **kwargs: calls.append(kwargs) or None,
    )
    payload = _load_fixture("submittal_created")
    payload["_simulated_swms_text"] = (
        "SWMS - Scaffold Bay 3\nErect scaffold with harness.\nFollow SWMS.\n"
    )
    event: WebhookEvent = parse_event(payload)

    result = asyncio.run(_process_procore_v1_webhook(
        payload,
        event,
        "corr-test",
        "delivery-key-test",
    ))

    assert result["status"] == "reviewed"
    assert len(calls) == 1
    assert calls[0]["delivery_key"] == "delivery-key-test"
    assert calls[0]["correlation_id"] == "corr-test"
    assert calls[0]["event"] == event
    assert calls[0]["review_artifact"]["document_hash"]
    assert calls[0]["writeback_enabled"] is False
    assert calls[0]["comment_posted"] is False

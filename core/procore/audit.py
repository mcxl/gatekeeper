"""Minimal Supabase audit writer for the Procore review pipeline.

The audit row is metadata-only: hashes, versions, statuses, counts, and
write-back state. It must not persist raw SWMS text, review prose, comment
body, attachment bytes, or amendment reasons.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from core.procore.webhook_handler import WebhookEvent

log = logging.getLogger(__name__)

_TIMEOUT = 10.0
_DEFAULT_RETENTION_DAYS = 365
_WRITEBACK_RESOURCE_STATUS = "unverified"


def _supabase_configured() -> bool:
    return bool(os.getenv("SUPABASE_URL", "") and os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))


def _positive_int_or_none(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _retention_days() -> int:
    raw = os.getenv("PROCORE_AUDIT_RETENTION_DAYS", str(_DEFAULT_RETENTION_DAYS))
    try:
        parsed = int(raw)
    except ValueError:
        return _DEFAULT_RETENTION_DAYS
    return parsed if parsed > 0 else _DEFAULT_RETENTION_DAYS


def _hard_fail_count(review_artifact: dict[str, Any]) -> int:
    amendments = review_artifact.get("required_amendments", [])
    if not isinstance(amendments, list):
        return 0
    hard_severities = {"hard_fail", "mandatory", "critical"}
    return sum(
        1
        for item in amendments
        if isinstance(item, dict)
        and str(item.get("severity", "")).strip().lower() in hard_severities
    )


def _finding_count(review_artifact: dict[str, Any]) -> int:
    amendments = review_artifact.get("required_amendments", [])
    if isinstance(amendments, list):
        return len(amendments)
    return 0


def build_procore_audit_record(
    *,
    event: WebhookEvent,
    review_artifact: dict[str, Any],
    delivery_key: str = "",
    correlation_id: str = "",
    retrieval_mode: str = "",
    writeback_enabled: bool = False,
    comment_posted: bool = False,
) -> dict[str, Any]:
    """Build the metadata-only payload for public.record_procore_audit(jsonb)."""
    return {
        "record_type": "review",
        "review_run_id": review_artifact.get("review_run_id", ""),
        "delivery_key": delivery_key or event.delivery_id,
        "correlation_id": correlation_id,
        "company_id": _positive_int_or_none(event.company_id),
        "project_id": _positive_int_or_none(event.project_id),
        "document_hash": review_artifact.get("document_hash", ""),
        "rule_pack_version": review_artifact.get("rule_pack_version", ""),
        "rule_library_version": review_artifact.get("rule_library_version", ""),
        "project_review_status": review_artifact.get("project_review_status", ""),
        "status_recommendation": review_artifact.get("status_recommendation", ""),
        "workflow_state": review_artifact.get("workflow_state", ""),
        "review_confidence": review_artifact.get("review_confidence", ""),
        "finding_count": _finding_count(review_artifact),
        "hard_fail_count": _hard_fail_count(review_artifact),
        "writeback": {
            "enabled": bool(writeback_enabled),
            "posted": bool(comment_posted),
            "retrieval_mode": retrieval_mode,
            "resource_surface": "submittals",
            "resource_id": _positive_int_or_none(event.resource_id),
            "resource_status": _WRITEBACK_RESOURCE_STATUS,
        },
        "retention_days": _retention_days(),
    }


def _post_supabase_audit(record: dict[str, Any]) -> int | None:
    base = os.getenv("SUPABASE_URL", "")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    url = f"{base}/rest/v1/rpc/record_procore_audit"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(url, headers=headers, json={"p_record": record})
        resp.raise_for_status()
        value = resp.json()
    if isinstance(value, int):
        return value
    return _positive_int_or_none(value)


def record_procore_audit(record: dict[str, Any]) -> int | None:
    """Write one Procore audit row, degrading to no-op if Supabase/RPC is absent."""
    if not _supabase_configured():
        log.info("Supabase not configured; skipping Procore audit write")
        return None
    try:
        return _post_supabase_audit(record)
    except Exception as exc:  # pragma: no cover - network/remote schema errors
        log.warning("Procore audit write failed; continuing without audit row: %s", exc)
        return None


def record_review_audit(
    *,
    event: WebhookEvent,
    review_artifact: dict[str, Any],
    delivery_key: str = "",
    correlation_id: str = "",
    retrieval_mode: str = "",
    writeback_enabled: bool = False,
    comment_posted: bool = False,
) -> int | None:
    """Build and write the metadata-only review audit record."""
    record = build_procore_audit_record(
        event=event,
        review_artifact=review_artifact,
        delivery_key=delivery_key,
        correlation_id=correlation_id,
        retrieval_mode=retrieval_mode,
        writeback_enabled=writeback_enabled,
        comment_posted=comment_posted,
    )
    return record_procore_audit(record)

"""
core/procore/webhook_handler.py — Procore webhook event processing for Phase 1 spike.

Bounded to one Procore surface: Submittals.
Receives submittal-created events, identifies uploaded SWMS PDFs,
runs pre-screen review, and returns a structured review artifact.

Human review is mandatory. Safe Method does not make approval decisions.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import httpx

log = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "data"
_PAYLOAD_LOG = _DATA_DIR / "procore_payloads.jsonl"
_REVIEW_LOG = _DATA_DIR / "procore_reviews.jsonl"
_IDEMPOTENCY_STORE: set[str] = set()
_LOCK = threading.Lock()

# ── Status vocabulary — never use Approved/Accepted/Compliant/Passed ────────

ALLOWED_STATUSES = frozenset({
    "Ready for Human Review",
    "Return for Amendment",
    "Escalate",
})

# ── Workflow states — never use approved/accepted/compliant/passed ──────────

ALLOWED_WORKFLOW_STATES = frozenset({
    "reviewed_pending_human",
    "returned_for_amendment_recommended",
    "escalated_for_attention",
})

MAX_REQUIRED_AMENDMENTS = 5

REVIEW_DISCLAIMER = (
    "Safe Method provides pre-screening support only "
    "and does not make binding approval decisions."
)


@dataclass
class WebhookEvent:
    """Parsed Procore webhook event."""
    event_type: str = ""
    delivery_id: str = ""
    project_id: int = 0
    company_id: int = 0
    resource_id: int = 0
    resource_name: str = ""
    timestamp: str = ""
    raw_payload: dict = field(default_factory=dict)


@dataclass
class SubmittalAttachment:
    """A single attachment from a submittal revision."""
    attachment_id: int = 0
    filename: str = ""
    content_type: str = ""
    url: str = ""


def validate_signature(payload_body: bytes, signature: str, secret: str) -> bool:
    """Validate Procore webhook HMAC-SHA256 signature."""
    if not secret or not signature:
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def parse_event(payload: dict) -> WebhookEvent:
    """Parse a raw Procore webhook payload into a WebhookEvent."""
    metadata = payload.get("metadata", {})
    return WebhookEvent(
        event_type=payload.get("event_type", ""),
        delivery_id=metadata.get("delivery_id", ""),
        project_id=payload.get("project_id", 0),
        company_id=payload.get("company_id", 0),
        resource_id=payload.get("resource_id", 0),
        resource_name=payload.get("resource_name", ""),
        timestamp=payload.get("timestamp", ""),
        raw_payload=payload,
    )


def is_duplicate(delivery_id: str) -> bool:
    """Check if this delivery_id has already been processed."""
    with _LOCK:
        if delivery_id in _IDEMPOTENCY_STORE:
            return True
        _IDEMPOTENCY_STORE.add(delivery_id)
        return False


def reset_idempotency() -> None:
    """Reset the in-memory idempotency store. For testing only."""
    with _LOCK:
        _IDEMPOTENCY_STORE.clear()


# ── Durable idempotency (T3) ─────────────────────────────────────────────────

def delivery_key(delivery_id: str, raw_body: bytes) -> str:
    """Stable idempotency key for a delivery.

    Prefers the Procore delivery id; falls back to a SHA-256 of the raw body
    when no delivery id is present, so every delivery is still de-duplicated
    (the current payloads only expose ``metadata.delivery_id``).
    """
    if delivery_id:
        return delivery_id
    return "sha256:" + hashlib.sha256(raw_body).hexdigest()


def _supabase_configured() -> bool:
    return bool(os.getenv("SUPABASE_URL", "") and os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))


def _reserve_supabase(key: str, correlation_id: str) -> bool:
    """Atomically reserve a delivery key via the Supabase RPC.

    Returns True when newly reserved, False when already seen. Raises on
    transport/HTTP error so the caller can fall back to the in-memory store.
    """
    base = os.getenv("SUPABASE_URL", "")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    url = f"{base}/rest/v1/rpc/reserve_procore_webhook_delivery"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            url,
            headers=headers,
            json={"p_delivery_key": key, "p_correlation_id": correlation_id},
        )
        resp.raise_for_status()
        return bool(resp.json())


def reserve_delivery(key: str, correlation_id: str = "") -> bool:
    """Reserve a delivery key before any side effect runs.

    Returns True if newly reserved (proceed), False if this is a duplicate.
    Durable via Supabase when configured; otherwise an in-memory fallback that
    is NOT durable across restarts — logged so the degradation is visible.
    """
    if _supabase_configured():
        try:
            return _reserve_supabase(key, correlation_id)
        except Exception as exc:  # pragma: no cover - network/parse errors
            log.warning(
                "Durable idempotency reserve failed (%s); using in-memory fallback", exc
            )
    else:
        log.info(
            "Supabase not configured; Procore idempotency is in-memory only (not durable)"
        )
    with _LOCK:
        if key in _IDEMPOTENCY_STORE:
            return False
        _IDEMPOTENCY_STORE.add(key)
        return True


def extract_submittal_attachments(event: WebhookEvent) -> list[SubmittalAttachment]:
    """Extract PDF attachments from a submittal event."""
    data = event.raw_payload.get("data", {})
    revision = data.get("current_revision", {})
    attachments = revision.get("attachments", [])
    result = []
    for att in attachments:
        if att.get("content_type", "").startswith("application/pdf") or \
           att.get("filename", "").lower().endswith(".pdf"):
            result.append(SubmittalAttachment(
                attachment_id=att.get("id", 0),
                filename=att.get("filename", ""),
                content_type=att.get("content_type", ""),
                url=att.get("url", ""),
            ))
    return result


def _local_jsonl_enabled() -> bool:
    """Whether local JSONL persistence under src/data is enabled.

    Default off (production-safe): the durable record is the Supabase audit
    trail (migration 008). Local JSONL is dev convenience only; enable with
    PROCORE_LOCAL_JSONL_ENABLED=true.
    """
    return os.getenv("PROCORE_LOCAL_JSONL_ENABLED", "false").strip().lower() == "true"


def log_payload(event: WebhookEvent) -> None:
    """Append the raw payload to the payload log for replay/debugging."""
    if not _local_jsonl_enabled():
        log.debug("Local JSONL disabled; skipping payload log write")
        return
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "logged_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "delivery_id": event.delivery_id,
        "event_type": event.event_type,
        "project_id": event.project_id,
        "resource_id": event.resource_id,
    }
    with _LOCK:
        with open(_PAYLOAD_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def log_review(review_artifact: dict, event: WebhookEvent) -> None:
    """Append the review artifact to the review log."""
    if not _local_jsonl_enabled():
        log.debug("Local JSONL disabled; skipping review log write")
        return
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "logged_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "delivery_id": event.delivery_id,
        "project_id": event.project_id,
        "resource_id": event.resource_id,
        "status_recommendation": review_artifact.get("status_recommendation", ""),
        "amendment_count": len(review_artifact.get("required_amendments", [])),
        "review_confidence": review_artifact.get("review_confidence", ""),
    }
    with _LOCK:
        with open(_REVIEW_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

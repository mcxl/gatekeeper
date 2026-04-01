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
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

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
    """Reset the idempotency store. For testing only."""
    with _LOCK:
        _IDEMPOTENCY_STORE.clear()


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


def log_payload(event: WebhookEvent) -> None:
    """Append the raw payload to the payload log for replay/debugging."""
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

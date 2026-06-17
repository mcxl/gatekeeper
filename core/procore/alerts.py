"""core/procore/alerts.py — canonical failure alerting for the Procore pipeline.

Extracted so the canonical /v1 path does not depend on the deprecated
api/procore.py module. Sends a Slack message when SLACK_WEBHOOK_URL is set,
otherwise logs. Never raises — alerting must not break the pipeline.
"""
from __future__ import annotations

import logging
import os

import httpx

log = logging.getLogger(__name__)


def alert_failure(message: str, correlation_id: str = "") -> None:
    """Emit a failure alert. Slack if configured, else log. Never raises."""
    text = f"{message} (correlation_id={correlation_id})" if correlation_id else message
    url = os.getenv("SLACK_WEBHOOK_URL", "")
    if not url:
        log.error("Procore pipeline alert: %s", text)
        return
    try:
        with httpx.Client(timeout=5.0) as client:
            client.post(url, json={"text": text})
    except Exception as exc:  # pragma: no cover - network errors
        log.warning("Slack alert failed: %s", exc)

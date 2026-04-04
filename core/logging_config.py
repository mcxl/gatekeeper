#!/usr/bin/env python3
"""
core/logging_config.py - Phase 1A structured JSON logging.

Provides async-safe correlation ID context via contextvars and a logger
factory that emits structured JSON.
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

_CORRELATION_ID: ContextVar[str] = ContextVar("correlation_id", default="none")
_DEFAULT_LOGGER_NAME = "gatekeeper.observability"


def set_correlation_id(cid: str) -> None:
    """Set correlation ID for the current async/task context."""
    _CORRELATION_ID.set(cid or "none")


def get_correlation_id() -> str:
    """Get correlation ID from contextvars."""
    return _CORRELATION_ID.get() or "none"


class _CorrelationFilter(logging.Filter):
    """Inject context correlation_id into each record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "correlation_id"):
            record.correlation_id = get_correlation_id()
        return True


class _JsonFormatter(logging.Formatter):
    """Render logs as a strict JSON object for observability."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "correlation_id": getattr(record, "correlation_id", "none") or "none",
            "event_type": getattr(record, "event_type", "log"),
            "duration_ms": getattr(record, "duration_ms", None),
            "metadata": getattr(record, "metadata", {}) or {},
        }
        return json.dumps(payload, ensure_ascii=True)


def get_logger(name: str) -> logging.Logger:
    """Return logger configured for structured JSON output."""
    logger = logging.getLogger(name)
    if getattr(logger, "_phase1a_configured", False):
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    handler.addFilter(_CorrelationFilter())
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger._phase1a_configured = True  # type: ignore[attr-defined]
    return logger


def log_event(
    event_type: str,
    duration_ms: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Log a structured event with correlation ID automatically injected."""
    logger = get_logger(_DEFAULT_LOGGER_NAME)
    logger.info(
        "",
        extra={
            "event_type": event_type,
            "duration_ms": duration_ms,
            "metadata": metadata or {},
        },
    )


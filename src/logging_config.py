"""
src/logging_config.py — Structured JSON logging for operational traceability.

Provides a JSON formatter and get_logger() helper.
Logs to stdout. Uses Python standard logging.
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

# ── Correlation ID via contextvars ──────────────────────────────────────────

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def new_correlation_id() -> str:
    """Generate and set a new correlation_id for the current context."""
    cid = str(uuid.uuid4())[:12]
    correlation_id_var.set(cid)
    return cid


def get_correlation_id() -> str:
    """Get the current correlation_id."""
    return correlation_id_var.get()


# ── JSON Formatter ──────────────────────────────────────────────────────────

class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "correlation_id": get_correlation_id(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Attach structured fields if present
        for field in ("job_id", "project_id", "source_surface", "event_type",
                       "duration_ms", "outcome", "error_message", "detail"):
            val = getattr(record, field, None)
            if val is not None:
                entry[field] = val
        if record.exc_info and record.exc_info[1]:
            entry["error_message"] = str(record.exc_info[1])
        return json.dumps(entry, default=str)


# ── Logger setup ────────────────────────────────────────────────────────────

_configured = False


def setup_logging(level: int = logging.INFO) -> None:
    """Configure structured JSON logging to stdout. Idempotent."""
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(level)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Get a named logger. Sets up JSON logging on first call."""
    setup_logging()
    return logging.getLogger(name)


def log_event(
    logger: logging.Logger,
    event_type: str,
    outcome: str = "success",
    job_id: str = "",
    project_id: str = "",
    source_surface: str = "",
    duration_ms: float | None = None,
    error_message: str = "",
    detail: dict | None = None,
    level: int = logging.INFO,
) -> None:
    """Log a structured operational event."""
    extra = {
        "event_type": event_type,
        "outcome": outcome,
        "job_id": job_id,
        "project_id": project_id,
        "source_surface": source_surface,
        "duration_ms": duration_ms,
        "error_message": error_message or None,
        "detail": detail or {},
    }
    logger.log(level, f"{event_type}: {outcome}", extra=extra)

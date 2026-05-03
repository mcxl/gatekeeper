"""
src/job_state.py — Simple append-only job-state tracking for webhook/review flows.

Appends state transitions to JSONL. Never overwrites records.
No state machine framework. No business logic tied to state changes.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from src.logging_config import get_correlation_id

_DATA_DIR = Path(__file__).parent / "data"
_STATE_LOG = _DATA_DIR / "job_state_log.jsonl"
_LOCK = threading.Lock()

# Phase 1A states
ALLOWED_STATES = frozenset({"received", "processing", "succeeded", "failed"})

# Phase 1A stages
ALLOWED_STAGES = frozenset({
    "webhook_entry", "document_fetch", "intake",
    "review", "artifact_write", "return_dispatch",
})


def append_state(
    state: str,
    stage: str,
    job_id: str = "",
    project_id: str = "",
    source_surface: str = "",
    source_item_id: str = "",
    event_id: str = "",
    correlation_id: str = "",
    error_message: str = "",
    detail: dict | None = None,
) -> dict:
    """Append a state transition record to the job-state log.

    Returns the record that was written.
    """
    if not correlation_id:
        correlation_id = get_correlation_id()

    record = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "correlation_id": correlation_id,
        "event_id": event_id,
        "job_id": job_id,
        "project_id": str(project_id),
        "source_surface": source_surface,
        "source_item_id": str(source_item_id),
        "state": state,
        "stage": stage,
        "error_message": error_message,
        "detail": detail or {},
    }

    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        with open(_STATE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return record


def read_state_log() -> list[dict]:
    """Read all state records. For testing/debugging only."""
    if not _STATE_LOG.exists():
        return []
    records = []
    with open(_STATE_LOG, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def clear_state_log() -> None:
    """Clear the state log. For testing only."""
    with _LOCK:
        if _STATE_LOG.exists():
            _STATE_LOG.unlink()

"""
core/procore/review_store.py — Store and retrieve full review artifacts for comparison.

Stores complete review artifacts keyed by source_item_id for later
resubmission comparison. Append-only JSONL with lookup by item.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

log = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "data"
_ARTIFACT_STORE = _DATA_DIR / "procore_review_artifacts.jsonl"
_LOCK = threading.Lock()


def store_artifact(artifact: dict) -> None:
    """Append a full review artifact to the store."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        with open(_ARTIFACT_STORE, "a", encoding="utf-8") as f:
            f.write(json.dumps(artifact, ensure_ascii=False) + "\n")


def find_previous_artifact(
    project_id: str,
    source_surface: str,
    source_item_id: str,
    exclude_run_id: str = "",
) -> dict | None:
    """Find the most recent prior review artifact for the same source item.

    Returns None if no previous artifact exists.
    """
    if not _ARTIFACT_STORE.exists():
        return None

    candidates = []
    with _LOCK:
        with open(_ARTIFACT_STORE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if (str(record.get("project_id", "")) == str(project_id)
                        and record.get("source_surface", "") == source_surface
                        and str(record.get("source_item_id", "")) == str(source_item_id)
                        and record.get("review_run_id", "") != exclude_run_id):
                    candidates.append(record)

    if not candidates:
        return None

    # Return most recent by reviewed_at
    candidates.sort(key=lambda r: r.get("reviewed_at", ""), reverse=True)
    return candidates[0]


def clear_store() -> None:
    """Clear the artifact store. For testing only."""
    with _LOCK:
        if _ARTIFACT_STORE.exists():
            _ARTIFACT_STORE.unlink()

"""
core/review_capture.py -- Append-only consultant review outcome log.

Stores non-sensitive review metadata only.
Used for consultant edit capture, commercial pilot evidence, and embedded integrations.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent / "src" / "data"
_REVIEW_FILE = _DATA_DIR / "review_outcomes.jsonl"


@dataclass
class ReviewOutcomeRecord:
    schema_version: str = "1.0"
    timestamp: str = ""
    review_source: str = "web_review"
    integration_source: str = "safe_method"
    issue_decision: str = "yes_with_edits"
    edit_categories: list[str] = field(default_factory=list)
    defect_taxonomy: list[str] = field(default_factory=list)
    review_minutes: int = 0
    total_minutes: int = 0
    reviewed_by: str = ""
    reviewer_user_id: str = ""
    validator_status: str = ""
    reviewer_status: str = ""
    issue_gate_fail_count: int = 0
    issue_gate_review_count: int = 0
    job_type: str = ""
    procore_company_id: str = ""
    procore_project_id: str = ""
    generation_timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


def append_review_outcome(record: ReviewOutcomeRecord) -> None:
    """Append one consultant review outcome without blocking on write failure."""
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(_REVIEW_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record), default=str) + "\n")
    except Exception as exc:
        log.warning("review_capture: append failed -- %s", exc)

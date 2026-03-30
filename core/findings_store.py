"""
core/findings_store.py — Append-only findings log + query interface.

V1 backend: JSONL file at src/data/findings_log.jsonl.
Interface designed for future swap to SQLite or Postgres without changing callers.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent / "src" / "data"
_FINDINGS_FILE = _DATA_DIR / "findings_log.jsonl"


def _get_pipeline_version() -> str:
    """Read pipeline version from VERSION file or env, fallback 'unknown'."""
    version = os.environ.get("PIPELINE_VERSION", "")
    if version:
        return version
    version_file = Path(__file__).parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "unknown"


@dataclass
class FindingRecord:
    schema_version: str = "1.0"
    timestamp: str = ""
    pipeline_version: str = ""
    stream_name: str = ""
    job_type: str = ""
    task_name: str = ""
    defect_type: str = ""
    check_name: str = ""
    finding_text: str = ""
    source: str = ""  # validator | reviewer_agent | external_review
    reviewer_agent_category: str = ""
    severity: str = ""  # hard_fail | review_flag | systemic
    resolved: bool = False
    promotion_id: str = ""
    fingerprint: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.pipeline_version:
            self.pipeline_version = _get_pipeline_version()
        if not self.fingerprint:
            self.fingerprint = self._compute_fingerprint()

    def _compute_fingerprint(self) -> str:
        """Deterministic fingerprint for logical defect identity.
        Stable across pipeline versions for the same logical defect."""
        task_norm = self.task_name.lower().strip()
        raw = f"{self.defect_type}|{self.check_name}|{self.job_type}|{task_norm}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def append_finding(record: FindingRecord) -> None:
    """Append one finding to findings_log.jsonl.
    Create file and directory if they do not exist.
    Never overwrite existing records.
    Never block on write failure — log error and continue."""
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(_FINDINGS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record), default=str) + "\n")
    except Exception as e:
        log.warning(f"findings_store: append failed — {e}")


def load_findings(
    job_type: str = "",
    defect_type: str = "",
    resolved: bool | None = None,
    min_timestamp: str = "",
    source: str = "",
) -> list[FindingRecord]:
    """Load findings from findings_log.jsonl with optional filters.
    Returns empty list if file does not exist."""
    if not _FINDINGS_FILE.exists():
        return []
    records = []
    try:
        with open(_FINDINGS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    rec = FindingRecord(**{k: v for k, v in data.items()
                                          if k in FindingRecord.__dataclass_fields__})
                    # Apply filters
                    if job_type and rec.job_type != job_type:
                        continue
                    if defect_type and rec.defect_type != defect_type:
                        continue
                    if resolved is not None and rec.resolved != resolved:
                        continue
                    if min_timestamp and rec.timestamp < min_timestamp:
                        continue
                    if source and rec.source != source:
                        continue
                    records.append(rec)
                except (json.JSONDecodeError, TypeError):
                    continue
    except Exception as e:
        log.warning(f"findings_store: load failed — {e}")
    return records

"""
core/pattern_detector.py — Detect recurring defect patterns in the findings store.

Runs on demand only. Never triggered automatically.
Surfaces RuleCandidate objects when a defect pattern recurs above threshold.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from core.findings_store import FindingRecord, load_findings

log = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent / "src" / "data"
_CANDIDATES_FILE = _DATA_DIR / "rule_candidates.jsonl"

# Severity weights
_SEVERITY_WEIGHTS: dict[str, float] = {
    "systemic": 3.0,
    "hard_fail": 2.0,
    "review_flag": 1.0,
}

# Source multipliers
_SOURCE_MULTIPLIERS: dict[str, float] = {
    "validator": 1.5,
    "reviewer_agent": 1.0,
    "external_review": 2.0,
}

# Known auto-generatable check patterns (issue gate check names + dominant control family keywords)
_AUTO_GENERATABLE_CHECKS = {
    "dominant_control_family", "hrcw_undercall", "unsupported_admin_controls",
    "framework_control_misuse", "wah_dominance_extended", "filler_controls",
    "job_type_mandatory_steps", "ccvs_alignment", "duplicate_controls",
    "missing_hold_point", "missing_stop_work", "missing_ppe",
}

_AUTO_GENERATABLE_FAMILIES = {
    "SIL", "CHM", "WAH", "SYS", "ELE", "EXC", "CON", "CRN",
}


@dataclass
class RuleCandidate:
    candidate_id: str = ""
    defect_family: str = ""
    check_name: str = ""
    job_type: str = ""
    occurrences: int = 0
    severity_score: float = 0.0
    example_findings: list[str] = field(default_factory=list)
    suggested_rule_text: str = ""
    suggested_target: str = ""
    auto_generatable: bool = False
    created_at: str = ""
    status: str = "pending"

    def __post_init__(self):
        if not self.candidate_id:
            self.candidate_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


def _composite_key(rec: FindingRecord) -> tuple[str, str, str, str]:
    """Group findings by defect_family + check_name + job_type + source."""
    return (rec.defect_type, rec.check_name, rec.job_type, rec.source)


def _score_finding(rec: FindingRecord) -> float:
    """Score a single finding by severity weight * source multiplier."""
    weight = _SEVERITY_WEIGHTS.get(rec.severity, 1.0)
    multiplier = _SOURCE_MULTIPLIERS.get(rec.source, 1.0)
    return weight * multiplier


def _is_auto_generatable(defect_family: str, check_name: str) -> bool:
    """Determine if a candidate can be auto-generated."""
    if check_name in _AUTO_GENERATABLE_CHECKS:
        return True
    if defect_family in _AUTO_GENERATABLE_FAMILIES:
        return True
    return False


def _suggest_target(check_name: str, defect_family: str) -> str:
    """Suggest the implementation target for a candidate."""
    if check_name in _AUTO_GENERATABLE_CHECKS:
        return "issue_gate"
    if defect_family.startswith("prompt_"):
        return "decomposer_prompt"
    if "control" in check_name.lower():
        return "control_writer_prompt"
    return "job_type_rules"


def _suggest_rule_text(defect_family: str, check_name: str, job_type: str,
                       examples: list[str]) -> str:
    """Generate a plain-English rule suggestion."""
    parts = [f"When job_type={job_type or 'any'}"]
    if check_name:
        parts.append(f"check '{check_name}' detects recurring '{defect_family}' defects")
    else:
        parts.append(f"recurring '{defect_family}' defects detected")
    if examples:
        parts.append(f"— e.g. {examples[0][:120]}")
    return ". ".join(parts) + "."


def detect_patterns(
    min_occurrences: int = 3,
    job_type: str = "",
    unresolved_only: bool = True,
) -> list[RuleCandidate]:
    """Detect recurring defect patterns in the findings store.
    Return candidates sorted by severity_score descending.
    Write candidates to src/data/rule_candidates.jsonl.
    Append only — do not overwrite existing candidates.
    Do not apply any rules."""
    findings = load_findings(
        job_type=job_type,
        resolved=False if unresolved_only else None,
    )

    # Group by composite key
    groups: dict[tuple, list[FindingRecord]] = defaultdict(list)
    for f in findings:
        groups[_composite_key(f)].append(f)

    candidates: list[RuleCandidate] = []
    for key, recs in groups.items():
        if len(recs) < min_occurrences:
            continue

        defect_family, check_name, jt, source = key
        severity_score = sum(_score_finding(r) for r in recs)
        examples = [r.finding_text for r in recs if r.finding_text][:3]

        candidate = RuleCandidate(
            defect_family=defect_family,
            check_name=check_name,
            job_type=jt,
            occurrences=len(recs),
            severity_score=severity_score,
            example_findings=examples,
            suggested_rule_text=_suggest_rule_text(defect_family, check_name, jt, examples),
            suggested_target=_suggest_target(check_name, defect_family),
            auto_generatable=_is_auto_generatable(defect_family, check_name),
        )
        candidates.append(candidate)

    # Sort by severity descending
    candidates.sort(key=lambda c: c.severity_score, reverse=True)

    # Append to candidates file
    if candidates:
        try:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(_CANDIDATES_FILE, "a", encoding="utf-8") as f:
                for c in candidates:
                    f.write(json.dumps(asdict(c), default=str) + "\n")
        except Exception as e:
            log.warning(f"pattern_detector: write failed — {e}")

    return candidates


def load_candidates(status: str = "") -> list[RuleCandidate]:
    """Load candidates from rule_candidates.jsonl with optional status filter."""
    if not _CANDIDATES_FILE.exists():
        return []
    results: list[RuleCandidate] = []
    try:
        with open(_CANDIDATES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    rc = RuleCandidate(**{k: v for k, v in data.items()
                                         if k in RuleCandidate.__dataclass_fields__})
                    if status and rc.status != status:
                        continue
                    results.append(rc)
                except (json.JSONDecodeError, TypeError):
                    continue
    except Exception as e:
        log.warning(f"pattern_detector: load failed — {e}")
    return results


def _update_candidate_status(candidate_id: str, new_status: str) -> bool:
    """Update a candidate's status in-place in the JSONL file.
    Returns True if found and updated."""
    if not _CANDIDATES_FILE.exists():
        return False
    lines: list[str] = []
    found = False
    try:
        with open(_CANDIDATES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    lines.append(line)
                    continue
                try:
                    data = json.loads(stripped)
                    if data.get("candidate_id") == candidate_id:
                        data["status"] = new_status
                        found = True
                    lines.append(json.dumps(data, default=str) + "\n")
                except json.JSONDecodeError:
                    lines.append(line)
        if found:
            with open(_CANDIDATES_FILE, "w", encoding="utf-8") as f:
                f.writelines(lines)
    except Exception as e:
        log.warning(f"pattern_detector: status update failed — {e}")
        return False
    return found

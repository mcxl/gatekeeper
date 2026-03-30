"""
core/job_type_rules.py — Job-type rule packs for SWMS validation.

Stub for Phase B — full implementation in Phase C.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class JobTypeRulePack:
    job_type: str
    mandatory_task_sequence: list[str] = field(default_factory=list)
    immediate_fail_if_missing: list[str] = field(default_factory=list)
    dominant_control_families: dict[str, str] = field(default_factory=dict)
    mandatory_hrcw_triggers: list[str] = field(default_factory=list)
    mandatory_additional_controls: list[str] = field(default_factory=list)
    clt_crane_detected: bool = False


JOB_TYPE_RULES: dict[str, JobTypeRulePack] = {}


def get_rule_pack(job_type: str) -> Optional[JobTypeRulePack]:
    """Returns None silently if job_type is unrecognised or empty."""
    if not job_type:
        return None
    return JOB_TYPE_RULES.get(job_type)

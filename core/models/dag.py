"""
core/models/dag.py — Pydantic schema for DAG sequence rules.

Lazy loaded: validated on first access, not at app startup.
If JSON is malformed, only that category fails.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel


class DagNode(BaseModel):
    id: str
    keywords: list[str]
    predecessors: list[str] = []
    predecessors_always: list[str] = []
    predecessors_if_cse: list[str] = []
    violation_type: Literal["HARD_FAIL", "HUMAN_REVIEW"]
    condition: Optional[str] = None
    note: Optional[str] = None
    mandatory_acknowledgment: Optional[str] = None


class DagRules(BaseModel):
    category: str
    mapping_confidence_threshold: float = 0.65
    cse_explicit_keywords: list[str] = []
    cse_ambiguous_indicators: list[str] = []
    atmospheric_minimum_controls: list[str] = []
    nodes: list[DagNode]


def load_dag_rules(path: str) -> DagRules:
    """Load and validate DAG rules from JSON.

    Raises ValidationError if schema mismatch.
    Called lazily on first use, not at startup.
    """
    with open(Path(path), encoding="utf-8") as f:
        data = json.load(f)
    return DagRules(**data)

"""
src/rule_library/rule_library.py — Thin mapping/annotation layer for the rule library.

Normalizes and annotates existing findings with stable rule identifiers and
consistent metadata. Does not replace review logic or make decisions.

Mapping precedence:
1. Deterministic issue gate mapping (finding_key exact match)
2. Project rule mapping (rule_id prefix PR-)
3. Reviewer normalized mapping (rule_family match)
4. Consultant-only (no canonical rule — rule_id null)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_LIBRARY_PATH = Path(__file__).parent / "rule_library.json"
_CACHE: dict | None = None


def load() -> dict:
    """Load the canonical rule library. Cached after first load."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if not _LIBRARY_PATH.exists():
        log.warning(f"Rule library not found: {_LIBRARY_PATH}")
        return {"library_version": "0.0", "rules": []}
    with open(_LIBRARY_PATH, encoding="utf-8") as f:
        _CACHE = json.load(f)
    return _CACHE


def _reload() -> dict:
    """Force reload (for testing)."""
    global _CACHE
    _CACHE = None
    return load()


def lookup(rule_id: str) -> dict | None:
    """Look up a rule by rule_id. Returns None if not found."""
    lib = load()
    for rule in lib.get("rules", []):
        if rule.get("rule_id") == rule_id:
            return rule
    return None


def list_active() -> list[dict]:
    """Return all active rules."""
    lib = load()
    return [r for r in lib.get("rules", []) if r.get("active", False)]


def list_by_layer(layer: str) -> list[dict]:
    """Return active rules filtered by layer (issue_gate, reviewer, etc.)."""
    return [r for r in list_active() if r.get("layer") == layer]


def _find_by_finding_key(finding_key: str) -> dict | None:
    """Find a rule by finding_key."""
    lib = load()
    for rule in lib.get("rules", []):
        if rule.get("finding_key") == finding_key and rule.get("active", False):
            return rule
    return None


def _find_by_family(rule_family: str, layer: str = "") -> dict | None:
    """Find the first active rule matching family and optionally layer."""
    for rule in list_active():
        if rule.get("rule_family") == rule_family:
            if not layer or rule.get("layer") == layer:
                return rule
    return None


def map_finding_to_rule(finding: dict) -> dict | None:
    """Map a finding to a canonical rule using precedence:
    1. finding_key exact match (issue gate)
    2. project_rule reference (PR- prefix)
    3. rule_family match (reviewer)
    4. None (consultant-only, no canonical rule)
    """
    # Tier 1: exact finding_key match (deterministic issue gate)
    fk = finding.get("finding_key") or finding.get("name") or finding.get("check", "")
    if fk:
        rule = _find_by_finding_key(fk)
        if rule:
            return rule

    # Tier 2: project rule reference
    pr_id = finding.get("rule_id", "")
    if pr_id and pr_id.startswith("PR-"):
        rule = lookup(pr_id)
        if rule:
            return rule

    # Tier 3: rule_family match for reviewer findings
    family = finding.get("rule_family", "")
    if family:
        return _find_by_family(family, layer="reviewer")

    return None


def annotate_finding(finding: dict) -> dict:
    """Annotate a single finding with rule library metadata.

    Adds rule_id, finding_key, rule_family, summary_label, library_version.
    Does not modify existing fields — additive only.
    """
    lib = load()
    result = dict(finding)
    rule = map_finding_to_rule(finding)

    if rule:
        result.setdefault("rule_id", rule["rule_id"])
        result.setdefault("finding_key", rule["finding_key"])
        result.setdefault("rule_family", rule["rule_family"])
        result.setdefault("summary_label", rule["summary_label"])
    else:
        result.setdefault("rule_id", None)
        result.setdefault("finding_key", finding.get("name", None))

    result["library_version"] = lib.get("library_version", "")
    return result


def annotate_findings(raw_findings: list[dict]) -> list[dict]:
    """Annotate a list of findings with rule library metadata."""
    return [annotate_finding(f) for f in raw_findings]

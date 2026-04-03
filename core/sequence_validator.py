"""
core/sequence_validator.py — Dumb DAG sequence runner.

No Procore logic. No workflow assumptions.
Takes task list + DAG rules path, returns structured result.
Never raises — errors return a safe fallback.
"""

from __future__ import annotations

import logging
from typing import Optional

log = logging.getLogger(__name__)


class SequenceValidator:
    def __init__(self, rules_path: str, strict_mode: bool = False):
        self._rules_path = rules_path
        self._rules = None
        self.strict_mode = strict_mode

    @property
    def rules(self):
        """Lazy load: validated on first access, not at startup."""
        if self._rules is None:
            from core.models.dag import load_dag_rules
            self._rules = load_dag_rules(self._rules_path)
        return self._rules

    def validate(self, tasks: list[dict], category: str) -> dict:
        """Validate task sequence against DAG rules.

        Returns structured result. Never raises.
        """
        try:
            return self._validate_inner(tasks, category)
        except Exception as e:
            log.warning(f"DAG validation error for {category}: {e}")
            return self._safe_fallback(str(e))

    def _validate_inner(self, tasks: list[dict], category: str) -> dict:
        rules = self.rules

        if rules.category != category:
            if self.strict_mode:
                return self._safe_fallback(f"Category mismatch: {category} vs {rules.category}")
            return {
                "valid": True,
                "hard_fails": [],
                "human_reviews": [],
                "mandatory_acknowledgments": [],
                "sequence_validated": False,
                "cse_overlap": "none",
                "note": f"Unknown category '{category}' — passed through (strict_mode=False)",
            }

        if not tasks:
            return {
                "valid": True,
                "hard_fails": [],
                "human_reviews": [],
                "mandatory_acknowledgments": [],
                "sequence_validated": True,
                "cse_overlap": "none",
                "note": "Empty task list",
            }

        cse_overlap = self._detect_cse_overlap(tasks)

        # Map each node to its position in the task list
        node_positions: dict[str, tuple[int, float]] = {}
        node_evidence: dict[str, str] = {}
        for node in rules.nodes:
            pos, conf = self._find_node_position(tasks, node)
            node_positions[node.id] = (pos, conf)
            if pos >= 0:
                node_evidence[node.id] = tasks[pos].get("task", "")[:100]

        hard_fails: list[dict] = []
        human_reviews: list[dict] = []
        mandatory_acks: list[str] = []

        for node in rules.nodes:
            pos, conf = node_positions[node.id]

            # Skip conditional nodes when condition not met
            if node.condition == "cse_overlap" and cse_overlap == "none":
                continue

            # Determine required predecessors
            required = list(node.predecessors)
            if node.predecessors_always:
                required.extend(node.predecessors_always)
            if node.predecessors_if_cse and cse_overlap != "none":
                required.extend(node.predecessors_if_cse)

            # Check for missing predecessors (node found but predecessor absent or after)
            if pos >= 0 and required:
                missing = []
                for pred_id in required:
                    pred_pos, _ = node_positions.get(pred_id, (-1, 0.0))
                    if pred_pos < 0 or pred_pos >= pos:
                        missing.append(pred_id)

                if missing:
                    tier = self._confidence_tier(conf)
                    evidence = node_evidence.get(node.id, "")
                    reasoning = self._build_reasoning(node, pos, missing, evidence)

                    finding = {
                        "node_id": node.id,
                        "violation_type": node.violation_type,
                        "detected_at_task": pos,
                        "missing_predecessors": missing,
                        "raw_evidence": evidence,
                        "mapping_confidence": round(conf, 2),
                        "confidence_tier": tier,
                        "reasoning": reasoning,
                    }

                    if node.violation_type == "HARD_FAIL":
                        hard_fails.append(finding)
                    else:
                        finding["mandatory_acknowledgment"] = node.mandatory_acknowledgment
                        human_reviews.append(finding)

            # Check for absent nodes that have mandatory_acknowledgment
            if pos < 0 and node.mandatory_acknowledgment:
                if node.violation_type == "HUMAN_REVIEW":
                    human_reviews.append({
                        "node_id": node.id,
                        "violation_type": "HUMAN_REVIEW",
                        "detected_at_task": -1,
                        "missing_predecessors": [],
                        "raw_evidence": "",
                        "mapping_confidence": 0.0,
                        "confidence_tier": self._confidence_tier(0.0),
                        "mandatory_acknowledgment": node.mandatory_acknowledgment,
                        "reasoning": f"Node '{node.id}' not found in task list — acknowledgment required.",
                    })

            if node.mandatory_acknowledgment and (
                pos < 0 or any(hr.get("node_id") == node.id for hr in human_reviews)
            ):
                mandatory_acks.append(node.mandatory_acknowledgment)

        # Atmospheric control check for CSE
        if cse_overlap != "none":
            missing_atm = self._check_atmospheric_controls(tasks)
            for missing_ctrl in missing_atm:
                severity = "HARD_FAIL" if cse_overlap == "explicit" else "HUMAN_REVIEW"
                finding = {
                    "node_id": "atmospheric_minimum_control",
                    "violation_type": severity,
                    "detected_at_task": -1,
                    "missing_predecessors": [],
                    "raw_evidence": f"Missing: {missing_ctrl}",
                    "mapping_confidence": 0.9,
                    "confidence_tier": self._confidence_tier(0.9),
                    "reasoning": f"Atmospheric minimum control '{missing_ctrl}' not found. CSE overlap: {cse_overlap}.",
                }
                if severity == "HARD_FAIL":
                    hard_fails.append(finding)
                else:
                    human_reviews.append(finding)

        # Deduplicate mandatory_acks
        mandatory_acks = list(dict.fromkeys(mandatory_acks))

        return {
            "valid": len(hard_fails) == 0,
            "hard_fails": hard_fails,
            "human_reviews": human_reviews,
            "mandatory_acknowledgments": mandatory_acks,
            "sequence_validated": True,
            "cse_overlap": cse_overlap,
            "note": None,
        }

    def _confidence_tier(self, score: float) -> str:
        if score >= 0.85:
            return "High confidence"
        elif score >= 0.65:
            return "Medium confidence"
        return "Low confidence — manual verification essential"

    def _detect_cse_overlap(self, tasks: list[dict]) -> str:
        all_text = " ".join(t.get("task", "") + " " + " ".join(t.get("controls", [])) for t in tasks).lower()
        rules = self.rules
        if any(kw in all_text for kw in rules.cse_explicit_keywords):
            return "explicit"
        if any(kw in all_text for kw in rules.cse_ambiguous_indicators):
            return "ambiguous"
        return "none"

    def _match_node(self, task: dict, node) -> tuple[bool, float]:
        task_text = (task.get("task", "") + " " + " ".join(task.get("controls", []))).lower()
        best_conf = 0.0
        matched = False
        for kw in node.keywords:
            kw_lower = kw.lower()
            if kw_lower in task_text:
                matched = True
                # Exact phrase match
                if len(kw_lower) > 10:
                    best_conf = max(best_conf, 0.95)
                elif len(kw_lower) > 4:
                    best_conf = max(best_conf, 0.75)
                else:
                    best_conf = max(best_conf, 0.65)
        return (matched, best_conf)

    def _check_atmospheric_controls(self, tasks: list[dict]) -> list[str]:
        all_text = " ".join(
            t.get("task", "") + " " + " ".join(t.get("controls", []))
            for t in tasks
        ).lower()
        missing = []
        for ctrl in self.rules.atmospheric_minimum_controls:
            if ctrl.lower() not in all_text:
                missing.append(ctrl)
        return missing

    def _find_node_position(self, tasks: list[dict], node) -> tuple[int, float]:
        for i, task in enumerate(tasks):
            matched, conf = self._match_node(task, node)
            if matched:
                return (i, conf)
        return (-1, 0.0)

    def _build_reasoning(self, node, detected_at: int, missing: list[str], evidence: str) -> str:
        return (
            f"Node '{node.id}' detected at task {detected_at} "
            f"(evidence: '{evidence}'). "
            f"Missing predecessors: {missing}. "
            f"Violation: {node.violation_type}."
        )

    def _safe_fallback(self, error_msg: str = "") -> dict:
        return {
            "valid": False,
            "hard_fails": [],
            "human_reviews": [],
            "mandatory_acknowledgments": [],
            "sequence_validated": False,
            "cse_overlap": "none",
            "note": f"Validation error: {error_msg}" if error_msg else "Validation error",
        }

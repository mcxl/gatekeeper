"""
tests/test_excavation_dag.py — Tests for excavation DAG sequence validator.
"""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.sequence_validator import SequenceValidator
from core.models.dag import DagRules, load_dag_rules

_RULES_PATH = str(Path(__file__).parent.parent / "core" / "dag_rules" / "excavation.json")


def _sv() -> SequenceValidator:
    return SequenceValidator(_RULES_PATH, strict_mode=False)


def _task(name: str, controls: list[str] | None = None) -> dict:
    return {"task": name, "controls": controls or []}


# ── Basic sequence checks ───────────────────────────────────────────────────

class TestBasicSequence:
    def test_byda_and_service_locating_present_pass(self):
        tasks = [
            _task("Obtain BYDA before you dig clearance"),
            _task("Service locating and pothole verification"),
            _task("Obtain permit before excavation"),
            _task("Excavation of trench"),
            _task("Install shoring"),
        ]
        result = _sv().validate(tasks, "excavation")
        assert result["sequence_validated"]
        # BYDA and service_locating present and in order
        byda_fails = [f for f in result["hard_fails"] if f["node_id"] == "byda_clearance"]
        assert len(byda_fails) == 0

    def test_byda_present_service_locating_absent_hard_fail(self):
        tasks = [
            _task("Obtain BYDA before you dig clearance"),
            _task("Excavation of trench"),  # no service locating before excavation
        ]
        result = _sv().validate(tasks, "excavation")
        # excavation_permit or mechanical_excavation should fail for missing predecessors
        hf_nodes = [f["node_id"] for f in result["hard_fails"]]
        assert len(result["hard_fails"]) > 0

    def test_trench_entry_before_shoring_hard_fail(self):
        tasks = [
            _task("BYDA before you dig clearance"),
            _task("Service locating and pothole"),
            _task("Obtain permit before excavation"),
            _task("Workers enter trench to lay pipes"),
            _task("Install shoring"),
        ]
        result = _sv().validate(tasks, "excavation")
        entry_fails = [f for f in result["hard_fails"] if f["node_id"] == "trench_entry"]
        assert len(entry_fails) > 0

    def test_trench_entry_after_shoring_pass(self):
        tasks = [
            _task("BYDA before you dig clearance"),
            _task("Service locating and pothole"),
            _task("Obtain permit before excavation"),
            _task("Excavation of trench"),
            _task("Install shoring and trench shield"),
            _task("Workers enter trench to lay pipes"),
        ]
        result = _sv().validate(tasks, "excavation")
        entry_fails = [f for f in result["hard_fails"] if f["node_id"] == "trench_entry"]
        assert len(entry_fails) == 0


# ── CSE overlap ─────────────────────────────────────────────────────────────

class TestCSEOverlap:
    def test_explicit_cse_no_atmospheric_hard_fail(self):
        tasks = [
            _task("BYDA before you dig clearance"),
            _task("Service locating and pothole"),
            _task("Obtain permit before excavation"),
            _task("Excavation of trench near manhole"),
            _task("Install shoring"),
            _task("Enter trench confined space"),
        ]
        result = _sv().validate(tasks, "excavation")
        assert result["cse_overlap"] == "explicit"
        atm_fails = [f for f in result["hard_fails"]
                      if "atmospheric" in f.get("node_id", "") or "atmospheric" in f.get("raw_evidence", "").lower()]
        assert len(atm_fails) > 0

    def test_explicit_cse_all_3_controls_pass(self):
        tasks = [
            _task("BYDA before you dig clearance"),
            _task("Service locating and pothole"),
            _task("Obtain permit before excavation"),
            _task("Excavation of trench near manhole"),
            _task("Install shoring"),
            _task("Atmospheric monitoring with gas detector", ["continuous monitor oxygen LEL", "rescue plan"]),
            _task("Enter trench confined space"),
        ]
        result = _sv().validate(tasks, "excavation")
        atm_fails = [f for f in result["hard_fails"]
                      if "atmospheric" in f.get("node_id", "")]
        assert len(atm_fails) == 0


# ── Competent person ────────────────────────────────────────────────────────

class TestCompetentPerson:
    def test_competent_person_absent_human_review(self):
        tasks = [
            _task("BYDA before you dig clearance"),
            _task("Service locating and pothole"),
            _task("Obtain permit before excavation"),
            _task("Excavation of trench"),
            _task("Install shoring"),
        ]
        result = _sv().validate(tasks, "excavation")
        hr_nodes = [f["node_id"] for f in result["human_reviews"]]
        assert "competent_person_signoff" in hr_nodes

    def test_mandatory_acknowledgment_populated(self):
        tasks = [
            _task("BYDA before you dig clearance"),
            _task("Service locating"),
            _task("Obtain permit before excavation"),
            _task("Excavation of trench"),
            _task("Install shoring"),
        ]
        result = _sv().validate(tasks, "excavation")
        assert len(result["mandatory_acknowledgments"]) > 0
        assert "competent person" in result["mandatory_acknowledgments"][0].lower()


# ── Unknown category and edge cases ─────────────────────────────────────────

class TestEdgeCases:
    def test_unknown_category_strict_false_pass(self):
        tasks = [_task("Some task")]
        result = _sv().validate(tasks, "plumbing")
        assert result["valid"] is True
        assert result["sequence_validated"] is False

    def test_empty_task_list(self):
        result = _sv().validate([], "excavation")
        assert result["valid"] is True
        assert len(result["hard_fails"]) == 0

    def test_malformed_json_path_never_raises(self):
        sv = SequenceValidator("/nonexistent/path.json")
        result = sv.validate([_task("test")], "excavation")
        assert result["sequence_validated"] is False


# ── Confidence tiers ────────────────────────────────────────────────────────

class TestConfidenceTiers:
    def test_high_confidence(self):
        assert _sv()._confidence_tier(0.95) == "High confidence"

    def test_medium_confidence(self):
        assert _sv()._confidence_tier(0.75) == "Medium confidence"

    def test_low_confidence(self):
        tier = _sv()._confidence_tier(0.60)
        assert "Low confidence" in tier
        assert "manual verification" in tier


# ── Reasoning trace ─────────────────────────────────────────────────────────

class TestReasoningTrace:
    def test_reasoning_contains_node_id_and_evidence(self):
        tasks = [
            _task("Excavation of trench"),  # no predecessors
        ]
        result = _sv().validate(tasks, "excavation")
        if result["hard_fails"]:
            hf = result["hard_fails"][0]
            assert "node_id" in hf
            assert "raw_evidence" in hf or "reasoning" in hf
            assert "missing_predecessors" in hf


# ── Pydantic schema validation ──────────────────────────────────────────────

class TestPydanticValidation:
    def test_valid_json_loads(self):
        rules = load_dag_rules(_RULES_PATH)
        assert rules.category == "excavation"
        assert len(rules.nodes) >= 8

    def test_invalid_json_rejects(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text('{"category": "test", "nodes": [{"id": "x"}]}')
        with pytest.raises(Exception):
            load_dag_rules(str(bad))

    def test_missing_violation_type_rejects(self, tmp_path):
        bad = tmp_path / "bad2.json"
        bad.write_text(json.dumps({
            "category": "test",
            "nodes": [{"id": "x", "keywords": ["y"]}]
        }))
        with pytest.raises(Exception):
            load_dag_rules(str(bad))

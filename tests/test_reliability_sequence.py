"""
Tests for Agent 3 reliability (extract_json) and task sequence ordering.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.utils import extract_json
from core.orchestrator import _reorder_tasks, _task_phase_score


# ── extract_json ─────────────────────────────────────────────────────────────

class TestExtractJson:
    def test_clean_json(self):
        assert extract_json('{"a": 1}') == {"a": 1}

    def test_json_with_trailing_commentary(self):
        text = '{"a": 1}\n\nHere is a summary of what I did...'
        assert extract_json(text) == {"a": 1}

    def test_json_array_with_trailing_text(self):
        text = '[{"task": "paint"}]\n\nNote: I included...'
        result = extract_json(text)
        assert isinstance(result, list)
        assert result[0]["task"] == "paint"

    def test_json_with_markdown_fences(self):
        text = '```json\n{"a": 1}\n```'
        assert extract_json(text) == {"a": 1}

    def test_json_with_leading_text(self):
        text = 'Here is the result:\n{"task": "repair"}'
        assert extract_json(text) == {"task": "repair"}

    def test_no_json_raises(self):
        with pytest.raises(ValueError, match="No valid JSON"):
            extract_json("This is just plain text with no JSON")

    def test_nested_json(self):
        text = '{"controls": [{"item": "harness"}]}\nDone.'
        result = extract_json(text)
        assert result["controls"][0]["item"] == "harness"


# ── Task sequence ordering ───────────────────────────────────────────────────

class TestTaskSequenceOrdering:
    def test_setup_comes_first(self):
        tasks = [
            {"task": "Paint exterior masonry", "scope": "painting"},
            {"task": "Establish site and plan access", "scope": "setup"},
        ]
        result = _reorder_tasks(tasks)
        assert "Establish" in result[0]["task"]
        assert "Paint" in result[1]["task"]

    def test_demob_comes_last(self):
        tasks = [
            {"task": "Demobilise and remove scaffold", "scope": ""},
            {"task": "Crack stitching repairs", "scope": "concrete"},
            {"task": "Mobilise and establish site", "scope": "setup"},
        ]
        result = _reorder_tasks(tasks)
        assert "Mobilise" in result[0]["task"]
        assert "Crack" in result[1]["task"]
        assert "Demobilise" in result[2]["task"]

    def test_repairs_before_painting(self):
        tasks = [
            {"task": "Paint exterior masonry", "scope": "painting"},
            {"task": "Repoint brickwork", "scope": "brick repair"},
        ]
        result = _reorder_tasks(tasks)
        assert "Repoint" in result[0]["task"]
        assert "Paint" in result[1]["task"]

    def test_renumbers_steps(self):
        tasks = [
            {"task": "Paint", "scope": "", "step": "1.5"},
            {"task": "Establish site", "scope": "setup", "step": "1.3"},
        ]
        result = _reorder_tasks(tasks)
        assert result[0]["step"] == "1.1"
        assert result[1]["step"] == "1.2"

    def test_qa_before_demob(self):
        tasks = [
            {"task": "Demobilise site", "scope": ""},
            {"task": "check work and fix defects", "scope": "qa"},
        ]
        result = _reorder_tasks(tasks)
        assert "check" in result[0]["task"]
        assert "Demobilise" in result[1]["task"]

    def test_full_sequence(self):
        tasks = [
            {"task": "Demobilise", "scope": ""},
            {"task": "Paint masonry", "scope": ""},
            {"task": "check defects", "scope": ""},
            {"task": "Establish site", "scope": "setup"},
            {"task": "Erect scaffold", "scope": ""},
            {"task": "Crack stitching", "scope": "repair"},
            {"task": "Remove green wall", "scope": ""},
            {"task": "Apply sealant", "scope": ""},
            {"task": "Reinstate green wall", "scope": ""},
        ]
        result = _reorder_tasks(tasks)
        names = [t["task"] for t in result]
        # Setup first
        assert names[0] == "Establish site"
        # Scaffold second
        assert names[1] == "Erect scaffold"
        # Removal third
        assert names[2] == "Remove green wall"
        # Repairs fourth
        assert names[3] == "Crack stitching"
        # Sealant fifth
        assert names[4] == "Apply sealant"
        # Painting sixth
        assert names[5] == "Paint masonry"
        # Reinstatement seventh
        assert names[6] == "Reinstate green wall"
        # QA eighth
        assert names[7] == "check defects"
        # Demob last
        assert names[8] == "Demobilise"

    def test_empty_list(self):
        assert _reorder_tasks([]) == []

    def test_single_task(self):
        tasks = [{"task": "Paint", "scope": ""}]
        result = _reorder_tasks(tasks)
        assert result[0]["step"] == "1.1"

    def test_phase_score_setup(self):
        assert _task_phase_score({"task": "Establish site", "scope": ""}) == 0

    def test_phase_score_painting(self):
        assert _task_phase_score({"task": "Paint exterior", "scope": ""}) == 5

    def test_phase_score_demob(self):
        assert _task_phase_score({"task": "Demobilise site", "scope": ""}) == 8

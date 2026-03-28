"""
Tests for post-expert-review refinement: demolition stripping, waterproofing fix,
issue-gate hardening, and interface controls injection.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from renderers.docx_renderer import sanitise_text
from core.orchestrator import (
    _fix_unsupported_waterproofing,
    _inject_interface_controls,
)


# ── Sanitise: ?? artifact stripping ──────────────────────────────────────────

class TestArtifactStripping:
    def test_double_question_mark_stripped(self):
        assert "STOP WORK" in sanitise_text("?? STOP WORK if: condition")
        assert not sanitise_text("?? STOP WORK").startswith("??")

    def test_normal_text_unchanged(self):
        assert sanitise_text("Normal control text") == "Normal control text"

    def test_question_mark_in_middle_preserved(self):
        result = sanitise_text("Is PPE required? Yes")
        assert "?" in result


# ── Waterproofing wording fix ────────────────────────────────────────────────

class TestWaterproofingFix:
    def test_waterproofing_replaced_when_scope_has_sealant(self):
        tb = {"task": "Apply sealants and waterproofing",
              "scope": "recaulking and silane clear sealer application"}
        _fix_unsupported_waterproofing(tb)
        assert "waterproof" not in tb["task"].lower()
        assert "sealer" in tb["task"].lower()

    def test_waterproofing_preserved_when_scope_is_waterproofing(self):
        tb = {"task": "Apply waterproofing membrane",
              "scope": "waterproofing to balcony areas"}
        _fix_unsupported_waterproofing(tb)
        assert "waterproof" in tb["task"].lower()

    def test_no_waterproofing_in_task_unchanged(self):
        tb = {"task": "Paint exterior masonry", "scope": "painting works"}
        _fix_unsupported_waterproofing(tb)
        assert tb["task"] == "Paint exterior masonry"


# ── Interface controls injection ─────────────────────────────────────────────

class TestInterfaceControls:
    def _make_tb(self, task_name="Establish site and plan access"):
        return {"task": task_name, "controls": [], "admin": [], "scope": ""}

    def _inference_occupied(self):
        return {"swms_classification": {"occupancy_context": "occupied"}}

    def test_interface_controls_injected_for_setup_task(self):
        tb = self._make_tb()
        _inject_interface_controls(tb, self._inference_occupied())
        admin_text = " ".join(tb["admin"]).lower()
        assert "resident" in admin_text
        assert "parking" in admin_text
        assert "vegetation" in admin_text

    def test_interface_controls_not_injected_for_non_setup_task(self):
        tb = self._make_tb("Paint exterior masonry and render")
        _inject_interface_controls(tb, self._inference_occupied())
        assert len(tb["admin"]) == 0

    def test_interface_controls_not_injected_for_unoccupied(self):
        tb = self._make_tb()
        _inject_interface_controls(tb, {"swms_classification": {}})
        assert len(tb["admin"]) == 0

    def test_no_duplicate_injection(self):
        tb = self._make_tb()
        inf = self._inference_occupied()
        _inject_interface_controls(tb, inf)
        count_before = len(tb["admin"])
        _inject_interface_controls(tb, inf)
        assert len(tb["admin"]) == count_before

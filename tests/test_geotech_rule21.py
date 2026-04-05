"""
tests/test_geotech_rule21.py — Tests for Rule 21: Geotech Trigger.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.validate import check_21_geotech_trigger
from core.schema import TaskBlock


def _task(
    task: str = "Excavation",
    scope: str = "",
    hazards: list[str] | None = None,
    controls: list[str] | None = None,
    admin: list[str] | None = None,
    **kwargs,
) -> TaskBlock:
    return TaskBlock(
        task=task,
        scope=scope,
        hazards=hazards or [],
        risk_pre="H",
        risk_post="L",
        controls=controls or [],
        admin=admin or [],
        hold_points=[],
        stop_work=[],
        ppe=[],
        responsibility={"SUP": "Foreman"},
        **kwargs,
    )


class TestGeotech:
    def test_excavation_with_geotech_pass(self):
        """Excavation >= 1.5m with geotech citation → PASS."""
        t = _task(
            task="Excavation of trench 2m deep near services",
            controls=["Geotechnical soil report obtained before excavation"],
        )
        assert check_21_geotech_trigger(t) == "PASS"

    def test_excavation_without_geotech_fail(self):
        """Excavation >= 1.5m without geotech citation → FAIL."""
        t = _task(
            task="Excavation of trench 2m deep near services",
            controls=["Install shoring before entry"],
        )
        assert check_21_geotech_trigger(t) == "FAIL"

    def test_shallow_excavation_skip(self):
        """Excavation < 1.5m → SKIP (not applicable)."""
        t = _task(
            task="Excavation of shallow trench 1.0m deep",
            controls=["Hand dig only"],
        )
        assert check_21_geotech_trigger(t) == "SKIP"

    def test_no_excavation_skip(self):
        """Non-excavation task → SKIP."""
        t = _task(
            task="Install scaffold to level 3",
            controls=["Edge protection before access"],
        )
        assert check_21_geotech_trigger(t) == "SKIP"

    def test_no_depth_no_shoring_skip(self):
        """Excavation task with no depth AND no shoring keywords → SKIP."""
        t = _task(
            task="Excavation of trench",
            controls=["Hand dig carefully"],
        )
        assert check_21_geotech_trigger(t) == "SKIP"

    def test_depth_in_scope_triggers(self):
        """Depth in scope text triggers check."""
        t = _task(
            task="Trench excavation",
            scope="Excavate to 2.5m depth for foundation",
            controls=["Install shoring"],
        )
        assert check_21_geotech_trigger(t) == "FAIL"

    def test_depth_in_scope_with_geotech_pass(self):
        t = _task(
            task="Trench excavation",
            scope="Excavate to 2.5m depth for foundation",
            controls=["Geotechnical assessment reviewed before dig"],
        )
        assert check_21_geotech_trigger(t) == "PASS"

    def test_geotech_in_admin_pass(self):
        """Geotech term in admin field is sufficient."""
        t = _task(
            task="Excavation of trench 3m deep",
            admin=["Obtain soil report before excavation commences"],
        )
        assert check_21_geotech_trigger(t) == "PASS"

    def test_foundation_report_pass(self):
        t = _task(
            task="Excavation of trench 1.5m deep",
            controls=["Foundation report reviewed and approved"],
        )
        assert check_21_geotech_trigger(t) == "PASS"

    def test_exactly_1_5m_triggers(self):
        """Exactly 1.5m should trigger the check."""
        t = _task(
            task="Excavation to 1.5m depth",
            controls=["Install shoring"],
        )
        assert check_21_geotech_trigger(t) == "FAIL"

    def test_deferred_citation_fails(self):
        """'Geotechnical report TBA' is vague — should FAIL."""
        t = _task(
            task="Excavation of trench 2m deep",
            controls=["Geotechnical report TBA"],
        )
        assert check_21_geotech_trigger(t) == "FAIL"

    def test_inferred_depth_from_shoring(self):
        """Shoring present without explicit depth → infer >= 1.5m → FAIL."""
        t = _task(
            task="Excavation of trench with shoring",
            controls=["Install trench shield"],
        )
        assert check_21_geotech_trigger(t) == "FAIL"

    def test_stable_rock_without_authority_fails(self):
        """'Stable rock — no shoring required' without CPEng/NPER → FAIL_STABLE_ROCK."""
        t = _task(
            task="Excavation to 2m in stable rock — no shoring required",
            controls=["Visual inspection daily"],
        )
        assert check_21_geotech_trigger(t) == "FAIL_STABLE_ROCK"

    def test_stable_rock_with_cpeng_passes(self):
        """Stable rock with CPEng authority → PASS."""
        t = _task(
            task="Excavation to 2m in stable rock — no shoring required",
            controls=["CPEng geotechnical engineer sign-off obtained"],
        )
        assert check_21_geotech_trigger(t) == "PASS"

    def test_score_task_includes_rule21(self):
        """score_task integrates Rule 21 — FAIL appears in errors."""
        from core.validate import score_task
        t = _task(
            task="Excavation of trench 2m deep",
            controls=["Install shoring before entry"],
        )
        result = score_task(t)
        rule21_errors = [e for e in result.errors if "Rule 21" in e]
        assert len(rule21_errors) == 1

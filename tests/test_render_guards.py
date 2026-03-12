"""
Tests for pre-render guard functions in core/validate.py.

T4 — Render guards
  • guard_tasks forces wah_applicable=False when ccvs_code does not start with 'WAH'.
  • guard_tasks caps admin controls at MAX_ADMIN items.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.validate import guard_tasks, MAX_ADMIN


# ── T4-A: wah_applicable corrected for ELE-H6 task ───────────────────────────

def test_guard_wah_corrected_to_false_for_ele_task():
    """wah_applicable=True on an ELE-H6 task must be forced to False by guard_tasks."""
    tasks = [
        {
            "task": "Electrical isolation",
            "ccvs_code": "ELE-H6",
            "wah_applicable": True,  # incorrectly set
            "admin": [],
        }
    ]

    result = guard_tasks(tasks)

    assert result[0]["wah_applicable"] is False, (
        f"Expected wah_applicable=False for ELE-H6, got {result[0]['wah_applicable']}"
    )


def test_guard_wah_preserved_for_wah_task():
    """wah_applicable=True on a WAH-H6 task must NOT be overridden."""
    tasks = [
        {
            "task": "Working at height on scaffold",
            "ccvs_code": "WAH-H6",
            "wah_applicable": True,
            "admin": [],
        }
    ]

    result = guard_tasks(tasks)

    assert result[0]["wah_applicable"] is True, (
        "wah_applicable=True should be preserved for a WAH ccvs_code"
    )


# ── T4-B: admin capped at MAX_ADMIN ──────────────────────────────────────────

def test_guard_admin_capped_at_max():
    """admin controls list longer than MAX_ADMIN is truncated to MAX_ADMIN items."""
    excess = MAX_ADMIN + 5  # e.g. 25 if MAX_ADMIN=20
    tasks = [
        {
            "task": "Some task",
            "ccvs_code": "N/A",
            "wah_applicable": False,
            "admin": [f"Admin control {i}" for i in range(excess)],
        }
    ]

    result = guard_tasks(tasks)

    assert len(result[0]["admin"]) == MAX_ADMIN, (
        f"Expected admin capped at {MAX_ADMIN}, got {len(result[0]['admin'])}"
    )


def test_guard_admin_under_max_unchanged():
    """admin controls list shorter than MAX_ADMIN is left unchanged."""
    tasks = [
        {
            "task": "Some task",
            "ccvs_code": "N/A",
            "wah_applicable": False,
            "admin": ["Control A", "Control B"],
        }
    ]

    result = guard_tasks(tasks)

    assert len(result[0]["admin"]) == 2


# ── T4-C: guard_tasks works on TaskBlock objects too ─────────────────────────

def test_guard_works_on_taskblock_objects():
    """guard_tasks correctly handles TaskBlock instances (not just dicts)."""
    from core.schema import TaskBlock

    task = TaskBlock(
        task="Structural repairs",
        scope="Crack stitching on Level 2",
        risk_pre="High-6",
        risk_post="Low-1",
        ccvs_code="STR-H6",
        wah_applicable=True,  # wrong — STR is not WAH
        controls=["Inspect crack before repair"],
        hold_points=["Verify engineer sign-off", "Confirm grout is approved"],
        stop_work=["Stop if crack widens", "Stop if movement detected"],
        ppe=["Hard hat and boots"],
        admin=[f"Admin item {i}" for i in range(MAX_ADMIN + 3)],
        responsibility={"SUP": "Oversee structural works"},
    )

    result = guard_tasks([task])

    assert result[0].wah_applicable is False
    assert len(result[0].admin) == MAX_ADMIN

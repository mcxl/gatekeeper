"""
Tests for stream-parity post-processing.

T2 — Stream parity
  • ccvs_code 'WAHH6' (no hyphen) is normalised to a valid pattern by _normalise_task.
  • Risk labels are enriched from letter grades to 'Label(score)' format.
  • _suppress_false_ccvs_single suppresses HOT-H6 on a plain painting task.
  • _hot_work_legitimate returns False for empty inference, True for hot-work inference.
"""

import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

CCVS_PATTERN = re.compile(r"^(N/A|[A-Z]{2,3}-[HML]\d)$")
RISK_PATTERN = re.compile(r"^(High|Medium|Low)\(\d+\)$")


# ── T2-A: ccvs_code repair ────────────────────────────────────────────────────

def test_normalise_task_repairs_malformed_ccvs():
    """A bare 'WAHH6' ccvs_code is repaired to N/A or a valid hyphenated code."""
    from core.orchestrator import _normalise_task

    tb = {
        "task": "Scaffold erection",
        "scope": "Level 3 facade access",
        "risk_pre": "H",
        "risk_post": "L",
        "ccvs_code": "WAHH6",
        "controls": ["Inspect scaffold before use"],
        "admin": [],
        "hold_points": [],
        "stop_work": [],
        "ppe": ["Hard hat"],
        "hazards": [],
    }

    result = _normalise_task(tb, inference={}, jurisdiction="AU", hot_work_ok=False)
    assert CCVS_PATTERN.match(result["ccvs_code"]), (
        f"ccvs_code '{result['ccvs_code']}' does not match {CCVS_PATTERN.pattern}"
    )


# ── T2-B: risk label enrichment ───────────────────────────────────────────────

def test_enrich_risk_labels_h_grade():
    """Letter grade 'H' is enriched to 'High(N)' matching the expected pattern."""
    from core.orchestrator import _enrich_risk_labels

    tb = {"risk_pre": "H", "risk_post": "L"}
    _enrich_risk_labels(tb)

    assert RISK_PATTERN.match(tb["risk_pre"]), (
        f"risk_pre '{tb['risk_pre']}' does not match {RISK_PATTERN.pattern}"
    )
    assert RISK_PATTERN.match(tb["risk_post"]), (
        f"risk_post '{tb['risk_post']}' does not match {RISK_PATTERN.pattern}"
    )


def test_enrich_risk_labels_already_enriched_unchanged():
    """A label already in 'High(6)' format is not double-enriched."""
    from core.orchestrator import _enrich_risk_labels

    tb = {"risk_pre": "High(6)", "risk_post": "Low(2)"}
    _enrich_risk_labels(tb)

    assert tb["risk_pre"] == "High(6)"
    assert tb["risk_post"] == "Low(2)"


# ── T2-C: _suppress_false_ccvs_single ────────────────────────────────────────

def test_suppress_false_ccvs_painting_task():
    """HOT-H6 ccvs_code on a plain painting task with no hot-work inference → N/A."""
    from core.orchestrator import _suppress_false_ccvs_single

    tb = {
        "task": "Painting exterior cladding panels",
        "scope": "Acrylic paint application on Level 4 west elevation",
        "ccvs_code": "HOT-H6",
        "controls": ["Apply paint using roller"],
        "admin": [],
        "hold_points": [],
        "stop_work": [],
    }

    _suppress_false_ccvs_single(tb, hot_work_legitimate=False)

    assert tb["ccvs_code"] == "N/A", (
        f"Expected ccvs_code 'N/A', got '{tb['ccvs_code']}'"
    )


def test_suppress_false_ccvs_preserves_legitimate_hot_work():
    """HOT-H6 on a real welding task is NOT suppressed when hot_work_legitimate=True."""
    from core.orchestrator import _suppress_false_ccvs_single

    tb = {
        "task": "Welding structural brackets",
        "scope": "Hot work on Level 2 steel frame",
        "ccvs_code": "HOT-H6",
        "controls": ["Obtain hot work permit before commencing"],
        "admin": [],
        "hold_points": [],
        "stop_work": [],
    }

    _suppress_false_ccvs_single(tb, hot_work_legitimate=True)

    assert tb["ccvs_code"] == "HOT-H6", (
        f"Expected ccvs_code 'HOT-H6' preserved, got '{tb['ccvs_code']}'"
    )


# ── T2-D: _hot_work_legitimate ────────────────────────────────────────────────

def test_hot_work_legitimate_empty_dict_returns_false():
    """Empty inference dict → _hot_work_legitimate returns False."""
    from core.orchestrator import _hot_work_legitimate

    assert _hot_work_legitimate({}) is False


def test_hot_work_legitimate_with_hot_work_permit_returns_true():
    """Inference containing 'hot work' keyword → _hot_work_legitimate returns True."""
    from core.orchestrator import _hot_work_legitimate

    inference = {
        "permits": ["hot work permit", "confined space entry permit"],
        "hrcw": True,
    }
    assert _hot_work_legitimate(inference) is True


def test_hot_work_legitimate_with_welding_returns_true():
    """Inference containing 'welding' → _hot_work_legitimate returns True."""
    from core.orchestrator import _hot_work_legitimate

    inference = {"activities": ["welding", "grinding"], "hrcw": True}
    assert _hot_work_legitimate(inference) is True


# ── T2-E: hrcw boolean correction from hrcw_category ─────────────────────────

def test_hrcw_corrected_when_category_cl2():
    """hrcw_category containing cl.2 forces hrcw=true even if originally false."""
    from core.orchestrator import _normalise_task

    tb = {
        "task": "Remove existing membrane",
        "scope": "Balcony waterproofing removal",
        "risk_pre": "H", "risk_post": "M",
        "ccvs_code": "SIL-H6",
        "hrcw": False,
        "hrcw_category": "SIL-H6-cl.2",
        "controls": ["Wet suppression"], "admin": [],
        "hold_points": [], "stop_work": [],
        "ppe": ["P2 mask"], "hazards": ["Silica dust"],
    }
    result = _normalise_task(tb, inference={}, jurisdiction="AU", hot_work_ok=False)
    assert result["hrcw"] is True


def test_hrcw_unchanged_when_category_no_class():
    """hrcw_category without cl.1/cl.2 does not force hrcw=true."""
    from core.orchestrator import _normalise_task

    tb = {
        "task": "Site establishment",
        "scope": "General setup",
        "risk_pre": "M", "risk_post": "L",
        "ccvs_code": "SYS-M3",
        "hrcw": False,
        "hrcw_category": "WAH-H4",
        "controls": ["Induction"], "admin": [],
        "hold_points": [], "stop_work": [],
        "ppe": ["Hard hat"], "hazards": ["Trip"],
    }
    result = _normalise_task(tb, inference={}, jurisdiction="AU", hot_work_ok=False)
    assert result["hrcw"] is False


def test_hrcw_unchanged_when_category_empty():
    """Empty hrcw_category does not change hrcw."""
    from core.orchestrator import _normalise_task

    tb = {
        "task": "Clean up",
        "scope": "General",
        "risk_pre": "L", "risk_post": "L",
        "ccvs_code": "N/A",
        "hrcw": False,
        "hrcw_category": "",
        "controls": ["Sweep area"], "admin": [],
        "hold_points": [], "stop_work": [],
        "ppe": [], "hazards": [],
    }
    result = _normalise_task(tb, inference={}, jurisdiction="AU", hot_work_ok=False)
    assert result["hrcw"] is False

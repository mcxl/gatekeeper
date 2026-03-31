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


# ── T2-B1.5: _task_phase_score — isolate/barricade tasks ─────────────────────

def test_isolate_task_phases_before_scaffold():
    """Isolate/barricade tasks should get phase 0 (before scaffold at 1)."""
    from core.orchestrator import _task_phase_score

    tb_isolate = {"task": "Isolate and barricade work areas", "scope": ""}
    tb_scaffold = {"task": "Erect scaffold to balconies", "scope": ""}
    assert _task_phase_score(tb_isolate) < _task_phase_score(tb_scaffold)


def test_barricade_task_phases_before_scaffold():
    from core.orchestrator import _task_phase_score

    tb_barricade = {"task": "Barricade balconies and common areas", "scope": ""}
    tb_scaffold = {"task": "Erect scaffold via courtyard", "scope": ""}
    assert _task_phase_score(tb_barricade) < _task_phase_score(tb_scaffold)


def test_exclusion_zone_phases_before_scaffold():
    from core.orchestrator import _task_phase_score

    tb_excl = {"task": "Set up exclusion zone around building", "scope": ""}
    assert _task_phase_score(tb_excl) == 0


def test_isolate_in_scope_does_not_trigger_phase_zero():
    """'isolate' in scope text (e.g. 'isolate work area') should not force phase 0."""
    from core.orchestrator import _task_phase_score

    tb = {"task": "Remove existing waterproofing", "scope": "isolate work area from occupied spaces"}
    # Should NOT be phase 0 — 'isolate' is a control within the task, not a standalone task
    assert _task_phase_score(tb) != 0


# ── T2-B1.6: _strip_generator_artefacts ─────────────────────────────────────

def test_strip_wah_licence_boilerplate():
    from core.orchestrator import _strip_generator_artefacts
    tb = {"ccvs_code": "WAH-H6", "controls": [
        "Install edge protection along balcony perimeter",
        "Working at heights licence verified for all workers",
        "Wear full body harness",
    ], "admin": [], "hold_points": [], "stop_work": [], "ppe": []}
    _strip_generator_artefacts(tb)
    assert len(tb["controls"]) == 2
    assert "licence" not in " ".join(tb["controls"]).lower()


def test_strip_anchor_6kn():
    from core.orchestrator import _strip_generator_artefacts
    tb = {"ccvs_code": "WAH-H6", "controls": [
        "Check anchor point rated to 6 kN before use",
        "Wear harness clipped to anchor",
    ], "admin": [], "hold_points": [], "stop_work": [], "ppe": []}
    _strip_generator_artefacts(tb)
    assert len(tb["controls"]) == 1


def test_strip_scaffold_load_test():
    from core.orchestrator import _strip_generator_artefacts
    tb = {"ccvs_code": "WAH-H6", "controls": [
        "Scaffold sections to be load-tested before use",
        "Check scaffold tag current",
    ], "admin": [], "hold_points": [], "stop_work": [], "ppe": []}
    _strip_generator_artefacts(tb)
    assert len(tb["controls"]) == 1
    assert "load-test" not in tb["controls"][0].lower()


def test_strip_no_hazardous_prerequisite():
    from core.orchestrator import _strip_generator_artefacts
    tb = {"ccvs_code": "CHM-H6", "controls": [], "admin": [
        "No hazardous substances identified",
        "SDS on site for membrane product",
    ], "hold_points": [], "stop_work": [], "ppe": []}
    _strip_generator_artefacts(tb)
    assert len(tb["admin"]) == 1
    assert "SDS" in tb["admin"][0]


def test_p2_replaced_with_organic_vapour_on_chm():
    from core.orchestrator import _strip_generator_artefacts
    tb = {"ccvs_code": "CHM-H6", "controls": [
        "Wear P2 mask during membrane application",
    ], "admin": [], "hold_points": [], "stop_work": [], "ppe": []}
    _strip_generator_artefacts(tb)
    assert "organic vapour" in tb["controls"][0].lower()
    assert "p2" not in tb["controls"][0].lower()


def test_p2_preserved_on_sil_task():
    from core.orchestrator import _strip_generator_artefacts
    tb = {"ccvs_code": "SIL-H6", "controls": [
        "Wear P2 respirator during grinding",
    ], "admin": [], "hold_points": [], "stop_work": [], "ppe": []}
    _strip_generator_artefacts(tb)
    assert "P2" in tb["controls"][0]


# ── T2-B2: _correct_ccvs_by_task_type — demob tasks ──────────────────────────

def test_dedup_monitoring_replaces_cross_family_copy():
    """Verbatim monitoring on unlike CCVS families gets replaced."""
    from core.orchestrator import _dedup_monitoring_across_tasks
    cc = "Dust extraction running and P2 respirator fitted before each grinding cycle"
    tasks = [
        {"task": "Remove membrane", "ccvs_code": "SIL-H6", "monitoring": {"critical_control": cc}},
        {"task": "Apply membrane", "ccvs_code": "CHM-H6", "monitoring": {"critical_control": cc}},
    ]
    _dedup_monitoring_across_tasks(tasks)
    # SIL task keeps dust monitoring (it matches); CHM task gets chemical template
    assert "dust" in tasks[0]["monitoring"]["critical_control"].lower() or "p2" in tasks[0]["monitoring"]["critical_control"].lower()
    assert "sds" in tasks[1]["monitoring"]["critical_control"].lower() or "ventilation" in tasks[1]["monitoring"]["critical_control"].lower()


def test_dedup_monitoring_preserves_same_family():
    """Same family reuse is not disturbed."""
    from core.orchestrator import _dedup_monitoring_across_tasks
    cc = "Dust extraction running"
    tasks = [
        {"task": "Remove membrane", "ccvs_code": "SIL-H6", "monitoring": {"critical_control": cc}},
        {"task": "Repair cracks", "ccvs_code": "SIL-H6", "monitoring": {"critical_control": cc}},
    ]
    _dedup_monitoring_across_tasks(tasks)
    assert tasks[0]["monitoring"]["critical_control"] == cc
    assert tasks[1]["monitoring"]["critical_control"] == cc


def test_fallback_ccvs_na_staging_gets_sys():
    """Staging/delivery task with N/A CCVS and hazards gets SYS-M3."""
    from core.orchestrator import _fallback_ccvs_na
    tasks = [
        {"task": "Deliver and stage portal frame bays", "ccvs_code": "N/A", "hazards": ["Manual handling"]},
    ]
    _fallback_ccvs_na(tasks)
    assert tasks[0]["ccvs_code"] == "SYS-M3"


def test_fallback_ccvs_na_does_not_overwrite_sil():
    """Valid SIL classification is not overwritten."""
    from core.orchestrator import _fallback_ccvs_na
    tasks = [
        {"task": "Remove membrane", "ccvs_code": "SIL-H6", "hazards": ["Silica dust"]},
    ]
    _fallback_ccvs_na(tasks)
    assert tasks[0]["ccvs_code"] == "SIL-H6"


def test_fallback_ccvs_na_skips_no_hazards():
    """N/A task without hazards stays N/A."""
    from core.orchestrator import _fallback_ccvs_na
    tasks = [
        {"task": "Deliver materials to site", "ccvs_code": "N/A", "hazards": []},
    ]
    _fallback_ccvs_na(tasks)
    assert tasks[0]["ccvs_code"] == "N/A"


def test_ccvs_earthworks_gets_sil():
    from core.orchestrator import _correct_ccvs_by_task_type
    tb = {"task": "Undertake bulk earthworks and establish formation", "ccvs_code": "N/A"}
    _correct_ccvs_by_task_type(tb)
    assert tb["ccvs_code"] == "SIL-H6"


def test_ccvs_stormwater_drainage_gets_sil():
    from core.orchestrator import _correct_ccvs_by_task_type
    tb = {"task": "Construct stormwater drainage infrastructure", "ccvs_code": "N/A"}
    _correct_ccvs_by_task_type(tb)
    assert tb["ccvs_code"] == "SIL-H6"


def test_ccvs_traffic_signal_gets_ele():
    from core.orchestrator import _correct_ccvs_by_task_type
    tb = {"task": "Install traffic signal infrastructure and commission", "ccvs_code": "N/A"}
    _correct_ccvs_by_task_type(tb)
    assert tb["ccvs_code"] == "ELE-H6"


def test_ccvs_line_marking_gets_sys():
    from core.orchestrator import _correct_ccvs_by_task_type
    tb = {"task": "Install line marking, pavement markers, signage", "ccvs_code": "N/A"}
    _correct_ccvs_by_task_type(tb)
    assert tb["ccvs_code"] == "SYS-M3"


def test_ccvs_locate_services_gets_sys():
    from core.orchestrator import _correct_ccvs_by_task_type
    tb = {"task": "Locate, expose, and protect Sydney Water assets", "ccvs_code": "N/A"}
    _correct_ccvs_by_task_type(tb)
    assert tb["ccvs_code"] == "SYS-M3"


def test_ccvs_crane_lift_gets_wah():
    """Crane-lift tasks should get WAH-H6."""
    from core.orchestrator import _correct_ccvs_by_task_type

    tb = {"task": "Crane-lift and distribute roof packs onto precast panels", "ccvs_code": "N/A"}
    _correct_ccvs_by_task_type(tb)
    assert tb["ccvs_code"] == "WAH-H6"


def test_ccvs_tilt_panel_gets_wah():
    from core.orchestrator import _correct_ccvs_by_task_type
    tb = {"task": "Lift, tilt, and position panel with mobile crane", "ccvs_code": "N/A"}
    _correct_ccvs_by_task_type(tb)
    assert tb["ccvs_code"] == "WAH-H6"


def test_ccvs_plumb_brace_gets_wah():
    from core.orchestrator import _correct_ccvs_by_task_type
    tb = {"task": "Plumb panel and install temporary bracing system", "ccvs_code": "N/A"}
    _correct_ccvs_by_task_type(tb)
    assert tb["ccvs_code"] == "WAH-H6"


def test_ccvs_remove_temp_bracing_gets_wah():
    """Remove temporary bracing is WAH (structural at height), not SIL."""
    from core.orchestrator import _correct_ccvs_by_task_type
    tb = {"task": "Remove temporary bracing system on engineer release only", "ccvs_code": "N/A"}
    _correct_ccvs_by_task_type(tb)
    assert tb["ccvs_code"] == "WAH-H6"


def test_ccvs_prepare_panel_bases_gets_sys():
    from core.orchestrator import _correct_ccvs_by_task_type
    tb = {"task": "Prepare panel bases and prop locations on slab", "ccvs_code": "N/A"}
    _correct_ccvs_by_task_type(tb)
    assert tb["ccvs_code"] == "SYS-M3"


def test_ccvs_scissor_lift_transfer_gets_wah():
    """Scissor lift transfer tasks should get WAH-H6."""
    from core.orchestrator import _correct_ccvs_by_task_type

    tb = {"task": "Transfer workers onto roof via scissor lift", "ccvs_code": "N/A"}
    _correct_ccvs_by_task_type(tb)
    assert tb["ccvs_code"] == "WAH-H6"


def test_ccvs_demolish_gets_sil():
    """Demolish tasks should get SIL-H6 (dust/debris)."""
    from core.orchestrator import _correct_ccvs_by_task_type

    tb = {"task": "Demolish existing partition walls and ceiling grid", "ccvs_code": "N/A"}
    _correct_ccvs_by_task_type(tb)
    assert tb["ccvs_code"] == "SIL-H6"


def test_ccvs_hold_point_gets_sys():
    """Hold point tasks are procedural — should get SYS-M3."""
    from core.orchestrator import _correct_ccvs_by_task_type

    tb = {"task": "Hold point: obtain supervisor sign-off on repairs", "ccvs_code": "N/A"}
    _correct_ccvs_by_task_type(tb)
    assert tb["ccvs_code"] == "SYS-M3"


def test_ccvs_dismantle_scaffold_stays_wah():
    """Dismantle scaffold should get WAH, not SIL — 'remove' in task name must not trigger SIL."""
    from core.orchestrator import _correct_ccvs_by_task_type

    tb = {"task": "Dismantle scaffold and remove from site", "ccvs_code": "N/A"}
    _correct_ccvs_by_task_type(tb)
    assert tb["ccvs_code"] == "WAH-H6"


def test_ccvs_dismantle_scaffold_and_demobilise_stays_wah():
    """Combined dismantle+demob task should get WAH, not SYS-M3."""
    from core.orchestrator import _correct_ccvs_by_task_type

    tb = {"task": "Dismantle scaffold and demobilise site", "ccvs_code": "N/A"}
    _correct_ccvs_by_task_type(tb)
    assert tb["ccvs_code"] == "WAH-H6"


def test_ccvs_remove_membrane_stays_sil():
    """Remove waterproofing membrane is genuinely SIL — must not get WAH."""
    from core.orchestrator import _correct_ccvs_by_task_type

    tb = {"task": "Remove existing waterproofing membrane and screed", "ccvs_code": "N/A"}
    _correct_ccvs_by_task_type(tb)
    assert tb["ccvs_code"] == "SIL-H6"


def test_ccvs_demob_task_corrected_to_sys():
    """Demob/reinstatement task should get SYS-M3, not WAH-H6."""
    from core.orchestrator import _correct_ccvs_by_task_type

    tb = {"task": "Site demobilisation and building reinstatement", "ccvs_code": "WAH-H6"}
    _correct_ccvs_by_task_type(tb)
    assert tb["ccvs_code"] == "SYS-M3"


def test_ccvs_handover_task_corrected_to_sys():
    from core.orchestrator import _correct_ccvs_by_task_type

    tb = {"task": "Handover and site clean", "ccvs_code": "WAH-H6"}
    _correct_ccvs_by_task_type(tb)
    assert tb["ccvs_code"] == "SYS-M3"


def test_ccvs_green_wall_reinstate_stays_wah():
    """Green wall reinstatement is genuinely at height — stays WAH."""
    from core.orchestrator import _correct_ccvs_by_task_type

    tb = {"task": "Reinstate green wall panels", "ccvs_code": "N/A"}
    _correct_ccvs_by_task_type(tb)
    assert tb["ccvs_code"] == "WAH-H6"


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


def test_hrcw_corrected_when_category_cl4():
    """hrcw_category containing cl.4 (asbestos) forces hrcw=true."""
    from core.orchestrator import _normalise_task

    tb = {
        "task": "Remove existing membrane",
        "scope": "Balcony waterproofing removal",
        "risk_pre": "H", "risk_post": "M",
        "ccvs_code": "SIL-H6",
        "hrcw": False,
        "hrcw_category": "cl.4 — Disturbance of asbestos",
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

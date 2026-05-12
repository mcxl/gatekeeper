"""Tests for pims/services/ccvs_fallback.py — Phase 9."""

from __future__ import annotations

from pims.services.ccvs_fallback import apply_ccvs_fallback


def test_no_op_when_code_already_set():
    parsed = {"ccvs_code": "WAH-H6", "conformance_status": "NCR"}
    assert apply_ccvs_fallback(parsed, "Scaffold edge unprotected") is None
    assert parsed["ccvs_code"] == "WAH-H6"


def test_no_op_when_status_pending():
    parsed = {"ccvs_code": None, "conformance_status": "Pending"}
    assert apply_ccvs_fallback(parsed, "SWMS completed for all workers") is None
    assert parsed["ccvs_code"] is None


def test_swms_maps_to_sys_m3():
    parsed = {"ccvs_code": None, "conformance_status": "Compliant"}
    matched = apply_ccvs_fallback(parsed, "SWMS remedial works completed.")
    assert matched == "swms"
    assert parsed["ccvs_code"] == "SYS-M3"
    assert parsed["ccvs_category"] == "Systems"


def test_toolbox_maps_to_sys_m3():
    parsed = {"ccvs_code": None, "conformance_status": "Compliant"}
    apply_ccvs_fallback(parsed, "Safety toolbox talk completed on 17 May")
    assert parsed["ccvs_code"] == "SYS-M3"


def test_white_card_maps_to_sys_l1():
    parsed = {"ccvs_code": None, "conformance_status": "Compliant"}
    apply_ccvs_fallback(parsed, "Louis Badu White card in system verified.")
    assert parsed["ccvs_code"] == "SYS-L1"


def test_fire_extinguisher_maps_to_sys_h6():
    parsed = {"ccvs_code": None, "conformance_status": "Compliant"}
    apply_ccvs_fallback(parsed, "Fire extinguisher accessible to workers.")
    assert parsed["ccvs_code"] == "SYS-H6"


def test_first_aid_maps_to_sys_h6():
    parsed = {"ccvs_code": None, "conformance_status": "Compliant"}
    apply_ccvs_fallback(parsed, "First aid kit fixed to temporary fence.")
    assert parsed["ccvs_code"] == "SYS-H6"


def test_scaff_tag_maps_to_sys_m4():
    parsed = {"ccvs_code": None, "conformance_status": "NCR"}
    apply_ccvs_fallback(parsed, "Scaff tag - unable to determine sign-off date.")
    assert parsed["ccvs_code"] == "SYS-M4"


def test_electrical_supply_maps_to_ene_m4():
    parsed = {"ccvs_code": None, "conformance_status": "Info"}
    apply_ccvs_fallback(parsed, "Electrical supply for working area supplied by GPO.")
    assert parsed["ccvs_code"] == "ENE-M4"
    assert parsed["ccvs_category"] == "Energy"


def test_daly_signs_typo_maps_to_sys_l1():
    """Production observed 'Daly signs' typo for 'Daily signs' — alias covered."""
    parsed = {"ccvs_code": None, "conformance_status": "Compliant"}
    apply_ccvs_fallback(parsed, "Daly signs completed by all workers on site.")
    assert parsed["ccvs_code"] == "SYS-L1"


def test_no_match_leaves_code_null():
    parsed = {"ccvs_code": None, "conformance_status": "Compliant"}
    matched = apply_ccvs_fallback(parsed, "Some uncategorisable observation.")
    assert matched is None
    assert parsed.get("ccvs_code") is None


def test_empty_text_no_op():
    parsed = {"ccvs_code": None, "conformance_status": "Compliant"}
    assert apply_ccvs_fallback(parsed, "") is None
    assert apply_ccvs_fallback(parsed, None) is None


def test_specific_keyword_wins_over_generic():
    """'first aid' must beat 'aid' if both existed — order in the map matters."""
    parsed = {"ccvs_code": None, "conformance_status": "Compliant"}
    matched = apply_ccvs_fallback(parsed, "first aid kit refilled this morning")
    assert matched == "first aid"
    assert parsed["ccvs_code"] == "SYS-H6"


def test_sets_confidence_medium_when_unset():
    parsed = {"ccvs_code": None, "conformance_status": "Compliant"}
    apply_ccvs_fallback(parsed, "SWMS reviewed today.")
    assert parsed.get("ccvs_confidence") == "Medium"

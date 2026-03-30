"""
tests/test_validator_upgrades.py — Tests for issue gate checks 14-20 and job-type rule packs.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.issue_gate import (
    CheckResult,
    _check_dominant_control_family,
    _check_hrcw_undercall,
    _check_unsupported_admin_controls,
    _check_framework_control_misuse,
    _check_wah_dominance_extended,
    _check_filler_controls,
    _check_job_type_mandatory_steps,
    SYSTEMIC_THRESHOLD,
)


def _task(name, ccvs="WAH-H6", mon_cc="", controls=None, admin=None, scope=""):
    return {
        "step": "1.1", "task": name, "scope": scope,
        "ccvs_code": ccvs, "hazards": ["test"],
        "controls": controls or [], "admin": admin or [],
        "hold_points": [], "stop_work": [],
        "monitoring": {"critical_control": mon_cc, "who_checks": "Sup",
                       "frequency": "daily", "what_to_look_for": "check"},
    }


# ── C14: Dominant control family ─────────────────────────────────────────────

class TestDominantControlFamily:
    def test_pass_correct_family(self):
        t = [_task("Remove existing waterproofing", mon_cc="SDS on site, ventilation confirmed")]
        assert _check_dominant_control_family(t).result == CheckResult.PASS

    def test_fail_wah_on_demolition(self):
        t = [_task("Demolition of tile bed", mon_cc="Harness clipped to anchor")]
        r = _check_dominant_control_family(t)
        assert r.result == CheckResult.FAIL
        assert "SIL" in r.detail

    def test_systemic_prefix(self):
        tasks = [
            _task("Demolition phase 1", mon_cc="Harness check"),
            _task("Removal of screed", mon_cc="Lanyard attached"),
            _task("Strip-out existing membrane", mon_cc="Anchor point checked"),
        ]
        r = _check_dominant_control_family(tasks)
        assert r.result == CheckResult.FAIL
        assert "SYSTEMIC:" in r.detail


# ── C15: HRCW undercall ──────────────────────────────────────────────────────

class TestHrcwUndercall:
    def test_pass_all_covered(self):
        t = [_task("Erect scaffold", scope="ewp access")]
        r = _check_hrcw_undercall(t, hrcw_selected=["powered_mobile_plant"])
        assert r.result == CheckResult.PASS

    def test_review_missing_hrcw(self):
        t = [_task("Use boom lift for access", scope="ewp roof")]
        r = _check_hrcw_undercall(t, hrcw_selected=[])
        assert r.result == CheckResult.REVIEW
        assert "powered_mobile_plant" in r.detail

    def test_no_fail_only_review(self):
        t = [_task("Crane lift panels", scope="tower crane")]
        r = _check_hrcw_undercall(t, hrcw_selected=[])
        assert r.result == CheckResult.REVIEW  # never FAIL


# ── C16: Unsupported admin controls ──────────────────────────────────────────

class TestUnsupportedAdminControls:
    def test_pass_clean(self):
        t = [_task("Paint wall", admin=["Brief workers on SDS"])]
        assert _check_unsupported_admin_controls(t).result == CheckResult.PASS

    def test_fail_council_permit(self):
        t = [_task("Setup site", admin=["Obtain council permit before work"])]
        r = _check_unsupported_admin_controls(t)
        assert r.result == CheckResult.FAIL

    def test_allowed_keyword_skipped(self):
        t = [_task("Setup", admin=["Obtain council permit"])]
        r = _check_unsupported_admin_controls(t, allowed=("council permit",))
        assert r.result == CheckResult.PASS


# ── C17: Framework control misuse ────────────────────────────────────────────

class TestFrameworkControlMisuse:
    def test_pass_clean(self):
        t = [_task("Paint masonry")]
        assert _check_framework_control_misuse(t).result == CheckResult.PASS

    def test_review_latent_standalone(self):
        t = [_task("Latent conditions check — stop work")]
        r = _check_framework_control_misuse(t)
        assert r.result == CheckResult.REVIEW

    def test_review_prestart_in_demob(self):
        t = [_task("Demobilise site", controls=["Conduct toolbox talk before leaving"])]
        r = _check_framework_control_misuse(t)
        assert r.result == CheckResult.REVIEW


# ── C18: WAH dominance ───────────────────────────────────────────────────────

class TestWahDominanceExtended:
    def test_pass_low_wah(self):
        tasks = [
            _task("T1", mon_cc="Dust extraction running"),
            _task("T2", mon_cc="SDS on site"),
            _task("T3", mon_cc="Harness clipped"),
        ]
        assert _check_wah_dominance_extended(tasks).result == CheckResult.PASS

    def test_review_high_wah(self):
        tasks = [
            _task("T1", mon_cc="Harness check"),
            _task("T2", mon_cc="Lanyard attached"),
            _task("T3", mon_cc="Anchor point secure"),
        ]
        r = _check_wah_dominance_extended(tasks)
        assert r.result == CheckResult.REVIEW

    def test_never_fails(self):
        tasks = [_task("T1", mon_cc="Harness")] * 10
        r = _check_wah_dominance_extended(tasks)
        assert r.result == CheckResult.REVIEW  # never FAIL


# ── C19: Filler controls ────────────────────────────────────────────────────

class TestFillerControls:
    def test_pass_no_filler(self):
        t = [_task("Paint", controls=["Wear respirator during spray application"])]
        assert _check_filler_controls(t).result == CheckResult.PASS

    def test_review_single_filler(self):
        t = [_task("Paint", controls=["follow swms"])]
        r = _check_filler_controls(t)
        assert r.result == CheckResult.REVIEW

    def test_fail_systemic_filler(self):
        t = [
            _task("T1", controls=["follow swms"]),
            _task("T2", controls=["use ppe as required"]),
            _task("T3", controls=["supervisor to monitor"]),
        ]
        r = _check_filler_controls(t)
        assert r.result == CheckResult.FAIL
        assert "SYSTEMIC:" in r.detail


# ── C20: Job-type mandatory steps ────────────────────────────────────────────

class TestJobTypeMandatorySteps:
    def test_skip_empty_job_type(self):
        r = _check_job_type_mandatory_steps([_task("Paint")], job_type="")
        assert r.result == CheckResult.PASS
        assert "skipped" in r.detail.lower()

    def test_skip_unknown_job_type(self):
        r = _check_job_type_mandatory_steps([_task("Paint")], job_type="unknown")
        assert r.result == CheckResult.PASS
        assert "skipped" in r.detail.lower()

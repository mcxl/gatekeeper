"""
Tests for content-quality post-processing: demolition stripping from controls,
responsibility improvement, and monitoring crosswalk improvement.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.orchestrator import (
    _strip_demolition_content,
    _strip_unsupported_controls,
    _strip_active_hazmat,
    _strip_sealant_drift,
    _strip_timber_drift,
    _improve_responsibility,
    _improve_monitoring,
)


# ── Demolition content stripping ─────────────────────────────────────────────

class TestDemolitionStripping:
    def test_strips_demolition_from_scaffold_dismantle(self):
        tb = {
            "task": "Dismantle scaffolding or retrieve EWP",
            "controls": [
                "Verify demolition notification submitted to SafeWork NSW",
                "Wear fall arrest harness before ascending",
            ],
            "admin": [
                "Obtain signed demolition licence — Class B or C",
                "Confirm all workers hold White Card",
            ],
        }
        _strip_demolition_content(tb)
        assert len(tb["controls"]) == 1
        assert "harness" in tb["controls"][0]
        assert len(tb["admin"]) == 1
        assert "White Card" in tb["admin"][0]

    def test_strips_demolition_from_green_wall_removal(self):
        tb = {
            "task": "Remove green wall and prepare surfaces",
            "admin": [
                "Obtain SafeWork NSW demolition notification",
                "Verify Demolition Licence (Class B or C)",
                "Brief workers on removal sequence",
            ],
            "controls": [],
        }
        _strip_demolition_content(tb)
        assert len(tb["admin"]) == 1
        assert "removal sequence" in tb["admin"][0]

    def test_preserves_demolition_on_actual_demolition_task(self):
        tb = {
            "task": "Demolition of internal walls",
            "admin": ["Obtain demolition licence", "Brief crew"],
            "controls": ["Demolition notification submitted"],
        }
        _strip_demolition_content(tb)
        assert len(tb["admin"]) == 2
        assert len(tb["controls"]) == 1

    def test_no_demolition_content_unchanged(self):
        tb = {
            "task": "Paint masonry",
            "controls": ["Wear harness", "Check scaffold"],
            "admin": ["Brief workers"],
        }
        _strip_demolition_content(tb)
        assert len(tb["controls"]) == 2
        assert len(tb["admin"]) == 1


# ── Responsibility improvement ───────────────────────────────────────────────

class TestResponsibilityImprovement:
    def test_replaces_generic_setup(self):
        tb = {
            "task": "Establish site and plan access",
            "responsibility": {
                "SUP": "Supervise Establish site and plan",
                "WKR": "Perform Establish site and plan per SWMS",
            },
        }
        _improve_responsibility(tb)
        assert "exclusion zone" in tb["responsibility"]["SUP"].lower()
        assert "barriers" in tb["responsibility"]["WKR"].lower()

    def test_replaces_generic_painting(self):
        tb = {
            "task": "Paint exterior masonry",
            "responsibility": {
                "SUP": "Supervise Paint exterior",
                "WKR": "Perform Paint exterior per SWMS",
            },
            "ccvs_code": "WAH-H6",
        }
        _improve_responsibility(tb)
        assert "scaffold" in tb["responsibility"]["SUP"].lower() or "fall arrest" in tb["responsibility"]["SUP"].lower()
        assert "respiratory" in tb["responsibility"]["WKR"].lower() or "harness" in tb["responsibility"]["WKR"].lower()

    def test_preserves_custom_responsibility(self):
        tb = {
            "task": "Paint exterior masonry",
            "responsibility": {
                "SUP": "Check scaffold daily, verify PPE, enforce exclusion zones",
                "WKR": "Apply paint per spec, wear harness at all times",
            },
        }
        _improve_responsibility(tb)
        assert "Check scaffold" in tb["responsibility"]["SUP"]  # unchanged
        assert "Apply paint" in tb["responsibility"]["WKR"]  # unchanged

    def test_replaces_generic_scaffold(self):
        tb = {
            "task": "Erect scaffolding",
            "responsibility": {
                "SUP": "Supervise Erect scaff",
                "WKR": "Perform Erect scaff per SWMS",
            },
        }
        _improve_responsibility(tb)
        assert "certification" in tb["responsibility"]["SUP"].lower()


# ── Monitoring improvement ───────────────────────────────────────────────────

class TestMonitoringImprovement:
    def test_setup_task_gets_exclusion_monitoring(self):
        tb = {
            "task": "Establish site",
            "scope": "setup",
            "monitoring": {
                "critical_control": "Check harness clipped to anchor",
                "who_checks": "",
                "frequency": "",
                "what_to_look_for": "",
            },
        }
        _improve_monitoring(tb)
        assert "exclusion" in tb["monitoring"]["critical_control"].lower()
        assert tb["monitoring"]["who_checks"] == "Supervisor"
        assert tb["monitoring"]["what_to_look_for"] != ""

    def test_paint_task_gets_chemical_monitoring(self):
        tb = {
            "task": "Paint exterior masonry",
            "scope": "painting",
            "monitoring": {
                "critical_control": "Check harness clipped",
                "who_checks": "",
                "frequency": "",
                "what_to_look_for": "",
            },
        }
        _improve_monitoring(tb)
        assert "sds" in tb["monitoring"]["critical_control"].lower()

    def test_grinding_task_gets_dust_monitoring(self):
        tb = {
            "task": "Crack stitching and repoint",
            "scope": "grinding mortar",
            "monitoring": {
                "critical_control": "Check harness",
                "who_checks": "",
                "frequency": "",
                "what_to_look_for": "",
            },
        }
        _improve_monitoring(tb)
        assert "dust" in tb["monitoring"]["critical_control"].lower() or "p2" in tb["monitoring"]["critical_control"].lower()

    def test_scaffold_task_keeps_scaffold_monitoring(self):
        tb = {
            "task": "Erect scaffolding",
            "scope": "",
            "monitoring": {
                "critical_control": "Check harness",
                "who_checks": "",
                "frequency": "",
                "what_to_look_for": "",
            },
        }
        _improve_monitoring(tb)
        # Scaffold tasks should get scaffold-specific monitoring, not harness
        assert "scaffold" in tb["monitoring"]["critical_control"].lower() or "ewp" in tb["monitoring"]["critical_control"].lower()

    def test_preserves_existing_who_checks(self):
        tb = {
            "task": "Paint walls",
            "scope": "",
            "monitoring": {
                "critical_control": "Check harness",
                "who_checks": "Site foreman",
                "frequency": "",
                "what_to_look_for": "",
            },
        }
        _improve_monitoring(tb)
        assert tb["monitoring"]["who_checks"] == "Site foreman"  # preserved


# ── Unsupported controls stripping ───────────────────────────────────────────

class TestUnsupportedControls:
    def test_strips_utility_isolation(self):
        tb = {
            "task": "Establish site",
            "controls": ["Install barriers", "Verify utility isolation certificate"],
            "admin": ["Brief workers"],
        }
        _strip_unsupported_controls(tb)
        assert len(tb["controls"]) == 1
        assert "barriers" in tb["controls"][0]

    def test_strips_shoring_plan(self):
        tb = {
            "task": "Brickwork reconstruction",
            "admin": ["Obtain structural engineer's shoring plan", "Brief crew"],
            "controls": [],
        }
        _strip_unsupported_controls(tb)
        assert len(tb["admin"]) == 1

    def test_strips_council_consent(self):
        tb = {
            "task": "Establish site",
            "admin": ["Obtain council development consent confirmation", "Record inductions"],
            "controls": [],
        }
        _strip_unsupported_controls(tb)
        assert len(tb["admin"]) == 1
        assert "inductions" in tb["admin"][0]

    def test_preserves_supported_controls(self):
        tb = {
            "task": "Paint masonry",
            "controls": ["Wear harness", "Check scaffold tag"],
            "admin": ["Brief workers on SDS"],
        }
        _strip_unsupported_controls(tb)
        assert len(tb["controls"]) == 2
        assert len(tb["admin"]) == 1


# ── Active hazmat stripping ──────────────────────────────────────────────────

class TestActiveHazmat:
    def test_converts_survey_task_to_latent_condition(self):
        tb = {
            "task": "Survey and identify latent hazardous materials",
            "scope": "Active asbestos survey",
            "controls": ["Engage licensed assessor", "Sample all suspect materials"],
            "admin": ["Obtain asbestos register"],
            "hazards": ["Asbestos exposure"],
            "responsibility": {"SUP": "Supervise Survey", "WKR": "Perform Survey per SWMS"},
            "monitoring": {
                "critical_control": "Check asbestos survey",
                "who_checks": "", "frequency": "", "what_to_look_for": "",
            },
        }
        _strip_active_hazmat(tb)
        assert "latent" in tb["task"].lower()
        assert "stop work" in tb["scope"].lower() or "stop work" in tb["controls"][0].lower()
        assert "licensed assessor" not in json.dumps(tb["controls"]).lower()

    def test_strips_hazmat_from_other_tasks(self):
        tb = {
            "task": "Remove green wall",
            "controls": ["Wear harness", "Complete hazmat survey before removal"],
            "admin": ["Obtain asbestos register"],
        }
        _strip_active_hazmat(tb)
        assert len(tb["controls"]) == 1
        assert "harness" in tb["controls"][0]
        assert len(tb["admin"]) == 0

    def test_preserves_stop_work_triggers(self):
        tb = {
            "task": "Paint fibre cement",
            "controls": ["Wear respirator"],
            "admin": [],
            "stop_work": ["Stop work if suspect ACM is disturbed"],
        }
        _strip_active_hazmat(tb)
        assert len(tb["stop_work"]) == 1  # preserved


# ── Sealant drift stripping ─────────────────────────────────────────────────

class TestSealantDrift:
    def test_strips_membrane_from_sealant_scope(self):
        tb = {
            "task": "Apply sealants to facade",
            "scope": "Apply sealants; apply damp-proof membrane where required.",
            "controls": [
                "Wear PPE",
                "Apply sealants and membranes only in dry conditions",
            ],
            "admin": [],
        }
        _strip_sealant_drift(tb)
        assert "membrane" not in tb["scope"].lower()
        assert len(tb["controls"]) == 1

    def test_preserves_non_sealant_tasks(self):
        tb = {
            "task": "Paint masonry",
            "scope": "Apply membrane primer",
            "controls": ["Apply membrane coat"],
            "admin": [],
        }
        _strip_sealant_drift(tb)
        assert "membrane" in tb["scope"].lower()  # unchanged

    def test_no_drift_unchanged(self):
        tb = {
            "task": "Apply sealants",
            "scope": "Recaulking joints with Emer-seal",
            "controls": ["Wear PPE"],
            "admin": [],
        }
        _strip_sealant_drift(tb)
        assert "recaulk" in tb["scope"].lower()


# ── Timber drift stripping ───────────────────────────────────────────────────

class TestTimberDrift:
    def test_strips_decay_from_timber_task(self):
        tb = {
            "task": "Treat timber beams and check for decay",
            "scope": "check timber members for rot and insect damage, apply preservative",
            "controls": [
                "Wear harness",
                "Apply preservative or biocide in well-ventilated area",
            ],
            "admin": [],
        }
        _strip_timber_drift(tb)
        assert "decay" not in tb["task"].lower()
        assert "preservative" not in tb["scope"].lower()
        assert len(tb["controls"]) == 1

    def test_preserves_non_timber_tasks(self):
        tb = {
            "task": "Repair concrete",
            "scope": "Check for decay in formwork",
            "controls": ["Apply preservative to formwork"],
            "admin": [],
        }
        _strip_timber_drift(tb)
        assert "decay" in tb["scope"].lower()  # unchanged

    def test_replaces_empty_scope(self):
        tb = {
            "task": "Treat timber beams and check for decay",
            "scope": "check for rot",
            "controls": [],
            "admin": [],
        }
        _strip_timber_drift(tb)
        assert "timber" in tb["scope"].lower()
        assert len(tb["scope"]) > 20

"""Tests for RA job-type classifier and hazard suppression."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.inference_matrix import classify_ra_scope, infer_to_dict_ra


class TestClassifyRaScope:
    """classify_ra_scope() returns correct job_type, building_context, scope_modifiers."""

    def test_data_centre_retrofit(self):
        """Benchmark case: data centre into existing tilt-up warehouse."""
        desc = ("Installing a data centre into an existing industrial warehouse "
                "(concrete tilt-up construction) in NSW")
        c = classify_ra_scope(desc)
        assert c["job_type"] == "fit_out"
        assert c["building_context"] == "existing"
        assert "tilt_up_context" in c["scope_modifiers"]
        assert "warehouse" in c["scope_modifiers"]
        assert "industrial" in c["scope_modifiers"]
        assert "electrical_install" in c["scope_modifiers"]

    def test_new_build_tiltup(self):
        """New-build tilt-up should classify as new_build."""
        desc = "Erection of tilt-up concrete panels for new warehouse construction"
        c = classify_ra_scope(desc)
        assert c["job_type"] == "new_build"
        assert c["building_context"] == "new"

    def test_demolition(self):
        desc = "Demolition of existing two-storey commercial building"
        c = classify_ra_scope(desc)
        assert c["job_type"] == "demolition"
        assert c["building_context"] == "existing"

    def test_maintenance(self):
        desc = "Routine maintenance and repair of existing HVAC system"
        c = classify_ra_scope(desc)
        assert c["job_type"] == "maintenance"
        assert "mechanical_install" in c["scope_modifiers"]

    def test_office_fitout(self):
        desc = "Office fit out of level 3 in occupied commercial building"
        c = classify_ra_scope(desc)
        assert c["job_type"] == "fit_out"
        assert c["building_context"] == "existing"
        assert "occupied_site" in c["scope_modifiers"]


class TestRaHazardSuppression:
    """RA hazard list should suppress new-build categories for existing-building work."""

    def test_data_centre_no_tiltup_hazard(self):
        """Tilt-up/precast hazard must NOT appear for fit-out in existing tilt-up building."""
        desc = ("Installing a data centre into an existing industrial warehouse "
                "(concrete tilt-up construction) in NSW")
        result = infer_to_dict_ra(desc, jurisdiction="AU")
        hazard_names = [h["hazard"].lower() for h in result["hazard_list"]]
        assert not any("tilt" in n or "precast" in n for n in hazard_names), (
            f"Tilt-up/precast hazard should be suppressed for fit-out: {hazard_names}"
        )

    def test_new_build_keeps_tiltup_hazard(self):
        """New-build tilt-up should retain the tilt-up/precast hazard."""
        desc = "Erection of tilt-up concrete panels for new warehouse"
        result = infer_to_dict_ra(desc, jurisdiction="AU")
        hazard_names = [h["hazard"].lower() for h in result["hazard_list"]]
        assert any("tilt" in n or "precast" in n for n in hazard_names), (
            f"Tilt-up/precast hazard should be present for new-build: {hazard_names}"
        )

    def test_classification_in_result(self):
        """infer_to_dict_ra must include ra_classification in result."""
        desc = "Installing a data centre into an existing industrial warehouse"
        result = infer_to_dict_ra(desc, jurisdiction="AU")
        assert "ra_classification" in result
        assert result["ra_classification"]["job_type"] == "fit_out"

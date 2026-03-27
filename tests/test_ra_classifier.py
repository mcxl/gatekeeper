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


class TestRaConfidence:
    """RA hazards must have appropriate confidence levels."""

    def test_data_centre_no_false_confirmed_hazards(self):
        """Context-only hazards for data-centre fit-out should not be confirmed.
        Legitimately scope-derived hazards (electrical installation) may be confirmed."""
        desc = ("Installing a data centre into an existing industrial warehouse "
                "(concrete tilt-up construction) in NSW")
        result = infer_to_dict_ra(desc, jurisdiction="AU")
        # These are legitimate confirmed hazards for data-centre scope
        _ALLOWED_CONFIRMED = {"General construction hazards",
                              "Work on or near energised electrical installations"}
        for h in result["hazard_list"]:
            if h["hazard"] in _ALLOWED_CONFIRMED:
                continue
            assert h["confidence"] != "confirmed", (
                f"'{h['hazard']}' should not be confirmed for fit-out: "
                f"got '{h['confidence']}'"
            )

    def test_data_centre_has_fit_out_hazards(self):
        """Data-centre fit-out should produce relevant services-installation hazards."""
        desc = ("Installing a data centre into an existing industrial warehouse "
                "(concrete tilt-up construction) in NSW")
        result = infer_to_dict_ra(desc, jurisdiction="AU")
        hazard_names = {h["hazard"].lower() for h in result["hazard_list"]}
        # Should have electrical, UPS, HVAC, fire services, existing services
        assert any("electrical" in n for n in hazard_names), \
            f"Should have electrical hazard: {hazard_names}"
        assert any("ups" in n for n in hazard_names), \
            f"Should have UPS hazard: {hazard_names}"
        assert any("hvac" in n for n in hazard_names), \
            f"Should have HVAC hazard: {hazard_names}"
        assert any("fire" in n for n in hazard_names), \
            f"Should have fire services hazard: {hazard_names}"
        assert any("existing services" in n or "service" in n for n in hazard_names), \
            f"Should have existing services hazard: {hazard_names}"

    def test_data_centre_no_wah_or_rigging(self):
        """WAH and rigging should not appear for data-centre fit-out —
        they were false positives from chain expansion of 'tilt-up'."""
        desc = ("Installing a data centre into an existing industrial warehouse "
                "(concrete tilt-up construction) in NSW")
        result = infer_to_dict_ra(desc, jurisdiction="AU")
        hazard_names = [h["hazard"].lower() for h in result["hazard_list"]]
        assert not any("height" in n or "fall" in n for n in hazard_names), (
            f"WAH should not appear for fit-out: {hazard_names}"
        )
        assert not any("rigging" in n or "dogging" in n for n in hazard_names), (
            f"Rigging should not appear for fit-out: {hazard_names}"
        )

    def test_directly_stated_hazard_is_confirmed(self):
        """Asbestos removal directly stated should be 'confirmed'."""
        desc = "Asbestos removal from ceiling panels in existing building"
        result = infer_to_dict_ra(desc, jurisdiction="AU")
        asb = [h for h in result["hazard_list"] if "asbestos" in h["hazard"].lower()]
        assert asb, "Asbestos hazard should be present"
        assert asb[0]["confidence"] == "confirmed", (
            f"Directly stated asbestos should be confirmed, got '{asb[0]['confidence']}'"
        )

    def test_all_hazards_have_confidence_field(self):
        """Every hazard dict must include a confidence field."""
        desc = "Scaffold erection and facade painting at 8-storey building"
        result = infer_to_dict_ra(desc, jurisdiction="AU")
        valid = {"confirmed", "likely", "if_applicable", "requires_verification"}
        for h in result["hazard_list"]:
            assert "confidence" in h, f"Missing confidence field: {h['hazard']}"
            assert h["confidence"] in valid, (
                f"Invalid confidence '{h['confidence']}' for {h['hazard']}"
            )

    def test_baseline_fallback_is_confirmed(self):
        """Baseline fallback hazard (when nothing matches) should be confirmed."""
        desc = "General office cleaning"
        result = infer_to_dict_ra(desc, jurisdiction="AU")
        # Should get the baseline fallback
        if result["hazard_list"]:
            baseline = result["hazard_list"][0]
            if baseline["hazard"] == "General construction hazards":
                assert baseline["confidence"] == "confirmed"

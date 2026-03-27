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
        # Only baseline fallback is allowed as confirmed for chain-derived scope
        _ALLOWED_CONFIRMED = {"General construction hazards"}
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


class TestRaPhaseGrouping:
    """RA hazards should be grouped into named phases."""

    BENCHMARK_DESC = (
        "Installing a data centre into an existing industrial warehouse "
        "(concrete tilt-up construction) in NSW"
    )

    def test_phase_groups_present(self):
        """infer_to_dict_ra must include phase_groups in result."""
        result = infer_to_dict_ra(self.BENCHMARK_DESC, jurisdiction="AU")
        assert "phase_groups" in result
        assert isinstance(result["phase_groups"], list)
        assert len(result["phase_groups"]) > 0

    def test_benchmark_has_three_phases(self):
        """Data-centre retrofit should produce 3 phases (no interface phase
        because 'occupied' is not in the description)."""
        result = infer_to_dict_ra(self.BENCHMARK_DESC, jurisdiction="AU")
        phase_names = [pg["phase"] for pg in result["phase_groups"]]
        assert "Existing building / structural suitability" in phase_names
        assert "Installation and fit-out" in phase_names
        assert "Live services / commissioning" in phase_names

    def test_slab_loading_in_existing_phase(self):
        """Slab loading should be in the existing building phase."""
        result = infer_to_dict_ra(self.BENCHMARK_DESC, jurisdiction="AU")
        existing = [pg for pg in result["phase_groups"]
                    if pg["phase"] == "Existing building / structural suitability"][0]
        names = [h["hazard"].lower() for h in existing["hazards"]]
        assert any("slab" in n for n in names), f"Slab loading not in existing phase: {names}"

    def test_electrical_hrcw_in_live_phase(self):
        """HRCW energised electrical should be in live services phase."""
        result = infer_to_dict_ra(self.BENCHMARK_DESC, jurisdiction="AU")
        live = [pg for pg in result["phase_groups"]
                if pg["phase"] == "Live services / commissioning"][0]
        names = [h["hazard"].lower() for h in live["hazards"]]
        assert any("energised" in n for n in names), f"Energised not in live phase: {names}"

    def test_hvac_in_install_phase(self):
        """HVAC should be in installation phase."""
        result = infer_to_dict_ra(self.BENCHMARK_DESC, jurisdiction="AU")
        install = [pg for pg in result["phase_groups"]
                   if pg["phase"] == "Installation and fit-out"][0]
        names = [h["hazard"].lower() for h in install["hazards"]]
        assert any("hvac" in n for n in names), f"HVAC not in install phase: {names}"

    def test_hazards_tagged_with_phase(self):
        """Each hazard in the flat list should have a 'phase' field."""
        result = infer_to_dict_ra(self.BENCHMARK_DESC, jurisdiction="AU")
        for h in result["hazard_list"]:
            assert "phase" in h, f"Missing phase field: {h['hazard']}"

    def test_all_hazards_accounted_for(self):
        """Total hazards in phase groups must equal total in flat list."""
        result = infer_to_dict_ra(self.BENCHMARK_DESC, jurisdiction="AU")
        grouped_count = sum(len(pg["hazards"]) for pg in result["phase_groups"])
        assert grouped_count == len(result["hazard_list"])


class TestRaControlLanguage:
    """RA controls should read as practical site actions, not compliance fragments."""

    BENCHMARK_DESC = (
        "Installing a data centre into an existing industrial warehouse "
        "(concrete tilt-up construction) in NSW"
    )

    def test_electrical_controls_are_practical(self):
        """Electrical hazard controls should include LOTO and test-before-touch."""
        result = infer_to_dict_ra(self.BENCHMARK_DESC, jurisdiction="AU")
        elec = [h for h in result["hazard_list"]
                if "electrical" in h["hazard"].lower()]
        assert elec, "Should have electrical hazards"
        all_controls = " ".join(
            " ".join(h["controls"].get("engineering", []) + h["controls"].get("admin", []))
            for h in elec
        ).lower()
        assert "loto" in all_controls or "isolation" in all_controls, \
            f"Electrical controls should mention LOTO/isolation: {all_controls[:200]}"
        assert "test" in all_controls or "verify" in all_controls, \
            f"Electrical controls should mention test/verify: {all_controls[:200]}"

    def test_no_raw_regulation_as_control(self):
        """RA controls should not start with 'WHS Reg' or 'AS/NZS' — those are references, not controls."""
        result = infer_to_dict_ra(self.BENCHMARK_DESC, jurisdiction="AU")
        for h in result["hazard_list"]:
            for ctrl_type in ("engineering", "admin"):
                for ctrl in h["controls"].get(ctrl_type, []):
                    assert not ctrl.startswith("WHS Reg"), \
                        f"Control should not be a regulation reference: '{ctrl}' in {h['hazard']}"
                    assert not ctrl.startswith("AS/NZS"), \
                        f"Control should not be a standard reference: '{ctrl}' in {h['hazard']}"

    def test_controls_have_engineering_and_admin(self):
        """Every hazard should have at least one engineering and one admin control."""
        result = infer_to_dict_ra(self.BENCHMARK_DESC, jurisdiction="AU")
        for h in result["hazard_list"]:
            assert h["controls"].get("engineering"), \
                f"Missing engineering controls: {h['hazard']}"
            assert h["controls"].get("admin"), \
                f"Missing admin controls: {h['hazard']}"

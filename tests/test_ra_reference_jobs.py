"""
RA reference job regression tests.

Run after any change to:
- core/inference_matrix.py (classifier, hazard list, HRCW register)
- renderers/ra_renderer.py (supplementary sections)

These are not exact-output tests. They assert structural properties
that should remain stable across inference matrix changes.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.inference_matrix import infer_to_dict_ra


# ============================================================
# Reference Case 1: Data Centre Retrofit
# ============================================================

_DC_DESC = (
    "Installing a data centre into an existing industrial warehouse "
    "(concrete tilt-up construction) in NSW"
)


class TestDataCentreRetrofit:
    """RA reference: fit-out in existing tilt-up warehouse."""

    def setup_method(self):
        self.result = infer_to_dict_ra(_DC_DESC, jurisdiction="AU")
        self.c = self.result["ra_classification"]
        self.hazards = self.result["hazard_list"]
        self.phases = self.result["phase_groups"]

    # Classification
    def test_job_type(self):
        assert self.c["job_type"] == "fit_out"

    def test_building_context(self):
        assert self.c["building_context"] == "existing"

    def test_scope_modifiers(self):
        mods = self.c["scope_modifiers"]
        assert "tilt_up_context" in mods
        assert "warehouse" in mods
        assert "electrical_install" in mods

    # Hazard count and relevance
    def test_hazard_count(self):
        assert 5 <= len(self.hazards) <= 15, f"Expected 5-15 hazards, got {len(self.hazards)}"

    def test_no_tiltup_erection_hazard(self):
        names = [h["hazard"].lower() for h in self.hazards]
        assert not any("tilt" in n and "erect" in n for n in names), \
            "Tilt-up erection should be suppressed for fit-out"

    def test_has_electrical_hazard(self):
        names = [h["hazard"].lower() for h in self.hazards]
        assert any("electrical" in n for n in names)

    def test_has_ups_hazard(self):
        names = [h["hazard"].lower() for h in self.hazards]
        assert any("ups" in n for n in names)

    # Confidence
    def test_no_false_confirmed(self):
        """Non-baseline hazards should not be confirmed from chain-derived matches."""
        for h in self.hazards:
            if h["hazard"] == "General construction hazards":
                continue
            if h["confidence"] == "confirmed":
                # Only allow confirmed if it's genuinely scope-stated
                assert "electrical" in h["hazard"].lower() or \
                       "switchboard" in h["hazard"].lower(), \
                    f"Unexpected confirmed: {h['hazard']}"

    # Phase grouping
    def test_has_multiple_phases(self):
        assert len(self.phases) >= 2, "Should have at least 2 phases"

    def test_all_hazards_have_confidence(self):
        valid = {"confirmed", "likely", "if_applicable", "requires_verification"}
        for h in self.hazards:
            assert h.get("confidence") in valid, f"Bad confidence on {h['hazard']}"


# ============================================================
# Reference Case 2: Facade Remedial Works
# ============================================================

_FACADE_DESC = (
    "External facade remedial works to a 12-storey occupied residential "
    "strata building in Sydney — scaffold access, concrete spalling repair, "
    "protective coating application, balcony waterproofing"
)


class TestFacadeRemedial:
    """RA reference: multi-trade remedial on occupied strata building."""

    def setup_method(self):
        self.result = infer_to_dict_ra(_FACADE_DESC, jurisdiction="AU")
        self.c = self.result["ra_classification"]
        self.hazards = self.result["hazard_list"]

    # Classification
    def test_job_type(self):
        # remedial or retrofit both acceptable
        assert self.c["job_type"] in ("remedial", "retrofit")

    def test_building_context(self):
        assert self.c["building_context"] == "existing"

    def test_occupied(self):
        mods = self.c["scope_modifiers"]
        assert any(m in mods for m in ("occupied_site", "occupied_interface", "strata")), \
            f"Should detect occupied context, got: {mods}"

    # Hazard relevance
    def test_hazard_count(self):
        assert 4 <= len(self.hazards) <= 20, f"Expected 4-20 hazards, got {len(self.hazards)}"

    def test_has_wah_hazard(self):
        names = [h["hazard"].lower() for h in self.hazards]
        assert any("height" in n or "fall" in n or "scaffold" in n for n in names)

    def test_has_silica_or_dust_hazard(self):
        all_text = " ".join(h["hazard"].lower() for h in self.hazards)
        all_text += " " + " ".join(
            " ".join(h.get("controls", {}).get("engineering", []))
            for h in self.hazards
        ).lower()
        assert "silica" in all_text or "dust" in all_text or "spalling" in all_text

    # HRCW
    def test_hrcw_falling_detected(self):
        flags = self.result.get("hrcw_flags", {})
        assert flags.get("falling_2m", False), "Should detect falling >2m HRCW"


# ============================================================
# Reference Case 3: Civil Infrastructure (Withers Road)
# ============================================================

_CIVIL_DESC = (
    "Partial upgrade of Withers Road, North Kellyville NSW — approximately "
    "400 metres of live lane road works, Sydney Water asset relocation, "
    "conversion from chip seal to 4 lanes, T-intersection with traffic lights, "
    "pedestrian walkways, and stormwater works"
)


class TestCivilInfrastructure:
    """RA reference: sparse-input civil road upgrade."""

    def setup_method(self):
        self.result = infer_to_dict_ra(_CIVIL_DESC, jurisdiction="AU")
        self.c = self.result["ra_classification"]
        self.hazards = self.result["hazard_list"]
        self.hrcw_reg = self.result.get("ra_hrcw_register", [])

    # Classification
    def test_job_type(self):
        assert self.c["job_type"] == "civil_infrastructure"

    def test_civil_modifiers(self):
        mods = self.c["scope_modifiers"]
        assert "road_corridor" in mods or "civil_infrastructure" in mods
        assert "live_lanes" in mods
        assert "utility_relocation" in mods
        assert "stormwater" in mods

    # Hazard count
    def test_hazard_count(self):
        assert 8 <= len(self.hazards) <= 25, f"Expected 8-25 hazards, got {len(self.hazards)}"

    # HRCW tri-state register
    def test_hrcw_register_exists(self):
        assert len(self.hrcw_reg) == 17, "Should have all 17 HRCW categories"

    def test_traffic_corridor_yes(self):
        h14 = next(h for h in self.hrcw_reg if h["ref"] == "H14")
        assert h14["status"] == "YES"

    def test_shaft_trench_yes(self):
        h07 = next(h for h in self.hrcw_reg if h["ref"] == "H07")
        assert h07["status"] == "YES"

    def test_mobile_plant_yes(self):
        h15 = next(h for h in self.hrcw_reg if h["ref"] == "H15")
        assert h15["status"] == "YES"

    def test_asbestos_conditional(self):
        h04 = next(h for h in self.hrcw_reg if h["ref"] == "H04")
        assert h04["status"] == "CONDITIONAL"

    def test_confined_space_conditional(self):
        h06 = next(h for h in self.hrcw_reg if h["ref"] == "H06")
        assert h06["status"] == "CONDITIONAL"

    def test_gas_conditional(self):
        h09 = next(h for h in self.hrcw_reg if h["ref"] == "H09")
        assert h09["status"] == "CONDITIONAL"

    def test_telecom_tower_no(self):
        h02 = next(h for h in self.hrcw_reg if h["ref"] == "H02")
        assert h02["status"] == "NO"

    def test_diving_no(self):
        h17 = next(h for h in self.hrcw_reg if h["ref"] == "H17")
        assert h17["status"] == "NO"

    def test_no_over_calling(self):
        """Categories that should be NO must remain NO."""
        must_be_no = {"H02", "H03", "H08", "H10", "H13", "H16", "H17"}
        for h in self.hrcw_reg:
            if h["ref"] in must_be_no:
                assert h["status"] == "NO", \
                    f"{h['ref']} should be NO, got {h['status']}"

    # Confidence distribution
    def test_has_confirmed_hazards(self):
        confirmed = [h for h in self.hazards if h["confidence"] == "confirmed"]
        assert len(confirmed) >= 1, "Should have at least 1 confirmed hazard"

    def test_has_conditional_hazards(self):
        conditional = [h for h in self.hazards
                       if h["confidence"] in ("if_applicable", "requires_verification")]
        assert len(conditional) >= 2, "Should have conditional hazards for sparse input"

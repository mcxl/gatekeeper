"""
Tests for the Combined WHS Control Pack data layer.

Validates build_swms_matrix(), build_control_pack(), and the
assembled data structure against the Withers Road benchmark.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.control_pack import build_control_pack, build_swms_matrix, _identify_trade_packages
from core.inference_matrix import infer_to_dict_ra


_WITHERS_DESC = (
    "Partial upgrade of Withers Road, North Kellyville NSW — approximately "
    "400 metres of live lane road works, Sydney Water asset relocation, "
    "conversion from chip seal to 4 lanes, T-intersection with traffic lights, "
    "pedestrian walkways, and stormwater works"
)

_WITHERS_META = {
    "project_name": "Withers Road Partial Upgrade",
    "site_address": "Withers Road, North Kellyville NSW 2155",
    "pcbu_name": "SD Group",
    "client": "The Hills Shire Council",
}


class TestTradePackageIdentification:

    def test_withers_road_extracts_packages(self):
        result = infer_to_dict_ra(_WITHERS_DESC, jurisdiction="AU")
        packages = _identify_trade_packages(_WITHERS_DESC, result.get("ra_hrcw_register", []))
        assert len(packages) >= 5, f"Expected at least 5 trade packages, got {len(packages)}: {packages}"

    def test_withers_road_includes_traffic_management(self):
        result = infer_to_dict_ra(_WITHERS_DESC, jurisdiction="AU")
        packages = _identify_trade_packages(_WITHERS_DESC, result.get("ra_hrcw_register", []))
        pkg_lower = [p.lower() for p in packages]
        assert any("traffic" in p or "live lane" in p or "road works" in p for p in pkg_lower), \
            f"Should include traffic management: {packages}"

    def test_withers_road_includes_sydney_water(self):
        result = infer_to_dict_ra(_WITHERS_DESC, jurisdiction="AU")
        packages = _identify_trade_packages(_WITHERS_DESC, result.get("ra_hrcw_register", []))
        pkg_lower = [p.lower() for p in packages]
        assert any("sydney water" in p or "water" in p for p in pkg_lower), f"Should include Sydney Water: {packages}"

    def test_withers_road_includes_stormwater(self):
        result = infer_to_dict_ra(_WITHERS_DESC, jurisdiction="AU")
        packages = _identify_trade_packages(_WITHERS_DESC, result.get("ra_hrcw_register", []))
        pkg_lower = [p.lower() for p in packages]
        assert any("stormwater" in p or "drainage" in p for p in pkg_lower), f"Should include stormwater: {packages}"


class TestBuildSwmsMatrix:

    def test_matrix_from_packages(self):
        result = infer_to_dict_ra(_WITHERS_DESC, jurisdiction="AU")
        hrcw = result.get("ra_hrcw_register", [])
        packages = _identify_trade_packages(_WITHERS_DESC, hrcw)
        matrix = build_swms_matrix(packages, hrcw)
        assert len(matrix) >= 4, f"Expected at least 4 SWMS entries, got {len(matrix)}"

    def test_matrix_entries_have_required_fields(self):
        result = infer_to_dict_ra(_WITHERS_DESC, jurisdiction="AU")
        hrcw = result.get("ra_hrcw_register", [])
        packages = _identify_trade_packages(_WITHERS_DESC, hrcw)
        matrix = build_swms_matrix(packages, hrcw)
        for entry in matrix:
            assert "trade_package" in entry
            assert "hrcw_refs" in entry
            assert "swms_title" in entry
            assert "required_before" in entry

    def test_traffic_management_has_h14(self):
        result = infer_to_dict_ra(_WITHERS_DESC, jurisdiction="AU")
        hrcw = result.get("ra_hrcw_register", [])
        matrix = build_swms_matrix(["traffic management"], hrcw)
        tm = [m for m in matrix if "traffic" in m["swms_title"].lower()]
        assert tm, "Should have traffic management entry"
        assert "H14" in tm[0]["hrcw_refs"], "Traffic management should reference H14"


class TestBuildControlPack:

    def setup_method(self):
        self.pack = build_control_pack(
            description=_WITHERS_DESC,
            project_meta=_WITHERS_META,
            jurisdiction="AU",
        )

    def test_document_type(self):
        assert self.pack["document_type"] == "combined_whs_control_pack"

    def test_project_meta_populated(self):
        meta = self.pack["project_meta"]
        assert meta["project_name"] == "Withers Road Partial Upgrade"
        assert meta["pcbu"] == "SD Group"
        assert meta["client"] == "The Hills Shire Council"

    def test_classification_is_civil(self):
        c = self.pack["ra_classification"]
        assert c["job_type"] == "civil_infrastructure"

    def test_hrcw_register_complete(self):
        assert len(self.pack["hrcw_register"]) == 17

    def test_hrcw_has_yes_entries(self):
        yes = [h for h in self.pack["hrcw_register"] if h["status"] == "YES"]
        assert len(yes) >= 3, f"Expected at least 3 YES HRCW, got {len(yes)}"

    def test_hrcw_has_conditional_entries(self):
        cond = [h for h in self.pack["hrcw_register"] if h["status"] == "CONDITIONAL"]
        assert len(cond) >= 3, f"Expected at least 3 CONDITIONAL HRCW, got {len(cond)}"

    def test_swms_matrix_populated(self):
        assert len(self.pack["swms_matrix"]) >= 4, \
            f"Expected at least 4 SWMS matrix entries, got {len(self.pack['swms_matrix'])}"

    def test_hold_points_populated(self):
        assert len(self.pack["hold_points"]) >= 3, \
            f"Expected at least 3 hold points, got {len(self.pack['hold_points'])}"

    def test_hold_points_have_structure(self):
        for hp in self.pack["hold_points"]:
            assert "ref" in hp
            assert "name" in hp
            assert "condition" in hp
            assert "authorised_by" in hp
            assert "evidence_required" in hp

    def test_risk_register_populated(self):
        assert len(self.pack["risk_register"]) >= 8, \
            f"Expected at least 8 risk register entries, got {len(self.pack['risk_register'])}"

    def test_risk_register_grouped(self):
        groups = {r["group"] for r in self.pack["risk_register"]}
        assert len(groups) >= 2, f"Expected at least 2 risk register groups, got {groups}"

    def test_risk_register_has_controls(self):
        for r in self.pack["risk_register"]:
            assert r.get("controls"), f"Risk entry {r['ref']} has no controls"

    def test_scope_summary_present(self):
        assert len(self.pack["scope_summary"]) > 50

    def test_review_meta_present(self):
        rm = self.pack["review_meta"]
        assert rm["review_status"] == "draft"
        assert len(rm["open_items"]) >= 1

    def test_open_items_include_conditional_hrcw(self):
        items = self.pack["review_meta"]["open_items"]
        hrcw_items = [i for i in items if i["source"] == "hrcw_register"]
        assert len(hrcw_items) >= 3, f"Expected conditional HRCW in open items, got {len(hrcw_items)}"

    def test_open_items_include_trade_confirmation(self):
        items = self.pack["review_meta"]["open_items"]
        trade_items = [i for i in items if "trade package" in i["item"].lower()]
        assert len(trade_items) >= 1, "Should flag trade packages as needing confirmation"

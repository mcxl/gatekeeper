"""Tests for SWMS scope classifier."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.inference_matrix import classify_swms_scope


class TestClassifySwmsScope:

    def test_facade_remedial_benchmark(self):
        """Benchmark case: facade remedial works on occupied strata building."""
        desc = (
            "External facade remedial works to a 12-storey occupied residential "
            "strata building in Sydney - scaffold access, concrete spalling repair, "
            "protective coating application, balcony waterproofing"
        )
        c = classify_swms_scope(desc)
        assert c["job_type"] == "remedial"
        assert c["building_context"] == "existing"
        assert c["occupancy_context"] == "occupied"
        assert "facade_work" in c["scope_modifiers"]
        assert "scaffold_access" in c["scope_modifiers"]
        assert "residential" in c["scope_modifiers"]
        assert "strata" in c["scope_modifiers"]
        assert "concrete_repair" in c["scope_modifiers"]
        assert "waterproofing" in c["scope_modifiers"]
        assert "protective_coating" in c["scope_modifiers"]

    def test_new_build_warehouse(self):
        desc = "New construction of steel-framed warehouse on greenfield site"
        c = classify_swms_scope(desc)
        assert c["job_type"] == "new_build"
        assert c["building_context"] == "new"
        assert c["occupancy_context"] == "unoccupied"

    def test_demolition(self):
        desc = "Demolition of existing two-storey masonry building"
        c = classify_swms_scope(desc)
        assert c["job_type"] == "demolition"
        assert c["building_context"] == "existing"

    def test_fitout_occupied(self):
        desc = "Office fit out on level 5 of occupied commercial tower"
        c = classify_swms_scope(desc)
        assert c["job_type"] == "fit_out"
        assert c["occupancy_context"] == "occupied"
        assert "commercial" in c["scope_modifiers"]

    def test_maintenance(self):
        desc = "Routine maintenance and repair of existing HVAC system in hospital"
        c = classify_swms_scope(desc)
        assert c["job_type"] == "maintenance"
        assert c["building_context"] == "existing"

    def test_scaffold_modifier(self):
        desc = "Scaffold erection for painting works"
        c = classify_swms_scope(desc)
        assert "scaffold_access" in c["scope_modifiers"]

    def test_rope_access_modifier(self):
        desc = "Rope access facade inspection using IRATA technicians"
        c = classify_swms_scope(desc)
        assert "rope_access" in c["scope_modifiers"]
        assert "facade_work" in c["scope_modifiers"]

    def test_high_rise_modifier(self):
        desc = "External works to 20 storey residential apartment tower"
        c = classify_swms_scope(desc)
        assert "high_rise" in c["scope_modifiers"]
        assert "residential" in c["scope_modifiers"]

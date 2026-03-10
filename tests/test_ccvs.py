#!/usr/bin/env python3
"""tests/test_ccvs.py — CCVS code validation tests."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from renderers.docx_renderer import validate_ccvs_code, sanitise_text
from core.validate import guard_tasks, strip_hallucinated_refs


class TestValidateCcvsCode:
    def test_valid_codes_pass(self):
        assert validate_ccvs_code("WAH-H6") == "WAH-H6"
        assert validate_ccvs_code("SIL-M4") == "SIL-M4"
        assert validate_ccvs_code("ELE-H9") == "ELE-H9"
        assert validate_ccvs_code("N/A") == "N/A"

    def test_missing_hyphen_repaired(self):
        assert validate_ccvs_code("WAHH6") == "WAH-H6"
        assert validate_ccvs_code("SILM4") == "SIL-M4"
        assert validate_ccvs_code("CHML2") == "CHM-L2"
        assert validate_ccvs_code("ELEH9") == "ELE-H9"

    def test_invalid_code_returns_na(self):
        assert validate_ccvs_code("SYS-H6") == "N/A"  # SYS not a valid stream
        assert validate_ccvs_code("XXXX") == "N/A"
        assert validate_ccvs_code("") == "N/A"
        assert validate_ccvs_code(None) == "N/A"

    def test_already_na(self):
        assert validate_ccvs_code("N/A") == "N/A"


class TestSanitiseText:
    def test_duplicate_steel_capped(self):
        assert sanitise_text("steel-capped steel-capped footwear") == "steel-capped footwear"

    def test_duplicate_cut_resistant(self):
        assert sanitise_text("cut-resistant cut-resistant gloves") == "cut-resistant gloves"

    def test_double_space(self):
        assert sanitise_text("hello  world") == "hello world"

    def test_clean_text_unchanged(self):
        assert sanitise_text("steel-capped footwear") == "steel-capped footwear"


class TestGuardTasks:
    def test_wah_flag_false_for_non_wah(self):
        task = {"ccvs_code": "ELE-E1", "wah_applicable": True, "admin_controls": []}
        guard_tasks([task])
        assert task["wah_applicable"] is False

    def test_wah_flag_kept_for_wah(self):
        task = {"ccvs_code": "WAH-H6", "wah_applicable": True, "admin_controls": []}
        guard_tasks([task])
        assert task["wah_applicable"] is True

    def test_admin_cap_at_20(self):
        task = {"ccvs_code": "", "admin_controls": list(range(25))}
        guard_tasks([task])
        assert len(task["admin_controls"]) == 20


class TestStripHallucinatedRefs:
    def test_removes_hallucinated(self):
        refs = ["WHS Act 2011", "AS/NZS 3580", "SafeWork NSW"]
        result = strip_hallucinated_refs(refs)
        assert "AS/NZS 3580" not in result
        assert len(result) == 2

    def test_keeps_valid_refs(self):
        refs = ["WHS Act 2011", "SafeWork NSW"]
        assert strip_hallucinated_refs(refs) == refs


class TestHrcwCheckbox:
    def test_double_space_checkbox(self):
        """HRCW [  ] double-space should be ticked by regex."""
        import re
        pattern = re.compile(r'\[\s*\]')
        assert pattern.sub('[✓]', '[  ]') == '[✓]'
        assert pattern.sub('[✓]', '[   ]') == '[✓]'
        assert pattern.sub('[✓]', '[]') == '[✓]'

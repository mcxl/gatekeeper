#!/usr/bin/env python3
"""tests/test_ccvs.py — CCVS code validation tests."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from renderers.docx_renderer import validate_ccvs_code, sanitise_text


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

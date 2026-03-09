#!/usr/bin/env python3
"""
tests/test_standards_registry.py — Verify standards registry and validation.

Usage:
    python -m pytest tests/test_standards_registry.py -v
    or:
    python tests/test_standards_registry.py
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import pytest
from vocab.standards_registry import (
    VERIFIED_STANDARDS,
    get_verified_standards,
    validate_standard_citations,
    strip_unverified_citations,
    detect_jurisdiction_from_query,
)


# ── Test 1: Standards retrieval AU ───────────────────────────────────────────

class TestStandardsRetrievalAU:
    def test_au_wah_and_silica(self):
        """get_verified_standards('AU', ['WAH-H6', 'SIL-H6']) returns WAH + silica standards."""
        standards = get_verified_standards("AU", ["WAH-H6", "SIL-H6"])

        # WAH standards present
        has_fall_arrest = any("1891" in s for s in standards)
        has_fall_code = any("Falls at Workplaces" in s for s in standards)
        assert has_fall_arrest, f"Expected AS/NZS 1891 in standards, got: {standards}"
        assert has_fall_code, f"Expected Falls CoP in standards"

        # Silica standards present
        has_silica = any("Silica" in s or "1716" in s for s in standards)
        assert has_silica, f"Expected silica standards, got: {standards}"

        # General construction included
        has_general = any("Construction Work" in s for s in standards)
        assert has_general, f"Expected general construction CoP"

    def test_au_general_included_by_default(self):
        standards = get_verified_standards("AU", [])
        assert any("Construction Work" in s for s in standards)

    def test_au_general_excluded_when_disabled(self):
        standards = get_verified_standards("AU", [], include_general=False)
        assert len(standards) == 0


# ── Test 2: Standards retrieval UK ───────────────────────────────────────────

class TestStandardsRetrievalUK:
    def test_uk_electrical_and_confined(self):
        """get_verified_standards('UK', ['ELE', 'CFS']) returns electrical + confined space standards."""
        standards = get_verified_standards("UK", ["ELE", "CFS"])

        # Electrical
        has_elec = any("Electricity at Work" in s or "7671" in s for s in standards)
        assert has_elec, f"Expected UK electrical standards, got: {standards}"

        # Confined space
        has_confined = any("Confined Spaces Regulations 1997" in s for s in standards)
        assert has_confined, f"Expected Confined Spaces Regulations"

        # CDM should be in general
        has_cdm = any("CDM" in s or "Construction (Design" in s for s in standards)
        assert has_cdm, f"Expected CDM in general construction"

        # LOLER should NOT be present (not in ELE or CFS)
        has_loler = any("LOLER" in s for s in standards)
        assert not has_loler, "LOLER should not be in ELE/CFS categories"


# ── Test 3: Hallucination strip ──────────────────────────────────────────────

class TestHallucinationStrip:
    def test_strip_fake_preserve_real(self):
        """AS/NZS 9999 stripped, AS/NZS 1891.1 preserved."""
        text = (
            "Use AS/NZS 9999 — fake standard and "
            "AS/NZS 1891.1 — real standard for fall arrest"
        )
        result = strip_unverified_citations(text, "AU", ["WAH"])
        assert "AS/NZS 9999" not in result, f"Fake standard not stripped: {result}"
        assert "AS/NZS 1891" in result, f"Real standard stripped: {result}"

    def test_validate_detects_fake(self):
        text = "Comply with AS/NZS 9999 and AS/NZS 3012"
        result = validate_standard_citations(text, "AU", ["ELE"])
        assert result["flag_count"] >= 1
        assert any("9999" in f for f in result["flagged"])
        assert any("3012" in v for v in result["verified"])

    def test_no_false_positives_on_clean_text(self):
        text = "Workers must wear steel-capped footwear and eye protection at all times"
        result = validate_standard_citations(text, "AU", ["WAH"])
        assert result["flag_count"] == 0


# ── Test 4: Jurisdiction mismatch detection ──────────────────────────────────

class TestJurisdictionMismatch:
    def test_uk_signals_detected(self):
        """CDM + HSE + principal designer → UK detected when AU selected."""
        query = "CDM notification required, principal designer appointed, HSE inspection expected"
        result = detect_jurisdiction_from_query(query, "AU")
        assert result["mismatch"] is True, f"Expected mismatch, got: {result}"
        assert result["detected"] == "UK", f"Expected UK, got: {result['detected']}"

    def test_no_mismatch_when_correct(self):
        query = "SWMS required for HRCW, SafeWork NSW notification"
        result = detect_jurisdiction_from_query(query, "AU")
        assert result["mismatch"] is False

    def test_us_signals(self):
        query = "OSHA inspection, 29 CFR compliance, NIOSH guidelines"
        result = detect_jurisdiction_from_query(query, "AU")
        assert result["mismatch"] is True
        assert result["detected"] == "US"

    def test_ca_signals(self):
        query = "Ontario O. Reg 213/91, WSIB requirements, WHMIS training"
        result = detect_jurisdiction_from_query(query, "AU")
        assert result["mismatch"] is True
        assert result["detected"] == "CA"


# ── Test 5: Full generation pass AU ──────────────────────────────────────────

class TestFullGenerationAU:
    def test_au_silica_swms_standards(self):
        """Generate SWMS for silica AU, check legislation cell has verified standards."""
        from core.inference_matrix import infer_to_dict
        from core.schema import TaskBlock
        from renderers.docx_renderer import render_swms_document
        from io import BytesIO
        from docx import Document

        inference = infer_to_dict("concrete grinding silica dust ground level", jurisdiction="AU")

        tasks = [TaskBlock(
            task="Concrete grinding",
            scope="Silica dust control — ground level",
            risk_pre="H", risk_post="M",
            controls=["Water suppression on grinder", "HEPA vacuum at source", "Exclusion zone 5m"],
            ppe=["P2 respirator (minimum)", "steel-capped footwear", "eye protection"],
            ccvs_code="SIL-H6",
            responsibility={"SUP": "Supervise task", "WKR": "Perform task per SWMS"},
        )]
        meta = {
            "project_name": "Standards Test AU",
            "site_address": "Sydney NSW",
            "principal_contractor": "mCXI",
            "version": "1.0",
        }

        docx_bytes = render_swms_document(tasks, meta, inference, jurisdiction="AU")
        doc = Document(BytesIO(docx_bytes))

        # Extract all text
        all_text = []
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    all_text.append(cell.text)
        text = " ".join(all_text)

        # Verify legislation present
        assert "Model WHS Act 2011" in text, "Missing Model WHS Act 2011 in legislation"

        # Validate no unverified citations in task controls
        control_text = " ".join(c for t in tasks for c in t.controls)
        result = validate_standard_citations(control_text, "AU", ["SIL-H6"])
        assert result["flag_count"] == 0, f"Unverified citations in controls: {result['flagged']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

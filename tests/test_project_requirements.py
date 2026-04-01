"""
tests/test_project_requirements.py — Tests for project requirements intake v1.
"""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.intake_extractor import ExtractionResult, extract_from_text
from core.project_requirements import (
    normalize_project_requirements,
    _detect_hrcw_requirements,
    _detect_site_constraints,
    _extract_named_authorities,
    _extract_rules,
    _HOLD_POINT_PATTERNS,
    _PERMIT_PATTERNS,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ── HRCW detection ──────────────────────────────────────────────────────────

class TestHrcwDetection:
    def test_fall_prevention_detected(self):
        text = "All work at height requires harness and edge protection. Scaffold access only."
        reqs = _detect_hrcw_requirements(text)
        categories = [r["category"] for r in reqs]
        assert "fall_prevention" in categories

    def test_crane_detected(self):
        text = "Mobile crane to be used for all lifts. Dogman required on site."
        reqs = _detect_hrcw_requirements(text)
        categories = [r["category"] for r in reqs]
        assert "crane_hoist" in categories

    def test_asbestos_detected(self):
        text = "Asbestos survey completed. Class B ACM removal required before demolition."
        reqs = _detect_hrcw_requirements(text)
        categories = [r["category"] for r in reqs]
        assert "asbestos" in categories

    def test_no_hrcw_on_clean_text(self):
        text = "General office administration and filing work."
        reqs = _detect_hrcw_requirements(text)
        assert len(reqs) == 0

    def test_multiple_categories(self):
        text = "Scaffold erection and crane lifting in confined space with excavation near live electrical."
        reqs = _detect_hrcw_requirements(text)
        categories = [r["category"] for r in reqs]
        assert len(categories) >= 3


# ── Site constraints ────────────────────────────────────────────────────────

class TestSiteConstraints:
    def test_occupied_building(self):
        text = "Building is occupied with tenants on floors 1-5."
        constraints = _detect_site_constraints(text)
        types = [c["constraint"] for c in constraints]
        assert "occupied_building" in types

    def test_live_traffic(self):
        text = "Works within live traffic corridor. CTMP required."
        constraints = _detect_site_constraints(text)
        types = [c["constraint"] for c in constraints]
        assert "live_traffic" in types

    def test_restricted_hours(self):
        text = "Night works permitted. Noise curfew 10pm-7am."
        constraints = _detect_site_constraints(text)
        types = [c["constraint"] for c in constraints]
        assert "restricted_hours" in types

    def test_no_constraints(self):
        text = "Standard greenfield construction site."
        constraints = _detect_site_constraints(text)
        assert len(constraints) == 0


# ── Rule extraction ─────────────────────────────────────────────────────────

class TestRuleExtraction:
    def test_hold_point_extracted(self):
        text = "Hold point: engineer inspection of formwork before pour commences."
        rules = _extract_rules(text, _HOLD_POINT_PATTERNS)
        assert len(rules) >= 1

    def test_permit_extracted(self):
        text = "Hot work permit required for all welding and cutting operations."
        rules = _extract_rules(text, _PERMIT_PATTERNS)
        assert len(rules) >= 1

    def test_no_rules_from_generic(self):
        text = "Please complete the work safely."
        rules = _extract_rules(text, _HOLD_POINT_PATTERNS)
        assert len(rules) == 0


# ── Named authorities ───────────────────────────────────────────────────────

class TestNamedAuthorities:
    def test_named_consultant(self):
        text = "Engineer: Smith and Associates to inspect all structural connections."
        authorities = _extract_named_authorities(text)
        assert len(authorities) >= 1

    def test_no_authorities(self):
        text = "Complete the work as per the drawings."
        authorities = _extract_named_authorities(text)
        assert len(authorities) == 0


# ── Full normalization ──────────────────────────────────────────────────────

class TestNormalization:
    def test_rich_project_requirements(self):
        text = (
            "Project: Level 3 Podium Slab — Apex Commercial Constructions\n"
            "Principal Contractor: SD Group\n"
            "Site Address: 100 George Street Parramatta NSW 2150\n\n"
            "All work at height requires scaffold with edge protection.\n"
            "Crane operations require approved lift plan and dogman.\n"
            "Hold point: engineer inspection of formwork before pour.\n"
            "Hold point: structural engineer sign-off before prop removal.\n"
            "Hot work permit required for all cutting and welding.\n"
            "Confined space entry permit required for riser access.\n"
            "Building is occupied — tenants on floors 1-4.\n"
            "Night works restricted: no work between 10pm and 7am.\n"
            "Mandatory PPE: hard hat, safety boots, hi-vis vest, safety glasses.\n"
            "Site induction required before first entry.\n"
            "Consultant: Leo and Associates for structural inspections.\n"
        )
        extraction = extract_from_text(text)
        result = normalize_project_requirements(extraction)

        assert result["pack_version"] == "1.0"
        assert result["requires_review"] is True
        assert result["status"] == "draft"

        pack = result["project_rule_pack"]
        assert "Apex" in pack["project_identity"]["project_name"]["value"] or "Podium" in pack["project_identity"]["project_name"]["value"]
        assert "SD Group" in pack["project_identity"]["principal_contractor"]["value"]
        assert len(pack["hrcw_requirements"]) >= 2
        assert len(pack["site_constraints"]) >= 2
        assert len(pack["hold_points"]) >= 1
        assert len(pack["permit_requirements"]) >= 1
        assert len(pack["named_authorities"]) >= 1

    def test_minimal_text_leaves_unresolved(self):
        text = "Please prepare safety requirements for the upcoming project."
        extraction = extract_from_text(text)
        result = normalize_project_requirements(extraction)

        assert result["requires_review"] is True
        assert len(result["unresolved_fields"]) > 0
        assert len(result["review_prompts"]) > 0

    def test_review_prompts_always_present(self):
        text = "Scaffold erection at 10 Main St Sydney NSW 2000 for Builder Corp."
        extraction = extract_from_text(text)
        result = normalize_project_requirements(extraction)
        assert any("CONFIRM" in p for p in result["review_prompts"])

    def test_extraction_warnings_passed_through(self):
        r = ExtractionResult(
            raw_text="Short",
            source_type="pasted_text",
            warnings=["extraction_insufficient: too short"],
        )
        result = normalize_project_requirements(r)
        assert "extraction_insufficient: too short" in result["extraction_warnings"]

    def test_mandatory_review_always_true(self):
        text = (
            "Project: Perfect Project\n"
            "Principal Contractor: Known Builder\n"
            "Address: 1 Perfect St Sydney NSW 2000\n"
            "All scaffold work requires edge protection and harness."
        )
        extraction = extract_from_text(text)
        result = normalize_project_requirements(extraction)
        assert result["requires_review"] is True
        assert result["status"] == "draft"

    def test_clarification_note_included(self):
        text = "Scaffold erection project at warehouse site."
        extraction = extract_from_text(text)
        result = normalize_project_requirements(
            extraction, clarification_note="Principal contractor is SD Group"
        )
        raw = result["project_rule_pack"]["raw_requirements_text"]
        assert "SD Group" in raw


# ── API endpoint ────────────────────────────────────────────────────────────

class TestProjectRequirementsEndpoint:
    def test_text_intake(self):
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)

        response = client.post(
            "/v1/project/requirements",
            data={
                "source_text": (
                    "Project: Warehouse Extension\n"
                    "Principal Contractor: Apex Constructions\n"
                    "Site: 50 Industry Drive Campbelltown NSW 2560\n"
                    "All crane operations require approved lift plan.\n"
                    "Scaffold must have edge protection before access.\n"
                    "Hold point: engineer inspection before concrete pour.\n"
                    "Building is occupied — warehouse operational during works."
                ),
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["pack_version"] == "1.0"
        assert body["requires_review"] is True
        assert body["status"] == "draft"
        assert len(body["project_rule_pack"]["hrcw_requirements"]) >= 1

    def test_empty_input_returns_400(self):
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)

        response = client.post("/v1/project/requirements", data={})
        assert response.status_code == 400

    def test_docx_file_intake(self):
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)

        path = FIXTURES_DIR / "test_swms_minimal.docx"
        if not path.exists():
            pytest.skip("DOCX fixture not available")

        with open(path, "rb") as f:
            response = client.post(
                "/v1/project/requirements",
                files={"source_file": ("reqs.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            )
        assert response.status_code == 200
        body = response.json()
        assert body["source_metadata"]["source_type"] == "docx_text"
        assert body["requires_review"] is True

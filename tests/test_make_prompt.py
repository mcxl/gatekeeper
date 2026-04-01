"""
tests/test_make_prompt.py — Tests for the prompt generation workflow.
"""

import json
import os
import shutil
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.make_prompt import (
    find_placeholders,
    format_field,
    list_assets,
    load_partial,
    render,
    resolve_partials,
)


# ── Partials ────────────────────────────────────────────────────────────────

class TestPartials:
    def test_load_headless_header(self):
        text = load_partial("headless_header")
        assert "Read SESSION_START.md" in text

    def test_load_standing_rules(self):
        text = load_partial("standing_rules")
        assert "Run pytest" in text

    def test_load_stop_and_report(self):
        text = load_partial("stop_and_report")
        assert "stop report" in text.lower()

    def test_missing_partial_raises(self):
        with pytest.raises(FileNotFoundError):
            load_partial("nonexistent_partial_xyz")


class TestResolvePartials:
    def test_resolve_single_partial(self):
        text = "Before\n{{>headless_header}}\nAfter"
        result = resolve_partials(text)
        assert "{{>headless_header}}" not in result
        assert "Read SESSION_START.md" in result
        assert "Before" in result
        assert "After" in result

    def test_resolve_multiple_partials(self):
        text = "{{>headless_header}}\n\n{{>standing_rules}}"
        result = resolve_partials(text)
        assert "Read SESSION_START.md" in result
        assert "Run pytest" in result


# ── Placeholders ────────────────────────────────────────────────────────────

class TestPlaceholders:
    def test_find_field_placeholders(self):
        text = "Hello {{customer}}, job {{job_type}} with {{>partial}}"
        result = find_placeholders(text)
        assert "customer" in result
        assert "job_type" in result
        assert "partial" not in result  # partials excluded

    def test_no_placeholders(self):
        assert find_placeholders("No placeholders here") == []


# ── Format field ────────────────────────────────────────────────────────────

class TestFormatField:
    def test_scope_modifiers_comma_separated(self):
        result = format_field("scope_modifiers", ["a", "b", "c"])
        assert result == "a, b, c"

    def test_quick_scan_focus_bulleted(self):
        result = format_field("quick_scan_focus", ["item one", "item two"])
        assert "   - item one" in result
        assert "   - item two" in result

    def test_string_passthrough(self):
        assert format_field("customer", "Acme Corp") == "Acme Corp"

    def test_none_returns_empty(self):
        assert format_field("x", None) == ""


# ── Render ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_brief(tmp_path):
    """Create a temporary brief for testing."""
    brief = {
        "customer": "Test Corp",
        "project": "Test project description",
        "job_type": "new_build",
        "scope_modifiers": ["mod_a", "mod_b"],
        "scope_of_works": "Do the work.",
        "quick_scan_focus": ["check A", "check B"],
        "last_used": None,
        "jobs_run": 0,
    }
    path = tmp_path / "test_brief.json"
    path.write_text(json.dumps(brief, indent=2), encoding="utf-8")
    return path


class TestRender:
    def test_successful_render(self, tmp_brief):
        result = render("next_pilot_job", str(tmp_brief))
        assert "Test Corp" in result
        assert "Test project description" in result
        assert "new_build" in result
        assert "mod_a, mod_b" in result
        assert "Do the work." in result
        assert "   - check A" in result
        assert "Read SESSION_START.md" in result  # from partial

    def test_missing_field_raises(self, tmp_path):
        brief = {"customer": "Incomplete"}
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(brief), encoding="utf-8")
        with pytest.raises(ValueError, match="Missing required fields"):
            render("next_pilot_job", str(path))

    def test_missing_template_raises(self, tmp_brief):
        with pytest.raises(FileNotFoundError):
            render("nonexistent_template_xyz", str(tmp_brief))

    def test_missing_brief_raises(self):
        with pytest.raises(FileNotFoundError):
            render("next_pilot_job", "/nonexistent/path.json")


class TestDryRun:
    def test_dry_run_shows_fields(self, tmp_brief):
        result = render("next_pilot_job", str(tmp_brief), dry_run=True)
        assert "[OK]" in result
        assert "customer" in result
        assert "ready to render" in result.lower()

    def test_dry_run_shows_missing(self, tmp_path):
        brief = {"customer": "Only Customer"}
        path = tmp_path / "partial.json"
        path.write_text(json.dumps(brief), encoding="utf-8")
        result = render("next_pilot_job", str(path), dry_run=True)
        assert "[MISSING]" in result
        assert "missing field" in result.lower()


class TestMetadataUpdate:
    def test_last_used_updated(self, tmp_brief):
        render("next_pilot_job", str(tmp_brief))
        with open(tmp_brief, encoding="utf-8") as f:
            updated = json.load(f)
        assert updated["last_used"] is not None
        assert "T" in updated["last_used"]  # ISO format

    def test_jobs_run_incremented(self, tmp_brief):
        render("next_pilot_job", str(tmp_brief))
        with open(tmp_brief, encoding="utf-8") as f:
            updated = json.load(f)
        assert updated["jobs_run"] == 1

    def test_jobs_run_increments_twice(self, tmp_brief):
        render("next_pilot_job", str(tmp_brief))
        render("next_pilot_job", str(tmp_brief))
        with open(tmp_brief, encoding="utf-8") as f:
            updated = json.load(f)
        assert updated["jobs_run"] == 2

    def test_dry_run_does_not_update(self, tmp_brief):
        render("next_pilot_job", str(tmp_brief), dry_run=True)
        with open(tmp_brief, encoding="utf-8") as f:
            data = json.load(f)
        assert data["last_used"] is None
        assert data["jobs_run"] == 0


class TestListAssets:
    def test_list_contains_templates(self):
        result = list_assets()
        assert "next_pilot_job" in result
        assert "tracking_update" in result

    def test_list_contains_partials(self):
        result = list_assets()
        assert "_headless_header" in result

    def test_list_contains_briefs(self):
        result = list_assets()
        assert "urban_flow_plumbing.json" in result

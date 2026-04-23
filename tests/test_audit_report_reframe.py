"""Tests for the deterministic checklist-instruction reframer."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from pims import audit_report_docx as arpt


@pytest.fixture(autouse=True)
def _isolate_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(arpt, "DATA_DIR", tmp_path)
    monkeypatch.setattr(arpt, "REFRAME_CACHE_PATH", tmp_path / "reframe_cache.jsonl")
    yield


def test_golden_example_check_leading_verb():
    out = arpt.reframe_instruction(
        "Check all workers have completed required inductions and training"
    )
    assert out == "All workers have completed required inductions and training."


def test_strips_verify_that():
    out = arpt.reframe_instruction("Verify that the scaffold tag is current")
    assert out == "The scaffold tag is current."


def test_strips_ensure_confirm_inspect_review():
    assert arpt.reframe_instruction("Ensure PPE is available").endswith(".")
    assert arpt.reframe_instruction("Confirm isolation is in place").startswith("Isolation")
    assert arpt.reframe_instruction("Inspect harnesses").startswith("Harnesses")
    assert arpt.reframe_instruction("Review SWMS").startswith("SWMS")


def test_adds_period_once():
    out = arpt.reframe_instruction("Check the site is clean.")
    assert out.endswith(".")
    assert not out.endswith("..")


def test_empty_input():
    assert arpt.reframe_instruction("") == ""
    assert arpt.reframe_instruction("   ") == ""


def test_cache_roundtrip(tmp_path):
    first = arpt.reframe_instruction("Check gates are locked")
    # Second call should hit cache (no exception, same answer).
    second = arpt.reframe_instruction("Check gates are locked")
    assert first == second == "Gates are locked."
    assert arpt.REFRAME_CACHE_PATH.exists()

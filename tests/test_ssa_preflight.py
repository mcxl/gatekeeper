"""Phase 4 preflight tests for the SSA pipeline.

Covers all gatekeeper-native checks via a "make good folder, mutate one
aspect, assert blocks" pattern.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from pims.services.ssa_quality.preflight import (
    CheckResult,
    format_results,
    run_preflight,
)


def _make_good_folder(tmp_path: Path) -> Path:
    folder = tmp_path / "2026-05-01-SDG-01"
    folder.mkdir()
    (folder / "Evidence_Master.csv").write_text(
        "timestamp,observation,filename\n"
        "2026-05-01_09-00-00,Top rail missing,a.jpg\n",
        encoding="utf-8",
    )
    Image.new("RGB", (400, 300), "red").save(folder / "a.jpg", "JPEG")
    return folder


def test_preflight_clean_folder_passes(tmp_path, monkeypatch):
    """A folder with the canonical inputs passes hard checks. Tool
    availability is informational so missing tools don't block."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # keep informational green
    folder = _make_good_folder(tmp_path)
    results, hard_pass = run_preflight(folder)
    assert hard_pass, format_results(results, use_colour=False)
    # All hard checks (non-informational) must be green.
    for r in results:
        if not r.informational:
            assert r.passed, f"hard check failed: {r.label} — {r.detail}"


def test_preflight_bad_folder_name_blocks(tmp_path):
    """A folder whose name doesn't match the contract must block."""
    folder = tmp_path / "bad-folder-name"
    folder.mkdir()
    results, hard_pass = run_preflight(folder)
    assert not hard_pass
    name_check = next(r for r in results if "Folder name" in r.label)
    assert not name_check.passed
    assert not name_check.informational


def test_preflight_missing_csv_blocks(tmp_path):
    """Missing Evidence_Master.csv must block and the dependent checks
    must show (skipped) detail, not silently pass."""
    folder = _make_good_folder(tmp_path)
    (folder / "Evidence_Master.csv").unlink()
    results, hard_pass = run_preflight(folder)
    assert not hard_pass
    csv_checks = [r for r in results if "Evidence_Master" in r.label]
    assert len(csv_checks) == 3  # exists / headers / rows
    assert not any(r.passed for r in csv_checks)
    assert any("skipped" in r.detail for r in csv_checks[1:])


def test_preflight_bad_csv_headers_blocks(tmp_path):
    """A CSV with the wrong header row must fail the header check but
    still pass the existence check."""
    folder = _make_good_folder(tmp_path)
    (folder / "Evidence_Master.csv").write_text(
        "wrong,header,names\nrow,row,row\n", encoding="utf-8",
    )
    results, hard_pass = run_preflight(folder)
    assert not hard_pass
    exists_check = next(r for r in results if "exists in folder root" in r.label)
    header_check = next(r for r in results if "expected headers" in r.label)
    assert exists_check.passed
    assert not header_check.passed
    assert "wrong" in header_check.detail


def test_preflight_empty_csv_blocks(tmp_path):
    """Header-only CSV (no data rows) must block."""
    folder = _make_good_folder(tmp_path)
    (folder / "Evidence_Master.csv").write_text(
        "timestamp,observation,filename\n", encoding="utf-8",
    )
    results, hard_pass = run_preflight(folder)
    assert not hard_pass
    row_check = next(r for r in results if "at least one data row" in r.label)
    assert not row_check.passed


def test_preflight_no_images_blocks(tmp_path):
    """No images in the folder root must block."""
    folder = _make_good_folder(tmp_path)
    (folder / "a.jpg").unlink()
    results, hard_pass = run_preflight(folder)
    assert not hard_pass
    img_check = next(r for r in results if "at least one image" in r.label)
    assert not img_check.passed


def test_preflight_missing_anthropic_key_is_informational(tmp_path, monkeypatch):
    """Missing ANTHROPIC_API_KEY warns but does not block — hard_pass
    stays True since the build can still run with --no-enrich."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    folder = _make_good_folder(tmp_path)
    results, hard_pass = run_preflight(folder)
    assert hard_pass
    key_check = next(r for r in results if "ANTHROPIC_API_KEY" in r.label)
    assert not key_check.passed
    assert key_check.informational


def test_format_results_renders_all_marks(tmp_path, monkeypatch):
    """format_results must produce one of [X] / [!] / [ ] for every check."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    folder = _make_good_folder(tmp_path)
    results, _ = run_preflight(folder)
    rendered = format_results(results, use_colour=False)
    assert "[X]" in rendered
    for line in rendered.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        assert stripped.startswith(("[X]", "[!]", "[ ]")), stripped

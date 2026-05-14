"""Phase 3 headless LibreOffice smoke-test tests.

Three scenarios:
1. A clean build_ssa_report_docx output round-trips through soffice
   cleanly (available=True, success=True, no failure_detail).
2. A docx with its word/document.xml removed produces an
   available=True, success=False result (soffice can't render it).
3. When soffice isn't reachable the smoke check returns
   available=False with a populated skip_reason.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from PIL import Image

from pims.services.ssa_pipeline import (
    EnrichedRow,
    ObservationRow,
    build_ssa_report_docx,
)
from pims.services.ssa_quality import libreoffice_smoke as _smoke
from pims.services.ssa_quality.libreoffice_smoke import (
    SmokeResult,
    _find_soffice,
    smoke_test_docx,
)


_SOFFICE_MISSING = _find_soffice() is None


def _save_jpeg(path: Path, size=(800, 600), color="red") -> Path:
    Image.new("RGB", size, color).save(path, "JPEG")
    return path


def _build_minimal_report(out: Path) -> None:
    photos_dir = out.parent / "photos"
    photos_dir.mkdir(exist_ok=True)
    p = _save_jpeg(photos_dir / "a.jpg", (800, 600))
    obs = ObservationRow(
        csv_row=1, timestamp_raw="", timestamp_iso=None,
        observation_text="x", csv_filename="a.jpg",
        resolved_filename="a.jpg", resolved_path=p,
    )
    rows = [EnrichedRow(obs=obs, finding="Top rail missing.",
                        conformance_status="NCR", legal_ref="WHS Reg cl.79")]
    build_ssa_report_docx(
        rows=rows,
        site_address="12 Test St",
        audit_date_ddmmyyyy="01/05/2026",
        narrative_summary="Audit summary.",
        output_path=out,
        prepared_by="Alan Richardson",
    )


@pytest.mark.skipif(_SOFFICE_MISSING, reason="LibreOffice not installed on this host")
def test_smoke_test_clean_docx_succeeds(tmp_path):
    """build_ssa_report_docx output must convert to PDF via headless soffice."""
    out = tmp_path / "r.docx"
    _build_minimal_report(out)
    result = smoke_test_docx(out)
    assert result.available, result.skip_reason
    assert result.success, result.failure_detail
    assert result.failure_detail == ""


@pytest.mark.skipif(_SOFFICE_MISSING, reason="LibreOffice not installed on this host")
def test_smoke_test_corrupt_docx_fails_cleanly(tmp_path):
    """A docx missing its document body part must produce a clean
    SmokeResult(success=False), not raise.

    Strips ``word/document.xml`` from a valid build_ssa_report_docx
    output — leaves the zip structurally valid but with no document
    body for soffice to render. soffice should fail and the smoke
    check should report it via failure_detail.
    """
    out = tmp_path / "r.docx"
    _build_minimal_report(out)

    broken = tmp_path / "r-broken.docx"
    with zipfile.ZipFile(out, "r") as zin, zipfile.ZipFile(broken, "w") as zout:
        for item in zin.infolist():
            if item.filename == "word/document.xml":
                continue  # strip the body
            zout.writestr(item, zin.read(item.filename))

    result = smoke_test_docx(broken)
    assert result.available, result.skip_reason
    assert not result.success
    assert result.failure_detail  # populated with diagnostic


def test_smoke_test_soft_skips_when_soffice_missing(tmp_path, monkeypatch):
    """When `_find_soffice` returns None the smoke check must return
    available=False with a populated skip_reason rather than raising."""
    monkeypatch.setattr(_smoke, "_find_soffice", lambda: None)
    out = tmp_path / "r.docx"
    out.write_bytes(b"")  # never read because we soft-skip first
    result = smoke_test_docx(out)
    assert isinstance(result, SmokeResult)
    assert result.available is False
    assert "libreoffice" in result.skip_reason.lower()

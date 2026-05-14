"""Phase 2 OOXML schema validation tests.

Three scenarios:
1. A clean build_ssa_report_docx output validates cleanly.
2. A deliberately-mutated docx (unknown element injected into the body)
   produces validation errors.
3. When dotnet isn't reachable the validator soft-skips with a reason.
"""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from pims.services.ssa_pipeline import (
    EnrichedRow,
    ObservationRow,
    build_ssa_report_docx,
)
from pims.services.ssa_quality import oxml_validator as _ov
from pims.services.ssa_quality.oxml_validator import (
    ValidationResult,
    _find_dotnet,
    validate_docx,
)


_DOTNET_MISSING = _find_dotnet() is None


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
    rows = [
        EnrichedRow(obs=obs, finding="Top rail missing.",
                    conformance_status="NCR", legal_ref="WHS Reg cl.79"),
    ]
    build_ssa_report_docx(
        rows=rows,
        site_address="12 Test St",
        audit_date_ddmmyyyy="01/05/2026",
        narrative_summary="Audit summary.",
        output_path=out,
        prepared_by="Alan Richardson",
    )


@pytest.mark.skipif(_DOTNET_MISSING, reason="dotnet not available on this host")
def test_validate_docx_clean_output_has_no_errors(tmp_path):
    """build_ssa_report_docx output must validate clean against the
    Microsoft 365 schema."""
    out = tmp_path / "r.docx"
    _build_minimal_report(out)
    result = validate_docx(out)
    assert result.available, result.skip_reason
    rendered = [e.short() for e in result.errors]
    assert result.errors == [], "\n".join(rendered)


@pytest.mark.skipif(_DOTNET_MISSING, reason="dotnet not available on this host")
def test_validate_docx_detects_schema_violation(tmp_path):
    """Injecting an unknown element into the document body must trip the
    schema validator."""
    out = tmp_path / "r.docx"
    _build_minimal_report(out)

    # Pull document.xml, inject a bogus element inside <w:body>, repack.
    rebuilt = tmp_path / "r-broken.docx"
    with zipfile.ZipFile(out, "r") as zin, zipfile.ZipFile(rebuilt, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                text = data.decode("utf-8")
                # Inject just before the closing body tag.
                text = text.replace(
                    "</w:body>", "<w:totallyBogus/></w:body>", 1
                )
                data = text.encode("utf-8")
            zout.writestr(item, data)

    result = validate_docx(rebuilt)
    assert result.available, result.skip_reason
    assert result.errors, "expected at least one schema error"
    # The bogus element should surface somewhere in the descriptions.
    joined = " ".join(e.description for e in result.errors)
    assert "totallyBogus" in joined or "unrecognized" in joined.lower() \
        or "not declared" in joined.lower()


def test_validate_docx_soft_skips_when_dotnet_missing(tmp_path, monkeypatch):
    """When `_find_dotnet` returns None the validator must return
    ``available=False`` with a non-empty skip_reason rather than raising."""
    monkeypatch.setattr(_ov, "_find_dotnet", lambda: None)
    out = tmp_path / "r.docx"
    out.write_bytes(b"")  # don't even need a real docx — we soft-skip first
    result = validate_docx(out)
    assert isinstance(result, ValidationResult)
    assert result.available is False
    assert "dotnet" in result.skip_reason.lower()

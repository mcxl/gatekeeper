"""Phase 1 byte-determinism regression for build_ssa_report_docx.

Two runs over identical inputs must produce byte-identical output.
Guards against accidental reintroduction of timestamp non-determinism
(zip mtimes, dcterms:created/modified) and against docxcompose-style
paraId drift.
"""
from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

from PIL import Image

from pims.services.ssa_pipeline import (
    EnrichedRow,
    ObservationRow,
    build_ssa_report_docx,
)


def _save_jpeg(path: Path, size=(800, 600), color="red") -> Path:
    Image.new("RGB", size, color).save(path, "JPEG")
    return path


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _build_rows(photos_dir: Path) -> list[EnrichedRow]:
    p1 = _save_jpeg(photos_dir / "a.jpg", (1200, 800))
    p2 = _save_jpeg(photos_dir / "b.jpg", (800, 1200), "blue")
    obs1 = ObservationRow(
        csv_row=1, timestamp_raw="", timestamp_iso=None,
        observation_text="x", csv_filename="a.jpg",
        resolved_filename="a.jpg", resolved_path=p1,
    )
    obs2 = ObservationRow(
        csv_row=2, timestamp_raw="", timestamp_iso=None,
        observation_text="y", csv_filename="b.jpg",
        resolved_filename="b.jpg", resolved_path=p2,
    )
    return [
        EnrichedRow(obs=obs1, finding="Top rail missing.",
                    conformance_status="NCR", legal_ref="WHS Reg cl.79"),
        EnrichedRow(obs=obs2, observation_text_clean="Site sign clear.",
                    conformance_status="Compliant", legal_ref="WHS Reg cl.34"),
    ]


def test_build_ssa_report_docx_byte_deterministic(tmp_path):
    """Two builds with identical inputs must produce byte-identical output."""
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()

    out1 = tmp_path / "r1.docx"
    out2 = tmp_path / "r2.docx"

    build_ssa_report_docx(
        rows=_build_rows(photos_dir),
        site_address="12 Test Street, Sydney NSW",
        audit_date_ddmmyyyy="01/05/2026",
        narrative_summary="Audit summary text.",
        output_path=out1,
        prepared_by="Alan Richardson",
    )
    build_ssa_report_docx(
        rows=_build_rows(photos_dir),
        site_address="12 Test Street, Sydney NSW",
        audit_date_ddmmyyyy="01/05/2026",
        narrative_summary="Audit summary text.",
        output_path=out2,
        prepared_by="Alan Richardson",
    )

    assert _sha256(out1) == _sha256(out2)


def test_build_ssa_report_docx_deterministic_with_empty_audit_date(tmp_path):
    """Empty audit date hits the sentinel fallback; output stays byte-stable."""
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()

    out1 = tmp_path / "r1.docx"
    out2 = tmp_path / "r2.docx"

    for out in (out1, out2):
        build_ssa_report_docx(
            rows=_build_rows(photos_dir),
            site_address="addr",
            audit_date_ddmmyyyy="",
            narrative_summary="x",
            output_path=out,
            prepared_by="Alan Richardson",
        )

    assert _sha256(out1) == _sha256(out2)


def test_build_ssa_report_docx_has_no_dcterms_timestamps(tmp_path):
    """After determinism post-pass, core.xml carries the audit-date
    timestamp, not the wall clock."""
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    out = tmp_path / "r.docx"
    build_ssa_report_docx(
        rows=_build_rows(photos_dir),
        site_address="addr",
        audit_date_ddmmyyyy="01/05/2026",
        narrative_summary="x",
        output_path=out,
        prepared_by="Alan Richardson",
    )
    with zipfile.ZipFile(out) as z:
        core = z.read("docProps/core.xml").decode("utf-8")
    # Both fields stamped with the audit-date iso, not a wall-clock time.
    assert "2026-05-01T00:00:00Z" in core

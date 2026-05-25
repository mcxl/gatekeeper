"""Unit tests for the PDF export hook in
``pims/scripts/generate_audit_report.py``.

The docx2pdf call itself is mocked — real conversion requires Word COM
and a real .docx; that integration is verified manually during the
per-folder render verification step.
"""
from __future__ import annotations

import sys
import types


from pims.scripts.generate_audit_report import _render_pdf_sibling


def test_render_pdf_returns_path_when_convert_succeeds(tmp_path, monkeypatch):
    docx = tmp_path / "X_2026-05-22-03.docx"
    docx.write_bytes(b"fake docx")
    pdf = tmp_path / "X_2026-05-22-03.pdf"

    def _fake_convert(d_in, d_out):
        # Simulate docx2pdf writing the pdf file.
        from pathlib import Path
        Path(d_out).write_bytes(b"%PDF-1.4\n%fake\n")

    fake_mod = types.ModuleType("docx2pdf")
    fake_mod.convert = _fake_convert
    monkeypatch.setitem(sys.modules, "docx2pdf", fake_mod)

    out = _render_pdf_sibling(docx)
    assert out == pdf
    assert pdf.exists()
    assert pdf.read_bytes().startswith(b"%PDF")


def test_render_pdf_returns_none_when_docx2pdf_missing(
    tmp_path, monkeypatch, capsys,
):
    docx = tmp_path / "X.docx"
    docx.write_bytes(b"fake")

    # Hide docx2pdf from import by replacing the loader.
    monkeypatch.setitem(sys.modules, "docx2pdf", None)

    out = _render_pdf_sibling(docx)
    assert out is None
    err = capsys.readouterr().err
    assert "docx2pdf" in err
    assert "skipping" in err.lower()


def test_render_pdf_returns_none_when_convert_raises(
    tmp_path, monkeypatch, capsys,
):
    docx = tmp_path / "X.docx"
    docx.write_bytes(b"fake")

    def _bad_convert(d_in, d_out):
        raise RuntimeError("Word COM RPC_E_CALL_REJECTED")

    fake_mod = types.ModuleType("docx2pdf")
    fake_mod.convert = _bad_convert
    monkeypatch.setitem(sys.modules, "docx2pdf", fake_mod)

    out = _render_pdf_sibling(docx)
    assert out is None
    err = capsys.readouterr().err
    assert "PDF export failed" in err
    assert "RPC_E_CALL_REJECTED" in err


def test_render_pdf_returns_none_when_convert_silently_fails(
    tmp_path, monkeypatch, capsys,
):
    """convert() runs without raising but no pdf gets written."""
    docx = tmp_path / "X.docx"
    docx.write_bytes(b"fake")

    def _silent_convert(d_in, d_out):
        pass  # No file written

    fake_mod = types.ModuleType("docx2pdf")
    fake_mod.convert = _silent_convert
    monkeypatch.setitem(sys.modules, "docx2pdf", fake_mod)

    out = _render_pdf_sibling(docx)
    assert out is None
    err = capsys.readouterr().err
    assert "reported success but file is missing" in err


def test_render_pdf_filename_matches_docx_with_pdf_ext(tmp_path, monkeypatch):
    docx = tmp_path / "RPD_SSA_Audit_Report_2026-05-22-03.docx"
    docx.write_bytes(b"fake")

    captured = {}

    def _fake_convert(d_in, d_out):
        captured["in"] = d_in
        captured["out"] = d_out
        from pathlib import Path
        Path(d_out).write_bytes(b"%PDF")

    fake_mod = types.ModuleType("docx2pdf")
    fake_mod.convert = _fake_convert
    monkeypatch.setitem(sys.modules, "docx2pdf", fake_mod)

    out = _render_pdf_sibling(docx)
    assert out.name == "RPD_SSA_Audit_Report_2026-05-22-03.pdf"
    assert captured["out"].endswith("RPD_SSA_Audit_Report_2026-05-22-03.pdf")

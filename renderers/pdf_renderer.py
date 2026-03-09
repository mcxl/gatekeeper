#!/usr/bin/env python3
"""
renderers/pdf_renderer.py — Convert DOCX bytes to PDF bytes.

Primary:   LibreOffice headless (Linux/Railway)
Fallback:  docx2pdf (Microsoft Word COM on Windows)
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def docx_to_pdf(docx_bytes: bytes) -> bytes:
    """
    Convert docx bytes to PDF bytes.

    Tries LibreOffice headless first, falls back to docx2pdf (Word COM).
    Raises RuntimeError if neither converter is available.
    """
    # Try LibreOffice first (Linux/Railway)
    try:
        soffice = _find_libreoffice()
        if soffice:
            logger.info(f"Using LibreOffice: {soffice}")
            return _convert_libreoffice(docx_bytes, soffice)
    except Exception as lo_err:
        logger.warning(f"LibreOffice failed: {lo_err}")

    # Try docx2pdf second (Windows)
    try:
        return _convert_docx2pdf(docx_bytes)
    except Exception as d2p_err:
        logger.warning(f"docx2pdf failed: {d2p_err}")

    raise RuntimeError("No PDF converter available.")


def _find_libreoffice() -> str | None:
    """Return path to soffice executable, or None."""
    import platform
    if platform.system() == "Windows":
        candidates = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path
    else:
        # Linux/Railway — check common paths
        for path in ["/usr/bin/soffice", "/usr/bin/libreoffice"]:
            if os.path.isfile(path):
                return path
    # Check PATH
    found = shutil.which("soffice") or shutil.which("libreoffice")
    return found


def _convert_libreoffice(docx_bytes: bytes, soffice: str) -> bytes:
    """Convert using LibreOffice headless subprocess."""
    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = os.path.join(tmpdir, "input.docx")
        with open(docx_path, "wb") as f:
            f.write(docx_bytes)

        cmd = [
            soffice,
            "--headless",
            "--convert-to", "pdf",
            "--outdir", tmpdir,
            docx_path,
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"LibreOffice conversion failed: {result.stderr.strip()}"
            )

        pdf_path = os.path.join(tmpdir, "input.pdf")
        if not os.path.isfile(pdf_path):
            raise RuntimeError("LibreOffice did not produce a PDF file")

        with open(pdf_path, "rb") as f:
            return f.read()


def _convert_docx2pdf(docx_bytes: bytes) -> bytes:
    """Convert using docx2pdf (Microsoft Word COM automation)."""
    try:
        from docx2pdf import convert
    except ImportError:
        raise RuntimeError(
            "No PDF converter available.\n"
            "Install one of:\n"
            "  1. LibreOffice: https://www.libreoffice.org/download/download/\n"
            "  2. docx2pdf:    pip install docx2pdf  (requires Microsoft Word)\n"
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = os.path.join(tmpdir, "input.docx")
        pdf_path = os.path.join(tmpdir, "input.pdf")

        with open(docx_path, "wb") as f:
            f.write(docx_bytes)

        convert(docx_path, pdf_path)

        if not os.path.isfile(pdf_path):
            raise RuntimeError("docx2pdf did not produce a PDF file")

        with open(pdf_path, "rb") as f:
            return f.read()

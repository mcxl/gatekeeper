"""Headless LibreOffice round-trip smoke test for generated docx files.

Catches "Word can open it but other consumers can't" issues by feeding
each built docx through LibreOffice's command-line PDF converter. If
soffice exits non-zero — or exits 0 without producing a non-empty PDF —
the docx has something wrong that python-docx and OpenXmlValidator both
missed.

Mirrors the OOXML validator's soft-skip pattern: when LibreOffice is
not installed, the smoke check returns ``SmokeResult(available=False)``
with a populated ``skip_reason`` rather than failing the build.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


# Probe in order: absolute Windows install paths first, then PATH lookup
# for soffice / soffice.exe. Matches rpd-ssa-builder's candidate list.
_LIBREOFFICE_CANDIDATES = (
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/usr/bin/soffice",
    "/usr/bin/libreoffice",
    "soffice",
    "soffice.exe",
)
_TIMEOUT_SECONDS = 180


@dataclass(frozen=True)
class SmokeResult:
    available: bool              # soffice reachable
    success: bool                # True iff conversion produced a non-empty PDF
    skip_reason: str = ""        # populated when available=False
    failure_detail: str = ""     # populated when available=True and success=False


def _find_soffice() -> str | None:
    """Resolve the soffice executable from the candidate list."""
    for candidate in _LIBREOFFICE_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
        which = shutil.which(candidate)
        if which:
            return which
    return None


def smoke_test_docx(docx_path: Path) -> SmokeResult:
    """Convert ``docx_path`` to PDF via headless LibreOffice. Never raises."""
    soffice = _find_soffice()
    if soffice is None:
        return SmokeResult(
            available=False, success=False,
            skip_reason=(
                "LibreOffice not found on PATH or in standard install "
                "locations. Install LibreOffice to enable the headless "
                "render smoke test."
            ),
        )

    try:
        with tempfile.TemporaryDirectory(prefix="ssa-smoke-") as tmp:
            result = subprocess.run(
                [soffice, "--headless", "--convert-to", "pdf",
                 "--outdir", tmp, str(docx_path)],
                capture_output=True, text=True, timeout=_TIMEOUT_SECONDS,
            )
            if result.returncode != 0:
                return SmokeResult(
                    available=True, success=False,
                    failure_detail=(
                        f"exit {result.returncode}; "
                        f"stdout={result.stdout.strip()!r}; "
                        f"stderr={result.stderr.strip()!r}"
                    ),
                )
            # soffice has been observed to exit 0 without producing a PDF
            # when the source docx is sufficiently malformed; assert a
            # non-empty file actually landed in the temp dir.
            pdfs = list(Path(tmp).glob("*.pdf"))
            if not pdfs:
                return SmokeResult(
                    available=True, success=False,
                    failure_detail="soffice exit 0 but no PDF produced",
                )
            if pdfs[0].stat().st_size == 0:
                return SmokeResult(
                    available=True, success=False,
                    failure_detail=f"PDF produced but empty: {pdfs[0].name}",
                )
            return SmokeResult(available=True, success=True)
    except subprocess.TimeoutExpired:
        return SmokeResult(
            available=True, success=False,
            failure_detail=f"LibreOffice timed out after {_TIMEOUT_SECONDS}s",
        )
    except (OSError, subprocess.SubprocessError) as e:
        return SmokeResult(
            available=True, success=False,
            failure_detail=f"LibreOffice invocation failed: {type(e).__name__}: {e}",
        )

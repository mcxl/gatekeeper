"""Run Microsoft's OpenXmlValidator over a generated docx.

Wraps the .NET CLI from rpd-ssa-builder's `_validator/` project. Validates
against Microsoft 365 — the same target Word uses when deciding whether
to fire the "found unreadable content" recovery prompt. Catching errors
here means we never ship a docx that needs Word recovery.

Cache strategy: the validator DLL is shared with rpd-ssa-builder at
``%LOCALAPPDATA%\\rpd-ssa-validator\\`` (off Google Drive to avoid sync
fighting `dotnet build`'s memory-mapped writes). If the cache is missing,
this module rebuilds it from rpd-ssa-builder's source dir. The default
source path can be overridden with the ``GATEKEEPER_SSA_VALIDATOR_SOURCE``
env var for non-Alan-Richardson installs.

Soft-then-hard policy:
- If `dotnet` isn't reachable → return ``ValidationResult(available=False)``;
  the caller decides whether to warn or fail.
- If `dotnet` IS reachable → build the CLI if needed, run it. Errors are
  returned via ``ValidationResult.errors``. The caller decides whether to
  abort the build.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


# Source directory holding `Validate.csproj` and `Program.cs`. Default points
# at rpd-ssa-builder's vendored source on Alan's machine; override via the
# `GATEKEEPER_SSA_VALIDATOR_SOURCE` env var for other installs.
_DEFAULT_SOURCE_DIR = Path(
    "G:/My Drive/alan_mcxico/SSA-evidence/SSA rules/_validator"
)
_VALIDATOR_SRC_DIR = Path(
    os.environ.get("GATEKEEPER_SSA_VALIDATOR_SOURCE", str(_DEFAULT_SOURCE_DIR))
)

# Build artefacts live OFF the source tree so Google Drive sync doesn't
# fight `dotnet build`'s memory-mapped writes during the apphost step.
# Shared with rpd-ssa-builder — both tools co-own this cache since they
# build from the same source.
_LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
_BUILD_ROOT = _LOCALAPPDATA / "rpd-ssa-validator"
_VALIDATOR_DLL = _BUILD_ROOT / "bin" / "Release" / "net8.0" / "Validate.dll"


@dataclass(frozen=True)
class ValidationError:
    id: str
    description: str
    error_type: str
    part_uri: str
    xpath: str
    node: str
    related_node: str
    related_part: str

    def short(self) -> str:
        """One-line summary suitable for log output."""
        loc = self.part_uri or "?"
        if self.node:
            loc += f" / <{self.node}>"
        return f"[{self.id or self.error_type}] {loc}: {self.description}"


@dataclass(frozen=True)
class ValidationResult:
    available: bool                # dotnet reachable and validator built
    errors: list[ValidationError]
    skip_reason: str = ""          # populated when available=False


# ---------------------------------------------------------------------------
# dotnet detection
# ---------------------------------------------------------------------------

def _find_dotnet() -> str | None:
    """Resolve the dotnet executable.

    Git Bash strips ``C:\\Program Files\\dotnet\\`` from its default PATH on
    Windows, so a PATH probe alone misses it. Falls back to common absolute
    install paths.
    """
    found = shutil.which("dotnet")
    if found:
        return found
    for cand in (
        Path("C:/Program Files/dotnet/dotnet.exe"),
        Path("C:/Program Files (x86)/dotnet/dotnet.exe"),
    ):
        if cand.is_file():
            return str(cand)
    return None


def _dotnet_works(dotnet_path: str) -> bool:
    try:
        result = subprocess.run(
            [dotnet_path, "--version"],
            capture_output=True, text=True, timeout=10,
        )
    except (subprocess.SubprocessError, OSError):
        return False
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Build (one-time, cached)
# ---------------------------------------------------------------------------

class _BuildError(Exception):
    pass


def _build_validator(dotnet_path: str) -> None:
    """Compile `_validator/` in Release mode, output redirected off Google
    Drive. NuGet restore happens implicitly.

    Caches under ``%LOCALAPPDATA%\\rpd-ssa-validator\\bin\\Release\\net8.0\\``.
    Subsequent calls are no-ops because the dll exists.
    """
    if _VALIDATOR_DLL.is_file():
        return
    if not _VALIDATOR_SRC_DIR.is_dir():
        raise _BuildError(
            f"validator source not found at {_VALIDATOR_SRC_DIR}. "
            "Either install rpd-ssa-builder or set "
            "GATEKEEPER_SSA_VALIDATOR_SOURCE to a directory containing "
            "Validate.csproj and Program.cs."
        )
    _BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    bin_dir = _BUILD_ROOT / "bin"
    obj_dir = _BUILD_ROOT / "obj"
    # Trailing backslash is required by MSBuild for *OutputPath properties.
    bin_arg = f"-p:BaseOutputPath={bin_dir}\\"
    obj_arg = f"-p:BaseIntermediateOutputPath={obj_dir}\\"

    result = subprocess.run(
        [dotnet_path, "build", "Validate.csproj",
         "--configuration", "Release",
         "--nologo", "--verbosity", "quiet",
         bin_arg, obj_arg],
        cwd=str(_VALIDATOR_SRC_DIR),
        capture_output=True, text=True, timeout=300,
        env={**os.environ,
             "DOTNET_NOLOGO": "true",
             "DOTNET_CLI_TELEMETRY_OPTOUT": "1"},
    )
    if result.returncode != 0:
        raise _BuildError(
            f"`dotnet build` failed (exit {result.returncode}):\n"
            f"{result.stdout.strip()}\n{result.stderr.strip()}"
        )
    if not _VALIDATOR_DLL.is_file():
        raise _BuildError(
            f"`dotnet build` succeeded but {_VALIDATOR_DLL} is missing"
        )


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def validate_docx(docx_path: Path) -> ValidationResult:
    """Validate `docx_path`. Returns a ValidationResult; never raises."""
    dotnet_path = _find_dotnet()
    if dotnet_path is None or not _dotnet_works(dotnet_path):
        return ValidationResult(
            available=False, errors=[],
            skip_reason=(
                "dotnet not found — install the .NET 8 SDK to enable "
                "OOXML schema validation "
                "(https://dotnet.microsoft.com/download)."
            ),
        )

    try:
        _build_validator(dotnet_path)
    except _BuildError as e:
        return ValidationResult(
            available=False, errors=[],
            skip_reason=f"validator build unavailable:\n{e}",
        )

    result = subprocess.run(
        [dotnet_path, str(_VALIDATOR_DLL), str(docx_path)],
        capture_output=True, text=True, timeout=120,
    )

    if result.returncode == 2:
        return ValidationResult(
            available=False, errors=[],
            skip_reason=f"validator arg error: {result.stderr.strip()}",
        )
    if result.returncode == 3:
        return ValidationResult(
            available=True, errors=[],
            skip_reason=f"validator crashed: {result.stderr.strip()}",
        )

    # Both 0 (clean) and 1 (errors) emit a JSON array on stdout.
    try:
        raw = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return ValidationResult(
            available=True, errors=[],
            skip_reason=(
                f"validator returned non-JSON stdout:\n{result.stdout.strip()}"
            ),
        )

    errors = [
        ValidationError(
            id=str(e.get("id", "")),
            description=str(e.get("description", "")),
            error_type=str(e.get("errorType", "")),
            part_uri=str(e.get("partUri", "")),
            xpath=str(e.get("xpath", "")),
            node=str(e.get("node", "")),
            related_node=str(e.get("relatedNode", "")),
            related_part=str(e.get("relatedPart", "")),
        )
        for e in raw
    ]
    return ValidationResult(available=True, errors=errors)

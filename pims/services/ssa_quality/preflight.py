"""--check preflight for the SSA pipeline.

Runs every check against an audit folder and reports them all — never
bails on the first failure. Hard failures block the build; informational
items print a warning only.

Mirrors rpd-ssa-builder's preflight shape (``CheckResult`` + ``run_preflight``
+ ``format_results``) but with gatekeeper-native checks for the SSA input
contract: folder name pattern, ``Evidence_Master.csv``, images in folder
root, SSA report template, and environment tools (LibreOffice, dotnet,
``ANTHROPIC_API_KEY``).
"""
from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from pathlib import Path

from pims.services.ssa_quality.libreoffice_smoke import _find_soffice
from pims.services.ssa_quality.oxml_validator import _find_dotnet

# ``SSA_REPORT_TEMPLATE`` is imported lazily inside ``_check_template``;
# top-level import would create a cycle because ``ssa_pipeline`` itself
# imports from ``ssa_quality`` (which imports this module).


# Folder name contract — mirrors run_ssa_pipeline.py's _FOLDER_RE.
_FOLDER_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})-(RPD|SDG)(?:-(\d{2}))?$"
)
_IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
_EVIDENCE_CSV_NAME = "Evidence_Master.csv"
# Mirrors ssa_pipeline._REQUIRED_HEADER. Kept locally so a rename in
# ssa_pipeline.py would surface as a drift-checker finding rather than
# silently breaking preflight.
_EXPECTED_CSV_HEADERS = ("timestamp", "observation", "filename")


@dataclass
class CheckResult:
    label: str
    passed: bool
    detail: str = ""
    informational: bool = False  # True = doesn't block the build


def _ok(label: str, detail: str = "") -> CheckResult:
    return CheckResult(label=label, passed=True, detail=detail)


def _fail(label: str, detail: str, informational: bool = False) -> CheckResult:
    return CheckResult(
        label=label, passed=False, detail=detail, informational=informational
    )


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _check_folder_name(folder: Path) -> CheckResult:
    label = "Folder name matches YYYY-MM-DD-{RPD,SDG}[-NN]"
    m = _FOLDER_RE.match(folder.name)
    if not m:
        return _fail(label, f"got {folder.name!r}")
    detail = f"client={m.group(4)}"
    if m.group(5):
        detail += f" sub_id={m.group(5)}"
    return _ok(label, detail)


def _check_evidence_csv(folder: Path) -> list[CheckResult]:
    p = folder / _EVIDENCE_CSV_NAME
    exists_label = f"{_EVIDENCE_CSV_NAME} exists in folder root"
    headers_label = (
        f"{_EVIDENCE_CSV_NAME} has expected headers "
        "(timestamp, observation, filename)"
    )
    rows_label = f"{_EVIDENCE_CSV_NAME} has at least one data row"

    results: list[CheckResult] = []
    if not p.is_file():
        results.append(_fail(exists_label, "missing"))
        results.append(_fail(headers_label, "(skipped — csv missing)"))
        results.append(_fail(rows_label, "(skipped — csv missing)"))
        return results
    results.append(_ok(exists_label, f"{p.stat().st_size} bytes"))

    try:
        text = p.read_text(encoding="utf-8-sig", errors="replace")
    except OSError as e:
        results.append(_fail(headers_label, f"unreadable: {e}"))
        results.append(_fail(rows_label, "(skipped — csv unreadable)"))
        return results

    rows = list(csv.reader(text.splitlines()))
    if not rows:
        results.append(_fail(headers_label, "csv is empty"))
        results.append(_fail(rows_label, "(skipped — csv empty)"))
        return results
    header = tuple(c.strip().lower() for c in rows[0])
    if header == _EXPECTED_CSV_HEADERS:
        results.append(_ok(headers_label))
    else:
        results.append(_fail(headers_label, f"got {header}"))
    data_rows = [r for r in rows[1:] if any(c.strip() for c in r)]
    if data_rows:
        results.append(_ok(rows_label, f"{len(data_rows)} row(s)"))
    else:
        results.append(_fail(rows_label, "no non-blank rows after header"))
    return results


def _check_images(folder: Path) -> CheckResult:
    label = "Folder contains at least one image (.jpg / .jpeg / .png)"
    imgs = [
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in _IMAGE_EXTS
    ]
    if imgs:
        return _ok(label, f"{len(imgs)} image(s)")
    return _fail(label, "none found in folder root")


def _check_template() -> CheckResult:
    label = "SSA report template readable at configured path"
    from pims.services.ssa_pipeline import SSA_REPORT_TEMPLATE
    if SSA_REPORT_TEMPLATE.is_file():
        return _ok(label, str(SSA_REPORT_TEMPLATE))
    return _fail(label, f"missing: {SSA_REPORT_TEMPLATE}")


def _check_libreoffice() -> CheckResult:
    label = "LibreOffice reachable (for render smoke test)"
    soffice = _find_soffice()
    if soffice:
        return _ok(label, soffice)
    return _fail(
        label,
        "not found — install LibreOffice to enable the smoke test",
        informational=True,
    )


def _check_dotnet() -> CheckResult:
    label = "dotnet reachable (for OOXML schema validation)"
    dotnet = _find_dotnet()
    if dotnet:
        return _ok(label, dotnet)
    return _fail(
        label,
        "not found — install .NET 8 SDK to enable schema validation",
        informational=True,
    )


def _check_anthropic_key() -> CheckResult:
    label = "ANTHROPIC_API_KEY set (for vision enrichment)"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return _ok(label)
    return _fail(
        label,
        "unset — vision pass will fail unless --no-enrich is used",
        informational=True,
    )


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run_preflight(folder: Path | str) -> tuple[list[CheckResult], bool]:
    """Run every check. Returns ``(results, hard_pass)``.

    ``hard_pass`` is ``True`` iff all non-informational checks passed.
    """
    folder = Path(folder)
    results: list[CheckResult] = []
    results.append(_check_folder_name(folder))
    results.extend(_check_evidence_csv(folder))
    results.append(_check_images(folder))
    results.append(_check_template())
    results.append(_check_libreoffice())
    results.append(_check_dotnet())
    results.append(_check_anthropic_key())
    hard_pass = all(r.passed for r in results if not r.informational)
    return results, hard_pass


def format_results(results: list[CheckResult], use_colour: bool = True) -> str:
    """Render the check list with [X] / [!] / [ ] markers and optional colour."""
    if use_colour:
        try:
            from colorama import Fore, Style, init as _init
            _init()
            green = Fore.GREEN
            red = Fore.RED
            yellow = Fore.YELLOW
            reset = Style.RESET_ALL
        except ImportError:
            green = red = yellow = reset = ""
    else:
        green = red = yellow = reset = ""

    lines: list[str] = []
    for r in results:
        if r.passed:
            mark = f"{green}[X]{reset}"
        elif r.informational:
            mark = f"{yellow}[!]{reset}"
        else:
            mark = f"{red}[ ]{reset}"
        line = f"  {mark} {r.label}"
        if r.detail:
            line += f"  -- {r.detail}"
        lines.append(line)
    return "\n".join(lines)

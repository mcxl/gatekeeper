"""SSA drift checker.

Exits 0 if no drift; 1 if drift detected. Run with:

    python tools/check_ssa_drift.py

Drift is the silent divergence between paired facts in different files.
A constant in one module, a literal in a template, a header tuple in a
docs file — they all encode the same truth, and if one moves while the
others don't, the build keeps working but produces wrong output. Word's
recovery prompt tolerates it; downstream consumers do not.

Checks today:

  1. ``Evidence_Master.csv`` header tuple — duplicated in
     ``ssa_pipeline._REQUIRED_HEADER`` and
     ``preflight._EXPECTED_CSV_HEADERS``. Must stay aligned or preflight
     silently accepts CSVs the pipeline can't parse.
  2. SSA report template placeholders — every ``PH_*`` constant in
     ``ssa_pipeline.py`` must appear as literal text somewhere in the
     report template ``.docx``. Catches "renamed PH_FOO in code but
     forgot the template" (or vice versa).
  3. Staging xlsx header widths — every entry in
     ``STAGING_HEADERS`` must have a corresponding entry in
     ``_STAGING_COL_WIDTHS``. Subset (not equality): extra width entries
     are tolerated (gap-4/5/6 forward-defined columns); missing entries
     are not.

Future checks can be added by appending to ``_CHECKS`` — each is a
``(label, callable)`` returning ``None`` on pass or a string detail on
fail.
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path
from typing import Callable, Optional

# Add repo root to sys.path so this script can be run from anywhere.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pims.services.ssa_pipeline import (
    _REQUIRED_HEADER,
    _STAGING_COL_WIDTHS,
    SSA_REPORT_PLACEHOLDERS,
    SSA_REPORT_TEMPLATE,
    STAGING_HEADERS,
)
from pims.services.ssa_quality.preflight import _EXPECTED_CSV_HEADERS


# Matches ``<w:t ...>text</w:t>`` runs so we can extract Word's visible
# text content from word/*.xml parts (placeholders may be split across
# multiple <w:t> runs when formatting boundaries land mid-token).
_W_T_RE = re.compile(r"<w:t[^>]*>([^<]*)</w:t>")


def _check_csv_headers() -> Optional[str]:
    if _REQUIRED_HEADER == _EXPECTED_CSV_HEADERS:
        return None
    return (
        f"ssa_pipeline._REQUIRED_HEADER={_REQUIRED_HEADER!r} "
        f"!= preflight._EXPECTED_CSV_HEADERS={_EXPECTED_CSV_HEADERS!r}"
    )


def _check_template_placeholders() -> Optional[str]:
    """Every PH_* must appear as literal text in the report template."""
    if not SSA_REPORT_TEMPLATE.is_file():
        return f"template missing: {SSA_REPORT_TEMPLATE}"
    # Concatenate <w:t> text across every word/*.xml part — covers
    # body, headers, footers, cover-page text boxes. Tag-strip via
    # findall then join, which collapses split-across-runs tokens.
    parts: list[str] = []
    with zipfile.ZipFile(SSA_REPORT_TEMPLATE) as z:
        for name in z.namelist():
            if name.startswith("word/") and name.endswith(".xml"):
                xml = z.read(name).decode("utf-8", errors="ignore")
                parts.extend(_W_T_RE.findall(xml))
    haystack = "".join(parts)
    missing = [ph for ph in SSA_REPORT_PLACEHOLDERS if ph not in haystack]
    if missing:
        return f"placeholder(s) not found in template: {missing}"
    return None


def _check_staging_header_widths() -> Optional[str]:
    """Every STAGING_HEADERS entry must have an _STAGING_COL_WIDTHS key.

    Subset check, not equality — _STAGING_COL_WIDTHS legitimately
    carries forward-defined gap-4/5/6 columns (phase, activity_ref,
    hrcw, swms_required, etc.) that aren't yet in STAGING_HEADERS.
    """
    missing = [h for h in STAGING_HEADERS if h not in _STAGING_COL_WIDTHS]
    if missing:
        return (
            f"STAGING_HEADERS entries missing _STAGING_COL_WIDTHS entry: "
            f"{missing}"
        )
    return None


_CHECKS: tuple[tuple[str, Callable[[], Optional[str]]], ...] = (
    ("Evidence_Master.csv header tuple matches across modules",
     _check_csv_headers),
    ("SSA report template carries every PH_* placeholder",
     _check_template_placeholders),
    ("Every STAGING_HEADERS entry has a width definition",
     _check_staging_header_widths),
)


def main() -> int:
    failures: list[tuple[str, str]] = []
    for label, fn in _CHECKS:
        detail = fn()
        if detail is None:
            print(f"  [X] {label}")
        else:
            print(f"  [ ] {label}")
            print(f"      {detail}")
            failures.append((label, detail))
    print()
    if not failures:
        print(f"OK - no drift across {len(_CHECKS)} check(s)")
        return 0
    print(f"DRIFT - {len(failures)} of {len(_CHECKS)} check(s) failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())

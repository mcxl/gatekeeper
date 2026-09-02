"""SSA drift checker.

Exits 0 if no drift; 1 if drift detected. Run with:

    python tools/check_ssa_drift.py

Drift is the silent divergence between paired constants in different
files. Today this checker covers one case — the Evidence_Master.csv
header tuple, which is duplicated in:

  - pims/services/ssa_pipeline.py   ``_REQUIRED_HEADER``
  - pims/services/ssa_quality/preflight.py  ``_EXPECTED_CSV_HEADERS``

Both must stay aligned; the preflight check would silently start
accepting CSVs the pipeline can't parse if they drift.

Future checks can be added by appending to ``_CHECKS`` — each is a
``(label, callable)`` returning ``None`` on pass or a string detail on
fail.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add repo root to sys.path so this script can be run from anywhere.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pims.services.ssa_pipeline import _REQUIRED_HEADER
from pims.services.ssa_quality.preflight import _EXPECTED_CSV_HEADERS


def _check_csv_headers() -> str | None:
    if _REQUIRED_HEADER == _EXPECTED_CSV_HEADERS:
        return None
    return (
        f"ssa_pipeline._REQUIRED_HEADER={_REQUIRED_HEADER!r} "
        f"!= preflight._EXPECTED_CSV_HEADERS={_EXPECTED_CSV_HEADERS!r}"
    )


_CHECKS: tuple[tuple[str, callable], ...] = (
    ("Evidence_Master.csv header tuple matches across modules",
     _check_csv_headers),
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

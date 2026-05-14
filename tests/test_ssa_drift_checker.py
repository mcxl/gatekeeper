"""Phase 5 drift checker tests."""
from __future__ import annotations

import sys
from pathlib import Path


def _import_checker():
    """Import (or re-import) the drift checker module from tools/."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    import check_ssa_drift  # noqa: E402
    return check_ssa_drift


def test_drift_checker_clean_state_returns_zero(capsys):
    """Current main passes — no drift across any of the wired checks."""
    drift = _import_checker()
    rc = drift.main()
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "[X]" in out
    assert "no drift" in out.lower()


def test_drift_checker_flags_csv_header_mismatch(capsys, monkeypatch):
    """Forcing the preflight constant to diverge from ssa_pipeline's
    must trip the CSV header check."""
    drift = _import_checker()
    monkeypatch.setattr(
        drift, "_EXPECTED_CSV_HEADERS",
        ("timestamp", "observation", "DIVERGED"),
    )
    rc = drift.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "DRIFT" in out
    assert "DIVERGED" in out


def test_drift_checker_flags_missing_placeholder_in_template(
    capsys, monkeypatch,
):
    """Adding a fake PH_* that doesn't exist in the template must trip
    the placeholder check."""
    drift = _import_checker()
    monkeypatch.setattr(
        drift, "SSA_REPORT_PLACEHOLDERS",
        ("{{SITE_ADDRESS}}", "{{NEVER_IN_TEMPLATE}}"),
    )
    rc = drift.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "DRIFT" in out
    assert "NEVER_IN_TEMPLATE" in out


def test_drift_checker_flags_staging_header_without_width(
    capsys, monkeypatch,
):
    """A STAGING_HEADERS entry with no corresponding width entry must
    trip the staging-width check."""
    drift = _import_checker()
    monkeypatch.setattr(
        drift, "STAGING_HEADERS",
        drift.STAGING_HEADERS + ("phantom_column",),
    )
    rc = drift.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "DRIFT" in out
    assert "phantom_column" in out


def test_drift_checker_tolerates_extra_width_entries(capsys):
    """_STAGING_COL_WIDTHS legitimately carries forward-defined gap-4/5/6
    columns that aren't yet in STAGING_HEADERS. The subset semantics must
    NOT flag this as drift."""
    drift = _import_checker()
    rc = drift.main()
    out = capsys.readouterr().out
    # Today's main has gap-4/5/6 width entries (phase, hrcw, swms_*)
    # absent from STAGING_HEADERS. If this test fails, the check
    # tightened to equality and is now too strict.
    assert rc == 0, out

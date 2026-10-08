"""Phase 5 drift checker tests."""
from __future__ import annotations

import sys
from pathlib import Path


def test_drift_checker_clean_state_returns_zero(capsys, monkeypatch):
    """Current main passes — no drift between paired constants."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    import check_ssa_drift  # noqa: E402
    rc = check_ssa_drift.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "[X]" in out
    assert "no drift" in out.lower()


def test_drift_checker_flags_csv_header_mismatch(capsys, monkeypatch):
    """Forcing the preflight constant to diverge from ssa_pipeline's
    must trip the drift check."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    import check_ssa_drift  # noqa: E402
    monkeypatch.setattr(
        check_ssa_drift, "_EXPECTED_CSV_HEADERS",
        ("timestamp", "observation", "DIVERGED"),
    )
    rc = check_ssa_drift.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "DRIFT" in out
    assert "DIVERGED" in out

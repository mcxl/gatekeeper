"""Slice B tests for ``--resume`` dispatch on the SSA pipeline.

Covers the resume-phase resolver and the CLI mutex / failure-recording
wiring around it. End-to-end ``run_once`` invocation is exercised by
``tests/test_ssa_pipeline.py``; here we patch ``run_once`` so the
dispatch logic can be checked in isolation.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from pims.scripts.run_ssa_pipeline import (
    _resolve_resume_phase,
    _update_run_status,
    main,
)


def _seed_state(folder: Path, run_status: dict | None = None) -> None:
    state = {"folder": folder.name, "rows": []}
    if run_status is not None:
        state["run_status"] = run_status
    (folder / ".ssa_state.json").write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# --- _resolve_resume_phase ---------------------------------------------------

def test_resolve_resume_after_phase1_success(tmp_path: Path) -> None:
    _seed_state(tmp_path)
    _update_run_status(tmp_path, "enrich-only")
    phase, msg = _resolve_resume_phase(tmp_path)
    assert phase == "from-state"
    assert msg == ""


def test_resolve_resume_after_phase2_success(tmp_path: Path) -> None:
    _seed_state(tmp_path)
    _update_run_status(tmp_path, "enrich-only")
    _update_run_status(tmp_path, "from-state")
    phase, _ = _resolve_resume_phase(tmp_path)
    assert phase == "from-report"


def test_resolve_resume_terminal_audit(tmp_path: Path) -> None:
    _seed_state(tmp_path)
    _update_run_status(tmp_path, "enrich-only")
    _update_run_status(tmp_path, "from-state")
    _update_run_status(tmp_path, "from-report")
    phase, msg = _resolve_resume_phase(tmp_path)
    assert phase is None
    assert msg.startswith("audit complete")


def test_resolve_resume_after_failure_reruns_failed_phase(
    tmp_path: Path,
) -> None:
    _seed_state(tmp_path)
    _update_run_status(tmp_path, "enrich-only")
    _update_run_status(
        tmp_path, "from-state", exit_code=1, error="boom",
    )
    phase, _ = _resolve_resume_phase(tmp_path)
    assert phase == "from-state"


def test_resolve_resume_no_sidecar(tmp_path: Path) -> None:
    phase, msg = _resolve_resume_phase(tmp_path)
    assert phase is None
    assert "missing" in msg


def test_resolve_resume_legacy_sidecar_no_run_status(tmp_path: Path) -> None:
    _seed_state(tmp_path)  # no run_status block
    phase, msg = _resolve_resume_phase(tmp_path)
    assert phase is None
    assert "no run_status" in msg


# --- main() CLI wiring -------------------------------------------------------

def test_main_resume_dispatches_to_from_state(tmp_path: Path) -> None:
    _seed_state(tmp_path)
    _update_run_status(tmp_path, "enrich-only")
    captured: dict[str, object] = {}

    def fake_run_once(folder, **kwargs):
        captured.update(kwargs)
        captured["folder"] = folder
        return {
            "outputs": [],
            "staging_status": "ok",
            "skipped": False,
        }

    with patch(
        "pims.scripts.run_ssa_pipeline.run_once", side_effect=fake_run_once,
    ):
        rc = main([str(tmp_path), "--resume"])
    assert rc == 0
    assert captured["from_state"] is True
    assert captured["from_report"] is False
    assert captured["stop_after"] is None


def test_main_resume_dispatches_to_enrich_only(tmp_path: Path) -> None:
    # Failure mid phase 1 → resume re-runs enrich-only.
    _seed_state(tmp_path)
    _update_run_status(
        tmp_path, "enrich-only", exit_code=1, error="oops",
    )
    captured: dict[str, object] = {}

    def fake_run_once(folder, **kwargs):
        captured.update(kwargs)
        return {
            "phase": "enrich-only",
            "outputs": [],
            "row_count": 0,
            "next_step": "edit and resume",
        }

    with patch(
        "pims.scripts.run_ssa_pipeline.run_once", side_effect=fake_run_once,
    ):
        rc = main([str(tmp_path), "--resume"])
    assert rc == 0
    assert captured["stop_after"] == "enrich"
    assert captured["from_state"] is False


def test_main_resume_terminal_returns_zero(tmp_path: Path) -> None:
    _seed_state(tmp_path)
    _update_run_status(tmp_path, "enrich-only")
    _update_run_status(tmp_path, "from-state")
    _update_run_status(tmp_path, "from-report")
    with patch("pims.scripts.run_ssa_pipeline.run_once") as run_once_mock:
        rc = main([str(tmp_path), "--resume"])
    assert rc == 0
    run_once_mock.assert_not_called()


def test_main_resume_no_sidecar_returns_one(tmp_path: Path) -> None:
    rc = main([str(tmp_path), "--resume"])
    assert rc == 1


def test_main_resume_mutex_with_other_phase_flags(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    _seed_state(tmp_path)
    _update_run_status(tmp_path, "enrich-only")
    rc = main([str(tmp_path), "--resume", "--from-state"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "mutually exclusive" in err


def test_main_failure_records_run_status(tmp_path: Path) -> None:
    _seed_state(tmp_path)
    _update_run_status(tmp_path, "enrich-only")  # last green = phase 1

    def boom(*_args, **_kwargs):
        raise FileNotFoundError("missing csv")

    with patch(
        "pims.scripts.run_ssa_pipeline.run_once", side_effect=boom,
    ):
        rc = main([str(tmp_path), "--from-state"])
    assert rc == 1
    rs = json.loads(
        (tmp_path / ".ssa_state.json").read_text(encoding="utf-8"),
    )["run_status"]
    assert rs["last_exit_code"] == 1
    assert rs["last_attempted_phase"] == "from-state"
    assert rs["last_completed_phase"] == "enrich-only"
    assert rs["next_suggested_phase"] == "from-state"
    assert "missing csv" in rs["last_error"]

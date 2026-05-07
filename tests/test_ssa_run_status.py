"""Unit tests for the run_status helper on the SSA pipeline sidecar.

Slice A of the resumable-runner plan: the helper stamps a `run_status`
block onto `.ssa_state.json` at the success exit of each phase.
Additive — phase 2/3 readers ignore unknown keys, so we only verify the
new block's shape and lifecycle here. Slice B (`--resume`) consumes
this block and adds end-to-end coverage.
"""
from __future__ import annotations

import json
from pathlib import Path

from pims.scripts.run_ssa_pipeline import _update_run_status


def _seed(folder: Path, extra: dict | None = None) -> Path:
    state = {"folder": folder.name, "rows": []}
    if extra:
        state.update(extra)
    state_path = folder / ".ssa_state.json"
    state_path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return state_path


def test_update_run_status_phase1_success(tmp_path: Path) -> None:
    state_path = _seed(tmp_path)
    _update_run_status(tmp_path, "enrich-only")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    rs = state["run_status"]
    assert rs["last_completed_phase"] == "enrich-only"
    assert rs["last_attempted_phase"] == "enrich-only"
    assert rs["last_exit_code"] == 0
    assert rs["last_error"] is None
    assert rs["next_suggested_phase"] == "from-state"
    assert rs["last_run_at"].endswith("Z")
    # Sidecar payload preserved.
    assert state["folder"] == tmp_path.name
    assert state["rows"] == []


def test_update_run_status_progresses_through_phases(tmp_path: Path) -> None:
    _seed(tmp_path)
    _update_run_status(tmp_path, "enrich-only")
    _update_run_status(tmp_path, "from-state")
    state = json.loads(
        (tmp_path / ".ssa_state.json").read_text(encoding="utf-8"),
    )
    assert state["run_status"]["last_completed_phase"] == "from-state"
    assert state["run_status"]["next_suggested_phase"] == "from-report"

    _update_run_status(tmp_path, "from-report")
    state = json.loads(
        (tmp_path / ".ssa_state.json").read_text(encoding="utf-8"),
    )
    assert state["run_status"]["last_completed_phase"] == "from-report"
    assert state["run_status"]["next_suggested_phase"] is None


def test_update_run_status_full_run_terminal(tmp_path: Path) -> None:
    _seed(tmp_path)
    _update_run_status(tmp_path, "full-run")
    rs = json.loads(
        (tmp_path / ".ssa_state.json").read_text(encoding="utf-8"),
    )["run_status"]
    assert rs["last_completed_phase"] == "full-run"
    assert rs["next_suggested_phase"] is None


def test_update_run_status_records_failure(tmp_path: Path) -> None:
    _seed(tmp_path)
    _update_run_status(tmp_path, "enrich-only")  # green
    _update_run_status(
        tmp_path, "from-state", exit_code=1, error="boom",
    )
    rs = json.loads(
        (tmp_path / ".ssa_state.json").read_text(encoding="utf-8"),
    )["run_status"]
    # Failure leaves the previous green phase as last_completed and
    # points next_suggested_phase at the phase that just failed, so
    # --resume re-runs it rather than skipping ahead.
    assert rs["last_completed_phase"] == "enrich-only"
    assert rs["last_attempted_phase"] == "from-state"
    assert rs["last_exit_code"] == 1
    assert rs["last_error"] == "boom"
    assert rs["next_suggested_phase"] == "from-state"


def test_update_run_status_missing_sidecar_is_noop(tmp_path: Path) -> None:
    # No .ssa_state.json — helper must not raise and must not create one.
    _update_run_status(tmp_path, "enrich-only")
    assert not (tmp_path / ".ssa_state.json").exists()


def test_update_run_status_preserves_unrelated_keys(tmp_path: Path) -> None:
    _seed(tmp_path, extra={
        "finding_render_order": [3, 1, 2],
        "enriched_xlsx_snapshot": {"A1": {"value": "x"}},
    })
    _update_run_status(tmp_path, "enrich-only")
    state = json.loads(
        (tmp_path / ".ssa_state.json").read_text(encoding="utf-8"),
    )
    assert state["finding_render_order"] == [3, 1, 2]
    assert state["enriched_xlsx_snapshot"] == {"A1": {"value": "x"}}
    assert "run_status" in state

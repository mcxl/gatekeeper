"""Quiescence-based watcher for SSA evidence folders.

Polls a watch root for dated audit folders (``YYYY-MM-DD-<RPD|SDG>``).
A folder is processed only when it is *quiescent*:

  - the latest input mtime is at least ``settle_seconds`` ago (default
    120 s — true wall-clock stability), AND
  - ``required_stable_polls`` consecutive snapshots (default 4) of
    ``(filename, size, mtime)`` are identical.

Quiescence snapshots exclude every watcher-owned artifact:
``.ssa_run.json``, ``.ssa_run.error``, ``.ssa_freeze``, ``.ssa_work/``,
both sentinel files, and the canonical output filenames for the
current folder (computed from the folder name, plus anything previously
recorded in ``.ssa_run.json`` ``outputs``). This stops the watcher
reacting to its own writes.

A frozen folder (``.ssa_freeze`` present) is skipped with a logged
reason; this is the manual-patch escape hatch.

Idempotency on the run itself is `run_ssa_pipeline.run_once`'s job
(manifest sha256 + recorded outputs); when nothing has changed the
pipeline returns ``skipped=True`` and no disk writes happen.

This module exposes:
  - ``Watcher`` — encapsulated state + polling logic. ``tick()`` drives
    one polling cycle per folder; tests call it directly with a fake
    clock.
  - ``run_forever()`` — convenience long-run loop. Used by
    ``pims/scripts/start_ssa_watcher.py``.
"""
from __future__ import annotations

import json
import logging
import re
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

log = logging.getLogger(__name__)


# --- folder + filename rules --------------------------------------------

_FOLDER_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(RPD|SDG)$")
_IMAGE_EXTS = {".jpg", ".jpeg", ".png"}

# Static exclusions — names always skipped from the input snapshot,
# regardless of folder. Output filenames are added per-folder.
_STATIC_EXCLUDED_NAMES = frozenset({
    ".ssa_run.json",
    ".ssa_run.error",
    ".ssa_freeze",
    "STAGING-NOT-UPLOADABLE.txt",
    "STAGING-NO-BULK-ENDPOINT.txt",
})
_STATIC_EXCLUDED_DIRS = frozenset({".ssa_work"})


def _expected_outputs(folder_name: str) -> set[str]:
    """Canonical output filenames for the folder, computed from its name.

    Excluded from the quiescence snapshot even on a folder that has
    never been processed — prevents the watcher reacting to its own
    first write.
    """
    m = _FOLDER_RE.match(folder_name)
    if not m:
        return set()
    yyyy, mm, dd, client = m.groups()
    yymmdd = f"{yyyy[2:]}{mm}{dd}"
    return {
        f"PIMS-Enriched-{yymmdd}-{client}.xlsx",
        f"Site-Safety-Audit-Report-{yymmdd}-{client}.docx",
        f"Site-Visit-Report-Upload-PIMS-Staging-{yymmdd}-{client}.xlsx",
    }


def _recorded_outputs(folder: Path) -> set[str]:
    rj = folder / ".ssa_run.json"
    if not rj.exists():
        return set()
    try:
        data = json.loads(rj.read_text(encoding="utf-8"))
    except Exception:
        return set()
    out = data.get("outputs") or []
    return {str(n) for n in out if isinstance(n, str)}


def _snapshot(folder: Path) -> tuple[tuple[str, int, int], ...]:
    """Filename / size / mtime triples for everything that counts as input.

    Sorted by lowercased filename so the snapshot is order-stable. mtime
    is rounded to the nearest int second — Drive sync touches sometimes
    bump fractional mtime within a stable poll, which would otherwise
    flap the snapshot.
    """
    excluded_names = _STATIC_EXCLUDED_NAMES \
        | _expected_outputs(folder.name) \
        | _recorded_outputs(folder)
    triples: list[tuple[str, int, int]] = []
    try:
        entries = list(folder.iterdir())
    except FileNotFoundError:
        return ()
    for p in entries:
        if p.is_dir():
            if p.name in _STATIC_EXCLUDED_DIRS:
                continue
            # Walk-into is not needed at v1 — audit folders are flat.
            continue
        if p.name in excluded_names:
            continue
        # Output-prefixed -partN.xlsx variants for the staging file:
        # exclude any file whose name is a recorded output.
        try:
            st = p.stat()
        except FileNotFoundError:
            continue
        triples.append((p.name.lower(), st.st_size, int(st.st_mtime)))
    triples.sort()
    return tuple(triples)


def _max_input_mtime(snap: tuple[tuple[str, int, int], ...]) -> int:
    if not snap:
        return 0
    return max(t[2] for t in snap)


def _is_eligible_folder(folder: Path) -> tuple[bool, str]:
    """Return (eligible, reason). Reason is "" on the truthy branch."""
    if not folder.is_dir():
        return False, "not a directory"
    if not _FOLDER_RE.match(folder.name):
        return False, "name does not match YYYY-MM-DD-<RPD|SDG>"
    if not (folder / "Evidence_Master.csv").exists():
        return False, "Evidence_Master.csv missing"
    has_image = any(
        p.is_file() and p.suffix.lower() in _IMAGE_EXTS
        for p in folder.iterdir()
    )
    if not has_image:
        return False, "no images present"
    return True, ""


# --- per-folder watcher state -------------------------------------------

@dataclass
class FolderState:
    """Rolling history of recent snapshots.

    ``snapshots`` is a bounded deque of length ``required_stable_polls``;
    quiescence is reached when the deque is full AND every entry is
    equal to the latest one.
    """
    snapshots: deque = field(default_factory=lambda: deque(maxlen=4))

    def push(self, snap, capacity: int) -> None:
        if self.snapshots.maxlen != capacity:
            self.snapshots = deque(self.snapshots, maxlen=capacity)
        self.snapshots.append(snap)

    def is_stable(self, capacity: int) -> bool:
        return (
            len(self.snapshots) == capacity
            and all(s == self.snapshots[0] for s in self.snapshots)
        )

    def reset(self) -> None:
        self.snapshots.clear()


# --- watcher -------------------------------------------------------------

@dataclass
class Watcher:
    watch_root: Path
    settle_seconds: int = 120
    required_stable_polls: int = 4
    runner: Callable[[Path], dict] | None = None  # injects run_once
    clock: Callable[[], float] = time.time
    state: dict[Path, FolderState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.runner is None:
            # Lazy import keeps watcher importable without the CLI.
            from pims.scripts.run_ssa_pipeline import run_once
            self.runner = run_once  # type: ignore[assignment]

    # --- tick ----------------------------------------------------------

    def _candidates(self) -> Iterable[Path]:
        if not self.watch_root.is_dir():
            return ()
        return sorted(p for p in self.watch_root.iterdir() if p.is_dir())

    def tick(self) -> list[dict]:
        """Run one polling cycle across all candidate folders.

        Returns a list of result dicts (one per folder examined) with
        keys ``folder``, ``action`` ∈ {``"skip"``, ``"wait"``,
        ``"frozen"``, ``"ran"``, ``"error"``}, plus ``reason`` /
        ``payload`` / ``error`` as applicable. Caller can log or test
        against this directly.
        """
        results: list[dict] = []
        for folder in self._candidates():
            results.append(self._tick_folder(folder))
        return results

    def _tick_folder(self, folder: Path) -> dict:
        eligible, reason = _is_eligible_folder(folder)
        if not eligible:
            self.state.pop(folder, None)
            return {"folder": folder.name, "action": "skip", "reason": reason}

        if (folder / ".ssa_freeze").exists():
            self.state.pop(folder, None)
            return {"folder": folder.name, "action": "frozen"}

        snap = _snapshot(folder)
        st = self.state.setdefault(folder, FolderState())
        st.push(snap, self.required_stable_polls)

        # (a) wall-clock settle
        latest = _max_input_mtime(snap)
        now = int(self.clock())
        settle_ok = (now - latest) >= self.settle_seconds

        # (b) snapshot stability
        stable = st.is_stable(self.required_stable_polls)

        if not (settle_ok and stable):
            return {
                "folder": folder.name,
                "action": "wait",
                "reason": (
                    f"settle_ok={settle_ok} stable={stable} "
                    f"polls={len(st.snapshots)}/{self.required_stable_polls}"
                ),
            }

        # Quiescent — invoke the pipeline runner. On success, .ssa_run.json
        # is updated; on failure, write .ssa_run.error and reset state so
        # the next cycle can retry once inputs change again.
        try:
            payload = self.runner(folder)  # type: ignore[misc]
        except Exception as exc:
            log.exception("pipeline failed for %s", folder)
            (folder / ".ssa_run.error").write_text(
                f"{type(exc).__name__}: {exc}\n", encoding="utf-8",
            )
            st.reset()
            return {"folder": folder.name, "action": "error", "error": str(exc)}

        # Clear any prior error sentinel after a clean run.
        err = folder / ".ssa_run.error"
        if err.exists():
            try:
                err.unlink()
            except OSError:
                pass

        # Outputs are now recorded — refresh stability state so the very
        # next poll doesn't immediately re-fire on the just-written files.
        st.reset()

        return {
            "folder": folder.name,
            "action": "ran",
            "skipped": bool(payload.get("skipped")),
            "staging_status": payload.get("staging_status"),
        }

    # --- long-run convenience -----------------------------------------

    def run_forever(self, poll_seconds: int = 30) -> None:
        log.info(
            "watcher start: root=%s settle=%ss polls=%d cadence=%ds",
            self.watch_root, self.settle_seconds,
            self.required_stable_polls, poll_seconds,
        )
        while True:
            try:
                results = self.tick()
            except Exception:
                log.exception("watcher tick failed; continuing")
                results = []
            for r in results:
                if r["action"] == "ran":
                    log.info("ran: %s status=%s skipped=%s",
                             r["folder"], r.get("staging_status"),
                             r.get("skipped"))
                elif r["action"] == "error":
                    log.error("error: %s — %s", r["folder"], r.get("error"))
                elif r["action"] == "frozen":
                    log.info("frozen: %s", r["folder"])
                # "wait" / "skip" are debug-only to avoid log spam.
                else:
                    log.debug("%s: %s %s", r["folder"], r["action"],
                              r.get("reason", ""))
            time.sleep(poll_seconds)

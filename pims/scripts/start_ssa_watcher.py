"""Long-running entry for the SSA watcher.

    python -m pims.scripts.start_ssa_watcher "G:\\My Drive\\alan_mcxico\\SSA-evidence"

Install via Windows Scheduled Task at logon. Logs to
``pims/audits/ssa_watcher.log`` and stderr.
"""
from __future__ import annotations

import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from pims.services.ssa_watcher import Watcher


def _setup_logging(log_path: Path, verbose: bool) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s | %(message)s",
    )
    file_h = RotatingFileHandler(
        log_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8",
    )
    file_h.setFormatter(fmt)
    stream_h = logging.StreamHandler(sys.stderr)
    stream_h.setFormatter(fmt)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(file_h)
    root.addHandler(stream_h)
    root.setLevel(logging.DEBUG if verbose else logging.INFO)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="start_ssa_watcher")
    ap.add_argument("watch_root", type=Path)
    ap.add_argument("--settle-seconds", type=int, default=120)
    ap.add_argument("--required-stable-polls", type=int, default=4)
    ap.add_argument("--poll-seconds", type=int, default=30)
    default_log = (
        Path(__file__).resolve().parent.parent / "audits" / "ssa_watcher.log"
    )
    ap.add_argument("--log-file", type=Path, default=default_log)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    if not args.watch_root.is_dir():
        print(f"error: watch_root is not a directory: {args.watch_root}",
              file=sys.stderr)
        return 1

    _setup_logging(args.log_file, args.verbose)
    Watcher(
        watch_root=args.watch_root,
        settle_seconds=args.settle_seconds,
        required_stable_polls=args.required_stable_polls,
    ).run_forever(poll_seconds=args.poll_seconds)
    return 0  # never reached


if __name__ == "__main__":
    raise SystemExit(main())

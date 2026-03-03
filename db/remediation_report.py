#!/usr/bin/env python3
"""
db/remediation_report.py — One-time library remediation report.

Scores every task in the DB using validate_task().
Writes a markdown report to db/remediation_needed.md listing
all failed tasks, their hard errors, and the offending bullets.

Usage:
    python db/remediation_report.py
"""

import os
import re
import sqlite3
from datetime import datetime

_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_DIR)
DB_PATH = os.path.join(_DIR, "gatekeeper.db")
REPORT_PATH = os.path.join(_DIR, "remediation_needed.md")

import sys
sys.path.insert(0, _ROOT)

from core.library import _load_task_from_row
from core.validate import validate_task


# ============================================================
# ERROR PARSING
# ============================================================

def _parse_error(error_str: str) -> tuple[str, str]:
    """
    Return (label, bullet_preview) from a validate_task error string.

    Error strings look like:
      "Check 9 — Fog score 28.2 exceeds hard cap 14 in controls: 'bullet…'"
      "Check 6 — Bullet exceeds 18-word hard cap (19 words) in admin: 'bullet…'"
      "Check 2 — CCVS code 'WAH' found embedded in controls: 'bullet…'"
    """
    # Extract check number and a short descriptor
    check_m = re.match(r"Check (\d+)\s*[—–-]\s*(.+)", error_str)
    if not check_m:
        return error_str, ""

    check_num = check_m.group(1)
    detail = check_m.group(2)

    # Build label: "Check N (short reason)"
    fog_m = re.search(r"Fog score ([\d.]+)", detail)
    words_m = re.search(r"\((\d+) words\)", detail)
    if fog_m:
        label = f"Check {check_num} (Fog {fog_m.group(1)})"
    elif words_m:
        label = f"Check {check_num} (Word cap {words_m.group(1)} words)"
    else:
        # Generic: use first meaningful word
        label = f"Check {check_num}"

    # Extract the offending bullet — first quoted string after the field name
    # e.g. "in controls: 'bullet text…' (complex words: [...])"
    bullet_m = re.search(r":\s*'([^']+)'", error_str)
    bullet = bullet_m.group(1) if bullet_m else ""

    return label, bullet


# ============================================================
# MAIN
# ============================================================

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    rows = cur.execute(
        "SELECT * FROM Tasks ORDER BY id"
    ).fetchall()

    total = len(rows)
    failed_tasks = []

    for row in rows:
        task_block = _load_task_from_row(cur, row)
        result = validate_task(task_block)

        if not result.passed:
            failed_tasks.append({
                "id": row["id"],
                "name": row["task_name"],
                "errors": result.errors,
            })

    conn.close()

    passed_count = total - len(failed_tasks)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = []
    lines.append("# Gatekeeper — Library Remediation Report")
    lines.append(f"Generated: {generated_at}")
    lines.append(f"Tasks passing: {passed_count}/{total}")
    lines.append(f"Tasks needing remediation: {len(failed_tasks)}/{total}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Tasks Requiring Manual Review")
    lines.append("")

    for entry in failed_tasks:
        lines.append(f"### Task {entry['id']} — {entry['name']}")
        lines.append(f"**Hard errors: {len(entry['errors'])}**")
        for err in entry["errors"]:
            label, bullet = _parse_error(err)
            if bullet:
                lines.append(f"- {label}: `{bullet}`")
            else:
                lines.append(f"- {label}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Remediation Instructions")
    lines.append(
        "Each task above needs manual editing before it passes the "
        "validator. Edit the task directly in the database or rebuild "
        "the seed entry in SWMS_TASK_LIBRARY.md."
    )
    lines.append(
        "Run `python main.py score <id>` after each edit to confirm."
    )
    lines.append("")

    report = "\n".join(lines)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Tasks passing:             {passed_count}/{total}")
    print(f"Tasks needing remediation: {len(failed_tasks)}/{total}")
    print(f"Report written to:         {REPORT_PATH}")


if __name__ == "__main__":
    main()

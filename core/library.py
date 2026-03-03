#!/usr/bin/env python3
"""
core/library.py — Task library: fuzzy lookup, AI generation fallback,
save and approve.

query_task(task_name, user) → TaskBlock
  Fuzzy-matches against approved DB tasks.
  >= 85: LIBRARY_HIT, return task.
  60–84: LIBRARY_HIT with warning appended.
  < 60: LIBRARY_MISS, falls back to generate_task().

save_task(task, approved_by) → int
  Persists TaskBlock to Tasks + Controls + Responsibility tables.

approve_task(task_id, approved_by) → None
  Sets status='approved', approved=1 for the given task_id.
"""

import os
import sqlite3
from datetime import datetime

from rapidfuzz import fuzz

from core.schema import AuditEvent, TaskBlock
from core.generate import generate_task
from core.validate import validate_task
from core.audit import log_event

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_ROOT, "db", "gatekeeper.db")


# ============================================================
# DB → TaskBlock reconstruction
# ============================================================

def _load_task_from_row(cur: sqlite3.Cursor, row: sqlite3.Row) -> TaskBlock:
    """Reconstruct a TaskBlock from a Tasks row + related tables."""
    task_id = row["id"]

    controls_rows = cur.execute(
        "SELECT control_type, content FROM Controls "
        "WHERE task_id = ? ORDER BY order_index",
        (task_id,),
    ).fetchall()

    field_map: dict[str, list[str]] = {
        "hold_point": [],
        "control":    [],
        "stop_work":  [],
        "admin":      [],
        "ppe":        [],
    }
    for cr in controls_rows:
        ctype = cr["control_type"] or "control"
        field_map.setdefault(ctype, []).append(cr["content"])

    resp_rows = cur.execute(
        "SELECT role, obligation FROM Responsibility WHERE task_id = ?",
        (task_id,),
    ).fetchall()
    responsibility = {r["role"]: r["obligation"] for r in resp_rows}
    if not responsibility:
        responsibility = {"SUP": ""}

    return TaskBlock(
        task=row["task_name"],
        scope=row["scope"] or "",
        risk_pre=row["risk_pre"] or "",
        risk_post=row["risk_post"] or "",
        hold_points=field_map["hold_point"],
        controls=field_map["control"],
        stop_work=field_map["stop_work"],
        admin=field_map["admin"],
        ppe=field_map["ppe"],
        responsibility=responsibility,
        ccvs_code=row["ccvs_code"],
        wah_applicable=bool(row["wah_applicable"]),
        source=row["source"] or "library",
        approved=bool(row["approved"]),
        version=row["version"] or "1.0",
    )


# ============================================================
# QUERY
# ============================================================

def query_task(task_name: str, user: str = "system") -> TaskBlock:
    """
    Look up a task by name using fuzzy matching.

    Score >= 80 → LIBRARY_HIT, return task.
    Score 50–79 → LIBRARY_HIT with low-confidence warning.
    Score < 50  → LIBRARY_MISS, call generate_task().

    All results pass through validate_task() before returning.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT * FROM Tasks WHERE approved = 1"
        ).fetchall()

        if not rows:
            log_event(AuditEvent(
                event_type="LIBRARY_MISS",
                user=user,
                inputs=task_name,
            ))
            return generate_task(task_name, user=user)

        # Fuzzy match against task_name column
        best_score = 0
        best_row = None
        for row in rows:
            score = fuzz.token_set_ratio(
                task_name.lower(), row["task_name"].lower()
            )
            if score > best_score:
                best_score = score
                best_row = row

        if best_score >= 50:
            task = _load_task_from_row(cur, best_row)
            log_event(AuditEvent(
                event_type="LIBRARY_HIT",
                task_id=best_row["id"],
                user=user,
                inputs=task_name,
                output_hash=str(best_score),
            ))
            result = validate_task(task)
            if best_score < 80:
                result.warnings.insert(
                    0,
                    f"Low-confidence library match (score {best_score}) — "
                    f"review task content before use.",
                )
            return task

        # score < 60 → generate
        log_event(AuditEvent(
            event_type="LIBRARY_MISS",
            user=user,
            inputs=task_name,
            output_hash=str(best_score),
        ))
        return generate_task(task_name, user=user)

    finally:
        conn.close()


# ============================================================
# SAVE
# ============================================================

def save_task(task: TaskBlock, approved_by: str = None) -> int:
    """
    Persist TaskBlock to Tasks + Controls + Responsibility tables.
    Returns new task id.
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO Tasks (
                task_name, scope, version, status,
                risk_pre, risk_post, ccvs_code,
                wah_applicable, source, approved, approved_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task.task,
                task.scope,
                task.version,
                "approved" if task.approved else "draft",
                task.risk_pre,
                task.risk_post,
                task.ccvs_code,
                1 if task.wah_applicable else 0,
                task.source,
                1 if task.approved else 0,
                approved_by,
            ),
        )
        task_id = cur.lastrowid

        field_to_type = {
            "hold_points": "hold_point",
            "controls":    "control",
            "stop_work":   "stop_work",
            "admin":       "admin",
            "ppe":         "ppe",
        }
        order = 0
        for field, ctype in field_to_type.items():
            for item in getattr(task, field, []):
                cur.execute(
                    """INSERT INTO Controls (
                        task_id, control_type, content,
                        order_index, is_ai_generated, reviewed
                    ) VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        task_id, ctype, item, order,
                        1 if task.source == "ai-generated" else 0,
                        1 if task.approved else 0,
                    ),
                )
                order += 1

        for role, obligation in task.responsibility.items():
            cur.execute(
                "INSERT INTO Responsibility (task_id, role, obligation) "
                "VALUES (?, ?, ?)",
                (task_id, role, obligation),
            )

        conn.commit()
        return task_id
    finally:
        conn.close()


# ============================================================
# APPROVE
# ============================================================

def approve_task(task_id: int, approved_by: str) -> None:
    """Set status='approved', approved=1, approved_by, approved_at for task_id."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """UPDATE Tasks
               SET status = 'approved',
                   approved = 1,
                   approved_by = ?,
                   approved_at = datetime('now')
               WHERE id = ?""",
            (approved_by, task_id),
        )
        conn.commit()
    finally:
        conn.close()

#!/usr/bin/env python3
"""
core/audit.py — AuditLog persistence layer.

log_event(event)  → insert AuditEvent into AuditLog, return new row id
get_log(task_id, limit) → return recent audit events as list of dicts
"""

import json
import os
import sqlite3

from core.schema import AuditEvent

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_ROOT, "db", "gatekeeper.db")


def log_event(event: AuditEvent) -> int:
    """Insert AuditEvent into AuditLog. Returns new row id."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO AuditLog (
                event_type, task_id, user, timestamp,
                inputs, output_hash, ai_unapproved
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                event.event_type,
                event.task_id,
                event.user,
                event.timestamp,
                event.inputs,
                event.output_hash,
                1 if event.ai_unapproved else 0,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_log(task_id: int = None, limit: int = 50) -> list[dict]:
    """Return recent audit events, optionally filtered by task_id."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        if task_id is not None:
            cur.execute(
                """SELECT * FROM AuditLog
                   WHERE task_id = ?
                   ORDER BY id DESC LIMIT ?""",
                (task_id, limit),
            )
        else:
            cur.execute(
                "SELECT * FROM AuditLog ORDER BY id DESC LIMIT ?",
                (limit,),
            )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

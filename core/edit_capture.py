"""
core/edit_capture.py — Compare generated SWMS docx to consultant-reviewed docx.

Extracts structured edit signals without storing raw document content.
Consultant stays in Word. Only edit-signal metadata is persisted.
"""

from __future__ import annotations

import difflib
import hashlib
import json
from io import BytesIO
from typing import Optional


def extract_swms_table_text(file_bytes: bytes) -> list[dict]:
    """Extract task rows from the SWMS table in a docx file.

    Scans all tables and selects the first whose header row contains "Task"
    and at least one of: Hazard, Control(s), Responsibility, CCVS.

    Returns list of normalized row dicts (no formatting metadata).
    Raises ValueError if no matching table found.
    """
    from docx import Document

    doc = Document(BytesIO(file_bytes))

    _REQUIRED = "task"
    _ANY_OF = ("hazard", "control", "controls", "responsibility", "ccvs")

    target_table = None
    header_map: dict[str, int] = {}

    for table in doc.tables:
        if not table.rows:
            continue
        header_cells = [c.text.strip().lower() for c in table.rows[0].cells]
        if _REQUIRED not in header_cells:
            continue
        if not any(kw in header_cells for kw in _ANY_OF):
            continue
        # Found matching table
        target_table = table
        for i, h in enumerate(header_cells):
            header_map[h] = i
        break

    if target_table is None:
        raise ValueError("SWMS table not found - check column headers")

    # Map known column names to output keys
    _COL_MAP = {
        "task": "task",
        "hazard": "hazards",
        "hazards": "hazards",
        "control": "controls",
        "controls": "controls",
        "responsibility": "responsibility",
        "ccvs": "ccvs",
        "ccvs code": "ccvs",
    }

    rows: list[dict] = []
    for ri, row in enumerate(target_table.rows):
        if ri == 0:
            continue  # skip header
        cells = [c.text.strip() for c in row.cells]
        entry: dict = {"row_index": ri}
        for col_name, col_idx in header_map.items():
            output_key = _COL_MAP.get(col_name)
            if output_key and col_idx < len(cells):
                entry[output_key] = cells[col_idx]
        # Only include rows that have task content
        if entry.get("task"):
            rows.append(entry)

    return rows


def fingerprint_snapshot(rows: list[dict]) -> str:
    """Return sha256 of the JSON-serialized normalized rows (excluding row_index)."""
    # Strip row_index for content-only fingerprint
    content = [{k: v for k, v in r.items() if k != "row_index"} for r in rows]
    serialized = json.dumps(content, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_edit_delta(
    generated_rows: list[dict],
    reviewed_rows: list[dict],
) -> dict:
    """Compare generated vs reviewed rows and return structured edit signals.

    Uses difflib.SequenceMatcher for row-level similarity.
    """
    gen_count = len(generated_rows)
    rev_count = len(reviewed_rows)
    total = max(gen_count, rev_count)

    if total == 0:
        return {
            "changed_task_count": 0,
            "total_task_count": 0,
            "generated_row_count": 0,
            "reviewed_row_count": 0,
            "average_similarity_ratio": 1.0,
            "changed_responsibilities_count": 0,
            "major_rewrite_detected": False,
        }

    similarities: list[float] = []
    changed_tasks = 0
    changed_responsibilities = 0
    pairs = min(gen_count, rev_count)

    for i in range(pairs):
        gen = generated_rows[i]
        rev = reviewed_rows[i]

        # Compare task + controls text
        gen_text = (gen.get("task", "") + " " + gen.get("controls", "")).strip()
        rev_text = (rev.get("task", "") + " " + rev.get("controls", "")).strip()
        ratio = difflib.SequenceMatcher(None, gen_text, rev_text).ratio()
        similarities.append(ratio)

        if ratio < 0.95:
            changed_tasks += 1

        # Check responsibility changes
        gen_resp = gen.get("responsibility", "").strip()
        rev_resp = rev.get("responsibility", "").strip()
        if gen_resp != rev_resp and rev_resp:
            changed_responsibilities += 1

    # Rows that exist in one but not the other count as changed
    changed_tasks += abs(gen_count - rev_count)

    avg_sim = sum(similarities) / len(similarities) if similarities else 0.0

    return {
        "changed_task_count": changed_tasks,
        "total_task_count": total,
        "generated_row_count": gen_count,
        "reviewed_row_count": rev_count,
        "average_similarity_ratio": round(avg_sim, 3),
        "changed_responsibilities_count": changed_responsibilities,
        "major_rewrite_detected": avg_sim < 0.7,
    }

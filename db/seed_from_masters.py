#!/usr/bin/env python3
"""
db/seed_from_masters.py — Load tasks from *_Master.txt files via Claude API.

Scans docs/ for files matching *_Master.txt, sends each to Claude API
with an extraction prompt, parses the returned JSON, and inserts into
db/gatekeeper.db.

Seeded tasks are marked: source='library', approved=0
(they require human review before use in generation).

Usage:
    python db/seed_from_masters.py

Requires:
    ANTHROPIC_API_KEY environment variable
    pip install anthropic
"""

import glob
import hashlib
import json
import os
import sqlite3
import sys

_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_dir)
DB_PATH = os.path.join(_dir, 'gatekeeper.db')
DOCS_DIR = os.path.join(PROJECT_ROOT, 'docs')
MASTER_GLOB = os.path.join(DOCS_DIR, '**', '*_Master.txt')

EXTRACTION_SYSTEM_PROMPT = (
    "Extract SWMS task blocks from this WHS reference document. "
    "Output a JSON array. Each item: {task_name, scope, controls[], "
    "hold_points[], stop_work[], admin[], ppe[], risk_pre, risk_post, "
    "wah_applicable}. Output JSON only."
)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096


# ============================================================
# CLAUDE API EXTRACTION
# ============================================================

def extract_tasks_via_api(text: str, client) -> list[dict]:
    """Send text to Claude API and return parsed JSON task list."""
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    raw = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    return json.loads(raw)


# ============================================================
# DB INSERT
# ============================================================

def insert_task(cur: sqlite3.Cursor, task: dict, source_file: str) -> tuple[int, int]:
    """Insert one task dict. Returns (task_id, controls_inserted)."""
    task_name = str(task.get('task_name', '')).strip()
    scope = str(task.get('scope', '')).strip()
    risk_pre = str(task.get('risk_pre', '')).strip()
    risk_post = str(task.get('risk_post', '')).strip()
    wah = 1 if task.get('wah_applicable') else 0

    cur.execute(
        """INSERT INTO Tasks (
            task_name, scope, version, status,
            risk_pre, risk_post,
            wah_applicable, source, approved, approved_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            task_name, scope, '1.0', 'draft',
            risk_pre, risk_post,
            wah, 'library', 0, source_file,
        ),
    )
    task_id = cur.lastrowid
    controls_inserted = 0

    field_to_type = {
        'hold_points': 'hold_point',
        'stop_work':   'stop_work',
        'admin':       'admin',
        'ppe':         'ppe',
        'controls':    'control',
    }
    order = 0
    for field, ctype in field_to_type.items():
        for item in task.get(field, []):
            cur.execute(
                """INSERT INTO Controls (
                    task_id, control_type, content,
                    order_index, is_ai_generated, reviewed
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                (task_id, ctype, str(item).strip(), order, 1, 0),
            )
            controls_inserted += 1
            order += 1

    return task_id, controls_inserted


# ============================================================
# MAIN
# ============================================================

def main():
    try:
        import anthropic
    except ImportError:
        print("ERROR: anthropic package not installed. Run: pip install anthropic")
        sys.exit(1)

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    master_files = sorted(glob.glob(MASTER_GLOB, recursive=True))
    if not master_files:
        print(f"No *_Master.txt files found under {DOCS_DIR}")
        print("Nothing to seed.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    total_tasks = 0
    total_controls = 0
    total_skipped = 0
    failures = []

    for filepath in master_files:
        filename = os.path.basename(filepath)
        print(f"Processing: {filename} ...", end=' ', flush=True)

        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()

        try:
            tasks = extract_tasks_via_api(text, client)
        except Exception as exc:
            print(f"FAILED (API error: {exc})")
            failures.append(f"{filename}: {exc}")
            continue

        file_tasks = 0
        file_controls = 0

        for task in tasks:
            task_name = str(task.get('task_name', '')).strip()
            if not task_name:
                continue

            # Duplicate check
            if cur.execute('SELECT id FROM Tasks WHERE task_name = ?',
                           (task_name,)).fetchone():
                total_skipped += 1
                continue

            try:
                _, nc = insert_task(cur, task, filename)
                file_tasks += 1
                file_controls += nc
            except Exception as exc:
                failures.append(f"{filename}/{task_name}: {exc}")

        conn.commit()
        total_tasks += file_tasks
        total_controls += file_controls
        print(f"{file_tasks} tasks, {file_controls} controls")

    conn.close()

    print()
    print(f"Tasks seeded:              {total_tasks}")
    print(f"Controls inserted:         {total_controls}")
    print(f"Duplicates skipped:        {total_skipped}")
    print(f"Parse/API failures:        {len(failures)}")
    if failures:
        for name in failures:
            print(f"  - {name}")
    print()
    print("Note: seeded tasks have approved=0 — review before use in generation.")


if __name__ == '__main__':
    main()

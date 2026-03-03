#!/usr/bin/env python3
"""
db/seed.py — Load SWMS task library into SQLite database.

Reads src/SWMS_TASK_LIBRARY.md, parses all Python dict task blocks,
and inserts into db/gatekeeper.db.

Mark all seeded tasks: source='library', approved=1,
approved_by='SWMS_TASK_LIBRARY_v1', status='approved'.
"""

import ast
import os
import re
import sqlite3
import sys

_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_dir)
DB_PATH = os.path.join(_dir, 'gatekeeper.db')
LIBRARY_PATH = os.path.join(PROJECT_ROOT, 'src', 'SWMS_TASK_LIBRARY.md')


# ============================================================
# RISK LABEL
# ============================================================

_RISK_LABELS = {1: "Low", 2: "Low", 3: "Low", 4: "Medium", 6: "High", 9: "High"}

def _risk_label(score) -> str:
    if not score:
        return ""
    label = _RISK_LABELS.get(int(score), "Unknown")
    return f"{label}-{score}"


# ============================================================
# TASK BLOCK EXTRACTION
# ============================================================

def extract_task_blocks(content: str) -> list[tuple[str, dict | None]]:
    """Return list of (heading, dict_or_None) for every ### section."""
    results = []
    sections = re.split(r'^###\s+', content, flags=re.MULTILINE)
    for section in sections[1:]:
        lines = section.split('\n', 1)
        heading = lines[0].strip()
        body = lines[1] if len(lines) > 1 else ''

        # First ```python block in this section
        match = re.search(r'```python\s*\n(\{.*?\}),?\s*\n```', body, re.DOTALL)
        if not match:
            results.append((heading, None))
            continue

        code = match.group(1)
        try:
            d = ast.literal_eval(code)
            results.append((heading, d))
        except Exception as exc:
            results.append((heading, None))
            print(f"  [parse failure] {heading}: {exc}")

    return results


# ============================================================
# CONTROL LINE PARSING
# ============================================================

_PPE_KEYWORDS = {
    'respirator', 'harness', 'gloves', 'helmet', 'hard hat',
    'hi-vis', 'vest or shirt', 'mask', 'goggles', 'steel-capped',
    'footwear', 'lanyard', 'earplugs', 'coverall', 'face shield',
}

_ADMIN_KEYWORDS = {
    'toolbox', 'sign-in', 'sds', 'competent person', 'briefed',
    'pre-start', 'load limit', 'do not modify', 'inspect before',
    'record', 'license', 'licence', 'certificate', 'briefing',
    'induction', 'permit',
}

def classify_control(line: str) -> str:
    """Map a single control line to a control_type."""
    ll = line.lower()

    if ('hold point' in ll
            or 'work must not commence' in ll
            or 'do not start' in ll):
        return 'hold_point'

    if ('remove from exposure' in ll
            or 'stop work' in ll
            or ll.startswith('stop and implement')):
        return 'stop_work'

    if line.startswith('PPE:') or any(kw in ll for kw in _PPE_KEYWORDS):
        return 'ppe'

    if line.startswith('Admin:') or any(kw in ll for kw in _ADMIN_KEYWORDS):
        return 'admin'

    return 'control'


def parse_control_lines(controls_str: str) -> list[tuple[str, str]]:
    """Return (control_type, content) for each non-empty control line."""
    results = []
    for line in controls_str.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Skip risk-header lines: e.g. "WFR (High — C=3): Controls in place."
        if re.match(r'^[A-Z]{2,4}\s+\(', line) and 'Controls in place' in line:
            continue
        results.append((classify_control(line), line))
    return results


# ============================================================
# WAH DETECTION
# ============================================================

def is_wah_task(d: dict) -> int:
    """Return 1 if task involves Working at Heights controls."""
    audit = d.get('audit', '')
    if re.search(r'\bWAH\b', audit):
        return 1
    task_lower = d.get('task', '').lower()
    wah_keywords = {'height', 'elevated', 'scaffold', 'ewp', 'rope access',
                    'ladder', 'aerial', 'boom lift', 'scissor lift', 'swing stage'}
    if any(kw in task_lower for kw in wah_keywords):
        return 1
    return 0


# ============================================================
# RESPONSIBILITY PARSING
# ============================================================

_ROLE_MAP = {
    'supervisor': 'SUP',
    'worker': 'WKR',
    'subcontractor': 'SUB',
    'operator': 'OP',
    'pm': 'PM',
    'project manager': 'PM',
}

def parse_role(resp_str: str) -> str:
    """Return best role code from resp string."""
    for keyword, code in _ROLE_MAP.items():
        if keyword in resp_str.lower():
            return code
    return 'SUP'


# ============================================================
# SEED
# ============================================================

def seed(conn: sqlite3.Connection, content: str) -> dict:
    cur = conn.cursor()

    seeded = 0
    controls_inserted = 0
    wah_count = 0
    skipped = 0
    failures = []

    for heading, d in extract_task_blocks(content):
        if d is None:
            failures.append(heading)
            continue

        # Split "task" field into name + scope
        task_text = d.get('task', '').strip()
        task_parts = task_text.split('\n', 1)
        task_name = task_parts[0].strip()
        scope = task_parts[1].strip() if len(task_parts) > 1 else ''

        # Duplicate check
        if cur.execute('SELECT id FROM Tasks WHERE task_name = ?',
                       (task_name,)).fetchone():
            skipped += 1
            continue

        pre = d.get('pre', '')
        post = d.get('post', '')
        audit = d.get('audit', '')

        # CCVS code: only set when audit is a CCVS audit string
        ccvs_code = None
        if audit.startswith('CCVS-'):
            ccvs_code = audit.rsplit('-', 1)[-1]

        wah = is_wah_task(d)
        if wah:
            wah_count += 1

        cur.execute(
            """INSERT INTO Tasks (
                task_name, scope, version, status,
                risk_pre, risk_post, ccvs_code,
                wah_applicable, source, approved, approved_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task_name, scope, '1.0', 'approved',
                _risk_label(pre), _risk_label(post), ccvs_code,
                wah, 'library', 1, 'SWMS_TASK_LIBRARY_v1',
            ),
        )
        task_id = cur.lastrowid
        seeded += 1

        # Controls
        for order, (ctype, content_line) in enumerate(
            parse_control_lines(d.get('controls', ''))
        ):
            cur.execute(
                """INSERT INTO Controls (
                    task_id, control_type, content,
                    order_index, is_ai_generated, reviewed
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                (task_id, ctype, content_line, order, 0, 1),
            )
            controls_inserted += 1

        # Responsibility — one row per slash-separated role
        resp_str = d.get('resp', 'Supervisor')
        role_parts = [p.strip() for p in resp_str.split('/')]
        obligation = d.get('control_summary', f"Implement {task_name} controls.")
        for rp in role_parts:
            role_code = parse_role(rp)
            cur.execute(
                'INSERT INTO Responsibility (task_id, role, obligation) VALUES (?, ?, ?)',
                (task_id, role_code, obligation),
            )

    conn.commit()

    return {
        'seeded': seeded,
        'controls_inserted': controls_inserted,
        'wah_count': wah_count,
        'skipped': skipped,
        'failures': failures,
    }


# ============================================================
# MAIN
# ============================================================

def main():
    if not os.path.exists(LIBRARY_PATH):
        print(f"ERROR: Library not found at {LIBRARY_PATH}")
        sys.exit(1)

    with open(LIBRARY_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    conn = sqlite3.connect(DB_PATH)
    try:
        report = seed(conn, content)
    finally:
        conn.close()

    print(f"Tasks seeded:              {report['seeded']}")
    print(f"Controls inserted:         {report['controls_inserted']}")
    print(f"Tasks with wah_applicable: {report['wah_count']}")
    print(f"Duplicates skipped:        {report['skipped']}")
    print(f"Parse failures:            {len(report['failures'])}")
    if report['failures']:
        for name in report['failures']:
            print(f"  - {name}")


if __name__ == '__main__':
    main()

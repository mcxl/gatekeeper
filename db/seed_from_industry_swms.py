#!/usr/bin/env python3
"""
db/seed_from_industry_swms.py — Extract and seed SWMS tasks from industry .doc files.

Reads all .doc files from reference-docs/industry-swms/ using raw binary
text extraction (files are OLE binary format, not .docx). Extracts task
blocks via Claude API, validates each against core/validate.py, and saves
passing tasks as approved=0, status=draft, version=industry-1.0.

Usage:
    python db/seed_from_industry_swms.py

Failures are logged to db/industry_swms_failures.txt.
"""

import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime

import anthropic
from dotenv import load_dotenv

load_dotenv()

_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_DIR)
sys.path.insert(0, _ROOT)

DB_PATH = os.path.join(_DIR, "gatekeeper.db")
SWMS_DIR = os.path.join(_ROOT, "reference-docs", "industry-swms")
FAILURES_PATH = os.path.join(_DIR, "industry_swms_failures.txt")

from core.schema import TaskBlock
from core.validate import validate_task, WAH_SENTENCE

CHUNK_SIZE = 12000
API_DELAY = 1.5
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096

EXTRACT_SYSTEM_PROMPT = (
    "You are an Australian WHS specialist. Extract SWMS task blocks "
    "from this Safe Work Method Statement or hazard information sheet. "
    "These documents describe plant, equipment, or work tasks with hazards "
    "and control measures. "
    "Output a JSON array. Each item must match exactly: "
    "{task_name, scope, controls[], hold_points[], stop_work[], "
    "admin[], ppe[], risk_pre, risk_post, wah_applicable} "
    "Only extract tasks directly supported by the document content. "
    "IMPORTANT — WAH rule: if wah_applicable is true, controls[0] MUST be "
    "this exact sentence verbatim:\n"
    + WAH_SENTENCE
    + "\nDo not paraphrase it. Copy it exactly as the first control.\n"
    "Output JSON only. No commentary."
)

GENERATION_RULES = (
    "\n\nRULES FOR EACH FIELD:\n"
    "- task_name: short imperative phrase, e.g. 'Operate Air Compressor'\n"
    "- scope: one sentence describing what the task covers\n"
    "- controls[]: DO NOT copy source text verbatim. REWRITE each control as a "
    "verb-first bullet using plain words (1-2 syllables where possible). "
    "Max 18 words per bullet. Active voice. No abstract nouns. "
    "Gunning Fog score must be below 14 — if a bullet has 3+ words with "
    "3+ syllables, split it into two shorter bullets.\n"
    "- hold_points[]: 2-4 items. 'Do not proceed until X confirmed' format.\n"
    "- stop_work[]: 2-4 items. 'Stop work if X occurs' format. Plain words only.\n"
    "- admin[]: 1-3 items. Record-keeping actions only. "
    "Start with: Brief, Record, Review, Notify, Check.\n"
    "- ppe[]: equipment names only, one item per entry, no commas within an entry\n"
    "- risk_pre: one of Low-1, Low-2, Low-3, Medium-4, High-6, High-9\n"
    "- risk_post: one of Low-1, Low-2, Low-3, Medium-4, High-6, High-9\n"
    "- wah_applicable: true if task involves work above 1.5m, else false\n"
    "Return [] if no clear SWMS tasks are present in the text."
)

DEFAULT_RESPONSIBILITY = {
    "SUP": "Implement controls, approve hold points, and stop work if unsafe.",
    "WKR": "Follow all controls, wear PPE, and stop work if hazard arises.",
}

VALID_RISK_LEVELS = {"Low-1", "Low-2", "Low-3", "Medium-4", "High-6", "High-9"}


# ============================================================
# .DOC TEXT EXTRACTION (binary OLE — extract printable ASCII)
# ============================================================

def extract_doc_text(doc_path: str) -> str:
    """Extract readable text from a binary .doc file via regex on raw bytes."""
    with open(doc_path, "rb") as f:
        raw = f.read()
    # Extract sequences of printable ASCII chars (length ≥ 4)
    strings = re.findall(rb"[ -~]{4,}", raw)
    text = "\n".join(s.decode("ascii", errors="ignore") for s in strings)
    # Collapse runs of whitespace-only lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Drop obvious OLE metadata junk at the start
    lines = text.splitlines()
    clean = []
    for line in lines:
        stripped = line.strip()
        # Skip short junk lines that look like binary artefacts
        if len(stripped) >= 3 and not re.match(r"^[^a-zA-Z]{0,3}$", stripped):
            clean.append(stripped)
    return "\n".join(clean)


# ============================================================
# API
# ============================================================

def call_api(client: anthropic.Anthropic, text: str) -> str:
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=EXTRACT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text + GENERATION_RULES}],
    )
    return message.content[0].text.strip()


def parse_response(raw: str) -> list[dict]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        end = next(
            (i for i in range(len(lines) - 1, 0, -1) if lines[i].strip() == "```"),
            len(lines),
        )
        text = "\n".join(lines[1:end])
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


# ============================================================
# TASK CONVERSION
# ============================================================

def _normalise_risk(value: str) -> str:
    if value in VALID_RISK_LEVELS:
        return value
    v = str(value).strip().lower()
    if v.startswith("high"):
        return "High-6"
    if v.startswith("low"):
        return "Low-2"
    return "Medium-4"


def dict_to_taskblock(d: dict) -> "TaskBlock | None":
    task_name = str(d.get("task_name", "")).strip()
    if not task_name:
        return None

    def _clean_list(key: str) -> list[str]:
        items = d.get(key, [])
        if not isinstance(items, list):
            return []
        return [str(i).strip() for i in items if str(i).strip()]

    wah = bool(d.get("wah_applicable", False))
    controls = _clean_list("controls")
    if wah:
        if not controls or controls[0].strip() != WAH_SENTENCE.strip():
            controls = [WAH_SENTENCE] + [c for c in controls if c.strip() != WAH_SENTENCE.strip()]

    return TaskBlock(
        task=task_name,
        scope=str(d.get("scope", "")).strip(),
        risk_pre=_normalise_risk(d.get("risk_pre", "Medium-4")),
        risk_post=_normalise_risk(d.get("risk_post", "Low-2")),
        hold_points=_clean_list("hold_points"),
        controls=controls,
        stop_work=_clean_list("stop_work"),
        admin=_clean_list("admin"),
        ppe=_clean_list("ppe"),
        responsibility=DEFAULT_RESPONSIBILITY.copy(),
        wah_applicable=wah,
        source="library",
        approved=False,
        version="industry-1.0",
    )


# ============================================================
# DB
# ============================================================

def _existing_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT task_name FROM Tasks").fetchall()
    return {r[0].lower() for r in rows}


def save_task(conn: sqlite3.Connection, task: TaskBlock) -> int:
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO Tasks (
            task_name, scope, version, status,
            risk_pre, risk_post, ccvs_code,
            wah_applicable, source, approved, approved_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            task.task, task.scope, task.version, "draft",
            task.risk_pre, task.risk_post, task.ccvs_code,
            1 if task.wah_applicable else 0,
            task.source, 0, None,
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
                (task_id, ctype, item, order, 0, 0),
            )
            order += 1

    for role, obligation in task.responsibility.items():
        cur.execute(
            "INSERT INTO Responsibility (task_id, role, obligation) VALUES (?, ?, ?)",
            (task_id, role, obligation),
        )

    return task_id


# ============================================================
# MAIN
# ============================================================

def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    conn = sqlite3.connect(DB_PATH)

    total_files = 0
    total_extracted = 0
    total_saved = 0
    total_failures = 0
    failure_lines: list[str] = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        existing = _existing_names(conn)

        doc_files = sorted(
            f for f in os.listdir(SWMS_DIR) if f.lower().endswith(".doc")
        )
        print(f"Found {len(doc_files)} .doc files in {SWMS_DIR}")

        for filename in doc_files:
            doc_path = os.path.join(SWMS_DIR, filename)
            print(f"\nProcessing: {filename}")
            total_files += 1

            try:
                text = extract_doc_text(doc_path)
            except Exception as exc:
                print(f"  [ERROR] Text extraction failed: {exc}")
                failure_lines.append(f"{filename} | extraction error: {exc}")
                continue

            if len(text) < 100:
                print(f"  [SKIP] Too little text ({len(text)} chars)")
                continue

            # Send whole document as single chunk (most .doc files are small)
            text_capped = text[:CHUNK_SIZE]
            print(f"  Text: {len(text_capped):,} chars … ", end="", flush=True)

            try:
                raw = call_api(client, text_capped)
            except Exception as exc:
                print(f"API error: {exc}")
                failure_lines.append(f"{filename} | API error: {exc}")
                time.sleep(API_DELAY)
                continue

            tasks_raw = parse_response(raw)
            print(f"{len(tasks_raw)} task(s) found")

            file_saved = 0
            for task_dict in tasks_raw:
                total_extracted += 1
                task_block = dict_to_taskblock(task_dict)
                if task_block is None:
                    total_failures += 1
                    failure_lines.append(f"{filename} | missing task_name")
                    continue

                if task_block.task.lower() in existing:
                    continue

                result = validate_task(task_block)
                if not result.passed:
                    total_failures += 1
                    err_summary = "; ".join(result.errors[:3])
                    failure_lines.append(
                        f"{filename} | FAILED: '{task_block.task}' | {err_summary}"
                    )
                    continue

                try:
                    save_task(conn, task_block)
                    existing.add(task_block.task.lower())
                    total_saved += 1
                    file_saved += 1
                except Exception as exc:
                    total_failures += 1
                    failure_lines.append(
                        f"{filename} | DB save error: '{task_block.task}' | {exc}"
                    )

            conn.commit()
            print(f"  Saved: {file_saved}")
            time.sleep(API_DELAY)

    finally:
        conn.close()

    if failure_lines:
        with open(FAILURES_PATH, "w", encoding="utf-8") as f:
            f.write(f"# Industry SWMS seed failures — {timestamp}\n\n")
            for line in failure_lines:
                f.write(line + "\n")

    print(f"\n{'='*50}")
    print(f"Files processed:             {total_files}")
    print(f"Tasks extracted:             {total_extracted}")
    print(f"Tasks saved to DB:           {total_saved}")
    print(f"Failures logged:             {total_failures}")
    if total_failures:
        print(f"Failures file:               {FAILURES_PATH}")


if __name__ == "__main__":
    main()

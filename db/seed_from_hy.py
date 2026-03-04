#!/usr/bin/env python3
"""
db/seed_from_hy.py — Extract and seed SWMS tasks from Hansen Yuncken procedures.

Reads all PDFs from reference-docs/principal-contractor-procedures/
hansen-yuncken-procedures/ via Claude API. Saves passing tasks as
version="hy-1.0", status=draft, approved=0.

HY procedures are the PRIMARY content authority per CLAUDE.md.
Run this after CoP seeding — hy-1.0 tasks override ref-1.0 on the same topic.

Usage:
    python db/seed_from_hy.py

Failures are logged to db/hy_seed_failures.txt.
"""

import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime

import anthropic
import pypdf
from dotenv import load_dotenv

load_dotenv()

_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_DIR)
sys.path.insert(0, _ROOT)

DB_PATH = os.path.join(_DIR, "gatekeeper.db")
HY_DIR = os.path.join(
    _ROOT,
    "reference-docs",
    "principal-contractor-procedures",
    "hansen-yuncken-procedures",
)
FAILURES_PATH = os.path.join(_DIR, "hy_seed_failures.txt")

from core.schema import TaskBlock
from core.validate import validate_task, WAH_SENTENCE

CHUNK_SIZE = 14000
MAX_CHUNKS = 5
API_DELAY = 1.5
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096

EXTRACT_SYSTEM_PROMPT = (
    "You are an Australian WHS specialist. Extract SWMS task blocks "
    "from this Hansen Yuncken safety procedure document. "
    "HY procedures are the primary authority for construction site safety "
    "in NSW. Focus on: work procedures, critical control requirements, "
    "verification steps, hold points, and stop work triggers. "
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
    "- task_name: short imperative phrase, e.g. 'Erect Temporary Works'\n"
    "- scope: one sentence describing what the task covers\n"
    "- controls[]: DO NOT copy source text verbatim. REWRITE each control as a "
    "verb-first bullet using plain words (1-2 syllables where possible). "
    "Max 18 words per bullet. Active voice. No abstract nouns "
    "(identification, preparation, management, provision, implementation, "
    "assessment, requirement, procedure). "
    "Gunning Fog score must be below 14 — if a bullet has 3+ words with "
    "3+ syllables, split it into two shorter bullets.\n"
    "- hold_points[]: 2-5 items. 'Do not proceed until X confirmed' format. "
    "Plain words only. These are engineer or PC verification gates.\n"
    "- stop_work[]: 2-5 items. 'Stop work if X occurs' format. Plain words only.\n"
    "- admin[]: 1-4 items. Record-keeping and briefing actions only. "
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
# PDF TEXT EXTRACTION
# ============================================================

def extract_pdf_text(pdf_path: str) -> str:
    reader = pypdf.PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        pages.append(text.strip())
    return "\n\n".join(p for p in pages if p)


def split_into_chunks(text: str, chunk_size: int) -> list[str]:
    chunks = []
    while text:
        if len(text) <= chunk_size:
            chunks.append(text)
            break
        cut = text.rfind("\n\n", 0, chunk_size)
        if cut == -1:
            cut = text.rfind(" ", 0, chunk_size)
        if cut == -1:
            cut = chunk_size
        chunks.append(text[:cut].strip())
        text = text[cut:].strip()
    return [c for c in chunks if c]


# ============================================================
# API
# ============================================================

def call_api(client: anthropic.Anthropic, chunk_text: str) -> str:
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=EXTRACT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": chunk_text + GENERATION_RULES}],
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
        version="hy-1.0",
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

    total_pdfs = 0
    total_extracted = 0
    total_saved = 0
    total_failures = 0
    failure_lines: list[str] = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        existing = _existing_names(conn)

        pdf_files = sorted(
            f for f in os.listdir(HY_DIR) if f.lower().endswith(".pdf")
        )
        print(f"Found {len(pdf_files)} PDFs in {HY_DIR}")

        for filename in pdf_files:
            pdf_path = os.path.join(HY_DIR, filename)
            print(f"\nProcessing: {filename}")
            total_pdfs += 1

            try:
                full_text = extract_pdf_text(pdf_path)
            except Exception as exc:
                print(f"  [ERROR] PDF extraction failed: {exc}")
                failure_lines.append(f"{filename} | PDF extraction error: {exc}")
                continue

            all_chunks = split_into_chunks(full_text, CHUNK_SIZE)
            chunks = all_chunks[:MAX_CHUNKS]
            print(f"  Text chunks: {len(chunks)} (of {len(all_chunks)} total, capped at {MAX_CHUNKS})")

            pdf_extracted = 0
            pdf_saved = 0

            for chunk_idx, chunk in enumerate(chunks, 1):
                print(f"  Chunk {chunk_idx}/{len(chunks)} ({len(chunk):,} chars) … ", end="", flush=True)

                try:
                    raw = call_api(client, chunk)
                except Exception as exc:
                    print(f"API error: {exc}")
                    failure_lines.append(f"{filename} chunk {chunk_idx} | API error: {exc}")
                    time.sleep(API_DELAY)
                    continue

                tasks_raw = parse_response(raw)
                print(f"{len(tasks_raw)} task(s) found")

                for task_dict in tasks_raw:
                    total_extracted += 1
                    pdf_extracted += 1

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
                        pdf_saved += 1
                    except Exception as exc:
                        total_failures += 1
                        failure_lines.append(
                            f"{filename} | DB save error: '{task_block.task}' | {exc}"
                        )

                time.sleep(API_DELAY)

            conn.commit()
            print(f"  Done: extracted={pdf_extracted}  saved={pdf_saved}")

    finally:
        conn.close()

    if failure_lines:
        with open(FAILURES_PATH, "w", encoding="utf-8") as f:
            f.write(f"# HY procedure seed failures — {timestamp}\n\n")
            for line in failure_lines:
                f.write(line + "\n")

    print(f"\n{'='*50}")
    print(f"PDFs processed:              {total_pdfs}")
    print(f"Tasks extracted:             {total_extracted}")
    print(f"Tasks saved to DB:           {total_saved}")
    print(f"Failures logged:             {total_failures}")
    if total_failures:
        print(f"Failures file:               {FAILURES_PATH}")


if __name__ == "__main__":
    main()

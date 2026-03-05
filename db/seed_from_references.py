#!/usr/bin/env python3
"""
db/seed_from_references.py — Extract and seed SWMS tasks from WHS reference PDFs.

Processes 10 priority files from docs/references/, extracts task blocks
via Claude API, validates each against core/validate.py, and saves passing
tasks as unapproved library entries (approved=0, status=draft, version=ref-1.0).

Usage:
    python db/seed_from_references.py

Failures are logged to db/reference_seed_failures.txt.
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
REFS_DIR = os.path.join(_ROOT, "docs", "references")
FAILURES_PATH = os.path.join(_DIR, "reference_seed_failures.txt")

from core.schema import TaskBlock
from core.validate import validate_task, WAH_SENTENCE
from vocab.swms_vocabulary import RETIRED_CODES


def remap_code(code):
    if not code:
        return code
    family = code.split('-')[0] if '-' in code else code
    if family in RETIRED_CODES:
        new_family = RETIRED_CODES[family]
        return code.replace(family, new_family, 1)
    return code

# ============================================================
# PRIORITY FILES — process in order, highest yield first
# ============================================================

PRIORITY_FILES = [
    "scaffolding-industry-safety-standard.pdf",
    "WHS-Safe Design of Structures-CoP.pdf",
    "model-code-practice-managing-psychosocial-hazards-work.pdf",
    "model_code_of_practice-how_to_manage_work_health_and_safety_risks-nov24.pdf",
]

CHUNK_SIZE = 14000   # chars per API call (~3500 tokens of content)
MAX_CHUNKS = 5       # per PDF — caps cost and time per file
API_DELAY = 1.5      # seconds between calls

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096

EXTRACT_SYSTEM_PROMPT = (
    "You are an Australian WHS specialist. Extract SWMS task blocks "
    "from this WHS reference document. "
    "Focus on: work procedures, control measures, risk controls, "
    "PPE requirements, hold points, stop work triggers. "
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

# Plain-English rules appended to user message to reduce validation failures
GENERATION_RULES = (
    "\n\nRULES FOR EACH FIELD:\n"
    "- task_name: short imperative phrase, e.g. 'Scaffold Erection and Dismantling'\n"
    "- scope: one sentence describing what the task covers\n"
    "- controls[]: DO NOT copy source text verbatim. REWRITE each control as a "
    "verb-first bullet using plain words (1-2 syllables where possible). "
    "Max 18 words per bullet. Active voice. No abstract nouns "
    "(identification, preparation, management, provision, implementation, "
    "assessment, requirement, procedure). "
    "Gunning Fog score must be below 14 — if a bullet has 3+ words with "
    "3+ syllables, split it into two shorter bullets.\n"
    "- hold_points[]: 2-5 items. 'Do not proceed until X confirmed' format. "
    "Plain words only.\n"
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


# ============================================================
# PDF TEXT EXTRACTION
# ============================================================

def extract_pdf_text(pdf_path: str) -> str:
    """Extract all text from a PDF, returning concatenated page text."""
    reader = pypdf.PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        # Normalise whitespace while preserving paragraph breaks
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        pages.append(text.strip())
    return "\n\n".join(p for p in pages if p)


def split_into_chunks(text: str, chunk_size: int) -> list[str]:
    """
    Split text into chunks of at most chunk_size chars, breaking on
    paragraph boundaries (double newlines) where possible.
    """
    chunks = []
    while text:
        if len(text) <= chunk_size:
            chunks.append(text)
            break
        # Find last paragraph break within chunk_size
        cut = text.rfind("\n\n", 0, chunk_size)
        if cut == -1:
            # No paragraph break — fall back to last space
            cut = text.rfind(" ", 0, chunk_size)
        if cut == -1:
            cut = chunk_size
        chunks.append(text[:cut].strip())
        text = text[cut:].strip()
    return [c for c in chunks if c]


# ============================================================
# API CALL
# ============================================================

def call_api(client: anthropic.Anthropic, chunk_text: str) -> str:
    """Send one chunk to Claude and return raw text response."""
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=EXTRACT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": chunk_text + GENERATION_RULES}],
    )
    return message.content[0].text.strip()


def parse_response(raw: str) -> list[dict]:
    """Parse Claude's JSON response into a list of task dicts."""
    text = raw.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        end = next(
            (i for i in range(len(lines) - 1, 0, -1) if lines[i].strip() == "```"),
            len(lines),
        )
        text = "\n".join(lines[1:end])
    # Extract JSON array (handles leading/trailing prose)
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


# ============================================================
# TASK CONVERSION AND VALIDATION
# ============================================================

VALID_RISK_LEVELS = {"Low-1", "Low-2", "Low-3", "Medium-4", "High-6", "High-9"}

def _normalise_risk(value: str) -> str:
    """Return a valid risk level string, defaulting to Medium-4."""
    if value in VALID_RISK_LEVELS:
        return value
    # Try to match e.g. "High" → "High-6", "Low" → "Low-2", "Medium" → "Medium-4"
    v = str(value).strip()
    if v.lower().startswith("high"):
        return "High-6"
    if v.lower().startswith("low"):
        return "Low-2"
    return "Medium-4"


def dict_to_taskblock(d: dict) -> TaskBlock | None:
    """Convert extracted task dict to TaskBlock. Returns None on bad data."""
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

    # WAH safety net: if wah_applicable but controls[0] isn't the exact sentence,
    # inject it. This catches cases where Claude paraphrased rather than copied.
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
        version="ref-1.0",
    )


# ============================================================
# DB HELPERS
# ============================================================

def _existing_names(conn: sqlite3.Connection) -> set[str]:
    """Return set of lower-cased task_names already in the DB."""
    rows = conn.execute("SELECT task_name FROM Tasks").fetchall()
    return {r[0].lower() for r in rows}


def save_ref_task(conn: sqlite3.Connection, task: TaskBlock) -> int:
    """Insert task as an unapproved draft. Returns new task_id."""
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO Tasks (
            task_name, scope, version, status,
            risk_pre, risk_post, ccvs_code,
            wah_applicable, source, approved, approved_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            task.task, task.scope, task.version, "draft",
            task.risk_pre, task.risk_post, remap_code(task.ccvs_code),
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
    total_passed = 0
    total_saved = 0
    total_failures = 0

    failure_lines: list[str] = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        existing = _existing_names(conn)

        for filename in PRIORITY_FILES:
            pdf_path = os.path.join(REFS_DIR, filename)
            if not os.path.exists(pdf_path):
                print(f"  [SKIP] {filename} — file not found")
                continue

            print(f"\nProcessing: {filename}")
            total_pdfs += 1

            # Extract and chunk
            try:
                full_text = extract_pdf_text(pdf_path)
            except Exception as exc:
                print(f"  [ERROR] PDF extraction failed: {exc}")
                failure_lines.append(f"{filename} | PDF extraction error: {exc}")
                continue

            chunks = split_into_chunks(full_text, CHUNK_SIZE)
            chunks = chunks[:MAX_CHUNKS]
            print(f"  Text chunks: {len(chunks)} (of {len(split_into_chunks(full_text, CHUNK_SIZE))} total, capped at {MAX_CHUNKS})")

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
                        failure_lines.append(
                            f"{filename} | Skipped: missing task_name in {task_dict}"
                        )
                        continue

                    # Duplicate check
                    if task_block.task.lower() in existing:
                        continue

                    # Validate
                    result = validate_task(task_block)
                    if not result.passed:
                        total_failures += 1
                        err_summary = "; ".join(result.errors[:3])
                        failure_lines.append(
                            f"{filename} | FAILED: '{task_block.task}' | {err_summary}"
                        )
                        continue

                    total_passed += 1

                    # Save
                    try:
                        save_ref_task(conn, task_block)
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

    # Write failures log
    if failure_lines:
        with open(FAILURES_PATH, "w", encoding="utf-8") as f:
            f.write(f"# Reference seed failures — {timestamp}\n\n")
            for line in failure_lines:
                f.write(line + "\n")

    print(f"\n{'='*50}")
    print(f"PDFs processed:              {total_pdfs}")
    print(f"Tasks extracted:             {total_extracted}")
    print(f"Tasks passing validation:    {total_passed}")
    print(f"Tasks saved to DB:           {total_saved}")
    print(f"Failures logged:             {total_failures}")
    if total_failures:
        print(f"Failures file:               {FAILURES_PATH}")


if __name__ == "__main__":
    main()

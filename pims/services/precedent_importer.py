"""pims/services/precedent_importer.py

Walks a folder of historical RPD audit reports and imports each actionable
finding (NCR / Conditional / Flagged / Action) into pims_precedent_examples.

Detection model
---------------
Each item in an RPD Audit Report .docx is two adjacent tables:
  1. A 2x2 "section header" table whose:
     - row 0 cells contain the section path (e.g. "Site Inspection / <section>")
     - row 1 col 0 holds the audit question
     - row 1 col 1 holds the status keyword (Compliant / Non-Compliant / Conditional / Flagged / Action)
  2. The next non-empty table — typically 2x6 — whose [0,*] cells are the
     merged narrative body (observation + "There is a legal requirement to:" /
     "Recommendations:" / non-compliance refs). Row [1] holds photo labels.

Idempotent UPSERT on (source_kind, source_file, source_item_key) using
Supabase REST `Prefer: resolution=merge-duplicates`.

CLI
---
    python -m pims.services.precedent_importer --source "<folder>" [--dry-run] [--limit N]

Env
---
    RPD_SUPABASE_URL          (required unless --dry-run)
    RPD_SUPABASE_SERVICE_KEY  (required unless --dry-run)
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx
from docx import Document

log = logging.getLogger(__name__)


# ---- Status normalisation ----

_STATUS_MAP = {
    "non-compliant": "NCR",
    "non compliant": "NCR",
    "noncompliant":  "NCR",
    "ncr":           "NCR",
    "conditional":   "Conditional",
    "flagged":       "Flagged",
    "action":        "Action",
    "action required": "Action",
}

_ACTIONABLE = {"NCR", "Conditional", "Flagged", "Action"}


def normalize_status(raw: str) -> Optional[str]:
    if not raw:
        return None
    key = raw.strip().lower()
    if key in _STATUS_MAP:
        return _STATUS_MAP[key]
    # tolerate trailing punctuation or extra words
    for k, v in _STATUS_MAP.items():
        if key.startswith(k):
            return v
    return None


# ---- Narrative split ----

# Lead-paragraph terminators that begin the recommendation/legal block.
_REC_SPLIT = re.compile(
    r"(There is a legal requirement to[:\s]|Recommendations?[:\s]|Non[- ]?compliance[:\s])",
    re.IGNORECASE,
)


def split_finding_recommendation(body: str) -> tuple[Optional[str], Optional[str]]:
    """Split body narrative into (finding_text, recommendation_text).

    Returns (None, None) if no clean split point is detected — caller should
    then store full body as observation_text only.
    """
    if not body:
        return None, None
    m = _REC_SPLIT.search(body)
    if not m:
        return None, None
    head = body[: m.start()].strip(" \t\r\n|·-")
    tail = body[m.start():].strip()
    if not head or not tail:
        return None, None
    return head, tail


# ---- Normalised retrieval key ----

# Strip site-specific tokens before computing the retrieval key:
#  - apartment / unit refs ("Apt 3", "1B", "Unit 12")
#  - directional refs ("north", "east balcony", "level 4")
#  - bare numbers + suffix letters
_SITE_NOISE = re.compile(
    r"\b("
    r"apt\s*\d+[a-z]?|"
    r"unit\s*\d+[a-z]?|"
    r"apartment\s*\d+[a-z]?|"
    r"level\s*\d+|"
    r"l\d+|"
    r"north|south|east|west|"
    r"balcony|balconies"
    r")\b",
    re.IGNORECASE,
)
_NUM_SUFFIX = re.compile(r"\b\d{1,4}[A-Za-z]?\b")
_WS = re.compile(r"\s+")


def normalize_key(text: str) -> str:
    if not text:
        return ""
    t = text.lower()
    t = _SITE_NOISE.sub(" ", t)
    t = _NUM_SUFFIX.sub(" ", t)
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = _WS.sub(" ", t).strip()
    return t


# ---- Section parsing ----

_SECTION_PREFIX_RE = re.compile(r"^\s*Site\s+Inspection\s*/\s*", re.IGNORECASE)


def parse_section_name(header_cell: str) -> str:
    if not header_cell:
        return ""
    return _SECTION_PREFIX_RE.sub("", header_cell.strip()).strip()


# ---- DOCX walking ----

@dataclass
class ImportItem:
    source_kind: str
    source_file: str
    source_item_key: str
    source_hash: str
    finding_text: Optional[str]
    recommendation_text: Optional[str]
    observation_text: Optional[str]
    normalized_key: Optional[str]
    section_name: Optional[str]
    status_normalized: Optional[str]


def _cell_text(cell) -> str:
    return (cell.text or "").strip()


def _is_section_header_table(t) -> Optional[tuple[str, str, str]]:
    """If table is a 2x2 section/question/status table, return
    (section, question, status_raw); else None.
    """
    rows = t.rows
    if len(rows) != 2 or len(rows[0].cells) != 2 or len(rows[1].cells) != 2:
        return None
    h0 = _cell_text(rows[0].cells[0])
    h1 = _cell_text(rows[0].cells[1])
    if not h0 or h0 != h1:
        return None
    if not _SECTION_PREFIX_RE.search(h0):
        return None
    q = _cell_text(rows[1].cells[0])
    s = _cell_text(rows[1].cells[1])
    if not q or not s:
        return None
    return (h0, q, s)


def _next_body_table(tables, start_idx: int) -> Optional[object]:
    """Return the next table after start_idx whose [0,0] cell is non-empty,
    excluding the next 2x2 header table."""
    for j in range(start_idx + 1, len(tables)):
        t = tables[j]
        # if we hit another section-header table, give up
        if _is_section_header_table(t):
            return None
        if not t.rows or not t.rows[0].cells:
            continue
        c00 = _cell_text(t.rows[0].cells[0])
        if c00:
            return t
    return None


def _extract_body_text(body_table) -> str:
    """Body table is typically 2x6. Row 0 cells [0..5] are the merged narrative
    (all identical). Row 1 holds photo labels — skip. Take cell [0,0] only."""
    if not body_table.rows:
        return ""
    return _cell_text(body_table.rows[0].cells[0])


def parse_report(path: Path) -> list[ImportItem]:
    fname = path.name
    try:
        doc = Document(str(path))
    except Exception as e:
        log.warning(f"Failed to open {fname}: {e}")
        return []

    items: list[ImportItem] = []
    tables = doc.tables
    item_index = 0
    i = 0
    while i < len(tables):
        header = _is_section_header_table(tables[i])
        if not header:
            i += 1
            continue
        section_raw, question, status_raw = header
        body_t = _next_body_table(tables, i)
        body_text = _extract_body_text(body_t) if body_t is not None else ""

        item_index += 1
        status_norm = normalize_status(status_raw)
        i += 1
        if status_norm not in _ACTIONABLE:
            continue

        # Combine question + body_text — body_text already contains the bulk
        # of the narrative; keep question as observation_text fallback.
        full_body = body_text.strip() or question.strip()
        finding, recommendation = split_finding_recommendation(full_body)

        section_name = parse_section_name(section_raw)
        norm = normalize_key((finding or full_body) + " " + section_name)

        item_key_seed = f"{fname}|{item_index}|{question}"
        item_key = hashlib.sha1(item_key_seed.encode("utf-8")).hexdigest()
        body_hash = hashlib.sha256(norm.encode("utf-8")).hexdigest() if norm else None

        items.append(ImportItem(
            source_kind="rpd_audit_report",
            source_file=fname,
            source_item_key=item_key,
            source_hash=body_hash or "",
            finding_text=finding,
            recommendation_text=recommendation,
            observation_text=full_body,
            normalized_key=norm or None,
            section_name=section_name or None,
            status_normalized=status_norm,
        ))
    return items


def discover_files(folder: Path) -> list[Path]:
    out = []
    for p in sorted(folder.glob("*.docx")):
        n = p.name
        if n.startswith("Robertsons"):
            continue
        if not n.startswith("RPD Audit Report -"):
            continue
        if n.startswith("~$"):
            continue
        out.append(p)
    return out


# ---- Upsert ----

def upsert_batch(supabase_url: str, service_key: str, items: list[ImportItem]) -> dict:
    """Idempotent upsert. Returns {inserted, total} (Supabase doesn't tell us
    new vs merged; total reflects rows posted)."""
    if not items:
        return {"posted": 0}
    headers = {
        "apikey":       service_key,
        "Content-Type": "application/json",
        "Prefer":       "resolution=merge-duplicates,return=minimal",
    }
    payload = []
    for it in items:
        payload.append({
            "source_kind":         it.source_kind,
            "source_file":         it.source_file,
            "source_item_key":     it.source_item_key,
            "source_hash":         it.source_hash or None,
            "finding_text":        it.finding_text,
            "recommendation_text": it.recommendation_text,
            "observation_text":    it.observation_text,
            "normalized_key":      it.normalized_key,
            "section_name":        it.section_name,
            "status_normalized":   it.status_normalized,
        })
    with httpx.Client(timeout=60) as c:
        r = c.post(
            f"{supabase_url}/rest/v1/pims_precedent_examples",
            headers=headers,
            params={"on_conflict": "source_kind,source_file,source_item_key"},
            json=payload,
        )
        if r.status_code not in (200, 201, 204):
            log.error(f"Upsert failed {r.status_code}: {r.text[:500]}")
            r.raise_for_status()
    return {"posted": len(payload)}


# ---- CLI ----

def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, help="Folder containing RPD Audit Report - *.docx")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int, default=0, help="Max files to process (0 = all)")
    args = p.parse_args(argv)

    folder = Path(args.source)
    if not folder.is_dir():
        print(f"Source folder not found: {folder}", file=sys.stderr)
        return 2

    files = discover_files(folder)
    if args.limit:
        files = files[: args.limit]
    print(f"Discovered {len(files)} RPD Audit Report files")

    all_items: list[ImportItem] = []
    items_per_file: dict[str, int] = {}
    total_items = 0
    for f in files:
        items = parse_report(f)
        items_per_file[f.name] = len(items)
        total_items += len(items)
        all_items.extend(items)
        print(f"  {f.name}: {len(items)} actionable items")

    print(f"Total actionable items: {len(all_items)}")

    if args.dry_run:
        print("Dry-run; not posting.")
        # show a couple
        for it in all_items[:3]:
            print("---")
            print(f"  status={it.status_normalized}  section={it.section_name}")
            print(f"  finding[:200]={(it.finding_text or '')[:200]!r}")
            print(f"  recommendation[:200]={(it.recommendation_text or '')[:200]!r}")
        return 0

    url = os.getenv("RPD_SUPABASE_URL", "")
    key = os.getenv("RPD_SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        print("RPD_SUPABASE_URL / RPD_SUPABASE_SERVICE_KEY not set", file=sys.stderr)
        return 3

    # Batch upsert in chunks to keep request size sensible.
    BATCH = 200
    posted = 0
    for i in range(0, len(all_items), BATCH):
        chunk = all_items[i:i + BATCH]
        upsert_batch(url, key, chunk)
        posted += len(chunk)
    print(f"Upserted {posted} rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

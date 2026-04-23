"""Audit report DOCX builder for PIMS /rpd.

Builds a two-part audit report per site:
    Part A: site summary + Open Actions Register
    Part B: full checklist (finding+photo for matches, reframed statement otherwise)

Checklist is loaded from an xlsx with two sheets, picked by project_value:
    project_value >= 250000  ->  ">$250K_inspection_checklist"
    project_value <  250000  ->  "<$250K_inspection_checklist"
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from io import BytesIO
from pathlib import Path

import openpyxl
from docx import Document
from docx.enum.text import WD_BREAK
from docx.shared import Pt

from src.docx_style_standard import (
    add_body_cell,
    add_controls_cell,
    apply_document_font,
    format_header_cell,
    set_cell_shading,
    set_col_widths,
    set_table_borders,
)

log = logging.getLogger(__name__)

PIMS_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = PIMS_DIR / "audit_report_template.docx"
DATA_DIR = PIMS_DIR / "data"
REFRAME_CACHE_PATH = DATA_DIR / "reframe_cache.jsonl"

SHEET_HIGH = ">$250K_inspection_checklist"
SHEET_LOW = "<$250K_inspection_checklist"
VALUE_THRESHOLD = 250000

_LEADING_VERB_RE = re.compile(
    r"^\s*(check|verify|ensure|confirm|inspect|review)\b(?:\s+that\b)?\s*",
    re.IGNORECASE,
)

# Cheap finite-verb heuristic used to decide whether the deterministic
# reframer's output would still be imperative-ish when no leading verb was
# stripped. Tokens ending in -s/-ed/-ing or common finite verbs qualify.
_FINITE_VERB_HINT_RE = re.compile(
    r"\b(is|are|was|were|has|have|had|does|do|did|will|shall|should|must|may|can|"
    r"could|would|been|being|be|include|requires|contains|complies|meets|"
    r"\w+ed|\w+ing|\w+s)\b",
    re.IGNORECASE,
)

MATCH_RATIO_THRESHOLD = 0.75


@dataclass
class ChecklistRow:
    category: str
    criteria: str
    instruction: str
    ccvs_category: str = ""
    ccvs_code: str = ""
    observation_text_enriched: str = ""


@dataclass
class SiteData:
    address: str
    project_value: float | None
    summary_text: str = ""
    observations: list[dict] = field(default_factory=list)
    open_actions: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Checklist loading
# ---------------------------------------------------------------------------

def load_checklist(
    project_value: float | int | None,
    xlsx_path: str | os.PathLike | None = None,
) -> list[ChecklistRow]:
    """Load checklist rows from the sheet chosen by project_value.

    Raises FileNotFoundError if the xlsx is missing, KeyError if the expected
    sheet is missing, and ValueError if project_value is None.
    """
    if project_value is None:
        raise ValueError("project_value is required to select checklist sheet")
    path = Path(xlsx_path) if xlsx_path else PIMS_DIR / "audit_checklist.xlsx"
    if not path.exists():
        raise FileNotFoundError(f"Checklist workbook missing: {path}")

    sheet_name = SHEET_HIGH if float(project_value) >= VALUE_THRESHOLD else SHEET_LOW
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    if sheet_name not in wb.sheetnames:
        raise KeyError(f"Sheet {sheet_name!r} missing from {path}")
    ws = wb[sheet_name]

    rows_iter = ws.iter_rows(values_only=True)
    header = next(rows_iter, None)
    if not header:
        return []
    header_map = {
        (str(c).strip().lower() if c is not None else ""): idx
        for idx, c in enumerate(header)
    }

    def _get(row: tuple, key: str) -> str:
        idx = header_map.get(key.lower())
        if idx is None or idx >= len(row):
            return ""
        v = row[idx]
        return "" if v is None else str(v).strip()

    out: list[ChecklistRow] = []
    for row in rows_iter:
        if not row or all(c is None or str(c).strip() == "" for c in row):
            continue
        out.append(
            ChecklistRow(
                category=_get(row, "Category"),
                criteria=_get(row, "Criteria"),
                instruction=_get(row, "Instruction"),
                ccvs_category=_get(row, "ccvs_category"),
                ccvs_code=_get(row, "ccvs_code"),
                observation_text_enriched=_get(row, "observation_text_enriched"),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Observation → checklist matcher
# ---------------------------------------------------------------------------

def match_observation(
    observation: dict,
    checklist: list[ChecklistRow],
    ratio_threshold: float = MATCH_RATIO_THRESHOLD,
) -> tuple[ChecklistRow | None, float]:
    """Match an observation to a checklist row.

    Primary: ccvs_code equality (case-insensitive, non-empty).
    Fallback: difflib ratio >= threshold on "category+criteria" vs
              "ccvs_category+observation_text_enriched".
    """
    obs_code = (observation.get("ccvs_code") or "").strip().lower()
    if obs_code:
        for row in checklist:
            if row.ccvs_code and row.ccvs_code.strip().lower() == obs_code:
                return row, 1.0

    obs_blob = (
        (observation.get("ccvs_category") or "")
        + " "
        + (observation.get("observation_text_enriched") or observation.get("observation_text") or "")
    ).strip().lower()
    if not obs_blob:
        return None, 0.0

    best_row: ChecklistRow | None = None
    best_ratio = 0.0
    for row in checklist:
        row_blob = f"{row.category} {row.criteria}".strip().lower()
        if not row_blob:
            continue
        ratio = SequenceMatcher(None, row_blob, obs_blob).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_row = row

    if best_ratio >= ratio_threshold:
        return best_row, best_ratio
    return None, best_ratio


# ---------------------------------------------------------------------------
# Reframer
# ---------------------------------------------------------------------------

def _load_cache() -> dict[str, str]:
    if not REFRAME_CACHE_PATH.exists():
        return {}
    out: dict[str, str] = {}
    try:
        with REFRAME_CACHE_PATH.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if "input" in rec and "output" in rec:
                        out[rec["input"]] = rec["output"]
                except json.JSONDecodeError:
                    continue
    except OSError:
        return {}
    return out


def _append_cache(instruction: str, reframed: str) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with REFRAME_CACHE_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"input": instruction, "output": reframed}) + "\n")
    except OSError:
        log.warning("Failed to append reframe cache", exc_info=True)


def _deterministic_reframe(instruction: str) -> tuple[str, bool]:
    """Return (reframed, matched_leading_verb)."""
    text = (instruction or "").strip()
    if not text:
        return "", False
    m = _LEADING_VERB_RE.match(text)
    matched = bool(m)
    if matched:
        text = text[m.end():].strip()
    if text:
        text = text[0].upper() + text[1:]
    if text and text[-1] not in ".!?":
        text = text + "."
    return text, matched


def _needs_llm_fallback(instruction: str, matched_verb: bool) -> bool:
    if not instruction:
        return False
    if ";" in instruction:
        return True
    if len(instruction) > 200:
        return True
    if matched_verb:
        return False
    first_six = " ".join(instruction.split()[:6])
    if not _FINITE_VERB_HINT_RE.search(first_six):
        return True
    return False


def _haiku_reframe(instruction: str) -> str | None:
    """Reframe via Claude Haiku. Returns None on any failure."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic  # type: ignore
    except ImportError:
        return None
    try:
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": (
                    "Rewrite this site-inspection checklist instruction as a "
                    "positive declarative statement of the compliant state, in "
                    "one sentence ending with a period. Do not add extra "
                    "commentary.\n\nInstruction: " + instruction
                ),
            }],
        )
        txt = "".join(
            blk.text for blk in msg.content if getattr(blk, "type", "") == "text"
        ).strip()
        if not txt:
            return None
        if txt[-1] not in ".!?":
            txt += "."
        return txt
    except Exception:
        log.warning("Haiku reframe failed", exc_info=True)
        return None


def reframe_instruction(instruction: str) -> str:
    """Reframe an imperative checklist instruction as a declarative statement.

    Strips leading Check/Verify/Ensure/Confirm/Inspect/Review (+ optional
    that), re-capitalises the first letter, and adds a trailing period.
    Falls back to Claude Haiku when the deterministic strip produced no
    leading-verb match AND the first 6 tokens lack a finite verb, or the
    instruction contains a ';' or exceeds 200 chars. Cached to
    pims/data/reframe_cache.jsonl.
    """
    if not instruction or not instruction.strip():
        return ""
    key = instruction.strip()
    cache = _load_cache()
    if key in cache:
        return cache[key]

    deterministic, matched = _deterministic_reframe(key)
    if _needs_llm_fallback(key, matched):
        haiku = _haiku_reframe(key)
        if haiku:
            _append_cache(key, haiku)
            return haiku
    _append_cache(key, deterministic)
    return deterministic


# ---------------------------------------------------------------------------
# DOCX build
# ---------------------------------------------------------------------------

def _page_break(doc: Document) -> None:
    p = doc.add_paragraph()
    p.add_run().add_break(WD_BREAK.PAGE)


def _h(doc: Document, text: str, size: int = 14) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(size)


def _p(doc: Document, text: str, size: int = 10) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(size)


def _open_actions_table(doc: Document, actions: list[dict]) -> None:
    headers = ["#", "Observation", "Action", "Responsible", "Due"]
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for i, h in enumerate(headers):
        format_header_cell(table.rows[0].cells[i], h)
    for a in actions:
        row = table.add_row()
        add_body_cell(row.cells[0], str(a.get("seq_no", "")))
        add_body_cell(row.cells[1], str(a.get("observation_text", "")))
        add_body_cell(row.cells[2], str(a.get("action_description", "")))
        add_body_cell(row.cells[3], str(a.get("responsible", "")))
        add_body_cell(row.cells[4], str(a.get("due_category", "")))
    set_col_widths(table, [1.2, 6.0, 5.0, 2.5, 1.8])
    set_table_borders(table)


def _checklist_row_block(
    doc: Document,
    row: ChecklistRow,
    matched_obs: dict | None,
) -> None:
    t = doc.add_table(rows=2, cols=2)
    t.style = "Table Grid"
    format_header_cell(t.rows[0].cells[0], row.category or "Checklist Item")
    format_header_cell(t.rows[0].cells[1], "Result")
    add_body_cell(t.rows[1].cells[0], row.criteria or "")
    if matched_obs is not None:
        finding = (
            matched_obs.get("observation_text_enriched")
            or matched_obs.get("observation_text")
            or ""
        )
        status = matched_obs.get("conformance_status") or ""
        photo = matched_obs.get("photo_url") or ""
        txt = f"[{status}] {finding}"
        if photo:
            txt += f"\nPhoto: {photo}"
        add_controls_cell(t.rows[1].cells[1], txt)
        if status.upper() == "NCR":
            set_cell_shading(t.rows[1].cells[1], "F8D7DA")
    else:
        add_controls_cell(t.rows[1].cells[1], reframe_instruction(row.instruction))
    set_col_widths(t, [7.0, 9.5])
    set_table_borders(t)


def _append_site(
    doc: Document,
    site: SiteData,
    checklist: list[ChecklistRow],
    is_first: bool,
) -> None:
    if not is_first:
        _page_break(doc)

    # Part A
    _h(doc, f"Audit Report — {site.address}", size=16)
    _p(doc, f"Project value: ${site.project_value:,.0f}" if site.project_value else "")
    if site.summary_text:
        _p(doc, site.summary_text)
    _h(doc, "Part A — Open Actions Register", size=13)
    if site.open_actions:
        _open_actions_table(doc, site.open_actions)
    else:
        _p(doc, "No open actions.")

    # Part B
    _page_break(doc)
    _h(doc, "Part B — Site Safety Inspection Checklist", size=13)
    for row in checklist:
        matched_obs: dict | None = None
        for obs in site.observations:
            cand, _ = match_observation(obs, [row])
            if cand is row:
                matched_obs = obs
                break
        _checklist_row_block(doc, row, matched_obs)


def build_audit_report_docx(
    sites_data: list[SiteData | dict],
    checklist_xlsx_path: str | os.PathLike | None = None,
    template_path: str | os.PathLike | None = None,
) -> BytesIO:
    """Build the audit report .docx across one or more sites.

    Raises FileNotFoundError if the template or checklist xlsx is missing,
    and ValueError if any site has a null project_value.
    """
    tpath = Path(template_path) if template_path else TEMPLATE_PATH
    if not tpath.exists():
        raise FileNotFoundError(f"Audit report template missing: {tpath}")

    sites: list[SiteData] = []
    for s in sites_data:
        if isinstance(s, dict):
            s = SiteData(
                address=s.get("address", ""),
                project_value=s.get("project_value"),
                summary_text=s.get("summary_text", ""),
                observations=s.get("observations", []) or [],
                open_actions=s.get("open_actions", []) or [],
            )
        if s.project_value is None:
            raise ValueError(f"Site {s.address!r} has null project_value")
        sites.append(s)

    doc = Document(str(tpath))
    apply_document_font(doc)

    for i, site in enumerate(sites):
        checklist = load_checklist(site.project_value, checklist_xlsx_path)
        _append_site(doc, site, checklist, is_first=(i == 0))

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

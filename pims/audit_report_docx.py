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
from docx.enum.table import WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_BREAK
from docx.shared import Cm, Pt, RGBColor

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
    client: str = ""
    prepared_by: str = ""
    inspection_datetime: str = ""
    audit_ref: str = ""
    # Pre-fetched open-action photo bytes, keyed by observation id.
    # Populated by the route before calling build_audit_report_docx.
    open_action_photo_bytes_by_obs_id: dict[str, bytes] = field(default_factory=dict)
    # Photo bytes for any observation (matched-checklist embeds), keyed by observation id.
    obs_photo_bytes_by_obs_id: dict[str, bytes] = field(default_factory=dict)


# Bold status palette for shaded cells — keyed by conformance_status.
# (bg_hex, font_hex). Hex without leading '#'.
STATUS_PALETTE: dict[str, tuple[str, str]] = {
    "Compliant":   ("00B050", "FFFFFF"),
    "Conditional": ("FFC000", "000000"),
    "NCR":         ("C00000", "FFFFFF"),
    "Info":        ("5B9BD5", "FFFFFF"),
}


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
# Cover-page population (Phase 0)
# ---------------------------------------------------------------------------

# Literal paragraph prefixes of example/boilerplate content in the shipped
# template. Matched exactly (startswith) so that future legitimate content a
# template editor adds is not accidentally deleted.
_EXAMPLE_PARAGRAPH_PREFIXES = (
    "Example….An inspection of the Robertson",  # para 9
    "Example 26 / 35",  # para 13
    "Example below",  # para 20
    "Powered mobile plant introduced without RPD verification",  # para 21
    "Workers removing tiles/render were not initially wearing P2",  # para 22
    "Silica controls for tile/bed removal non-compliant",  # para 23
    "Required RCS danger signage not displayed",  # para 24
    "Electrical equipment lacked supporting inspection",  # para 25
)

_COVER_TITLE_SUFFIX = "Site Safety Audit Report"

_MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def _format_audit_date(raw: str) -> str:
    """Format an ISO-ish date/datetime string as 'D Month YYYY' (e.g.
    '30 April 2026'). Returns '—' if parsing fails or input is empty."""
    if not raw:
        return "—"
    s = str(raw).strip()
    # Accept 'YYYY-MM-DD', 'YYYY-MM-DDTHH:MM:SS', 'YYYY-MM-DD HH:MM:SS'.
    head = s.split("T", 1)[0].split(" ", 1)[0]
    parts = head.split("-")
    if len(parts) != 3:
        return s
    try:
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
        if not (1 <= month <= 12):
            return s
        return f"{day} {_MONTH_NAMES[month - 1]} {year}"
    except (TypeError, ValueError):
        return s


def _score_totals(sites: list["SiteData"]) -> dict:
    total_items = 0
    passed = 0
    ncr = 0
    conditional = 0
    actions = 0
    for s in sites:
        for obs in s.observations:
            total_items += 1
            status = (obs.get("conformance_status") or "").strip()
            if status == "Compliant":
                passed += 1
            elif status == "NCR":
                ncr += 1
            elif status == "Conditional":
                conditional += 1
        actions += len(s.open_actions)
    flagged = total_items - passed
    # D4: integer percent matches the reference docx convention
    # (e.g. "47 / 48 (98%)"), not "47 / 48 (97.92%)".
    pct = int(round(100 * passed / total_items)) if total_items else 0
    return {
        "total": total_items,
        "passed": passed,
        "flagged": flagged,
        "ncr": ncr,
        "conditional": conditional,
        "actions": actions,
        "pct": pct,
        "score_text": f"{passed} / {total_items} ({pct}%)",
    }


def _strip_company_suffix(name: str) -> str:
    """D1: Strip trailing company-form suffixes from a client display
    name. The reference docx files render the contractor as
    "Robertson's Remedial and Painting", not "…Pty Ltd". Drop the
    suffix at the title path so cover/Part B render the trade name."""
    s = (name or "").strip()
    for suffix in (
        " Pty. Ltd.", " Pty Ltd.", " Pty. Ltd", " Pty Ltd",
        " Pty. Limited", " Pty Limited",
        " Pty.", " Pty",
        " Ltd.", " Ltd",
    ):
        if s.endswith(suffix):
            return s[: -len(suffix)].rstrip()
    return s


def _resolve_cover_title(sites: list["SiteData"]) -> str:
    if len(sites) == 1:
        client = _strip_company_suffix(sites[0].client or "")
        if not client:
            raise ValueError(
                "Single-site audit report requires a non-empty site.client "
                "(populate sites.client_name); refusing to render a generic title."
            )
        return f"{client} – {_COVER_TITLE_SUFFIX}"
    clients = {_strip_company_suffix(s.client or "") for s in sites}
    clients.discard("")
    if len(clients) == 1:
        return f"{next(iter(clients))} – {_COVER_TITLE_SUFFIX}"
    return _COVER_TITLE_SUFFIX


def _resolve_executive_summary(sites: list["SiteData"], totals: dict) -> str:
    if len(sites) > 1:
        return (
            f"This audit covers {len(sites)} sites. {totals['ncr']} "
            f"non-conformances and {totals['conditional']} conditional findings "
            f"were identified across {totals['total']} inspection items."
        )
    s = sites[0]
    if s.summary_text and s.summary_text.strip():
        return s.summary_text.strip()
    return (
        f"This Work Health and Safety audit was conducted on "
        f"{s.inspection_datetime} at {s.address}. The inspection covered "
        f"{totals['total']} checklist items, identifying {totals['ncr']} "
        f"non-conformances and {totals['conditional']} conditional findings. "
        f"{totals['actions']} actions remain open at the time of this report."
    )


def _clear_paragraph_runs(p) -> None:
    for r in list(p.runs):
        r._element.getparent().remove(r._element)


def _replace_paragraph_text(p, text: str) -> None:
    _clear_paragraph_runs(p)
    p.add_run(text)


def _replace_paragraph_with_lines(p, lines: list[str]) -> None:
    _clear_paragraph_runs(p)
    if not lines:
        p.add_run("None.")
        return
    p.add_run(lines[0])
    for line in lines[1:]:
        br_run = p.add_run()
        br_run.add_break()
        p.add_run(line)


def _set_cell_text_preserving_style(cell, text: str) -> None:
    # Prefer updating the first run of the first paragraph so font/size is
    # preserved. Clear any other paragraphs in the cell to keep it a single
    # value cell.
    if not cell.paragraphs:
        cell.text = text
        return
    first = cell.paragraphs[0]
    _clear_paragraph_runs(first)
    first.add_run(text)
    for extra in cell.paragraphs[1:]:
        extra._element.getparent().remove(extra._element)


def _replace_inline_placeholder(doc, placeholder: str, value: str) -> int:
    """Replace placeholder with value inline across body, table cells, and
    section footers/headers. Preserves surrounding text by collapsing the
    paragraph's runs into a single run when the placeholder is split across
    runs. Returns count of replacements made."""
    count = 0

    def _walk_paragraphs(paragraphs):
        nonlocal count
        for p in paragraphs:
            if placeholder not in p.text:
                continue
            new_text = p.text.replace(placeholder, value)
            _clear_paragraph_runs(p)
            p.add_run(new_text)
            count += 1

    def _walk_tables(tables):
        for table in tables:
            for row in table.rows:
                for cell in row.cells:
                    _walk_paragraphs(cell.paragraphs)
                    _walk_tables(cell.tables)

    _walk_paragraphs(doc.paragraphs)
    _walk_tables(doc.tables)
    for section in doc.sections:
        for hf in (section.header, section.footer,
                   section.first_page_header, section.first_page_footer,
                   section.even_page_header, section.even_page_footer):
            try:
                _walk_paragraphs(hf.paragraphs)
                _walk_tables(hf.tables)
            except Exception:
                continue
    return count


def _find_paragraph_by_prefix(doc, prefix: str):
    for p in doc.paragraphs:
        if p.text.startswith(prefix):
            return p
    return None


def _delete_paragraph(p) -> None:
    p._element.getparent().remove(p._element)


def _populate_cover(doc, sites: list["SiteData"]) -> None:
    """Replace cover-page placeholders with computed content from site metadata.

    Missing placeholders (e.g. when called against a blank template in tests)
    are logged at WARNING and skipped — never raised. Runs pre-loop so the
    rest of the render pipeline is unaffected.
    """
    totals = _score_totals(sites)
    title = _resolve_cover_title(sites)
    exec_summary = _resolve_executive_summary(sites, totals)

    if len(sites) == 1:
        site_conducted = sites[0].address
    else:
        site_conducted = f"Multiple sites ({len(sites)})"

    # Use report-level fields from the first site for prepared_by and
    # inspection_datetime. Multi-site reports assume a single audit event.
    prepared_by = sites[0].prepared_by or ""
    inspection_datetime = sites[0].inspection_datetime or ""

    # --- Paragraph placeholders ---------------------------------------
    # Title: paragraph contains the literal suffix "Site Safety Audit Report".
    title_p = None
    for p in doc.paragraphs:
        if _COVER_TITLE_SUFFIX in p.text:
            title_p = p
            break
    if title_p is not None:
        _replace_paragraph_text(title_p, title)
    else:
        log.warning("Cover title paragraph not found")

    audit_date_formatted = _format_audit_date(inspection_datetime)

    paragraph_replacements = {
        "[Insert Site Address]": site_conducted,
        "[Insert Executive Summary]": exec_summary,
        "[Insert Score]": totals["score_text"],
    }

    # Inline substitution for "[Insert Current Date]" — preserves any
    # surrounding text such as the "Date: " footer prefix. Walks body
    # paragraphs, every cell paragraph, and every section footer paragraph.
    _replace_inline_placeholder(
        doc, "[Insert Current Date]", audit_date_formatted,
    )
    for placeholder, value in paragraph_replacements.items():
        p = _find_paragraph_by_prefix(doc, placeholder)
        if p is None:
            log.warning("Cover placeholder %r not found", placeholder)
            continue
        _replace_paragraph_text(p, value)

    # Open Actions Register + Findings — multi-line replacements.
    oa_placeholder = "[Insert line items from Open Actions Register"
    oa_p = _find_paragraph_by_prefix(doc, oa_placeholder)
    if oa_p is None:
        log.warning("Cover placeholder %r not found", oa_placeholder)
    else:
        oa_lines: list[str] = []
        for s in sites:
            for a in s.open_actions:
                desc = str(a.get("action_description") or a.get("observation_text") or "").strip()
                resp = str(a.get("responsible") or "").strip()
                due = str(a.get("due_category") or "").strip()
                bits = [b for b in (desc, resp, due) if b]
                if bits:
                    oa_lines.append("• " + " — ".join(bits))
        _replace_paragraph_with_lines(oa_p, oa_lines)

    f_placeholder = "[Insert Summary of Findings"
    f_p = _find_paragraph_by_prefix(doc, f_placeholder)
    if f_p is None:
        log.warning("Cover placeholder %r not found", f_placeholder)
    else:
        finding_lines: list[str] = []
        for s in sites:
            for obs in s.observations:
                status = (obs.get("conformance_status") or "").strip()
                if status in ("NCR", "Conditional"):
                    text = (
                        obs.get("observation_text_enriched")
                        or obs.get("observation_text")
                        or ""
                    ).strip()
                    if text:
                        finding_lines.append("• " + text)
        _replace_paragraph_with_lines(f_p, finding_lines)

    # --- Label/value tables -------------------------------------------
    # D5: KPI labels match the reference docx convention
    # ("Flagged observations" / "Open actions", not "Flagged items" /
    # "Actions"). We accept BOTH spellings on lookup so the renderer is
    # tolerant of templates that haven't been re-cleaned.
    # D2: "Date of inspection" cell takes the human-readable
    # `_format_audit_date(inspection_datetime)`, not the raw ISO string.
    inspection_date_display = _format_audit_date(inspection_datetime)
    # Table 1 uses a single row with alternating label/value cells.
    label_values_single_row = {
        "Score": totals["score_text"],
        "Flagged observations": f"{totals['flagged']}",
        "Flagged items": f"{totals['flagged']}",  # tolerant fallback
        "Open actions": f"{totals['actions']}",
        "Actions": f"{totals['actions']}",  # tolerant fallback
    }
    # Tables 2/5/7/9 use a two-cell label/value row.
    label_values_label_pair = {
        "Site conducted": site_conducted,
        "Prepared by": prepared_by,
        "Date of inspection": inspection_date_display,
        "Flagged observations (row)": f"{totals['flagged']} flagged",
        "Flagged items (row)": f"{totals['flagged']} flagged",
    }
    # Table 9's label cell literal text is also "Flagged items" — to
    # disambiguate from Table 1, we detect by table shape (single row &
    # >= 4 cells vs single row & 2 cells).

    seen_labels: set[str] = set()
    for table in doc.tables:
        if not table.rows:
            continue
        row = table.rows[0]
        cells = row.cells
        n = len(cells)
        # Single-row, alternating label/value (Table 1 shape).
        if len(table.rows) == 1 and n >= 4 and n % 2 == 0:
            matched_any = False
            for i in range(0, n, 2):
                label = cells[i].text.strip()
                if label in label_values_single_row:
                    _set_cell_text_preserving_style(
                        cells[i + 1], label_values_single_row[label]
                    )
                    seen_labels.add(label)
                    matched_any = True
            if matched_any:
                continue
        # Two-cell label/value row.
        if n >= 2:
            label = cells[0].text.strip()
            # Disambiguate "Flagged items"/"Flagged observations" between
            # Table 1 (single-row alternating, n>=4) and Table 9 (2-cell).
            target_key = label
            if label == "Flagged items" and len(table.rows) == 1 and n == 2:
                target_key = "Flagged items (row)"
            elif label == "Flagged observations" and len(table.rows) == 1 and n == 2:
                target_key = "Flagged observations (row)"
            if target_key in label_values_label_pair:
                _set_cell_text_preserving_style(
                    cells[1], label_values_label_pair[target_key]
                )
                seen_labels.add(target_key)

    for lbl in list(label_values_single_row) + list(label_values_label_pair):
        if lbl not in seen_labels:
            log.warning("Cover label cell %r not found", lbl)

    # --- Delete hard-coded example paragraphs -------------------------
    for prefix in _EXAMPLE_PARAGRAPH_PREFIXES:
        p = _find_paragraph_by_prefix(doc, prefix)
        if p is None:
            log.warning("Cover example paragraph with prefix %r not found", prefix)
            continue
        _delete_paragraph(p)

    # --- Delete stray "Photo N" scaffold tables --------------------
    # The shipped template contains single-row "Photo N" placeholder
    # tables that are designer layout scaffolds — unpopulated in the
    # live render and visually bleed artwork between the summary and
    # Part A. Drop any table whose first cell starts with "Photo ".
    # (The rendered checklist blocks from _checklist_row_block do not
    # have "Photo " as their first cell, so they are not affected.)
    removed_scaffold = 0
    for table in list(doc.tables):
        if not table.rows:
            continue
        first_cell_text = table.rows[0].cells[0].text.strip()
        if first_cell_text.lower().startswith("photo "):
            tbl = table._element
            parent = tbl.getparent()
            if parent is not None:
                parent.remove(tbl)
                removed_scaffold += 1
    if removed_scaffold == 0:
        log.warning("No scaffold 'Photo N' table found on cover to remove")

    # --- Delete stray "Photo N" scaffold paragraphs --------------------
    # Template paragraphs of the form "Photo 45", "Photo 46", … are layout
    # scaffolds that bleed into the body when the renderer appends sites.
    # Strip them anywhere in the doc; rendered photo captions use a leading
    # italic small font and live inside table cells, so they are not affected.
    _photo_label_re = re.compile(r"^\s*Photo\s+\d+\s*$", re.IGNORECASE)
    for p in list(doc.paragraphs):
        if _photo_label_re.match(p.text or ""):
            _delete_paragraph(p)


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


def _apply_status_cell(cell, status: str) -> None:
    """Shade a cell with the bold status palette and force the font colour
    on every run currently in the cell. Statuses outside the palette leave
    the cell untouched (no shading, default font)."""
    entry = STATUS_PALETTE.get((status or "").strip())
    if entry is None:
        return
    bg_hex, font_hex = entry
    set_cell_shading(cell, bg_hex)
    rgb = RGBColor.from_string(font_hex)
    for p in cell.paragraphs:
        for run in p.runs:
            run.font.color.rgb = rgb


def _embed_photo(
    cell,
    photo_bytes: bytes | None,
    fallback_text: str,
    caption: str | None = None,
) -> None:
    """Embed photo_bytes into cell as an inline image, or write fallback_text
    if bytes are absent or PIL/embed fails. Matches the thumbnail behaviour
    of the staging-review DOCX path in pims/routes.py.

    When caption is provided and the embed succeeds, the caption text is added
    as a small italic line under the image (e.g. "Photo 12")."""
    if not photo_bytes:
        add_body_cell(cell, fallback_text)
        return
    try:
        from io import BytesIO
        from PIL import Image as PILImage
        pil = PILImage.open(BytesIO(photo_bytes)).convert("RGB")
        pil.thumbnail((600, 600), PILImage.LANCZOS)
        buf = BytesIO()
        pil.save(buf, format="JPEG", quality=85)
        buf.seek(0)
        # Clear default paragraph text then embed.
        p = cell.paragraphs[0]
        for r in list(p.runs):
            r._element.getparent().remove(r._element)
        p.add_run().add_picture(buf, width=Cm(3.5))
        if caption:
            cap_p = cell.add_paragraph()
            cap_run = cap_p.add_run(caption)
            cap_run.italic = True
            cap_run.font.size = Pt(8)
    except Exception:
        log.warning("Photo embed failed; falling back to text", exc_info=True)
        add_body_cell(cell, fallback_text)


# Local mirror of pims.routes.CCVS_CATEGORY_BY_PREFIX so the renderer
# does not import from routes (which would create a cycle through
# FastAPI / Supabase config). Keep in sync if routes changes.
_CCVS_CATEGORY_BY_PREFIX_LOCAL: dict[str, str] = {
    "WAH": "Working at Height",
    "IRA": "Industrial Rope Access",
    "SIL": "Silica",
    "STR": "Structural",
    "MOB": "Mobile Plant",
    "CHM": "Chemicals",
    "ENE": "Energy",
    "SYS": "Systems",
}


def _render_findings_paragraphs(doc: Document, actions: list[dict]) -> None:
    """Reference-docx-shape findings renderer.

    Emits two paragraphs per finding to match
    pims/56-58_Fraters_Ave_Sans_Souci.docx and
    pims/7_Hampden_Rd_Cremorne.docx:

      <status> #<N>. <Category> – <Sub-category> – <observation_text>
      Required action: <action_description / recommendation>

    Photos are NOT embedded here — they live with the checklist
    matches in the Site Safety Inspection section, per the reference
    docx convention. Open Actions Register layout (the bordered
    7-column table) is intentionally retired in favour of this prose
    block.
    """
    if not actions:
        _p(doc, "No findings.")
        return
    for n, a in enumerate(actions, start=1):
        status = (a.get("conformance_status") or "").strip() or "Finding"
        category = (a.get("ccvs_category") or "").strip()
        if not category:
            code = (a.get("ccvs_code") or "").strip()
            prefix = code.split("-", 1)[0] if code else ""
            category = _CCVS_CATEGORY_BY_PREFIX_LOCAL.get(prefix, "Uncategorised")
        # Sub-category — use the ccvs_code (e.g. "ENE-M4") if no
        # explicit sub-category text is on the observation row.
        sub = (a.get("ccvs_subcategory") or "").strip()
        if not sub:
            sub = (a.get("ccvs_code") or "").strip() or "—"
        body = (
            (a.get("observation_text_enriched") or "").strip()
            or (a.get("observation_text") or "").strip()
        )
        head_line = f"{status} #{n}. {category} – {sub} – {body}"
        _p(doc, head_line)
        action_text = (
            (a.get("action_description") or "").strip()
            or (a.get("recommendation") or "").strip()
            or (a.get("observation_text_enriched") or "").strip()
        )
        if action_text:
            _p(doc, f"Required action: {action_text}")


def _open_actions_table(
    doc: Document,
    actions: list[dict],
    photo_bytes_by_obs_id: dict[str, bytes] | None = None,
    photo_counter: list[int] | None = None,
) -> None:
    photo_bytes_by_obs_id = photo_bytes_by_obs_id or {}
    headers = ["#", "Status", "Photo", "Action", "Responsible", "Due", "CCVS"]
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for i, h in enumerate(headers):
        format_header_cell(table.rows[0].cells[i], h)
    for a in actions:
        row = table.add_row()
        add_body_cell(row.cells[0], str(a.get("seq_no", "")))
        status = a.get("conformance_status") or ""
        add_body_cell(row.cells[1], status)
        _apply_status_cell(row.cells[1], status)
        obs_id = str(a.get("id") or "")
        photo_bytes = photo_bytes_by_obs_id.get(obs_id)
        caption = None
        if photo_bytes and photo_counter is not None:
            photo_counter[0] += 1
            caption = f"Photo {photo_counter[0]}"
        _embed_photo(row.cells[2], photo_bytes, "—", caption=caption)
        # Action falls back to the enriched observation when no action
        # description is recorded.
        action_text = (
            (a.get("action_description") or "").strip()
            or (a.get("observation_text_enriched") or "").strip()
            or (a.get("observation_text") or "").strip()
        )
        add_body_cell(row.cells[3], action_text)
        add_body_cell(row.cells[4], str(a.get("responsible", "")))
        add_body_cell(row.cells[5], str(a.get("due_category", "")))
        add_body_cell(row.cells[6], str(a.get("ccvs_code") or ""))
    set_col_widths(table, [0.8, 1.6, 3.5, 5.5, 2.2, 1.6, 1.3])
    set_table_borders(table)


def _append_photo_to_cell(
    cell, photo_bytes: bytes | None, caption: str | None = None,
) -> None:
    """Append an inline photo (and optional caption) as new paragraphs at the
    end of cell, preserving any existing text. No-op if bytes absent."""
    if not photo_bytes:
        return
    try:
        from io import BytesIO
        from PIL import Image as PILImage
        pil = PILImage.open(BytesIO(photo_bytes)).convert("RGB")
        pil.thumbnail((600, 600), PILImage.LANCZOS)
        buf = BytesIO()
        pil.save(buf, format="JPEG", quality=85)
        buf.seek(0)
        img_p = cell.add_paragraph()
        img_p.add_run().add_picture(buf, width=Cm(3.5))
        if caption:
            cap_p = cell.add_paragraph()
            cap_run = cap_p.add_run(caption)
            cap_run.italic = True
            cap_run.font.size = Pt(8)
    except Exception:
        log.warning("Inline photo embed failed", exc_info=True)


def _checklist_row_block(
    doc: Document,
    row: ChecklistRow,
    matched_obs: dict | None,
    photo_bytes_by_obs_id: dict[str, bytes] | None = None,
    photo_counter: list[int] | None = None,
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
        status = (matched_obs.get("conformance_status") or "").strip()
        # Status now lives in the cell shading — no "[STATUS] " prefix.
        result_cell = t.rows[1].cells[1]
        add_controls_cell(result_cell, finding)
        _apply_status_cell(result_cell, status)
        photo_bytes = None
        if photo_bytes_by_obs_id is not None:
            obs_id = str(matched_obs.get("id") or "")
            photo_bytes = photo_bytes_by_obs_id.get(obs_id)
        if photo_bytes and photo_counter is not None:
            photo_counter[0] += 1
            _append_photo_to_cell(
                result_cell, photo_bytes, f"Photo {photo_counter[0]}",
            )
    else:
        add_controls_cell(t.rows[1].cells[1], reframe_instruction(row.instruction))
    set_col_widths(t, [7.0, 9.5])
    set_table_borders(t)


def _italic_small(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.italic = True
    run.font.size = Pt(9)


def _part_c_banner(doc: Document, totals: dict) -> None:
    """Three-cell summary banner that opens Part C. Uses STATUS_PALETTE so
    severity reads at a glance; the counts themselves live authoritatively
    on the cover and in the Part B metadata table."""
    score_text = totals["score_text"]
    flagged = totals["flagged"]
    actions = totals["actions"]
    cells_spec = [
        (score_text, "Compliant"),
        (f"{flagged} flagged", "Conditional" if flagged > 0 else "Compliant"),
        (f"{actions} open", "NCR" if actions > 0 else "Compliant"),
    ]
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    for i, (text, status) in enumerate(cells_spec):
        cell = table.rows[0].cells[i]
        add_body_cell(cell, text)
        _apply_status_cell(cell, status)
        for p in cell.paragraphs:
            for run in p.runs:
                run.bold = True
    set_col_widths(table, [4.0, 4.0, 4.0])
    set_table_borders(table)


AUDITCO_LICENCE_PLACEHOLDER = "AC-NSW-XXXXXX"


def _part_d_signoff(doc: Document, site: SiteData) -> None:
    """Emit the Part D — Auditor Sign-off section for one site.

    Order: page break, heading, italic disclaimer combining the regulatory
    basis with the draft-status sentence, then a five-row signature table
    (Auditor name / Position / Auditor signature / Date signed / AuditCo
    licence). The signature and date-signed value rows use explicit
    3 cm and 1 cm heights respectively so re-pagination by Word does not
    collapse them.
    """
    _page_break(doc)
    _h(doc, "Part D — Auditor Sign-off", size=13)

    # D2: format the draft date as "D Month YYYY" (e.g. "30 April 2026"),
    # not the raw ISO/datetime string from the request body.
    draft_date_display = _format_audit_date(site.inspection_datetime)
    disclaimer = (
        "This report has been prepared in accordance with NSW WHS "
        "Regulation 2017 and SafeWork NSW codes of practice. Findings are "
        "based on conditions observed at the time of the audit. This "
        "document is a draft for review until signed by a competent "
        f"person; the draft date is {draft_date_display} and "
        f"the audit reference is {site.audit_ref or '—'}."
    )
    _italic_small(doc, disclaimer)

    # TODO: replace AUDITCO_LICENCE_PLACEHOLDER with the live AuditCo
    # licence number when it's captured upstream (per-auditor or per-org).
    rows_spec: list[tuple[str, str, float | None]] = [
        ("Auditor name",      site.prepared_by or "",         None),
        ("Position",          "",                             None),
        ("Auditor signature", "",                             3.0),
        ("Date signed",       "",                             1.0),
        ("AuditCo licence",   AUDITCO_LICENCE_PLACEHOLDER,    None),
    ]
    table = doc.add_table(rows=len(rows_spec), cols=2)
    table.style = "Table Grid"
    for i, (label, value, height_cm) in enumerate(rows_spec):
        format_header_cell(table.rows[i].cells[0], label)
        add_body_cell(table.rows[i].cells[1], value)
        if height_cm is not None:
            table.rows[i].height = Cm(height_cm)
            table.rows[i].height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
    set_col_widths(table, [4.0, 10.0])
    set_table_borders(table)


def _site_metadata_table(doc: Document, site: SiteData, totals: dict) -> None:
    """Two-column label/value table for Part B.

    The Compliant / Conditional / NCR count rows reuse the bold status
    palette (`_apply_status_cell`) so the severity reads at a glance.
    Rows intentionally duplicate 'Prepared by' and 'Date of inspection'
    from the cover — the cover is a one-page top-level summary; Part B
    restates per-site context at the start of each site section.
    """
    pv = (
        f"${site.project_value:,.0f}"
        if site.project_value is not None else "—"
    )
    rows: list[tuple[str, str, str | None]] = [
        ("Client",             site.client or "—",              None),
        ("Site address",       site.address or "—",             None),
        ("Date of inspection", site.inspection_datetime or "—", None),
        ("Prepared by",        site.prepared_by or "—",         None),
        ("Audit reference",    site.audit_ref or "—",           None),
        ("Project value",      pv,                              None),
        ("Total items",        str(totals["total"]),             None),
        ("Compliant",          str(totals["passed"]),            "Compliant"),
        ("Conditional",        str(totals["conditional"]),       "Conditional"),
        ("NCR",                str(totals["ncr"]),               "NCR"),
        ("Open actions",       str(totals["actions"]),           None),
    ]
    table = doc.add_table(rows=len(rows), cols=2)
    table.style = "Table Grid"
    for i, (label, value, status) in enumerate(rows):
        format_header_cell(table.rows[i].cells[0], label)
        add_body_cell(table.rows[i].cells[1], value)
        if status is not None:
            _apply_status_cell(table.rows[i].cells[1], status)
    set_col_widths(table, [3.5, 6.5])
    set_table_borders(table)


def _append_site(
    doc: Document,
    site: SiteData,
    checklist: list[ChecklistRow],
    is_first: bool,
) -> None:
    if not is_first:
        _page_break(doc)

    # Site title banner.
    # Per-site body heading is OMITTED for single-site reports to match
    # the reference docx layout (cover already shows address). Multi-site
    # reports keep an address heading at the start of each site's body.
    if is_first is False:
        _h(doc, site.address, size=16)

    # Shared photo counter — sequential "Photo N" captions across the
    # checklist row embeds within this site.
    photo_counter: list[int] = [0]

    # Findings section — paragraph format matching the reference docx
    # (no Part A header, no Open Actions Register table). Each NCR /
    # Conditional rendered as two paragraphs: heading + Required action.
    _h(doc, "Findings", size=13)
    _render_findings_paragraphs(doc, site.open_actions)

    # Site Safety Inspection section — the full checklist with photos
    # embedded only on matched rows. No Part C banner, no Part B
    # metadata duplication (cover carries the metadata already).
    _page_break(doc)
    _h(doc, "Site Safety Inspection", size=13)

    matches_by_row: list[tuple[ChecklistRow, list[dict]]] = []
    for row in checklist:
        row_matches: list[dict] = []
        for obs in site.observations:
            cand, _ = match_observation(obs, [row])
            if cand is row:
                row_matches.append(obs)
        matches_by_row.append((row, row_matches))

    has_duplicates = any(len(m) > 1 for _, m in matches_by_row)
    if has_duplicates:
        _p(
            doc,
            "Note: multiple observations are rendered against the same "
            "criterion where applicable.",
            size=9,
        )

    # Group rows by category, preserving xlsx order of first appearance.
    current_category: str | None = None
    category_group: list[tuple[ChecklistRow, list[dict]]] = []

    def _flush_category():
        nonlocal category_group
        if not category_group:
            return
        total_obs = sum(len(m) for _, m in category_group)
        compliant = sum(
            1
            for _, matches in category_group
            for obs in matches
            if (obs.get("conformance_status") or "").strip() == "Compliant"
        )
        if total_obs > 0:
            _italic_small(
                doc, f"Category score: {compliant}/{total_obs} compliant",
            )
        category_group = []

    for row, row_matches in matches_by_row:
        category = row.category or "Uncategorised"
        if category != current_category:
            _flush_category()
            current_category = category
            _h(doc, category, size=12)
        category_group.append((row, row_matches))

        if not row_matches:
            _checklist_row_block(doc, row, None)
            continue
        if len(row_matches) > 1:
            log.debug(
                "Rendering %d observations against checklist row %s / %s",
                len(row_matches), row.category, row.criteria,
            )
        for obs in row_matches:
            _checklist_row_block(
                doc,
                row,
                obs,
                photo_bytes_by_obs_id=site.obs_photo_bytes_by_obs_id,
                photo_counter=photo_counter,
            )

    _flush_category()

    # Part D (Auditor Sign-off) intentionally omitted to match the
    # reference docx layout. Re-enable with _part_d_signoff(doc, site)
    # if a signing block is required by a future customer.


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
                client=s.get("client", "") or "",
                prepared_by=s.get("prepared_by", "") or "",
                inspection_datetime=s.get("inspection_datetime", "") or "",
                audit_ref=s.get("audit_ref", "") or "",
                open_action_photo_bytes_by_obs_id=(
                    s.get("open_action_photo_bytes_by_obs_id") or {}
                ),
                obs_photo_bytes_by_obs_id=(
                    s.get("obs_photo_bytes_by_obs_id") or {}
                ),
            )
        if s.project_value is None:
            raise ValueError(f"Site {s.address!r} has null project_value")
        sites.append(s)

    doc = Document(str(tpath))
    apply_document_font(doc)
    _populate_cover(doc, sites)

    for i, site in enumerate(sites):
        checklist = load_checklist(site.project_value, checklist_xlsx_path)
        _append_site(doc, site, checklist, is_first=(i == 0))

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

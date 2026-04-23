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
    # Pre-fetched open-action photo bytes, keyed by observation id.
    # Populated by the route before calling build_audit_report_docx.
    open_action_photo_bytes_by_obs_id: dict[str, bytes] = field(default_factory=dict)


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
    pct = round(100 * passed / total_items, 2) if total_items else 0
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


def _resolve_cover_title(sites: list["SiteData"]) -> str:
    if len(sites) == 1:
        client = (sites[0].client or "").strip()
        if not client:
            raise ValueError(
                "Single-site audit report requires a non-empty site.client "
                "(populate sites.client_name); refusing to render a generic title."
            )
        return f"{client} – {_COVER_TITLE_SUFFIX}"
    clients = {(s.client or "").strip() for s in sites}
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

    paragraph_replacements = {
        "[Insert Site Address]": site_conducted,
        "[Insert Executive Summary]": exec_summary,
        "[Insert Score]": totals["score_text"],
    }
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
    # Table 1 uses a single row with alternating label/value cells.
    label_values_single_row = {
        "Score": totals["score_text"],
        "Flagged items": f"{totals['flagged']}",
        "Actions": f"{totals['actions']}",
    }
    # Tables 2/5/7/9 use a two-cell label/value row.
    label_values_label_pair = {
        "Site conducted": site_conducted,
        "Prepared by": prepared_by,
        "Date of inspection": inspection_datetime,
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
            # Disambiguate "Flagged items" between Table 1 and Table 9.
            target_key = label
            if label == "Flagged items" and len(table.rows) == 1 and n == 2:
                target_key = "Flagged items (row)"
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


def _embed_photo(cell, photo_bytes: bytes | None, fallback_text: str) -> None:
    """Embed photo_bytes into cell as an inline image, or write fallback_text
    if bytes are absent or PIL/embed fails. Matches the thumbnail behaviour
    of the staging-review DOCX path in pims/routes.py."""
    if not photo_bytes:
        add_body_cell(cell, fallback_text)
        return
    try:
        from io import BytesIO
        from PIL import Image as PILImage
        pil = PILImage.open(BytesIO(photo_bytes)).convert("RGB")
        pil.thumbnail((300, 300), PILImage.LANCZOS)
        buf = BytesIO()
        pil.save(buf, format="JPEG", quality=85)
        buf.seek(0)
        # Clear default paragraph text then embed.
        p = cell.paragraphs[0]
        for r in list(p.runs):
            r._element.getparent().remove(r._element)
        p.add_run().add_picture(buf, width=Cm(3.5))
    except Exception:
        log.warning("Photo embed failed; falling back to text", exc_info=True)
        add_body_cell(cell, fallback_text)


def _open_actions_table(
    doc: Document,
    actions: list[dict],
    photo_bytes_by_obs_id: dict[str, bytes] | None = None,
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
        _embed_photo(row.cells[2], photo_bytes_by_obs_id.get(obs_id), "—")
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
        status = (matched_obs.get("conformance_status") or "").strip()
        photo = matched_obs.get("photo_url") or ""
        # Status now lives in the cell shading — no "[STATUS] " prefix.
        txt = finding
        if photo:
            txt += f"\nPhoto: {photo}"
        add_controls_cell(t.rows[1].cells[1], txt)
        _apply_status_cell(t.rows[1].cells[1], status)
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

    # Site title banner.
    _h(doc, f"Audit Report — {site.address}", size=16)

    # Part A — Open Actions Register (leads the body so what's wrong and
    # what's being done about it is the first thing the reader sees).
    _h(doc, "Part A — Open Actions Register", size=13)
    if site.open_actions:
        _open_actions_table(
            doc, site.open_actions, site.open_action_photo_bytes_by_obs_id,
        )
    else:
        _p(doc, "No open actions.")

    # Part B — Site Visit Summary (metadata + narrative).
    _page_break(doc)
    _h(doc, "Part B — Site Visit Summary", size=13)
    if site.project_value:
        _p(doc, f"Project value: ${site.project_value:,.0f}")
    if site.summary_text:
        _p(doc, site.summary_text)

    # Part C — Checklist.
    _page_break(doc)
    _h(doc, "Part C — Site Safety Inspection Checklist", size=13)

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

    for row, row_matches in matches_by_row:
        if not row_matches:
            _checklist_row_block(doc, row, None)
            continue
        if len(row_matches) > 1:
            log.debug(
                "Rendering %d observations against checklist row %s / %s",
                len(row_matches), row.category, row.criteria,
            )
        for obs in row_matches:
            _checklist_row_block(doc, row, obs)


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
                open_action_photo_bytes_by_obs_id=(
                    s.get("open_action_photo_bytes_by_obs_id") or {}
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

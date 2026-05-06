"""One-off post-processing: populate the Status of Previous
Recommendations table with the current audit's findings.

Operator-driven script per the 2026-05-06 review request:
  - Read every per-finding detail block in the SSA report docx
  - Build one prior-recs row per finding with these mappings:
      Recommendation     -> "F<n> – <finding_title>"
      Required Actions   -> Recommendation cell from the finding's
                           detail table (verbatim)
      Status (<date>)    -> blank
      Commentary         -> short observation summary + "See F<n>."
  - Update the table header from "Status (DD/MM/YY)" to
    "Status (<audit-date-DD/MM/YY>)"
  - Apply every change as a Word tracked change with author "Claude"
    so the operator can review and accept in Word

Run:
    python -m pims.scripts.populate_prior_recs_table \
        "G:/.../Site-Safety-Audit-Report-260501-SDG-01.docx" \
        --audit-date 01/05/26 \
        --output    "G:/.../Site-Safety-Audit-Report-260501-SDG-01-tracked.docx"

Tracked-changes mechanics:
  - Each newly inserted row carries <w:trPr><w:ins .../></w:trPr>
    so Word renders the whole row as inserted in the change-bar
    track.
  - The original placeholder row's runs are wrapped in <w:del>
    elements (with <w:delText> instead of <w:t>) so Word renders
    the placeholder text as struck-through-and-deleted.
  - Header cell rewrite uses paired <w:del>/<w:ins> elements so
    "Status (DD/MM/YY)" renders as deleted alongside the new
    "Status (01/05/26)" insertion.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

AUTHOR = "Claude"
TRACKED_DATE = (
    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
)


def _next_revision_id(state: dict[str, int]) -> str:
    """Monotonic revision-id counter shared across <w:ins>/<w:del>
    insertions so Word treats them as parts of the same revision."""
    state["n"] = state.get("n", 100) + 1
    return str(state["n"])


def _make_ins_run(text: str, rev: str, font_name: str = "Aptos") -> OxmlElement:
    """Build a <w:ins> wrapping a <w:r><w:t> with the given text.

    The run inherits the template's body font (Aptos) so the inserted
    cell content matches the surrounding cell formatting in Word's
    tracked-changes view.
    """
    ins = OxmlElement("w:ins")
    ins.set(qn("w:id"), rev)
    ins.set(qn("w:author"), AUTHOR)
    ins.set(qn("w:date"), TRACKED_DATE)
    r = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    rFonts = OxmlElement("w:rFonts")
    rFonts.set(qn("w:ascii"), font_name)
    rFonts.set(qn("w:hAnsi"), font_name)
    rFonts.set(qn("w:cs"), font_name)
    rPr.append(rFonts)
    r.append(rPr)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    ins.append(r)
    return ins


def _make_inserted_paragraph(text: str, rev: str) -> OxmlElement:
    """A <w:p> whose single run is wrapped in <w:ins>."""
    p = OxmlElement("w:p")
    p.append(_make_ins_run(text, rev))
    return p


def _make_inserted_cell(
    text: str, rev: str, width_twips: int,
) -> OxmlElement:
    tc = OxmlElement("w:tc")
    tcPr = OxmlElement("w:tcPr")
    tcW = OxmlElement("w:tcW")
    tcW.set(qn("w:w"), str(width_twips))
    tcW.set(qn("w:type"), "dxa")
    tcPr.append(tcW)
    tc.append(tcPr)
    if text:
        tc.append(_make_inserted_paragraph(text, rev))
    else:
        # Word still requires a paragraph in the cell. Use an empty
        # paragraph WITHOUT a w:ins (blank cells aren't tracked-as-
        # inserted runs; the row-level w:ins on trPr already marks
        # the whole row as inserted).
        empty_p = OxmlElement("w:p")
        tc.append(empty_p)
    return tc


def _mark_row_as_inserted(tr_element: OxmlElement, rev: str) -> None:
    """Add <w:trPr><w:ins .../></w:trPr> so Word shows the row as
    a tracked insertion."""
    trPr = tr_element.find(qn("w:trPr"))
    if trPr is None:
        trPr = OxmlElement("w:trPr")
        tr_element.insert(0, trPr)
    if trPr.find(qn("w:ins")) is None:
        ins = OxmlElement("w:ins")
        ins.set(qn("w:id"), rev)
        ins.set(qn("w:author"), AUTHOR)
        ins.set(qn("w:date"), TRACKED_DATE)
        trPr.append(ins)


def _wrap_runs_in_del(tc_element: OxmlElement, rev: str) -> None:
    """Wrap every <w:r> inside the cell in a <w:del> element and
    rename <w:t> → <w:delText> so Word renders the existing content
    as struck-through-deleted."""
    for r in list(tc_element.iter(qn("w:r"))):
        # Skip if already inside a <w:del> (idempotent on re-runs).
        parent = r.getparent()
        if parent.tag == qn("w:del"):
            continue
        del_el = OxmlElement("w:del")
        del_el.set(qn("w:id"), rev)
        del_el.set(qn("w:author"), AUTHOR)
        del_el.set(qn("w:date"), TRACKED_DATE)
        # Replace <w:t> with <w:delText> inside the run (Word's
        # required form for deleted text content).
        for t in r.iter(qn("w:t")):
            new_t = OxmlElement("w:delText")
            new_t.set(qn("xml:space"), "preserve")
            new_t.text = t.text
            t.getparent().replace(t, new_t)
        r.addprevious(del_el)
        del_el.append(r)


def _replace_header_cell_text(
    tc_element: OxmlElement,
    new_text: str,
    rev_state: dict[str, int],
) -> None:
    """Replace the header cell's existing text with ``new_text`` as
    a tracked change. Old runs get wrapped in <w:del>; a fresh
    <w:ins>-wrapped run with ``new_text`` is appended to the
    paragraph."""
    rev_del = _next_revision_id(rev_state)
    _wrap_runs_in_del(tc_element, rev_del)
    rev_ins = _next_revision_id(rev_state)
    paragraphs = list(tc_element.iter(qn("w:p")))
    if paragraphs:
        paragraphs[0].append(_make_ins_run(new_text, rev_ins))


def _detail_table_field(detail_tbl, label: str) -> str:
    """Return the right-cell text of the 2-col detail table whose
    left-cell label matches ``label`` (case-insensitive). Empty
    string when the label isn't found."""
    for row in detail_tbl.rows:
        if len(row.cells) < 2:
            continue
        cell_label = row.cells[0].text.strip().lower()
        if cell_label == label.lower():
            return row.cells[1].text.strip()
    return ""


def _short_summary(observation_text: str, max_words: int = 14) -> str:
    """Take the first sentence of the observation, cap at ``max_words``."""
    if not observation_text:
        return ""
    s = observation_text.strip()
    # Truncate at first sentence end.
    for marker in (". ", "; "):
        cut = s.find(marker)
        if 0 < cut < 200:
            s = s[:cut + 1]
            break
    words = s.split()
    if len(words) > max_words:
        s = " ".join(words[:max_words]) + "…"
    return s.rstrip(".")


def populate_prior_recs(
    docx_in: Path,
    docx_out: Path,
    audit_date_ddmmyy: str,
) -> dict:
    """Populate the prior-recs table in-place and write the result to
    ``docx_out`` with every change marked as tracked (author=Claude).

    Returns a diagnostics dict listing the number of rows written and
    the column header rewrite.
    """
    doc = Document(docx_in)

    # Locate the per-finding detail tables (2-col, first cell label
    # "Location") and the prior-recs table (4-col, first cell label
    # "Recommendation").
    detail_tables = []
    prior_tbl = None
    for t in doc.tables:
        if (
            len(t.columns) == 2
            and t.rows
            and t.rows[0].cells[0].text.strip() == "Location"
        ):
            detail_tables.append(t)
        if (
            len(t.columns) == 4
            and t.rows
            and "Recommendation" in t.rows[0].cells[0].text
            and "Required Actions" in t.rows[0].cells[1].text
        ):
            prior_tbl = t
    if prior_tbl is None:
        raise RuntimeError("Status of Previous Recommendations table not found")
    if not detail_tables:
        raise RuntimeError("No per-finding detail tables found")

    rev_state: dict[str, int] = {}

    # --- Header rewrite: Status (DD/MM/YY) -> Status (<audit_date>)
    header_cells = list(prior_tbl.rows[0].cells)
    status_cell = None
    for c in header_cells:
        if "Status" in c.text and "(" in c.text:
            status_cell = c
            break
    if status_cell is not None:
        new_header_text = f"Status ({audit_date_ddmmyy})"
        _replace_header_cell_text(status_cell._tc, new_header_text, rev_state)

    # --- Build new rows from the detail tables
    new_rows_oxml: list[OxmlElement] = []
    rec_widths = (
        prior_tbl._tbl.find(qn("w:tblGrid"))
        .findall(qn("w:gridCol"))
    )
    col_widths = [int(g.get(qn("w:w"))) for g in rec_widths]

    for n, dtbl in enumerate(detail_tables, start=1):
        title = ""
        # The #N heading paragraph sits immediately before each detail
        # table. Walk back from the table element to find the most
        # recent paragraph starting with "#".
        tbl_el = dtbl._tbl
        prev = tbl_el.getprevious()
        while prev is not None:
            if prev.tag == qn("w:p"):
                text = "".join(t.text or "" for t in prev.iter(qn("w:t"))).strip()
                if text.startswith("#"):
                    # "#3 Some Title" -> "Some Title"
                    parts = text.split(" ", 1)
                    title = parts[1].strip() if len(parts) > 1 else ""
                    break
            prev = prev.getprevious()

        rec_text = _detail_table_field(dtbl, "Recommendation") \
            or _detail_table_field(dtbl, "Required Action")
        observation_text = _detail_table_field(dtbl, "Observation")

        recommendation_cell = f"F{n} – {title}".rstrip(" –")
        required_actions_cell = rec_text
        commentary_cell = (
            f"{_short_summary(observation_text)} See F{n}."
            if observation_text else f"See F{n}."
        )

        rev_row = _next_revision_id(rev_state)
        tr = OxmlElement("w:tr")
        _mark_row_as_inserted(tr, rev_row)
        for i, cell_text in enumerate([
            recommendation_cell,
            required_actions_cell,
            "",                  # status — blank (new recommendation)
            commentary_cell,
        ]):
            w = col_widths[i] if i < len(col_widths) else 2000
            tr.append(_make_inserted_cell(cell_text, rev_row, w))
        new_rows_oxml.append(tr)

    # --- Mark the existing placeholder row as deleted (its runs
    # become <w:del>) and insert the new rows BEFORE it so Word's
    # accept-all flow leaves only the new rows.
    placeholder_tr = prior_tbl.rows[1]._tr
    rev_del_row = _next_revision_id(rev_state)
    # Mark trPr as deleted-row.
    trPr = placeholder_tr.find(qn("w:trPr"))
    if trPr is None:
        trPr = OxmlElement("w:trPr")
        placeholder_tr.insert(0, trPr)
    if trPr.find(qn("w:del")) is None:
        del_tr = OxmlElement("w:del")
        del_tr.set(qn("w:id"), rev_del_row)
        del_tr.set(qn("w:author"), AUTHOR)
        del_tr.set(qn("w:date"), TRACKED_DATE)
        trPr.append(del_tr)
    # Wrap each cell's runs in <w:del> so cell content renders as
    # struck-through-deleted.
    for tc in placeholder_tr.iter(qn("w:tc")):
        rev_del_cell = _next_revision_id(rev_state)
        _wrap_runs_in_del(tc, rev_del_cell)

    # Insert new rows before the placeholder.
    for new_tr in new_rows_oxml:
        placeholder_tr.addprevious(new_tr)

    docx_out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(docx_out)
    return {
        "rows_inserted": len(new_rows_oxml),
        "header_updated": status_cell is not None,
        "output": str(docx_out),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="populate_prior_recs_table")
    ap.add_argument("docx_in", type=Path)
    ap.add_argument(
        "--output", type=Path, default=None,
        help="output path; defaults to <input>-tracked.docx",
    )
    ap.add_argument(
        "--audit-date", default="01/05/26",
        help="Audit date for the column header, format DD/MM/YY",
    )
    args = ap.parse_args(argv)

    if not args.docx_in.exists():
        print(f"error: {args.docx_in} not found")
        return 1
    out = args.output or args.docx_in.with_name(
        args.docx_in.stem + "-tracked" + args.docx_in.suffix,
    )
    diag = populate_prior_recs(args.docx_in, out, args.audit_date)
    print("rows inserted:", diag["rows_inserted"])
    print("header updated:", diag["header_updated"])
    print("output:", diag["output"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

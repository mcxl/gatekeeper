"""Apply dotted BFBFBF 1/4 pt borders, normalise reds, strip borders from Yes/No cells.

Only touches photos rows that are already 4-cell; never converts a 2-row line-item's
content row into a photos row.
"""
from pathlib import Path
import shutil

from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

SRC = Path(r"C:\Users\AlanRichardson\OneDrive - AuditCo\Motus\Motus NEW\Motus Site Safety Audit - 260421.docx")

BORDER_NAMES = ("top", "left", "bottom", "right", "insideH", "insideV", "start", "end")
CELL_BORDER_NAMES = ("top", "left", "bottom", "right", "start", "end")
DIAGONAL_NAMES = ("tl2br", "tr2bl")

BORDER_SZ = "2"
BORDER_VAL = "dotted"
BORDER_COLOR = "BFBFBF"
RED_HEX = "FF0000"


def _make_border(name: str) -> OxmlElement:
    el = OxmlElement(f"w:{name}")
    el.set(qn("w:val"), BORDER_VAL)
    el.set(qn("w:sz"), BORDER_SZ)
    el.set(qn("w:space"), "0")
    el.set(qn("w:color"), BORDER_COLOR)
    return el


def _make_nil_border(name: str) -> OxmlElement:
    el = OxmlElement(f"w:{name}")
    el.set(qn("w:val"), "nil")
    return el


def _set_tbl_borders(tbl) -> None:
    tblPr = tbl.find(qn("w:tblPr"))
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        tbl.insert(0, tblPr)
    existing = tblPr.find(qn("w:tblBorders"))
    if existing is not None:
        tblPr.remove(existing)
    tblBorders = OxmlElement("w:tblBorders")
    for name in BORDER_NAMES:
        tblBorders.append(_make_border(name))
    for name in DIAGONAL_NAMES:
        tblBorders.append(_make_nil_border(name))
    tblPr.append(tblBorders)


def _set_cell_borders(tc) -> None:
    tcPr = tc.find(qn("w:tcPr"))
    if tcPr is None:
        tcPr = OxmlElement("w:tcPr")
        tc.insert(0, tcPr)
    existing = tcPr.find(qn("w:tcBorders"))
    if existing is not None:
        tcPr.remove(existing)
    tcBorders = OxmlElement("w:tcBorders")
    for name in CELL_BORDER_NAMES:
        tcBorders.append(_make_border(name))
    for name in DIAGONAL_NAMES:
        tcBorders.append(_make_nil_border(name))
    tcPr.append(tcBorders)


def _set_cell_border_side(tc, side: str, nil: bool = True) -> None:
    """Override a single side of the cell border. side in top/left/bottom/right."""
    tcPr = tc.find(qn("w:tcPr"))
    if tcPr is None:
        tcPr = OxmlElement("w:tcPr")
        tc.insert(0, tcPr)
    tcBorders = tcPr.find(qn("w:tcBorders"))
    if tcBorders is None:
        tcBorders = OxmlElement("w:tcBorders")
        tcPr.append(tcBorders)
    existing = tcBorders.find(qn(f"w:{side}"))
    if existing is not None:
        tcBorders.remove(existing)
    tcBorders.append(_make_nil_border(side) if nil else _make_border(side))


def _strip_cell_borders_to_nil(tc) -> None:
    """Set every side of the cell border to nil."""
    tcPr = tc.find(qn("w:tcPr"))
    if tcPr is None:
        tcPr = OxmlElement("w:tcPr")
        tc.insert(0, tcPr)
    existing = tcPr.find(qn("w:tcBorders"))
    if existing is not None:
        tcPr.remove(existing)
    tcBorders = OxmlElement("w:tcBorders")
    for name in CELL_BORDER_NAMES + DIAGONAL_NAMES:
        tcBorders.append(_make_nil_border(name))
    tcPr.append(tcBorders)


def _cell_text(tc) -> str:
    return "".join((t.text or "") for t in tc.iter(qn("w:t"))).strip()


def _cell_fill(tc):
    tcPr = tc.find(qn("w:tcPr"))
    if tcPr is None:
        return None
    shd = tcPr.find(qn("w:shd"))
    if shd is None:
        return None
    return shd.get(qn("w:fill"))


def _is_reddish(hex_str) -> bool:
    if not hex_str or hex_str.lower() in ("auto", "none"):
        return False
    h = hex_str.lstrip("#")
    if len(h) != 6:
        return False
    try:
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
    except ValueError:
        return False
    return r >= 128 and r >= g + 40 and r >= b + 40


def _is_line_item_table(tbl) -> bool:
    rows = tbl.findall(qn("w:tr"))
    if not rows:
        return False
    first_row = rows[0]
    cells = first_row.findall(qn("w:tc"))
    if len(cells) < 2:
        return False
    txt = _cell_text(cells[-1]).lower()
    return txt in ("yes", "no")


def _normalise_cell_red(tc) -> bool:
    tcPr = tc.find(qn("w:tcPr"))
    if tcPr is None:
        return False
    shd = tcPr.find(qn("w:shd"))
    if shd is None:
        return False
    fill = shd.get(qn("w:fill"))
    if not _is_reddish(fill):
        return False
    shd.set(qn("w:fill"), RED_HEX)
    if shd.get(qn("w:color")) is not None:
        shd.set(qn("w:color"), "auto")
    shd.set(qn("w:val"), "clear")
    return True


def process(doc_path: Path) -> None:
    doc = Document(str(doc_path))
    count_tables = 0
    count_cells = 0
    count_red = 0
    count_line_items = 0
    count_yesno_stripped = 0
    count_question_right_stripped = 0

    for tbl in list(doc.element.body.iter(qn("w:tbl"))):
        count_tables += 1
        _set_tbl_borders(tbl)
        for tc in tbl.iter(qn("w:tc")):
            _set_cell_borders(tc)
            count_cells += 1
            if _normalise_cell_red(tc):
                count_red += 1

        if _is_line_item_table(tbl):
            count_line_items += 1
            rows = tbl.findall(qn("w:tr"))
            first_row = rows[0]
            first_cells = first_row.findall(qn("w:tc"))
            if len(first_cells) >= 2:
                yesno_cell = first_cells[-1]
                question_cell = first_cells[-2]
                _strip_cell_borders_to_nil(yesno_cell)
                count_yesno_stripped += 1
                _set_cell_border_side(question_cell, "right", nil=True)
                count_question_right_stripped += 1

    doc.save(str(doc_path))
    print(f"Tables processed:            {count_tables}")
    print(f"Cells processed:             {count_cells}")
    print(f"Red cells normalised:        {count_red}")
    print(f"Line-item tables:            {count_line_items}")
    print(f"Yes/No cells borders nil'd:  {count_yesno_stripped}")
    print(f"Question cell right nil'd:   {count_question_right_stripped}")


if __name__ == "__main__":
    if not SRC.exists():
        raise SystemExit(f"Not found: {SRC}")
    backup = SRC.with_suffix(".bak.docx")
    if not backup.exists():
        shutil.copy2(SRC, backup)
        print(f"Backup created: {backup}")
    else:
        print(f"Backup already exists: {backup}")
    process(SRC)
    print(f"Saved: {SRC}")

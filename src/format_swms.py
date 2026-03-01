#!/usr/bin/env python3
"""
RPD SWMS Document Formatter
Post-processing rules applied to every generated SWMS document
before saving.  Called by build_all_swms.py.

Rules:
  1. Bold all em dashes (—) and capitalise the following letter
  2. Standardise all fonts to Aptos 8pt
  3. Bold control labels + yellow highlight on STOP WORK / HOLD POINT
  4. Bold sub-labels (any "Label:" pattern at start of text in CCVS)
  5. Italic for [bracketed] task descriptions
  6. Emergency Response: white text + red highlight on task name
"""

import copy
import re
from lxml import etree
from docx.oxml.ns import qn

# ============================================================
# CONSTANTS
# ============================================================

FONT_NAME = 'Aptos'
FONT_SIZE = '16'          # half-points → 8pt
EM = '\u2014'

# Labels that get bold only (no highlight)
BOLD_LABELS = [
    'Engineering:',
    'Admin:',
    'PPE:',
    'Supervision:',
]

# Labels that get bold + yellow highlight
BOLD_YELLOW_LABELS = [
    'STOP WORK if:',
    'STOP WORK:',
    'STOP WORK',
]

# HOLD POINT phrases — bold + yellow highlight
HOLD_POINT_PHRASES = [
    'HOLD POINT',
]

# Emergency Response — white text + red highlight
EMERGENCY_PHRASES = [
    'Emergency Response',
]

# ============================================================
# XML HELPERS
# ============================================================

def _ensure_rPr(r_elem):
    """Return the w:rPr child of a run, creating one if needed."""
    rPr = r_elem.find(qn('w:rPr'))
    if rPr is None:
        rPr = etree.SubElement(r_elem, qn('w:rPr'))
        r_elem.insert(0, rPr)
    return rPr


def _set_bold(rPr):
    """Add w:b to run properties if not present."""
    if rPr.find(qn('w:b')) is None:
        etree.SubElement(rPr, qn('w:b'))


def _set_highlight(rPr, colour):
    """Set w:highlight on run properties. colour = 'yellow', 'red', etc."""
    hl = rPr.find(qn('w:highlight'))
    if hl is None:
        hl = etree.SubElement(rPr, qn('w:highlight'))
    hl.set(qn('w:val'), colour)


def _set_color(rPr, hex_colour):
    """Set w:color on run properties. hex_colour = 'FFFFFF', '000000', etc."""
    c = rPr.find(qn('w:color'))
    if c is None:
        c = etree.SubElement(rPr, qn('w:color'))
    c.set(qn('w:val'), hex_colour)


def _make_run_from(rPr_orig, text, bold=False, highlight=None,
                   color=None):
    """Create a new w:r element with optional formatting overrides."""
    nr = etree.Element(qn('w:r'))
    if rPr_orig is not None:
        nrPr = copy.deepcopy(rPr_orig)
    else:
        nrPr = etree.SubElement(nr, qn('w:rPr'))
    if bold:
        _set_bold(nrPr)
    if highlight:
        _set_highlight(nrPr, highlight)
    if color:
        _set_color(nrPr, color)
    if nrPr.getparent() is None:
        nr.insert(0, nrPr)
    nt = etree.SubElement(nr, qn('w:t'))
    nt.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    nt.text = text
    return nr


def _split_and_insert(p, r, pos, label_text, rPr_orig, idx,
                       before, after, bold=True, highlight=None,
                       color=None):
    """Remove run r from paragraph p and insert up to 3 replacement
    runs: before-text, label (formatted), after-text."""
    insert_idx = idx
    if before:
        p.insert(insert_idx, _make_run_from(rPr_orig, before))
        insert_idx += 1

    p.insert(insert_idx,
             _make_run_from(rPr_orig, label_text,
                            bold=bold, highlight=highlight,
                            color=color))
    insert_idx += 1

    if after:
        p.insert(insert_idx, _make_run_from(rPr_orig, after))
        insert_idx += 1

    return 1  # count


# ============================================================
# RULE 1 — Bold em dashes + capitalise following letter
# ============================================================

def bold_em_dashes(doc):
    """Split runs at every em dash so the dash itself is bold.

    Also capitalises the first letter after each dash in the run
    text before splitting, so the source is corrected in-place.
    """
    count = 0
    for p in doc.element.body.iter(qn('w:p')):
        runs_with_dash = [
            r for r in p.findall(qn('w:r'))
            if (r.find(qn('w:t')) is not None
                and r.find(qn('w:t')).text
                and EM in r.find(qn('w:t')).text)
        ]
        for r in runs_with_dash:
            t_elem = r.find(qn('w:t'))
            rPr_orig = r.find(qn('w:rPr'))

            # Capitalise first letter after each em dash
            raw = re.sub(
                EM + r' ([a-z])',
                lambda m: EM + ' ' + m.group(1).upper(),
                t_elem.text,
            )
            parts = raw.split(EM)
            idx = list(p).index(r)
            p.remove(r)

            insert_idx = idx
            for j, part in enumerate(parts):
                if j > 0:
                    p.insert(insert_idx,
                             _make_run_from(rPr_orig, EM, bold=True))
                    insert_idx += 1
                    count += 1

                if part:
                    p.insert(insert_idx,
                             _make_run_from(rPr_orig, part))
                    insert_idx += 1
    return count


# ============================================================
# RULE 2 — Standardise fonts to Aptos 8pt
# ============================================================

def standardise_fonts(doc):
    """Set every w:rFonts to Aptos and every w:sz/w:szCs to 8pt
    throughout the document body."""
    count = 0
    for rPr in doc.element.body.iter(qn('w:rPr')):
        changed = False

        # Font name
        rFonts = rPr.find(qn('w:rFonts'))
        if rFonts is not None:
            for attr in (qn('w:ascii'), qn('w:hAnsi'), qn('w:cs'),
                         qn('w:eastAsia')):
                cur = rFonts.get(attr)
                if cur is not None and cur != FONT_NAME:
                    rFonts.set(attr, FONT_NAME)
                    changed = True
                elif cur is None and attr in (qn('w:ascii'), qn('w:hAnsi')):
                    rFonts.set(attr, FONT_NAME)
                    changed = True

        # Font size
        for tag in (qn('w:sz'), qn('w:szCs')):
            sz = rPr.find(tag)
            if sz is not None:
                if sz.get(qn('w:val')) != FONT_SIZE:
                    sz.set(qn('w:val'), FONT_SIZE)
                    changed = True

        if changed:
            count += 1
    return count


# ============================================================
# RULE 3 — Bold control labels + yellow highlight on STOP WORK
#           and HOLD POINT
# ============================================================

def bold_control_labels(doc):
    """Find control labels and STOP WORK / HOLD POINT phrases.
    Split them into formatted runs:
      - Engineering:, Admin:, PPE:, Supervision: → bold
      - STOP WORK if: → bold + yellow highlight
      - HOLD POINT → bold + yellow highlight
    """
    all_labels = (
        [(lbl, False, None, None) for lbl in BOLD_LABELS] +
        [(lbl, True, 'yellow', None) for lbl in BOLD_YELLOW_LABELS] +
        [(lbl, True, 'yellow', None) for lbl in HOLD_POINT_PHRASES]
    )
    count = 0
    for p in doc.element.body.iter(qn('w:p')):
        for r in list(p.findall(qn('w:r'))):
            t_elem = r.find(qn('w:t'))
            if t_elem is None or not t_elem.text:
                continue
            text = t_elem.text

            for label, needs_hl, hl_colour, txt_colour in all_labels:
                if label not in text:
                    continue

                pos = text.find(label)
                before = text[:pos]
                after = text[pos + len(label):]
                rPr_orig = r.find(qn('w:rPr'))
                idx = list(p).index(r)
                p.remove(r)

                count += _split_and_insert(
                    p, r, pos, label, rPr_orig, idx,
                    before, after,
                    bold=True,
                    highlight=hl_colour,
                    color=txt_colour,
                )
                break  # one label per run
    return count


# ============================================================
# RULE 4 — Bold sub-labels (any "Label:" at start of run text)
# ============================================================

def bold_sub_labels(doc):
    """In CCVS control cells, bold any sub-label pattern like
    'Anchor verification:', 'Two-rope system:', 'Rescue readiness:'
    etc. — any text ending with ':' followed by a space at the
    start of a run or after a bullet.

    Only matches capitalised words before the colon (to avoid
    false positives on phrases like 'e.g.:' or 'i.e.:').
    """
    # Match: start-of-text, optional whitespace, then
    # one or more capitalised words (with hyphens/slashes) ending ':'
    pattern = re.compile(
        r'^(\s*)'                        # leading whitespace
        r'([A-Z][A-Za-z/\-\s]*[a-z]:)'  # Label ending with colon
        r'(\s.*|$)',                      # rest of text
        re.DOTALL,
    )
    # Skip labels already handled by Rule 3
    already_handled = set(BOLD_LABELS + BOLD_YELLOW_LABELS +
                          HOLD_POINT_PHRASES)

    count = 0
    for p in doc.element.body.iter(qn('w:p')):
        for r in list(p.findall(qn('w:r'))):
            t_elem = r.find(qn('w:t'))
            if t_elem is None or not t_elem.text:
                continue

            # Skip if already bold
            rPr = r.find(qn('w:rPr'))
            if rPr is not None and rPr.find(qn('w:b')) is not None:
                continue

            m = pattern.match(t_elem.text)
            if not m:
                continue

            label = m.group(2)
            if label in already_handled:
                continue

            before = m.group(1)  # leading whitespace
            after = m.group(3)
            rPr_orig = r.find(qn('w:rPr'))
            idx = list(p).index(r)
            p.remove(r)

            count += _split_and_insert(
                p, r, 0, label, rPr_orig, idx,
                before if before.strip() else before,
                after,
                bold=True,
            )
    return count


# ============================================================
# RULE 5 — Italic for [bracketed] task descriptions
# ============================================================

def italic_bracketed_descriptions(doc):
    """Find text wrapped in [square brackets] and make it italic.
    Applies dark grey colour (444444) for visual distinction.
    Targets task description text in column 0/1 of the task table.
    """
    pattern = re.compile(r'(\[.+?\])')
    count = 0

    for p in doc.element.body.iter(qn('w:p')):
        for r in list(p.findall(qn('w:r'))):
            t_elem = r.find(qn('w:t'))
            if t_elem is None or not t_elem.text:
                continue
            text = t_elem.text

            if '[' not in text or ']' not in text:
                continue

            m = pattern.search(text)
            if not m:
                continue

            bracket_text = m.group(1)
            pos = text.find(bracket_text)
            before = text[:pos]
            after = text[pos + len(bracket_text):]
            rPr_orig = r.find(qn('w:rPr'))
            idx = list(p).index(r)
            p.remove(r)

            insert_idx = idx

            if before:
                p.insert(insert_idx,
                         _make_run_from(rPr_orig, before))
                insert_idx += 1

            # Italic + dark grey run for bracketed text
            ir = etree.Element(qn('w:r'))
            if rPr_orig is not None:
                irPr = copy.deepcopy(rPr_orig)
            else:
                irPr = etree.SubElement(ir, qn('w:rPr'))
            if irPr.find(qn('w:i')) is None:
                etree.SubElement(irPr, qn('w:i'))
            _set_color(irPr, '444444')
            # Remove bold if present (descriptions should not be bold)
            b_elem = irPr.find(qn('w:b'))
            if b_elem is not None:
                irPr.remove(b_elem)
            if irPr.getparent() is None:
                ir.insert(0, irPr)
            it = etree.SubElement(ir, qn('w:t'))
            it.set('{http://www.w3.org/XML/1998/namespace}space',
                   'preserve')
            it.text = bracket_text
            p.insert(insert_idx, ir)
            insert_idx += 1
            count += 1

            if after:
                p.insert(insert_idx,
                         _make_run_from(rPr_orig, after))
                insert_idx += 1

    return count


# ============================================================
# RULE 6 — Emergency Response: white text + red highlight
# ============================================================

def highlight_emergency_response(doc):
    """Find 'Emergency Response' in task name cells and apply
    white text + red highlight."""
    count = 0
    for p in doc.element.body.iter(qn('w:p')):
        for r in list(p.findall(qn('w:r'))):
            t_elem = r.find(qn('w:t'))
            if t_elem is None or not t_elem.text:
                continue

            for phrase in EMERGENCY_PHRASES:
                if phrase not in t_elem.text:
                    continue

                text = t_elem.text
                pos = text.find(phrase)
                before = text[:pos]
                after = text[pos + len(phrase):]
                rPr_orig = r.find(qn('w:rPr'))
                idx = list(p).index(r)
                p.remove(r)

                count += _split_and_insert(
                    p, r, pos, phrase, rPr_orig, idx,
                    before, after,
                    bold=True,
                    highlight='red',
                    color='FFFFFF',
                )
                break
    return count


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def format_swms(doc):
    """Apply all formatting rules to a SWMS document.
    Call this once before doc.save().

    Returns a dict of counts for reporting.
    """
    results = {}
    results['em_dashes'] = bold_em_dashes(doc)
    results['fonts'] = standardise_fonts(doc)
    results['labels'] = bold_control_labels(doc)
    results['sub_labels'] = bold_sub_labels(doc)
    results['italic_desc'] = italic_bracketed_descriptions(doc)
    results['emergency'] = highlight_emergency_response(doc)
    return results

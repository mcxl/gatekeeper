#!/usr/bin/env python3
"""
RPD SWMS Document Formatter
Post-processing rules applied to every generated SWMS document
before saving.  Called by build_all_swms.py.

Rules:
  1. Bold all em dashes (—) and capitalise the following letter
  2. Standardise all fonts to Aptos
  3. Bold control labels: Engineering:, Admin:, PPE:, Supervision:,
     Hold Point:, STOP WORK (with optional "if:")
"""

import copy
import re
from lxml import etree
from docx.oxml.ns import qn

# ============================================================
# CONSTANTS
# ============================================================

FONT_NAME = 'Aptos'
EM = '\u2014'

# Labels that must be bold.  Matched at the start of a run's text
# or immediately after a bullet/newline.
BOLD_LABELS = [
    'Engineering:',
    'Admin:',
    'PPE:',
    'Supervision:',
    'Hold Point:',
    'STOP WORK if:',
    'STOP WORK:',
    'STOP WORK',
]


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
                    # Bold em dash run
                    dr = etree.Element(qn('w:r'))
                    if rPr_orig is not None:
                        drPr = copy.deepcopy(rPr_orig)
                    else:
                        drPr = etree.SubElement(dr, qn('w:rPr'))
                    if drPr.find(qn('w:b')) is None:
                        etree.SubElement(drPr, qn('w:b'))
                    if drPr.getparent() is None:
                        dr.insert(0, drPr)
                    dt = etree.SubElement(dr, qn('w:t'))
                    dt.set(
                        '{http://www.w3.org/XML/1998/namespace}space',
                        'preserve',
                    )
                    dt.text = EM
                    p.insert(insert_idx, dr)
                    insert_idx += 1
                    count += 1

                if part:
                    nr = etree.Element(qn('w:r'))
                    if rPr_orig is not None:
                        nrPr = copy.deepcopy(rPr_orig)
                        nr.insert(0, nrPr)
                    nt = etree.SubElement(nr, qn('w:t'))
                    nt.set(
                        '{http://www.w3.org/XML/1998/namespace}space',
                        'preserve',
                    )
                    nt.text = part
                    p.insert(insert_idx, nr)
                    insert_idx += 1
    return count


# ============================================================
# RULE 2 — Standardise fonts to Aptos
# ============================================================

def standardise_fonts(doc):
    """Set every w:rFonts in the document body to Aptos."""
    count = 0
    for rFonts in doc.element.body.iter(qn('w:rFonts')):
        changed = False
        for attr in (qn('w:ascii'), qn('w:hAnsi'), qn('w:cs'),
                     qn('w:eastAsia')):
            cur = rFonts.get(attr)
            if cur is not None and cur != FONT_NAME:
                rFonts.set(attr, FONT_NAME)
                changed = True
            elif cur is None and attr in (qn('w:ascii'), qn('w:hAnsi')):
                rFonts.set(attr, FONT_NAME)
                changed = True
        if changed:
            count += 1
    return count


# ============================================================
# RULE 3 — Bold control labels
# ============================================================

def bold_control_labels(doc):
    """Find control labels (Engineering:, Admin:, PPE:, etc.) and
    split them into a bold run followed by the remaining text."""
    count = 0
    for p in doc.element.body.iter(qn('w:p')):
        for r in list(p.findall(qn('w:r'))):
            t_elem = r.find(qn('w:t'))
            if t_elem is None or not t_elem.text:
                continue
            text = t_elem.text

            for label in BOLD_LABELS:
                if label not in text:
                    continue

                pos = text.find(label)
                before = text[:pos]
                after = text[pos + len(label):]
                rPr_orig = r.find(qn('w:rPr'))
                idx = list(p).index(r)
                p.remove(r)

                insert_idx = idx

                # Text before the label (keep original formatting)
                if before:
                    br = etree.Element(qn('w:r'))
                    if rPr_orig is not None:
                        br.insert(0, copy.deepcopy(rPr_orig))
                    bt = etree.SubElement(br, qn('w:t'))
                    bt.set(
                        '{http://www.w3.org/XML/1998/namespace}space',
                        'preserve',
                    )
                    bt.text = before
                    p.insert(insert_idx, br)
                    insert_idx += 1

                # The label itself — bold
                lr = etree.Element(qn('w:r'))
                if rPr_orig is not None:
                    lrPr = copy.deepcopy(rPr_orig)
                else:
                    lrPr = etree.SubElement(lr, qn('w:rPr'))
                if lrPr.find(qn('w:b')) is None:
                    etree.SubElement(lrPr, qn('w:b'))
                if lrPr.getparent() is None:
                    lr.insert(0, lrPr)
                lt = etree.SubElement(lr, qn('w:t'))
                lt.set(
                    '{http://www.w3.org/XML/1998/namespace}space',
                    'preserve',
                )
                lt.text = label
                p.insert(insert_idx, lr)
                insert_idx += 1
                count += 1

                # Text after the label (keep original formatting)
                if after:
                    ar = etree.Element(qn('w:r'))
                    if rPr_orig is not None:
                        ar.insert(0, copy.deepcopy(rPr_orig))
                    at = etree.SubElement(ar, qn('w:t'))
                    at.set(
                        '{http://www.w3.org/XML/1998/namespace}space',
                        'preserve',
                    )
                    at.text = after
                    p.insert(insert_idx, ar)
                    insert_idx += 1

                # Only process first matching label per run
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
    return results

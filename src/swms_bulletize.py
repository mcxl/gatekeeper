#!/usr/bin/env python3
"""
swms_bulletize.py — SWMS Consolidated Table Bullet Post-Processor
Converts semicolon-separated control_summary text in the consolidated table (tables[2])
into ▪ small square bullet paragraphs.

Bullet: ▪ U+25AA — Technical/engineering — Calibri 9pt — indent left=360/hanging=180

Usage:
    python swms_bulletize.py input.docx output.docx

The script:
1. Unpacks the docx (zip archive)
2. Adds/updates abstractNum (id=99) + num (id=99) with ▪ bullet definition
3. Rewrites col 3 of each data row in tables[2] as bullet paragraphs
4. Repacks into a valid .docx
"""

import sys
import os
import zipfile
import shutil
import tempfile
from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

def w(tag): return f'{{{W}}}{tag}'
ns = {'w': W}

ABSTRACT_NUM_ID = '99'
NUM_ID          = '99'

BULLET_CHAR = '&#x25AA;'  # ▪ direct Unicode — Calibri supports it natively

ABSTRACT_XML = f'''<w:abstractNum xmlns:w="{W}" w:abstractNumId="{ABSTRACT_NUM_ID}">
  <w:nsid w:val="FF{ABSTRACT_NUM_ID}0000"/>
  <w:multiLevelType w:val="singleLevel"/>
  <w:tmpl w:val="AAFF{ABSTRACT_NUM_ID}BB"/>
  <w:lvl w:ilvl="0">
    <w:start w:val="1"/>
    <w:numFmt w:val="bullet"/>
    <w:lvlText w:val="{BULLET_CHAR}"/>
    <w:lvlJc w:val="left"/>
    <w:pPr>
      <w:ind w:left="360" w:hanging="180"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/>
      <w:sz w:val="18"/>
      <w:szCs w:val="18"/>
    </w:rPr>
  </w:lvl>
</w:abstractNum>'''

NUM_XML = f'''<w:num xmlns:w="{W}" w:numId="{NUM_ID}">
  <w:abstractNumId w:val="{ABSTRACT_NUM_ID}"/>
</w:num>'''


CCVS_MARKER = "CCVS HOLD POINTS"

def _run_xml(text, bold=False, highlight=False):
    """Build a single <w:r> XML string at 9pt Calibri."""
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    bold_xml = '<w:b/>' if bold else '<w:b w:val="0"/>'
    hi_xml = '<w:highlight w:val="yellow"/>' if highlight else ''
    return (
        f'<w:r xmlns:w="{W}">'
        f'<w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/>'
        f'{bold_xml}{hi_xml}'
        f'<w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr>'
        f'<w:t xml:space="preserve">{text}</w:t>'
        f'</w:r>'
    )

def make_bullet_para(text, ccvs_prefix=False):
    """
    Build a ▪ bullet <w:p> at 9pt Calibri with zero before/after spacing.
    If ccvs_prefix=True, prepend CCVS HOLD POINTS as bold + yellow run,
    then render the remainder as normal weight.
    """
    text = text.strip().rstrip(';').strip()
    if not text:
        return None

    # Build run(s)
    if ccvs_prefix:
        # Bold + yellow marker, then normal text after
        after = text[len(CCVS_MARKER):].strip()
        runs_xml = _run_xml(CCVS_MARKER, bold=True, highlight=True)
        if after:
            runs_xml += _run_xml(' ' + after, bold=False)
    else:
        runs_xml = _run_xml(text, bold=False)

    para_xml = (
        f'<w:p xmlns:w="{W}">'
        f'<w:pPr>'
        f'<w:numPr><w:ilvl w:val="0"/><w:numId w:val="{NUM_ID}"/></w:numPr>'
        f'<w:spacing w:before="0" w:after="0"/>'
        f'<w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr>'
        f'</w:pPr>'
        f'{runs_xml}'
        f'</w:p>'
    )
    return etree.fromstring(para_xml)


def unpack_docx(docx_path, work_dir):
    """Unpack a .docx file (zip archive) to a working directory."""
    with zipfile.ZipFile(docx_path, 'r') as zf:
        zf.extractall(work_dir)
    print(f'  Unpacked {os.path.basename(docx_path)}')


def pack_docx(work_dir, output_path, original_path):
    """
    Repack a working directory into a .docx file.
    Preserves the file order and compression from the original where possible.
    """
    # Get the original file list order to maintain compatibility
    original_names = []
    if original_path and os.path.exists(original_path):
        with zipfile.ZipFile(original_path, 'r') as zf:
            original_names = zf.namelist()

    # Collect all files in work_dir
    all_files = []
    for root, dirs, files in os.walk(work_dir):
        for f in files:
            full = os.path.join(root, f)
            arcname = os.path.relpath(full, work_dir).replace('\\', '/')
            all_files.append(arcname)

    # Order: original order first, then any new files
    ordered = []
    for name in original_names:
        if name in all_files:
            ordered.append(name)
            all_files.remove(name)
    ordered.extend(all_files)  # any new files at the end

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for arcname in ordered:
            full_path = os.path.join(work_dir, arcname.replace('/', os.sep))
            if os.path.exists(full_path):
                zf.write(full_path, arcname)

    print(f'  Packed {os.path.basename(output_path)}')


def update_numbering(num_path):
    """Add/replace abstractNum 99 and num 99 in numbering.xml."""
    tree = etree.parse(num_path)
    root = tree.getroot()

    # Remove existing id=99 if present (idempotent)
    for an in root.findall(w('abstractNum')):
        if an.get(w('abstractNumId')) == ABSTRACT_NUM_ID:
            root.remove(an)
    for nm in root.findall(w('num')):
        if nm.get(w('numId')) == NUM_ID:
            root.remove(nm)

    # Insert abstractNum before first w:num element
    first_num = root.find(w('num'))
    if first_num is not None:
        idx = list(root).index(first_num)
        root.insert(idx, etree.fromstring(ABSTRACT_XML))
    else:
        root.append(etree.fromstring(ABSTRACT_XML))

    root.append(etree.fromstring(NUM_XML))
    tree.write(num_path, xml_declaration=True, encoding='utf-8', pretty_print=True)
    print('  numbering.xml updated — abstractNum/num id=99')


def bulletize_consolidated(doc_path):
    """Rewrite col 3 of each data row in tables[2] as bullet paragraphs."""
    tree = etree.parse(doc_path)
    root = tree.getroot()
    tables = root.findall('.//w:tbl', ns)

    if len(tables) < 3:
        print(f'  ERROR: expected >=3 tables, found {len(tables)}')
        return 0

    tbl = tables[2]
    rows = tbl.findall('w:tr', ns)
    replaced = 0

    for i, row in enumerate(rows[1:], 1):
        cells = row.findall('w:tc', ns)
        if len(cells) <= 3:
            continue
        cell = cells[3]

        # Collect full text across all paragraphs in cell
        full_text = ' '.join(
            ''.join(t.text or '' for t in p.findall('.//w:t', ns))
            for p in cell.findall('w:p', ns)
        ).strip()

        if not full_text:
            continue

        # Split on semicolons — each becomes one bullet
        bullets = [b.strip().rstrip(';').strip() for b in full_text.split(';') if b.strip()]
        if not bullets:
            continue

        # Remove all existing paragraphs
        for p in cell.findall(w('p')):
            cell.remove(p)

        # Detect CCVS prefix on first bullet
        ccvs_first = bullets[0].startswith(CCVS_MARKER)

        # Add bullet paragraphs
        for b_i, bullet_text in enumerate(bullets):
            is_first_ccvs = ccvs_first and b_i == 0
            para = make_bullet_para(bullet_text, ccvs_prefix=is_first_ccvs)
            if para is not None:
                cell.append(para)

        replaced += 1
        preview = repr(full_text[:55])
        print(f'  Row {i:>2}: {len(bullets):>2} bullets — {preview}...')

    tree.write(doc_path, xml_declaration=True, encoding='utf-8', pretty_print=True)
    return replaced


def run(input_path, output_path):
    print(f'\n{"="*60}')
    print(f'  SWMS Bulletizer')
    print(f'  Input:  {os.path.basename(input_path)}')
    print(f'  Output: {os.path.basename(output_path)}')
    print(f'{"="*60}\n')

    work_dir = tempfile.mkdtemp(prefix='swms_bullet_')
    try:
        # Unpack
        unpack_docx(input_path, work_dir)

        # Update numbering
        num_path = os.path.join(work_dir, 'word', 'numbering.xml')
        if os.path.exists(num_path):
            update_numbering(num_path)
        else:
            print('  WARNING: numbering.xml not found — creating minimal one')
            os.makedirs(os.path.dirname(num_path), exist_ok=True)
            with open(num_path, 'w', encoding='utf-8') as f:
                f.write(f'<?xml version="1.0" encoding="utf-8"?>\n'
                        f'<w:numbering xmlns:w="{W}">\n'
                        f'{ABSTRACT_XML}\n'
                        f'{NUM_XML}\n'
                        f'</w:numbering>')
            # Add relationship if missing
            rels_path = os.path.join(work_dir, 'word', '_rels', 'document.xml.rels')
            if os.path.exists(rels_path):
                with open(rels_path, encoding='utf-8') as f:
                    rels = f.read()
                if 'numbering' not in rels:
                    rels = rels.replace('</Relationships>',
                        '<Relationship Id="rId99" '
                        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" '
                        'Target="numbering.xml"/>\n</Relationships>')
                    with open(rels_path, 'w', encoding='utf-8') as f:
                        f.write(rels)

        # Bulletize document
        doc_path = os.path.join(work_dir, 'word', 'document.xml')
        replaced = bulletize_consolidated(doc_path)
        print(f'\n  Consolidated table: {replaced} rows bulletized')

        # Pack
        pack_docx(work_dir, output_path, input_path)

        print(f'\n{"="*60}')
        print(f'  Complete -> {output_path}')
        print(f'{"="*60}\n')
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python swms_bulletize.py input.docx output.docx')
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])

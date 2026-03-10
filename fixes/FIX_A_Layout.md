# FIX GROUP A — Layout & Page Structure
Target: `renderers/docx_renderer.py`

## A1 · P0 Spacing
Para immediately before Table 0:
```python
para.paragraph_format.space_before = Pt(0)
para.paragraph_format.space_after  = Pt(0)
```

## A2 · Strip w:pageBreakBefore before Table 0
```python
from docx.oxml.ns import qn
for para in doc.paragraphs:
    pPr = para._p.find(qn('w:pPr'))
    if pPr is not None:
        pb = pPr.find(qn('w:pageBreakBefore'))
        if pb is not None:
            pPr.remove(pb)
```

## A3 · Top margin — first section
```python
from docx.shared import Cm
if doc.sections:
    doc.sections[0].top_margin = Cm(1.0)
```

Test: Cover table stays fully on page 1.
Commit: `fix(layout): P0 spacing, page break removal, top margin`

# FIX GROUP D — Worker Sign-Off Table Row Fragmentation
Target: `renderers/docx_renderer.py` → Table 8 builder

## D1 · Prevent row split across page break
```python
from docx.oxml.ns import qn
from lxml import etree

def prevent_row_break(row):
    tr = row._tr
    trPr = tr.find(qn('w:trPr'))
    if trPr is None:
        trPr = etree.SubElement(tr, qn('w:trPr'))
    cant = etree.SubElement(trPr, qn('w:cantSplit'))
    cant.set(qn('w:val'), '1')

for row in t8.rows:
    prevent_row_break(row)
```

Test: 10+ workers — no mid-row page break.
Commit: `fix(signoff): prevent table row fragmentation`

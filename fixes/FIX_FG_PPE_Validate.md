# FIX GROUP F — PPE Deduplication
Target: `renderers/docx_renderer.py`

## F1 · Dedup PPE list
```python
def dedup_ppe(ppe_list):
    seen, result = set(), []
    for item in ppe_list:
        key = item.strip().lower()
        if key not in seen:
            seen.add(key)
            result.append(item.strip())
    return result
```
Apply before writing PPE cell.

---

# FIX GROUP G — validate.py Guards

## G1 · WAH flag — force False if ccvs_code not WAH prefix
```python
if not task.get("ccvs_code","").startswith("WAH"):
    task["wah_applicable"] = False
```

## G2 · Admin controls hard cap = 20
```python
MAX_ADMIN = 20
for task in tasks:
    task["admin_controls"] = task.get("admin_controls",[])[:MAX_ADMIN]
```

## G3 · Data row fill = white (no amber)
```python
from docx.oxml.ns import qn
from lxml import etree
def set_cell_fill(cell, colour="FFFFFF"):
    tc = cell._tc
    tcPr = tc.find(qn('w:tcPr')) or etree.SubElement(tc, qn('w:tcPr'))
    shd = tcPr.find(qn('w:shd')) or etree.SubElement(tcPr, qn('w:shd'))
    shd.set(qn('w:val'),'clear')
    shd.set(qn('w:color'),'auto')
    shd.set(qn('w:fill'), colour)
```

Commit: `fix(validate): WAH flag, admin cap, white cell fill, PPE dedup`

# FIX GROUP E — CCVS Code Formatting
Target: `renderers/docx_renderer.py`, `validate.py`

## E1 · Normalise CCVS format (hyphen separator)
```python
import re
def normalise_ccvs(code: str) -> str:
    code = code.strip().upper().replace("/", "-")
    if "-" not in code:
        m = re.match(r'^([A-Z]{2,4})([A-Z0-9]{1,4})$', code)
        if m:
            code = f"{m.group(1)}-{m.group(2)}"
    return code
```
Apply to every CCVS value before writing to cell.

## E2 · N/A filter for CCVS monitoring table
```python
ccvs_rows = [
    t for t in tasks
    if t.get("ccvs_code") and t.get("status","").upper() != "N/A"
]
```

Test: `"WAHH6"` → `"WAH-H6"`. N/A tasks excluded.
Commit: `fix(ccvs): hyphen format + N/A filter`

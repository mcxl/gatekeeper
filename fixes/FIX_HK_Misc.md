# FIX GROUP H — Legislation & References

## H1 · Default jurisdiction = WHS Act 2011 (NSW)
In `jurisdictions.py`:
```python
DEFAULT_JURISDICTION = {
    "act": "Work Health and Safety Act 2011 (NSW)",
    "regulation": "Work Health and Safety Regulation 2017 (NSW)",
    "code": "SafeWork NSW Codes of Practice",
}
def resolve_jurisdiction(job):
    return job.get("jurisdiction") or DEFAULT_JURISDICTION
```

## H2 · Strip AS/NZS 3580 hallucination
In `validate.py`:
```python
HALLUCINATED_REFS = {"AS/NZS 3580","AS/NZS3580"}
def strip_hallucinated_refs(citations):
    return [c for c in citations if c not in HALLUCINATED_REFS]
```

---

# FIX GROUP I — HRCW Checkbox

## I1 · Regex handles variable whitespace
```python
import re
HRCW_PATTERN = re.compile(r'\[\s*\]')
def tick_hrcw(text, active):
    return HRCW_PATTERN.sub('[✓]', text, count=1) if active else text
```

---

# FIX GROUP J — validate_output()

## J1 · Post-render guard
```python
import re
from docx import Document
PLACEHOLDER_RE = re.compile(r'\[.*?\]')

def validate_output(doc_path):
    errors = []
    doc = Document(doc_path)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if PLACEHOLDER_RE.search(cell.text.strip()):
                    errors.append(f"Placeholder: '{cell.text[:60]}'")
    return errors
```

---

# FIX GROUP K — Unit Tests (8 minimum)
File: `tests/test_ccvs.py`

| # | Input | Expected |
|---|-------|----------|
| 1 | `normalise_ccvs("WAHH6")` | `"WAH-H6"` |
| 2 | `normalise_ccvs("WAH/H6")` | `"WAH-H6"` |
| 3 | `dedup_ppe(["hard hat","Hard Hat","gloves"])` | 2 items |
| 4 | `ccvs_code="ELE-E1"` → wah_applicable | `False` |
| 5 | 25 admin controls → trimmed | `len == 20` |
| 6 | Footer `{doc_ref}` resolved | `"SWMS-260307"` |
| 7 | validate_output with `[PCBU Name]` | errors non-empty |
| 8 | HRCW `[  ]` double-space | `"[✓]"` |

Run: `pytest tests/ -v`
Commit: `fix(misc): legislation, HRCW, validate_output, unit tests`

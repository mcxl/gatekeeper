# FIX GROUP B — PCBU / Principal Contractor Fields
Target: `renderers/docx_renderer.py` → `_fill_cover_table()`

## B1 · PCBU field
```python
pcbu_name = job.get("pcbu_name") or job.get("company_name") or "[PCBU Name]"
t0.cell(1, 1).paragraphs[0].runs[0].text = pcbu_name
```

## B2 · Principal Contractor field (separate from PCBU)
```python
principal = job.get("principal_contractor") or job.get("pcbu_name") or "[Principal Contractor]"
t0.cell(2, 1).paragraphs[0].runs[0].text = principal
```

Test: Both fields render independently.
Commit: `fix(cover): PCBU and principal contractor field population`

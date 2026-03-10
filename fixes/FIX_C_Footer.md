# FIX GROUP C — Footer Slug Resolution
Target: `renderers/docx_renderer.py` → `_apply_footers()`

## C1 · Resolve footer tokens
```python
FOOTER_TOKENS = {
    "{doc_ref}":  job.get("doc_ref", "SWMS-DRAFT"),
    "{revision}": job.get("revision", "V1"),
    "{project}":  job.get("project_name", ""),
    "{date}":     job.get("issue_date", ""),
}
for section in doc.sections:
    for para in section.footer.paragraphs:
        for run in para.runs:
            for token, value in FOOTER_TOKENS.items():
                run.text = run.text.replace(token, value)
```

Test: Footer shows `SWMS-260307 V2` not `{doc_ref} {revision}`.
Commit: `fix(footer): resolve slug tokens in all section footers`

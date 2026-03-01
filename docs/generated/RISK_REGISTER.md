# RISK REGISTER — Codebase Analysis

*Generated: 02/03/2026 — Gatekeeper Project — RPD*

---

| # | Risk | Severity | Description | Mitigation |
|---|------|----------|-------------|------------|
| 1 | Hardcoded Windows paths | Medium | Found in 11 location(s): swms_22smith_spalling.py:134, swms_22smith_spalling.py:178, swms_22smith_spalling.py:228, swms_22smith_spalling.py:275, SWMS_BASE_GENERAL.py:747... | Use os.path.join() or pathlib for all file paths |
| 2 | External dependencies | Low | 9 third-party packages: SWMS_BASE_GENERAL, docx, lxml, openpyxl, shutil, swms_generator, swms_vocabulary, tempfile, zipfile | Pin versions in requirements.txt — verify compatibility before upgrading |
| 3 | Locked output files | High | 1 lock file(s) detected: ~$D-MSW-002_Remedial_Works_Master_SWMS.docx | Close Word/Excel before running builds — lock files prevent overwrite |
| 4 | Test coverage gaps | High | 1/19 source files have matching test files. Uncovered: audit_classification.py, build_all_swms.py, data_analysis.py, docx_style_standard.py, format_swms.py, generate_project_docs.py, risk_register_to_docx.py, risk_register_to_xlsx.py... | Add test_<filename>.py for critical modules — prioritise engine and validators |
| 5 | Missing error handling | Medium | 1 file(s) use open() without any try/except: vocab_tool.py | Add try/except around file I/O in scripts that write to outputs/ |

**Total risks identified:** 5

### Summary

- **High:** 2
- **Medium:** 2
- **Low:** 1


## Cross-Reference Notes

- Test coverage gap risk is documented — aligns with PROJECT_STATUS file counts
- COMPLIANCE_MATRIX reports missing output documents

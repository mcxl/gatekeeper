"""SSA output quality guards.

Subpackage that hardens the SSA report-docx output path. Modules land
across Phases 1-5 of the SDG-SSA quality hardening plan
(docs/plans/sdg-ssa-quality-hardening.md):

- determinism       (Phase 1) — byte-stable docx output
- oxml_validator    (Phase 2) — OOXML schema validation
- libreoffice_smoke (Phase 3) — headless render smoke test
- preflight         (Phase 4) — --check folder/inputs validation
"""
from .determinism import make_docx_deterministic
from .libreoffice_smoke import SmokeResult, smoke_test_docx
from .oxml_validator import ValidationError, ValidationResult, validate_docx
from .preflight import CheckResult, format_results, run_preflight

__all__ = [
    "make_docx_deterministic",
    "ValidationError",
    "ValidationResult",
    "validate_docx",
    "SmokeResult",
    "smoke_test_docx",
    "CheckResult",
    "format_results",
    "run_preflight",
]

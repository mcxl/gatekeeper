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

__all__ = ["make_docx_deterministic"]

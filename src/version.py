"""
src/version.py — Version constants for traceability on artifacts.

Simple constants. No version registry or database.
Stamp relevant JSON artifacts with these for operational traceability.
"""

ENGINE_VERSION = "1.0.0"

RULE_LIBRARY_VERSION = "1.0"

PROMPT_VERSIONS = {
    "decomposer": "2026-04-01",
    "control_writer": "2026-04-01",
    "risk_assessor": "2026-03-30",
    "assembler": "2026-03-30",
    "reviewer_agent": "2026-04-01",
}


def version_stamp() -> dict:
    """Return a version metadata dict for stamping artifacts."""
    return {
        "engine_version": ENGINE_VERSION,
        "rule_library_version": RULE_LIBRARY_VERSION,
        "prompt_versions": dict(PROMPT_VERSIONS),
    }

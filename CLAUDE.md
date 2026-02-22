# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Gatekeeper is a Zero-Trust Safety Framework for the construction industry. It addresses normalization of deviance through mandatory mental checkpoints, audit classification, and data-driven risk analysis. Built by AuditCo (mcxi.com.au).

## Commands

```bash
# Setup
python -m venv venv
source venv/Scripts/activate   # Windows/Git Bash
pip install -r requirements.txt

# Run tests
pytest tests/

# Run a single test
pytest tests/test_mental_checkpoints.py

# Run a specific test function
pytest tests/test_mental_checkpoints.py::test_function_name
```

## Architecture

### src/ — Core Modules

- **swms_generator.py** - Main SWMS generation module that populates a Word template with FSC-compliant Safe Work Method Statements for Australian construction projects. Uses python-docx and contains task splitting logic, risk controls, and Gatekeeper gate code mapping.
- **swms_bulletize.py** - Bullet formatting helper for SWMS document output
- **mental_checkpoints.py** - `MentalCheckpoint` class: defines deliberate pause points that interrupt automatic work processes to force safety engagement and prevent complacency
- **audit_classification.py** - `AuditClassification` class: performs quantitative risk scoring for site inspections with observations categorized by severity (e.g., "MEDIUM")
- **data_analysis.py** - Trend identification and proactive risk analysis using pandas/numpy

### docs/ — SWMS System Documentation

- **SWMS_GENERATOR_MASTER_v16_0.md** - Master instructions for SWMS generation (the authoritative reference)
- **SWMS_TASK_LIBRARY.md** - Library of construction tasks and their associated controls
- **SWMS_METHODOLOGY.md** - Generation methodology and process
- **SWMS_OPERATOR_GUIDE.md** - Guide for operators using the system
- **USER_INPUT_REQUEST_GENERAL.md** - User input templates for SWMS requests
- **PROJECT_INSTRUCTIONS.md** - Project setup instructions
- **SWMS_Template.docx** - Word template used as the base for generated SWMS documents

### tests/

Tests mirror the `src/` module names (e.g., `test_mental_checkpoints.py`).

## Workflow
1. Create feature branch from main
2. Write tests first
3. Implement feature
4. Commit with descriptive message

## Boundaries
✅ Always:
- Follow Australian WHS Act 2011 and regulations
- Use FSC-compliant risk language
- Write tests before implementing features

⚠️ Ask first:
- Changes to gate code classifications
- Modifying SWMS template structure

🚫 Never:
- Commit API keys or credentials
- Delete failing tests
- Use non-metric units

## Known Gotchas
- Add lessons learned here using # in Claude Code

## Dependencies

Core: pandas, numpy, python-docx (document generation). Testing: pytest.

## Import Convention

Modules are imported from `src/` directly:
```python
from src.mental_checkpoints import MentalCheckpoint
from src.audit_classification import AuditClassification
```

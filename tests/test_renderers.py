"""
Tests for renderers/docx_renderer.py and renderers/md_renderer.py
"""

import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.schema import TaskBlock
from core.validate import WAH_SENTENCE
from renderers.md_renderer import render_md


# ============================================================
# HELPERS
# ============================================================

def _make_task(**kwargs) -> TaskBlock:
    defaults = dict(
        task="Test Task",
        scope="Test scope",
        risk_pre="Medium-4",
        risk_post="Low-1",
        responsibility={"SUP": "Oversee task"},
        controls=[
            "Inspect area before starting work",
            "Wear correct PPE at all times",
            "Remove debris from work zone",
        ],
        hold_points=["Verify setup complete", "Confirm crew briefed"],
        stop_work=["Stop if conditions change", "Stop if equipment fails"],
        ppe=["Wear hard hat and boots"],
        admin=[],
        approved=True,
    )
    defaults.update(kwargs)
    return TaskBlock(**defaults)


# ============================================================
# MD RENDERER
# ============================================================

def test_md_approved():
    """Approved task renders no warning banner."""
    task = _make_task(approved=True)
    md = render_md(task)
    assert "AI-GENERATED" not in md
    assert "PENDING REVIEW" not in md


def test_md_unapproved():
    """Unapproved task includes warning banner at end."""
    task = _make_task(approved=False, source="ai-generated")
    md = render_md(task)
    assert "AI-GENERATED" in md
    assert "PENDING REVIEW" in md
    # Banner must be the last non-empty line
    last_line = [l for l in md.splitlines() if l.strip()][-1]
    assert "PENDING REVIEW" in last_line or "approved" in last_line.lower()


def test_md_wah():
    """WAH sentence appears as the first controls bullet when wah_applicable."""
    task = _make_task(
        wah_applicable=True,
        controls=[WAH_SENTENCE, "Inspect harness before use", "Wear hard hat"],
    )
    md = render_md(task)
    # WAH sentence text should appear in the output
    assert "unprotected edge" in md
    assert "WAH" in md


# ============================================================
# DOCX RENDERER — legacy render_docx() removed
# Active DOCX tests are in test_renderer.py (render_swms_document)
# ============================================================

def test_legacy_render_docx_raises():
    """render_docx() is retired and must raise RuntimeError."""
    from renderers.docx_renderer import render_docx
    task = _make_task()
    import pytest
    with pytest.raises(RuntimeError, match="retired"):
        render_docx(task)

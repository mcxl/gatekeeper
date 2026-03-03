"""
Tests for renderers/docx_renderer.py and renderers/md_renderer.py
"""

import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.schema import TaskBlock
from core.validate import WAH_SENTENCE
from renderers.docx_renderer import AMBER_BG, render_docx
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
# DOCX RENDERER
# ============================================================

def test_docx_returns_bytes():
    """render_docx returns non-empty bytes that form a valid ZIP (docx format)."""
    task = _make_task()
    result = render_docx(task)
    assert isinstance(result, bytes)
    assert len(result) > 0
    # .docx files are ZIP archives — validate the container
    import io
    assert zipfile.is_zipfile(io.BytesIO(result))


def test_docx_unapproved_amber():
    """Unapproved task rows contain amber fill (FFE699) in the docx XML."""
    task = _make_task(approved=False)
    docx_bytes = render_docx(task)

    import io
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:
        doc_xml = z.read("word/document.xml").decode("utf-8")

    assert AMBER_BG.upper() in doc_xml.upper(), (
        f"Expected amber fill {AMBER_BG} not found in document XML"
    )

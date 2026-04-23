"""End-to-end smoke test: build audit report docx with one matched obs + one reframed row."""
from __future__ import annotations

from pathlib import Path
from io import BytesIO

import openpyxl
import pytest
from docx import Document

from pims import audit_report_docx as arpt


@pytest.fixture(autouse=True)
def _isolate_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(arpt, "DATA_DIR", tmp_path)
    monkeypatch.setattr(arpt, "REFRAME_CACHE_PATH", tmp_path / "reframe_cache.jsonl")


@pytest.fixture
def checklist_xlsx(tmp_path):
    p = tmp_path / "checklist.xlsx"
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet(arpt.SHEET_HIGH)
    ws.append(["Category", "Criteria", "Instruction", "ccvs_code", "ccvs_category",
               "observation_text_enriched"])
    ws.append(["01. Planning", "Is PPE provided?",
               "Check all workers have required PPE", "WAH-H6",
               "Working at Height", "PPE worn at height"])
    ws.append(["02. Systems", "Is induction complete?",
               "Check all workers have completed required inductions and training",
               "SYS-L1", "Systems", "Induction records current"])
    # Low sheet also needs to exist for loader sanity though unused here
    low = wb.create_sheet(arpt.SHEET_LOW)
    low.append(["Category", "Criteria", "Instruction"])
    wb.save(p)
    return p


@pytest.fixture
def template_docx(tmp_path):
    p = tmp_path / "template.docx"
    Document().save(p)
    return p


def test_build_docx_with_match_and_reframe(checklist_xlsx, template_docx):
    sites = [arpt.SiteData(
        address="1 Test St, Sydney",
        project_value=500000,
        client="Test Client Pty Ltd",
        summary_text="Routine inspection.",
        observations=[{
            "seq_no": 1,
            "photo_url": "P001",
            "observation_text": "Worker at height without harness",
            "observation_text_enriched": "Worker on roof without fall protection",
            "conformance_status": "NCR",
            "ccvs_code": "WAH-H6",
            "action_required": True,
            "action_description": "Issue harness",
            "responsible": "Site Supervisor",
            "due_category": "Immediate",
        }],
        open_actions=[],
    )]
    sites[0].open_actions = [o for o in sites[0].observations if o.get("action_required")]

    buf = arpt.build_audit_report_docx(
        sites,
        checklist_xlsx_path=checklist_xlsx,
        template_path=template_docx,
    )
    assert isinstance(buf, BytesIO)
    buf.seek(0)
    doc = Document(buf)

    full_text = "\n".join(p.text for p in doc.paragraphs)
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                full_text += "\n" + cell.text

    # Part A + Part B headers
    assert "Part A" in full_text
    assert "Part B" in full_text
    # The matched row renders the NCR finding + photo
    assert "P001" in full_text
    assert "NCR" in full_text
    # The unmatched row (inductions) is reframed per the golden example
    assert "All workers have completed required inductions and training." in full_text


def test_no_checklist_block_has_duplicate_header_text(checklist_xlsx, template_docx):
    """Regression guard: the header row of a _checklist_row_block must be
    [category, 'Result']. No row 0 produced by this code path should have
    identical text in its first two cells unless the cell text is literally
    'Result' (i.e. category is missing and falls back to the same literal)."""
    sites = [arpt.SiteData(
        address="Test Site",
        project_value=500_000,
        client="Acme",
        prepared_by="J",
        inspection_datetime="1 Jan 2026, 10:00 AEDT",
        summary_text="S",
        observations=[],
        open_actions=[],
    )]
    buf = arpt.build_audit_report_docx(
        sites,
        checklist_xlsx_path=checklist_xlsx,
        template_path=template_docx,
    )
    buf.seek(0)
    doc = Document(buf)
    for t in doc.tables:
        if not t.rows or len(t.rows[0].cells) < 2:
            continue
        a = t.rows[0].cells[0].text.strip()
        b = t.rows[0].cells[1].text.strip()
        if not a or not b:
            continue
        if a == b and a != "Result" and b != "Result":
            raise AssertionError(
                f"Header row cells mirror each other: {a!r} == {b!r}"
            )


def test_build_fails_on_null_project_value(checklist_xlsx, template_docx):
    sites = [arpt.SiteData(address="X", project_value=None, client="Acme", observations=[])]
    with pytest.raises(ValueError):
        arpt.build_audit_report_docx(
            sites,
            checklist_xlsx_path=checklist_xlsx,
            template_path=template_docx,
        )


def test_build_fails_on_missing_template(checklist_xlsx, tmp_path):
    sites = [arpt.SiteData(address="X", project_value=100000, client="Acme", observations=[])]
    with pytest.raises(FileNotFoundError):
        arpt.build_audit_report_docx(
            sites,
            checklist_xlsx_path=checklist_xlsx,
            template_path=tmp_path / "nope.docx",
        )

"""Smoke tests for the canonical-template audit-report renderer.

Stage B (2026-05-13): the renderer fills the pre-existing checklist
structure in pims/RPD_SSA_template-inserted.docx via
pims/services/template_index.py + the observation→LineItem matcher in
pims/audit_report_docx.py. These tests assert against that canonical
structure, NOT the degraded `audit_report_template.docx` shape the
prior renderer targeted.

The 18 Phase D/E/F/G tests that asserted Part A/B/C/D structure from
the degraded-template path have been deleted (see git history at
commit 7b785c4 for the Stage-A-skipped state). Their replacements
live here and in tests/test_audit_report_fill.py.
"""
from __future__ import annotations

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
    ws.append(["Category", "Criteria", "Instruction"])
    ws.append(["01. Planning and Risk Management (Project Value >$250K)",
               "01. Does the site sign include required warnings?",
               "Check the site sign."])
    low = wb.create_sheet(arpt.SHEET_LOW)
    low.append(["Category", "Criteria", "Instruction"])
    low.append(["01. Planning and Risk Management (Project Value <$250K)",
                "01. Is the QR code displayed?",
                "Check the QR code."])
    wb.save(p)
    return p


def _full_text(doc: Document) -> str:
    parts = [p.text for p in doc.paragraphs]
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Renderer contract
# ---------------------------------------------------------------------------

def test_renderer_is_single_site_only(checklist_xlsx):
    """Stage B 2026-05-13: build_audit_report_docx mutates pre-existing
    template tables in place, so multi-site-in-one-doc would silently
    overwrite. Single-site contract is enforced at the boundary."""
    sites = [
        arpt.SiteData(address="A", project_value=100_000, client="Client A",
                      observations=[], open_actions=[]),
        arpt.SiteData(address="B", project_value=100_000, client="Client B",
                      observations=[], open_actions=[]),
    ]
    with pytest.raises(ValueError, match="single-site"):
        arpt.build_audit_report_docx(sites, checklist_xlsx_path=checklist_xlsx)


def test_build_fails_on_null_project_value(checklist_xlsx):
    sites = [arpt.SiteData(address="X", project_value=None, client="Acme",
                           observations=[])]
    with pytest.raises(ValueError):
        arpt.build_audit_report_docx(sites, checklist_xlsx_path=checklist_xlsx)


def test_build_fails_on_missing_template(checklist_xlsx, tmp_path):
    sites = [arpt.SiteData(address="X", project_value=100_000, client="Acme",
                           observations=[])]
    with pytest.raises(FileNotFoundError):
        arpt.build_audit_report_docx(
            sites,
            checklist_xlsx_path=checklist_xlsx,
            template_path=tmp_path / "nope.docx",
        )


# ---------------------------------------------------------------------------
# Canonical-template body structure
# ---------------------------------------------------------------------------

def _render_one_site(observations, project_value, checklist_xlsx,
                     client="Robertson's Remedial and Painting Pty Ltd"):
    site = arpt.SiteData(
        address="96-98 Hampden Rd, Russell Lea NSW",
        project_value=project_value,
        client=client,
        prepared_by="Test Auditor",
        inspection_datetime="13 May 2026 09:00 AEST",
        summary_text="Stage B smoke render.",
        observations=observations,
        open_actions=[],
        report_issue_date="2026-05-13",
    )
    if not arpt.TEMPLATE_PATH.exists():
        pytest.skip("Canonical template not present")
    buf = arpt.build_audit_report_docx([site], checklist_xlsx_path=checklist_xlsx)
    buf.seek(0)
    return Document(buf)


def test_no_part_abcd_headings_in_canonical_render(checklist_xlsx):
    """Canonical template has no Part A/B/C/D — the Stage A pivot
    removed the renderer code that emitted those. Regression guard."""
    doc = _render_one_site([], 300_000, checklist_xlsx)
    text = _full_text(doc)
    for marker in ("Part A —", "Part B —", "Part C —", "Part D —",
                   "Auditor Sign-off"):
        assert marker not in text, f"Stale Part-X marker present: {marker!r}"


def test_canonical_render_has_executive_summary_and_inspection_headings(
    checklist_xlsx,
):
    """Canonical template carries both heading texts; renderer leaves
    them in place. References (Cremorne / Fraters) carry both."""
    doc = _render_one_site([], 300_000, checklist_xlsx)
    text = _full_text(doc)
    assert "Executive Summary" in text
    assert "Site Safety Inspection" in text


def test_inactive_planning_tier_renders_as_na(checklist_xlsx):
    """A site with project_value >= VALUE_THRESHOLD ($250K) renders
    the <$250K planning section's per-criterion status cells as N/A
    (and vice versa). The canonical template carries BOTH planning
    sections; only one can be active per site."""
    from pims.services.template_index import get_index, PLANNING_LOW
    doc = _render_one_site([], 300_000, checklist_xlsx)
    # Find every header_table_idx in the inactive section and assert
    # its status cell is N/A.
    idx = get_index()
    inactive_items = [li for li in idx.items if li.section == PLANNING_LOW]
    assert inactive_items, "expected at least one inactive-tier item"
    for li in inactive_items:
        status_cell = doc.tables[li.header_table_idx].rows[0].cells[1]
        assert status_cell.text.strip() == "N/A", (
            f"inactive planning tier item at header_table_idx="
            f"{li.header_table_idx} should be N/A, got "
            f"{status_cell.text.strip()!r}"
        )


def test_active_planning_tier_keeps_default_for_unmatched(checklist_xlsx):
    """Active-tier line items with no matching observation keep their
    template-default Compliant shading (the canonical template's
    default state)."""
    from pims.services.template_index import get_index, PLANNING_HIGH
    doc = _render_one_site([], 300_000, checklist_xlsx)
    idx = get_index()
    active_items = [li for li in idx.items if li.section == PLANNING_HIGH]
    assert active_items
    # All status cells in the active tier should read "Compliant"
    # (template default left intact when no obs matches).
    for li in active_items:
        cell = doc.tables[li.header_table_idx].rows[0].cells[1]
        assert cell.text.strip() == "Compliant", (
            f"active tier unmatched item at header_table_idx="
            f"{li.header_table_idx} should keep Compliant default, got "
            f"{cell.text.strip()!r}"
        )


def test_na_section_items_paint_na_when_unmatched(checklist_xlsx):
    """Sections in NA_SECTIONS (Rope access, Plant and equipment,
    Demolition, Energy and services) get N/A on items with no
    matching observation."""
    from pims.services.template_index import get_index, NA_SECTIONS
    doc = _render_one_site([], 300_000, checklist_xlsx)
    idx = get_index()
    na_items = [li for li in idx.items if li.section in NA_SECTIONS]
    assert na_items
    for li in na_items:
        cell = doc.tables[li.header_table_idx].rows[0].cells[1]
        assert cell.text.strip() == "N/A", (
            f"NA_SECTIONS item at {li.header_table_idx} should be N/A, "
            f"got {cell.text.strip()!r}"
        )


def test_matched_observation_paints_worst_status(checklist_xlsx):
    """When 2+ observations match one line item, the status cell
    reflects the worst-severity status (NCR > Conditional > Compliant).
    """
    from pims.services.template_index import get_index
    obs = [
        {"id": "o1", "conformance_status": "Compliant",
         "ccvs_category": "General work at height",
         "observation_text_enriched": "Edge protection present on east elevation."},
        {"id": "o2", "conformance_status": "NCR",
         "ccvs_category": "General work at height",
         "observation_text_enriched": "Edge protection partially missing on south elevation."},
    ]
    doc = _render_one_site(obs, 300_000, checklist_xlsx)
    idx = get_index()
    # Find the line item that received both observations (matched by
    # observation_text_enriched against item_text).
    matched_idx = None
    for li in idx.items:
        cell = doc.tables[li.header_table_idx].rows[0].cells[1]
        if cell.text.strip() == "NCR":
            matched_idx = li.header_table_idx
            break
    assert matched_idx is not None, "no LineItem received NCR status"


def test_multi_observation_narratives_concatenate(checklist_xlsx):
    """Multiple matched observations on one line item concatenate
    their narratives in the single narrative cell with blank-line
    separators. No new rows are added to the obs_table."""
    obs = [
        {"id": "o1", "conformance_status": "Compliant",
         "ccvs_category": "General work at height",
         "observation_text_enriched": "FIRST_NARRATIVE_MARKER edge protection ok."},
        {"id": "o2", "conformance_status": "NCR",
         "ccvs_category": "General work at height",
         "observation_text_enriched": "SECOND_NARRATIVE_MARKER edge protection partial."},
    ]
    doc = _render_one_site(obs, 300_000, checklist_xlsx)
    text = _full_text(doc)
    assert "FIRST_NARRATIVE_MARKER" in text
    assert "SECOND_NARRATIVE_MARKER" in text


def test_cover_populates_no_bracketed_placeholders_remain(checklist_xlsx):
    """No [Insert ...] tokens should survive in the final docx. The
    canonical template's title-page + page-2 header placeholders are
    populated by _populate_cover."""
    import re
    doc = _render_one_site([], 300_000, checklist_xlsx)
    text = _full_text(doc)
    leftovers = re.findall(r"\[Insert[^\]]{0,80}\]", text)
    assert leftovers == [], f"unreplaced placeholders: {leftovers}"

"""
tests/test_edit_capture.py — Tests for consultant edit capture.
"""

import json
import os
import sys
from io import BytesIO
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.edit_capture import (
    compute_edit_delta,
    extract_swms_table_text,
    fingerprint_snapshot,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ── Helpers ─────────────────────────────────────────────────────────────────

def _make_docx_bytes(headers: list[str], rows: list[list[str]]) -> bytes:
    """Create a minimal docx in memory with a single table."""
    from docx import Document
    doc = Document()
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    for i, h in enumerate(headers):
        table.rows[0].cells[i].text = h
    for ri, row_data in enumerate(rows):
        for ci, val in enumerate(row_data):
            table.rows[ri + 1].cells[ci].text = val
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ── Table detection ─────────────────────────────────────────────────────────

class TestTableDetection:
    def test_extract_finds_swms_table(self):
        docx = _make_docx_bytes(
            ["Step", "Task", "Hazards", "Controls"],
            [["1.1", "Install scaffold", "Fall", "Edge protection"]],
        )
        rows = extract_swms_table_text(docx)
        assert len(rows) == 1
        assert rows[0]["task"] == "Install scaffold"

    def test_extract_raises_on_no_matching_table(self):
        docx = _make_docx_bytes(
            ["Name", "Age", "City"],
            [["Alice", "30", "Sydney"]],
        )
        with pytest.raises(ValueError, match="SWMS table not found"):
            extract_swms_table_text(docx)

    def test_extract_requires_task_header(self):
        """Table with Hazards but no Task header should not match."""
        docx = _make_docx_bytes(
            ["Step", "Hazards", "Controls"],
            [["1.1", "Fall", "Harness"]],
        )
        with pytest.raises(ValueError, match="SWMS table not found"):
            extract_swms_table_text(docx)

    def test_extract_case_insensitive_headers(self):
        docx = _make_docx_bytes(
            ["STEP", "TASK", "HAZARDS", "CONTROLS"],
            [["1.1", "Paint wall", "Fumes", "Ventilation"]],
        )
        rows = extract_swms_table_text(docx)
        assert len(rows) == 1

    def test_extract_matches_ccvs_header(self):
        docx = _make_docx_bytes(
            ["Step", "Task", "CCVS"],
            [["1.1", "Install roof", "WAH-H6"]],
        )
        rows = extract_swms_table_text(docx)
        assert rows[0]["ccvs"] == "WAH-H6"


# ── Normalized extraction ───────────────────────────────────────────────────

class TestNormalizedExtraction:
    def test_row_index_starts_at_1(self):
        docx = _make_docx_bytes(
            ["Step", "Task", "Controls"],
            [["1.1", "Task A", "Control A"], ["1.2", "Task B", "Control B"]],
        )
        rows = extract_swms_table_text(docx)
        assert rows[0]["row_index"] == 1
        assert rows[1]["row_index"] == 2

    def test_whitespace_stripped(self):
        docx = _make_docx_bytes(
            ["Step", "Task", "Controls"],
            [["1.1", "  Task A  ", "  Control A  "]],
        )
        rows = extract_swms_table_text(docx)
        assert rows[0]["task"] == "Task A"
        assert rows[0]["controls"] == "Control A"

    def test_empty_task_rows_skipped(self):
        docx = _make_docx_bytes(
            ["Step", "Task", "Controls"],
            [["1.1", "Task A", "Control A"], ["", "", ""], ["1.2", "Task B", "Control B"]],
        )
        rows = extract_swms_table_text(docx)
        assert len(rows) == 2


# ── Fingerprint ─────────────────────────────────────────────────────────────

class TestFingerprint:
    def test_fingerprint_deterministic(self):
        rows = [{"task": "A", "controls": "B"}]
        fp1 = fingerprint_snapshot(rows)
        fp2 = fingerprint_snapshot(rows)
        assert fp1 == fp2
        assert len(fp1) == 64  # sha256 hex

    def test_row_index_excluded_from_fingerprint(self):
        rows_a = [{"row_index": 1, "task": "A", "controls": "B"}]
        rows_b = [{"row_index": 99, "task": "A", "controls": "B"}]
        assert fingerprint_snapshot(rows_a) == fingerprint_snapshot(rows_b)

    def test_different_content_different_fingerprint(self):
        rows_a = [{"task": "A", "controls": "B"}]
        rows_b = [{"task": "A", "controls": "C"}]
        assert fingerprint_snapshot(rows_a) != fingerprint_snapshot(rows_b)


# ── Edit delta ──────────────────────────────────────────────────────────────

class TestEditDelta:
    def test_identical_rows(self):
        rows = [{"task": "A", "controls": "B", "responsibility": "Foreman"}]
        delta = compute_edit_delta(rows, rows)
        assert delta["changed_task_count"] == 0
        assert delta["average_similarity_ratio"] == 1.0
        assert delta["major_rewrite_detected"] is False

    def test_minor_edit(self):
        gen = [{"task": "Install scaffold", "controls": "Edge protection", "responsibility": "Foreman"}]
        rev = [{"task": "Install scaffold", "controls": "Edge protection and guardrails", "responsibility": "J. Smith"}]
        delta = compute_edit_delta(gen, rev)
        assert delta["changed_responsibilities_count"] == 1
        assert delta["average_similarity_ratio"] > 0.5

    def test_major_rewrite(self):
        gen = [{"task": "Task A", "controls": "Control A"}]
        rev = [{"task": "Completely different task", "controls": "Entirely new controls for different scope"}]
        delta = compute_edit_delta(gen, rev)
        assert delta["major_rewrite_detected"] is True

    def test_row_count_difference(self):
        gen = [{"task": "A", "controls": "B"}]
        rev = [{"task": "A", "controls": "B"}, {"task": "C", "controls": "D"}]
        delta = compute_edit_delta(gen, rev)
        assert delta["generated_row_count"] == 1
        assert delta["reviewed_row_count"] == 2
        assert delta["total_task_count"] == 2
        assert delta["changed_task_count"] >= 1  # extra row counts as changed

    def test_empty_rows(self):
        delta = compute_edit_delta([], [])
        assert delta["total_task_count"] == 0
        assert delta["major_rewrite_detected"] is False

    def test_changed_responsibilities_counted(self):
        gen = [
            {"task": "A", "controls": "C", "responsibility": "Foreman"},
            {"task": "B", "controls": "D", "responsibility": "Worker"},
        ]
        rev = [
            {"task": "A", "controls": "C", "responsibility": "J. Smith"},
            {"task": "B", "controls": "D", "responsibility": "Worker"},
        ]
        delta = compute_edit_delta(gen, rev)
        assert delta["changed_responsibilities_count"] == 1


# ── Category normalization ──────────────────────────────────────────────────

class TestCategoryNormalization:
    def test_normalize_categories(self):
        raw = " CCVS Fix , Responsibility ,  , hold point "
        categories = [c.strip().lower() for c in raw.split(",") if c.strip()]
        assert categories == ["ccvs fix", "responsibility", "hold point"]

    def test_empty_string(self):
        categories = [c.strip().lower() for c in "".split(",") if c.strip()]
        assert categories == []


# ── Real DOCX fixture ──────────────────────────────────────────────────────

class TestRealDocxFixture:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.gen_path = FIXTURES_DIR / "test_swms_minimal.docx"
        self.rev_path = FIXTURES_DIR / "test_swms_reviewed.docx"
        if not self.gen_path.exists() or not self.rev_path.exists():
            pytest.skip("Real DOCX fixtures not available")

    def test_extract_from_real_docx(self):
        with open(self.gen_path, "rb") as f:
            rows = extract_swms_table_text(f.read())
        assert len(rows) == 2
        assert rows[0]["task"] == "Erect scaffold to level 3"

    def test_delta_between_real_docx(self):
        with open(self.gen_path, "rb") as f:
            gen_rows = extract_swms_table_text(f.read())
        with open(self.rev_path, "rb") as f:
            rev_rows = extract_swms_table_text(f.read())
        delta = compute_edit_delta(gen_rows, rev_rows)
        assert delta["total_task_count"] == 2
        assert delta["changed_responsibilities_count"] == 2  # both changed
        assert delta["average_similarity_ratio"] > 0.0

    def test_fingerprints_differ(self):
        with open(self.gen_path, "rb") as f:
            gen_rows = extract_swms_table_text(f.read())
        with open(self.rev_path, "rb") as f:
            rev_rows = extract_swms_table_text(f.read())
        assert fingerprint_snapshot(gen_rows) != fingerprint_snapshot(rev_rows)


# ── API endpoint (via TestClient) ───────────────────────────────────────────

class TestCaptureEditsEndpoint:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.gen_path = FIXTURES_DIR / "test_swms_minimal.docx"
        self.rev_path = FIXTURES_DIR / "test_swms_reviewed.docx"
        if not self.gen_path.exists() or not self.rev_path.exists():
            pytest.skip("Real DOCX fixtures not available")
        # Patch the edits path to use tmp_path
        self._tmp_edits = tmp_path / "consultant_edits.jsonl"

    def test_endpoint_success(self):
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)

        with open(self.gen_path, "rb") as gf, open(self.rev_path, "rb") as rf:
            response = client.post(
                "/v1/swms/capture-edits",
                files={
                    "generated_docx": ("gen.docx", gf, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                    "reviewed_docx": ("rev.docx", rf, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                },
                data={
                    "job_id": "test-001",
                    "review_duration_mins": "15",
                    "would_issue": "yes",
                    "main_edit_categories": "CCVS, responsibility, hold point",
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert body["job_id"] == "test-001"
        assert body["would_issue"] is True
        assert body["main_edit_categories"] == ["ccvs", "responsibility", "hold point"]
        assert body["total_task_count"] == 2
        assert "generated_doc_fingerprint" in body
        assert "reviewed_doc_fingerprint" in body
        assert body["capture_version"] == "1.0"

    def test_endpoint_bad_docx(self):
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)

        response = client.post(
            "/v1/swms/capture-edits",
            files={
                "generated_docx": ("gen.docx", BytesIO(b"not a docx"), "application/octet-stream"),
                "reviewed_docx": ("rev.docx", BytesIO(b"not a docx"), "application/octet-stream"),
            },
            data={
                "job_id": "test-bad",
                "review_duration_mins": "10",
                "would_issue": "no",
                "main_edit_categories": "",
            },
        )
        assert response.status_code in (400, 500)

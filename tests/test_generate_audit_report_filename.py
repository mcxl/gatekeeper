"""Unit tests for filename composition + folder-id parsing in
``pims/scripts/generate_audit_report.py``.

Covers:
- canonical folder name produces the documented filename
- NN extraction from -RPD-NN / -SDG-NN suffixes
- non-canonical folder name falls back to xlsx audit_date + NN=01
- both docx (.docx) and multi-site (.zip) extensions
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from pims.scripts.generate_audit_report import (
    _compose_output_name,
    _parse_folder_id,
)


# ---------- _parse_folder_id ----------

@pytest.mark.parametrize(
    "folder, expected",
    [
        ("2026-05-22-RPD-03", ("2026-05-22", "RPD", "03")),
        ("2026-05-20-RPD-02", ("2026-05-20", "RPD", "02")),
        ("2026-05-22-RPD-01", ("2026-05-22", "RPD", "01")),
        ("2026-04-11-SDG-12", ("2026-04-11", "SDG", "12")),
    ],
)
def test_parse_folder_id_canonical(folder, expected):
    assert _parse_folder_id(folder) == expected


@pytest.mark.parametrize(
    "folder",
    [
        "2026-05-22-RPD",          # no NN
        "RPD-03",                  # no date
        "2026-05-22-XYZ-03",       # unknown client
        "2026-5-22-RPD-03",        # zero-pad missing
        "2026-05-22-RPD-3",        # NN not zero-padded
        "site-2026-05-22-RPD-03",  # prefix not allowed
        "",
    ],
)
def test_parse_folder_id_noncanonical(folder):
    assert _parse_folder_id(folder) == (None, None, None)


# ---------- _compose_output_name ----------

def test_compose_docx_canonical_folder(tmp_path):
    folder = tmp_path / "2026-05-22-RPD-03"
    folder.mkdir()
    xlsx = folder / "Site_Visit_Report_2026-05-22.xlsx"
    xlsx.write_bytes(b"\x50\x4b")  # not actually parsed here

    name = _compose_output_name(xlsx, ".docx", "2026-05-22")
    assert name == "RPD_SSA_Audit_Report_2026-05-22-03.docx"


def test_compose_docx_canonical_takes_priority_over_xlsx_date(tmp_path):
    """Folder name is authoritative; xlsx audit_date is ignored when folder
    matches canonical form (xlsx may be stale or wrong)."""
    folder = tmp_path / "2026-05-22-RPD-03"
    folder.mkdir()
    xlsx = folder / "Site_Visit_Report_2026-05-22.xlsx"
    xlsx.write_bytes(b"\x50\x4b")

    name = _compose_output_name(xlsx, ".docx", "1999-01-01")
    assert name == "RPD_SSA_Audit_Report_2026-05-22-03.docx"


def test_compose_docx_sdg_client(tmp_path):
    folder = tmp_path / "2026-04-11-SDG-12"
    folder.mkdir()
    xlsx = folder / "Site_Visit_Report_2026-04-11.xlsx"
    xlsx.write_bytes(b"\x50\x4b")

    name = _compose_output_name(xlsx, ".docx", "2026-04-11")
    # Note: filename prefix stays "RPD_SSA_" per current convention;
    # client distinction lives in the folder name only.
    assert name == "RPD_SSA_Audit_Report_2026-04-11-12.docx"


def test_compose_zip_canonical_folder(tmp_path):
    folder = tmp_path / "2026-05-22-RPD-03"
    folder.mkdir()
    xlsx = folder / "Site_Visit_Report_2026-05-22.xlsx"
    xlsx.write_bytes(b"\x50\x4b")

    name = _compose_output_name(xlsx, ".zip", "2026-05-22")
    assert name == "RPD_SSA_Audit_Reports_2026-05-22-03.zip"


def test_compose_noncanonical_folder_falls_back_to_xlsx_date(
    tmp_path, capsys
):
    folder = tmp_path / "some_random_folder"
    folder.mkdir()
    xlsx = folder / "Site_Visit_Report_2026-05-22.xlsx"
    xlsx.write_bytes(b"\x50\x4b")

    name = _compose_output_name(xlsx, ".docx", "2026-05-22")
    assert name == "RPD_SSA_Audit_Report_2026-05-22-01.docx"
    err = capsys.readouterr().err
    assert "does not match" in err
    assert "NN=01" in err


def test_compose_noncanonical_folder_no_xlsx_date_falls_back_to_today(
    tmp_path, capsys
):
    folder = tmp_path / "weird"
    folder.mkdir()
    xlsx = folder / "Site_Visit_Report.xlsx"
    xlsx.write_bytes(b"\x50\x4b")

    name = _compose_output_name(xlsx, ".docx", None)
    today = date.today().isoformat()
    assert name == f"RPD_SSA_Audit_Report_{today}-01.docx"
    err = capsys.readouterr().err
    assert "does not match" in err

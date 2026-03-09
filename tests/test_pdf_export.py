#!/usr/bin/env python3
"""
tests/test_pdf_export.py — Verify PDF export pipeline.

Tests:
  1. SWMS PDF — render + convert, confirm PDF starts with %PDF-
  2. RA PDF — render + convert, confirm PDF starts with %PDF-
  3. Both formats SWMS — render both, confirm docx + pdf both present
  4. Format selector UI — confirm JS state logic (tested via function existence)

Usage:
    python tests/test_pdf_export.py
"""

import os
import sys
import json
import base64

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from io import BytesIO
from core.inference_matrix import infer_to_dict, infer_to_dict_ra
from core.schema import TaskBlock
from renderers.docx_renderer import render_swms_document
from renderers.ra_renderer import render_ra_document
from renderers.pdf_renderer import docx_to_pdf


DESCRIPTION = "concrete grinding silica dust Cranebrook"
META = {
    "project_name": "PDF Export Test",
    "site_address": "218 Vincent Rd Cranebrook NSW 2749",
    "principal_contractor": "mCXI",
    "version": "1.0",
}


def main():
    results = []

    # ── Test 1: SWMS PDF ──────────────────────────────────────
    print("Test 1: SWMS PDF...")
    try:
        inference = infer_to_dict(DESCRIPTION, jurisdiction="AU")
        tasks = [TaskBlock(
            task="Concrete grinding", scope="Silica dust control — ground level",
            risk_pre="H", risk_post="M",
            controls=["Water suppression on grinder", "HEPA vacuum at source", "Exclusion zone 5m"],
            ppe=["P2 respirator (minimum)", "steel-capped footwear", "eye protection"],
            ccvs_code="SIL-H6",
            responsibility={"SUP": "Supervise task", "WKR": "Perform task per SWMS"},
        )]
        docx_bytes = render_swms_document(tasks, META, inference, jurisdiction="AU")
        pdf_bytes = docx_to_pdf(docx_bytes)

        ok_pdf = pdf_bytes[:5] == b"%PDF-"
        ok_size = len(pdf_bytes) > 10000
        ok_filename = True  # Would be SWMS-218-Vincent-...-V01.pdf in frontend

        # Save
        out = os.path.join(_ROOT, "tests", "test_swms_export.pdf")
        with open(out, "wb") as f:
            f.write(pdf_bytes)

        ok = ok_pdf and ok_size
        results.append(("Test 1: SWMS PDF", ok,
            f"PDF header={ok_pdf}, size={len(pdf_bytes)} bytes, saved={out}"))
    except Exception as e:
        results.append(("Test 1: SWMS PDF", False, f"Error: {e}"))

    # ── Test 2: RA PDF ────────────────────────────────────────
    print("Test 2: RA PDF...")
    try:
        ra_inference = infer_to_dict_ra(DESCRIPTION, jurisdiction="AU")
        hazards = ra_inference["hazard_list"]
        ra_meta = {**META, "description": DESCRIPTION}
        ra_docx = render_ra_document(hazards, ra_meta, ra_inference, jurisdiction="AU")
        ra_pdf = docx_to_pdf(ra_docx)

        ok_pdf = ra_pdf[:5] == b"%PDF-"
        ok_size = len(ra_pdf) > 5000

        out = os.path.join(_ROOT, "tests", "test_ra_export.pdf")
        with open(out, "wb") as f:
            f.write(ra_pdf)

        ok = ok_pdf and ok_size
        results.append(("Test 2: RA PDF", ok,
            f"PDF header={ok_pdf}, size={len(ra_pdf)} bytes, saved={out}"))
    except Exception as e:
        results.append(("Test 2: RA PDF", False, f"Error: {e}"))

    # ── Test 3: Both formats SWMS ─────────────────────────────
    print("Test 3: Both formats SWMS...")
    try:
        # Simulate /render/both response
        inference = infer_to_dict(DESCRIPTION, jurisdiction="AU")
        tasks = [TaskBlock(
            task="Concrete grinding", scope="Silica dust control — ground level",
            risk_pre="H", risk_post="M",
            controls=["Water suppression on grinder", "HEPA vacuum at source", "Exclusion zone 5m"],
            ppe=["P2 respirator (minimum)", "steel-capped footwear", "eye protection"],
            ccvs_code="SIL-H6",
            responsibility={"SUP": "Supervise task", "WKR": "Perform task per SWMS"},
        )]
        docx_bytes = render_swms_document(tasks, META, inference, jurisdiction="AU")
        pdf_bytes = docx_to_pdf(docx_bytes)

        # Build response like /render/both returns
        both_response = {
            "docx": base64.b64encode(docx_bytes).decode(),
            "pdf": base64.b64encode(pdf_bytes).decode(),
            "docx_filename": "SWMS-PDF-Export-Test-090326-V01.docx",
            "pdf_filename": "SWMS-PDF-Export-Test-090326-V01.pdf",
        }

        # Verify both are decodable
        decoded_docx = base64.b64decode(both_response["docx"])
        decoded_pdf = base64.b64decode(both_response["pdf"])
        ok_docx = len(decoded_docx) > 10000
        ok_pdf = decoded_pdf[:5] == b"%PDF-"
        ok_keys = all(k in both_response for k in ("docx", "pdf", "docx_filename", "pdf_filename"))

        ok = ok_docx and ok_pdf and ok_keys
        results.append(("Test 3: Both formats SWMS", ok,
            f"docx={len(decoded_docx)}B, pdf={len(decoded_pdf)}B, keys={ok_keys}"))
    except Exception as e:
        results.append(("Test 3: Both formats SWMS", False, f"Error: {e}"))

    # ── Test 4: Format selector UI ────────────────────────────
    print("Test 4: Format selector UI...")
    try:
        dev_html_path = os.path.join(_ROOT, "frontend", "dev.html")
        with open(dev_html_path, "r", encoding="utf-8") as f:
            html = f.read()

        ok_btns = 'id="fmt-docx"' in html and 'id="fmt-pdf"' in html and 'id="fmt-both"' in html
        ok_default = 'fmt-btn active" id="fmt-pdf"' in html
        ok_func = 'function selectFormat(' in html
        ok_label = 'OUTPUT FORMAT' in html
        ok_suffix = "fmtSuffix" in html

        ok = ok_btns and ok_default and ok_func and ok_label and ok_suffix
        results.append(("Test 4: Format selector UI", ok,
            f"buttons={ok_btns}, default_pdf={ok_default}, func={ok_func}, label={ok_label}, suffix={ok_suffix}"))
    except Exception as e:
        results.append(("Test 4: Format selector UI", False, f"Error: {e}"))

    # ── Report ────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("PDF EXPORT — 4 TESTS")
    print("=" * 70)
    all_pass = True
    for label, passed, detail in results:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  {status}  {label}")
        if detail:
            print(f"         {detail}")
    print("=" * 70)

    # Converter info
    from renderers.pdf_renderer import _find_libreoffice
    lo = _find_libreoffice()
    converter = f"LibreOffice ({lo})" if lo else "docx2pdf (Microsoft Word COM)"
    print(f"  PDF converter: {converter}")
    print("=" * 70)
    print(f"RESULT: {'ALL 4 PASSED' if all_pass else 'SOME TESTS FAILED'}")
    print("=" * 70)


if __name__ == "__main__":
    main()

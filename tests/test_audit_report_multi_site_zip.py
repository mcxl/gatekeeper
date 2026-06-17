"""Route-level test for the audit-report multi-site zip path (Stage B
2026-05-13). Single-site returns docx; ≥2 sites returns a zip with one
docx per site.

See docs/plans/CODEX_REVIEW_audit_report_stage_b.md §4a / §B3.
"""
from __future__ import annotations

import asyncio
import zipfile
from io import BytesIO

import pytest


@pytest.fixture
def patched_routes(monkeypatch):
    try:
        from pims import routes
    except ModuleNotFoundError as e:
        pytest.skip(f"pims.routes unavailable: {e}")
    from pims.audit_report_docx import TEMPLATE_PATH
    if not TEMPLATE_PATH.exists():
        pytest.skip(f"canonical template not present: {TEMPLATE_PATH.name}")
    return routes


def _make_fake_build(call_counter):
    """Return a fake build_audit_report_docx that writes a tiny .docx-ish
    payload tagged with the address so we can verify per-site rendering.
    """
    def fake_build(sites_data, **_kw):
        # Stage B contract: only one site per call.
        assert len(sites_data) == 1, (
            f"build_audit_report_docx must be called single-site; "
            f"got {len(sites_data)} sites in one call"
        )
        site = sites_data[0]
        call_counter.append(site.address)
        # Minimal "docx"-shaped payload — bytes are opaque to the route.
        return BytesIO(b"PK\x03\x04tagged:" + site.address.encode("utf-8"))
    return fake_build


def test_multi_site_request_returns_zip_with_one_docx_per_site(
    patched_routes, monkeypatch,
):
    call_counter: list[str] = []

    async def fake_fetch_sites(_ids):
        return [
            {"id": "11111111-1111-1111-1111-111111111111",
             "address_raw": "1 First St", "project_value": 300_000,
             "client_name": "Client A"},
            {"id": "22222222-2222-2222-2222-222222222222",
             "address_raw": "2 Second St", "project_value": 300_000,
             "client_name": "Client A"},
        ]

    async def fake_fetch_obs(_site_id):
        return []

    monkeypatch.setattr(patched_routes, "_fetch_sites_by_id", fake_fetch_sites)
    monkeypatch.setattr(patched_routes, "_fetch_observations_for_site", fake_fetch_obs)
    monkeypatch.setattr(patched_routes, "verify_session_cookie", lambda *_a, **_kw: True)
    monkeypatch.setattr(patched_routes, "RPD_SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(patched_routes, "RPD_SUPABASE_SERVICE_KEY", "test-key")

    from pims import audit_report_docx as arpt
    monkeypatch.setattr(arpt, "build_audit_report_docx", _make_fake_build(call_counter))

    req = patched_routes.AuditReportRequest(
        site_ids=[
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222",
        ],
        summary_text="S",
        prepared_by="J. Auditor",
        inspection_datetime="13 May 2026 09:00 AEST",
    )

    response = asyncio.run(
        patched_routes.generate_audit_report_rpd(req, pims_sess="valid")
    )

    # Two render calls — one per site.
    assert len(call_counter) == 2
    assert call_counter[0] == "1 First St"
    assert call_counter[1] == "2 Second St"

    # Response is zip (Content-Type + Content-Disposition).
    assert response.media_type == "application/zip"
    assert "filename=" in response.headers["Content-Disposition"]
    assert ".zip" in response.headers["Content-Disposition"]

    # Body is a real zip with two entries. StreamingResponse exposes
    # body_iterator which is the underlying BytesIO for our case.
    async def _collect():
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode("utf-8"))
        return b"".join(chunks)
    try:
        body = asyncio.run(_collect())
    except TypeError:
        # body_iterator is a sync iterable
        chunks = []
        for chunk in response.body_iterator:
            chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode("utf-8"))
        body = b"".join(chunks)
    zf = zipfile.ZipFile(BytesIO(body))
    names = zf.namelist()
    assert len(names) == 2
    payload_addresses = []
    for name in names:
        payload = zf.read(name)
        assert payload.startswith(b"PK\x03\x04tagged:")
        payload_addresses.append(payload.split(b"tagged:", 1)[1].decode("utf-8"))
    assert sorted(payload_addresses) == ["1 First St", "2 Second St"]


def test_single_site_request_returns_single_docx(patched_routes, monkeypatch):
    """Single-site path still returns docx (not zip)."""
    call_counter: list[str] = []

    async def fake_fetch_sites(_ids):
        return [{
            "id": "11111111-1111-1111-1111-111111111111",
            "address_raw": "1 First St", "project_value": 300_000,
            "client_name": "Client A",
        }]

    async def fake_fetch_obs(_site_id):
        return []

    monkeypatch.setattr(patched_routes, "_fetch_sites_by_id", fake_fetch_sites)
    monkeypatch.setattr(patched_routes, "_fetch_observations_for_site", fake_fetch_obs)
    monkeypatch.setattr(patched_routes, "verify_session_cookie", lambda *_a, **_kw: True)
    monkeypatch.setattr(patched_routes, "RPD_SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(patched_routes, "RPD_SUPABASE_SERVICE_KEY", "test-key")
    from pims import audit_report_docx as arpt
    monkeypatch.setattr(arpt, "build_audit_report_docx", _make_fake_build(call_counter))

    req = patched_routes.AuditReportRequest(
        site_ids=["11111111-1111-1111-1111-111111111111"],
        summary_text="S",
        prepared_by="J. Auditor",
        inspection_datetime="13 May 2026 09:00 AEST",
    )

    response = asyncio.run(
        patched_routes.generate_audit_report_rpd(req, pims_sess="valid")
    )

    assert len(call_counter) == 1
    expected_media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert response.media_type == expected_media_type
    assert ".docx" in response.headers["Content-Disposition"]
    assert ".zip" not in response.headers["Content-Disposition"]

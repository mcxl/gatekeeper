"""Route-level tests for the audit-report endpoint.

These tests guard against schema drift between PostgREST ?select=... values
and the pims_observations schema in pims/pims_migration.sql. A mismatched
column name causes Supabase to 400, which bubbled up as a 500 in production
(Codex P4 — live alert on pilot site 1208 Pacific Highway Pymble).
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

import pytest


# --- Helpers ----------------------------------------------------------------

_PIMS_MIGRATION = Path(__file__).resolve().parent.parent / "pims" / "pims_migration.sql"


def _parse_pims_observations_columns() -> set[str]:
    """Extract column names from the pims_observations CREATE TABLE block.

    Returns the set of column identifiers so we can assert every select-list
    column exists in the schema. Implementation is deliberately dumb: match
    identifier at start-of-line inside the CREATE TABLE ... pims_observations
    (...) block.
    """
    src = _PIMS_MIGRATION.read_text(encoding="utf-8")
    m = re.search(
        r"CREATE TABLE IF NOT EXISTS public\.pims_observations\s*\((.*?)\);",
        src, re.DOTALL,
    )
    if not m:
        raise AssertionError("pims_observations CREATE TABLE block not found")
    body = m.group(1)
    cols: set[str] = set()
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--") or stripped.startswith("CHECK"):
            continue
        # Column lines start with an identifier followed by whitespace and a type.
        t = re.match(r"([a-z_][a-z0-9_]*)\s+[A-Za-z]", stripped)
        if t:
            cols.add(t.group(1))
    return cols


@pytest.fixture
def patched_routes(monkeypatch):
    try:
        from pims import routes
    except ModuleNotFoundError as e:
        pytest.skip(f"pims.routes unavailable: {e}")
    return routes


# --- Schema tests -----------------------------------------------------------

def test_observation_select_columns_all_exist_in_schema(patched_routes):
    """Every column named in OBSERVATION_SELECT_COLUMNS must exist in
    pims_observations — otherwise PostgREST returns 400 at request time.

    This is the regression guard for Codex P4 (photo_id -> photo_url rename)."""
    schema_cols = _parse_pims_observations_columns()
    select_cols = set(patched_routes.OBSERVATION_SELECT_COLUMNS.split(","))
    missing = select_cols - schema_cols
    assert not missing, (
        f"Columns in _fetch_observations_for_site select not in "
        f"pims_observations schema: {missing}. "
        f"Schema has: {sorted(schema_cols)}"
    )


def test_observation_select_includes_photo_url_not_photo_id(patched_routes):
    """Pin the specific fix: the select list uses photo_url (real column),
    not photo_id (does not exist)."""
    cols = patched_routes.OBSERVATION_SELECT_COLUMNS
    assert "photo_url" in cols
    assert "photo_id" not in cols


def test_observation_select_covers_renderer_requirements(patched_routes):
    """Every column the renderer reads via observation.get(...) must be
    in the select list. Drift here causes silent data-loss in the .docx."""
    required = {
        "id", "seq_no", "site_address",
        "observation_text", "observation_text_enriched",
        "conformance_status", "ccvs_code", "ccvs_category",
        "action_required", "action_description",
        "responsible", "due_category",
        "legal_reference", "filename", "photo_url",
    }
    cols = set(patched_routes.OBSERVATION_SELECT_COLUMNS.split(","))
    missing = required - cols
    assert not missing, f"Renderer-required columns missing from select: {missing}"


# --- End-to-end call: captured params echo the constant ---------------------

class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _CaptureClient:
    last_params: dict | None = None

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, headers=None, params=None):
        _CaptureClient.last_params = dict(params or {})
        return _FakeResp([])


def test_request_model_rejects_missing_prepared_by(patched_routes):
    """Pydantic 422: prepared_by is required and must be non-empty."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        patched_routes.AuditReportRequest(
            site_ids=["11111111-1111-1111-1111-111111111111"],
            inspection_datetime="23 Apr 2026 09:00 AEDT",
        )
    with pytest.raises(ValidationError):
        patched_routes.AuditReportRequest(
            site_ids=["11111111-1111-1111-1111-111111111111"],
            prepared_by="",
            inspection_datetime="23 Apr 2026 09:00 AEDT",
        )


def test_request_model_rejects_missing_inspection_datetime(patched_routes):
    """Pydantic 422: inspection_datetime is required and must be non-empty."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        patched_routes.AuditReportRequest(
            site_ids=["11111111-1111-1111-1111-111111111111"],
            prepared_by="J. Auditor",
        )
    with pytest.raises(ValidationError):
        patched_routes.AuditReportRequest(
            site_ids=["11111111-1111-1111-1111-111111111111"],
            prepared_by="J. Auditor",
            inspection_datetime="",
        )


def test_request_happy_path_threads_fields_into_site_data(patched_routes, monkeypatch):
    """Happy path: prepared_by and inspection_datetime from the request
    reach every constructed SiteData."""
    captured: dict = {}

    async def fake_fetch_sites(_ids):
        return [
            {"id": "11111111-1111-1111-1111-111111111111",
             "address_raw": "1 A St", "project_value": 300_000,
             "client_name": "Client A"},
            {"id": "22222222-2222-2222-2222-222222222222",
             "address_raw": "2 B St", "project_value": 300_000,
             "client_name": "Client A"},
        ]

    async def fake_fetch_obs(_site_id):
        return []

    def fake_build(sites_data, **_kw):
        captured["sites"] = list(sites_data)
        from io import BytesIO
        return BytesIO(b"PK\x03\x04")

    monkeypatch.setattr(patched_routes, "_fetch_sites_by_id", fake_fetch_sites)
    monkeypatch.setattr(patched_routes, "_fetch_observations_for_site", fake_fetch_obs)
    monkeypatch.setattr(patched_routes, "verify_session_cookie", lambda _c: True)
    monkeypatch.setattr(patched_routes, "RPD_SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(patched_routes, "RPD_SUPABASE_SERVICE_KEY", "test-key")
    # Template + xlsx existence checks read from disk; point them at real files.
    from pims import audit_report_docx as arpt
    monkeypatch.setattr(arpt, "TEMPLATE_PATH", arpt.TEMPLATE_PATH)  # no-op but explicit
    # Patch build_audit_report_docx at its import site in pims.routes by
    # intercepting the inline `from pims.audit_report_docx import ...` — we
    # do that by replacing the builder on the source module before import.
    monkeypatch.setattr(arpt, "build_audit_report_docx", fake_build)

    req = patched_routes.AuditReportRequest(
        site_ids=[
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222",
        ],
        summary_text="Summary.",
        prepared_by="J. Auditor",
        inspection_datetime="23 Apr 2026 09:00 AEDT",
    )

    asyncio.run(patched_routes.generate_audit_report_rpd(req, pims_sess="valid"))

    assert "sites" in captured
    assert len(captured["sites"]) == 2
    for s in captured["sites"]:
        assert s.prepared_by == "J. Auditor"
        assert s.inspection_datetime == "23 Apr 2026 09:00 AEDT"


def test_fetch_sends_constant_select_to_supabase(patched_routes, monkeypatch):
    """Belt-and-braces: the outgoing request uses the constant verbatim,
    so the schema assertions above actually guard the live call."""
    monkeypatch.setattr(patched_routes, "RPD_SUPABASE_URL",
                        "https://example.supabase.co")
    monkeypatch.setattr(patched_routes, "RPD_SUPABASE_SERVICE_KEY", "test-key")
    monkeypatch.setattr(patched_routes.httpx, "AsyncClient", _CaptureClient)
    _CaptureClient.last_params = None

    asyncio.run(patched_routes._fetch_observations_for_site(
        "11111111-1111-1111-1111-111111111111"))

    assert _CaptureClient.last_params is not None
    assert _CaptureClient.last_params["select"] == patched_routes.OBSERVATION_SELECT_COLUMNS

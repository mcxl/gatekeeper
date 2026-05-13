"""One-off: render audit-report v8 (Stage B+ matcher) against live
Supabase data for 96-98 Hampden Rd Russel Lea, and save to the
SSA-evidence folder alongside v2-v5."""
from __future__ import annotations

import asyncio
import os
import shutil
import sys
from pathlib import Path

import httpx

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

# Load .env (mirrors pattern used by pims/scripts/generate_audit_report.py).
_env = _REPO / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _v = _line.split("=", 1)
        _k = _k.strip()
        _v = _v.strip().strip('"').strip("'")
        if _k and _k not in os.environ:
            os.environ[_k] = _v

import logging  # noqa: E402

from pims.audit_report_docx import SiteData, build_audit_report_docx, PIMS_DIR  # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(levelname)s:%(message)s")
log = logging.getLogger("v8")

RPD_URL = os.environ.get("RPD_SUPABASE_URL") or os.environ.get("SUPABASE_URL") or "https://nebdpofqglfyfyqqodni.supabase.co"
RPD_KEY = (
    os.environ.get("RPD_SUPABASE_SERVICE_KEY")
    or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    or os.environ.get("SUPABASE_SERVICE_KEY")
)
SITE_ID = "98896ff0-996b-44d6-b878-66c4f301226d"

if not RPD_KEY:
    print("ERROR: no Supabase service key found in env (.env or os.environ).")
    print("Tried: RPD_SUPABASE_SERVICE_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_SERVICE_KEY")
    sys.exit(2)


async def fetch():
    cols = (
        "id,seq_no,site_address,observation_text,observation_text_enriched,"
        "conformance_status,ccvs_code,ccvs_category,action_required,"
        "action_description,responsible,due_category,legal_reference,"
        "filename,photo_url,observation_date,audit_id,submitted_by,prepared_by"
    )
    headers = {
        "apikey": RPD_KEY,
        "Authorization": f"Bearer {RPD_KEY}",
        "Prefer": "return=representation",
    }
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.get(
            f"{RPD_URL}/rest/v1/pims_observations",
            headers=headers,
            params={
                "select": cols,
                "site_id": f"eq.{SITE_ID}",
                "review_status": "eq.Approved",
                "staging": "eq.false",
                "order": "observation_date.asc",
            },
        )
        r.raise_for_status()
        obs = r.json()
    open_actions = [o for o in obs if o.get("action_required")]
    # Stage B fetches photos for ALL observations because the renderer
    # embeds them in per-criterion checklist photo cells, not just
    # the Open Actions Register.
    photo_bytes_by_id: dict[str, bytes] = {}
    async with httpx.AsyncClient(timeout=60) as c:
        for o in obs:
            url = o.get("photo_url")
            if not url:
                continue
            try:
                rr = await c.get(url)
                if rr.status_code == 200:
                    photo_bytes_by_id[str(o["id"])] = rr.content
            except Exception as e:
                log.warning("photo fetch failed for %s: %s", o.get("id"), e)
    return obs, open_actions, photo_bytes_by_id


obs, open_actions, photo_bytes_by_id = asyncio.run(fetch())

# Track unmatched count for visibility.
import pims.audit_report_docx as arpt  # noqa: E402

_unmatched: list[str] = []
_orig = arpt.log.warning


def _track(msg, *a, **kw):
    if isinstance(msg, str) and "unmatched obs" in msg:
        _unmatched.append(str(a[0]) if a else "?")
    _orig(msg, *a, **kw)


arpt.log.warning = _track

from collections import Counter  # noqa: E402

print(f"Fetched {len(obs)} observations, {len(open_actions)} open actions, {len(photo_bytes_by_id)} photos")
print(f"Status distribution: {Counter(o['conformance_status'] for o in obs)}")

site = SiteData(
    address="96-98 Hampden Rd Russel Lea",
    project_value=250_000,
    client="Robertson's Remedial and Painting Pty Ltd",
    prepared_by="Alan Richardson",
    inspection_datetime="12 May 2026 07:30 AEST",
    observations=obs,
    open_actions=open_actions,
    open_action_photo_bytes_by_obs_id=photo_bytes_by_id,
    report_issue_date="2026-05-13",
)
buf = build_audit_report_docx([site], checklist_xlsx_path=PIMS_DIR / "audit_checklist.xlsx")
local_out = PIMS_DIR / "RPD_SSA_v8_LIVE_96-98_Hampden.docx"
local_out.write_bytes(buf.read())
print(f"WROTE {local_out} ({local_out.stat().st_size:,} bytes)")
print(f"Unmatched obs: {len(_unmatched)}/{len(obs)}  match-rate: {(len(obs)-len(_unmatched))/len(obs)*100:.1f}%")

# Copy to SSA-evidence
ssa_dir = Path(r"G:\My Drive\alan_mcxico\SSA-evidence\2026-05-12-RPD-01")
if ssa_dir.exists():
    target = ssa_dir / "Audit_Report_96-98_Hampden_Rd_Russel_Lea_v8.docx"
    shutil.copy2(local_out, target)
    print(f"COPIED to {target}")
else:
    print(f"SSA-evidence folder not found: {ssa_dir}")

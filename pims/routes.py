"""
pims/routes.py — PIMS observation endpoints for Safe Method / Gatekeeper

Routes:
    POST /pims/observation/rpd      — RPD (Robertson's Remedial and Painting)
    POST /pims/observation/sdgroup  — SD Group (future)

Auth: X-PIMS-Token header checked against env var per client.

Each endpoint:
    1. Validates token
    2. Saves raw observation to Supabase immediately (with auto seq_no)
    3. Returns 200 to client instantly
    4. Enriches via Claude Haiku in background
    5. Uploads photo to Supabase Storage in background if photo_base64 provided
"""

from __future__ import annotations

import asyncio
import base64
import hmac
import json
import logging
import os
import urllib.parse
import uuid as _uuid_mod
from datetime import date, datetime, timezone
from io import BytesIO
from typing import Optional

import httpx
import openpyxl
from docx import Document as DocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from fastapi import APIRouter, BackgroundTasks, Cookie, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from PIL import Image as PILImage
from pydantic import BaseModel, Field

from api.pims_auth import COOKIE_NAME, verify_session_cookie

log = logging.getLogger(__name__)

router = APIRouter(prefix="/pims", tags=["pims"])

# ── Environment ────────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# RPD Supabase
RPD_SUPABASE_URL         = os.getenv("RPD_SUPABASE_URL", "")
RPD_SUPABASE_KEY         = os.getenv("RPD_SUPABASE_ANON_KEY", "")
RPD_SUPABASE_SERVICE_KEY = os.getenv("RPD_SUPABASE_SERVICE_KEY", "")
RPD_PIMS_TOKEN           = os.getenv("PIMS_RPD_TOKEN", "")

# SD Group Supabase (future)
SDG_SUPABASE_URL         = os.getenv("SDG_SUPABASE_URL", "")
SDG_SUPABASE_KEY         = os.getenv("SDG_SUPABASE_ANON_KEY", "")
SDG_SUPABASE_SERVICE_KEY = os.getenv("SDG_SUPABASE_SERVICE_KEY", "")
SDG_PIMS_TOKEN           = os.getenv("PIMS_SDG_TOKEN", "")

MAX_ROWS = 100
IMAGE_TIMEOUT = httpx.Timeout(5.0, connect=3.0, read=5.0)
# 5.0 = default for write + pool; connect and read set explicitly.
IMAGE_CONCURRENCY = 5
MAX_IMG_BYTES = 10 * 1024 * 1024  # 10 MB hard cap per image
MAX_UPLOAD_FILE_BYTES = 5 * 1024 * 1024
MAX_UPLOAD_ROWS = 500
_ALLOWED_IMG_HOST = "nebdpofqglfyfyqqodni.supabase.co"
_ALLOWED_IMG_PREFIX = "/storage/v1/object/public/pims-photos/"

VALID_CONFORMANCE_STATUS = {
    "ncr": "NCR",
    "compliant": "Compliant",
    "conditional": "Conditional",
    "info": "Info",
}

VALID_CCVS = {
    "WAH-H6", "WAH-H9",
    "IRA-H6", "IRA-H9",
    "SIL-H6", "SIL-H9",
    "STR-H6", "STR-H9",
    "MOB-H6", "MOB-M4",
    "CHM-M3", "CHM-H6",
    "ENE-M4", "ENE-H6",
    "SYS-L1", "SYS-L2",
    "SYS-M3", "SYS-M4",
    "SYS-H6",
}

CCVS_CATEGORY_BY_PREFIX = {
    "WAH": "Working at Height",
    "IRA": "Industrial Rope Access",
    "SIL": "Silica",
    "STR": "Structural",
    "MOB": "Mobile Plant",
    "CHM": "Chemicals",
    "ENE": "Energy",
    "SYS": "Systems",
}

STAGING_COPY_FIELDS = [
    "audit_id", "seq_no", "observation_date", "observation_text",
    "filename", "photo_url", "submitted_by", "device_info",
    "enriched", "enriched_at", "conformance_status", "ccvs_code",
    "ccvs_category", "ccvs_confidence", "action_required",
    "action_description", "responsible", "due_category", "monitoring_note",
    "observation_text_enriched", "legal_reference",
]

# ── Request / Response models ──────────────────────────────────────────────────

class ObservationRequest(BaseModel):
    audit_ref:        str = Field(..., max_length=100, pattern=r"^[A-Za-z0-9_\-]+$")
    seq_no:           Optional[int] = None
    observation_text: str = Field(..., max_length=2000)
    observation_date: Optional[str] = None
    photo_url:        Optional[str] = None
    filename:         Optional[str] = None
    photo_base64:     Optional[str] = Field(default=None, max_length=20_000_000)
    submitted_by:     Optional[str] = None
    device_info:      Optional[str] = None

class ObservationResponse(BaseModel):
    id:                 str
    seq_no:             Optional[int]
    conformance_status: Optional[str]
    ccvs_code:          Optional[str]
    ccvs_category:      Optional[str]
    ccvs_confidence:    Optional[str]
    action_required:    bool
    action_description: Optional[str]
    monitoring_note:    Optional[str]
    review_status:      str


class StagingExportRequest(BaseModel):
    ids: list[str]

# ── Haiku enrichment ───────────────────────────────────────────────────────────

ENRICHMENT_SYSTEM = """You are a WHS compliance classifier for Australian construction.

Given a field observation from a site safety audit, return a JSON object with:

{
  "conformance_status": "Compliant" | "Conditional" | "NCR" | "Info",
  "ccvs_code": one of the approved codes below or null,
  "ccvs_category": category name or null,
  "ccvs_confidence": "High" | "Medium" | "Low",
  "action_required": true | false,
  "action_description": short plain-English action required or null,
  "responsible": "PC" | "Subcontractor" | "Inspector" | null,
  "due_category": "Immediate" | "Next audit" | "Ongoing" | "N/A",
  "monitoring_note": what to verify at next audit or null,
  "observation_text_enriched": a professional rewrite of the observation in plain Australian English, suitable for a formal WHS audit report. 2-3 sentences. Must include the hazard, the finding, and the implication,
  "legal_reference": the single most relevant NSW legal reference — WHS Act 2011, WHS Regulation 2017 clause, or SafeWork NSW Code of Practice section. Format: "WHS Regulation 2017 cl 54" or "SafeWork NSW COP: Managing Risks of Falls at Workplaces s3.2". Null if Info status
}

APPROVED CCVS CODES (use only these exact strings):
WAH-H6, WAH-H9 — working at height (scaffold, EWP, rope access, ladders)
IRA-H6, IRA-H9 — industrial rope access
SIL-H6, SIL-H9 — silica dust (grinding, cutting, jackhammering, drilling)
STR-H6, STR-H9 — structural (concrete breakout, balustrade, render, crack injection)
MOB-H6, MOB-M4 — mobile plant and traffic management
CHM-M3, CHM-H6 — hazardous chemicals (paints, solvents, epoxies, waterproofing)
ENE-M4, ENE-H6 — energy / manual handling
SYS-L1, SYS-L2 — systems (induction, sign-in, daily register)
SYS-M3, SYS-M4 — systems (SWMS, toolbox talks, permits, inspections)
SYS-H6         — systems (emergency response, rescue plans)

RULES:
- If observation mentions compliance, assign "Compliant" status
- If observation mentions "ACTION REQUIRED" or a deficiency, assign "NCR"
- If observation is compliant but has outstanding verifications, assign "Conditional"
- If observation is a header, context note, or photo label only, assign "Info" with null ccvs_code
- ccvs_confidence: High = clear match, Medium = reasonable match, Low = uncertain
- action_required must be true for NCR and Conditional
RPD SWMS REFERENCE (use these when assigning ccvs_code and legal_reference):

WAH — Working at Height (WAH-H6, WAH-H9):
  SWMS: SCAFFOLD v9.0, SWING-STAGE v9.0, EWP v2.0, PAINTING-WORKS v9.0 s3.1-3.4
  Controls: Full body harness AS/NZS 1891.1; guardrails top and mid-rail; green tag after
    competent-person inspection; scaffold inspected ≤30-day intervals and after >60 km/h wind;
    EWP operator EWPA Yellow Card sighted; PSV current and on site before each shift
  Legal: WHS Regulation 2017 cl 228–244 (HRCW falls); SafeWork NSW COP: Managing Risks of Falls at Workplaces

EWP — Elevated Work Platform (WAH-H6):
  SWMS: EWP v2.0 Steps 1.4, 1.6, 1.8, 1.10; PAINTING-WORKS v9.0 s3.4
  Controls: PSV on site; EWPA Yellow Card recorded; pre-start checklist signed before each shift;
    harness connected at all times on platform; rescue plan for incapacitated operator at height
  Legal: WHS Regulation 2017 cl 223–226; SafeWork NSW COP: Plant and Structures

SILICA — Silica Dust (SIL-H6, SIL-H9):
  SWMS: REMEDIAL-WORKS v9.0 Steps 10, 11, 13, 14, 17, 18, 19, 24; PAINTING-WORKS v9.0 s2.8, 2.9
  Controls: Wet suppression OR on-tool HEPA extraction before any silica work commences;
    P2 respirator AS/NZS 1716 fit-checked and worn; exclusion zone for adjacent workers and residents;
    balcony dust seal in place for occupied units; no dry grinding or cutting without controls
  Legal: WHS Regulation 2017 cl 407; SafeWork NSW COP: Managing Risks of Silica s2.3

CHEMICALS — Hazardous Chemicals (CHM-M3, CHM-H6):
  SWMS: REMEDIAL-WORKS v9.0 Step 20; PAINTING-WORKS v9.0 s2.10; PAINTING-WORKS v9.0 s2.6 (lead)
  Controls: SDS on site for all products; chemical-resistant gloves; P2/P3 respirator for
    isocyanates and solvent-based products; ventilation before applying VOC products;
    spill kit 110% capacity of largest container; flammable storage compliant
  Legal: WHS Regulation 2017 cl 332–361; SafeWork NSW COP: Managing Risks of Hazardous Chemicals

SWING STAGE — Suspended Scaffold (WAH-H6, WAH-H9):
  SWMS: SWING-STAGE v9.0 Steps 2.1–2.10
  Controls: Engineer-certified design on site; two-rope system (working + safety independently anchored);
    rope grab adjusted per worker before descending; anemometer in use — suspend >40 km/h;
    emergency lowering operable from ground; suspension trauma rescue plan rehearsed
  Legal: WHS Regulation 2017 cl 228–244; AS/NZS 1576 (suspended scaffolding)

- Return ONLY valid JSON. No commentary, no markdown fences."""


async def enrich_observation(observation_text: str) -> dict:
    """Call Claude Haiku to classify and enrich a PIMS observation."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key":         ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type":      "application/json",
                },
                json={
                    "model":      "claude-haiku-4-5",
                    "max_tokens": 768,
                    "system":     ENRICHMENT_SYSTEM,
                    "messages": [
                        {"role": "user", "content": f"Observation: {observation_text}"}
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["content"][0]["text"].strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                log.warning(f"Haiku JSON parse failed: {e} | raw: {text[:200]}")
                return {}
    except Exception as e:
        log.error(f"Haiku enrichment failed: {type(e).__name__}: {e}")
        raise


async def enrich_and_update(
    supabase_url: str,
    supabase_service_key: str,
    record_id: str,
    observation_text: str,
) -> None:
    """Background task — enrich observation and patch the staging record."""
    try:
        enrichment = await enrich_observation(observation_text)
    except Exception as e:
        log.error(f"Background enrichment failed for {record_id}: {e}")
        return

    headers = _supabase_headers(supabase_service_key, prefer="return=minimal")
    patch = {
        "conformance_status":        enrichment.get("conformance_status"),
        "ccvs_code":                 enrichment.get("ccvs_code"),
        "ccvs_category":             enrichment.get("ccvs_category"),
        "ccvs_confidence":           enrichment.get("ccvs_confidence"),
        "action_required":           enrichment.get("action_required", False),
        "action_description":        enrichment.get("action_description"),
        "responsible":               enrichment.get("responsible"),
        "due_category":              enrichment.get("due_category", "N/A"),
        "monitoring_note":           enrichment.get("monitoring_note"),
        "observation_text_enriched": enrichment.get("observation_text_enriched"),
        "legal_reference":           enrichment.get("legal_reference"),
        "enriched":                  True,
        "enriched_at":               datetime.now(timezone.utc).isoformat(),
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.patch(
                f"{supabase_url}/rest/v1/pims_staging",
                headers=headers,
                params={"id": f"eq.{record_id}"},
                json=patch,
            )
            if r.status_code not in (200, 204):
                log.error(f"Background patch failed {r.status_code}: {r.text}")
            else:
                log.info(f"Background enrichment complete for {record_id}")
    except Exception as e:
        log.error(f"Background patch exception for {record_id}: {e}")


async def upload_photo_background(
    supabase_url: str,
    supabase_service_key: str,
    record_id: str,
    filename: str,
    photo_base64: str,
    audit_ref: str,
) -> None:
    """Background task — decode base64 photo and upload to Supabase Storage."""
    try:
        photo_bytes = base64.b64decode(photo_base64)
    except Exception as e:
        log.error(f"Base64 decode failed for {record_id}: {e}")
        return

    storage_path = f"{audit_ref}/{filename}"
    storage_url  = f"{supabase_url}/storage/v1/object/pims-photos/{storage_path}"
    public_url   = f"{supabase_url}/storage/v1/object/public/pims-photos/{storage_path}"

    headers = {
        "apikey":        supabase_service_key,
        "Authorization": f"Bearer {supabase_service_key}",
        "Content-Type":  "image/jpeg",
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.put(storage_url, headers=headers, content=photo_bytes)
            if r.status_code not in (200, 201):
                log.error(f"Photo upload failed {r.status_code}: {r.text}")
                return
            log.info(f"Photo uploaded for {record_id}: {storage_path}")

            # Patch staging record with photo_url
            patch_headers = _supabase_headers(supabase_service_key, prefer="return=minimal")
            r2 = await client.patch(
                f"{supabase_url}/rest/v1/pims_staging",
                headers=patch_headers,
                params={"id": f"eq.{record_id}"},
                json={"photo_url": public_url},
            )
            if r2.status_code not in (200, 204):
                log.error(f"photo_url patch failed {r2.status_code}: {r2.text}")
            else:
                log.info(f"photo_url updated for {record_id}")
    except Exception as e:
        log.error(f"Photo upload exception for {record_id}: {e}")


# ── Supabase helpers ───────────────────────────────────────────────────────────

def _supabase_headers(supabase_key: str, prefer: str = "return=representation") -> dict:
    """Build standard Supabase REST headers."""
    return {
        "apikey":        supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type":  "application/json",
        "Prefer":        prefer,
    }


async def get_or_create_audit(
    supabase_url: str,
    supabase_service_key: str,
    audit_ref: str,
) -> str:
    """Return existing audit id or create via upsert (race-safe)."""
    today = date.today().isoformat()
    parts = audit_ref.split("_", 1)
    audit_date = parts[0] if len(parts[0]) == 10 else today
    site_name  = parts[1].replace("_", " ") if len(parts) > 1 else audit_ref

    headers = _supabase_headers(
        supabase_service_key,
        prefer="return=representation,resolution=merge-duplicates",
    )
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{supabase_url}/rest/v1/pims_audits",
            headers=headers,
            params={"on_conflict": "audit_ref"},
            json={
                "audit_ref":  audit_ref,
                "site_name":  site_name,
                "audit_date": audit_date,
                "auditor":    "Alan Richardson",
            },
        )
        r.raise_for_status()
        return r.json()[0]["id"]


async def next_seq_no(
    supabase_url: str,
    supabase_service_key: str,
    audit_id: str,
) -> int:
    """Return max(seq_no) + 1 for the given audit, or 1 if none exist."""
    headers = _supabase_headers(supabase_service_key, prefer="return=representation")
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"{supabase_url}/rest/v1/pims_staging",
            headers=headers,
            params={
                "audit_id": f"eq.{audit_id}",
                "select":   "seq_no",
                "order":    "seq_no.desc",
                "limit":    "1",
            },
        )
        r.raise_for_status()
        rows = r.json()
        if rows and rows[0].get("seq_no") is not None:
            return rows[0]["seq_no"] + 1
        return 1


async def insert_staging(
    supabase_url: str,
    supabase_service_key: str,
    audit_id: str,
    request: ObservationRequest,
    enrichment: dict,
    seq_no: int,
) -> str:
    """Insert observation into pims_staging. Returns record id."""
    headers = _supabase_headers(supabase_service_key)
    current_seq_no = seq_no
    record = {
        "audit_id":           audit_id,
        "seq_no":             current_seq_no,
        "photo_url":          request.photo_url,
        "filename":           request.filename,
        "observation_date":   (request.observation_date or "")[:10] or date.today().isoformat(),
        "observation_text":   request.observation_text,
        "submitted_by":       request.submitted_by,
        "device_info":        request.device_info,
        "enriched":           False,
        "enriched_at":        None,
        "conformance_status": enrichment.get("conformance_status"),
        "ccvs_code":          enrichment.get("ccvs_code"),
        "ccvs_category":      enrichment.get("ccvs_category"),
        "ccvs_confidence":    enrichment.get("ccvs_confidence"),
        "action_required":    enrichment.get("action_required", False),
        "action_description": enrichment.get("action_description"),
        "responsible":        enrichment.get("responsible"),
        "due_category":       enrichment.get("due_category", "N/A"),
        "monitoring_note":    enrichment.get("monitoring_note"),
        "observation_text_enriched": enrichment.get("observation_text_enriched"),
        "legal_reference":           enrichment.get("legal_reference"),
        "review_status":      "Pending",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        for _attempt in range(3):
            r = await client.post(
                f"{supabase_url}/rest/v1/pims_staging",
                headers=headers,
                json=record,
            )
            if r.status_code in (200, 201):
                return r.json()[0]["id"]
            if r.status_code == 409:
                current_seq_no = await next_seq_no(
                    supabase_url,
                    supabase_service_key,
                    audit_id,
                )
                record["seq_no"] = current_seq_no
                continue
            log.error(f"Supabase staging insert error {r.status_code}: {r.text}")
            r.raise_for_status()
        raise HTTPException(
            status_code=409,
            detail="seq_no conflict — could not allocate unique sequence number.",
        )


# ── Route handlers ─────────────────────────────────────────────────────────────

async def _handle_observation(
    request: ObservationRequest,
    supabase_url: str,
    supabase_service_key: str,
    expected_token: str,
    token: str,
    background_tasks: BackgroundTasks,
) -> ObservationResponse:
    """Shared handler for all client observation endpoints."""
    if not expected_token or not hmac.compare_digest(token, expected_token):
        raise HTTPException(status_code=401, detail="Invalid PIMS token")

    if not supabase_url:
        raise HTTPException(status_code=503, detail="Supabase URL not configured")

    if not supabase_service_key:
        raise HTTPException(status_code=503, detail="Supabase service key not configured")
    if request.photo_base64 and len(request.photo_base64) > 20_000_000:
        raise HTTPException(status_code=413, detail="photo_base64 exceeds maximum allowed size.")

    empty_enrichment = {
        "conformance_status":        None,
        "ccvs_code":                 None,
        "ccvs_category":             None,
        "ccvs_confidence":           None,
        "action_required":           False,
        "action_description":        None,
        "responsible":               None,
        "due_category":              "N/A",
        "monitoring_note":           None,
        "observation_text_enriched": None,
        "legal_reference":           None,
    }

    try:
        audit_id = await get_or_create_audit(supabase_url, supabase_service_key, request.audit_ref)
        seq_no = request.seq_no if request.seq_no is not None else await next_seq_no(supabase_url, supabase_service_key, audit_id)
        record_id = await insert_staging(supabase_url, supabase_service_key, audit_id, request, empty_enrichment, seq_no)
    except Exception as e:
        log.error(f"Supabase insert failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to save observation")

    # Enrich in background
    background_tasks.add_task(
        enrich_and_update,
        supabase_url=supabase_url,
        supabase_service_key=supabase_service_key,
        record_id=record_id,
        observation_text=request.observation_text,
    )

    # Upload photo in background if base64 provided
    if request.photo_base64 and request.filename:
        background_tasks.add_task(
            upload_photo_background,
            supabase_url=supabase_url,
            supabase_service_key=supabase_service_key,
            record_id=record_id,
            filename=request.filename,
            photo_base64=request.photo_base64,
            audit_ref=request.audit_ref,
        )

    return ObservationResponse(
        id=                 record_id,
        seq_no=             seq_no,
        conformance_status= "Pending",
        ccvs_code=          None,
        ccvs_category=      None,
        ccvs_confidence=    None,
        action_required=    False,
        action_description= None,
        monitoring_note=    "Enrichment running in background",
        review_status=      "Pending",
    )


@router.post("/observation/rpd", response_model=ObservationResponse)
async def rpd_observation(
    request: Request,
    payload: ObservationRequest,
    background_tasks: BackgroundTasks,
    x_pims_token: str = Header(..., alias="X-PIMS-Token"),
):
    """Receive a field observation for RPD and enrich with CCVS codes."""
    return await _handle_observation(
        request=              payload,
        supabase_url=         RPD_SUPABASE_URL,
        supabase_service_key= RPD_SUPABASE_SERVICE_KEY,
        expected_token=       RPD_PIMS_TOKEN,
        token=                x_pims_token,
        background_tasks=     background_tasks,
    )


@router.post("/observation/sdgroup", response_model=ObservationResponse)
async def sdgroup_observation(
    request: Request,
    payload: ObservationRequest,
    background_tasks: BackgroundTasks,
    x_pims_token: str = Header(..., alias="X-PIMS-Token"),
):
    """Receive a field observation for SD Group and enrich with CCVS codes."""
    return await _handle_observation(
        request=              payload,
        supabase_url=         SDG_SUPABASE_URL,
        supabase_service_key= SDG_SUPABASE_SERVICE_KEY,
        expected_token=       SDG_PIMS_TOKEN,
        token=                x_pims_token,
        background_tasks=     background_tasks,
    )


@router.post("/staging/{staging_id}/approve")
async def approve_staging_rpd(
    request: Request,
    staging_id: str,
    pims_sess: str | None = Cookie(default=None, alias="pims_sess"),
):
    if not verify_session_cookie(pims_sess):
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    if not _is_uuid(staging_id):
        raise HTTPException(status_code=422, detail="Invalid staging_id format.")
    if not RPD_SUPABASE_URL:
        raise HTTPException(status_code=503, detail="Supabase URL not configured")
    if not RPD_SUPABASE_SERVICE_KEY:
        raise HTTPException(status_code=503, detail="Supabase service key not configured")

    headers_repr    = _supabase_headers(RPD_SUPABASE_SERVICE_KEY, prefer="return=representation")
    headers_minimal = _supabase_headers(RPD_SUPABASE_SERVICE_KEY, prefer="return=minimal")

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"{RPD_SUPABASE_URL}/rest/v1/pims_staging",
            headers=headers_repr,
            params={"id": f"eq.{staging_id}", "select": "*"},
        )
        r.raise_for_status()
        rows = r.json()

        if not rows:
            raise HTTPException(status_code=404, detail=f"Staging record {staging_id} not found.")

        staging = rows[0]

        if staging.get("review_status") == "Approved":
            raise HTTPException(status_code=409, detail=f"Staging record {staging_id} is already Approved.")

        if not staging.get("observation_text"):
            raise HTTPException(status_code=422, detail="Cannot approve a record with no observation_text.")

        now_utc = datetime.now(timezone.utc).isoformat()
        obs_row = {field: staging.get(field) for field in STAGING_COPY_FIELDS}
        obs_row.update({
            "staging_id":    staging_id,
            "review_status": "Approved",
            "approved_by":   "dashboard",
            "approved_at":   now_utc,
        })

        r2 = await client.post(
            f"{RPD_SUPABASE_URL}/rest/v1/pims_observations",
            headers={**headers_repr, "Prefer": "return=representation,resolution=ignore-duplicates"},
            params={"on_conflict": "staging_id"},
            json=obs_row,
        )
        if r2.status_code not in (200, 201):
            log.error(f"pims_observations insert failed: {r2.status_code} {r2.text}")
            raise HTTPException(
                status_code=500,
                detail="Failed to promote observation. Contact administrator.",
            )

        new_obs = r2.json()
        if not new_obs:
            r_existing = await client.get(
                f"{RPD_SUPABASE_URL}/rest/v1/pims_observations",
                headers=headers_repr,
                params={"staging_id": f"eq.{staging_id}", "select": "*"},
            )
            r_existing.raise_for_status()
            new_obs = r_existing.json()
        new_obs = new_obs[0] if isinstance(new_obs, list) else new_obs

        r3 = await client.patch(
            f"{RPD_SUPABASE_URL}/rest/v1/pims_staging",
            headers=headers_minimal,
            params={"id": f"eq.{staging_id}"},
            json={"review_status": "Approved"},
        )
        if r3.status_code not in (200, 204):
            log.error(f"pims_staging status update failed for {staging_id}: {r3.status_code} {r3.text}")
            raise HTTPException(
                status_code=500,
                detail="Observation promoted but status update failed. Contact administrator.",
            )

        ccvs = staging.get("ccvs_code")
        response = {
            "observation": new_obs,
            "staging_id":  staging_id,
            "message":     "Record promoted to pims_observations.",
        }
        if ccvs and ccvs not in VALID_CCVS:
            response["ccvs_warning"] = f"CCVS code '{ccvs}' is not in the approved RPD taxonomy."

        return response


def _is_uuid(val) -> bool:
    try:
        _uuid_mod.UUID(str(val))
        return True
    except (ValueError, TypeError):
        return False


def _validate_uuids(ids: list) -> list[str]:
    bad = [i for i in ids if not _is_uuid(i)]
    if bad:
        raise HTTPException(status_code=422, detail=f"Invalid UUID(s): {bad[:5]}")
    return [str(i) for i in ids]


def _is_allowed_url(url) -> bool:
    if not url:
        return False
    try:
        p = urllib.parse.urlparse(url)
        return (
            p.scheme == "https"
            and p.netloc == _ALLOWED_IMG_HOST
            and p.path.startswith(_ALLOWED_IMG_PREFIX)
        )
    except Exception:
        return False


async def _fetch_staging_rows(ids: list[str]) -> list[dict]:
    if not ids:
        raise HTTPException(status_code=422, detail="Select at least one row to export.")
    if len(ids) > MAX_ROWS:
        raise HTTPException(
            status_code=422,
            detail=f"Export limit is {MAX_ROWS} rows. {len(ids)} requested.",
        )

    safe = _validate_uuids(ids)
    headers_sb = _supabase_headers(RPD_SUPABASE_SERVICE_KEY)
    params = {
        "select": "*",
        "order": "seq_no.asc",
        "id": f"in.({','.join(safe)})",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"{RPD_SUPABASE_URL}/rest/v1/pims_staging",
            headers=headers_sb,
            params=params,
        )
        r.raise_for_status()
        return r.json()


async def _fetch_images(urls: list) -> list:
    sem = asyncio.Semaphore(IMAGE_CONCURRENCY)

    async def _one(url) -> bytes | None:
        if not _is_allowed_url(url):
            if url:
                log.warning(f"Blocked non-allowlisted URL: {url}")
            return None
        async with sem:
            try:
                async with httpx.AsyncClient(timeout=IMAGE_TIMEOUT) as c:
                    r = await c.get(url)
                if r.status_code != 200:
                    log.warning(f"Image fetch {r.status_code}: {url}")
                    return None

                ct = r.headers.get("content-type", "").split(";")[0].strip().lower()
                if ct not in {"image/jpeg", "image/png", "image/webp"}:
                    log.warning(f"Rejected content-type '{ct}': {url}")
                    return None

                cl = r.headers.get("content-length")
                if cl:
                    try:
                        if int(cl) > MAX_IMG_BYTES:
                            log.warning(f"Rejected oversized image (Content-Length={cl}): {url}")
                            return None
                    except (ValueError, TypeError):
                        pass

                content = r.content
                if len(content) > MAX_IMG_BYTES:
                    log.warning(f"Rejected oversized image ({len(content)} bytes): {url}")
                    return None
                return content
            except Exception as e:
                log.warning(f"Image fetch failed: {e}")
                return None

    return list(await asyncio.gather(*[_one(u) for u in urls]))


def _cell_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _parse_upload_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    text = _cell_text(value).lower()
    return text in {"true", "1", "yes", "y"}


def _parse_upload_date(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = _cell_text(value)
    if not text:
        return None
    candidate = text[:10] if len(text) >= 10 else text
    try:
        return date.fromisoformat(candidate).isoformat()
    except ValueError:
        return None


def _derive_ccvs_category(code: str | None) -> str | None:
    if not code:
        return None
    prefix = code.split("-", 1)[0]
    return CCVS_CATEGORY_BY_PREFIX.get(prefix)


def _drun(para, text, bold=False, italic=False, size_pt=9, color_hex=None):
    run = para.add_run(text)
    run.font.name = "Aptos"
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size_pt)
    if color_hex:
        run.font.color.rgb = RGBColor(
            int(color_hex[0:2], 16),
            int(color_hex[2:4], 16),
            int(color_hex[4:6], 16),
        )
    return run


def _set_fill(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _add_footer(section):
    footer = section.footer
    para = footer.paragraphs[0]
    para.clear()
    para.alignment = WD_ALIGN_PARAGRAPH.LEFT

    run_co = para.add_run(
        "Robertson’s Remedial and Painting Pty Ltd"
        "  ·  Photographic Inspection Register"
    )
    run_co.font.name = "Aptos"
    run_co.font.size = Pt(7)
    run_co.font.color.rgb = RGBColor(0x6B, 0x7A, 0x99)

    para.add_run("\t")

    for label, field in [("Page ", " PAGE "), (" of ", None), ("", " NUMPAGES ")]:
        if label:
            r = para.add_run(label)
            r.font.name = "Aptos"
            r.font.size = Pt(7)
            r.font.color.rgb = RGBColor(0x6B, 0x7A, 0x99)
        if field:
            for ftype, fval in [("begin", None), (None, field), ("end", None)]:
                run = para.add_run()
                run.font.name = "Aptos"
                run.font.size = Pt(7)
                run.font.color.rgb = RGBColor(0x6B, 0x7A, 0x99)
                if ftype:
                    fc = OxmlElement("w:fldChar")
                    fc.set(qn("w:fldCharType"), ftype)
                    run._r.append(fc)
                else:
                    it = OxmlElement("w:instrText")
                    it.set(qn("xml:space"), "preserve")
                    it.text = fval
                    run._r.append(it)

    pPr = para._p.get_or_add_pPr()
    tabs = OxmlElement("w:tabs")
    tab = OxmlElement("w:tab")
    tab.set(qn("w:val"), "right")
    tab.set(qn("w:pos"), "9026")
    tabs.append(tab)
    pPr.append(tabs)


@router.post("/staging/rpd/docx")
async def download_staging_docx(
    request: Request,
    payload: StagingExportRequest,
    pims_sess: str | None = Cookie(default=None, alias=COOKIE_NAME),
):
    if not verify_session_cookie(pims_sess):
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    if not RPD_SUPABASE_SERVICE_KEY:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    rows = await _fetch_staging_rows(payload.ids)
    if not rows:
        raise HTTPException(status_code=404, detail="No rows found.")

    images = await _fetch_images([r.get("photo_url") for r in rows])

    doc = DocxDocument()
    section = doc.sections[0]
    section.top_margin = Cm(1.5)
    section.bottom_margin = Cm(1.5)
    section.left_margin = Cm(1.8)
    section.right_margin = Cm(1.8)
    doc.styles["Normal"].font.name = "Aptos"
    doc.styles["Normal"].font.size = Pt(9)
    _add_footer(section)

    col_w = [400, 1000, 2500, 3526, 800, 800]
    headers = ["#", "Date", "Photo", "Observation", "CCVS", "Conformance"]

    table = doc.add_table(rows=1, cols=6)
    table.style = "Table Grid"
    tbl = table._tbl
    grid = OxmlElement("w:tblGrid")
    for w in col_w:
        gc = OxmlElement("w:gridCol")
        gc.set(qn("w:w"), str(w))
        grid.append(gc)
    tbl.insert(0, grid)

    for i, cell in enumerate(table.rows[0].cells):
        _set_fill(cell, "0A1628")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _drun(p, headers[i], bold=True, color_hex="FFFFFF")

    for i, (row_data, img_bytes) in enumerate(zip(rows, images)):
        dr = table.add_row()
        cells = dr.cells

        cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        _drun(cells[0].paragraphs[0], str(row_data.get("seq_no") or i + 1), bold=True)

        _drun(cells[1].paragraphs[0], str(row_data.get("observation_date") or ""))

        if img_bytes:
            try:
                pil = PILImage.open(BytesIO(img_bytes)).convert("RGB")
                pil.thumbnail((300, 300), PILImage.LANCZOS)
                buf = BytesIO()
                pil.save(buf, format="JPEG", quality=85)
                buf.seek(0)
                cells[2].paragraphs[0].add_run().add_picture(buf, width=Cm(4.0))
            except Exception as exc:
                log.warning(f"DOCX PIL embed failed row {row_data.get('id')}: {exc}")
                _drun(
                    cells[2].paragraphs[0],
                    row_data.get("filename") or "Photo unavailable",
                    size_pt=8,
                    color_hex="6B7A99",
                )
        else:
            _drun(
                cells[2].paragraphs[0],
                row_data.get("filename") or "Photo unavailable",
                size_pt=8,
                color_hex="6B7A99",
            )

        enriched = row_data.get("observation_text_enriched") or ""
        legal = row_data.get("legal_reference") or ""
        if enriched:
            _drun(cells[3].paragraphs[0], enriched, italic=True, size_pt=8, color_hex="1E3A5F")
        if legal:
            p_ll = cells[3].add_paragraph()
            _drun(p_ll, "§ Legal Reference", bold=True, size_pt=8, color_hex="6B7A99")
            p_lt = cells[3].add_paragraph()
            _drun(p_lt, legal, italic=True, size_pt=8, color_hex="6B7A99")

        _drun(cells[4].paragraphs[0], row_data.get("ccvs_code") or "—")
        _drun(cells[5].paragraphs[0], row_data.get("conformance_status") or "—")

    buf_out = BytesIO()
    doc.save(buf_out)
    buf_out.seek(0)
    fname = f"PIMS_Report_{date.today().isoformat()}.docx"
    return StreamingResponse(
        buf_out,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


@router.post("/staging/rpd/xlsx")
async def download_staging_xlsx(
    request: Request,
    payload: StagingExportRequest,
    pims_sess: str | None = Cookie(default=None, alias=COOKIE_NAME),
):
    if not verify_session_cookie(pims_sess):
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    if not RPD_SUPABASE_SERVICE_KEY:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    rows = await _fetch_staging_rows(payload.ids)
    if not rows:
        raise HTTPException(status_code=404, detail="No rows found.")

    images = await _fetch_images([r.get("photo_url") for r in rows])

    col_names = [
        "#", "Date", "Finding", "Photo ID", "Photo",
        "CCVS Code", "Legal Reference", "Conformance Status",
        "Action Description", "Responsible", "Due Category",
        "Monitoring Note", "Observation",
    ]
    col_widths = [4, 12, 40, 14, 10, 10, 35, 16, 35, 14, 12, 28, 35]
    blue_cols = {6, 7}

    navy = "0A1628"
    blue_h = "1E40AF"
    white = "FFFFFF"
    border_c = "D1D5DB"
    text_c = "111827"

    def solid(h):
        return PatternFill(fill_type="solid", fgColor=h)

    def bdr():
        s = Side(style="thin", color=border_c)
        return Border(top=s, left=s, bottom=s, right=s)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Staging"

    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = 9
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True

    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[1].height = 28

    hdr_font = Font(name="Aptos", bold=True, color=white, size=9)
    hdr_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    data_font = Font(name="Aptos", size=8.5, color=text_c)
    data_align = Alignment(horizontal="left", vertical="top", wrap_text=True)

    for c, name in enumerate(col_names, 1):
        cell = ws.cell(row=1, column=c, value=name)
        cell.fill = solid(blue_h if c in blue_cols else navy)
        cell.font = hdr_font
        cell.alignment = hdr_align
        cell.border = bdr()

    for i, (row_data, img_bytes) in enumerate(zip(rows, images)):
        r_num = i + 2
        fill = solid("FFFFFF" if i % 2 == 0 else "F4F7FC")
        ws.row_dimensions[r_num].height = 90

        values = [
            i + 1,
            str(row_data.get("observation_date") or ""),
            row_data.get("observation_text_enriched") or "",
            row_data.get("filename") or "",
            None,
            row_data.get("ccvs_code") or "",
            row_data.get("legal_reference") or "",
            row_data.get("conformance_status") or "",
            row_data.get("action_description") or "",
            row_data.get("responsible") or "",
            row_data.get("due_category") or "",
            row_data.get("monitoring_note") or "",
            row_data.get("observation_text") or "",
        ]

        for c, val in enumerate(values, 1):
            if val is None:
                continue
            cell = ws.cell(row=r_num, column=c, value=val)
            cell.fill = fill
            cell.font = data_font
            cell.alignment = data_align
            cell.border = bdr()

        pc = ws.cell(row=r_num, column=5, value="")
        pc.fill = fill
        pc.border = bdr()

        if img_bytes:
            try:
                pil = PILImage.open(BytesIO(img_bytes)).convert("RGB")
                pil.thumbnail((72, 72), PILImage.LANCZOS)
                buf = BytesIO()
                pil.save(buf, format="JPEG", quality=85)
                buf.seek(0)
                xl_img = XLImage(buf)
                xl_img.width = 60
                xl_img.height = 60
                ws.add_image(xl_img, f"E{r_num}")
            except Exception as exc:
                log.warning(f"XLSX PIL embed failed row {row_data.get('id')}: {exc}")
                pc.value = row_data.get("filename") or "[photo]"
        else:
            pc.value = row_data.get("filename") or "[photo]"

    buf_out = BytesIO()
    wb.save(buf_out)
    buf_out.seek(0)
    fname = f"PIMS_Staging_{date.today().isoformat()}.xlsx"
    return StreamingResponse(
        buf_out,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


@router.post("/upload/observations")
async def upload_observations_xlsx(
    request: Request,
    file: UploadFile = File(...),
    is_current_audit: bool = Form(False),
    pims_sess: str | None = Cookie(default=None, alias=COOKIE_NAME),
):
    if not verify_session_cookie(pims_sess):
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    if not RPD_SUPABASE_URL:
        raise HTTPException(status_code=503, detail="Supabase URL not configured")
    if not RPD_SUPABASE_SERVICE_KEY:
        raise HTTPException(status_code=503, detail="Supabase service key not configured")

    filename = _cell_text(file.filename)
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Invalid file type - upload a .xlsx file")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > MAX_UPLOAD_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 5MB limit")

    try:
        wb = openpyxl.load_workbook(BytesIO(content), data_only=True)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid file - must be a valid .xlsx file",
        )

    if "Observations" not in wb.sheetnames:
        raise HTTPException(
            status_code=422,
            detail="Sheet 'Observations' not found",
        )

    ws = wb["Observations"]
    header_map: dict[str, int] = {}
    for col_idx, cell in enumerate(ws[3], 1):
        header = _cell_text(cell.value).lower()
        if header:
            header_map[header] = col_idx

    required_headers = {"site_address", "audit_date", "observation_text"}
    missing = sorted(required_headers - set(header_map))
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required column(s): {', '.join(missing)}",
        )

    def _cell(row_num: int, col_name: str):
        col_idx = header_map.get(col_name)
        if not col_idx:
            return None
        return ws.cell(row=row_num, column=col_idx).value

    parsed_rows: list[dict] = []
    for excel_row in range(5, ws.max_row + 1):
        observation_text = _cell_text(_cell(excel_row, "observation_text"))
        if not observation_text:
            continue
        parsed_rows.append(
            {
                "_row": excel_row,
                "site_address": _cell(excel_row, "site_address"),
                "audit_date": _cell(excel_row, "audit_date"),
                "observation_text": observation_text,
                "conformance_status": _cell(excel_row, "conformance_status"),
                "ccvs_code": _cell(excel_row, "ccvs_code"),
                "ccvs_category": _cell(excel_row, "ccvs_category"),
                "action_description": _cell(excel_row, "action_description"),
                "responsible": _cell(excel_row, "responsible"),
                "due_category": _cell(excel_row, "due_category"),
                "recommendation": _cell(excel_row, "recommendation"),
                "monitoring_note": _cell(excel_row, "monitoring_note"),
                "legal_ref": _cell(excel_row, "legal_ref"),
                "photo_refs": _cell(excel_row, "photo_refs"),
                "prepared_by": _cell(excel_row, "prepared_by"),
                "source_pdf": _cell(excel_row, "source_pdf"),
                "section": _cell(excel_row, "section"),
                "needs_review": _cell(excel_row, "needs_review"),
            }
        )

    if not parsed_rows:
        raise HTTPException(
            status_code=422,
            detail="No data rows with observation_text found from row 5 onward",
        )
    if len(parsed_rows) > MAX_UPLOAD_ROWS:
        raise HTTPException(
            status_code=422,
            detail=f"Upload limit is {MAX_UPLOAD_ROWS} rows. {len(parsed_rows)} provided.",
        )

    headers_repr = _supabase_headers(RPD_SUPABASE_SERVICE_KEY, prefer="return=representation")
    headers_minimal = _supabase_headers(RPD_SUPABASE_SERVICE_KEY, prefer="return=minimal")
    inserted = 0
    skipped = 0
    flagged = 0
    errors: list[dict] = []
    now_utc = datetime.now(timezone.utc).isoformat()
    fallback_source = filename or "uploaded.xlsx"

    async with httpx.AsyncClient(timeout=20) as client:
        for row in parsed_rows:
            row_num = int(row["_row"])
            observation_text = _cell_text(row.get("observation_text"))
            audit_date_value = _parse_upload_date(row.get("audit_date"))
            if not audit_date_value:
                errors.append(
                    {
                        "row": row_num,
                        "field": "audit_date",
                        "message": "Invalid date format - use YYYY-MM-DD",
                    }
                )
                continue

            conformance_raw = _cell_text(row.get("conformance_status")).lower()
            conformance_status = None
            if conformance_raw:
                conformance_status = VALID_CONFORMANCE_STATUS.get(conformance_raw)
                if not conformance_status:
                    errors.append(
                        {
                            "row": row_num,
                            "field": "conformance_status",
                            "message": "Invalid value. Use NCR, Compliant, Conditional, Info, or blank.",
                        }
                    )
                    continue

            ccvs_raw = _cell_text(row.get("ccvs_code")).upper()
            ccvs_invalid = False
            ccvs_code = ccvs_raw or None
            if ccvs_code and ccvs_code not in VALID_CCVS:
                ccvs_code = None
                ccvs_invalid = True

            ccvs_category = _cell_text(row.get("ccvs_category")) or _cell_text(row.get("section"))
            if not ccvs_category:
                ccvs_category = _derive_ccvs_category(ccvs_code)
            if not ccvs_category:
                ccvs_category = None

            site_address = _cell_text(row.get("site_address")) or None
            dup_params = {
                "select": "id",
                "limit": "1",
                "audit_date": f"eq.{audit_date_value}",
                "observation_text": f"eq.{observation_text}",
            }
            dup_params["site_address"] = "is.null" if site_address is None else f"eq.{site_address}"
            dup_resp = await client.get(
                f"{RPD_SUPABASE_URL}/rest/v1/pims_observations",
                headers=headers_repr,
                params=dup_params,
            )
            dup_resp.raise_for_status()
            if dup_resp.json():
                skipped += 1
                continue

            needs_review = _parse_upload_bool(row.get("needs_review")) or ccvs_invalid
            insert_row = {
                "site_address": site_address,
                "audit_date": audit_date_value,
                "observation_text": observation_text,
                "conformance_status": conformance_status,
                "ccvs_code": ccvs_code,
                "ccvs_category": ccvs_category,
                "action_description": _cell_text(row.get("action_description")) or None,
                "responsible": _cell_text(row.get("responsible")) or None,
                "due_category": _cell_text(row.get("due_category")) or None,
                "recommendation": _cell_text(row.get("recommendation")) or None,
                "monitoring_note": _cell_text(row.get("monitoring_note")) or None,
                "legal_ref": _cell_text(row.get("legal_ref")) or None,
                "photo_refs": _cell_text(row.get("photo_refs")) or None,
                "prepared_by": _cell_text(row.get("prepared_by")) or "Alan Richardson",
                "source_pdf": None
                if is_current_audit
                else (_cell_text(row.get("source_pdf")) or fallback_source),
                "needs_review": needs_review,
                "staging": True,
                "enriched": True,
                "action_required": conformance_status in {"NCR", "Conditional"},
                "imported_at": now_utc,
            }
            insert_resp = await client.post(
                f"{RPD_SUPABASE_URL}/rest/v1/pims_observations",
                headers=headers_minimal,
                json=insert_row,
            )
            if insert_resp.status_code not in (200, 201):
                log.warning(
                    "Upload insert failed for row %s: %s %s",
                    row_num,
                    insert_resp.status_code,
                    insert_resp.text,
                )
                errors.append(
                    {
                        "row": row_num,
                        "field": "row",
                        "message": "Failed to insert this row.",
                    }
                )
                continue

            inserted += 1
            if needs_review:
                flagged += 1

    return {
        "inserted": inserted,
        "skipped": skipped,
        "flagged": flagged,
        "errors": errors,
    }


@router.get("/observations/rpd")
async def list_observations_rpd(
    request: Request,
    pims_sess: str | None = Cookie(default=None, alias=COOKIE_NAME),
    audit_id: str | None = None,
    limit: int = 500,
    offset: int = 0,
):
    if not verify_session_cookie(pims_sess):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not RPD_SUPABASE_URL:
        raise HTTPException(status_code=503, detail="Supabase URL not configured")
    if not RPD_SUPABASE_SERVICE_KEY:
        raise HTTPException(status_code=503, detail="Supabase service key not configured")
    if audit_id and not _is_uuid(audit_id):
        raise HTTPException(status_code=422, detail="Invalid audit_id format.")
    if limit < 1:
        raise HTTPException(status_code=422, detail="limit must be >= 1.")
    if offset < 0:
        raise HTTPException(status_code=422, detail="offset must be >= 0.")

    limit = min(limit, 1000)

    headers = _supabase_headers(RPD_SUPABASE_SERVICE_KEY, prefer="return=representation")
    params = {
        "review_status": "eq.Approved",
        "order":         "approved_at.desc",
        "select":        "*",
        "limit":         str(limit),
        "offset":        str(offset),
    }
    if audit_id:
        params["audit_id"] = f"eq.{audit_id}"

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"{RPD_SUPABASE_URL}/rest/v1/pims_observations",
            headers=headers,
            params=params,
        )
        r.raise_for_status()
        return r.json()

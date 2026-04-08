"""
pims/routes.py — PIMS observation endpoints for Safe Method / Gatekeeper

Routes:
    POST /pims/observation/rpd      — RPD (Robertson's Remedial and Painting)
    POST /pims/observation/sdgroup  — SD Group (future)

Auth: X-PIMS-Token header checked against env var per client.

Each endpoint:
    1. Validates token
    2. Calls Claude Haiku to enrich the observation
    3. Writes enriched record to client Supabase pims_staging table
    4. Returns enrichment result
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
from pydantic import BaseModel

log = logging.getLogger(__name__)

router = APIRouter(prefix="/pims", tags=["pims"])

# ── Environment ────────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY   = os.getenv("ANTHROPIC_API_KEY", "")

# RPD Supabase
RPD_SUPABASE_URL    = os.getenv("RPD_SUPABASE_URL", "https://nebdpofqglfyfyqqodni.supabase.co")
RPD_SUPABASE_KEY    = os.getenv("RPD_SUPABASE_ANON_KEY", "")
RPD_PIMS_TOKEN      = os.getenv("PIMS_RPD_TOKEN", "")

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

STAGING_COPY_FIELDS = [
    "audit_id", "seq_no", "observation_date", "observation_text",
    "filename", "photo_url", "submitted_by", "device_info",
    "enriched", "enriched_at", "conformance_status", "ccvs_code",
    "ccvs_category", "ccvs_confidence", "action_required",
    "action_description", "responsible", "due_category", "monitoring_note",
    "observation_text_enriched", "legal_reference",
]

# SD Group Supabase (future)
SDG_SUPABASE_URL    = os.getenv("SDG_SUPABASE_URL", "")
SDG_SUPABASE_KEY    = os.getenv("SDG_SUPABASE_ANON_KEY", "")
SDG_PIMS_TOKEN      = os.getenv("PIMS_SDG_TOKEN", "")

# ── Request / Response models ──────────────────────────────────────────────────

class ObservationRequest(BaseModel):
    audit_ref:        str                    # e.g. "RPD-SSA"
    seq_no:           Optional[int] = None   # optional — auto-assigned if omitted
    observation_text: str                    # dictated observation
    observation_date: Optional[str] = None  # YYYY-MM-DD, defaults to today
    photo_url:        Optional[str] = None  # Supabase Storage URL
    filename:         Optional[str] = None  # original photo filename
    submitted_by:     Optional[str] = None  # auditor name
    device_info:      Optional[str] = None  # "iPhone 15 Pro"

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
        async with httpx.AsyncClient(timeout=60) as client:
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
            return json.loads(text)
    except Exception as e:
        log.error(f"Haiku enrichment failed: {type(e).__name__}: {e}")
        raise


# ── Supabase helpers ───────────────────────────────────────────────────────────

async def get_or_create_audit(
    supabase_url: str,
    supabase_key: str,
    audit_ref: str,
) -> str:
    """Return existing audit id or create a new audit record."""
    headers = {
        "apikey":        supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type":  "application/json",
        "Prefer":        "return=representation",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        # Check if audit exists
        r = await client.get(
            f"{supabase_url}/rest/v1/pims_audits",
            headers=headers,
            params={"audit_ref": f"eq.{audit_ref}", "select": "id"},
        )
        r.raise_for_status()
        existing = r.json()
        if existing:
            return existing[0]["id"]

        # Create new audit
        today = date.today().isoformat()
        # Parse date from audit_ref (YYYY-MM-DD_SiteName)
        parts = audit_ref.split("_", 1)
        audit_date = parts[0] if len(parts[0]) == 10 else today
        site_name  = parts[1].replace("_", " ") if len(parts) > 1 else audit_ref

        r2 = await client.post(
            f"{supabase_url}/rest/v1/pims_audits",
            headers=headers,
            json={
                "audit_ref":  audit_ref,
                "site_name":  site_name,
                "audit_date": audit_date,
                "auditor":    "Alan Richardson",
            },
        )
        r2.raise_for_status()
        return r2.json()[0]["id"]


async def insert_staging(
    supabase_url: str,
    supabase_key: str,
    audit_id: str,
    request: ObservationRequest,
    enrichment: dict,
) -> str:
    """Insert enriched observation into pims_staging. Returns record id."""
    headers = {
        "apikey":        supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type":  "application/json",
        "Prefer":        "return=representation",
    }
    record = {
        "audit_id":           audit_id,
        "seq_no":             request.seq_no,
        "photo_url":          request.photo_url,
        "filename":           request.filename,
        "observation_date":   request.observation_date or date.today().isoformat(),
        "observation_text":   request.observation_text,
        "submitted_by":       request.submitted_by,
        "device_info":        request.device_info,
        "enriched":           True,
        "enriched_at":        datetime.utcnow().isoformat(),
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
        r = await client.post(
            f"{supabase_url}/rest/v1/pims_staging",
            headers=headers,
            json=record,
        )
        r.raise_for_status()
        return r.json()[0]["id"]


# ── Route handlers ─────────────────────────────────────────────────────────────

async def _handle_observation(
    request: ObservationRequest,
    supabase_url: str,
    supabase_key: str,
    expected_token: str,
    token: str,
) -> ObservationResponse:
    """Shared handler for all client observation endpoints."""
    if not expected_token or token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid PIMS token")

    if not supabase_key:
        raise HTTPException(status_code=503, detail="Supabase not configured for this client")

    try:
        enrichment = await enrich_observation(request.observation_text)
    except Exception as e:
        log.error(f"Haiku enrichment failed: {e}")
        enrichment = {
            "conformance_status": None,
            "ccvs_code":          None,
            "ccvs_category":      None,
            "ccvs_confidence":    "Low",
            "action_required":    False,
            "action_description": None,
            "responsible":        None,
            "due_category":       "N/A",
            "monitoring_note":    None,
        }

    try:
        audit_id = await get_or_create_audit(supabase_url, supabase_key, request.audit_ref)
        record_id = await insert_staging(supabase_url, supabase_key, audit_id, request, enrichment)
    except Exception as e:
        log.error(f"Supabase insert failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to save observation")

    return ObservationResponse(
        id=                 record_id,
        seq_no=             request.seq_no,
        conformance_status= enrichment.get("conformance_status"),
        ccvs_code=          enrichment.get("ccvs_code"),
        ccvs_category=      enrichment.get("ccvs_category"),
        ccvs_confidence=    enrichment.get("ccvs_confidence"),
        action_required=    enrichment.get("action_required", False),
        action_description= enrichment.get("action_description"),
        monitoring_note=    enrichment.get("monitoring_note"),
        review_status=      "Pending",
    )


@router.post("/observation/rpd", response_model=ObservationResponse)
async def rpd_observation(
    request: ObservationRequest,
    x_pims_token: str = Header(..., alias="X-PIMS-Token"),
):
    """Receive a field observation for RPD and enrich with CCVS codes."""
    return await _handle_observation(
        request=       request,
        supabase_url=  RPD_SUPABASE_URL,
        supabase_key=  RPD_SUPABASE_KEY,
        expected_token=RPD_PIMS_TOKEN,
        token=         x_pims_token,
    )


@router.post("/observation/sdgroup", response_model=ObservationResponse)
async def sdgroup_observation(
    request: ObservationRequest,
    x_pims_token: str = Header(..., alias="X-PIMS-Token"),
):
    """Receive a field observation for SD Group and enrich with CCVS codes."""
    return await _handle_observation(
        request=       request,
        supabase_url=  SDG_SUPABASE_URL,
        supabase_key=  SDG_SUPABASE_KEY,
        expected_token=SDG_PIMS_TOKEN,
        token=         x_pims_token,
    )


@router.post("/staging/{staging_id}/approve")
async def approve_staging_rpd(
    staging_id: str,
    x_pims_token: str = Header(..., alias="X-PIMS-Token"),
):
    if not RPD_PIMS_TOKEN or x_pims_token != RPD_PIMS_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid PIMS token")

    headers = {
        "apikey":        RPD_SUPABASE_KEY,
        "Authorization": f"Bearer {RPD_SUPABASE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "return=representation",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"{RPD_SUPABASE_URL}/rest/v1/pims_staging",
            headers=headers,
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

        now_utc = datetime.utcnow().isoformat()
        obs_row = {field: staging.get(field) for field in STAGING_COPY_FIELDS}
        obs_row.update({
            "staging_id":    staging_id,
            "review_status": "Approved",
            "approved_by":   "dashboard",
            "approved_at":   now_utc,
        })

        r2 = await client.post(
            f"{RPD_SUPABASE_URL}/rest/v1/pims_observations",
            headers=headers,
            json=obs_row,
        )
        if r2.status_code not in (200, 201):
            log.error(f"pims_observations insert failed: {r2.status_code} {r2.text}")
            raise HTTPException(status_code=500, detail=f"Failed to insert observation: {r2.text}")

        new_obs = r2.json()[0]

        r3 = await client.patch(
            f"{RPD_SUPABASE_URL}/rest/v1/pims_staging",
            headers={**headers, "Prefer": "return=minimal"},
            params={"id": f"eq.{staging_id}"},
            json={"review_status": "Approved"},
        )
        if r3.status_code not in (200, 204):
            log.warning(f"pims_staging status update failed for {staging_id}: {r3.status_code} {r3.text}")

        ccvs = staging.get("ccvs_code")
        response = {
            "observation": new_obs,
            "staging_id":  staging_id,
            "message":     "Record promoted to pims_observations.",
        }
        if ccvs and ccvs not in VALID_CCVS:
            response["ccvs_warning"] = f"CCVS code '{ccvs}' is not in the approved RPD taxonomy."

        return response


@router.get("/observations/rpd")
async def list_observations_rpd(
    x_pims_token: str = Header(..., alias="X-PIMS-Token"),
    audit_id: str | None = None,
):
    if not RPD_PIMS_TOKEN or x_pims_token != RPD_PIMS_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid PIMS token")

    headers = {
        "apikey":        RPD_SUPABASE_KEY,
        "Authorization": f"Bearer {RPD_SUPABASE_KEY}",
        "Content-Type":  "application/json",
    }
    params = {
        "review_status": "eq.Approved",
        "order":         "approved_at.desc",
        "select":        "*",
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

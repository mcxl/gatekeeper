#!/usr/bin/env python3
"""
core/swms_analyser.py
Mode 02: Analyse existing SWMS against Gatekeeper Standard.
Mode 03: Extract scope from Scope of Works / Specification.
"""

import json
import logging
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)
client = AsyncAnthropic()


def _parse_json_response(text: str) -> dict:
    """Strip markdown fences and parse JSON."""
    text = text.strip()
    if text.startswith('```'):
        parts = text.split('```')
        text = parts[1] if len(parts) > 1 else text
        if text.startswith('json'):
            text = text[4:]
    return json.loads(text.strip())


ANALYSE_PROMPT = """You are a WHS Safety adviser reviewing a Safe Work Method Statement
against the Gatekeeper Standard for Australian construction.

UPLOADED SWMS TEXT:
{swms_text}

Analyse this SWMS and return a JSON object with exactly this structure:

{{
  "pcbu_name": "company name found in document, or empty string",
  "project_address": "site address found in document, or empty string",
  "manager_name": "manager or supervisor name found, or empty string",
  "principal_contractor": "PC name found, or empty string",
  "jurisdiction": "AU",
  "title": "3-6 word job title only e.g. Painting project — 23 Bill St Kiama",
  "work_activity_summary": "one sentence — what work is being done",
  "description": "detailed rewritten job description capturing all tasks,
                  trade types, location context, HRCW categories, materials
                  and equipment — written to generate a full new SWMS from",
  "gaps": [
    "each string is one compliance gap — missing controls, missing permits,
     missing PPE items, missing HRCW tick, inadequate risk rating, missing
     hold point, missing STOP WORK trigger, missing CCVS code, etc."
  ],
  "hrcw_categories": ["list of applicable HRCW categories"],
  "existing_tasks": ["list of task names found in the uploaded SWMS"]
}}

Be thorough on gaps — this is a compliance tool.
Return only valid JSON, no preamble.
"""


SCOPE_EXTRACT_PROMPT = """You are a WHS Safety adviser reading a Scope of Works or
Specification document for an Australian construction project.

DOCUMENT TEXT:
{doc_text}

Extract the work scope and return a JSON object with exactly this structure:

{{
  "project_name": "project name if found, else empty string",
  "project_address": "site address if found, else empty string",
  "principal_contractor": "principal contractor if found, else empty string",
  "site_contact": "site contact person if found, else empty string",
  "site_phone": "site contact phone if found, else empty string",
  "pcbu_name": "company name (PCBU) if found, else empty string",
  "project_description": "brief project description if found, else empty string",
  "site_conditions": "site conditions mentioned e.g. occupied, heritage, high-rise, else empty string",
  "access_constraints": "access restrictions or constraints mentioned, else empty string",
  "neighbouring_properties": "neighbouring property concerns if mentioned, else empty string",
  "environmental_considerations": "environmental factors if mentioned, else empty string",
  "approval_requirements": "approvals or permits mentioned, else empty string",
  "emergency_assembly_point": "emergency assembly point if found, else empty string",
  "nearest_hospital": "nearest hospital if found, else empty string",
  "induction_requirements": "site induction requirements if mentioned, else empty string",
  "special_permits": "special permits required if mentioned, else empty string",
  "whs_legislation_state": "state or territory for WHS legislation if found, else empty string",
  "manager_name": "project manager or supervisor if found, else empty string",
  "jurisdiction": "AU",
  "title": "3-6 word job title only e.g. Painting project — 23 Bill St Kiama",
  "work_activity_summary": "one sentence — what construction work is being done",
  "description": "detailed job description capturing: all trade types and work
                  activities, access methods (scaffold/EWP/ladder), materials
                  and chemicals, location context (heights/confined spaces/traffic/
                  underground services), specific hazards mentioned. Write as if
                  describing the job to generate a SWMS — be specific.",
  "hrcw_categories": ["list of HRCW categories that appear to apply"]
}}

Focus on WHAT work is being done, not commercial or contractual terms.
Return only valid JSON, no preamble.
"""


async def analyse_existing_swms(swms_text: str) -> dict:
    """Mode 02: Analyse uploaded SWMS, return gap analysis + job data."""
    try:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": ANALYSE_PROMPT.format(swms_text=swms_text[:12000])
            }]
        )
        return _parse_json_response(response.content[0].text)
    except Exception as e:
        logger.error(f"SWMS analysis error: {e}")
        raise RuntimeError(f"Could not analyse SWMS: {str(e)}")


async def extract_scope_from_document(doc_text: str) -> dict:
    """Mode 03: Extract work scope from Scope of Works / Specification."""
    try:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": SCOPE_EXTRACT_PROMPT.format(doc_text=doc_text[:12000])
            }]
        )
        return _parse_json_response(response.content[0].text)
    except Exception as e:
        logger.error(f"Scope extraction error: {e}")
        raise RuntimeError(f"Could not extract scope: {str(e)}")

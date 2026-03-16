#!/usr/bin/env python3
"""
core/swms_analyser.py
Mode 02: Analyse existing SWMS against Gatekeeper Standard.
Mode 03: Extract scope from Scope of Works / Specification.
"""

import json
import logging
import re
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)
client = AsyncAnthropic()

MODEL = 'claude-sonnet-4-6'

# Minimal valid scope dict — returned when all parsing fails
_EMPTY_SCOPE = {
    "pcbu_name": "",
    "project_address": "",
    "manager_name": "",
    "principal_contractor": "",
    "jurisdiction": "AU",
    "title": "",
    "work_activity_summary": "",
    "description": "",
    "hrcw_categories": [],
}


def _parse_json_response(text: str) -> dict:
    """Extract JSON from Claude response. Never raises — returns partial dict on failure."""
    if not text or not text.strip():
        return dict(_EMPTY_SCOPE)

    text = text.strip()
    # Strip markdown fences
    if text.startswith('```'):
        parts = text.split('```')
        text = parts[1] if len(parts) > 1 else text
        if text.startswith('json'):
            text = text[4:]
    text = text.strip()

    # Step 1: Extract first { to last }
    first = text.find('{')
    last = text.rfind('}')
    if first != -1 and last > first:
        candidate = text[first:last + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
        # Step 2: Walk backwards to find largest valid JSON
        for i in range(last, first, -1):
            if text[i] == '}':
                try:
                    return json.loads(text[first:i + 1])
                except json.JSONDecodeError:
                    continue

    # Step 3: Regex field extraction from raw text
    logger.warning("JSON parse failed — extracting fields via regex")
    result = _regex_extract_fields(text)
    if result:
        return result

    # Step 4: Return empty scope dict so user sees review form with Required fields
    logger.warning("All JSON parsing failed — returning empty scope dict")
    return dict(_EMPTY_SCOPE)


def _regex_extract_fields(text: str) -> dict:
    """Extract key-value pairs from malformed JSON using regex."""
    result = {}
    # "key": "value" (string values — handles escaped quotes)
    for m in re.finditer(r'"(\w+)"\s*:\s*"((?:[^"\\]|\\.)*)"', text):
        result[m.group(1)] = m.group(2).replace('\\"', '"').replace('\\n', '\n')
    # "key": [...] (array values)
    for m in re.finditer(r'"(\w+)"\s*:\s*\[([^\]]*)\]', text):
        key = m.group(1)
        if key not in result:
            items = re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(2))
            result[key] = items
    # "key": true/false
    for m in re.finditer(r'"(\w+)"\s*:\s*(true|false)', text):
        key = m.group(1)
        if key not in result:
            result[key] = m.group(2) == 'true'
    # "key": number
    for m in re.finditer(r'"(\w+)"\s*:\s*(-?\d+(?:\.\d+)?)', text):
        key = m.group(1)
        if key not in result:
            try:
                result[key] = json.loads(m.group(2))
            except (json.JSONDecodeError, ValueError):
                pass
    return result


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


SCOPE_EXTRACT_PROMPT = """You are a WHS Safety adviser reading an
Australian construction document — this may be a Scope of Works,
Specification, Contractor Quote, or Methodology Statement.

DOCUMENT TEXT:
{doc_text}

DOCUMENT TYPE RECOGNITION:
- Specification / Methodology: formal sections, numbered clauses,
  product specs, methodology descriptions
- Contractor Quote: line items with prices, trade headings,
  inclusions/exclusions lists, item descriptions
- Mixed: quote with embedded scope narrative

TABLE OF CONTENTS / SCOPE SUMMARY (typically page 2):
Page 2 typically contains a Table of Contents or scope summary listing all
work sections. Extract HRCW indicators and trade types by reading the section
headings in the ToC — you do not need to read every page. If the ToC mentions
scaffolding, rope access, EWP, demolition, waterproofing at height, balconies,
facade works — these are HRCW indicators. Extract them from the ToC headings
directly rather than waiting to read the full content pages.

key_activities should be extracted from ToC section headings on page 2, not
just page 3 content. A ToC heading like '2.2 Re-Waterproofing of Suites 7, 8,
11 and 12 Balconies' is a key activity.

For ALL document types, extract the actual work being done — not
commercial terms, prices, or exclusions.

For QUOTE documents specifically:
- Read every line item under trade headings as a scope activity
- Treat dashed or bulleted line items as individual work activities
- Combine related line items into coherent task descriptions
- Ignore dollar amounts, GST, preliminaries costs, and exclusions

Return a JSON object with exactly this structure:

{{
  "pcbu_name": "company name if found, else empty string",
  "project_address": "site address if found, else empty string",
  "manager_name": "project manager or supervisor if found, else empty string",
  "principal_contractor": "principal contractor if found, else empty string",
  "jurisdiction": "AU",
  "title": "3-6 word job title only e.g. Exterior remedial works — 18 Danks St Waterloo",
  "work_activity_summary": "one sentence capturing ALL trade types — e.g. Exterior remedial works including crack stitching, brickwork repointing, concrete spalling repairs, sealant application, and painting to common property facades",
  "description": "Comprehensive job description capturing ALL of the following found in the document:
    - Every trade type and work activity mentioned (crack stitching, repointing, spalling, painting, waterproofing etc.)
    - Specific materials and products named (e.g. Thor Helical bars, Fosroc nitoseal MS250, Dulux Duspec)
    - Access methods required (scaffold, EWP, rope access, ladder)
    - Location context (building type, storeys, occupied/vacant, exterior/interior)
    - Any special conditions (heritage, occupied, traffic management, strata)
    - HRCW implications (work at height, demolition, structural elements)
    Write as a detailed brief to generate a complete multi-task SWMS from.
    Do NOT omit line items — every scope activity must appear in this description.",
  "hrcw_categories": ["list of HRCW categories that appear to apply based on the scope"]
}}

Return only valid JSON, no preamble.
"""


async def analyse_existing_swms(swms_text: str) -> dict:
    """Mode 02: Analyse uploaded SWMS, return gap analysis + job data."""
    try:
        response = await client.messages.create(
            model=MODEL,
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
    """Mode 03: Extract work scope from Scope of Works / Specification.
    Never raises — always returns a usable dict, even if partial or empty."""
    import asyncio
    try:
        response = await asyncio.wait_for(
            client.messages.create(
                model=MODEL,
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": SCOPE_EXTRACT_PROMPT.format(doc_text=doc_text[:8000])
                }]
            ),
            timeout=45.0,
        )
        result = _parse_json_response(response.content[0].text)
        # Ensure we always have the minimum required keys
        for key, default in _EMPTY_SCOPE.items():
            result.setdefault(key, default)
        return result
    except asyncio.TimeoutError:
        logger.warning("Scope extraction timed out at 45s — returning partial result")
        partial = dict(_EMPTY_SCOPE)
        partial["description"] = doc_text[:500]
        partial["partial"] = True
        return partial
    except Exception as e:
        logger.error(f"Scope extraction error: {e}")
        partial = dict(_EMPTY_SCOPE)
        partial["description"] = doc_text[:500] if doc_text else ""
        partial["partial"] = True
        partial["error"] = str(e)
        return partial


async def save_extraction(
    filename: str,
    file_size: int,
    extracted_fields: dict,
    duration_ms: int,
    user_id: str | None = None,
    document_type: str = "scope",
) -> None:
    """Save extraction to Supabase scope library. Never blocks or raises."""
    import os
    import httpx

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_ANON_KEY", "")
    if not supabase_url or not supabase_key:
        logger.debug("Supabase not configured — skipping extraction save")
        return

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            # Insert scope_documents row
            doc_payload = {
                "filename": filename,
                "file_size_bytes": file_size,
                "document_type": document_type,
            }
            if user_id:
                doc_payload["created_by"] = user_id

            doc_res = await http.post(
                f"{supabase_url}/rest/v1/scope_documents",
                headers=headers,
                json=doc_payload,
            )
            if doc_res.status_code not in (200, 201):
                logger.warning(f"scope_documents insert failed: {doc_res.status_code} {doc_res.text}")
                return

            doc_id = doc_res.json()[0]["id"]

            # Insert scope_extractions row
            ext_payload = {
                "document_id": doc_id,
                "extracted_fields": extracted_fields,
                "extraction_duration_ms": duration_ms,
            }
            ext_res = await http.post(
                f"{supabase_url}/rest/v1/scope_extractions",
                headers=headers,
                json=ext_payload,
            )
            if ext_res.status_code not in (200, 201):
                logger.warning(f"scope_extractions insert failed: {ext_res.status_code} {ext_res.text}")
                return

            logger.info(f"Saved extraction for '{filename}' → doc_id={doc_id}")
    except Exception as e:
        logger.warning(f"save_extraction failed (non-blocking): {e}")

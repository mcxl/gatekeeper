"""Vision-enabled per-observation enrichment for the SSA pipeline.

For each evidence row this module sends the photo (downscaled,
EXIF-normalised, base64-encoded) plus the auditor's raw observation
text to an Anthropic vision call and receives a JSON record carrying:

  - conformance_status  (Compliant / Conditional / NCR / Info / Unmatched)
  - ccvs_code           (one of the 150 valid <STREAM>-<TIER> codes)
  - ccvs_category       (plain-English category derived from the stream)
  - finding             (multi-sentence narrative, year-12 plain English)
  - legal_ref           (NSW WHS regulation / AS / SafeWork NSW citation)
  - recommendation      (one-sentence corrective action)
  - monitoring_note     (one-sentence reviewer follow-up cue)

Replaces the keyword-based ``ChecklistLookup.match_observation``
matcher — that approach hit 5/21 on real audit data with one outright
misroute. The vision approach uses the photo as primary evidence,
which matches how the human reviewer assigns these fields.

LLM is on by default. ``ANTHROPIC_API_KEY`` must be set in the
environment. When the key is missing or any individual call fails,
the row falls back to ``conformance_status="Unmatched"`` and blank
fields — never raises into the orchestrator.

Cost expectation: ~21 rows × one Sonnet vision call ≈ $0.10–$0.20 per
typical audit. Image is downscaled to 1024 px longest edge before
base64 encoding to keep input tokens predictable.
"""
from __future__ import annotations

import base64
import json
import logging
import os
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx

from pims.services.ssa_ccvs_taxonomy import (
    STREAM_TO_CATEGORY,
    TIER_DESCRIPTION,
    VALID_STATUSES,
    category_for,
    is_valid_code,
)
from pims.services.ssa_pipeline import EnrichedRow

log = logging.getLogger(__name__)

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
VISION_MODEL = "claude-opus-4-7"

# Largest edge for the photo passed into the vision call. 1024 px is
# enough resolution for compliance evidence (signage legibility, edge
# protection presence, PPE on workers) while keeping each call's input
# tokens around 1k–1.5k for the image plus ~500 for text.
_VISION_MAX_EDGE_PX = 1024

# Hard cap on JSON output size — replies are small structured records,
# 800 tokens is plenty for the longest finding paragraph + citations.
_MAX_OUTPUT_TOKENS = 800


def _encode_photo_for_vision(path: Path) -> tuple[str, str] | None:
    """EXIF-normalise + downscale + JPEG-encode + base64.

    Returns ``(base64_str, "image/jpeg")`` or ``None`` on failure /
    missing file. JPEG quality 85 is the same setting as the embedded-
    thumbnail path, so the image the LLM sees is consistent with what
    the reviewer sees in the deliverable.
    """
    try:
        from PIL import Image, ImageOps
    except Exception:
        log.warning("Pillow unavailable — vision enrichment skipped")
        return None
    if not path.exists():
        return None
    try:
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im)
            longest = max(im.width, im.height)
            if longest > _VISION_MAX_EDGE_PX:
                ratio = _VISION_MAX_EDGE_PX / float(longest)
                im = im.resize(
                    (int(im.width * ratio), int(im.height * ratio)),
                    Image.LANCZOS,
                )
            buf = BytesIO()
            im.convert("RGB").save(buf, format="JPEG", quality=85)
            data = base64.standard_b64encode(buf.getvalue()).decode("ascii")
            return data, "image/jpeg"
    except Exception:
        log.warning("vision photo encode failed for %s", path, exc_info=True)
        return None


_TIER_LIST = "\n".join(f"  {t}  {desc}" for t, desc in TIER_DESCRIPTION.items())
_STREAM_LIST = "\n".join(
    f"  {s}  {cat}" for s, cat in sorted(STREAM_TO_CATEGORY.items())
)

_SYSTEM_PROMPT = (
    "You are an Australian construction WHS auditor reviewing one site "
    "evidence photo plus the auditor's raw note. Classify the "
    "observation against the canonical CCVS taxonomy and write the "
    "review-ready finding.\n\n"
    "OUTPUT JSON ONLY — no prose, no markdown fences. The JSON object "
    "must carry exactly these keys:\n"
    '  status            ∈ ["Compliant", "Conditional", "NCR", "Info", "Unmatched"]\n'
    '  ccvs_code         "<STREAM>-<TIER>" or "" if no clear match\n'
    '  ccvs_category     plain-English category for the chosen stream, or ""\n'
    '  finding           2–4 sentence narrative, year-12 plain English\n'
    '  legal_ref         NSW WHS Reg / AS / SafeWork NSW citation, or ""\n'
    '  recommendation    one short sentence, or ""\n'
    '  monitoring_note   one short sentence reviewer cue, or ""\n\n'
    "STREAM PREFIXES (pick exactly one):\n"
    f"{_STREAM_LIST}\n\n"
    "SEVERITY TIERS:\n"
    f"{_TIER_LIST}\n\n"
    "CLASSIFICATION RULES:\n"
    "- Compliant: photo shows the control in place AND the auditor's "
    "  note describes a satisfactory state. Use a tier (usually L1/L2) "
    "  but the row records compliance, not non-conformance.\n"
    "- Conditional: control is present but partially in place, OR the "
    "  evidence needs follow-up. Tier M3/M4 typical.\n"
    "- NCR: control absent or seriously inadequate. Tier H6/H9.\n"
    "- Info: contextual / record-keeping observation, no control "
    "  judgement. Tier L1/L2 typical.\n"
    "- Unmatched: neither photo nor note give enough signal to "
    "  classify. Reviewer assigns at QA. Set ccvs_code, ccvs_category "
    "  to \"\" in this case.\n\n"
    "FINDING WRITING RULES (year-12 plain English, Australian):\n"
    "- 2–4 sentences. Describe what was observed, why it matters, and "
    "  what good looks like. Do not paraphrase the raw note — write "
    "  the reviewer-grade finding.\n"
    "- Cite the legal_ref inside the finding sentence when one applies "
    "  (e.g. \"contrary to WHS Regulation 2017 cl.79\").\n"
    "- Banned vocabulary: crucial, pivotal, landscape, ensure, "
    "  leverage, robust, comprehensive, navigate, delve, it's "
    "  important to note, serves as, at its core. No em-dash clusters, "
    "  no signposting, no sycophantic openers/closers, no emoji, no "
    "  curly quotes.\n"
    "- Do not invent measurements, names, dates, or evidence not "
    "  present in the photo or note.\n"
    "- For Compliant rows, the finding describes what was seen and "
    "  why it satisfies the requirement.\n\n"
    "LEGAL_REF RULES:\n"
    "- Use canonical Australian forms: \"NSW WHS Regulation 2017 cl.79\", "
    "  \"WHS Act 2011 s.19\", \"AS/NZS 1576.1:2019\", \"SafeWork NSW "
    "  Code of Practice: Construction Work (2022)\".\n"
    "- Leave \"\" if you do not know the citation. Do not fabricate.\n\n"
    "RECOMMENDATION + MONITORING_NOTE:\n"
    "- Both single-sentence. Recommendation is the corrective action; "
    "  monitoring_note is what the next audit should verify.\n"
    "- For Compliant / Info rows, recommendation may be \"\" and "
    "  monitoring_note records the verification cue."
)


async def _vision_call(
    photo_b64: str, photo_mime: str, observation_text: str,
    site_address: str, audit_date_iso: str, api_key: str,
) -> dict[str, Any]:
    """Single Anthropic vision call. Returns the parsed JSON dict.

    Raises on HTTP error / JSON parse failure / network — caller wraps
    in try/except and falls back to Unmatched on any failure.
    """
    user_text = (
        f"SITE: {site_address or '(unresolved)'}\n"
        f"AUDIT_DATE: {audit_date_iso}\n"
        f"AUDITOR_NOTE: {observation_text}\n"
    )
    body = {
        "model": VISION_MODEL,
        "max_tokens": _MAX_OUTPUT_TOKENS,
        "system": _SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": photo_mime,
                            "data": photo_b64,
                        },
                    },
                    {"type": "text", "text": user_text},
                ],
            }
        ],
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
            json=body,
        )
        resp.raise_for_status()
        text = resp.json()["content"][0]["text"].strip()
    # Strip code fences if the model wrapped output despite instruction.
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0].strip()
    return json.loads(text)


def _coerce_record(raw: dict[str, Any]) -> dict[str, str]:
    """Validate + normalise a single LLM record.

    - status falls back to ``"Unmatched"`` if not in the allowed set
    - ccvs_code is dropped (and category cleared) if it does not
      validate against the taxonomy
    - ccvs_category is regenerated from the (validated) code so the
      reviewer-facing label is always self-consistent
    """
    def _s(key: str) -> str:
        v = raw.get(key, "")
        return "" if v is None else str(v).strip()

    status = _s("status") or "Unmatched"
    if status not in VALID_STATUSES:
        status = "Unmatched"

    code = _s("ccvs_code").upper().replace(" ", "")
    if code and not is_valid_code(code):
        log.info("LLM returned invalid ccvs_code %r — dropping", code)
        code = ""
    category = category_for(code) if code else ""

    return {
        "status": status,
        "ccvs_code": code,
        "ccvs_category": category,
        "finding": _s("finding"),
        "legal_ref": _s("legal_ref"),
        "recommendation": _s("recommendation"),
        "monitoring_note": _s("monitoring_note"),
    }


async def enrich_rows_with_vision(
    rows: list[EnrichedRow],
    site_address: str,
    audit_date_iso: str,
) -> dict[str, Any]:
    """In-place enrichment: photo+note → status + CCVS + finding fields.

    Returns a diagnostics dict for ``.ssa_run.json``:
        {
          "model":        str,
          "rows_total":   int,
          "rows_called":  int,    # rows that had a resolved photo
          "rows_ok":      int,    # successful enrichments
          "rows_failed":  int,    # API / parse / encode failures
          "errors":       [str],  # short error reasons (deduped)
        }

    Rows without a resolved photo cannot be vision-classified — they
    keep ``status="Unmatched"`` and blank fields.
    """
    diag: dict[str, Any] = {
        "model": VISION_MODEL,
        "rows_total": len(rows),
        "rows_called": 0,
        "rows_ok": 0,
        "rows_failed": 0,
        "errors": [],
    }

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log.warning(
            "ANTHROPIC_API_KEY not set — vision enrichment skipped, "
            "every row stays Unmatched"
        )
        diag["errors"].append("ANTHROPIC_API_KEY missing")
        return diag

    seen_errors: set[str] = set()
    for row in rows:
        path = row.obs.resolved_path
        if path is None:
            continue
        encoded = _encode_photo_for_vision(path)
        if encoded is None:
            diag["rows_failed"] += 1
            seen_errors.add(f"photo encode failed: {path.name}")
            continue
        photo_b64, photo_mime = encoded
        diag["rows_called"] += 1

        text = row.observation_text_clean or row.obs.observation_text or ""
        try:
            raw = await _vision_call(
                photo_b64, photo_mime, text,
                site_address, audit_date_iso, api_key,
            )
        except httpx.HTTPStatusError as exc:
            diag["rows_failed"] += 1
            seen_errors.add(
                f"http {exc.response.status_code} on row {row.obs.csv_row}"
            )
            continue
        except Exception as exc:
            diag["rows_failed"] += 1
            seen_errors.add(f"{type(exc).__name__} on row {row.obs.csv_row}")
            log.warning(
                "vision call failed on row %s", row.obs.csv_row,
                exc_info=True,
            )
            continue

        try:
            rec = _coerce_record(raw)
        except Exception as exc:
            diag["rows_failed"] += 1
            seen_errors.add(f"parse error on row {row.obs.csv_row}: {exc}")
            continue

        row.conformance_status = rec["status"]
        row.ccvs_code = rec["ccvs_code"]
        row.ccvs_category = rec["ccvs_category"]
        if rec["finding"]:
            row.finding = rec["finding"]
        if rec["legal_ref"]:
            row.legal_ref = rec["legal_ref"]
        if rec["recommendation"]:
            row.recommendation = rec["recommendation"]
        if rec["monitoring_note"]:
            row.monitoring_note = rec["monitoring_note"]
        diag["rows_ok"] += 1

    diag["errors"] = sorted(seen_errors)
    return diag


async def generate_narrative_summary(
    rows: list[EnrichedRow],
    site_address: str,
    audit_date_iso: str,
) -> str:
    """Compose the Executive Summary paragraph after vision enrichment.

    Pulls from the now-populated ``finding`` + ``conformance_status``
    fields. Returns ``""`` when no Anthropic key is set or the call
    fails — caller substitutes the empty string into the template's
    ``{{NARRATIVE_SUMMARY}}`` placeholder.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return ""
    if not rows:
        return ""

    payload = [
        {
            "status": r.conformance_status,
            "ccvs_category": r.ccvs_category,
            "finding": r.finding or r.observation_text_clean,
        }
        for r in rows
    ]

    system = (
        "You write the Executive Summary paragraph at the top of an "
        "Australian construction site safety audit report. Output ONE "
        "paragraph, 100–140 words, no bullets, no headings, no lists. "
        "Open with the site address and audit date in a single "
        "sentence. Then summarise the audit's overall picture grounded "
        "in the findings supplied — note major non-conformance themes "
        "by hazard family, balance with positive observations. End "
        "with one sentence on the next-step posture (close out NCRs, "
        "monitor Conditional). Australian English, year-12 plain "
        "English. Banned vocabulary: crucial, pivotal, landscape, "
        "ensure, leverage, robust, comprehensive, navigate, delve, "
        "it's important to note, serves as, at its core. Do not "
        "invent counts, names, dates, or breaches not in the input. "
        "Return ONLY the paragraph text — no JSON, no quotes, no "
        "markdown."
    )
    user_text = (
        f"SITE: {site_address or '(unresolved)'}\n"
        f"AUDIT_DATE: {audit_date_iso}\n"
        f"FINDINGS:\n{json.dumps(payload, ensure_ascii=False)}"
    )
    body = {
        "model": VISION_MODEL,
        "max_tokens": 600,
        "system": system,
        "messages": [{"role": "user", "content": user_text}],
    }
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                ANTHROPIC_URL,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": ANTHROPIC_VERSION,
                    "content-type": "application/json",
                },
                json=body,
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"].strip()
    except Exception:
        log.warning("narrative summary generation failed", exc_info=True)
        return ""

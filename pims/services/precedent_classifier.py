"""pims/services/precedent_classifier.py

Backfill ccvs_code / ccvs_category on rows in pims_precedent_examples.

Two-pass strategy:
  1. Deterministic regex/keyword pass driven by the section_name and
     observation/finding text.
  2. Optional Claude Haiku batch pass for residue (rows still null).
     Low-confidence Haiku results are dropped — only high confidence
     writes back to the row.

CLI:
    python -m pims.services.precedent_classifier [--limit N] [--haiku]

Idempotent — only updates rows where ccvs_code IS NULL.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from typing import Optional

import httpx
from anthropic import Anthropic, APIStatusError

log = logging.getLogger(__name__)


# ---- Approved CCVS taxonomy (mirrors ENRICHMENT_SYSTEM in routes.py) ----

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

CATEGORY_BY_PREFIX = {
    "WAH": "Working at Height",
    "IRA": "Industrial Rope Access",
    "SIL": "Silica",
    "STR": "Structural",
    "MOB": "Mobile Plant",
    "CHM": "Chemicals",
    "ENE": "Energy",
    "SYS": "Systems",
}


# ---- Deterministic mapping ----

# Section-name → default CCVS (fallback when no keyword override).
SECTION_DEFAULT = {
    "rope access":                                ("IRA-H6", "Industrial Rope Access"),
    "general work at height":                     ("WAH-H6", "Working at Height"),
    "hazardous substances and silica control":    ("CHM-M3", "Chemicals"),
    "plant and equipment safety":                 ("MOB-H6", "Mobile Plant"),
    "worker competency and ppe":                  ("SYS-M4", "Systems"),
    "ppe and worker competency":                  ("SYS-M4", "Systems"),
    "planning and risk management (project value <$250k)":  ("SYS-M3", "Systems"),
    "planning and risk management (project value >$250k)":  ("SYS-M3", "Systems"),
    "planning and site establishment":            ("SYS-L2", "Systems"),
    "site security and other controls":           ("SYS-L2", "Systems"),
    "demolition and temporary works":             ("STR-H6", "Structural"),
    "energy and services":                        ("ENE-M4", "Energy"),
}


# Keyword → CCVS overrides. Highest-precedence list checked first.
KEYWORD_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bsilica\b|\bcrystalline silica\b|grind(ing|er)|jackhammer|chisel|puddle flange", re.I), "SIL-H6"),
    (re.compile(r"\bsds\b|safety data sheet|hazardous chemical|chemical register", re.I), "CHM-M3"),
    (re.compile(r"rope access|irata|sprat|descender|rope grab|harness register", re.I), "IRA-H6"),
    (re.compile(r"\bewp\b|elevated work platform|yellow card|psv|scissor lift|boom lift", re.I), "WAH-H6"),
    (re.compile(r"scaffold|swing[\s-]?stage|guardrail|handrail|edge protection", re.I), "WAH-H6"),
    (re.compile(r"ladder|fall from height|fall arrest|fall restraint|harness", re.I), "WAH-H6"),
    (re.compile(r"\bswms\b|toolbox talk|induction|sign[\s-]on|authoris(ed|ation)", re.I), "SYS-M4"),
    (re.compile(r"emergency plan|rescue plan|first aid", re.I), "SYS-H6"),
    (re.compile(r"electric(al)?|test and tag|leads?|rcd", re.I), "ENE-M4"),
    (re.compile(r"crane|forklift|telehandler|mobile plant|hoist", re.I), "MOB-H6"),
    (re.compile(r"propping|temporary works|demolition|structural support", re.I), "STR-H6"),
]


@dataclass
class ClassifyResult:
    ccvs_code: str
    ccvs_category: str
    method: str  # "keyword" | "section_default" | "haiku"


def deterministic_classify(text: str, section_name: Optional[str]) -> Optional[ClassifyResult]:
    """Return (code, category, method) or None when uncertain."""
    text_l = (text or "").lower()
    for rx, code in KEYWORD_RULES:
        if rx.search(text_l):
            cat = CATEGORY_BY_PREFIX.get(code.split("-")[0], None)
            if cat:
                return ClassifyResult(code, cat, "keyword")
    if section_name:
        sec_l = section_name.strip().lower()
        if sec_l in SECTION_DEFAULT:
            code, cat = SECTION_DEFAULT[sec_l]
            return ClassifyResult(code, cat, "section_default")
    return None


# ---- Haiku batch classifier (residue) ----

HAIKU_SYSTEM = """You are a WHS classifier for Australian construction.

Given a list of audit findings, return a JSON array. For EACH input item, return:

{
  "idx": <int — input index>,
  "ccvs_code": one of the approved codes below or null,
  "ccvs_category": category name or null,
  "confidence": "high" | "medium" | "low"
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

Categories: Working at Height, Industrial Rope Access, Silica, Structural,
Mobile Plant, Chemicals, Energy, Systems.

If uncertain, return ccvs_code: null AND confidence: "low". Do NOT guess.

Return ONLY a valid JSON array. No commentary, no markdown fences."""


def _build_haiku_user(items: list[dict]) -> str:
    lines = ["Items:"]
    for i, it in enumerate(items):
        sec = it.get("section_name") or "(no section)"
        txt = (it.get("text") or "")[:600]
        lines.append(f"[{i}] section={sec!r}: {txt}")
    return "\n".join(lines)


def haiku_classify_batch(items: list[dict], api_key: str) -> list[Optional[ClassifyResult]]:
    """Return a list aligned with `items`. Entry is None if confidence != high
    or code missing."""
    out: list[Optional[ClassifyResult]] = [None] * len(items)
    if not items:
        return out
    model_id = os.getenv("PIMS_PRECEDENT_MODEL", os.getenv("PIMS_ENRICHMENT_MODEL", "claude-haiku-4-5-20251001"))
    try:
        client = Anthropic(api_key=api_key, timeout=60)
        msg = client.messages.create(
            model=model_id,
            max_tokens=1024,
            system=HAIKU_SYSTEM,
            messages=[{"role": "user", "content": _build_haiku_user(items)}],
        )
        text = msg.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        parsed = json.loads(text)
    except APIStatusError as e:
        try:
            body_str = json.dumps(e.body, default=str) if isinstance(e.body, (dict, list)) else str(e.body)
        except Exception:
            body_str = repr(e.body)
        err_type = ""
        try:
            err_type = e.response.headers.get("anthropic-error-type", "") if getattr(e, "response", None) else ""
        except Exception:
            pass
        log.warning(
            f"Haiku classify batch APIStatusError model={model_id} "
            f"status={e.status_code} type={err_type!r} body={body_str[:2000]}"
        )
        return out
    except Exception as e:
        log.warning(f"Haiku classify batch failed model={model_id}: {e}")
        return out
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        idx = entry.get("idx")
        if not isinstance(idx, int) or not (0 <= idx < len(items)):
            continue
        code = entry.get("ccvs_code")
        cat = entry.get("ccvs_category")
        conf = (entry.get("confidence") or "").lower()
        if conf != "high" or code not in VALID_CCVS or not cat:
            continue
        out[idx] = ClassifyResult(code, cat, "haiku")
    return out


# ---- DB I/O via Supabase REST ----

def _supabase_headers(key: str, prefer: str = "return=representation") -> dict:
    return {"apikey": key, "Content-Type": "application/json", "Prefer": prefer}


def fetch_unclassified(url: str, key: str, limit: int = 0) -> list[dict]:
    params = {
        "select": "id,observation_text,finding_text,section_name",
        "ccvs_code": "is.null",
    }
    if limit:
        params["limit"] = str(limit)
    with httpx.Client(timeout=30) as c:
        r = c.get(f"{url}/rest/v1/pims_precedent_examples",
                  headers=_supabase_headers(key), params=params)
        r.raise_for_status()
        return r.json()


def patch_classification(url: str, key: str, row_id: str,
                         result: ClassifyResult) -> bool:
    with httpx.Client(timeout=30) as c:
        r = c.patch(
            f"{url}/rest/v1/pims_precedent_examples",
            headers=_supabase_headers(key, prefer="return=minimal"),
            params={"id": f"eq.{row_id}", "ccvs_code": "is.null"},
            json={"ccvs_code": result.ccvs_code,
                  "ccvs_category": result.ccvs_category},
        )
        if r.status_code not in (200, 204):
            log.warning(f"patch failed {r.status_code}: {r.text[:200]}")
            return False
    return True


# ---- CLI ----

def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--haiku", action="store_true",
                   help="Enable Haiku batch pass on deterministic residue.")
    args = p.parse_args(argv)

    url = os.getenv("RPD_SUPABASE_URL", "")
    key = os.getenv("RPD_SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        print("RPD_SUPABASE_URL / RPD_SUPABASE_SERVICE_KEY not set",
              file=sys.stderr)
        return 3

    rows = fetch_unclassified(url, key, args.limit)
    print(f"Fetched {len(rows)} unclassified rows")

    # Deterministic pass.
    det_updated = 0
    residue: list[dict] = []
    for row in rows:
        text = row.get("finding_text") or row.get("observation_text") or ""
        sec = row.get("section_name")
        res = deterministic_classify(text, sec)
        if res is None:
            residue.append(row)
            continue
        if patch_classification(url, key, row["id"], res):
            det_updated += 1
    print(f"Deterministic: assigned {det_updated} / {len(rows)}; "
          f"residue {len(residue)}")

    if args.haiku and residue:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            print("ANTHROPIC_API_KEY not set; skipping Haiku pass.",
                  file=sys.stderr)
            return 0
        BATCH = 10
        haiku_updated = 0
        for i in range(0, len(residue), BATCH):
            chunk = residue[i:i + BATCH]
            payload = []
            for r in chunk:
                payload.append({
                    "section_name": r.get("section_name"),
                    "text": (r.get("finding_text")
                             or r.get("observation_text") or ""),
                })
            results = haiku_classify_batch(payload, api_key)
            for r, res in zip(chunk, results):
                if res and patch_classification(url, key, r["id"], res):
                    haiku_updated += 1
        print(f"Haiku: assigned {haiku_updated} / {len(residue)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

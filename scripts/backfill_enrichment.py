"""Backfill observation_text_enriched for pims_staging records via Haiku."""
import json, os, httpx

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

ENRICHMENT_SYSTEM = """You are a WHS compliance classifier for Australian construction.

Given a field observation from a site safety audit, return a JSON object with:

{
  "observation_text_enriched": a professional rewrite of the observation in plain Australian English, suitable for a formal WHS audit report. 2-3 sentences. Must include the hazard, the finding, and the implication,
  "legal_reference": the single most relevant NSW legal reference — WHS Act 2011, WHS Regulation 2017 clause, or SafeWork NSW Code of Practice section. Format: "WHS Regulation 2017 cl 54" or "SafeWork NSW COP: Managing Risks of Falls at Workplaces s3.2". Null if Info status
}

APPROVED CCVS CODES context:
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

RPD SWMS REFERENCE:

WAH — Working at Height (WAH-H6, WAH-H9):
  Legal: WHS Regulation 2017 cl 228-244 (HRCW falls); SafeWork NSW COP: Managing Risks of Falls at Workplaces

EWP — Elevated Work Platform (WAH-H6):
  Controls: PSV on site; EWPA Yellow Card recorded; pre-start checklist signed before each shift; harness connected at all times on platform; rescue plan for incapacitated operator at height
  Legal: WHS Regulation 2017 cl 223-226; SafeWork NSW COP: Plant and Structures

SILICA — Silica Dust (SIL-H6, SIL-H9):
  Legal: WHS Regulation 2017 cl 407; SafeWork NSW COP: Managing Risks of Silica s2.3

CHEMICALS — Hazardous Chemicals (CHM-M3, CHM-H6):
  Legal: WHS Regulation 2017 cl 332-361; SafeWork NSW COP: Managing Risks of Hazardous Chemicals

SWING STAGE — Suspended Scaffold (WAH-H6, WAH-H9):
  Legal: WHS Regulation 2017 cl 228-244; AS/NZS 1576 (suspended scaffolding)

- Return ONLY valid JSON. No commentary, no markdown fences."""


def call_haiku(observation_text: str) -> dict:
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5",
                "max_tokens": 768,
                "system": ENRICHMENT_SYSTEM,
                "messages": [{"role": "user", "content": f"Observation: {observation_text}"}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get("content", [])
        if not content or not content[0].get("text"):
            raise ValueError(f"Empty response from Haiku: stop={data.get('stop_reason')} usage={data.get('usage')}")
        text = content[0]["text"].strip()
        print(f"  RAW: {text[:200]}")
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        parsed = json.loads(text.strip())
        # Handle Haiku returning null for enriched text
        if parsed.get("observation_text_enriched") is None:
            parsed["observation_text_enriched"] = None
        return parsed


# Records to enrich (id, seq_no, observation_text) — skip empty texts
RECORDS = [
    ("1119fee3-ad23-414b-a3f6-2db7fb34aff4", 10, "EWP pre-start checklist confirmed completed. Compliant - WHS Regulation 2017 cl.229."),
]

if __name__ == "__main__":
    for i, (rid, seq, text) in enumerate(RECORDS, 1):
        print(f"\n[{i}/{len(RECORDS)}] seq={seq} id={rid[:8]}...")
        print(f"  Input: {text[:80]}")
        try:
            result = call_haiku(text)
            enriched = result.get("observation_text_enriched")
            legal = result.get("legal_reference")
            if enriched:
                print(f"  Enriched: {enriched[:100]}...")
            else:
                print("  Enriched: NULL (Haiku declined to enrich)")
            print(f"  Legal: {legal}")
            print(f"  UPDATE_JSON: {json.dumps({'id': rid, 'observation_text_enriched': enriched, 'legal_reference': legal})}")
        except Exception as e:
            print(f"  ERROR: {e}")

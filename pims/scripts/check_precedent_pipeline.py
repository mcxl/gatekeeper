"""Smoke check for the precedent retrieval + supplement pipeline.

Pulls one recent staging row's observation_text, runs find_precedents,
builds the supplement, and prints both. Read-only.

Usage:
    python -m pims.scripts.check_precedent_pipeline [--text "..."]
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

import httpx

from pims.services.precedent_matcher import find_precedents
from pims.services.precedent_prompt import build_supplement


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--text", default=None,
                   help="Observation text to test (otherwise pull from staging)")
    args = p.parse_args()

    url = os.getenv("RPD_SUPABASE_URL", "")
    key = os.getenv("RPD_SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        print("RPD_SUPABASE_URL / RPD_SUPABASE_SERVICE_KEY not set",
              file=sys.stderr)
        return 3

    text = args.text
    if not text:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                f"{url}/rest/v1/pims_staging",
                headers={"apikey": key},
                params={
                    "select": "observation_text",
                    "order": "submitted_at.desc",
                    "limit": "1",
                },
            )
            r.raise_for_status()
            rows = r.json()
            if not rows:
                print("No staging rows found.", file=sys.stderr)
                return 1
            text = rows[0]["observation_text"]

    print(f"OBSERVATION:\n{text}\n")
    matches = await find_precedents(text, url, key, top_k=3)
    print(f"MATCHES ({len(matches)}):")
    for m in matches:
        print(f"  - {m.id}  score={m.score:.2f}  reasons={m.match_reasons}")
        print(f"    section={m.section_name}  ccvs={m.ccvs_code}")
    print()
    supplement = build_supplement(text, matches)
    print("SUPPLEMENT:")
    print(supplement or "(none)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

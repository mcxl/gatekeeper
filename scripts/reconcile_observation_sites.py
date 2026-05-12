"""scripts/reconcile_observation_sites.py

Phase 8 of docs/plans/PIMS_ENRICHMENT_AND_SITE_LINKAGE_FIX.md.

Iterates approved pims_observations rows with site_id IS NULL and tries
to resolve them via services.site_resolver. Updates rows that resolve
unambiguously. Leaves no-match and ambiguous rows alone (and logs them
for human review).

Phase 7 prevents new orphans at the source. This script catches:
  - rows created before Phase 7 deployed
  - rows whose sites row was created after the observation (the
    original Hampden Rd scenario)
  - rows whose site_address typo is fixed by a new entry in the
    site_resolver alias dict

Idempotent — safe to run on a schedule.

Usage:
    python scripts/reconcile_observation_sites.py [--dry-run] [--limit N]

Env required:
    RPD_SUPABASE_URL
    RPD_SUPABASE_SERVICE_KEY
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from pims.services.site_resolver import resolve_site_id  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("reconcile")

SUPABASE_URL = os.environ["RPD_SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["RPD_SUPABASE_SERVICE_KEY"]


def _headers(prefer: str = "return=minimal") -> dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


async def fetch_orphans(client: httpx.AsyncClient, limit: int) -> list[dict]:
    r = await client.get(
        f"{SUPABASE_URL}/rest/v1/pims_observations",
        headers=_headers("return=representation"),
        params={
            "site_id":       "is.null",
            "review_status": "eq.Approved",
            "staging":       "eq.false",
            "select":        "id,site_address",
            "limit":         str(limit),
        },
    )
    r.raise_for_status()
    return r.json()


async def patch_site_id(client: httpx.AsyncClient, obs_id: str, site_id: str) -> None:
    r = await client.patch(
        f"{SUPABASE_URL}/rest/v1/pims_observations",
        headers=_headers("return=minimal"),
        params={"id": f"eq.{obs_id}"},
        json={"site_id": site_id},
    )
    r.raise_for_status()


async def run(dry_run: bool, limit: int) -> int:
    fixed = 0
    no_match = 0
    ambiguous = 0
    blank_address = 0

    async with httpx.AsyncClient(timeout=30) as client:
        rows = await fetch_orphans(client, limit)
        log.info("found %d orphan approved observation(s)", len(rows))

        for row in rows:
            obs_id = row["id"]
            addr = row.get("site_address")
            if not addr:
                log.warning("BLANK obs=%s site_address is empty", obs_id)
                blank_address += 1
                continue

            resolved = await resolve_site_id(
                addr,
                supabase_url=SUPABASE_URL,
                supabase_key=SUPABASE_KEY,
                client=client,
            )
            if not resolved:
                # resolve_site_id returns None for both no-match and
                # ambiguous — log raw address so a human can decide.
                log.warning("UNRESOLVED obs=%s site_address=%r", obs_id, addr)
                no_match += 1
                continue

            if dry_run:
                log.info("DRY-RUN would patch obs=%s -> site_id=%s (addr=%r)", obs_id, resolved, addr)
            else:
                try:
                    await patch_site_id(client, obs_id, resolved)
                    log.info("PATCHED obs=%s -> site_id=%s (addr=%r)", obs_id, resolved, addr)
                except httpx.HTTPStatusError as e:
                    log.error("patch failed obs=%s: %s body=%s", obs_id, e, e.response.text[:300])
                    continue
            fixed += 1

    log.info(
        "summary: candidates=%d fixed=%d unresolved=%d blank_address=%d ambiguous_or_no_match=%d",
        len(rows), fixed, no_match, blank_address, ambiguous,
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=1000)
    args = ap.parse_args()
    return asyncio.run(run(dry_run=args.dry_run, limit=args.limit))


if __name__ == "__main__":
    raise SystemExit(main())

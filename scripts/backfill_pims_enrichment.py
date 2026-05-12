"""scripts/backfill_pims_enrichment.py

Phase 3 of docs/plans/PIMS_ENRICHMENT_AND_SITE_LINKAGE_FIX.md.

Re-runs Claude Haiku enrichment for pims_staging rows where
enrichment failed at submission time (enriched=false). PATCHes the
enrichment columns onto both pims_staging and the matching
pims_observations row (joined by staging_id).

HARD CONSTRAINT: this script must NEVER touch site_id, site_address,
review_status, approved_by, approved_at, or staging on either table.
Phase 4 owns site_id/site_address; Phase 6/7 own approval columns.

Usage:
    python scripts/backfill_pims_enrichment.py --site-id <uuid> [--dry-run]
    python scripts/backfill_pims_enrichment.py --ids a,b,c [--dry-run]

Env required:
    ANTHROPIC_API_KEY
    RPD_SUPABASE_URL
    RPD_SUPABASE_SERVICE_KEY
    PIMS_ENRICHMENT_MODEL (optional; defaults to dated Haiku 4.5)
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from pims.routes import enrich_observation, ENRICHMENT_SYSTEM  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("backfill")

SUPABASE_URL = os.environ["RPD_SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["RPD_SUPABASE_SERVICE_KEY"]

ENRICHMENT_COLUMNS = (
    "conformance_status",
    "ccvs_code",
    "ccvs_category",
    "ccvs_confidence",
    "action_required",
    "action_description",
    "responsible",
    "due_category",
    "monitoring_note",
    "observation_text_enriched",
    "legal_reference",
    "recommendation",
)


def _headers(prefer: str = "return=minimal") -> dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


async def fetch_staging_by_ids(client: httpx.AsyncClient, ids: list[str]) -> list[dict]:
    r = await client.get(
        f"{SUPABASE_URL}/rest/v1/pims_staging",
        headers=_headers("return=representation"),
        params={
            "id": f"in.({','.join(ids)})",
            "enriched": "eq.false",
            "select": "id,observation_text",
        },
    )
    r.raise_for_status()
    return r.json()


async def fetch_staging_ids_for_site(client: httpx.AsyncClient, site_id: str) -> list[str]:
    """Look up staging_ids of observations linked to this site."""
    r = await client.get(
        f"{SUPABASE_URL}/rest/v1/pims_observations",
        headers=_headers("return=representation"),
        params={
            "site_id": f"eq.{site_id}",
            "select": "staging_id",
        },
    )
    r.raise_for_status()
    return [row["staging_id"] for row in r.json() if row.get("staging_id")]


async def patch_staging(client: httpx.AsyncClient, staging_id: str, payload: dict) -> None:
    r = await client.patch(
        f"{SUPABASE_URL}/rest/v1/pims_staging",
        headers=_headers("return=minimal"),
        params={"id": f"eq.{staging_id}"},
        json=payload,
    )
    r.raise_for_status()


async def patch_observation_by_staging_id(
    client: httpx.AsyncClient, staging_id: str, payload: dict
) -> int:
    """Returns row count patched (0 if no observation exists for this staging_id)."""
    r = await client.patch(
        f"{SUPABASE_URL}/rest/v1/pims_observations",
        headers=_headers("return=representation"),
        params={"staging_id": f"eq.{staging_id}"},
        json=payload,
    )
    r.raise_for_status()
    return len(r.json())


async def run(staging_ids: list[str], dry_run: bool) -> None:
    model_id = os.getenv("PIMS_ENRICHMENT_MODEL", "claude-haiku-4-5-20251001")
    prompt_hash = hashlib.sha256(ENRICHMENT_SYSTEM.encode("utf-8")).hexdigest()[:16]
    log.info("backfill provenance: model=%s prompt_sha256_16=%s", model_id, prompt_hash)
    log.info("dry_run=%s ids=%d", dry_run, len(staging_ids))

    async with httpx.AsyncClient(timeout=60) as client:
        rows = await fetch_staging_by_ids(client, staging_ids)
        log.info("matched %d staging rows with enriched=false", len(rows))

        ok = 0
        skipped = 0
        failed = 0

        for row in rows:
            sid = row["id"]
            text = row.get("observation_text") or ""
            if not text.strip():
                log.warning("skip %s: empty observation_text", sid)
                skipped += 1
                continue

            try:
                enrichment = await enrich_observation(text)
            except Exception as e:
                log.error("enrich failed %s: %s", sid, e)
                failed += 1
                continue

            if not enrichment:
                log.warning("skip %s: enrichment returned empty dict", sid)
                skipped += 1
                continue

            patch_payload = {col: enrichment.get(col) for col in ENRICHMENT_COLUMNS}
            patch_payload["enriched"] = True
            patch_payload["enriched_at"] = datetime.now(timezone.utc).isoformat()

            if dry_run:
                log.info(
                    "DRY-RUN %s status=%s ccvs=%s action_req=%s enriched_len=%d",
                    sid,
                    patch_payload.get("conformance_status"),
                    patch_payload.get("ccvs_code"),
                    patch_payload.get("action_required"),
                    len(patch_payload.get("observation_text_enriched") or ""),
                )
                ok += 1
                continue

            # Phase 9.2 hardening: catch broader httpx.RequestError so
            # transient connection issues don't abort the whole loop
            # (the original Phase 3 run died on ConnectError mid-batch,
            # leaving 15 rows where the observation was patched but
            # staging silently lagged — the residue had to be repaired
            # by SQL). Retry each PATCH once with backoff. Verify the
            # staging row actually committed before touching observation.
            patched_via_retry = False
            for attempt in range(2):
                try:
                    await patch_staging(client, sid, patch_payload)
                    break
                except (httpx.HTTPStatusError, httpx.RequestError) as e:
                    if attempt == 0:
                        log.warning("patch_staging retry %s: %s", sid, type(e).__name__)
                        await asyncio.sleep(2.0)
                        continue
                    log.error("patch_staging failed %s: %s", sid, e)
                    failed += 1
                    patched_via_retry = False
                    break
            else:
                patched_via_retry = False
            # Verify staging row is now enriched=true before patching obs.
            try:
                r_check = await client.get(
                    f"{SUPABASE_URL}/rest/v1/pims_staging",
                    headers=_headers("return=representation"),
                    params={"id": f"eq.{sid}", "select": "enriched"},
                )
                r_check.raise_for_status()
                check_rows = r_check.json()
                if not check_rows or not check_rows[0].get("enriched"):
                    log.error("staging verify failed %s: not enriched after patch", sid)
                    failed += 1
                    continue
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                log.error("staging verify request failed %s: %s", sid, e)
                failed += 1
                continue
            # Staging confirmed enriched; now safe to patch observation.
            for attempt in range(2):
                try:
                    obs_patched = await patch_observation_by_staging_id(client, sid, patch_payload)
                    log.info(
                        "PATCHED staging=%s observations=%d status=%s ccvs=%s",
                        sid, obs_patched,
                        patch_payload.get("conformance_status"),
                        patch_payload.get("ccvs_code"),
                    )
                    ok += 1
                    patched_via_retry = True
                    break
                except (httpx.HTTPStatusError, httpx.RequestError) as e:
                    if attempt == 0:
                        log.warning("patch_observation retry %s: %s", sid, type(e).__name__)
                        await asyncio.sleep(2.0)
                        continue
                    log.error("patch_observation failed %s: %s — staging is enriched=true but observation lags",
                              sid, e)
                    failed += 1
                    break
            if not patched_via_retry and ok == 0:
                pass  # already counted in failed

        log.info("summary: ok=%d skipped=%d failed=%d", ok, skipped, failed)


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--site-id", help="Resolve staging_ids via pims_observations.site_id")
    g.add_argument("--ids", help="Comma-separated staging row ids")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.ids:
        ids = [s.strip() for s in args.ids.split(",") if s.strip()]
    else:
        async def _collect() -> list[str]:
            async with httpx.AsyncClient(timeout=30) as client:
                return await fetch_staging_ids_for_site(client, args.site_id)
        ids = asyncio.run(_collect())

    if not ids:
        log.error("no staging ids resolved")
        return 1

    asyncio.run(run(ids, dry_run=args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

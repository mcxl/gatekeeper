"""Backfill photo_url for SSA observations promoted from a DRAFT.md import.

Background — observations loaded into pims_observations from the SSA
pipeline's *.md draft carry only text labels ("Photo 3") in photo_refs.
The image bytes are never uploaded to the pims-photos bucket and
photo_url stays null, so the dashboard shows no thumbnail.

This script resolves each "Photo N" label to its local evidence file via
the audit's reviewed-observations.json (photo_ref -> storage_path), PUTs
the bytes to pims-photos/RPD-SSA/<uuid>.jpg, and PATCHes the row with the
public photo_url + filename. The first listed photo becomes photo_url;
any additional referenced photos are uploaded too (future-proofing).

Idempotent — re-running upserts the storage object and re-applies the
same PATCH. Scoped to one audit via SOURCE_PDF_PREFIX.

Usage:
    python scripts/backfill_ssa_photos.py \
        --output-dir "C:/.../audit-concierge/outputs/RPD-SSA-260528-01" \
        --source-pdf-prefix "RPD-SSA-260528-01"

Env required (from gatekeeper/.env):
    SUPABASE_URL              (or RPD_SUPABASE_URL)
    SUPABASE_SERVICE_ROLE_KEY (or RPD_SUPABASE_SERVICE_KEY)
"""
from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import os
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ssa-photo-backfill")

BUCKET = "pims-photos"
AUDIT_REF = "RPD-SSA"


def _load_env() -> tuple[str, str]:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    url = os.environ.get("RPD_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = (
        os.environ.get("RPD_SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    )
    if not url or not key:
        raise RuntimeError("Supabase URL/service key missing in gatekeeper/.env")
    return url.rstrip("/"), key


def _rest_headers(key: str, prefer: str = "return=minimal") -> dict[str, str]:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def _build_photo_map(output_dir: Path) -> dict[str, Path]:
    """photo_ref ('Photo 3') -> absolute local image path, from reviewed JSON."""
    reviewed = output_dir / "reviewed-observations.json"
    data = json.loads(reviewed.read_text(encoding="utf-8"))
    mapping: dict[str, Path] = {}
    for obs in data:
        ref = obs.get("photo_ref")
        sp = obs.get("storage_path")
        if ref and sp:
            mapping[ref.strip()] = (output_dir / sp).resolve()
    return mapping


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--source-pdf-prefix", required=True,
                    help="e.g. RPD-SSA-260528-01 — matches source_pdf LIKE prefix%%")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    output_dir = Path(args.output_dir).resolve()
    photo_map = _build_photo_map(output_dir)
    log.info("photo_ref -> file map: %d entries", len(photo_map))

    supabase_url, service_key = _load_env()

    with httpx.Client(timeout=60) as client:
        r = client.get(
            f"{supabase_url}/rest/v1/pims_observations",
            headers=_rest_headers(service_key, prefer="return=representation"),
            params={
                "select":      "id,site_address,photo_refs,photo_url,filename",
                "source_pdf":  f"like.{args.source_pdf_prefix}%",
                "photo_url":   "is.null",
                "photo_refs":  "not.is.null",
            },
        )
        r.raise_for_status()
        rows = r.json()
        log.info("candidate rows (photo_url null, photo_refs set): %d", len(rows))

        uploaded = patched = missing = 0
        for row in rows:
            obs_id = row["id"]
            refs = [t.strip() for t in (row.get("photo_refs") or "").split(",") if t.strip()]
            first_public_url: str | None = None
            first_filename: str | None = None

            for ref in refs:
                local = photo_map.get(ref)
                if not local or not local.exists():
                    log.warning("MISSING ref=%r obs=%s — not in photo map/disk", ref, obs_id)
                    missing += 1
                    continue
                filename = local.name  # uuid.jpg — globally unique
                storage_path = f"{AUDIT_REF}/{filename}"
                public_url = f"{supabase_url}/storage/v1/object/public/{BUCKET}/{storage_path}"
                if first_public_url is None:
                    first_public_url, first_filename = public_url, filename

                if args.dry_run:
                    log.info("DRY obs=%s ref=%s -> %s", obs_id, ref, storage_path)
                    continue

                content_type = mimetypes.guess_type(filename)[0] or "image/jpeg"
                put = client.put(
                    f"{supabase_url}/storage/v1/object/{BUCKET}/{storage_path}",
                    headers={
                        "apikey": service_key,
                        "Authorization": f"Bearer {service_key}",
                        "Content-Type": content_type,
                        "x-upsert": "true",
                    },
                    content=local.read_bytes(),
                )
                if put.status_code not in (200, 201):
                    log.error("UPLOAD-FAIL obs=%s ref=%s %s %s",
                              obs_id, ref, put.status_code, put.text[:200])
                    continue
                uploaded += 1
                log.info("UPLOADED obs=%s ref=%s -> %s", obs_id, ref, storage_path)

            if first_public_url and not args.dry_run:
                patch = client.patch(
                    f"{supabase_url}/rest/v1/pims_observations",
                    headers=_rest_headers(service_key, prefer="return=minimal"),
                    params={"id": f"eq.{obs_id}"},
                    json={"photo_url": first_public_url, "filename": first_filename},
                )
                if patch.status_code not in (200, 204):
                    log.error("PATCH-FAIL obs=%s %s %s", obs_id, patch.status_code, patch.text[:200])
                    continue
                patched += 1

    log.info("summary: rows=%d uploaded=%d patched=%d missing=%d",
             len(rows), uploaded, patched, missing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""One-off recovery: upload Le Vesinet 2026-05-12 photos to Supabase Storage.

Background — the Site Visit Report xlsx upload at /pims/upload/observations
carries photo filenames into pims_observations.photo_refs but does NOT
upload the actual image bytes to the pims-photos storage bucket. The
dashboard renders from photo_url, so rows show an em-dash with no
thumbnail.

This script walks the affected rows for site
12-14 Le Vesinet Dr Hunters Hill (id c4105174-18dc-4dd9-b6c5-f1cf523cb03a),
finds each photo_refs filename in the local evidence folder, PUTs the
bytes to pims-photos/RPD-SSA/<filename>, and PATCHes the row with the
public photo_url + filename.

Idempotent — re-running overwrites the storage object and re-applies
the same PATCH. Limited to the Le Vesinet site by design; broaden the
SITE_ID constant only after reviewing the candidate rows.

Env required (from gatekeeper/.env):
    SUPABASE_URL              (or RPD_SUPABASE_URL)
    SUPABASE_SERVICE_ROLE_KEY (or RPD_SUPABASE_SERVICE_KEY)
"""
from __future__ import annotations

import logging
import mimetypes
import os
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("photo-upload")

SITE_ID    = "c4105174-18dc-4dd9-b6c5-f1cf523cb03a"
AUDIT_REF  = "RPD-SSA"
EVIDENCE   = Path(r"G:\My Drive\alan_mcxico\SSA-evidence\2026-05-12-RPD")
BUCKET     = "pims-photos"


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
        raise RuntimeError(
            "Supabase URL/service key missing. Expected SUPABASE_URL + "
            "SUPABASE_SERVICE_ROLE_KEY (or RPD_-prefixed) in gatekeeper/.env"
        )
    return url.rstrip("/"), key


def _rest_headers(key: str, prefer: str = "return=minimal") -> dict[str, str]:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def _find_evidence(filename: str) -> Path | None:
    """Case-insensitive resolve filename in the evidence folder."""
    if not EVIDENCE.exists():
        return None
    target = filename.lower()
    for p in EVIDENCE.iterdir():
        if p.is_file() and p.name.lower() == target:
            return p
    return None


def main() -> int:
    supabase_url, service_key = _load_env()

    with httpx.Client(timeout=60) as client:
        # Fetch candidate rows.
        r = client.get(
            f"{supabase_url}/rest/v1/pims_observations",
            headers=_rest_headers(service_key, prefer="return=representation"),
            params={
                "select":         "id,photo_refs,filename,photo_url",
                "site_id":        f"eq.{SITE_ID}",
                "staging":        "eq.false",
                "review_status":  "eq.Approved",
                "photo_url":      "is.null",
                "photo_refs":     "not.is.null",
            },
        )
        r.raise_for_status()
        rows = r.json()
        log.info("found %d candidate rows", len(rows))

        uploaded = 0
        skipped_missing = 0
        for row in rows:
            obs_id = row["id"]
            ref = (row.get("photo_refs") or "").strip()
            if not ref:
                continue
            # photo_refs may be a single filename or a comma list — first wins.
            filename = ref.split(",")[0].strip()
            evidence_path = _find_evidence(filename)
            if not evidence_path:
                log.warning("MISSING file=%r obs=%s — not in evidence folder", filename, obs_id)
                skipped_missing += 1
                continue

            content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            storage_path = f"{AUDIT_REF}/{filename}"
            storage_url  = f"{supabase_url}/storage/v1/object/{BUCKET}/{storage_path}"
            public_url   = f"{supabase_url}/storage/v1/object/public/{BUCKET}/{storage_path}"

            put = client.put(
                storage_url,
                headers={
                    "apikey":        service_key,
                    "Authorization": f"Bearer {service_key}",
                    "Content-Type":  content_type,
                    "x-upsert":      "true",
                },
                content=evidence_path.read_bytes(),
            )
            if put.status_code not in (200, 201):
                log.error("UPLOAD-FAIL obs=%s file=%s %s %s",
                          obs_id, filename, put.status_code, put.text[:200])
                continue

            patch = client.patch(
                f"{supabase_url}/rest/v1/pims_observations",
                headers=_rest_headers(service_key, prefer="return=minimal"),
                params={"id": f"eq.{obs_id}"},
                json={"photo_url": public_url, "filename": filename},
            )
            if patch.status_code not in (200, 204):
                log.error("PATCH-FAIL obs=%s %s %s", obs_id, patch.status_code, patch.text[:200])
                continue
            uploaded += 1
            log.info("UPLOADED obs=%s -> %s", obs_id, storage_path)

    log.info("summary: candidates=%d uploaded=%d missing_in_folder=%d",
             len(rows), uploaded, skipped_missing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

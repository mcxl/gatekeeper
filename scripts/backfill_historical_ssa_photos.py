"""Controlled photo backfill for the historical PIMS SSA import.

The historical spreadsheet import kept the finding text but lost its photo
links. This script links only explicitly matched photos from the same audit
folder, site, date, and finding. It never deletes rows or photos.

Run a dry run first, then repeat with ``--apply``.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


BUCKET = "pims-photos"
SOURCE_PDF = "PIMS_SSA_NCR_historical_import.xlsx"
AUDIT_ROOT = Path(r"C:\Users\AlanRichardson\OneDrive - AuditCo\RPD\SSA")
CONTROLLED_ROOT = Path(
    r"C:\Users\AlanRichardson\Documents\agentic-os-workspace\audit-concierge\controlled\pims-photo-backfill-2026-08-31"
)


def norm(value: str | None) -> str:
    """Normalize punctuation and spaces for address matching."""
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


AUDITS: list[dict[str, Any]] = [
    {
        "key": "mount-st-pyrmont-260811",
        "site": "17-29 Mount St Pyrmont",
        "date": "2026-08-11",
        "folder": "SSA - 17-29 Mount St Pyrmont 260811",
        "version": "SSA - 260811-V1",
    },
    {
        "key": "elizabeth-bay-260813",
        "site": "2 Elizabeth Bay Cres Elizabeth Bay",
        "date": "2026-08-13",
        "folder": "SSA - 2 Elizabeth Bay Cr Elizabeth Bay 260813",
        "version": "SSA - 260813-V1",
    },
    {
        "key": "milson-point-260811",
        "site": "39-43 Milson Point Rd Cremorne Point",
        "date": "2026-08-11",
        "folder": "SSA - 39-43 Milson Point Rd Cremorne Point 260811",
        "version": "SSA - 260811-V1",
    },
    {
        "key": "hampden-russel-lea-260813",
        "site": "96-98 Hampden Rd Russel Lea",
        "date": "2026-08-13",
        "folder": "SSA - 96-98 Hampden Rd Russel Lea 260813",
        "version": "SSA - 260813-V1",
    },
    {
        "key": "russel-st-lilyfield-260813",
        "site": "13-29 Russel Street Lilyfield",
        "date": "2026-08-13",
        "folder": "SSA -13 Russell St Lilyfield 260813",
        "version": "SSA - 260813-V1",
    },
]


# Each rule is deliberately specific. A rule must match the row's site/date,
# section, and all finding keywords. Source keywords then disambiguate duplicate
# photo references such as Mount St Photo 8.
RULES: list[dict[str, Any]] = [
    {
        "audit": "mount-st-pyrmont-260811",
        "section": "3.1",
        "keywords": ["shabir nazari"],
        "photo_ref": "Photo 8",
        "source_keywords": ["shabir nazari"],
    },
    {
        "audit": "elizabeth-bay-260813",
        "section": "3.1",
        "keywords": ["daily sign-in"],
        "photo_ref": "Photo 6",
        "source_keywords": ["attendance"],
    },
    {
        "audit": "elizabeth-bay-260813",
        "section": "8.8",
        "keywords": ["paint containers", "gas meters"],
        "photo_ref": "Photo 8",
        "source_keywords": ["covered exterior area", "metal staircase"],
    },
    {
        "audit": "milson-point-260811",
        "section": "1.2",
        "keywords": ["project risk assessment"],
        "photo_ref": "Photo 11",
        "source_keywords": ["project risk assessment"],
    },
    {
        "audit": "milson-point-260811",
        "section": "3.1",
        "keywords": ["safety meeting form", "none currently active"],
        "photo_ref": "Photo 13",
        "source_keywords": ["safety meeting form", "none currently active"],
    },
    {
        "audit": "milson-point-260811",
        "section": "4.6",
        "keywords": ["access ladder", "scaffold landing"],
        "photo_ref": "Photo 8",
        "source_keywords": ["ladder", "scaffold working platform"],
    },
    {
        "audit": "milson-point-260811",
        "section": "7.1",
        "keywords": ["electrical leads", "rcd box"],
        "photo_ref": "Photo 4",
        "source_keywords": ["electrical leads", "rcd box"],
    },
    {
        "audit": "milson-point-260811",
        "section": "8.2",
        "keywords": ["ardex wpm 405"],
        "photo_ref": "Photo 2",
        "source_keywords": ["ardex wpm 405"],
    },
    {
        "audit": "hampden-russel-lea-260813",
        "section": "7.1",
        "keywords": ["test-and-tag due date"],
        "photo_ref": "Photo 4",
        "source_keywords": ["test/inspection tag"],
    },
]


def load_env() -> tuple[str, str]:
    """Load the service key from the controlled local environment only."""
    env_file = Path(
        r"C:\Users\AlanRichardson\Documents\agentic-os-workspace\audit-concierge\.env"
    )
    if env_file.exists():
        for raw in env_file.read_text(encoding="utf-8").splitlines():
            if not raw.strip() or raw.lstrip().startswith("#") or "=" not in raw:
                continue
            name, value = raw.split("=", 1)
            os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))
    url = (os.environ.get("RPD_SUPABASE_URL") or "").rstrip("/")
    key = os.environ.get("RPD_SUPABASE_SERVICE_KEY") or ""
    if not url or not key:
        raise RuntimeError("RPD Supabase URL/service key is not available")
    return url, key


def headers(key: str, prefer: str = "return=minimal") -> dict[str, str]:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def source_paths(audit: dict[str, Any]) -> tuple[Path, Path]:
    root = AUDIT_ROOT / audit["folder"]
    # Lilyfield has one extra nested folder in OneDrive.
    if not root.exists() and audit["key"] == "russel-st-lilyfield-260813":
        children = list(AUDIT_ROOT.glob("SSA -13 Russell St Lilyfield 260813*"))
        if children:
            root = children[0]
    files = root / f'{audit["version"]} - files'
    photos = root / f'{audit["version"]} - photos'
    if audit["key"] == "russel-st-lilyfield-260813" and not files.exists():
        nested = next((p for p in root.iterdir() if p.is_dir()), root)
        files = nested / f'{audit["version"]} - files'
        photos = nested / f'{audit["version"]} - photos'
    return files, photos


def load_source_entries(audit: dict[str, Any]) -> list[dict[str, Any]]:
    files, _ = source_paths(audit)
    reviewed = files / "reviewed-observations.json"
    if not reviewed.exists():
        return []
    return json.loads(reviewed.read_text(encoding="utf-8"))


def section_of(text: str) -> str:
    return text.split(" -", 1)[0].strip()


def match_row(row: dict[str, Any], sources: dict[str, list[dict[str, Any]]], audits: dict[str, dict[str, Any]]) -> dict[str, Any]:
    site = norm(row.get("site_address"))
    date = row.get("observation_date") or row.get("audit_date")
    candidates: list[dict[str, Any]] = []
    text = (row.get("observation_text") or "").lower()
    section = section_of(row.get("observation_text") or "")
    for rule in RULES:
        audit = audits[rule["audit"]]
        if norm(audit["site"]) != site or audit["date"] != date:
            continue
        if section != rule["section"]:
            continue
        if not all(word in text for word in rule["keywords"]):
            continue
        candidates.append(rule)
    if len(candidates) != 1:
        return {"status": "ambiguous" if candidates else "unmatched", "row_id": row["id"], "reason": "rule count %d" % len(candidates)}
    rule = candidates[0]
    audit = audits[rule["audit"]]
    entries = [
        e for e in sources[rule["audit"]]
        if (e.get("photo_ref") or "").strip() == rule["photo_ref"]
        and all(k in (e.get("finding") or "").lower() for k in rule["source_keywords"])
    ]
    if len(entries) != 1:
        return {"status": "ambiguous" if entries else "unmatched", "row_id": row["id"], "reason": "source entry count %d" % len(entries)}
    files, photos = source_paths(audit)
    source = entries[0]
    local = (photos / source["storage_path"]).resolve()
    if not local.exists():
        return {"status": "unmatched", "row_id": row["id"], "reason": f"missing source photo: {local}"}
    return {
        "status": "matched",
        "row_id": row["id"],
        "site_address": row.get("site_address"),
        "observation_date": date,
        "section": section,
        "audit_key": rule["audit"],
        "source_observation_id": source.get("observation_id"),
        "photo_ref": rule["photo_ref"],
        "source_finding": source.get("finding"),
        "local_path": str(local),
        "storage_path": f'RPD-SSA/historical/{rule["audit"]}/{local.name}',
    }


def get_rows(session: requests.Session, url: str, key: str) -> list[dict[str, Any]]:
    response = session.get(
        f"{url}/rest/v1/pims_observations",
        headers=headers(key, "return=representation"),
        params={
            "select": "id,site_address,observation_date,audit_date,observation_text,photo_url,photo_refs,filename,source_pdf",
            "source_pdf": f"eq.{SOURCE_PDF}",
            "photo_url": "is.null",
            "order": "observation_date.desc,created_at.asc,id.asc",
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def count_table(session: requests.Session, url: str, key: str, table: str) -> int:
    response = session.get(
        f"{url}/rest/v1/{table}",
        headers={**headers(key, "return=minimal"), "Prefer": "count=exact"},
        params={"select": "id", "limit": "1"},
        timeout=60,
    )
    response.raise_for_status()
    content_range = response.headers.get("content-range", "")
    return int(content_range.split("/")[-1]) if "/" in content_range else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="upload and patch matched rows")
    args = parser.parse_args()
    url, key = load_env()
    audits = {a["key"]: a for a in AUDITS}
    sources = {a["key"]: load_source_entries(a) for a in AUDITS}
    session = requests.Session()
    before_obs = count_table(session, url, key, "pims_observations")
    before_staging = count_table(session, url, key, "pims_staging")
    rows = get_rows(session, url, key)
    manifest: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "apply" if args.apply else "dry-run",
        "source_pdf": SOURCE_PDF,
        "before_counts": {"pims_observations": before_obs, "pims_staging": before_staging},
        "matches": [],
        "unmatched": [],
        "applied": [],
    }
    for row in rows:
        result = match_row(row, sources, audits)
        if result["status"] == "matched":
            manifest["matches"].append(result)
        else:
            manifest["unmatched"].append(result)
    if args.apply:
        for item in manifest["matches"]:
            local = Path(item["local_path"])
            public_url = f"{url}/storage/v1/object/public/{BUCKET}/{item['storage_path']}"
            upload = session.put(
                f"{url}/storage/v1/object/{BUCKET}/{item['storage_path']}",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "image/jpeg",
                    "x-upsert": "true",
                },
                data=local.read_bytes(),
                timeout=120,
            )
            upload.raise_for_status()
            patch = session.patch(
                f"{url}/rest/v1/pims_observations",
                headers=headers(key),
                params={"id": f"eq.{item['row_id']}"},
                json={"photo_url": public_url, "filename": local.name, "photo_refs": item["photo_ref"]},
                timeout=60,
            )
            patch.raise_for_status()
            item = {**item, "public_url": public_url, "status": "applied"}
            manifest["applied"].append(item)
    after_obs = count_table(session, url, key, "pims_observations")
    after_staging = count_table(session, url, key, "pims_staging")
    manifest["after_counts"] = {"pims_observations": after_obs, "pims_staging": after_staging}
    manifest["counts_unchanged"] = before_obs == after_obs and before_staging == after_staging
    CONTROLLED_ROOT.mkdir(parents=True, exist_ok=True)
    output = CONTROLLED_ROOT / ("manifest-apply.json" if args.apply else "manifest-dry-run.json")
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "mode": manifest["mode"],
        "candidate_rows": len(rows),
        "matched": len(manifest["matches"]),
        "unmatched": len(manifest["unmatched"]),
        "applied": len(manifest["applied"]),
        "counts_unchanged": manifest["counts_unchanged"],
        "manifest": str(output),
    }))
    if manifest["unmatched"]:
        for item in manifest["unmatched"]:
            print(f"UNMATCHED {item['row_id']}: {item['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

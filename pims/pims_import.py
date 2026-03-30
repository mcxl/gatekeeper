#!/usr/bin/env python3
"""
pims_import.py — Import enriched PIMS XLSX into Supabase
Uses httpx directly — no supabase Python package required.

Usage:
    python pims_import.py PIMS_Unitas_Enriched.xlsx --dry-run
    python pims_import.py PIMS_Unitas_Enriched.xlsx
"""

import sys
import os
import argparse
import json
import httpx
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL  = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY  = os.getenv("SUPABASE_ANON_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env")
    sys.exit(1)

HEADERS = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "return=representation",
}


def post(table: str, data: list) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    r = httpx.post(url, headers=HEADERS, content=json.dumps(data), timeout=30)
    if r.status_code not in (200, 201):
        raise Exception(f"Insert failed [{r.status_code}]: {r.text[:300]}")
    return r.json()


def clean(val):
    if val is None:
        return None
    if isinstance(val, float) and str(val) == 'nan':
        return None
    s = str(val).strip()
    return s if s and s.lower() not in ('nan', 'none', '') else None


def import_pims(xlsx_path: str, dry_run: bool = False):
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Importing: {xlsx_path}\n")

    df = pd.read_excel(xlsx_path, sheet_name="Enriched Register", header=0)
    df = df.fillna('')

    # ── Audit metadata ──
    print("Audit details (press Enter to accept default):")
    site_name  = input("  Site name [Unitas Business Park, Rouse Hill]: ").strip() or "Unitas Business Park, Rouse Hill"
    address    = input("  Site address [Rouse Hill NSW 2155]: ").strip() or "Rouse Hill NSW 2155"
    pc         = input("  Principal contractor [SD Group]: ").strip() or "SD Group"
    audit_date = input("  Audit date [2026-02-26]: ").strip() or "2026-02-26"
    auditor    = input("  Auditor name: ").strip() or "Unknown"
    audit_ref  = input(f"  Audit ref [Unitas-2026-02-26]: ").strip() or "Unitas-2026-02-26"

    audit_row = {
        "audit_ref":            audit_ref,
        "site_name":            site_name,
        "site_address":         address,
        "principal_contractor": pc,
        "audit_date":           audit_date,
        "auditor":              auditor,
    }

    if dry_run:
        print(f"\n[DRY RUN] Would create audit: {audit_row}")
    else:
        result = post("pims_audits", [audit_row])
        audit_id = result[0]["id"]
        print(f"\n✓ Audit created: {audit_id}")

    # ── Build observation rows ──
    observations = []
    for _, row in df.iterrows():
        seq = clean(row.get('#'))
        if not seq:
            continue
        obs = {
            "seq_no":             int(seq),
            "photo_id":           clean(row.get('Photo ID')),
            "filename":           clean(row.get('Filename')),
            "observation_date":   clean(row.get('Observation Date')),
            "observation_text":   clean(row.get('Observation')) or "",
            "conformance_status": clean(row.get('Conformance Status')),
            "ccvs_code":          clean(row.get('CCVS Code')),
            "ccvs_category":      clean(row.get('CCVS Category')),
            "action_required":    str(row.get('Action Required', '')).strip() == 'Yes',
            "action_description": clean(row.get('Action Description')),
            "responsible":        clean(row.get('Responsible')),
            "due_category":       clean(row.get('Due')) or 'N/A',
            "monitoring_note":    clean(row.get('Monitoring Note')),
            "closeout_status":    clean(row.get('Close-out Status')) or 'N/A',
        }
        observations.append(obs)

    print(f"\nPrepared {len(observations)} observation rows")

    if dry_run:
        print("\n[DRY RUN] First 5 rows:")
        for r in observations[:5]:
            print(f"  #{r['seq_no']:02d} | {r['conformance_status']:<12} | {r['ccvs_code'] or '—':<10} | {(r['action_description'] or '—')[:70]}")
        print(f"\n  ... and {len(observations)-5} more rows")
        print("\n[DRY RUN] Nothing written. Remove --dry-run to import live.")
        return

    # ── Insert in batches ──
    batch = [{**o, "audit_id": audit_id} for o in observations]
    BATCH = 50
    inserted = 0
    for i in range(0, len(batch), BATCH):
        chunk = batch[i:i+BATCH]
        post("pims_observations", chunk)
        inserted += len(chunk)
        print(f"  Inserted {inserted}/{len(batch)}...")

    print(f"\n✓ Done. {inserted} observations imported.")
    print(f"✓ Open pims_dashboard.html in your browser to view the dashboard.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("xlsx", help="Path to enriched XLSX file")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    import_pims(args.xlsx, dry_run=args.dry_run)

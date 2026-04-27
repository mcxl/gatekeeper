"""Local renderer for the Site Visit Report — fetches live PIMS data from
Supabase and writes a .docx to disk. No FastAPI server required.

Use cases:
  - QA / spec compliance review without waiting on a Railway deploy.
  - Reproducing a 500 / blank-output incident from a real site_id.
  - Exporting a one-off report for a stakeholder.

Required env (typically via .env or shell):
  RPD_SUPABASE_URL              https://<project>.supabase.co
  RPD_SUPABASE_SERVICE_KEY      service_role key (DOES bypass RLS;
                                handle accordingly — never log)

Usage:
  python scripts/render_site_visit_report.py --site-id <uuid>
  python scripts/render_site_visit_report.py --address "1208 Pacific Highway Pymble"
  python scripts/render_site_visit_report.py --site-id <uuid> --output ~/Downloads/report.docx
  python scripts/render_site_visit_report.py --site-id <uuid> --include-pending

By default, observations are filtered as the live route does
(staging=false AND source_pdf IS NULL AND review_status='Approved').
Use --include-pending to also include Pending review_status — handy
when QA-testing against a site whose observations have not been
approved yet (the rpd-pims pilot is in this state at the time of
writing).
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

import httpx

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from pims.services.checklist_matcher import (  # noqa: E402
    ChecklistItem,
    cross_reference,
)
from pims.services.site_visit_report import (  # noqa: E402
    SiteContext,
    build,
)


def _supabase_get(url: str, service_key: str, path: str, params: dict) -> list:
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Accept": "application/json",
    }
    full = f"{url}/rest/v1/{path}?{urlencode(params, safe=',')}"
    with httpx.Client(timeout=30) as client:
        r = client.get(full, headers=headers)
        r.raise_for_status()
        return r.json()


def _resolve_site(url, key, *, site_id: str | None, address: str | None) -> dict:
    if site_id:
        rows = _supabase_get(url, key, "sites", {
            "select": "id,address_raw,project_value,client_name",
            "id": f"eq.{site_id}",
        })
    else:
        rows = _supabase_get(url, key, "sites", {
            "select": "id,address_raw,project_value,client_name",
            "address_raw": f"eq.{address}",
        })
    if not rows:
        raise SystemExit(f"site not found: site_id={site_id} address={address}")
    site = rows[0]
    if site.get("project_value") is None:
        raise SystemExit(
            f"site {site['address_raw']!r} has no project_value — "
            "ineligible for audit-report generation"
        )
    return site


def _fetch_checklist(url, key, tier: str) -> list[ChecklistItem]:
    rows = _supabase_get(url, key, "checklist_items", {
        "select": ("id,category_no,category_name,item_no,criteria,"
                   "instruction,ccvs_category,ccvs_code,project_value_tier"),
        "project_value_tier": f"eq.{tier}",
        "order": "category_no.asc,item_no.asc",
    })
    return [ChecklistItem.from_row(r) for r in rows]


def _fetch_observations(url, key, site_id: str, *, include_pending: bool) -> list[dict]:
    """Paginated fetch via PostgREST Range headers — same shape as the
    live route's _fetch_observations_for_site."""
    select = (
        "id,seq_no,site_address,observation_text,observation_text_enriched,"
        "conformance_status,ccvs_code,ccvs_category,action_required,"
        "action_description,responsible,due_category,legal_reference,"
        "filename,photo_url,photo_refs,observation_date,audit_id,"
        "submitted_by,prepared_by,review_status"
    )
    filters = {
        "select": select,
        "site_id": f"eq.{site_id}",
        "staging": "eq.false",
        "source_pdf": "is.null",
        "order": "observation_date.asc",
    }
    if not include_pending:
        filters["review_status"] = "eq.Approved"

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }
    out: list[dict] = []
    PAGE = 1000
    with httpx.Client(timeout=30) as client:
        for page in range(50):
            start, end = page * PAGE, page * PAGE + PAGE - 1
            qp = filters.copy()
            full = f"{url}/rest/v1/pims_observations?{urlencode(qp, safe=',')}"
            r = client.get(full, headers={
                **headers, "Range-Unit": "items", "Range": f"{start}-{end}",
            })
            r.raise_for_status()
            batch = r.json()
            out.extend(batch)
            if len(batch) < PAGE:
                return out
    raise SystemExit("observation pagination exceeded 50 pages")


def _resolve_audit_ref(url, key, observations: list[dict]) -> str:
    audit_ids = [o.get("audit_id") for o in observations if o.get("audit_id")]
    if not audit_ids:
        return ""
    rows = _supabase_get(url, key, "pims_audits", {
        "select": "audit_ref,audit_date",
        "id": "in.(" + ",".join(audit_ids) + ")",
        "order": "audit_date.desc",
        "limit": "1",
    })
    if not rows:
        return ""
    return (rows[0].get("audit_ref") or "").strip()


def _format_date_range(observations: list[dict]) -> str:
    dates = sorted(o["observation_date"] for o in observations
                   if o.get("observation_date"))
    if not dates:
        return "—"
    return f"{dates[0]} – {dates[-1]}"


def main() -> int:
    parser = argparse.ArgumentParser()
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--site-id", help="canonical sites.id (uuid)")
    src.add_argument("--address", help="sites.address_raw exact match")
    parser.add_argument("--output", default=None,
                        help="output .docx path (default: ./Site_Visit_Report_<date>.docx)")
    parser.add_argument("--include-pending", action="store_true",
                        help="include observations with review_status='Pending' "
                             "(live route only renders Approved)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    url = os.environ.get("RPD_SUPABASE_URL")
    key = os.environ.get("RPD_SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise SystemExit(
            "RPD_SUPABASE_URL and RPD_SUPABASE_SERVICE_KEY must be set in env"
        )

    site = _resolve_site(url, key, site_id=args.site_id, address=args.address)
    tier = "high" if float(site["project_value"]) >= 250000 else "low"
    print(f"site: {site['address_raw']} (id={site['id']}, tier={tier})")

    items = _fetch_checklist(url, key, tier)
    print(f"checklist_items: {len(items)} rows for tier={tier}")

    observations = _fetch_observations(
        url, key, site["id"], include_pending=args.include_pending,
    )
    statuses: dict[str, int] = {}
    for o in observations:
        s = o.get("review_status") or "?"
        statuses[s] = statuses.get(s, 0) + 1
    print(f"observations: {len(observations)} rows ({statuses})")

    results, unmatched = cross_reference(items, observations)
    state_counts: dict[str, int] = {}
    for r in results:
        state_counts[r.state] = state_counts.get(r.state, 0) + 1
    print(f"results by state: {state_counts}")
    print(f"unmatched observations: {len(unmatched)}")

    audit_ref = _resolve_audit_ref(url, key, observations) or "—"
    prepared_by = ""
    for o in observations:
        v = (o.get("prepared_by") or o.get("submitted_by") or "").strip()
        if v:
            prepared_by = v
            break

    ctx = SiteContext(
        address=site["address_raw"],
        project_value_tier=tier,
        audit_ref=audit_ref,
        prepared_by=prepared_by,
    )
    buf, unknown_tokens = build(
        ctx=ctx,
        results=results,
        unmatched=unmatched,
        audit_date_range=_format_date_range(observations),
    )
    if unknown_tokens:
        print(f"WARNING: unknown tokens in template: {sorted(unknown_tokens)}")

    # Phase 7 deterministic issue gate.
    from pims.services.site_visit_report_gate import run_gate
    docx_bytes = buf.getvalue()
    gate = run_gate(
        ctx=ctx, results=results, unmatched=unmatched, docx_bytes=docx_bytes,
    )
    if gate.warnings:
        print(f"gate: {len(gate.warnings)} WARNING(s):")
        for w in gate.warnings:
            print(f"  [{w.check}] {w.message}")
    if gate.errors:
        print(f"gate: {len(gate.errors)} ERROR(s):")
        for e in gate.errors:
            print(f"  [{e.check}] {e.message}")
        # Still write the file so a developer can open it and diagnose.
        # Production route fails the request; the CLI is for diagnosis.

    out = Path(args.output) if args.output else Path(
        f"Site_Visit_Report_{date.today().isoformat()}.docx"
    )
    out.write_bytes(docx_bytes)
    print(f"wrote {out} ({out.stat().st_size:,} bytes)")
    return 1 if gate.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

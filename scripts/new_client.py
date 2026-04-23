"""Scaffold a new PIMS client.

Mechanizes steps 1, 3, 4, 5 of docs/new_client_setup.md:

* Step 1 (optional, with --supabase-url + --supabase-service-key):
  apply pims/pims_migration.sql and INSERT the first pims_audits row.
* Step 3: clone frontend/pims_dashboard_rpd.html to
  frontend/pims_dashboard_<slug>.html with brand strings rewritten.
* Step 4: add the 4-line env-var block and the POST/GET handler pair
  to pims/routes.py.
* Step 5: add the /pims-<slug> dashboard route to api/main.py.

Leaves staging/commit to the operator. Does not touch Railway,
Supabase project creation, iPhone shortcut, or Cowork project.

Usage:
    python scripts/new_client.py \
        --slug abc --short ABC \
        --name "ABC Building Services Pty Ltd" \
        --ref ABC-SSA \
        [--supabase-url https://xxx.supabase.co] \
        [--supabase-service-key sb_secret_xxx]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROUTES = REPO / "pims" / "routes.py"
MAIN = REPO / "api" / "main.py"
DASHBOARD_SRC = REPO / "frontend" / "pims_dashboard_rpd.html"
MIGRATION = REPO / "pims" / "pims_migration.sql"

AUDIT_REF_RE = re.compile(r"^[A-Za-z0-9_\-]+$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_\-]*$")
SHORT_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
LEGACY_JWT_RE = re.compile(r"eyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.")


def die(msg: str) -> "None":
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(2)


def validate(args: argparse.Namespace) -> None:
    if not AUDIT_REF_RE.match(args.ref):
        die(f"--ref {args.ref!r} must match ^[A-Za-z0-9_\\-]+$")
    if not SLUG_RE.match(args.slug):
        die(f"--slug {args.slug!r} must be lowercase alphanumeric / hyphen / underscore")
    if not SHORT_RE.match(args.short):
        die(f"--short {args.short!r} must be UPPERCASE letters/digits/underscore")
    if not args.name.strip():
        die("--name must not be empty")
    if (args.supabase_url and not args.supabase_service_key) or (
        args.supabase_service_key and not args.supabase_url
    ):
        die("--supabase-url and --supabase-service-key must be supplied together")


# ---------------------------------------------------------------------------
# pims/routes.py patches
# ---------------------------------------------------------------------------

ENV_BLOCK_TEMPLATE = """
# {name} Supabase
{SHORT}_SUPABASE_URL         = os.getenv("{SHORT}_SUPABASE_URL", "")
{SHORT}_SUPABASE_KEY         = os.getenv("{SHORT}_SUPABASE_ANON_KEY", "")
{SHORT}_SUPABASE_SERVICE_KEY = os.getenv("{SHORT}_SUPABASE_SERVICE_KEY", "")
{SHORT}_PIMS_TOKEN           = os.getenv("PIMS_{SHORT}_TOKEN", "")
"""

HANDLER_TEMPLATE = '''

@router.post("/observation/{slug}", response_model=ObservationResponse)
async def {slug_py}_observation(
    request: Request,
    payload: ObservationRequest,
    background_tasks: BackgroundTasks,
    x_pims_token: str = Header(..., alias="X-PIMS-Token"),
):
    """Receive a field observation for {name} and enrich with CCVS codes."""
    return await _handle_observation(
        request=              payload,
        supabase_url=         {SHORT}_SUPABASE_URL,
        supabase_service_key= {SHORT}_SUPABASE_SERVICE_KEY,
        expected_token=       {SHORT}_PIMS_TOKEN,
        token=                x_pims_token,
        background_tasks=     background_tasks,
    )


@router.get("/observations/{slug}")
async def list_observations_{slug_py}(
    request: Request,
    pims_sess: str | None = Cookie(default=None, alias=COOKIE_NAME),
    audit_id: str | None = None,
    limit: int = 500,
    offset: int = 0,
):
    if not verify_session_cookie(pims_sess):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not {SHORT}_SUPABASE_URL:
        raise HTTPException(status_code=503, detail="Supabase URL not configured")
    if not {SHORT}_SUPABASE_SERVICE_KEY:
        raise HTTPException(status_code=503, detail="Supabase service key not configured")
    if audit_id and not _is_uuid(audit_id):
        raise HTTPException(status_code=422, detail="Invalid audit_id format.")
    if limit < 1:
        raise HTTPException(status_code=422, detail="limit must be >= 1.")
    if offset < 0:
        raise HTTPException(status_code=422, detail="offset must be >= 0.")

    limit = min(limit, 1000)
    headers = _supabase_headers({SHORT}_SUPABASE_SERVICE_KEY, prefer="return=representation")
    params = {{
        "review_status": "eq.Approved",
        "order":         "approved_at.desc",
        "select":        "*",
        "limit":         str(limit),
        "offset":        str(offset),
    }}
    if audit_id:
        params["audit_id"] = f"eq.{{audit_id}}"

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"{{{SHORT}_SUPABASE_URL}}/rest/v1/pims_observations",
            headers=headers,
            params=params,
        )
        r.raise_for_status()
        return r.json()
'''


def _read_preserve_bom(path: Path) -> tuple[str, bool, str]:
    """Return (text_with_lf_eols, has_bom, original_eol)."""
    raw = path.read_bytes()
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    if has_bom:
        raw = raw[3:]
    eol = "\r\n" if b"\r\n" in raw else "\n"
    text = raw.decode("utf-8")
    # Normalize to LF for string matching; restore on write.
    if eol == "\r\n":
        text = text.replace("\r\n", "\n")
    return text, has_bom, eol


def _write_preserve_bom(path: Path, text: str, has_bom: bool, eol: str) -> None:
    if eol == "\r\n":
        text = text.replace("\n", "\r\n")
    data = text.encode("utf-8")
    if has_bom:
        data = b"\xef\xbb\xbf" + data
    path.write_bytes(data)


def patch_routes(slug: str, short: str, name: str) -> None:
    src, has_bom, eol = _read_preserve_bom(ROUTES)
    short_upper = short.upper()

    if f"{short_upper}_SUPABASE_URL" in src:
        die(f"pims/routes.py already references {short_upper}_SUPABASE_URL — client exists")

    # Insert env-var block after the SDG block.
    sdg_anchor = 'SDG_PIMS_TOKEN           = os.getenv("PIMS_SDG_TOKEN", "")'
    if sdg_anchor not in src:
        die(f"could not find SDG env anchor in {ROUTES}")
    env_block = ENV_BLOCK_TEMPLATE.format(name=name, SHORT=short_upper)
    src = src.replace(sdg_anchor, sdg_anchor + env_block.rstrip() + "\n", 1)

    # Append handler pair at EOF.
    slug_py = slug.replace("-", "_")
    handlers = HANDLER_TEMPLATE.format(slug=slug, slug_py=slug_py, name=name, SHORT=short_upper)
    if not src.endswith("\n"):
        src += "\n"
    src += handlers

    _write_preserve_bom(ROUTES, src, has_bom, eol)
    print(f"[ok] pims/routes.py: env block + POST /observation/{slug} + GET /observations/{slug}")


# ---------------------------------------------------------------------------
# api/main.py patches
# ---------------------------------------------------------------------------

MAIN_ROUTE_TEMPLATE = '''

@app.get("/pims-{slug}", response_class=HTMLResponse)
async def serve_pims_{slug_py}(request: Request):
    if not verify_session_cookie(request.cookies.get(COOKIE_NAME)):
        return RedirectResponse(url="/pims-login", status_code=302)
    path = os.path.join(_FRONTEND_DIR, "pims_dashboard_{slug}.html")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    content = content.replace("__SUPABASE_URL__", os.getenv("{SHORT}_SUPABASE_URL", ""))
    content = content.replace("__SUPABASE_ANON__", os.getenv("{SHORT}_SUPABASE_ANON_KEY", ""))
    return HTMLResponse(content=content, headers={{"Cache-Control": "no-cache"}})
'''


def patch_main(slug: str, short: str) -> None:
    src, has_bom, eol = _read_preserve_bom(MAIN)
    short_upper = short.upper()

    if f'"/pims-{slug}"' in src:
        die(f"api/main.py already defines /pims-{slug} route")

    # Anchor on the closing of the /pims-rpd handler specifically (the
    # /pims handler has an identical final two lines, so we anchor on the
    # unique function name serve_pims_rpd and walk forward).
    marker = "async def serve_pims_rpd("
    idx = src.find(marker)
    if idx == -1:
        die("could not find serve_pims_rpd in api/main.py")
    tail = '    return HTMLResponse(content=content, headers={"Cache-Control": "no-cache"})\n'
    tail_idx = src.find(tail, idx)
    if tail_idx == -1:
        die("could not find end of serve_pims_rpd body in api/main.py")
    insert_at = tail_idx + len(tail)

    slug_py = slug.replace("-", "_")
    block = MAIN_ROUTE_TEMPLATE.format(slug=slug, slug_py=slug_py, SHORT=short_upper)
    src = src[:insert_at] + block + src[insert_at:]
    _write_preserve_bom(MAIN, src, has_bom, eol)
    print(f"[ok] api/main.py: added GET /pims-{slug}")


# ---------------------------------------------------------------------------
# frontend dashboard clone
# ---------------------------------------------------------------------------


def build_dashboard(slug: str, short: str, name: str, ref: str) -> None:
    dest = REPO / "frontend" / f"pims_dashboard_{slug}.html"
    if dest.exists():
        die(f"{dest} already exists; refusing to overwrite")

    src, has_bom, eol = _read_preserve_bom(DASHBOARD_SRC)

    # Safety net: abort if the source template still has a hard-coded JWT.
    if LEGACY_JWT_RE.search(src):
        die(
            "source template frontend/pims_dashboard_rpd.html still contains a "
            "legacy JWT literal. Fix the template first so it uses "
            "__SUPABASE_URL__ / __SUPABASE_ANON__ placeholders."
        )
    if "__SUPABASE_URL__" not in src or "__SUPABASE_ANON__" not in src:
        die(
            "source template is missing __SUPABASE_URL__ / __SUPABASE_ANON__ "
            "placeholders — scaffold would produce a non-functional dashboard."
        )

    # Brand rewrites.
    out = (
        src
        .replace("PIMS Dashboard — RPD", f"PIMS Dashboard — {short}")
        .replace("<span>/ RPD</span>", f"<span>/ {short}</span>")
    )

    # Endpoint rewrites: per-client report/export routes. Matching backend
    # routes are NOT scaffolded yet — operator adds them once needed.
    endpoint_map = {
        "/pims/report/rpd":       f"/pims/report/{slug}",
        "/pims/staging/rpd/xlsx": f"/pims/staging/{slug}/xlsx",
        "/pims/staging/rpd/docx": f"/pims/staging/{slug}/docx",
    }
    endpoint_warnings: list[str] = []
    for old, new in endpoint_map.items():
        if old in out:
            out = out.replace(old, new)
            endpoint_warnings.append(new)

    _write_preserve_bom(dest, out, has_bom, eol)
    print(f"[ok] frontend/{dest.name}: cloned from pims_dashboard_rpd.html")
    print(f"     brand: title + header -> {short}")
    print(f"     audit_ref placeholder: {ref} (no literal occurrences in template; used for Supabase INSERT only)")
    if endpoint_warnings:
        print("[warn] dashboard now calls these backend endpoints which do NOT exist yet:")
        for ep in endpoint_warnings:
            print(f"         {ep}")
        print("       Add matching handlers to pims/routes.py before using report/export features.")


# ---------------------------------------------------------------------------
# Optional Supabase bootstrap
# ---------------------------------------------------------------------------


def bootstrap_sql(name: str, ref: str, site_name: str) -> str:
    # Escape single-quotes in user-supplied values.
    def q(s: str) -> str:
        return s.replace("'", "''")

    migration = MIGRATION.read_text(encoding="utf-8-sig")
    insert = (
        f"\n-- First audit row for {q(name)}\n"
        f"INSERT INTO public.pims_audits (audit_ref, site_name, audit_date) "
        f"VALUES ('{q(ref)}', '{q(site_name)}', CURRENT_DATE) "
        f"ON CONFLICT (audit_ref) DO NOTHING;\n"
    )
    return migration + insert


def run_supabase_bootstrap(url: str, service_key: str, name: str, ref: str) -> None:
    try:
        import httpx
    except ImportError:
        die("httpx not installed; cannot run --supabase-* bootstrap")

    sql = bootstrap_sql(name=name, ref=ref, site_name=name)
    # Supabase doesn't expose raw SQL over PostgREST. The operator has two
    # realistic options: supabase_mcp.apply_migration, or paste into the SQL
    # editor. This helper prints the SQL and instructions; we don't invoke
    # the MCP server from a standalone script.
    print(
        "[info] --supabase-url / --supabase-service-key supplied. "
        "Raw SQL bootstrap requires either the Supabase SQL editor "
        "or the supabase MCP apply_migration tool. The SQL to run is "
        "below; copy into the SQL editor for the target project."
    )
    print("----- BEGIN BOOTSTRAP SQL -----")
    print(sql)
    print("----- END BOOTSTRAP SQL -----")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def preflight(slug: str, short: str) -> None:
    """Read all three sources, verify every abort condition, touch nothing.

    If this returns without calling die(), the three patch_* functions are
    safe to run in sequence — the anchors exist and nothing conflicts.
    """
    short_upper = short.upper()
    dest_html = REPO / "frontend" / f"pims_dashboard_{slug}.html"
    if dest_html.exists():
        die(f"{dest_html} already exists; rerun after removing it or pick a different --slug")

    routes_src, _, _ = _read_preserve_bom(ROUTES)
    if f"{short_upper}_SUPABASE_URL" in routes_src:
        die(f"pims/routes.py already references {short_upper}_SUPABASE_URL -- client exists")
    if 'SDG_PIMS_TOKEN           = os.getenv("PIMS_SDG_TOKEN", "")' not in routes_src:
        die(f"could not find SDG env anchor in {ROUTES}")

    main_src, _, _ = _read_preserve_bom(MAIN)
    if f'"/pims-{slug}"' in main_src:
        die(f"api/main.py already defines /pims-{slug} route")
    if "async def serve_pims_rpd(" not in main_src:
        die("could not find serve_pims_rpd in api/main.py")
    tail = '    return HTMLResponse(content=content, headers={"Cache-Control": "no-cache"})\n'
    idx = main_src.find("async def serve_pims_rpd(")
    if main_src.find(tail, idx) == -1:
        die("could not find end of serve_pims_rpd body in api/main.py")

    dash_src, _, _ = _read_preserve_bom(DASHBOARD_SRC)
    if LEGACY_JWT_RE.search(dash_src):
        die(
            "source template frontend/pims_dashboard_rpd.html still contains a "
            "legacy JWT literal. Fix the template first so it uses "
            "__SUPABASE_URL__ / __SUPABASE_ANON__ placeholders."
        )
    if "__SUPABASE_URL__" not in dash_src or "__SUPABASE_ANON__" not in dash_src:
        die(
            "source template is missing __SUPABASE_URL__ / __SUPABASE_ANON__ "
            "placeholders -- scaffold would produce a non-functional dashboard."
        )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--slug", required=True, help="lowercase slug, e.g. 'abc' (URL path + filename)")
    p.add_argument("--short", required=True, help="UPPERCASE short code, e.g. 'ABC' (env-var prefix + header)")
    p.add_argument("--name", required=True, help="client full legal name, e.g. 'ABC Building Services Pty Ltd'")
    p.add_argument("--ref", required=True, help="first audit_ref, e.g. 'ABC-SSA' (must match ^[A-Za-z0-9_-]+$)")
    p.add_argument("--supabase-url", default="", help="optional: Supabase project URL for bootstrap")
    p.add_argument("--supabase-service-key", default="", help="optional: sb_secret_... for bootstrap")
    args = p.parse_args()

    validate(args)
    preflight(slug=args.slug, short=args.short)

    patch_routes(slug=args.slug, short=args.short, name=args.name)
    patch_main(slug=args.slug, short=args.short)
    build_dashboard(slug=args.slug, short=args.short, name=args.name, ref=args.ref)

    if args.supabase_url and args.supabase_service_key:
        run_supabase_bootstrap(
            url=args.supabase_url,
            service_key=args.supabase_service_key,
            name=args.name,
            ref=args.ref,
        )
    else:
        print("[info] --supabase-url / --supabase-service-key not supplied.")
        print("       Run pims/pims_migration.sql in the target Supabase SQL editor, then:")
        print(
            f"       INSERT INTO public.pims_audits (audit_ref, site_name, audit_date) "
            f"VALUES ('{args.ref}', '{args.name}', CURRENT_DATE);"
        )

    print()
    print(f"[done] scaffold complete for client '{args.name}' (slug={args.slug}, short={args.short}).")
    print(f"       still manual (v3 step numbers):")
    print(f"         Step 2 (Railway env vars), Step 4 (Supabase bootstrap SQL),")
    print(f"         Step 5 (deploy), Step 6 (dashboard test),")
    print(f"         Step 7 (Snap shortcut), Step 8 (Snap test),")
    print(f"         Step 9 (Cowork project).")
    print("       Required Railway env vars:")
    print(f"         {args.short.upper()}_SUPABASE_URL")
    print(f"         {args.short.upper()}_SUPABASE_ANON_KEY")
    print(f"         {args.short.upper()}_SUPABASE_SERVICE_KEY")
    print(f"         PIMS_{args.short.upper()}_TOKEN")
    print("       Review `git diff pims/routes.py api/main.py` before committing.")


if __name__ == "__main__":
    main()

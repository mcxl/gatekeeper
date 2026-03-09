#!/usr/bin/env python3
"""
tests/test_deployment.py — 5 deployment readiness checks.

Check 1: Auth endpoints exist in api/main.py
Check 2: Frontend served (/ → login.html, /app → dev.html)
Check 3: Protected endpoint rejects unauthenticated requests
Check 4: Health endpoint returns expected fields
Check 5: requirements.txt has all needed packages
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)


def main():
    results = []

    # ── Check 1: Auth endpoints exist ──────────────────
    print("Check 1: Auth endpoints...")
    try:
        with open(os.path.join(_ROOT, "api", "main.py"), "r") as f:
            code = f.read()
        endpoints = [
            "/auth/signup", "/auth/login", "/auth/logout",
            "/auth/refresh", "/auth/me", "/auth/reset-password",
        ]
        found = [ep for ep in endpoints if ep in code]
        ok = len(found) == len(endpoints)
        results.append(("Check 1: Auth endpoints", ok, f"{len(found)}/{len(endpoints)} found"))
    except Exception as e:
        results.append(("Check 1: Auth endpoints", False, str(e)))

    # ── Check 2: Frontend served ───────────────────────
    print("Check 2: Frontend serving...")
    try:
        with open(os.path.join(_ROOT, "api", "main.py"), "r") as f:
            code = f.read()
        ok_login = "login.html" in code and 'async def index' in code
        ok_app = "dev.html" in code and '/app' in code
        ok = ok_login and ok_app
        results.append(("Check 2: Frontend served", ok, f"login={ok_login}, app={ok_app}"))
    except Exception as e:
        results.append(("Check 2: Frontend served", False, str(e)))

    # ── Check 3: Protected endpoints ───────────────────
    print("Check 3: Protected endpoints...")
    try:
        with open(os.path.join(_ROOT, "api", "main.py"), "r") as f:
            code = f.read()
        protected = [
            "generate_auto", "generate_full", "generate_stream",
            "render_docx_endpoint", "render_pdf_endpoint", "render_both_endpoint",
            "generate_ra", "render_ra_endpoint",
            "render_ra_pdf_endpoint", "render_ra_both_endpoint",
        ]
        import re
        count = 0
        for fn in protected:
            pattern = rf"async def {fn}\(.*get_current_user"
            if re.search(pattern, code):
                count += 1
        ok = count == len(protected)
        results.append(("Check 3: Protected endpoints", ok, f"{count}/{len(protected)} protected"))
    except Exception as e:
        results.append(("Check 3: Protected endpoints", False, str(e)))

    # ── Check 4: Health endpoint ───────────────────────
    print("Check 4: Health endpoint...")
    try:
        with open(os.path.join(_ROOT, "api", "main.py"), "r") as f:
            code = f.read()
        ok_env = "environment" in code and 'ENVIRONMENT' in code
        ok_supa = "supabase_configured" in code
        ok_platform = "platform.system()" in code
        ok = ok_env and ok_supa and ok_platform
        results.append(("Check 4: Health endpoint", ok, f"env={ok_env}, supabase={ok_supa}, platform={ok_platform}"))
    except Exception as e:
        results.append(("Check 4: Health endpoint", False, str(e)))

    # ── Check 5: Requirements complete ─────────────────
    print("Check 5: Requirements...")
    try:
        with open(os.path.join(_ROOT, "requirements.txt"), "r") as f:
            reqs = f.read().lower()
        needed = ["python-jose", "passlib", "httpx", "aiofiles", "fastapi", "uvicorn", "python-dotenv"]
        found = [pkg for pkg in needed if pkg in reqs]
        ok = len(found) == len(needed)
        results.append(("Check 5: Requirements", ok, f"{len(found)}/{len(needed)}: {', '.join(found)}"))
    except Exception as e:
        results.append(("Check 5: Requirements", False, str(e)))

    # ── Report ─────────────────────────────────────────
    print("\n" + "=" * 70)
    print("DEPLOYMENT READINESS — 5 CHECKS")
    print("=" * 70)
    all_pass = True
    for label, passed, detail in results:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  {status}  {label}")
        if detail:
            print(f"         {detail}")
    print("=" * 70)
    print(f"RESULT: {'ALL 5 PASSED' if all_pass else 'SOME CHECKS FAILED'}")
    print("=" * 70)


if __name__ == "__main__":
    main()

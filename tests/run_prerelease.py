#!/usr/bin/env python3
"""
tests/run_prerelease.py

Pre-release deployment gate for Category 1 flows.
Any failing check exits with code 1.
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import re
import sys
import uuid
from contextlib import redirect_stdout
from pathlib import Path

import httpx

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

PASS = "PASS"
FAIL = "FAIL"


def _print_header() -> None:
    print("\nSafe Method Pre-Release Checklist")
    print("=" * 70)


def _print_footer(all_passed: bool) -> None:
    print("=" * 70)
    print(f"RESULT: {'ALL CATEGORY 1 FLOWS PASSED' if all_passed else 'CATEGORY 1 FAILURE'}")
    print("=" * 70)


def _flow_result(name: str, ok: bool, detail: str) -> tuple[str, bool, str]:
    return (name, ok, detail)


def _load_tiltup_description() -> str:
    fixture_path = _ROOT / "tests" / "reference_jobs" / "01_tiltup.json"
    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)
    return data["description"]


def check_flow_1_tiltup_sequence() -> tuple[str, bool, str]:
    """
    FLOW 1: Tilt-up sequence check (automated).
    """
    name = "FLOW 1: Tilt-up sequence check"
    try:
        from core.orchestrator import generate_swms

        description = _load_tiltup_description()
        result = asyncio.run(
            generate_swms(
                description=description,
                project_meta={"project_name": "Prerelease Tiltup"},
            )
        )
        tasks = result.get("tasks") or []
        if not tasks:
            return _flow_result(name, False, "No tasks returned by generation pipeline")

        task_texts = [str(t.get("task", "")).lower() for t in tasks]
        first_task = task_texts[0]
        first_keywords = ("mobilise", "mobilize", "establish", "site setup", "site establishment")
        first_ok = any(k in first_task for k in first_keywords)

        # Check prop/brace task exists
        brace_keywords = ("brace", "prop")
        brace_indices = [i for i, t in enumerate(task_texts) if any(k in t for k in brace_keywords)]
        brace_exists = len(brace_indices) > 0

        # Check prop/brace removal appears after a lift/erect/position task
        lift_keywords = ("lift", "erect", "position")
        lift_indices = [i for i, t in enumerate(task_texts) if any(k in t for k in lift_keywords)]
        removal_keywords = ("remove", "de-prop", "deprop", "strip")
        removal_indices = [
            i for i, t in enumerate(task_texts)
            if any(k in t for k in removal_keywords) and any(k in t for k in brace_keywords)
        ]
        removal_after_lift = (
            min(removal_indices) > min(lift_indices)
            if removal_indices and lift_indices
            else not removal_indices  # no removal task is acceptable
        )

        if first_ok and brace_exists and removal_after_lift:
            return _flow_result(
                name,
                True,
                f"first='{tasks[0].get('task', '')[:80]}', brace_count={len(brace_indices)}, last='{tasks[-1].get('task', '')[:80]}'",
            )

        return _flow_result(
            name,
            False,
            (
                "sequence mismatch "
                f"first_ok={first_ok} brace_exists={brace_exists} removal_after_lift={removal_after_lift} "
                f"first='{first_task[:80]}'"
            ),
        )
    except Exception as e:
        return _flow_result(name, False, f"{type(e).__name__}: {e}")


def check_flow_2_api_key_auth() -> tuple[str, bool, str]:
    """
    FLOW 2: API key auth check (automated).
    """
    name = "FLOW 2: API key auth check"
    try:
        from core.api_keys import get_user_or_api_key
        from api.main import app

        if not callable(get_user_or_api_key):
            return _flow_result(name, False, "get_user_or_api_key is not callable")

        v1_generate_exists = any(
            getattr(route, "path", "") == "/v1/generate/stream"
            and "POST" in getattr(route, "methods", set())
            for route in app.routes
        )
        if not v1_generate_exists:
            return _flow_result(name, False, "/v1/generate/stream route not registered")

        return _flow_result(name, True, "Auth dependency importable and v1 generate route registered")
    except Exception as e:
        return _flow_result(name, False, f"{type(e).__name__}: {e}")


def check_flow_3_correlation_middleware() -> tuple[str, bool, str]:
    """
    FLOW 3: Correlation ID middleware check (automated).
    """
    name = "FLOW 3: Correlation ID middleware check"
    try:
        from api.main import app

        async def _run() -> tuple[int, str]:
            try:
                async with httpx.AsyncClient(app=app, base_url="http://testserver") as client:
                    response = await client.get("/health")
            except TypeError:
                # Compatibility fallback for httpx versions that require ASGITransport.
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                    response = await client.get("/health")
            return response.status_code, response.headers.get("x-correlation-id", "")

        status_code, cid = asyncio.run(_run())
        if status_code != 200:
            return _flow_result(name, False, f"GET /health returned {status_code}")
        if not cid:
            return _flow_result(name, False, "x-correlation-id header missing")

        parsed = uuid.UUID(cid)
        if parsed.version != 4:
            return _flow_result(name, False, f"x-correlation-id is UUID version {parsed.version}, expected v4")

        return _flow_result(name, True, f"x-correlation-id={cid}")
    except Exception as e:
        return _flow_result(name, False, f"{type(e).__name__}: {e}")


def check_flow_4_job_states() -> tuple[str, bool, str]:
    """
    FLOW 4: job_states table check (automated).
    """
    name = "FLOW 4: job_states table check"
    try:
        import core.job_state as job_state_mod
        from core.job_state import record_state

        captured_events: list[dict] = []
        original_log_event = job_state_mod.log_event

        def _capturing_log_event(event_type: str, duration_ms: int | None = None, metadata: dict | None = None) -> None:
            captured_events.append(
                {
                    "event_type": event_type,
                    "metadata": metadata or {},
                }
            )
            original_log_event(event_type=event_type, duration_ms=duration_ms, metadata=metadata or {})

        job_state_mod.log_event = _capturing_log_event
        try:
            asyncio.run(
                record_state(
                    "prerelease-check",
                    "swms_generate",
                    "received",
                    {"source": "prerelease"},
                )
            )
        finally:
            job_state_mod.log_event = original_log_event

        reasons = [
            str(ev.get("metadata", {}).get("reason", ""))
            for ev in captured_events
            if ev.get("event_type") == "job_state_write_failed"
        ]
        reasons = [r for r in reasons if r]
        if not reasons:
            return _flow_result(name, True, "record_state returned cleanly")

        invalid_reasons = [r for r in reasons if r != "supabase_not_configured"]
        if invalid_reasons:
            return _flow_result(name, False, f"job_state_write_failed reasons not allowed: {invalid_reasons}")

        return _flow_result(name, True, "record_state returned; only supabase_not_configured logged")
    except Exception as e:
        return _flow_result(name, False, f"{type(e).__name__}: {e}")


def check_flow_5_route_boundary_instrumentation() -> tuple[str, bool, str]:
    """
    FLOW 5: Route boundary instrumentation check (automated).

    Ensures the four named endpoints have received/complete/failed record_state calls.
    """
    name = "FLOW 5: Route boundary instrumentation check"
    try:
        source = (_ROOT / "api" / "main.py").read_text(encoding="utf-8")

        # Ensure each endpoint declaration is present.
        endpoint_markers = [
            '@app.post("/generate/stream")',
            '@v1.post("/generate/stream")',
            '@app.post("/render/docx")',
            '@app.post("/render/pdf")',
        ]
        for marker in endpoint_markers:
            if marker not in source:
                return _flow_result(name, False, f"Missing endpoint marker: {marker}")

        patterns = {
            "swms_generate_received": r'record_state\(\s*cid,\s*"swms_generate",\s*"received"',
            "swms_generate_complete": r'record_state\(\s*cid,\s*"swms_generate",\s*"complete"',
            "swms_generate_failed": r'record_state\(\s*cid,\s*"swms_generate",\s*"failed"',
            "render_docx_received": r'record_state\(\s*cid,\s*"render_docx",\s*"received"',
            "render_docx_complete": r'record_state\(\s*cid,\s*"render_docx",\s*"complete"',
            "render_docx_failed": r'record_state\(\s*cid,\s*"render_docx",\s*"failed"',
            "render_pdf_received": r'record_state\(\s*cid,\s*"render_pdf",\s*"received"',
            "render_pdf_complete": r'record_state\(\s*cid,\s*"render_pdf",\s*"complete"',
            "render_pdf_failed": r'record_state\(\s*cid,\s*"render_pdf",\s*"failed"',
        }
        counts = {key: len(re.findall(pattern, source, flags=re.MULTILINE)) for key, pattern in patterns.items()}

        if counts["swms_generate_received"] < 2 or counts["swms_generate_complete"] < 2 or counts["swms_generate_failed"] < 2:
            return _flow_result(name, False, f"swms_generate instrumentation counts too low: {counts}")
        if counts["render_docx_received"] < 1 or counts["render_docx_complete"] < 1 or counts["render_docx_failed"] < 1:
            return _flow_result(name, False, f"render_docx instrumentation counts too low: {counts}")
        if counts["render_pdf_received"] < 1 or counts["render_pdf_complete"] < 1 or counts["render_pdf_failed"] < 1:
            return _flow_result(name, False, f"render_pdf instrumentation counts too low: {counts}")

        return _flow_result(name, True, "All four endpoints contain received/complete/failed instrumentation")
    except Exception as e:
        return _flow_result(name, False, f"{type(e).__name__}: {e}")


def main() -> int:
    _print_header()

    checks = [
        check_flow_1_tiltup_sequence,
        check_flow_2_api_key_auth,
        check_flow_3_correlation_middleware,
        check_flow_4_job_states,
        check_flow_5_route_boundary_instrumentation,
    ]

    results: list[tuple[str, bool, str]] = []
    for check in checks:
        result = check()
        results.append(result)
        status = PASS if result[1] else FAIL
        print(f"{status}  {result[0]}")
        if result[2]:
            print(f"      {result[2]}")

    all_passed = all(r[1] for r in results)
    _print_footer(all_passed)
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

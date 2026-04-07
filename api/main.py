#!/usr/bin/env python3
"""
api/main.py — Gatekeeper web interface.

Endpoints:
  GET  /          → login page (login.html)
  POST /generate  → query_task() → return DOCX + MD downloads
  GET  /tasks     → list approved tasks as JSON
  GET  /health    → simple health check

Usage:
  python -m uvicorn api.main:app --reload --port 8000
  or:
  python api/main.py
"""

import json
import logging
import os
import sys
import time
import traceback
import uuid

logger = logging.getLogger(__name__)

from renderers.pdf_renderer import pdf_available

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(_ROOT, ".env"))

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    traces_sample_rate=0.2,
    environment=os.getenv("ENVIRONMENT", "production"),
    integrations=[FastApiIntegration(), StarletteIntegration()],
)

from fastapi import Depends, FastAPI, File, Form, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from typing import Literal
from pydantic import BaseModel, EmailStr, Field

from core.auth import (
    get_current_user, get_optional_user,
    signup, login, refresh_session, sign_out, reset_password,
    FRONTEND_URL,
)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from api.upload_routes import router as upload_router
from api.intake_routes import router as intake_router
from api.procore import router as procore_router
from core.api_keys import get_user_or_api_key, log_api_key_usage
from core.job_state import record_state
from core.logging_config import get_correlation_id, log_event, set_correlation_id

app = FastAPI(title="Gatekeeper SWMS Generator", version="1.0")
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    """Attach and propagate correlation_id for every inbound request."""
    started = time.perf_counter()
    inbound_cid = request.headers.get("X-Correlation-ID", "").strip()
    cid = inbound_cid or str(uuid.uuid4())
    set_correlation_id(cid)

    log_event(
        event_type="request_received",
        duration_ms=None,
        metadata={
            "method": request.method,
            "path": request.url.path,
            "correlation_id": cid,
        },
    )

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = int((time.perf_counter() - started) * 1000)
        log_event(
            event_type="request_complete",
            duration_ms=duration_ms,
            metadata={
                "status_code": 500,
                "method": request.method,
                "path": request.url.path,
                "correlation_id": cid,
            },
        )
        raise

    duration_ms = int((time.perf_counter() - started) * 1000)
    if "x-correlation-id" not in response.headers:
        response.headers["x-correlation-id"] = cid
    log_event(
        event_type="request_complete",
        duration_ms=duration_ms,
        metadata={
            "status_code": response.status_code,
            "method": request.method,
            "path": request.url.path,
            "correlation_id": cid,
        },
    )
    return response

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

from fastapi.exceptions import RequestValidationError
@app.exception_handler(RequestValidationError)
async def _validation_error_handler(request: Request, exc: RequestValidationError):
    """Return user-friendly JSON instead of FastAPI's raw 422."""
    errors = exc.errors()
    # Build a readable message from the first error
    if errors:
        e = errors[0]
        loc = " → ".join(str(l) for l in e.get("loc", []) if l != "body")
        msg = e.get("msg", "Invalid input")
        detail = f"{loc}: {msg}" if loc else msg
    else:
        detail = "Invalid request. Please check your input and try again."
    return JSONResponse(status_code=400, content={"detail": detail})

from api.control_pack_routes import router as control_pack_router
app.include_router(upload_router)
app.include_router(intake_router)
app.include_router(control_pack_router)
app.include_router(procore_router, prefix="/procore")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:8000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://js.sentry-cdn.com https://browser.sentry-cdn.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com https://fonts.googleapis.com; "
            "img-src 'self' data:; "
            "connect-src 'self' https://o4511019411177472.ingest.us.sentry.io https://*.supabase.co; "
            "worker-src 'none';"
        )
        return response


app.add_middleware(SecurityHeadersMiddleware)

_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
class CachedStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "public, max-age=31536000"
        return response

app.mount("/static", CachedStaticFiles(directory=_STATIC_DIR), name="static")

import sqlite3
DB_PATH = os.path.join(_ROOT, "db", "gatekeeper.db")


def _html_response(path: str) -> HTMLResponse:
    with open(path, encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content, headers={"Cache-Control": "no-cache"})


def _get_approved_tasks() -> list[dict]:
    """Return all approved tasks as a list of dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, task_name, scope, version, risk_pre, risk_post, wah_applicable "
        "FROM Tasks WHERE status='approved' ORDER BY task_name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ============================================================
# AUTH MODELS
# ============================================================

class AuthSignup(BaseModel):
    email: str
    password: str
    full_name: str = ""

class AuthLogin(BaseModel):
    email: str
    password: str

class AuthRefresh(BaseModel):
    refresh_token: str

class AuthResetPassword(BaseModel):
    email: str

class ContactRequest(BaseModel):
    name: str = Field(..., max_length=100)
    email: EmailStr
    subject: str = Field(..., max_length=200)
    message: str = Field(..., max_length=2000)


# ============================================================
# AUTH ENDPOINTS
# ============================================================

@app.post("/auth/signup")
@limiter.limit("5/minute")
async def auth_signup(request: Request, body: AuthSignup):
    result = signup(body.email, body.password, body.full_name)
    return result

@app.post("/auth/login")
@limiter.limit("10/minute")
async def auth_login(request: Request, body: AuthLogin):
    result = login(body.email, body.password)
    return result

@app.post("/auth/logout")
async def auth_logout(user: dict = Depends(get_current_user)):
    # Extract token from the request — user dict has user_id
    # sign_out needs the raw token; we'll accept it in the body or just invalidate client-side
    return {"message": "Logged out successfully"}

@app.post("/auth/refresh")
async def auth_refresh(body: AuthRefresh):
    result = refresh_session(body.refresh_token)
    return result

@app.get("/auth/me")
async def auth_me(user: dict = Depends(get_current_user)):
    return user

@app.post("/auth/reset-password")
async def auth_reset_password(body: AuthResetPassword):
    reset_password(body.email)
    return {"message": "If that email exists, a reset link has been sent."}


# ============================================================
# SERVE FRONTEND
# ============================================================

_FRONTEND_DIR = os.path.join(_ROOT, "frontend")


@app.get("/app", response_class=HTMLResponse)
async def serve_app():
    return _html_response(os.path.join(_FRONTEND_DIR, "dashboard.html"))


@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    return _html_response(os.path.join(_FRONTEND_DIR, "dashboard.html"))


@app.get("/pims", response_class=HTMLResponse)
async def serve_pims():
    return _html_response(os.path.join(_FRONTEND_DIR, "pims_dashboard.html"))


@app.get("/pims-rpd", response_class=HTMLResponse)
async def serve_pims_rpd():
    return _html_response(os.path.join(_FRONTEND_DIR, "pims_dashboard_rpd.html"))


@app.get("/ra", response_class=HTMLResponse)
async def serve_ra():
    return _html_response(os.path.join(_FRONTEND_DIR, "dev.html"))


@app.get("/control-pack", response_class=HTMLResponse)
async def serve_control_pack():
    return _html_response(os.path.join(_FRONTEND_DIR, "control_pack.html"))


@app.get("/contact", response_class=HTMLResponse)
async def serve_contact():
    return _html_response(os.path.join(_FRONTEND_DIR, "contact.html"))


@app.post("/contact")
async def submit_contact(body: ContactRequest):
    masked_email = body.email[:2] + "***@***" if body.email else ""
    logger.info(
        "CONTACT FORM: name=%s email=%s subject=%s message=%s",
        body.name,
        masked_email,
        body.subject,
        body.message[:200],
    )
    return JSONResponse({"status": "ok"})


@app.get("/terms", response_class=HTMLResponse)
async def serve_terms():
    terms_path = os.path.join(_FRONTEND_DIR, "terms.html")
    if os.path.isfile(terms_path):
        return _html_response(terms_path)
    return HTMLResponse("<h1>Terms &amp; Conditions</h1><p>Coming soon.</p>")


# ============================================================
# ROUTES
# ============================================================

TRADE_TYPES = [
    "Remedial", "Painting", "Waterproofing", "Cladding", "Structural",
    "Civil", "Mechanical", "Electrical", "Work at Height", "Demolition",
    "Groundworks", "Scaffolding",
]
PRINCIPAL_CONTRACTORS = [
    "General", "Hansen Yuncken", "Multiplex", "Lendlease", "Built", "Richard Crookes",
]


@app.get("/swms", response_class=HTMLResponse)
async def serve_swms():
    return _html_response(os.path.join(_FRONTEND_DIR, "app.html"))


@app.get("/review", response_class=HTMLResponse)
async def serve_review():
    return _html_response(os.path.join(_FRONTEND_DIR, "review.html"))


@app.get("/", response_class=HTMLResponse)
async def index():
    return _html_response(os.path.join(_FRONTEND_DIR, "marketing.html"))


@app.get("/demo", response_class=HTMLResponse)
async def demo_page():
    return _html_response(os.path.join(_FRONTEND_DIR, "demo.html"))


@app.get("/tasks")
async def list_tasks():
    """Return all approved tasks as JSON."""
    tasks = _get_approved_tasks()
    return JSONResponse(
        content={"tasks": tasks, "count": len(tasks)},
        headers={"Cache-Control": "public, max-age=300"},
    )


@app.post("/generate")
async def generate(
    request: Request,
    task_name: str = Form(...),
    site_name: str = Form(""),
    trade_type: str = Form(""),
    principal_contractor: str = Form("General"),
    output_format: str = Form("both"),
    user: dict = Depends(get_current_user),
):
    """
    Generate SWMS for given task name.
    Returns JSON with base64-encoded DOCX and/or markdown content.
    """
    try:
        from core.library import query_task
        from renderers.md_renderer import render_md

        task = query_task(task_name)

        result = {
            "task_name": task.task,
            "source": task.source,
            "approved": task.approved,
            "risk_pre": task.risk_pre,
            "risk_post": task.risk_post,
        }

        if output_format in ("docx", "both"):
            # Legacy DOCX via old templates is retired.
            # Use /generate/stream or /v1/generate/stream for Safe Method DOCX.
            result["docx_error"] = (
                "Legacy DOCX generation is retired. "
                "Use /generate/stream for Safe Method template output."
            )

        if output_format in ("md", "both"):
            md_text = render_md(task)
            result["markdown"] = md_text
            result["md_filename"] = f"{task.task.replace(' ', '_')[:40]}.md"

        if task.source == "ai-generated" and task.db_id is not None and not task.approved:
            result["draft_id"] = task.db_id
            result["message"] = f"AI-generated draft saved as Task {task.db_id}. Review then approve."

        return JSONResponse(content=result)

    except Exception as exc:
        logger.error(f"Generate failed:\n{traceback.format_exc()}")
        return JSONResponse(
            content={"detail": "An internal error occurred. Please try again."},
            status_code=500,
        )


@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    return JSONResponse(
        content={
            "status": "ok",
            "pdf_available": pdf_available(),
            "gotenberg_url": bool(os.getenv("GOTENBERG_URL", "")),
        },
        headers={"Cache-Control": "public, max-age=60"},
    )


@app.post("/upload/extract")
async def upload_extract(
    request: Request,
    file: UploadFile | None = File(None),
):
    """
    Accept a file (PDF/DOCX/PNG/JPG) or JSON {text}, extract text,
    call Claude for structured field extraction, return fields.
    """
    from core.document_extractor import (
        extract_from_text,
        extract_from_image,
        extract_text_from_pdf,
        extract_text_from_docx,
    )

    try:
        content_type = request.headers.get("content-type", "")

        # JSON body with plain text
        if "application/json" in content_type:
            body = await request.json()
            text = body.get("text", "")
            if not text.strip():
                return JSONResponse(content={"error": "Empty text"}, status_code=400)
            if len(text) > 50000:
                return JSONResponse(content={"error": "Text exceeds 50,000 character limit"}, status_code=400)
            fields = extract_from_text(text)
            return JSONResponse(content=fields)

        # File upload
        if file is None:
            return JSONResponse(content={"error": "No file or text provided"}, status_code=400)

        file_bytes = await file.read()
        fname = (file.filename or "").lower()

        if fname.endswith(".pdf"):
            text = extract_text_from_pdf(file_bytes)
            fields = extract_from_text(text)
        elif fname.endswith(".docx"):
            text = extract_text_from_docx(file_bytes)
            fields = extract_from_text(text)
        elif fname.endswith((".png", ".jpg", ".jpeg")):
            mt_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
            ext = "." + fname.rsplit(".", 1)[-1]
            fields = extract_from_image(file_bytes, mt_map[ext])
        else:
            return JSONResponse(
                content={"error": f"Unsupported file type: {fname}"},
                status_code=400,
            )

        return JSONResponse(content=fields)

    except Exception as exc:
        logger.error(f"Upload extract failed:\n{traceback.format_exc()}")
        return JSONResponse(content={"detail": "An internal error occurred. Please try again."}, status_code=500)


@app.post("/upload/swms-gap")
async def upload_swms_gap(file: UploadFile = File(...)):
    """
    Accept an existing SWMS file (PDF/DOCX), extract its content,
    and return a gap analysis comparing it against Gatekeeper standards.
    """
    from core.document_extractor import extract_text_from_pdf, extract_text_from_docx

    try:
        file_bytes = await file.read()
        fname = (file.filename or "").lower()

        if fname.endswith(".pdf"):
            text = extract_text_from_pdf(file_bytes)
        elif fname.endswith(".docx"):
            text = extract_text_from_docx(file_bytes)
        else:
            return JSONResponse(
                content={"error": "Only PDF and DOCX accepted for gap analysis"},
                status_code=400,
            )

        # Use Claude for gap analysis
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return JSONResponse(content={"error": "API key not configured"}, status_code=500)

        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system="""Analyse this existing SWMS document against Australian Model WHS Regulations 2017 requirements.
Return a JSON object:
{
  "gaps": ["list of missing or inadequate items"],
  "matched": ["list of items that meet requirements"],
  "confidence": 0.0 to 1.0
}
Return ONLY the JSON object.""",
            messages=[{"role": "user", "content": text[:8000]}],
        )
        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        result = json.loads(raw)
        return JSONResponse(content=result)

    except Exception as exc:
        logger.error(f"SWMS gap analysis failed:\n{traceback.format_exc()}")
        return JSONResponse(content={"detail": "An internal error occurred. Please try again."}, status_code=500)


# ============================================================
# INFERENCE & ROUTING
# ============================================================

@app.get("/infer")
@limiter.limit("30/minute")
def infer_endpoint(
    request: Request,
    q: str = Query(..., max_length=2000),
    jurisdiction: Literal["AU", "NZ", "UK", "US", "CA"] = "AU",
    document_type: Literal["swms", "ra"] = "swms",
):
    """
    GET /infer?q=<work description>&jurisdiction=AU&document_type=swms
    Returns inferred WHS requirements. No Claude call — pure inference.
    For document_type=ra, includes hazard_list with L/C scores.
    """
    if document_type == "ra":
        from core.inference_matrix import infer_to_dict_ra
        result = infer_to_dict_ra(q, jurisdiction=jurisdiction)
    else:
        from core.inference_matrix import infer_to_dict
        result = infer_to_dict(q, jurisdiction=jurisdiction)
    return JSONResponse(content=result, headers={"Cache-Control": "private, max-age=60"})


@app.get("/generate/route")
def check_route(description: str):
    from core.orchestrator import route as _route
    from core.inference_matrix import infer_to_dict
    inference = infer_to_dict(description)
    selected = _route(description, inference)
    return {
        "description": description[:100],
        "route": selected,
        "hrcw": inference["hrcw"],
        "hrcw_category": inference.get("hrcw_category"),
        "safework_notification": inference["safework_notification_required"],
    }


@app.post("/generate/auto")
@limiter.limit("20/minute")
async def generate_auto(request: Request, body: dict, user: dict = Depends(get_current_user)):
    from core.orchestrator import generate_swms
    try:
        description = body.get("description", "")
        project_meta = body.get("project_meta", {})
        jurisdiction = body.get("jurisdiction", "AU")
        scope_context = body.get("scope_context", None)
        # Ensure work_activity and description are populated
        if not project_meta.get("work_activity"):
            # Use first sentence of description as work activity
            first_sentence = description.split(".")[0].strip()
            project_meta["work_activity"] = first_sentence[:200] if first_sentence else description[:200]
        if not project_meta.get("description"):
            project_meta["description"] = description
        result = await generate_swms(
            description=description,
            project_meta=project_meta,
            force_full=body.get("force_full", False),
            force_simple=body.get("force_simple", False),
            jurisdiction=jurisdiction,
            scope_context=scope_context,
        )
        return result
    except Exception as e:
        logger.error(f"Generate auto failed:\n{traceback.format_exc()}")
        return {"detail": "An internal error occurred. Please try again."}


@app.post("/generate/full")
async def generate_full(request: dict, user: dict = Depends(get_current_user)):
    from core.orchestrator import generate_swms
    try:
        result = await generate_swms(
            description=request.get("description", ""),
            project_meta=request.get("project_meta", {}),
            force_full=True,
            jurisdiction=request.get("jurisdiction", "AU"),
            scope_context=request.get("scope_context"),
        )
        return result
    except Exception as e:
        logger.error(f"Generate full failed:\n{traceback.format_exc()}")
        return {"detail": "An internal error occurred. Please try again."}

@app.post("/generate/stream")
async def generate_stream(request: dict, user: dict = Depends(get_current_user)):
    """
    POST /generate/stream
    Server-Sent Events stream. Yields JSON lines as each task completes.
    Client reads via EventSource or fetch + ReadableStream.
    """
    import json
    from fastapi.responses import StreamingResponse
    from core.orchestrator import generate_swms_stream

    cid = get_correlation_id()
    await record_state(cid, "swms_generate", "received", {"path": "/generate/stream"})

    description = (request.get("description") or "").strip()
    if not description or len(description.split()) < 3:
        return JSONResponse(
            content={"detail": "Description is required (at least 3 words)."},
            status_code=422,
        )
    project_meta = request.get("project_meta", {})
    force_full = request.get("force_full", False)
    force_simple = request.get("force_simple", False)
    jurisdiction = request.get("jurisdiction", "AU")
    scope_context = request.get("scope_context")

    async def event_generator():
        import asyncio
        try:
            stream = generate_swms_stream(
                description=description,
                project_meta=project_meta,
                force_full=force_full,
                force_simple=force_simple,
                jurisdiction=jurisdiction,
                scope_context=scope_context,
            )
            stream_iter = stream.__aiter__()
            while True:
                try:
                    event = await asyncio.wait_for(stream_iter.__anext__(), timeout=15.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except StopAsyncIteration:
                    break
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
            await record_state(cid, "swms_generate", "complete", {"path": "/generate/stream"})
        except Exception as e:
            await record_state(
                cid,
                "swms_generate",
                "failed",
                {"path": "/generate/stream", "error": type(e).__name__, "detail": str(e)[:200]},
            )
            logger.error(f"Stream generation failed:\n{traceback.format_exc()}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'Generation failed: {type(e).__name__}: {e}'})}\n\n"
            raise

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/render/docx")
async def render_docx_endpoint(request: dict, user: dict = Depends(get_current_user)):
    """
    POST /render/docx
    Accepts {"tasks": [...], "project_meta": {...}, "inference": {...}, "filename": "optional"}
    Renders all tasks into a single Word document and returns as file download.
    Runs post-render validation if validate=true (default).
    """
    cid = get_correlation_id()
    await record_state(cid, "render_docx", "received", {"path": "/render/docx"})
    try:
        jurisdiction = request.get("jurisdiction", "AU")
        docx_bytes, filename = _render_tasks_to_docx(request, jurisdiction=jurisdiction)

        # Post-render validation (advisory — never blocks output)
        validator_summary = None
        if request.get("validate", True):
            validator_summary = _validate_rendered_output(
                docx_bytes, request.get("tasks", []), filename, request,
            )

        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        if validator_summary:
            headers["X-Validator-Status"] = validator_summary.get("status", "")
            action = validator_summary.get("suggested_action", "")[:200]
            headers["X-Validator-Action"] = action.encode("ascii", errors="replace").decode("ascii")
            # Reviewer headers (present only when ESCALATE_EXTERNAL triggered reviewer)
            if "reviewer_status" in validator_summary:
                headers["X-Reviewer-Status"] = validator_summary["reviewer_status"]
                rev_action = validator_summary.get("reviewer_action", "")[:200]
                headers["X-Reviewer-Action"] = rev_action.encode("ascii", errors="replace").decode("ascii")

        await record_state(cid, "render_docx", "complete", {"path": "/render/docx"})
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers=headers,
        )
    except ValueError as e:
        await record_state(
            cid,
            "render_docx",
            "failed",
            {"path": "/render/docx", "error": type(e).__name__, "detail": str(e)[:200]},
        )
        return JSONResponse(content={"error": str(e)}, status_code=400)
    except Exception as e:
        await record_state(
            cid,
            "render_docx",
            "failed",
            {"path": "/render/docx", "error": type(e).__name__, "detail": str(e)[:200]},
        )
        logger.error(f"Render DOCX failed:\n{traceback.format_exc()}")
        return JSONResponse(content={"detail": f"Render failed: {type(e).__name__}: {e}"}, status_code=500)


def _validate_rendered_output(
    docx_bytes: bytes,
    tasks_raw: list[dict],
    filename: str,
    request: dict,
) -> dict | None:
    """Run the internal validator on rendered SWMS output and log the result.

    Returns the validator result as a dict (for response headers),
    or None if validation is skipped/fails.
    Writes _validator_result.json alongside output. Always advisory.
    """
    try:
        from core.validator_runner import run_internal_validator, StreamConfig
        from src.issue_gate import Stage

        stage_str = request.get("validation_stage", "benchmark")
        stage = Stage.ISSUE_READY if stage_str == "issue_ready" else Stage.BENCHMARK
        wah_threshold = request.get("wah_threshold", 50)
        allowed_kw = tuple(request.get("allowed_keywords", []))

        config = StreamConfig(
            stage=stage, wah_threshold=wah_threshold, allowed_keywords=allowed_kw,
        )
        result = run_internal_validator(tasks=tasks_raw, stream_config=config)

        import json as _json
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "outputs")
        if os.path.isdir(output_dir):
            base = filename.rsplit(".", 1)[0] if "." in filename else filename
            result_path = os.path.join(output_dir, f"{base}_validator_result.json")
            with open(result_path, "w", encoding="utf-8") as f:
                _json.dump({
                    "status": result.status.value,
                    "failing_checks": result.failing_checks,
                    "review_checks": result.review_checks,
                    "suggested_action": result.suggested_action,
                    "retry_recommended": result.retry_recommended,
                    "defect_classifications": result.defect_classifications,
                }, f, indent=2)

        summary = {
            "status": result.status.value,
            "failing_count": len(result.failing_checks),
            "review_count": len(result.review_checks),
            "suggested_action": result.suggested_action,
        }

        # If ESCALATE_EXTERNAL, trigger parallel reviewer agent
        if result.status.value == "ESCALATE_EXTERNAL":
            try:
                import asyncio as _asyncio
                from core.reviewer_agent import run_parallel_review

                scope_text = request.get("description", "")
                if not scope_text:
                    scope_text = request.get("project_meta", {}).get("work_activity", "")
                job_type_val = request.get("job_type", "")

                loop = _asyncio.new_event_loop()
                reviewer_result = loop.run_until_complete(
                    run_parallel_review(
                        swms_content=_json.dumps(tasks_raw, default=str, separators=(',', ':')),
                        scope_content=scope_text,
                        job_type=job_type_val,
                    )
                )
                loop.close()

                # Write reviewer result JSON
                if os.path.isdir(output_dir):
                    reviewer_path = os.path.join(output_dir, f"{base}_reviewer_result.json")
                    with open(reviewer_path, "w", encoding="utf-8") as f:
                        _json.dump(reviewer_result.to_dict(), f, indent=2)

                summary["reviewer_status"] = reviewer_result.overall_status
                summary["reviewer_action"] = reviewer_result.recommended_action
            except Exception as rev_err:
                logger.warning(f"Reviewer agent skipped: {rev_err}")

        # Capture findings into the findings store
        try:
            from core.findings_store import FindingRecord, append_finding
            stream = request.get("stream_name", request.get("project_meta", {}).get("project_name", ""))
            jt = request.get("job_type", "")
            for fc in result.failing_checks:
                append_finding(FindingRecord(
                    stream_name=stream, job_type=jt, task_name="",
                    defect_type="deterministic_fix", check_name=fc.split(":")[0] if ":" in fc else fc,
                    finding_text=fc, source="validator", severity="hard_fail",
                ))
            for rc in result.review_checks:
                append_finding(FindingRecord(
                    stream_name=stream, job_type=jt, task_name="",
                    defect_type="flag_for_review", check_name=rc.split(":")[0] if ":" in rc else rc,
                    finding_text=rc, source="validator", severity="review_flag",
                ))
            if result.status.value == "ESCALATE_EXTERNAL" and "reviewer_status" in summary:
                try:
                    for hf in reviewer_result.hard_fails:
                        cat = hf.split("]")[0].strip("[") if "[" in hf else ""
                        append_finding(FindingRecord(
                            stream_name=stream, job_type=jt, task_name="",
                            defect_type="expert_review_only", check_name="reviewer_hard_fail",
                            finding_text=hf, source="reviewer_agent",
                            reviewer_agent_category=cat, severity="hard_fail",
                        ))
                    for ri in reviewer_result.review_items:
                        cat = ri.split("]")[0].strip("[") if "[" in ri else ""
                        append_finding(FindingRecord(
                            stream_name=stream, job_type=jt, task_name="",
                            defect_type="flag_for_review", check_name="reviewer_review_item",
                            finding_text=ri, source="reviewer_agent",
                            reviewer_agent_category=cat, severity="review_flag",
                        ))
                except NameError:
                    pass  # reviewer_result not available
        except Exception as findings_err:
            logger.warning(f"Findings capture skipped: {findings_err}")

        return summary
    except Exception as e:
        logger.warning(f"Post-render validation skipped: {e}")
        return None


def _build_filename(project_meta: dict, ext: str) -> str:
    """Build SWMS-{ddmmyyyy}-V1.{ext} filename — matches footer text format."""
    from datetime import date
    d = project_meta.get("date", "")
    if d:
        # Normalise: strip slashes/hyphens to get digits only
        d = d.replace("/", "").replace("-", "")
    if not d or not d.isdigit():
        d = date.today().strftime("%d%m%Y")
    return f"SWMS-{d}-V1.{ext}"


def _render_tasks_to_docx(request: dict, jurisdiction: str = "AU") -> tuple[bytes, str]:
    """Shared helper: parse request, render docx, return (bytes, filename)."""
    from core.schema import TaskBlock
    from renderers.docx_renderer import render_swms_document

    tasks_raw = request.get("tasks", [])
    project_meta = request.get("project_meta", {})
    inference = request.get("inference", {})
    filename = request.get("filename") or _build_filename(project_meta, "docx")
    if not filename.endswith(".docx"):
        filename += ".docx"

    if not tasks_raw:
        raise ValueError("No tasks provided")

    from core.validate import normalise_monitoring_freq

    task_blocks = []
    for t in tasks_raw:
        t.setdefault("responsibility", {"SUP": "Supervise task", "WKR": "Perform task per SWMS"})
        t.setdefault("scope", "")
        t.setdefault("risk_pre", "M")
        t.setdefault("risk_post", "L")
        t.setdefault("source", "ai-generated")
        if t.get("monitoring"):
            t["monitoring"] = normalise_monitoring_freq(t["monitoring"])
        try:
            task_blocks.append(TaskBlock(**{k: v for k, v in t.items() if k in TaskBlock.model_fields}))
        except Exception as e:
            logger.warning(f"Task deserialization failed, skipping: {e}")
            continue

    from core.validate import guard_tasks
    task_blocks = guard_tasks(task_blocks)
    docx_bytes = render_swms_document(task_blocks, project_meta, inference, jurisdiction=jurisdiction)
    return docx_bytes, filename


@app.post("/render/pdf")
async def render_pdf_endpoint(request: dict, user: dict = Depends(get_current_user)):
    """
    POST /render/pdf
    Same body as /render/docx. Returns PDF file download.
    """
    from renderers.pdf_renderer import docx_to_pdf

    cid = get_correlation_id()
    await record_state(cid, "render_pdf", "received", {"path": "/render/pdf"})
    try:
        docx_bytes, docx_filename = _render_tasks_to_docx(request)
        pdf_bytes = docx_to_pdf(docx_bytes)
        pdf_filename = docx_filename.rsplit(".", 1)[0] + ".pdf"

        await record_state(cid, "render_pdf", "complete", {"path": "/render/pdf"})
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{pdf_filename}"'},
        )
    except ValueError as e:
        await record_state(
            cid,
            "render_pdf",
            "failed",
            {"path": "/render/pdf", "error": type(e).__name__, "detail": str(e)[:200]},
        )
        return JSONResponse(content={"error": str(e)}, status_code=400)
    except Exception as e:
        await record_state(
            cid,
            "render_pdf",
            "failed",
            {"path": "/render/pdf", "error": type(e).__name__, "detail": str(e)[:200]},
        )
        logger.error(f"Render PDF failed:\n{traceback.format_exc()}")
        return JSONResponse(content={"detail": f"Render failed: {type(e).__name__}: {e}"}, status_code=500)


@app.post("/render/both")
async def render_both_endpoint(request: dict, user: dict = Depends(get_current_user)):
    """
    POST /render/both
    Returns JSON with base64-encoded DOCX and PDF.
    """
    import base64
    from renderers.pdf_renderer import docx_to_pdf

    try:
        docx_bytes, docx_filename = _render_tasks_to_docx(request)
        pdf_bytes = docx_to_pdf(docx_bytes)
        pdf_filename = docx_filename.rsplit(".", 1)[0] + ".pdf"

        return JSONResponse(content={
            "docx": base64.b64encode(docx_bytes).decode(),
            "pdf": base64.b64encode(pdf_bytes).decode(),
            "docx_filename": docx_filename,
            "pdf_filename": pdf_filename,
        })
    except ValueError as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"Render both failed:\n{traceback.format_exc()}")
        return JSONResponse(content={"detail": f"Render failed: {type(e).__name__}: {e}"}, status_code=500)


# ============================================================
# RISK ASSESSMENT ENDPOINTS
# ============================================================

@app.post("/generate/ra")
async def generate_ra(request: dict, user: dict = Depends(get_current_user)):
    """
    POST /generate/ra
    Generate Risk Assessment hazard list from work description.
    Returns inference with hazard_list for RA rendering.
    """
    from core.inference_matrix import infer_to_dict_ra
    try:
        description = request.get("description", "")
        project_meta = request.get("project_meta", {})
        jurisdiction = request.get("jurisdiction", "AU")
        ca_province = request.get("ca_province", "")

        if not project_meta.get("work_activity"):
            first_sentence = description.split(".")[0].strip()
            project_meta["work_activity"] = first_sentence[:200] if first_sentence else description[:200]
        if not project_meta.get("description"):
            project_meta["description"] = description

        inference = infer_to_dict_ra(description, jurisdiction=jurisdiction, ca_province=ca_province)
        return {
            "hazards": inference.get("hazard_list", []),
            "inference": inference,
            "project_meta": project_meta,
            "hazard_count": len(inference.get("hazard_list", [])),
        }
    except Exception as e:
        logger.error(f"Generate RA failed:\n{traceback.format_exc()}")
        return {"detail": "An internal error occurred. Please try again."}


@app.post("/render/ra")
async def render_ra_endpoint(request: dict, user: dict = Depends(get_current_user)):
    """
    POST /render/ra
    Accepts {"hazards": [...], "project_meta": {...}, "inference": {...}, "jurisdiction": "AU"}
    Renders hazard register into a Risk Assessment Word document.
    """
    try:
        docx_bytes, filename = _render_ra_to_docx(request)
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ValueError as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"Render RA failed:\n{traceback.format_exc()}")
        return JSONResponse(content={"detail": "An internal error occurred. Please try again."}, status_code=500)


# ============================================================
# RA PDF / BOTH ENDPOINTS
# ============================================================

def _render_ra_to_docx(request: dict) -> tuple[bytes, str]:
    """Shared helper: parse RA request, render docx, return (bytes, filename)."""
    from renderers.ra_renderer import render_ra_document
    from core.jurisdictions import get_jurisdiction
    from datetime import date as _date

    hazards = request.get("hazards", [])
    project_meta = request.get("project_meta", {})
    inference = request.get("inference", {})
    jurisdiction = request.get("jurisdiction", "AU")
    ca_province = request.get("ca_province", "")

    if not hazards:
        raise ValueError("No hazards provided")

    docx_bytes = render_ra_document(
        hazards, project_meta, inference,
        jurisdiction=jurisdiction, ca_province=ca_province,
    )

    name = project_meta.get("project_name", "Output")
    safe = "".join(c if c.isalnum() or c in " -_" else "" for c in name).strip()
    safe = safe.replace(" ", "-")[:40]
    jur = get_jurisdiction(jurisdiction, ca_province=ca_province)
    d = _date.today().strftime(jur["date_format"]).replace("/", "").replace("-", "")
    version = project_meta.get("version", "1.0").replace(".", "")
    filename = request.get("filename") or f"RA-{safe}-{d}-V{version.zfill(2)}.docx"
    if not filename.endswith(".docx"):
        filename += ".docx"

    return docx_bytes, filename


@app.post("/render/ra/pdf")
async def render_ra_pdf_endpoint(request: dict, user: dict = Depends(get_current_user)):
    """POST /render/ra/pdf — Render RA as PDF."""
    from renderers.pdf_renderer import docx_to_pdf
    try:
        docx_bytes, docx_filename = _render_ra_to_docx(request)
        pdf_bytes = docx_to_pdf(docx_bytes)
        pdf_filename = docx_filename.rsplit(".", 1)[0] + ".pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{pdf_filename}"'},
        )
    except ValueError as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"Render RA PDF failed:\n{traceback.format_exc()}")
        return JSONResponse(content={"detail": "An internal error occurred. Please try again."}, status_code=500)


@app.post("/render/ra/both")
async def render_ra_both_endpoint(request: dict, user: dict = Depends(get_current_user)):
    """POST /render/ra/both — Render RA as both DOCX and PDF (base64 JSON)."""
    import base64
    from renderers.pdf_renderer import docx_to_pdf
    try:
        docx_bytes, docx_filename = _render_ra_to_docx(request)
        pdf_bytes = docx_to_pdf(docx_bytes)
        pdf_filename = docx_filename.rsplit(".", 1)[0] + ".pdf"
        return JSONResponse(content={
            "docx": base64.b64encode(docx_bytes).decode(),
            "pdf": base64.b64encode(pdf_bytes).decode(),
            "docx_filename": docx_filename,
            "pdf_filename": pdf_filename,
        })
    except ValueError as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"Render RA both failed:\n{traceback.format_exc()}")
        return JSONResponse(content={"detail": "An internal error occurred. Please try again."}, status_code=500)


# ============================================================
# PROCORE WEBHOOK — PHASE 1 SPIKE
# ============================================================

import os as _os
from pathlib import Path as _Path

_PROCORE_WEBHOOK_SECRET = _os.getenv("PROCORE_WEBHOOK_SECRET", "")
_PROCORE_RULE_PACKS_DIR = _Path(__file__).parent.parent / "src" / "data" / "procore_rule_packs"


@app.post("/v1/procore/webhook")
async def procore_webhook_endpoint(request: Request):
    """
    POST /v1/procore/webhook

    Receives Procore submittal events, extracts SWMS PDF,
    runs bounded pre-screen review, returns structured artifact.
    Human review is mandatory. Does not make approval decisions.

    Phase 1: Submittals surface only.
    """
    from core.procore.webhook_handler import (
        extract_submittal_attachments,
        is_duplicate,
        log_payload,
        log_review,
        parse_event,
        validate_signature,
    )
    from core.procore.prescreen_reviewer import run_prescreen_review

    # Read raw body for signature validation
    body = await request.body()

    # Validate webhook signature if secret is configured
    if _PROCORE_WEBHOOK_SECRET:
        sig = request.headers.get("X-Procore-Signature", "")
        if not validate_signature(body, sig, _PROCORE_WEBHOOK_SECRET):
            return JSONResponse(
                content={"error": "Invalid webhook signature"},
                status_code=401,
            )

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return JSONResponse(content={"error": "Invalid JSON"}, status_code=400)

    event = parse_event(payload)

    # Log payload for replay/debugging
    log_payload(event)

    # Idempotency check
    if event.delivery_id and is_duplicate(event.delivery_id):
        return JSONResponse(content={"status": "already_processed", "delivery_id": event.delivery_id})

    # Phase 1: only handle submittal events
    if "submittal" not in event.event_type:
        return JSONResponse(content={"status": "ignored", "reason": "not a submittal event"})

    # Extract PDF attachments
    attachments = extract_submittal_attachments(event)
    if not attachments:
        return JSONResponse(content={
            "status": "no_pdf",
            "reason": "No PDF attachments found in submittal",
        })

    # Load project rule pack
    _PROCORE_RULE_PACKS_DIR.mkdir(parents=True, exist_ok=True)
    rule_pack_path = _PROCORE_RULE_PACKS_DIR / f"project_{event.project_id}.json"
    if not rule_pack_path.exists():
        return JSONResponse(content={
            "status": "no_rule_pack",
            "reason": f"No project rule pack found for project {event.project_id}",
            "project_id": event.project_id,
        })

    with open(rule_pack_path, encoding="utf-8") as f:
        rule_pack = json.load(f)

    att = attachments[0]
    swms_text = ""
    retrieval_mode = "none"

    # Phase 1B: try live Procore API retrieval first
    try:
        from core.procore.api_client import fetch_attachment, is_live_configured
        if is_live_configured() and att.url:
            pdf_bytes = fetch_attachment(event.project_id, att.url)
            from core.intake_extractor import extract_from_pdf
            extraction = extract_from_pdf(pdf_bytes, source_label=att.filename)
            if extraction.text_extraction_succeeded:
                swms_text = extraction.raw_text
                retrieval_mode = "live_api"
                logger.info(f"Live retrieval: {len(swms_text)} chars from {att.filename}")
    except Exception as live_err:
        logger.warning(f"Live Procore retrieval failed: {live_err}")

    # Phase 1A fallback: simulated/fixture text
    if not swms_text:
        swms_text = payload.get("_simulated_swms_text", "")
        if swms_text:
            retrieval_mode = "simulated"

    if not swms_text:
        fixture_path = payload.get("_fixture_pdf_text_path", "")
        if fixture_path and _Path(fixture_path).exists():
            swms_text = _Path(fixture_path).read_text(encoding="utf-8")
            retrieval_mode = "fixture"

    if not swms_text:
        return JSONResponse(content={
            "status": "no_text",
            "reason": f"Could not extract text from {att.filename}. "
                      "Configure PROCORE_ACCESS_TOKEN for live retrieval, "
                      "or provide _simulated_swms_text for testing.",
            "attachment": att.filename,
        })

    # Run pre-screen review
    review_artifact = run_prescreen_review(
        swms_text, rule_pack,
        job_id=f"procore-{event.project_id}-{event.resource_id}",
        document_reference=att.filename,
        source_surface="submittals",
        source_item_id=str(event.resource_id),
    )

    # Log review and store full artifact for Phase 3 comparison
    log_review(review_artifact, event)
    try:
        from core.procore.review_store import store_artifact
        store_artifact(review_artifact)
    except Exception:
        logger.warning("Failed to store review artifact for comparison")

    # Phase 3: resubmission comparison
    comparison = None
    try:
        from core.procore.review_store import find_previous_artifact
        from core.procore.resubmission_comparison import compare_reviews
        previous = find_previous_artifact(
            project_id=str(event.project_id),
            source_surface="submittals",
            source_item_id=str(event.resource_id),
            exclude_run_id=review_artifact.get("review_run_id", ""),
        )
        if previous:
            comparison = compare_reviews(review_artifact, previous, current_swms_text=swms_text)
    except Exception as cmp_err:
        logger.warning(f"Resubmission comparison failed: {cmp_err}")

    # Phase 1B: post comment back to Procore if live and configured
    comment_posted = False
    try:
        from core.procore.api_client import (
            format_review_as_comment,
            is_live_configured,
            post_submittal_comment,
        )
        if is_live_configured() and retrieval_mode == "live_api":
            comment_text = format_review_as_comment(review_artifact, att.filename)
            post_submittal_comment(event.project_id, event.resource_id, comment_text)
            comment_posted = True
    except Exception as comment_err:
        logger.warning(f"Procore comment post failed: {comment_err}")

    response_content = {
        "status": "reviewed",
        "delivery_id": event.delivery_id,
        "project_id": event.project_id,
        "attachment": att.filename,
        "retrieval_mode": retrieval_mode,
        "comment_posted": comment_posted,
        "review": review_artifact,
    }
    if comparison:
        response_content["comparison"] = comparison
    return JSONResponse(content=response_content)


# ============================================================
# INTAKE NORMALIZER
# ============================================================


@app.post("/v1/swms/intake")
async def intake_normalize_endpoint(
    source_text: str = Form(default=""),
    source_file: UploadFile = File(default=None),
    source_type: str = Form(default="pasted_text"),
    source_label: str = Form(default=""),
    clarification_note: str = Form(default=""),
):
    """
    POST /v1/swms/intake

    Create a reviewable job-brief draft from a single text-bearing intake source.
    Consultant review is mandatory before generation.
    Does not start generation. Returns a draft artifact only.
    """
    from core.intake_extractor import (
        extract_from_docx,
        extract_from_pdf,
        extract_from_text,
    )
    from core.intake_normalizer import normalize_intake

    try:
        if source_file and source_file.filename:
            file_bytes = await source_file.read()
            label = source_label or source_file.filename or ""
            fname = (source_file.filename or "").lower()
            if fname.endswith(".pdf"):
                extraction = extract_from_pdf(file_bytes, source_label=label)
            elif fname.endswith((".docx", ".doc")):
                extraction = extract_from_docx(file_bytes, source_label=label)
            else:
                # Try as text
                try:
                    text = file_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    text = file_bytes.decode("latin-1", errors="replace")
                extraction = extract_from_text(text, source_type="pasted_text", source_label=label)
        elif source_text:
            extraction = extract_from_text(
                source_text,
                source_type=source_type,
                source_label=source_label,
            )
        else:
            return JSONResponse(
                content={"error": "Provide source_text or source_file"},
                status_code=400,
            )

        result = normalize_intake(extraction, clarification_note=clarification_note)
        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Intake normalization failed:\n{traceback.format_exc()}")
        return JSONResponse(
            content={"detail": "An internal error occurred. Please try again."},
            status_code=500,
        )


# ============================================================
# PROJECT REQUIREMENTS INTAKE
# ============================================================


@app.post("/v1/project/requirements")
async def project_requirements_endpoint(
    source_text: str = Form(default=""),
    source_file: UploadFile = File(default=None),
    source_type: str = Form(default="pasted_text"),
    source_label: str = Form(default=""),
    clarification_note: str = Form(default=""),
):
    """
    POST /v1/project/requirements

    Create a reviewable project rule pack from a single text-bearing source.
    Human review is mandatory before the pack is treated as active.
    Does not approve or reject any SWMS. Returns a draft rule pack only.
    """
    from core.intake_extractor import (
        extract_from_docx,
        extract_from_pdf,
        extract_from_text,
    )
    from core.project_requirements import normalize_project_requirements

    try:
        if source_file and source_file.filename:
            file_bytes = await source_file.read()
            label = source_label or source_file.filename or ""
            fname = (source_file.filename or "").lower()
            if fname.endswith(".pdf"):
                extraction = extract_from_pdf(file_bytes, source_label=label)
            elif fname.endswith((".docx", ".doc")):
                extraction = extract_from_docx(file_bytes, source_label=label)
            else:
                try:
                    text = file_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    text = file_bytes.decode("latin-1", errors="replace")
                extraction = extract_from_text(text, source_type="pasted_text", source_label=label)
        elif source_text:
            extraction = extract_from_text(
                source_text,
                source_type=source_type,
                source_label=source_label,
            )
        else:
            return JSONResponse(
                content={"error": "Provide source_text or source_file"},
                status_code=400,
            )

        result = normalize_project_requirements(extraction, clarification_note=clarification_note)
        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Project requirements intake failed:\n{traceback.format_exc()}")
        return JSONResponse(
            content={"detail": "An internal error occurred. Please try again."},
            status_code=500,
        )


# ============================================================
# CONSULTANT EDIT CAPTURE
# ============================================================

import threading
_edit_capture_lock = threading.Lock()


@app.post("/v1/swms/capture-edits")
async def capture_edits_endpoint(
    generated_docx: UploadFile = File(...),
    reviewed_docx: UploadFile = File(...),
    job_id: str = Form(...),
    review_duration_mins: int = Form(...),
    would_issue: str = Form(...),
    main_edit_categories: str = Form(""),
):
    """
    POST /v1/swms/capture-edits

    Compare generated SWMS docx to consultant-reviewed docx.
    Stores only structured edit signals — no raw document content.
    """
    from datetime import datetime, timezone
    from core.edit_capture import (
        compute_edit_delta,
        extract_swms_table_text,
        fingerprint_snapshot,
    )

    try:
        gen_bytes = await generated_docx.read()
        rev_bytes = await reviewed_docx.read()

        gen_rows = extract_swms_table_text(gen_bytes)
        rev_rows = extract_swms_table_text(rev_bytes)

        gen_fp = fingerprint_snapshot(gen_rows)
        rev_fp = fingerprint_snapshot(rev_rows)

        delta = compute_edit_delta(gen_rows, rev_rows)

        # Normalize categories
        categories = [
            c.strip().lower()
            for c in main_edit_categories.split(",")
            if c.strip()
        ]

        # Parse would_issue from form string
        would_issue_bool = would_issue.lower() in ("true", "1", "yes")

        record = {
            "capture_version": "1.0",
            "job_id": job_id,
            "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "review_duration_mins": review_duration_mins,
            "would_issue": would_issue_bool,
            "main_edit_categories": categories,
            "changed_task_count": delta["changed_task_count"],
            "total_task_count": delta["total_task_count"],
            "generated_row_count": delta["generated_row_count"],
            "reviewed_row_count": delta["reviewed_row_count"],
            "average_similarity_ratio": delta["average_similarity_ratio"],
            "changed_responsibilities_count": delta["changed_responsibilities_count"],
            "major_rewrite_detected": delta["major_rewrite_detected"],
            "generated_doc_fingerprint": gen_fp,
            "reviewed_doc_fingerprint": rev_fp,
        }

        # Append to JSONL — thread-safe for single-process use
        import json
        from pathlib import Path
        edits_path = Path(__file__).parent.parent / "src" / "data" / "consultant_edits.jsonl"
        edits_path.parent.mkdir(parents=True, exist_ok=True)
        with _edit_capture_lock:
            with open(edits_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return JSONResponse(content=record)

    except ValueError as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"Edit capture failed:\n{traceback.format_exc()}")
        return JSONResponse(
            content={"detail": "An internal error occurred. Please try again."},
            status_code=500,
        )


# ============================================================
# WAITLIST
# ============================================================

_WAITLIST_PATH = os.path.join(_ROOT, "data", "waitlist.json")
_DEMO_LEADS_PATH = os.path.join(_ROOT, "data", "demo_leads.json")


@app.post("/demo/email-capture")
@limiter.limit("10/hour")
async def demo_email_capture(request: Request):
    """Capture email from demo page — no auth required."""
    from datetime import datetime, timezone
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(content={"detail": "Invalid JSON"}, status_code=400)

    email = str(body.get("email", "")).strip()
    if not email or "@" not in email:
        return JSONResponse(content={"detail": "Valid email required"}, status_code=422)

    context = str(body.get("context", ""))[:200]

    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "email": email,
        "context": context,
    }

    os.makedirs(os.path.dirname(_DEMO_LEADS_PATH), exist_ok=True)
    import json as _json
    existing = []
    if os.path.exists(_DEMO_LEADS_PATH):
        try:
            with open(_DEMO_LEADS_PATH, encoding="utf-8") as f:
                existing = _json.load(f)
        except Exception:
            existing = []
    existing.append(entry)
    with open(_DEMO_LEADS_PATH, "w", encoding="utf-8") as f:
        _json.dump(existing, f, indent=2, ensure_ascii=False)

    return JSONResponse(content={"status": "ok"})


@app.post("/waitlist/submit")
@limiter.limit("5/hour")
async def waitlist_submit(request: Request):
    """Accept waitlist signup — no auth required. Rate limited 5/hour/IP."""
    from datetime import datetime, timezone
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(content={"detail": "Invalid JSON"}, status_code=400)

    # Validate required fields
    _REQUIRED = ("name", "company", "role", "email", "swms_per_month", "state")
    missing = [f for f in _REQUIRED if not str(body.get(f, "")).strip()]
    if missing:
        return JSONResponse(
            content={"detail": f"Missing required fields: {', '.join(missing)}"},
            status_code=422,
        )
    email = str(body.get("email", "")).strip()
    if "@" not in email:
        return JSONResponse(
            content={"detail": "Invalid email address"},
            status_code=422,
        )

    # Normalize procore_user to bool
    pu = body.get("procore_user", False)
    if isinstance(pu, str):
        pu = pu.lower() in ("true", "yes", "1")

    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "name": str(body.get("name", "")).strip(),
        "company": str(body.get("company", "")).strip(),
        "role": str(body.get("role", "")).strip(),
        "email": email,
        "swms_per_month": str(body.get("swms_per_month", "")).strip(),
        "procore_user": pu,
        "state": str(body.get("state", "")).strip(),
        "review_method": str(body.get("review_method", "")).strip(),
    }

    os.makedirs(os.path.dirname(_WAITLIST_PATH), exist_ok=True)

    import json as _json
    existing = []
    if os.path.exists(_WAITLIST_PATH):
        try:
            with open(_WAITLIST_PATH, encoding="utf-8") as f:
                existing = _json.load(f)
        except Exception:
            existing = []
    existing.append(entry)
    with open(_WAITLIST_PATH, "w", encoding="utf-8") as f:
        _json.dump(existing, f, indent=2, ensure_ascii=False)

    return JSONResponse(content={"status": "ok", "message": "Application received"})


# ============================================================
# JURISDICTION CHECK
# ============================================================

@app.get("/check-jurisdiction")
def check_jurisdiction(q: str, selected: str = "AU"):
    """
    GET /check-jurisdiction?q=<text>&selected=AU
    Detect if job description contains signals for a different jurisdiction.
    """
    from vocab.standards_registry import detect_jurisdiction_from_query
    try:
        result = detect_jurisdiction_from_query(q, selected)
    except Exception:
        logger.error(f"Jurisdiction detection failed:\n{traceback.format_exc()}")
        result = {"mismatch": False, "detected": selected}
    return JSONResponse(content=result, headers={"Cache-Control": "private, max-age=60"})


# ============================================================
# VERSIONED API — /v1/ (service account + JWT auth)
# ============================================================

from fastapi import APIRouter
v1 = APIRouter(prefix="/v1")


@v1.post("/generate/stream")
async def v1_generate_stream(request: dict, auth: dict = Depends(get_user_or_api_key)):
    """POST /v1/generate/stream — SSE stream with API key or JWT auth."""
    import json as _json
    import time as _time
    from core.orchestrator import generate_swms_stream

    cid = get_correlation_id()
    await record_state(cid, "swms_generate", "received", {"path": "/v1/generate/stream"})

    description = (request.get("description") or "").strip()
    if not description or len(description.split()) < 3:
        return JSONResponse(
            content={"detail": "Description is required (at least 3 words)."},
            status_code=422,
        )
    project_meta = request.get("project_meta", {})
    force_full = request.get("force_full", False)
    force_simple = request.get("force_simple", False)
    jurisdiction = request.get("jurisdiction", "AU")
    scope_context = request.get("scope_context")

    start_ms = _time.monotonic_ns() // 1_000_000

    async def event_generator():
        import asyncio
        success = True
        try:
            stream = generate_swms_stream(
                description=description,
                project_meta=project_meta,
                force_full=force_full,
                force_simple=force_simple,
                jurisdiction=jurisdiction,
                scope_context=scope_context,
            )
            stream_iter = stream.__aiter__()
            while True:
                try:
                    event = await asyncio.wait_for(stream_iter.__anext__(), timeout=15.0)
                    yield f"data: {_json.dumps(event)}\n\n"
                except StopAsyncIteration:
                    break
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
            await record_state(cid, "swms_generate", "complete", {"path": "/v1/generate/stream"})
        except Exception as e:
            success = False
            await record_state(
                cid,
                "swms_generate",
                "failed",
                {"path": "/v1/generate/stream", "error": type(e).__name__, "detail": str(e)[:200]},
            )
            logger.error(f"v1 stream generation failed:\n{traceback.format_exc()}")
            yield f"data: {_json.dumps({'type': 'error', 'message': 'An internal error occurred. Please try again.'})}\n\n"
            raise
        finally:
            if auth.get("key_id"):
                elapsed = (_time.monotonic_ns() // 1_000_000) - start_ms
                log_api_key_usage(
                    key_id=auth["key_id"],
                    endpoint="/v1/generate/stream",
                    description_length=len(description),
                    duration_ms=elapsed,
                    success=success,
                )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@v1.post("/render/docx")
async def v1_render_docx(request: dict, auth: dict = Depends(get_user_or_api_key)):
    """POST /v1/render/docx — Render DOCX with API key or JWT auth."""
    try:
        jurisdiction = request.get("jurisdiction", "AU")
        docx_bytes, filename = _render_tasks_to_docx(request, jurisdiction=jurisdiction)
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ValueError as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"v1 render DOCX failed:\n{traceback.format_exc()}")
        return JSONResponse(content={"detail": "An internal error occurred. Please try again."}, status_code=500)


@v1.post("/render/pdf")
async def v1_render_pdf(request: dict, auth: dict = Depends(get_user_or_api_key)):
    """POST /v1/render/pdf — Render PDF with API key or JWT auth."""
    from renderers.pdf_renderer import docx_to_pdf
    try:
        docx_bytes, docx_filename = _render_tasks_to_docx(request)
        pdf_bytes = docx_to_pdf(docx_bytes)
        pdf_filename = docx_filename.rsplit(".", 1)[0] + ".pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{pdf_filename}"'},
        )
    except ValueError as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"v1 render PDF failed:\n{traceback.format_exc()}")
        return JSONResponse(content={"detail": "An internal error occurred. Please try again."}, status_code=500)


from pims.routes import router as pims_router
app.include_router(pims_router)
app.include_router(v1)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

#!/usr/bin/env python3
"""
api/main.py — Gatekeeper web interface.

Endpoints:
  GET  /          → task generation form (index.html)
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
import traceback

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
from fastapi.templating import Jinja2Templates
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
from core.api_keys import get_user_or_api_key, log_api_key_usage

app = FastAPI(title="Gatekeeper SWMS Generator", version="1.0")
app.add_middleware(GZipMiddleware, minimum_size=1000)

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

app.include_router(upload_router)
app.include_router(intake_router)

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

_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
templates = Jinja2Templates(directory=_TEMPLATE_DIR)
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


@app.get("/ra", response_class=HTMLResponse)
async def serve_ra():
    # RA spec TBD — serve dashboard for now
    return _html_response(os.path.join(_FRONTEND_DIR, "dashboard.html"))


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


@app.get("/", response_class=HTMLResponse)
async def index():
    return _html_response(os.path.join(_FRONTEND_DIR, "login.html"))


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
        from renderers.docx_renderer import render_docx
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
            docx_bytes = render_docx(task)
            import base64
            result["docx_b64"] = base64.b64encode(docx_bytes).decode()
            result["docx_filename"] = f"{task.task.replace(' ', '_')[:40]}.docx"

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


@app.get("/health")
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

    description = request.get("description", "")
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
        except Exception as e:
            logger.error(f"Stream generation failed:\n{traceback.format_exc()}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'An internal error occurred. Please try again.'})}\n\n"

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
    """
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
        logger.error(f"Render DOCX failed:\n{traceback.format_exc()}")
        return JSONResponse(content={"detail": "An internal error occurred. Please try again."}, status_code=500)


def _build_filename(project_meta: dict, ext: str) -> str:
    """Build SWMS-<address-slug>-<date>-V01.<ext> filename."""
    import re
    from datetime import date
    # Prefer project_address (intake flow), fall back to project_name
    raw = (project_meta.get("project_address")
           or project_meta.get("project_name")
           or "Output")
    # Strip unit/level prefixes, postcodes, state codes, country
    raw = re.sub(r'(?i)\b(unit|level|suite|lot|shop)\s*\d+[,/]?\s*', '', raw)
    raw = re.sub(r'\b(NSW|VIC|QLD|SA|WA|TAS|NT|ACT)\b', '', raw, flags=re.IGNORECASE)
    raw = re.sub(r'\b\d{4}\b', '', raw)  # strip postcodes
    raw = re.sub(r'(?i)\b(australia)\b', '', raw)
    # Keep only alphanumeric, spaces, hyphens
    safe = "".join(c if c.isalnum() or c in " -" else " " for c in raw).strip()
    # Collapse whitespace, convert to hyphen-separated
    safe = re.sub(r'\s+', '-', safe).strip('-')
    # Cap at suburb: keep up to 5 hyphen-separated tokens (e.g. 218-Vincent-Rd-Cranebrook)
    parts = safe.split('-')
    safe = '-'.join(parts[:5]) if len(parts) > 5 else safe
    safe = safe[:40]
    d = date.today().strftime("%y%m%d")
    version = project_meta.get("version", "1.0").replace(".", "")
    return f"SWMS-{safe}-{d}-V{version.zfill(2)}.{ext}"


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

    # Sanitise monitoring frequency
    _VALID_FREQ = {"before each use", "each shift start", "continuous", "daily", "weekly"}
    _FREQ_MAP = {
        "before use": "before each use", "prior to each use": "before each use",
        "pre-use": "before each use", "start of shift": "each shift start",
        "shift start": "each shift start", "per shift": "each shift start",
        "every shift": "each shift start", "before each shift start": "each shift start",
        "ongoing": "continuous", "continuously": "continuous",
        "constant": "continuous", "real-time": "continuous",
        "each day": "daily", "every day": "daily", "once daily": "daily",
        "each week": "weekly", "once weekly": "weekly", "every week": "weekly",
    }

    def _sanitise_monitoring(mon):
        if not isinstance(mon, dict):
            return None
        freq = mon.get("frequency", "")
        if freq not in _VALID_FREQ:
            mon["frequency"] = _FREQ_MAP.get(freq.lower().strip(), "daily")
        return mon

    task_blocks = []
    for t in tasks_raw:
        t.setdefault("responsibility", {"SUP": "Supervise task", "WKR": "Perform task per SWMS"})
        t.setdefault("scope", "")
        t.setdefault("risk_pre", "M")
        t.setdefault("risk_post", "L")
        t.setdefault("source", "ai-generated")
        if t.get("monitoring"):
            t["monitoring"] = _sanitise_monitoring(t["monitoring"])
        try:
            task_blocks.append(TaskBlock(**{k: v for k, v in t.items() if k in TaskBlock.model_fields}))
        except Exception:
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
        logger.error(f"Render PDF failed:\n{traceback.format_exc()}")
        return JSONResponse(content={"detail": "An internal error occurred. Please try again."}, status_code=500)


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
        return JSONResponse(content={"detail": "An internal error occurred. Please try again."}, status_code=500)


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
# JURISDICTION CHECK
# ============================================================

@app.get("/check-jurisdiction")
def check_jurisdiction(q: str, selected: str = "AU"):
    """
    GET /check-jurisdiction?q=<text>&selected=AU
    Detect if job description contains signals for a different jurisdiction.
    """
    from vocab.standards_registry import detect_jurisdiction_from_query
    result = detect_jurisdiction_from_query(q, selected)
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

    description = request.get("description", "")
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
        except Exception as e:
            success = False
            logger.error(f"v1 stream generation failed:\n{traceback.format_exc()}")
            yield f"data: {_json.dumps({'type': 'error', 'message': 'An internal error occurred. Please try again.'})}\n\n"
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


app.include_router(v1)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)


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

import io
import json
import logging
import os
import sys
import traceback

logger = logging.getLogger(__name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(_ROOT, ".env"))

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from core.auth import (
    get_current_user, get_optional_user,
    signup, login, refresh_session, sign_out, reset_password,
    FRONTEND_URL,
)
from api.upload_routes import router as upload_router

app = FastAPI(title="Gatekeeper SWMS Generator", version="1.0")
app.include_router(upload_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
templates = Jinja2Templates(directory=_TEMPLATE_DIR)
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

import sqlite3
DB_PATH = os.path.join(_ROOT, "db", "gatekeeper.db")


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


# ============================================================
# AUTH ENDPOINTS
# ============================================================

@app.post("/auth/signup")
async def auth_signup(body: AuthSignup):
    result = signup(body.email, body.password, body.full_name)
    return result

@app.post("/auth/login")
async def auth_login(body: AuthLogin):
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
    return FileResponse(os.path.join(_FRONTEND_DIR, "dashboard.html"))


@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    return FileResponse(os.path.join(_FRONTEND_DIR, "dashboard.html"))


@app.get("/swms", response_class=HTMLResponse)
async def serve_swms():
    return FileResponse(os.path.join(_FRONTEND_DIR, "app.html"))


@app.get("/ra", response_class=HTMLResponse)
async def serve_ra():
    # RA spec TBD — serve dashboard for now
    return FileResponse(os.path.join(_FRONTEND_DIR, "dashboard.html"))


@app.get("/terms", response_class=HTMLResponse)
async def serve_terms():
    terms_path = os.path.join(_FRONTEND_DIR, "terms.html")
    if os.path.isfile(terms_path):
        return FileResponse(terms_path)
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


@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(os.path.join(_FRONTEND_DIR, "login.html"))


@app.get("/tasks")
async def list_tasks():
    """Return all approved tasks as JSON."""
    tasks = _get_approved_tasks()
    return JSONResponse(content={"tasks": tasks, "count": len(tasks)})


@app.post("/generate")
async def generate(
    request: Request,
    task_name: str = Form(...),
    site_name: str = Form(""),
    trade_type: str = Form(""),
    principal_contractor: str = Form("General"),
    output_format: str = Form("both"),
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
        return JSONResponse(
            content={"error": str(exc)},
            status_code=500,
        )


@app.get("/health")
async def health():
    return {"status": "ok"}


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
        return JSONResponse(content={"error": str(exc)}, status_code=500)


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
        return JSONResponse(content={"error": str(exc)}, status_code=500)


# ============================================================
# INFERENCE & ROUTING
# ============================================================

@app.get("/infer")
def infer_endpoint(q: str, jurisdiction: str = "AU", document_type: str = "swms"):
    """
    GET /infer?q=<work description>&jurisdiction=AU&document_type=swms
    Returns inferred WHS requirements. No Claude call — pure inference.
    For document_type=ra, includes hazard_list with L/C scores.
    """
    if document_type == "ra":
        from core.inference_matrix import infer_to_dict_ra
        return infer_to_dict_ra(q, jurisdiction=jurisdiction)
    from core.inference_matrix import infer_to_dict
    return infer_to_dict(q, jurisdiction=jurisdiction)


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
async def generate_auto(request: dict, user: dict = Depends(get_current_user)):
    from core.orchestrator import generate_swms
    try:
        description = request.get("description", "")
        project_meta = request.get("project_meta", {})
        jurisdiction = request.get("jurisdiction", "AU")
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
            force_full=request.get("force_full", False),
            force_simple=request.get("force_simple", False),
            jurisdiction=jurisdiction,
        )
        return result
    except Exception as e:
        return {"error": str(e)}


@app.post("/generate/full")
async def generate_full(request: dict, user: dict = Depends(get_current_user)):
    from core.orchestrator import generate_swms
    try:
        result = await generate_swms(
            description=request.get("description", ""),
            project_meta=request.get("project_meta", {}),
            force_full=True,
            jurisdiction=request.get("jurisdiction", "AU"),
        )
        return result
    except Exception as e:
        return {"error": str(e)}

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

    async def event_generator():
        try:
            async for event in generate_swms_stream(
                description=description,
                project_meta=project_meta,
                force_full=force_full,
                force_simple=force_simple,
                jurisdiction=jurisdiction,
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            import json as _json
            yield f"data: {_json.dumps({'type': 'error', 'message': str(e)})}\n\n"

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
        return JSONResponse(content={"error": str(e), "traceback": traceback.format_exc()}, status_code=500)


def _build_filename(project_meta: dict, ext: str) -> str:
    """Build SWMS-<name>-<date>-V01.<ext> filename."""
    from datetime import date
    name = project_meta.get("project_name", "Output")
    # Sanitise for filename
    safe = "".join(c if c.isalnum() or c in " -_" else "" for c in name).strip()
    safe = safe.replace(" ", "-")[:40]
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
        return JSONResponse(content={"error": str(e), "traceback": traceback.format_exc()}, status_code=500)


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
        return JSONResponse(content={"error": str(e), "traceback": traceback.format_exc()}, status_code=500)


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
        return {"error": str(e)}


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
        return JSONResponse(content={"error": str(e)}, status_code=500)


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
        return JSONResponse(content={"error": str(e), "traceback": traceback.format_exc()}, status_code=500)


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
        return JSONResponse(content={"error": str(e), "traceback": traceback.format_exc()}, status_code=500)


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
    return detect_jurisdiction_from_query(q, selected)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)


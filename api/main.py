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
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Gatekeeper SWMS Generator", version="1.0")

_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
templates = Jinja2Templates(directory=_TEMPLATE_DIR)

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
# ROUTES
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    tasks = _get_approved_tasks()
    task_names = [t["task_name"] for t in tasks]
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "task_names": json.dumps(task_names)},
    )


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
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM Tasks WHERE status='approved'").fetchone()[0]
    conn.close()
    return {"status": "ok", "approved_tasks": count}


# ============================================================
# STANDALONE RUNNER
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

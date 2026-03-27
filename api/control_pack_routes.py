"""
api/control_pack_routes.py -- Combined WHS Control Pack prototype endpoints.

Prototype-only routes for generating and rendering project-level
WHS control packs. Separate from standalone RA and SWMS paths.
"""

import logging
import traceback

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response

from core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/control-pack", tags=["control-pack"])


@router.post("/generate")
async def control_pack_generate(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """
    POST /control-pack/generate

    Generate a Combined WHS Control Pack from a project description
    and optional trade packages.

    Request body:
    {
        "description": str (required, min 10 words),
        "project_meta": {
            "project_name": str,
            "site_address": str,
            "pcbu_name": str,
            "client": str,
            ...
        },
        "trade_packages": list[str] | null  (if null, auto-extracted),
        "jurisdiction": str (default "AU"),
        "format": "json" | "docx" (default "docx")
    }

    Returns:
    - format=json: the full control pack data structure
    - format=docx: the rendered .docx as file download
    """
    from core.control_pack import build_control_pack
    from renderers.control_pack_renderer import render_control_pack

    body = await request.json()

    description = (body.get("description") or "").strip()
    if not description or len(description.split()) < 5:
        return JSONResponse(
            content={"detail": "Description is required (at least 5 words)."},
            status_code=422,
        )

    project_meta = body.get("project_meta", {})
    trade_packages = body.get("trade_packages")  # None = auto-extract
    jurisdiction = body.get("jurisdiction", "AU")
    output_format = body.get("format", "docx")

    try:
        pack = build_control_pack(
            description=description,
            project_meta=project_meta,
            trade_packages=trade_packages,
            jurisdiction=jurisdiction,
        )
    except Exception as e:
        logger.error(f"Control pack generation failed:\n{traceback.format_exc()}")
        return JSONResponse(
            content={"detail": f"Generation failed: {type(e).__name__}: {e}"},
            status_code=500,
        )

    if output_format == "json":
        # Return the data structure (strip large inference dict for readability)
        result = {k: v for k, v in pack.items() if k != "inference"}
        result["trade_package_count"] = len(pack.get("swms_matrix", []))
        result["hrcw_yes_count"] = sum(1 for h in pack.get("hrcw_register", []) if h["status"] == "YES")
        result["hrcw_conditional_count"] = sum(1 for h in pack.get("hrcw_register", []) if h["status"] == "CONDITIONAL")
        result["hold_point_count"] = len(pack.get("hold_points", []))
        result["risk_register_count"] = len(pack.get("risk_register", []))
        result["open_item_count"] = len(pack.get("review_meta", {}).get("open_items", []))
        return JSONResponse(content=result)

    # Default: render .docx
    try:
        docx_bytes = render_control_pack(pack)
    except Exception as e:
        logger.error(f"Control pack render failed:\n{traceback.format_exc()}")
        return JSONResponse(
            content={"detail": f"Render failed: {type(e).__name__}: {e}"},
            status_code=500,
        )

    # Build filename
    import re
    from datetime import date
    name = project_meta.get("project_name", "Control-Pack")
    safe = re.sub(r'[\\/:*?"<>|]', "-", name)[:40].replace(" ", "-")
    d = date.today().strftime("%d%m%Y")
    filename = f"WHS-CP-{safe}-{d}-V01.docx"

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

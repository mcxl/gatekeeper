#!/usr/bin/env python3
"""
core/orchestrator.py — Multi-agent SWMS generation orchestrator.

Routes work descriptions to either:
  - Simple path: existing single-agent generate.py (fast, cheap)
  - Full path:   4-agent pipeline (higher quality, HRCW/complex tasks)

Usage:
    import asyncio
    from core.orchestrator import generate_swms

    result = asyncio.run(generate_swms(
        description="swing stage painting of apartment building facade",
        project_meta={"project_name": "...", "site_address": "..."},
    ))
"""

from __future__ import annotations
import asyncio
import functools
import logging
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

log = logging.getLogger(__name__)

# ── Routing thresholds ────────────────────────────────────────────────────────

# Always use full pipeline for HRCW work
HRCW_ALWAYS_FULL: bool = True

# Always use full pipeline when SafeWork notification required
SAFEWORK_ALWAYS_FULL: bool = True

# Sentence count above which full pipeline is used
SENTENCE_THRESHOLD: int = 4

# ── Agent imports (deferred to avoid import errors if agents/ not yet created) ─

def _import_agents():
    from agents.decomposer import run_decomposer
    from agents.risk_assessor import run_risk_assessor
    from agents.control_writer import run_control_writer, write_controls_single
    from agents.assembler import run_assembler, run_assembler_single
    return run_decomposer, run_risk_assessor, run_control_writer, write_controls_single, run_assembler, run_assembler_single


# ── Routing ───────────────────────────────────────────────────────────────────

def route(description: str, inference: dict) -> str:
    """
    Determine pipeline route.

    Returns:
        'simple' — single-agent fast path (existing generate.py)
        'full'   — 4-agent pipeline
    """
    if HRCW_ALWAYS_FULL and inference.get("hrcw"):
        log.info("Route: full — HRCW work identified")
        return "full"

    if SAFEWORK_ALWAYS_FULL and inference.get("safework_notification_required"):
        log.info("Route: full — SafeWork notification required")
        return "full"

    # Estimate task count from sentence/clause structure
    import re
    clauses = re.split(r"[.;,\n]", description)
    clauses = [c.strip() for c in clauses if len(c.strip()) > 10]
    if len(clauses) > SENTENCE_THRESHOLD:
        log.info(f"Route: full — {len(clauses)} clauses detected (threshold: {SENTENCE_THRESHOLD})")
        return "full"

    log.info("Route: simple — low complexity, no HRCW")
    return "simple"


# ── Simple path ───────────────────────────────────────────────────────────────

async def _run_simple_path(
    description: str,
    project_meta: dict,
    inference: dict,
    scope_context: dict = None,
) -> list[dict]:
    """
    Existing single-agent generation. Falls back gracefully if generate.py
    is not async — wraps in executor if needed.
    """
    from core.generate import generate_task
    import asyncio
    loop = asyncio.get_event_loop()
    fn = functools.partial(generate_task, description, scope_context=scope_context)
    task = await loop.run_in_executor(None, fn)
    result = task.model_dump() if hasattr(task, 'model_dump') else task
    return [result] if isinstance(result, dict) else result


# ── Full 4-agent pipeline ─────────────────────────────────────────────────────

async def _run_full_pipeline(
    description: str,
    project_meta: dict,
    inference: dict,
    scope_context: dict = None,
) -> tuple[list[dict], dict]:
    """
    Run all four agents in sequence.
    Returns (task_blocks, agent_outputs_debug).
    """
    (run_decomposer, run_risk_assessor,
     run_control_writer, write_controls_single,
     run_assembler, run_assembler_single) = _import_agents()

    agent_outputs: dict = {}
    errors: list[str] = []

    # ── Agent 1: Decompose ────────────────────────────────────────────────────
    log.info("Agent 1 — Decomposer starting")
    try:
        task_manifest = await run_decomposer(description, inference, scope_context=scope_context)
        agent_outputs["task_manifest"] = task_manifest
        log.info(f"Agent 1 — {task_manifest['total_tasks']} tasks decomposed")
    except Exception as e:
        log.error(f"Agent 1 failed: {e}")
        raise RuntimeError(f"Decomposer failed: {e}") from e

    # ── Agent 2: Risk assess ──────────────────────────────────────────────────
    log.info("Agent 2 — Risk Assessor starting")
    try:
        risk_manifest = await run_risk_assessor(task_manifest, inference)
        agent_outputs["risk_manifest"] = risk_manifest
        log.info(f"Agent 2 — {len(risk_manifest['risks'])} tasks risk-assessed")
    except Exception as e:
        log.error(f"Agent 2 failed: {e}")
        raise RuntimeError(f"Risk Assessor failed: {e}") from e

    # ── Per-task concurrent: Agent 3 (controls) → Agent 4 (assemble) ──────────
    tasks = task_manifest.get("tasks", [])
    risks_by_seq = {r["sequence"]: r for r in risk_manifest.get("risks", [])}

    async def _process_task(idx: int, task: dict) -> dict:
        seq = task["sequence"]
        risk = risks_by_seq.get(seq, {})
        log.info(f"Agent 3+4 — task {idx+1}/{len(tasks)}: {task['task'][:40]}")

        # Agent 3: write controls
        try:
            ctrl = await write_controls_single(task, risk, inference, scope_context=scope_context)
        except Exception as e:
            log.error(f"Agent 3 failed for task {idx+1} ({task['task'][:40]}): {e}")
            ctrl = {}

        # Agent 4: assemble
        single_manifest = {**task_manifest, "tasks": [task], "total_tasks": 1}
        single_risk = {**risk_manifest, "risks": [risk] if risk else []}
        single_ctrl = {"controls": [ctrl]}
        try:
            result = await run_assembler(
                single_manifest, single_risk, single_ctrl, inference, project_meta
            )
            tb = result[0] if result else {}
        except Exception as e:
            log.error(f"Agent 4 failed for task {idx+1} ({task['task'][:40]}): {e}")
            return {}

        # Validate + retry
        val_result = _validate_task_block(tb)
        if not val_result["valid"]:
            log.warning(f"Task {tb.get('task', '?')} failed validation: {val_result['errors']} — retrying")
            try:
                tb = await run_assembler_single(tb, val_result["errors"], inference)
                errors.extend(val_result["errors"])
            except Exception as e:
                log.error(f"Retry assembler failed for task {idx+1}: {e}")

        log.info(f"Task {idx+1}/{len(tasks)} complete")
        return tb

    task_blocks = list(await asyncio.gather(
        *[_process_task(idx, task) for idx, task in enumerate(tasks)]
    ))

    agent_outputs["task_blocks_raw"] = task_blocks
    if errors:
        agent_outputs["validation_errors"] = errors

    return task_blocks, agent_outputs


# ── Public interface ──────────────────────────────────────────────────────────

async def generate_swms(
    description: str,
    project_meta: Optional[dict] = None,
    force_full: bool = False,
    force_simple: bool = False,
    jurisdiction: str = "AU",
    scope_context: Optional[dict] = None,
) -> dict:
    """
    Main entry point for SWMS generation.

    Args:
        description:   Plain-text work description
        project_meta:  Dict with project_name, site_address, principal_contractor, version
        force_full:    Override routing — always use full pipeline
        force_simple:  Override routing — always use simple pipeline

    Returns:
        {
            "route": "simple" | "full",
            "tasks": list[TaskBlock dict],
            "inference": dict,
            "agent_outputs": dict,   # debug — intermediate manifests
            "task_count": int,
        }
    """
    from core.inference_matrix import infer_to_dict

    project_meta = project_meta or {}

    # Step 1: inference pre-fill
    log.info("Running inference matrix pre-fill")
    inference = infer_to_dict(description, jurisdiction=jurisdiction)

    # Build jurisdiction context for agent prompts
    if jurisdiction != "AU":
        from core.jurisdictions import get_jurisdiction
        jur = get_jurisdiction(jurisdiction)
        jur_context = (
            f"\n\nJURISDICTION: {jur['name']} ({jurisdiction}). "
            f"Regulatory body: {jur['regulator']}. "
            f"Primary legislation: {jur['legislation']['primary_act']}. "
            f"Use {jurisdiction} terminology, standards, and regulatory references throughout. "
            f"Do not reference Australian legislation unless comparing."
        )
        description = description + jur_context

    # Inject verified standards reference into description for agent prompts
    from vocab.standards_registry import (
        get_verified_standards,
        validate_standard_citations,
        strip_unverified_citations,
    )
    verified_refs = get_verified_standards(
        jurisdiction=jurisdiction,
        ccvs_codes=inference.get("ccvs_codes", []),
    )
    if verified_refs:
        standards_block = "\n".join(f"  — {s}" for s in verified_refs)
        description += (
            "\n\nVERIFIED STANDARDS FOR THIS JOB:\n"
            "The following standards and codes are verified as current and applicable. "
            "Reference ONLY these standards by name. Do not cite any standard number "
            "that is not in this list:\n\n"
            f"{standards_block}\n\n"
            "If you need to reference a standard not in this list, describe the "
            "requirement in plain English without citing a standard number."
        )

    # Step 2: routing
    if force_full:
        selected_route = "full"
    elif force_simple:
        selected_route = "simple"
    else:
        selected_route = route(description, inference)

    log.info(f"Route selected: {selected_route}")

    # Step 3: run pipeline
    agent_outputs: dict = {}

    if selected_route == "simple":
        task_blocks = await _run_simple_path(description, project_meta, inference, scope_context=scope_context)
    else:
        task_blocks, agent_outputs = await _run_full_pipeline(
            description, project_meta, inference, scope_context=scope_context
        )

    # Post-generation normalisation (plain English, CCVS repair, risk labels, citation strip)
    hot_work_ok = _hot_work_legitimate(inference)
    task_blocks = [_normalise_task(tb, inference, jurisdiction, hot_work_ok) for tb in task_blocks]
    _suppress_false_ccvs(task_blocks, inference)

    # Log any flagged citations for monitoring
    ccvs_codes = inference.get("ccvs_codes", [])
    validation = validate_standard_citations(
        str(task_blocks), jurisdiction, ccvs_codes
    )
    if validation["flag_count"] > 0:
        log.warning(
            f"WARNING: {validation['flag_count']} unverified citations stripped: "
            f"{validation['flagged']}"
        )

    return {
        "route": selected_route,
        "tasks": task_blocks,
        "inference": inference,
        "agent_outputs": agent_outputs,
        "task_count": len(task_blocks),
    }




async def generate_swms_stream(
    description: str,
    project_meta: dict | None = None,
    force_full: bool = False,
    force_simple: bool = False,
    jurisdiction: str = "AU",
    scope_context: dict | None = None,
):
    """
    Async generator version of generate_swms().
    Yields dicts as each stage completes so the caller can stream to client.

    Yield types:
        {"type": "route",      "route": str, "inference": dict}
        {"type": "task_count", "count": int}
        {"type": "task",       "index": int, "total": int, "task": dict}
        {"type": "done",       "task_count": int}
        {"type": "error",      "message": str}
    """
    from core.inference_matrix import infer_to_dict

    project_meta = project_meta or {}

    # Step 1: inference
    inference = infer_to_dict(description, jurisdiction=jurisdiction)

    # Build jurisdiction context for agent prompts
    if jurisdiction != "AU":
        from core.jurisdictions import get_jurisdiction
        jur = get_jurisdiction(jurisdiction)
        jur_context = (
            f"\n\nJURISDICTION: {jur['name']} ({jurisdiction}). "
            f"Regulatory body: {jur['regulator']}. "
            f"Primary legislation: {jur['legislation']['primary_act']}. "
            f"Use {jurisdiction} terminology, standards, and regulatory references throughout. "
            f"Do not reference Australian legislation unless comparing."
        )
        description = description + jur_context

    # Step 2: routing
    if force_full:
        selected_route = "full"
    elif force_simple:
        selected_route = "simple"
    else:
        selected_route = route(description, inference)

    yield {"type": "route", "route": selected_route, "inference": inference}

    # Step 3: simple path — single task, yield immediately
    if selected_route == "simple":
        task_blocks = await _run_simple_path(description, project_meta, inference, scope_context=scope_context)
        yield {"type": "task_count", "count": len(task_blocks)}
        for i, tb in enumerate(task_blocks):
            yield {"type": "task", "index": i, "total": len(task_blocks), "task": tb}
        yield {"type": "done", "task_count": len(task_blocks)}
        return

    # Step 4: full pipeline — agents 1+2 on full manifest, then per-task 3→4
    (run_decomposer, run_risk_assessor,
     _run_control_writer_batch, write_controls_single,
     run_assembler, run_assembler_single) = _import_agents()

    try:
        task_manifest = await run_decomposer(description, inference, scope_context=scope_context)
    except Exception as e:
        yield {"type": "error", "message": f"Decomposer failed: {e}"}
        return

    try:
        risk_manifest = await run_risk_assessor(task_manifest, inference)
    except Exception as e:
        yield {"type": "error", "message": f"Risk Assessor failed: {e}"}
        return

    # Per-task loop: agent 3 (controls) → agent 4 (assemble) → yield
    tasks = task_manifest.get("tasks", [])
    risks_by_seq = {r["sequence"]: r for r in risk_manifest.get("risks", [])}
    total = len(tasks)

    yield {"type": "task_count", "count": total}

    hot_work_ok = _hot_work_legitimate(inference)
    assembled = []
    for idx, task in enumerate(tasks):
        seq = task["sequence"]
        risk = risks_by_seq.get(seq, {})

        try:
            # Agent 3: controls for this task
            ctrl = await write_controls_single(task, risk, inference, scope_context=scope_context)

            # Agent 4: assemble this task
            single_manifest = {**task_manifest, "tasks": [task], "total_tasks": 1}
            single_risk = {**risk_manifest, "risks": [risk] if risk else []}
            single_ctrl = {"controls": [ctrl]}
            result = await run_assembler(
                single_manifest, single_risk, single_ctrl, inference, project_meta
            )
            tb = result[0] if result else {}

            # Validate + retry
            val = _validate_task_block(tb)
            if not val["valid"]:
                try:
                    tb = await run_assembler_single(tb, val["errors"], inference)
                except Exception:
                    pass

            tb = _normalise_task(tb, inference, jurisdiction, hot_work_ok)
            assembled.append(tb)
            yield {"type": "task", "index": idx, "total": total, "task": tb}
            await asyncio.sleep(0)

        except Exception as e:
            yield {"type": "error", "message": f"Task {idx+1} failed: {e}"}
            assembled.append({})

    yield {"type": "done", "task_count": len(assembled), "route": selected_route}


# ── Risk label enrichment ─────────────────────────────────────────────────────

_RISK_LABELS = {"H": "High", "M": "Medium", "L": "Low"}


def _enrich_risk_labels(tb: dict) -> None:
    """Convert risk_pre/risk_post from 'H'/'M'/'L' to 'High(9)'/'Medium(4)'/'Low(2)'.

    Uses risk_pre_score/risk_post_score dicts {likelihood, consequence} if available.
    Falls back to defaults based on letter grade.
    """
    _DEFAULTS = {"H": 9, "M": 4, "L": 2}

    for field, score_field in [("risk_pre", "risk_pre_score"),
                                ("risk_post", "risk_post_score")]:
        rating = tb.get(field, "")
        # Skip if already enriched (e.g. "High(6)")
        if "(" in str(rating):
            continue
        letter = rating.strip().upper()[:1] if rating else ""
        label = _RISK_LABELS.get(letter, rating)
        # Compute numeric score from likelihood × consequence
        score_data = tb.get(score_field, {})
        if isinstance(score_data, dict) and score_data:
            score = score_data.get("likelihood", 1) * score_data.get("consequence", 1)
        else:
            score = _DEFAULTS.get(letter, 0)
        if score:
            tb[field] = f"{label}({score})"
        elif label:
            tb[field] = label


# ── Plain English enforcement ─────────────────────────────────────────────────

def _enforce_plain_english(tb: dict) -> dict:
    """Auto-replace formal phrases with plain English in all control text fields."""
    from vocab.swms_vocabulary import enforce_vocabulary
    for field in ("controls", "admin", "stop_work", "hold_points", "ppe", "hazards"):
        if field in tb and isinstance(tb[field], list):
            tb[field] = [enforce_vocabulary(item) for item in tb[field]]
    # Glove selection: chemical-resistant vs cut-resistant based on task context
    _enforce_glove_selection(tb)
    # SIL scoring: downgrade SIL-H6/H9 to SIL-M4 for passive dust tasks
    _enforce_sil_scoring(tb)
    return tb


import re as _re

_CHEMICAL_KEYWORDS = _re.compile(
    r"\b(epoxy|resin|hardener|solvent|chemical|acid|alkali|caustic|adhesive|"
    r"primer|paint|coating|membrane|sealant|grout|mortar|waterproof|hazardous\s+substance)\b",
    _re.I,
)

_CHEMICAL_GLOVE = "chemical-resistant gloves (nitrile or task-appropriate)"
_CUT_GLOVE = "cut-resistant gloves"


_GLOVE_PATTERN = _re.compile(
    r"\b(cut-resistant gloves|chemical-resistant gloves|nitrile gloves|"
    r"work gloves|safety gloves|protective gloves|leather gloves|"
    r"disposable gloves|rubber gloves|latex gloves|butyl gloves|"
    r"laminate gloves|gloves)\b", _re.I,
)


def _enforce_glove_selection(tb: dict) -> None:
    """Set glove type based on whether the task involves chemicals."""
    task_text = (tb.get("task", "") + " " + tb.get("scope", "")).lower()
    has_chemicals = bool(_CHEMICAL_KEYWORDS.search(task_text))
    target_glove = _CHEMICAL_GLOVE if has_chemicals else _CUT_GLOVE

    ppe = tb.get("ppe", [])
    if not isinstance(ppe, list):
        return

    # Replace any glove item with the correct type for this task
    found_glove = False
    new_ppe = []
    for item in ppe:
        if _GLOVE_PATTERN.search(item):
            if not found_glove:
                new_ppe.append(target_glove)
                found_glove = True
            # skip duplicate glove entries
        else:
            new_ppe.append(item)
    tb["ppe"] = new_ppe


_ACTIVE_DUST_PATTERNS = [
    _re.compile(r"\b(grind|grinding|cut|cutting|drill|drilling|saw|sawing|jackhammer|demolish|break|chip|chase|core)\w*\b", _re.I),
]

_PASSIVE_DUST_KEYWORDS = [
    "clean", "vacuum", "sweep", "wipe", "mop", "wash", "damp", "housekeep",
]


_HOT_WORK_CONFIRM_PATTERNS = [
    _re.compile(r"\bweld", _re.I),
    _re.compile(r"\boxy\b", _re.I),
    _re.compile(r"\bacetylene\b", _re.I),
    _re.compile(r"\btorch\b", _re.I),
    _re.compile(r"\bflame\s*cut", _re.I),
    _re.compile(r"\barc\s*weld", _re.I),
    _re.compile(r"\bhot\s*work", _re.I),
    _re.compile(r"\bbrazing\b", _re.I),
    _re.compile(r"\bsoldering\b", _re.I),
]


def _hot_work_legitimate(inference: dict) -> bool:
    """Return True if inference indicates real hot work is present in the job."""
    all_inf = str(inference).lower()
    return "hot work" in all_inf or "welding" in all_inf


def _suppress_false_ccvs_single(tb: dict, hot_work_legitimate: bool) -> None:
    """Suppress a HOT CCVS code on a single task block if hot work is not real."""
    if hot_work_legitimate:
        return
    ccvs = tb.get("ccvs_code", "N/A")
    if not ccvs.startswith("HOT"):
        return
    task_text = (tb.get("task", "") + " " + tb.get("scope", "")).lower()
    real_hot = any(p.search(task_text) for p in _HOT_WORK_CONFIRM_PATTERNS)
    if not real_hot:
        tb["ccvs_code"] = "N/A"
        for field in ("controls", "admin", "hold_points", "stop_work"):
            if field in tb and isinstance(tb[field], list):
                tb[field] = [item for item in tb[field]
                             if "hot work" not in item.lower()]


def _suppress_false_ccvs(task_blocks: list[dict], inference: dict) -> None:
    """Suppress HOT CCVS codes when inference says no hot work is present."""
    hot_work_ok = _hot_work_legitimate(inference)
    for tb in task_blocks:
        _suppress_false_ccvs_single(tb, hot_work_ok)


def _normalise_task(tb: dict, inference: dict, jurisdiction: str, hot_work_ok: bool) -> dict:
    """Apply all per-task post-processing in a single call."""
    from renderers.docx_renderer import validate_ccvs_code
    from vocab.standards_registry import strip_unverified_citations
    ccvs_codes = inference.get("ccvs_codes", [])
    tb = _enforce_plain_english(tb)
    if "ccvs_code" in tb:
        tb["ccvs_code"] = validate_ccvs_code(tb["ccvs_code"])
    _enrich_risk_labels(tb)
    _suppress_false_ccvs_single(tb, hot_work_ok)
    for field in ("controls", "admin", "stop_work", "hold_points"):
        if field in tb and isinstance(tb[field], list):
            tb[field] = [
                strip_unverified_citations(ctrl, jurisdiction, ccvs_codes)
                for ctrl in tb[field]
            ]
    return tb


def _enforce_sil_scoring(tb: dict) -> None:
    """Downgrade SIL-H6/H9 to SIL-M4 for passive/cleaning tasks (no active dust generation)."""
    ccvs = tb.get("ccvs_code", "N/A")
    if ccvs not in ("SIL-H6", "SIL-H9"):
        return
    # Check task name only (scope may mention upstream activities like grinding)
    task_name = tb.get("task", "").lower()
    # If task involves active dust generation, keep the high code
    for pat in _ACTIVE_DUST_PATTERNS:
        if pat.search(task_name):
            return
    # No active dust generation — downgrade to SIL-M4
    tb["ccvs_code"] = "SIL-M4"


# ── Validation helper ─────────────────────────────────────────────────────────

def _validate_task_block(tb: dict) -> dict:
    """
    Lightweight TaskBlock validation.
    Returns {"valid": bool, "errors": list[str]}.
    Mirrors core/validate.py checks without the full dataclass conversion.
    """
    errors: list[str] = []

    # Required fields
    for field in ["task", "scope", "risk_pre", "risk_post", "controls", "ppe", "ccvs_code"]:
        if field not in tb or not tb[field]:
            errors.append(f"Missing or empty field: '{field}'")

    # Risk ratings
    valid_ratings = {"L", "M", "H"}
    if tb.get("risk_pre") not in valid_ratings:
        errors.append(f"Invalid risk_pre: '{tb.get('risk_pre')}'")
    if tb.get("risk_post") not in valid_ratings:
        errors.append(f"Invalid risk_post: '{tb.get('risk_post')}'")
    if tb.get("risk_post") == "H":
        errors.append("risk_post cannot be H — residual risk must be L or M")

    # Controls
    controls = tb.get("controls", [])
    if len(controls) < 3:
        errors.append(f"Only {len(controls)} controls — minimum 3 required")
    total_chars = sum(len(c) for c in controls)
    if total_chars > 1800:
        errors.append(f"Controls total {total_chars} chars — maximum 1800")

    # CCVS / WAH consistency
    ccvs = tb.get("ccvs_code", "N/A")
    wah = tb.get("wah_applicable", False)
    if ccvs.startswith("WAH") and not wah:
        errors.append(f"ccvs_code is {ccvs} but wah_applicable is False")
    if not ccvs.startswith("WAH") and wah:
        errors.append(f"wah_applicable is True but ccvs_code is {ccvs}")

    # H risk must have CCVS code
    if tb.get("risk_pre") == "H" and ccvs == "N/A":
        errors.append("High pre-risk task must have a CCVS code — N/A not permitted")

    return {"valid": len(errors) == 0, "errors": errors}


# ── CLI entrypoint ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json  # noqa: F401
    import sys
    import logging

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    desc = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else (
        "Erect swing stage and apply elastomeric paint to apartment building facade. "
        "Building is occupied. 12 storeys."
    )

    meta = {
        "project_name": "CLI Test",
        "site_address": "Test Site",
        "principal_contractor": "RPD",
        "version": "1.0",
    }

    print(f"\nDescription: {desc}\n")
    result = asyncio.run(generate_swms(desc, meta))

    print(f"Route: {result['route']}")
    print(f"Tasks: {result['task_count']}")
    print(f"HRCW: {result['inference']['hrcw']}")
    print()

    for i, tb in enumerate(result["tasks"], 1):
        print(f"Task {i}: {tb.get('task', '?')}")
        print(f"  Risk: {tb.get('risk_pre')} → {tb.get('risk_post')}")
        print(f"  CCVS: {tb.get('ccvs_code')}")
        print(f"  Controls: {len(tb.get('controls', []))}")
        print()

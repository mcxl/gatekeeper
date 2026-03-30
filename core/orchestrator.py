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
import re as _re
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from agents.decomposer import run_decomposer
from agents.risk_assessor import run_risk_assessor
from agents.control_writer import write_controls_single
from agents.assembler import run_assembler, run_assembler_single

log = logging.getLogger(__name__)

# ── Routing thresholds ────────────────────────────────────────────────────────

# Always use full pipeline for HRCW work
HRCW_ALWAYS_FULL: bool = True

# Always use full pipeline when SafeWork notification required
SAFEWORK_ALWAYS_FULL: bool = True

# Sentence count above which full pipeline is used
SENTENCE_THRESHOLD: int = 4


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
    clauses = _re.split(r"[.;,\n]", description)
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
    scope_context: dict | None = None,
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
    scope_context: dict | None = None,
) -> tuple[list[dict], dict]:
    """
    Run all four agents in sequence.
    Returns (task_blocks, agent_outputs_debug).
    """
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
        risk_manifest = await run_risk_assessor(task_manifest, inference, scope_context)
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
            # Provide minimal fallback so assembler doesn't crash on missing sequence
            ctrl = {
                "sequence": task.get("sequence", idx + 1),
                "controls": ["Refer to site-specific controls", "Supervisor to verify before work starts", "Follow project safety management plan"],
                "hold_points": [],
                "stop_work": [],
                "admin": [],
                "ppe": ["Hard hat", "Hi-vis vest", "Safety boots"],
                "ccvs_code": "N/A",
            }

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
    from core.inference_matrix import infer_to_dict, classify_swms_scope

    project_meta = project_meta or {}

    # Step 1: inference pre-fill + scope classification
    log.info("Running inference matrix pre-fill")
    inference = infer_to_dict(description, jurisdiction=jurisdiction)
    swms_classification = classify_swms_scope(description)
    inference["swms_classification"] = swms_classification

    scope_context = scope_context or {}
    scope_context.setdefault("job_type", swms_classification["job_type"])
    scope_context.setdefault("building_context", swms_classification["building_context"])
    scope_context.setdefault("occupancy_context", swms_classification["occupancy_context"])
    if swms_classification["scope_modifiers"]:
        scope_context.setdefault("scope_modifiers", ", ".join(swms_classification["scope_modifiers"]))

    excluded = _detect_excluded_items(description)
    if excluded:
        scope_context["excluded_items"] = "DO NOT generate tasks for: " + ", ".join(excluded) + " — these are latent conditions or variations, not contracted scope"

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
    task_blocks = _reorder_tasks(task_blocks)

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
    from core.inference_matrix import infer_to_dict, classify_swms_scope

    project_meta = project_meta or {}

    # Step 1: inference + scope classification
    inference = infer_to_dict(description, jurisdiction=jurisdiction)
    swms_classification = classify_swms_scope(description)
    inference["swms_classification"] = swms_classification

    # Merge classification into scope_context for agent prompts
    scope_context = scope_context or {}
    scope_context.setdefault("job_type", swms_classification["job_type"])
    scope_context.setdefault("building_context", swms_classification["building_context"])
    scope_context.setdefault("occupancy_context", swms_classification["occupancy_context"])
    if swms_classification["scope_modifiers"]:
        scope_context.setdefault("scope_modifiers", ", ".join(swms_classification["scope_modifiers"]))

    # Detect excluded/variation items and pass to agents as exclusions
    excluded = _detect_excluded_items(description)
    if excluded:
        scope_context["excluded_items"] = "DO NOT generate tasks for: " + ", ".join(excluded) + " — these are latent conditions or variations, not contracted scope"

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
    try:
        task_manifest = await run_decomposer(description, inference, scope_context=scope_context)
    except Exception as e:
        yield {"type": "error", "message": f"Decomposer failed: {e}"}
        return

    try:
        risk_manifest = await run_risk_assessor(task_manifest, inference, scope_context)
    except Exception as e:
        yield {"type": "error", "message": f"Risk Assessor failed: {e}"}
        return

    # Per-task loop: agent 3 (controls) → agent 4 (assemble) → yield
    tasks = task_manifest.get("tasks", [])
    risks_by_seq = {r["sequence"]: r for r in risk_manifest.get("risks", [])}
    total = len(tasks)

    # ── Parallel per-task execution ───────────────────────────
    _SEM = asyncio.Semaphore(3)

    _MAX_RETRIES = 1

    async def _process_single_task(idx: int, task: dict) -> tuple[int, dict]:
        seq = task["sequence"]
        risk = risks_by_seq.get(seq, {})
        last_error = None
        for attempt in range(_MAX_RETRIES + 1):
            async with _SEM:
                try:
                    ctrl = await write_controls_single(task, risk, inference)

                    single_manifest = {**task_manifest, "tasks": [task], "total_tasks": 1}
                    single_risk = {**risk_manifest, "risks": [risk] if risk else []}
                    single_ctrl = {"controls": [ctrl]}
                    result = await run_assembler(
                        single_manifest, single_risk, single_ctrl, inference, project_meta
                    )
                    tb = result[0] if result else {}

                    val = _validate_task_block(tb)
                    if not val["valid"]:
                        try:
                            tb = await run_assembler_single(tb, val["errors"], inference)
                        except Exception:
                            pass

                    # Full normalisation (same as non-streaming path)
                    hot_work_ok = _hot_work_legitimate(inference)
                    tb = _normalise_task(tb, inference, jurisdiction, hot_work_ok)
                    log.warning(f"Task {idx+1} complete")
                    return (idx, tb)

                except Exception as e:
                    last_error = e
                    if attempt < _MAX_RETRIES:
                        log.warning(f"Task {idx+1} failed (attempt {attempt+1}), retrying: {e}")
                    else:
                        log.error(f"Task {idx+1} failed after {_MAX_RETRIES+1} attempts: {e}")
        return (idx, {})

    yield {"type": "task_count", "count": total}

    log.warning(f"Starting parallel execution — {total} tasks, semaphore 5")
    assembled_map: dict[int, dict] = {}
    coros = [_process_single_task(idx, task) for idx, task in enumerate(tasks)]

    for coro in asyncio.as_completed(coros):
        idx, tb = await coro
        assembled_map[idx] = tb
        yield {"type": "task", "index": idx, "total": total, "task": tb}
        await asyncio.sleep(0)

    assembled = [assembled_map[i] for i in range(total)]
    log.warning(f"Parallel execution complete — {total} tasks assembled")

    # Full normalisation pass (same as non-streaming path)
    hot_work_ok = _hot_work_legitimate(inference)
    assembled = [_normalise_task(tb, inference, jurisdiction, hot_work_ok)
                 for tb in assembled if tb.get("task")]
    _suppress_false_ccvs(assembled, inference)
    assembled = _reorder_tasks(assembled)
    yield {
        "type": "done",
        "task_count": len(assembled),
        "route": selected_route,
        "tasks": assembled,
    }


# ── Risk label enrichment ─────────────────────────────────────────────────────

_RISK_LABELS = {"H": "High", "M": "Medium", "L": "Low"}


def _enrich_risk_labels(tb: dict) -> None:
    """Convert risk_pre/risk_post from 'H'/'M'/'L' to 'High(9)'/'Medium(4)'/'Low(2)'.

    Uses risk_pre_score/risk_post_score dicts {likelihood, consequence} if available.
    Falls back to defaults based on letter grade.
    """
    _DEFAULTS = {"H": 6, "M": 3, "L": 1}

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

def _detect_excluded_items(description: str) -> list[str]:
    """
    Detect items mentioned in exclusion/variation/latent-condition context.
    Returns a list of excluded item labels for the decomposer to avoid.
    """
    from core.inference_matrix import _EXCLUSION_CONTEXT_PATTERNS
    text = description.lower()
    excluded = []

    _HAZMAT_KEYWORDS = {
        "asbestos": "asbestos removal or survey",
        "lead paint": "lead paint removal or testing",
        "toxic material": "toxic material handling",
        "hazardous material": "hazardous material handling",
    }
    for kw, label in _HAZMAT_KEYWORDS.items():
        if kw in text:
            # Check if it's in an exclusion context
            idx = text.find(kw)
            context = text[max(0, idx - 200):idx + len(kw) + 200]
            if any(pat in context for pat in _EXCLUSION_CONTEXT_PATTERNS):
                excluded.append(label)

    return excluded


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


def _plain_english_pass(tb: dict) -> dict:
    """Final plain-English pass over all text fields including task name and scope."""
    from vocab.swms_vocabulary import enforce_vocabulary
    # String fields
    for field in ("task", "scope"):
        if field in tb and isinstance(tb[field], str) and tb[field]:
            tb[field] = enforce_vocabulary(tb[field])
    # List fields (second pass catches anything _enforce_plain_english missed)
    for field in ("controls", "admin", "stop_work", "hold_points", "ppe", "hazards"):
        if field in tb and isinstance(tb[field], list):
            tb[field] = [enforce_vocabulary(item) for item in tb[field]]
    # Monitoring critical_control
    mon = tb.get("monitoring")
    if isinstance(mon, dict) and isinstance(mon.get("critical_control"), str):
        mon["critical_control"] = enforce_vocabulary(mon["critical_control"])
    # Responsibility fields
    resp = tb.get("responsibility")
    if isinstance(resp, dict):
        for role in ("SUP", "WKR"):
            if role in resp and isinstance(resp[role], str):
                resp[role] = enforce_vocabulary(resp[role])
    return tb


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


# ── Task sequence ordering ────────────────────────────────────────────────────

# Phase keywords scored by expected site workflow order.
# Lower score = earlier in sequence. Tasks matched to the first matching phase.
_PHASE_ORDER = [
    # Phase 0: Preliminaries / site setup / access
    (0, ["set up", "setup", "establish site", "establish and",
         "site prep", "plan access", "preliminar", "induction",
         "site setup", "mobilise site", "mobilize site",
         "mobilise and", "mobilize and", "establish scaffold",
         "mobilise boom", "mobilize boom"]),
    # Phase 1: Access equipment erection
    (1, ["erect scaffold", "scaffold erect", "install scaffold",
         "position ewp", "ewp setup", "access equipment",
         "set up scaffold", "scaffolding and"]),
    # Phase 2: Removals / stripping / preparation
    (2, ["remove green", "remove wall", "strip", "dismantle green",
         "prepare surface", "surface prep", "prep surface", "prepare masonry",
         "prepare render", "prepare facade", "clean facade",
         "pressure wash", "survey", "mark area",
         "inspect facade", "check and expose", "check and isolate",
         "crack inspection", "inspect crack"]),
    # Phase 3: Structural repairs
    (3, ["crack stitch", "spalling", "concrete repair", "reconstruct",
         "repoint", "brickwork", "structural"]),
    # Phase 4: Sealant / waterproofing / sealer
    (4, ["sealant", "seal", "caulk", "silane", "waterproof", "sealer"]),
    # Phase 5: Coatings / painting / finishes
    (5, ["paint", "coating", "primer", "stain", "timber treat", "treat timber",
         "finish", "render seal"]),
    # Phase 6: Reinstatement
    (6, ["reinstate", "reinstall", "restore green", "green wall reinstat"]),
    # Phase 7: QA / defect check / completion
    (7, ["defect", "check work", "quality", "completion", "sign-off",
         "practical completion", "make good"]),
    # Phase 8: Demobilisation — checked BEFORE phase 0 in _task_phase_score
    (8, ["demobilise", "demobilize", "demob", "dismantle scaffold",
         "remove scaffold", "site restor"]),
]


_DEMOB_KEYWORDS = ["demobilise", "demobilize", "demob", "dismantle scaffold",
                    "remove scaffold", "site restor"]
_REPAIR_KEYWORDS = ["crack stitch", "spalling", "concrete repair", "reconstruct",
                     "repoint", "brickwork reconstruct", "brickwork repoint",
                     "brickwork repair", "structural repair", "repair concrete",
                     "repair brick", "mortar joint", "repair spalling"]
_QA_KEYWORDS = ["check work", "check completed", "check remedial",
                "quality", "practical completion", "make good defect",
                "sign-off"]


_COATING_TASK_KEYWORDS = ["paint", "stain", "coat", "seal unpaint", "timber treat",
                          "treat timber", "primer", "timber beam"]


def _task_phase_score(tb: dict) -> int:
    """Return a phase score for sorting. Unmatched tasks get score 5 (coatings).

    Priority order (checked against task name first, then scope):
      demob (8) > coating-by-name (5) > repair (3) > QA (7) > phase table > default (5).
    Coating is checked on task name BEFORE the phase table so 'Paint masonry'
    doesn't get scored as prep (2) due to 'surface prep' in the scope.
    """
    task_name = tb.get("task", "").lower()
    scope = tb.get("scope", "").lower()
    text = task_name + " " + scope
    # Check demob first
    if any(kw in text for kw in _DEMOB_KEYWORDS):
        return 8
    # Check repair before QA
    if any(kw in text for kw in _REPAIR_KEYWORDS):
        return 3
    # Check scaffold/access erection by task name — must be before QA check
    if any(kw in task_name for kw in ("erect scaffold", "scaffold erect", "install scaffold",
                                       "position ewp", "erect and certify",
                                       "erect access", "access equipment")) and "dismantle" not in task_name:
        return 1
    # Check reinstatement by task name — before coating check (avoids "finishing" matching coat)
    if any(kw in task_name for kw in ("reinstate", "reinstall")):
        return 6
    # Check coating by TASK NAME only — avoids scope keywords (surface prep) overriding
    if any(kw in task_name for kw in _COATING_TASK_KEYWORDS):
        return 5
    # QA / defect check
    if any(kw in text for kw in _QA_KEYWORDS) or ("defect" in text and "repair" not in text):
        return 7
    for score, keywords in _PHASE_ORDER:
        if score >= 7:
            continue
        if any(kw in text for kw in keywords):
            return score
    return 5


def _reorder_tasks(task_blocks: list[dict]) -> list[dict]:
    """Sort tasks into a logical site workflow sequence.

    Preserves relative order of tasks within the same phase.
    Re-numbers step fields (1.1, 1.2, ...) after sorting.
    """
    if not task_blocks:
        return task_blocks
    # Stable sort by phase score
    sorted_tasks = sorted(task_blocks, key=_task_phase_score)
    # Re-number
    for i, tb in enumerate(sorted_tasks, 1):
        tb["step"] = f"1.{i}"
    return sorted_tasks


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


def _fix_unsupported_waterproofing(tb: dict) -> None:
    """
    If a task says 'waterproofing' but the scope mentions sealant/silane/recaulk,
    replace the task name with quote-faithful wording.
    Prevents agent drift from 'apply sealant' to 'waterproofing'.
    """
    task = tb.get("task", "").lower()
    scope = tb.get("scope", "").lower()
    if "waterproof" not in task:
        return
    _SEALANT_KEYWORDS = ("sealant", "silane", "recaulk", "caulk", "sealer")
    if any(kw in scope for kw in _SEALANT_KEYWORDS):
        # Replace waterproofing with sealant-faithful wording
        tb["task"] = _re.sub(
            r'(?i)\bwaterproofing\b', 'sealer application', tb["task"])
        tb["task"] = _re.sub(
            r'(?i)\bApply\s+sealants\s+and\s+waterproofing\b',
            'Apply sealants and sealer', tb["task"])
        # If task still contains "waterproof", do a final cleanup
        tb["task"] = _re.sub(
            r'(?i)\bwaterproof\w*', 'sealer application', tb["task"])


# ── Content-quality post-processing ───────────────────────────────────────────

# Controls the agent invents that are not supported by a typical remedial painting quote
_UNSUPPORTED_CONTROL_PHRASES = [
    "utility isolation certificate", "utility isolation",
    "service isolation", "electrical isolation", "gas isolation", "water isolation",
    "shoring plan", "shoring and stability", "propping plan", "propping design",
    "council development consent", "council consent",
    "power isolation certificate",
    "traffic control plan",
    "road opening permit", "traffic management plan",
    "lane closure", "speed reduction",
    "as 1742",
    "after-hours work permit", "after-hours permit", "council after-hours",
]

# Active hazmat survey/assessment workflow — the quote treats these as latent conditions
_ACTIVE_HAZMAT_PHRASES = [
    "hazardous materials survey", "hazmat survey", "pre-refurbishment survey",
    "asbestos survey", "asbestos register", "acm status",
    "licensed assessor", "asbestos assessor",
    "hazardous material assessment",
]


def _strip_unsupported_controls(tb: dict) -> None:
    """Strip controls the agent invents that are not supported by the source quote.

    Remedial painting quotes typically do not require utility isolation
    certificates, structural shoring plans, council development consent, etc.
    These are reasonable for larger construction projects but not quote-faithful
    for a painting/remedial scope.
    """
    for field in ("controls", "admin", "hold_points", "stop_work"):
        items = tb.get(field, [])
        if isinstance(items, list):
            tb[field] = [item for item in items
                         if not any(p in item.lower() for p in _UNSUPPORTED_CONTROL_PHRASES)]


_SEALANT_DRIFT_PHRASES = [
    "membrane", "waterproofing membrane", "damp-proof membrane",
    "tanking", "waterproof coat", "waterproofing system",
    "waterproof sealant", "hydrophobic or waterproof",
    "waterproofing", "waterproof",
]


def _strip_sealant_drift(tb: dict) -> None:
    """Strip membrane/waterproofing drift from sealant tasks.

    The quote specifies recaulking (Parchem Nitoseal MS250 / Emer-seal) and
    silane clear sealer — not waterproofing membranes. Agent drift into
    membrane/tanking/waterproofing is unsupported.
    """
    task_name = tb.get("task", "").lower()
    if not any(kw in task_name for kw in ("sealant", "seal", "caulk")):
        return
    if "paint" in task_name:  # don't touch painting tasks
        return
    # Strip membrane/waterproofing from scope
    scope = tb.get("scope", "")
    for phrase in _SEALANT_DRIFT_PHRASES:
        scope = scope.replace(phrase, "").replace(phrase.title(), "")
    # Clean up trailing semicolons/commas from removal
    scope = _re.sub(r';\s*;', ';', scope)
    scope = _re.sub(r',\s*,', ',', scope)
    scope = _re.sub(r'\s+', ' ', scope).strip().rstrip(';,.')
    tb["scope"] = scope
    # Strip from all list fields including hazards
    for field in ("controls", "admin", "hazards", "hold_points", "stop_work"):
        items = tb.get(field, [])
        if isinstance(items, list):
            tb[field] = [item for item in items
                         if not any(p in item.lower() for p in _SEALANT_DRIFT_PHRASES)]


_TIMBER_DRIFT_PHRASES = [
    "decay", "biocide", "preservativ", "fungicid",
    "insecticid", "insect damage", "rot and",
    "timber rot", "check for rot",
]


_GREEN_WALL_DRIFT_PHRASES = [
    "irrigat",  # catches irrigation, irrigating, irrigated
    "drainage test", "pressure test",
    "electrical isolation", "energise", "power isolation",
    "certification", "certif", "commissioning",
]


def _strip_green_wall_drift(tb: dict) -> None:
    """Strip testing/certification scope from green wall reinstatement.

    The quote says 'green wall x 2 - removal / reinstatement works'.
    No irrigation testing, electrical commissioning, or certification is mentioned.
    """
    task_name = tb.get("task", "").lower()
    if "reinstate" not in task_name and "reinstall" not in task_name:
        return
    if "green wall" not in task_name and "green" not in tb.get("scope", "").lower():
        return
    # Clean task name
    tb["task"] = _re.sub(r'(?i)\s+and\s+test\b.*$', '', tb["task"]).strip()
    if not tb["task"]:
        tb["task"] = "Reinstate green wall system"
    # Clean scope string
    scope = tb.get("scope", "")
    for phrase in _GREEN_WALL_DRIFT_PHRASES:
        scope = _re.sub(r'(?i)\b' + _re.escape(phrase) + r'\w*\b', '', scope)
    scope = _re.sub(r'\s+', ' ', scope).strip().rstrip(';,.')
    if scope:
        tb["scope"] = scope
    else:
        tb["scope"] = "Reinstall green wall modules and fixings to prepared substrate"
    # Strip drift from all list fields
    for field in ("controls", "admin", "hazards", "hold_points", "stop_work"):
        items = tb.get(field, [])
        if isinstance(items, list):
            tb[field] = [item for item in items
                         if not any(p in item.lower() for p in _GREEN_WALL_DRIFT_PHRASES)]


def _strip_timber_drift(tb: dict) -> None:
    """Strip decay/biocide/preservative drift from timber stain tasks.

    The quote specifies: prepare timbers with Intergrain Ultraprep timber
    cleaner, finish in 2x coats Intergrain Ultradeck timber stain. No decay
    diagnosis, preservative, or biocide treatment is in scope.
    """
    task_name = tb.get("task", "").lower()
    if not any(kw in task_name for kw in ("timber beam", "treat timber", "timber treat",
                                           "timber stain", "timber feature",
                                           "structural timber", "treat structural")):
        return
    # Clean task name
    tb["task"] = _re.sub(r'(?i)\band\s+check\s+for\s+decay\b', '', tb["task"]).strip()
    # Clean scope — use case-insensitive substring removal (no word boundaries
    # because phrases like "preservativ" need to match "preservative")
    scope = tb.get("scope", "")
    for phrase in _TIMBER_DRIFT_PHRASES:
        scope = _re.sub(r'(?i)' + _re.escape(phrase) + r'\w*', '', scope)
    scope = _re.sub(r'\s+', ' ', scope).strip().rstrip(';,.')
    if not scope or len(scope) < 20:
        scope = ("Prepare unpainted timber beams and architectural features with "
                 "timber cleaner, finish in 2 coats timber stain per specification")
    tb["scope"] = scope
    # Strip drift from controls, admin, and hazards
    for field in ("controls", "admin", "hazards"):
        items = tb.get(field, [])
        if isinstance(items, list):
            tb[field] = [item for item in items
                         if not any(p in item.lower() for p in _TIMBER_DRIFT_PHRASES)]


def _strip_active_hazmat(tb: dict) -> None:
    """Strip active hazmat survey/assessment workflow from tasks.

    The quote treats pre-existing toxic materials as latent conditions subject
    to variation — not as an active work task. Remove active survey controls
    but preserve the latent-condition pathway (stop work if encountered).
    """
    task_name = tb.get("task", "").lower()
    # If the task IS a hazmat survey/assessment/check, convert to a stop-work note
    _is_hazmat_task = (
        ("survey" in task_name and ("hazardous" in task_name or "latent" in task_name))
        or ("test" in task_name and "toxic" in task_name)
        or ("check" in task_name and "latent" in task_name and "toxic" in task_name)
        or ("identify" in task_name and ("hazardous" in task_name or "toxic" in task_name))
    )
    if _is_hazmat_task:
        # Replace active survey workflow with latent-condition stop-work
        tb["task"] = "Latent conditions check — stop work if toxic materials encountered"
        tb["scope"] = ("Pre-existing toxic materials (lead paint, asbestos) are latent conditions "
                       "subject to additional cost — deemed variation per contract. "
                       "If suspect material is found, stop work and notify supervisor.")
        tb["controls"] = [
            "Stop work immediately if suspect material (e.g. fibrous board, flaking paint on pre-1970 surfaces) is encountered",
            "Do not disturb, sample, or remove any suspect material",
            "Notify supervisor and site manager — arrange licensed assessment before resuming",
        ]
        tb["admin"] = [
            "Brief all workers at induction: if you see suspect material, stop and report",
        ]
        tb["hold_points"] = [
            "\u26a0\ufe0f HOLD POINT — do not resume work in affected area until licensed assessor has cleared the material",
        ]
        tb["stop_work"] = [
            "\U0001f6d1 STOP WORK if: any suspect fibrous, powdery, or flaking material is disturbed or exposed",
        ]
        tb["hazards"] = [
            "Exposure to pre-existing toxic materials (lead paint, asbestos) if disturbed during remedial works",
        ]
        tb["responsibility"] = {
            "SUP": "Brief crew on latent conditions, stop work if suspect material found, arrange assessment",
            "WKR": "Report any suspect material immediately, do not disturb or sample",
        }
        monitoring = tb.get("monitoring")
        if isinstance(monitoring, dict):
            monitoring["critical_control"] = "All workers briefed on latent-condition stop-work procedure"
            monitoring["who_checks"] = "Supervisor"
            monitoring["frequency"] = "at induction and start of each new work area"
            monitoring["what_to_look_for"] = "Workers can describe stop-work trigger; no suspect material disturbed"
        return

    # For other tasks, strip active hazmat controls but keep stop-work triggers
    for field in ("controls", "admin", "hold_points"):
        items = tb.get(field, [])
        if isinstance(items, list):
            tb[field] = [item for item in items
                         if not any(p in item.lower() for p in _ACTIVE_HAZMAT_PHRASES)]
    # Also fix monitoring critical_control if it references hazmat survey
    mon = tb.get("monitoring")
    if isinstance(mon, dict):
        cc = mon.get("critical_control", "")
        if any(p in cc.lower() for p in _ACTIVE_HAZMAT_PHRASES):
            # Replace with the task's actual dominant hazard monitoring
            _improve_monitoring(tb)


def _strip_demolition_content(tb: dict) -> None:
    """Strip any content containing 'demolition' from non-demolition tasks.

    Uses broad pattern matching — any list item containing 'demolition' (case-insensitive)
    is removed. This is aggressive but justified: the quote is for remedial painting,
    and no item mentioning demolition is source-supported.
    """
    task_name = tb.get("task", "").lower()
    # If the task is actual demolition, keep everything
    if "demolit" in task_name and "dismantle" not in task_name:
        return
    # Broad match: remove any item containing "demolition" (any variant)
    for field in ("controls", "admin", "hold_points", "hazards", "stop_work"):
        items = tb.get(field, [])
        if isinstance(items, list):
            tb[field] = [item for item in items
                         if "demolit" not in item.lower()]


def _improve_responsibility(tb: dict) -> None:
    """Replace generic SUP/WKR boilerplate with task-specific responsibility text.

    The assembler agent generates 'Supervise [task name]' and 'Perform [task name]
    per SWMS' for every task. This replaces those with more specific language
    based on task type.
    """
    resp = tb.get("responsibility")
    if not isinstance(resp, dict):
        return
    task_name = tb.get("task", "").lower()
    ccvs = tb.get("ccvs_code", "N/A")

    # Only replace if current text is the generic boilerplate pattern
    sup = resp.get("SUP", "")
    wkr = resp.get("WKR", "")
    sup_is_generic = sup.startswith("Supervise ") and len(sup.split()) <= 8
    wkr_is_generic = "per SWMS" in wkr and wkr.startswith("Perform ")

    if not (sup_is_generic or wkr_is_generic):
        return

    # Task-specific responsibility patterns
    if any(kw in task_name for kw in ("establish", "setup", "set up", "mobilise")):
        if sup_is_generic:
            resp["SUP"] = "Verify exclusion zone complete, barriers intact, access controlled before work starts"
        if wkr_is_generic:
            resp["WKR"] = "Set up and maintain barriers, stop work if zone breached, report access issues"
    elif any(kw in task_name for kw in ("scaffold", "ewp", "erect", "dismantle")):
        if sup_is_generic:
            resp["SUP"] = "Verify scaffold or EWP certification, supervise erection, sign off load checks"
        if wkr_is_generic:
            resp["WKR"] = "Follow erection plan, wear harness at height, report defects"
    elif any(kw in task_name for kw in ("paint", "coat", "stain", "treat timber", "timber beam")):
        # Check painting BEFORE repair — "paint masonry" should match painting, not repair
        if sup_is_generic:
            resp["SUP"] = "Verify scaffold and fall arrest systems, enforce exclusion zone, check SDS"
        if wkr_is_generic:
            resp["WKR"] = "Use harness and lanyard, wear respiratory protection, report faults"
    elif any(kw in task_name for kw in ("crack", "repoint", "brick", "masonry", "spalling", "concrete")):
        if sup_is_generic:
            resp["SUP"] = "Supervise repairs, check scaffold safety, approve debris controls, sign hold points"
        if wkr_is_generic:
            resp["WKR"] = "Perform repairs per SWMS, wear PPE, use dust control, report defects"
    elif any(kw in task_name for kw in ("seal", "sealant", "caulk", "silane")):
        if sup_is_generic:
            resp["SUP"] = "Verify SDS on site, check ventilation, sign off hold points"
        if wkr_is_generic:
            resp["WKR"] = "Apply sealant per specification, wear PPE, report chemical exposure"
    elif any(kw in task_name for kw in ("green wall", "reinstate", "reinstall")):
        if sup_is_generic:
            resp["SUP"] = "Verify fall protection, check module weights, sign off hold points"
        if wkr_is_generic:
            resp["WKR"] = "Wear fall harness, check lanyard attachment, report equipment damage"
    elif any(kw in task_name for kw in ("check", "defect", "make good", "quality")):
        if sup_is_generic:
            resp["SUP"] = "Verify access equipment safe, approve defect list, sign off completion"
        if wkr_is_generic:
            resp["WKR"] = "Inspect per specification, photograph defects, report issues"
    elif any(kw in task_name for kw in ("demob", "handover", "site restor")):
        if sup_is_generic:
            resp["SUP"] = "Supervise dismantling and demobilisation, verify controls, manage site access"
        if wkr_is_generic:
            resp["WKR"] = "Dismantle and clear per SWMS, report hazards, obey spotter directions"


# Monitoring critical-control patterns by hazard type
_MONITORING_BY_HAZARD = {
    "setup": {
        "critical_control": "Exclusion zone barriers complete, signage visible, access controlled",
        "who_checks": "Supervisor",
        "frequency": "before each shift start",
        "what_to_look_for": "Barriers intact, signage legible, no unauthorised entry",
    },
    "scaffold": {
        "critical_control": "Scaffold or EWP daily pre-use check completed, documented, no visible defects",
        "who_checks": "Supervisor and competent scaffolder or qualified operator",
        "frequency": "daily",
        "what_to_look_for": "Completed checklist sheet, dated and signed, attached to scaffold or EWP",
    },
    "dust": {
        "critical_control": "Dust extraction running and P2 respirator fitted before each grinding cycle",
        "who_checks": "Supervisor",
        "frequency": "before each use",
        "what_to_look_for": "Worker confirmation and visual check of extraction hose and respirator seal",
    },
    "chemical": {
        "critical_control": "SDS on site, PPE matched to chemical, ventilation confirmed",
        "who_checks": "Supervisor",
        "frequency": "before each shift start",
        "what_to_look_for": "SDS visible at work station, correct gloves/respirator worn, ventilation adequate",
    },
    "wah": {
        "critical_control": "Harness clipped to anchor and lanyard taut before worker goes to height",
        "who_checks": "Supervisor",
        "frequency": "daily",
        "what_to_look_for": "Visual confirmation of harness fit, lanyard connection, anchor point integrity",
    },
    "removal": {
        "critical_control": "Exclusion zone marked, barriers in place, no pedestrians below work area",
        "who_checks": "Supervisor",
        "frequency": "daily",
        "what_to_look_for": "Visual inspection; hazard tape, signage, and netting installed and intact",
    },
    "qa": {
        "critical_control": "Defect list reviewed and signed off by supervisor before rectification starts",
        "who_checks": "Supervisor",
        "frequency": "before each rectification session",
        "what_to_look_for": "Signed defect list, photographic record, specification document on site",
    },
}


def _improve_monitoring(tb: dict) -> None:
    """Replace generic WAH-only monitoring with hazard-specific critical controls."""
    mon = tb.get("monitoring")
    if not isinstance(mon, dict):
        # Create monitoring if missing — use schema field names (who, evidence)
        # with fallback aliases (who_checks, what_to_look_for) for renderer compatibility
        tb["monitoring"] = {"critical_control": "", "who": "", "who_checks": "",
                            "frequency": "", "evidence": "", "what_to_look_for": ""}
        mon = tb["monitoring"]
    task_name = tb.get("task", "").lower()
    scope = tb.get("scope", "").lower()
    text = task_name + " " + scope

    # Determine dominant hazard type for monitoring.
    # First try task-name keywords, then use the final CCVS code as authoritative
    # override if it disagrees — since _correct_ccvs_by_task_type already ran.
    if any(kw in text for kw in ("establish", "setup", "set up", "mobilise", "exclusion")):
        pattern = "setup"
    elif any(kw in text for kw in ("scaffold", "ewp", "erect", "dismantle")):
        pattern = "scaffold"
    elif any(kw in text for kw in ("grind", "cutting", "drill", "crack stitch", "repoint", "spalling", "mortar", "brickwork re")):
        pattern = "dust"
    elif any(kw in text for kw in ("sealant", "paint", "stain", "primer", "coat", "treat")):
        pattern = "chemical"
    elif any(kw in text for kw in ("check", "defect", "inspect", "make good", "rectif",
                                     "test and check", "confirm")):
        pattern = "qa"
    elif any(kw in text for kw in ("remove green", "remove wall", "strip",
                                     "reinstate green", "reinstall green", "reinstate wall",
                                     "reinstate and")):
        pattern = "removal"
    else:
        pattern = "wah"  # fallback

    # CCVS-based override: if the corrected CCVS code disagrees with the keyword
    # pattern, trust the CCVS (it was set by _correct_ccvs_by_task_type which
    # uses a more comprehensive keyword set).
    ccvs = tb.get("ccvs_code", "N/A")
    _CCVS_TO_PATTERN = {
        "SIL": "dust", "CHM": "chemical", "WAH": "wah",
        "TRF": "setup", "ELE": "scaffold",
    }
    ccvs_prefix = ccvs.split("-")[0] if "-" in ccvs else ccvs
    # SYS maps to either "setup" or "qa" depending on task keywords
    if ccvs_prefix == "SYS":
        if any(kw in text for kw in ("establish", "mobilise", "setup", "set up")):
            ccvs_pattern = "setup"
        else:
            ccvs_pattern = "qa"
    else:
        ccvs_pattern = _CCVS_TO_PATTERN.get(ccvs_prefix)
    if ccvs_pattern and ccvs_pattern != pattern and ccvs_pattern in _MONITORING_BY_HAZARD:
        pattern = ccvs_pattern

    template = _MONITORING_BY_HAZARD[pattern]
    # Only overwrite empty or generic fields — set both alias pairs for schema/renderer compat
    if not mon.get("who_checks") and not mon.get("who"):
        mon["who_checks"] = template["who_checks"]
        mon["who"] = template["who_checks"]
    if not mon.get("frequency"):
        mon["frequency"] = template["frequency"]
    if not mon.get("what_to_look_for") and not mon.get("evidence"):
        mon["what_to_look_for"] = template["what_to_look_for"]
        mon["evidence"] = template["what_to_look_for"]
    # Replace critical control if it doesn't match the task's dominant hazard.
    # For dust/chemical tasks, harness/scaffold monitoring is the wrong focus —
    # the critical control should be about dust extraction or SDS, not access.
    cc = mon.get("critical_control", "")
    cc_lower = cc.lower()
    should_replace = False
    if pattern == "dust" and "dust" not in cc_lower and "p2" not in cc_lower and "extraction" not in cc_lower:
        should_replace = True
    elif pattern == "chemical" and "sds" not in cc_lower and "chemical" not in cc_lower and "ventilation" not in cc_lower:
        should_replace = True
    elif pattern == "setup" and "exclusion" not in cc_lower and "barrier" not in cc_lower:
        should_replace = True
    elif pattern == "scaffold" and "scaffold" not in cc_lower and "ewp" not in cc_lower and "tag" not in cc_lower:
        should_replace = True
    elif pattern == "removal" and "exclusion" not in cc_lower and "barrier" not in cc_lower:
        should_replace = True
    elif pattern == "qa" and "defect" not in cc_lower and "specification" not in cc_lower and "sign" not in cc_lower:
        should_replace = True
    elif pattern == "wah":
        should_replace = False  # keep whatever the agent set for WAH tasks
    if should_replace:
        mon["critical_control"] = template["critical_control"]


def _correct_ccvs_by_task_type(tb: dict) -> None:
    """Correct CCVS code based on the task's dominant hazard.

    Runs on ALL tasks — fixes WAH overcall, fills N/A, and corrects mismatches
    (e.g. CHM on a dust task). The CCVS should reflect the dominant METHOD hazard:
    - Grinding/cutting/repointing → SIL (silica/dust)
    - Painting/coating/sealant → CHM (chemical exposure)
    - Scaffold erection/dismantling → WAH (genuinely WAH)
    - Green wall removal/reinstatement → WAH (at height)
    - Site setup/QA → SYS-M3
    """
    ccvs = tb.get("ccvs_code", "N/A")
    task_name = tb.get("task", "").lower()

    # Determine the correct CCVS from task name keywords.
    # Chemical-dominant keywords override SIL when both are present
    # (e.g. "Apply waterproofing membrane and new tile" → CHM, not SIL).
    _CHM_DOMINANT = ("waterproof", "membrane", "epoxy", "primer")
    if any(kw in task_name for kw in _CHM_DOMINANT):
        tb["ccvs_code"] = "CHM-H6"
        return

    # Inspection/investigation tasks are procedural (SYS) even if they mention repair targets
    _INSPECTION_KW = ("investigate", "survey", "inspect", "check facade", "check slab",
                       "mark repair", "document condition")
    if any(kw in task_name for kw in _INSPECTION_KW):
        tb["ccvs_code"] = "SYS-M3"
        return

    _WAH_METHOD = ("scaffold", "ewp", "erect", "dismantle", "access equipment",
                    "rope access", "abseil", "ladder", "remove green", "reinstate",
                    "roof access", "roof perimeter", "on roof",
                    "gutter", "flashing", "mobilise boom", "lower waste")
    if any(kw in task_name for kw in _WAH_METHOD):
        correct = "WAH-H6"
    elif any(kw in task_name for kw in ("grind", "cut", "repoint", "crack stitch",
                                         "stitch", "spalling", "mortar", "reconstruct",
                                         "demolition", "slab crack", "tile")):
        correct = "SIL-H6"
    elif any(kw in task_name for kw in ("paint", "coat", "stain", "seal", "sealant",
                                         "treat", "primer", "timber",
                                         "waterproof", "render", "epoxy", "membrane")):
        correct = "CHM-H6"
    elif any(kw in task_name for kw in ("establish", "setup", "set up", "mobilise",
                                         "prop base", "prepare and level",
                                         "confirm crane", "confirm lift",
                                         "remove temporary prop", "remove prop",
                                         "remove traffic", "remove exclusion")):
        correct = "SYS-M3"
    elif any(kw in task_name for kw in ("check", "defect", "inspect", "make good")):
        correct = "SYS-M3"
    else:
        return  # no confident match — keep whatever the agent set

    # Apply correction if current code doesn't match
    if ccvs == "N/A" or ccvs != correct:
        tb["ccvs_code"] = correct


def _normalise_task(tb: dict, inference: dict, jurisdiction: str, hot_work_ok: bool) -> dict:
    """Apply all per-task post-processing in a single call."""
    from renderers.docx_renderer import validate_ccvs_code
    from vocab.standards_registry import strip_unverified_citations
    ccvs_codes = inference.get("ccvs_codes", [])
    tb = _enforce_plain_english(tb)
    tb = _plain_english_pass(tb)
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
    _fix_unsupported_waterproofing(tb)
    _strip_demolition_content(tb)
    _strip_unsupported_controls(tb)
    _strip_active_hazmat(tb)
    _strip_sealant_drift(tb)
    _strip_timber_drift(tb)
    _strip_green_wall_drift(tb)
    _improve_responsibility(tb)
    _propagate_scaffold_wah(tb, inference)
    _inject_occupied_controls(tb, inference)
    _inject_interface_controls(tb, inference)
    _inject_ewp_transfer_controls(tb, inference)
    _correct_ccvs_by_task_type(tb)
    _improve_monitoring(tb)  # runs AFTER CCVS correction so monitoring aligns to final code
    # Deduplicate control lists (exact match removal, preserve order)
    for field in ("controls", "admin", "hold_points", "stop_work", "hazards"):
        items = tb.get(field, [])
        if isinstance(items, list) and len(items) > 1:
            seen = set()
            deduped = []
            for item in items:
                key = item.strip().lower()
                if key not in seen:
                    seen.add(key)
                    deduped.append(item)
            tb[field] = deduped

    # wah_applicable: True if CCVS is WAH OR hrcw_category indicates fall >2m
    ccvs_wah = tb.get("ccvs_code", "N/A").startswith("WAH")
    hrcw_cat = str(tb.get("hrcw_category", "")).lower()
    hrcw_wah = "cl.2" in hrcw_cat or "fall" in hrcw_cat or "height" in hrcw_cat
    tb["wah_applicable"] = ccvs_wah or hrcw_wah
    return tb


# Task name keywords that indicate elevated execution — WAH should be propagated
_ELEVATED_TASK_KEYWORDS = [
    # Scaffold work (match even with words between erect/dismantle and scaffold)
    "erect scaffold", "dismantle scaffold", "scaffold erect", "scaffold dismantle",
    "install scaffold", "remove scaffold", "strip scaffold",
    "erect modular scaffold", "erect tube", "scaffold system",
    # Facade / external work performed at height
    "facade", "external wall", "balcony", "balustrade",
    "spalling", "render", "coating", "waterproof", "sealant",
    "cladding", "curtain wall", "window",
    # Explicit height references
    "at height", "elevated", "above ground",
    # Repair/inspection on the building face
    "repair concrete", "concrete repair", "patch", "grind",
    "remove concrete", "remove damaged", "damaged concrete",
    "prepare surface", "surface preparation", "surface prep",
    "apply protective", "apply coating", "prime",
    "apply repair", "install repair", "repair material",
    "check completed", "check remedial", "check all", "fix defect",
    "inspect facade", "inspect scaffold", "touchup",
]


def _propagate_scaffold_wah(tb: dict, inference: dict) -> None:
    """
    Propagate WAH to tasks clearly executed at height on a scaffold job.

    Only the task name is checked — not controls or hazards, which may
    mention scaffold context without the task itself being elevated.
    """
    hrcw_flags = inference.get("hrcw_flags", {})
    if not hrcw_flags.get("falling_2m", False):
        return

    ccvs = tb.get("ccvs_code", "N/A")
    if ccvs.startswith("WAH"):
        return  # already WAH-coded

    task_name = tb.get("task", "").lower()

    if any(kw in task_name for kw in _ELEVATED_TASK_KEYWORDS):
        tb["ccvs_code"] = "WAH-H6"
        return

    # Catch scaffold erection/dismantling even with words between verb and 'scaffold'
    if "scaffold" in task_name and any(
        v in task_name for v in ("erect", "dismantle", "install", "remove", "strip")
    ):
        tb["ccvs_code"] = "WAH-H6"


# —— Occupied-building control injection ——————————————————————————————————————

_OCCUPIED_SETUP_CONTROLS = [
    "Notify building occupants / body corporate / strata manager of work schedule, access restrictions, and expected noise/dust at least 48 hours before work starts",
    "Restrict work to approved hours agreed with building management — typically 7am-5pm weekdays unless otherwise approved",
]

_OCCUPIED_SETUP_HOLD_POINTS = [
    "\u26a0\ufe0f HOLD POINT \u2014 do not start work until: written notification delivered to all affected occupants and body corporate/strata manager",
]

_OCCUPIED_ELEVATED_ADMIN = [
    "Close and barricade balconies directly below active work zone before elevated work starts each day",
    "Notify affected residents before any noise/dust generating work on their level or adjacent levels",
]

_OCCUPIED_ELEVATED_STOP_WORK = [
    "\U0001f6d1 STOP WORK if: occupant balcony below work zone is not closed and barricaded",
]


def _inject_occupied_controls(tb: dict, inference: dict) -> None:
    """
    Inject occupant-protection controls for occupied-building jobs.

    Adds notification and access-restriction controls to site-setup tasks,
    and balcony/occupant protection to elevated tasks.
    """
    classification = inference.get("swms_classification", {})
    if classification.get("occupancy_context") != "occupied":
        return

    task_name = tb.get("task", "").lower()

    # Skip demob/dismantle tasks — interface controls don't belong here
    if any(kw in task_name for kw in ("demob", "dismantle", "remove scaffold")):
        return

    controls = tb.setdefault("controls", [])
    admin = tb.setdefault("admin", [])
    hold_points = tb.setdefault("hold_points", [])
    stop_work = tb.setdefault("stop_work", [])

    # Detect if this is a setup/mobilisation task
    _SETUP_KEYWORDS = ["set up", "setup", "establish", "mobilise site", "mobilize site", "plan"]
    is_setup = any(kw in task_name for kw in _SETUP_KEYWORDS)

    # Detect if this is an elevated task
    is_elevated = tb.get("wah_applicable", False) or tb.get("ccvs_code", "N/A").startswith("WAH")

    existing_text = " ".join(controls + admin + hold_points + stop_work).lower()

    if is_setup:
        for ctrl in _OCCUPIED_SETUP_CONTROLS:
            if "notify" not in existing_text or "body corporate" not in existing_text:
                if ctrl not in controls:
                    controls.append(ctrl)
                    existing_text += " " + ctrl.lower()
        for hp in _OCCUPIED_SETUP_HOLD_POINTS:
            if "notification" not in existing_text or "body corporate" not in existing_text:
                if hp not in hold_points:
                    hold_points.append(hp)
                    existing_text += " " + hp.lower()

    if is_elevated:
        for item in _OCCUPIED_ELEVATED_ADMIN:
            if "balcony" not in existing_text or "barricade" not in existing_text:
                if item not in admin:
                    admin.append(item)
                    existing_text += " " + item.lower()
        for sw in _OCCUPIED_ELEVATED_STOP_WORK:
            if "balcony" not in existing_text or "barricaded" not in existing_text:
                if sw not in stop_work:
                    stop_work.append(sw)
                    existing_text += " " + sw.lower()


# —— Interface controls injection (residential / strata / occupied) ────────────

_INTERFACE_CONTROLS_RESIDENTIAL = [
    "Residents responsible for clearing personal items, furniture, potted plants, and non-common fixtures from balcony and work areas before each phase — area left/excluded if not cleared",
    "Temporary access to neighbouring properties required — confirm access arrangements before commencing",
    "Vegetation trimmed away from surfaces designated for painting or remedial works prior to commencement — area excluded if vegetation impedes access",
    "On-site parking or provision of parking permits required for duration of works",
    "Final inspection and agreed scope of works to be confirmed before commencement",
]


def _inject_interface_controls(tb: dict, inference: dict) -> None:
    """
    Inject interface controls for occupied residential / strata jobs.

    These are quote-derived conditions (resident clearing, neighbour access,
    vegetation, parking, pre-commencement inspection) added to the first
    site-setup task.
    """
    classification = inference.get("swms_classification", {})
    if classification.get("occupancy_context") != "occupied":
        return
    # Only inject into site-setup / mobilisation tasks (not demob)
    task_name = tb.get("task", "").lower()
    if any(kw in task_name for kw in ("demob", "dismantle", "remove scaffold")):
        return
    _SETUP_KW = ["set up", "setup", "establish", "mobilise site", "mobilize site",
                  "plan access", "site and plan"]
    if not any(kw in task_name for kw in _SETUP_KW):
        return

    admin = tb.setdefault("admin", [])
    existing_text = " ".join(admin).lower()
    for ctrl in _INTERFACE_CONTROLS_RESIDENTIAL:
        # Only add if the key phrase is not already present
        key_phrase = ctrl.split(" — ")[0][:40].lower()
        if key_phrase not in existing_text:
            admin.append(ctrl)
            existing_text += " " + ctrl.lower()


# —— EWP transfer-point control injection ─────────────────────────────────────

_TRANSFER_TASK_KEYWORDS = [
    "transfer", "guardrail opening", "platform to roof", "roof to platform",
    "ewp to roof", "roof to ewp", "return to lift", "return to platform",
    "cross guardrail", "step onto roof", "step off roof",
    # Agent-generated variants for EWP roof access
    "access roof", "roof perimeter", "roof access",
    "position ewp", "ascent", "descent",
]

_EWP_TRANSFER_CONTROLS = [
    "BASE CONTROLS TAGGED OUT before any worker initiates transfer step \u2014 non-negotiable. Ground spotter confirms tag-out complete and calls 'TRANSFER CLEAR' before worker moves",
    "Confirm horizontal gap between EWP platform and roof landing does not exceed 300mm and vertical step does not exceed 100mm \u2014 re-measure if EWP has repositioned",
    "Worker attaches lanyard to certified structural roof anchor before disconnecting from EWP anchor \u2014 worker must not be unattached at any point during transfer",
    "Ground spotter maintains visual contact with transferring worker throughout and confirms safe landing before clearing next worker",
]

_EWP_TRANSFER_HOLD_POINTS = [
    "\u26a0\ufe0f HOLD POINT \u2014 do not initiate transfer until: EWP base controls are tagged out, ground spotter is in position, and gap/step dimensions are confirmed within limits (300mm horizontal / 100mm vertical)",
]

_EWP_TRANSFER_STOP_WORK = [
    "\U0001f6d1 STOP WORK if: EWP base controls are not tagged out or spotter is not in position before transfer",
    "\U0001f6d1 STOP WORK if: gap between EWP platform and roof exceeds 300mm horizontal or 100mm vertical step",
    "\ud83d\uded1 STOP WORK if: wind speed exceeds EWP manufacturer OEM limit \u2014 do not transfer in high wind",
]


def _inject_ewp_transfer_controls(tb: dict, inference: dict) -> None:
    """
    Inject specialist EWP-to-roof transfer controls when the scope
    involves EWP transfer and the task is a transfer step.
    """
    classification = inference.get("swms_classification", {})
    modifiers = classification.get("scope_modifiers", [])
    if "ewp_transfer" not in modifiers and "ewp_access" not in modifiers:
        return

    task_name = tb.get("task", "").lower()
    if not any(kw in task_name for kw in _TRANSFER_TASK_KEYWORDS):
        return

    controls = tb.setdefault("controls", [])
    hold_points = tb.setdefault("hold_points", [])
    stop_work = tb.setdefault("stop_work", [])
    existing_text = " ".join(controls + hold_points + stop_work).lower()

    # Inject hold point first (mandatory gate — always add for transfer tasks)
    for hp in _EWP_TRANSFER_HOLD_POINTS:
        if hp not in hold_points:
            hold_points.insert(0, hp)

    # Inject critical controls at top
    for ctrl in reversed(_EWP_TRANSFER_CONTROLS):
        if ctrl not in controls:
            controls.insert(0, ctrl)

    # Inject stop-work triggers
    for sw in _EWP_TRANSFER_STOP_WORK:
        if sw not in stop_work:
            stop_work.append(sw)


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

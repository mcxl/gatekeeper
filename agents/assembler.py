#!/usr/bin/env python3
"""
agents/assembler.py — Agent 4: Assembler
Merges all manifests into validated TaskBlock JSON list.

Input:  TaskManifest + RiskManifest + ControlManifest + inference + project_meta
Output: list[TaskBlock dict]
"""

from __future__ import annotations
import json
import re
import anthropic

SYSTEM_PROMPT = """\
You are a SWMS document assembler for Australian construction.

You receive outputs from three specialist agents and must merge them into a
final validated list of TaskBlock JSON objects ready for Word document rendering.

PLAIN ENGLISH WRITING RULES (WorkCover NSW Guidelines):
- Use simple words: start not commence, use not utilise, before not
  prior to, check not inspect, fix not rectify, need not require,
  must not shall
- Use active voice and action verbs
- Never use: ensure, utilise, commence, prior to, shall, rectify,
  in accordance with, in the event that, due to the fact that
- If any merged text contains formal language, rewrite to plain English

YOUR JOBS:
1. Merge TaskManifest + RiskManifest + ControlManifest by sequence number
2. Populate all remaining fields: responsibility, source, approved, version
3. Enforce field limits:
   - controls: total characters across all controls ≤1800
   - admin: each item ≤100 chars
   - ppe: deduplicated, no duplicates
   - task name: ≤60 chars
   - scope: ≤120 chars
4. Verify CCVS integrity: H pre-risk must have a CCVS code (not N/A)
   APPROVED CCVS CODES — use only these exact strings, no others:
   WAH-H6, WAH-H9, IRA-H6, IRA-H9,
   ELE-M4, ELE-H6, SIL-H6, SIL-H9,
   STR-H6, STR-H9, CFS-H9,
   ENE-M4, ENE-H6, HOT-M4, HOT-H6,
   MOB-M4, MOB-H6, ASB-H6, ASB-H9,
   LED-H6, CHM-M3, CHM-H6,
   TRF-M4, TRF-H6,
   SYS-L1, SYS-L2, SYS-M3, SYS-M4, SYS-H6, SYS-H9,
   N/A
   Any code not in this list is INVALID — replace with the closest approved code or N/A.
5. wah_applicable = true ONLY if ccvs_code starts with "WAH"
6. responsibility.SUP: what the supervisor is responsible for — plain English, ≤20 words
7. responsibility.WKR: what workers are responsible for — plain English, ≤20 words

RESPONSIBILITY PATTERNS:
  SUP: "Supervise [task], ensure controls in place, sign off hold points"
  WKR: "Perform [task] per SWMS, report hazards, comply with all controls"

If any control entry exceeds 1800 chars total, trim the least critical controls
(admin first, then lower-priority engineering controls) to bring within limit.

Return ONLY a valid JSON array of TaskBlock objects. No commentary. No markdown fences.
Each TaskBlock schema:
{
  "task": "task name ≤60 chars",
  "scope": "scope ≤120 chars",
  "hazards": ["genuine risk description — what could harm workers, not task method"],
  "risk_pre": "H",
  "risk_post": "M",
  "controls": ["control 1", "control 2"],
  "hold_points": ["⚠️ HOLD POINT — ..."],
  "stop_work": ["🛑 STOP WORK if: ..."],
  "admin": ["admin item"],
  "ppe": ["PPE item"],
  "responsibility": {"SUP": "supervisor responsibility", "WKR": "worker responsibility"},
  "ccvs_code": "WAH-H6",
  "wah_applicable": false,
  "monitoring": {
    "critical_control": "observable check under 15 words",
    "who": "Supervisor",
    "frequency": "each shift start",
    "evidence": "what confirms compliance"
  },
  "source": "ai-generated",
  "approved": false,
  "version": "1.0"
}
"""

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


async def run_assembler(
    task_manifest: dict,
    risk_manifest: dict,
    control_manifest: dict,
    inference: dict,
    project_meta: dict,
) -> list[dict]:
    """
    Run Agent 4 — Assembler.
    Returns list of TaskBlock dicts.
    """
    # Pre-assemble the merged payload — Agent 4 validates and formats
    merged = _pre_merge(task_manifest, risk_manifest, control_manifest)

    project_context = (
        f"Project: {project_meta.get('project_name', 'Unknown')}\n"
        f"Site: {project_meta.get('site_address', 'Unknown')}\n"
        f"Principal contractor: {project_meta.get('principal_contractor', 'Unknown')}\n"
        f"SWMS version: {project_meta.get('version', '1.0')}"
    )

    user_content = (
        f"{project_context}\n\n"
        f"Merged task data to assemble:\n"
        f"{json.dumps(merged, indent=2)}\n\n"
        f"Assemble into final TaskBlock array. Enforce all field limits. "
        f"Return JSON array only."
    )

    message = _get_client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    text = message.content[0].text.strip()
    text = re.sub(r"^```[a-z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)

    task_blocks = json.loads(text)
    if not isinstance(task_blocks, list):
        raise ValueError("Assembler must return a JSON array")

    # Post-process: enforce constraints that Claude may miss
    for tb in task_blocks:
        _post_process_task_block(tb)

    return task_blocks


async def run_assembler_single(
    task_block: dict,
    errors: list[str],
    inference: dict,
) -> dict:
    """
    Single-task retry for a failed TaskBlock.
    Called by orchestrator when validation fails after full pipeline.
    """
    errors_str = "\n".join(f"  - {e}" for e in errors)

    user_content = (
        f"This TaskBlock failed validation with these errors:\n{errors_str}\n\n"
        f"TaskBlock to fix:\n{json.dumps(task_block, indent=2)}\n\n"
        f"Fix all errors and return the corrected TaskBlock as a JSON object."
    )

    message = _get_client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    text = message.content[0].text.strip()
    text = re.sub(r"^```[a-z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)

    fixed = json.loads(text)
    _post_process_task_block(fixed)
    return fixed


def _pre_merge(
    task_manifest: dict,
    risk_manifest: dict,
    control_manifest: dict,
) -> list[dict]:
    """
    Pre-merge the three manifests by sequence number before passing to Agent 4.
    Reduces Agent 4 token load — it only needs to format and validate.
    """
    risks = {r["sequence"]: r for r in risk_manifest["risks"]}
    controls = {c["sequence"]: c for c in control_manifest["controls"]}

    merged = []
    for task in task_manifest["tasks"]:
        seq = task["sequence"]
        risk = risks.get(seq, {})
        ctrl = controls.get(seq, {})

        merged.append({
            "sequence": seq,
            "task": task["task"],
            "scope": task["scope"],
            "trade_type": task["trade_type"],
            "hrcw": task.get("hrcw", False),
            "hrcw_category": risk.get("hrcw_category"),
            "hazards": risk.get("hazards", []),
            "dominant_hazard": risk.get("dominant_hazard", ""),
            "risk_pre": risk.get("risk_pre", "M"),
            "risk_post": risk.get("risk_post", "L"),
            "risk_pre_score": risk.get("risk_pre_score", {}),
            "risk_post_score": risk.get("risk_post_score", {}),
            "controls": ctrl.get("controls", []),
            "hold_points": ctrl.get("hold_points", []),
            "stop_work": ctrl.get("stop_work", []),
            "admin": ctrl.get("admin", []),
            "ppe": ctrl.get("ppe", []),
            "ccvs_code": ctrl.get("ccvs_code", "N/A"),
            "wah_applicable": ctrl.get("wah_applicable", False),
            "monitoring": ctrl.get("monitoring"),
        })

    return merged


def _post_process_task_block(tb: dict) -> None:
    """
    Enforce hard constraints on a TaskBlock after assembly.
    Mutates in place.
    """
    # wah_applicable must align with ccvs_code
    ccvs = tb.get("ccvs_code", "N/A")
    tb["wah_applicable"] = ccvs.startswith("WAH")

    # Deduplicate PPE
    seen = set()
    deduped_ppe = []
    for item in tb.get("ppe", []):
        norm = item.lower().split("—")[0].strip()
        if norm not in seen:
            seen.add(norm)
            deduped_ppe.append(item)
    tb["ppe"] = deduped_ppe

    # Enforce controls bullet cap — hard limit 8 per task
    controls = tb.get("controls", [])
    if len(controls) > 8:
        controls = controls[:8]
    tb["controls"] = controls

    # Set source/approved/version defaults
    tb.setdefault("source", "ai-generated")
    tb.setdefault("approved", False)
    tb.setdefault("version", "1.0")

    # Monitoring must be None when ccvs_code is N/A
    if ccvs == "N/A":
        tb["monitoring"] = None

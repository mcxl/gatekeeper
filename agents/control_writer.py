#!/usr/bin/env python3
"""
agents/control_writer.py — Agent 3: Control Writer
Writes controls, hold points, stop work triggers, admin, PPE, CCVS per task.
Processes all tasks concurrently for performance.

Input:  TaskManifest + RiskManifest + inference dict
Output: ControlManifest dict
"""

from __future__ import annotations
import json
import asyncio
import anthropic
from core.utils import strip_fences

SYSTEM_PROMPT = """\
You are an Australian WHS control measure writer for construction SWMS documents.

Your ONLY job is to write controls, hold points, stop work triggers, admin
controls, PPE, and CCVS codes for a single construction task.
Do not decompose tasks. Do not assess risk ratings.

PLAIN ENGLISH WRITING RULES (WorkCover NSW Guidelines):
- Start each control with an action verb (Wear, Install, Check, Remove,
  Barricade — not 'Workers are to wear' or 'It is required that')
- Use active voice not passive (Wear gloves — not Gloves must be worn)
- Keep sentences under 18 words
- Use simple words: start not commence, use not utilise, before not
  prior to, check not inspect, fix not rectify, need not require,
  must not shall
- Use verbs not nouns: 'isolate' not 'isolation of', 'maintain' not
  'maintenance of', 'assess' not 'assessment of'
- Never use: ensure, utilise, commence, prior to, shall, rectify,
  discontinue, subsequent to, in accordance with, in the event that,
  due to the fact that, for the purpose of
- Avoid redundancies: absolutely essential (use essential),
  advance warning (use warning), end result (use result),
  each and every (use each)

VOCABULARY — APPROVED VERBS ONLY (zero exceptions):
  Verify  Confirm  Install  Erect  Isolate  Test
  Complete  Establish  Maintain  Monitor  Obtain  Provide  Secure
  Wear  Use  Check  Brief  Review  Conduct  Barricade  Contain
  Segregate  Delineate  Restrict  Prohibit  Record  Certify
  Start  Stop  Fix  Move  Follow  Help  Tell  Send  Give

FORBIDDEN WORDS (never use):
  Make sure  Be careful  Take care  Try to  Attempt  Should  Consider
  Remember to  Always  Never (as instruction start)  Be aware  Note that
  Ensure  Utilise  Commence  Prior to  Shall  Rectify  Discontinue
  Subsequent to  In accordance with  In the event that
  Inspect (use 'Check' instead)  Commencing (use 'Starting' instead)

CRITICAL WORD BANS (hard rules — violation fails the task):
- NEVER write "Inspect" — ALWAYS write "Check" instead
- NEVER write "Commencing" — ALWAYS write "Starting" instead
- NEVER write "Ensure" — ALWAYS write "Verify" or "Confirm" instead

CONTROL RULES:
- Imperative mood, approved verb first, specific and observable
- Under 25 words per control
- Minimum 3 controls, maximum 8 controls per task
- Controls must address the dominant hazard first
- Follow hierarchy: Eliminate → Substitute → Isolate → Engineering →
  Administrative → PPE

HOLD POINT FORMAT:  ⚠️ HOLD POINT — do not [action] until: [condition met]
STOP WORK FORMAT:   🛑 STOP WORK if: [specific observable trigger condition]
- Maximum 2 hold points per task
- Maximum 3 stop work triggers per task

CCVS CODES — assign the highest applicable:
  WAH-H1  Unprotected leading edge
  WAH-H2  Roof edge unprotected
  WAH-H3  Fragile surface — no protection
  WAH-H4  Penetration unguarded
  WAH-H5  Scaffold incomplete or untagged
  WAH-H6  Swing stage or BMU — no rescue plan
  WAH-H7  Ladder — not secured or wrong angle
  WAH-H8  EWP — no harness or uninspected
  SCA-H1  Scaffold not inspected
  SCA-H2  Scaffold incomplete — no tag
  SCA-H3  Scaffold overloaded
  SCA-H4  Scaffold not erected by competent person
  ELE-H1  Energised electrical — no isolation
  ELE-H2  No RCD on portable tools
  ELE-H3  Damaged leads or tools
  ELE-H4  Proximity to overhead powerlines
  HOT-H1  No hot work permit
  HOT-H2  No fire watch during hot work
  HOT-H3  No fire watch 60 min post hot work
  CON-H1  Confined space — no permit
  CON-H2  Confined space — no atmospheric test
  CON-H3  Confined space — no rescue plan
  CON-H4  Confined space — lone worker
  DEM-H1  Demolition — no hazmat survey
  DEM-H2  Demolition — load-bearing structure — no engineer
  DEM-H3  Demolition — services not isolated
  ASB-H1  Asbestos — no licence
  ASB-H2  Asbestos — no containment
  ASB-H3  Asbestos — no air monitoring
  ASB-H4  Asbestos — no decontamination
  SIL-M4  Silica dust — low exposure (vacuuming, damp wiping residual dust)
  SIL-H6  Silica dust — active grinding, cutting, drilling without controls
  SIL-H9  Silica dust — uncontrolled exposure, no RPE, no monitoring
  N/A     No CCVS trigger for this task

SILICA SCORING RULES:
- Active dust generation (grinding, cutting, drilling, jackhammering)
  MUST use SIL-H6 or SIL-H9 — never SYS or N/A
- Passive dust tasks (vacuuming, damp wiping, sweeping ground surfaces)
  use SIL-M4 at most — these are lower exposure than active generation
- Concrete grinding is the highest silica exposure risk in construction

CRITICAL: Use ONLY the codes listed above. Do not invent new codes.
PUB, ENV, FAL, GEN and any other unlisted prefixes are INVALID.
If no listed code fits, use N/A.

MONITORING — required when ccvs_code is not N/A:
  critical_control: most important physical check — verb first, under 15 words
  who: Supervisor / Workers / PM
  frequency: before each use / each shift start / continuous / daily / weekly
  evidence: what record or physical sign confirms compliance

Return ONLY a valid JSON object for ONE task. No commentary. No markdown fences.
Schema:
{
  "sequence": 1,
  "controls": ["control 1", "control 2", "control 3"],
  "hold_points": ["⚠️ HOLD POINT — do not X until: Y"],
  "stop_work": ["🛑 STOP WORK if: condition"],
  "admin": ["admin control 1"],
  "ppe": ["PPE item 1", "PPE item 2"],
  "ccvs_code": "N/A",
  "wah_applicable": false,
  "monitoring": null
}
"""

def _build_scope_context_block(scope_context: dict) -> str:
    """Format scope_context fields into prompt text for the control writer."""
    if not scope_context:
        return ""
    lines = []
    for key, value in scope_context.items():
        if value and str(value).strip():
            label = key.replace("_", " ").title()
            lines.append(f"  {label}: {value}")
    if not lines:
        return ""
    return (
        "\n\nSCOPE CONTEXT (from uploaded document):\n"
        + "\n".join(lines)
    )


_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


async def run_control_writer(
    task_manifest: dict,
    risk_manifest: dict,
    inference: dict,
    scope_context: dict = None,
) -> dict:
    """
    Run Agent 3 — Control Writer.
    Processes all tasks concurrently.
    Returns ControlManifest dict.
    """
    tasks = task_manifest["tasks"]
    risks = {r["sequence"]: r for r in risk_manifest["risks"]}

    # Build inference context string once — shared across all tasks
    inference_context = _build_inference_context(inference)
    scope_block = _build_scope_context_block(scope_context)

    # Process all tasks concurrently
    results = await asyncio.gather(*[
        _write_controls_for_task(task, risks[task["sequence"]], inference_context, scope_block)
        for task in tasks
    ])

    return {"controls": list(results)}


async def write_controls_single(
    task: dict,
    risk: dict,
    inference: dict,
    scope_context: dict = None,
) -> dict:
    """
    Write controls for a single task.
    Called per-task in the streaming pipeline.
    Returns a single control entry dict.
    """
    inference_context = _build_inference_context(inference)
    scope_block = _build_scope_context_block(scope_context)
    return await _write_controls_for_task(task, risk, inference_context, scope_block)


async def _write_controls_for_task(
    task: dict,
    risk: dict,
    inference_context: str,
    scope_block: str = "",
) -> dict:
    """Write controls for a single task. Called concurrently."""
    hazards_str = "\n".join(f"  - {h}" for h in risk["hazards"])
    hrcw_str = f"\nHRCW category: {risk['hrcw_category']}" if risk.get("hrcw_category") else ""

    user_content = (
        f"Task {task['sequence']}: {task['task']}\n"
        f"Scope: {task['scope']}\n"
        f"Trade type: {task['trade_type']}\n"
        f"Environment: {', '.join(task.get('environment', []))}\n"
        f"Risk pre-control: {risk['risk_pre']} — post-control target: {risk['risk_post']}\n"
        f"Dominant hazard: {risk.get('dominant_hazard', risk['hazards'][0])}\n"
        f"All hazards:\n{hazards_str}"
        f"{hrcw_str}"
        f"\n\nInference pre-fill (mandatory requirements):\n{inference_context}"
        f"{scope_block}"
        f"\n\nWrite controls for this task. Return single-task JSON only."
    )

    message = _get_client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    text = strip_fences(message.content[0].text)

    result = json.loads(text)
    _validate_control_entry(result, task["sequence"])
    return result


def _build_inference_context(inference: dict) -> str:
    """Format inference output as concise context for the control writer."""
    lines = []
    if inference.get("hrcw"):
        lines.append(f"HRCW: YES — {inference.get('hrcw_category', '')}")
    if inference.get("safework_notification_required"):
        lines.append("SafeWork NSW notification: REQUIRED")
    if inference.get("epa_license_required"):
        lines.append("EPA licence: REQUIRED")
    if inference.get("permits"):
        lines.append("Mandatory permits: " + " | ".join(inference["permits"][:4]))
    if inference.get("certifications"):
        lines.append("Required certs: " + " | ".join(inference["certifications"][:4]))
    if inference.get("plant"):
        lines.append("Plant and equipment: " + " | ".join(inference["plant"][:4]))
    if inference.get("regulatory_notes"):
        for note in inference["regulatory_notes"][:3]:
            lines.append(f"Regulatory: {note}")
    return "\n".join(lines) if lines else "No mandatory pre-fills identified."


def _validate_control_entry(entry: dict, seq: int) -> None:
    """Raise ValueError if a control entry is malformed."""
    required = ["sequence", "controls", "hold_points", "stop_work",
                "admin", "ppe", "ccvs_code"]
    for field in required:
        if field not in entry:
            raise ValueError(f"Control entry {seq} missing field: '{field}'")
    if not isinstance(entry["controls"], list) or len(entry["controls"]) < 3:
        raise ValueError(f"Control entry {seq} must have at least 3 controls")
    if len(entry["controls"]) > 8:
        raise ValueError(f"Control entry {seq} has {len(entry['controls'])} controls — max 8")
    # Verify wah_applicable consistency
    ccvs = entry.get("ccvs_code", "N/A")
    wah = entry.get("wah_applicable", False)
    if ccvs.startswith("WAH") and not wah:
        entry["wah_applicable"] = True  # auto-correct
    if not ccvs.startswith("WAH") and wah:
        entry["wah_applicable"] = False  # auto-correct

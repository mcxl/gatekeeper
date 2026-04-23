#!/usr/bin/env python3
"""
agents/risk_assessor.py — Agent 2: Risk Assessor
Assesses hazards and risk ratings per task from TaskManifest.

Input:  TaskManifest + inference dict
Output: RiskManifest dict
"""

from __future__ import annotations
import re
import anthropic
from core.utils import strip_fences

from prompts.system import SAFE_METHOD_SYSTEM_BEHAVIOUR
from prompts.swms import SWMS_BEHAVIOUR

SYSTEM_PROMPT = SAFE_METHOD_SYSTEM_BEHAVIOUR + "\n\n" + SWMS_BEHAVIOUR + "\n\n" + """\
You are an Australian WHS risk assessor for construction work in NSW.

Your ONLY job is to identify hazards and assign risk ratings for each task.
Do not write control measures. Do not write PPE lists. Only assess risk.

RISK MATRIX — 3x3:
  Likelihood:   1=Unlikely  2=Possible  3=Likely
  Consequence:  1=Minor     2=Moderate  3=Severe
  Score = L x C:  1-2=L   3-4=M   6-9=H

PLAIN ENGLISH WRITING RULES (WorkCover NSW Guidelines):
- Use simple words: start not commence, use not utilise, before not
  prior to, check not inspect, fix not rectify
- Write hazard descriptions in plain English — specific and observable
- Use active voice

RULES:
- List all credible hazards per task — minimum 2, maximum 6
- Be specific: "fall from height — swing stage failure" not "fall hazard"
- risk_pre: inherent risk BEFORE any controls applied
- risk_post: residual risk AFTER controls — must be L or M, never H post-control
- hrcw_category: exact WHS Reg 2017 Sch 3 clause reference if HRCW, else null
- dominant_hazard: the single highest-consequence hazard for this task

WHS Reg 2017 Schedule 3 HRCW categories (use exact wording):
  cl.1  — Construction work on or adjacent to road used by traffic
  cl.2  — Construction work at height — risk of fall >2m
  cl.3  — Demolition of load-bearing structure
  cl.4  — Disturbance of asbestos
  cl.5  — Tilt-up or precast concrete
  cl.6  — Work in or adjacent to energised electrical installation
  cl.7  — Work in confined space
  cl.8  — Work involving use of explosives
  cl.9  — Work on or near pressurised gas distribution main
  cl.10 — Work on telecommunications or energy infrastructure
  cl.11 — Tunnelling
  cl.12 — Excavation deeper than 1.5m
  cl.13 — Work in or near shaft or trench deeper than 1.5m
  cl.14 — Coffer dam or caisson
  cl.15 — Concrete pumping
  cl.16 — Work involving diving

Return ONLY a valid JSON object. No commentary. No markdown fences.
Schema:
{
  "risks": [
    {
      "sequence": 1,
      "hazards": ["hazard 1", "hazard 2"],
      "dominant_hazard": "the highest consequence hazard",
      "risk_pre": "H",
      "risk_post": "M",
      "risk_pre_score": {"likelihood": 3, "consequence": 3},
      "risk_post_score": {"likelihood": 2, "consequence": 3},
      "hrcw_category": null
    }
  ]
}
"""

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _build_scope_context_block(scope_context: dict) -> str:
    """Format scope_context fields into prompt text for the risk assessor."""
    if not scope_context:
        return ""
    lines = []
    mapping = {
        "occupied_building": "Occupied Building",
        "height_work": "Height Work",
        "confined_spaces": "Confined Spaces",
        "hazardous_materials": "Hazardous Materials",
        "special_conditions": "Special Conditions",
        "work_areas": "Work Areas",
    }
    for key, label in mapping.items():
        value = scope_context.get(key)
        if not value:
            continue
        if isinstance(value, list):
            if value:
                lines.append(f"  {label}: {', '.join(str(v) for v in value)}")
        elif str(value).strip():
            lines.append(f"  {label}: {value}")
    if not lines:
        return ""
    return (
        "\n\nSCOPE CONTEXT:\n"
        + "\n".join(lines)
    )


async def run_risk_assessor(task_manifest: dict, inference: dict, scope_context: dict | None = None) -> dict:
    """
    Run Agent 2 — Risk Assessor.
    Returns RiskManifest dict.
    """
    tasks_summary = "\n".join(
        f"  {t['sequence']}. [{t['trade_type']}] {t['task']} — {t['scope']}"
        f"{'  [HRCW: ' + ', '.join(t.get('hrcw_flags', [])) + ']' if t.get('hrcw') else ''}"
        for t in task_manifest["tasks"]
    )

    env_summary = ", ".join(task_manifest.get("environment_summary", []))

    hrcw_notes = ""
    if inference.get("hrcw_category"):
        hrcw_notes = f"\nPre-identified HRCW: {inference['hrcw_category']}"

    user_content = (
        f"Tasks to assess:\n{tasks_summary}\n"
        f"\nEnvironment: {env_summary}"
        f"{hrcw_notes}"
        f"{_build_scope_context_block(scope_context)}"
        f"\n\nAssess hazards and risk ratings for each task. Return RiskManifest JSON only."
    )

    message = _get_client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=8192,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_content}],
    )

    block = message.content[0]
    if not hasattr(block, 'text'):
        raise ValueError(f"Unexpected content block type: {type(block)}")
    text = strip_fences(block.text)

    text = re.sub(r",\s*([}\]])", r"", text)
    from core.utils import extract_json
    manifest = extract_json(text)
    _validate_risk_manifest(manifest, len(task_manifest["tasks"]))
    return manifest


def _validate_risk_manifest(manifest: dict, expected_count: int) -> None:
    """Raise ValueError if RiskManifest is malformed."""
    if "risks" not in manifest:
        raise ValueError("RiskManifest missing 'risks' key")
    if len(manifest["risks"]) != expected_count:
        raise ValueError(
            f"RiskManifest has {len(manifest['risks'])} risks, "
            f"expected {expected_count}"
        )
    valid_ratings = {"L", "M", "H"}
    for i, risk in enumerate(manifest["risks"]):
        for field in ["sequence", "hazards", "risk_pre", "risk_post"]:
            if field not in risk:
                raise ValueError(f"Risk {i+1} missing field: '{field}'")
        if risk["risk_pre"] not in valid_ratings:
            raise ValueError(f"Risk {i+1} invalid risk_pre: '{risk['risk_pre']}'")
        if risk["risk_post"] not in valid_ratings:
            raise ValueError(f"Risk {i+1} invalid risk_post: '{risk['risk_post']}'")
        if risk["risk_post"] == "H":
            raise ValueError(
                f"Risk {i+1} risk_post is H — residual risk must be L or M"
            )
        if not isinstance(risk["hazards"], list) or len(risk["hazards"]) < 2:
            raise ValueError(f"Risk {i+1} must have at least 2 hazards")

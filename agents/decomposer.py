#!/usr/bin/env python3
"""
TASK COUNT LIMIT: Generate a maximum of 12 tasks. Combine minor steps into logical groups to stay within this limit. Quality over quantity — 8-12 well-scoped tasks is ideal.
agents/decomposer.py — Agent 1: Task Decomposer
Breaks a work description into an ordered TaskManifest.

Input:  raw work description + inference dict
Output: TaskManifest dict
"""

from __future__ import annotations
import json
import re
import anthropic
from core.utils import strip_fences

SYSTEM_PROMPT = """\
You are a construction SWMS task decomposer for Australian construction work.

Your ONLY job is to break a work description into an ordered list of logical tasks.
Do not assess risk. Do not write controls. Do not write PPE. Only decompose.

PLAIN ENGLISH WRITING RULES (WorkCover NSW Guidelines):
- Use simple words: start not commence, use not utilise, before not
  prior to, check not inspect, fix not rectify, need not require
- Use active voice and action verbs — verb first
- Keep task names and scope text concise and direct

RULES:
- Maximum 8 tasks. 6-8 tasks is ideal. Combine minor steps into logical groups.
- Tasks must be in logical work sequence:
    mobilisation → site establishment → preparatory works →
    principal works → finishing → defects / make good → demobilisation

TRADE-SPECIFIC SEQUENCE RULES (override generic sequence):
- Tilt-up or precast concrete: site setup → formwork erection →
  reinforcement → concrete pour → cure and strip formwork →
  panel preparation and inspection → crane erection and panel
  installation → post-erection bracing → defect inspection and
  fix → brace removal (engineer release only) → demobilisation.
  NEVER place brace removal before erection. NEVER place site
  setup after any construction activity.
- Scaffold: site setup → scaffold erection → principal works →
  scaffold dismantling → demobilisation.
- Demolition: site setup → services isolation → hazmat survey
  and removal → structural demolition (top-down) → debris
  removal → demobilisation.

- Each task must be a discrete, observable unit of work
- task field: verb first, plain English, under 10 words
- scope field: what is specifically included in this task, under 25 words
- trade_type: one of —
    General, WAH, Structural, Electrical, Plumbing, Gas, Mechanical,
    Civil, Demolition, Painting, Waterproofing, Concrete, Roofing, Other
- environment: list of applicable flags from —
    at height, occupied building, near public, confined space, indoor,
    outdoor, near traffic, near waterway, near services, hot work,
    hazmat, night work, remote
- hrcw: true only if task directly involves WHS Reg 2017 Schedule 3 work
- hrcw_flags: list of HRCW categories that apply, empty list if hrcw=false
- complexity: low / medium / high

Return ONLY a valid JSON object. No commentary. No markdown fences.
Schema:
{
  "tasks": [
    {
      "sequence": 1,
      "task": "verb-first task name under 10 words",
      "scope": "what is included under 25 words",
      "trade_type": "General",
      "environment": ["flag1", "flag2"],
      "hrcw": false,
      "hrcw_flags": [],
      "complexity": "low"
    }
  ],
  "total_tasks": 1,
  "primary_trade": "trade name",
  "environment_summary": ["all unique environment flags across all tasks"],
  "hrcw_present": false
}
"""

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _build_scope_context_block(scope_context: dict) -> str:
    """Format scope_context fields into prompt text for the decomposer."""
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
        "\n\nSCOPE CONTEXT:\n"
        + "\n".join(lines)
    )


async def run_decomposer(description: str, inference: dict, scope_context: dict | None = None) -> dict:
    """
    Run Agent 1 — Task Decomposer.
    Returns TaskManifest dict.
    """
    hrcw_context = ""
    if inference.get("hrcw"):
        hrcw_context = f"\nHRCW category identified: {inference.get('hrcw_category', 'Unknown')}"

    env_context = ""
    env_flags = [
        q for q in inference.get("qualifications", [])[:6]
        if any(w in q.lower() for w in ["height", "occupied", "traffic", "water", "confined", "hazmat"])
    ]
    if env_flags:
        env_context = "\nEnvironment context from pre-analysis:\n" + "\n".join(f"  - {e}" for e in env_flags)

    scope_block = _build_scope_context_block(scope_context)

    user_content = (
        f"Work description:\n{description}"
        f"{hrcw_context}"
        f"{env_context}"
        f"{scope_block}"
        f"\n\nGenerate between 8 and 12 tasks. Maximum 12 — combine minor steps if needed."
        f"\n\nDecompose into ordered tasks. Return TaskManifest JSON only."
    )

    message = _get_client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    block = message.content[0]
    if not hasattr(block, 'text'):
        raise ValueError(f"Unexpected content block type: {type(block)}")
    text = strip_fences(block.text)

    text = re.sub(r",\s*([}\]])", r"", text)
    manifest = json.loads(text)
    _validate_task_manifest(manifest)
    return manifest


def _validate_task_manifest(manifest: dict) -> None:
    """Raise ValueError if TaskManifest is malformed."""
    required_keys = ["tasks", "total_tasks", "primary_trade", "hrcw_present"]
    for key in required_keys:
        if key not in manifest:
            raise ValueError(f"TaskManifest missing required key: '{key}'")
    if not isinstance(manifest["tasks"], list) or len(manifest["tasks"]) == 0:
        raise ValueError("TaskManifest.tasks must be a non-empty list")
    if len(manifest["tasks"]) > 12:
        raise ValueError(f"TaskManifest has {len(manifest['tasks'])} tasks — maximum is 12")
    for i, task in enumerate(manifest["tasks"]):
        for field in ["sequence", "task", "scope", "trade_type", "hrcw", "complexity"]:
            if field not in task:
                raise ValueError(f"Task {i+1} missing field: '{field}'")

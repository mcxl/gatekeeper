#!/usr/bin/env python3
"""
core/generate.py — Claude API task generation with validation and audit logging.

generate_task(raw_input, user) → TaskBlock
  Calls Claude API, parses JSON, validates, retries once on failure.
  Raises GenerationError if both attempts fail.
  All attempts logged to AuditLog.
"""

import hashlib
import json
import os

from dotenv import load_dotenv
load_dotenv()

import anthropic

from core.schema import AuditEvent, TaskBlock, ValidationResult
from core.validate import validate_task
from core.audit import log_event

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vocab.swms_vocabulary import HAZARDS  # import to confirm vocab path works

# Re-import WAH_SENTENCE from validate (single source of truth)
from core.validate import WAH_SENTENCE

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2048

SYSTEM_PROMPT = """You are Gatekeeper SWMS Generator.

Generate a commercially usable Australian Safe Work Method
Statement using minimal user input and strong structured inference.

Output one JSON object only matching the TaskBlock schema.
Do not output commentary, markdown, or explanations.

TAXONOMY — Gatekeeper v2.0 Final

15 live hazard families:
WAH, IRA, ELE, SIL, STR, CFS, ENE, HOT, MOB, ASB, LED, TRF, ENV, CHM, SYS

Retired codes — remap before use:
WFA -> WAH, HAZ -> CHM, PRE -> ENE, WFR -> WAH, EMR -> SYS

30 approved CCVS codes (scores must be 1,2,3,4,6,9 only):
WAH-H6, WAH-H9, IRA-H6, IRA-H9,
ELE-M4, ELE-H6, SIL-H6, SIL-H9,
STR-H6, STR-H9, CFS-H9,
ENE-M4, ENE-H6, HOT-M4, HOT-H6,
MOB-M4, MOB-H6, ASB-H6, ASB-H9,
LED-H6, CHM-M3, CHM-H6,
TRF-M4, TRF-H6,
SYS-L1, SYS-L2, SYS-M3, SYS-M4, SYS-H6, SYS-H9

RISK MATRIX — 3x3 only
Likelihood: Unlikely(1), Possible(2), Almost Certain(3)
Consequence: Low(1), Medium(2), High(3)
Score = likelihood x consequence
Valid scores: 1, 2, 3, 4, 6, 9
Labels: Low(1), Low(2), Medium(3), Medium(4), High(6), High(9)

CCVS TRIGGER RULE
A task triggers CCVS when all four conditions are met:
- hazard family matches an approved code
- consequence letter matches (L/M/H)
- pre-control score meets or exceeds threshold
- resulting code is in the approved CCVS list

When CCVS triggers:
- ccvs_code = approved code (e.g. WAH-H6)
- first control must be HOLD POINT block
- HOLD POINT heading exactly: CCVS —HOLD POINT - do not start work until

When CCVS does not trigger:
- ccvs_code = N/A

The code appears ONLY in ccvs_code field.
Never in controls, admin, ppe, or responsibility fields.

CONTROL ORDER (always this sequence):
1. hold_point (only if CCVS triggers)
2. engineering controls
3. admin controls
4. ppe
5. stop_work

FORMATTING RULES
- Never use colon character in control text
- Never use semicolon character
- Use em dash as separator — bold verification phrase
- One control per bullet
- Verb first (Verify, Install, Inspect, Barricade, Record, Tag-out)
- 6-12 words per bullet, 18-word hard cap
- WAH cross-reference line exempt from word cap

RESPONSIBILITY FORMAT
Role — specific obligation (max 10 words)
Roles: SUP, WKR, SUB, PM, OP
Never include role names in controls fields.

OUTPUT — TaskBlock schema:
{
  "task": "task name",
  "scope": "scope note",
  "risk_pre": "High(6)",
  "risk_post": "Low(2)",
  "hold_points": ["item 1", "item 2"],
  "controls": ["control 1", "control 2"],
  "stop_work": ["trigger 1"],
  "admin": ["admin item"],
  "ppe": ["ppe item"],
  "responsibility": {"SUP": "obligation", "WKR": "obligation"},
  "ccvs_code": "WAH-H6",
  "wah_applicable": false,
  "source": "ai-generated",
  "approved": false,
  "version": "1.0"
}
"""


class GenerationError(Exception):
    """Raised when generation fails validation after two attempts."""
    def __init__(self, message: str, result: ValidationResult):
        super().__init__(message)
        self.result = result


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _call_api(client: anthropic.Anthropic, prompt: str) -> str:
    """Call Claude API and return raw text response."""
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def _parse_task(raw: str) -> TaskBlock:
    """Parse JSON string into TaskBlock. Strips code fences if present."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(
            lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        )
    data = json.loads(text)
    return TaskBlock(
        task=data.get("task", ""),
        scope=data.get("scope", ""),
        risk_pre=data.get("risk_pre", ""),
        risk_post=data.get("risk_post", ""),
        hold_points=data.get("hold_points", []),
        controls=data.get("controls", []),
        stop_work=data.get("stop_work", []),
        admin=data.get("admin", []),
        ppe=data.get("ppe", []),
        responsibility=data.get("responsibility", {"SUP": "", "WKR": ""}),
        ccvs_code=data.get("ccvs_code"),
        wah_applicable=bool(data.get("wah_applicable", False)),
        source="ai-generated",
        approved=False,
    )


def generate_task(raw_input: str, user: str = "system") -> TaskBlock:
    """
    Generate a TaskBlock via Claude API.

    - Calls API with raw_input.
    - Parses JSON response → TaskBlock.
    - Validates with validate_task(). On failure, retries once with
      errors appended to the prompt.
    - If second attempt fails: raises GenerationError.
    - Logs every attempt (GENERATED or VALIDATION_FAILED) to AuditLog.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY environment variable not set.")

    client = anthropic.Anthropic(api_key=api_key)

    prompt = raw_input
    last_result: ValidationResult | None = None

    for attempt in range(1, 3):
        raw_response = _call_api(client, prompt)

        try:
            task = _parse_task(raw_response)
        except Exception as exc:
            log_event(AuditEvent(
                event_type="VALIDATION_FAILED",
                user=user,
                inputs=prompt[:500],
                output_hash=_hash(raw_response),
                ai_unapproved=True,
            ))
            if attempt == 2:
                raise GenerationError(
                    f"JSON parse failed on attempt {attempt}: {exc}",
                    ValidationResult(
                        passed=False,
                        errors=[f"JSON parse error: {exc}"],
                    ),
                )
            prompt = (
                raw_input
                + f"\n\nPrevious attempt produced invalid JSON: {exc}"
                + "\nOutput valid JSON only."
            )
            continue

        result = validate_task(task)

        if result.passed:
            log_event(AuditEvent(
                event_type="GENERATED",
                user=user,
                inputs=prompt[:500],
                output_hash=_hash(raw_response),
                ai_unapproved=True,
            ))
            return task

        # Validation failed
        last_result = result
        log_event(AuditEvent(
            event_type="VALIDATION_FAILED",
            user=user,
            inputs=prompt[:500],
            output_hash=_hash(raw_response),
            ai_unapproved=True,
        ))

        if attempt == 1:
            error_summary = "\n".join(result.errors[:5])
            prompt = (
                raw_input
                + f"\n\nPrevious attempt failed validation:\n{error_summary}"
                + "\nFix all errors and output valid JSON only."
            )

    raise GenerationError(
        f"Generation failed validation after 2 attempts. "
        f"Errors: {last_result.errors}",
        last_result,
    )

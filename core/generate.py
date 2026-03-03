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

SYSTEM_PROMPT = (
    "You are an Australian WHS specialist generating "
    "SWMS task content. Output ONLY valid JSON matching this schema exactly.\n"
    "No markdown. No commentary.\n"
    "{task, scope, risk_pre, risk_post, hold_points[], controls[], "
    "stop_work[], admin[], ppe[], responsibility{SUP,WKR}, "
    "ccvs_code or null, wah_applicable true/false}\n"
    "RULES:\n"
    "- One item per array = one control only\n"
    "- If wah_applicable true, controls[0] must be WAH sentence verbatim:\n"
    + WAH_SENTENCE
    + "\n- ccvs_code in ccvs_code field only — never in controls or admin\n"
    "- Role names in responsibility only — never in controls\n"
    "- Verb-first bullets. Hard cap 18 words per bullet. No semicolons."
)


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

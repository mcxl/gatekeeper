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
from core.inference_matrix import infer_to_dict

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vocab.swms_vocabulary import HAZARDS  # import to confirm vocab path works

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

MONITORING RULE
Generate monitoring only when ccvs_code is not N/A.
When monitoring is required:
- critical_control: the single most important physical check — verb first, observable, under 15 words
- who: role title only (Supervisor, Workers, PM)
- frequency: one of — before each use, each shift start, continuous, daily, weekly
- evidence: what physical record or observable sign confirms the control is in place
When ccvs_code = N/A: omit monitoring field entirely (null).



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
- Verb first (Verify, Install, Check, Barricade, Record, Tag-out)
- 6-12 words per bullet, 18-word hard cap
- WAH cross-reference line exempt from word cap
- WAH cross-reference line only permitted when wah_applicable is true
- When wah_applicable is false, omit WAH cross-reference entirely — do not add it to controls

RESPONSIBILITY FORMAT
Role — specific obligation (max 10 words)
Roles: SUP, WKR, SUB, PM, OP
Never include role names in controls fields.

HAZARD DESCRIPTIONS
The "hazards" field must list genuine risks — what could go wrong and harm workers.
Not task methods or scope. Examples:
- "Respirable crystalline silica dust — lung disease, silicosis"
- "Skin sensitisation from uncured epoxy resin — chemical burns, dermatitis"
- "Struck by falling objects — head/body injury"
Minimum 2 hazards per task.

OUTPUT — TaskBlock schema:
{
  "task": "task name",
  "scope": "scope note",
  "hazards": ["hazard description 1", "hazard description 2"],
  "risk_pre": "High(6)",
  "risk_post": "Low(2)",
  "hold_points": ["item 1", "item 2"],
  "controls": ["control 1", "control 2"],
  "stop_work": ["trigger 1"],
  "admin": ["admin item"],
  "ppe": ["ppe item"],
  "responsibility": {"SUP": "obligation", "WKR": "obligation"},
  "ccvs_code": "WAH-H6",
  "monitoring": {
    "critical_control": "what the supervisor physically checks — one observable action",
    "who": "Supervisor",
    "frequency": "each shift start",
    "evidence": "what record or physical sign confirms compliance"
  },
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
    monitoring_data = data.get("monitoring")
    monitoring = None
    if monitoring_data and isinstance(monitoring_data, dict):
        from core.schema import MonitoringEntry
        try:
            monitoring = MonitoringEntry(**monitoring_data)
        except Exception:
            monitoring = None

    # Strip role-name prefixes from admin/controls/ppe bullets (Check 3 guard)
    # Converts "Supervisor to check barriers" -> "Check barriers"
    import re as _re
    _ROLE_PREFIX = _re.compile(
        r'^(SUP|WKR|SUB|PM|OP|Supervisor|Worker|Subcontractor|Operator)'
        r'\s+(to\s+|[-\u2014]\s*)',
        _re.IGNORECASE
    )
    for field in ("controls", "admin", "ppe"):
        cleaned = []
        for item in data.get(field, []):
            stripped = _ROLE_PREFIX.sub("", item).strip()
            if stripped:
                # Capitalise first letter after stripping
                stripped = stripped[0].upper() + stripped[1:]
            cleaned.append(stripped)
        data[field] = cleaned

    # Force wah_applicable=False when ccvs_code is not a WAH code.
    # Guards against model incorrectly setting wah_applicable=true for tasks
    # like LED-H6 (lead paint ground floor) which trigger Check 4 failures.
    import re
    ccvs_code = data.get("ccvs_code") or "N/A"
    wah_ccvs = str(ccvs_code).startswith("WAH")
    if not wah_ccvs:
        data["wah_applicable"] = False
    wah_applicable = bool(data.get("wah_applicable", False))

    # Strip WAH cross-reference bullets when wah_applicable is not active.
    if not wah_applicable:
        for field in ("controls", "admin", "hold_points"):
            data[field] = [
                item for item in data.get(field, [])
                if "WAH" not in item
            ]

    return TaskBlock(
        task=data.get("task", ""),
        scope=data.get("scope", ""),
        hazards=data.get("hazards", []),
        risk_pre=data.get("risk_pre", ""),
        risk_post=data.get("risk_post", ""),
        hold_points=data.get("hold_points", []),
        controls=data.get("controls", []),
        stop_work=data.get("stop_work", []),
        admin=data.get("admin", []),
        ppe=data.get("ppe", []),
        responsibility=data.get("responsibility", {"SUP": "", "WKR": ""}),
        ccvs_code=data.get("ccvs_code"),
        monitoring=monitoring,
        wah_applicable=bool(data.get("wah_applicable", False)),
        source="ai-generated",
        approved=False,
    )




def _build_inference_block(inferred: dict) -> str:
    """
    Format inferred requirements as a structured prompt block.
    Returns empty string if inference found nothing significant.
    """
    if not inferred:
        return ""

    lines = []

    if inferred.get("hrcw"):
        lines.append("HRCW: YES")
        if inferred.get("hrcw_category"):
            lines.append(f"HRCW category: {inferred['hrcw_category']}")
        if inferred.get("hrcw_license_class"):
            lines.append(f"Required licence: {inferred['hrcw_license_class']}")

    if inferred.get("safework_notification_required"):
        lines.append("SafeWork NSW notification: REQUIRED before work commences")

    if inferred.get("epa_license_required"):
        lines.append("EPA licence: REQUIRED")

    if inferred.get("certifications"):
        certs = inferred["certifications"][:6]
        lines.append("Mandatory certifications:")
        for c in certs:
            lines.append(f"  - {c}")

    if inferred.get("permits"):
        permits = inferred["permits"][:6]
        lines.append("Mandatory permits and approvals:")
        for p in permits:
            lines.append(f"  - {p}")

    if inferred.get("ppe"):
        baseline = {"safety glasses", "high-visibility", "steel-capped", "hard hat"}
        extra_ppe = [
            p for p in inferred["ppe"]
            if not any(b in p.lower() for b in baseline)
        ][:6]
        if extra_ppe:
            lines.append("Additional mandatory PPE:")
            for p in extra_ppe:
                lines.append(f"  - {p}")

    if inferred.get("notifications"):
        notifs = inferred["notifications"][:4]
        lines.append("Required notifications:")
        for n in notifs:
            lines.append(f"  - {n}")

    if inferred.get("regulatory_notes"):
        notes = inferred["regulatory_notes"][:3]
        lines.append("Regulatory notes:")
        for n in notes:
            lines.append(f"  - {n}")

    if not lines:
        return ""

    block = (
        "\n\n--- MANDATORY REQUIREMENTS (from WHS inference) ---"
        "\nThe following requirements are mandatory for this work type."
        "\nAll items below MUST be reflected in controls, admin, and PPE fields."
        "\n"
        + "\n".join(lines)
        + "\n--- END MANDATORY REQUIREMENTS ---"
    )
    return block

def _build_scope_block(scope_context: dict) -> str:
    """Format scope_context fields into a readable block for prompts."""
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
        "\n\n--- SCOPE CONTEXT (from uploaded document) ---\n"
        + "\n".join(lines)
        + "\n--- END SCOPE CONTEXT ---"
    )


def generate_task(raw_input: str, user: str = "system", scope_context: dict = None) -> TaskBlock:
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

    # ── Inference pre-fill ────────────────────────────────────────────────────
    try:
        _inferred = infer_to_dict(raw_input)
    except Exception:
        _inferred = {}

    _inference_block = _build_inference_block(_inferred)
    _scope_block = _build_scope_block(scope_context)
    prompt = raw_input + _inference_block + _scope_block
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
            fog_errors = [e for e in result.errors if "Fog score" in e]
            check2_errors = [e for e in result.errors if "Check 2" in e]
            check3_errors = [e for e in result.errors if "Check 3" in e]
            other_errors = [
                e for e in result.errors
                if "Fog score" not in e and "Check 2" not in e and "Check 3" not in e
            ]

            error_summary = "\n".join((other_errors + check2_errors + check3_errors + fog_errors)[:7])

            fog_hint = ""
            if fog_errors:
                fog_hint = (
                    "\n\nFOG REWRITE RULES — apply to every flagged bullet:"
                    "\n- Replace any word with 3+ syllables with a shorter equivalent"
                    "\n- Maximum 2 polysyllabic words per bullet"
                    "\n- Examples: 'monitoring' -> 'checking', 'confirmed' -> 'sighted',"
                    " 'application' -> 'use', 'baseline' -> 'reading',"
                    " 'encapsulation' -> 'sealing', 'containment' -> 'barrier'"
                    "\n- Rewrite the entire bullet in plain English, verb first, under 12 words"
                )

            check2_hint = ""
            if check2_errors:
                check2_hint = (
                    "\n\nCHECK 2 — HAZARD CODE RULE:"
                    "\n- Hazard family codes (WAH, IRA, ELE, SIL, STR, CFS, ENE, HOT, MOB,"
                    " ASB, LED, TRF, ENV, CHM, SYS) must NEVER appear in bullet text"
                    "\n- These codes belong only in the ccvs_code field"
                    "\n- Remove or rephrase any bullet containing a bare hazard code"
                    "\n- Example: 'WAH cross-reference — ground floor only' is INVALID"
                    "\n  Rewrite as: 'Ground floor work only — no fall risk above 1.5m'"
                )

            check3_hint = ""
            if check3_errors:
                check3_hint = (
                    "\n\nCHECK 3 — ROLE NAME RULE:"
                    "\n- Role names (SUP, WKR, SUB, PM, OP, Supervisor, Worker,"
                    " Subcontractor, Operator) must NEVER appear in controls, admin, or ppe fields"
                    "\n- Role obligations belong only in the responsibility field"
                    "\n- Remove the role name and rewrite as a plain instruction"
                    "\n- Example: 'Supervisor to inspect containment' is INVALID in admin"
                    "\n  Rewrite as: 'Inspect containment barriers before work starts'"
                )

            prompt = (
                raw_input
                + f"\n\nPrevious attempt failed validation:\n{error_summary}"
                + check2_hint
                + check3_hint
                + fog_hint
                + "\nFix all errors and output valid JSON only."
            )

    raise GenerationError(
        f"Generation failed validation after 2 attempts. "
        f"Errors: {last_result.errors}",
        last_result,
    )
